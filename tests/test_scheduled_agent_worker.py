"""Responses API worker and credential-isolation regressions for #133 Slice 4B/4D."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_worker import (
    WorkerToolRuntime,
    build_worker_prompt,
    run_authorized_worker,
    worker_capabilities_for,
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
            "result_content": "completed bounded local work",
            "requested_effects": [],
        }
    )


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
    assert result.result_content == "completed bounded local work"
    assert result.requested_effects == ()


def test_worker_job_has_no_model_controlled_github_write_credential() -> None:
    workflow = Path(".github/workflows/scheduled-agent-runtime.yml").read_text(encoding="utf-8")

    assert "worker:" in workflow
    assert "persist-credentials: false" in workflow
    assert "OPENAI_API_KEY:" in workflow
    worker_section = workflow.split("\n  worker:", 1)[1].split("\n  apply:", 1)[0]
    assert "GITHUB_TOKEN:" not in worker_section
    assert "contents: read" in worker_section
    assert "contents: write" not in worker_section
    assert "issues: write" not in worker_section
    assert "pull-requests: write" not in worker_section
