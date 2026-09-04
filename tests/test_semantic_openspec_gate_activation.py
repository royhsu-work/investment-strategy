"""Current semantic OpenSpec and default-branch activation contracts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split())


def test_mechanical_validation_and_semantic_review_are_distinct() -> None:
    shared = _text("agents/AGENTS.md")
    review = _text("agents/skills/openspec-review/SKILL.md")
    assert "bookkeeping-only OpenSpec revision does not stale" in shared
    assert "Mechanical validation alone does not create semantic acceptance" in shared
    assert "material semantic OpenSpec change" in shared
    assert "semantic baseline B" in review
    assert "material semantic changes in (B, R]" in review
    assert "Successful mechanical OpenSpec validation is not semantic PASS evidence" in review


def test_implementation_completion_uses_action_model_without_same_wake_execution() -> None:
    implementation = _text("agents/skills/implementation/SKILL.md")
    assert "no material semantic OpenSpec change" in implementation
    assert "directly to Reviewer / review-implementation" in implementation
    assert "material semantic OpenSpec change" in implementation
    assert "Lead / resolve-question" in implementation
    assert "Reviewer / review-openspec" in implementation


def test_implementation_and_archive_reviews_require_exact_current_head() -> None:
    for path in (
        "agents/skills/implementation-review/SKILL.md",
        "agents/skills/archive-review/SKILL.md",
    ):
        text = _text(path)
        assert "exact-current-head gate" in text
        assert "bookkeeping exception does not weaken" in text


def test_unmerged_governance_is_not_current_invocation_authority() -> None:
    for path in (
        "agents/AGENTS.md",
        "agents/scheduled-task-migration.md",
        "README.md",
    ):
        text = _text(path)
        assert "default-branch merge is the activation boundary" in text
        assert "unmerged governance PR" in text
        assert "review target/input" in text
        assert "must not govern its own current invocation" in text


def test_pre_activation_evidence_is_historical_not_routing_state() -> None:
    messages = _text("agents/templates/messages.md")
    assert "Action: <action>" in messages
    assert "Role is derived" in messages
    assert "Messages are durable evidence surfaces" in messages
