from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, cast

import pytest

from investment_strategy import issue_comment_bridge as bridge
from investment_strategy import scheduled_agent_carrier as carrier
from investment_strategy.scheduled_agent_checkin import checkin_title
from investment_strategy.scheduled_agent_idle_admission import (
    IdleCandidate,
    IdleDispatchEnvelope,
    make_idle_admission_request,
    parse_idle_admission_event,
    qualify_idle_handoff,
    render_idle_admission_request,
)
from investment_strategy.workflow_dispatch import (
    DispatchDecision,
    ObservationProvenance,
    Routing,
)

WORKFLOW_PATH = Path(".github/workflows/scheduled-agent-bridge.yml")
REQUEST_BODY = "DISPATCH_REQUEST\nRequested-At: 2026-09-03T03:45:00Z"
REVISION = "cb8f9ec12d826e0d71897a4c73ece961d00df59e"
_RECOVERY_TEST_FIELDS = {
    "predecessor_run_id": 7001,
    "predecessor_run_attempt": 1,
    "predecessor_job_id": 7002,
    "predecessor_artifact_id": 7003,
    "predecessor_artifact_digest": "sha256:" + "1" * 64,
    "failure_evidence_sha256": "2" * 64,
    "recovery_episode_sha256": "3" * 64,
}


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


def test_retry_limit_dispatch_result_carries_one_content_addressed_continuation() -> None:
    continuation = bridge.render_application_continuation_request(
        repository="owner/repo",
        issue_number=138,
        original_request_comment_id=987,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=7001,
        predecessor_run_attempt=1,
        predecessor_job_id=7002,
        predecessor_artifact_id=7003,
        predecessor_artifact_digest="sha256:" + "1" * 64,
        failure_evidence_sha256="2" * 64,
        recovery_episode_sha256="3" * 64,
    )
    decision = _decision("FAIL_CLOSED")
    decision = DispatchDecision(
        completeness=decision.completeness,
        observation_provenance=decision.observation_provenance,
        formal_issue_ids=decision.formal_issue_ids,
        preactivation_candidate_ids=decision.preactivation_candidate_ids,
        selected_issue_id=decision.selected_issue_id,
        selected_routing=decision.selected_routing,
        disposition=decision.disposition,
        reason="application-completion-continuation-required",
    )

    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=decision,
        application_continuation=continuation,
    )
    parsed = bridge.parse_dispatch_result_document(rendered)

    assert parsed.application_continuation == continuation
    with pytest.raises(ValueError, match="only valid"):
        bridge.render_dispatch_result_document(
            request_comment_id=987,
            default_branch_revision=REVISION,
            decision=_decision("NO_WORK"),
            application_continuation=continuation,
        )
    malformed = json.loads(rendered)
    malformed["application_continuation"] = "APPLICATION_CONTINUATION\nmalformed"
    with pytest.raises(RuntimeError, match="application continuation"):
        bridge.parse_dispatch_result_document(json.dumps(malformed))


def test_production_shaped_no_work_bootstrap_reaches_one_typed_idle_ingress() -> None:
    """The bridge artifact is consumed once, then Lead's candidate is typed."""

    decision_fixture = _decision("NO_WORK")
    no_work = DispatchDecision(
        completeness=decision_fixture.completeness,
        observation_provenance=decision_fixture.observation_provenance,
        formal_issue_ids=decision_fixture.formal_issue_ids,
        preactivation_candidate_ids=decision_fixture.preactivation_candidate_ids,
        selected_issue_id=decision_fixture.selected_issue_id,
        selected_routing=decision_fixture.selected_routing,
        disposition=decision_fixture.disposition,
        reason="no-routed-work",
    )
    artifact = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=no_work,
    )
    parsed = bridge.parse_dispatch_result_document(artifact)
    assert parsed.disposition == "NO_WORK"
    assert qualify_idle_handoff(no_work)

    envelope = IdleDispatchEnvelope(
        repository="owner/repo",
        default_branch="main",
        request_comment_id=parsed.request_comment_id,
        dispatch_run_id=202,
        dispatch_artifact_id=303,
        dispatch_artifact_sha256="a" * 64,
        default_branch_revision=parsed.default_branch_revision,
    )
    candidate = IdleCandidate(
        kind="new",
        source_kind="canonical-requirement",
        source_ref="openspec/spec.md#idle",
        source_revision=REVISION,
        evidence="bounded production-shaped finding",
        title="Explore the bounded finding",
        body="Change: unset\n\nEvidence: bounded production-shaped finding",
        labels=("action:explore-change",),
    )
    request = make_idle_admission_request(envelope, candidate)
    body = render_idle_admission_request(request)
    event = {
        "action": "created",
        "issue": {
            "number": 77,
            "title": "[Agent Runtime] 2026-09-29",
            "state": "open",
            "labels": [],
        },
        "comment": {
            "id": 404,
            "body": body,
            "user": {"login": "owner"},
            "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
        },
    }
    assert parse_idle_admission_event(event, repository="owner/repo") == request

    for disposition in ("AUTHORIZE", "FAIL_CLOSED"):
        decision = _decision(cast(Literal["AUTHORIZE", "FAIL_CLOSED"], disposition))
        assert not qualify_idle_handoff(decision)


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


def _preactivation_admission() -> list[dict[str, object]]:
    """Authoritative current-route admission for first pre-activation tests."""

    return [
        {
            "id": 42,
            "event": "labeled",
            "created_at": "2026-09-18T00:00:00Z",
            "label": {"name": "action:explore-change"},
        }
    ]


def _formal_frontier_comment(
    comment_id: int,
    *,
    action: str,
    role: str,
    result: str,
    successor: str,
    request_id: int,
    change: str,
    issue_number: int = 138,
    revision: str = REVISION,
) -> dict[str, object]:
    body = "\n".join(
        (
            "ACTION_RESULT",
            f"Workflow: #{issue_number}",
            f"Change: {change}",
            f"Action: {action}",
            f"Role: {role}",
            f"Result: {result.upper().replace('-', '_')}",
            f"Revision: {revision}",
            f"Default-Branch-Revision: {revision}",
            "Application-Correlation: "
            f"application:{request_id}:{issue_number}:{change}:{role}:{action}:{result}:{revision}",
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


@pytest.mark.parametrize("duplicate_count", (1, 2, 3))
def test_duplicate_formal_reemission_of_one_accepted_intent_releases_successor(
    duplicate_count: int,
) -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
    change = f"duplicate-formal-intent-{duplicate_count}"
    request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="finalize-change",
        role="lead",
        result_kind="archive-ready",
        issue_number=138,
        change=change,
    )
    decision = _application_decision_comment(request, comment_id=91)
    formal_comments = [
        _formal_frontier_comment(
            100 + index * 10,
            action="finalize-change",
            role="lead",
            result="archive-ready",
            successor="Reviewer / review-archive",
            request_id=90,
            change=change,
        )
        for index in range(duplicate_count)
    ]
    lifecycle = _frontier_lifecycle([(100, "finalize-change", "review-archive")])
    lifecycle.extend(
        {
            "id": 100 + index * 10,
            "event": "commented",
            "created_at": f"2026-09-18T02:00:{12 + index:02d}Z",
        }
        for index in range(1, duplicate_count)
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, *formal_comments]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return lifecycle
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


def test_accepted_intent_qualifies_formal_result_after_safe_main_advance() -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
    formal_revision = "b" * 40
    advanced_revision = "a" * 40
    change = "formal-evidence-descendant-proof"
    request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="finalize-change",
        role="lead",
        result_kind="archive-ready",
        issue_number=138,
        change=change,
        authorization_revision=REVISION,
    )
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
    body = str(formal["body"])
    formal["body"] = (
        body.replace(f"Revision: {REVISION}", f"Revision: {formal_revision}")
        .replace(
            f"Default-Branch-Revision: {REVISION}",
            f"Default-Branch-Revision: {formal_revision}",
        )
        .replace(
            f":{REVISION}\nRepository-derived successor:",
            f":{formal_revision}\nRepository-derived successor:",
        )
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "finalize-change", "review-archive")])
        if path in {
            f"compare/{REVISION}...{advanced_revision}",
            f"compare/{formal_revision}...{advanced_revision}",
        }:
            base_sha = path.removeprefix("compare/").split("...")[0]
            return {"status": "ahead", "base_commit": {"sha": base_sha}}
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


