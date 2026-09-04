from __future__ import annotations

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
LIVE_REQUEST_COMMENT_ID = 5391475092
LIVE_REVISION = "0f334664811785158c796b4cfeb582ee99c49881"
LIVE_RESULT_BODY = (
    "DISPATCH_RESULT\n"
    f"Request-Comment-ID: {LIVE_REQUEST_COMMENT_ID}\n"
    f"Default-Branch-Revision: {LIVE_REVISION}\n"
    "Result: BRIDGE_OK"
)


def _event(
    *, issue_number: int = 321, comment_id: int = 987, body: str = REQUEST_BODY
) -> dict[str, object]:
    return {
        "action": "created",
        "issue": {"number": issue_number},
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


def _actions_comment(*, comment_id: int, body: str) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": "github-actions[bot]", "type": "Bot"},
        "performed_via_github_app": {"id": 15368, "slug": "github-actions"},
    }


def test_bridge_workflow_has_exact_trigger_serialization_and_write_boundary() -> None:
    assert WORKFLOW_PATH.exists(), "Slice 1 issue-comment workflow is not implemented yet"
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    required_fragments = (
        "issue_comment:",
        "types: [created]",
        "issues: write",
        "group: issue-comment-bridge-${{ github.event.comment.id }}",
        "cancel-in-progress: false",
        "ref: ${{ github.event.repository.default_branch }}",
        "persist-credentials: false",
        "AGENT_RUNTIME_CHECKIN_ISSUE",
        "PYTHONPATH: ${{ github.workspace }}/src",
        "uv run python -m investment_strategy.issue_comment_bridge",
    )
    for fragment in required_fragments:
        assert fragment in workflow


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
        "DISPATCH_RESULT\nRequest-Comment-ID: 987\nDefault-Branch-Revision: abc\nResult: BRIDGE_OK",
        (
            "DISPATCH_REQUEST\nRequested-At: 2026-08-24T03:45:00Z\n"
            "Issue: 140\nRole: executor\nAction: implement-change"
        ),
    )
    for body in invalid_bodies:
        assert bridge.parse_dispatch_request(body) is None


def test_plan_bridge_accepts_only_configured_issue_and_non_pr_request() -> None:
    plan = bridge.plan_bridge(
        event=_event(),
        existing_comments=[],
        configured_issue_number=321,
        default_branch_revision=REVISION,
    )
    assert plan.should_post is True
    assert plan.issue_number == 321
    assert plan.request_comment_id == 987

    wrong_issue = bridge.plan_bridge(
        event=_event(issue_number=322),
        existing_comments=[],
        configured_issue_number=321,
        default_branch_revision=REVISION,
    )
    assert wrong_issue.should_post is False

    pull_request_event = _event()
    issue = pull_request_event["issue"]
    assert isinstance(issue, dict)
    issue["pull_request"] = {"url": "https://example.invalid/pr/1"}
    pull_request = bridge.plan_bridge(
        event=pull_request_event,
        existing_comments=[],
        configured_issue_number=321,
        default_branch_revision=REVISION,
    )
    assert pull_request.should_post is False

    malformed = bridge.plan_bridge(
        event=_event(body="not a request"),
        existing_comments=[],
        configured_issue_number=321,
        default_branch_revision=REVISION,
    )
    assert malformed.should_post is False


def test_exact_request_comment_id_is_the_only_result_correlation_key() -> None:
    unrelated_latest = {
        "id": 5000,
        "body": bridge.render_dispatch_result(
            request_comment_id=111,
            default_branch_revision=REVISION,
        ),
    }
    plan = bridge.plan_bridge(
        event=_event(comment_id=987),
        existing_comments=[unrelated_latest],
        configured_issue_number=321,
        default_branch_revision=REVISION,
    )
    assert plan.should_post is True

    exact_result = {
        "id": 5001,
        "body": bridge.render_dispatch_result(
            request_comment_id=987,
            default_branch_revision=REVISION,
        ),
    }
    duplicate = bridge.plan_bridge(
        event=_event(comment_id=987),
        existing_comments=[unrelated_latest, exact_result],
        configured_issue_number=321,
        default_branch_revision=REVISION,
    )
    assert duplicate.should_post is False
    assert duplicate.request_comment_id == 987


