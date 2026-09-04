"""Structured-result boundary tests for the external semantic worker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from investment_strategy.scheduled_agent_action_model import ResultKind
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_worker import parse_worker_result


def _raw(**overrides: object) -> str:
    payload: dict[str, object] = {
        "issue_number": 138,
        "role": "executor",
        "action": "implement-change",
        "change": "simplify-scheduled-agent-control-plane",
        "result_kind": "ready",
        "evidence_ref": "issuecomment-typed-result",
        "result_content": "semantic evidence",
        "requested_effects": [],
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_parser_accepts_one_exact_typed_result() -> None:
    request = WorkerRequest(138, "executor", "implement-change")
    result = parse_worker_result(_raw(), request)
    assert result.issue_number == 138
    assert result.action == "implement-change"
    assert result.typed_result.result.kind is ResultKind.READY
    assert result.requested_effects == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"issue_number": 139},
        {"role": "lead"},
        {"action": "unknown-action"},
        {"result_kind": "not-a-result"},
        {"requested_effects": "not-a-list"},
    ],
)
def test_parser_rejects_identity_or_vocabulary_mismatch(overrides: dict[str, object]) -> None:
    request = WorkerRequest(138, "executor", "implement-change")
    with pytest.raises(ValueError):
        parse_worker_result(_raw(**overrides), request)


def test_parser_preserves_requested_effect_as_untrusted_data() -> None:
    request = WorkerRequest(138, "executor", "implement-change")
    raw = _raw(
        requested_effects=[
            {"kind": "issue-comment", "payload_json": '{"issue_number":138,"body":"evidence"}'}
        ]
    )
    result = parse_worker_result(raw, request)
    assert result.requested_effects[0].kind == "issue-comment"


def test_worker_module_has_no_model_or_actions_runtime() -> None:
    source = Path("src/investment_strategy/scheduled_agent_worker.py").read_text(encoding="utf-8")
    for forbidden in ("OPENAI_API", "Responses", "WorkerToolRuntime", "subprocess"):
        assert forbidden not in source