def test_accepted_formal_result_waits_for_consequence_postconditions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
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
        "consequence_postconditions_complete",
        lambda *_args, **_kwargs: False,
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
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
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

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-successor-pending"
    assert completion.request_comment_id == 90
    assert completion.job_id is None


def test_completed_formal_result_at_safe_ancestor_is_not_resumed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
    formal_revision = "b" * 40
    advanced_revision = "a" * 40
    change = "formal-result-safe-ancestor"
    request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="finalize-change",
        role="lead",
        result_kind="archive-ready",
        issue_number=138,
        change=change,
        authorization_revision=REVISION,
    )
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
    body = str(formal["body"])
    formal["body"] = (
        body.replace(f"Revision: {REVISION}", f"Revision: {formal_revision}")
        .replace(
            f"Default-Branch-Revision: {REVISION}",
            f"Default-Branch-Revision: {formal_revision}",
        )
        .replace(
            f":{REVISION}\nRepository-derived successor:",
            f":{formal_revision}\nRepository-derived successor:",
        )
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }
    observed_revisions: list[str] = []
    observed_accepted_intent: list[bool] = []

    def fake_postconditions(*_args: object, **kwargs: object) -> bool:
        revision = cast(str, kwargs["current_revision"])
        observed_revisions.append(revision)
        observed_accepted_intent.append(cast(bool, kwargs["accepted_intent"]))
        return revision == formal_revision

    monkeypatch.setattr(bridge, "consequence_postconditions_complete", fake_postconditions)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "finalize-change", "review-archive")])
        if path in {
            f"compare/{REVISION}...{advanced_revision}",
            f"compare/{formal_revision}...{advanced_revision}",
        }:
            base_sha = path.removeprefix("compare/").split("...")[0]
            return {"status": "ahead", "base_commit": {"sha": base_sha}}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=advanced_revision,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion(
        "NONE",
        "application-completion-none",
    )
    assert observed_revisions == [advanced_revision]
    assert observed_accepted_intent == [True]


def test_predecessor_is_not_resumed_after_merged_successor_consumes_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(234, "reviewer", "review-archive")
    worker = bridge.parse_worker_result(
        json.dumps(
            {
                "issue_number": 234,
                "role": "reviewer",
                "action": "review-archive",
                "change": "archive-change",
                "result_kind": "pass",
                "evidence_ref": "pr#313@head",
                "result_content": "review pass",
                "requested_effects": [],
            }
        ),
        source,
        authorized_change="archive-change",
    )

    class Observation:
        routing = ("executor", "merge-archive-pr")

    monkeypatch.setattr(bridge, "normalize_github_issue", lambda _issue: Observation())
    monkeypatch.setattr(
        bridge,
        "merged_pr_readiness_complete",
        lambda **kwargs: kwargs["action"] == "merge-archive-pr",
    )

    assert bridge._successor_consequence_supersedes(
        repository="owner/repo",
        token=str(REVISION),
        source=source,
        worker=worker,
        current_issue={},
        change="archive-change",
        current_revision=REVISION,
    )


