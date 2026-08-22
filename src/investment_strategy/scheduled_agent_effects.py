"""Fresh reauthorization boundary for Scheduled Agent durable effects."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.workflow_dispatch import DispatchPreflight, classify_dispatch


@dataclass(frozen=True)
class StagedEffect:
    """One invocation-local requested durable effect."""

    kind: str
    payload_json: str


@dataclass(frozen=True)
class EffectBatch:
    """Worker output bound to its original machine-authorized source."""

    source: WorkerRequest
    effects: tuple[StagedEffect, ...]


@dataclass(frozen=True)
class ApplyResult:
    """Application outcome plus optional newly dispatched continuation."""

    applied: bool
    reason: str
    continuation: WorkerRequest | None = None


FreshPreflight = Callable[[], DispatchPreflight]
EffectGuard = Callable[[StagedEffect], bool]
EffectApplier = Callable[[StagedEffect], None]
PostconditionObserver = Callable[[StagedEffect], bool]
TopologyValidator = Callable[[WorkerRequest, StagedEffect], bool]


def _authorized_request(preflight: DispatchPreflight) -> WorkerRequest | None:
    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id is None
        or decision.selected_routing is None
    ):
        return None
    role, action = decision.selected_routing
    return WorkerRequest(decision.selected_issue_id, role, action)


def apply_effect_batch(
    batch: EffectBatch,
    *,
    fresh_preflight: FreshPreflight,
    effect_guard: EffectGuard,
    topology_validator: TopologyValidator,
    apply_effect: EffectApplier,
    observe_postcondition: PostconditionObserver,
) -> ApplyResult:
    """Apply one staged batch only after fresh same-source reauthorization."""

    current = _authorized_request(fresh_preflight())
    if current != batch.source:
        return ApplyResult(False, "source-no-longer-authorized")

    # Validate the complete normal batch before its first durable mutation.
    for effect in batch.effects:
        if not effect_guard(effect):
            return ApplyResult(False, "effect-precondition-rejected")
        if effect.kind == "routing-transition" and not topology_validator(batch.source, effect):
            return ApplyResult(False, "illegal-routing-successor")

    for effect in batch.effects:
        apply_effect(effect)
        if not observe_postcondition(effect):
            return ApplyResult(False, "postcondition-failed")

    continuation = _authorized_request(fresh_preflight())
    return ApplyResult(True, "applied", continuation)
