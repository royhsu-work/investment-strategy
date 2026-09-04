from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from investment_strategy.human_authority import (
    DecisionComment,
    HumanInputDisposition,
    HumanInputDispositionKind,
    HumanInputFreshnessResult,
    LabelEvent,
    evaluate_human_input_freshness,
    is_human_decision_approved,
)

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class BoundaryFixture:
    role: str
    action: str
    relied_upon_at: datetime
    comments: tuple[DecisionComment, ...]
    dispositions: tuple[HumanInputDisposition, ...] = ()


def _ts(minute: int) -> datetime:
    return datetime(2026, 8, 20, 0, minute, tzinfo=UTC)


def _comment(
    *,
    id: int,
    minute: int,
    body: str,
    author: str = "royhsu-work",
    app: str | None = None,
    provenance_available: bool = True,
) -> DecisionComment:
    return DecisionComment(
        id=id,
        created_at=_ts(minute),
        updated_at=_ts(minute),
        author=author,
        body=body,
        provenance_available=provenance_available,
        performed_via_github_app=app,
    )


def _evaluate(fixture: BoundaryFixture) -> HumanInputFreshnessResult:
    return evaluate_human_input_freshness(
        comments=fixture.comments,
        relied_upon_at=fixture.relied_upon_at,
        dispositions=fixture.dispositions,
    )


def _governance() -> str:
    return (ROOT / "agents" / "AGENTS.md").read_text()


def _human_input_section() -> str:
    governance = _governance()
    heading = "## Consequential-boundary substantive Human input freshness and disposition"
    start = governance.index(heading)
    rest = governance[start:]
    next_heading = rest.find("\n## ", len(heading))
    return rest if next_heading == -1 else rest[:next_heading]


def test_material_direct_human_input_after_executor_snapshot_blocks_ready() -> None:
    fixture = BoundaryFixture(
        role="Executor",
        action="implement-change",
        relied_upon_at=_ts(2),
        comments=(
            _comment(id=101, minute=1, body="earlier Human context"),
            _comment(id=102, minute=3, body="Does this implementation change the approved scope?"),
        ),
    )

    result = _evaluate(fixture)

    assert not result.clear
    assert result.blocking_comment_ids == (102,)
    assert result.fail_closed_comment_ids == ()


def test_exact_comment_disposition_clears_only_that_late_human_input() -> None:
    fixture = BoundaryFixture(
        role="Executor",
        action="implement-change",
        relied_upon_at=_ts(2),
        comments=(
            _comment(id=102, minute=3, body="Does this implementation change the approved scope?"),
            _comment(
                id=103,
                minute=4,
                body="Also clarify whether the test seam is production state.",
            ),
        ),
        dispositions=(
            HumanInputDisposition(
                comment_id=102,
                kind=HumanInputDispositionKind.ESCALATED,
                rationale="Scope judgment is routed to Lead.",
            ),
        ),
    )

    result = _evaluate(fixture)

    assert not result.clear
    assert result.blocking_comment_ids == (103,)
    assert result.dispositioned_comment_ids == (102,)


def test_material_human_input_blocks_reviewer_gate_and_post_pass_merge() -> None:
    reviewer = BoundaryFixture(
        role="Reviewer",
        action="review-implementation",
        relied_upon_at=_ts(5),
        comments=(_comment(id=201, minute=6, body="This traceability claim looks incomplete."),),
    )
    merge = BoundaryFixture(
        role="Executor",
        action="merge-pr",
        relied_upon_at=_ts(8),
        comments=(
            _comment(
                id=202,
                minute=9,
                body="Please do not merge until this assumption is checked.",
            ),
        ),
    )

    assert _evaluate(reviewer).blocking_comment_ids == (201,)
    assert _evaluate(merge).blocking_comment_ids == (202,)


def test_explicit_non_blocking_disposition_does_not_create_lifecycle_state() -> None:
    fixture = BoundaryFixture(
        role="Reviewer",
        action="review-openspec",
        relied_upon_at=_ts(10),
        comments=(_comment(id=301, minute=11, body="Thanks, acknowledged."),),
        dispositions=(
            HumanInputDisposition(
                comment_id=301,
                kind=HumanInputDispositionKind.NON_BLOCKING,
                rationale="Acknowledgement only; no scope, evidence, or authority consequence.",
            ),
        ),
    )

    result = _evaluate(fixture)

    assert result.clear
    assert result.dispositioned_comment_ids == (301,)
    assert result.blocking_comment_ids == ()


def test_missing_raw_provenance_for_human_attributed_comment_fails_closed() -> None:
    fixture = BoundaryFixture(
        role="Executor",
        action="implement-change",
        relied_upon_at=_ts(12),
        comments=(
            _comment(
                id=401,
                minute=13,
                body="Human-attributed content with unavailable raw provenance",
                provenance_available=False,
            ),
        ),
    )

    result = _evaluate(fixture)

    assert not result.clear
    assert result.blocking_comment_ids == ()
    assert result.fail_closed_comment_ids == (401,)