@pytest.mark.parametrize(
    ("predecessor_disposition", "disposition"),
    [
        ("ACCEPTED", "ACCEPTED"),
        ("ACCEPTED", "REJECTED"),
        ("REJECTED", "REJECTED"),
        (None, "REJECTED"),
    ],
)
def test_completed_predecessor_acceptance_does_not_compete_with_new_frontier(
    disposition: str,
    predecessor_disposition: str | None,
) -> None:
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
    predecessor_decision = _application_decision_comment(
        predecessor_request, comment_id=71, disposition=predecessor_disposition or "ACCEPTED"
    )
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
    current_decision = _application_decision_comment(
        current_request, comment_id=91, disposition=disposition
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:implement-change"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [predecessor_request, current_request]
        if path.startswith("issues/138/comments?"):
            return [
                *([] if predecessor_disposition is None else [predecessor_decision]),
                predecessor_frontier,
                current_decision,
            ]
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
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
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

    if predecessor_disposition != "ACCEPTED":
        # A missing or explicitly rejected owner cannot prove a consequence.
        assert completion.state == "INVALID"
        assert completion.reason == "application-completion-consequence-without-acceptance"
        return
    assert completion.state == ("INVALID" if disposition == "ACCEPTED" else "REJECTED")
    assert completion.reason == (
        "application-completion-recovery-evidence-missing"
        if disposition == "ACCEPTED"
        else "application-completion-rejected"
    )
    assert completion.request_comment_id == 90
    assert completion.job_id is None


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
            return _preactivation_admission()
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
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": runs}
        if path.startswith("actions/runs/") and path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
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
            return _preactivation_admission()
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
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
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

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-recovery-evidence-missing"
    assert completion.request_comment_id == 654
    assert completion.job_id is None


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
            return _preactivation_admission()
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
            return _preactivation_admission()
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
            return _preactivation_admission()
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


def test_historical_raw_request_is_source_filtered_before_frontier_read() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    unrelated = {
        "id": 652,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                "Workflow: #234",
                "Action: resolve-question",
                "Worker-Result: legacy raw payload",
            )
        ),
        "created_at": "2026-09-17T12:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

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

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_malformed_legacy_encoded_source_is_filtered_before_frontier_read() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")

    def legacy_comment(comment_id: int, raw_worker_result: str) -> dict[str, object]:
        encoded = base64.b64encode(raw_worker_result.encode("utf-8")).decode("ascii")
        return {
            "id": comment_id,
            "body": "\n".join(
                (
                    "EFFECT_REQUEST",
                    "Dispatch-Request-Comment-ID: 100",
                    "Dispatch-Decision-Comment-ID: 200",
                    f"Worker-Result-B64: {encoded}",
                )
            ),
            "created_at": "2026-09-17T12:00:00Z",
            "user": {"login": "owner"},
            "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
        }

    malformed_json = legacy_comment(
        657,
        '{"issue_number": 999, "role": "executor", "action": "merge-pr", '
        '"result_content": "unterminated',
    )
    obsolete_identity = legacy_comment(
        658,
        json.dumps(
            {
                "issue_nuber": 998,
                "role": "executor",
                "action": "merge-pr",
                "result_content": "obsolete action vocabulary",
                "requested_effects": [],
            }
        ),
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [malformed_json, obsolete_identity]
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

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_truncated_legacy_encoded_source_is_filtered_before_frontier_read() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    raw_worker_result = json.dumps(
        {
            "issue_number": 999,
            "role": "lead",
            "action": "explore-change",
            "result_content": "historical payload " + ("x" * 7000),
            "requested_effects": [],
        },
        separators=(",", ":"),
    )
    encoded = base64.b64encode(raw_worker_result.encode("utf-8")).decode("ascii")
    truncated = encoded[:160] + "..."
    unrelated = {
        "id": 659,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                "Dispatch-Request-Comment-ID: 100",
                "Dispatch-Decision-Comment-ID: 200",
                f"Worker-Result-B64: {truncated}",
            )
        ),
        "created_at": "2026-09-17T12:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

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

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_preactivation_ingress_before_routing_admission_is_historical() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    historical = _effect_request_comment(
        comment_id=653,
        created_at="2026-09-17T23:59:59Z",
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [historical]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_unbound_terminal_transport_is_inert_history() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    unbound = {
        "id": 654,
        "body": "EFFECT_REQUEST\nlegacy malformed transport",
        "created_at": "2026-09-18T01:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [unbound]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9654,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 1,
                    }
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/9654/jobs":
            return {
                "jobs": [
                    {
                        "id": 9754,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
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

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_unbound_live_transport_blocks_without_source_ownership() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    unbound = {
        "id": 655,
        "body": "EFFECT_REQUEST\nlegacy malformed transport",
        "created_at": "2026-09-18T01:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [unbound]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9655,
                        "display_title": "Scheduled Agent Application 655",
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

    assert completion == bridge.ApplicationCompletion(
        "INVALID",
        "application-completion-unbound-transport-unresolved",
    )


def test_raw_current_source_request_is_classified_after_source_binding() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = {
        "id": 656,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                "Workflow: #138",
                "Action: explore-change",
                "Worker-Result: legacy raw payload",
            )
        ),
        "created_at": "2026-09-18T01:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9656,
                        "display_title": "Scheduled Agent Application 656",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 1,
                    }
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/9656/jobs":
            return {
                "jobs": [
                    {
                        "id": 9756,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
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

    assert completion == bridge.ApplicationCompletion(
        "REJECTED",
        "application-completion-terminal-no-accept",
        request_comment_id=656,
    )


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
            return _preactivation_admission()
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
            return _preactivation_admission()
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
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
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
            return _preactivation_admission()
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
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
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

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-recovery-evidence-missing"
    assert completion.request_comment_id == 654
    assert completion.job_id is None


@pytest.mark.parametrize(
    (
        "current_action",
        "application_run_count",
        "accepted_decision_count",
        "trusted_accepted_decision",
        "expected",
    ),
    (
        (
            "propose-change",
            1,
            1,
            True,
            ("INVALID", "application-completion-recovery-evidence-missing"),
        ),
        (
            "propose-change",
            2,
            1,
            True,
            ("INVALID", "application-completion-run-identity-ambiguous"),
        ),
        (
            "propose-change",
            1,
            2,
            True,
            ("AMBIGUOUS", "application-completion-invalid-frontier-accepted-intents-ambiguous"),
        ),
        (
            "review-openspec",
            1,
            1,
            True,
            ("INVALID", "application-completion-current-frontier-invalid"),
        ),
        (
            "propose-change",
            1,
            1,
            False,
            ("INVALID", "application-completion-current-frontier-invalid"),
        ),
    ),
)
def test_current_accepted_application_stops_replaying_after_repeated_failed_attempt(
    current_action: str,
    application_run_count: int,
    accepted_decision_count: int,
    trusted_accepted_decision: bool,
    expected: tuple[str, str],
) -> None:
    """Stop replay after the exact production prefix has already been retried."""

    current_revision = "e617a05ada51af9ff8f20697bbf07c4bfc8ec19e"
    authorization_revision = "2e00e236f24ba41302c9ba18c685acdf4cebe4ed"
    source = bridge.WorkerRequest(322, "lead", "propose-change")

    def request(comment_id: int, action: str, result_kind: str) -> dict[str, object]:
        item = _effect_request_comment(
            comment_id=comment_id,
            created_at="2026-09-22T16:51:57Z",
            issue_number=322,
            action=action,
            role="lead",
            result_kind=result_kind,
            authorization_revision=authorization_revision,
        )
        body = cast(str, item["body"])
        lines = body.splitlines()
        raw = base64.b64decode(lines[2].removeprefix("Worker-Result-B64: ")).decode("utf-8")
        worker = json.loads(raw)
        worker["_semantic_intent_version"] = 2
        encoded = base64.b64encode(
            json.dumps(worker, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        item["body"] = "\n".join((lines[0], lines[1], f"Worker-Result-B64: {encoded}"))
        return item

    explore_request = request(5780481954, "explore-change", "proposal-ready")
    explore_decision = _application_decision_comment(
        explore_request,
        comment_id=5780489187,
    )
    explore_decision["created_at"] = "2026-09-22T16:52:28Z"
    explore_result = _formal_frontier_comment(
        5780489851,
        action="explore-change",
        role="lead",
        result="proposal-ready",
        successor="Lead / propose-change",
        request_id=5780481954,
        change="unset",
        issue_number=322,
        revision=current_revision,
    )
    explore_result["created_at"] = "2026-09-22T16:52:31Z"

    accepted_request = request(5781255019, "propose-change", "ready-for-openspec-review")
    accepted_decision = _application_decision_comment(
        accepted_request,
        comment_id=5781260361,
    )
    accepted_decision["created_at"] = "2026-09-22T17:48:32Z"
    if not trusted_accepted_decision:
        accepted_decision["user"] = {"login": "attacker"}
        accepted_decision.pop("performed_via_github_app", None)
    # This is the observed current GitHub ACTION_RESULT: its application
    # correlation is absent, so it cannot qualify the accepted intent.
    uncorrelated_result = {
        "id": 5781309198,
        "created_at": "2026-09-22T17:52:19Z",
        "body": "\n".join(
            (
                "ACTION_RESULT",
                "Workflow: #322",
                "Change: unset",
                "Role: lead",
                "Action: propose-change",
                "Result: READY_FOR_OPENSPEC_REVIEW",
                f"Revision: {current_revision}",
                f"Default-Branch-Revision: {current_revision}",
                "Evidence: ACTION_RESULT Workflow: #322 Change: unset",
            )
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    issue = {
        "number": 322,
        "title": "Explore restoring NO_WORK idle discovery after Action-only dispatch",
        "state": "open",
        "created_at": "2026-09-22T15:39:54Z",
        "closed_at": None,
        "labels": [{"name": f"action:{current_action}"}],
        "body": "Change: unset",
    }
    lifecycle = [
        {
            "id": 31612089246,
            "event": "labeled",
            "created_at": "2026-09-22T15:39:56Z",
            "label": {"name": "action:explore-change"},
        },
        {"id": 5780489187, "event": "commented", "created_at": "2026-09-22T16:52:28Z"},
        {"id": 5780489851, "event": "commented", "created_at": "2026-09-22T16:52:31Z"},
        {
            "id": 31616529231,
            "event": "unlabeled",
            "created_at": "2026-09-22T16:52:34Z",
            "label": {"name": "action:explore-change"},
        },
        {
            "id": 31616529287,
            "event": "labeled",
            "created_at": "2026-09-22T16:52:34Z",
            "label": {"name": "action:propose-change"},
        },
        {"id": 5781260361, "event": "commented", "created_at": "2026-09-22T17:48:32Z"},
        {"id": 5781309198, "event": "commented", "created_at": "2026-09-22T17:52:19Z"},
        {
            "id": 31620014721,
            "event": "unlabeled",
            "created_at": "2026-09-22T17:52:21Z",
            "label": {"name": "action:propose-change"},
        },
        {
            "id": 31620014750,
            "event": "labeled",
            "created_at": "2026-09-22T17:52:21Z",
            "label": {"name": "action:review-openspec"},
        },
        {
            "id": 31647225754,
            "event": "unlabeled",
            "created_at": "2026-09-23T03:05:36Z",
            "label": {"name": "action:review-openspec"},
        },
        {
            "id": 31647225775,
            "event": "labeled",
            "created_at": "2026-09-23T03:05:36Z",
            "label": {"name": "action:propose-change"},
        },
    ]

    issue_comment_list = [explore_decision, explore_result, accepted_decision, uncorrelated_result]
    if accepted_decision_count == 2:
        issue_comment_list.append(
            {
                **accepted_decision,
                "id": 5781260362,
                "created_at": "2026-09-22T17:48:33Z",
            }
        )
    application_run_reads = 0

    def fake_read(_repository: str, _token: str, path: str) -> object:
        nonlocal application_run_reads
        if path.startswith("issues/comments?"):
            return [explore_request, accepted_request]
        if path.startswith("issues/322/comments?"):
            return issue_comment_list
        if path == "issues/322":
            return issue
        if path.startswith("issues/322/timeline?"):
            return lifecycle
        if path.startswith("compare/"):
            base = path.removeprefix("compare/").split("...", 1)[0]
            return {"status": "ahead", "base_commit": {"sha": base}}
        if path.startswith("actions/workflows/"):
            application_run_reads += 1
            return {
                "workflow_runs": [
                    {
                        "id": 35762997171 + index,
                        "display_title": "Scheduled Agent Application 5781255019",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 6,
                    }
                    for index in range(application_run_count)
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/35762997171/jobs":
            return {"jobs": [{"id": 107028234822, "name": "apply"}]}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=current_revision,
        read=fake_read,
        now=datetime(2026, 9, 23, 4, 0, tzinfo=UTC),
    )

    assert (completion.state, completion.reason) == expected
    if expected[0] == "RESUMABLE":
        assert completion.request_comment_id == 5781255019
        assert completion.job_id == 107028234822
    elif expected[1] in {
        "application-completion-run-identity-ambiguous",
        "application-completion-rerun-limit",
        "application-completion-continuation-required",
        "application-completion-recovery-evidence-missing",
    }:
        assert application_run_reads > 0
    else:
        assert application_run_reads == 0


def test_live_322_accepted_request_does_not_resume_completed_failed_application_job() -> None:
    """A repeated #322 application attempt must stop the scheduled retry loop."""

    fixture_path = Path(__file__).parent / "fixtures" / "issue322-application-recovery.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    revision = cast(str, fixture["source_revision"])
    request = cast(dict[str, object], fixture["request_comment"])
    issue = cast(dict[str, object], fixture["issue"])
    issue_comments = cast(list[dict[str, object]], fixture["issue_comments"])
    lifecycle = cast(list[dict[str, object]], fixture["timeline"])
    comparisons = cast(dict[str, dict[str, object]], fixture["comparisons"])
    run = cast(dict[str, object], fixture["application_run"])
    job = cast(dict[str, object], fixture["application_job"])
    request_id = cast(int, request["id"])
    run_id = cast(int, run["id"])
    job_id = cast(int, job["id"])
    source = bridge.WorkerRequest(322, "lead", "resolve-question")
    observed: list[str] = []

    def fake_read(_repository: str, _token: str, path: str) -> object:
        observed.append(path)
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/322/comments?"):
            return issue_comments
        if path == "issues/322":
            return issue
        if path.startswith("issues/322/timeline?"):
            return lifecycle
        if path.startswith("compare/"):
            base = path.removeprefix("compare/").split("...", 1)[0]
            if base == revision:
                return {
                    "status": "identical",
                    "base_commit": {"sha": revision},
                    "ahead_by": 0,
                    "behind_by": 0,
                    "files": [],
                }
            return comparisons[base]
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": [run]}
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == f"actions/runs/{run_id}/jobs":
            return {"jobs": [job]}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "royhsu-work/investment-strategy",
        "fixture",
        source=source,
        current_revision=revision,
        read=fake_read,
        now=datetime(2026, 9, 24, 13, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion(
        "INVALID",
        "application-completion-recovery-evidence-missing",
        request_comment_id=request_id,
    )
    assert request_id == 5810765007
    assert run_id == 35976411803
    assert job_id == 107664011251
    assert run["run_attempt"] == 7
    assert any(path.startswith("actions/workflows/") for path in observed)
    assert f"actions/runs/{run_id}/jobs" in observed


def test_new_evidence_continues_past_the_former_attempt_threshold() -> None:
    source = bridge.WorkerRequest(322, "lead", "resolve-question")
    request = _effect_request_comment(
        comment_id=5810765007,
        created_at="2026-09-23T03:00:00Z",
        issue_number=322,
        action=source.action,
        role=source.role,
        result_kind="ready-for-openspec-review",
    )
    decision = _application_decision_comment(request, comment_id=5810765008)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/322/comments?"):
            return [decision]
        raise AssertionError(path)

    accepted_sha256 = hashlib.sha256(cast(str, decision["body"]).encode("utf-8")).hexdigest()
    predecessor = bridge.ApplicationRecoveryArtifact(
        run_id=7001,
        run_attempt=1,
        job_id=7002,
        artifact_id=7003,
        artifact_digest="sha256:" + "1" * 64,
        request_comment_id=5810765007,
        accepted_decision_sha256=accepted_sha256,
        failure_evidence_sha256="2" * 64,
        recovery_episode_sha256="3" * 64,
        recovery_attempt=4,
        continuation_eligible=True,
        document={"prior_failure_evidence_sha256": ["6" * 64, "7" * 64, "8" * 64]},
    )
    body = bridge._application_continuation_body(
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=5810765007,
        predecessor_evidence=predecessor,
        read=fake_read,
    )

    assert body is not None
    parsed = bridge.parse_application_continuation_request(body)
    assert parsed is not None
    assert parsed.issue_number == source.issue_number
    assert parsed.original_request_comment_id == 5810765007
    assert (
        parsed.accepted_decision_sha256
        == hashlib.sha256(cast(str, decision["body"]).encode("utf-8")).hexdigest()
    )

    repeated = bridge.ApplicationRecoveryArtifact(
        run_id=7002,
        run_attempt=1,
        job_id=7003,
        artifact_id=7004,
        artifact_digest="sha256:" + "4" * 64,
        request_comment_id=5810765007,
        accepted_decision_sha256=accepted_sha256,
        failure_evidence_sha256="2" * 64,
        recovery_episode_sha256="3" * 64,
        recovery_attempt=5,
        continuation_eligible=True,
        document={"prior_failure_evidence_sha256": ["6" * 64, "7" * 64, "8" * 64, "2" * 64]},
    )
    assert (
        bridge._application_continuation_body(
            repository="owner/repo",
            token=REVISION,
            source=source,
            request_comment_id=5810765007,
            predecessor_evidence=repeated,
            read=fake_read,
        )
        is None
    )


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
            return _preactivation_admission()
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
            return _preactivation_admission()
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


def test_completed_formal_result_uses_fresh_revision_for_postconditions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
    formal_evidence_revision = "b" * 40
    application_observation_revision = "c" * 40
    advanced_revision = "a" * 40
    change = "formal-result-observation-revision"
    request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="finalize-change",
        role="lead",
        result_kind="archive-ready",
        issue_number=138,
        change=change,
        authorization_revision=REVISION,
    )
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
    body = str(formal["body"])
    formal["body"] = (
        body.replace(f"Revision: {REVISION}", f"Revision: {formal_evidence_revision}")
        .replace(
            f"Default-Branch-Revision: {REVISION}",
            f"Default-Branch-Revision: {formal_evidence_revision}",
        )
        .replace(
            f":{REVISION}\nRepository-derived successor:",
            f":{application_observation_revision}\nRepository-derived successor:",
        )
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }
    observed_revisions: list[str] = []

    def fake_postconditions(*_args: object, **kwargs: object) -> bool:
        revision = cast(str, kwargs["current_revision"])
        observed_revisions.append(revision)
        return revision == application_observation_revision

    monkeypatch.setattr(bridge, "consequence_postconditions_complete", fake_postconditions)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "finalize-change", "review-archive")])
        if path in {
            f"compare/{REVISION}...{advanced_revision}",
            f"compare/{formal_evidence_revision}...{advanced_revision}",
            f"compare/{application_observation_revision}...{advanced_revision}",
        }:
            base_sha = path.removeprefix("compare/").split("...")[0]
            return {"status": "ahead", "base_commit": {"sha": base_sha}}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=advanced_revision,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion(
        "NONE",
        "application-completion-none",
    )
    assert observed_revisions == [advanced_revision]


def _carrier_plan_fixture(authorization_revision: str = REVISION) -> carrier.CarrierPlan:
    return carrier.make_carrier_plan(
        repository="owner/repo",
        issue_number=322,
        change="restore-no-work-idle-discovery",
        action="implement-change",
        authorization_revision=authorization_revision,
        operation="pull-request-head-update",
        target={
            "repository": "owner/repo",
            "pull_request_number": 353,
            "ref": "refs/heads/agent/change",
        },
        expected={"ref_sha": "a" * 40},
        requested={
            "ref": "refs/heads/agent/change",
            "sha": "b" * 40,
            "force": False,
        },
        expected_postcondition={
            "ref": "refs/heads/agent/change",
            "ref_sha": "b" * 40,
            "pull_request_number": 353,
            "pull_request_head_sha": "b" * 40,
        },
    )


def _accepted_carrier_record() -> bridge.ApplicationDecisionRecord:
    return bridge.ApplicationDecisionRecord(
        request_comment_id=90,
        request_body_sha256="1" * 64,
        authorization_revision=REVISION,
        issue_number=322,
        role="executor",
        action="implement-change",
        change="restore-no-work-idle-discovery",
        result_kind="more-implementation-required",
        disposition="ACCEPTED",
        worker_result_sha256="2" * 64,
        raw_worker_result="{}",
        reason="application accepted",
    )


def _qualified_recovery_fixture(
    *,
    accepted_decision_sha256: str = "a" * 64,
    run_id: int = 777,
    run_attempt: int = 1,
    job_id: int = 888,
    artifact_id: int = 999,
    request_comment_id: int = 90,
    recovery_attempt: int = 1,
    continuation_eligible: bool = True,
    prior_failures: tuple[str, ...] = (),
) -> bridge.ApplicationRecoveryArtifact:
    return bridge.ApplicationRecoveryArtifact(
        run_id=run_id,
        run_attempt=run_attempt,
        job_id=job_id,
        artifact_id=artifact_id,
        artifact_digest="sha256:" + "3" * 64,
        request_comment_id=request_comment_id,
        accepted_decision_sha256=accepted_decision_sha256,
        failure_evidence_sha256="4" * 64,
        recovery_episode_sha256="5" * 64,
        recovery_attempt=recovery_attempt,
        continuation_eligible=continuation_eligible,
        document={"prior_failure_evidence_sha256": list(prior_failures)},
    )


def _trusted_connector_comment(comment_id: int, body: str) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }


def _carrier_outcome_fixture(
    plan: carrier.CarrierPlan,
    recovery: bridge.ApplicationRecoveryArtifact,
    *,
    carrier_artifact_id: int,
    carrier_artifact_digest: str,
    outcome: Literal["COMPLETE", "REFUSED"] = "COMPLETE",
) -> carrier.CarrierOutcomeReport:
    complete = outcome == "COMPLETE"
    return carrier.CarrierOutcomeReport(
        repository="owner/repo",
        issue_number=322,
        request_comment_id=90,
        accepted_decision_sha256=recovery.accepted_decision_sha256,
        continuation_correlation=bridge.application_continuation_correlation(
            "owner/repo",
            322,
            90,
            recovery.accepted_decision_sha256,
            recovery.run_id,
            recovery.run_attempt,
            recovery.job_id,
            recovery.artifact_id,
            recovery.artifact_digest,
            recovery.failure_evidence_sha256,
            recovery.recovery_episode_sha256,
        ),
        predecessor_run_id=recovery.run_id,
        predecessor_run_attempt=recovery.run_attempt,
        predecessor_job_id=recovery.job_id,
        recovery_artifact_id=recovery.artifact_id,
        recovery_artifact_digest=recovery.artifact_digest,
        failure_evidence_sha256=recovery.failure_evidence_sha256,
        recovery_episode_sha256=recovery.recovery_episode_sha256,
        carrier_artifact_id=carrier_artifact_id,
        carrier_artifact_digest=carrier_artifact_digest,
        plan_id=plan.plan_id,
        operation=plan.operation,
        outcome=outcome,
        mutation_status="COMPLETED" if complete else "NO_WRITE",
        precondition="MATCH",
        observed_precondition_json=json.dumps(
            dict(plan.expected), sort_keys=True, separators=(",", ":")
        ),
        postcondition="COMPLETE" if complete else "INCOMPLETE",
        unfinished_boundary="none" if complete else "carrier-operation",
        failure_code="none" if complete else "connector-refused",
        failure_summary="none" if complete else "connector refused",
    )


def _carrier_dispatch_result_bytes(
    qualified: carrier.QualifiedCarrierPlan,
    *,
    request_comment_id: int = 91,
) -> bytes:
    continuation = bridge.render_application_continuation_request(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=90,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=777,
        predecessor_run_attempt=1,
        predecessor_job_id=888,
        predecessor_artifact_id=997,
        predecessor_artifact_digest="sha256:" + "3" * 64,
        failure_evidence_sha256="4" * 64,
        recovery_episode_sha256="5" * 64,
    )
    payload = {
        "schema": bridge.DISPATCH_RESULT_SCHEMA,
        "request_comment_id": request_comment_id,
        "default_branch_revision": REVISION,
        "disposition": "FAIL_CLOSED",
        "reason": "application-completion-carrier-required",
        "application_continuation": continuation,
        "qualified_carrier": carrier.qualified_carrier_document(qualified),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _carrier_completion_reader(
    *,
    carrier_digest: str,
    dispatch_bytes: bytes | None = None,
) -> bridge.GitHubReader:
    dispatch_digest = (
        None if dispatch_bytes is None else f"sha256:{hashlib.sha256(dispatch_bytes).hexdigest()}"
    )

    def read(_repository: str, _token: str, path: str) -> object:
        if path == f"compare/{REVISION}...{REVISION}":
            return {"status": "identical", "base_commit": {"sha": REVISION}}
        if path.startswith("actions/workflows/scheduled-agent-application.yml/runs?"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 90",
                        "status": "completed",
                        "run_attempt": 1,
                        "head_sha": REVISION,
                    }
                ]
            }
        if path == "actions/runs/777/jobs":
            return {
                "jobs": [
                    {
                        "id": 888,
                        "name": "apply",
                        "steps": [
                            {
                                "name": "Upload exact external carrier plan",
                                "conclusion": "success",
                            }
                        ],
                    }
                ]
            }
        if path == "actions/runs/777/artifacts?per_page=100":
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 999,
                        "name": "carrier-plan.json",
                        "expired": False,
                        "digest": carrier_digest,
                        "workflow_run": {"id": 777, "head_sha": REVISION},
                    }
                ],
            }
        if path.startswith("actions/workflows/scheduled-agent-bridge.yml/runs?"):
            if dispatch_bytes is None:
                return {"workflow_runs": []}
            return {
                "workflow_runs": [
                    {
                        "id": 555,
                        "display_title": "Scheduled Agent Dispatch 91",
                        "status": "completed",
                        "conclusion": "success",
                        "head_sha": REVISION,
                    }
                ]
            }
        if path == "actions/runs/555/artifacts?per_page=100" and dispatch_bytes is not None:
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 556,
                        "name": "dispatch-result.json",
                        "expired": False,
                        "digest": dispatch_digest,
                        "workflow_run": {"id": 555, "head_sha": REVISION},
                    }
                ],
            }
        raise AssertionError(path)

    return read


