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
    EffectBatch,
    GitHubEffectAdapter,
    formal_application_correlation,
)
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    WorkerRequest,
    acquire_dispatch_preflight,
)
from investment_strategy.scheduled_agent_validation_resource import ValidationResourceTarget
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    ObservationProvenance,
    Routing,
)

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
    current_state_provenance: ObservationProvenance = ObservationProvenance.QUALIFIED,
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
                current_state_provenance=current_state_provenance,
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
        defer_issue_comments: bool = False,
        allow_pending_continuation: bool = False,
        pending_application_correlation: str | None = None,
    ) -> tuple[EffectBatch, bridge.ApplyResult]:
        assert source == expected_source
        assert request_comment_id == 102
        assert allow_pending_continuation is False
        assert pending_application_correlation is None
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
                "defer_issue_comments": defer_issue_comments,
                "allow_pending_continuation": allow_pending_continuation,
                "pending_application_correlation": pending_application_correlation,
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
        return EffectBatch(source=source, effects=()), bridge.ApplyResult(True, "applied")

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
            "defer_issue_comments": True,
            "allow_pending_continuation": False,
            "pending_application_correlation": None,
        },
        {
            "request_comment_id": 102,
            "apply_derived": True,
            "materialization_promote_change": True,
            "validated_materialization_revision": target.revision,
            "defer_issue_comments": False,
            "allow_pending_continuation": False,
            "pending_application_correlation": None,
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


def test_plan_application_recovers_a_persisted_validation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    result_body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: resolve-question\n"
        "Role: lead\n"
        "Result: READY_FOR_OPENSPEC_REVIEW\n"
        f"Revision: {_REVISION}\n"
        f"Default-Branch-Revision: {_REVISION}\n"
        "Evidence-Ref: issuecomment-worker-evidence\n"
        "Repository-derived successor: Reviewer / review-openspec\n"
    )
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="ready-for-openspec-review",
        current_revision=_REVISION,
        request_comment_id=777,
    )
    bound_lines = result_body.splitlines()
    bound_lines.insert(
        next(
            index
            for index, line in enumerate(bound_lines)
            if line.startswith("Default-Branch-Revision:")
        )
        + 1,
        f"Application-Correlation: {correlation}",
    )
    bound_body = "\n".join(bound_lines)
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
    worker_result = {
        "issue_number": 138,
        "role": "lead",
        "action": "resolve-question",
        "change": _CHANGE,
        "result_kind": "ready-for-openspec-review",
        "evidence_ref": "issuecomment-worker-evidence",
        "result_content": result_body,
        "requested_effects": [
            {
                "kind": "github-mutation",
                "payload_json": json.dumps(materialization, sort_keys=True),
            },
            {
                "kind": "issue-comment",
                "payload_json": json.dumps({"issue_number": 138, "body": result_body}),
            },
        ],
    }
    body = _effect_request(worker_result)
    request = parse_application_request(body)
    assert request is not None
    comment = {
        "id": 900,
        "body": bound_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda *_args, **_kwargs: {
            "number": 138,
            "state": "open",
            "created_at": "2026-09-17T00:00:00Z",
            "closed_at": None,
            "labels": [{"name": "action:resolve-question"}],
            "body": f"Change: {_CHANGE}",
        },
    )
    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda _repository, _token, path: (
            (comment,)
            if "comments" in path
            else (
                {
                    "event": "commented",
                    "id": 900,
                    "created_at": "2026-09-17T00:00:00Z",
                },
            )
        ),
    )

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(
            action="resolve-question",
            issue_number=138,
            change=_CHANGE,
            current_state_provenance=ObservationProvenance.INDETERMINATE,
        ),
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source == source
    assert plan.pending_continuation
    assert plan.pending_application_correlation == correlation


