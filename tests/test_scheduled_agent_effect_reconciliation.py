"""Accepted effect reconciliation at interruption boundaries."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from investment_strategy import issue_comment_bridge as dispatch
from investment_strategy import scheduled_agent_application_bridge as application
from investment_strategy.scheduled_agent_action_model import (
    Action,
    ActionApplicationDecision,
    ActionSource,
    ApplicationDisposition,
    ApplicationRejection,
    ApplicationRejectionKind,
    BoundedActionResult,
    ResultKind,
    TypedResult,
    role_for,
)
from investment_strategy.scheduled_agent_effects import (
    EffectBatch,
    EffectRecoveryEvidence,
    StagedEffect,
    apply_effect_batch,
    parse_application_decision,
    parse_effect_batch,
    render_application_decision_body,
)
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    WorkerRequest,
    acquire_dispatch_preflight,
)
from investment_strategy.workflow_dispatch import DispatchPreflight, ObservationProvenance

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


@pytest.mark.parametrize("empty_original", [False, True])
@pytest.mark.parametrize("already_durable", [False, True])
def test_exception_recovery_real_guarded_engine_cross_wake(
    monkeypatch: pytest.MonkeyPatch, empty_original: bool, already_durable: bool
) -> None:
    """Real guarded effect engine: no old replay; one lawful formal/successor."""

    import investment_strategy.scheduled_agent_effects as effects
    import investment_strategy.scheduled_agent_merge_acceptance as merge

    original, source = _batch()
    semantic = {
        "issue_number": source.issue_number,
        "role": source.role,
        "action": source.action,
        "change": CHANGE,
        "result_kind": "ready",
        "evidence_ref": "issuecomment-138-qualified",
        "result_content": "already accepted",
    }
    original_effects = (
        []
        if empty_original
        else [
            {"kind": effect.kind, "payload_json": effect.payload_json}
            for effect in original.effects
        ]
    )
    formal = {
        "kind": "issue-comment",
        "payload_json": json.dumps({"issue_number": 138, "body": "ACTION_RESULT\nformal"}),
    }
    accepted_raw = json.dumps(dict(semantic, requested_effects=original_effects))
    fresh_raw = json.dumps(dict(semantic, requested_effects=[formal]))
    projected_raw, original_count = application._accepted_reconciliation_effect_projection(
        accepted_raw=accepted_raw,
        projected_raw=fresh_raw,
        source=source,
        change=CHANGE,
    )
    assert original_count == len(original_effects)
    formal_effect = parse_effect_batch(projected_raw, source, authorized_change=CHANGE).effects[-1]
    derived = StagedEffect(
        "routing-transition",
        json.dumps({"issue_number": 138, "action": "implement-change"}),
        derived=True,
    )
    state = {
        "original": already_durable,
        "formal": False,
        "successor": False,
    }
    writes: list[str] = []

    def identify(effect: StagedEffect) -> str:
        if effect == derived:
            return "successor"
        if effect == formal_effect:
            return "formal"
        return "original"

    class Adapter:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        def observe_postcondition(self, effect: StagedEffect) -> bool:
            return state[identify(effect)]

        def guard(self, effect: StagedEffect) -> bool:
            assert not state[identify(effect)]
            return True

        def apply(self, effect: StagedEffect) -> None:
            key = identify(effect)
            assert not state[key]
            writes.append(key)
            state[key] = True

        def validate_implementation_checkpoint(self, *_a: object) -> bool:
            return True

        def carrier_plan_if_required(self, *_a: object) -> None:
            return None

        def effect_rejection(self) -> None:
            return None

    monkeypatch.setattr(merge, "GitHubEffectAdapter", Adapter)
    monkeypatch.setattr(merge, "acquire_current_github_preflight", lambda *_a, **_k: None)
    monkeypatch.setattr(
        effects,
        "_typed_application_plan",
        lambda *_a: (_decision(), derived, None),
    )

    def run(*, proven_empty: bool) -> tuple[EffectBatch, effects.ApplyResult]:
        return merge.run_guarded_effect_application(
            projected_raw,
            source=source,
            repository="owner/repo",
            token=REVISION,
            current_revision=REVISION,
            authorized_change=CHANGE,
            accepted_intent=True,
            reconcile_only=True,
            uncertain_effect_index=original_count - 1,
            proven_empty_original_effects=proven_empty,
        )

    if empty_original:
        _, rejected = run(proven_empty=False)
        assert not rejected.applied and writes == []
    if not empty_original and not already_durable:
        _, blocked = run(proven_empty=False)
        assert not blocked.applied and writes == []
        state["original"] = True

    _, first = run(proven_empty=empty_original)
    assert first.applied
    assert writes == ["formal", "successor"]
    _, second = run(proven_empty=empty_original)
    assert second.applied and writes == ["formal", "successor"]


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


@pytest.mark.parametrize("effect_kind", ["issue-comment", "github-mutation"])
def test_unknown_attempted_prefix_allows_only_unattempted_formal_result_and_successor(
    monkeypatch: pytest.MonkeyPatch,
    effect_kind: str,
) -> None:
    """A lost effect response can complete without replaying its write.

    The formal ACTION_RESULT is a *later* Effect in the same original batch.
    It was never reached when the first Effect's response was lost and must be
    allowed to persist after the original effect has been freshly proved.
    """
    import investment_strategy.scheduled_agent_effects as effects

    batch, _ = _batch()
    batch = replace(
        batch,
        effects=(
            StagedEffect(effect_kind, json.dumps({"effect_identity": "accepted"})),
            StagedEffect("issue-comment", json.dumps({"body": "ACTION_RESULT\naccepted"})),
        ),
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
    state = {"first": False, "formal": False, "route": False}
    writes: list[str] = []

    def observed(effect: StagedEffect) -> bool:
        if effect.kind == effect_kind and effect.payload_json == batch.effects[0].payload_json:
            return state["first"]
        return state["route"] if effect.kind == "routing-transition" else state["formal"]

    def apply(effect: StagedEffect) -> None:
        if effect == batch.effects[0]:
            pytest.fail("unproven original Effect was replayed")
        if effect.kind == "routing-transition":
            state["route"] = True
            writes.append("route")
        else:
            state["formal"] = True
            writes.append("formal")

    def reconcile() -> effects.ApplyResult:
        return apply_effect_batch(
            batch,
            fresh_preflight=lambda: cast(DispatchPreflight, None),
            effect_guard=lambda _effect: True,
            apply_effect=apply,
            observe_postcondition=observed,
            current_revision=REVISION,
            accepted_intent=True,
            reconcile_only=True,
            uncertain_effect_index=0,
        )

    assert not reconcile().applied
    assert writes == []
    state["first"] = True  # Later fresh GitHub GET proves the lost write.
    assert reconcile().applied
    assert writes == ["formal", "route"]
    assert reconcile().applied
    assert writes == ["formal", "route"]


def test_unknown_derived_effect_is_never_replayed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import investment_strategy.scheduled_agent_effects as effects

    batch, _ = _batch()
    monkeypatch.setattr(
        effects,
        "_typed_application_plan",
        lambda *_args: (
            _decision(),
            StagedEffect(
                "routing-transition",
                json.dumps({"issue_number": 138, "action": "implement-change"}),
                True,
            ),
            None,
        ),
    )
    writes: list[StagedEffect] = []
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: cast(DispatchPreflight, None),
        effect_guard=lambda _effect: True,
        apply_effect=writes.append,
        observe_postcondition=lambda effect: effect.kind != "routing-transition",
        current_revision=REVISION,
        accepted_intent=True,
        reconcile_only=True,
        uncertain_effect_index=len(batch.effects),
    )
    assert not result.applied and not writes
    assert result.recovery_evidence is not None
    assert result.recovery_evidence.unfinished_boundary == "effect-reconciliation"
    assert result.recovery_evidence.failed_effect_index == len(batch.effects)


@pytest.mark.parametrize("first_kind", ["issue-comment", "github-mutation"])
def test_dispatch_read_only_observer_checks_attempted_prefix_not_unwritten_formal(
    monkeypatch: pytest.MonkeyPatch,
    first_kind: str,
) -> None:
    """Dispatch and Application reuse one postcondition owner, without writes."""
    batch, source = _batch()
    raw = json.dumps(
        {
            "issue_number": source.issue_number,
            "role": source.role,
            "action": source.action,
            "change": CHANGE,
            "result_kind": "ready",
            "evidence_ref": "issuecomment-138-qualified",
            "result_content": "already accepted",
            "requested_effects": [
                {"kind": first_kind, "payload_json": batch.effects[0].payload_json},
                {
                    "kind": "issue-comment",
                    "payload_json": json.dumps({"body": "ACTION_RESULT\npending"}),
                },
            ],
        }
    )
    decision = render_application_decision_body(
        request_comment_id=91,
        request_body="effect-request-identity",
        authorization_revision=REVISION,
        decision=_decision(),
        disposition="ACCEPTED",
        raw_worker_result=raw,
        reason="application accepted",
    )
    record = parse_application_decision(decision)
    assert record is not None
    monkeypatch.setattr(application, "_fresh_application_worker_result", lambda raw, **_kw: raw)
    state = {"original": False, "formal": False}
    observations: list[str] = []

    class ReadOnlyAdapter:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def observe_postcondition(self, effect: StagedEffect) -> bool:
            observations.append(effect.kind)
            return (
                state["original"]
                if effect.payload_json == batch.effects[0].payload_json
                else state["formal"]
            )

    monkeypatch.setattr(application, "GitHubEffectAdapter", ReadOnlyAdapter)
    evidence: dict[str, object] = {
        "reason": "indeterminate accepted effects require reconciliation",
        "mutation_status": "unknown",
        "unfinished_boundary": "effect-reconciliation",
        "failed_effect_index": 0,
        "failed_effect_kind": first_kind,
        "failed_effect_sha256": hashlib.sha256(batch.effects[0].payload_json.encode()).hexdigest(),
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
        "rejection": None,
    }

    def observe() -> bool:
        return application.accepted_read_only_effects_complete(
            record=record,
            source=source,
            recovery_evidence=evidence,
            repository="owner/repo",
            token=REVISION,
            current_revision=REVISION,
            default_branch="main",
        )

    assert not observe()
    state["original"] = True
    assert observe()  # The later formal write is not a prerequisite.
    assert observations == [first_kind, first_kind]

    evidence["failed_effect_index"] = 1
    evidence["failed_effect_kind"] = "issue-comment"
    evidence["failed_effect_sha256"] = hashlib.sha256(
        json.loads(raw)["requested_effects"][1]["payload_json"].encode()
    ).hexdigest()
    assert not observe()  # But when the formal write itself was unknown, observe it.
    state["formal"] = True
    assert observe()


def test_archive_phase_drift_observes_original_dispatch_before_writing_new_pr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Real Application projection changes shape without rebinding an unknown write."""
    import investment_strategy.scheduled_agent_effects as effects

    source = WorkerRequest(138, "lead", "finalize-change")
    raw = json.dumps(
        {
            "issue_number": 138,
            "role": "lead",
            "action": "finalize-change",
            "change": CHANGE,
            "result_kind": "archive-ready",
            "evidence_ref": "issuecomment-138-qualified",
            "result_content": "original immutable accepted intent",
            "requested_effects": [],
        }
    )
    decision_body = render_application_decision_body(
        request_comment_id=91,
        request_body="original request",
        authorization_revision=REVISION,
        decision=ActionApplicationDecision(
            ApplicationDisposition.ACCEPT,
            ActionSource(138, CHANGE, Action.FINALIZE_CHANGE, REVISION),
            BoundedActionResult(
                138,
                CHANGE,
                Action.FINALIZE_CHANGE,
                TypedResult(ResultKind.ARCHIVE_READY, "issuecomment-138-qualified"),
            ),
            Action.REVIEW_ARCHIVE,
            role_for(Action.REVIEW_ARCHIVE),
        ),
        disposition="ACCEPTED",
        raw_worker_result=raw,
        reason="application accepted",
    )
    record = parse_application_decision(decision_body)
    assert record is not None
    stage = {"value": "missing-branch", "original_completed": False}
    monkeypatch.setattr(application, "_machine_result_revision", lambda *_a, **_kw: REVISION)
    monkeypatch.setattr(
        application,
        "_fresh_archive_state",
        lambda *_a, **_kw: (
            stage["value"],
            None if stage["value"] == "missing-branch" else "agent/archive-deterministic-recovery",
            None if stage["value"] == "missing-branch" else "b" * 40,
        ),
    )
    monkeypatch.setattr(application, "_fresh_non_control_effects", lambda *_a, **_kw: [])
    monkeypatch.setattr(
        application, "_formal_body_for_worker", lambda *_a, **_kw: "ACTION_RESULT\nproof"
    )

    def project(revision: str) -> EffectBatch:
        projected = application._fresh_application_worker_result(
            raw,
            source=source,
            change=CHANGE,
            repository="owner/repo",
            token=REVISION,
            current_revision=revision,
            default_branch="main",
            request_comment_id=91,
        )
        return parse_effect_batch(projected, source, authorized_change=CHANGE)

    original_batch = project(REVISION)
    old = original_batch.effects[0]
    assert json.loads(old.payload_json)["operation"] == "workflow-dispatch"
    unknown = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind=old.kind,
        failed_effect_sha256=hashlib.sha256(old.payload_json.encode()).hexdigest(),
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="unknown",
        unfinished_boundary="effect-postcondition",
    )
    assert application._attempted_effect_checkpoint(original_batch, unknown) is not None
    assert record.action == source.action
    assert record.role == source.role
    assert record.issue_number == source.issue_number
    assert record.disposition == "ACCEPTED"
    monkeypatch.setattr(
        application,
        "_application_decision_comment_for_request",
        lambda **_kw: (record, decision_body),
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7001")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github-output"))
    artifact = tmp_path / "effect-checkpoint.json"
    assert application._write_application_recovery_evidence(
        str(artifact),
        result=application.ApplyResult(False, "unknown", recovery_evidence=unknown),
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=91,
        trigger_comment_id=91,
        authorization_revision=REVISION,
        current_revision=REVISION,
        run_attempt=1,
        continuation=None,
        predecessor=None,
        effect_batch=original_batch,
    )
    failure = json.loads(artifact.read_text())["failure_evidence"]
    assert failure["attempted_effects"][0]["payload_json"] == old.payload_json
    stage["value"] = "missing-pr"
    advanced_revision = "c" * 40
    advanced_batch = project(advanced_revision)
    assert json.loads(advanced_batch.effects[0].payload_json)["operation"] == "pull-request-create"
    assert advanced_batch.effects[0].payload_json != old.payload_json
    adapter_context: list[dict[str, object]] = []

    class Observer:
        def __init__(self, *_a: object, **_kw: object) -> None:
            adapter_context.append(_kw)

        def observe_postcondition(self, effect: StagedEffect) -> bool:
            assert effect == old  # Never observe the freshly projected PR as the old write.
            return bool(stage["original_completed"])

    monkeypatch.setattr(application, "GitHubEffectAdapter", Observer)

    def original_complete() -> bool:
        return application.accepted_read_only_effects_complete(
            record=record,
            source=source,
            recovery_evidence=failure,
            repository="owner/repo",
            token=REVISION,
            current_revision=advanced_revision,
            default_branch="main",
        )

    assert not original_complete()
    stage["original_completed"] = True
    assert original_complete()
    expected_correlation = effects.formal_application_correlation(
        source,
        change=CHANGE,
        result_kind="archive-ready",
        current_revision=REVISION,
        request_comment_id=91,
    )
    assert all(
        item["pending_application_correlation"] == expected_correlation
        and item["current_revision"] == advanced_revision
        for item in adapter_context
    )
    # The missing PR is a *new* carrier-owned write. Its exact carrier
    # postcondition advances the next real Application projection to the
    # formal-result phase; the old dispatch is never issued again.
    writes: list[str] = ["github-mutation"]  # fresh, qualified PR-create carrier
    stage["value"] = "ready"
    formal_batch = project(advanced_revision)
    assert [effect.kind for effect in formal_batch.effects] == ["issue-comment"]
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
    done: set[str] = set()

    def execute(effect: StagedEffect) -> None:
        if effect == old:
            pytest.fail("original dispatch replayed")
        writes.append(effect.kind)
        done.add(effect.payload_json)

    def finish() -> effects.ApplyResult:
        return apply_effect_batch(
            formal_batch,
            fresh_preflight=lambda: cast(DispatchPreflight, None),
            effect_guard=lambda _effect: True,
            apply_effect=execute,
            observe_postcondition=lambda effect: effect.payload_json in done,
            current_revision=advanced_revision,
            accepted_intent=True,
        )

    assert finish().applied
    assert finish().applied
    assert writes == ["github-mutation", "issue-comment", "routing-transition"]