@pytest.mark.parametrize(
    ("plan_revision", "ancestry_status", "eligible"),
    [
        (REVISION, "ahead", True),
        ("d" * 40, "ahead", True),
        ("d" * 40, "behind", False),
        ("d" * 40, None, False),
    ],
)
def test_completed_application_prefers_saved_qualified_carrier_over_producer_resume(
    monkeypatch: pytest.MonkeyPatch,
    plan_revision: str,
    ancestry_status: str | None,
    eligible: bool,
) -> None:
    plan = _carrier_plan_fixture(plan_revision)
    raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    digest = f"sha256:{hashlib.sha256(raw).hexdigest()}"

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path == f"compare/{REVISION}...{plan_revision}":
            return {"status": ancestry_status, "base_commit": {"sha": REVISION}}
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 90",
                        "status": "completed",
                        "run_attempt": 1,
                        "head_sha": REVISION,
                    }
                ]
            }
        if path == "actions/runs/777/jobs":
            return {
                "jobs": [
                    {
                        "id": 888,
                        "name": "apply",
                        "steps": [
                            {
                                "name": "Upload exact external carrier plan",
                                "conclusion": "success",
                            }
                        ],
                    }
                ]
            }
        if path == "actions/runs/777/artifacts?per_page=100":
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 999,
                        "name": "carrier-plan.json",
                        "expired": False,
                        "digest": digest,
                        "workflow_run": {"id": 777, "head_sha": REVISION},
                    }
                ],
            }
        raise AssertionError(path)

    recovery = _qualified_recovery_fixture()
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )
    monkeypatch.setattr(bridge, "read_github_artifact_bytes", lambda *_args: raw)
    completion = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=fake_read,
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
    )

    if not eligible:
        assert completion.state == "INVALID"
        assert completion.reason == "application-completion-carrier-evidence-invalid"
        assert completion.qualified_carrier is None
        assert completion.job_id is None
        return
    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-carrier-required"
    assert completion.job_id is None
    assert completion.qualified_carrier is not None
    assert completion.qualified_carrier.plan == plan
    assert completion.qualified_carrier.artifact_digest == digest


