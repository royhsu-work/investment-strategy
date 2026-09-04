"""Focused tests for typed Action-result application and exact effect guards."""

from __future__ import annotations

import inspect
import json

import pytest

import investment_strategy.scheduled_agent_effects as effects
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
        if path == "issues/159" and method == "PATCH":
            labels = payload["labels"] if isinstance(payload, dict) else []
            issue["labels"] = [{"name": name} for name in labels]
        return issue

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        "owner/repo",
        "token",
        source,
        authorized_change=change,
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
    raw = json.dumps(
        {
            "issue_number": 159,
            "role": "executor",
            "action": "merge-implementation-pr",
            "change": change,
            "result_kind": "merged",
            "result_content": "MERGE_RESULT",
            "requested_effects": [{"kind": effect.kind, "payload_json": effect.payload_json}],
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

    assert calls == [
        ("issues/138/comments?per_page=100&sort=created&direction=desc", "GET"),
    ]
    assert adapter.observe_postcondition(effect)


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
    }
    first_page = [
        {
            "id": index,
            "body": f"unrelated-{index}",
            "user": {"login": "github-actions[bot]"},
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
        "This pull request is the repository-owned final archive snapshot. Its non-closing linkage "
        "preserves traceability while the coordination Issue remains open; independent Reviewer PASS, "
        "unchanged-head verification, current gates, and Lead terminal finalization remain required.\n\n"
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
    adapter.apply(effect)
    assert adapter.observe_postcondition(effect)
    assert ("pulls", "POST") in calls