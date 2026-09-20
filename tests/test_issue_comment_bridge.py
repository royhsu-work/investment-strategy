from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, cast

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
    issue_number: int = 138,
    change: str = "unset",
    authorization_revision: str = REVISION,
) -> dict[str, object]:
    import base64

    worker_result = {
        "issue_number": issue_number,
        "role": role,
        "action": action,
        "change": change,
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
                f"Authorization-Revision: {authorization_revision}",
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


def _formal_frontier_comment(
    comment_id: int,
    *,
    action: str,
    role: str,
    result: str,
    successor: str,
    request_id: int,
    change: str,
) -> dict[str, object]:
    body = "\n".join(
        (
            "ACTION_RESULT",
            "Workflow: #138",
            f"Change: {change}",
            f"Action: {action}",
            f"Role: {role}",
            f"Result: {result.upper().replace('-', '_')}",
            f"Revision: {REVISION}",
            f"Default-Branch-Revision: {REVISION}",
            "Application-Correlation: "
            f"application:{request_id}:138:{change}:{role}:{action}:{result}:{REVISION}",
            f"Repository-derived successor: {successor}",
        )
    )
    return {
        "id": comment_id,
        "body": body,
        "created_at": f"2026-09-18T02:00:{comment_id // 10:02d}Z",
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }


def _frontier_lifecycle(
    transitions: list[tuple[int, str, str | None]],
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for index, (comment_id, current_action, successor_action) in enumerate(transitions):
        second = index + 1
        events.append(
            {
                "id": comment_id,
                "event": "commented",
                "created_at": f"2026-09-18T02:00:{comment_id // 10:02d}Z",
            }
        )
        if successor_action is None:
            continue
        # A -> A has no label write at the second occurrence.  The formal
        # qualifier proves that recurrence from the preceding bound result.
        if second > 1 and successor_action == current_action:
            continue
        events.extend(
            (
                {
                    "id": 1000 + index * 2,
                    "event": "unlabeled",
                    "created_at": f"2026-09-18T02:00:{comment_id // 10 + 1:02d}Z",
                    "label": {"name": f"action:{current_action}"},
                },
                {
                    "id": 1001 + index * 2,
                    "event": "labeled",
                    "created_at": f"2026-09-18T02:00:{comment_id // 10 + 1:02d}Z",
                    "label": {"name": f"action:{successor_action}"},
                },
            )
        )
    return events


@pytest.mark.parametrize(
    ("topology", "formal_comments", "transitions"),
    (
        (
            "A->A",
            (
                _formal_frontier_comment(
                    80,
                    action="implement-change",
                    role="executor",
                    result="more-implementation-required",
                    successor="Executor / implement-change",
                    request_id=80,
                    change="recurrence-a-a",
                ),
                _formal_frontier_comment(
                    100,
                    action="implement-change",
                    role="executor",
                    result="more-implementation-required",
                    successor="Executor / implement-change",
                    request_id=100,
                    change="recurrence-a-a",
                ),
            ),
            [
                (80, "review-implementation", "implement-change"),
                (100, "implement-change", "implement-change"),
            ],
        ),
        (
            "A->B->A",
            (
                _formal_frontier_comment(
                    80,
                    action="implement-change",
                    role="executor",
                    result="spec-blocker",
                    successor="Lead / resolve-question",
                    request_id=80,
                    change="recurrence-a-b-a",
                ),
                _formal_frontier_comment(
                    100,
                    action="resolve-question",
                    role="lead",
                    result="ready",
                    successor="Executor / implement-change",
                    request_id=100,
                    change="recurrence-a-b-a",
                ),
            ),
            [
                (80, "implement-change", "resolve-question"),
                (100, "resolve-question", "implement-change"),
            ],
        ),
    ),
)
def test_historical_same_action_application_does_not_block_current_frontier(
    topology: str,
    formal_comments: tuple[dict[str, object], ...],
    transitions: list[tuple[int, str, str | None]],
) -> None:
    del topology
    source = bridge.WorkerRequest(138, "executor", "implement-change")
    change = str(formal_comments[-1]["body"]).split("Change: ", 1)[1].splitlines()[0]
    historical_request = _effect_request_comment(
        comment_id=50,
        created_at="2026-09-18T01:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="more-implementation-required",
        issue_number=138,
        change=change,
    )
    historical_decision = _application_decision_comment(historical_request, comment_id=60)
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:implement-change"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [historical_request]
        if path.startswith("issues/138/comments?"):
            return [historical_decision, *formal_comments]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle(transitions)
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_same_action_frontier_acceptance_binds_its_own_formal_result() -> None:
    source = bridge.WorkerRequest(138, "executor", "implement-change")
    change = "recurrence-a-a-current"
    current_request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="more-implementation-required",
        issue_number=138,
        change=change,
    )
    decision = _application_decision_comment(current_request, comment_id=91)
    predecessor = _formal_frontier_comment(
        80,
        action="implement-change",
        role="executor",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=70,
        change=change,
    )
    current = _formal_frontier_comment(
        100,
        action="implement-change",
        role="executor",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=90,
        change=change,
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:implement-change"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [current_request]
        if path.startswith("issues/138/comments?"):
            return [decision, predecessor, current]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle(
                [
                    (80, "review-implementation", "implement-change"),
                    (100, "implement-change", "implement-change"),
                ]
            )
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion.state == "COMPLETE"
    assert completion.reason == "application-completion-complete"
    assert completion.request_comment_id == 90


def test_accepted_formal_result_waits_for_requested_effect_postconditions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(138, "lead", "finalize-change")
    change = "archive-postcondition-recovery"
    requested_effects = [
        {
            "kind": "issue-comment",
            "payload_json": json.dumps(
                {
                    "issue_number": 138,
                    "body": (
                        "ARCHIVE_REQUEST\n"
                        "Workflow: #138\n"
                        f"Change: {change}\n"
                        "Action: finalize-change\n"
                        f"Revision: {REVISION}"
                    ),
                },
                sort_keys=True,
            ),
        },
        {
            "kind": "github-mutation",
            "payload_json": json.dumps(
                {
                    "issue_number": 138,
                    "operation": "workflow-dispatch",
                    "workflow_id": "openspec-archive.yml",
                    "ref": "main",
                    "inputs": {
                        "change": change,
                        "issue": "138",
                        "revision": REVISION,
                        "request_key": f"archive-138-{REVISION}",
                    },
                },
                sort_keys=True,
            ),
        },
    ]
    worker = {
        "issue_number": 138,
        "role": "lead",
        "action": "finalize-change",
        "change": change,
        "result_kind": "archive-ready",
        "evidence_ref": "archive-evidence",
        "result_content": "archive evidence",
        "requested_effects": requested_effects,
    }
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    request = {
        "id": 90,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                f"Authorization-Revision: {REVISION}",
                f"Worker-Result-B64: {encoded}",
            )
        ),
        "created_at": "2026-09-18T02:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }
    decision = _application_decision_comment(request, comment_id=91)
    formal = _formal_frontier_comment(
        100,
        action="finalize-change",
        role="lead",
        result="archive-ready",
        successor="Reviewer / review-archive",
        request_id=90,
        change=change,
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }
    monkeypatch.setattr(
        bridge,
        "requested_effect_postconditions_complete",
        lambda **_kwargs: False,
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "finalize-change", "review-archive")])
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 90",
                        "status": "completed",
                        "conclusion": "success",
                        "run_attempt": 1,
                    }
                ]
            }
        if path == "actions/runs/777/jobs":
            return {
                "jobs": [
                    {
                        "id": 888,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ]
            }
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE", completion
    assert completion.reason == "application-completion-resuming"
    assert completion.request_comment_id == 90
    assert completion.job_id == 888


def test_completed_predecessor_acceptance_does_not_compete_with_new_frontier() -> None:
    source = bridge.WorkerRequest(138, "executor", "implement-change")
    change = "recurrence-a-a-new-occurrence"
    predecessor_request = _effect_request_comment(
        comment_id=70,
        created_at="2026-09-18T01:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="more-implementation-required",
        issue_number=138,
        change=change,
    )
    predecessor_decision = _application_decision_comment(predecessor_request, comment_id=71)
    predecessor_frontier = _formal_frontier_comment(
        80,
        action="implement-change",
        role="executor",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=70,
        change=change,
    )
    current_request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T03:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="more-implementation-required",
        issue_number=138,
        change=change,
    )
    current_decision = _application_decision_comment(current_request, comment_id=91)
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:implement-change"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [predecessor_request, current_request]
        if path.startswith("issues/138/comments?"):
            return [predecessor_decision, predecessor_frontier, current_decision]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(80, "review-implementation", "implement-change")])
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 90",
                        "status": "completed",
                        "conclusion": "failure",
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
        now=datetime(2026, 9, 18, 4, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-resuming"
    assert completion.request_comment_id == 90
    assert completion.job_id == 888


def test_current_frontier_reuses_formal_ancestry_after_main_advances() -> None:
    source = bridge.WorkerRequest(138, "executor", "implement-change")
    advanced_revision = "a" * 40
    formal = _formal_frontier_comment(
        100,
        action="implement-change",
        role="executor",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=90,
        change="frontier-main-advance",
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:implement-change"}],
        "body": "Change: frontier-main-advance",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return []
        if path.startswith("issues/138/comments?"):
            return [formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "implement-change", "implement-change")])
        if path == f"compare/{REVISION}...{advanced_revision}":
            return {"status": "ahead", "base_commit": {"sha": REVISION}}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=advanced_revision,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_preaccept_live_application_run_is_not_redispatched() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
        authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return []
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "in_progress",
                        "run_attempt": 1,
                    }
                ]
            }
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-preaccept-in-progress"
    assert completion.job_id is None