def test_completed_application_consumes_only_exact_complete_carrier_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _carrier_plan_fixture()
    carrier_raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    carrier_digest = f"sha256:{hashlib.sha256(carrier_raw).hexdigest()}"
    recovery = _qualified_recovery_fixture(artifact_id=997)
    report = _carrier_outcome_fixture(
        plan,
        recovery,
        carrier_artifact_id=999,
        carrier_artifact_digest=carrier_digest,
    )
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )
    previous_dispatch = _carrier_dispatch_result_bytes(qualified)
    comments = (
        _trusted_connector_comment(
            91,
            "DISPATCH_REQUEST\nRequested-At: 2026-10-08T05:49:00Z",
        ),
        _trusted_connector_comment(
            92,
            carrier.render_carrier_outcome_report(report),
        ),
    )
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )

    def read_artifact(_repository: str, _token: str, path: str) -> bytes:
        if path == "actions/artifacts/999/zip":
            return carrier_raw
        if path == "actions/artifacts/556/zip":
            return previous_dispatch
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "read_github_artifact_bytes", read_artifact)
    completion = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=_carrier_completion_reader(
            carrier_digest=carrier_digest,
            dispatch_bytes=previous_dispatch,
        ),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recent_comments=comments,
        current_dispatch_request_comment_id=100,
    )

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-continuation-required"
    assert completion.qualified_carrier is None
    assert completion.recovery_artifact == recovery


