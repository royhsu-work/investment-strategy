"""Contract coverage for OpenSpec traceability responsibility ownership."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_lead_declares_skill_traceability_and_reviewer_owns_gate() -> None:
    lead = _normalized(ROOT / "agents/skills/openspec-change/SKILL.md")
    reviewer = _normalized(ROOT / "agents/skills/openspec-review/SKILL.md")
    assert "Skill maintenance traceability" in lead
    assert "Lead owns" in lead
    assert "materially affected Skills" in lead
    assert "independent Reviewer / review-openspec" in lead
    assert "Skill maintenance traceability" in reviewer
    assert "undeclared material Skill" in reviewer
    assert "Formatting" in reviewer


def test_reviewer_retains_reverse_first_semantic_gate() -> None:
    reviewer = _normalized(ROOT / "agents/roles/reviewer.md")
    skill = _normalized(ROOT / "agents/skills/openspec-review/SKILL.md")
    assert "Reviewer owns independent gate decisions" in reviewer
    assert "reverse-first" in skill
    assert "tasks -> design -> specs -> proposal" in skill
    assert "proposal -> specs -> design -> tasks" in skill
    assert "Both directions must be complete before PASS" in skill
    assert "FINDINGS" in skill


def test_readme_orients_to_traceability_without_copying_review_protocol() -> None:
    readme = _normalized(ROOT / "README.md")
    assert "OpenSpec authoring conventions" in readme
    assert "openspec/config.yaml" in readme
    assert "review-implementation" in readme
    assert "Detailed semantics belong" in readme
    assert "reverse-first" not in readme


def test_executor_does_not_claim_semantic_traceability_review() -> None:
    implementation = _normalized(ROOT / "agents/skills/implementation/SKILL.md")
    assert "Executor does not perform semantic bidirectional OpenSpec review" in implementation
    assert "material semantic correction" in implementation
    assert "Lead" in implementation


def test_existing_openspec_authoring_and_mechanical_rules_remain_intact() -> None:
    config = _normalized(ROOT / "openspec/config.yaml")
    for required in (
        "Trace major design decisions to requirements",
        "Trace Behavior/Product tasks through proposal, capability specs, and design",
        "Before declaring a change complete, run strict OpenSpec validation",
    ):
        assert required in config