def _completion_matrix_reader(
    requests: list[dict[str, object]],
    *,
    live_ids: set[int] | None = None,
    accepted_ids: set[int] | None = None,
    rejected_ids: set[int] | None = None,
) -> bridge.GitHubReader:
    live_ids = set() if live_ids is None else live_ids
    accepted_ids = set() if accepted_ids is None else accepted_ids
    rejected_ids = set() if rejected_ids is None else rejected_ids
    request_ids = [int(cast(int, request["id"])) for request in requests]
    decisions = [
        _application_decision_comment(
            request,
            disposition="ACCEPTED" if int(cast(int, request["id"])) in accepted_ids else "REJECTED",
            comment_id=700 + index,
        )
        for index, request in enumerate(requests)
        if int(cast(int, request["id"])) in accepted_ids
        or int(cast(int, request["id"])) in rejected_ids
    ]
    run_by_request = {request_id: 9000 + index for index, request_id in enumerate(request_ids)}
    runs = [
        {
            "id": run_by_request[cast(int, request["id"])],
            "display_title": f"Scheduled Agent Application {request['id']}",
            "status": "in_progress" if request["id"] in live_ids else "completed",
            "conclusion": None if request["id"] in live_ids else "failure",
            "run_attempt": 1,
        }
        for request in requests
    ]

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return requests
        if path.startswith("issues/138/comments?"):
            return decisions
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return []
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": runs}
        if path.startswith("actions/runs/") and path.endswith("/jobs"):
            run_id = int(path.split("/")[2])
            return {
                "jobs": [
                    {
                        "id": run_id + 100,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        raise AssertionError(path)

    return fake_read


@pytest.mark.parametrize("count", (1, 2, 3))
def test_terminal_preactcept_candidates_do_not_compete_by_raw_cardinality(count: int) -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654 + index,
            created_at=f"2026-09-18T01:0{index}:00Z",
            authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        )
        for index in range(count)
    ]

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=_completion_matrix_reader(requests),
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "REJECTED"
    assert completion.reason == "application-completion-terminal-no-accept"
    assert completion.state != "AMBIGUOUS"


def test_terminal_preactcept_candidate_survives_archived_authorization_revision() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
        authorization_revision="5ef5fd95e57c563a03a96df85248cdb4f3c5f502",
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return []
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9000,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        if path == "actions/runs/9000/jobs":
            return {
                "jobs": [
                    {
                        "id": 9100,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        if path.startswith("compare/"):
            raise OSError("archived commit is no longer observable")
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "REJECTED"
    assert completion.reason == "application-completion-terminal-no-accept"


def test_terminal_noise_plus_one_live_candidate_waits_for_live_ingress() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654 + index,
            created_at=f"2026-09-18T01:0{index}:00Z",
            authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        )
        for index in range(3)
    ]

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=_completion_matrix_reader(requests, live_ids={656}),
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-preaccept-in-progress"
    assert completion.request_comment_id == 656


def test_rejected_noise_plus_one_live_candidate_does_not_release_ownership() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654 + index,
            created_at=f"2026-09-18T01:0{index}:00Z",
            authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        )
        for index in range(3)
    ]

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=_completion_matrix_reader(
            requests,
            live_ids={656},
            rejected_ids={654, 655},
        ),
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.request_comment_id == 656


