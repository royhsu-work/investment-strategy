from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
LOCAL_SKILL_GOVERNANCE = AGENTS / "skills/skill-creator/references/repository-governance.md"


def _text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_project_wide_proportionality_has_one_runtime_reference() -> None:
    proportionality = _text(AGENTS / "proportionality.md")
    config = _text(ROOT / "openspec/config.yaml")

    assert "openspec/specs/repository-governance/spec.md" in proportionality
    assert "reference only" in proportionality
    assert "current requirement, safety property, or demonstrated failure mode" in config
    assert "current change's relevant scope" in config


def test_skill_maintenance_uses_progressive_disclosure_without_external_authority() -> None:
    guidance = _text(LOCAL_SKILL_GOVERNANCE)

    assert "only when the current governed action materially" in guidance
    assert "progressive disclosure" in guidance
    assert "demonstrated cross-Skill reuse" in guidance
    assert "External or mutable" in guidance
    assert "never Scheduled-Agent runtime authority by itself" in guidance
    assert "agents/AGENTS.md" in guidance
    assert "agents/roles/*" in guidance
    assert "hypothetical future reuse" in guidance
    assert not (AGENTS / "skills/skill-maintenance.md").exists()


def test_skill_maintenance_resource_has_demonstrated_cross_role_reuse() -> None:
    expected = "agents/skills/skill-creator/references/repository-governance.md"
    legacy = "agents/skills/skill-maintenance.md"
    for role in ("lead.md", "executor.md", "reviewer.md"):
        text = _text(AGENTS / "roles" / role)
        assert expected in text
        assert legacy not in text


def test_lead_idle_advisory_can_recommend_skill_maintenance_without_mutation_authority() -> None:
    lead = _text(AGENTS / "roles/lead.md")

    for phrase in (
        "repeated action mistakes",
        "missing or obsolete Skill guidance",
        "unnecessary Skill complexity",
        "duplicated Skill guidance",
    ):
        assert phrase in lead

    assert "recommendation remains advisory" in lead
    assert "independent repository-authorized admission evidence" in lead
    assert "Advisory-only findings remain non-routing" not in lead