def test_completed_application_blocks_a_previous_unreported_carrier_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _carrier_plan_fixture()
    carrier_raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    carrier_digest = f"sha256:{hashlib.sha256(carrier_raw).hexdigest()}"
    recovery = _qualified_recovery_fixture(artifact_id=997)
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )
    previous_dispatch = _carrier_dispatch_result_bytes(qualified)
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )

    def read_artifact(_repository: str, _token: str, path: str) -> bytes:
        if path == "actions/artifacts/999/zip":
            return carrier_raw
        if path == "actions/artifacts/556/zip":
            return previous_dispatch
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "read_github_artifact_bytes", read_artifact)
    completion = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=_carrier_completion_reader(
            carrier_digest=carrier_digest,
            dispatch_bytes=previous_dispatch,
        ),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recent_comments=(
            _trusted_connector_comment(
                91,
                "DISPATCH_REQUEST\nRequested-At: 2026-10-08T05:49:00Z",
            ),
        ),
        current_dispatch_request_comment_id=100,
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-carrier-outcome-missing"
    assert completion.qualified_carrier is None


def test_completed_application_blocks_refused_carrier_outcome_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _carrier_plan_fixture()
    carrier_raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    carrier_digest = f"sha256:{hashlib.sha256(carrier_raw).hexdigest()}"
    recovery = _qualified_recovery_fixture(artifact_id=997)
    report = _carrier_outcome_fixture(
        plan,
        recovery,
        carrier_artifact_id=999,
        carrier_artifact_digest=carrier_digest,
        outcome="REFUSED",
    )
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )
    monkeypatch.setattr(
        bridge,
        "read_github_artifact_bytes",
        lambda *_args: carrier_raw,
    )
    completion = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=_carrier_completion_reader(carrier_digest=carrier_digest),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recent_comments=(
            _trusted_connector_comment(
                92,
                carrier.render_carrier_outcome_report(report),
            ),
        ),
        current_dispatch_request_comment_id=100,
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-carrier-outcome-incomplete"
    assert completion.qualified_carrier is None


def test_completed_application_distinguishes_absent_from_incomplete_carrier_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _accepted_carrier_record()
    recovery = _qualified_recovery_fixture(
        recovery_attempt=4,
        prior_failures=("6" * 64, "7" * 64, "8" * 64),
    )
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )

    def reader(total_count: int) -> bridge.GitHubReader:
        def fake_read(_repository: str, _token: str, path: str) -> object:
            if path.startswith("actions/workflows/"):
                return {
                    "workflow_runs": [
                        {
                            "id": 777,
                            "display_title": "Scheduled Agent Application 90",
                            "status": "completed",
                            "run_attempt": 50,
                            "head_sha": REVISION,
                        }
                    ]
                }
            if path == "actions/runs/777/jobs":
                return {"jobs": [{"id": 888, "name": "apply"}]}
            if path == "actions/runs/777/artifacts?per_page=100":
                return {"total_count": total_count, "artifacts": []}
            raise AssertionError(path)

        return fake_read

    absent = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=reader(0),
        record=record,
        accepted_decision_sha256="a" * 64,
    )
    incomplete = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=reader(1),
        record=record,
        accepted_decision_sha256="a" * 64,
    )

    assert (absent.state, absent.reason, absent.job_id) == (
        "RESUMABLE",
        "application-completion-continuation-required",
        None,
    )
    assert (incomplete.state, incomplete.reason) == (
        "INVALID",
        "application-completion-carrier-evidence-invalid",
    )


def test_qualified_carrier_consumer_executes_connector_and_skips_complete() -> None:
    plan = _carrier_plan_fixture()
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest="sha256:" + "3" * 64,
        plan=plan,
    )
    remote = {"sha": "a" * 40}
    calls: list[str] = []

    def qualify(_qualified: carrier.QualifiedCarrierPlan) -> carrier.CarrierQualification:
        return "COMPLETE" if remote["sha"] == "b" * 40 else "ELIGIBLE"

    def connector(exact_plan: carrier.CarrierPlan) -> None:
        calls.append(exact_plan.plan_id)
        remote["sha"] = cast(str, exact_plan.requested["sha"])

    assert (
        carrier.consume_qualified_carrier(qualified, qualify=qualify, connector=connector)
        == "executed-complete"
    )
    assert calls == [plan.plan_id]
    assert (
        carrier.consume_qualified_carrier(qualified, qualify=qualify, connector=connector)
        == "already-complete"
    )
    assert calls == [plan.plan_id]


