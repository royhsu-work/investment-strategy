"""Accepted effect reconciliation at interruption boundaries."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import cast

import pytest

from investment_strategy.scheduled_agent_action_model import (
    Action,
    ActionApplicationDecision,
    ActionSource,
    ApplicationDisposition,
    BoundedActionResult,
    ResultKind,
    TypedResult,
    role_for,
)
from investment_strategy.scheduled_agent_effects import (
    EffectBatch,
    StagedEffect,
    apply_effect_batch,
    parse_effect_batch,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.workflow_dispatch import DispatchPreflight

REVISION = "a" * 40
CHANGE = "deterministic-recovery"


def _batch(
    action: str = "resolve-question", kind: str = "ready"
) -> tuple[EffectBatch, WorkerRequest]:
    source = WorkerRequest(138, "lead", action)
    raw = json.dumps(
        {
            "issue_number": 138,
            "role": source.role,
            "action": action,
            "change": CHANGE,
            "result_kind": kind,
            "evidence_ref": "issuecomment-138-qualified",
            "result_content": "already accepted",
            "requested_effects": [
                {
                    "kind": "issue-comment",
                    "payload_json": json.dumps({"issue_number": 138, "body": "evidence"}),
                }
            ],
        }
    )
    return parse_effect_batch(raw, source), source


def _decision() -> ActionApplicationDecision:
    source = ActionSource(138, CHANGE, Action.RESOLVE_QUESTION, REVISION)
    result = BoundedActionResult(
        138,
        CHANGE,
        Action.RESOLVE_QUESTION,
        TypedResult(ResultKind.READY, "issuecomment-138-qualified"),
    )
    return ActionApplicationDecision(
        ApplicationDisposition.ACCEPT,
        source,
        result,
        Action.IMPLEMENT_CHANGE,
        role_for(Action.IMPLEMENT_CHANGE),
    )


@pytest.mark.parametrize("already_complete", [True, False])
def test_accepted_effect_reconciles_before_write_and_then_commits_successor(
    monkeypatch: pytest.MonkeyPatch, already_complete: bool
) -> None:
    """A lost mutation response must not repeat an already durable effect."""
    import investment_strategy.scheduled_agent_effects as effects

    batch, _source = _batch()
    # The plan still comes from the existing Action model and qualified Issue.
    monkeypatch.setattr(
        effects,
        "_typed_application_plan",
        lambda *_args: (
            _decision(),
            StagedEffect(
                "routing-transition",
                json.dumps({"issue_number": 138, "action": "implement-change"}),
                derived=True,
            ),
            None,
        ),
    )
    effects_seen: list[str] = []
    state = {"issue-comment": already_complete, "routing-transition": False}

    def observed(effect: StagedEffect) -> bool:
        return state[effect.kind]

    def applied(effect: StagedEffect) -> None:
        effects_seen.append(effect.kind)
        state[effect.kind] = True

    def guard(effect: StagedEffect) -> bool:
        if state[effect.kind]:
            pytest.fail("completed effect was checked as an unwritten mutation")
        return True

    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: cast(DispatchPreflight, None),
        effect_guard=guard,
        apply_effect=applied,
        observe_postcondition=observed,
        current_revision=REVISION,
        accepted_intent=True,
    )
    assert result.applied
    assert effects_seen == (
        ["routing-transition"] if already_complete else ["issue-comment", "routing-transition"]
    )


def test_accepted_effect_never_replays_postcondition_after_interrupted_successor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import investment_strategy.scheduled_agent_effects as effects

    batch, _source = _batch()
    monkeypatch.setattr(
        effects,
        "_typed_application_plan",
        lambda *_args: (
            _decision(),
            StagedEffect(
                "routing-transition",
                json.dumps({"issue_number": 138, "action": "implement-change"}),
                derived=True,
            ),
            None,
        ),
    )
    writes: list[StagedEffect] = []
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: cast(DispatchPreflight, None),
        effect_guard=lambda _effect: pytest.fail("already complete effect was guarded"),
        apply_effect=writes.append,
        observe_postcondition=lambda _effect: True,
        current_revision=REVISION,
        accepted_intent=True,
    )
    assert result.applied and writes == []


@pytest.mark.parametrize("effect_kind", ["issue-comment", "github-mutation"])
@pytest.mark.parametrize("already_complete", [True, False])
def test_indeterminate_write_reconciles_only_confirmed_effects(
    monkeypatch: pytest.MonkeyPatch,
    effect_kind: str,
    already_complete: bool,
) -> None:
    """Unknown/partial writes cannot be replayed; a proved result can route."""
    import investment_strategy.scheduled_agent_effects as effects

    batch, _source = _batch()
    batch = replace(
        batch,
        effects=(StagedEffect(effect_kind, json.dumps({"effect_identity": "accepted"})),),
    )
    monkeypatch.setattr(
        effects,
        "_typed_application_plan",
        lambda *_args: (
            _decision(),
            StagedEffect(
                "routing-transition",
                json.dumps({"issue_number": 138, "action": "implement-change"}),
                derived=True,
            ),
            None,
        ),
    )
    writes: list[str] = []
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: cast(DispatchPreflight, None),
        effect_guard=lambda _effect: True,
        apply_effect=lambda effect: writes.append(effect.kind),
        observe_postcondition=lambda effect: (
            already_complete if effect.kind == effect_kind else bool(writes)
        ),
        current_revision=REVISION,
        accepted_intent=True,
        reconcile_only=True,
    )
    if already_complete:
        assert result.applied and writes == ["routing-transition"]
    else:
        assert not result.applied
        assert result.reason == "indeterminate accepted effects require reconciliation"
        assert writes == []
