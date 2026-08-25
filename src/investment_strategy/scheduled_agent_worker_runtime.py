"""Runtime worker entry point with repository-owned staged-effect guidance."""

from __future__ import annotations

import os
from pathlib import Path

import investment_strategy.scheduled_agent_worker as worker
from investment_strategy.scheduled_agent_effect_contract import (
    allowed_github_mutation_operations,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_ORIGINAL_BUILD_WORKER_PROMPT = worker.build_worker_prompt
_ORIGINAL_AUTHORIZED_REQUEST_FROM_ENVIRONMENT = worker._authorized_request_from_environment
_DEBT_DISPOSITIONS = frozenset({"terminal-cleanup", "unfinished-recovery"})


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


def build_worker_prompt(request: WorkerRequest, checkout_root: Path) -> str:
    """Add the shared staged-effect contract without granting write authority."""

    base = _ORIGINAL_BUILD_WORKER_PROMPT(request, checkout_root)
    operations = sorted(allowed_github_mutation_operations(request.role, request.action))
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
