from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from investment_strategy.human_authority import (
    DecisionComment,
    HumanDecisionBoundary,
    IssueCreation,
    LabelEvent,
    advisory_admission_ref,
    decision_comment_from_raw,
    decision_ref_for_boundary,
    escalation_response_ref,
    explore_admission_ref,
    is_human_advisory_admission_approved,
    is_human_created_explore_admission,
    is_human_decision_approved,
    is_human_explore_admission_approved,
    issue_creation_from_raw,
    label_event_from_raw,
    propose_admission_ref,
)

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
REVIEWER = ROOT / "agents" / "roles" / "reviewer.md"
EXECUTOR = ROOT / "agents" / "roles" / "executor.md"


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


def _raw_issue(
    *,
    body: str = "Admission: Lead / explore-change\nChange: unset\n\nInvestigate the issue.",
    app: object = None,
    include_provenance: bool = True,
    actor: str = "royhsu-work",
) -> dict[str, object]:
    raw: dict[str, object] = {
        "id": 500,
        "created_at": "2026-08-16T07:00:00Z",
        "user": {"login": actor},
        "body": body,
    }
    if include_provenance:
        raw["performed_via_github_app"] = app
    return raw


def test_actor_identity_alone_is_not_human_authority() -> None:
    decision_ref = explore_admission_ref(47)
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
    decision_ref = propose_admission_ref(47)
    assert _approved(
        decision_ref,
        comments=(_comment(id=10, minute=1, decision_ref=decision_ref),),
        events=(_event(id=20, minute=2),),
    )


def test_missing_or_mismatched_decision_ref_cannot_satisfy_boundary() -> None:
    comments = (_comment(id=10, minute=1, decision_ref=advisory_admission_ref(47)),)
    events = (_event(id=20, minute=2),)
    assert not _approved(explore_admission_ref(47), comments=comments, events=events)


def test_event_first_binding_prevents_one_event_from_fanning_out() -> None:
    ref_one = explore_admission_ref(47)
    ref_two = propose_admission_ref(47)
    comments = (
        _comment(id=10, minute=1, decision_ref=ref_one),
        _comment(id=11, minute=2, decision_ref=ref_two),
    )
    events = (_event(id=20, minute=3),)

    assert not _approved(ref_one, comments=comments, events=events)
    assert _approved(ref_two, comments=comments, events=events)


def test_replacement_comment_requires_a_later_approval_event() -> None:
    decision_ref = escalation_response_ref(1234)
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
    decision_ref = escalation_response_ref(5678)
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
    decision_ref = advisory_admission_ref(47)
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
    decision_ref = explore_admission_ref(47)
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
    decision_ref = escalation_response_ref(999)
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


def test_current_human_reserved_boundaries_use_exact_serialized_anchors() -> None:
    assert explore_admission_ref(52) == "issue:52:admission:lead:explore-change"
    assert propose_admission_ref(52) == "issue:52:admission:lead:propose-change"
    assert advisory_admission_ref(52) == "issue:52:advisory-admission"
    assert escalation_response_ref(5303804185) == "issuecomment:5303804185"

    assert decision_ref_for_boundary(
        HumanDecisionBoundary.EXPLORE_ADMISSION,
        issue_number=52,
    ) == explore_admission_ref(52)
    assert decision_ref_for_boundary(
        HumanDecisionBoundary.PROPOSE_ADMISSION,
        issue_number=52,
    ) == propose_admission_ref(52)
    assert decision_ref_for_boundary(
        HumanDecisionBoundary.ADVISORY_ADMISSION,
        issue_number=52,
    ) == advisory_admission_ref(52)
    assert decision_ref_for_boundary(
        HumanDecisionBoundary.ESCALATION_RESPONSE,
        escalation_comment_id=5303804185,
    ) == escalation_response_ref(5303804185)


def test_unmapped_human_reserved_boundary_fails_closed() -> None:
    with pytest.raises(ValueError, match="unmapped Human-reserved boundary"):
        decision_ref_for_boundary("future-authorization", issue_number=47)


def test_boundary_anchor_requires_the_correct_durable_identity() -> None:
    with pytest.raises(ValueError, match="issue_number is required"):
        decision_ref_for_boundary(HumanDecisionBoundary.EXPLORE_ADMISSION)
    with pytest.raises(ValueError, match="escalation_comment_id is required"):
        decision_ref_for_boundary(HumanDecisionBoundary.ESCALATION_RESPONSE)
    with pytest.raises(ValueError, match="positive integer"):
        explore_admission_ref(0)


def test_human_advisory_admission_requires_distinct_intake_capability() -> None:
    decision_ref = advisory_admission_ref(47)
    comments = (_comment(id=10, minute=1, decision_ref=decision_ref),)
    events = (_event(id=20, minute=2),)

    assert not is_human_advisory_admission_approved(
        issue_number=47,
        intake_approval_label_present=False,
        human_approval_label_present=True,
        comments=comments,
        label_events=events,
    )
    assert is_human_advisory_admission_approved(
        issue_number=47,
        intake_approval_label_present=True,
        human_approval_label_present=True,
        comments=comments,
        label_events=events,
    )


