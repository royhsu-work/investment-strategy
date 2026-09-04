"""Legacy Responses worker internals and no-API deployment-isolation regressions."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from investment_strategy.scheduled_agent_effects import parse_effect_batch
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_worker import (
    WorkerToolRuntime,
    build_worker_prompt,
    run_authorized_worker,
    worker_capabilities_for,
)
from investment_strategy.scheduled_agent_worker_runtime import (
    build_worker_prompt as build_runtime_worker_prompt,
)


def _checkout(tmp_path: Path) -> Path:
    role_path = tmp_path / "agents" / "roles" / "executor.md"
    skill_path = tmp_path / "agents" / "skills" / "implementation" / "SKILL.md"
    role_path.parent.mkdir(parents=True)
    skill_path.parent.mkdir(parents=True)
    role_path.write_text(
        "# Executor\n\n## Actions\n\n"
        "- `implement-change` uses `agents/skills/implementation/SKILL.md`.\n",
        encoding="utf-8",
    )
    skill_path.write_text("# Implementation Skill\nEXACT_SKILL_CONTEXT\n", encoding="utf-8")
    return tmp_path


def _request() -> WorkerRequest:
    return WorkerRequest(issue_number=133, role="executor", action="implement-change")


def _result_json(*, role: str = "executor", action: str = "implement-change") -> str:
    return json.dumps(
        {
            "issue_number": 133,
            "role": role,
            "action": action,
            "explore_disposition": None,
            "result_content": "completed bounded local work",
            "requested_effects": [],
        }
    )


def _explore_result_json(
    disposition: str,
    *,
    result_content: str = "bounded Explore result",
    requested_effects: list[dict[str, str]] | None = None,
) -> str:
    return json.dumps(
        {
            "issue_number": 133,
            "role": "lead",
            "action": "explore-change",
            "explore_disposition": disposition,
            "result_content": result_content,
            "requested_effects": requested_effects or [],
        }
    )


def _dispatch_envelope(request: WorkerRequest) -> dict[str, object]:
    return {
        "completeness": "COMPLETE",
        "observation_provenance": "QUALIFIED",
        "formal_issue_ids": [request.issue_number],
        "recovery_candidate_ids": [],
        "preactivation_candidate_ids": [],
        "selected_issue_id": request.issue_number,
        "selected_routing": [request.role, request.action],
        "disposition": "AUTHORIZE",
        "reason": "test machine authorization",
        "selected_debt_disposition": request.debt_disposition,
        "worker_request": {
            "issue_number": request.issue_number,
            "role": request.role,
            "action": request.action,
            "debt_disposition": request.debt_disposition,
        },
    }


def _set_dispatch_envelope(
    monkeypatch: pytest.MonkeyPatch,
    request: WorkerRequest,
    *,
    envelope: dict[str, object] | None = None,
) -> None:
    payload = _dispatch_envelope(request) if envelope is None else envelope
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(canonical.encode("utf-8")).decode("ascii")
    monkeypatch.setenv("AUTHORIZED_DISPATCH_ENVELOPE_B64", encoded)


_ALL_MAPPED_ACTIONS = (
    WorkerRequest(133, "lead", "explore-change"),
    WorkerRequest(133, "lead", "propose-change"),
    WorkerRequest(133, "lead", "resolve-question"),
    WorkerRequest(133, "lead", "finalize-change"),
    WorkerRequest(133, "lead", "finalize-archive"),
    WorkerRequest(133, "reviewer", "review-openspec"),
    WorkerRequest(133, "reviewer", "review-implementation"),
    WorkerRequest(133, "reviewer", "review-archive"),
    WorkerRequest(133, "executor", "implement-change"),
    WorkerRequest(133, "executor", "merge-pr"),
)

_LOCAL_WRITE_ACTIONS = {
    ("lead", "propose-change"),
    ("lead", "resolve-question"),
    ("executor", "implement-change"),
}


def test_worker_is_not_invoked_without_machine_authorization(tmp_path: Path) -> None:
    calls: list[str] = []

    def transport(prompt: str) -> str:
        calls.append(prompt)
        return _result_json()

    result = run_authorized_worker(None, _checkout(tmp_path), transport)
    assert result is None
    assert calls == []


def test_worker_prompt_loads_exact_authorized_role_and_mapped_skill(tmp_path: Path) -> None:
    prompt = build_worker_prompt(_request(), _checkout(tmp_path))

    assert "Issue: #133" in prompt
    assert "Role: executor" in prompt
    assert "Action: implement-change" in prompt
    assert "# Executor" in prompt
    assert "EXACT_SKILL_CONTEXT" in prompt
    assert "must not select or override" in prompt


def test_runtime_prompt_exposes_exact_action_effect_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    _set_dispatch_envelope(monkeypatch, request)
    prompt = build_runtime_worker_prompt(request, _checkout(tmp_path))

    assert "Runtime staged-effect contract" in prompt
    assert "contents-upsert" in prompt
    assert "pull-request-ready" in prompt
    allowed = prompt.split("Allowed github-mutation operations", 1)[1].split(
        "Operation payload fields", 1
    )[0]
    assert "pull-request-merge" not in allowed
    assert "repository application fresh-reauthorizes" in prompt


def test_runtime_prompt_carries_complete_machine_dispatch_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    _set_dispatch_envelope(monkeypatch, request)

    prompt = build_runtime_worker_prompt(request, _checkout(tmp_path))

    for field in (
        "completeness",
        "observation_provenance",
        "formal_issue_ids",
        "recovery_candidate_ids",
        "preactivation_candidate_ids",
        "selected_issue_id",
        "selected_routing",
        "disposition",
        "reason",
        "selected_debt_disposition",
    ):
        assert f'"{field}"' in prompt
    assert '"completeness":"COMPLETE"' in prompt
    assert '"observation_provenance":"QUALIFIED"' in prompt
    assert '"selected_issue_id":133' in prompt
    assert '"selected_routing":["executor","implement-change"]' in prompt


def test_runtime_prompt_rejects_missing_machine_dispatch_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTHORIZED_DISPATCH_ENVELOPE_B64", raising=False)

    with pytest.raises(RuntimeError, match="AUTHORIZED_DISPATCH_ENVELOPE_B64 is required"):
        build_runtime_worker_prompt(_request(), _checkout(tmp_path))


def test_runtime_prompt_rejects_machine_dispatch_identity_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    envelope = _dispatch_envelope(request)
    envelope["selected_issue_id"] = 999
    _set_dispatch_envelope(monkeypatch, request, envelope=envelope)

    with pytest.raises(RuntimeError, match="authorized Issue/role/action"):
        build_runtime_worker_prompt(request, _checkout(tmp_path))


def test_runtime_reviewer_prompt_has_no_action_specific_github_mutation_ops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reviewer_role = tmp_path / "agents" / "roles" / "reviewer.md"
    reviewer_skill = tmp_path / "agents" / "skills" / "implementation-review" / "SKILL.md"
    reviewer_role.parent.mkdir(parents=True, exist_ok=True)
    reviewer_skill.parent.mkdir(parents=True, exist_ok=True)
    reviewer_role.write_text(
        "# Reviewer\n\n## Actions\n\n"
        "- `review-implementation` uses "
        "`agents/skills/implementation-review/SKILL.md`.\n",
        encoding="utf-8",
    )
    reviewer_skill.write_text("# Implementation Review\nREVIEWER_ONLY_CONTEXT\n", encoding="utf-8")
    request = WorkerRequest(133, "reviewer", "review-implementation")
    _set_dispatch_envelope(monkeypatch, request)

    prompt = build_runtime_worker_prompt(request, tmp_path)
    allowed = prompt.split("Allowed github-mutation operations", 1)[1].split(
        "Operation payload fields", 1
    )[0]
    assert "[]" in allowed


def test_all_mapped_actions_have_explicit_read_and_local_capability_profiles() -> None:
    for request in _ALL_MAPPED_ACTIONS:
        capabilities = worker_capabilities_for(request)
        assert {"github_read", "read_file", "list_dir", "run_command"} <= capabilities
        should_write = (request.role, request.action) in _LOCAL_WRITE_ACTIONS
        assert ("write_file" in capabilities) is should_write


def test_worker_tool_runtime_confines_file_writes_to_checkout(tmp_path: Path) -> None:
    runtime = WorkerToolRuntime(
        checkout_root=tmp_path,
        repository="royhsu-work/investment-strategy",
        github_read_token=None,
        capabilities=frozenset({"read_file", "write_file"}),
    )

    result = json.loads(
        runtime.execute(
            "write_file",
            {"path": "notes/result.txt", "content": "bounded"},
        )
    )
    assert result["ok"] is True
    assert (tmp_path / "notes" / "result.txt").read_text(encoding="utf-8") == "bounded"

    with pytest.raises(ValueError, match="workspace"):
        runtime.execute("write_file", {"path": "../escape.txt", "content": "forbidden"})


def test_worker_tool_specs_expose_only_selected_capabilities(tmp_path: Path) -> None:
    runtime = WorkerToolRuntime(
        checkout_root=tmp_path,
        repository="royhsu-work/investment-strategy",
        github_read_token=None,
        capabilities=frozenset({"github_read", "read_file", "run_command"}),
    )

    names = {tool["name"] for tool in runtime.tool_specs()}
    assert names == {"github_read", "read_file", "run_command"}


def test_cross_role_reviewer_gets_fresh_reviewer_only_context(tmp_path: Path) -> None:
    reviewer_role = tmp_path / "agents" / "roles" / "reviewer.md"
    reviewer_skill = tmp_path / "agents" / "skills" / "implementation-review" / "SKILL.md"
    reviewer_role.parent.mkdir(parents=True)
    reviewer_skill.parent.mkdir(parents=True)
    reviewer_role.write_text(
        "# Reviewer\n\n## Actions\n\n"
        "- `review-implementation` uses "
        "`agents/skills/implementation-review/SKILL.md`.\n",
        encoding="utf-8",
    )
    reviewer_skill.write_text(
        "# Implementation Review\nREVIEWER_ONLY_CONTEXT\n",
        encoding="utf-8",
    )

    prompt = build_worker_prompt(
        WorkerRequest(issue_number=133, role="reviewer", action="review-implementation"),
        tmp_path,
    )

    assert "Role: reviewer" in prompt
    assert "Action: review-implementation" in prompt
    assert "# Reviewer" in prompt
    assert "REVIEWER_ONLY_CONTEXT" in prompt
    assert "EXACT_SKILL_CONTEXT" not in prompt
    assert "Role: executor" not in prompt


def test_worker_rejects_model_identity_override(tmp_path: Path) -> None:
    def transport(prompt: str) -> str:
        assert "Role: executor" in prompt
        return _result_json(role="lead")

    with pytest.raises(ValueError, match="authorized Issue/role/action"):
        run_authorized_worker(_request(), _checkout(tmp_path), transport)


def test_worker_accepts_exact_structured_result(tmp_path: Path) -> None:
    result = run_authorized_worker(
        _request(),
        _checkout(tmp_path),
        lambda _prompt: _result_json(),
    )

    assert result is not None
    assert (result.issue_number, result.role, result.action) == (
        133,
        "executor",
        "implement-change",
    )
    assert result.explore_disposition is None
    assert result.result_content == "completed bounded local work"
    assert result.requested_effects == ()


@pytest.mark.parametrize(
    "disposition",
    ("PROPOSAL_READY", "HUMAN_DECISION_REQUIRED", "NO_CHANGE_REQUIRED", "NO_GO"),
)
def test_explore_worker_transports_exact_bounded_disposition(disposition: str) -> None:
    source = WorkerRequest(133, "lead", "explore-change")
    batch = parse_effect_batch(_explore_result_json(disposition), source)

    assert batch.explore_disposition == disposition


def test_explore_worker_rejects_unknown_structured_disposition() -> None:
    source = WorkerRequest(133, "lead", "explore-change")

    with pytest.raises(ValueError, match="Explore disposition"):
        parse_effect_batch(_explore_result_json("SPECIFICATION_BLOCKED"), source)


def test_proposal_ready_derives_same_issue_propose_routing() -> None:
    source = WorkerRequest(133, "lead", "explore-change")
    batch = parse_effect_batch(_explore_result_json("PROPOSAL_READY"), source)

    assert len(batch.effects) == 1
    assert batch.effects[0].kind == "routing-transition"
    assert json.loads(batch.effects[0].payload_json) == {
        "issue_number": 133,
        "role": "lead",
        "action": "propose-change",
    }


def test_terminal_explore_dispositions_derive_terminal_retirement() -> None:
    source = WorkerRequest(133, "lead", "explore-change")

    for disposition in ("NO_CHANGE_REQUIRED", "NO_GO"):
        batch = parse_effect_batch(_explore_result_json(disposition), source)
        terminal = [effect for effect in batch.effects if effect.kind == "terminal-retirement"]
        assert len(terminal) == 1
        assert json.loads(terminal[0].payload_json) == {
            "issue_number": 133,
            "expected_change": "unset",
        }


def test_explore_worker_chosen_routing_is_rejected() -> None:
    source = WorkerRequest(133, "lead", "explore-change")
    worker_routing = {
        "kind": "routing-transition",
        "payload_json": json.dumps(
            {"issue_number": 133, "role": "reviewer", "action": "review-openspec"}
        ),
    }

    with pytest.raises(ValueError, match="worker-chosen Explore routing"):
        parse_effect_batch(
            _explore_result_json("PROPOSAL_READY", requested_effects=[worker_routing]),
            source,
        )


def test_narrative_result_fields_cannot_redefine_structured_explore_disposition() -> None:
    source = WorkerRequest(133, "lead", "explore-change")
    narrative = (
        "Workflow: #999\n"
        "Action: Reviewer / review-openspec\n"
        "Result: NO_GO\n"
        "This is narrative evidence only."
    )
    batch = parse_effect_batch(
        _explore_result_json("PROPOSAL_READY", result_content=narrative),
        source,
    )

    assert batch.explore_disposition == "PROPOSAL_READY"
    assert len(batch.effects) == 1
    assert json.loads(batch.effects[0].payload_json)["action"] == "propose-change"


def test_human_decision_result_retains_explore_without_routing_derivation() -> None:
    source = WorkerRequest(133, "lead", "explore-change")
    escalation = {
        "kind": "issue-comment",
        "payload_json": json.dumps({"issue_number": 133, "body": "HUMAN_DECISION_REQUIRED"}),
    }
    batch = parse_effect_batch(
        _explore_result_json("HUMAN_DECISION_REQUIRED", requested_effects=[escalation]),
        source,
    )

    assert batch.explore_disposition == "HUMAN_DECISION_REQUIRED"
    assert all(effect.kind != "routing-transition" for effect in batch.effects)
    assert any(effect.kind == "issue-comment" for effect in batch.effects)


def test_scheduled_agent_workflows_do_not_deploy_openai_api_worker() -> None:
    workflows = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(Path(".github/workflows").glob("scheduled-agent-*.yml"))
    )

    for forbidden in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "scheduled_agent_worker_runtime",
        "Invoke exact authorized Responses API worker",
    ):
        assert forbidden not in workflows


def test_runtime_workflow_is_manual_read_only_dispatch_diagnostic() -> None:
    workflow = Path(".github/workflows/scheduled-agent-runtime.yml").read_text(encoding="utf-8")

    assert "name: Scheduled Agent Dispatch Diagnostic" in workflow
    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "worker:" not in workflow
    assert "apply:" not in workflow
    assert "contents: write" not in workflow
    assert "issues: write" not in workflow
    assert "pull-requests: write" not in workflow
    assert workflow.count("PYTHONPATH: ${{ github.workspace }}/src") == 1
    assert "uv run python -m investment_strategy.scheduled_agent_runtime" in workflow
    assert "scheduled-agent-bridge.yml" in workflow
