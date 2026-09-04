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
    classify_dispatch,
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


def _formal_issue(*, action: str, change: str) -> dict[str, object]:
    return {
        "number": 133,
        "state": "open",
        "body": f"Change: {change}\nCause-Ref: issuecomment-22\n",
        "created_at": "2026-08-31T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "agent:lead"}, {"name": f"action:{action}"}],
    }


def _review_pass(change: str) -> dict[str, object]:
    return {
        "id": 91,
        "issue_url": "https://api.github.com/repos/royhsu-work/investment-strategy/issues/133",
        "body": (
            "## REVIEW_RESULT\n\n"
            "Workflow: #133\n"
            f"Change: `{change}`\n"
            "Action: `Reviewer / review-openspec`\n"
            "Result: `PASS`\n"
            "Revision: `0123456789012345678901234567890123456789`\n"
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
    }


def _proposal_ready_comment(change: str = "unset") -> dict[str, object]:
    return {
        "id": 22,
        "issue_url": "https://api.github.com/repos/royhsu-work/investment-strategy/issues/133",
        "body": (
            "## ACTION_RESULT\n"
            "Workflow: #133\n"
            f"Change: {change}\n"
            "Action: Lead / explore-change\n"
            "Result: PROPOSAL_READY\n"
        ),
        "user": {"login": "github-actions[bot]"},
        "author_association": "CONTRIBUTOR",
    }


def _propose_research_batch() -> EffectBatch:
    source = WorkerRequest(133, "lead", "propose-change")
    raw = json.dumps(
        {
            "issue_number": 133,
            "role": "lead",
            "action": "propose-change",
            "explore_disposition": None,
            "propose_disposition": "RESEARCH_REQUIRED",
            "result_content": "bounded research correction",
            "requested_effects": [],
        }
    )
    return parse_effect_batch(raw, source)


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


def test_selected_propose_without_explore_baseline_fails_locally_without_queue_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight = DispatchPreflight(
        issues=(
            RepositoryIssueSnapshot(
                issue_number=168,
                change="unset",
                routing=("lead", "propose-change"),
                created_order=1,
            ),
            RepositoryIssueSnapshot(
                issue_number=169,
                change="unset",
                routing=("lead", "explore-change"),
                created_order=2,
            ),
        ),
        enumeration=EnumerationEvidence(
            observed_count=2,
            source_total_count=2,
            incomplete_results=False,
            exhausted=True,
            observation_provenance=ObservationProvenance.QUALIFIED,
        ),
    )
    decision = classify_dispatch(preflight)
    assert decision.selected_issue_id == 168
    assert decision.selected_routing == ("lead", "propose-change")

    issue: dict[str, object] = {
        "number": 168,
        "state": "open",
        "body": "Change: unset\n",
        "created_at": "2026-08-27T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "agent:lead"}, {"name": "action:propose-change"}],
    }

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        del repository, token, allow_not_found
        if api_path == "issues/168" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path.startswith("issues/168/comments") and method == "GET":
            return []
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    source = WorkerRequest(168, "lead", "propose-change")
    activation = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 168,
                "operation": "issue-update",
                "fields": {"body": "Change: canonical-change\n"},
                "expected": {"body": "Change: unset\n"},
            }
        ),
    )
    adapter = GitHubEffectAdapter("royhsu-work/investment-strategy", "token", source)
    result = apply_effect_batch(
        EffectBatch(source=source, effects=(activation,)),
        fresh_preflight=lambda: preflight,
        effect_guard=adapter.guard,
        topology_validator=lambda _source, _effect: True,
        apply_effect=lambda _effect: None,
        observe_postcondition=lambda _effect: True,
    )

    assert result.applied is False
    assert result.reason == "effect precondition rejected"
    assert classify_dispatch(preflight).selected_issue_id == 168


def test_selected_propose_with_ambiguous_explore_baselines_fails_action_local_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issue: dict[str, object] = {
        "number": 168,
        "state": "open",
        "body": "Change: unset\n",
        "created_at": "2026-08-27T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "agent:lead"}, {"name": "action:propose-change"}],
    }
    baseline = {
        "body": (
            "## ACTION_RESULT\n"
            "Workflow: #168\n"
            "Change: unset\n"
            "Action: Lead / explore-change\n"
            "Result: PROPOSAL_READY\n"
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
    }

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        del repository, token, allow_not_found
        if api_path == "issues/168" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path.startswith("issues/168/comments") and method == "GET":
            return [json.loads(json.dumps(baseline)), json.loads(json.dumps(baseline))]
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    source = WorkerRequest(168, "lead", "propose-change")
    activation = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 168,
                "operation": "issue-update",
                "fields": {"body": "Change: canonical-change\n"},
                "expected": {"body": "Change: unset\n"},
            }
        ),
    )
    adapter = GitHubEffectAdapter("royhsu-work/investment-strategy", "token", source)

    assert not adapter.guard(activation)


