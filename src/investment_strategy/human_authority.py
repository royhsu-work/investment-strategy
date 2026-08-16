from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

HUMAN_ACTOR = "royhsu-work"
APPROVAL_LABEL = "human:approved"
DECISION_REF_PREFIX = "Human-Decision-For: "


@dataclass(frozen=True)
class DecisionComment:
    id: int
    created_at: datetime
    updated_at: datetime
    author: str
    body: str
    provenance_available: bool
    performed_via_github_app: str | None


@dataclass(frozen=True)
class LabelEvent:
    id: int
    created_at: datetime
    actor: str
    label: str
    provenance_available: bool
    performed_via_github_app: str | None


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _timestamp(value: object, field: str) -> datetime:
    raw = _string(value, field)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc


def _raw_app_provenance(raw: Mapping[str, object]) -> tuple[bool, str | None]:
    if "performed_via_github_app" not in raw:
        return False, None
    app = raw["performed_via_github_app"]
    return True, None if app is None else "github_app"


def decision_comment_from_raw(raw: Mapping[str, object]) -> DecisionComment:
    user = _mapping(raw.get("user"), "user")
    provenance_available, app = _raw_app_provenance(raw)
    return DecisionComment(
        id=_integer(raw.get("id"), "id"),
        created_at=_timestamp(raw.get("created_at"), "created_at"),
        updated_at=_timestamp(raw.get("updated_at"), "updated_at"),
        author=_string(user.get("login"), "user.login"),
        body=_string(raw.get("body"), "body"),
        provenance_available=provenance_available,
        performed_via_github_app=app,
    )


def label_event_from_raw(raw: Mapping[str, object]) -> LabelEvent:
    if raw.get("event") != "labeled":
        raise ValueError("only labeled events can establish approval authority")
    actor = _mapping(raw.get("actor"), "actor")
    label = _mapping(raw.get("label"), "label")
    provenance_available, app = _raw_app_provenance(raw)
    return LabelEvent(
        id=_integer(raw.get("id"), "id"),
        created_at=_timestamp(raw.get("created_at"), "created_at"),
        actor=_string(actor.get("login"), "actor.login"),
        label=_string(label.get("name"), "label.name"),
        provenance_available=provenance_available,
        performed_via_github_app=app,
    )


def parse_decision_ref(body: str) -> str | None:
    refs = [
        line.removeprefix(DECISION_REF_PREFIX).strip()
        for line in body.splitlines()
        if line.startswith(DECISION_REF_PREFIX)
    ]
    if len(refs) != 1 or not refs[0]:
        return None
    return refs[0]


def _is_human_provenance(
    actor: str,
    provenance_available: bool,
    performed_via_github_app: str | None,
) -> bool:
    return actor == HUMAN_ACTOR and provenance_available and performed_via_github_app is None


def _qualifying_comments(comments: tuple[DecisionComment, ...]) -> tuple[DecisionComment, ...]:
    return tuple(
        comment
        for comment in comments
        if _is_human_provenance(
            comment.author,
            comment.provenance_available,
            comment.performed_via_github_app,
        )
        and parse_decision_ref(comment.body) is not None
    )


def is_human_decision_approved(
    *,
    expected_ref: str,
    approval_label_present: bool,
    comments: tuple[DecisionComment, ...],
    label_events: tuple[LabelEvent, ...],
) -> bool:
    """Evaluate provenance-bound Human authority without persistent approval state."""
    if not expected_ref or not approval_label_present:
        return False

    qualifying_comments = _qualifying_comments(comments)
    expected_comments = tuple(
        comment
        for comment in qualifying_comments
        if parse_decision_ref(comment.body) == expected_ref
    )
    if not expected_comments:
        return False

    latest_expected = max(expected_comments, key=lambda item: (item.created_at, item.id))
    qualifying_events = tuple(
        event
        for event in label_events
        if event.label == APPROVAL_LABEL
        and _is_human_provenance(
            event.actor,
            event.provenance_available,
            event.performed_via_github_app,
        )
    )

    for event in sorted(
        qualifying_events,
        key=lambda item: (item.created_at, item.id),
        reverse=True,
    ):
        candidates = tuple(
            comment
            for comment in qualifying_comments
            if (comment.created_at, comment.id) < (event.created_at, event.id)
        )
        if not candidates:
            continue
        bound = max(candidates, key=lambda item: (item.created_at, item.id))
        if parse_decision_ref(bound.body) != expected_ref:
            continue
        if bound != latest_expected:
            continue
        if bound.updated_at > event.created_at:
            continue
        return True

    return False
