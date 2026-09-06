"""Application-time merge acceptance for the machine-gated Scheduled Agent runtime."""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.human_authority import HUMAN_ACTOR
from investment_strategy.native_closing_merge_application import (
    acquire_native_closing_merge_result,
)
from investment_strategy.native_closing_preflight import (
    MergeStrategy,
    NativeClosingDisposition,
)
from investment_strategy.scheduled_agent_effect_contract import GITHUB_MUTATION_KIND
from investment_strategy.scheduled_agent_effects import (
    ApplyResult,
    EffectBatch,
    GitHubEffectAdapter,
    StagedEffect,
    apply_effect_batch,
    parse_effect_batch,
)
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    acquire_current_github_preflight,
)

_MERGE_REVIEW_ACTION = {
    "merge-implementation-pr": "review-implementation",
    "merge-archive-pr": "review-archive",
}
_ACCEPTED_CHECK_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})
_SHA = re.compile(r"^[0-9a-f]{40}$")


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


PreApplyGuard = Callable[[StagedEffect], bool]


class _EffectPreconditionStale(RuntimeError):
    """Signal that a mutation-adjacent effect precondition changed."""


@dataclass(frozen=True)
class MergeAcceptanceSnapshot:
    """Fresh structural evidence required immediately before a merge effect."""

    pr_open: bool
    current_head_sha: str | None
    expected_head_sha: str
    reviewer_pass_head_sha: str | None
    required_checks_pass: bool
    non_closing_linkage: bool
    native_closing_preflight_allowed: bool
    contradictory_evidence: bool
    human_input_fresh: bool
    complete: bool
    historical_merged_carrier_allowed: bool = False


def merge_acceptance_allows(snapshot: MergeAcceptanceSnapshot) -> bool:
    """Return whether all fresh merge-acceptance predicates hold together."""

    return (
        snapshot.complete
        and (snapshot.pr_open or snapshot.historical_merged_carrier_allowed)
        and snapshot.current_head_sha == snapshot.expected_head_sha
        and snapshot.reviewer_pass_head_sha == snapshot.expected_head_sha
        and snapshot.required_checks_pass
        and snapshot.non_closing_linkage
        and snapshot.native_closing_preflight_allowed
        and not snapshot.contradictory_evidence
        and snapshot.human_input_fresh
    )


def _github_json(repository: str, token: str, api_path: str) -> object:
    normalized_path = api_path.lstrip("/")
    api_url = f"https://api.github.com/repos/{repository}"
    if normalized_path:
        api_url = f"{api_url}/{normalized_path}"
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        return json.loads(response.read().decode("utf-8"))


def _paged_github_list(
    repository: str,
    token: str,
    api_path: str,
) -> tuple[Mapping[str, object], ...]:
    items: list[Mapping[str, object]] = []
    page = 1
    while True:
        separator = "&" if "?" in api_path else "?"
        decoded = _github_json(
            repository,
            token,
            f"{api_path}{separator}{urlencode({'per_page': 100, 'page': page})}",
        )
        if not isinstance(decoded, list):
            raise RuntimeError("GitHub paginated evidence endpoint returned a non-list response")
        current: list[Mapping[str, object]] = []
        for item in decoded:
            if not isinstance(item, Mapping):
                raise RuntimeError("GitHub paginated evidence endpoint returned a malformed item")
            current.append(cast(Mapping[str, object], item))
        items.extend(current)
        if len(current) < 100:
            return tuple(items)
        page += 1


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _pull_request_head_sha(payload: Mapping[str, object]) -> str | None:
    head = payload.get("head")
    if not isinstance(head, Mapping):
        return None
    sha = head.get("sha")
    return sha if isinstance(sha, str) else None


def _merge_payload(effect: StagedEffect) -> Mapping[str, object] | None:
    if effect.kind != GITHUB_MUTATION_KIND:
        return None
    try:
        payload = json.loads(effect.payload_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping) or payload.get("operation") != "pull-request-merge":
        return None
    return cast(Mapping[str, object], payload)


