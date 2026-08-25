from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_explore_is_tenth_lead_action_with_one_owned_skill() -> None:
    shared = _normalized(AGENTS)
    lead = _normalized(LEAD)
    assert "Exactly ten normal actions are supported" in shared
    action_row = "| Lead | `explore-change` | `agents/skills/openspec-explore/SKILL.md` |"
    assert action_row in _read(AGENTS)
    assert "Legal tuples are exactly the ten role/action pairs" in shared
    assert "`explore-change` uses `agents/skills/openspec-explore/SKILL.md`" in lead
    assert EXPLORE.is_file()


def test_explore_is_optional_and_cannot_create_formal_change_or_code() -> None:
    explore = _normalized(EXPLORE)
    for required in (
        "optional pre-Propose",
        "problem before solution",
        "Change: unset",
        "MUST NOT create `openspec/changes/`",
        "MUST NOT modify implementation code",
        "direct-to-Propose",
    ):
        assert required in explore


def test_explore_uses_decision_complete_outcomes_and_human_boundary() -> None:
    explore = _normalized(EXPLORE)
    for required in (
        "decision-complete",
        "PROPOSAL_READY",
        "NO_CHANGE_REQUIRED",
        "NO_GO",
        "HUMAN_DECISION_REQUIRED",
        "SPECIFICATION_BLOCKED",
        "does not persist a Change id",
        "Human intent",
    ):
        assert required in explore


def test_explore_and_direct_propose_share_executable_preactivation_contract() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "combined pre-activation candidate contract",
        "coherent routed Explore",
        "executable-approved direct-Propose",
        "earliest GitHub `created_at` then lower Issue number ordering",
        "Current routing debt is handled before intake",
        "A formal workflow otherwise wins over intake",
    ):
        assert required in shared


def test_explore_has_no_research_state_machine_or_review_gate() -> None:
    explore = _normalized(EXPLORE)
    for forbidden in (
        "status:exploring",
        "review-explore",
        "completeness score",
        "research database",
        "hidden memory",
    ):
        absent_state = f"does not require `{forbidden}`"
        absent_mechanism = f"MUST NOT introduce `{forbidden}`"
        assert absent_state in explore or absent_mechanism in explore


def test_explore_terminal_results_can_close_without_fake_change() -> None:
    lead = _normalized(LEAD)
    explore = _normalized(EXPLORE)
    assert "terminal research Issue" in lead
    assert "NO_CHANGE_REQUIRED" in explore
    assert "NO_GO" in explore
    assert "without creating a fake OpenSpec Change" in explore
