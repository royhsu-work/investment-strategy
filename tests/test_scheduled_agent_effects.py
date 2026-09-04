"""Focused tests for typed Action-result application and exact effect guards."""

from __future__ import annotations

import inspect
import json

import pytest

from investment_strategy.scheduled_agent_action_model import ResultKind
from investment_strategy.scheduled_agent_effect_contract import (
    allowed_github_mutation_operations,
)
from investment_strategy.scheduled_agent_effects import (
    GitHubEffectAdapter,
    StagedEffect,
    apply_effect_batch,
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


def test_transition_validator_is_not_a_runtime_dependency() -> None:
    source = inspect.getsource(apply_effect_batch)
    assert "topology" not in source
    assert "workflow_text" not in source


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
    foreign_ref = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 138,
                "operation": "ref-update",
                "ref": "refs/heads/agent/other-change",
                "expected_sha": head_sha,
                "sha": "c" * 40,
            }
        ),
    )

    assert adapter.guard(correct_pr)
    assert not adapter.guard(foreign_pr)
    assert not adapter.guard(foreign_ref)
