from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import pytest

from investment_strategy import issue_comment_bridge as bridge
from investment_strategy.scheduled_agent_checkin import checkin_title
from investment_strategy.workflow_dispatch import (
    DispatchDecision,
    ObservationProvenance,
    Routing,
)

WORKFLOW_PATH = Path(".github/workflows/scheduled-agent-bridge.yml")
REQUEST_BODY = "DISPATCH_REQUEST\nRequested-At: 2026-09-03T03:45:00Z"
REVISION = "cb8f9ec12d826e0d71897a4c73ece961d00df59e"


def _event(
    *,
    issue_number: int = 142,
    comment_id: int = 987,
    body: str = REQUEST_BODY,
    state: Literal["open", "closed"] = "open",
    labels: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "action": "created",
        "issue": {
            "number": issue_number,
            "title": checkin_title(date(2026, 9, 3)),
            "state": state,
            "labels": [] if labels is None else labels,
        },
        "comment": {"id": comment_id, "body": body},
    }


def _decision(
    disposition: Literal["AUTHORIZE", "NO_WORK", "FAIL_CLOSED"],
    *,
    issue_number: int | None = None,
    routing: Routing | None = None,
) -> DispatchDecision:
    return DispatchDecision(
        completeness="COMPLETE",
        observation_provenance=ObservationProvenance.QUALIFIED,
        formal_issue_ids=(() if issue_number is None else (issue_number,)),
        preactivation_candidate_ids=(),
        selected_issue_id=issue_number,
        selected_routing=routing,
        disposition=disposition,
        reason="test decision",
    )


def test_bridge_is_run_scoped_transport_without_mailbox_semantics() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "issue_comment:" in workflow
    assert "types: [created]" in workflow
    assert "run-name: Scheduled Agent Dispatch ${{ github.event.comment.id }}" in workflow
    assert "issues: read" in workflow
    assert "actions: write" in workflow
    assert "Resume exact incomplete application before semantic dispatch" in workflow
    assert "ref: ${{ github.event.repository.default_branch }}" in workflow
    assert "persist-credentials: false" in workflow
    assert "uv run python -m investment_strategy.issue_comment_bridge" in workflow
    assert '--result-payload "$RUNNER_TEMP/dispatch-result.json"' in workflow
    assert "actions/upload-artifact@v7" in workflow
    assert "name: dispatch-result.json" in workflow
    assert "archive: false" in workflow
    assert "Build plaintext JSON dispatch result" not in workflow
    assert "DISPATCH_DECISION" not in workflow
    assert "BEGIN_SCHEDULED_AGENT_DISPATCH_RESULT" not in workflow
    assert "END_SCHEDULED_AGENT_DISPATCH_RESULT" not in workflow
    for forbidden in ("AGENT_RUNTIME_CHECKIN_ISSUE", "--comments-path", "ISSUE_NUMBER"):
        assert forbidden not in workflow


def test_request_and_run_name_parsers_require_exact_identity() -> None:
    request = bridge.parse_dispatch_request(REQUEST_BODY)
    assert request is not None
    assert request.requested_at == "2026-09-03T03:45:00Z"
    assert bridge.render_dispatch_run_name(987) == "Scheduled Agent Dispatch 987"
    assert bridge.parse_dispatch_run_name("Scheduled Agent Dispatch 987") == 987
    assert bridge.parse_dispatch_run_name("Scheduled Agent Dispatch 0987") is None
    assert bridge.render_application_run_name(654) == "Scheduled Agent Application 654"
    assert bridge.parse_application_run_name("Scheduled Agent Application 654") == 654
    assert bridge.parse_application_run_name("Scheduled Agent Application 0654") is None

    for body in (
        "DISPATCH_REQUEST",
        "DISPATCH_REQUEST\nRequested-At:",
        f"{REQUEST_BODY}\nExtra: nope",
        " DISPATCH_REQUEST\nRequested-At: 2026-09-03T03:45:00Z",
    ):
        assert bridge.parse_dispatch_request(body) is None