def _review_record(body: object) -> tuple[str, str, str, str | None] | None:
    if not isinstance(body, str):
        return None
    action_match = re.search(
        r"Action:\s*\x60?Reviewer / (review-(?:implementation|archive))\x60?",
        body,
    )
    result_match = re.search(
        r"Result:\s*\x60?(PASS|IMPLEMENTATION_FINDINGS|FINDINGS)\x60?",
        body,
    )
    revision_match = re.search(r"Revision:\s*\x60?([0-9a-f]{40})\x60?", body)
    default_revision_match = re.search(
        r"Default-Branch-Revision:\s*\x60?([0-9a-f]{40})\x60?",
        body,
    )
    if action_match is None or result_match is None or revision_match is None:
        return None
    default_revision = None if default_revision_match is None else default_revision_match.group(1)
    return (
        action_match.group(1),
        result_match.group(1),
        revision_match.group(1),
        default_revision,
    )


def _latest_matching_pass(
    comments: tuple[Mapping[str, object], ...],
    expected_head_sha: str,
    *,
    required_review_action: str,
) -> tuple[str | None, str | None, datetime | None, bool, bool, str | None]:
    records: list[tuple[datetime, int, str, str, str, str | None]] = []
    complete = True
    for comment in comments:
        record = _review_record(comment.get("body"))
        if record is None:
            continue
        created_at = _timestamp(comment.get("created_at"))
        comment_id = comment.get("id")
        if created_at is None or not isinstance(comment_id, int):
            complete = False
            continue
        action, result, revision, default_revision = record
        records.append((created_at, comment_id, action, result, revision, default_revision))

    matching = [record for record in records if record[4] == expected_head_sha]
    passes = [
        record for record in matching if record[3] == "PASS" and record[2] == required_review_action
    ]
    if not passes:
        return None, None, None, False, complete, None

    latest_pass = max(passes, key=lambda item: (item[0], item[1]))
    later_contradiction = any(
        (record[0], record[1]) > (latest_pass[0], latest_pass[1])
        and record[2] == latest_pass[2]
        and record[3] != "PASS"
        for record in records
    )
    return (
        latest_pass[4],
        latest_pass[2],
        latest_pass[0],
        later_contradiction,
        complete,
        latest_pass[5],
    )


def _non_closing_linkage(body: object, issue_number: int) -> bool:
    if not isinstance(body, str):
        return False
    return re.search(rf"(?im)^\s*Refs\s+#{issue_number}\b", body) is not None


def _required_checks_pass(repository: str, token: str, head_sha: str) -> tuple[bool, bool]:
    decoded = _github_json(repository, token, f"commits/{head_sha}/check-runs?per_page=100")
    if not isinstance(decoded, Mapping):
        return False, False
    total_count = decoded.get("total_count")
    raw_runs = decoded.get("check_runs")
    if (
        not isinstance(total_count, int)
        or not isinstance(raw_runs, list)
        or total_count != len(raw_runs)
    ):
        return False, False
    if total_count == 0:
        return False, False
    for raw in raw_runs:
        if not isinstance(raw, Mapping):
            return False, False
        status = raw.get("status")
        conclusion = raw.get("conclusion")
        if status != "completed" or conclusion not in _ACCEPTED_CHECK_CONCLUSIONS:
            return False, True
    return True, True


def _human_input_fresh(
    comments: tuple[Mapping[str, object], ...],
    relied_upon_at: datetime | None,
) -> tuple[bool, bool]:
    if relied_upon_at is None:
        return False, False
    for comment in comments:
        created_at = _timestamp(comment.get("created_at"))
        if created_at is None:
            return False, False
        if created_at <= relied_upon_at:
            continue
        user = comment.get("user")
        if not isinstance(user, Mapping) or not isinstance(user.get("login"), str):
            return False, False
        if user.get("login") != HUMAN_ACTOR:
            continue
        if "performed_via_github_app" not in comment:
            return False, False
        if comment.get("performed_via_github_app") is None:
            # The mutation adapter does not make semantic materiality judgments.
            # A newer direct-Human comment therefore requires a later accepted
            # review before merge rather than being inferred non-blocking here.
            return False, True
    return True, True


def _is_historical_merged_carrier(payload: Mapping[str, object]) -> bool:
    return (
        payload.get("state") == "closed"
        and payload.get("merged") is True
        and _valid_sha(payload.get("merge_commit_sha"))
        and _pull_request_head_sha(payload) is not None
        and _timestamp(payload.get("merged_at")) is not None
    )