def test_plan_application_recovers_persisted_result_after_main_advances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    historical_revision = "3" * 40
    current_revision = "4" * 40
    result_body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: resolve-question\n"
        "Role: lead\n"
        "Result: READY_FOR_OPENSPEC_REVIEW\n"
        f"Revision: {historical_revision}\n"
        f"Default-Branch-Revision: {historical_revision}\n"
        "Evidence-Ref: issuecomment-worker-evidence\n"
        "Repository-derived successor: Reviewer / review-openspec\n"
    )
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="ready-for-openspec-review",
        current_revision=historical_revision,
        request_comment_id=777,
    )
    bound_lines = result_body.splitlines()
    bound_lines.insert(
        next(
            index
            for index, line in enumerate(bound_lines)
            if line.startswith("Default-Branch-Revision:")
        )
        + 1,
        f"Application-Correlation: {correlation}",
    )
    bound_body = "\n".join(bound_lines)
    materialization = {
        "issue_number": 138,
        "operation": "application-materialize",
        "expected_change": _CHANGE,
        "change": _CHANGE,
        "branch": f"agent/{_CHANGE}",
        "base_sha": historical_revision,
        "message": "test validation boundary",
        "files": [],
        "pr_number": 178,
    }
    worker_result = {
        "issue_number": 138,
        "role": "lead",
        "action": "resolve-question",
        "change": _CHANGE,
        "result_kind": "ready-for-openspec-review",
        "evidence_ref": "issuecomment-worker-evidence",
        "result_content": result_body,
        "requested_effects": [
            {
                "kind": "github-mutation",
                "payload_json": json.dumps(materialization, sort_keys=True),
            },
            {
                "kind": "issue-comment",
                "payload_json": json.dumps({"issue_number": 138, "body": result_body}),
            },
        ],
    }
    body = _effect_request(worker_result, revision=current_revision)
    request = parse_application_request(body)
    assert request is not None
    comment = {
        "id": 900,
        "body": bound_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    recovery_revision = "2" * 40
    recovery_comment = {
        "id": 899,
        "body": (
            "APPLICATION_RECOVERY\n"
            "Workflow: #138\n"
            f"Change: {_CHANGE}\n"
            "Source: Lead / propose-change\n"
            "Target: Lead / resolve-question\n"
            f"Default-Branch-Revision: {recovery_revision}\n"
            f"Failed-Authorization-Revision: {'1' * 40}\n"
            "Request-Comment-ID: 901\n"
            "Reason: partial-first-activation"
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda *_args, **_kwargs: {
            "number": 138,
            "state": "open",
            "created_at": "2026-09-17T00:00:00Z",
            "closed_at": None,
            "labels": [{"name": "action:resolve-question"}],
            "body": f"Change: {_CHANGE}",
        },
    )
    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda _repository, _token, path: (
            (recovery_comment, comment)
            if "comments" in path
            else (
                {
                    "event": "commented",
                    "id": 899,
                    "created_at": "2026-09-17T00:00:00Z",
                },
                {
                    "event": "unlabeled",
                    "id": 901,
                    "created_at": "2026-09-17T00:00:01Z",
                    "label": {"name": "action:propose-change"},
                },
                {
                    "event": "labeled",
                    "id": 902,
                    "created_at": "2026-09-17T00:00:01Z",
                    "label": {"name": "action:resolve-question"},
                },
                {
                    "event": "commented",
                    "id": 900,
                    "created_at": "2026-09-17T00:00:02Z",
                },
            )
        ),
    )
    ancestry_calls: list[tuple[object, ...]] = []

    def fake_ancestor(*args: str) -> bool:
        ancestry_calls.append(args)
        return True

    monkeypatch.setattr(bridge, "_authorization_revision_is_ancestor", fake_ancestor)

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(
            action="resolve-question",
            issue_number=138,
            change=_CHANGE,
            current_state_provenance=ObservationProvenance.INDETERMINATE,
        ),
        repository=_REPOSITORY,
        current_revision=current_revision,
    )

    assert plan.should_apply
    assert plan.source == source
    assert plan.pending_continuation
    assert plan.pending_application_correlation == correlation
    assert {call[2] for call in ancestry_calls} == {historical_revision, recovery_revision}


def test_plan_application_recovers_persisted_formal_result_without_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "reviewer", "review-openspec")
    result_body = (
        "REVIEW_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: Reviewer / review-openspec\n"
        "Role: reviewer\n"
        "Result: PASS\n"
        f"Revision: {_REVISION}\n"
        f"Default-Branch-Revision: {_REVISION}\n"
        "Evidence-Ref: issuecomment-worker-evidence\n"
        "Repository-derived successor: Executor / implement-change\n"
    )
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="pass",
        current_revision=_REVISION,
        request_comment_id=777,
    )
    bound_lines = result_body.splitlines()
    bound_lines.insert(
        next(
            index
            for index, line in enumerate(bound_lines)
            if line.startswith("Default-Branch-Revision:")
        )
        + 1,
        f"Application-Correlation: {correlation}",
    )
    bound_body = "\n".join(bound_lines)
    worker_result = {
        "issue_number": 138,
        "role": "reviewer",
        "action": "review-openspec",
        "change": _CHANGE,
        "result_kind": "pass",
        "evidence_ref": "issuecomment-worker-evidence",
        "result_content": result_body,
        "requested_effects": [
            {
                "kind": "issue-comment",
                "payload_json": json.dumps(
                    {"issue_number": 138, "body": result_body},
                    sort_keys=True,
                ),
            }
        ],
    }
    body = _effect_request(worker_result)
    request = parse_application_request(body)
    assert request is not None
    current_issue = {
        "number": 138,
        "title": checkin_title(date(2026, 9, 3)),
        "state": "open",
        "created_at": "2026-09-17T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "action:review-openspec"}],
        "body": f"Change: {_CHANGE}",
    }
    comment = {
        "id": 900,
        "body": bound_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda *_args, **_kwargs: current_issue,
    )
    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda _repository, _token, path: (
            (comment,)
            if "comments" in path
            else (
                {
                    "event": "commented",
                    "id": 900,
                    "created_at": "2026-09-17T00:00:00Z",
                },
            )
        ),
    )

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(
            action="review-openspec",
            issue_number=138,
            change=_CHANGE,
            current_state_provenance=ObservationProvenance.INDETERMINATE,
        ),
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source == source
    assert plan.pending_continuation
    assert plan.pending_application_correlation == correlation


