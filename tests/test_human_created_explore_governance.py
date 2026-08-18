from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"
README = ROOT / "README.md"


def test_shared_governance_owns_human_created_explore_alternative() -> None:
    shared = AGENTS.read_text()

    assert "creation-bound Human Explore admission" in shared
    assert "`Admission: Lead / explore-change`" in shared
    assert "`Change: unset`" in shared
    assert "raw Issue creation provenance" in shared
    assert "performed_via_github_app == null" in shared
    assert "routing remains routing state rather than Human authority" in shared
    assert "general provenance-bound Human decision/approval predicate" in shared


def test_explore_skill_consumes_but_does_not_redefine_shared_authority() -> None:
    explore = EXPLORE.read_text()

    assert "creation-bound Human Explore admission alternative" in explore
    assert "shared governance" in explore
    assert "general provenance-bound Human decision path" in explore
    assert "direct-to-Propose" in explore


def test_human_facing_intake_guidance_exposes_exact_declaration_only_as_orientation() -> None:
    readme = README.read_text()

    assert "Human-created Formal Explore intake" in readme
    assert "Admission: Lead / explore-change\nChange: unset" in readme
    assert "agents/AGENTS.md" in readme
    assert "does not redefine" in readme


def test_creation_shortcut_is_not_presented_as_direct_propose_or_later_authority() -> None:
    shared = AGENTS.read_text()

    assert "issue:<issue-number>:admission:lead:propose-change" in shared
    assert "Human direct-Propose admission" in shared
    assert "creation-bound" in shared
    assert "HUMAN_DECISION_REQUIRED" in shared
