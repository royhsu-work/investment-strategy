"""One immutable affirmative qualification decision for current formal consequences.

This module is deliberately a small pure decision boundary. It reconstructs only
the repository-owned formal result and Issue lifecycle evidence needed to decide
whether the current route, or one pending derived consequence, is qualified. It
owns no workflow state, cursor, registry, or carrier.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal, cast

from investment_strategy.scheduled_agent_action_model import (
    Action,
    ResultKind,
    TypedResult,
    next_action,
    role_for,
)
from investment_strategy.scheduled_agent_formal_result import (
    _CORRELATION,
    _WORKFLOW,
    FormalLifecycleEvent,
    _field,
    _is_github_actions_comment,
    _marker,
    _normalize_action,
    _normalize_result,
    _normalize_role,
    _valid_sha,
    parse_formal_result,
)
from investment_strategy.workflow_dispatch import ObservationProvenance

_LIFECYCLE_EVENTS = frozenset({"commented", "closed", "labeled", "reopened", "unlabeled"})
_ACTION_LABEL_PREFIX = "action:"
_RECOVERY_MARKER = "APPLICATION_RECOVERY"
_RECOVERY_REASON = "partial-first-activation"
_RECOVERY_SOURCE = ("lead", "propose-change")
_RECOVERY_TARGET = ("lead", "resolve-question")


@dataclass(frozen=True, slots=True)
class IssueLifecycleEvent:
    """One relevant event from the GitHub Issue timeline."""

    event_id: int | None
    event: str | None
    label: str | None
    created_at: str | None
    valid: bool


@dataclass(frozen=True, slots=True)
class AdministrativeRecoveryEvent:
    """One repository-Actions repair of a stranded first formal activation."""

    comment_id: int | None
    issue_number: int | None
    change: str | None
    source: tuple[str, str] | None
    target: tuple[str, str] | None
    default_branch_revision: str | None
    failed_authorization_revision: str | None
    request_comment_id: int | None
    reason: str | None
    valid: bool


@dataclass(frozen=True, slots=True)
class QualificationInput:
    """The complete immutable evidence set consumed by one qualification."""

    issue_number: int
    change: str
    state: str
    current_routing: tuple[str, str] | None
    expected_routing: tuple[str, str] | None
    expected_terminal: bool
    source_routing: tuple[str, str] | None
    expected_result_kind: str | None
    expected_application_correlation: str | None
    current_revision: str | None
    mode: Literal["current", "pending"]
    events: tuple[FormalLifecycleEvent, ...]
    recovery_events: tuple[AdministrativeRecoveryEvent, ...]
    lifecycle_events: tuple[IssueLifecycleEvent, ...]
    authorization_ancestry: tuple[tuple[str, str], ...] = ()
    allow_successor_frontier: bool = False


@dataclass(frozen=True, slots=True)
class QualificationDecision:
    """The only formal consequence decision exposed to consumers."""

    provenance: ObservationProvenance
    reason: str
    event: FormalLifecycleEvent | AdministrativeRecoveryEvent | None = None

    @property
    def qualified(self) -> bool:
        return self.provenance is ObservationProvenance.QUALIFIED


@dataclass(frozen=True, slots=True)
class CurrentFrontier:
    """The repository-derived owner of the currently routed frontier.

    This is only a view of the existing formal qualification decision.  It is
    deliberately not persisted and does not introduce an occurrence counter
    or another workflow state.  ``event`` is the latest qualified formal
    consequence (or administrative recovery); a pre-activation frontier has
    no predecessor event.
    """

    issue_number: int
    change: str
    current_routing: tuple[str, str] | None
    event: FormalLifecycleEvent | AdministrativeRecoveryEvent | None
    decision: QualificationDecision


def _positive_decimal(value: str | None) -> int | None:
    if value is None or not value.isdigit() or value.startswith("0"):
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _recovery_event_from_payload(
    payload: Mapping[str, object],
    *,
    current_revision: str | None,
) -> AdministrativeRecoveryEvent | None:
    body = payload.get("body")
    if not isinstance(body, str) or _marker(body) != _RECOVERY_MARKER:
        return None
    if not _is_github_actions_comment(payload):
        return AdministrativeRecoveryEvent(
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
        )

    raw_workflow = _field(body, "Workflow")
    workflow_match = None if raw_workflow is None else _WORKFLOW.fullmatch(raw_workflow)
    issue_number = None if workflow_match is None else int(workflow_match.group(1))
    change = _field(body, "Change")
    source_role, source_action = _normalize_action(_field(body, "Source"))
    target_role, target_action = _normalize_action(_field(body, "Target"))
    source = None if source_role is None or source_action is None else (source_role, source_action)
    target = None if target_role is None or target_action is None else (target_role, target_action)
    default_branch_revision = _field(body, "Default-Branch-Revision")
    failed_authorization_revision = _field(body, "Failed-Authorization-Revision")
    request_comment_id = _positive_decimal(_field(body, "Request-Comment-ID"))
    reason = _field(body, "Reason")
    comment_id = payload.get("id")
    valid_comment_id = (
        isinstance(comment_id, int) and not isinstance(comment_id, bool) and comment_id > 0
    )
    valid = (
        valid_comment_id
        and issue_number is not None
        and change not in {None, "", "unset"}
        and source == _RECOVERY_SOURCE
        and target == _RECOVERY_TARGET
        and _valid_sha(default_branch_revision)
        and _valid_sha(failed_authorization_revision)
        and request_comment_id is not None
        and reason == _RECOVERY_REASON
        and current_revision is not None
    )
    return AdministrativeRecoveryEvent(
        comment_id=cast(int | None, comment_id) if valid_comment_id else None,
        issue_number=issue_number,
        change=change,
        source=source,
        target=target,
        default_branch_revision=(
            default_branch_revision if _valid_sha(default_branch_revision) else None
        ),
        failed_authorization_revision=(
            failed_authorization_revision if _valid_sha(failed_authorization_revision) else None
        ),
        request_comment_id=request_comment_id,
        reason=reason,
        valid=valid,
    )


def _event_from_checkpoint(
    payload: Mapping[str, object],
    *,
    current_revision: str | None,
) -> FormalLifecycleEvent | None:
    """Reconstruct a legacy implementation completion from its bound checkpoint."""

    body = payload.get("body")
    if not isinstance(body, str) or _marker(body) != "SLICE_CHECKPOINT":
        return None
    if not _is_github_actions_comment(payload):
        return None
    raw_workflow = _field(body, "Workflow")
    workflow_match = None if raw_workflow is None else _WORKFLOW.fullmatch(raw_workflow)
    issue_number = None if workflow_match is None else int(workflow_match.group(1))
    change = _field(body, "Change")
    role_field = _normalize_role(_field(body, "Role"))
    action_role, action = _normalize_action(_field(body, "Action"))
    role = role_field if role_field is not None else action_role
    revision = _field(body, "Revision")
    correlation = _field(body, "Application-Correlation")
    parsed_correlation = None if correlation is None else _CORRELATION.fullmatch(correlation)
    comment_id = payload.get("id")
    valid_comment_id = (
        isinstance(comment_id, int) and not isinstance(comment_id, bool) and comment_id > 0
    )
    default_branch_revision = None if parsed_correlation is None else parsed_correlation.group(7)
    result = None if parsed_correlation is None else _normalize_result(parsed_correlation.group(6))
    successor: tuple[str, str] | None = None
    terminal = False
    transition_valid = False
    if action is not None and result is not None:
        try:
            model_action = Action(action)
            if role != role_for(model_action).value:
                raise ValueError
            expected_successor_action = next_action(model_action, TypedResult(result))
            terminal = expected_successor_action is None
            successor = (
                None
                if expected_successor_action is None
                else (
                    role_for(expected_successor_action).value,
                    expected_successor_action.value,
                )
            )
            transition_valid = True
        except (TypeError, ValueError):
            transition_valid = False
    valid = (
        valid_comment_id
        and issue_number is not None
        and change is not None
        and action == Action.IMPLEMENT_CHANGE.value
        and role == role_for(Action.IMPLEMENT_CHANGE).value
        and result
        in {
            ResultKind.MORE_IMPLEMENTATION_REQUIRED,
            ResultKind.READY,
        }
        and _valid_sha(revision)
        and _valid_sha(default_branch_revision)
        and parsed_correlation is not None
        and parsed_correlation.group(2) == str(issue_number)
        and parsed_correlation.group(3) == change
        and parsed_correlation.group(4) == role
        and parsed_correlation.group(5) == action
        and parsed_correlation.group(7) == revision
        and transition_valid
    )
    return FormalLifecycleEvent(
        comment_id=cast(int | None, comment_id) if valid_comment_id else None,
        issue_number=issue_number,
        change=change,
        role=role,
        action=action,
        result_kind=None if result is None else result.value,
        revision=revision if _valid_sha(revision) else None,
        default_branch_revision=(
            default_branch_revision if _valid_sha(default_branch_revision) else None
        ),
        application_correlation=correlation,
        successor=successor,
        terminal=terminal,
        valid=valid,
    )


def _issue_lifecycle_event_from_payload(
    payload: Mapping[str, object],
) -> IssueLifecycleEvent | None:
    raw_event = payload.get("event")
    if raw_event not in _LIFECYCLE_EVENTS:
        return None
    raw_id = payload.get("id")
    raw_created_at = payload.get("created_at")
    valid_id = isinstance(raw_id, int) and not isinstance(raw_id, bool) and raw_id > 0
    valid_created_at = isinstance(raw_created_at, str) and bool(raw_created_at.strip())
    label: str | None = None
    valid = valid_id and valid_created_at
    if raw_event in {"labeled", "unlabeled"}:
        raw_label = payload.get("label")
        label_payload = raw_label if isinstance(raw_label, Mapping) else None
        label_value = None if label_payload is None else label_payload.get("name")
        label = label_value if isinstance(label_value, str) else None
        valid = (
            valid
            and label is not None
            and label.startswith(_ACTION_LABEL_PREFIX)
            and len(label) > len(_ACTION_LABEL_PREFIX)
        )
        if valid:
            if label is None:
                valid = False
            else:
                try:
                    Action(label[len(_ACTION_LABEL_PREFIX) :])
                except ValueError:
                    valid = False
    return IssueLifecycleEvent(
        event_id=cast(int | None, raw_id) if valid_id else None,
        event=cast(str | None, raw_event),
        label=label,
        created_at=cast(str | None, raw_created_at) if valid_created_at else None,
        valid=valid,
    )


def _lifecycle_order_key(event: IssueLifecycleEvent) -> tuple[str, int]:
    return (
        "" if event.created_at is None else event.created_at,
        10**30 if event.event_id is None else event.event_id,
    )


def _formal_order_key(
    event: FormalLifecycleEvent,
    lifecycle_events: tuple[IssueLifecycleEvent, ...],
) -> tuple[str, int]:
    if event.comment_id is not None:
        matching = tuple(
            item
            for item in lifecycle_events
            if item.event == "commented" and item.event_id == event.comment_id
        )
        if len(matching) == 1:
            return _lifecycle_order_key(matching[0])
        return "", event.comment_id
    return "", 10**30


def _recovery_order_key(
    event: AdministrativeRecoveryEvent,
    lifecycle_events: tuple[IssueLifecycleEvent, ...],
) -> tuple[str, int]:
    if event.comment_id is not None:
        matching = tuple(
            item
            for item in lifecycle_events
            if item.event == "commented" and item.event_id == event.comment_id
        )
        if len(matching) == 1:
            return _lifecycle_order_key(matching[0])
        return "", event.comment_id
    return "", 10**30


def build_qualification_input(
    *,
    issue_number: int,
    change: str,
    state: str,
    current_routing: tuple[str, str] | None,
    comments: Iterable[Mapping[str, object]],
    current_revision: str | None,
    mode: Literal["current", "pending"] = "current",
    expected_routing: tuple[str, str] | None = None,
    expected_terminal: bool = False,
    source_routing: tuple[str, str] | None = None,
    expected_result_kind: str | None = None,
    expected_application_correlation: str | None = None,
    lifecycle_events: Iterable[Mapping[str, object]] = (),
    authorization_ancestry: tuple[tuple[str, str], ...] = (),
    allow_successor_frontier: bool = False,
) -> QualificationInput:
    """Reconstruct one complete current/pending qualification input."""

    lifecycle: list[IssueLifecycleEvent] = []
    for raw_event in lifecycle_events:
        if isinstance(raw_event, Mapping):
            lifecycle_event = _issue_lifecycle_event_from_payload(raw_event)
            if lifecycle_event is not None:
                lifecycle.append(lifecycle_event)
        else:
            lifecycle.append(IssueLifecycleEvent(None, None, None, None, False))
    lifecycle_tuple = tuple(sorted(lifecycle, key=_lifecycle_order_key))

    events: list[FormalLifecycleEvent] = []
    checkpoint_events: list[FormalLifecycleEvent] = []
    recovery_events: list[AdministrativeRecoveryEvent] = []
    for comment in comments:
        recovery_event = _recovery_event_from_payload(
            comment,
            current_revision=current_revision,
        )
        if recovery_event is not None:
            recovery_events.append(recovery_event)
            continue
        formal_event = parse_formal_result(comment, current_revision=current_revision)
        if formal_event is not None:
            events.append(formal_event)
            continue
        checkpoint_event = _event_from_checkpoint(comment, current_revision=current_revision)
        if checkpoint_event is not None:
            checkpoint_events.append(checkpoint_event)
    formal_correlations = {
        event.application_correlation
        for event in events
        if event.application_correlation is not None
    }
    events.extend(
        event
        for event in checkpoint_events
        if event.application_correlation not in formal_correlations
    )
    events.sort(key=lambda item: _formal_order_key(item, lifecycle_tuple))
    recovery_events.sort(key=lambda item: _recovery_order_key(item, lifecycle_tuple))
    return QualificationInput(
        issue_number=issue_number,
        change=change,
        state=state,
        current_routing=current_routing,
        expected_routing=expected_routing,
        expected_terminal=expected_terminal,
        source_routing=source_routing,
        expected_result_kind=expected_result_kind,
        expected_application_correlation=expected_application_correlation,
        current_revision=current_revision,
        mode=mode,
        events=tuple(events),
        recovery_events=tuple(recovery_events),
        lifecycle_events=lifecycle_tuple,
        authorization_ancestry=authorization_ancestry,
        allow_successor_frontier=allow_successor_frontier,
    )


def _indeterminate(
    reason: str,
    event: FormalLifecycleEvent | AdministrativeRecoveryEvent | None = None,
) -> QualificationDecision:
    return QualificationDecision(
        ObservationProvenance.INDETERMINATE,
        reason,
        event,
    )


def _qualified(
    reason: str,
    event: FormalLifecycleEvent | AdministrativeRecoveryEvent,
) -> QualificationDecision:
    return QualificationDecision(
        ObservationProvenance.QUALIFIED,
        reason,
        event,
    )


def _normalized_kind(value: str | None) -> str | None:
    if value is None:
        return None
    return value.lower().replace("_", "-")


def _comment_order_key(
    event: FormalLifecycleEvent | AdministrativeRecoveryEvent,
    lifecycle_events: tuple[IssueLifecycleEvent, ...],
) -> tuple[str, int] | None:
    if event.comment_id is None:
        return None
    matches = tuple(
        item
        for item in lifecycle_events
        if item.event == "commented" and item.event_id == event.comment_id
    )
    if len(matches) != 1 or not matches[0].valid:
        return None
    return _lifecycle_order_key(matches[0])


def _event_interval(
    event: FormalLifecycleEvent | AdministrativeRecoveryEvent,
    next_event: FormalLifecycleEvent | AdministrativeRecoveryEvent | None,
    lifecycle_events: tuple[IssueLifecycleEvent, ...],
) -> tuple[IssueLifecycleEvent, ...] | None:
    start = _comment_order_key(event, lifecycle_events)
    if start is None:
        return None
    end = None if next_event is None else _comment_order_key(next_event, lifecycle_events)
    if next_event is not None and end is None:
        return None
    return tuple(
        item
        for item in lifecycle_events
        if item.valid
        and _lifecycle_order_key(item) > start
        and (end is None or _lifecycle_order_key(item) < end)
    )


def _interval_binds_successor(
    interval: tuple[IssueLifecycleEvent, ...],
    successor: tuple[str, str] | None,
    terminal: bool,
) -> bool:
    relevant = tuple(
        item for item in interval if item.event in {"closed", "labeled", "reopened", "unlabeled"}
    )
    if terminal:
        closes = tuple(item for item in relevant if item.event == "closed")
        if len(closes) != 1 or any(item.event in {"labeled", "reopened"} for item in relevant):
            return False
        close_index = next(index for index, item in enumerate(relevant) if item is closes[0])
        return all(
            index < close_index for index, item in enumerate(relevant) if item.event == "unlabeled"
        )
    if successor is None:
        return False
    expected_label = f"{_ACTION_LABEL_PREFIX}{successor[1]}"
    label_indexes = tuple(index for index, item in enumerate(relevant) if item.event == "labeled")
    if not label_indexes or any(relevant[index].label != expected_label for index in label_indexes):
        return False
    first_label_index = label_indexes[0]
    if any(item.event != "unlabeled" for item in relevant[:first_label_index]):
        return False

    # Once a formal result has bound its derived successor, an exact
    # administrative close+unroute followed by reopen+restore of that same
    # route is idempotent lifecycle restoration, not semantic ABA replay.
    # Any different route, partial restoration, or extra lifecycle mutation
    # remains unqualified.
    cursor = first_label_index + 1
    while cursor < len(relevant):
        cycle = relevant[cursor : cursor + 4]
        if len(cycle) != 4:
            return False
        closed, unlabeled, reopened, relabeled = cycle
        if (
            closed.event != "closed"
            or unlabeled.event != "unlabeled"
            or unlabeled.label != expected_label
            or reopened.event != "reopened"
            or relabeled.event != "labeled"
            or relabeled.label != expected_label
        ):
            return False
        cursor += 4
    return True


def _lifecycle_integrity(events: tuple[IssueLifecycleEvent, ...]) -> bool:
    ids = tuple(event.event_id for event in events)
    return (
        bool(events)
        and all(event.valid for event in events)
        and all(event_id is not None for event_id in ids)
        and len(set(ids)) == len(ids)
        and tuple(sorted(events, key=_lifecycle_order_key)) == events
    )


def _formal_interval_is_bound(
    events: tuple[FormalLifecycleEvent, ...],
    index: int,
    lifecycle_events: tuple[IssueLifecycleEvent, ...],
) -> bool:
    next_event = None if index + 1 >= len(events) else events[index + 1]
    interval = _event_interval(events[index], next_event, lifecycle_events)
    if interval is not None and not any(
        item.event in {"closed", "labeled", "reopened", "unlabeled"} for item in interval
    ):
        # A same-Action result has no label write. Its source must already be
        # established by the preceding bound transition; equality alone cannot
        # seed a qualification chain. All preceding intervals are checked by
        # the same decision, so an intervening ABA cannot be hidden here.
        current = events[index]
        source = (current.role, current.action)
        return (
            index > 0
            and not current.terminal
            and current.successor == source
            and events[index - 1].successor == source
        )
    return interval is not None and _interval_binds_successor(
        interval,
        events[index].successor,
        events[index].terminal,
    )


def _qualify_administrative_recovery(
    qualification: QualificationInput,
) -> QualificationDecision | None:
    if qualification.mode != "current" or not qualification.recovery_events:
        return None
    recovery = qualification.recovery_events[-1]
    if (
        len(qualification.recovery_events) != 1
        or not recovery.valid
        or recovery.issue_number != qualification.issue_number
        or recovery.change != qualification.change
        or recovery.source != _RECOVERY_SOURCE
        or recovery.target != _RECOVERY_TARGET
        or recovery.reason != _RECOVERY_REASON
    ):
        return _indeterminate("administrative-recovery-evidence-incomplete", recovery)
    if (
        recovery.default_branch_revision != qualification.current_revision
        and (
            recovery.default_branch_revision,
            qualification.current_revision,
        )
        not in qualification.authorization_ancestry
    ):
        return _indeterminate("administrative-recovery-evidence-stale", recovery)
    if (
        qualification.state != "open"
        or qualification.current_routing != recovery.target
        or recovery.target is None
    ):
        return _indeterminate("administrative-recovery-postcondition-not-qualified", recovery)
    interval = _event_interval(recovery, None, qualification.lifecycle_events)
    if interval is None or not _interval_binds_successor(interval, recovery.target, False):
        return _indeterminate("administrative-recovery-binding-incomplete", recovery)
    return _qualified("current-administrative-recovery-route-qualified", recovery)


def _qualify_administrative_recovery_predecessor(
    qualification: QualificationInput,
    formal_event: FormalLifecycleEvent,
) -> QualificationDecision:
    """Qualify recovery as the predecessor of a later formal consequence.

    Recovery is an application-owned repair of a partially persisted first
    activation.  A later formal result for the same Change is therefore the
    continuation of that repair when the repository timeline proves that the
    recovery established its source route before the formal comment.  The
    formal result still has to pass the normal qualification below; this
    helper only proves the predecessor relationship.
    """

    recovery = qualification.recovery_events[-1]
    if (
        len(qualification.recovery_events) != 1
        or not recovery.valid
        or recovery.issue_number != qualification.issue_number
        or recovery.change != qualification.change
        or recovery.source != _RECOVERY_SOURCE
        or recovery.target != _RECOVERY_TARGET
        or recovery.reason != _RECOVERY_REASON
    ):
        return _indeterminate("administrative-recovery-evidence-incomplete", recovery)
    if (
        recovery.default_branch_revision != qualification.current_revision
        and (
            recovery.default_branch_revision,
            qualification.current_revision,
        )
        not in qualification.authorization_ancestry
    ):
        return _indeterminate("administrative-recovery-evidence-stale", recovery)
    if (
        not formal_event.valid
        or formal_event.issue_number != qualification.issue_number
        or formal_event.change != qualification.change
        or formal_event.role != recovery.target[0]
        or formal_event.action != recovery.target[1]
    ):
        return _indeterminate(
            "administrative-recovery-competing-formal-evidence",
            formal_event,
        )
    recovery_order = _comment_order_key(recovery, qualification.lifecycle_events)
    formal_order = _comment_order_key(formal_event, qualification.lifecycle_events)
    if recovery_order is None or formal_order is None or recovery_order >= formal_order:
        return _indeterminate(
            "administrative-recovery-formal-ordering-incomplete",
            formal_event,
        )
    interval = _event_interval(recovery, formal_event, qualification.lifecycle_events)
    if interval is None or not _interval_binds_successor(interval, recovery.target, False):
        return _indeterminate(
            "administrative-recovery-predecessor-binding-incomplete",
            recovery,
        )
    return _qualified("administrative-recovery-precedes-formal", recovery)


def qualify_current_formal_consequence(
    qualification: QualificationInput,
) -> QualificationDecision:
    """Evaluate exactly once whether one current formal consequence is qualified."""

    if qualification.change == "unset":
        return QualificationDecision(
            ObservationProvenance.QUALIFIED,
            "preactivation-change-unset",
        )
    if (
        not isinstance(qualification.issue_number, int)
        or qualification.issue_number <= 0
        or qualification.state not in {"open", "closed"}
        or qualification.mode not in {"current", "pending"}
        or not isinstance(qualification.allow_successor_frontier, bool)
        or not _valid_sha(qualification.current_revision)
    ):
        return _indeterminate("qualification-input-incomplete")
    if not _lifecycle_integrity(qualification.lifecycle_events):
        return _indeterminate("issue-lifecycle-evidence-incomplete")
    if qualification.recovery_events:
        competing = tuple(
            event for event in qualification.events if event.change == qualification.change
        )
        if competing:
            predecessor = _qualify_administrative_recovery_predecessor(
                qualification,
                competing[0],
            )
            if not predecessor.qualified:
                return predecessor
        else:
            recovery = _qualify_administrative_recovery(qualification)
            if recovery is not None:
                return recovery
    if not qualification.events:
        return _indeterminate("formal-lifecycle-evidence-missing")

    latest = qualification.events[-1]
    if (
        not latest.valid
        or latest.issue_number != qualification.issue_number
        or latest.change != qualification.change
    ):
        return _indeterminate("latest-formal-evidence-incomplete", latest)
    if (
        latest.default_branch_revision != qualification.current_revision
        and (
            latest.default_branch_revision,
            qualification.current_revision,
        )
        not in qualification.authorization_ancestry
    ):
        return _indeterminate("latest-formal-evidence-stale", latest)
    relevant_suffix: list[FormalLifecycleEvent] = []
    for event in reversed(qualification.events):
        if (
            not event.valid
            or event.issue_number != qualification.issue_number
            or event.change != qualification.change
        ):
            break
        relevant_suffix.append(event)
    relevant_suffix.reverse()
    suffix = tuple(relevant_suffix)
    for index in range(len(suffix) - 1):
        previous = suffix[index]
        current = suffix[index + 1]
        if previous.successor != (current.role, current.action):
            return _indeterminate("lifecycle-ordering-incomplete", current)

    if qualification.mode == "current":
        for index in range(len(suffix)):
            if not _formal_interval_is_bound(suffix, index, qualification.lifecycle_events):
                return _indeterminate("issue-lifecycle-binding-incomplete", suffix[index])
        if qualification.state == "open":
            if (
                qualification.current_routing is None
                or latest.terminal
                or latest.successor != qualification.current_routing
            ):
                return _indeterminate("current-postcondition-not-qualified", latest)
            return _qualified("current-formal-route-qualified", latest)
        if qualification.current_routing is not None or not latest.terminal:
            return _indeterminate("current-terminal-postcondition-not-qualified", latest)
        return _qualified("current-formal-terminal-qualified", latest)

    if qualification.state != "open":
        return _indeterminate("pending-source-is-not-open", latest)
    if (
        qualification.source_routing is None
        or (latest.role, latest.action) != qualification.source_routing
    ):
        return _indeterminate("pending-source-routing-not-qualified", latest)
    at_source_frontier = qualification.current_routing == qualification.source_routing
    at_accepted_successor_frontier = (
        qualification.allow_successor_frontier
        and qualification.expected_routing is not None
        and qualification.current_routing == qualification.expected_routing
        and qualification.current_routing != qualification.source_routing
    )
    if not at_source_frontier and not at_accepted_successor_frontier:
        return _indeterminate("pending-source-routing-not-qualified", latest)
    if qualification.expected_result_kind is None or latest.result_kind != _normalized_kind(
        qualification.expected_result_kind
    ):
        return _indeterminate("pending-result-not-qualified", latest)
    if (
        qualification.expected_application_correlation is None
        or latest.application_correlation != qualification.expected_application_correlation
    ):
        return _indeterminate("pending-application-correlation-not-qualified", latest)

    latest_interval = _event_interval(latest, None, qualification.lifecycle_events)
    if latest_interval is None:
        return _indeterminate("pending-comment-lifecycle-missing", latest)
    if at_source_frontier:
        if any(
            item.event in {"closed", "labeled", "reopened", "unlabeled"}
            for item in latest_interval
        ):
            return _indeterminate("pending-lifecycle-superseded", latest)
    elif not _interval_binds_successor(
        latest_interval,
        qualification.expected_routing,
        False,
    ):
        return _indeterminate("accepted-successor-lifecycle-binding-incomplete", latest)
    for index in range(len(suffix) - 1):
        if not _formal_interval_is_bound(suffix, index, qualification.lifecycle_events):
            return _indeterminate("issue-lifecycle-binding-incomplete", suffix[index])

    if qualification.expected_terminal:
        if not latest.terminal:
            return _indeterminate("pending-terminal-not-qualified", latest)
        return _qualified("pending-terminal-qualified", latest)
    if (
        qualification.expected_routing is None
        or latest.terminal
        or latest.successor != qualification.expected_routing
    ):
        return _indeterminate("pending-successor-not-qualified", latest)
    if at_accepted_successor_frontier:
        return _qualified("accepted-successor-postcondition-qualified", latest)
    return _qualified("pending-successor-qualified", latest)


def derive_current_frontier(qualification: QualificationInput) -> CurrentFrontier | None:
    """Derive the current frontier from the existing formal qualifier.

    Consumers must use the returned predecessor event to scope an application
    occurrence.  A historical result is never a current occurrence merely
    because its Role/Action equals the current route.
    """

    if qualification.mode != "current":
        return None
    decision = qualify_current_formal_consequence(qualification)
    if not decision.qualified:
        return None
    return CurrentFrontier(
        issue_number=qualification.issue_number,
        change=qualification.change,
        current_routing=qualification.current_routing,
        event=decision.event,
        decision=decision,
    )


__all__ = [
    "AdministrativeRecoveryEvent",
    "CurrentFrontier",
    "FormalLifecycleEvent",
    "IssueLifecycleEvent",
    "QualificationDecision",
    "QualificationInput",
    "build_qualification_input",
    "derive_current_frontier",
    "qualify_current_formal_consequence",
]
