"""One immutable affirmative qualification decision for current formal consequences.

This module is deliberately a small pure decision boundary. It reconstructs only
the repository-owned formal result and Issue lifecycle evidence needed to decide
whether the current route, or one pending derived consequence, is qualified. It
owns no workflow state, cursor, registry, or carrier.
"""

from __future__ import annotations

import re
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
from investment_strategy.workflow_dispatch import ObservationProvenance

_FORMAL_RESULT_MARKERS = frozenset({"ACTION_RESULT", "REVIEW_RESULT", "MERGE_RESULT"})
_LIFECYCLE_EVENTS = frozenset({"commented", "closed", "labeled", "reopened", "unlabeled"})
_ACTION_LABEL_PREFIX = "action:"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_WORKFLOW = re.compile(r"^#([1-9][0-9]*)$")
_CORRELATION = re.compile(
    r"^application:([1-9][0-9]*):([1-9][0-9]*):([^:]+):"
    r"(lead|reviewer|executor):([a-z0-9-]+):([a-z0-9-]+):([0-9a-f]{40})$"
)
_SUCCESSOR = re.compile(r"^(Lead|Reviewer|Executor)\s*/\s*([a-z0-9-]+)(?:\s+\([^)]*\))?$")
_ACTION_WITH_ROLE = re.compile(r"^(Lead|Reviewer|Executor)\s*/\s*([a-z0-9-]+)$")
_GITHUB_ACTIONS_BOT = "github-actions[bot]"
_GITHUB_ACTIONS_APP = "github-actions"


@dataclass(frozen=True, slots=True)
class FormalLifecycleEvent:
    """One repository-Actions formal result observation."""

    comment_id: int | None
    issue_number: int | None
    change: str | None
    role: str | None
    action: str | None
    result_kind: str | None
    revision: str | None
    default_branch_revision: str | None
    application_correlation: str | None
    successor: tuple[str, str] | None
    terminal: bool
    valid: bool


@dataclass(frozen=True, slots=True)
class IssueLifecycleEvent:
    """One relevant event from the GitHub Issue timeline."""

    event_id: int | None
    event: str | None
    label: str | None
    created_at: str | None
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
    lifecycle_events: tuple[IssueLifecycleEvent, ...]


@dataclass(frozen=True, slots=True)
class QualificationDecision:
    """The only formal consequence decision exposed to consumers."""

    provenance: ObservationProvenance
    reason: str
    event: FormalLifecycleEvent | None = None

    @property
    def qualified(self) -> bool:
        return self.provenance is ObservationProvenance.QUALIFIED


def _field_values(body: str, key: str) -> tuple[str, ...]:
    return tuple(
        value.strip().strip(chr(96))
        for value in re.findall(rf"(?m)^{re.escape(key)}:\s*(.*)$", body)
    )


def _field(body: str, key: str) -> str | None:
    values = _field_values(body, key)
    if len(values) != 1 or not values[0]:
        return None
    return values[0]


def _marker(body: str) -> str | None:
    first = body.splitlines()[:1]
    if not first:
        return None
    value = first[0].strip()
    if value.startswith("## "):
        value = value[3:].strip()
    return value


def _is_github_actions_comment(payload: Mapping[str, object]) -> bool:
    user = payload.get("user")
    app = payload.get("performed_via_github_app")
    return (
        isinstance(user, Mapping)
        and user.get("login") == _GITHUB_ACTIONS_BOT
        and isinstance(app, Mapping)
        and app.get("slug") == _GITHUB_ACTIONS_APP
    )


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _normalize_role(value: object) -> str | None:
    if value in {"lead", "reviewer", "executor"}:
        return cast(str, value)
    return None


def _normalize_action(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str) or not value:
        return None, None
    match = _ACTION_WITH_ROLE.fullmatch(value)
    if match is not None:
        return (
            {"Lead": "lead", "Reviewer": "reviewer", "Executor": "executor"}[match.group(1)],
            match.group(2),
        )
    return None, value


def _normalize_result(value: object) -> ResultKind | None:
    if not isinstance(value, str):
        return None
    normalized = value.lower().replace("_", "-")
    try:
        return ResultKind(normalized)
    except ValueError:
        return None


def _expected_marker(action: str | None) -> str | None:
    if action is None:
        return None
    if action.startswith("review-"):
        return "REVIEW_RESULT"
    if action.startswith("merge-"):
        return "MERGE_RESULT"
    return "ACTION_RESULT"


def _successor_value(body: str) -> tuple[tuple[str, str] | None, bool]:
    values = _field_values(body, "Repository-derived successor")
    if len(values) > 1:
        return None, False
    if not values:
        return None, True
    value = values[0]
    if value.lower() in {"terminal", "none"}:
        return None, True
    match = _SUCCESSOR.fullmatch(value)
    if match is None:
        return None, False
    role = {"Lead": "lead", "Reviewer": "reviewer", "Executor": "executor"}[match.group(1)]
    return (role, match.group(2)), True


