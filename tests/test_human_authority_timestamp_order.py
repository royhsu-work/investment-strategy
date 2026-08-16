from __future__ import annotations

from datetime import UTC, datetime

from investment_strategy.human_authority import (
    DecisionComment,
    LabelEvent,
    explore_admission_ref,
    is_human_decision_approved,
)


def test_equal_timestamp_comment_and_approval_event_fails_closed() -> None:
    decision_ref = explore_admission_ref(47)
    timestamp = datetime(2026, 8, 16, 7, 1, tzinfo=UTC)
    comment = DecisionComment(
        id=10,
        created_at=timestamp,
        updated_at=timestamp,
        author="royhsu-work",
        body=f"decision\nHuman-Decision-For: {decision_ref}",
        provenance_available=True,
        performed_via_github_app=None,
    )
    event = LabelEvent(
        id=20,
        created_at=timestamp,
        actor="royhsu-work",
        label="human:approved",
        provenance_available=True,
        performed_via_github_app=None,
    )

    assert not is_human_decision_approved(
        expected_ref=decision_ref,
        approval_label_present=True,
        comments=(comment,),
        label_events=(event,),
    )
