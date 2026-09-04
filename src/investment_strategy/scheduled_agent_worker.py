"""Structured-result parser for the external Scheduled-Agent semantic worker.

GitHub Actions never hosts a model worker. This module only validates the
bounded result supplied by the external Scheduled Task and binds it to the
machine-authorized Action.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from investment_strategy.scheduled_agent_action_model import Action as ModelAction
from investment_strategy.scheduled_agent_action_model import (
    BoundedActionResult,
    ResultKind,
    TypedResult,
    role_for,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest


@dataclass(frozen=True)
class WorkerRequestedEffect:
    """Invocation-local requested effect; never authority."""

    kind: str
    payload_json: str


@dataclass(frozen=True)
class WorkerActionResult:
    """Typed result bound to one exact machine-selected Action."""

    issue_number: int
    role: str
    action: str
    change: str
    result_content: str
    requested_effects: tuple[WorkerRequestedEffect, ...]
    typed_result: BoundedActionResult


def _effect_from_payload(payload: object) -> WorkerRequestedEffect:
    if not isinstance(payload, Mapping):
        raise ValueError("requested effect must be an object")
    kind = payload.get("kind")
    payload_json = payload.get("payload_json")
    if (
        not isinstance(kind, str)
        or not kind.strip()
        or not isinstance(payload_json, str)
        or not payload_json.strip()
    ):
        raise ValueError("requested effect requires non-empty strings")
    return WorkerRequestedEffect(kind=kind, payload_json=payload_json)


def parse_worker_result(raw: str, request: WorkerRequest) -> WorkerActionResult:
    """Validate one structured result without executing a model or tool."""

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("worker result is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("worker result must be a JSON object")

    issue_number = decoded.get("issue_number")
    role = decoded.get("role")
    action = decoded.get("action")
    change = decoded.get("change")
    result_kind = decoded.get("result_kind")
    evidence_ref = decoded.get("evidence_ref")
    result_content = decoded.get("result_content")
    requested_effects = decoded.get("requested_effects")
    if (
        not isinstance(issue_number, int)
        or isinstance(issue_number, bool)
        or not isinstance(role, str)
        or not isinstance(action, str)
        or not isinstance(change, str)
        or not isinstance(result_kind, str)
        or not isinstance(result_content, str)
        or not isinstance(requested_effects, list)
        or (evidence_ref is not None and not isinstance(evidence_ref, str))
    ):
        raise ValueError("worker result has invalid fields")
    if (issue_number, role, action) != (request.issue_number, request.role, request.action):
        raise ValueError("worker result does not match authorized Action")
    try:
        model_action = ModelAction(action)
        kind = ResultKind(result_kind)
    except ValueError as exc:
        raise ValueError("worker result vocabulary is invalid") from exc
    if role_for(model_action).value != role:
        raise ValueError("worker result Role is not derived from Action")
    typed = BoundedActionResult(
        issue_number=issue_number,
        change=change,
        action=model_action,
        result=TypedResult(kind, evidence_ref=evidence_ref),
    )
    return WorkerActionResult(
        issue_number=issue_number,
        role=role,
        action=action,
        change=change,
        result_content=result_content,
        requested_effects=tuple(_effect_from_payload(item) for item in requested_effects),
        typed_result=typed,
    )
