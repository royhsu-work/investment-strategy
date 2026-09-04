from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pytest import MonkeyPatch

from investment_strategy import issue_comment_bridge as bridge
from investment_strategy.workflow_dispatch import (
    DispatchDecision,
    ObservationProvenance,
    Routing,
)

WORKFLOW_PATH = Path(".github/workflows/scheduled-agent-bridge.yml")
REQUEST_BODY = "DISPATCH_REQUEST\nRequested-At: 2026-08-24T03:45:00Z"
REVISION = "cb8f9ec12d826e0d71897a4c73ece961d00df59e"


def _event(
    *,
    issue_number: int = 321,
    comment_id: int = 987,
    body: str = REQUEST_BODY,
    title: str = "[Agent Runtime] 2026-09-03",
    state: Literal["open", "closed"] = "open",
    labels: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "action": "created",
        "issue": {
            "number": issue_number,
            "title": title,
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
        recovery_candidate_ids=(),
        preactivation_candidate_ids=(),
        selected_issue_id=issue_number,
        selected_routing=routing,
        disposition=disposition,
        reason="test decision",
    )


def test_bridge_workflow_is_run_scoped_and_has_no_mailbox_write() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "issue_comment:" in workflow
    assert "types: [created]" in workflow
    assert "run-name: Scheduled Agent Dispatch ${{ github.event.comment.id }}" in workflow
    assert "issues: read" in workflow
    assert "ref: ${{ github.event.repository.default_branch }}" in workflow
    assert "persist-credentials: false" in workflow
    assert "uv run python -m investment_strategy.issue_comment_bridge" in workflow
    assert "BEGIN_SCHEDULED_AGENT_DISPATCH_RESULT" in workflow
    assert "END_SCHEDULED_AGENT_DISPATCH_RESULT" in workflow
    for forbidden in (
        "AGENT_RUNTIME_CHECKIN_ISSUE",
        "--comments-path",
        "Post correlated machine dispatch decision",
        "ISSUE_NUMBER",
    ):
        assert forbidden not in workflow


def test_request_parser_accepts_only_exact_two_line_contract() -> None:
    request = bridge.parse_dispatch_request(REQUEST_BODY)
    assert request is not None
    assert request.requested_at == "2026-08-24T03:45:00Z"

    invalid_bodies = (
        "DISPATCH_REQUEST",
        "DISPATCH_REQUEST\nRequested-At:",
        "DISPATCH_REQUEST\nRequested-At: 2026-08-24T03:45:00Z\nExtra: nope",
        " DISPATCH_REQUEST\nRequested-At: 2026-08-24T03:45:00Z",
        "DISPATCH_REQUEST\n Requested-At: 2026-08-24T03:45:00Z",
    )
    for body in invalid_bodies:
        assert bridge.parse_dispatch_request(body) is None


def test_run_name_binds_exact_request_identity() -> None:
    assert bridge.render_dispatch_run_name(987) == "Scheduled Agent Dispatch 987"
    assert bridge.parse_dispatch_run_name("Scheduled Agent Dispatch 987") == 987
    assert bridge.parse_dispatch_run_name("Scheduled Agent Dispatch 0987") is None
    assert bridge.parse_dispatch_run_name("Scheduled Agent Dispatch 987 extra") is None
    assert bridge.parse_dispatch_run_name("Scheduled Agent Dispatch 0") is None


def test_run_scoped_result_is_one_strict_decision_block() -> None:
    decision = _decision(
        "AUTHORIZE",
        issue_number=138,
        routing=("executor", "implement-change"),
    )
    block = bridge.render_run_scoped_dispatch_result(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=decision,
    )

    parsed = bridge.parse_run_scoped_dispatch_result(
        f"runner noise\n{block}\npost-step noise",
        request_comment_id=987,
    )
    assert parsed is not None
    assert parsed.request_comment_id == 987
    assert parsed.issue_number == 138
    assert parsed.role == "executor"
    assert parsed.action == "implement-change"

    assert (
        bridge.parse_run_scoped_dispatch_result(
            f"{block}\n{block}",
            request_comment_id=987,
        )
        is None
    )
    assert (
        bridge.parse_run_scoped_dispatch_result(
            block,
            request_comment_id=988,
        )
        is None
    )


def test_dispatch_decision_parser_preserves_exact_machine_vocabulary() -> None:
    decisions = (
        _decision("NO_WORK"),
        _decision("FAIL_CLOSED"),
        _decision(
            "AUTHORIZE",
            issue_number=138,
            routing=("executor", "implement-change"),
        ),
    )
    for decision in decisions:
        rendered = bridge.render_dispatch_decision(
            request_comment_id=987,
            default_branch_revision=REVISION,
            decision=decision,
        )
        parsed = bridge.parse_dispatch_decision(rendered)
        assert parsed is not None
        assert parsed.request_comment_id == 987
        assert parsed.disposition == decision.disposition


def test_dispatch_plan_uses_event_identity_without_comment_history() -> None:
    decision = _decision(
        "AUTHORIZE",
        issue_number=321,
        routing=("executor", "implement-change"),
    )
    plan = bridge.plan_dispatch_decision(
        event=_event(),
        default_branch_revision=REVISION,
        decision=decision,
    )
    assert plan.should_emit is True
    assert plan.issue_number == 321
    assert plan.request_comment_id == 987
    assert plan.result_body is not None
    assert "Issue: 321" in plan.result_body
    assert "Action: implement-change" in plan.result_body


def test_dispatch_plan_rejects_formal_workflow_issue_as_transport_shard() -> None:
    decision = _decision("NO_WORK")
    plan = bridge.plan_dispatch_decision(
        event=_event(labels=[{"name": "agent:executor"}]),
        default_branch_revision=REVISION,
        decision=decision,
    )
    assert plan.should_emit is False


def test_production_dispatch_decision_consumes_runtime_acquisition(
    monkeypatch: MonkeyPatch,
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


def test_runtime_checkin_identity_uses_local_date_and_non_workflow_shape() -> None:
    from investment_strategy.scheduled_agent_checkin import (
        checkin_title,
        parse_checkin_day,
        taipei_day,
    )

    assert taipei_day(datetime(2026, 9, 2, 16, 30, tzinfo=UTC)) == date(2026, 9, 3)
    payload = {
        "number": 142,
        "title": checkin_title(date(2026, 9, 3)),
        "state": "open",
        "labels": [],
    }
    assert parse_checkin_day(payload) == date(2026, 9, 3)

    routed = dict(payload)
    routed["labels"] = [{"name": "action:implement-change"}]
    assert parse_checkin_day(routed) is None

    pull_request = dict(payload)
    pull_request["pull_request"] = {}
    assert parse_checkin_day(pull_request) is None


def test_closed_shard_keeps_inflight_dispatch_identity_after_rollover() -> None:
    decision = _decision("NO_WORK")
    plan = bridge.plan_dispatch_decision(
        event=_event(state="closed"),
        default_branch_revision=REVISION,
        decision=decision,
    )
    assert plan.should_emit is True
    assert plan.issue_number == 321
    assert plan.request_comment_id == 987