def test_merge_phase_drift_preserves_original_merge_before_ref_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Merge observation is never replaced by the next projected ref-delete."""
    source = WorkerRequest(138, "executor", "merge-archive-pr")
    raw = json.dumps(
        {
            "issue_number": 138,
            "role": source.role,
            "action": source.action,
            "change": CHANGE,
            "result_kind": "merged",
            "evidence_ref": "issuecomment-138-reviewed",
            "result_content": "immutable merge acceptance",
            "requested_effects": [],
        }
    )
    carrier = {
        "number": 432,
        "state": "open",
        "merged": False,
        "head": {"ref": "agent/archive-deterministic-recovery", "sha": "b" * 40},
        "base": {"ref": "main", "sha": REVISION},
    }
    monkeypatch.setattr(application, "_machine_result_revision", lambda *_a, **_kw: REVISION)
    monkeypatch.setattr(application, "_fresh_merge_carrier", lambda **_kw: carrier)
    monkeypatch.setattr(application, "_fresh_pull_requests", lambda *_a, **_kw: (carrier,))
    monkeypatch.setattr(application, "_fresh_non_control_effects", lambda *_a, **_kw: [])
    monkeypatch.setattr(
        application, "_formal_body_for_worker", lambda *_a, **_kw: "MERGE_RESULT\nproof"
    )
    monkeypatch.setattr(application, "_github_json", lambda *_a, **_kw: carrier)
    monkeypatch.setattr(application, "_merged_carrier_is_in_current_default", lambda *_a: True)
    monkeypatch.setattr(application, "_fresh_branch_head", lambda *_a: "b" * 40)

    def project(revision: str) -> EffectBatch:
        projected = application._fresh_application_worker_result(
            raw,
            source=source,
            change=CHANGE,
            repository="owner/repo",
            token=REVISION,
            current_revision=revision,
            default_branch="main",
            request_comment_id=91,
        )
        return parse_effect_batch(projected, source, authorized_change=CHANGE)

    original = project(REVISION)
    merge = original.effects[0]
    assert json.loads(merge.payload_json)["operation"] == "pull-request-merge"
    checkpoint = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind=merge.kind,
        failed_effect_sha256=hashlib.sha256(merge.payload_json.encode()).hexdigest(),
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="unknown",
        unfinished_boundary="effect-postcondition",
    )
    attempted = application._attempted_effect_checkpoint(original, checkpoint)
    assert attempted is not None
    carrier.update(
        state="closed",
        merged=True,
        merged_at="2026-11-09T09:00:00Z",
        merge_commit_sha="c" * 40,
    )
    next_batch = project("d" * 40)
    cleanup = next_batch.effects[0]
    assert json.loads(cleanup.payload_json)["operation"] == "ref-delete"
    assert cleanup.payload_json != merge.payload_json
    failure = {
        "reason": "postcondition was unknown",
        "failed_effect_index": 0,
        "failed_effect_kind": merge.kind,
        "failed_effect_sha256": checkpoint.failed_effect_sha256,
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
        "mutation_status": "unknown",
        "unfinished_boundary": "effect-postcondition",
        "rejection": None,
        "attempted_effects": attempted,
        "attempt_revision": REVISION,
    }
    record = application.ApplicationDecisionRecord(
        issue_number=source.issue_number,
        role=source.role,
        action=source.action,
        change=CHANGE,
        result_kind="merged",
        authorization_revision=REVISION,
        request_comment_id=91,
        request_body_sha256=hashlib.sha256(b"original request").hexdigest(),
        disposition="ACCEPTED",
        worker_result_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        raw_worker_result=raw,
        reason="application accepted",
    )
    observed: list[StagedEffect] = []

    class Reader:
        def __init__(self, *_a: object, **_kw: object) -> None:
            pass

        def observe_postcondition(self, effect: StagedEffect) -> bool:
            observed.append(effect)
            return effect == merge

    monkeypatch.setattr(application, "GitHubEffectAdapter", Reader)
    assert application.accepted_read_only_effects_complete(
        record=record,
        source=source,
        recovery_evidence=failure,
        repository="owner/repo",
        token=REVISION,
        current_revision="d" * 40,
        default_branch="main",
    )
    assert observed == [merge]  # No ref-delete observation or replay.


@pytest.mark.parametrize(
    ("role", "action", "kind", "successor", "marker"),
    [
        ("lead", "resolve-question", "ready", Action.IMPLEMENT_CHANGE, "ACTION_RESULT"),
        (
            "reviewer",
            "review-implementation",
            "pass",
            Action.MERGE_IMPLEMENTATION_PR,
            "REVIEW_RESULT",
        ),
        ("executor", "merge-archive-pr", "merged", Action.FINALIZE_ARCHIVE, "MERGE_RESULT"),
    ],
)
@pytest.mark.parametrize("current_gate_valid", [True, False])
def test_original_formal_post_at_r1_is_never_reissued_at_descendant_r2(
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    action: str,
    kind: str,
    successor: Action,
    marker: str,
    current_gate_valid: bool,
) -> None:
    """Real formal producer -> immutable checkpoint -> R2 plan -> one successor.

    The old GitHub POST was durable even though its immediate confirmation was
    lost. A descendant default HEAD is never permission to mint a new formal
    comment or reinterpret the original review at the new revision.
    """
    import investment_strategy.scheduled_agent_effects as effects

    source = WorkerRequest(138, role, action)
    old_revision, new_revision = REVISION, "c" * 40
    raw = json.dumps(
        {
            "issue_number": 138,
            "role": role,
            "action": action,
            "change": CHANGE,
            "result_kind": kind,
            "evidence_ref": "issuecomment-138-qualified",
            "result_content": "original accepted semantic result",
            "requested_effects": [],
        }
    )
    old_projection = application._application_owned_worker_result(
        raw,
        source=source,
        change=CHANGE,
        current_revision=old_revision,
        result_revision=old_revision,
        request_comment_id=91,
    )
    new_projection = application._application_owned_worker_result(
        raw,
        source=source,
        change=CHANGE,
        current_revision=new_revision,
        result_revision=old_revision,
        request_comment_id=91,
    )
    original_batch = parse_effect_batch(old_projection, source, authorized_change=CHANGE)
    old_formal = original_batch.effects[0]
    assert json.loads(old_formal.payload_json)["body"].startswith(marker + "\n")
    rewritten_batch = parse_effect_batch(new_projection, source, authorized_change=CHANGE)
    assert rewritten_batch.effects[0] != old_formal  # The exact replay bug.
    failure_status = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind="issue-comment",
        failed_effect_sha256=hashlib.sha256(old_formal.payload_json.encode()).hexdigest(),
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="unknown",
        unfinished_boundary="effect-postcondition",
    )
    snapshot = application._attempted_effect_checkpoint(original_batch, failure_status)
    assert snapshot is not None
    failure = {
        "failed_effect_index": 0,
        "failed_effect_kind": "issue-comment",
        "failed_effect_sha256": failure_status.failed_effect_sha256,
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
        "attempted_effects": snapshot,
        "attempt_revision": old_revision,
    }
    restored = application._retain_completed_accepted_formal_effect(
        new_projection,
        failure=failure,
        source=source,
        change=CHANGE,
        result_kind=kind,
        request_comment_id=91,
    )
    assert restored is not None
    restored_raw, original_correlation = restored
    restored_batch = parse_effect_batch(restored_raw, source, authorized_change=CHANGE)
    assert restored_batch.effects[0] == old_formal
    assert original_correlation == effects.formal_application_correlation(
        source,
        change=CHANGE,
        result_kind=kind,
        current_revision=old_revision,
        request_comment_id=91,
    )
    model_action = Action(action)
    decision = ActionApplicationDecision(
        ApplicationDisposition.ACCEPT,
        ActionSource(138, CHANGE, model_action, new_revision),
        BoundedActionResult(
            138, CHANGE, model_action, TypedResult(ResultKind(kind), "issuecomment-138-qualified")
        ),
        successor,
        role_for(successor),
    )
    derived = effects.derived_transition_effect(
        issue_number=138, change=CHANGE, successor=successor
    )
    monkeypatch.setattr(effects, "_typed_application_plan", lambda *_a: (decision, derived, None))
    writes: list[str] = []
    routed = False

    def observe(effect: StagedEffect) -> bool:
        return effect == old_formal or (effect == derived and routed)

    def guard(effect: StagedEffect) -> bool:
        if effect == old_formal:
            pytest.fail("already committed formal result reached a write guard")
        return current_gate_valid

    def apply(effect: StagedEffect) -> None:
        nonlocal routed
        if effect != derived:
            pytest.fail("formal result replayed under R2 correlation")
        writes.append("successor")
        routed = True

    result = apply_effect_batch(
        restored_batch,
        fresh_preflight=lambda: cast(DispatchPreflight, None),
        effect_guard=guard,
        apply_effect=apply,
        observe_postcondition=observe,
        current_revision=new_revision,
        accepted_intent=True,
    )
    assert result.applied is current_gate_valid
    assert writes == (["successor"] if current_gate_valid else [])


@pytest.mark.parametrize("rejected_successor_first", [False, True])
def test_application_continuation_at_r2_preserves_durable_r1_formal_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rejected_successor_first: bool,
) -> None:
    """Exercise the real Application entrypoint, not only the restore helper.

    The original formal POST succeeded but its response was lost. The R2
    continuation must hand the exact R1 formal effect and correlation to the
    shared executor; only the current, qualified successor may be written.
    """
    import investment_strategy.scheduled_agent_effects as effects

    source = WorkerRequest(138, "lead", "resolve-question")
    r1, r2, r3 = REVISION, "c" * 40, "d" * 40
    request_id, continuation_id = 91, 1000
    raw = json.dumps(
        {
            "_semantic_intent_version": 2,
            "issue_number": source.issue_number,
            "role": source.role,
            "action": source.action,
            "change": CHANGE,
            "result_kind": "ready",
            "evidence_ref": "issuecomment-138-qualified",
            "result_content": "accepted semantic decision",
            "requested_effects": [],
        },
        sort_keys=True,
    )
    old_projection = application._application_owned_worker_result(
        raw,
        source=source,
        change=CHANGE,
        current_revision=r1,
        result_revision=r1,
        request_comment_id=request_id,
    )
    original_batch = parse_effect_batch(old_projection, source, authorized_change=CHANGE)
    original_formal = original_batch.effects[0]
    original_body = json.loads(original_formal.payload_json)["body"]
    assert original_body.startswith("ACTION_RESULT\n")
    status = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind="issue-comment",
        failed_effect_sha256=hashlib.sha256(original_formal.payload_json.encode()).hexdigest(),
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="unknown",
        unfinished_boundary="effect-postcondition",
    )
    snapshot = application._attempted_effect_checkpoint(original_batch, status)
    assert snapshot is not None
    failure = {
        "reason": "effect response lost",
        "failed_effect_index": 0,
        "failed_effect_kind": status.failed_effect_kind,
        "failed_effect_sha256": status.failed_effect_sha256,
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
        "mutation_status": "unknown",
        "unfinished_boundary": "effect-postcondition",
        "rejection": None,
        "attempted_effects": snapshot,
        "attempt_revision": r1,
    }
    request_body = application.render_application_request(application.ApplicationRequest(r1, raw))
    decision_body = render_application_decision_body(
        request_comment_id=request_id,
        request_body=request_body,
        authorization_revision=r1,
        decision=_decision(),
        disposition="ACCEPTED",
        raw_worker_result=raw,
        reason="application accepted",
    )
    record = parse_application_decision(decision_body)
    assert record is not None
    digest = hashlib.sha256(decision_body.encode()).hexdigest()
    continuation_body = application.render_application_continuation_request(
        repository="royhsu-work/investment-strategy",
        issue_number=source.issue_number,
        original_request_comment_id=request_id,
        accepted_decision_sha256=digest,
        predecessor_run_id=7001,
        predecessor_run_attempt=1,
        predecessor_job_id=7002,
        predecessor_artifact_id=7003,
        predecessor_artifact_digest="sha256:" + "d" * 64,
        failure_evidence_sha256="e" * 64,
        recovery_episode_sha256="f" * 64,
    )
    event = {
        "action": "created",
        "issue": {
            "number": 142,
            "title": "[Agent Runtime] 2026-09-03",
            "state": "open",
            "labels": [],
        },
        "comment": {
            "id": continuation_id,
            "body": continuation_body,
            "user": {"login": "royhsu-work"},
            "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
        },
    }
    event_path = tmp_path / "continuation-event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    continuation = application.parse_application_continuation_request(continuation_body)
    assert continuation is not None
    predecessor = application.ApplicationRecoveryArtifact(
        run_id=7001,
        run_attempt=1,
        job_id=7002,
        artifact_id=7003,
        artifact_digest="sha256:" + "d" * 64,
        request_comment_id=request_id,
        accepted_decision_sha256=digest,
        failure_evidence_sha256="e" * 64,
        recovery_episode_sha256="f" * 64,
        recovery_attempt=1,
        continuation_eligible=True,
        document={
            "issue_number": source.issue_number,
            "role": source.role,
            "action": source.action,
            "authorization_revision": r1,
            "trigger_comment_id": request_id,
            "failure_evidence": failure,
            "prior_failure_evidence_sha256": [],
            "predecessor": None,
        },
    )
    active = {
        "revision": r2,
        "predecessor": predecessor,
        "gate_valid": not rejected_successor_first,
    }

    def r2_projection(_raw: str, **kwargs: object) -> str:
        assert _raw == raw
        assert kwargs["current_revision"] == active["revision"]
        return application._application_owned_worker_result(
            raw,
            source=source,
            change=CHANGE,
            current_revision=cast(str, active["revision"]),
            result_revision=r1,
            request_comment_id=request_id,
        )

    monkeypatch.setattr(application, "_fresh_application_worker_result", r2_projection)
    monkeypatch.setattr(application, "_fresh_event_observation", lambda *_a: False)
    preflight = acquire_dispatch_preflight(
        observations=(
            GitHubIssueObservation(
                issue_number=source.issue_number,
                change=CHANGE,
                routing=("lead", "resolve-question"),
                state="open",
                created_order=1,
                authoritative=True,
                current_state_provenance=ObservationProvenance.QUALIFIED,
            ),
        ),
        source_total_count=1,
        incomplete_results=False,
        exhausted=True,
        human_authorized=True,
    )
    monkeypatch.setattr(application, "acquire_current_github_preflight", lambda *_a: preflight)
    monkeypatch.setattr(
        application,
        "_find_application_decision_from_current_frontier",
        lambda **_kw: record,
    )
    monkeypatch.setattr(
        application,
        "_application_decision_comment_for_request",
        lambda **_kw: (record, decision_body),
    )
    monkeypatch.setattr(
        application,
        "qualify_application_continuation_predecessor",
        lambda *_a, **_kw: active["predecessor"],
    )
    monkeypatch.setattr(application, "_authorization_revision_is_ancestor", lambda *_a: True)
    monkeypatch.setattr(application, "_accepted_worker_result_for_continuation", lambda **_kw: raw)
    monkeypatch.setattr(application, "_verified_zero_original_accepted_effects", lambda **_kw: True)
    monkeypatch.setattr(
        application, "read_application_recovery_artifact", lambda *_a, **_kw: predecessor
    )
    monkeypatch.setattr(
        dispatch, "_application_runs", lambda *_a, **_kw: ({"id": 7001, "run_attempt": 1},)
    )

    class DurableReader:
        def __init__(self, *_a: object, **kwargs: object) -> None:
            assert kwargs[
                "pending_application_correlation"
            ] == effects.formal_application_correlation(
                source,
                change=CHANGE,
                result_kind="ready",
                current_revision=r1,
                request_comment_id=request_id,
            )

        def observe_postcondition(self, effect: StagedEffect) -> bool:
            assert effect == original_formal
            return True

    monkeypatch.setattr(application, "GitHubEffectAdapter", DurableReader)
    monkeypatch.setattr(application, "_write_carrier_outputs", lambda *_a: None)
    monkeypatch.setattr(application, "_write_validation_outputs", lambda *_a: None)

    effects_written: list[StagedEffect] = []
    model_decision = ActionApplicationDecision(
        ApplicationDisposition.ACCEPT,
        ActionSource(138, CHANGE, Action.RESOLVE_QUESTION, r2),
        BoundedActionResult(
            138,
            CHANGE,
            Action.RESOLVE_QUESTION,
            TypedResult(ResultKind.READY, "issuecomment-138-qualified"),
        ),
        Action.IMPLEMENT_CHANGE,
        role_for(Action.IMPLEMENT_CHANGE),
    )
    successor = effects.derived_transition_effect(
        issue_number=138, change=CHANGE, successor=Action.IMPLEMENT_CHANGE
    )
    monkeypatch.setattr(
        effects,
        "_typed_application_plan",
        lambda *_a: (
            replace(
                model_decision,
                source=ActionSource(
                    138, CHANGE, Action.RESOLVE_QUESTION, cast(str, active["revision"])
                ),
            ),
            successor,
            None,
        ),
    )

    def execute(
        raw_worker_result: str, **kwargs: object
    ) -> tuple[EffectBatch, effects.ApplyResult]:
        assert kwargs["source"] == source
        assert kwargs["current_revision"] == active["revision"]
        assert kwargs["accepted_intent"] is True
        assert kwargs["pending_application_correlation"] == effects.formal_application_correlation(
            source,
            change=CHANGE,
            result_kind="ready",
            current_revision=r1,
            request_comment_id=request_id,
        )
        batch = parse_effect_batch(raw_worker_result, source, authorized_change=CHANGE)
        assert batch.effects == (original_formal,)
        result = apply_effect_batch(
            batch,
            fresh_preflight=lambda: cast(DispatchPreflight, None),
            effect_guard=lambda effect: effect == successor and bool(active["gate_valid"]),
            apply_effect=effects_written.append,
            observe_postcondition=lambda effect: (
                effect == original_formal or effect in effects_written
            ),
            current_revision=cast(str, active["revision"]),
            accepted_intent=True,
            effect_rejection=lambda: ApplicationRejection(
                ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED,
                "expected current default-branch HEAD",
                "default-branch HEAD changed before derived transition",
            ),
        )
        return batch, result

    monkeypatch.setattr(application, "run_guarded_effect_application", execute)
    monkeypatch.setenv("GITHUB_REPOSITORY", "royhsu-work/investment-strategy")
    monkeypatch.setenv("GITHUB_TOKEN", "test")
    monkeypatch.setenv("GITHUB_RUN_ID", "8001")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github-output"))
    recovery_path = tmp_path / "derived-zero-write-recovery.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "application-bridge",
            "--event-path",
            str(event_path),
            "--revision",
            r2,
            "--default-branch",
            "main",
            "--recovery-evidence-path",
            str(recovery_path),
        ],
    )
    assert application._main_unprotected(application.ApplicationExceptionContext()) == (
        1 if rejected_successor_first else 0
    )
    if rejected_successor_first:
        assert effects_written == []
        recovered_document = json.loads(recovery_path.read_text(encoding="utf-8"))
        failed = recovered_document["failure_evidence"]
        assert failed["attempt_revision"] == r1
        assert failed["mutation_status"] == "not-complete"
        assert failed["completed_effect_indexes"] == [0]
        assert failed["attempted_effects"][0]["payload_json"] == original_formal.payload_json
        assert failed["attempted_effects"][1]["kind"] == "routing-transition"

        active["revision"] = r3
        active["gate_valid"] = True
        active["predecessor"] = replace(
            predecessor,
            run_id=8001,
            run_attempt=1,
            job_id=8002,
            artifact_id=8003,
            artifact_digest="sha256:" + "a" * 64,
            failure_evidence_sha256=recovered_document["failure_evidence_sha256"],
            recovery_episode_sha256=recovered_document["recovery_episode_sha256"],
            recovery_attempt=recovered_document["recovery_attempt"],
            document=recovered_document,
        )
        next_continuation = application.render_application_continuation_request(
            repository="royhsu-work/investment-strategy",
            issue_number=source.issue_number,
            original_request_comment_id=request_id,
            accepted_decision_sha256=digest,
            predecessor_run_id=8001,
            predecessor_run_attempt=1,
            predecessor_job_id=8002,
            predecessor_artifact_id=8003,
            predecessor_artifact_digest="sha256:" + "a" * 64,
            failure_evidence_sha256=recovered_document["failure_evidence_sha256"],
            recovery_episode_sha256=recovered_document["recovery_episode_sha256"],
        )
        event["comment"] = {
            **cast(dict[str, object], event["comment"]),
            "id": 1001,
            "body": next_continuation,
        }
        event_path.write_text(json.dumps(event), encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "application-bridge",
                "--event-path",
                str(event_path),
                "--revision",
                r3,
                "--default-branch",
                "main",
            ],
        )
        assert application._main_unprotected(application.ApplicationExceptionContext()) == 0
    assert effects_written == [successor]


@pytest.mark.parametrize(
    ("role", "action", "kind", "successor"),
    [
        ("lead", "resolve-question", "ready", Action.IMPLEMENT_CHANGE),
        ("reviewer", "review-implementation", "pass", Action.MERGE_IMPLEMENTATION_PR),
        ("executor", "merge-archive-pr", "merged", Action.FINALIZE_ARCHIVE),
    ],
)
def test_durable_formal_then_zero_write_successor_rejection_recovers_after_revision_moves(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    role: str,
    action: str,
    kind: str,
    successor: Action,
) -> None:
    """A rejected *unattempted* successor must not become an unknown write.

    Exercise the real Effect engine, durable recovery writer, read-only
    qualifier, fresh R3 continuation projection, and a single successor write.
    The R1 formal result stays immutable through both R2 and R3.
    """
    import investment_strategy.scheduled_agent_effects as effects

    source = WorkerRequest(138, role, action)
    r1, r2, r3 = REVISION, "c" * 40, "d" * 40
    request_id = 91
    raw = json.dumps(
        {
            "_semantic_intent_version": 2,
            "issue_number": source.issue_number,
            "role": role,
            "action": action,
            "change": CHANGE,
            "result_kind": kind,
            "evidence_ref": "issuecomment-138-qualified",
            "result_content": "immutable accepted semantic result",
            "requested_effects": [],
        },
        sort_keys=True,
    )
    original = application._application_owned_worker_result(
        raw,
        source=source,
        change=CHANGE,
        current_revision=r1,
        result_revision=r1,
        request_comment_id=request_id,
    )
    original_batch = parse_effect_batch(original, source, authorized_change=CHANGE)
    formal = original_batch.effects[0]
    r2_projection = application._application_owned_worker_result(
        raw,
        source=source,
        change=CHANGE,
        current_revision=r2,
        result_revision=r1,
        request_comment_id=request_id,
    )
    prior_failure = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind=formal.kind,
        failed_effect_sha256=hashlib.sha256(formal.payload_json.encode()).hexdigest(),
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="unknown",
        unfinished_boundary="effect-postcondition",
    )
    attempted = application._attempted_effect_checkpoint(original_batch, prior_failure)
    assert attempted is not None
    original_failure: dict[str, object] = {
        "failed_effect_index": 0,
        "failed_effect_kind": formal.kind,
        "failed_effect_sha256": prior_failure.failed_effect_sha256,
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
        "mutation_status": "unknown",
        "unfinished_boundary": "effect-postcondition",
        "rejection": None,
        "attempted_effects": attempted,
        "attempt_revision": r1,
    }
    restored_r2 = application._retain_completed_accepted_formal_effect(
        r2_projection,
        failure=original_failure,
        source=source,
        change=CHANGE,
        result_kind=kind,
        request_comment_id=request_id,
    )
    assert restored_r2 is not None
    original_correlation = restored_r2[1]
    batch = parse_effect_batch(restored_r2[0], source, authorized_change=CHANGE)
    assert batch.effects == (formal,)
    decision = ActionApplicationDecision(
        ApplicationDisposition.ACCEPT,
        ActionSource(138, CHANGE, Action(action), r2),
        BoundedActionResult(
            138, CHANGE, Action(action), TypedResult(ResultKind(kind), "issuecomment-138-qualified")
        ),
        successor,
        role_for(successor),
    )
    derived = effects.derived_transition_effect(
        issue_number=138, change=CHANGE, successor=successor
    )
    monkeypatch.setattr(effects, "_typed_application_plan", lambda *_a: (decision, derived, None))
    rejection = ApplicationRejection(
        ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED,
        "unchanged source and HEAD",
        "main advanced between preflight and derived guard",
    )
    writes: list[StagedEffect] = []
    stale = apply_effect_batch(
        batch,
        fresh_preflight=lambda: cast(DispatchPreflight, None),
        effect_guard=lambda _effect: False,
        apply_effect=lambda _effect: pytest.fail("no Effect may be written at rejected gate"),
        observe_postcondition=lambda effect: effect == formal,
        current_revision=r2,
        accepted_intent=True,
        effect_rejection=lambda: rejection,
    )
    assert not stale.applied and stale.recovery_evidence is not None
    assert stale.recovery_evidence.failed_effect_index == 1
    assert stale.recovery_evidence.completed_effect_indexes == (0,)
    assert stale.recovery_evidence.mutation_status == "not-complete"

    request_body = application.render_application_request(application.ApplicationRequest(r1, raw))
    decision_body = render_application_decision_body(
        request_comment_id=request_id,
        request_body=request_body,
        authorization_revision=r1,
        decision=replace(
            decision,
            source=ActionSource(138, CHANGE, Action(action), r1),
        ),
        disposition="ACCEPTED",
        raw_worker_result=raw,
        reason="application accepted",
    )
    # The persisted accepted decision belongs to R1, even though the current
    # effect guard and successor are checked at a newer default-branch HEAD.
    record = parse_application_decision(decision_body)
    assert record is not None
    monkeypatch.setattr(
        application,
        "_application_decision_comment_for_request",
        lambda **_kw: (record, decision_body),
    )
    # The derived guard rejection follows an independently qualified earlier
    # formal-write response loss. A newly emitted checkpoint is not the whole
    # accepted history; retain its original native predecessor as proof.
    first_sha = application._canonical_sha256(original_failure)
    first_artifact = application.ApplicationRecoveryArtifact(
        run_id=6001,
        run_attempt=1,
        job_id=6002,
        artifact_id=6003,
        artifact_digest="sha256:" + "e" * 64,
        request_comment_id=request_id,
        accepted_decision_sha256=hashlib.sha256(decision_body.encode()).hexdigest(),
        failure_evidence_sha256=first_sha,
        recovery_episode_sha256="f" * 64,
        recovery_attempt=1,
        continuation_eligible=True,
        document={
            "issue_number": source.issue_number,
            "role": source.role,
            "action": source.action,
            "authorization_revision": r1,
            "trigger_comment_id": request_id,
            "prior_failure_evidence_sha256": [],
            "predecessor": None,
            "failure_evidence": original_failure,
        },
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7001")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github-output"))
    artifact = tmp_path / "zero-write-derived-recovery.json"
    assert application._write_application_recovery_evidence(
        str(artifact),
        result=stale,
        repository="royhsu-work/investment-strategy",
        token=REVISION,
        source=source,
        request_comment_id=request_id,
        trigger_comment_id=1000,
        authorization_revision=r1,
        current_revision=r2,
        run_attempt=1,
        continuation=None,
        predecessor=first_artifact,
        effect_batch=batch,
    )
    document = json.loads(artifact.read_text(encoding="utf-8"))
    assert document["continuation_eligible"] is True
    failure = document["failure_evidence"]
    assert failure["attempt_revision"] == r1
    assert failure["attempted_effects"][0]["payload_json"] == formal.payload_json
    assert failure["attempted_effects"][1]["kind"] == derived.kind
    assert application._accepted_recovery_boundary(failure) == "READ_ONLY"

    observed: list[StagedEffect] = []

    class Reader:
        def __init__(self, *_a: object, **kwargs: object) -> None:
            assert kwargs["pending_application_correlation"] == original_correlation

        def observe_postcondition(self, effect: StagedEffect) -> bool:
            observed.append(effect)
            assert effect == formal  # Never demand the rejected derived write.
            return True

    monkeypatch.setattr(application, "GitHubEffectAdapter", Reader)
    monkeypatch.setattr(application, "_accepted_worker_result_for_continuation", lambda **_kw: raw)
    monkeypatch.setattr(application, "_verified_zero_original_accepted_effects", lambda **_kw: True)
    monkeypatch.setattr(
        application, "read_application_recovery_artifact", lambda *_a, **_kw: first_artifact
    )
    monkeypatch.setattr(
        dispatch, "_application_runs", lambda *_a, **_kw: ({"id": 6001, "run_attempt": 1},)
    )
    current_artifact = application.ApplicationRecoveryArtifact(
        run_id=7001,
        run_attempt=1,
        job_id=7002,
        artifact_id=7003,
        artifact_digest="sha256:" + "a" * 64,
        request_comment_id=request_id,
        accepted_decision_sha256=document["accepted_decision_sha256"],
        failure_evidence_sha256=document["failure_evidence_sha256"],
        recovery_episode_sha256=document["recovery_episode_sha256"],
        recovery_attempt=2,
        continuation_eligible=True,
        document=document,
    )
    assert application.accepted_read_only_effects_complete(
        record=record,
        source=source,
        recovery_evidence=failure,
        repository="royhsu-work/investment-strategy",
        token=REVISION,
        current_revision=r3,
        default_branch="main",
        recovery_artifact=current_artifact,
    )
    assert observed == [formal]

    r3_projection = application._application_owned_worker_result(
        raw,
        source=source,
        change=CHANGE,
        current_revision=r3,
        result_revision=r1,
        request_comment_id=request_id,
    )
    restored_r3 = application._retain_completed_accepted_formal_effect(
        r3_projection,
        failure=failure,
        source=source,
        change=CHANGE,
        result_kind=kind,
        request_comment_id=request_id,
    )
    assert restored_r3 is not None and restored_r3[1] == restored_r2[1]
    fresh_batch = parse_effect_batch(restored_r3[0], source, authorized_change=CHANGE)
    assert fresh_batch.effects == (formal,)

    def observe(effect: StagedEffect) -> bool:
        return effect == formal or effect in writes

    def apply(effect: StagedEffect) -> None:
        if effect != derived:
            pytest.fail("a completed formal result or another Effect was replayed")
        writes.append(effect)

    def continue_once() -> effects.ApplyResult:
        return apply_effect_batch(
            fresh_batch,
            fresh_preflight=lambda: cast(DispatchPreflight, None),
            effect_guard=lambda effect: effect == derived,
            apply_effect=apply,
            observe_postcondition=observe,
            current_revision=r3,
            accepted_intent=True,
        )

    assert continue_once().applied
    assert continue_once().applied
    assert writes == [derived]


@pytest.mark.parametrize("partially_complete", [False, True])
def test_unknown_recovery_crosses_real_artifact_dispatch_and_continuation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    partially_complete: bool,
) -> None:
    """The genuine scheduled dispatcher must reach read-only reconciliation.

    Exercise writer -> exact uploaded bytes -> reader -> completion classifier
    -> producer -> strict continuation qualifier, not a fabricated eligible
    dataclass or a direct call to the Effect engine alone.
    """
    batch, source = _batch()
    requested_effects = [
        {"kind": batch.effects[0].kind, "payload_json": batch.effects[0].payload_json}
    ]
    if partially_complete:
        requested_effects.append(
            {
                "kind": "issue-comment",
                "payload_json": json.dumps(
                    {"issue_number": source.issue_number, "body": "second accepted consequence"}
                ),
            }
        )
    # The application-owned formal result is strictly later than the failed
    # write, and therefore cannot be required as a recovery precondition.
    requested_effects.append(
        {
            "kind": "issue-comment",
            "payload_json": json.dumps(
                {"issue_number": source.issue_number, "body": "ACTION_RESULT\naccepted"}
            ),
        }
    )
    raw = json.dumps(
        {
            "issue_number": source.issue_number,
            "role": source.role,
            "action": source.action,
            "change": CHANGE,
            "result_kind": "ready",
            "evidence_ref": "issuecomment-138-qualified",
            "result_content": "already accepted",
            "requested_effects": requested_effects,
        },
        sort_keys=True,
    )
    original = "EFFECT_REQUEST\nAuthorization-Revision: " + REVISION
    decision_body = render_application_decision_body(
        request_comment_id=91,
        request_body=original,
        authorization_revision=REVISION,
        decision=_decision(),
        disposition="ACCEPTED",
        raw_worker_result=raw,
        reason="application accepted",
    )
    record = parse_application_decision(decision_body)
    assert record is not None
    decision_digest = hashlib.sha256(decision_body.encode()).hexdigest()
    failure_effect = requested_effects[1 if partially_complete else 0]
    status = EffectRecoveryEvidence(
        failed_effect_index=1 if partially_complete else 0,
        failed_effect_kind=cast(str, failure_effect["kind"]),
        failed_effect_sha256=hashlib.sha256(
            cast(str, failure_effect["payload_json"]).encode()
        ).hexdigest(),
        completed_effect_indexes=(0,) if partially_complete else (),
        completed_effect_sha256=(
            hashlib.sha256(batch.effects[0].payload_json.encode()).hexdigest(),
        )
        if partially_complete
        else (),
        mutation_status="unknown",
        unfinished_boundary="effect-postcondition",
        rejection=None,
    )
    monkeypatch.setattr(
        application,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (record, decision_body),
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7001")
    recovery_path = tmp_path / "application-recovery.json"
    application._write_application_recovery_evidence(
        str(recovery_path),
        result=application.ApplyResult(
            False, "durable postcondition not observed", recovery_evidence=status
        ),
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=91,
        trigger_comment_id=91,
        authorization_revision=REVISION,
        current_revision=REVISION,
        run_attempt=1,
        continuation=None,
        predecessor=None,
        effect_batch=parse_effect_batch(raw, source, authorized_change=CHANGE),
    )
    document = json.loads(recovery_path.read_text(encoding="utf-8"))
    assert document["continuation_eligible"] is True
    assert len(document["failure_evidence"]["attempted_effects"]) == status.failed_effect_index + 1
    raw_artifact = recovery_path.read_bytes()
    artifact_digest = "sha256:" + hashlib.sha256(raw_artifact).hexdigest()
    run = {
        "id": 7001,
        "run_attempt": 1,
        "status": "completed",
        "head_sha": REVISION,
        "display_title": "Scheduled Agent Application 91",
    }
    job = {
        "id": 7002,
        "name": "apply",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "success",
        "steps": [{"name": "Upload exact application recovery evidence", "conclusion": "success"}],
    }

    def read(_repo: str, _token: str, path: str) -> object:
        if path == "actions/runs/7001":
            return run
        if path == "actions/runs/7001/attempts/1/jobs":
            return {"total_count": 1, "jobs": [job]}
        if path == "actions/runs/7001/artifacts?per_page=100":
            return {
                "artifacts": [
                    {
                        "id": 7003,
                        "name": "application-recovery-evidence",
                        "digest": artifact_digest,
                        "expired": False,
                        "workflow_run": {"id": 7001, "head_sha": REVISION},
                    }
                ]
            }
        raise AssertionError(f"unexpected GitHub read: {path}")

    def artifact_reader(_repo: str, _token: str, path: str) -> bytes:
        assert path == "actions/artifacts/7003/zip"
        return raw_artifact

    qualified = application.read_application_recovery_artifact(
        "owner/repo",
        "test",
        run_id=7001,
        run_attempt=1,
        job_id=7002,
        request_comment_id=91,
        accepted_decision_sha256=decision_digest,
        read=read,
        artifact_reader=artifact_reader,
        strict_read=True,
    )
    assert qualified is not None and qualified.continuation_eligible
    monkeypatch.setattr(dispatch, "_application_runs", lambda *_args, **_kw: (run,))
    monkeypatch.setattr(
        dispatch, "_qualified_unapplied_terminal_carrier_effect", lambda *_args, **_kw: False
    )
    monkeypatch.setattr(
        dispatch, "_qualified_carrier_for_application_run", lambda *_args, **_kw: None
    )
    monkeypatch.setattr(dispatch, "read_github_artifact_bytes", artifact_reader)
    completion = dispatch._application_job(
        "owner/repo",
        "test",
        91,
        read=read,
        record=record,
        accepted_decision_sha256=decision_digest,
    )
    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-continuation-required"
    accepted_comment = {
        "id": 92,
        "body": decision_body,
        "created_at": "2026-09-22T15:39:54Z",
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    monkeypatch.setattr(dispatch, "_paged_list", lambda *_args, **_kw: (accepted_comment,))
    continuation_body = dispatch._application_continuation_body(
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=91,
        predecessor_evidence=qualified,
    )
    assert continuation_body is not None
    continuation = application.parse_application_continuation_request(continuation_body)
    assert continuation is not None
    request_comment = {
        "id": 1000,
        "body": continuation_body,
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }
    monkeypatch.setattr(
        application,
        "_paged_github_list",
        lambda _repo, _token, path: (
            (accepted_comment,) if path.startswith("issues/138/") else (request_comment,)
        ),
    )
    verified = application.qualify_application_continuation_predecessor(
        "owner/repo",
        "test",
        continuation,
        current_comment_id=1000,
        transport_issue_number=500,
        read=read,
        artifact_reader=artifact_reader,
    )
    assert verified is not None
    assert application._accepted_predecessor_disposition(verified) == "INDETERMINATE"

    # A first read-only Application continuation can observe the exact same
    # unfinished frontier. That observation creates a new *qualified* artifact
    # but must not permanently disable later reads or spawn identical writes.
    unknown = EffectRecoveryEvidence(
        failed_effect_index=status.failed_effect_index,
        failed_effect_kind=status.failed_effect_kind,
        failed_effect_sha256=status.failed_effect_sha256,
        completed_effect_indexes=status.completed_effect_indexes,
        completed_effect_sha256=status.completed_effect_sha256,
        mutation_status="unknown",
        unfinished_boundary="effect-reconciliation",
        rejection=None,
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7004")
    second_path = tmp_path / "repeated-read-only.json"
    application._write_application_recovery_evidence(
        str(second_path),
        result=application.ApplyResult(
            False,
            "indeterminate accepted effects require reconciliation",
            recovery_evidence=unknown,
        ),
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=91,
        trigger_comment_id=1000,
        authorization_revision=REVISION,
        current_revision=REVISION,
        run_attempt=1,
        continuation=continuation,
        predecessor=verified,
    )
    assert second_path.is_file()
    repeated = json.loads(second_path.read_text(encoding="utf-8"))
    assert repeated["continuation_eligible"] is True
    repeated_bytes = second_path.read_bytes()
    second_run = {**run, "id": 7004, "display_title": "Scheduled Agent Application 1000"}
    second_job = {**job, "id": 7005}

    def read_later(_repo: str, _token: str, path: str) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path == "actions/runs/7004":
            return second_run
        if path == "actions/runs/7004/attempts/1/jobs":
            return {"total_count": 1, "jobs": [second_job]}
        if path == "actions/runs/7004/artifacts?per_page=100":
            return {
                "artifacts": [
                    {
                        "id": 7006,
                        "name": "application-recovery-evidence",
                        "digest": "sha256:" + hashlib.sha256(repeated_bytes).hexdigest(),
                        "expired": False,
                        "workflow_run": {"id": 7004, "head_sha": REVISION},
                    }
                ]
            }
        raise AssertionError(f"unexpected read-only observation: {path}")

    def later_bytes(_repo: str, _token: str, path: str) -> bytes:
        assert path == "actions/artifacts/7006/zip"
        return repeated_bytes

    second_qualified = application.read_application_recovery_artifact(
        "owner/repo",
        REVISION,
        run_id=7004,
        run_attempt=1,
        job_id=7005,
        request_comment_id=91,
        accepted_decision_sha256=decision_digest,
        read=read_later,
        artifact_reader=later_bytes,
        strict_read=True,
    )
    assert second_qualified is not None and second_qualified.continuation_eligible
    monkeypatch.setattr(dispatch, "_application_runs", lambda *_args, **_kw: (second_run,))
    monkeypatch.setattr(dispatch, "read_github_artifact_bytes", later_bytes)
    real_batch = parse_effect_batch(raw, source, authorized_change=CHANGE)
    effect_ids = [(effect.kind, effect.payload_json) for effect in real_batch.effects]
    effect_state = [bool(partially_complete)] + [False] * (len(effect_ids) - 1)
    monkeypatch.setattr(application, "_fresh_application_worker_result", lambda raw, **_kw: raw)

    class ReadOnlyAdapter:
        def __init__(self, *_args: object, **_kw: object) -> None:
            pass

        def observe_postcondition(self, effect: StagedEffect) -> bool:
            return effect_state[effect_ids.index((effect.kind, effect.payload_json))]

    monkeypatch.setattr(application, "GitHubEffectAdapter", ReadOnlyAdapter)

    def classify_again() -> dispatch.ApplicationCompletion:
        return dispatch._application_job(
            "owner/repo",
            REVISION,
            91,
            read=read_later,
            record=record,
            accepted_decision_sha256=decision_digest,
            current_revision=REVISION,
        )

    first_read = classify_again()
    assert first_read.reason == "application-completion-read-only-observing"
    assert first_read.state == "RESUMABLE"
    # An unchanged observation is not an executable new continuation.
    effect_state[status.failed_effect_index] = True
    later_read = classify_again()
    assert later_read.state == "RESUMABLE"
    assert later_read.reason == "application-completion-continuation-required"
    assert later_read.recovery_artifact is not None
    resumed_body = dispatch._application_continuation_body(
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=91,
        predecessor_evidence=later_read.recovery_artifact,
    )
    assert resumed_body is not None
    resumed_request = application.parse_application_continuation_request(resumed_body)
    assert resumed_request is not None
    second_request_comment = {**request_comment, "id": 1001, "body": resumed_body}
    monkeypatch.setattr(
        application,
        "_paged_github_list",
        lambda _repo, _token, path: (
            (accepted_comment,) if path.startswith("issues/138/") else (second_request_comment,)
        ),
    )
    resumed_predecessor = application.qualify_application_continuation_predecessor(
        "owner/repo",
        REVISION,
        resumed_request,
        current_comment_id=1001,
        transport_issue_number=500,
        read=read_later,
        artifact_reader=later_bytes,
    )
    assert resumed_predecessor is not None

    # The shared Effect engine then persists only the never-attempted formal
    # result and model-derived successor, never either previously attempted
    # effect. A repeated successful continuation is idempotent.
    import investment_strategy.scheduled_agent_effects as effects

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
    effect_state_route = {"routed": False}
    writes: list[str] = []

    def observed(effect: StagedEffect) -> bool:
        if effect.kind == "routing-transition":
            return effect_state_route["routed"]
        return effect_state[effect_ids.index((effect.kind, effect.payload_json))]

    def apply(effect: StagedEffect) -> None:
        if effect.kind == "routing-transition":
            effect_state_route["routed"] = True
            writes.append("successor")
            return
        index = effect_ids.index((effect.kind, effect.payload_json))
        assert index == len(effect_ids) - 1  # Only the never-attempted formal comment.
        effect_state[index] = True
        writes.append("formal-result")

    def finish() -> effects.ApplyResult:
        return apply_effect_batch(
            real_batch,
            fresh_preflight=lambda: cast(DispatchPreflight, None),
            effect_guard=lambda _effect: True,
            apply_effect=apply,
            observe_postcondition=observed,
            current_revision=REVISION,
            accepted_intent=True,
            reconcile_only=True,
            uncertain_effect_index=unknown.failed_effect_index,
        )

    assert finish().applied
    assert finish().applied
    assert writes == ["formal-result", "successor"]


@pytest.mark.parametrize("new_completed_frontier", [False, True])
def test_read_only_recovery_of_recovery_is_evidence_bounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    new_completed_frontier: bool,
) -> None:
    """A new run is not progress; only a new durable completion witness is."""
    batch, source = _batch()
    remaining_payload = json.dumps({"issue_number": 138, "body": "later verified effect"})
    accepted_raw = json.dumps(
        {
            "issue_number": source.issue_number,
            "role": source.role,
            "action": source.action,
            "change": CHANGE,
            "result_kind": "ready",
            "evidence_ref": "issuecomment-138-qualified",
            "result_content": "already accepted",
            "requested_effects": [
                {"kind": "issue-comment", "payload_json": batch.effects[0].payload_json},
                {"kind": "issue-comment", "payload_json": remaining_payload},
            ],
        },
        sort_keys=True,
    )
    decision_body = render_application_decision_body(
        request_comment_id=91,
        request_body="effect-request-identity",
        authorization_revision=REVISION,
        decision=_decision(),
        disposition="ACCEPTED",
        raw_worker_result=accepted_raw,
        reason="application accepted",
    )
    record = parse_application_decision(decision_body)
    assert record is not None
    monkeypatch.setattr(
        application,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (record, decision_body),
    )
    effect_identity = hashlib.sha256(batch.effects[0].payload_json.encode()).hexdigest()
    initial = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind="issue-comment",
        failed_effect_sha256=effect_identity,
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="unknown",
        unfinished_boundary="effect-postcondition",
        rejection=None,
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7001")
    first_path = tmp_path / "first-recovery.json"
    application._write_application_recovery_evidence(
        str(first_path),
        result=application.ApplyResult(
            False, "postcondition unobserved", recovery_evidence=initial
        ),
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=91,
        trigger_comment_id=91,
        authorization_revision=REVISION,
        current_revision=REVISION,
        run_attempt=1,
        continuation=None,
        predecessor=None,
    )
    first_document = json.loads(first_path.read_text(encoding="utf-8"))
    assert first_document["continuation_eligible"] is True
    predecessor = application.ApplicationRecoveryArtifact(
        run_id=7001,
        run_attempt=1,
        job_id=7002,
        artifact_id=7003,
        artifact_digest="sha256:" + "4" * 64,
        request_comment_id=91,
        accepted_decision_sha256=hashlib.sha256(decision_body.encode()).hexdigest(),
        failure_evidence_sha256=first_document["failure_evidence_sha256"],
        recovery_episode_sha256=first_document["recovery_episode_sha256"],
        recovery_attempt=1,
        continuation_eligible=True,
        document=first_document,
    )
    progress = EffectRecoveryEvidence(
        failed_effect_index=1 if new_completed_frontier else 0,
        failed_effect_kind="issue-comment",
        failed_effect_sha256=hashlib.sha256(remaining_payload.encode()).hexdigest()
        if new_completed_frontier
        else effect_identity,
        completed_effect_indexes=(0,) if new_completed_frontier else (),
        completed_effect_sha256=(effect_identity,) if new_completed_frontier else (),
        mutation_status="unknown",
        unfinished_boundary="effect-reconciliation",
        rejection=None,
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7004")
    second_path = tmp_path / "second-recovery.json"
    application._write_application_recovery_evidence(
        str(second_path),
        result=application.ApplyResult(
            False,
            "indeterminate accepted effects require reconciliation",
            recovery_evidence=progress,
        ),
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=91,
        trigger_comment_id=1000,
        authorization_revision=REVISION,
        current_revision=REVISION,
        run_attempt=1,
        continuation=None,
        predecessor=predecessor,
    )
    second_document = json.loads(second_path.read_text(encoding="utf-8"))
    assert second_document["predecessor"]["run_id"] == 7001
    assert second_document["recovery_attempt"] == 2
    assert second_document["prior_failure_evidence_sha256"] == [
        first_document["failure_evidence_sha256"]
    ]
    # A stable read-only observation must retain the ability to observe a
    # *later* authoritative GitHub postcondition, without replaying the write.
    assert second_document["continuation_eligible"] is True


@pytest.mark.parametrize("pre_guard_failure", [False, True])
def test_partial_guard_exception_reuses_verified_unattempted_suffix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pre_guard_failure: bool
) -> None:
    """Native-shaped recovery evidence: E0 durable, E1 never called, then fresh E1/formal/route."""

    import investment_strategy.scheduled_agent_effects as effects

    original, source = _batch()
    first = original.effects[0]
    second = StagedEffect(
        "issue-comment", json.dumps({"issue_number": 138, "body": "second accepted write"})
    )
    formal = StagedEffect(
        "issue-comment", json.dumps({"issue_number": 138, "body": "ACTION_RESULT\nformal"})
    )
    semantic = {
        "issue_number": source.issue_number,
        "role": source.role,
        "action": source.action,
        "change": CHANGE,
        "result_kind": "ready",
        "evidence_ref": "issuecomment-138-qualified",
        "result_content": "accepted semantics",
    }
    accepted_raw = json.dumps(
        dict(
            semantic,
            requested_effects=[
                {"kind": effect.kind, "payload_json": effect.payload_json}
                for effect in (first, second)
            ],
        )
    )
    projected_raw = json.dumps(
        dict(
            semantic,
            requested_effects=[
                {"kind": effect.kind, "payload_json": effect.payload_json}
                for effect in (first, second, formal)
            ],
        )
    )
    recovered_raw, original_count = application._accepted_reconciliation_effect_projection(
        accepted_raw=accepted_raw,
        projected_raw=projected_raw,
        source=source,
        change=CHANGE,
    )
    assert original_count == 2
    batch = parse_effect_batch(recovered_raw, source, authorized_change=CHANGE)
    successor = effects.derived_transition_effect(
        issue_number=138, change=CHANGE, successor=Action.IMPLEMENT_CHANGE
    )
    monkeypatch.setattr(
        effects, "_typed_application_plan", lambda *_a: (_decision(), successor, None)
    )
    labels = {first: "E0", second: "E1", formal: "formal", successor: "successor"}
    durable: set[str] = set()
    writes: list[str] = []
    interrupted = {"allowed": True}

    def observe(effect: StagedEffect) -> bool:
        return labels[effect] in durable

    def guard(effect: StagedEffect) -> bool:
        if interrupted["allowed"] and effect == second and (pre_guard_failure or "E0" in durable):
            raise OSError("transient GitHub GET failure before this write")
        return True

    def apply(effect: StagedEffect) -> None:
        key = labels[effect]
        assert key not in durable, f"replayed {key}"
        durable.add(key)
        writes.append(key)

    def run(recover: bool) -> effects.ApplyResult:
        return apply_effect_batch(
            batch,
            fresh_preflight=lambda: cast(DispatchPreflight, None),
            effect_guard=guard,
            apply_effect=apply,
            observe_postcondition=observe,
            current_revision=REVISION,
            accepted_intent=True,
            reconcile_only=recover,
            uncertain_effect_index=0 if recover else None,
        )

    failed = run(False)
    assert not failed.applied and failed.recovery_evidence is not None
    assert failed.recovery_evidence.unfinished_boundary == "effect-precondition-exception"
    assert failed.recovery_evidence.mutation_status == "not-complete"
    if pre_guard_failure:
        assert failed.recovery_evidence.failed_effect_index == 0
        assert writes == []
        durable.add("E0")  # Independently observed before any lawful continuation.
    else:
        assert failed.recovery_evidence.failed_effect_index == 1
        assert failed.recovery_evidence.completed_effect_indexes == (0,)
        assert writes == ["E0"]
    decision_body = render_application_decision_body(
        request_comment_id=91,
        request_body="exact accepted request",
        authorization_revision=REVISION,
        decision=_decision(),
        disposition="ACCEPTED",
        raw_worker_result=accepted_raw,
        reason="application accepted",
    )
    record = parse_application_decision(decision_body)
    assert record is not None
    monkeypatch.setattr(
        application,
        "_application_decision_comment_for_request",
        lambda **_kw: (record, decision_body),
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7001")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github-output"))
    artifact_path = tmp_path / "recovery.json"
    assert application._write_application_recovery_evidence(
        str(artifact_path),
        result=failed,
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=91,
        trigger_comment_id=91,
        authorization_revision=REVISION,
        current_revision=REVISION,
        run_attempt=1,
        continuation=None,
        predecessor=None,
        effect_batch=batch,
    )
    failure = json.loads(artifact_path.read_text())["failure_evidence"]
    assert application._accepted_recovery_boundary(failure) == "READ_ONLY"
    attempted = application._verified_attempted_effect_checkpoint(failure, source=source)
    assert attempted is not None
    assert attempted[0] == first
    assert attempted[-1] == (first if pre_guard_failure else second)

    class FreshAdapter:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def observe_postcondition(self, effect: StagedEffect) -> bool:
            return observe(effect)

    monkeypatch.setattr(application, "GitHubEffectAdapter", FreshAdapter)
    native_document = json.loads(artifact_path.read_text())
    native = application.ApplicationRecoveryArtifact(
        run_id=7001,
        run_attempt=1,
        job_id=7002,
        artifact_id=7003,
        artifact_digest="sha256:" + "b" * 64,
        request_comment_id=91,
        accepted_decision_sha256=native_document["accepted_decision_sha256"],
        failure_evidence_sha256=native_document["failure_evidence_sha256"],
        recovery_episode_sha256=native_document["recovery_episode_sha256"],
        recovery_attempt=1,
        continuation_eligible=True,
        document=native_document,
    )
    monkeypatch.setattr(
        application, "_accepted_worker_result_for_continuation", lambda **_kw: accepted_raw
    )
    monkeypatch.setattr(
        dispatch, "_application_runs", lambda *_a, **_kw: ({"id": 7001, "run_attempt": 1},)
    )

    def qualified(checkpoint: dict[str, object]) -> bool:
        return application.accepted_read_only_effects_complete(
            record=record,
            source=source,
            recovery_evidence=checkpoint,
            repository="owner/repo",
            token=REVISION,
            current_revision=REVISION,
            default_branch="main",
            recovery_artifact=native,
        )

    assert qualified(failure)
    mutated = dict(failure, failed_effect_sha256="f" * 64)
    assert not qualified(mutated)

    # The identical latest before-write checkpoint must not hide a previous
    # attempted write whose response was lost. That history is UNKNOWN, not
    # a certified NOT_APPLIED permission for the same immutable Effect.
    previous_failure = dict(
        failure,
        mutation_status="unknown",
        unfinished_boundary="effect-postcondition",
        operation_stage="WRITE",
        write_call_entered=True,
    )
    previous_hash = application._canonical_sha256(previous_failure)
    previous = replace(
        native,
        failure_evidence_sha256=previous_hash,
        document={
            **native_document,
            "failure_evidence": previous_failure,
            "failure_evidence_sha256": previous_hash,
        },
    )
    latest_document = {
        **native_document,
        "recovery_attempt": 2,
        "trigger_comment_id": 1000,
        "prior_failure_evidence_sha256": [previous_hash],
        "predecessor": {
            "run_id": previous.run_id,
            "run_attempt": previous.run_attempt,
            "job_id": previous.job_id,
            "artifact_id": previous.artifact_id,
            "artifact_digest": previous.artifact_digest,
            "failure_evidence_sha256": previous_hash,
            "recovery_attempt": 1,
        },
    }
    latest = replace(
        native,
        run_id=8001,
        job_id=8002,
        artifact_id=8003,
        recovery_attempt=2,
        document=latest_document,
    )
    monkeypatch.setattr(
        application, "read_application_recovery_artifact", lambda *_a, **_kw: previous
    )
    assert not application.accepted_read_only_effects_complete(
        record=record,
        source=source,
        recovery_evidence=failure,
        repository="owner/repo",
        token=REVISION,
        current_revision=REVISION,
        default_branch="main",
        recovery_artifact=latest,
    )
    durable.remove("E0")
    # No completed prefix exists when the failure preceded every Effect.
    assert qualified(failure) is pre_guard_failure
    durable.add("E0")
    interrupted["allowed"] = False
    if pre_guard_failure:
        # The source checkpoint proves only E0 was unattempted; the next
        # fresh run must still inspect E0 rather than assuming it was done.
        durable.remove("E0")
        assert run(False).applied
        assert writes == ["E0", "E1", "formal", "successor"]
    else:
        assert run(True).applied
        assert writes == ["E0", "E1", "formal", "successor"]
    assert run(False).applied
    assert writes == ["E0", "E1", "formal", "successor"]


def test_attempted_effect_exception_is_unknown_not_a_write_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same engine distinguishes an uncalled E1 from a lost E1 write response."""

    import investment_strategy.scheduled_agent_effects as effects

    base, _source = _batch()
    second = StagedEffect(
        "issue-comment", json.dumps({"issue_number": 138, "body": "second accepted write"})
    )
    batch = replace(base, effects=(base.effects[0], second))
    successor = effects.derived_transition_effect(
        issue_number=138, change=CHANGE, successor=Action.IMPLEMENT_CHANGE
    )
    monkeypatch.setattr(
        effects, "_typed_application_plan", lambda *_a: (_decision(), successor, None)
    )
    complete: set[StagedEffect] = set()
    writes: list[StagedEffect] = []

    def apply(effect: StagedEffect) -> None:
        if effect == second:
            raise OSError("lost write response for E1")
        complete.add(effect)
        writes.append(effect)

    def reconcile() -> effects.ApplyResult:
        return apply_effect_batch(
            batch,
            fresh_preflight=lambda: cast(DispatchPreflight, None),
            effect_guard=lambda _e: True,
            apply_effect=apply,
            observe_postcondition=lambda e: e in complete,
            current_revision=REVISION,
            accepted_intent=True,
            reconcile_only=True,
            uncertain_effect_index=1,
        )

    first = apply_effect_batch(
        batch,
        fresh_preflight=lambda: cast(DispatchPreflight, None),
        effect_guard=lambda _e: True,
        apply_effect=apply,
        observe_postcondition=lambda e: e in complete,
        current_revision=REVISION,
        accepted_intent=True,
    )
    assert not first.applied and first.recovery_evidence is not None
    assert first.recovery_evidence.mutation_status == "unknown"
    assert first.recovery_evidence.unfinished_boundary == "effect-postcondition"
    assert first.recovery_evidence.operation_stage == "WRITE"
    assert first.recovery_evidence.write_call_entered is True
    assert first.recovery_evidence.raw_error == "lost write response for E1"
    assert first.recovery_evidence.completed_effect_indexes == (0,)
    assert writes == [batch.effects[0]]
    assert not reconcile().applied
    assert writes == [batch.effects[0]]  # The uncertain E1 must never replay.
    complete.add(second)  # A later fresh GET establishes exact E1 durability.
    assert reconcile().applied
    assert writes == [batch.effects[0], successor]


