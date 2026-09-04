"""Static checks for the shared Action-only message contract."""

from pathlib import Path

MESSAGES = Path("agents/templates/messages.md").read_text(encoding="utf-8")


def test_messages_are_evidence_and_result_surfaces_not_control_state() -> None:
    for marker in (
        "ACTION_RESULT",
        "REVIEW_RESULT",
        "SLICE_CHECKPOINT",
        "MERGE_RESULT",
        "HUMAN_DECISION_REQUIRED",
        "EXECUTION_EXCEPTION",
    ):
        assert marker in MESSAGES
    for forbidden in (
        "HANDOFF",
        "HANDOFF_COMPLETION_REQUEST",
        "continuation_required",
        "response mailbox",
        "workflow topology parser",
    ):
        assert forbidden not in MESSAGES


def test_result_templates_carry_action_identity_without_independent_role_state() -> None:
    assert "Action: <action>" in MESSAGES
    assert "Role: <derived role>" in MESSAGES
    assert "next Action" in MESSAGES
    assert "successor" in MESSAGES
