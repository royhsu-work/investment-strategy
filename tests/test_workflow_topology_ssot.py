"""Checks that executable Action topology is the only machine transition source."""

from pathlib import Path

from investment_strategy.scheduled_agent_action_model import (
    ACTION_ROLE,
    TRANSITIONS,
    render_workflow_presentation,
)


def test_workflow_contains_exact_generated_action_projection() -> None:
    workflow = Path("agents/workflow.md").read_text(encoding="utf-8")
    start_marker = "<!-- BEGIN GENERATED ACTION MODEL -->"
    end_marker = "<!-- END GENERATED ACTION MODEL -->"
    start = workflow.index(start_marker)
    end = workflow.index(end_marker, start) + len(end_marker)
    assert workflow[start : end + 1] == render_workflow_presentation()


def test_all_actions_have_derived_roles_and_finite_transitions() -> None:
    assert set(ACTION_ROLE) == set(TRANSITIONS)
    assert "merge-implementation-pr" in {action.value for action in ACTION_ROLE}
    assert "merge-archive-pr" in {action.value for action in ACTION_ROLE}
    assert "merge-pr" not in {action.value for action in ACTION_ROLE}
