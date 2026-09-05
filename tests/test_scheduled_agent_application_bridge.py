"""Regression coverage for fresh repository-authorized application ingress."""

from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path
from typing import cast

import pytest

from investment_strategy.scheduled_agent_application_bridge import (
    APPLICATION_REQUEST_MARKER,
    AUTHORIZATION_REVISION_PREFIX,
    parse_application_request,
    plan_application,
)
from investment_strategy.scheduled_agent_checkin import checkin_title
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    WorkerRequest,
    acquire_dispatch_preflight,
)
from investment_strategy.workflow_dispatch import DispatchPreflight, Routing

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "4e3241d7d84a64012bf3b6218442128a4cb48d7a"


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


def _effect_request(
    worker_result: dict[str, object] | None = None,
    *,
    revision: str = _REVISION,
) -> str:
    raw = json.dumps(worker_result or _worker_result(), sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return "\n".join(
        (
            APPLICATION_REQUEST_MARKER,
            f"{AUTHORIZATION_REVISION_PREFIX}{revision}",
            f"Worker-Result-B64: {encoded}",
        )
    )


def _preflight(
    *,
    action: str = "explore-change",
    issue_number: int = 138,
    change: str = "unset",
    human_authorized: bool = True,
) -> DispatchPreflight:
    role = (
        "reviewer"
        if action.startswith("review-")
        else "executor"
        if action.startswith(("implement", "merge"))
        else "lead"
    )
    return acquire_dispatch_preflight(
        observations=(
            GitHubIssueObservation(
                issue_number=issue_number,
                change=change,
                routing=cast(Routing, (role, action)),
                state="open",
                created_order=1,
                authoritative=True,
            ),
        ),
        source_total_count=1,
        incomplete_results=False,
        exhausted=True,
        human_authorized=human_authorized,
    )


def _connector_comment(comment_id: int, body: str, *, trusted: bool = True) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": ({"slug": "chatgpt-codex-connector"} if trusted else None),
    }


def _event(body: str, *, trusted: bool = True) -> dict[str, object]:
    return {
        "action": "created",
        "issue": {
            "number": 142,
            "title": checkin_title(date(2026, 9, 3)),
            "state": "open",
            "labels": [],
        },
        "comment": _connector_comment(102, body, trusted=trusted),
    }


def test_parse_application_request_decodes_revision_bound_worker_result() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None
    assert request.authorization_revision == _REVISION
    assert json.loads(request.raw_worker_result) == _worker_result()


def test_parse_application_request_rejects_old_correlation_shape() -> None:
    with pytest.raises(ValueError, match="exactly three lines"):
        parse_application_request("\n".join((APPLICATION_REQUEST_MARKER, "old", "old", "old")))


def test_plan_application_derives_source_from_fresh_repository_preflight() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(),
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source == WorkerRequest(138, "lead", "explore-change")
    assert json.loads(plan.raw_worker_result or "") == _worker_result()


def test_plan_application_rejects_untrusted_or_stale_ingress() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None

    with pytest.raises(ValueError, match="configured ChatGPT connector"):
        plan_application(
            event=_event(body, trusted=False),
            request=request,
            preflight=_preflight(),
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )

    stale_request = parse_application_request(_effect_request(revision="0" * 40))
    assert stale_request is not None
    with pytest.raises(ValueError, match="authorization revision is stale"):
        plan_application(
            event=_event(_effect_request(revision="0" * 40)),
            request=stale_request,
            preflight=_preflight(),
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_plan_application_rejects_worker_claim_that_differs_from_fresh_selection() -> None:
    body = _effect_request(
        _worker_result(action="resolve-question", result_kind="human-decision-required")
    )
    request = parse_application_request(body)
    assert request is not None
    with pytest.raises(ValueError, match="does not match fresh repository Action"):
        plan_application(
            event=_event(body),
            request=request,
            preflight=_preflight(),
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_application_boundary_does_not_replay_dispatch_artifacts() -> None:
    source = Path("src/investment_strategy/scheduled_agent_application_bridge.py").read_text(
        encoding="utf-8"
    )
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")

    assert "fetch_dispatch_result" not in source
    assert "scheduled_agent_dispatch_result" not in source
    assert "Dispatch-Request-Comment-ID" not in source
    assert "Dispatch-Run-ID" not in source
    assert workflow.count("startsWith(github.event.comment.body, 'EFFECT_REQUEST')") == 1
    assert "VALIDATION_RESOURCE_REQUEST" not in workflow
    assert "WORK_PRODUCT_REQUEST" not in workflow
    assert "FORMALIZE_CHANGE_REQUEST" not in workflow
