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
    )
    document = json.loads(recovery_path.read_text(encoding="utf-8"))
    assert document["continuation_eligible"] is True
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
    assert second_document["continuation_eligible"] is new_completed_frontier
