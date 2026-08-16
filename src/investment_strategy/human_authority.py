from __future__ import annotations

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
