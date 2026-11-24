"""Fresh Action-only Scheduled-Agent dispatch acquisition."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_action_model import Action as ModelAction
from investment_strategy.scheduled_agent_action_model import WorkflowDependencies, role_for
from investment_strategy.scheduled_agent_carrier import (
    github_comment_has_app_provenance,
    github_read_bytes_with_retry,
)
from investment_strategy.scheduled_agent_checkin import is_runtime_checkin_issue
from investment_strategy.scheduled_agent_formal_qualification import (
    build_qualification_input,
    qualify_current_formal_consequence,
)
from investment_strategy.scheduled_agent_formal_result import FormalLifecycleEvent
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
_GITHUB_ACTIONS_BOT = "github-actions[bot]"
_GITHUB_ACTIONS_APP = "github-actions"


def is_github_actions_comment(payload: Mapping[str, object]) -> bool:
    """Recognize formal evidence authored by the repository Actions app."""

    return github_comment_has_app_provenance(
        payload, actor=_GITHUB_ACTIONS_BOT, app_slug=_GITHUB_ACTIONS_APP
    )


@dataclass(frozen=True)
class GitHubIssueObservation:
    """Invocation-local normalized Issue observation."""

    issue_number: int
    change: str
    routing: Routing | None
    state: str
    created_order: int
    authoritative: bool
    current_state_provenance: ObservationProvenance = ObservationProvenance.QUALIFIED
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
    dependencies: WorkflowDependencies | None = (),
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
                    observation.current_state_provenance
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
        dependencies=dependencies,
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


def _is_inert_closed_history(
    *,
    state: str,
    routing: Routing | None,
    routing_debt: bool,
    labels_valid: bool,
    routing_valid: bool,
) -> bool:
    """Identify a closed record that cannot affect a current consequence."""

    return (
        state == "closed"
        and labels_valid
        and routing_valid
        and routing is None
        and not routing_debt
    )


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
    """Normalize one current GitHub Issue; agent labels are ignored.

    ``authoritative`` covers facts that can affect the current dispatch
    consequence. A safely identified closed, unrouted, non-debt record is
    terminal history, so its body and ordering metadata are not current
    consequence inputs and must not poison the repository preflight.
    """

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
    change, change_valid = _change_from_body(payload.get("body"))
    closed_valid = _github_timestamp(payload.get("closed_at"))
    routing_debt = state == "closed" and any(
        name.startswith(_ROUTING_LABEL_PREFIXES) for name in labels
    )
    inert_closed_history = _is_inert_closed_history(
        state=cast(str, state),
        routing=routing,
        routing_debt=routing_debt,
        labels_valid=labels_valid,
        routing_valid=routing_valid,
    )
    authoritative = (
        labels_valid and routing_valid
        if inert_closed_history
        else all((labels_valid, routing_valid, created_valid, change_valid, closed_valid))
    )
    return GitHubIssueObservation(
        issue_number=number,
        change=change,
        routing=routing,
        state=cast(str, state),
        created_order=created_order,
        authoritative=authoritative,
        current_state_provenance=ObservationProvenance.QUALIFIED,
        routing_debt=routing_debt,
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
    raw = github_read_bytes_with_retry(
        request,
        open_request=urlopen,  # noqa: S310 - trusted GitHub API host
        wait=time.sleep,
    )
    decoded = json.loads(raw.decode("utf-8"))
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


def _github_get_object(url: str, token: str) -> Mapping[str, object]:
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    raw = github_read_bytes_with_retry(
        request,
        open_request=urlopen,  # noqa: S310 - trusted GitHub API host
        wait=time.sleep,
    )
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, Mapping):
        raise RuntimeError("GitHub API returned a malformed object")
    return cast(Mapping[str, object], decoded)


def _current_default_branch_revision(
    repository: str,
    token: str,
) -> str | None:
    repository_url = f"https://api.github.com/repos/{repository}"
    root = _github_get_object(repository_url, token)
    branch = root.get("default_branch")
    if not isinstance(branch, str) or not branch or branch.startswith("refs/"):
        return None
    ref = _github_get_object(
        f"{repository_url}/git/ref/heads/{branch}",
        token,
    )
    obj = ref.get("object")
    revision = None if not isinstance(obj, Mapping) else obj.get("sha")
    if isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{40}", revision):
        return revision
    return None


def _github_issue_comment_pages(
    repository: str,
    token: str,
    issue_number: int,
) -> tuple[Mapping[str, object], ...]:
    comments: list[Mapping[str, object]] = []
    page = 1
    while True:
        suffix = "" if page == 1 else f"&page={page}"
        items = _github_get_list_page(
            f"https://api.github.com/repos/{repository}/issues/{issue_number}/comments"
            f"?per_page=100&sort=created&direction=desc{suffix}",
            token,
        )
        comments.extend(items)
        if len(items) < 100:
            return tuple(comments)
        page += 1


def _github_issue_timeline_pages(
    repository: str,
    token: str,
    issue_number: int,
) -> tuple[Mapping[str, object], ...]:
    events: list[Mapping[str, object]] = []
    page = 1
    while True:
        items = _github_get_list_page(
            f"https://api.github.com/repos/{repository}/issues/{issue_number}/timeline"
            f"?per_page=100&page={page}",
            token,
        )
        events.extend(items)
        if len(items) < 100:
            return tuple(events)
        page += 1


def _qualify_current_observation(
    observation: GitHubIssueObservation,
    comments: tuple[Mapping[str, object], ...],
    lifecycle_events: tuple[Mapping[str, object], ...],
    current_revision: str | None,
    authorization_ancestry: tuple[tuple[str, str], ...] = (),
    *,
    require_completed: bool = False,
) -> GitHubIssueObservation:
    if observation.change == "unset":
        return (
            replace(observation, current_state_provenance=ObservationProvenance.INDETERMINATE)
            if require_completed
            else observation
        )
    qualification_input = build_qualification_input(
        issue_number=observation.issue_number,
        change=observation.change,
        state=observation.state,
        current_routing=observation.routing,
        comments=comments,
        current_revision=current_revision,
        lifecycle_events=lifecycle_events,
        authorization_ancestry=authorization_ancestry,
    )
    decision = qualify_current_formal_consequence(qualification_input)
    if require_completed and not (
        decision.qualified
        and isinstance(decision.event, FormalLifecycleEvent)
        and decision.event.terminal
        and decision.event.action == "finalize-archive"
        and decision.event.result_kind == "lifecycle-complete"
    ):
        return replace(observation, current_state_provenance=ObservationProvenance.INDETERMINATE)
    return replace(observation, current_state_provenance=decision.provenance)


def _qualify_current_observations(
    repository: str,
    token: str,
    observations: tuple[GitHubIssueObservation, ...],
    current_revision: str | None,
    *,
    required_completion: frozenset[int] = frozenset(),
    suspended: frozenset[int] = frozenset(),
    comments_by_issue: Mapping[int, tuple[Mapping[str, object], ...]],
) -> tuple[GitHubIssueObservation, ...]:
    qualified: list[GitHubIssueObservation] = []
    for observation in observations:
        require_completed = observation.issue_number in required_completion
        if observation.issue_number in suspended:
            qualified.append(observation)
            continue
        if observation.change == "unset":
            qualified.append(
                replace(observation, current_state_provenance=ObservationProvenance.INDETERMINATE)
                if require_completed
                else observation
            )
            continue
        # Closed Issues without a current routing label are inert historical
        # workflow records.  Their pre-activation terminal evidence may use
        # legacy result envelopes, but they cannot be selected or supply a
        # current consequence.  Keep the strict qualifier for open routes and
        # closed routing debt so active and premature-close cases still fail
        # closed.
        if observation.state == "closed" and observation.routing is None and not require_completed:
            qualified.append(observation)
            continue
        comments = comments_by_issue.get(observation.issue_number)
        if comments is None:
            comments = _github_issue_comment_pages(repository, token, observation.issue_number)
        lifecycle_events = _github_issue_timeline_pages(
            repository,
            token,
            observation.issue_number,
        )
        if observation.routing_debt:
            qualified.append(observation)
            continue
        # Observe ancestry of the bound historical authorization. The qualifier
        # still owns causal binding and lifecycle no-supersession; ancestry alone
        # never makes a current route eligible and cannot authorize new effects.
        authorization_ancestry: list[tuple[str, str]] = []
        if current_revision is not None:
            # Reuse the formal evidence parser for both ordinary results and
            # application-owned recovery. A recovery is itself a durable
            # authorization at its recorded default-branch revision; omitting
            # that revision makes a valid recovery stale as soon as main
            # advances through the repair it enabled.
            qualification_input = build_qualification_input(
                issue_number=observation.issue_number,
                change=observation.change,
                state=observation.state,
                current_routing=observation.routing,
                comments=comments,
                current_revision=current_revision,
                lifecycle_events=lifecycle_events,
            )
            revisions = {
                event.default_branch_revision
                for event in qualification_input.events
                if event.valid
                and event.issue_number == observation.issue_number
                and event.change == observation.change
                and event.default_branch_revision is not None
                and event.default_branch_revision != current_revision
            }
            revisions.update(
                event.default_branch_revision
                for event in qualification_input.recovery_events
                if event.valid
                and event.issue_number == observation.issue_number
                and event.change == observation.change
                and event.default_branch_revision is not None
                and event.default_branch_revision != current_revision
            )
            for revision in sorted(revisions):
                comparison = _github_get_object(
                    f"https://api.github.com/repos/{repository}/compare/{revision}...{current_revision}",
                    token,
                )
                if (
                    comparison.get("status") in {"ahead", "identical"}
                    and comparison.get("behind_by") == 0
                ):
                    authorization_ancestry.append((revision, current_revision))
        qualified.append(
            _qualify_current_observation(
                observation,
                comments,
                lifecycle_events,
                current_revision,
                tuple(authorization_ancestry),
                require_completed=require_completed,
            )
            if current_revision is not None
            else replace(
                observation,
                current_state_provenance=ObservationProvenance.INDETERMINATE,
            )
        )
    return tuple(qualified)


def _declared_blockers(
    repository: str, issue_number: int, comments: tuple[Mapping[str, object], ...]
) -> tuple[int | None, ...]:
    """The latest qualified declaration is the entire prerequisite set."""
    owner = repository.split("/", 1)[0]
    commands: list[tuple[datetime, int, Mapping[str, object]]] = []
    seen: set[int] = set()
    for raw in comments:
        body = raw.get("body")
        user = raw.get("user")
        if (
            not isinstance(body, str)
            or not body.strip().startswith("Blocked by:")
            or raw.get("author_association") != "OWNER"
            or not isinstance(user, Mapping)
            or user.get("login") != owner
        ):
            continue
        if "performed_via_github_app" not in raw:
            raise ValueError("maintenance declaration provenance unavailable")
        if raw["performed_via_github_app"] is not None and not github_comment_has_app_provenance(
            raw, actor=owner, app_slug="chatgpt-codex-connector"
        ):
            continue
        comment_id = raw.get("id")
        created = raw.get("created_at")
        if (
            not isinstance(comment_id, int)
            or isinstance(comment_id, bool)
            or comment_id <= 0
            or comment_id in seen
            or raw.get("issue_url")
            != f"https://api.github.com/repos/{repository}/issues/{issue_number}"
            or not isinstance(created, str)
            or not _github_timestamp(created)
        ):
            raise ValueError("maintenance declaration identity invalid")
        seen.add(comment_id)
        commands.append((datetime.fromisoformat(created.replace("Z", "+00:00")), comment_id, raw))
    if not commands:
        return ()
    _, _, current = max(commands, key=lambda item: (item[0], item[1]))
    if current.get("created_at") != current.get("updated_at"):
        raise ValueError("maintenance declaration was edited")
    command = cast(str, current["body"]).strip()
    if command == "Blocked by: none":
        return ()
    item_pattern = r"(?:#[1-9][0-9]*|external)"
    if re.fullmatch(rf"Blocked by: {item_pattern}(?:, *{item_pattern})*", command) is None:
        raise ValueError("maintenance declaration invalid")
    blockers = tuple(sorted({int(number) for number in re.findall(r"#([0-9]+)", command)}))
    if issue_number in blockers:
        raise ValueError("maintenance dependency cannot block itself")
    # None denotes a declared external prerequisite, never a fabricated Issue.
    return (*blockers, None) if "external" in command else blockers


def _read_dependencies(
    repository: str,
    token: str,
    observations: tuple[GitHubIssueObservation, ...],
    comments_by_issue: dict[int, tuple[Mapping[str, object], ...]],
) -> WorkflowDependencies:
    """Read the current graph once, from existing routed Issue comments."""
    if any(item.routing_debt for item in observations):
        return ()
    by_number = {item.issue_number: item for item in observations}
    dependencies: list[tuple[int, tuple[int | None, ...]]] = []
    for item in observations:
        if item.state != "open" or item.routing is None:
            continue
        comments = _github_issue_comment_pages(repository, token, item.issue_number)
        comments_by_issue[item.issue_number] = comments
        blockers = _declared_blockers(repository, item.issue_number, comments)
        for number in blockers:
            if number is None:
                continue
            target = by_number.get(number)
            if (
                target is None
                or not target.authoritative
                or (target.state == "open" and target.routing is None)
            ):
                raise ValueError("maintenance dependency target unavailable")
        if blockers:
            dependencies.append((item.issue_number, blockers))
    return tuple(dependencies)


def acquire_current_github_preflight(
    repository: str,
    token: str,
    *,
    repository_root: object | None = None,
) -> DispatchPreflight:
    """Reconstruct dependencies and current executable workflow eligibility."""

    del repository_root
    observations = _normalized_observations(_github_issue_pages(repository, token))
    current_revision = _current_default_branch_revision(repository, token)
    comments_by_issue: dict[int, tuple[Mapping[str, object], ...]] = {}
    try:
        dependencies = _read_dependencies(repository, token, observations, comments_by_issue)
    except ValueError:
        return acquire_dispatch_preflight(
            observations=observations,
            source_total_count=len(observations),
            incomplete_results=False,
            exhausted=True,
            dependencies=None,
        )
    if dependencies and current_revision is None:
        return acquire_dispatch_preflight(
            observations=observations,
            source_total_count=len(observations),
            incomplete_results=False,
            exhausted=True,
            dependencies=None,
        )

    targets = {number for _, blockers in dependencies for number in blockers if number is not None}
    closed_targets = tuple(
        item for item in observations if item.state == "closed" and item.issue_number in targets
    )
    completed = {
        item.issue_number
        for item in _qualify_current_observations(
            repository,
            token,
            closed_targets,
            current_revision,
            required_completion=frozenset(item.issue_number for item in closed_targets),
            comments_by_issue=comments_by_issue,
        )
        if item.current_state_provenance is ObservationProvenance.QUALIFIED
    }
    outstanding = tuple(
        (number, remaining)
        for number, blockers in dependencies
        if (remaining := tuple(blocker for blocker in blockers if blocker not in completed))
    )
    # Suspended work is not eligible for mutation. Retain its current
    # structural identity and defer formal frontier qualification until resume.
    observations = _qualify_current_observations(
        repository,
        token,
        observations,
        current_revision,
        suspended=frozenset(number for number, _ in outstanding),
        comments_by_issue=comments_by_issue,
    )
    return acquire_dispatch_preflight(
        observations=observations,
        source_total_count=len(observations),
        incomplete_results=False,
        exhausted=True,
        dependencies=outstanding,
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