@pytest.mark.parametrize("completed_first", [False, True])
def test_initial_accepted_effect_observation_failure_has_exact_frontier(
    monkeypatch: pytest.MonkeyPatch, completed_first: bool
) -> None:
    """RED: the initial all-Effect GET can fail before any effect guard is called."""

    import investment_strategy.scheduled_agent_effects as effects

    original, _source = _batch()
    second = StagedEffect(
        "issue-comment", json.dumps({"issue_number": 138, "body": "second accepted write"})
    )
    batch = replace(original, effects=(original.effects[0], second))
    successor = effects.derived_transition_effect(
        issue_number=138, change=CHANGE, successor=Action.IMPLEMENT_CHANGE
    )
    monkeypatch.setattr(
        effects, "_typed_application_plan", lambda *_args: (_decision(), successor, None)
    )
    observed: list[StagedEffect] = []
    writes: list[StagedEffect] = []

    def read_postcondition(effect: StagedEffect) -> bool:
        observed.append(effect)
        if effect == second:
            raise OSError("GitHub GET failed before any E1 write")
        return completed_first

    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: cast(DispatchPreflight, None),
        effect_guard=lambda _effect: pytest.fail("guard ran after unqualified GET"),
        apply_effect=lambda effect: writes.append(effect),
        observe_postcondition=read_postcondition,
        current_revision=REVISION,
        accepted_intent=True,
    )
    assert not result.applied
    assert result.recovery_evidence is not None
    evidence = result.recovery_evidence
    assert evidence.failed_effect_index == 1
    assert evidence.failed_effect_sha256 == hashlib.sha256(second.payload_json.encode()).hexdigest()
    assert evidence.unfinished_boundary == "effect-precondition-exception"
    assert evidence.completed_effect_indexes == ((0,) if completed_first else ())
    assert evidence.mutation_status == "not-complete"  # invocation-local only
    assert evidence.operation_stage == "READ"
    assert evidence.write_call_entered is False
    assert evidence.raw_error == "GitHub GET failed before any E1 write"
    assert observed == [original.effects[0], second]
    assert writes == []