def test_dispatch_result_document_round_trips_one_machine_decision() -> None:
    decision = _decision(
        "AUTHORIZE",
        issue_number=138,
        routing=("executor", "implement-change"),
    )
    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=decision,
    )
    payload = json.loads(rendered)

    assert payload == {
        "schema": "scheduled-agent-dispatch-result/v1",
        "request_comment_id": 987,
        "default_branch_revision": REVISION,
        "disposition": "AUTHORIZE",
        "issue_number": 138,
        "action": "implement-change",
    }
    assert "role" not in payload

    parsed = bridge.parse_dispatch_result_document(rendered)
    assert parsed.issue_number == 138
    assert parsed.role == "executor"
    assert parsed.action == "implement-change"


def test_dispatch_result_document_rejects_invalid_action_and_extra_role() -> None:
    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=_decision(
            "AUTHORIZE",
            issue_number=138,
            routing=("executor", "merge-implementation-pr"),
        ),
    )
    payload = json.loads(rendered)

    payload["action"] = "merge-pr"
    with pytest.raises(RuntimeError, match="Action is invalid"):
        bridge.parse_dispatch_result_document(json.dumps(payload))

    payload["action"] = "merge-implementation-pr"
    payload["role"] = "executor"
    with pytest.raises(RuntimeError, match="schema is invalid"):
        bridge.parse_dispatch_result_document(json.dumps(payload))


@pytest.mark.parametrize("disposition", ["NO_WORK", "FAIL_CLOSED"])
def test_non_authorizing_decisions_have_no_selected_work(
    disposition: Literal["NO_WORK", "FAIL_CLOSED"],
) -> None:
    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=_decision(disposition),
    )
    parsed = bridge.parse_dispatch_result_document(rendered)
    assert parsed.disposition == disposition
    assert parsed.issue_number is None
    assert parsed.action is None
    assert parsed.reason == "test decision"


def test_dispatch_plan_uses_only_current_day_shard_identity() -> None:
    decision = _decision(
        "AUTHORIZE",
        issue_number=138,
        routing=("executor", "implement-change"),
    )
    plan = bridge.plan_dispatch_decision(
        event=_event(),
        default_branch_revision=REVISION,
        decision=decision,
    )
    assert plan.should_emit is True
    assert plan.issue_number == 142
    assert plan.request_comment_id == 987
    assert plan.result_body is not None
    payload = json.loads(plan.result_body)
    assert payload["issue_number"] == 138
    assert payload["action"] == "implement-change"
    assert "role" not in payload

    formal_shard = _event(labels=[{"name": "action:implement-change"}])
    assert (
        bridge.plan_dispatch_decision(
            event=formal_shard,
            default_branch_revision=REVISION,
            decision=_decision("NO_WORK"),
        ).should_emit
        is False
    )


def test_production_dispatch_delegates_to_fresh_runtime_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight = object()
    decision = _decision("NO_WORK")
    observed: dict[str, object] = {}

    def fake_acquire(repository: str, token: str) -> object:
        observed["repository"] = repository
        observed["token"] = token
        return preflight

    def fake_classify(value: object) -> DispatchDecision:
        observed["preflight"] = value
        return decision

    monkeypatch.setattr(bridge, "acquire_current_github_preflight", fake_acquire)
    monkeypatch.setattr(bridge, "classify_dispatch", fake_classify)

    assert bridge.acquire_production_dispatch_decision("owner/repo", "token") is decision
    assert observed == {
        "repository": "owner/repo",
        "token": "token",
        "preflight": preflight,
    }


def test_shard_date_is_timezone_bound_and_not_workflow_state() -> None:
    from investment_strategy.scheduled_agent_checkin import parse_checkin_day, taipei_day

    assert taipei_day(datetime(2026, 9, 2, 16, 30, tzinfo=UTC)) == date(2026, 9, 3)
    payload = {
        "number": 142,
        "title": checkin_title(date(2026, 9, 3)),
        "state": "open",
        "labels": [],
    }
    assert parse_checkin_day(payload) == date(2026, 9, 3)
    assert parse_checkin_day({**payload, "labels": [{"name": "action:implement-change"}]}) is None