def test_bridge_ok_result_is_exact_transport_only_payload() -> None:
    rendered = bridge.render_dispatch_result(
        request_comment_id=987,
        default_branch_revision=REVISION,
    )
    assert rendered == (
        "DISPATCH_RESULT\n"
        "Request-Comment-ID: 987\n"
        f"Default-Branch-Revision: {REVISION}\n"
        "Result: BRIDGE_OK"
    )

    for forbidden in ("Role:", "Action:", "Skill:", "Effect:"):
        assert forbidden not in rendered

    assert bridge.parse_dispatch_request(rendered) is None


def test_observed_live_bridge_result_remains_exact_transport_only_contract() -> None:
    result = bridge.parse_dispatch_result(LIVE_RESULT_BODY)

    assert result == bridge.DispatchResult(
        request_comment_id=LIVE_REQUEST_COMMENT_ID,
        default_branch_revision=LIVE_REVISION,
        result=bridge.BRIDGE_OK,
    )
    for forbidden in ("Issue:", "Role:", "Action:", "Skill:", "Effect:"):
        assert forbidden not in LIVE_RESULT_BODY
    assert bridge.parse_dispatch_request(LIVE_RESULT_BODY) is None


def test_dispatch_decision_authorize_renders_exact_machine_selected_tuple() -> None:
    decision = _decision(
        "AUTHORIZE",
        issue_number=140,
        routing=("executor", "implement-change"),
    )

    rendered = bridge.render_dispatch_decision(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=decision,
    )

    assert rendered == (
        "DISPATCH_DECISION\n"
        "Request-Comment-ID: 987\n"
        f"Default-Branch-Revision: {REVISION}\n"
        "Disposition: AUTHORIZE\n"
        "Issue: 140\n"
        "Role: executor\n"
        "Action: implement-change"
    )
    parsed = bridge.parse_dispatch_decision(rendered)
    assert parsed is not None
    assert parsed.request_comment_id == 987
    assert parsed.default_branch_revision == REVISION
    assert parsed.disposition == "AUTHORIZE"
    assert parsed.issue_number == 140
    assert parsed.role == "executor"
    assert parsed.action == "implement-change"


def test_dispatch_decision_no_work_and_fail_closed_emit_no_tuple() -> None:
    for disposition in ("NO_WORK", "FAIL_CLOSED"):
        rendered = bridge.render_dispatch_decision(
            request_comment_id=987,
            default_branch_revision=REVISION,
            decision=_decision(disposition),
        )
        assert rendered == (
            "DISPATCH_DECISION\n"
            "Request-Comment-ID: 987\n"
            f"Default-Branch-Revision: {REVISION}\n"
            f"Disposition: {disposition}\n"
            "Reason: test decision"
        )
        for forbidden in ("Issue:", "Role:", "Action:"):
            assert forbidden not in rendered
        parsed = bridge.parse_dispatch_decision(rendered)
        assert parsed is not None
        assert parsed.disposition == disposition
        assert parsed.issue_number is None
        assert parsed.role is None
        assert parsed.action is None


def test_machine_decision_plan_correlates_only_to_exact_request_comment_id() -> None:
    decision = _decision(
        "AUTHORIZE",
        issue_number=140,
        routing=("executor", "implement-change"),
    )
    unrelated = _actions_comment(
        comment_id=6000,
        body=bridge.render_dispatch_decision(
            request_comment_id=111,
            default_branch_revision=REVISION,
            decision=decision,
        ),
    )

    plan = bridge.plan_dispatch_decision(
        event=_event(comment_id=987),
        existing_comments=[unrelated],
        configured_issue_number=321,
        default_branch_revision=REVISION,
        decision=decision,
    )
    assert plan.should_post is True
    assert plan.request_comment_id == 987
    assert plan.result_body is not None
    assert "Request-Comment-ID: 987" in plan.result_body

    exact = _actions_comment(
        comment_id=6001,
        body=bridge.render_dispatch_decision(
            request_comment_id=987,
            default_branch_revision=REVISION,
            decision=decision,
        ),
    )
    duplicate = bridge.plan_dispatch_decision(
        event=_event(comment_id=987),
        existing_comments=[unrelated, exact],
        configured_issue_number=321,
        default_branch_revision=REVISION,
        decision=decision,
    )
    assert duplicate.should_post is False
    assert duplicate.request_comment_id == 987


