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
    shared = _text(AGENTS / "AGENTS.md")

    assert "Skill authoring and maintenance" in shared
    assert "progressive disclosure" in shared
    assert "conditionally needed" in shared
    assert "genuine cross-Skill reuse" in shared
    assert "external mutable" in shared
    assert "MUST NOT become runtime authority" in shared
    assert "agents/AGENTS.md" in shared
    assert "agents/roles/*" in shared


def test_lead_idle_advisory_can_recommend_skill_maintenance_without_mutation_authority() -> None:
    shared = _text(AGENTS / "AGENTS.md")
    lead = _text(AGENTS / "roles/lead.md")

    for phrase in (
        "repeated action mistakes",
        "missing or obsolete Skill guidance",
        "unnecessary Skill complexity",
        "duplicated Skill guidance",
    ):
        assert phrase in shared

    assert "Skill-maintenance recommendation" in shared
    assert "does not grant mutation authority" in shared
    assert "Skill-maintenance opportunities" in lead
    assert "normal Human-admitted OpenSpec lifecycle" in lead
