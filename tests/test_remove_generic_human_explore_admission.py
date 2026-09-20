from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from investment_strategy import human_authority
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    acquire_dispatch_preflight,
)
from investment_strategy.workflow_dispatch import (
    Action as WorkflowAction,
)
from investment_strategy.workflow_dispatch import (
    DispatchDecision,
    Role,
    Routing,
    classify_dispatch,
)

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


def test_shared_projection_names_source_decision_not_physical_writer() -> None:
    shared = _governance()

    assert (
        "Materialization authority follows the qualified source decision, not the physical writer."
        in shared
    )
    assert (
        "Agent-authored advisory text and an Agent-created ticket cannot self-authorize "
        "additional work." not in shared
    )


def _current_issue(
    number: int,
    action: WorkflowAction | None,
    *,
    change: str = "source-decision-explore-materialization",
    order: int = 1,
) -> GitHubIssueObservation:
    routing: Routing | None
    if action is None:
        routing = None
    else:
        role: Role = "reviewer"
        if not action.startswith("review-"):
            role = "executor" if action.startswith(("implement", "merge")) else "lead"
        routing = (role, action)
    return GitHubIssueObservation(
        issue_number=number,
        change=change,
        routing=routing,
        state="open",
        created_order=order,
        authoritative=True,
    )


def _dispatch(issues: tuple[GitHubIssueObservation, ...]) -> DispatchDecision:
    return classify_dispatch(
        acquire_dispatch_preflight(
            observations=issues,
            source_total_count=len(issues),
            incomplete_results=False,
            exhausted=True,
        )
    )


def test_materialized_explore_dispatch_is_origin_neutral() -> None:
    decision = _dispatch((_current_issue(234, "explore-change", change="unset"),))

    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 234
    assert decision.selected_routing == ("lead", "explore-change")
    assert not hasattr(GitHubIssueObservation, "origin")
    assert not hasattr(GitHubIssueObservation, "writer")


def test_materialized_explore_does_not_bypass_formal_wip_ordering() -> None:
    decision = _dispatch(
        (
            _current_issue(234, "explore-change", change="unset", order=1),
            _current_issue(229, "implement-change", change="formal-change", order=2),
        )
    )

    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 229
    assert decision.selected_routing == ("executor", "implement-change")


def test_unrouted_agent_recommendation_cannot_create_queue_authority() -> None:
    decision = _dispatch((_current_issue(999, None, change="unset"),))

    assert decision.disposition == "NO_WORK"
    assert decision.selected_issue_id is None


def test_connector_materialization_cannot_satisfy_human_reserved_authority() -> None:
    decision_ref = human_authority.escalation_response_ref(234)
    timestamp = datetime(2026, 9, 20, 19, 0, tzinfo=UTC)
    connector_comment = human_authority.DecisionComment(
        id=1,
        created_at=timestamp,
        updated_at=timestamp,
        author=human_authority.HUMAN_ACTOR,
        body=f"Human-Decision-For: {decision_ref}",
        provenance_available=True,
        performed_via_github_app="github_app",
    )
    connector_event = human_authority.LabelEvent(
        id=2,
        created_at=timestamp,
        actor=human_authority.HUMAN_ACTOR,
        label=human_authority.APPROVAL_LABEL,
        provenance_available=True,
        performed_via_github_app="github_app",
    )

    assert not human_authority.is_human_decision_approved(
        expected_ref=decision_ref,
        approval_label_present=True,
        comments=(connector_comment,),
        label_events=(connector_event,),
    )


def test_slice_three_and_verification_markers_are_durable_before_handoff() -> None:
    tasks = (
        ROOT / "openspec" / "changes" / "source-decision-explore-materialization" / "tasks.md"
    ).read_text(encoding="utf-8")

    for task_id in ("3.1", "3.2", "3.3", "4.1", "4.2", "4.3"):
        assert any(line.startswith(f"- [x] {task_id}") for line in tasks.splitlines())
