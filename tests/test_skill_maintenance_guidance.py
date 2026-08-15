from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"


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
    guidance = _text(AGENTS / "skills/skill-maintenance.md")

    assert "progressive disclosure" in guidance
    assert "conditionally needed" in guidance
    assert "genuine cross-Skill reuse" in guidance
    assert "External mutable" in guidance
    assert "MUST NOT become runtime authority" in guidance
    assert "agents/AGENTS.md" in guidance
    assert "agents/roles/*" in guidance
    assert "hypothetical future reuse" in guidance


def test_skill_maintenance_resource_has_demonstrated_cross_role_reuse() -> None:
    for role in ("lead.md", "executor.md", "reviewer.md"):
        assert "agents/skills/skill-maintenance.md" in _text(AGENTS / "roles" / role)


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
