"""Responses API worker and credential-isolation regressions for #133 Slice 4B."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_worker import (
    build_worker_prompt,
    run_authorized_worker,
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
