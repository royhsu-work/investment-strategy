"""Machine-gated Scheduled Agent runtime acquisition and worker authorization.

The runtime reconstructs current GitHub Issue state before mapped model work,
normalizes that state into the pure ``workflow_dispatch`` classifier, and
constructs a worker request only from an ``AUTHORIZE`` decision. Trigger
metadata is intentionally non-authoritative.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from urllib.request import Request, urlopen

from investment_strategy.workflow_dispatch import (
    Action,
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RecoveryEvidence,
    RepositoryIssueSnapshot,
    Role,
    Routing,
    TerminalEvidence,
    classify_dispatch,
)

_AGENT_LABELS: dict[str, Role] = {
    "agent:lead": "lead",
    "agent:reviewer": "reviewer",
    "agent:executor": "executor",
}
_ACTION_LABELS: dict[str, Action] = {
    "action:explore-change": "explore-change",
    "action:propose-change": "propose-change",
    "action:resolve-question": "resolve-question",
    "action:finalize-change": "finalize-change",
    "action:finalize-archive": "finalize-archive",
    "action:review-openspec": "review-openspec",
    "action:review-implementation": "review-implementation",
    "action:review-archive": "review-archive",
    "action:implement-change": "implement-change",
    "action:merge-pr": "merge-pr",
}
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_MESSAGE_FIELD = re.compile(r"(?m)^(Workflow|Change|Action|Result):\s*(.+?)\s*$")


@dataclass(frozen=True)
class GitHubIssueObservation:
    """Invocation-local normalized GitHub Issue observation."""

    issue_number: int
    change: str
    routing: Routing | None
    state: str
    created_order: int
    authoritative: bool
    premature_close_recovery: RecoveryEvidence = "not-candidate"
    terminal_evidence: TerminalEvidence = "not-terminal"


@dataclass(frozen=True)
class RuntimeTrigger:
    """Non-authoritative wake metadata used only to prove override resistance."""

    requested_issue: int | None = None
    requested_role: str | None = None
    requested_action: str | None = None


@dataclass(frozen=True)
class WorkerRequest:
    """Exact machine-authorized mapped worker identity for one invocation."""

    issue_number: int
    role: str
    action: str


def acquire_dispatch_preflight(
    *,
    observations: tuple[GitHubIssueObservation, ...],
    source_total_count: int | None,
    incomplete_results: bool,
    exhausted: bool,
) -> DispatchPreflight:
    """Normalize current GitHub observations into the production preflight."""

    issues = tuple(
        RepositoryIssueSnapshot(
            issue_number=observation.issue_number,
            change=observation.change,
            routing=observation.routing,
            state="open" if observation.state == "open" else "closed",
            created_order=observation.created_order,
            premature_close_recovery=observation.premature_close_recovery,
            terminal_evidence=observation.terminal_evidence,
            current_state_provenance=(
                ObservationProvenance.QUALIFIED
                if observation.authoritative
                else ObservationProvenance.INDETERMINATE
            ),
        )
        for observation in observations
    )
    return DispatchPreflight(
        issues=issues,
        enumeration=EnumerationEvidence(
            observed_count=len(observations),
            source_total_count=source_total_count,
            incomplete_results=incomplete_results,
            exhausted=exhausted,
            observation_provenance=(
                ObservationProvenance.QUALIFIED
                if all(observation.authoritative for observation in observations)
                else ObservationProvenance.INDETERMINATE
            ),
        ),
    )


def authorize_worker_request(
    preflight: DispatchPreflight,
    trigger: RuntimeTrigger,
) -> WorkerRequest | None:
    """Construct one exact worker request only from classifier authorization."""

    del trigger
    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id is None
        or decision.selected_routing is None
    ):
        return None

    role, action = decision.selected_routing
    return WorkerRequest(
        issue_number=decision.selected_issue_id,
        role=role,
        action=action,
    )


def _created_order(created_at: object, issue_number: int) -> tuple[int, bool]:
    if not isinstance(created_at, str):
        return issue_number, False
    try:
        normalized = created_at.replace("Z", "+00:00")
        return int(datetime.fromisoformat(normalized).timestamp() * 1_000_000), True
    except ValueError:
        return issue_number, False


def _label_names(payload: Mapping[str, object]) -> tuple[set[str], bool]:
    raw_labels = payload.get("labels")
    if not isinstance(raw_labels, list):
        return set(), False

    names: set[str] = set()
    for raw_label in raw_labels:
        if not isinstance(raw_label, Mapping):
            return set(), False
        name = raw_label.get("name")
        if not isinstance(name, str):
            return set(), False
        names.add(name)
    return names, True


def _routing_from_labels(labels: set[str]) -> tuple[Routing | None, bool]:
    agent_labels = [name for name in labels if name.startswith("agent:")]
    action_labels = [name for name in labels if name.startswith("action:")]

    if not agent_labels and not action_labels:
        return None, True
    if len(agent_labels) != 1 or len(action_labels) != 1:
        return None, False

    role = _AGENT_LABELS.get(agent_labels[0])
    action = _ACTION_LABELS.get(action_labels[0])
    if role is None or action is None:
        return None, False
    return (role, action), True


def normalize_github_issue(payload: Mapping[str, object]) -> GitHubIssueObservation | None:
    """Normalize one current GitHub Issues API object.

    Pull-request projections returned by the Issues endpoint are intentionally
    ignored. Any malformed authorization-bearing field marks the observation
    unqualified so the production classifier fails closed.
    """

    if "pull_request" in payload:
        return None

    number = payload.get("number")
    state = payload.get("state")
    body = payload.get("body")
    if not isinstance(number, int) or state not in {"open", "closed"}:
        return None

    labels, labels_valid = _label_names(payload)
    routing, routing_valid = _routing_from_labels(labels)
    created_order, created_valid = _created_order(payload.get("created_at"), number)

    body_text = body if isinstance(body, str) else ""
    change_matches = _CHANGE_LINE.findall(body_text)
    change_valid = len(change_matches) <= 1
    if len(change_matches) == 1:
        change = change_matches[0]
    elif routing is None:
        change = "unset"
    else:
        change = "unset"
        change_valid = False

    recovery: RecoveryEvidence = "not-candidate"
    terminal_evidence: TerminalEvidence = "not-terminal"
    if state == "closed" and change != "unset":
        terminal_evidence = "indeterminate"
        if routing is not None:
            recovery = "indeterminate"

    return GitHubIssueObservation(
        issue_number=number,
        change=change,
        routing=routing,
        state=cast(str, state),
        created_order=created_order,
        authoritative=labels_valid and routing_valid and created_valid and change_valid,
        premature_close_recovery=recovery,
        terminal_evidence=terminal_evidence,
    )


def _strip_code(value: str) -> str:
    normalized = value.strip()
    if len(normalized) >= 2 and normalized.startswith("`") and normalized.endswith("`"):
        return normalized[1:-1].strip()
    return normalized


def _message_fields(body: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for name, raw_value in _MESSAGE_FIELD.findall(body):
        fields.setdefault(name, []).append(_strip_code(raw_value))
    return fields


def _valid_lifecycle_complete_comment(
    payload: Mapping[str, object],
    *,
    issue_number: int,
    change: str,
    repository_owner: str,
) -> bool:
    """Recognize one canonical trusted terminal ACTION_RESULT."""

    body = payload.get("body")
    user = payload.get("user")
    author_association = payload.get("author_association")
    if not isinstance(body, str) or not isinstance(user, Mapping):
        return False
    actor = user.get("login")
    trusted_owner = actor == repository_owner and author_association == "OWNER"
    trusted_runtime = actor == "github-actions[bot]"
    if not (trusted_owner or trusted_runtime):
        return False
    if "## ACTION_RESULT" not in body.splitlines():
        return False

    fields = _message_fields(body)
    expected = {
        "Workflow": f"#{issue_number}",
        "Change": change,
        "Action": "Lead / finalize-archive",
        "Result": "LIFECYCLE_COMPLETE",
    }
    return all(fields.get(name) == [value] for name, value in expected.items())


def _terminal_evidence_from_comments(
    comments: Iterable[Mapping[str, object]],
    *,
    issue_number: int,
    change: str,
    repository_owner: str,
) -> TerminalEvidence:
    valid = [
        comment
        for comment in comments
        if _valid_lifecycle_complete_comment(
            comment,
            issue_number=issue_number,
            change=change,
            repository_owner=repository_owner,
        )
    ]
    if len(valid) == 1:
        return "terminal-history"
    if len(valid) > 1:
        return "indeterminate"
    return "not-terminal"


def _apply_terminal_evidence(
    observation: GitHubIssueObservation,
    evidence: TerminalEvidence,
) -> GitHubIssueObservation:
    if evidence == "terminal-history":
        return replace(
            observation,
            terminal_evidence=evidence,
            premature_close_recovery="not-candidate",
        )
    return replace(
        observation,
        terminal_evidence=evidence,
        premature_close_recovery=(
            "indeterminate"
            if observation.state == "closed"
            and observation.change != "unset"
            and observation.routing is not None
            else observation.premature_close_recovery
        ),
    )


def acquire_from_issue_pages(
    pages: Iterable[Iterable[Mapping[str, object]]],
    *,
    exhausted: bool,
    terminal_evidence_by_issue: Mapping[int, TerminalEvidence] | None = None,
) -> DispatchPreflight:
    """Build a complete preflight from exhaustively fetched Issues API pages."""

    evidence_by_issue = terminal_evidence_by_issue or {}
    observations: list[GitHubIssueObservation] = []
    for page in pages:
        for payload in page:
            observation = normalize_github_issue(payload)
            if observation is None:
                continue
            if observation.issue_number in evidence_by_issue:
                observation = _apply_terminal_evidence(
                    observation,
                    evidence_by_issue[observation.issue_number],
                )
            observations.append(observation)

    normalized = tuple(observations)
    return acquire_dispatch_preflight(
        observations=normalized,
        source_total_count=len(normalized) if exhausted else None,
        incomplete_results=not exhausted,
        exhausted=exhausted,
    )


def _github_get_list_page(url: str, token: str) -> tuple[Mapping[str, object], ...]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, list):
        raise RuntimeError("GitHub API returned a non-list response")

    items: list[Mapping[str, object]] = []
    for item in decoded:
        if not isinstance(item, Mapping):
            raise RuntimeError("GitHub API returned a malformed item")
        items.append(cast(Mapping[str, object], item))
    return tuple(items)


def _github_issue_pages(
    repository: str,
    token: str,
) -> tuple[tuple[Mapping[str, object], ...], ...]:
    """Exhaust the repository Issues endpoint using current authenticated reads."""

    pages: list[tuple[Mapping[str, object], ...]] = []
    page_number = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repository}/issues"
            f"?state=all&per_page=100&page={page_number}"
        )
        page_items = _github_get_list_page(url, token)
        pages.append(page_items)
        if len(page_items) < 100:
            return tuple(pages)
        page_number += 1


def _github_issue_comment_pages(
    repository: str,
    token: str,
    issue_number: int,
) -> tuple[tuple[Mapping[str, object], ...], ...]:
    """Exhaust comments for one closed workflow-looking Issue."""

    pages: list[tuple[Mapping[str, object], ...]] = []
    page_number = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repository}/issues/{issue_number}/comments"
            f"?per_page=100&page={page_number}"
        )
        page_items = _github_get_list_page(url, token)
        pages.append(page_items)
        if len(page_items) < 100:
            return tuple(pages)
        page_number += 1


def _github_issue(repository: str, token: str, issue_number: int) -> Mapping[str, object]:
    url = f"https://api.github.com/repos/{repository}/issues/{issue_number}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, Mapping):
        raise RuntimeError("GitHub Issue API returned a malformed item")
    return cast(Mapping[str, object], decoded)


def acquire_current_github_preflight(repository: str, token: str) -> DispatchPreflight:
    """Freshly acquire and normalize complete current repository Issue state."""

    pages = _github_issue_pages(repository, token)
    preliminary = acquire_from_issue_pages(pages, exhausted=True)
    repository_owner = repository.split("/", 1)[0]
    terminal_evidence: dict[int, TerminalEvidence] = {}
    reobserved: dict[int, GitHubIssueObservation] = {}

    for issue in preliminary.issues:
        if issue.state != "closed" or issue.change == "unset":
            continue
        comment_pages = _github_issue_comment_pages(repository, token, issue.issue_number)
        comments = (comment for page in comment_pages for comment in page)
        evidence = _terminal_evidence_from_comments(
            comments,
            issue_number=issue.issue_number,
            change=issue.change,
            repository_owner=repository_owner,
        )
        if evidence == "terminal-history":
            current = normalize_github_issue(_github_issue(repository, token, issue.issue_number))
            if (
                current is None
                or not current.authoritative
                or current.state != "closed"
                or current.change != issue.change
                or current.routing != issue.routing
            ):
                evidence = "indeterminate"
            else:
                reobserved[issue.issue_number] = current
        terminal_evidence[issue.issue_number] = evidence

    observations: list[GitHubIssueObservation] = []
    for issue in preliminary.issues:
        observation = reobserved.get(issue.issue_number)
        if observation is None:
            observation = GitHubIssueObservation(
                issue_number=issue.issue_number,
                change=issue.change,
                routing=issue.routing,
                state=issue.state,
                created_order=issue.created_order,
                authoritative=(
                    issue.current_state_provenance is ObservationProvenance.QUALIFIED
                ),
                premature_close_recovery=issue.premature_close_recovery,
                terminal_evidence=issue.terminal_evidence,
            )
        if issue.issue_number in terminal_evidence:
            observation = _apply_terminal_evidence(
                observation, terminal_evidence[issue.issue_number]
            )
        observations.append(observation)

    return acquire_dispatch_preflight(
        observations=tuple(observations),
        source_total_count=len(observations),
        incomplete_results=False,
        exhausted=True,
    )


def _serialize_worker_request(
    request: WorkerRequest | None,
    preflight: DispatchPreflight,
) -> dict[str, Any]:
    decision = classify_dispatch(preflight)
    return {
        "disposition": decision.disposition,
        "reason": decision.reason,
        "formal_issue_ids": decision.formal_issue_ids,
        "recovery_candidate_ids": decision.recovery_candidate_ids,
        "preactivation_candidate_ids": decision.preactivation_candidate_ids,
        "selected_issue_id": decision.selected_issue_id,
        "selected_routing": decision.selected_routing,
        "worker_request": (
            None
            if request is None
            else {
                "issue_number": request.issue_number,
                "role": request.role,
                "action": request.action,
            }
        ),
    }


def _write_github_outputs(request: WorkerRequest | None) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    lines = [f"authorized={'true' if request is not None else 'false'}"]
    if request is not None:
        lines.extend(
            (
                f"issue_number={request.issue_number}",
                f"role={request.role}",
                f"action={request.action}",
            )
        )
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def main() -> int:
    """Run one pre-model dispatch wake from current GitHub state."""

    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    preflight = acquire_current_github_preflight(repository, token)
    request = authorize_worker_request(preflight, RuntimeTrigger())
    _write_github_outputs(request)
    print(json.dumps(_serialize_worker_request(request, preflight), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
