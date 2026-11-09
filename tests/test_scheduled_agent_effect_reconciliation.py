"""Accepted effect reconciliation at interruption boundaries."""

from __future__ import annotations

import hashlib
import json
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
        if path == "actions/runs/7001/jobs":
            return {"jobs": [job]}
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
        if path == "actions/runs/7004/jobs":
            return {"jobs": [second_job]}
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