def test_qualified_carrier_consumer_reconciles_lost_response_without_resend() -> None:
    plan = _carrier_plan_fixture()
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest="sha256:" + "4" * 64,
        plan=plan,
    )
    remote = {"sha": "a" * 40}
    calls = 0

    def qualify(_qualified: carrier.QualifiedCarrierPlan) -> carrier.CarrierQualification:
        return "COMPLETE" if remote["sha"] == "b" * 40 else "ELIGIBLE"

    def connector(exact_plan: carrier.CarrierPlan) -> None:
        nonlocal calls
        calls += 1
        remote["sha"] = cast(str, exact_plan.requested["sha"])
        raise TimeoutError("response lost after server write")

    assert (
        carrier.consume_qualified_carrier(qualified, qualify=qualify, connector=connector)
        == "reconciled-complete"
    )
    assert calls == 1


def test_carrier_outcome_report_round_trips_exact_lineage() -> None:
    report = carrier.CarrierOutcomeReport(
        repository="owner/repo",
        issue_number=322,
        request_comment_id=90,
        accepted_decision_sha256="a" * 64,
        continuation_correlation="b" * 64,
        predecessor_run_id=777,
        predecessor_run_attempt=1,
        predecessor_job_id=888,
        recovery_artifact_id=997,
        recovery_artifact_digest="sha256:" + "3" * 64,
        failure_evidence_sha256="4" * 64,
        recovery_episode_sha256="5" * 64,
        carrier_artifact_id=999,
        carrier_artifact_digest="sha256:" + "6" * 64,
        plan_id=_carrier_plan_fixture().plan_id,
        operation="pull-request-head-update",
        outcome="COMPLETE",
        mutation_status="COMPLETED",
        precondition="MATCH",
        observed_precondition_json=json.dumps(
            dict(_carrier_plan_fixture().expected), sort_keys=True, separators=(",", ":")
        ),
        postcondition="COMPLETE",
        unfinished_boundary="none",
        failure_code="none",
        failure_summary="none",
    )

    body = carrier.render_carrier_outcome_report(report)

    assert body.splitlines()[0] == "APPLICATION_CARRIER_OUTCOME"
    assert carrier.parse_carrier_outcome_report(body) == report


def test_carrier_outcome_report_rejects_malformed_evidence_and_parses_shape_only() -> None:
    report = carrier.CarrierOutcomeReport(
        repository="owner/repo",
        issue_number=322,
        request_comment_id=90,
        accepted_decision_sha256="a" * 64,
        continuation_correlation="b" * 64,
        predecessor_run_id=777,
        predecessor_run_attempt=1,
        predecessor_job_id=888,
        recovery_artifact_id=997,
        recovery_artifact_digest="sha256:" + "3" * 64,
        failure_evidence_sha256="4" * 64,
        recovery_episode_sha256="5" * 64,
        carrier_artifact_id=999,
        carrier_artifact_digest="sha256:" + "6" * 64,
        plan_id=_carrier_plan_fixture().plan_id,
        operation="pull-request-head-update",
        outcome="COMPLETE",
        mutation_status="COMPLETED",
        precondition="MATCH",
        observed_precondition_json=json.dumps(
            dict(_carrier_plan_fixture().expected), sort_keys=True, separators=(",", ":")
        ),
        postcondition="COMPLETE",
        unfinished_boundary="none",
        failure_code="none",
        failure_summary="none",
    )
    body = carrier.render_carrier_outcome_report(report)

    assert carrier.parse_carrier_outcome_report(body + "\n") is None
    assert (
        carrier.parse_carrier_outcome_report(
            body.replace("Postcondition: COMPLETE", "Postcondition: UNKNOWN")
        )
        is None
    )
    other_repository_body = body.replace("Repository: owner/repo", "Repository: other/repo")
    assert carrier.parse_carrier_outcome_report(other_repository_body) is not None


def test_carrier_documents_reject_tampering_and_dispatch_round_trips_handoff() -> None:
    plan = _carrier_plan_fixture()
    document = carrier.carrier_plan_document(plan)
    tampered = dict(document)
    tampered_requested = dict(cast(dict[str, object], document["requested"]))
    tampered_requested["sha"] = "c" * 40
    tampered["requested"] = tampered_requested
    with pytest.raises(ValueError, match="content address"):
        carrier.parse_carrier_plan_document(tampered)

    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest="sha256:" + "5" * 64,
        plan=plan,
    )
    continuation = bridge.render_application_continuation_request(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=90,
        accepted_decision_sha256="6" * 64,
        predecessor_run_id=7001,
        predecessor_run_attempt=1,
        predecessor_job_id=7002,
        predecessor_artifact_id=7003,
        predecessor_artifact_digest="sha256:" + "1" * 64,
        failure_evidence_sha256="2" * 64,
        recovery_episode_sha256="3" * 64,
    )
    failed = _decision("FAIL_CLOSED")
    failed = DispatchDecision(
        completeness=failed.completeness,
        observation_provenance=failed.observation_provenance,
        formal_issue_ids=failed.formal_issue_ids,
        preactivation_candidate_ids=failed.preactivation_candidate_ids,
        selected_issue_id=None,
        selected_routing=None,
        disposition="FAIL_CLOSED",
        reason="application-completion-carrier-required",
    )
    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=failed,
        application_continuation=continuation,
        qualified_carrier=qualified,
    )
    parsed = bridge.parse_dispatch_result_document(rendered)

    assert parsed.application_continuation == continuation
    assert parsed.qualified_carrier == qualified


def test_continuation_chain_selects_one_leaf_and_preserves_branches() -> None:
    latest_runs = (
        {
            "id": 700,
            "display_title": "Scheduled Agent Application 90",
            "run_attempt": 50,
        },
        {
            "id": 701,
            "display_title": "Scheduled Agent Application 101",
            "run_attempt": 1,
        },
        {
            "id": 702,
            "display_title": "Scheduled Agent Application 102",
            "run_attempt": 1,
        },
    )
    linear_leaf = bridge._continuation_leaf_comment_ids(
        request_comment_id=90,
        continuation_predecessors={101: (700, 1), 102: (701, 1)},
        workflow_runs=latest_runs,
    )
    assert linear_leaf == (102,)

    branched_leaves = bridge._continuation_leaf_comment_ids(
        request_comment_id=90,
        continuation_predecessors={101: (700, 50), 102: (700, 50)},
        workflow_runs=latest_runs,
    )
    assert branched_leaves == (101, 102)

    incomplete = bridge._continuation_leaf_comment_ids(
        request_comment_id=90,
        continuation_predecessors={101: (700, 1)},
        workflow_runs=(latest_runs[0],),
    )
    assert incomplete is None


