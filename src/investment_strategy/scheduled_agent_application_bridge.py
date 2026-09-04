"""Issue-comment ingress for repository-owned Scheduled Agent effect application."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from investment_strategy.issue_comment_bridge import MachineDispatchDecision
from investment_strategy.scheduled_agent_checkin import is_runtime_checkin_issue
from investment_strategy.scheduled_agent_dispatch_result import fetch_dispatch_result
from investment_strategy.scheduled_agent_effect_contract import GITHUB_MUTATION_KIND
from investment_strategy.scheduled_agent_effects import (
    StagedEffect,
    parse_effect_batch,
    topology_allows_successor,
)
from investment_strategy.scheduled_agent_merge_acceptance import run_guarded_effect_application
from investment_strategy.scheduled_agent_runtime import WorkerRequest

APPLICATION_REQUEST_MARKER = "EFFECT_REQUEST"
DISPATCH_REQUEST_COMMENT_ID_PREFIX = "Dispatch-Request-Comment-ID: "
DISPATCH_RUN_ID_PREFIX = "Dispatch-Run-ID: "
WORKER_RESULT_B64_PREFIX = "Worker-Result-B64: "
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"
_CONTENT_OPERATIONS = frozenset({"contents-upsert", "contents-delete"})


@dataclass(frozen=True)
class ApplicationRequest:
    """One transport request bound to one exact prior machine dispatch run."""

    dispatch_request_comment_id: int
    dispatch_run_id: int
    raw_worker_result: str


@dataclass(frozen=True)
class ApplicationPlan:
    """Validated application input or an unrelated-comment no-op."""

    should_apply: bool
    source: WorkerRequest | None = None
    raw_worker_result: str | None = None
    effect_request_comment_id: int | None = None


@dataclass(frozen=True)
class ExactValidationMutation:
    """One content mutation whose Git commit must appear in the exact post-apply chain."""

    operation: str
    path: str
    branch: str
    message: str
    blob_sha: str | None = None


@dataclass(frozen=True)
class ExactValidationProbe:
    """Pre-application branch identity plus the exact expected content commit sequence."""

    branch: str
    before_sha: str
    mutations: tuple[ExactValidationMutation, ...]


@dataclass(frozen=True)
class ExactValidationTarget:
    """Exact repository revision proven to be the final application-produced revision."""

    repository: str
    revision: str
    correlation: str


def _positive_decimal(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0 or str(parsed) != value:
        return None
    return parsed


def parse_application_request(body: str) -> ApplicationRequest | None:
    """Parse the exact bounded EFFECT_REQUEST transport format."""

    lines = body.split("\n")
    if not lines or lines[0] != APPLICATION_REQUEST_MARKER:
        return None
    if len(lines) != 4:
        raise ValueError("EFFECT_REQUEST must contain exactly four lines")
    if not lines[1].startswith(DISPATCH_REQUEST_COMMENT_ID_PREFIX):
        raise ValueError("EFFECT_REQUEST dispatch request id is missing")
    if not lines[2].startswith(DISPATCH_RUN_ID_PREFIX):
        raise ValueError("EFFECT_REQUEST dispatch run id is missing")
    if not lines[3].startswith(WORKER_RESULT_B64_PREFIX):
        raise ValueError("EFFECT_REQUEST worker result is missing")

    request_comment_id = _positive_decimal(lines[1][len(DISPATCH_REQUEST_COMMENT_ID_PREFIX) :])
    dispatch_run_id = _positive_decimal(lines[2][len(DISPATCH_RUN_ID_PREFIX) :])
    encoded_result = lines[3][len(WORKER_RESULT_B64_PREFIX) :]
    if request_comment_id is None or dispatch_run_id is None or not encoded_result:
        raise ValueError("EFFECT_REQUEST identity is invalid")
    if encoded_result != encoded_result.strip():
        raise ValueError("EFFECT_REQUEST worker result must be trimmed")

    try:
        raw_worker_result = base64.b64decode(encoded_result.encode("ascii"), validate=True).decode(
            "utf-8"
        )
        decoded = json.loads(raw_worker_result)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise ValueError("EFFECT_REQUEST worker result is not valid base64 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("EFFECT_REQUEST worker result must decode to a JSON object")

    return ApplicationRequest(
        dispatch_request_comment_id=request_comment_id,
        dispatch_run_id=dispatch_run_id,
        raw_worker_result=raw_worker_result,
    )


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _app_slug(payload: Mapping[str, object]) -> str | None:
    app = _as_mapping(payload.get("performed_via_github_app"))
    slug = None if app is None else app.get("slug")
    return slug if isinstance(slug, str) else None


def _actor_login(payload: Mapping[str, object]) -> str | None:
    user = _as_mapping(payload.get("user"))
    login = None if user is None else user.get("login")
    return login if isinstance(login, str) else None


def _trusted_connector_comment(comment: Mapping[str, object], repository_owner: str) -> bool:
    return (
        _actor_login(comment) == repository_owner
        and _app_slug(comment) == _CHATGPT_CONNECTOR_APP_SLUG
    )


def plan_application(
    *,
    event: Mapping[str, object],
    request: ApplicationRequest,
    dispatch_result: MachineDispatchDecision,
    repository: str,
    current_revision: str,
) -> ApplicationPlan:
    """Validate event identity and one run-scoped dispatch result."""

    if "/" not in repository or not current_revision:
        raise ValueError("repository and current revision are required")
    issue = _as_mapping(event.get("issue"))
    event_comment = _as_mapping(event.get("comment"))
    if event.get("action") != "created" or issue is None or event_comment is None:
        return ApplicationPlan(False)
    if "pull_request" in issue or not is_runtime_checkin_issue(issue):
        return ApplicationPlan(False)

    body = event_comment.get("body")
    if not isinstance(body, str) or parse_application_request(body) != request:
        raise ValueError("EFFECT_REQUEST event body does not match parsed request")
    repository_owner = repository.split("/", 1)[0]
    if not _trusted_connector_comment(event_comment, repository_owner):
        raise ValueError("EFFECT_REQUEST must originate from the configured ChatGPT connector")
    event_comment_id = _positive_int(event_comment.get("id"))
    if event_comment_id is None:
        raise ValueError("EFFECT_REQUEST event comment id is invalid")
    if request.dispatch_request_comment_id != dispatch_result.request_comment_id:
        raise ValueError("EFFECT_REQUEST request does not match dispatch result")
    if dispatch_result.default_branch_revision != current_revision:
        raise ValueError("DISPATCH_DECISION revision is stale")
    if (
        dispatch_result.disposition != "AUTHORIZE"
        or dispatch_result.issue_number is None
        or dispatch_result.role is None
        or dispatch_result.action is None
    ):
        raise ValueError("EFFECT_REQUEST requires an AUTHORIZE dispatch result")

    return ApplicationPlan(
        should_apply=True,
        source=WorkerRequest(
            issue_number=dispatch_result.issue_number,
            role=dispatch_result.role,
            action=dispatch_result.action,
            debt_disposition=dispatch_result.debt_disposition,
        ),
        raw_worker_result=request.raw_worker_result,
        effect_request_comment_id=event_comment_id,
    )


def _github_json(repository: str, token: str, api_path: str) -> object:
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        return json.loads(response.read().decode("utf-8"))


def _git_blob_sha(content: str) -> str:
    encoded = content.encode("utf-8")
    header = f"blob {len(encoded)}\0".encode("ascii")
    return hashlib.sha1(header + encoded, usedforsecurity=False).hexdigest()


def _branch_head_sha(repository: str, token: str, branch: str) -> str:
    decoded = _github_json(repository, token, f"branches/{quote(branch, safe='')}")
    payload = _as_mapping(decoded)
    commit = None if payload is None else _as_mapping(payload.get("commit"))
    sha = None if commit is None else commit.get("sha")
    if not isinstance(sha, str) or not sha:
        raise RuntimeError("validation branch head observation is incomplete")
    return sha


def _branch_head_sha_if_present(repository: str, token: str, branch: str) -> str | None:
    try:
        return _branch_head_sha(repository, token, branch)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _matching_ref_create_sha(
    raw_worker_result: str,
    source: WorkerRequest,
    branch: str,
) -> str | None:
    batch = parse_effect_batch(raw_worker_result, source)
    target_ref = f"refs/heads/{branch}"
    matching_creates: list[tuple[int, str]] = []
    first_content_index: int | None = None

    for index, effect in enumerate(batch.effects):
        if effect.kind != GITHUB_MUTATION_KIND:
            continue
        try:
            decoded = json.loads(effect.payload_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("branch mutation payload became malformed") from exc
        payload = _as_mapping(decoded)
        if payload is None:
            continue

        operation = payload.get("operation")
        if (
            first_content_index is None
            and operation in _CONTENT_OPERATIONS
            and payload.get("branch") == branch
        ):
            first_content_index = index
        if operation == "ref-create" and payload.get("ref") == target_ref:
            sha = payload.get("sha")
            if not isinstance(sha, str) or not sha:
                raise RuntimeError("OpenSpec validation branch creation identity is incomplete")
            matching_creates.append((index, sha))
        if operation in {"ref-update", "ref-delete"} and payload.get("ref") == target_ref:
            raise RuntimeError("OpenSpec validation target branch ref history is ambiguous")

    if first_content_index is None:
        return None
    eligible = [sha for index, sha in matching_creates if index < first_content_index]
    if len(matching_creates) > 1 or len(eligible) > 1:
        raise RuntimeError("OpenSpec validation target branch creation is ambiguous")
    return eligible[0] if len(eligible) == 1 else None


def _content_mutations_for_validation(
    raw_worker_result: str,
    source: WorkerRequest,
) -> tuple[ExactValidationMutation, ...]:
    batch = parse_effect_batch(raw_worker_result, source)
    mutations: list[ExactValidationMutation] = []
    contains_openspec = False

    for effect in batch.effects:
        if effect.kind != GITHUB_MUTATION_KIND:
            continue
        try:
            decoded = json.loads(effect.payload_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("content mutation payload became malformed") from exc
        payload = _as_mapping(decoded)
        if payload is None or payload.get("operation") not in _CONTENT_OPERATIONS:
            continue

        operation = cast(str, payload["operation"])
        path = payload.get("path")
        branch = payload.get("branch")
        message = payload.get("message")
        if not all(isinstance(value, str) and value for value in (path, branch, message)):
            raise RuntimeError("content mutation identity is incomplete")

        content = payload.get("content")
        blob_sha: str | None = None
        if operation == "contents-upsert":
            if not isinstance(content, str):
                raise RuntimeError("content upsert payload is missing content")
            blob_sha = _git_blob_sha(content)

        normalized_path = cast(str, path)
        contains_openspec = contains_openspec or normalized_path.startswith("openspec/")
        mutations.append(
            ExactValidationMutation(
                operation=operation,
                path=normalized_path,
                branch=cast(str, branch),
                message=cast(str, message),
                blob_sha=blob_sha,
            )
        )

    if not contains_openspec:
        return ()
    branches = {mutation.branch for mutation in mutations}
    if len(branches) != 1:
        raise RuntimeError("OpenSpec validation target is ambiguous across content branches")
    return tuple(mutations)


def prepare_exact_openspec_validation(
    raw_worker_result: str,
    *,
    source: WorkerRequest,
    repository: str,
    token: str,
    workflow_text: str | None = None,
) -> ExactValidationProbe | None:
    """Capture the exact pre-apply identity for a topology-gated OpenSpec write."""

    mutations = _content_mutations_for_validation(raw_worker_result, source)
    if not mutations:
        return None
    if workflow_text is None:
        try:
            workflow_text = Path("agents/workflow.md").read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError("OpenSpec validation gate topology is unavailable") from exc
    review_effect = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps(
            {
                "issue_number": source.issue_number,
                "role": "reviewer",
                "action": "review-openspec",
            },
            sort_keys=True,
        ),
    )
    if not topology_allows_successor(workflow_text, source, review_effect):
        return None
    branch = mutations[0].branch
    before_sha = _branch_head_sha_if_present(repository, token, branch)
    if before_sha is None:
        before_sha = _matching_ref_create_sha(raw_worker_result, source, branch)
        if before_sha is None:
            raise RuntimeError(
                "OpenSpec validation target branch is absent without a matching ref-create"
            )
    return ExactValidationProbe(
        branch=branch,
        before_sha=before_sha,
        mutations=mutations,
    )


def _commit_matches_mutation(
    detail: Mapping[str, object],
    mutation: ExactValidationMutation,
    *,
    expected_parent: str,
    expected_sha: str,
) -> bool:
    if detail.get("sha") != expected_sha:
        return False
    parents = detail.get("parents")
    if not isinstance(parents, list) or len(parents) != 1:
        return False
    parent = _as_mapping(parents[0])
    if parent is None or parent.get("sha") != expected_parent:
        return False
    commit = _as_mapping(detail.get("commit"))
    if commit is None or commit.get("message") != mutation.message:
        return False
    files = detail.get("files")
    if not isinstance(files, list) or len(files) != 1:
        return False
    file_payload = _as_mapping(files[0])
    if file_payload is None or file_payload.get("filename") != mutation.path:
        return False
    status = file_payload.get("status")
    if mutation.operation == "contents-delete":
        return status == "removed"
    return status in {"added", "modified"} and file_payload.get("sha") == mutation.blob_sha


def prove_exact_openspec_validation(
    probe: ExactValidationProbe,
    *,
    repository: str,
    token: str,
    correlation: str,
) -> ExactValidationTarget:
    """Prove the final branch head is exactly the linear commit sequence produced by application."""

    after_sha = _branch_head_sha(repository, token, probe.branch)
    if after_sha == probe.before_sha:
        raise RuntimeError("OpenSpec application did not advance the target branch")

    compared = _github_json(repository, token, f"compare/{probe.before_sha}...{after_sha}")
    comparison = _as_mapping(compared)
    raw_commits = None if comparison is None else comparison.get("commits")
    if (
        comparison is None
        or comparison.get("status") != "ahead"
        or comparison.get("total_commits") != len(probe.mutations)
        or not isinstance(raw_commits, list)
        or len(raw_commits) != len(probe.mutations)
    ):
        raise RuntimeError("OpenSpec application produced an unexpected commit sequence")

    parent_sha = probe.before_sha
    for raw_commit, mutation in zip(raw_commits, probe.mutations, strict=True):
        commit = _as_mapping(raw_commit)
        commit_sha = None if commit is None else commit.get("sha")
        if not isinstance(commit_sha, str):
            raise RuntimeError("OpenSpec application commit identity is incomplete")
        detail = _as_mapping(_github_json(repository, token, f"commits/{commit_sha}"))
        if detail is None or not _commit_matches_mutation(
            detail,
            mutation,
            expected_parent=parent_sha,
            expected_sha=commit_sha,
        ):
            raise RuntimeError(
                "OpenSpec application commit proof does not match the requested effect"
            )
        parent_sha = commit_sha

    if parent_sha != after_sha:
        raise RuntimeError("OpenSpec application final revision proof is inconsistent")
    return ExactValidationTarget(
        repository=repository,
        revision=after_sha,
        correlation=correlation,
    )


def _write_validation_outputs(target: ExactValidationTarget | None) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    lines = [f"validation_required={'true' if target is not None else 'false'}"]
    if target is not None:
        lines.extend(
            (
                f"validation_target_repository={target.repository}",
                f"validation_target_revision={target.revision}",
                f"validation_correlation={target.correlation}",
            )
        )
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def _load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    """Apply one run-scoped worker result through the write-authorized boundary."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    event = _load_json(args.event_path)
    if not isinstance(event, Mapping):
        raise RuntimeError("GitHub event payload must be an object")
    event_mapping = cast(Mapping[str, object], event)
    event_comment = _as_mapping(event_mapping.get("comment"))
    if event_comment is None:
        return 0
    body = event_comment.get("body")
    if not isinstance(body, str):
        return 0
    request = parse_application_request(body)
    if request is None:
        return 0
    issue = _as_mapping(event_mapping.get("issue"))
    if issue is None or "pull_request" in issue or not is_runtime_checkin_issue(issue):
        return 0

    event_comment_id = _positive_int(event_comment.get("id"))
    issue_number = _positive_int(issue.get("number"))
    if event_comment_id is None or issue_number is None:
        raise RuntimeError("EFFECT_REQUEST event identity is incomplete")
    repository_owner = repository.split("/", 1)[0]
    if not _trusted_connector_comment(event_comment, repository_owner):
        raise RuntimeError("EFFECT_REQUEST must originate from the configured ChatGPT connector")

    observed_comment = _as_mapping(
        _github_json(repository, token, f"issues/comments/{event_comment_id}")
    )
    if observed_comment is None:
        raise RuntimeError("EFFECT_REQUEST current comment observation is incomplete")
    if (
        observed_comment.get("id") != event_comment_id
        or observed_comment.get("body") != body
        or not _trusted_connector_comment(observed_comment, repository_owner)
    ):
        raise RuntimeError("EFFECT_REQUEST current comment observation is incomplete")
    observed_issue = _as_mapping(_github_json(repository, token, f"issues/{issue_number}"))
    if (
        observed_issue is None
        or observed_issue.get("number") != issue_number
        or not is_runtime_checkin_issue(observed_issue)
    ):
        raise RuntimeError("EFFECT_REQUEST current shard observation is invalid")

    dispatch_result = fetch_dispatch_result(
        repository,
        token,
        request_comment_id=request.dispatch_request_comment_id,
        run_id=request.dispatch_run_id,
        current_revision=args.revision,
    )
    plan = plan_application(
        event=event_mapping,
        request=request,
        dispatch_result=dispatch_result,
        repository=repository,
        current_revision=args.revision,
    )
    if not plan.should_apply:
        return 0
    if (
        plan.source is None
        or plan.raw_worker_result is None
        or plan.effect_request_comment_id is None
    ):
        raise RuntimeError("application plan is missing validated source/result identity")

    workflow_text = Path("agents/workflow.md").read_text(encoding="utf-8")
    probe = prepare_exact_openspec_validation(
        plan.raw_worker_result,
        source=plan.source,
        repository=repository,
        token=token,
        workflow_text=workflow_text,
    )
    _, result = run_guarded_effect_application(
        plan.raw_worker_result,
        source=plan.source,
        repository=repository,
        token=token,
        workflow_text=workflow_text,
        current_revision=args.revision,
    )

    target: ExactValidationTarget | None = None
    if result.applied and probe is not None:
        target = prove_exact_openspec_validation(
            probe,
            repository=repository,
            token=token,
            correlation=f"effect-request-{plan.effect_request_comment_id}",
        )
    _write_validation_outputs(target)
    print(
        json.dumps(
            {
                "applied": result.applied,
                "reason": result.reason,
                "validation_revision": None if target is None else target.revision,
            },
            sort_keys=True,
        )
    )
    return 0 if result.applied else 1


if __name__ == "__main__":
    raise SystemExit(main())