def test_repository_authorized_explore_does_not_need_human_predicate() -> None:
    # Repository-authorized Explore uses independent canonical/deferred/direction/friction evidence.
    # This module deliberately exposes no helper that converts that path into Human authority.
    assert HumanDecisionBoundary.EXPLORE_ADMISSION.value == "explore-admission"


def test_reserved_human_capabilities_are_distinct_and_role_protected() -> None:
    shared = AGENTS.read_text()
    assert "`human:approved`" in shared
    assert "`intake:approved`" in shared
    assert "`intake:approved` remains distinct from" in shared
    assert "its presence or actor attribution alone is insufficient Human proof" in shared
    for role in (LEAD, REVIEWER, EXECUTOR):
        text = role.read_text()
        assert "`human:approved`" in text
        assert "`intake:approved`" in text
        assert "Do not add, remove, restore, or manufacture" in text


def test_provenance_migration_is_prospective_not_retroactive() -> None:
    shared = AGENTS.read_text()
    assert "activates prospectively on default-branch merge" in shared
    assert "Workflows already\nterminal before activation" in shared
    assert "MUST NOT be retroactively reopened or invalidated" in shared
    assert (
        "A still-pending Human-reserved decision first consumed after activation MUST satisfy"
        in shared
    )
    assert "fresh Human decision carrying the exact expected `decision_ref`" in shared


def test_human_created_formal_explore_requires_exact_raw_creation_contract() -> None:
    creation = issue_creation_from_raw(_raw_issue())
    assert isinstance(creation, IssueCreation)
    assert is_human_created_explore_admission(
        creation=creation,
        current_agent_label="agent:lead",
        current_action_label="action:explore-change",
        declaration_history_unambiguous=True,
    )


@pytest.mark.parametrize(
    ("raw", "agent", "action", "history_ok"),
    [
        (_raw_issue(app={"id": 1, "slug": "connector"}), "agent:lead", "action:explore-change", True),
        (_raw_issue(include_provenance=False), "agent:lead", "action:explore-change", True),
        (_raw_issue(body="Change: unset"), "agent:lead", "action:explore-change", True),
        (
            _raw_issue(
                body=(
                    "Admission: Lead / explore-change\n"
                    "Admission: Lead / explore-change\n"
                    "Change: unset"
                )
            ),
            "agent:lead",
            "action:explore-change",
            True,
        ),
        (
            _raw_issue(body="Admission: Lead / propose-change\nChange: unset"),
            "agent:lead",
            "action:explore-change",
            True,
        ),
        (_raw_issue(), "agent:reviewer", "action:explore-change", True),
        (_raw_issue(), "agent:lead", "action:propose-change", True),
        (_raw_issue(), "agent:lead", "action:explore-change", False),
    ],
)
def test_human_created_formal_explore_fails_closed_for_invalid_evidence(
    raw: dict[str, object],
    agent: str,
    action: str,
    history_ok: bool,
) -> None:
    creation = issue_creation_from_raw(raw)
    assert not is_human_created_explore_admission(
        creation=creation,
        current_agent_label=agent,
        current_action_label=action,
        declaration_history_unambiguous=history_ok,
    )


def test_human_created_formal_explore_requires_one_unset_change_declaration() -> None:
    for body in (
        "Admission: Lead / explore-change\nChange: active-change",
        "Admission: Lead / explore-change\nChange: unset\nChange: unset",
        "Admission: Lead / explore-change\nChange: unset\nChange: another-change",
    ):
        assert not is_human_created_explore_admission(
            creation=issue_creation_from_raw(_raw_issue(body=body)),
            current_agent_label="agent:lead",
            current_action_label="action:explore-change",
            declaration_history_unambiguous=True,
        )


def test_human_explore_admission_falls_back_to_existing_general_predicate() -> None:
    issue_number = 88
    decision_ref = explore_admission_ref(issue_number)
    connector_creation = issue_creation_from_raw(
        _raw_issue(app={"id": 1, "slug": "connector"})
    )
    assert is_human_explore_admission_approved(
        issue_number=issue_number,
        creation=connector_creation,
        current_agent_label="agent:lead",
        current_action_label="action:explore-change",
        declaration_history_unambiguous=True,
        approval_label_present=True,
        comments=(_comment(id=10, minute=1, decision_ref=decision_ref),),
        label_events=(_event(id=20, minute=2),),
    )


def test_creation_shortcut_does_not_mutate_general_decision_semantics() -> None:
    propose_ref = propose_admission_ref(88)
    assert not _approved(propose_ref, comments=(), events=())
    assert _approved(
        propose_ref,
        comments=(_comment(id=10, minute=1, decision_ref=propose_ref),),
        events=(_event(id=20, minute=2),),
    )
