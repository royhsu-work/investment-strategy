"""Tests for typed Action application at the durable effect boundary."""

import json

import pytest

from investment_strategy.scheduled_agent_action_model import (
    Action,
    BoundedActionResult,
    ResultKind,
    TypedResult,
)
from investment_strategy.scheduled_agent_effects import (
    EffectBatch,
    StagedEffect,
    apply_effect_batch,
)
from investment_strategy.scheduled_agent_runtime import (
    EnumerationEvidence,
    RepositoryIssueSnapshot,
    WorkerRequest,
)
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    ObservationProvenance,
)


_REVISION = "a" * 40
_CHANGE = "simplify-scheduled-agent-control-plane"


def _source() -> WorkerRequest:
    return WorkerRequest(138, "executor", "implement-change")


def _preflight() -> DispatchPreflight:
    return DispatchPreflight(
        issues=(
            RepositoryIssueSnapshot(
                issue_number=138,
                change=_CHANGE,
                routing=("executor", "implement-change"),
            ),
        ),
        enumeration=EnumerationEvidence(
            observed_count=1,
            source_total_count=1,
            incomplete_results=False,
            exhausted=True,
            observation_provenance=ObservationProvenance.QUALIFIED,
        ),
    )


def _typed_result(
    kind: ResultKind = ResultKind.SPEC_BLOCKER,
    *,
    effects: tuple[StagedEffect, ...] = (),
) -> EffectBatch:
    return EffectBatch(
        source=_source(),
        effects=effects,
        typed_result=BoundedActionResult(
            issue_number=138,
            change=_CHANGE,
            action=Action.IMPLEMENT_CHANGE,
            result=TypedResult(kind, evidence_ref="issuecomment-typed-result"),
        ),
    )


def test_typed_application_derives_routing_effect_and_exits_current_wake() -> None:
    applied: list[StagedEffect] = []

    result = apply_effect_batch(
        _typed_result(),
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: True,
        topology_validator=lambda _request, _effect: pytest.fail(
            "typed successor must use the Action model, not Markdown topology"
        ),
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
    )

    assert result.applied
    assert result.continuation is None
    assert len(applied) == 1
    assert applied[0].derived
    assert json.loads(applied[0].payload_json) == {
        "issue_number": 138,
        "role": "lead",
        "action": "resolve-question",
    }


def test_worker_cannot_submit_a_typed_successor() -> None:
    worker_routing = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "role": "lead",
                "action": "finalize-archive",
            }
        ),
    )
    applied: list[StagedEffect] = []

    result = apply_effect_batch(
        _typed_result(effects=(worker_routing,)),
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: pytest.fail("rejected before effect guard"),
        topology_validator=lambda _request, _effect: pytest.fail("rejected before topology"),
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
    )

    assert not result.applied
    assert result.continuation is None
    assert "worker-routing-effect" in result.reason
    assert applied == []
