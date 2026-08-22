"""Fresh effect-application and continuation regressions for #133 Slice 4C."""

from __future__ import annotations

from investment_strategy.scheduled_agent_effects import (
    EffectBatch,
    StagedEffect,
    apply_effect_batch,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RepositoryIssueSnapshot,
)


def _preflight(*, role: str = "executor", action: str = "implement-change") -> DispatchPreflight:
    return DispatchPreflight(
        issues=(
            RepositoryIssueSnapshot(
                issue_number=133,
                change="enforce-runtime-dispatch-preconditions",
                routing=(role, action),  # type: ignore[arg-type]
                created_order=1,
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


def _batch(effect: StagedEffect | None = None) -> EffectBatch:
    return EffectBatch(
        source=WorkerRequest(issue_number=133, role="executor", action="implement-change"),
        effects=((effect or StagedEffect(kind="issue-comment", payload_json="{}")),),
    )


def test_apply_reauthorizes_same_source_before_any_effect() -> None:
    applied: list[StagedEffect] = []
    result = apply_effect_batch(
        _batch(),
        fresh_preflight=lambda: _preflight(),
        effect_guard=lambda _effect: True,
        topology_validator=lambda _source, _effect: True,
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
    )
    assert result.applied is True
    assert len(applied) == 1


def test_stale_source_rejects_whole_batch_without_effect() -> None:
    applied: list[StagedEffect] = []
    result = apply_effect_batch(
        _batch(),
        fresh_preflight=lambda: _preflight(role="reviewer", action="review-implementation"),
        effect_guard=lambda _effect: True,
        topology_validator=lambda _source, _effect: True,
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
    )
    assert result.applied is False
    assert result.reason == "source dispatch is stale"
    assert applied == []


def test_effect_specific_guard_rejects_whole_batch() -> None:
    applied: list[StagedEffect] = []
    result = apply_effect_batch(
        _batch(),
        fresh_preflight=lambda: _preflight(),
        effect_guard=lambda _effect: False,
        topology_validator=lambda _source, _effect: True,
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
    )
    assert result.applied is False
    assert result.reason == "effect precondition rejected"
    assert applied == []


def test_illegal_routing_successor_is_rejected_before_apply() -> None:
    effect = StagedEffect(
        kind="routing-transition",
        payload_json='{"role":"lead","action":"finalize-change"}',
    )
    result = apply_effect_batch(
        _batch(effect),
        fresh_preflight=lambda: _preflight(),
        effect_guard=lambda _effect: True,
        topology_validator=lambda _source, _effect: False,
        apply_effect=lambda _effect: None,
        observe_postcondition=lambda _effect: True,
    )
    assert result.applied is False
    assert result.reason == "routing successor rejected"


def test_postcondition_failure_fails_closed_after_effect() -> None:
    result = apply_effect_batch(
        _batch(),
        fresh_preflight=lambda: _preflight(),
        effect_guard=lambda _effect: True,
        topology_validator=lambda _source, _effect: True,
        apply_effect=lambda _effect: None,
        observe_postcondition=lambda _effect: False,
    )
    assert result.applied is False
    assert result.reason == "durable postcondition not observed"


def test_same_role_continuation_requires_fresh_redispatch() -> None:
    states = iter((_preflight(), _preflight(role="executor", action="merge-pr")))
    result = apply_effect_batch(
        _batch(),
        fresh_preflight=lambda: next(states),
        effect_guard=lambda _effect: True,
        topology_validator=lambda _source, _effect: True,
        apply_effect=lambda _effect: None,
        observe_postcondition=lambda _effect: True,
    )
    assert result.continuation == WorkerRequest(
        issue_number=133,
        role="executor",
        action="merge-pr",
    )


def test_cross_role_continuation_is_new_machine_selected_identity() -> None:
    states = iter((_preflight(), _preflight(role="reviewer", action="review-implementation")))
    result = apply_effect_batch(
        _batch(),
        fresh_preflight=lambda: next(states),
        effect_guard=lambda _effect: True,
        topology_validator=lambda _source, _effect: True,
        apply_effect=lambda _effect: None,
        observe_postcondition=lambda _effect: True,
    )
    assert result.continuation == WorkerRequest(
        issue_number=133,
        role="reviewer",
        action="review-implementation",
    )
