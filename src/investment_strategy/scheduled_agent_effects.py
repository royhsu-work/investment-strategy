"""Fresh reauthorization boundary for Scheduled Agent durable effects."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.workflow_dispatch import DispatchPreflight


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

    raise NotImplementedError("fresh Scheduled Agent effect application is not implemented")
