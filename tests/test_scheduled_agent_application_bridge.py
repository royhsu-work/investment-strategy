"""Regression coverage for fresh repository-authorized application ingress."""

from __future__ import annotations

import base64
import json
import sys
from datetime import date
from pathlib import Path
from typing import cast

import pytest

import investment_strategy.scheduled_agent_application_bridge as bridge
from investment_strategy.scheduled_agent_application_bridge import (
    APPLICATION_REQUEST_MARKER,
    AUTHORIZATION_REVISION_PREFIX,
    parse_application_request,
    plan_application,
)
from investment_strategy.scheduled_agent_carrier import CarrierRequired, make_carrier_plan
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
    assert "End invocation at CarrierRequired boundary" in workflow
    assert workflow.count("steps.apply.outputs.carrier_required != 'true'") == 8


def test_main_exits_at_carrier_boundary_before_formal_continuation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    worker_result = _worker_result(
        action="implement-change",
        role="executor",
        result_kind="spec-blocker",
    )
    worker_result["change"] = "carrier-exit-change"
    body = _effect_request(worker_result, revision=_REVISION)
    event = _event(body)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    output_path = tmp_path / "github-output.txt"
    source = WorkerRequest(138, "executor", "implement-change")
    carrier_plan = make_carrier_plan(
        repository=_REPOSITORY,
        issue_number=138,
        change="carrier-exit-change",
        action="implement-change",
        authorization_revision=_REVISION,
        operation="pull-request-ready",
        target={"pull_request_number": 226},
        expected={"head_sha": _REVISION},
        requested={"head_sha": _REVISION, "draft": False},
        expected_postcondition={"draft": False},
    )
    events: list[str] = []

    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scheduled_agent_application_bridge",
            "--event-path",
            str(event_path),
            "--revision",
            _REVISION,
            "--default-branch",
            "main",
        ],
    )
    monkeypatch.setattr(bridge, "_fresh_event_observation", lambda *_args: None)
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(
            action="implement-change",
            issue_number=138,
            change="carrier-exit-change",
        ),
    )
    monkeypatch.setattr(
        bridge,
        "plan_application",
        lambda **_kwargs: bridge.ApplicationPlan(
            should_apply=True,
            source=source,
            raw_worker_result=json.dumps(worker_result),
        ),
    )

    def raise_carrier(*_args: object, **_kwargs: object) -> object:
        events.append("application")
        raise CarrierRequired(carrier_plan)

    monkeypatch.setattr(bridge, "run_guarded_effect_application", raise_carrier)
    monkeypatch.setattr(
        bridge,
        "_write_carrier_outputs",
        lambda result: events.append(f"carrier:{result.carrier_plan.plan_id}"),
    )
    monkeypatch.setattr(
        bridge,
        "_write_validation_outputs",
        lambda target: events.append(f"validation:{target}"),
    )

    assert bridge.main() == 0

    assert events == ["application", f"carrier:{carrier_plan.plan_id}", "validation:None"]
    output = capsys.readouterr().out
    assert '"carrier_required": true' in output
    assert '"effects": 0' in output
    assert "ACTION_RESULT" not in output
    assert "SLICE_CHECKPOINT" not in output
