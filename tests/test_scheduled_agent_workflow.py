"""Repository governance points to one Action-only execution contract."""

from pathlib import Path

from investment_strategy.scheduled_agent_action_model import render_workflow_presentation


def test_workflow_document_is_a_human_projection_of_the_action_model() -> None:
    path = Path("agents/workflow.md")
    workflow = path.read_text(encoding="utf-8")
    assert "Scheduled-Dispatch-Mode: workflow-dynamic" in workflow
    assert "one Action per Scheduled Task wake" in workflow
    assert "Role = role_for(Action)" in workflow
    assert "next_action(current_action, result)" in workflow

    start_marker = "<!-- BEGIN GENERATED ACTION MODEL -->"
    end_marker = "<!-- END GENERATED ACTION MODEL -->"
    start = workflow.index(start_marker)
    end = workflow.index(end_marker, start) + len(end_marker)
    assert workflow[start : end + 1] == render_workflow_presentation()

    for forbidden in (
        "HANDOFF",
        "HANDOFF_COMPLETION_REQUEST",
        "same-role immediate continuation",
        "cross-role wake barrier",
        "response mailbox",
        "Markdown topology parsing",
    ):
        assert forbidden not in workflow
