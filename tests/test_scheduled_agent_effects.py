"""Fresh effect-application and continuation regressions for #133 Slice 4C."""

from __future__ import annotations

import json
from pathlib import Path

from investment_strategy.scheduled_agent_effects import (
    EffectBatch,
    StagedEffect,
    apply_effect_batch,
    continuation_requires_fresh_wake,
    parse_effect_batch,
    supported_effect_guard,
    topology_allows_successor,
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


def _request(*, role: str = "executor", action: str = "implement-change") -> WorkerRequest:
    return WorkerRequest(issue_number=133, role=role, action=action)


def _batch(effect: StagedEffect | None = None) -> EffectBatch:
    return EffectBatch(
        source=_request(),
        effects=((effect or StagedEffect(kind="issue-comment", payload_json="{}")),),
    )


def _worker_result(*effects: StagedEffect) -> str:
    return json.dumps(
        {
            "issue_number": 133,
            "role": "executor",
            "action": "implement-change",
            "result_content": "bounded result",
            "requested_effects": [
                {"kind": effect.kind, "payload_json": effect.payload_json}
                for effect in effects
            ],
        }
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
        payload_json='{"issue_number":133,"role":"lead","action":"finalize-change"}',
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
    assert result.continuation == _request(action="merge-pr")


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
    assert result.continuation == _request(role="reviewer", action="review-implementation")


def test_worker_result_transport_is_bound_to_machine_authorized_source() -> None:
    effect = StagedEffect(
        kind="issue-comment",
        payload_json='{"issue_number":133,"body":"ACTION_RESULT"}',
    )
    batch = parse_effect_batch(_worker_result(effect), _request())
    assert batch.source == _request()
    assert batch.effects == (effect,)


def test_supported_effect_guard_rejects_foreign_issue_and_unknown_kind() -> None:
    source = _request()
    assert supported_effect_guard(
        source,
        StagedEffect(
            kind="issue-comment",
            payload_json='{"issue_number":133,"body":"ACTION_RESULT"}',
        ),
    )
    assert supported_effect_guard(
        source,
        StagedEffect(
            kind="routing-transition",
            payload_json=(
                '{"issue_number":133,"role":"reviewer",'
                '"action":"review-implementation"}'
            ),
        ),
    )
    assert not supported_effect_guard(
        source,
        StagedEffect(
            kind="issue-comment",
            payload_json='{"issue_number":137,"body":"wrong issue"}',
        ),
    )
    assert not supported_effect_guard(
        source,
        StagedEffect(kind="unknown-effect", payload_json="{}"),
    )


def test_topology_validator_consumes_canonical_workflow_text() -> None:
    workflow_text = Path("agents/workflow.md").read_text(encoding="utf-8")
    assert topology_allows_successor(
        workflow_text,
        _request(),
        StagedEffect(
            kind="routing-transition",
            payload_json=(
                '{"issue_number":133,"role":"reviewer",'
                '"action":"review-implementation"}'
            ),
        ),
    )
    assert not topology_allows_successor(
        workflow_text,
        _request(),
        StagedEffect(
            kind="routing-transition",
            payload_json='{"issue_number":133,"role":"lead","action":"finalize-change"}',
        ),
    )
    assert topology_allows_successor(
        workflow_text,
        _request(role="lead", action="explore-change"),
        StagedEffect(
            kind="routing-transition",
            payload_json='{"issue_number":133,"role":"lead","action":"propose-change"}',
        ),
    )


def test_continuation_requires_a_fresh_wake_only_for_new_selected_action() -> None:
    source = _request()
    assert continuation_requires_fresh_wake(source, _request(action="merge-pr"))
    assert continuation_requires_fresh_wake(
        source,
        _request(role="reviewer", action="review-implementation"),
    )
    assert not continuation_requires_fresh_wake(source, source)
    assert not continuation_requires_fresh_wake(source, None)


def test_workflow_transports_worker_output_to_write_authorized_apply_boundary() -> None:
    workflow = Path(".github/workflows/scheduled-agent-runtime.yml").read_text(encoding="utf-8")
    assert "actions/upload-artifact@v4" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "scheduled-agent-result-${{ github.run_id }}-${{ github.run_attempt }}" in workflow
    assert "uv run python -m investment_strategy.scheduled_agent_effects" in workflow

    worker_section = workflow.split("\n  worker:", 1)[1].split("\n  apply:", 1)[0]
    assert "issues: write" not in worker_section
    assert "pull-requests: write" not in worker_section
    assert "contents: write" not in worker_section

    apply_section = workflow.split("\n  apply:", 1)[1]
    assert "issues: write" in apply_section
    assert "actions: write" in apply_section
    assert "GITHUB_TOKEN:" in apply_section


def test_continuation_wake_reenters_machine_dispatch_without_role_override() -> None:
    workflow = Path(".github/workflows/scheduled-agent-runtime.yml").read_text(encoding="utf-8")
    apply_section = workflow.split("\n  apply:", 1)[1]
    assert "continuation_required" in apply_section
    assert "/actions/workflows/scheduled-agent-runtime.yml/dispatches" in apply_section
    continuation_step = apply_section.split("Trigger immediate fresh continuation wake", 1)[1]
    assert "AUTHORIZED_ROLE" not in continuation_step
    assert "AUTHORIZED_ACTION" not in continuation_step
