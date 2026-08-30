"""Machine-gated Scheduled Agent runtime acquisition and worker authorization.

Normal dispatch reconstructs complete current open GitHub Issue state plus the
bounded set of current closed Issues that still carry workflow routing debt.
Completed closed history whose routing has been retired is not normal dispatch
input; detailed recovery evidence is acquired only for current debt candidates.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
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
    classify_open_dispatch,
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
_WORKFLOW_ROUTING_LABELS = tuple((*_AGENT_LABELS, *_ACTION_LABELS))
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")


def _change_matches(body: str) -> list[str]:
    """Return canonical Change fields outside fenced Markdown examples."""

    matches: list[str] = []
    fence_char: str | None = None
    for line in body.splitlines():
        stripped = line.lstrip()
        marker = stripped[0] if stripped.startswith(("```", "~~~")) else None
        if marker is not None:
            if fence_char is None:
                fence_char = marker
            elif marker == fence_char:
                fence_char = None
            continue
        if fence_char is not None:
            continue
        match = _CHANGE_LINE.fullmatch(line)
        if match is not None:
            matches.append(match.group(1))
    return matches


_MESSAGE_FIELD = re.compile(r"(?m)^(?:-\s+)?(Workflow|Change|Action|Result):\s*(.+?)\s*$")
_HUMAN_RETIREMENT = re.compile(
    r"^Human administrative retirement:\s*"
    r"abandon Change (?P<change>[A-Za-z0-9._-]+)\.\s*"
    r"Do not recover or resume #(?P<issue>[1-9][0-9]*)\.(?:\s|$)"
)
_LEGACY_QUOTED_CHANGE_LINE = re.compile(r"(?m)^`Change:\s*(?P<change>[A-Za-z0-9._-]+)`\s*$")
_LEGACY_ARCHIVE_PR_LINE = re.compile(r"(?m)^Archive PR:\s*#[1-9][0-9]*\s*$")
_LEGACY_AUTHORIZED_REVISION_LINE = re.compile(
    r"(?m)^Authorized exact revision:\s*`(?P<revision>[0-9a-f]{40})`\s*$"
)
_LEGACY_ARCHIVE_MERGE_SENTENCE = re.compile(
    r"Merge executed with `expected_head_sha=(?P<head>[0-9a-f]{40})` and succeeded\. "
    r"GitHub merge result commit: `(?P<merge>[0-9a-f]{40})`\."
)
_LEGACY_FINAL_ARCHIVE_HEAD_LINE = re.compile(
    r"(?m)^Authorized/reviewed archive head:\s*`(?P<head>[0-9a-f]{40})`\s*$"
)
_LEGACY_FINAL_ARCHIVE_MERGE_LINE = re.compile(
    r"(?m)^Archive merge commit / current `main` HEAD:\s*`(?P<merge>[0-9a-f]{40})`\s*$"
)
_TERMINAL_ARCHIVE_PR = re.compile(r"Archive PR #(?P<pr>[1-9][0-9]*)", re.IGNORECASE)
_TERMINAL_ARCHIVE_HEAD = re.compile(
    r"(?:exact(?: reviewed/accepted)? head|authorized/reviewed archive head|"
    r"authorized exact revision)"
    r"[^0-9a-f]{0,48}`?(?P<head>[0-9a-f]{40})`?",
    re.IGNORECASE,
)
_TERMINAL_MERGE_COMMIT = re.compile(
    r"(?:merge commit(?: / current `main` HEAD)?|GitHub merge result commit)"
    r"[^0-9a-f]{0,48}`?(?P<merge>[0-9a-f]{40})`?",
    re.IGNORECASE,
)

# Default-branch activation of workflow-dynamic dispatch and its terminal journal contract.
# Commit 0312a56fe38f1702ac8e53ddd7aa6a1deba1cb0d, 2026-08-13T18:11:21Z.
_WORKFLOW_DYNAMIC_ACTIVATED_AT = datetime(2026, 8, 13, 18, 11, 21, tzinfo=UTC)
# Default-branch activation of terminal-aligned Issue closure. Before this commit,
# normal Archive linkage could close the coordination Issue before Lead persisted
# LIFECYCLE_COMPLETE. Commit 6c241723338e47052ca18499c30aef0b11db87d7,
# 2026-08-20T16:50:34Z.
_TERMINAL_CLOSE_ALIGNMENT_ACTIVATED_AT = datetime(2026, 8, 20, 16, 50, 34, tzinfo=UTC)
# First default-branch deployment of the repository-owned machine dispatcher.
# Historical terminal journals created before this boundary may retain the old
# close-before-final-comment ordering; later history must obey terminal-aligned
# ordering. Merge PR #144, commit b7ce952ee8dbd26760441b871d0807a2ece0c3cd.
_MACHINE_DISPATCH_ACTIVATED_AT = datetime(2026, 8, 24, 12, 6, 8, tzinfo=UTC)


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
    legacy_terminal_candidate: bool = False
    routing_debt: bool = False


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
    debt_disposition: str | None = None


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
            routing_debt=observation.routing_debt,
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
        debt_disposition=decision.selected_debt_disposition,
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


def _routing_state_from_labels(
    labels: set[str], *, state: str
) -> tuple[Routing | None, bool, bool]:
    agent_labels = [name for name in labels if name.startswith("agent:")]
    action_labels = [name for name in labels if name.startswith("action:")]
    routing_debt = state == "closed" and bool(agent_labels or action_labels)

    if any(name not in _AGENT_LABELS for name in agent_labels) or any(
        name not in _ACTION_LABELS for name in action_labels
    ):
        return None, False, routing_debt
    if len(agent_labels) > 1 or len(action_labels) > 1:
        return None, False, routing_debt
    if not agent_labels and not action_labels:
        return None, True, False
    if len(agent_labels) == 1 and len(action_labels) == 1:
        return (
            (_AGENT_LABELS[agent_labels[0]], _ACTION_LABELS[action_labels[0]]),
            True,
            routing_debt,
        )
    if state == "closed":
        return None, True, True
    return None, False, False


def _routing_from_labels(labels: set[str]) -> tuple[Routing | None, bool]:
    routing, valid, _ = _routing_state_from_labels(labels, state="open")
    return routing, valid


def _github_timestamp(value: object) -> tuple[datetime | None, bool]:
    if value is None:
        return None, True
    if not isinstance(value, str):
        return None, False
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None, False
    if parsed.tzinfo is None:
        return None, False
    return parsed.astimezone(UTC), True


def normalize_github_issue(payload: Mapping[str, object]) -> GitHubIssueObservation | None:
    """Normalize one current GitHub Issues API object."""

    if "pull_request" in payload:
        return None

    number = payload.get("number")
    state = payload.get("state")
    body = payload.get("body")
    if not isinstance(number, int) or state not in {"open", "closed"}:
        return None

    labels, labels_valid = _label_names(payload)
    routing, routing_valid, routing_debt = _routing_state_from_labels(labels, state=state)
    created_order, created_valid = _created_order(payload.get("created_at"), number)
    closed_at, closed_valid = _github_timestamp(payload.get("closed_at"))

    body_text = body if isinstance(body, str) else ""
    change_matches = _change_matches(body_text)
    change_valid = len(change_matches) <= 1
    if len(change_matches) == 1:
        change = change_matches[0]
    elif routing is None and not routing_debt:
        change = "unset"
    else:
        change = "unset"
        change_valid = False

    recovery: RecoveryEvidence = "not-candidate"
    terminal_evidence: TerminalEvidence = "not-terminal"
    legacy_terminal_candidate = False
    if state == "closed" and change != "unset" and routing_debt:
        terminal_evidence = "indeterminate"
        recovery = "indeterminate"
        legacy_terminal_candidate = (
            closed_valid and closed_at is not None and closed_at < _WORKFLOW_DYNAMIC_ACTIVATED_AT
        )

    return GitHubIssueObservation(
        issue_number=number,
        change=change,
        routing=routing,
        state=cast(str, state),
        created_order=created_order,
        authoritative=(
            labels_valid and routing_valid and created_valid and closed_valid and change_valid
        ),
        premature_close_recovery=recovery,
        terminal_evidence=terminal_evidence,
        legacy_terminal_candidate=legacy_terminal_candidate,
        routing_debt=routing_debt,
    )


def _normalize_closed_issue(payload: Mapping[str, object]) -> GitHubIssueObservation | None:
    """Normalize closed state, including the bounded pre-dynamic quoted Change shape."""

    observation = normalize_github_issue(payload)
    if observation is None or observation.state != "closed" or observation.change != "unset":
        return observation

    body = payload.get("body")
    if not isinstance(body, str) or _change_matches(body):
        return observation
    legacy_matches = _LEGACY_QUOTED_CHANGE_LINE.findall(body)
    if len(legacy_matches) != 1:
        return observation

    labels, labels_valid = _label_names(payload)
    routing, routing_valid, routing_debt = _routing_state_from_labels(labels, state="closed")
    created_order, created_valid = _created_order(
        payload.get("created_at"), observation.issue_number
    )
    closed_at, closed_valid = _github_timestamp(payload.get("closed_at"))
    if not closed_valid or closed_at is None or closed_at >= _WORKFLOW_DYNAMIC_ACTIVATED_AT:
        return observation

    return GitHubIssueObservation(
        issue_number=observation.issue_number,
        change=legacy_matches[0],
        routing=routing,
        state="closed",
        created_order=created_order,
        authoritative=(labels_valid and routing_valid and created_valid and closed_valid),
        premature_close_recovery=("indeterminate" if routing_debt else "not-candidate"),
        terminal_evidence=("indeterminate" if routing_debt else "not-terminal"),
        legacy_terminal_candidate=routing_debt,
        routing_debt=routing_debt,
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


def _terminal_research_result_from_comment(
    payload: Mapping[str, object],
    *,
    issue_number: int,
    repository_owner: str,
) -> str | None:
    body = payload.get("body")
    user = payload.get("user")
    author_association = payload.get("author_association")
    if not isinstance(body, str) or not isinstance(user, Mapping):
        return None
    actor = user.get("login")
    trusted_owner = actor == repository_owner and author_association == "OWNER"
    trusted_runtime = actor == "github-actions[bot]"
    if not (trusted_owner or trusted_runtime):
        return None
    if "## ACTION_RESULT" not in body.splitlines():
        return None

    fields = _message_fields(body)
    expected = {
        "Workflow": f"#{issue_number}",
        "Change": "unset",
        "Action": "Lead / explore-change",
    }
    if not all(fields.get(name) == [value] for name, value in expected.items()):
        return None
    results = fields.get("Result")
    if results is None or len(results) != 1 or results[0] not in {"NO_CHANGE_REQUIRED", "NO_GO"}:
        return None
    return results[0]


def _terminal_research_evidence_from_comments(
    comments: Iterable[Mapping[str, object]],
    *,
    issue_number: int,
    repository_owner: str,
) -> TerminalEvidence:
    results = tuple(
        result
        for comment in comments
        if (
            result := _terminal_research_result_from_comment(
                comment,
                issue_number=issue_number,
                repository_owner=repository_owner,
            )
        )
        is not None
    )
    if not results:
        return "not-terminal"
    if len(set(results)) == 1:
        return "terminal-history"
    return "indeterminate"


def _terminal_identity(
    payload: Mapping[str, object],
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    body = payload.get("body")
    if not isinstance(body, str):
        return frozenset(), frozenset(), frozenset()
    return (
        frozenset(_TERMINAL_ARCHIVE_PR.findall(body)),
        frozenset(_TERMINAL_ARCHIVE_HEAD.findall(body)),
        frozenset(_TERMINAL_MERGE_COMMIT.findall(body)),
    )


def _terminal_comments_compatible(comments: Iterable[Mapping[str, object]]) -> bool:
    identities = tuple(_terminal_identity(comment) for comment in comments)
    for index in range(3):
        values: set[str] = set()
        for identity in identities:
            values.update(identity[index])
        if len(values) > 1:
            return False
    return True


def _valid_legacy_archive_merge_comment(
    payload: Mapping[str, object],
    *,
    change: str,
    repository_owner: str,
) -> bool:
    """Recognize the bounded pre-dynamic archive-merge terminal journal shape."""

    body = payload.get("body")
    user = payload.get("user")
    author_association = payload.get("author_association")
    if not isinstance(body, str) or not isinstance(user, Mapping):
        return False
    if user.get("login") != repository_owner or author_association != "OWNER":
        return False

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines or lines[0] != "Executor / merge-pr — ARCHIVE MERGED":
        return False

    fields = _message_fields(body)
    if fields.get("Change") != [change]:
        return False
    if len(_LEGACY_ARCHIVE_PR_LINE.findall(body)) != 1:
        return False

    authorized = _LEGACY_AUTHORIZED_REVISION_LINE.findall(body)
    merged = _LEGACY_ARCHIVE_MERGE_SENTENCE.findall(body)
    if len(authorized) != 1 or len(merged) != 1:
        return False
    expected_head, merge_commit = merged[0]
    if authorized[0] != expected_head or not merge_commit:
        return False
    if "Handoff target: Lead / `finalize-archive`" not in body:
        return False

    created_at, created_valid = _github_timestamp(payload.get("created_at"))
    updated_at, updated_valid = _github_timestamp(payload.get("updated_at"))
    return (
        created_valid
        and updated_valid
        and created_at is not None
        and updated_at is not None
        and created_at == updated_at
    )


def _valid_legacy_final_archive_comment(
    payload: Mapping[str, object],
    *,
    change: str,
    repository_owner: str,
) -> bool:
    """Recognize the bounded pre-dynamic Lead final-archive terminal journal shape."""

    body = payload.get("body")
    user = payload.get("user")
    author_association = payload.get("author_association")
    if not isinstance(body, str) or not isinstance(user, Mapping):
        return False
    if user.get("login") != repository_owner or author_association != "OWNER":
        return False

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines or lines[0] != "## Lead — final archive confirmation":
        return False

    fields = _message_fields(body)
    if fields.get("Change") != [change] or fields.get("Action") != ["finalize-archive"]:
        return False
    if "Result: **ARCHIVE_CONFIRMED_ON_DEFAULT_BRANCH**" not in lines:
        return False
    if len(_LEGACY_ARCHIVE_PR_LINE.findall(body)) != 1:
        return False

    authorized_heads = _LEGACY_FINAL_ARCHIVE_HEAD_LINE.findall(body)
    merge_commits = _LEGACY_FINAL_ARCHIVE_MERGE_LINE.findall(body)
    if len(authorized_heads) != 1 or len(merge_commits) != 1:
        return False

    created_at, created_valid = _github_timestamp(payload.get("created_at"))
    updated_at, updated_valid = _github_timestamp(payload.get("updated_at"))
    return (
        created_valid
        and updated_valid
        and created_at is not None
        and updated_at is not None
        and created_at == updated_at
    )


def _valid_human_retirement_comment(
    payload: Mapping[str, object],
    *,
    issue_number: int,
    change: str,
    repository_owner: str,
) -> bool:
    body = payload.get("body")
    user = payload.get("user")
    author_association = payload.get("author_association")
    if not isinstance(body, str) or not isinstance(user, Mapping):
        return False
    if user.get("login") != repository_owner or author_association != "OWNER":
        return False
    if (
        "performed_via_github_app" not in payload
        or payload.get("performed_via_github_app") is not None
    ):
        return False

    created_at, created_valid = _github_timestamp(payload.get("created_at"))
    updated_at, updated_valid = _github_timestamp(payload.get("updated_at"))
    if (
        not created_valid
        or not updated_valid
        or created_at is None
        or updated_at is None
        or created_at != updated_at
    ):
        return False

    match = _HUMAN_RETIREMENT.match(body.strip())
    if match is None:
        return False
    return match.group("change") == change and int(match.group("issue")) == issue_number


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
    if not valid:
        return "not-terminal"
    if _terminal_comments_compatible(valid):
        return "terminal-history"
    return "indeterminate"


def _has_human_retirement_comment(
    comments: Iterable[Mapping[str, object]],
    *,
    issue_number: int,
    change: str,
    repository_owner: str,
) -> bool:
    valid = [
        comment
        for comment in comments
        if _valid_human_retirement_comment(
            comment,
            issue_number=issue_number,
            change=change,
            repository_owner=repository_owner,
        )
    ]
    return len(valid) == 1


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
            and observation.routing_debt
            else observation.premature_close_recovery
        ),
    )


def _legacy_terminal_evidence_from_checkout(
    change: str,
    *,
    repository_root: Path,
) -> TerminalEvidence:
    """Classify pre-workflow-dynamic closed history from current OpenSpec state."""

    changes_root = repository_root / "openspec" / "changes"
    archive_root = changes_root / "archive"
    if not changes_root.is_dir() or not archive_root.is_dir():
        return "indeterminate"
    if (changes_root / change).exists():
        return "indeterminate"
    matches = tuple(path for path in archive_root.glob(f"????-??-??-{change}") if path.is_dir())
    return "terminal-history" if len(matches) == 1 else "indeterminate"


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
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, list):
        raise RuntimeError("GitHub API returned a non-list response")

    items: list[Mapping[str, object]] = []
    for item in decoded:
        if not isinstance(item, Mapping):
            raise RuntimeError("GitHub API returned a malformed item")
        items.append(cast(Mapping[str, object], item))
    return tuple(items)


def _github_issue_pages_for_state(
    repository: str,
    token: str,
    state: Literal["open", "closed", "all"],
) -> tuple[tuple[Mapping[str, object], ...], ...]:
    pages: list[tuple[Mapping[str, object], ...]] = []
    page_number = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repository}/issues"
            f"?state={state}&per_page=100&page={page_number}"
        )
        page_items = _github_get_list_page(url, token)
        pages.append(page_items)
        if len(page_items) < 100:
            return tuple(pages)
        page_number += 1


def _github_open_issue_pages(
    repository: str,
    token: str,
) -> tuple[tuple[Mapping[str, object], ...], ...]:
    return _github_issue_pages_for_state(repository, token, "open")


def _github_closed_issue_pages(
    repository: str,
    token: str,
) -> tuple[tuple[Mapping[str, object], ...], ...]:
    """Compatibility helper; production normal dispatch does not call this."""

    return _github_issue_pages_for_state(repository, token, "closed")


def _github_closed_routing_issue_pages(
    repository: str,
    token: str,
) -> tuple[tuple[Mapping[str, object], ...], ...]:
    """Acquire and fresh-observe only current Issues with workflow-routing debt."""

    candidate_ids: set[int] = set()
    for label in _WORKFLOW_ROUTING_LABELS:
        page_number = 1
        while True:
            url = (
                f"https://api.github.com/repos/{repository}/issues"
                f"?state=closed&labels={label}&per_page=100&page={page_number}"
            )
            page_items = _github_get_list_page(url, token)
            for item in page_items:
                if "pull_request" in item:
                    continue
                number = item.get("number")
                if not isinstance(number, int):
                    raise RuntimeError("GitHub closed-routing query returned an invalid Issue")
                candidate_ids.add(number)
            if len(page_items) < 100:
                break
            page_number += 1

    if not candidate_ids:
        return ()
    fresh = tuple(_github_issue(repository, token, number) for number in sorted(candidate_ids))
    return (fresh,)


def _github_issue_pages(
    repository: str,
    token: str,
) -> tuple[tuple[Mapping[str, object], ...], ...]:
    """Compatibility helper for detailed all-Issue acquisition tests."""

    return _github_issue_pages_for_state(repository, token, "all")


def _github_issue_comment_pages(
    repository: str,
    token: str,
    issue_number: int,
) -> tuple[tuple[Mapping[str, object], ...], ...]:
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
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, Mapping):
        raise RuntimeError("GitHub Issue API returned a malformed item")
    return cast(Mapping[str, object], decoded)


def _normalized_observations(
    pages: Iterable[Iterable[Mapping[str, object]]],
) -> tuple[GitHubIssueObservation, ...]:
    return tuple(
        observation
        for page in pages
        for payload in page
        if (observation := normalize_github_issue(payload)) is not None
    )


def _normalized_closed_observations(
    pages: Iterable[Iterable[Mapping[str, object]]],
) -> tuple[GitHubIssueObservation, ...]:
    return tuple(
        observation
        for page in pages
        for payload in page
        if (observation := _normalize_closed_issue(payload)) is not None
    )


def _github_last_visible_issue_comment(
    repository: str,
    token: str,
    *,
    issue_number: int,
    reported_comment_count: int,
) -> Mapping[str, object] | None:
    """Return the last currently visible comment with at most two bounded API reads."""

    if reported_comment_count < 1:
        return None
    page_number = max(1, (reported_comment_count + 99) // 100)
    for candidate_page in (page_number, page_number - 1):
        if candidate_page < 1:
            continue
        url = (
            f"https://api.github.com/repos/{repository}/issues/{issue_number}/comments"
            f"?per_page=100&page={candidate_page}"
        )
        page = _github_get_list_page(url, token)
        if page:
            return page[-1]
    return None


def _structural_terminal_marker(
    repository: str,
    token: str,
    *,
    raw_issue: Mapping[str, object],
    observation: GitHubIssueObservation,
) -> bool:
    """Compatibility proof helper for historical regression fixtures."""

    if (
        not observation.authoritative
        or observation.state != "closed"
        or observation.change == "unset"
    ):
        return False

    comment_count = raw_issue.get("comments")
    if type(comment_count) is not int or comment_count < 1:
        return False

    closed_at, closed_valid = _github_timestamp(raw_issue.get("closed_at"))
    if not closed_valid or closed_at is None:
        return False

    marker = _github_last_visible_issue_comment(
        repository,
        token,
        issue_number=observation.issue_number,
        reported_comment_count=comment_count,
    )
    if marker is None:
        return False

    completed_at, completed_valid = _github_timestamp(marker.get("created_at"))
    if not completed_valid or completed_at is None:
        return False

    repository_owner = repository.split("/", 1)[0]
    if observation.routing is None:
        return (
            raw_issue.get("state_reason") == "not_planned"
            and completed_at <= closed_at
            and _valid_human_retirement_comment(
                marker,
                issue_number=observation.issue_number,
                change=observation.change,
                repository_owner=repository_owner,
            )
        )

    if observation.routing == ("lead", "finalize-archive"):
        if _valid_lifecycle_complete_comment(
            marker,
            issue_number=observation.issue_number,
            change=observation.change,
            repository_owner=repository_owner,
        ):
            if completed_at <= closed_at:
                return True
            if (
                closed_at < _TERMINAL_CLOSE_ALIGNMENT_ACTIVATED_AT
                and closed_at < completed_at < _TERMINAL_CLOSE_ALIGNMENT_ACTIVATED_AT
            ):
                return True

            updated_at, updated_valid = _github_timestamp(marker.get("updated_at"))
            return (
                raw_issue.get("state_reason") == "completed"
                and updated_valid
                and updated_at == completed_at
                and closed_at < completed_at < _MACHINE_DISPATCH_ACTIVATED_AT
            )
        if completed_at > closed_at:
            return False
        return (
            observation.legacy_terminal_candidate
            and raw_issue.get("state_reason") == "completed"
            and _valid_legacy_final_archive_comment(
                marker,
                change=observation.change,
                repository_owner=repository_owner,
            )
        )

    return (
        observation.legacy_terminal_candidate
        and observation.routing == ("executor", "merge-pr")
        and raw_issue.get("state_reason") == "completed"
        and closed_at <= completed_at < _WORKFLOW_DYNAMIC_ACTIVATED_AT
        and _valid_legacy_archive_merge_comment(
            marker,
            change=observation.change,
            repository_owner=repository_owner,
        )
    )


def _invalid_current_debt(observation: GitHubIssueObservation) -> GitHubIssueObservation:
    return replace(observation, authoritative=False, premature_close_recovery="indeterminate")


def _acquire_detailed_exceptional_preflight(
    repository: str,
    token: str,
    *,
    repository_root: Path,
    open_observations: tuple[GitHubIssueObservation, ...],
    closed_pages: tuple[tuple[Mapping[str, object], ...], ...],
) -> DispatchPreflight:
    """Acquire terminal/recovery evidence only for current closed-routing debt."""

    repository_owner = repository.split("/", 1)[0]
    observations: list[GitHubIssueObservation] = list(open_observations)

    for original in _normalized_closed_observations(closed_pages):
        if original.state != "closed" or not original.routing_debt:
            observations.append(_invalid_current_debt(original))
            continue

        if original.change == "unset":
            comment_pages = _github_issue_comment_pages(repository, token, original.issue_number)
            comments = tuple(comment for page in comment_pages for comment in page)
            evidence = _terminal_research_evidence_from_comments(
                comments,
                issue_number=original.issue_number,
                repository_owner=repository_owner,
            )
            current_raw = _github_issue(repository, token, original.issue_number)
            current = _normalize_closed_issue(current_raw)
            if (
                current is None
                or not current.authoritative
                or current.state != "closed"
                or current.change != "unset"
                or not current.routing_debt
            ):
                observations.append(_invalid_current_debt(current or original))
                continue
            observations.append(_apply_terminal_evidence(current, evidence))
            continue

        if original.legacy_terminal_candidate:
            evidence = _legacy_terminal_evidence_from_checkout(
                original.change,
                repository_root=repository_root,
            )
            observations.append(_apply_terminal_evidence(original, evidence))
            continue

        comment_pages = _github_issue_comment_pages(repository, token, original.issue_number)
        comments = tuple(comment for page in comment_pages for comment in page)
        evidence = _terminal_evidence_from_comments(
            comments,
            issue_number=original.issue_number,
            change=original.change,
            repository_owner=repository_owner,
        )

        current_raw = _github_issue(repository, token, original.issue_number)
        current = _normalize_closed_issue(current_raw)
        if (
            current is None
            or not current.authoritative
            or current.state != "closed"
            or current.change != original.change
            or not current.routing_debt
        ):
            observations.append(_invalid_current_debt(current or original))
            continue

        active_change = repository_root / "openspec" / "changes" / original.change
        if evidence == "not-terminal" and _has_human_retirement_comment(
            comments,
            issue_number=original.issue_number,
            change=original.change,
            repository_owner=repository_owner,
        ):
            if current_raw.get("state_reason") == "not_planned" and not active_change.exists():
                evidence = "terminal-history"
            else:
                evidence = "indeterminate"

        if evidence == "not-terminal":
            if current.routing is not None and active_change.exists():
                observations.append(
                    replace(
                        current,
                        terminal_evidence="not-terminal",
                        premature_close_recovery="qualifying",
                    )
                )
                continue
            evidence = "indeterminate"

        observations.append(_apply_terminal_evidence(current, evidence))

    return acquire_dispatch_preflight(
        observations=tuple(observations),
        source_total_count=len(observations),
        incomplete_results=False,
        exhausted=True,
    )


def acquire_current_github_preflight(
    repository: str,
    token: str,
    *,
    repository_root: Path | None = None,
) -> DispatchPreflight:
    """Acquire dispatch from complete current open state plus current routing debt."""

    root = Path.cwd() if repository_root is None else repository_root
    open_pages = _github_open_issue_pages(repository, token)
    open_observations = _normalized_observations(open_pages)
    open_preflight = acquire_dispatch_preflight(
        observations=open_observations,
        source_total_count=len(open_observations),
        incomplete_results=False,
        exhausted=True,
    )
    open_decision = classify_open_dispatch(open_preflight)

    # Multiple/invalid/incomplete OPEN state fails before any closed debt is loaded.
    if open_decision.disposition == "FAIL_CLOSED":
        return open_preflight

    closed_pages = _github_closed_routing_issue_pages(repository, token)
    if not _normalized_closed_observations(closed_pages):
        return open_preflight

    return _acquire_detailed_exceptional_preflight(
        repository,
        token,
        repository_root=root,
        open_observations=open_observations,
        closed_pages=closed_pages,
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
        "selected_debt_disposition": decision.selected_debt_disposition,
        "worker_request": (
            None
            if request is None
            else {
                "issue_number": request.issue_number,
                "role": request.role,
                "action": request.action,
                "debt_disposition": request.debt_disposition,
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
        if request.debt_disposition is not None:
            lines.append(f"debt_disposition={request.debt_disposition}")
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
