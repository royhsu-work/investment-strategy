from __future__ import annotations

from pathlib import Path

from investment_strategy import human_authority

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"


def _governance() -> str:
    return " ".join(AGENTS.read_text(encoding="utf-8").split())


def test_routed_formal_explore_is_origin_neutral_for_queue_eligibility() -> None:
    text = _governance()
    assert "ordinary routed Explore eligibility does not require Human approval" in text
    assert "open `Lead / explore-change + Change: unset`" in text
    assert "origin does not control dispatcher eligibility" in text


def test_formal_wip_and_stable_order_still_dominate_pre_activation_explore() -> None:
    text = _governance()
    assert "A formal workflow always wins over intake" in text
    assert "earliest GitHub `created_at` then lower Issue number ordering" in text
    assert "premature-close recovery" in text


def test_direct_propose_human_admission_remains_distinct() -> None:
    text = _governance()
    assert "Human direct-Propose admission" in text
    assert "issue:<issue-number>:admission:lead:propose-change" in text


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
    assert (
        human_authority.decision_ref_for_boundary(
            human_authority.HumanDecisionBoundary.PROPOSE_ADMISSION,
            issue_number=93,
        )
        == "issue:93:admission:lead:propose-change"
    )
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
