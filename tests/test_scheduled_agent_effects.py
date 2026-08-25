"""Fresh effect-application and continuation regressions for #133 Slice 4C/4D."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_effects as effects
from investment_strategy.scheduled_agent_effect_contract import (
    allowed_github_mutation_operations,
    mapped_role_actions,
)
from investment_strategy.scheduled_agent_effects import (
    EffectBatch,
    GitHubEffectAdapter,
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
                {"kind": effect.kind, "payload_json": effect.payload_json} for effect in effects
            ],
        }
    )


def _terminal_retirement_effect(change: str = "archived-change") -> StagedEffect:
    return StagedEffect(
        kind="terminal-retirement",
        payload_json=json.dumps({"issue_number": 133, "expected_change": change}),
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


def test_same_action_remaining_work_also_requires_fresh_worker() -> None:
    source = _request()
    assert continuation_requires_fresh_wake(source, source)


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
                '{"issue_number":133,"role":"reviewer","action":"review-implementation"}'
            ),
        ),
    )
    assert supported_effect_guard(
        source,
        StagedEffect(
            kind="github-mutation",
            payload_json=json.dumps(
                {
                    "issue_number": 133,
                    "operation": "contents-upsert",
                    "path": "src/example.py",
                    "branch": "agent/example",
                    "message": "Update example",
                    "content": "print('ok')\n",
                    "expected_sha": None,
                }
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
        _request(role="reviewer", action="review-implementation"),
        StagedEffect(
            kind="github-mutation",
            payload_json=json.dumps(
                {
                    "issue_number": 133,
                    "operation": "contents-upsert",
                    "path": "src/example.py",
                    "branch": "agent/example",
                    "message": "forbidden reviewer write",
                    "content": "x = 1\n",
                    "expected_sha": None,
                }
            ),
        ),
    )
    assert not supported_effect_guard(
        source,
        StagedEffect(kind="unknown-effect", payload_json="{}"),
    )


def test_terminal_retirement_requires_machine_terminal_cleanup_for_resolve_question() -> None:
    effect = _terminal_retirement_effect()
    assert supported_effect_guard(
        WorkerRequest(133, "lead", "resolve-question", debt_disposition="terminal-cleanup"),
        effect,
    )
    assert not supported_effect_guard(
        WorkerRequest(133, "lead", "resolve-question", debt_disposition="unfinished-recovery"),
        effect,
    )
    assert not supported_effect_guard(
        WorkerRequest(133, "lead", "resolve-question"),
        effect,
    )


def test_terminal_cleanup_removes_only_workflow_labels_and_accepts_zero_debt_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issue: dict[str, object] = {
        "number": 133,
        "state": "closed",
        "body": "Change: archived-change\n",
        "created_at": "2026-08-20T00:00:00Z",
        "closed_at": "2026-08-25T00:00:00Z",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-archive"},
            {"name": "human:approved"},
        ],
    }
    mutations: list[tuple[str, str, object | None]] = []
    injected = False

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        nonlocal injected
        del repository, token, allow_not_found
        if api_path == "issues/133" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path.startswith("issues/133/labels/") and method == "DELETE":
            mutations.append((method, api_path, payload))
            label = api_path.rsplit("/", 1)[-1].replace("%3A", ":")
            labels = issue["labels"]
            assert isinstance(labels, list)
            issue["labels"] = [
                item
                for item in labels
                if not (isinstance(item, dict) and item.get("name") == label)
            ]
            if not injected:
                labels = issue["labels"]
                assert isinstance(labels, list)
                labels.append({"name": "concurrent:keep"})
                injected = True
            return None
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    source = WorkerRequest(133, "lead", "resolve-question", debt_disposition="terminal-cleanup")
    effect = _terminal_retirement_effect()
    adapter = GitHubEffectAdapter("royhsu-work/investment-strategy", "token", source)

    assert adapter.guard(effect)
    adapter.apply(effect)
    assert adapter.observe_postcondition(effect)

    labels = issue["labels"]
    assert isinstance(labels, list)
    names = {item["name"] for item in labels if isinstance(item, dict)}
    assert names == {"human:approved", "concurrent:keep"}
    assert all(method == "DELETE" and payload is None for method, _, payload in mutations)
    assert {path.rsplit("/", 1)[-1].replace("%3A", ":") for _, path, _ in mutations} == {
        "agent:lead",
        "action:finalize-archive",
    }


def test_all_ten_mapped_actions_have_shared_durable_effect_profiles() -> None:
    expected_actions = {
        ("lead", "explore-change"),
        ("lead", "propose-change"),
        ("lead", "resolve-question"),
        ("lead", "finalize-change"),
        ("lead", "finalize-archive"),
        ("reviewer", "review-openspec"),
        ("reviewer", "review-implementation"),
        ("reviewer", "review-archive"),
        ("executor", "implement-change"),
        ("executor", "merge-pr"),
    }
    assert mapped_role_actions() == expected_actions

    required_operations = {
        ("lead", "explore-change"): {"issue-update"},
        ("lead", "propose-change"): {"contents-upsert", "pull-request-create"},
        ("lead", "resolve-question"): {"issue-create", "contents-upsert"},
        ("lead", "finalize-change"): {"issue-create", "pull-request-create"},
        ("lead", "finalize-archive"): {"issue-update"},
        ("reviewer", "review-openspec"): set(),
        ("reviewer", "review-implementation"): set(),
        ("reviewer", "review-archive"): set(),
        ("executor", "implement-change"): {"contents-upsert", "pull-request-ready"},
        ("executor", "merge-pr"): {"pull-request-merge", "ref-delete"},
    }
    for identity, operations in required_operations.items():
        assert operations <= allowed_github_mutation_operations(*identity)


def test_topology_validator_consumes_canonical_workflow_text() -> None:
    workflow_text = Path("agents/workflow.md").read_text(encoding="utf-8")
    assert topology_allows_successor(
        workflow_text,
        _request(),
        StagedEffect(
            kind="routing-transition",
            payload_json=(
                '{"issue_number":133,"role":"reviewer","action":"review-implementation"}'
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


def test_continuation_requires_a_fresh_wake_for_any_selected_work() -> None:
    source = _request()
    assert continuation_requires_fresh_wake(source, source)
    assert continuation_requires_fresh_wake(source, _request(action="merge-pr"))
    assert continuation_requires_fresh_wake(
        source,
        _request(role="reviewer", action="review-implementation"),
    )
    assert not continuation_requires_fresh_wake(source, None)


def test_workflow_transports_worker_output_to_write_authorized_apply_boundary() -> None:
    workflow = Path(".github/workflows/scheduled-agent-runtime.yml").read_text(encoding="utf-8")
    assert "actions/upload-artifact@v4" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "scheduled-agent-result-${{ github.run_id }}-${{ github.run_attempt }}" in workflow
    assert "uv run python -m investment_strategy.scheduled_agent_merge_acceptance" in workflow
    assert "uv run python -m investment_strategy.scheduled_agent_worker_runtime" in workflow
    assert "debt_disposition: ${{ steps.preflight.outputs.debt_disposition }}" in workflow
    assert "AUTHORIZED_DEBT_DISPOSITION" in workflow

    worker_section = workflow.split("\n  worker:", 1)[1].split("\n  apply:", 1)[0]
    assert "issues: write" not in worker_section
    assert "pull-requests: write" not in worker_section
    assert "contents: write" not in worker_section

    apply_section = workflow.split("\n  apply:", 1)[1]
    assert "issues: write" in apply_section
    assert "pull-requests: write" in apply_section
    assert "contents: write" in apply_section
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
