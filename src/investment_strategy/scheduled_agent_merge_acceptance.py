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
from urllib.parse import urlencode
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
    topology_allows_successor,
)
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    acquire_current_github_preflight,
)

_REVIEW_ACTIONS = ("review-implementation", "review-archive")
_ACCEPTED_CHECK_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})
_DEBT_DISPOSITIONS = frozenset({"terminal-cleanup", "unfinished-recovery"})

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


def merge_acceptance_allows(snapshot: MergeAcceptanceSnapshot) -> bool:
    """Return whether all fresh merge-acceptance predicates hold together."""

    return (
        snapshot.complete
        and snapshot.pr_open
        and snapshot.current_head_sha == snapshot.expected_head_sha
        and snapshot.reviewer_pass_head_sha == snapshot.expected_head_sha
        and snapshot.required_checks_pass
        and snapshot.non_closing_linkage
        and snapshot.native_closing_preflight_allowed
        and not snapshot.contradictory_evidence
        and snapshot.human_input_fresh
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


def _review_record(body: object) -> tuple[str, str, str] | None:
    if not isinstance(body, str):
        return None
    action_match = re.search(r"Action:\s*`?Reviewer / (review-(?:implementation|archive))`?", body)
    result_match = re.search(r"Result:\s*`?(PASS|IMPLEMENTATION_FINDINGS|FINDINGS)`?", body)
    revision_match = re.search(r"Revision:\s*`?([0-9a-f]{40})`?", body)
    if action_match is None or result_match is None or revision_match is None:
        return None
    return action_match.group(1), result_match.group(1), revision_match.group(1)


def _latest_matching_pass(
    comments: tuple[Mapping[str, object], ...],
    expected_head_sha: str,
) -> tuple[str | None, str | None, datetime | None, bool, bool]:
    records: list[tuple[datetime, int, str, str, str]] = []
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
        action, result, revision = record
        records.append((created_at, comment_id, action, result, revision))

    matching = [record for record in records if record[4] == expected_head_sha]
    passes = [record for record in matching if record[3] == "PASS" and record[2] in _REVIEW_ACTIONS]
    if not passes:
        return None, None, None, False, complete

    latest_pass = max(passes, key=lambda item: (item[0], item[1]))
    later_contradiction = any(
        (record[0], record[1]) > (latest_pass[0], latest_pass[1])
        and record[2] == latest_pass[2]
        and record[3] != "PASS"
        for record in records
    )
    return latest_pass[4], latest_pass[2], latest_pass[0], later_contradiction, complete


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

    reviewer_pass_head, review_action, pass_time, contradiction, review_complete = (
        _latest_matching_pass(comments, expected_head_sha)
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
    )


def _merge_effect_allows(
    effect: StagedEffect,
    *,
    source: WorkerRequest,
    repository: str,
    token: str,
) -> bool:
    """Freshly re-evaluate one merge effect at the mutation-adjacent boundary."""

    payload = _merge_payload(effect)
    if payload is None:
        return True
    number = payload.get("number")
    expected_head_sha = payload.get("expected_head_sha")
    merge_method = payload.get("merge_method", "merge")
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
    snapshot = acquire_merge_acceptance_snapshot(
        repository=repository,
        token=token,
        issue_number=source.issue_number,
        pr_number=number,
        expected_head_sha=expected_head_sha,
        merge_strategy=merge_strategy,
    )
    return merge_acceptance_allows(snapshot)


def run_effect_application(
    raw_worker_result: str,
    *,
    source: WorkerRequest,
    repository: str,
    token: str,
    workflow_text: str,
    pre_apply_guard: PreApplyGuard | None = None,
) -> tuple[EffectBatch, ApplyResult]:
    """Apply through shared effect guards plus an optional mutation-adjacent guard."""

    batch = parse_effect_batch(raw_worker_result, source)
    adapter = GitHubEffectAdapter(repository, token, source)

    def apply_with_fresh_guard(effect: StagedEffect) -> None:
        if pre_apply_guard is not None and not pre_apply_guard(effect):
            raise _EffectPreconditionStale
        adapter.apply(effect)

    try:
        result = apply_effect_batch(
            batch,
            fresh_preflight=lambda: acquire_current_github_preflight(repository, token),
            effect_guard=adapter.guard,
            topology_validator=lambda request, effect: topology_allows_successor(
                workflow_text,
                request,
                effect,
            ),
            apply_effect=apply_with_fresh_guard,
            observe_postcondition=adapter.observe_postcondition,
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
    workflow_text: str,
) -> tuple[EffectBatch, ApplyResult]:
    """Reject stale merge acceptance before and immediately adjacent to merge application."""

    batch = parse_effect_batch(raw_worker_result, source)
    for effect in batch.effects:
        if _merge_payload(effect) is None:
            continue
        if not _merge_effect_allows(
            effect,
            source=source,
            repository=repository,
            token=token,
        ):
            return batch, ApplyResult(False, "fresh merge acceptance rejected")

    return run_effect_application(
        raw_worker_result,
        source=source,
        repository=repository,
        token=token,
        workflow_text=workflow_text,
        pre_apply_guard=lambda effect: _merge_effect_allows(
            effect,
            source=source,
            repository=repository,
            token=token,
        ),
    )


def _source_from_environment() -> WorkerRequest:
    issue = os.environ.get("AUTHORIZED_ISSUE")
    role = os.environ.get("AUTHORIZED_ROLE")
    action = os.environ.get("AUTHORIZED_ACTION")
    raw_disposition = os.environ.get("AUTHORIZED_DEBT_DISPOSITION", "")
    disposition = raw_disposition or None
    if not issue or not role or not action:
        raise RuntimeError("machine-authorized Issue/role/action environment is required")
    if disposition is not None and disposition not in _DEBT_DISPOSITIONS:
        raise RuntimeError("AUTHORIZED_DEBT_DISPOSITION is invalid")
    try:
        issue_number = int(issue)
    except ValueError as exc:
        raise RuntimeError("AUTHORIZED_ISSUE must be an integer") from exc
    return WorkerRequest(
        issue_number=issue_number,
        role=role,
        action=action,
        debt_disposition=disposition,
    )


def _write_github_outputs(batch: EffectBatch, result: ApplyResult) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    lines = [
        f"applied={'true' if result.applied else 'false'}",
        f"continuation_required={'true' if result.continuation is not None else 'false'}",
    ]
    if result.continuation is not None:
        lines.extend(
            (
                f"continuation_issue={result.continuation.issue_number}",
                f"continuation_role={result.continuation.role}",
                f"continuation_action={result.continuation.action}",
            )
        )
        if result.continuation.debt_disposition is not None:
            lines.append(f"continuation_debt_disposition={result.continuation.debt_disposition}")
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def main() -> int:
    """Apply one same-run result through merge acceptance plus effect reauthorization."""

    if len(sys.argv) != 2:
        raise RuntimeError("worker result path argument is required")
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    source = _source_from_environment()
    raw_worker_result = Path(sys.argv[1]).read_text(encoding="utf-8")
    workflow_text = Path("agents/workflow.md").read_text(encoding="utf-8")
    batch, result = run_guarded_effect_application(
        raw_worker_result,
        source=source,
        repository=repository,
        token=token,
        workflow_text=workflow_text,
    )
    _write_github_outputs(batch, result)
    print(
        json.dumps(
            {
                "applied": result.applied,
                "reason": result.reason,
                "continuation": (
                    None
                    if result.continuation is None
                    else {
                        "issue_number": result.continuation.issue_number,
                        "role": result.continuation.role,
                        "action": result.continuation.action,
                        "debt_disposition": result.continuation.debt_disposition,
                    }
                ),
            },
            sort_keys=True,
        )
    )
    return 0 if result.applied else 1


if __name__ == "__main__":
    raise SystemExit(main())