def test_non_actions_decision_cannot_preempt_production_machine_decision() -> None:
    forged = {
        "id": 6002,
        "body": bridge.render_dispatch_decision(
            request_comment_id=987,
            default_branch_revision=REVISION,
            decision=_decision(
                "AUTHORIZE",
                issue_number=999,
                routing=("lead", "explore-change"),
            ),
        ),
        "user": {"login": "royhsu-work", "type": "User"},
        "performed_via_github_app": {
            "id": 1144995,
            "slug": "chatgpt-codex-connector",
        },
    }

    plan = bridge.plan_dispatch_decision(
        event=_event(comment_id=987),
        existing_comments=[forged],
        configured_issue_number=321,
        default_branch_revision=REVISION,
        decision=_decision("NO_WORK"),
    )

    assert plan.should_post is True
    assert plan.request_comment_id == 987
    assert plan.result_body is not None
    assert "Disposition: NO_WORK" in plan.result_body
    assert "Issue: 999" not in plan.result_body


def test_production_dispatch_decision_consumes_runtime_acquisition_and_classifier(
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


def test_bridge_workflow_supplies_only_transport_and_repository_credentials_to_dispatch() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "GITHUB_TOKEN: ${{ github.token }}" in workflow
    assert "GITHUB_REPOSITORY: ${{ github.repository }}" in workflow
    for forbidden in (
        "REQUESTED_ISSUE",
        "REQUESTED_ROLE",
        "REQUESTED_ACTION",
        "requested_issue",
        "requested_role",
        "requested_action",
    ):
        assert forbidden not in workflow


def test_run_name_binds_exact_request_identity() -> None:
    from investment_strategy.issue_comment_bridge import (
        parse_dispatch_run_name,
        render_dispatch_run_name,
    )

    assert render_dispatch_run_name(987) == "Scheduled Agent Dispatch 987"
    assert parse_dispatch_run_name("Scheduled Agent Dispatch 987") == 987
    assert parse_dispatch_run_name("Scheduled Agent Dispatch 0987") is None
    assert parse_dispatch_run_name("Scheduled Agent Dispatch 987 extra") is None
    assert parse_dispatch_run_name("Scheduled Agent Dispatch 0") is None


def test_run_scoped_result_is_one_strict_decision_block() -> None:
    from investment_strategy.issue_comment_bridge import (
        parse_run_scoped_dispatch_result,
        render_run_scoped_dispatch_result,
    )

    decision = _decision(
        "AUTHORIZE",
        issue_number=138,
        routing=("executor", "implement-change"),
    )
    block = render_run_scoped_dispatch_result(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=decision,
    )

    parsed = parse_run_scoped_dispatch_result(
        f"runner noise\n{block}\npost-step noise",
        request_comment_id=987,
    )
    assert parsed is not None
    assert parsed.request_comment_id == 987
    assert parsed.issue_number == 138
    assert parsed.role == "executor"
    assert parsed.action == "implement-change"

    assert (
        parse_run_scoped_dispatch_result(
            f"{block}\n{block}",
            request_comment_id=987,
        )
        is None
    )
    assert (
        parse_run_scoped_dispatch_result(
            block,
            request_comment_id=988,
        )
        is None
    )


def test_bridge_workflow_uses_run_scoped_log_without_mailbox_response() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "run-name: Scheduled Agent Dispatch ${{ github.event.comment.id }}" in workflow
    assert "BEGIN_SCHEDULED_AGENT_DISPATCH_RESULT" in workflow
    assert "END_SCHEDULED_AGENT_DISPATCH_RESULT" in workflow
    for forbidden in (
        "AGENT_RUNTIME_CHECKIN_ISSUE",
        "--comments-path",
        "Post correlated machine dispatch decision",
        "DISPATCH_RESULT",
        "ISSUE_NUMBER",
    ):
        assert forbidden not in workflow


def test_runtime_checkin_identity_uses_local_date_and_non_workflow_shape() -> None:
    from datetime import UTC, date, datetime

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