def test_application_continuation_binds_exact_failure_transition() -> None:
    render = bridge.render_application_continuation_request
    first = render(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=987,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=12345,
        predecessor_run_attempt=2,
        predecessor_job_id=23456,
        predecessor_artifact_id=34567,
        predecessor_artifact_digest="sha256:" + "b" * 64,
        failure_evidence_sha256="c" * 64,
        recovery_episode_sha256="d" * 64,
    )
    duplicate = render(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=987,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=12345,
        predecessor_run_attempt=2,
        predecessor_job_id=23456,
        predecessor_artifact_id=34567,
        predecessor_artifact_digest="sha256:" + "b" * 64,
        failure_evidence_sha256="c" * 64,
        recovery_episode_sha256="d" * 64,
    )
    parsed = bridge.parse_application_continuation_request(first)

    assert first == duplicate
    assert parsed is not None
    assert getattr(parsed, "predecessor_run_id", None) == 12345
    assert getattr(parsed, "predecessor_run_attempt", None) == 2
    assert getattr(parsed, "predecessor_job_id", None) == 23456
    assert getattr(parsed, "predecessor_artifact_id", None) == 34567
    assert getattr(parsed, "predecessor_artifact_digest", None) == "sha256:" + "b" * 64
    assert getattr(parsed, "failure_evidence_sha256", None) == "c" * 64
    assert getattr(parsed, "recovery_episode_sha256", None) == "d" * 64

    next_body = render(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=987,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=12346,
        predecessor_run_attempt=1,
        predecessor_job_id=23457,
        predecessor_artifact_id=34568,
        predecessor_artifact_digest="sha256:" + "e" * 64,
        failure_evidence_sha256="f" * 64,
        recovery_episode_sha256="d" * 64,
    )
    next_parsed = bridge.parse_application_continuation_request(next_body)

    assert next_body != first
    assert next_parsed is not None
    assert getattr(next_parsed, "recovery_episode_sha256", None) == getattr(
        parsed, "recovery_episode_sha256", None
    )
    assert getattr(next_parsed, "continuation_correlation", None) != getattr(
        parsed, "continuation_correlation", None
    )


def test_unreported_carrier_handoff_is_found_before_later_noncarrier_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _carrier_plan_fixture()
    carrier_raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    carrier_digest = f"sha256:{hashlib.sha256(carrier_raw).hexdigest()}"
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )
    older_result = _carrier_dispatch_result_bytes(
        qualified,
        request_comment_id=91,
    )
    newer_result = bridge.render_dispatch_result_document(
        request_comment_id=98,
        default_branch_revision=REVISION,
        decision=_decision("FAIL_CLOSED"),
    ).encode("utf-8")
    artifacts = {
        5601: older_result,
        5602: newer_result,
    }
    digests = {
        artifact_id: f"sha256:{hashlib.sha256(raw).hexdigest()}"
        for artifact_id, raw in artifacts.items()
    }

    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("actions/workflows/scheduled-agent-bridge.yml/runs?"):
            return {
                "workflow_runs": [
                    {
                        "id": 555,
                        "display_title": bridge.render_dispatch_run_name(91),
                        "status": "completed",
                        "head_sha": REVISION,
                    },
                    {
                        "id": 558,
                        "display_title": bridge.render_dispatch_run_name(98),
                        "status": "completed",
                        "head_sha": REVISION,
                    },
                ]
            }
        if path == "actions/runs/555/artifacts?per_page=100":
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 5601,
                        "name": "dispatch-result.json",
                        "expired": False,
                        "digest": digests[5601],
                        "workflow_run": {"id": 555, "head_sha": REVISION},
                    }
                ],
            }
        if path == "actions/runs/558/artifacts?per_page=100":
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 5602,
                        "name": "dispatch-result.json",
                        "expired": False,
                        "digest": digests[5602],
                        "workflow_run": {"id": 558, "head_sha": REVISION},
                    }
                ],
            }
        raise AssertionError(path)

    monkeypatch.setattr(
        bridge,
        "read_github_artifact_bytes",
        lambda _repository, _token, path: artifacts[int(path.split("/")[2])],
    )
    status = bridge._prior_dispatch_handoff_reason(
        "owner/repo",
        "token",
        recent_comments=(
            _trusted_connector_comment(91, REQUEST_BODY),
            _trusted_connector_comment(98, REQUEST_BODY),
        ),
        owner="owner",
        current_dispatch_request_comment_id=100,
        plan_id=plan.plan_id,
        read=read,
    )

    assert status == "application-completion-carrier-outcome-missing"


def test_prior_dispatch_without_a_visible_run_fails_closed_before_carrier_reissue() -> None:
    status = bridge._prior_dispatch_handoff_reason(
        "owner/repo",
        "token",
        recent_comments=(_trusted_connector_comment(91, REQUEST_BODY),),
        owner="owner",
        current_dispatch_request_comment_id=100,
        plan_id=_carrier_plan_fixture().plan_id,
        read=lambda _repository, _token, path: (
            {"workflow_runs": []}
            if path.startswith("actions/workflows/scheduled-agent-bridge.yml/runs?")
            else (_ for _ in ()).throw(AssertionError(path))
        ),
    )

    assert status == "application-completion-carrier-prior-dispatch-incomplete"



def test_carrier_outcome_consumer_blocks_duplicate_identical_reports() -> None:
    plan = _carrier_plan_fixture()
    recovery = _qualified_recovery_fixture(artifact_id=997)
    carrier_digest = "sha256:" + "6" * 64
    report_body = carrier.render_carrier_outcome_report(
        _carrier_outcome_fixture(
            plan,
            recovery,
            carrier_artifact_id=999,
            carrier_artifact_digest=carrier_digest,
        )
    )
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )

    outcome, reason = bridge._carrier_outcome_status(
        recent_comments=(
            _trusted_connector_comment(92, report_body),
            _trusted_connector_comment(93, report_body),
        ),
        owner="owner",
        repository="owner/repo",
        source=bridge.WorkerRequest(322, "executor", "implement-change"),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recovery_artifact=recovery,
        qualified_carrier=qualified,
    )

    assert outcome == "BLOCKED"
    assert reason == "application-completion-carrier-outcome-ambiguous"


def test_carrier_outcome_consumer_rejects_repository_mismatch() -> None:
    plan = _carrier_plan_fixture()
    recovery = _qualified_recovery_fixture(artifact_id=997)
    carrier_digest = "sha256:" + "6" * 64
    report = replace(
        _carrier_outcome_fixture(
            plan,
            recovery,
            carrier_artifact_id=999,
            carrier_artifact_digest=carrier_digest,
        ),
        repository="other/repo",
    )
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )

    outcome, reason = bridge._carrier_outcome_status(
        recent_comments=(
            _trusted_connector_comment(
                92,
                carrier.render_carrier_outcome_report(report),
            ),
        ),
        owner="owner",
        repository="owner/repo",
        source=bridge.WorkerRequest(322, "executor", "implement-change"),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recovery_artifact=recovery,
        qualified_carrier=qualified,
    )

    assert outcome == "BLOCKED"
    assert reason == "application-completion-carrier-outcome-plan-reused"


def test_carrier_outcome_cannot_claim_matching_precondition_with_other_observation() -> None:
    plan = _carrier_plan_fixture()
    recovery = _qualified_recovery_fixture(artifact_id=997)
    report = _carrier_outcome_fixture(
        plan,
        recovery,
        carrier_artifact_id=999,
        carrier_artifact_digest="sha256:" + "6" * 64,
    )
    mismatched_report = replace(
        report,
        observed_precondition_json=json.dumps(
            {"ref_sha": "c" * 40},
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest="sha256:" + "6" * 64,
        plan=plan,
    )

    outcome, reason = bridge._carrier_outcome_status(
        recent_comments=(
            _trusted_connector_comment(
                92,
                carrier.render_carrier_outcome_report(mismatched_report),
            ),
        ),
        owner="owner",
        repository="owner/repo",
        source=bridge.WorkerRequest(322, "executor", "implement-change"),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recovery_artifact=recovery,
        qualified_carrier=qualified,
    )

    assert outcome == "BLOCKED"
    assert reason == "application-completion-carrier-outcome-invalid"
