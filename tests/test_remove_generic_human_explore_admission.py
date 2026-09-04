from __future__ import annotations

from pathlib import Path

from investment_strategy import human_authority

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"


def _governance() -> str:
    return " ".join(AGENTS.read_text(encoding="utf-8").split())


def test_pre_activation_queue_is_action_only_and_bounded() -> None:
    text = _governance()
    assert "bounded pre-activation Actions" in text
    assert "Formal Change work has priority over pre-activation work" in text
    assert "WIP=1 violation" in text
    assert "Historical role labels" in text


def test_agent_creation_and_explore_stay_non_recursive() -> None:
    lead = " ".join(LEAD.read_text(encoding="utf-8").split())
    explore = " ".join(EXPLORE.read_text(encoding="utf-8").split())
    assert "optional or merely deferred prose creates no routed work" in lead
    assert "Do not recursively create arbitrary routed Issues" in lead
    assert "Do not create arbitrary Issues" in explore


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


def test_human_boundaries_are_not_replaced_by_connector_activity() -> None:
    shared = _governance()
    assert "Connector activity alone is insufficient" in shared
    assert "Reserved Human decisions require" in shared
