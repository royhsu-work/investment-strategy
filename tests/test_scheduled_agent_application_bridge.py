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
from investment_strategy.scheduled_agent_effects import (
    GitHubEffectAdapter,
    formal_application_correlation,
)
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    WorkerRequest,
    acquire_dispatch_preflight,
)
from investment_strategy.scheduled_agent_validation_resource import ValidationResourceTarget
from investment_strategy.workflow_dispatch import DispatchPreflight, Routing

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "4e3241d7d84a64012bf3b6218442128a4cb48d7a"
_CHANGE = "qualify-active-formal-consequences"


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
    assert plan.request_comment_id == 102
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


def test_main_validation_boundary_preserves_exact_binding_for_fresh_successor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected_source = WorkerRequest(138, "lead", "resolve-question")
    formal_body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: resolve-question\n"
        "Role: lead\n"
        "Result: READY\n"
        f"Revision: {_REVISION}\n"
        "Evidence-Ref: issuecomment-worker-evidence\n"
    )
    materialization = {
        "issue_number": 138,
        "operation": "application-materialize",
        "expected_change": _CHANGE,
        "change": _CHANGE,
        "branch": f"agent/{_CHANGE}",
        "base_sha": _REVISION,
        "message": "test validation boundary",
        "files": [],
        "pr_number": 178,
    }
    worker_result = _worker_result(
        action="resolve-question",
        role="lead",
        result_kind="ready",
    )
    worker_result["change"] = _CHANGE
    worker_result["requested_effects"] = [
        {
            "kind": "issue-comment",
            "payload_json": json.dumps({"issue_number": 138, "body": formal_body}),
        },
        {
            "kind": "github-mutation",
            "payload_json": json.dumps(materialization, sort_keys=True),
        },
    ]
    body = _effect_request(worker_result, revision=_REVISION)
    event = _event(body)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    output_path = tmp_path / "github-output.txt"

    target = ValidationResourceTarget(
        repository=_REPOSITORY,
        revision="b" * 40,
        correlation="effect-request-138",
        pr_number=178,
        change=_CHANGE,
        validation_required=True,
    )
    applications: list[GitHubEffectAdapter] = []
    durable_evidence: list[str] = []
    calls: list[dict[str, object]] = []

    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setattr(bridge, "_fresh_event_observation", lambda *_args: None)
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(
            action="resolve-question",
            issue_number=138,
            change=_CHANGE,
        ),
    )
    monkeypatch.setattr(
        bridge,
        "observe_materialization_target",
        lambda *_args, **_kwargs: target,
    )

    def fake_run(
        _raw_worker_result: str,
        *,
        source: WorkerRequest,
        repository: str,
        token: str,
        current_revision: str,
        request_comment_id: int | None = None,
        apply_derived: bool = True,
        materialization_promote_change: bool = False,
        validated_materialization_revision: str | None = None,
    ) -> tuple[object, bridge.ApplyResult]:
        assert source == expected_source
        assert request_comment_id == 102
        adapter = GitHubEffectAdapter(
            repository,
            token,
            source,
            authorized_change=_CHANGE,
            current_revision=current_revision,
            expected_result_kind="ready",
            request_comment_id=request_comment_id,
        )
        applications.append(adapter)
        calls.append(
            {
                "request_comment_id": request_comment_id,
                "apply_derived": apply_derived,
                "materialization_promote_change": materialization_promote_change,
                "validated_materialization_revision": validated_materialization_revision,
            }
        )
        correlation = formal_application_correlation(
            source,
            change=_CHANGE,
            result_kind="ready",
            current_revision=current_revision,
            request_comment_id=102,
        )
        bound = formal_body.replace(
            "Evidence-Ref: issuecomment-worker-evidence\n",
            (
                f"Application-Correlation: {correlation}\n"
                "Evidence-Ref: issuecomment-worker-evidence\n"
            ),
        )
        if apply_derived:
            assert materialization_promote_change
            assert validated_materialization_revision == target.revision
            assert durable_evidence == [bound]
            assert source.action == "resolve-question"
        else:
            assert not materialization_promote_change
            assert validated_materialization_revision is None
            assert durable_evidence == []
            durable_evidence.append(bound)
        return object(), bridge.ApplyResult(True, "applied")

    monkeypatch.setattr(bridge, "run_guarded_effect_application", fake_run)

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
    assert bridge.main() == 0

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
            "--validation-passed",
            "--validated-revision",
            target.revision,
        ],
    )
    assert bridge.main() == 0

    assert calls == [
        {
            "request_comment_id": 102,
            "apply_derived": False,
            "materialization_promote_change": False,
            "validated_materialization_revision": None,
        },
        {
            "request_comment_id": 102,
            "apply_derived": True,
            "materialization_promote_change": True,
            "validated_materialization_revision": target.revision,
        },
    ]
    assert len(applications) == 2
    assert applications[0] is not applications[1]
    assert all(not hasattr(adapter, "_formal_evidence_observed") for adapter in applications)
    correlation = formal_application_correlation(
        expected_source,
        change=_CHANGE,
        result_kind="ready",
        current_revision=_REVISION,
        request_comment_id=102,
    )
    assert durable_evidence == [
        formal_body.replace(
            "Evidence-Ref: issuecomment-worker-evidence\n",
            (
                f"Application-Correlation: {correlation}\n"
                "Evidence-Ref: issuecomment-worker-evidence\n"
            ),
        )
    ]
    output = capsys.readouterr().out
    assert '"validation_completed": false' in output
    assert '"validation_completed": true' in output


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
            request_comment_id=102,
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
