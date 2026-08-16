from __future__ import annotations

from datetime import UTC, datetime

import pytest

from investment_strategy.human_authority import (
    DecisionComment,
    LabelEvent,
    decision_comment_from_raw,
    is_human_decision_approved,
    label_event_from_raw,
)


def _ts(minute: int) -> datetime:
    return datetime(2026, 8, 16, 7, minute, tzinfo=UTC)


def _comment(
    *,
    id: int,
    minute: int,
    decision_ref: str,
    updated_minute: int | None = None,
    app: str | None = None,
    provenance_available: bool = True,
) -> DecisionComment:
    return DecisionComment(
        id=id,
        created_at=_ts(minute),
        updated_at=_ts(updated_minute if updated_minute is not None else minute),
        author="royhsu-work",
        body=f"decision\nHuman-Decision-For: {decision_ref}",
        provenance_available=provenance_available,
        performed_via_github_app=app,
    )


def _event(
    *,
    id: int,
    minute: int,
    app: str | None = None,
    provenance_available: bool = True,
) -> LabelEvent:
    return LabelEvent(
        id=id,
        created_at=_ts(minute),
        actor="royhsu-work",
        label="human:approved",
        provenance_available=provenance_available,
        performed_via_github_app=app,
    )


def _approved(
    expected_ref: str,
    *,
    comments: tuple[DecisionComment, ...],
    events: tuple[LabelEvent, ...],
    label_present: bool = True,
) -> bool:
    return is_human_decision_approved(
        expected_ref=expected_ref,
        approval_label_present=label_present,
        comments=comments,
        label_events=events,
    )


def test_actor_identity_alone_is_not_human_authority() -> None:
    decision_ref = "issue:47:admission:lead:explore-change"
    assert not _approved(
        decision_ref,
        comments=(_comment(id=1, minute=1, decision_ref=decision_ref, app="chatgpt"),),
        events=(_event(id=2, minute=2),),
    )
    assert not _approved(
        decision_ref,
        comments=(_comment(id=1, minute=1, decision_ref=decision_ref),),
        events=(_event(id=2, minute=2, app="chatgpt"),),
    )
    assert not _approved(
        decision_ref,
        comments=(
            _comment(
                id=1,
                minute=1,
                decision_ref=decision_ref,
                provenance_available=False,
            ),
        ),
        events=(_event(id=2, minute=2),),
    )


def test_valid_human_comment_and_later_human_approval_event_pass() -> None:
    decision_ref = "issue:47:admission:lead:propose-change"
    assert _approved(
        decision_ref,
        comments=(_comment(id=10, minute=1, decision_ref=decision_ref),),
        events=(_event(id=20, minute=2),),
    )


def test_missing_or_mismatched_decision_ref_cannot_satisfy_boundary() -> None:
    comments = (_comment(id=10, minute=1, decision_ref="issue:47:advisory-admission"),)
    events = (_event(id=20, minute=2),)
    assert not _approved("issue:47:admission:lead:explore-change", comments=comments, events=events)


def test_event_first_binding_prevents_one_event_from_fanning_out() -> None:
    ref_one = "issue:47:admission:lead:explore-change"
    ref_two = "issue:47:admission:lead:propose-change"
    comments = (
        _comment(id=10, minute=1, decision_ref=ref_one),
        _comment(id=11, minute=2, decision_ref=ref_two),
    )
    events = (_event(id=20, minute=3),)

    assert not _approved(ref_one, comments=comments, events=events)
    assert _approved(ref_two, comments=comments, events=events)


def test_replacement_comment_requires_a_later_approval_event() -> None:
    decision_ref = "issuecomment:1234"
    original = _comment(id=10, minute=1, decision_ref=decision_ref)
    first_event = _event(id=20, minute=2)
    replacement = _comment(id=30, minute=3, decision_ref=decision_ref)

    assert not _approved(
        decision_ref,
        comments=(original, replacement),
        events=(first_event,),
    )
    assert _approved(
        decision_ref,
        comments=(original, replacement),
        events=(first_event, _event(id=40, minute=4)),
    )


def test_post_approval_edit_invalidates_until_later_approval_event() -> None:
    decision_ref = "issuecomment:5678"
    edited = _comment(
        id=10,
        minute=1,
        updated_minute=3,
        decision_ref=decision_ref,
    )

    assert not _approved(
        decision_ref,
        comments=(edited,),
        events=(_event(id=20, minute=2),),
    )
    assert _approved(
        decision_ref,
        comments=(edited,),
        events=(_event(id=20, minute=2), _event(id=40, minute=4)),
    )


def test_current_approval_label_and_qualifying_labeled_event_are_required() -> None:
    decision_ref = "issue:47:advisory-admission"
    comments = (_comment(id=10, minute=1, decision_ref=decision_ref),)
    events = (_event(id=20, minute=2),)
    assert not _approved(
        decision_ref,
        comments=comments,
        events=events,
        label_present=False,
    )
    assert not _approved(decision_ref, comments=comments, events=())


def test_raw_adapter_preserves_missing_provenance_as_fail_closed_evidence() -> None:
    decision_ref = "issue:47:admission:lead:explore-change"
    raw_comment: dict[str, object] = {
        "id": 10,
        "created_at": "2026-08-16T07:01:00Z",
        "updated_at": "2026-08-16T07:01:00Z",
        "user": {"login": "royhsu-work"},
        "body": f"decision\nHuman-Decision-For: {decision_ref}",
    }
    raw_event: dict[str, object] = {
        "id": 20,
        "created_at": "2026-08-16T07:02:00Z",
        "actor": {"login": "royhsu-work"},
        "event": "labeled",
        "label": {"name": "human:approved"},
        "performed_via_github_app": None,
    }

    comment = decision_comment_from_raw(raw_comment)
    event = label_event_from_raw(raw_event)
    assert not comment.provenance_available
    assert not _approved(decision_ref, comments=(comment,), events=(event,))


def test_raw_adapter_distinguishes_human_and_app_provenance() -> None:
    decision_ref = "issuecomment:999"
    raw_comment: dict[str, object] = {
        "id": 10,
        "created_at": "2026-08-16T07:01:00Z",
        "updated_at": "2026-08-16T07:01:00Z",
        "user": {"login": "royhsu-work"},
        "body": f"decision\nHuman-Decision-For: {decision_ref}",
        "performed_via_github_app": None,
    }
    raw_event: dict[str, object] = {
        "id": 20,
        "created_at": "2026-08-16T07:02:00Z",
        "actor": {"login": "royhsu-work"},
        "event": "labeled",
        "label": {"name": "human:approved"},
        "performed_via_github_app": {"id": 1, "slug": "connector"},
    }

    comment = decision_comment_from_raw(raw_comment)
    event = label_event_from_raw(raw_event)
    assert comment.provenance_available
    assert comment.performed_via_github_app is None
    assert event.provenance_available
    assert event.performed_via_github_app == "github_app"
    assert not _approved(decision_ref, comments=(comment,), events=(event,))


def test_unlabeled_event_never_establishes_authority() -> None:
    raw_event: dict[str, object] = {
        "id": 20,
        "created_at": "2026-08-16T07:02:00Z",
        "actor": {"login": "royhsu-work"},
        "event": "unlabeled",
        "label": {"name": "human:approved"},
        "performed_via_github_app": None,
    }
    with pytest.raises(ValueError, match="only labeled events"):
        label_event_from_raw(raw_event)
