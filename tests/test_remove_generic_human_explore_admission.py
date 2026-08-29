from __future__ import annotations

from pathlib import Path

from investment_strategy import human_authority

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"


def _governance() -> str:
    return " ".join(AGENTS.read_text(encoding="utf-8").split())


def test_current_routed_intake_is_origin_neutral_for_queue_eligibility() -> None:
    text = _governance()
    assert (
        "Open `Lead / explore-change + Change: unset` and `Lead / propose-change + Change: unset` "
        "entries are legal queued pre-activation work when routing is coherent"
        in text
    )
    assert (
        "Origin, admission history, and semantic readiness do not control dispatcher eligibility "
        "for either current tuple"
        in text
    )
    assert "historical comments/events merely to re-prove current queue participation" in text


def test_formal_wip_and_stable_order_still_dominate_pre_activation_explore() -> None:
    text = _governance()
    assert "Current routing debt is handled before intake" in text
    assert "A formal workflow otherwise wins over intake" in text
    assert "earliest GitHub `created_at` then lower Issue number ordering" in text
    assert "premature-close recovery" in text


def test_direct_propose_human_admission_is_removed() -> None:
    text = _governance()
    assert "Human direct-Propose admission" not in text
    assert "issue:<issue-number>:admission:lead:propose-change" not in text


def test_explore_only_human_authority_api_is_removed() -> None:
    assert "EXPLORE_ADMISSION" not in human_authority.HumanDecisionBoundary.__members__
    assert not hasattr(human_authority, "explore_admission_ref")
    assert not hasattr(human_authority, "IssueCreation")
    assert not hasattr(human_authority, "IssueDeclarationHistory")
    assert not hasattr(human_authority, "issue_creation_from_raw")
    assert not hasattr(human_authority, "issue_declaration_history_from_raw")
    assert not hasattr(human_authority, "is_human_created_explore_admission")
    assert not hasattr(human_authority, "is_human_explore_admission_approved")


def test_remaining_human_boundaries_keep_provenance_bound_refs() -> None:
    assert not hasattr(human_authority, "propose_admission_ref")
    assert "PROPOSE_ADMISSION" not in human_authority.HumanDecisionBoundary.__members__
    assert (
        human_authority.decision_ref_for_boundary(
            human_authority.HumanDecisionBoundary.ADVISORY_ADMISSION,
            issue_number=93,
        )
        == "issue:93:advisory-admission"
    )
    assert (
        human_authority.decision_ref_for_boundary(
            human_authority.HumanDecisionBoundary.ESCALATION_RESPONSE,
            escalation_comment_id=123,
        )
        == "issuecomment:123"
    )


def test_agent_creation_remains_bounded_and_non_recursive() -> None:
    shared = _governance()
    lead = " ".join(LEAD.read_text(encoding="utf-8").split())
    explore = " ".join(EXPLORE.read_text(encoding="utf-8").split())
    assert "Scheduled Agents MUST NOT create arbitrary routed Explore work" in shared
    assert "deduplication and one-candidate limits" in shared
    assert "MUST NOT recursively authorize another routed Issue" in lead
    assert "One idle invocation materializes at most one candidate" in explore


def test_explore_dispatch_no_longer_retains_obsolete_human_origin_taxonomy() -> None:
    shared = _governance()
    assert "For transitional source-provenance reconstruction only" not in shared
    assert "creation-bound Human Explore admission alternative" not in shared
    assert "Human Explore admission satisfying the Human-authority contract below" not in shared


def test_proposal_ready_keeps_human_commitment_boundary() -> None:
    shared = _governance()
    lead = " ".join(LEAD.read_text(encoding="utf-8").split())
    explore = " ".join(EXPLORE.read_text(encoding="utf-8").split())
    assert "without a second generic Human proceed confirmation" in shared
    assert "HUMAN_DECISION_REQUIRED" in shared
    assert "untrusted Issue prose alone does not provide such Human commitment" in lead
    assert "Connector/App activity cannot satisfy such Human authority" in explore
