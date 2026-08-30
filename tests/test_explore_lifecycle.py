from __future__ import annotations

import json
from pathlib import Path

import pytest

from investment_strategy.scheduled_agent_effects import (
    parse_effect_batch,
    topology_allows_successor,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RepositoryIssueSnapshot,
    classify_dispatch,
)

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
WORKFLOW = ROOT / "agents" / "workflow.md"
MESSAGES = ROOT / "agents" / "templates" / "messages.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"
CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
REVIEW = ROOT / "agents" / "skills" / "openspec-review" / "SKILL.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _propose_result(
    *,
    disposition: str | None,
    requested_effects: list[dict[str, str]] | None = None,
) -> str:
    return json.dumps(
        {
            "issue_number": 175,
            "role": "lead",
            "action": "propose-change",
            "explore_disposition": None,
            "propose_disposition": disposition,
            "result_content": "researchable material evidence gap",
            "requested_effects": requested_effects or [],
        }
    )


def _complete_preactivation(
    *issues: RepositoryIssueSnapshot,
) -> DispatchPreflight:
    return DispatchPreflight(
        issues=issues,
        enumeration=EnumerationEvidence(
            observed_count=len(issues),
            source_total_count=len(issues),
            incomplete_results=False,
            exhausted=True,
            observation_provenance=ObservationProvenance.QUALIFIED,
        ),
    )


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
        "normal successful continuation",
        "durable evidence-backed structured `PROPOSAL_READY`",
    ):
        assert required in explore
    assert "direct-to-Propose" not in explore


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


def test_explore_and_propose_share_current_routing_preactivation_contract() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "combined pre-activation candidate contract",
        "coherent routed Explore",
        "coherent routed Propose",
        "earliest GitHub `created_at` then lower Issue number ordering",
        "Current routing debt is handled before intake",
        "A formal workflow otherwise wins over intake",
    ):
        assert required in shared
    assert "executable-approved direct-Propose" not in shared


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


def test_researchable_propose_gap_derives_same_issue_explore_correction() -> None:
    source = WorkerRequest(175, "lead", "propose-change")
    batch = parse_effect_batch(_propose_result(disposition="RESEARCH_REQUIRED"), source)

    assert batch.propose_disposition == "RESEARCH_REQUIRED"
    assert len(batch.effects) == 1
    assert batch.effects[0].kind == "routing-transition"
    assert json.loads(batch.effects[0].payload_json) == {
        "issue_number": 175,
        "role": "lead",
        "action": "explore-change",
    }


def test_worker_cannot_choose_propose_to_explore_correction_without_structured_result() -> None:
    source = WorkerRequest(175, "lead", "propose-change")
    worker_routing = {
        "kind": "routing-transition",
        "payload_json": json.dumps(
            {"issue_number": 175, "role": "lead", "action": "explore-change"}
        ),
    }

    with pytest.raises(ValueError, match="worker-chosen Propose correction"):
        parse_effect_batch(
            _propose_result(disposition=None, requested_effects=[worker_routing]),
            source,
        )


def test_explore_contract_requires_reconstructable_material_claim_source_chain() -> None:
    explore = _normalized(EXPLORE)
    for required in (
        "material claim",
        "supporting source/evidence",
        "source fact/evidence",
        "interpretation/inference",
        "unresolved question",
        "cannot establish `PROPOSAL_READY`",
    ):
        assert required in explore


def test_explore_action_result_preserves_claim_sources_without_routing_prose_control() -> None:
    messages = _normalized(MESSAGES)
    for required in (
        "every material conclusion",
        "supporting source/evidence",
        "source fact/evidence",
        "Lead interpretation/inference",
        "unresolved questions",
        "bounded structured Explore disposition",
        "does not encode a worker-chosen successor",
        "repository-owned application derives and observes that effect",
        "without turning narrative routing prose into control state",
    ):
        assert required in messages


def test_propose_and_reviewer_independently_verify_source_evidence_before_formalization() -> None:
    change = _normalized(CHANGE)
    review = _normalized(REVIEW)
    for required in (
        "independently",
        "source/evidence",
        "feasibility",
        "same Issue",
        "explore-change",
        "Change: unset",
    ):
        assert required in change
    for required in (
        "independently",
        "source/evidence",
        "supported by",
        "feasibility",
        "FINDINGS",
    ):
        assert required in review


def test_workflow_topology_contains_pre_activation_propose_research_correction() -> None:
    workflow_text = _read(WORKFLOW)
    workflow = " ".join(workflow_text.split())
    assert "pre-activation" in workflow
    assert "`Lead / propose-change`" in workflow
    assert "`Lead / explore-change`" in workflow
    assert "researchable" in workflow
    assert "Change: unset" in workflow

    source = WorkerRequest(175, "lead", "propose-change")
    batch = parse_effect_batch(_propose_result(disposition="RESEARCH_REQUIRED"), source)
    assert topology_allows_successor(workflow_text, source, batch.effects[0])


def test_restored_current_propose_reenters_ordinary_fifo_without_migration_token() -> None:
    parked = RepositoryIssueSnapshot(
        issue_number=168,
        change="unset",
        routing=None,
        created_order=1,
    )
    later_explore = RepositoryIssueSnapshot(
        issue_number=169,
        change="unset",
        routing=("lead", "explore-change"),
        created_order=2,
    )
    before_restore = classify_dispatch(_complete_preactivation(parked, later_explore))
    assert before_restore.selected_issue_id == 169

    restored = RepositoryIssueSnapshot(
        issue_number=168,
        change="unset",
        routing=("lead", "propose-change"),
        created_order=1,
    )
    after_restore = classify_dispatch(_complete_preactivation(restored, later_explore))
    assert after_restore.preactivation_candidate_ids == (168, 169)
    assert after_restore.selected_issue_id == 168
    assert after_restore.selected_routing == ("lead", "propose-change")

    earlier_explore = RepositoryIssueSnapshot(
        issue_number=167,
        change="unset",
        routing=("lead", "explore-change"),
        created_order=0,
    )
    ordinary_fifo = classify_dispatch(
        _complete_preactivation(earlier_explore, restored, later_explore)
    )
    assert ordinary_fifo.preactivation_candidate_ids == (167, 168, 169)
    assert ordinary_fifo.selected_issue_id == 167
    assert ordinary_fifo.selected_routing == ("lead", "explore-change")
