from __future__ import annotations

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
