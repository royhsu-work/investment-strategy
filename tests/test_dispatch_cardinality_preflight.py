"""Fixture-driven regression coverage for executable dispatch cardinality preflight."""

from pathlib import Path
from typing import Literal

import pytest

import investment_strategy.scheduled_agent_runtime as runtime
import investment_strategy.workflow_dispatch as workflow_dispatch
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RecoveryEvidence,
    RepositoryIssueSnapshot,
    Routing,
    TerminalEvidence,
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
    terminal: TerminalEvidence = "not-terminal",
    provenance: ObservationProvenance = ObservationProvenance.QUALIFIED,
) -> RepositoryIssueSnapshot:
    return RepositoryIssueSnapshot(
        issue_number=number,
        change=change,
        routing=routing,
        state=state,
        created_order=created_order,
        premature_close_recovery=recovery,
        terminal_evidence=terminal,
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


def _queued_propose_payload(
    number: int = 168,
    *,
    created_at: str = "2026-08-27T01:00:00Z",
) -> dict[str, object]:
    return {
        "number": number,
        "state": "open",
        "body": "Change: unset",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:propose-change"},
        ],
        "created_at": created_at,
        "closed_at": None,
    }


def _queued_explore_payload(
    number: int = 169,
    *,
    created_at: str = "2026-08-27T02:00:00Z",
) -> dict[str, object]:
    return {
        "number": number,
        "state": "open",
        "body": "Change: unset",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:explore-change"},
        ],
        "created_at": created_at,
        "closed_at": None,
    }


def _duplicate_workflow_field_comment() -> dict[str, object]:
    return {
        "id": 5460000000,
        "body": (
            "## ACTION_RESULT\n\n"
            "Workflow: #168\n"
            "Change: `unset`\n"
            "Action: `Lead / explore-change`\n"
            "Result: `PROPOSAL_READY`\n\n"
            "Evidence notes:\n"
            "- Workflow: Scheduled Agent Bridge\n"
        ),
        "user": {"login": "github-actions[bot]"},
        "author_association": "NONE",
        "created_at": "2026-08-27T01:30:00Z",
        "updated_at": "2026-08-27T01:30:00Z",
    }


def test_zero_formal_work_selects_oldest_combined_pre_activation_candidate() -> None:
    decision = classify_dispatch(
        snapshot(
            issue(20, "unset", ("lead", "propose-change"), created_order=1),
            issue(19, "unset", ("lead", "explore-change"), created_order=2),
        )
    )
    assert decision.preactivation_candidate_ids == (20, 19)
    assert decision.selected_issue_id == 20
    assert decision.selected_routing == ("lead", "propose-change")


def test_current_propose_tuple_is_preactivation_candidate_without_admission_state() -> None:
    decision = classify_dispatch(
        snapshot(issue(20, "unset", ("lead", "propose-change"), created_order=1))
    )
    assert decision.preactivation_candidate_ids == (20,)
    assert decision.selected_issue_id == 20
    assert decision.selected_routing == ("lead", "propose-change")


def test_production_fifo_does_not_read_history_to_qualify_current_propose(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    propose = _queued_propose_payload()
    explore = _queued_explore_payload()
    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((propose, explore),),
    )
    monkeypatch.setattr(runtime, "_github_closed_routing_issue_pages", lambda repository, token: ())

    def forbidden_history(*args: object, **kwargs: object) -> object:
        raise AssertionError("global dispatch must not re-derive current Propose eligibility")

    monkeypatch.setattr(runtime, "_github_issue_comment_pages", forbidden_history)
    monkeypatch.setattr(runtime, "_github_issue_event_pages", forbidden_history)

    decision = classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )
    assert decision.disposition == "AUTHORIZE"
    assert decision.preactivation_candidate_ids == (168, 169)
    assert decision.selected_issue_id == 168
    assert decision.selected_routing == ("lead", "propose-change")


def test_irrelevant_duplicate_markdown_fields_cannot_remove_current_propose_from_fifo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    propose = _queued_propose_payload()
    explore = _queued_explore_payload()
    duplicate_field = _duplicate_workflow_field_comment()
    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((propose, explore),),
    )
    monkeypatch.setattr(runtime, "_github_closed_routing_issue_pages", lambda repository, token: ())
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: (
            ((duplicate_field,),) if issue_number == 168 else ((),)
        ),
    )

    def forbidden_events(*args: object, **kwargs: object) -> object:
        raise AssertionError("Markdown history must not fall back to Human-admission reconstruction")

    monkeypatch.setattr(runtime, "_github_issue_event_pages", forbidden_events)

    decision = classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )
    assert decision.disposition == "AUTHORIZE"
    assert decision.preactivation_candidate_ids == (168, 169)
    assert decision.selected_issue_id == 168
    assert decision.selected_routing == ("lead", "propose-change")


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


def test_closed_terminal_routing_debt_is_selected_for_cleanup_before_open_formal() -> None:
    decision = classify_dispatch(
        snapshot(
            issue(
                90,
                "archived",
                ("lead", "finalize-archive"),
                state="closed",
                terminal="terminal-history",
            ),
            issue(
                133,
                "enforce-runtime-dispatch-preconditions",
                ("reviewer", "review-implementation"),
            ),
        )
    )
    assert decision.formal_issue_ids == (133,)
    assert decision.selected_issue_id == 90
    assert decision.selected_routing == ("lead", "resolve-question")
    assert decision.selected_debt_disposition == "terminal-cleanup"


def test_closed_finalize_archive_without_completion_fails_closed() -> None:
    decision = classify_dispatch(
        snapshot(
            issue(
                90,
                "archiving",
                ("lead", "finalize-archive"),
                state="closed",
                recovery="indeterminate",
            )
        )
    )
    assert decision.disposition == "FAIL_CLOSED"


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


def test_slice2_runtime_exposes_activation_prewrite_authorization() -> None:
    assert hasattr(workflow_dispatch, "activation_prewrite_authorized")


def test_slice2_runtime_exposes_activation_postwrite_acceptance() -> None:
    assert hasattr(workflow_dispatch, "activation_postwrite_accepted")


def test_shared_governance_points_to_executable_dispatch_ssot() -> None:
    text = " ".join(AGENTS.read_text(encoding="utf-8").split())
    for required in (
        "repository-owned executable dispatch is the only normal-selection authority",
        "authoritative current GitHub observations",
        "observable enumeration/provenance completeness",
        "`AUTHORIZE`, `NO_WORK`, or `FAIL_CLOSED`",
        "A partial enumeration is never proof of zero formal WIP",
        "Detailed candidate construction",
        "production executable code and regression tests",
    ):
        assert required in text
    assert "complete repository-wide durable Issue snapshot" not in text


def test_parked_or_reset_work_restarts_from_current_main_not_old_readiness() -> None:
    governance = " ".join(AGENTS.read_text(encoding="utf-8").split())
    orientation = " ".join(MIGRATION.read_text(encoding="utf-8").split())
    assert "Previous conversation memory is never required for correctness" in governance
    assert "execute fresh production dispatch from resulting durable state" in governance
    for required in (
        "parked/reset work",
        "then-current `main`",
        "Former PASS/readiness evidence remains historical evidence only",
        "fresh repository-wide reconstruction",
        "not a second recovery or dispatch rule",
    ):
        assert required in orientation