def test_formal_propose_research_correction_allowed_before_first_review_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    change = "simplify-scheduled-agent-control-plane"
    issue = _formal_issue(action="propose-change", change=change)

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        del repository, token, payload, allow_not_found
        if api_path == "issues/133" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path == "issues/133/comments?per_page=100&page=1" and method == "GET":
            return []
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    batch = _propose_research_batch()
    adapter = GitHubEffectAdapter(
        "royhsu-work/investment-strategy",
        "token",
        batch.source,
    )

    assert len(batch.effects) == 1
    assert adapter.guard(batch.effects[0])


def test_formal_propose_research_correction_rejected_after_first_review_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    change = "simplify-scheduled-agent-control-plane"
    issue = _formal_issue(action="propose-change", change=change)

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        del repository, token, payload, allow_not_found
        if api_path == "issues/133" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path == "issues/133/comments?per_page=100&page=1" and method == "GET":
            return [_review_pass(change)]
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    batch = _propose_research_batch()
    adapter = GitHubEffectAdapter(
        "royhsu-work/investment-strategy",
        "token",
        batch.source,
    )

    assert not adapter.guard(batch.effects[0])


def test_formal_active_propose_preserves_preactivation_exact_cause_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    change = "simplify-scheduled-agent-control-plane"
    issue = _formal_issue(action="propose-change", change=change)
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 133,
                "operation": "issue-label-add",
                "label": "human:notified",
            }
        ),
    )

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        del repository, token, payload, allow_not_found
        if api_path == "issues/133" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path == "issues/comments/22" and method == "GET":
            return _proposal_ready_comment("unset")
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        "royhsu-work/investment-strategy",
        "token",
        WorkerRequest(133, "lead", "propose-change"),
    )

    assert adapter.guard(effect)


def test_formal_explore_successor_rejected_if_first_review_pass_already_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    change = "simplify-scheduled-agent-control-plane"
    issue = _formal_issue(action="explore-change", change=change)
    result_body = (
        "## ACTION_RESULT\n"
        "Workflow: #133\n"
        f"Change: {change}\n"
        "Action: Lead / explore-change\n"
        "Result: PROPOSAL_READY\n"
    )
    cause_payload = json.dumps({"issue_number": 133, "body": result_body})
    route = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps(
            {"issue_number": 133, "role": "lead", "action": "propose-change"},
            sort_keys=True,
        ),
        derived=True,
        cause_payload_json=cause_payload,
    )

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        del repository, token, payload, allow_not_found
        if api_path == "issues/133" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path == "issues/133/comments?per_page=100&page=1" and method == "GET":
            return [_review_pass(change)]
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        "royhsu-work/investment-strategy",
        "token",
        WorkerRequest(133, "lead", "explore-change"),
    )

    assert not adapter.guard(route)


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


def test_repository_deployment_has_no_scheduled_worker_apply_boundary() -> None:
    runtime_workflow = Path(".github/workflows/scheduled-agent-runtime.yml").read_text(
        encoding="utf-8"
    )
    bridge_workflow = Path(".github/workflows/scheduled-agent-bridge.yml").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "actions/upload-artifact@v4",
        "actions/download-artifact@v4",
        "scheduled_agent_merge_acceptance",
        "scheduled_agent_worker_runtime",
        "AUTHORIZED_DEBT_DISPOSITION",
    ):
        assert forbidden not in runtime_workflow

    assert "issue_comment:" in bridge_workflow
    assert "investment_strategy.issue_comment_bridge" in bridge_workflow
    assert "issues: read" in bridge_workflow


def test_continuation_is_owned_by_next_chatgpt_scheduled_wake_not_actions_retrigger() -> None:
    runtime_workflow = Path(".github/workflows/scheduled-agent-runtime.yml").read_text(
        encoding="utf-8"
    )
    migration = Path("agents/scheduled-task-migration.md").read_text(encoding="utf-8")

    assert "continuation_required" not in runtime_workflow
    assert "/actions/workflows/scheduled-agent-runtime.yml/dispatches" not in runtime_workflow
    assert "workflow_dispatch:" in runtime_workflow
    assert "Scheduled Task" in migration
    assert "fresh repository-wide reconstruction" in migration