def _effect_request_comment(
    *,
    comment_id: int,
    created_at: str,
    action: str = "explore-change",
    role: str = "lead",
    result_kind: str = "proposal-ready",
) -> dict[str, object]:
    import base64

    worker_result = {
        "issue_number": 138,
        "role": role,
        "action": action,
        "change": "unset",
        "result_kind": result_kind,
        "evidence_ref": "same-evidence",
        "result_content": "same semantic payload",
        "requested_effects": [],
    }
    raw = json.dumps(worker_result, sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return {
        "id": comment_id,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                f"Authorization-Revision: {REVISION}",
                f"Worker-Result-B64: {encoded}",
            )
        ),
        "created_at": created_at,
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }


def _application_decision_comment(
    request: dict[str, object],
    *,
    disposition: str = "ACCEPTED",
    comment_id: int = 700,
) -> dict[str, object]:
    body = request["body"]
    assert isinstance(body, str)
    lines = body.splitlines()
    authorization_revision = lines[1].removeprefix("Authorization-Revision: ")
    encoded = lines[2].removeprefix("Worker-Result-B64: ")
    raw = base64.b64decode(encoded.encode("ascii"), validate=True).decode("utf-8")
    worker = json.loads(raw)
    return {
        "id": comment_id,
        "body": "\n".join(
            (
                "APPLICATION_DECISION",
                f"Request-Comment: {request['id']}",
                f"Request-Body-SHA256: {hashlib.sha256(body.encode('utf-8')).hexdigest()}",
                f"Authorization-Revision: {authorization_revision}",
                f"Issue: {worker['issue_number']}",
                f"Role: {worker['role']}",
                f"Action: {worker['action']}",
                f"Change: {worker['change']}",
                f"Result-Kind: {worker['result_kind']}",
                f"Disposition: {disposition}",
                f"Worker-Result-SHA256: {hashlib.sha256(raw.encode('utf-8')).hexdigest()}",
                f"Application-Intent-B64: {encoded}",
                "Reason: test",
            )
        ),
        "created_at": "2026-09-18T01:30:00Z",
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }


def _current_source_issue() -> dict[str, object]:
    return {
        "number": 138,
        "title": checkin_title(date(2026, 9, 3)),
        "state": "open",
        "created_at": "2026-09-17T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "action:explore-change"}],
        "body": "Change: unset",
    }


def test_missing_acceptance_is_not_resumed_before_semantic_replay() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-acceptance-missing"


def test_one_accepted_intent_is_resumed_before_semantic_replay() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )
    decision = _application_decision_comment(request)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision]
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "completed",
                        "run_attempt": 1,
                    }
                ]
            }
        if path == "actions/runs/777/jobs":
            return {"jobs": [{"id": 888, "name": "apply"}]}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.request_comment_id == 654
    assert completion.job_id == 888


def test_rejected_intent_returns_ownership_to_later_semantic_dispatch() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )
    decision = _application_decision_comment(request, disposition="REJECTED")

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision]
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "REJECTED"
    assert completion.reason == "application-completion-rejected"


def test_distinct_accepted_requests_never_alias_by_equal_payload() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654,
            created_at="2026-09-18T01:00:00Z",
        ),
        _effect_request_comment(
            comment_id=655,
            created_at="2026-09-18T01:01:00Z",
        ),
    ]
    decisions = [
        _application_decision_comment(requests[0], comment_id=700),
        _application_decision_comment(requests[1], comment_id=701),
    ]

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return requests
        if path.startswith("issues/138/comments?"):
            return decisions
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "AMBIGUOUS"
    assert completion.reason == "application-completion-accepted-ambiguous"