def _event_from_comment(
    payload: Mapping[str, object],
    *,
    current_revision: str | None,
) -> FormalLifecycleEvent | None:
    body = payload.get("body")
    if not isinstance(body, str) or not _is_github_actions_comment(payload):
        return None
    marker = _marker(body)
    if marker not in _FORMAL_RESULT_MARKERS:
        return None

    raw_workflow = _field(body, "Workflow")
    workflow_match = None if raw_workflow is None else _WORKFLOW.fullmatch(raw_workflow)
    issue_number = None if workflow_match is None else int(workflow_match.group(1))
    change = _field(body, "Change")
    role_field = _normalize_role(_field(body, "Role"))
    action_role, action = _normalize_action(_field(body, "Action"))
    role = role_field if role_field is not None else action_role
    result = _normalize_result(_field(body, "Result"))
    revision = _field(body, "Revision")
    default_branch_revision = _field(body, "Default-Branch-Revision")
    correlation = _field(body, "Application-Correlation")
    successor, successor_shape_valid = _successor_value(body)

    parsed_correlation = None if correlation is None else _CORRELATION.fullmatch(correlation)
    terminal = False
    transition_valid = False
    if action is not None and result is not None:
        try:
            model_action = Action(action)
            if role != role_for(model_action).value:
                raise ValueError
            expected_successor_action = next_action(
                model_action,
                TypedResult(result),
            )
            terminal = expected_successor_action is None
            expected_successor = (
                None
                if expected_successor_action is None
                else (
                    role_for(expected_successor_action).value,
                    expected_successor_action.value,
                )
            )
            transition_valid = successor_shape_valid and successor == expected_successor
        except (TypeError, ValueError):
            transition_valid = False

    correlation_valid = (
        parsed_correlation is not None
        and issue_number is not None
        and change is not None
        and role is not None
        and action is not None
        and result is not None
        and _valid_sha(revision)
        and parsed_correlation.group(2) == str(issue_number)
        and parsed_correlation.group(3) == change
        and parsed_correlation.group(4) == role
        and parsed_correlation.group(5) == action
        and parsed_correlation.group(6) == result.value
        and parsed_correlation.group(7) == default_branch_revision
    )
    comment_id = payload.get("id")
    valid_comment_id = (
        isinstance(comment_id, int) and not isinstance(comment_id, bool) and comment_id > 0
    )
    valid = (
        valid_comment_id
        and marker == _expected_marker(action)
        and issue_number is not None
        and change is not None
        and role is not None
        and action is not None
        and result is not None
        and _valid_sha(revision)
        and _valid_sha(default_branch_revision)
        and parsed_correlation is not None
        and correlation_valid
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
    for comment in comments:
        formal_event = _event_from_comment(comment, current_revision=current_revision)
        if formal_event is not None:
            events.append(formal_event)
    events.sort(key=lambda item: _formal_order_key(item, lifecycle_tuple))
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
        lifecycle_events=lifecycle_tuple,
    )


def _indeterminate(
    reason: str,
    event: FormalLifecycleEvent | None = None,
) -> QualificationDecision:
    return QualificationDecision(
        ObservationProvenance.INDETERMINATE,
        reason,
        event,
    )


def _qualified(reason: str, event: FormalLifecycleEvent) -> QualificationDecision:
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
    event: FormalLifecycleEvent,
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
    event: FormalLifecycleEvent,
    next_event: FormalLifecycleEvent | None,
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
    labels = tuple(item for item in relevant if item.event == "labeled")
    if len(labels) != 1 or labels[0].label != f"{_ACTION_LABEL_PREFIX}{successor[1]}":
        return False
    label_index = next(index for index, item in enumerate(relevant) if item is labels[0])
    return not any(
        item.event in {"closed", "reopened"}
        or (item.event == "labeled" and index != label_index)
        or (item.event == "unlabeled" and index > label_index)
        for index, item in enumerate(relevant)
    )


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
    return interval is not None and _interval_binds_successor(
        interval,
        events[index].successor,
        events[index].terminal,
    )


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
        or not _valid_sha(qualification.current_revision)
    ):
        return _indeterminate("qualification-input-incomplete")
    if not qualification.events:
        return _indeterminate("formal-lifecycle-evidence-missing")
    if not _lifecycle_integrity(qualification.lifecycle_events):
        return _indeterminate("issue-lifecycle-evidence-incomplete")

    latest = qualification.events[-1]
    if (
        not latest.valid
        or latest.issue_number != qualification.issue_number
        or latest.change != qualification.change
    ):
        return _indeterminate("latest-formal-evidence-incomplete", latest)
    if latest.default_branch_revision != qualification.current_revision:
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
        or qualification.current_routing != qualification.source_routing
        or (latest.role, latest.action) != qualification.source_routing
    ):
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
    if any(
        item.event in {"closed", "labeled", "reopened", "unlabeled"} for item in latest_interval
    ):
        return _indeterminate("pending-lifecycle-superseded", latest)
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
    return _qualified("pending-successor-qualified", latest)


__all__ = [
    "FormalLifecycleEvent",
    "IssueLifecycleEvent",
    "QualificationDecision",
    "QualificationInput",
    "build_qualification_input",
    "qualify_current_formal_consequence",
]