def test_terminal_noise_plus_one_accepted_intent_owns_continuation() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654 + index,
            created_at=f"2026-09-18T01:0{index}:00Z",
            authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        )
        for index in range(3)
    ]

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=_completion_matrix_reader(requests, accepted_ids={654}),
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-resuming"
    assert completion.request_comment_id == 654


def test_deleted_ingress_after_accept_uses_immutable_intent() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )
    decision = _application_decision_comment(request)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return []
        if path.startswith("issues/138/comments?"):
            return [decision]
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return []
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "in_progress",
                        "run_attempt": 1,
                    }
                ]
            }
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
    assert completion.reason == "application-completion-in-progress"


def test_edited_ingress_after_accept_cannot_block_immutable_intent() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    original = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )
    edited = {**original, "body": "EFFECT_REQUEST\nmalformed-after-accept"}
    decision = _application_decision_comment(original)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [edited]
        if path.startswith("issues/138/comments?"):
            return [decision]
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return []
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "in_progress",
                        "run_attempt": 1,
                    }
                ]
            }
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
    assert completion.reason == "application-completion-in-progress"


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
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return []
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": []}
        if path.startswith("compare/"):
            return {}
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
    assert completion.reason == "application-completion-preaccept-evidence-unknown"


def test_unrelated_legacy_request_does_not_poison_current_source() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    unrelated = _effect_request_comment(
        comment_id=653,
        created_at="2026-09-18T00:59:00Z",
        issue_number=999,
    )
    body = unrelated["body"]
    assert isinstance(body, str)
    encoded = body.splitlines()[2].removeprefix("Worker-Result-B64: ")
    unrelated["body"] = "\n".join(
        (
            "EFFECT_REQUEST",
            "Dispatch-Request-Comment-ID: 100",
            "Dispatch-Run-ID: 200",
            f"Worker-Result-B64: {encoded}",
        )
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [unrelated]
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

    assert completion.state == "NONE"
    assert completion.reason == "application-completion-none"


def test_same_source_malformed_legacy_request_still_fails_closed() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    malformed = _effect_request_comment(
        comment_id=653,
        created_at="2026-09-18T00:59:00Z",
    )
    body = malformed["body"]
    assert isinstance(body, str)
    encoded = body.splitlines()[2].removeprefix("Worker-Result-B64: ")
    malformed["body"] = "\n".join(
        (
            "EFFECT_REQUEST",
            "Dispatch-Request-Comment-ID: 100",
            "Dispatch-Run-ID: 200",
            f"Worker-Result-B64: {encoded}",
        )
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [malformed]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return []
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": []}
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
    assert completion.reason == "application-completion-preaccept-evidence-unknown"


def test_protocol_request_without_acceptance_returns_source_ownership() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-19T06:08:00Z",
        authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return []
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": []}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=fake_read,
        now=datetime(2026, 9, 19, 7, 0, tzinfo=UTC),
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-preaccept-evidence-unknown"


def test_preprotocol_inert_request_is_retired_without_semantic_replay() -> None:
    source = bridge.WorkerRequest(234, "lead", "resolve-question")
    legacy_revision = "6ffd99baee9289090b5c2178a5ce6801d8f1f335"
    change = "source-decision-explore-materialization"
    request = _effect_request_comment(
        comment_id=5729806158,
        created_at="2026-09-18T12:09:34Z",
        action="resolve-question",
        role="lead",
        result_kind="ready-for-openspec-review",
        issue_number=234,
        change=change,
        authorization_revision=legacy_revision,
    )
    issue = {
        "number": 234,
        "state": "open",
        "created_at": "2026-09-09T10:59:41Z",
        "closed_at": None,
        "labels": [{"name": "action:resolve-question"}],
        "body": f"Change: {change}",
    }
    predecessor = {
        "id": 10,
        "body": "\n".join(
            (
                "ACTION_RESULT",
                "Workflow: #234",
                f"Change: {change}",
                "Role: executor",
                "Action: implement-change",
                "Result: SPEC_BLOCKER",
                f"Revision: {bridge._APPLICATION_DECISION_PROTOCOL_REVISION}",
                f"Default-Branch-Revision: {bridge._APPLICATION_DECISION_PROTOCOL_REVISION}",
                "Application-Correlation: "
                f"application:1:234:{change}:executor:implement-change:spec-blocker:"
                f"{bridge._APPLICATION_DECISION_PROTOCOL_REVISION}",
                "Repository-derived successor: Lead / resolve-question",
            )
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    predecessor_timeline = [
        {"id": 10, "event": "commented", "created_at": "2026-09-18T12:00:00Z"},
        {
            "id": 11,
            "event": "unlabeled",
            "created_at": "2026-09-18T12:00:01Z",
            "label": {"name": "action:implement-change"},
        },
        {
            "id": 12,
            "event": "labeled",
            "created_at": "2026-09-18T12:00:01Z",
            "label": {"name": "action:resolve-question"},
        },
    ]

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/234/comments?"):
            return [predecessor]
        if path.startswith("issues/234/timeline?"):
            return predecessor_timeline
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 5729806158",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 1,
                    }
                ]
            }
        if path == "actions/runs/777/jobs":
            return {
                "jobs": [
                    {
                        "id": 888,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        if path == f"compare/{legacy_revision}...{bridge._APPLICATION_DECISION_PROTOCOL_REVISION}":
            return {"status": "ahead", "base_commit": {"sha": legacy_revision}}
        if path == "issues/234":
            return issue
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=fake_read,
        now=datetime(2026, 9, 19, 7, 0, tzinfo=UTC),
    )

    assert completion.state == "REJECTED"
    assert completion.reason == "application-completion-rejected"
    assert completion.request_comment_id == 5729806158


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
        if path.startswith("issues/138/timeline?"):
            return []
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
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
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
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
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

    assert completion.state == "AMBIGUOUS"
    assert completion.reason == "application-completion-accepted-ambiguous"
