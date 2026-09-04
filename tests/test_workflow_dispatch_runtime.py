"""Regression coverage for the executable Action dispatch boundary."""

from __future__ import annotations

from pathlib import Path

from investment_strategy.scheduled_agent_action_model import Action
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    acquire_dispatch_preflight,
)
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    action_entry_authorized,
    action_model_shadow,
    activation_postwrite_accepted,
    classify_dispatch,
)


def _preflight(
    observations: tuple[GitHubIssueObservation, ...],
    *,
    source_total_count: int | None = None,
    incomplete_results: bool = False,
    exhausted: bool = True,
    human_authorized: bool = True,
) -> DispatchPreflight:
    return acquire_dispatch_preflight(
        observations=observations,
        source_total_count=(
            len(observations) if source_total_count is None else source_total_count
        ),
        incomplete_results=incomplete_results,
        exhausted=exhausted,
        human_authorized=human_authorized,
    )


def _issue(
    number: int,
    action: str | None,
    *,
    change: str = "simplify-scheduled-agent-control-plane",
    order: int = 1,
) -> GitHubIssueObservation:
    role = None
    if action is not None:
        role = (
            "reviewer"
            if action.startswith("review-")
            else ("executor" if action.startswith(("implement", "merge")) else "lead")
        )
    return GitHubIssueObservation(
        issue_number=number,
        change=change,
        routing=None if action is None else (role, action),
        state="open",
        created_order=order,
        authoritative=True,
    )


def test_action_only_dispatch_selects_exactly_one_formal_work_item() -> None:
    preflight = _preflight((_issue(138, "implement-change"),))
    decision = classify_dispatch(preflight)
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 138
    assert decision.selected_routing == ("executor", "implement-change")
    assert decision.formal_issue_ids == (138,)
    assert action_entry_authorized(preflight, 138, ("executor", "implement-change"))


def test_wip_and_incomplete_observations_fail_closed() -> None:
    two = _preflight((_issue(138, "implement-change"), _issue(139, "review-implementation")))
    assert classify_dispatch(two).reason == "wip-more-than-one"

    incomplete = _preflight(
        (_issue(138, "implement-change"),),
        source_total_count=None,
        incomplete_results=True,
        exhausted=False,
    )
    assert classify_dispatch(incomplete).disposition == "FAIL_CLOSED"
    assert classify_dispatch(incomplete).completeness == "INDETERMINATE"


def test_shadow_is_a_pure_comparison_of_the_same_executable_model() -> None:
    preflight = _preflight((_issue(138, "review-openspec"),))
    comparison = action_model_shadow(preflight)
    assert comparison.matches
    assert comparison.expected.action is Action.REVIEW_OPENSPEC


def test_activation_postcondition_requires_exact_change_and_action() -> None:
    preflight = _preflight(
        (
            _issue(
                138,
                "propose-change",
                change="simplify-scheduled-agent-control-plane",
            ),
        )
    )
    assert activation_postwrite_accepted(
        preflight,
        issue_number=138,
        expected_change="simplify-scheduled-agent-control-plane",
    )
    assert not activation_postwrite_accepted(
        preflight,
        issue_number=138,
        expected_change="other-change",
    )


def test_generated_governance_projection_has_no_second_runtime_dag() -> None:
    workflow = Path("agents/workflow.md").read_text(encoding="utf-8")
    assert "Scheduled-Dispatch-Mode: workflow-dynamic" in workflow
    start_marker = "<!-- BEGIN GENERATED ACTION MODEL -->"
    end_marker = "<!-- END GENERATED ACTION MODEL -->"
    start = workflow.index(start_marker)
    end = workflow.index(end_marker, start) + len(end_marker)
    assert workflow[start : end + 1].endswith("\n")
    assert (
        "parse"
        not in Path("src/investment_strategy/workflow_dispatch.py")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "HANDOFF" not in workflow