def _repository_default_branch_sha(
    repository: str,
    token: str,
) -> tuple[str | None, str | None]:
    try:
        payload = _github_json(repository, token, "")
        if not isinstance(payload, Mapping):
            return None, None
        default_branch = payload.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch.strip():
            return None, None
        ref = _github_json(
            repository,
            token,
            f"git/ref/heads/{quote(default_branch, safe='/')}",
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return None, None
    if not isinstance(ref, Mapping):
        return default_branch, None
    obj = ref.get("object")
    if not isinstance(obj, Mapping):
        return default_branch, None
    sha = obj.get("sha")
    return default_branch, sha if _valid_sha(sha) else None


def _default_branch_contains_commit(
    repository: str,
    token: str,
    *,
    merge_commit_sha: str,
    default_branch: str,
) -> bool:
    try:
        comparison = _github_json(
            repository,
            token,
            f"compare/{merge_commit_sha}...{quote(default_branch, safe='/')}",
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return False
    if not isinstance(comparison, Mapping):
        return False
    return comparison.get("status") in {"ahead", "identical"} and comparison.get("behind_by") == 0


def _merge_commit_has_parent(
    repository: str,
    token: str,
    *,
    merge_commit_sha: str,
    parent_sha: str,
) -> bool:
    """Bind a post-merge reconciliation to the pre-merge authorized base."""

    try:
        commit = _github_json(repository, token, f"commits/{merge_commit_sha}")
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return False
    if not isinstance(commit, Mapping):
        return False
    parents = commit.get("parents")
    if not isinstance(parents, list):
        return False
    return any(
        isinstance(parent, Mapping) and parent.get("sha") == parent_sha for parent in parents
    )


def _historical_merged_carrier_allowed(
    payload: Mapping[str, object],
    *,
    repository: str,
    token: str,
    expected_head_sha: str,
    current_revision: str | None,
    expected_branch: str | None,
    reviewer_pass_default_branch_revision: str | None = None,
) -> bool:
    if (
        not _is_historical_merged_carrier(payload)
        or _pull_request_head_sha(payload) != expected_head_sha
        or not _valid_sha(current_revision)
    ):
        return False
    head = payload.get("head")
    base = payload.get("base")
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        return False
    head_repo = head.get("repo")
    base_repo = base.get("repo")
    if (
        not isinstance(head_repo, Mapping)
        or not isinstance(base_repo, Mapping)
        or head_repo.get("full_name") != repository
        or base_repo.get("full_name") != repository
        or (expected_branch is not None and head.get("ref") != expected_branch)
    ):
        return False
    default_branch, current_default_sha = _repository_default_branch_sha(repository, token)
    if (
        default_branch is None
        or current_default_sha != current_revision
        or base.get("ref") != default_branch
    ):
        return False
    merge_commit_sha = payload.get("merge_commit_sha")
    if not _valid_sha(merge_commit_sha) or not _default_branch_contains_commit(
        repository,
        token,
        merge_commit_sha=cast(str, merge_commit_sha),
        default_branch=default_branch,
    ):
        return False
    if reviewer_pass_default_branch_revision is None:
        return True
    if (
        reviewer_pass_default_branch_revision == current_revision
        and _valid_sha(reviewer_pass_default_branch_revision)
    ):
        return True
    return _valid_sha(reviewer_pass_default_branch_revision) and _merge_commit_has_parent(
        repository,
        token,
        merge_commit_sha=cast(str, merge_commit_sha),
        parent_sha=reviewer_pass_default_branch_revision,
    )


def _lifecycle_context(review_action: str | None) -> str:
    if review_action == "review-implementation":
        return "implementation"
    if review_action == "review-archive":
        return "archive"
    return ""


def acquire_merge_acceptance_snapshot(
    *,
    repository: str,
    token: str,
    issue_number: int,
    pr_number: int,
    expected_head_sha: str,
    merge_strategy: MergeStrategy,
    required_review_action: str,
    current_revision: str | None = None,
    expected_branch: str | None = None,
) -> MergeAcceptanceSnapshot:
    """Acquire current GitHub evidence for one staged merge immediately before application."""

    try:
        pr = _github_json(repository, token, f"pulls/{pr_number}")
        comments = _paged_github_list(repository, token, f"issues/{issue_number}/comments")
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return MergeAcceptanceSnapshot(
            False, None, expected_head_sha, None, False, False, False, True, False, False
        )
    if not isinstance(pr, Mapping):
        return MergeAcceptanceSnapshot(
            False, None, expected_head_sha, None, False, False, False, True, False, False
        )

    (
        reviewer_pass_head,
        review_action,
        pass_time,
        contradiction,
        review_complete,
        reviewer_pass_default_branch_revision,
    ) = _latest_matching_pass(
        comments,
        expected_head_sha,
        required_review_action=required_review_action,
    )
    try:
        checks_pass, checks_complete = _required_checks_pass(repository, token, expected_head_sha)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        checks_pass, checks_complete = False, False
    human_fresh, human_complete = _human_input_fresh(comments, pass_time)
    native_result = acquire_native_closing_merge_result(
        repository=repository,
        token=token,
        coordination_issue=issue_number,
        pr_number=pr_number,
        expected_head_sha=expected_head_sha,
        lifecycle_context=_lifecycle_context(review_action),
        merge_strategy=merge_strategy,
    )
    native_complete = native_result.disposition is not NativeClosingDisposition.FAIL_CLOSED
    historical_merged_carrier_allowed = False
    if pr.get("state") != "open":
        historical_merged_carrier_allowed = _historical_merged_carrier_allowed(
            pr,
            repository=repository,
            token=token,
            expected_head_sha=expected_head_sha,
            current_revision=current_revision,
            expected_branch=expected_branch,
            reviewer_pass_default_branch_revision=reviewer_pass_default_branch_revision,
        )
    complete = review_complete and checks_complete and human_complete and native_complete

    return MergeAcceptanceSnapshot(
        pr_open=pr.get("state") == "open",
        current_head_sha=_pull_request_head_sha(pr),
        expected_head_sha=expected_head_sha,
        reviewer_pass_head_sha=reviewer_pass_head,
        required_checks_pass=checks_pass,
        non_closing_linkage=_non_closing_linkage(pr.get("body"), issue_number),
        native_closing_preflight_allowed=native_result.allowed,
        contradictory_evidence=contradiction,
        human_input_fresh=human_fresh,
        complete=complete,
        historical_merged_carrier_allowed=historical_merged_carrier_allowed,
    )


def _merge_effect_allows(
    effect: StagedEffect,
    *,
    source: WorkerRequest,
    repository: str,
    token: str,
    current_revision: str | None = None,
    expected_change: str | None = None,
) -> bool:
    """Freshly re-evaluate one merge effect at the mutation-adjacent boundary."""

    payload = _merge_payload(effect)
    if payload is None:
        return True
    number = payload.get("number")
    expected_head_sha = payload.get("expected_head_sha")
    merge_method = payload.get("merge_method", "merge")
    required_review_action = _MERGE_REVIEW_ACTION.get(source.action)
    if required_review_action is None:
        return False
    if (
        not isinstance(number, int)
        or not isinstance(expected_head_sha, str)
        or not isinstance(merge_method, str)
    ):
        return False
    try:
        merge_strategy = MergeStrategy(merge_method)
    except ValueError:
        return False
    if not isinstance(expected_change, str) or not expected_change.strip():
        return False
    expected_branch = (
        f"agent/archive-{expected_change}"
        if source.action == "merge-archive-pr"
        else f"agent/{expected_change}"
    )
    snapshot = acquire_merge_acceptance_snapshot(
        repository=repository,
        token=token,
        issue_number=source.issue_number,
        pr_number=number,
        expected_head_sha=expected_head_sha,
        merge_strategy=merge_strategy,
        required_review_action=required_review_action,
        current_revision=current_revision,
        expected_branch=expected_branch,
    )
    return merge_acceptance_allows(snapshot)


def run_effect_application(
    raw_worker_result: str,
    *,
    source: WorkerRequest,
    repository: str,
    token: str,
    pre_apply_guard: PreApplyGuard | None = None,
    current_revision: str | None = None,
    apply_derived: bool = True,
    materialization_promote_change: bool = False,
    validated_materialization_revision: str | None = None,
) -> tuple[EffectBatch, ApplyResult]:
    """Apply through shared effect guards plus an optional mutation-adjacent guard."""

    batch = parse_effect_batch(raw_worker_result, source)
    if batch.typed_result is None:
        return batch, ApplyResult(False, "typed application rejected:result-missing")
    adapter = GitHubEffectAdapter(
        repository,
        token,
        source,
        authorized_change=batch.typed_result.change,
        current_revision=current_revision,
        materialization_promote_change=materialization_promote_change,
        validated_materialization_revision=validated_materialization_revision,
    )

    def apply_with_fresh_guard(effect: StagedEffect) -> None:
        if pre_apply_guard is not None and not pre_apply_guard(effect):
            raise _EffectPreconditionStale
        adapter.apply(effect)

    carrier_plan_provider = getattr(adapter, "carrier_plan_if_required", None)
    if not callable(carrier_plan_provider):
        carrier_plan_provider = None

    try:
        result = apply_effect_batch(
            batch,
            fresh_preflight=lambda: acquire_current_github_preflight(repository, token),
            effect_guard=adapter.guard,
            apply_effect=apply_with_fresh_guard,
            observe_postcondition=adapter.observe_postcondition,
            current_revision=current_revision,
            apply_derived=apply_derived,
            carrier_plan_for_effect=carrier_plan_provider,
        )
    except _EffectPreconditionStale:
        result = ApplyResult(False, "effect precondition became stale")
    return batch, result


def run_guarded_effect_application(
    raw_worker_result: str,
    *,
    source: WorkerRequest,
    repository: str,
    token: str,
    current_revision: str | None = None,
    apply_derived: bool = True,
    materialization_promote_change: bool = False,
    validated_materialization_revision: str | None = None,
) -> tuple[EffectBatch, ApplyResult]:
    """Reject stale merge acceptance before and immediately adjacent to merge application."""

    batch = parse_effect_batch(raw_worker_result, source)
    expected_change = None if batch.typed_result is None else batch.typed_result.change
    for effect in batch.effects:
        if _merge_payload(effect) is None:
            continue
        if not _merge_effect_allows(
            effect,
            source=source,
            repository=repository,
            token=token,
            current_revision=current_revision,
            expected_change=expected_change,
        ):
            return batch, ApplyResult(False, "fresh merge acceptance rejected")

    return run_effect_application(
        raw_worker_result,
        source=source,
        repository=repository,
        token=token,
        current_revision=current_revision,
        apply_derived=apply_derived,
        materialization_promote_change=materialization_promote_change,
        validated_materialization_revision=validated_materialization_revision,
        pre_apply_guard=lambda effect: _merge_effect_allows(
            effect,
            source=source,
            repository=repository,
            token=token,
            current_revision=current_revision,
            expected_change=expected_change,
        ),
    )


def _source_from_environment() -> WorkerRequest:
    issue = os.environ.get("AUTHORIZED_ISSUE")
    role = os.environ.get("AUTHORIZED_ROLE")
    action = os.environ.get("AUTHORIZED_ACTION")
    if not issue or not role or not action:
        raise RuntimeError("machine-authorized Issue/role/action environment is required")
    try:
        issue_number = int(issue)
    except ValueError as exc:
        raise RuntimeError("AUTHORIZED_ISSUE must be an integer") from exc
    return WorkerRequest(
        issue_number=issue_number,
        role=role,
        action=action,
    )


def _write_github_outputs(result: ApplyResult) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write(f"applied={'true' if result.applied else 'false'}\n")


def main() -> int:
    """Apply one result through merge acceptance plus effect reauthorization."""

    if len(sys.argv) != 2:
        raise RuntimeError("worker result path argument is required")
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    source = _source_from_environment()
    raw_worker_result = Path(sys.argv[1]).read_text(encoding="utf-8")
    batch, result = run_guarded_effect_application(
        raw_worker_result,
        source=source,
        repository=repository,
        token=token,
    )
    _write_github_outputs(result)
    print(
        json.dumps(
            {
                "applied": result.applied,
                "reason": result.reason,
                "effects": len(batch.effects),
            },
            sort_keys=True,
        )
    )
    return 0 if result.applied else 1


if __name__ == "__main__":
    raise SystemExit(main())
