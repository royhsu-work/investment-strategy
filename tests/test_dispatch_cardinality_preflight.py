"""Fixture-driven regression coverage for executable dispatch cardinality preflight."""

from pathlib import Path
from typing import Literal

from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RecoveryEvidence,
    RepositoryIssueSnapshot,
    Routing,
    action_entry_authorized,
    classify_dispatch,
)

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
MIGRATION = ROOT / "agents" / "scheduled-task-migration.md"


def issue(
    number: int,
    change: str,
    routing: Routing | None,
    *,
    state: Literal["open", "closed"] = "open",
    created_order: int = 0,
    recovery: RecoveryEvidence = "not-candidate",
    provenance: ObservationProvenance = ObservationProvenance.QUALIFIED,
) -> RepositoryIssueSnapshot:
    return RepositoryIssueSnapshot(
        issue_number=number,
        change=change,
        routing=routing,
        state=state,
        created_order=created_order,
        premature_close_recovery=recovery,
        current_state_provenance=provenance,
    )


def snapshot(*issues: RepositoryIssueSnapshot, complete: bool = True) -> DispatchPreflight:
    count = len(issues)
    return DispatchPreflight(
        issues=issues,
        enumeration=EnumerationEvidence(
            observed_count=count,
            source_total_count=count if complete else count + 1,
            incomplete_results=False,
            exhausted=complete,
            observation_provenance=ObservationProvenance.QUALIFIED,
        ),
    )


def test_zero_formal_work_selects_oldest_combined_pre_activation_candidate() -> None:
    decision = classify_dispatch(
        snapshot(
            issue(20, "unset", ("lead", "propose-change"), created_order=2),
            issue(19, "unset", ("lead", "explore-change"), created_order=1),
        )
    )
    assert decision.preactivation_candidate_ids == (19, 20)
    assert decision.selected_issue_id == 19


def test_one_formal_work_wins_over_queued_explore() -> None:
    preflight = snapshot(
        issue(30, "active-change", ("executor", "implement-change")),
        issue(31, "unset", ("lead", "explore-change")),
    )
    decision = classify_dispatch(preflight)
    assert decision.formal_issue_ids == (30,)
    assert decision.selected_issue_id == 30
    assert not action_entry_authorized(preflight, 31, ("lead", "explore-change"))


def test_selected_explore_stops_when_fresh_enumeration_is_indeterminate() -> None:
    preflight = snapshot(issue(41, "unset", ("lead", "explore-change")), complete=False)
    decision = classify_dispatch(preflight)
    assert decision.completeness == "INDETERMINATE"
    assert decision.disposition == "FAIL_CLOSED"


def test_one_qualifying_premature_close_blocks_queue_for_lead_recovery() -> None:
    preflight = snapshot(
        issue(
            43,
            "unfinished-change",
            ("executor", "implement-change"),
            state="closed",
            recovery="qualifying",
        ),
        issue(44, "unset", ("lead", "explore-change")),
    )
    decision = classify_dispatch(preflight)
    assert decision.recovery_candidate_ids == (43,)
    assert decision.selected_routing == ("lead", "resolve-question")
    assert action_entry_authorized(preflight, 43, ("lead", "resolve-question"))


def test_two_premature_close_recovery_candidates_fail_closed() -> None:
    preflight = snapshot(
        issue(
            45,
            "first",
            ("reviewer", "review-implementation"),
            state="closed",
            recovery="qualifying",
        ),
        issue(46, "second", ("executor", "merge-pr"), state="closed", recovery="qualifying"),
    )
    assert classify_dispatch(preflight).disposition == "FAIL_CLOSED"


def test_indeterminate_premature_close_evidence_fails_closed() -> None:
    preflight = snapshot(
        issue(48, "possible", ("lead", "finalize-change"), state="closed", recovery="indeterminate")
    )
    assert classify_dispatch(preflight).disposition == "FAIL_CLOSED"


def test_two_formal_workflows_fail_closed_without_winner_selection() -> None:
    preflight = snapshot(
        issue(60, "first", ("executor", "implement-change")),
        issue(61, "second", ("reviewer", "review-openspec")),
    )
    decision = classify_dispatch(preflight)
    assert decision.formal_issue_ids == (60, 61)
    assert decision.disposition == "FAIL_CLOSED"
    assert decision.selected_issue_id is None


def test_terminal_pending_work_wins_over_pre_activation_queue() -> None:
    decision = classify_dispatch(
        snapshot(
            issue(90, "archiving", ("lead", "finalize-archive"), state="closed"),
            issue(91, "unset", ("lead", "explore-change")),
        )
    )
    assert decision.selected_issue_id == 90


def test_current_state_provenance_is_required() -> None:
    preflight = snapshot(
        issue(
            130,
            "bound-ci-observation-by-execution-opportunity",
            ("lead", "resolve-question"),
            provenance=ObservationProvenance.INDETERMINATE,
        )
    )
    decision = classify_dispatch(preflight)
    assert decision.observation_provenance is ObservationProvenance.INDETERMINATE
    assert decision.disposition == "FAIL_CLOSED"


def test_removed_current_routing_is_not_reconstructed_from_history() -> None:
    decision = classify_dispatch(
        snapshot(
            issue(130, "bound-ci-observation-by-execution-opportunity", None),
            issue(133, "enforce-runtime-dispatch-preconditions", ("executor", "implement-change")),
        )
    )
    assert decision.formal_issue_ids == (133,)
    assert decision.selected_issue_id == 133


def test_shared_governance_exposes_concrete_complete_preflight_procedure() -> None:
    text = " ".join(AGENTS.read_text(encoding="utf-8").split())
    for required in (
        "complete repository-wide durable Issue snapshot",
        "observable enumeration completeness",
        "partial page",
        "role-local",
        "candidate-local",
        "indeterminate",
        "only then",
        "mapped Skill",
    ):
        assert required in text


def test_parked_or_reset_work_restarts_from_current_main_not_old_readiness() -> None:
    governance = " ".join(AGENTS.read_text(encoding="utf-8").split())
    orientation = " ".join(MIGRATION.read_text(encoding="utf-8").split())
    for required in (
        "later wake reconstructs the repaired current repository from scratch",
        "stale PASS/readiness",
    ):
        assert required in governance
    for required in (
        "parked/reset work",
        "then-current `main`",
        "Former PASS/readiness evidence remains historical evidence only",
        "fresh repository-wide reconstruction",
        "not a second recovery or dispatch rule",
    ):
        assert required in orientation