def test_real_issue233_mixed_formal_history_recovers_persisted_review_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(233, "reviewer", "review-openspec")
    change = "operationalize-review-openspec-semantic-proof"
    historical_review_revision = "7f7a376bb052d6b45307ee04587719dcc430cd39"
    review_authorization_revision = "1991e31bf97b0286d5f4affb3dff5e9354b32c9a"
    current_revision = "b708129828e541227095ff801c2801907bae7d2e"
    result_body = (
        "REVIEW_RESULT\n"
        "Workflow: #233\n"
        f"Change: {change}\n"
        "Action: Reviewer / review-openspec\n"
        "Role: reviewer\n"
        "Result: PASS\n"
        f"Revision: {historical_review_revision}\n"
        f"Default-Branch-Revision: {review_authorization_revision}\n"
        "Evidence-Ref: https://github.com/royhsu-work/investment-strategy/pull/247\n"
        "Review-Mode: fresh exact-revision independent reverse-first and forward semantic review\n"
        "Traceability: tasks -> design -> specs -> proposal and proposal -> specs -> design -> tasks are complete for the same exact zero-delta target.\n"
        "Parent: Human-approved repository-wide semantic-consumption scope and the #229 regression boundary are preserved; the active-formal case remains a proof case, not a scope replacement.\n"
        "Boundary: DERIVE -> CHALLENGE -> REALIZE -> CLOSE operationalizes the existing review owner without adding an Action, Result, state, verifier, registry, second workflow graph, or semantic authority.\n"
        "Runtime-Evidence: The current-main closed-history and recovery-ancestry repairs are reused; the proposal keeps the pre-activation -> durable producer/application evidence -> descendant qualification -> typed continuation -> application postcondition chain explicit.\n"
        "Substrate: Strict OpenSpec validation passed 8/8 for the exact PR #247 head, and the remaining Skill/test changes are bounded implementation work on the existing repository Skill/test owners.\n"
        "Safety: Current/default evidence is distinguished from candidate, staged, future, or unavailable proof; application/carrier authority, fresh reauthorization, lifecycle/ABA qualification, and fail-closed behavior remain intact.\n"
        "Skill-Maintenance: The existing agents/skills/openspec-review/SKILL.md is the sole declared procedure owner; validator/wiring coverage is planned on the existing repository-Skill test surface.\n"
        "Findings: None.\n"
        "Repository-derived successor: Executor / implement-change"
    )
    application_correlation = formal_application_correlation(
        source,
        change=change,
        result_kind="pass",
        current_revision=review_authorization_revision,
        request_comment_id=5710940292,
    )
    persisted_body = result_body.replace(
        f"Default-Branch-Revision: {review_authorization_revision}\n",
        (
            f"Default-Branch-Revision: {review_authorization_revision}\n"
            f"Application-Correlation: {application_correlation}\n"
        ),
    )
    recovery_body = (
        "APPLICATION_RECOVERY\n"
        "Workflow: #233\n"
        f"Change: {change}\n"
        "Source: Lead / propose-change\n"
        "Target: Lead / resolve-question\n"
        "Default-Branch-Revision: cf953ef356bdbd05848cdaf74663f4281bbe8a25\n"
        "Failed-Authorization-Revision: 24308310d6d65064ddd3a3d76e43cd3c9dd87cdc\n"
        "Request-Comment-ID: 5693106011\n"
        "Reason: partial-first-activation"
    )
    old_formal_body = (
        "ACTION_RESULT\n"
        "Workflow: #233\n"
        f"Change: {change}\n"
        "Action: resolve-question\n"
        "Role: lead\n"
        "Result: READY_FOR_OPENSPEC_REVIEW\n"
        "Revision: 0923580f161408c2953700b7e07e1c34dd03b5b5\n"
        "Default-Branch-Revision: 0923580f161408c2953700b7e07e1c34dd03b5b5\n"
        "Application-Correlation: application:5709636345:233:operationalize-review-openspec-semantic-proof:lead:resolve-question:ready-for-openspec-review:0923580f161408c2953700b7e07e1c34dd03b5b5\n"
        "Evidence-Ref: https://github.com/royhsu-work/investment-strategy/pull/247\n"
        "Decision: The proposal now includes the review-consumption repair and the residual formal-activation/application closure.\n"
        "Decision: Existing runtime/application owners and the current descendant/recovery evidence remain authoritative; no new state, exception, or review layer is introduced.\n"
        "Verification: PR #247 is the exact carrier for fresh independent review after application-owned materialization and strict OpenSpec validation.\n"
        "Repository-derived successor: Reviewer / review-openspec\n"
    )
    def bot_comment(comment_id: int, body: str) -> dict[str, object]:
        return {
            "id": comment_id,
            "body": body,
            "user": {"login": "github-actions[bot]"},
            "performed_via_github_app": {"slug": "github-actions"},
        }

    recovery_comment = bot_comment(5707223672, recovery_body)
    old_formal_comment = bot_comment(5709649340, old_formal_body)
    persisted_formal_comment = bot_comment(5710947012, persisted_body)
    worker_result = {
        "issue_number": 233,
        "role": "reviewer",
        "action": "review-openspec",
        "change": change,
        "result_kind": "pass",
        "evidence_ref": "https://github.com/royhsu-work/investment-strategy/pull/247",
        "result_content": result_body,
        "requested_effects": [
            {
                "kind": "issue-comment",
                "payload_json": json.dumps(
                    {"issue_number": 233, "body": result_body},
                    sort_keys=True,
                ),
            }
        ],
    }
    request_body = _effect_request(worker_result, revision=current_revision)
    request = parse_application_request(request_body)
    assert request is not None
    event = {
        "action": "created",
        "issue": {
            "number": 252,
            "title": checkin_title(date(2026, 9, 17)),
            "state": "open",
            "labels": [],
        },
        "comment": _connector_comment(5711090028, request_body),
    }
    current_issue = {
        "number": 233,
        "title": "Explore review-openspec semantic gate consumption after #229 PASS",
        "state": "open",
        "created_at": "2026-09-09T07:28:08Z",
        "closed_at": None,
        "labels": [{"name": "action:review-openspec"}],
        "body": f"Change: {change}",
    }
    lifecycle = (
        {
            "id": 30822867782,
            "event": "labeled",
            "created_at": "2026-09-09T11:00:04Z",
            "label": {"name": "action:explore-change"},
        },
        {"id": 5707223672, "event": "commented", "created_at": "2026-09-17T01:52:20Z"},
        {
            "id": 31287353469,
            "event": "unlabeled",
            "created_at": "2026-09-17T01:52:22Z",
            "label": {"name": "action:propose-change"},
        },
        {
            "id": 31287353519,
            "event": "labeled",
            "created_at": "2026-09-17T01:52:22Z",
            "label": {"name": "action:resolve-question"},
        },
        {"id": 5709649340, "event": "commented", "created_at": "2026-09-17T05:56:39Z"},
        {
            "id": 31302117639,
            "event": "unlabeled",
            "created_at": "2026-09-17T07:40:31Z",
            "label": {"name": "action:resolve-question"},
        },
        {
            "id": 31302117669,
            "event": "labeled",
            "created_at": "2026-09-17T07:40:31Z",
            "label": {"name": "action:review-openspec"},
        },
        {"id": 5710947012, "event": "commented", "created_at": "2026-09-17T07:53:07Z"},
    )
    compare_calls: list[str] = []

    def fake_github_json(
        _repo: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == "issues/233":
            return current_issue
        if path.startswith("compare/"):
            compare_calls.append(path)
            failed_revision, _separator, _current = path.removeprefix("compare/").partition("...")
            return {
                "status": "ahead",
                "base_commit": {"sha": failed_revision},
            }
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_github_json", fake_github_json)
    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda _repo, _token, path: (
            (recovery_comment, old_formal_comment, persisted_formal_comment)
            if "comments" in path
            else lifecycle
        ),
    )
    decisions: list[object] = []
    real_qualifier = bridge.qualify_current_formal_consequence

    def capture_qualification(qualification: object) -> object:
        decision = real_qualifier(qualification)
        decisions.append(decision)
        return decision

    monkeypatch.setattr(bridge, "qualify_current_formal_consequence", capture_qualification)
    plan = plan_application(
        event=event,
        request=request,
        preflight=_preflight(
            action="review-openspec",
            issue_number=233,
            change=change,
            current_state_provenance=ObservationProvenance.INDETERMINATE,
        ),
        repository=_REPOSITORY,
        current_revision=current_revision,
    )
    assert plan.should_apply
    assert plan.source == source
    assert plan.pending_continuation
    assert plan.pending_application_correlation == application_correlation
    assert historical_review_revision != review_authorization_revision
    assert any(
        review_authorization_revision in path and current_revision in path
        for path in compare_calls
    )
    assert decisions
    assert getattr(decisions[-1], "qualified", False)


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