def test_run_local_effect_frontier_cannot_prove_accepted_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED: the same absent effect may have a lost response in an earlier run."""

    original, source = _batch()
    effect = original.effects[0]
    body = render_application_decision_body(
        request_comment_id=91,
        request_body="exact accepted request",
        authorization_revision=REVISION,
        decision=_decision(),
        disposition="ACCEPTED",
        raw_worker_result=json.dumps(
            {
                "issue_number": 138,
                "role": "lead",
                "action": "resolve-question",
                "change": CHANGE,
                "result_kind": "ready",
                "evidence_ref": "issuecomment-138-qualified",
                "result_content": "accepted",
                "requested_effects": [{"kind": effect.kind, "payload_json": effect.payload_json}],
            }
        ),
        reason="application accepted",
    )
    record = parse_application_decision(body)
    assert record is not None
    failure: dict[str, object] = {
        "reason": "effect observation raised before write: OSError",
        "mutation_status": "not-complete",
        "unfinished_boundary": "effect-precondition-exception",
        "failed_effect_index": 0,
        "failed_effect_kind": effect.kind,
        "failed_effect_sha256": hashlib.sha256(effect.payload_json.encode()).hexdigest(),
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
        "rejection": None,
        "attempt_revision": REVISION,
        "attempted_effects": [
            {"kind": effect.kind, "payload_json": effect.payload_json, "derived": False}
        ],
    }

    class Observer:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def observe_postcondition(self, _effect: StagedEffect) -> bool:
            return False

    monkeypatch.setattr(application, "GitHubEffectAdapter", Observer)
    # No run / predecessor evidence was supplied. An invocation-local
    # before-write failure must not upgrade an earlier unknown write to
    # an intent-wide NOT_APPLIED permission.
    assert not application.accepted_read_only_effects_complete(
        record=record,
        source=source,
        recovery_evidence=failure,
        repository="owner/repo",
        token=REVISION,
        current_revision=REVISION,
        default_branch="main",
    )
