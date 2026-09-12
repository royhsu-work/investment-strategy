"""Focused tests for typed Action-result application and exact effect guards."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable

import pytest

import investment_strategy.scheduled_agent_effects as effects
from investment_strategy.scheduled_agent_action_model import ResultKind
from investment_strategy.scheduled_agent_carrier import CarrierRequired, make_carrier_plan
from investment_strategy.scheduled_agent_effect_contract import (
    allowed_github_mutation_operations,
)
from investment_strategy.scheduled_agent_effects import (
    GitHubEffectAdapter,
    StagedEffect,
    apply_effect_batch,
    formal_application_correlation,
    parse_effect_batch,
    supported_effect_guard,
)
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    WorkerRequest,
    acquire_dispatch_preflight,
)
from investment_strategy.workflow_dispatch import (
    Action as WorkflowAction,
)
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    Role,
)

_REVISION = "a" * 40
_CHANGE = "simplify-scheduled-agent-control-plane"
_REQUEST_COMMENT_ID = 1003


def _preflight(
    *,
    issue_number: int = 138,
    action: WorkflowAction = "implement-change",
    change: str = _CHANGE,
    human_authorized: bool = True,
) -> DispatchPreflight:
    role: Role = "executor" if action.startswith(("implement", "merge")) else "lead"
    if action.startswith("review-"):
        role = "reviewer"
    return acquire_dispatch_preflight(
        observations=(
            GitHubIssueObservation(
                issue_number=issue_number,
                change=change,
                routing=(role, action),
                state="open",
                created_order=1,
                authoritative=True,
            ),
        ),
        source_total_count=1,
        incomplete_results=False,
        exhausted=True,
        human_authorized=human_authorized,
    )


def _raw(
    *,
    action: str = "implement-change",
    role: str = "executor",
    change: str = _CHANGE,
    result_kind: str = "spec-blocker",
    requested_effects: list[dict[str, str]] | None = None,
) -> str:
    return json.dumps(
        {
            "issue_number": 138,
            "role": role,
            "action": action,
            "change": change,
            "result_kind": result_kind,
            "evidence_ref": "issuecomment-typed-result",
            "result_content": "bounded result",
            "requested_effects": requested_effects or [],
        }
    )


def test_parse_effect_batch_binds_typed_result_and_effects() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    batch = parse_effect_batch(_raw(), source)
    assert batch.source == source
    assert batch.typed_result is not None
    assert batch.typed_result.result.kind is ResultKind.SPEC_BLOCKER
    assert batch.effects == ()


def test_typed_application_derives_one_successor_without_continuation() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    batch = parse_effect_batch(_raw(), source)
    applied: list[StagedEffect] = []

    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: True,
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
    )

    assert result.applied
    assert not hasattr(result, "continuation")
    assert len(applied) == 1
    assert applied[0].derived
    assert json.loads(applied[0].payload_json) == {
        "issue_number": 138,
        "action": "resolve-question",
    }


def test_carrier_required_is_a_hard_invocation_exit_before_successor_effects() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    carrier_plan = make_carrier_plan(
        repository="owner/repo",
        issue_number=138,
        change=_CHANGE,
        action="implement-change",
        authorization_revision=_REVISION,
        operation="pull-request-ready",
        target={"pull_request_number": 178},
        expected={"head_sha": _REVISION},
        requested={"head_sha": _REVISION, "draft": False},
        expected_postcondition={"draft": False},
    )
    batch = parse_effect_batch(
        _raw(
            result_kind="spec-blocker",
            requested_effects=[
                {
                    "kind": "github-mutation",
                    "payload_json": json.dumps(
                        {
                            "issue_number": 138,
                            "operation": "ref-delete",
                            "ref": "heads/agent/temporary",
                            "expected_sha": _REVISION,
                        }
                    ),
                },
                {
                    "kind": "issue-comment",
                    "payload_json": json.dumps(
                        {"issue_number": 138, "body": "must not run after carrier"}
                    ),
                },
            ],
        ),
        source,
    )
    applied: list[StagedEffect] = []
    observed: list[StagedEffect] = []

    def apply(effect: StagedEffect) -> None:
        applied.append(effect)
        raise CarrierRequired(carrier_plan)

    def observe(effect: StagedEffect) -> bool:
        observed.append(effect)
        return True

    with pytest.raises(CarrierRequired) as raised:
        apply_effect_batch(
            batch,
            fresh_preflight=_preflight,
            effect_guard=lambda _effect: True,
            apply_effect=apply,
            observe_postcondition=observe,
            current_revision=_REVISION,
        )

    assert raised.value.plan == carrier_plan
    assert len(applied) == 1
    assert observed == []


def _accept_checkpoint(
    _request: effects.MaterializationRequest,
    _task_ids: tuple[str, ...],
) -> bool:
    return True


def _implementation_checkpoint_effects() -> list[dict[str, str]]:
    task_payload = {
        "issue_number": 138,
        "operation": "application-materialize",
        "expected_change": _CHANGE,
        "change": _CHANGE,
        "branch": f"agent/{_CHANGE}",
        "base_sha": _REVISION,
        "message": "checkpoint verified task markers",
        "files": [
            {
                "path": f"openspec/changes/{_CHANGE}/tasks.md",
                "blob_sha": "b" * 40,
                "expected_sha": "c" * 40,
            }
        ],
        "pr_number": 178,
    }
    checkpoint_payload = {
        "issue_number": 138,
        "body": (
            "SLICE_CHECKPOINT\n"
            "Workflow: #138\n"
            f"Change: {_CHANGE}\n"
            "Action: implement-change\n"
            "Role: executor\n"
            "Completed-Tasks: 2.1, 2.2\n"
            f"Revision: {_REVISION}\n"
            "Application-Correlation: checkpoint-correlation\n"
            "Gate-Evidence: exact-head VERIFY\n"
            "Remaining-Approved-Boundary: continue with Slice 3"
        ),
    }
    return [
        {
            "kind": "github-mutation",
            "payload_json": json.dumps(task_payload),
        },
        {
            "kind": "issue-comment",
            "payload_json": json.dumps(checkpoint_payload),
        },
    ]


@pytest.mark.parametrize(
    "result_kind,requested_effects",
    (
        ("more-implementation-required", []),
        ("ready", []),
        ("more-implementation-required", _implementation_checkpoint_effects()[:1]),
        ("ready", _implementation_checkpoint_effects()[1:]),
    ),
)
def test_implement_completion_rejects_incomplete_checkpoint_effects(
    result_kind: str,
    requested_effects: list[dict[str, str]],
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    batch = parse_effect_batch(
        _raw(result_kind=result_kind, requested_effects=requested_effects),
        source,
    )
    applied: list[StagedEffect] = []
    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: pytest.fail("incomplete implementation advanced"),
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
    )

    assert not result.applied
    assert "implementation-checkpoint-incomplete" in result.reason
    assert applied == []


@pytest.mark.parametrize(
    "result_kind,successor",
    (
        ("more-implementation-required", "implement-change"),
        ("ready", "review-implementation"),
    ),
)
def test_implement_completion_derives_successor_after_task_then_checkpoint(
    result_kind: str,
    successor: str,
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    batch = parse_effect_batch(
        _raw(
            result_kind=result_kind,
            requested_effects=_implementation_checkpoint_effects(),
        ),
        source,
    )
    applied: list[StagedEffect] = []
    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: True,
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
        validate_implementation_checkpoint=_accept_checkpoint,
    )

    assert result.applied
    assert [effect.kind for effect in applied] == [
        "github-mutation",
        "issue-comment",
        "routing-transition",
    ]
    assert applied[-1].derived
    assert json.loads(applied[-1].payload_json) == {
        "issue_number": 138,
        "action": successor,
    }


def test_implement_completion_accepts_code_and_task_checkpoint_in_one_manifest() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    requested_effects = _implementation_checkpoint_effects()
    materialization = json.loads(requested_effects[0]["payload_json"])
    files = materialization["files"]
    assert isinstance(files, list)
    files.append(
        {
            "path": "src/investment_strategy/stage_one.py",
            "blob_sha": "d" * 40,
            "expected_sha": "e" * 40,
        }
    )
    requested_effects[0] = {
        "kind": "github-mutation",
        "payload_json": json.dumps(materialization),
    }
    batch = parse_effect_batch(
        _raw(
            result_kind="more-implementation-required",
            requested_effects=requested_effects,
        ),
        source,
    )
    applied: list[StagedEffect] = []
    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: True,
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
        validate_implementation_checkpoint=_accept_checkpoint,
    )

    assert result.applied
    assert [effect.kind for effect in applied] == [
        "github-mutation",
        "issue-comment",
        "routing-transition",
    ]


def test_implement_completion_rejects_reordered_or_duplicate_checkpoint_effects() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    effects = _implementation_checkpoint_effects()
    reordered = parse_effect_batch(
        _raw(
            result_kind="more-implementation-required",
            requested_effects=list(reversed(effects)),
        ),
        source,
    )
    duplicated = parse_effect_batch(
        _raw(
            result_kind="more-implementation-required",
            requested_effects=effects + [effects[1]],
        ),
        source,
    )

    for batch in (reordered, duplicated):
        applied: list[StagedEffect] = []
        result = apply_effect_batch(
            batch,
            fresh_preflight=_preflight,
            effect_guard=lambda _effect: pytest.fail("invalid checkpoint advanced"),
            apply_effect=applied.append,
            observe_postcondition=lambda _effect: True,
            current_revision=_REVISION,
        )
        assert not result.applied
        assert "implementation-checkpoint-incomplete" in result.reason
        assert applied == []


def _complete_checkpoint_body() -> str:
    return "\n".join(
        (
            "SLICE_CHECKPOINT",
            "Workflow: #138",
            f"Change: {_CHANGE}",
            "Action: implement-change",
            "Role: executor",
            "Completed-Tasks: 2.1, 2.2",
            f"Revision: {_REVISION}",
            "Application-Correlation: checkpoint-correlation",
            "Gate-Evidence: exact-head VERIFY",
            "Remaining-Approved-Boundary: continue with Slice 3",
        )
    )


def _checkpoint_effects_with_body(body: str) -> list[dict[str, str]]:
    effects = _implementation_checkpoint_effects()
    effects[1] = {
        "kind": "issue-comment",
        "payload_json": json.dumps({"issue_number": 138, "body": body}),
    }
    return effects


def _apply_completion_effects(
    requested_effects: list[dict[str, str]],
    validate_checkpoint: Callable[[effects.MaterializationRequest, tuple[str, ...]], bool]
    | None = None,
) -> tuple[effects.ApplyResult, list[StagedEffect]]:
    source = WorkerRequest(138, "executor", "implement-change")
    batch = parse_effect_batch(
        _raw(result_kind="more-implementation-required", requested_effects=requested_effects),
        source,
    )
    applied: list[StagedEffect] = []
    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: True,
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
        validate_implementation_checkpoint=validate_checkpoint,
    )
    return result, applied


def _invalid_checkpoint_bodies() -> tuple[str, ...]:
    valid = _complete_checkpoint_body()
    return (
        valid.replace("Workflow: #138", "Workflow: #139"),
        valid.replace("Change: simplify-scheduled-agent-control-plane", "Change: other-change"),
        valid.replace("Action: implement-change", "Action: review-implementation"),
        valid.replace(
            "Completed-Tasks: 2.1, 2.2",
            "Completed-Tasks: 2.1, 2.1",
        ),
        valid.replace(
            f"Revision: {_REVISION}",
            f"Revision: {_REVISION}\nRevision: {_REVISION}",
        ),
        valid.replace("Gate-Evidence: exact-head VERIFY", "Gate-Evidence: "),
        valid.replace(
            "Remaining-Approved-Boundary: continue with Slice 3",
            "Remaining-Approved-Boundary: ",
        ),
        valid + "\nUnexpected: value",
    )


@pytest.mark.parametrize("body", _invalid_checkpoint_bodies())
def test_implement_completion_rejects_ambiguous_checkpoint_body(body: str) -> None:
    result, applied = _apply_completion_effects(_checkpoint_effects_with_body(body))

    assert not result.applied
    assert "implementation-checkpoint-incomplete" in result.reason
    assert applied == []


def test_implement_completion_requires_executable_slice_validator() -> None:
    result, applied = _apply_completion_effects(_implementation_checkpoint_effects())

    assert not result.applied
    assert "implementation-checkpoint-incomplete" in result.reason
    assert applied == []


def test_implement_completion_rejects_multiple_slice_task_ids_at_application_boundary() -> None:
    body = _complete_checkpoint_body().replace(
        "Completed-Tasks: 2.1, 2.2",
        "Completed-Tasks: 2.1, 2.2, 3.1",
    )
    result, applied = _apply_completion_effects(
        _checkpoint_effects_with_body(body),
        lambda _request, task_ids: task_ids == ("2.1", "2.2"),
    )

    assert not result.applied
    assert "implementation-checkpoint-incomplete" in result.reason
    assert applied == []


def test_durable_task_markers_without_checkpoint_do_not_advance() -> None:
    result, applied = _apply_completion_effects(_implementation_checkpoint_effects()[:1])

    assert not result.applied
    assert "implementation-checkpoint-incomplete" in result.reason
    assert applied == []


def test_checkpoint_before_task_does_not_advance() -> None:
    result, applied = _apply_completion_effects(
        list(reversed(_checkpoint_effects_with_body(_complete_checkpoint_body())))
    )

    assert not result.applied
    assert "implementation-checkpoint-incomplete" in result.reason
    assert applied == []


def test_carrier_recovery_durably_checkpoints_exact_slice_on_later_wake() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    requested_effects = _implementation_checkpoint_effects()
    batch = parse_effect_batch(
        _raw(
            result_kind="more-implementation-required",
            requested_effects=requested_effects,
        ),
        source,
    )
    carrier_plan = make_carrier_plan(
        repository="owner/repo",
        issue_number=138,
        change=_CHANGE,
        action="implement-change",
        authorization_revision=_REVISION,
        operation="pull-request-ready",
        target={"pull_request_number": 178},
        expected={"head_sha": _REVISION},
        requested={"head_sha": _REVISION, "draft": False},
        expected_postcondition={"draft": False},
    )
    first_applied: list[StagedEffect] = []
    first_observed: list[StagedEffect] = []

    def first_apply(effect: StagedEffect) -> None:
        first_applied.append(effect)
        raise CarrierRequired(carrier_plan)

    def first_observe(effect: StagedEffect) -> bool:
        first_observed.append(effect)
        return True

    with pytest.raises(CarrierRequired):
        apply_effect_batch(
            batch,
            fresh_preflight=_preflight,
            effect_guard=lambda _effect: True,
            apply_effect=first_apply,
            observe_postcondition=first_observe,
            current_revision=_REVISION,
            validate_implementation_checkpoint=_accept_checkpoint,
        )

    assert [effect.kind for effect in first_applied] == ["github-mutation"]
    assert first_observed == []

    second_applied: list[StagedEffect] = []
    validation_calls: list[tuple[str, tuple[str, ...]]] = []

    def validate_checkpoint(
        request: effects.MaterializationRequest,
        task_ids: tuple[str, ...],
    ) -> bool:
        validation_calls.append((request.base_sha, task_ids))
        return request.base_sha == _REVISION and task_ids == ("2.1", "2.2")

    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: True,
        apply_effect=second_applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
        validate_implementation_checkpoint=validate_checkpoint,
    )

    assert result.applied
    assert [effect.kind for effect in second_applied] == [
        "github-mutation",
        "issue-comment",
        "routing-transition",
    ]
    assert validation_calls == [(_REVISION, ("2.1", "2.2"))]


def test_replay_accepts_already_durable_checkpoint_effects() -> None:
    requested_effects = _checkpoint_effects_with_body(_complete_checkpoint_body())
    durable: set[tuple[str, str]] = set()

    def apply_once(effect: StagedEffect) -> None:
        durable.add((effect.kind, effect.payload_json))

    first, _ = _apply_completion_effects(requested_effects, _accept_checkpoint)
    second = apply_effect_batch(
        parse_effect_batch(
            _raw(
                result_kind="more-implementation-required",
                requested_effects=requested_effects,
            ),
            WorkerRequest(138, "executor", "implement-change"),
        ),
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: True,
        apply_effect=apply_once,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
        validate_implementation_checkpoint=_accept_checkpoint,
    )

    assert first.applied
    assert second.applied
    assert len(durable) == 3


def test_terminal_result_derives_closed_terminal_effect() -> None:
    source = WorkerRequest(138, "lead", "finalize-archive")
    batch = parse_effect_batch(
        _raw(
            action="finalize-archive",
            role="lead",
            result_kind="lifecycle-complete",
            change=_CHANGE,
        ),
        source,
    )
    applied: list[StagedEffect] = []
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: _preflight(action="finalize-archive"),
        effect_guard=lambda _effect: True,
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
    )

    assert result.applied
    assert len(applied) == 1
    assert applied[0].kind == "terminal-transition"
    assert json.loads(applied[0].payload_json) == {
        "issue_number": 138,
        "expected_change": _CHANGE,
    }


def test_worker_cannot_submit_transition_authority() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    worker_route = {
        "kind": "routing-transition",
        "payload_json": json.dumps({"issue_number": 138, "action": "finalize-archive"}),
    }
    batch = parse_effect_batch(
        _raw(requested_effects=[worker_route]),
        source,
    )
    applied: list[StagedEffect] = []
    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=lambda _effect: pytest.fail("worker transition reached effect guard"),
        apply_effect=applied.append,
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
    )
    assert not result.applied
    assert "worker-transition-effect" in result.reason
    assert applied == []


def test_active_formal_route_rejects_connector_authored_direct_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "owner/repo"
    source = WorkerRequest(138, "executor", "implement-change")
    issue = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-08T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:implement-change"},
        ],
    }
    connector_comment = {
        "id": 1001,
        "body": (
            "ACTION_RESULT\n"
            "Workflow: #138\n"
            f"Change: {_CHANGE}\n"
            "Action: implement-change\n"
            "Role: executor\n"
            "Result: SPEC_BLOCKER\n"
        ),
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        del method, payload
        if path == "issues/138":
            return issue
        if path == "issues/138/comments?per_page=100&sort=created&direction=desc":
            return [connector_comment]
        raise AssertionError(f"unexpected GitHub call: {path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
    )
    effect = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps({"issue_number": 138, "action": "resolve-question"}),
        derived=True,
    )

    assert not adapter.guard(effect)


def test_active_terminal_rejects_connector_authored_premature_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "owner/repo"
    source = WorkerRequest(138, "lead", "finalize-archive")
    issue = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-08T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-archive"},
        ],
    }
    connector_comment = {
        "id": 1002,
        "body": (
            "ACTION_RESULT\n"
            "Workflow: #138\n"
            f"Change: {_CHANGE}\n"
            "Action: finalize-archive\n"
            "Role: lead\n"
            "Result: LIFECYCLE_COMPLETE\n"
        ),
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        del method, payload
        if path == "issues/138":
            return issue
        if path == "issues/138/comments?per_page=100&sort=created&direction=desc":
            return [connector_comment]
        raise AssertionError(f"unexpected GitHub call: {path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
    )
    effect = StagedEffect(
        kind="terminal-transition",
        payload_json=json.dumps({"issue_number": 138, "expected_change": _CHANGE}),
        derived=True,
    )

    assert not adapter.guard(effect)


def test_repository_actions_formal_transition_is_qualified_after_comment_postcondition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "owner/repo"
    source = WorkerRequest(138, "executor", "implement-change")
    issue: dict[str, object] = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-08T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:implement-change"},
        ],
    }
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="spec-blocker",
        request_comment_id=_REQUEST_COMMENT_ID,
        current_revision=_REVISION,
    )
    body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: implement-change\n"
        "Role: executor\n"
        "Result: SPEC_BLOCKER\n"
        f"Revision: {_REVISION}\n"
        f"Default-Branch-Revision: {_REVISION}\n"
        f"Application-Correlation: {correlation}\n"
        "Repository-derived successor: Lead / resolve-question\n"
        "Evidence: application postcondition\n"
    )
    actions_comment = {
        "id": 1003,
        "body": body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    patches: list[dict[str, object]] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        if path == "issues/138":
            if method == "PATCH":
                assert isinstance(payload, dict)
                patches.append(payload)
                labels = payload.get("labels")
                assert isinstance(labels, list)
                issue["labels"] = [{"name": label} for label in labels]
            return json.loads(json.dumps(issue))
        if path == "issues/138/comments?per_page=100&sort=created&direction=desc":
            return [actions_comment]
        if path == "issues/138/comments" and method == "POST":
            return actions_comment
        if path == "issues/comments/1003":
            return actions_comment
        raise AssertionError(f"unexpected GitHub call: {method} {path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
        current_revision=_REVISION,
        request_comment_id=_REQUEST_COMMENT_ID,
        expected_result_kind="spec-blocker",
    )
    requested = {
        "kind": "issue-comment",
        "payload_json": json.dumps({"issue_number": 138, "body": body}),
    }
    batch = parse_effect_batch(
        _raw(result_kind="spec-blocker", requested_effects=[requested]),
        source,
    )

    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=adapter.guard,
        apply_effect=adapter.apply,
        observe_postcondition=adapter.observe_postcondition,
        current_revision=_REVISION,
    )

    assert result.applied
    assert patches == [{"labels": ["action:resolve-question"]}]


def test_fresh_adapter_reconstructs_durable_formal_binding_without_local_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "owner/repo"
    source = WorkerRequest(138, "executor", "implement-change")
    issue: dict[str, object] = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-08T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:implement-change"},
        ],
    }
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="spec-blocker",
        request_comment_id=_REQUEST_COMMENT_ID,
        current_revision=_REVISION,
    )
    body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: implement-change\n"
        "Role: executor\n"
        "Result: SPEC_BLOCKER\n"
        f"Revision: {_REVISION}\n"
        f"Default-Branch-Revision: {_REVISION}\n"
        f"Application-Correlation: {correlation}\n"
        "Repository-derived successor: Lead / resolve-question\n"
        "Evidence: exact durable postcondition\n"
    )
    durable_comments: list[dict[str, object]] = []
    calls: list[tuple[str, str]] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        calls.append((path, method))
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        if path == "issues/138":
            if method == "PATCH":
                assert isinstance(payload, dict)
                labels = payload.get("labels")
                assert isinstance(labels, list)
                issue["labels"] = [{"name": label} for label in labels]
            return json.loads(json.dumps(issue))
        if path == "issues/138/comments?per_page=100&sort=created&direction=desc":
            return durable_comments
        if path == "issues/138/comments" and method == "POST":
            comment = {
                "id": 1003,
                "body": body,
                "user": {"login": "github-actions[bot]"},
                "performed_via_github_app": {"slug": "github-actions"},
            }
            durable_comments.append(comment)
            return comment
        if path == "issues/comments/1003":
            return durable_comments[0]
        raise AssertionError(f"unexpected GitHub call: {method} {path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    first_adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
        current_revision=_REVISION,
        request_comment_id=_REQUEST_COMMENT_ID,
        expected_result_kind="spec-blocker",
    )
    batch = parse_effect_batch(
        _raw(
            result_kind="spec-blocker",
            requested_effects=[
                {
                    "kind": "issue-comment",
                    "payload_json": json.dumps({"issue_number": 138, "body": body}),
                }
            ],
        ),
        source,
    )
    first_result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=first_adapter.guard,
        apply_effect=first_adapter.apply,
        observe_postcondition=first_adapter.observe_postcondition,
        current_revision=_REVISION,
    )
    assert first_result.applied
    assert len(durable_comments) == 1
    assert not hasattr(first_adapter, "_formal_evidence_observed")

    issue["labels"] = [
        {"name": "agent:executor"},
        {"name": "action:implement-change"},
    ]
    fresh_adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
        current_revision=_REVISION,
        request_comment_id=_REQUEST_COMMENT_ID,
        expected_result_kind="spec-blocker",
    )
    derived = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps(
            {"issue_number": 138, "action": "resolve-question"},
            sort_keys=True,
        ),
        derived=True,
    )

    assert fresh_adapter.guard(derived)
    assert calls.count(("issues/138/comments?per_page=100&sort=created&direction=desc", "GET")) >= 2
    assert calls.count(("issues/138/comments", "POST")) == 1


def test_application_bindings_are_collision_resistant_and_do_not_alias_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "owner/repo"
    source = WorkerRequest(138, "executor", "implement-change")
    issue = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-08T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:implement-change"},
        ],
    }
    first_id = _REQUEST_COMMENT_ID
    second_id = first_id + 1
    first_correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="spec-blocker",
        current_revision=_REVISION,
        request_comment_id=first_id,
    )
    second_correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="spec-blocker",
        current_revision=_REVISION,
        request_comment_id=second_id,
    )
    assert first_correlation != second_correlation
    body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: implement-change\n"
        "Role: executor\n"
        "Result: SPEC_BLOCKER\n"
        f"Revision: {_REVISION}\n"
        f"Application-Correlation: {first_correlation}\n"
        "Evidence-Ref: issuecomment-first\n"
    )
    actions_comment = {
        "id": 1005,
        "body": body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        if path == "issues/138":
            return issue
        if path == "issues/138/comments?per_page=100&sort=created&direction=desc":
            return [actions_comment]
        raise AssertionError(f"unexpected GitHub call: {path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
        current_revision=_REVISION,
        expected_result_kind="spec-blocker",
        request_comment_id=second_id,
    )
    effect = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps(
            {"issue_number": 138, "action": "resolve-question"},
            sort_keys=True,
        ),
        derived=True,
    )

    assert not adapter.guard(effect)
    actions_comment["body"] = body.replace(
        f"Application-Correlation: {first_correlation}\n",
        f"Evidence-Ref: {second_correlation}\n",
    )
    assert not adapter.guard(effect)


def test_known_effect_guard_rejection_exposes_same_evaluation_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    issue = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-08T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:implement-change"},
        ],
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        if path == "issues/138":
            return issue
        if path == "pulls/178":
            return {}
        raise AssertionError(f"unexpected GitHub call: {path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        "owner/repo",
        "token",
        source,
        authorized_change=_CHANGE,
        current_revision=_REVISION,
        request_comment_id=_REQUEST_COMMENT_ID,
        expected_result_kind="spec-blocker",
    )
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "pull-request-ready",
                "number": 178,
                "expected_head_sha": "b" * 40,
            }
        ),
    )
    batch = parse_effect_batch(
        _raw(
            result_kind="spec-blocker",
            requested_effects=[{"kind": effect.kind, "payload_json": effect.payload_json}],
        ),
        source,
    )
    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=adapter.guard,
        apply_effect=lambda _effect: pytest.fail("rejected effect mutated"),
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
        effect_rejection=adapter.effect_rejection,
    )

    assert not result.applied
    assert result.rejection is not None
    assert result.rejection.classification.value == "effect-precondition-unsatisfied"
    assert result.rejection.observed == effect.payload_json


def test_change_unset_preactivation_route_remains_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issue = {
        "number": 138,
        "state": "open",
        "body": "Change: unset\n",
        "created_at": "2026-09-08T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:propose-change"},
        ],
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        del method, payload
        if path == "issues/138":
            return issue
        raise AssertionError(f"unexpected GitHub call: {path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        "owner/repo",
        "token",
        WorkerRequest(138, "lead", "propose-change"),
        authorized_change="unset",
    )
    effect = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps({"issue_number": 138, "action": "explore-change"}),
        derived=True,
    )

    assert adapter.guard(effect)


def test_stale_or_unqualified_source_fails_closed() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    batch = parse_effect_batch(_raw(), source)
    stale = _preflight(action="review-implementation")
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: stale,
        effect_guard=lambda _effect: True,
        apply_effect=lambda _effect: pytest.fail("stale source mutated"),
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
    )
    assert not result.applied

    unqualified = _preflight(human_authorized=False)
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: unqualified,
        effect_guard=lambda _effect: True,
        apply_effect=lambda _effect: pytest.fail("unqualified source mutated"),
        observe_postcondition=lambda _effect: True,
        current_revision=_REVISION,
    )
    assert not result.applied


def test_effect_contract_has_explicit_merge_actions_and_no_content_mutation() -> None:
    merge_ops = allowed_github_mutation_operations("executor", "merge-implementation-pr")
    archive_ops = allowed_github_mutation_operations("executor", "merge-archive-pr")
    assert merge_ops == frozenset({"pull-request-merge", "ref-delete"})
    assert archive_ops == merge_ops
    assert all(not operation.startswith("contents-") for operation in merge_ops)
    with pytest.raises(ValueError):
        allowed_github_mutation_operations("executor", "merge-pr")


def test_supported_effect_guard_rejects_content_and_routing_label_mutation() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    content = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "contents-upsert",
                "path": "README.md",
            }
        ),
    )
    assert not supported_effect_guard(source, content)

    label = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "issue-label-add",
                "label": "action:merge-archive-pr",
            }
        ),
    )
    assert not supported_effect_guard(source, label)


@pytest.mark.parametrize("label", ("human:approved", "intake:approved"))
def test_worker_cannot_mutate_reserved_authority_labels(label: str) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "issue-label-add",
                "label": label,
            }
        ),
    )

    assert not supported_effect_guard(source, effect)


def test_merged_carrier_merge_is_idempotent_without_put(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    change = "prevent-native-closing-bypass"
    source = WorkerRequest(159, "executor", "merge-implementation-pr")
    expected_head = "b" * 40
    pr = {
        "number": 167,
        "state": "closed",
        "merged": True,
        "body": "Implementation\n\nRefs #159\n",
        "head": {
            "ref": f"agent/{change}",
            "sha": expected_head,
            "repo": {"full_name": "owner/repo"},
        },
        "base": {
            "ref": "main",
            "repo": {"full_name": "owner/repo"},
        },
        "merge_commit_sha": "c" * 40,
        "merged_at": "2026-08-27T06:00:00Z",
    }
    issue = {
        "number": 159,
        "state": "open",
        "body": f"Change: {change}",
        "labels": [{"name": "action:merge-implementation-pr"}],
        "created_at": "2026-08-27T05:00:00Z",
        "closed_at": None,
    }
    calls: list[tuple[str, str]] = []
    correlation = formal_application_correlation(
        source,
        change=change,
        result_kind="merged",
        request_comment_id=_REQUEST_COMMENT_ID,
        current_revision=_REVISION,
    )
    formal_body = (
        "MERGE_RESULT\n"
        "Workflow: #159\n"
        f"Change: {change}\n"
        "Action: merge-implementation-pr\n"
        "Role: executor\n"
        "Result: MERGED\n"
        f"Revision: {expected_head}\n"
        f"Default-Branch-Revision: {_REVISION}\n"
        f"Application-Correlation: {correlation}\n"
        "Repository-derived successor: Lead / finalize-change\n"
        "Evidence: carrier recovery formal transition qualification"
    )
    actions_comment = {
        "id": 992,
        "body": formal_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        calls.append((path, method))
        if path == "issues/159/comments?per_page=100&sort=created&direction=desc":
            return [actions_comment]
        if path == "issues/159/comments" and method == "POST":
            return actions_comment
        if path == "issues/comments/992":
            return actions_comment
        if path == "issues/159" and method == "PATCH":
            labels = payload["labels"] if isinstance(payload, dict) else []
            issue["labels"] = [{"name": name} for name in labels]
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        return issue

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        "owner/repo",
        "token",
        source,
        authorized_change=change,
        current_revision=_REVISION,
        request_comment_id=_REQUEST_COMMENT_ID,
        expected_result_kind="merged",
    )
    monkeypatch.setattr(adapter, "_source_still_current", lambda: True)
    monkeypatch.setattr(adapter, "_current_issue", lambda: issue)
    monkeypatch.setattr(
        adapter,
        "_source_pull_request",
        lambda _number, require_open: pr,
    )
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 159,
                "operation": "pull-request-merge",
                "number": 167,
                "expected_head_sha": expected_head,
                "merge_method": "merge",
            }
        ),
    )
    formal_effect = StagedEffect(
        kind="issue-comment",
        payload_json=json.dumps({"issue_number": 159, "body": formal_body}),
    )
    raw = json.dumps(
        {
            "issue_number": 159,
            "role": "executor",
            "action": "merge-implementation-pr",
            "change": change,
            "result_kind": "merged",
            "result_content": "MERGE_RESULT",
            "requested_effects": [
                {"kind": effect.kind, "payload_json": effect.payload_json},
                {"kind": formal_effect.kind, "payload_json": formal_effect.payload_json},
            ],
        }
    )
    batch = parse_effect_batch(raw, source)
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: _preflight(
            issue_number=159,
            action="merge-implementation-pr",
            change=change,
        ),
        effect_guard=adapter.guard,
        apply_effect=adapter.apply,
        observe_postcondition=adapter.observe_postcondition,
        current_revision=_REVISION,
    )
    assert result.applied
    assert not any(path.endswith("/merge") and method == "PUT" for path, method in calls)


def test_issue_comment_reuses_existing_bot_comment_without_post(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "royhsu-work/investment-strategy"
    source = WorkerRequest(138, "lead", "finalize-change")
    body = (
        "ARCHIVE_REQUEST\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: finalize-change\n"
        f"Revision: {_REVISION}"
    )
    issue = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "labels": [{"name": "action:finalize-change"}],
    }
    existing = {
        "id": 991,
        "body": body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    calls: list[tuple[str, str]] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        calls.append((api_path, method))
        if api_path == "issues/138":
            return issue
        if api_path == "issues/138/comments?per_page=100&sort=created&direction=desc":
            return [existing]
        if api_path == "issues/comments/991":
            return existing
        if method == "POST":
            raise AssertionError("replayed issue comment must not be created")
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
    )
    effect = StagedEffect(
        kind="issue-comment",
        payload_json=json.dumps({"issue_number": 138, "body": body}),
    )

    adapter.apply(effect)
    assert adapter.observe_postcondition(effect)

    assert calls == [
        ("issues/138/comments?per_page=100&sort=created&direction=desc", "GET"),
        ("issues/comments/991", "GET"),
    ]


def test_issue_comment_does_not_reuse_connector_authored_formal_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "royhsu-work/investment-strategy"
    source = WorkerRequest(138, "lead", "finalize-change")
    body = "ACTION_RESULT\nResult: ARCHIVE_READY"
    connector_comment = {
        "id": 991,
        "body": body,
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }
    actions_comment = {
        "id": 992,
        "body": body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    calls: list[tuple[str, str]] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        del payload
        calls.append((api_path, method))
        if api_path == "issues/138/comments?per_page=100&sort=created&direction=desc":
            return [connector_comment]
        if api_path == "issues/138/comments" and method == "POST":
            return actions_comment
        if api_path == "issues/comments/992":
            return actions_comment
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
    )
    effect = StagedEffect(
        kind="issue-comment",
        payload_json=json.dumps({"issue_number": 138, "body": body}),
    )

    adapter.apply(effect)
    assert adapter.observe_postcondition(effect)

    assert calls == [
        ("issues/138/comments?per_page=100&sort=created&direction=desc", "GET"),
        ("issues/138/comments", "POST"),
        ("issues/comments/992", "GET"),
    ]


def test_empty_github_api_path_uses_repository_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urls: list[str] = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"default_branch":"main"}'

    def fake_urlopen(request: object, timeout: int) -> FakeResponse:
        assert timeout == 30
        url = getattr(request, "full_url", None)
        assert isinstance(url, str)
        urls.append(url)
        return FakeResponse()

    monkeypatch.setattr(effects, "urlopen", fake_urlopen)

    assert effects._github_json("owner/repo", "token", "") == {"default_branch": "main"}
    assert urls == ["https://api.github.com/repos/owner/repo"]


def test_transition_validator_is_not_a_runtime_dependency() -> None:
    source = inspect.getsource(apply_effect_batch)
    assert "topology" not in source
    assert "workflow_text" not in source


def test_routing_transition_replaces_all_routing_labels_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "royhsu-work/investment-strategy"
    source = WorkerRequest(138, "executor", "implement-change")
    issue: dict[str, object] = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-03T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:implement-change"},
            {"name": "human:notified"},
            {"name": "priority"},
        ],
    }
    patches: list[dict[str, object]] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        **_kwargs: object,
    ) -> object:
        if api_path == "issues/138" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path == "issues/138" and method == "PATCH":
            assert payload is not None
            labels = payload.get("labels")
            assert isinstance(labels, list)
            patches.append(payload)
            issue["labels"] = [{"name": name} for name in labels]
            return json.loads(json.dumps(issue))
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(
        "investment_strategy.scheduled_agent_effects._github_json",
        fake_github_json,
    )
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
    )
    effect = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps({"issue_number": 138, "action": "resolve-question"}),
        derived=True,
    )

    adapter.apply(effect)

    assert patches == [
        {
            "labels": ["human:notified", "priority", "action:resolve-question"],
        }
    ]
    assert adapter.observe_postcondition(effect)


def test_terminal_transition_closes_and_clears_routing_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "royhsu-work/investment-strategy"
    source = WorkerRequest(138, "lead", "finalize-archive")
    issue: dict[str, object] = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-03T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-archive"},
            {"name": "human:notified"},
        ],
    }
    patches: list[dict[str, object]] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        **_kwargs: object,
    ) -> object:
        if api_path == "issues/138" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path == "issues/138" and method == "PATCH":
            assert payload is not None
            state = payload.get("state")
            labels = payload.get("labels")
            assert state == "closed"
            assert isinstance(labels, list)
            patches.append(payload)
            issue["state"] = state
            issue["labels"] = [{"name": name} for name in labels]
            return json.loads(json.dumps(issue))
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(
        "investment_strategy.scheduled_agent_effects._github_json",
        fake_github_json,
    )
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
    )
    effect = StagedEffect(
        kind="terminal-transition",
        payload_json=json.dumps({"issue_number": 138, "expected_change": _CHANGE}),
        derived=True,
    )

    adapter.apply(effect)

    assert patches == [{"state": "closed", "labels": ["human:notified"]}]
    assert adapter.observe_postcondition(effect)


def test_github_adapter_binds_pr_and_ref_targets_to_authorized_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "royhsu-work/investment-strategy"
    source = WorkerRequest(138, "executor", "implement-change")
    head_sha = "b" * 40
    issue = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-03T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "agent:executor"}, {"name": "action:implement-change"}],
    }

    def pull_request(number: int, branch: str) -> dict[str, object]:
        return {
            "number": number,
            "state": "open",
            "merged": False,
            "body": "Implementation\n\nRefs #138\n",
            "head": {
                "ref": branch,
                "sha": head_sha,
                "repo": {"full_name": repository},
            },
            "base": {
                "ref": "main",
                "repo": {"full_name": repository},
            },
        }

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        **_kwargs: object,
    ) -> object:
        if api_path == "issues/138":
            return issue
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "pulls/178":
            return pull_request(178, "agent/simplify-scheduled-agent-control-plane")
        if api_path == "pulls/167":
            return pull_request(167, "agent/other-change")
        if api_path == "git/ref/heads/agent/simplify-scheduled-agent-control-plane":
            return {"object": {"sha": head_sha}}
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(
        "investment_strategy.scheduled_agent_effects._github_json",
        fake_github_json,
    )
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
    )
    correct_pr = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "pull-request-update",
                "number": 178,
                "expected_head_sha": head_sha,
                "fields": {"title": "updated"},
            }
        ),
    )
    foreign_pr = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "pull-request-update",
                "number": 167,
                "expected_head_sha": head_sha,
                "fields": {"title": "updated"},
            }
        ),
    )
    assert adapter.guard(correct_pr)
    assert not adapter.guard(foreign_pr)

    issue["labels"] = [
        {"name": "agent:executor"},
        {"name": "action:merge-implementation-pr"},
    ]
    merge_source = WorkerRequest(138, "executor", "merge-implementation-pr")
    ref_adapter = GitHubEffectAdapter(
        repository,
        "token",
        merge_source,
        authorized_change=_CHANGE,
    )
    correct_ref = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "ref-delete",
                "ref": "refs/heads/agent/simplify-scheduled-agent-control-plane",
                "expected_sha": head_sha,
            }
        ),
    )
    foreign_ref = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "ref-delete",
                "ref": "refs/heads/agent/other-change",
                "expected_sha": head_sha,
            }
        ),
    )

    assert ref_adapter.guard(correct_ref)
    assert not ref_adapter.guard(foreign_ref)


def test_application_archive_workflow_dispatch_is_exact_revision_and_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "royhsu-work/investment-strategy"
    source = WorkerRequest(138, "lead", "finalize-change")
    revision = "d" * 40
    request_key = f"archive-138-{revision}"
    issue = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-04T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "agent:lead"}, {"name": "action:finalize-change"}],
    }
    runs: list[dict[str, object]] = []
    dispatches: list[object] = []
    dispatch_visibility_reads = 0

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        if api_path == "issues/138":
            return issue
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main":
            return {"object": {"sha": revision}}
        if api_path == (
            "actions/workflows/openspec-archive.yml/runs"
            "?event=workflow_dispatch&branch=main&per_page=100"
        ):
            nonlocal dispatch_visibility_reads
            dispatch_visibility_reads += 1
            if dispatch_visibility_reads < 3:
                return {"workflow_runs": []}
            return {"workflow_runs": list(runs)}
        if api_path == "actions/workflows/openspec-archive.yml/dispatches" and method == "POST":
            assert isinstance(payload, dict)
            dispatches.append(payload)
            inputs = payload["inputs"]
            assert isinstance(inputs, dict)
            runs.append(
                {
                    "id": 1201,
                    "display_title": f"OpenSpec Archive {inputs['request_key']}",
                    "event": "workflow_dispatch",
                    "path": ".github/workflows/openspec-archive.yml",
                    "head_branch": "main",
                    "head_sha": revision,
                }
            )
            return None
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    monkeypatch.setattr(effects.time, "sleep", lambda _seconds: None)
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
        current_revision=revision,
    )
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "workflow-dispatch",
                "workflow_id": "openspec-archive.yml",
                "ref": "main",
                "inputs": {
                    "change": _CHANGE,
                    "issue": "138",
                    "revision": revision,
                    "request_key": request_key,
                },
            }
        ),
    )

    assert adapter.guard(effect)
    adapter.apply(effect)
    assert adapter.observe_postcondition(effect)
    adapter.apply(effect)
    assert adapter.observe_postcondition(effect)
    assert dispatches == [
        {
            "ref": "main",
            "inputs": {
                "change": _CHANGE,
                "issue": "138",
                "revision": revision,
                "request_key": request_key,
            },
        }
    ]


def test_issue_comment_reuses_existing_bot_comment_on_later_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "royhsu-work/investment-strategy"
    source = WorkerRequest(138, "lead", "finalize-change")
    body = (
        "ARCHIVE_REQUEST\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: finalize-change\n"
        f"Revision: {_REVISION}"
    )
    existing = {
        "id": 992,
        "body": body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    first_page = [
        {
            "id": index,
            "body": f"unrelated-{index}",
            "user": {"login": "github-actions[bot]"},
            "performed_via_github_app": {"slug": "github-actions"},
        }
        for index in range(100)
    ]
    calls: list[str] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        del method, payload
        calls.append(api_path)
        if api_path == "issues/138/comments?per_page=100&sort=created&direction=desc":
            return first_page
        if api_path == ("issues/138/comments?per_page=100&sort=created&direction=desc&page=2"):
            return [existing]
        if api_path == "issues/comments/992":
            return existing
        raise AssertionError(f"unexpected GitHub call: {api_path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        repository,
        "token",
        source,
        authorized_change=_CHANGE,
    )
    effect = StagedEffect(
        kind="issue-comment",
        payload_json=json.dumps({"issue_number": 138, "body": body}),
    )

    adapter.apply(effect)
    assert calls == [
        "issues/138/comments?per_page=100&sort=created&direction=desc",
        "issues/138/comments?per_page=100&sort=created&direction=desc&page=2",
    ]
    assert adapter.observe_postcondition(effect)


def test_archive_pull_request_create_binds_exact_branch_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "owner/repo"
    source = WorkerRequest(138, "lead", "finalize-change")
    base_revision = "c" * 40
    archive_revision = "b" * 40
    branch = f"agent/archive-{_CHANGE}"
    body = (
        "Archive OpenSpec change `simplify-scheduled-agent-control-plane`.\n\n"
        "This pull request is the repository-owned final archive snapshot. "
        "Its non-closing linkage preserves traceability while the coordination Issue "
        "remains open; independent Reviewer PASS, unchanged-head verification, "
        "current gates, and Lead terminal finalization remain required.\n\n"
        "Refs #138"
    )
    issue = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "labels": [{"name": "action:finalize-change"}],
        "created_at": "2026-09-04T00:00:00Z",
        "closed_at": None,
    }
    pull_request = {
        "number": 200,
        "state": "open",
        "merged": False,
        "title": "Archive OpenSpec change simplify-scheduled-agent-control-plane",
        "body": body,
        "draft": False,
        "head": {
            "ref": branch,
            "sha": archive_revision,
            "repo": {"full_name": repository},
        },
        "base": {
            "ref": "main",
            "sha": base_revision,
            "repo": {"full_name": repository},
        },
    }
    calls: list[tuple[str, str]] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        calls.append((path, method))
        if path == "issues/138":
            return issue
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": base_revision}}
        if path == f"git/ref/heads/{branch}":
            return {"object": {"sha": archive_revision}}
        if path.startswith("pulls?state=all"):
            return []
        if path == "pulls" and method == "POST":
            return {"number": 200}
        if path == "pulls/200":
            return pull_request
        raise AssertionError(f"unexpected GitHub call: {method} {path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        repository,
        archive_revision,
        source,
        authorized_change=_CHANGE,
        current_revision=base_revision,
    )
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "pull-request-create",
                "title": "Archive OpenSpec change simplify-scheduled-agent-control-plane",
                "body": body,
                "head": branch,
                "base": "main",
                "draft": False,
                "expected_head_sha": archive_revision,
            }
        ),
    )

    assert adapter.guard(effect)
    with pytest.raises(CarrierRequired) as raised:
        adapter.apply(effect)
    plan = raised.value.plan
    assert plan.operation == "pull-request-create"
    assert plan.requested["head_sha"] == archive_revision
    assert plan.force is False
    assert ("pulls", "POST") not in calls


def test_archive_pull_request_create_reuses_exact_existing_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "owner/repo"
    source = WorkerRequest(138, "lead", "finalize-change")
    base_revision = "c" * 40
    archive_revision = "b" * 40
    branch = f"agent/archive-{_CHANGE}"
    title = "Archive exact carrier"
    body = "Refs #138"
    existing = {
        "number": 200,
        "state": "open",
        "merged": False,
        "title": title,
        "body": body,
        "draft": False,
        "head": {
            "ref": branch,
            "sha": archive_revision,
            "repo": {"full_name": repository},
        },
        "base": {
            "ref": "main",
            "sha": base_revision,
            "repo": {"full_name": repository},
        },
    }
    observation = GitHubIssueObservation(
        issue_number=138,
        change=_CHANGE,
        routing=("lead", "finalize-change"),
        state="open",
        created_order=1,
        authoritative=True,
    )
    calls: list[tuple[str, str]] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        del payload
        calls.append((path, method))
        if path == f"git/ref/heads/{branch}":
            return {"object": {"sha": archive_revision}}
        if path == "git/ref/heads/main":
            return {"object": {"sha": base_revision}}
        if path.startswith("pulls?state=all"):
            return [existing]
        if path == "pulls/200":
            return existing
        if method == "POST":
            raise AssertionError("exact existing archive PR must be reused")
        raise AssertionError(f"unexpected GitHub call: {method} {path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        repository,
        archive_revision,
        source,
        authorized_change=_CHANGE,
        current_revision=base_revision,
    )
    monkeypatch.setattr(adapter, "_source_still_current", lambda: True)
    monkeypatch.setattr(adapter, "_authorized_issue_observation", lambda _current=None: observation)
    monkeypatch.setattr(adapter, "_default_branch", lambda: "main")
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "pull-request-create",
                "title": title,
                "body": body,
                "head": branch,
                "base": "main",
                "draft": False,
                "expected_head_sha": archive_revision,
            }
        ),
    )

    assert adapter.guard(effect)
    adapter.apply(effect)
    assert adapter.observe_postcondition(effect)
    assert ("pulls", "POST") not in calls


def test_non_merge_carrier_recovery_observes_current_postcondition_without_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    head_sha = "b" * 40
    issue = {
        "number": 138,
        "state": "open",
        "body": f"Change: {_CHANGE}\n",
        "created_at": "2026-09-08T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:implement-change"},
        ],
    }
    pull_request = {
        "number": 178,
        "state": "open",
        "merged": False,
        "draft": True,
        "body": "Implementation\n\nRefs #138\n",
        "head": {
            "ref": f"agent/{_CHANGE}",
            "sha": head_sha,
            "repo": {"full_name": "owner/repo"},
        },
        "base": {
            "ref": "main",
            "repo": {"full_name": "owner/repo"},
        },
    }
    calls: list[tuple[str, str]] = []
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="spec-blocker",
        request_comment_id=_REQUEST_COMMENT_ID,
        current_revision=_REVISION,
    )
    formal_body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: implement-change\n"
        "Role: executor\n"
        "Result: SPEC_BLOCKER\n"
        f"Revision: {_REVISION}\n"
        f"Default-Branch-Revision: {_REVISION}\n"
        f"Application-Correlation: {correlation}\n"
        "Repository-derived successor: Lead / resolve-question\n"
        "Evidence: carrier recovery formal transition qualification"
    )
    actions_comment = {
        "id": 992,
        "body": formal_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        calls.append((path, method))
        if path == "issues/138/comments?per_page=100&sort=created&direction=desc":
            return [actions_comment]
        if path == "issues/138/comments" and method == "POST":
            return actions_comment
        if path == "issues/comments/992":
            return actions_comment
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        if path == "issues/138":
            if method == "PATCH" and isinstance(payload, dict):
                labels = payload.get("labels")
                if isinstance(labels, list):
                    issue["labels"] = [
                        {"name": label} for label in labels if isinstance(label, str)
                    ]
            return issue
        if path == "pulls/178":
            return pull_request
        raise AssertionError(f"unexpected GitHub call: {method} {path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "pull-request-ready",
                "number": 178,
                "expected_head_sha": head_sha,
            }
        ),
    )
    first_adapter = GitHubEffectAdapter(
        "owner/repo",
        "token",
        source,
        authorized_change=_CHANGE,
        current_revision=_REVISION,
    )

    with pytest.raises(CarrierRequired) as raised:
        first_adapter.apply(effect)

    assert raised.value.plan.operation == "pull-request-ready"
    assert raised.value.plan.requested["draft"] is False

    pull_request["draft"] = False
    calls.clear()
    second_adapter = GitHubEffectAdapter(
        "owner/repo",
        "token",
        source,
        authorized_change=_CHANGE,
        current_revision=_REVISION,
        request_comment_id=_REQUEST_COMMENT_ID,
        expected_result_kind="spec-blocker",
    )
    formal_effect = StagedEffect(
        kind="issue-comment",
        payload_json=json.dumps({"issue_number": 138, "body": formal_body}),
    )
    batch = parse_effect_batch(
        _raw(
            result_kind="spec-blocker",
            requested_effects=[
                {
                    "kind": effect.kind,
                    "payload_json": effect.payload_json,
                },
                {
                    "kind": formal_effect.kind,
                    "payload_json": formal_effect.payload_json,
                },
            ],
        ),
        source,
    )

    result = apply_effect_batch(
        batch,
        fresh_preflight=_preflight,
        effect_guard=second_adapter.guard,
        apply_effect=second_adapter.apply,
        observe_postcondition=second_adapter.observe_postcondition,
        current_revision=_REVISION,
    )

    assert result.applied
    assert calls.count(("issues/138", "PATCH")) == 1
    assert all(path != "pulls/178" or method == "GET" for path, method in calls)
    assert issue["labels"] == [
        {"name": "action:resolve-question"},
    ]


def test_merge_carrier_recovery_rejects_old_authorization_after_main_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(159, "executor", "merge-implementation-pr")
    change = "prevent-native-closing-bypass"
    old_revision = "a" * 40
    new_revision = "c" * 40
    current_main_revision = old_revision
    expected_head = "b" * 40
    issue = {
        "number": 159,
        "state": "open",
        "body": f"Change: {change}\n",
        "created_at": "2026-09-08T00:00:00Z",
        "closed_at": None,
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:merge-implementation-pr"},
        ],
    }
    pull_request = {
        "number": 167,
        "state": "open",
        "merged": False,
        "body": "Implementation\n\nRefs #159\n",
        "head": {
            "ref": f"agent/{change}",
            "sha": expected_head,
            "repo": {"full_name": "owner/repo"},
        },
        "base": {
            "ref": "main",
            "repo": {"full_name": "owner/repo"},
        },
    }
    calls: list[tuple[str, str]] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
        **_kwargs: object,
    ) -> object:
        calls.append((path, method))
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": current_main_revision}}
        if path == "issues/159":
            return issue
        if path == "pulls/167":
            return pull_request
        raise AssertionError(f"unexpected GitHub call: {method} {path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 159,
                "operation": "pull-request-merge",
                "number": 167,
                "expected_head_sha": expected_head,
                "merge_method": "merge",
            }
        ),
    )
    first_adapter = GitHubEffectAdapter(
        "owner/repo",
        "token",
        source,
        authorized_change=change,
        current_revision=old_revision,
    )

    with pytest.raises(CarrierRequired):
        first_adapter.apply(effect)

    current_main_revision = new_revision
    calls.clear()
    fresh_adapter = GitHubEffectAdapter(
        "owner/repo",
        "token",
        source,
        authorized_change=change,
        current_revision=old_revision,
    )
    raw = json.dumps(
        {
            "issue_number": 159,
            "role": "executor",
            "action": "merge-implementation-pr",
            "change": change,
            "result_kind": "merged",
            "result_content": "MERGE_RESULT",
            "requested_effects": [
                {
                    "kind": effect.kind,
                    "payload_json": effect.payload_json,
                }
            ],
        }
    )
    batch = parse_effect_batch(raw, source)
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: _preflight(
            issue_number=159,
            action="merge-implementation-pr",
            change=change,
        ),
        effect_guard=fresh_adapter.guard,
        apply_effect=fresh_adapter.apply,
        observe_postcondition=fresh_adapter.observe_postcondition,
        current_revision=old_revision,
    )

    assert not result.applied
    assert result.reason == "effect precondition rejected"
    assert not any(method != "GET" for _path, method in calls)
