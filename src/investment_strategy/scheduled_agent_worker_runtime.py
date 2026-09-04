"""Runtime worker entry point with repository-owned staged-effect guidance."""

from __future__ import annotations

import base64
import binascii
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import investment_strategy.scheduled_agent_worker as worker
from investment_strategy.scheduled_agent_effect_contract import (
    allowed_github_mutation_operations,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_ORIGINAL_BUILD_WORKER_PROMPT = worker.build_worker_prompt
_ORIGINAL_AUTHORIZED_REQUEST_FROM_ENVIRONMENT = worker._authorized_request_from_environment
_DEBT_DISPOSITIONS = frozenset({"terminal-cleanup", "unfinished-recovery"})
_REQUIRED_DISPATCH_ENVELOPE_FIELDS = frozenset(
    {
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
        "worker_request",
    }
)


def _authorized_request_from_environment() -> WorkerRequest:
    """Preserve the machine-derived closed-routing disposition across the worker boundary."""

    request = _ORIGINAL_AUTHORIZED_REQUEST_FROM_ENVIRONMENT()
    raw_disposition = os.environ.get("AUTHORIZED_DEBT_DISPOSITION", "")
    disposition = raw_disposition or None
    if disposition is not None and disposition not in _DEBT_DISPOSITIONS:
        raise RuntimeError("AUTHORIZED_DEBT_DISPOSITION is invalid")
    return WorkerRequest(
        issue_number=request.issue_number,
        role=request.role,
        action=request.action,
        debt_disposition=disposition,
    )


def _integer_id_list(value: object, *, field: str) -> list[int]:
    if not isinstance(value, list) or any(type(item) is not int for item in value):
        raise RuntimeError(f"dispatch envelope {field} is invalid")
    return cast(list[int], value)


def _dispatch_envelope_from_environment(request: WorkerRequest) -> dict[str, Any]:
    """Decode and validate the exact repository-produced action-entry evidence."""

    raw = os.environ.get("AUTHORIZED_DISPATCH_ENVELOPE_B64", "")
    if not raw:
        raise RuntimeError("AUTHORIZED_DISPATCH_ENVELOPE_B64 is required")

    try:
        decoded = base64.b64decode(raw.encode("ascii"), validate=True).decode("utf-8")
        payload = json.loads(decoded)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise RuntimeError("AUTHORIZED_DISPATCH_ENVELOPE_B64 is invalid") from exc

    if not isinstance(payload, Mapping):
        raise RuntimeError("dispatch envelope must be a JSON object")
    if set(payload) != _REQUIRED_DISPATCH_ENVELOPE_FIELDS:
        raise RuntimeError("dispatch envelope fields are incomplete or unexpected")

    if payload.get("completeness") != "COMPLETE":
        raise RuntimeError("dispatch envelope completeness is not COMPLETE")
    if payload.get("observation_provenance") != "QUALIFIED":
        raise RuntimeError("dispatch envelope observation provenance is not QUALIFIED")
    if payload.get("disposition") != "AUTHORIZE":
        raise RuntimeError("dispatch envelope disposition is not AUTHORIZE")

    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason:
        raise RuntimeError("dispatch envelope reason is invalid")

    for field in (
        "formal_issue_ids",
        "recovery_candidate_ids",
        "preactivation_candidate_ids",
    ):
        _integer_id_list(payload.get(field), field=field)

    routing = payload.get("selected_routing")
    expected_routing = [request.role, request.action]
    if payload.get("selected_issue_id") != request.issue_number or routing != expected_routing:
        raise RuntimeError("dispatch envelope does not match authorized Issue/role/action")

    selected_debt = payload.get("selected_debt_disposition")
    if selected_debt is not None and selected_debt not in _DEBT_DISPOSITIONS:
        raise RuntimeError("dispatch envelope selected_debt_disposition is invalid")
    if selected_debt != request.debt_disposition:
        raise RuntimeError("dispatch envelope debt disposition does not match authorized request")

    worker_request = payload.get("worker_request")
    if not isinstance(worker_request, Mapping):
        raise RuntimeError("dispatch envelope worker_request is invalid")
    if (
        worker_request.get("issue_number"),
        worker_request.get("role"),
        worker_request.get("action"),
        worker_request.get("debt_disposition"),
    ) != (
        request.issue_number,
        request.role,
        request.action,
        request.debt_disposition,
    ):
        raise RuntimeError("dispatch envelope worker_request does not match authorized request")

    return dict(payload)


def _canonical_dispatch_envelope(request: WorkerRequest) -> str:
    envelope = _dispatch_envelope_from_environment(request)
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def build_worker_prompt(request: WorkerRequest, checkout_root: Path) -> str:
    """Add immutable dispatch evidence and staged-effect contract without write authority."""

    base = _ORIGINAL_BUILD_WORKER_PROMPT(request, checkout_root)
    operations = sorted(allowed_github_mutation_operations(request.role, request.action))
    machine_envelope = _canonical_dispatch_envelope(request)
    debt_envelope = (
        "No closed-routing debt disposition is authorized for this invocation.\n"
        if request.debt_disposition is None
        else (
            "Repository-owned dispatch also authorized the immutable invocation-local "
            f"Debt-Disposition: {request.debt_disposition}. Do not reclassify or substitute it.\n"
        )
    )
    return (
        base
        + "\n\n## Machine evidence envelope\n"
        + "The canonical JSON below was produced by repository-owned dispatch for this exact "
        + "worker invocation. Consume it as immutable action-entry evidence; do not rederive, "
        + "replace, or weaken any field.\n"
        + "```json\n"
        + machine_envelope
        + "\n```\n"
        + debt_envelope
        + "\n## Runtime staged-effect contract\n"
        + "Durable GitHub mutation remains repository-owned. Express requested effects only in "
        + "the structured `requested_effects` array. Supported common effects are:\n"
        + "- `issue-comment`: payload_json object with `issue_number` and `body`.\n"
        + "- `routing-transition`: payload_json object with `issue_number`, `role`, and `action`; "
        + "the application boundary validates the successor against `agents/workflow.md`.\n"
        + "- `terminal-retirement`: payload_json object with `issue_number` and `expected_change`. "
        + "It is accepted only for a repository-authorized terminal owner; for "
        + "`Lead / resolve-question` it additionally requires machine Debt-Disposition "
        + "`terminal-cleanup`. Application closes without replacing labels when needed, then "
        + "fresh-reads and removes only exact workflow routing labels.\n"
        + "- `github-mutation`: payload_json must always include the authorized source "
        + "`issue_number` plus one operation allowed for this exact action.\n"
        + f"Allowed github-mutation operations for this invocation: {operations}.\n"
        + "Operation payload fields:\n"
        + "- issue-create: title, optional body, optional labels.\n"
        + "- issue-update: fields (title/body/state), optional expected current fields.\n"
        + "- issue-label-add: label.\n"
        + "- contents-upsert: path, branch, message, content, expected_sha "
        + "(null only for create).\n"
        + "- contents-delete: path, branch, message, expected_sha.\n"
        + "- ref-create: ref (`refs/heads/...`), sha.\n"
        + "- ref-update: ref, expected_sha, sha.\n"
        + "- ref-delete: ref, expected_sha.\n"
        + "- pull-request-create: title, body, head, base, optional draft.\n"
        + "- pull-request-update: number, expected_head_sha, fields (title/body/state/base).\n"
        + "- pull-request-ready: number, expected_head_sha.\n"
        + "- pull-request-merge: number, expected_head_sha, optional merge_method.\n"
        + "Do not request an operation absent from the allowed list. Every request is staged only; "
        + "repository application fresh-reauthorizes source state and effect-specific "
        + "preconditions.\n"
    )


def main() -> int:
    """Run the existing Responses worker with the shared effect contract in its prompt."""

    worker.build_worker_prompt = build_worker_prompt
    worker._authorized_request_from_environment = _authorized_request_from_environment
    return worker.main()


if __name__ == "__main__":
    raise SystemExit(main())
