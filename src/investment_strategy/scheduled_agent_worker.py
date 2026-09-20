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


def parse_worker_result(
    raw: str,
    request: WorkerRequest,
    *,
    authorized_change: str | None = None,
) -> WorkerActionResult:
    """Normalize semantic output onto one machine-authorized source.

    The external worker owns only the bounded semantic result.  Identity fields
    are accepted as a migration boundary for historical envelopes, but the
    application-provided ``request`` and ``authorized_change`` are the source
    of truth.  Optional mechanical fields are normalized at this boundary so a
    missing ``requested_effects`` field cannot manufacture a pre-ACCEPT
    competing candidate.
    """

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("worker result is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("worker result must be a JSON object")

    claimed_issue_number = decoded.get("issue_number")
    claimed_role = decoded.get("role")
    claimed_action = decoded.get("action")
    claimed_change = decoded.get("change")
    result_kind = decoded.get("result_kind")
    evidence_ref = decoded.get("evidence_ref")
    result_content = decoded.get("result_content")
    requested_effects = decoded.get("requested_effects", [])
    if (
        not isinstance(result_kind, str)
        or not isinstance(result_content, str)
        or not isinstance(requested_effects, list)
        or (evidence_ref is not None and not isinstance(evidence_ref, str))
    ):
        raise ValueError("worker result has invalid fields")

    if claimed_issue_number is not None and (
        not isinstance(claimed_issue_number, int)
        or isinstance(claimed_issue_number, bool)
        or claimed_issue_number != request.issue_number
    ):
        raise ValueError("worker result does not match authorized Issue")
    if claimed_role is not None and (
        not isinstance(claimed_role, str) or claimed_role != request.role
    ):
        raise ValueError("worker result does not match authorized Role")
    if claimed_action is not None and (
        not isinstance(claimed_action, str) or claimed_action != request.action
    ):
        raise ValueError("worker result does not match authorized Action")
    if claimed_change is not None and not isinstance(claimed_change, str):
        raise ValueError("worker result Change is invalid")
    if authorized_change is not None and not isinstance(authorized_change, str):
        raise ValueError("authorized Change is invalid")
    if (
        claimed_change is not None
        and authorized_change is not None
        and claimed_change != authorized_change
    ):
        raise ValueError("worker result does not match authorized Change")
    change = authorized_change if authorized_change is not None else claimed_change
    if not isinstance(change, str) or not change:
        raise ValueError("worker result Change is missing")
    try:
        model_action = ModelAction(request.action)
        kind = ResultKind(result_kind)
    except ValueError as exc:
        raise ValueError("worker result vocabulary is invalid") from exc
    if role_for(model_action).value != request.role:
        raise ValueError("authorized Role is not derived from Action")
    typed = BoundedActionResult(
        issue_number=request.issue_number,
        change=change,
        action=model_action,
        result=TypedResult(kind, evidence_ref=evidence_ref),
    )
    return WorkerActionResult(
        issue_number=request.issue_number,
        role=request.role,
        action=request.action,
        change=change,
        result_content=result_content,
        requested_effects=tuple(_effect_from_payload(item) for item in requested_effects),
        typed_result=typed,
    )