def test_connector_authored_comment_is_not_reclassified_as_direct_human_input() -> None:
    fixture = BoundaryFixture(
        role="Executor",
        action="merge-pr",
        relied_upon_at=_ts(14),
        comments=(
            _comment(
                id=501,
                minute=15,
                body="ACTION_RESULT emitted by Scheduled Agent",
                app="github_app",
            ),
        ),
    )

    result = _evaluate(fixture)

    assert result.clear
    assert result.blocking_comment_ids == ()
    assert result.fail_closed_comment_ids == ()


def test_non_human_actor_is_outside_direct_human_freshness_classifier() -> None:
    fixture = BoundaryFixture(
        role="Lead",
        action="finalize-change",
        relied_upon_at=_ts(16),
        comments=(
            _comment(
                id=601,
                minute=17,
                body="bot comment",
                author="some-other-actor",
                app=None,
            ),
        ),
    )

    assert _evaluate(fixture).clear


def test_cross_role_scope_question_requires_explicit_lead_escalation_disposition() -> None:
    question = _comment(
        id=701,
        minute=19,
        body="Does this change the approved specification boundary?",
    )
    blocked = BoundaryFixture(
        role="Executor",
        action="implement-change",
        relied_upon_at=_ts(18),
        comments=(question,),
    )
    escalated = BoundaryFixture(
        role="Executor",
        action="implement-change",
        relied_upon_at=_ts(18),
        comments=(question,),
        dispositions=(
            HumanInputDisposition(
                comment_id=701,
                kind=HumanInputDispositionKind.ESCALATED,
                rationale="Specification/scope judgment belongs to Lead / resolve-question.",
            ),
        ),
    )

    assert _evaluate(blocked).blocking_comment_ids == (701,)
    result = _evaluate(escalated)
    assert result.clear
    assert result.dispositioned_comment_ids == (701,)


def test_human_reserved_decision_still_requires_provenance_bound_approval() -> None:
    decision = _comment(
        id=801,
        minute=21,
        body="Human-Decision-For: issue:107:admission:lead:propose-change\nProceed.",
    )
    freshness = BoundaryFixture(
        role="Lead",
        action="propose-change",
        relied_upon_at=_ts(20),
        comments=(decision,),
        dispositions=(
            HumanInputDisposition(
                comment_id=801,
                kind=HumanInputDispositionKind.ANSWERED,
                rationale="Comment was observed and dispositioned for freshness only.",
            ),
        ),
    )

    assert _evaluate(freshness).clear
    assert not is_human_decision_approved(
        expected_ref="issue:107:admission:lead:propose-change",
        approval_label_present=True,
        comments=(decision,),
        label_events=(),
    )

    approval_event = LabelEvent(
        id=802,
        created_at=_ts(22),
        actor="royhsu-work",
        label="human:approved",
        provenance_available=True,
        performed_via_github_app=None,
    )
    assert is_human_decision_approved(
        expected_ref="issue:107:admission:lead:propose-change",
        approval_label_present=True,
        comments=(decision,),
        label_events=(approval_event,),
    )


def test_repeated_wake_reuses_exact_disposition_but_newer_comment_remains_actionable() -> None:
    first = _comment(id=901, minute=24, body="Please verify the traceability mapping.")
    newer = _comment(id=902, minute=25, body="Also verify the replacement responsibility.")
    disposition = HumanInputDisposition(
        comment_id=901,
        kind=HumanInputDispositionKind.ANSWERED,
        rationale="Traceability mapping was verified against the approved artifacts.",
    )

    first_wake = BoundaryFixture(
        role="Reviewer",
        action="review-implementation",
        relied_upon_at=_ts(23),
        comments=(first,),
        dispositions=(disposition,),
    )
    repeated_wake = BoundaryFixture(
        role="Reviewer",
        action="review-implementation",
        relied_upon_at=_ts(23),
        comments=(first, newer),
        dispositions=(disposition,),
    )

    first_result = _evaluate(first_wake)
    assert first_result.clear
    assert first_result.dispositioned_comment_ids == (901,)

    repeated_result = _evaluate(repeated_wake)
    assert not repeated_result.clear
    assert repeated_result.dispositioned_comment_ids == (901,)
    assert repeated_result.blocking_comment_ids == (902,)


def test_shared_governance_owns_consequential_human_input_freshness() -> None:
    section = _human_input_section()

    assert "fresh-read" in section
    assert "consequential" in section
    assert "exact comment id" in section
    assert "correctness" in section
    assert "traceability" in section
    assert "gate validity" in section
    assert "mutation assumptions" in section


def test_direct_human_freshness_classifier_does_not_grant_human_authority() -> None:
    section = _human_input_section()

    assert "performed_via_github_app == null" in section
    assert "does not grant Human authority" in section
    assert "provenance-bound Human" in section


def test_shared_contract_forbids_comment_processing_state() -> None:
    section = _human_input_section()

    assert "comment queue" in section
    assert "unread" in section
    assert "acknowledgement" in section
    assert "MUST NOT" in section
