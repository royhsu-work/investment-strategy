"""Fresh Action-only Scheduled-Agent dispatch acquisition."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_action_model import Action as ModelAction
from investment_strategy.scheduled_agent_action_model import role_for
from investment_strategy.scheduled_agent_checkin import is_runtime_checkin_issue
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RepositoryIssueSnapshot,
    Routing,
    classify_dispatch,
)

_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_ACTION_LABELS = {f"action:{action.value}": action.value for action in ModelAction}
_ROUTING_LABEL_PREFIXES = ("agent:", "action:")


@dataclass(frozen=True)
class GitHubIssueObservation:
    """Invocation-local normalized Issue observation."""

    issue_number: int
    change: str
    routing: Routing | None
    state: str
    created_order: int
    authoritative: bool
    routing_debt: bool = False


@dataclass(frozen=True)
class RuntimeTrigger:
    """Non-authoritative wake metadata retained only for override tests."""

    requested_issue: int | None = None
    requested_role: str | None = None
    requested_action: str | None = None


@dataclass(frozen=True)
class WorkerRequest:
    """Exact machine-authorized Action and its derived Role."""

    issue_number: int
    role: str
    action: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.issue_number, int)
            or isinstance(self.issue_number, bool)
            or self.issue_number <= 0
        ):
            raise ValueError("worker Issue identity is invalid")
        try:
            action = ModelAction(self.action)
        except ValueError as exc:
            raise ValueError("worker Action identity is invalid") from exc
        if self.role != role_for(action).value:
            raise ValueError("worker Role must be derived from Action")


def acquire_dispatch_preflight(
    *,
    observations: tuple[GitHubIssueObservation, ...],
    source_total_count: int | None,
    incomplete_results: bool,
    exhausted: bool,
    human_authorized: bool = True,
) -> DispatchPreflight:
    """Build one current-state preflight from fresh GitHub observations."""

    return DispatchPreflight(
        issues=tuple(
            RepositoryIssueSnapshot(
                issue_number=observation.issue_number,
                change=observation.change,
                routing=observation.routing,
                state="open" if observation.state == "open" else "closed",
                created_order=observation.created_order,
                current_state_provenance=(
                    ObservationProvenance.QUALIFIED
                    if observation.authoritative
                    else ObservationProvenance.INDETERMINATE
                ),
                routing_debt=observation.routing_debt,
            )
            for observation in observations
        ),
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
        human_authorized=human_authorized,
    )


def authorize_worker_request(
    preflight: DispatchPreflight,
    trigger: RuntimeTrigger,
) -> WorkerRequest | None:
    """Create one worker request only from fresh machine selection."""

    del trigger
    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id is None
        or decision.selected_routing is None
    ):
        return None
    role, action = decision.selected_routing
    return WorkerRequest(decision.selected_issue_id, role, action)


def _created_order(created_at: object, issue_number: int) -> tuple[int, bool]:
    if not isinstance(created_at, str):
        return issue_number, False
    try:
        return (
            int(datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp() * 1_000_000),
            True,
        )
    except ValueError:
        return issue_number, False


def _label_names(payload: Mapping[str, object]) -> tuple[set[str], bool]:
    raw = payload.get("labels")
    if not isinstance(raw, list):
        return set(), False
    names: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str):
            return set(), False
        names.add(cast(str, item["name"]))
    return names, True


def _routing_from_labels(
    labels: set[str],
) -> tuple[Routing | None, bool]:
    action_labels = sorted(name for name in labels if name.startswith("action:"))
    if any(name not in _ACTION_LABELS for name in action_labels) or len(action_labels) > 1:
        return None, False
    if not action_labels:
        return None, True
    action_text = _ACTION_LABELS[action_labels[0]]
    action = ModelAction(action_text)
    return (role_for(action).value, action.value), True


def _github_timestamp(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _change_from_body(body: object) -> tuple[str, bool]:
    if not isinstance(body, str):
        return "unset", False
    for line in body.splitlines():
        canonical_line = line.strip()
        if not canonical_line:
            continue
        match = _CHANGE_LINE.fullmatch(canonical_line)
        if match is None:
            return "unset", True
        return match.group(1), True
    return "unset", True


def normalize_github_issue(
    payload: Mapping[str, object],
) -> GitHubIssueObservation | None:
    """Normalize one current GitHub Issue; agent labels are ignored."""

    if "pull_request" in payload:
        return None
    number = payload.get("number")
    state = payload.get("state")
    if (
        not isinstance(number, int)
        or isinstance(number, bool)
        or number <= 0
        or state not in {"open", "closed"}
    ):
        return None

    if is_runtime_checkin_issue(payload):
        return None

    labels, labels_valid = _label_names(payload)
    routing, routing_valid = _routing_from_labels(labels)
    created_order, created_valid = _created_order(payload.get("created_at"), number)
    if routing is None:
        change, change_valid = "unset", True
    else:
        change, change_valid = _change_from_body(payload.get("body"))
    closed_valid = _github_timestamp(payload.get("closed_at"))
    return GitHubIssueObservation(
        issue_number=number,
        change=change,
        routing=routing,
        state=cast(str, state),
        created_order=created_order,
        authoritative=all((labels_valid, routing_valid, created_valid, change_valid, closed_valid)),
        routing_debt=state == "closed"
        and any(name.startswith(_ROUTING_LABEL_PREFIXES) for name in labels),
    )


def acquire_from_issue_pages(
    pages: Iterable[Iterable[Mapping[str, object]]],
    *,
    exhausted: bool,
) -> DispatchPreflight:
    """Normalize exhaustively fetched Issue API pages."""

    observations: list[GitHubIssueObservation] = []
    for page in pages:
        for payload in page:
            observation = normalize_github_issue(payload)
            if observation is None:
                if "pull_request" not in payload and not is_runtime_checkin_issue(payload):
                    raise RuntimeError("GitHub Issues API returned an invalid Issue observation")
                continue
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
            raise RuntimeError("GitHub API returned a malformed Issue")
        items.append(cast(Mapping[str, object], item))
    return tuple(items)


def _github_issue_pages(
    repository: str,
    token: str,
) -> tuple[tuple[Mapping[str, object], ...], ...]:
    pages: list[tuple[Mapping[str, object], ...]] = []
    page = 1
    while True:
        items = _github_get_list_page(
            f"https://api.github.com/repos/{repository}/issues?state=all&per_page=100&page={page}",
            token,
        )
        pages.append(items)
        if len(items) < 100:
            return tuple(pages)
        page += 1


def _normalized_observations(
    pages: Iterable[Iterable[Mapping[str, object]]],
) -> tuple[GitHubIssueObservation, ...]:
    observations: list[GitHubIssueObservation] = []
    for page in pages:
        for payload in page:
            observation = normalize_github_issue(payload)
            if observation is None:
                if "pull_request" not in payload and not is_runtime_checkin_issue(payload):
                    raise RuntimeError("GitHub Issues API returned an invalid Issue observation")
                continue
            observations.append(observation)
    return tuple(observations)


def acquire_current_github_preflight(
    repository: str,
    token: str,
    *,
    repository_root: object | None = None,
) -> DispatchPreflight:
    """Fresh-read the complete current coordination-Issue surface, including closed debt."""

    del repository_root
    observations = _normalized_observations(_github_issue_pages(repository, token))
    return acquire_dispatch_preflight(
        observations=observations,
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
    """Run one read-only machine dispatch from current GitHub state."""

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
