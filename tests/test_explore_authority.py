from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_repository_authorized_explore_admission_is_bounded() -> None:
    shared = _normalized(AGENTS)
    lead = _normalized(LEAD)
    explore = _normalized(EXPLORE)

    for required in (
        "canonical MUST/SHALL requirement",
        "required deferred follow-up",
        "project-direction commitment",
        "behavior-preserving maintenance/friction",
        "at most one",
        "Change: unset",
        "intake:approved",
        "independent source",
    ):
        assert required in shared or required in lead or required in explore


def test_agent_authored_work_cannot_self_authorize_more_work() -> None:
    shared = _normalized(AGENTS)
    explore = _normalized(EXPLORE)

    for required in (
        "Agent-authored advisory",
        "Agent-created ticket",
        "recursively",
        "fail closed",
    ):
        assert required in shared or required in explore


def test_readme_has_explicit_project_direction_commitment_surface() -> None:
    readme = _normalized(README)
    shared = _normalized(AGENTS)

    assert "Project direction commitments" in _read(README)
    for required in (
        "prospective",
        "scoped",
        "affirmative",
        "descriptive",
        "deferred",
    ):
        assert required in readme or required in shared


def test_in_envelope_proposal_ready_does_not_require_generic_second_proceed() -> None:
    shared = _normalized(AGENTS)
    explore = _normalized(EXPLORE)

    for required in (
        "authority envelope",
        "PROPOSAL_READY",
        "Lead / propose-change",
        "without a second generic Human proceed",
        "same Issue",
    ):
        assert required in shared or required in explore


def test_new_human_reserved_decisions_still_stop_explore() -> None:
    shared = _normalized(AGENTS)
    explore = _normalized(EXPLORE)

    for required in (
        "new product/project direction",
        "material scope",
        "risk acceptance",
        "security/privacy/cost/operational",
        "HUMAN_DECISION_REQUIRED",
    ):
        assert required in shared or required in explore


def test_idle_discovery_is_non_disruptive_and_deduplicated() -> None:
    shared = _normalized(AGENTS)
    lead = _normalized(LEAD)

    for required in (
        "already eligible pre-activation work",
        "deduplicate",
        "at most one candidate",
        "no repository noise",
        "Rule-of-Three",
        "single-instance structural hazard",
    ):
        assert required in shared or required in lead
