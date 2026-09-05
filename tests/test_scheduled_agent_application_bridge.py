"""Regression coverage for run-scoped Scheduled Agent application ingress."""

from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path
from typing import Literal

import pytest

from investment_strategy.issue_comment_bridge import MachineDispatchDecision
from investment_strategy.scheduled_agent_application_bridge import (
    APPLICATION_REQUEST_MARKER,
    parse_application_request,
    plan_application,
)
from investment_strategy.scheduled_agent_checkin import checkin_title
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "4e3241d7d84a64012bf3b6218442128a4cb48d7a"


def _connector_comment(comment_id: int, body: str) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }


def _worker_result(
    *,
    action: str = "explore-change",
    role: str = "lead",
    result_kind: str = "proposal-ready",
) -> dict[str, object]:
    return {
        "issue_number": 138,
        "role": role,
        "action": action,
        "change": "unset",
        "result_kind": result_kind,
        "evidence_ref": "issuecomment-typed-result",
        "result_content": "bounded semantic evidence",
        "requested_effects": [],
    }


def _effect_request(worker_result: dict[str, object] | None = None) -> str:
    raw = json.dumps(worker_result or _worker_result(), sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return "\n".join(
        (
            APPLICATION_REQUEST_MARKER,
            "Dispatch-Request-Comment-ID: 100",
            "Dispatch-Run-ID: 200",
            f"Worker-Result-B64: {encoded}",
        )
    )


def _dispatch_decision(
    *,
    revision: str = _REVISION,
    role: str = "lead",
    action: str = "explore-change",
    disposition: Literal["AUTHORIZE", "NO_WORK"] = "AUTHORIZE",
) -> MachineDispatchDecision:
    if disposition == "AUTHORIZE":
        return MachineDispatchDecision(
            request_comment_id=100,
            default_branch_revision=revision,
            disposition=disposition,
            issue_number=138,
            role=role,
            action=action,
        )
    return MachineDispatchDecision(
        request_comment_id=100,
        default_branch_revision=revision,
        disposition=disposition,
        reason="no work",
    )


def _event(body: str, *, trusted: bool = True) -> dict[str, object]:
    comment = _connector_comment(102, body)
    if not trusted:
        comment["performed_via_github_app"] = None
    return {
        "action": "created",
        "issue": {
            "number": 142,
            "title": checkin_title(date(2026, 9, 3)),
            "state": "open",
            "labels": [],
        },
        "comment": comment,
    }


def test_parse_application_request_decodes_exact_worker_result() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None
    assert request.dispatch_request_comment_id == 100
    assert request.dispatch_run_id == 200
    assert json.loads(request.raw_worker_result) == _worker_result()


def test_parse_application_request_rejects_unknown_shape() -> None:
    with pytest.raises(ValueError, match="exactly four lines"):
        parse_application_request(APPLICATION_REQUEST_MARKER)


def test_plan_application_binds_connector_event_and_machine_result() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    decision = _dispatch_decision()
    assert request is not None

    plan = plan_application(
        event=_event(body),
        request=request,
        dispatch_result=decision,
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source == WorkerRequest(138, "lead", "explore-change")
    assert plan.effect_request_comment_id == 102
    assert json.loads(plan.raw_worker_result or "") == _worker_result()


def test_plan_application_rejects_untrusted_connector_or_stale_revision() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    decision = _dispatch_decision()
    assert request is not None

    with pytest.raises(ValueError, match="configured ChatGPT connector"):
        plan_application(
            event=_event(body, trusted=False),
            request=request,
            dispatch_result=decision,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )

    stale = _dispatch_decision(revision="0" * 40)
    with pytest.raises(ValueError, match="revision is stale"):
        plan_application(
            event=_event(body),
            request=request,
            dispatch_result=stale,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_application_boundary_does_not_parse_governance_or_host_a_worker() -> None:
    source = Path("src/investment_strategy/scheduled_agent_application_bridge.py").read_text(
        encoding="utf-8"
    )
    assert "agents/workflow.md" not in source
    assert "OPENAI" not in source
    assert "Responses" not in source


def test_application_reuses_exact_dispatch_artifact_reader() -> None:
    source = Path("src/investment_strategy/scheduled_agent_application_bridge.py").read_text(
        encoding="utf-8"
    )
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")

    assert "fetch_dispatch_result" in source
    assert "parse_run_scoped_dispatch_result" not in source
    assert "actions: write" in workflow
