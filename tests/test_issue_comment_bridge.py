from __future__ import annotations

from pathlib import Path

from investment_strategy import issue_comment_bridge as bridge

WORKFLOW_PATH = Path(".github/workflows/scheduled-agent-bridge.yml")
REQUEST_BODY = "DISPATCH_REQUEST\nRequested-At: 2026-08-24T03:45:00Z"
REVISION = "cb8f9ec12d826e0d71897a4c73ece961d00df59e"


def _event(
    *, issue_number: int = 321, comment_id: int = 987, body: str = REQUEST_BODY
) -> dict[str, object]:
    return {
        "action": "created",
        "issue": {"number": issue_number},
        "comment": {"id": comment_id, "body": body},
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
