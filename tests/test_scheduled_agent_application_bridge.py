"""Regression coverage for Scheduled Agent issue-comment application ingress."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from investment_strategy.scheduled_agent_application_bridge import (
    APPLICATION_REQUEST_MARKER,
    parse_application_request,
    plan_application,
)

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "4e3241d7d84a64012bf3b6218442128a4cb48d7a"
_CHECKIN_ISSUE = 142


def _app(slug: str) -> dict[str, object]:
    return {"slug": slug}


def _user(login: str) -> dict[str, object]:
    return {"login": login}


def _connector_comment(comment_id: int, body: str) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": _user("royhsu-work"),
        "performed_via_github_app": _app("chatgpt-codex-connector"),
    }


def _actions_comment(comment_id: int, body: str) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": _user("github-actions[bot]"),
        "performed_via_github_app": _app("github-actions"),
    }


def _worker_result() -> dict[str, object]:
    return {
        "issue_number": 138,
        "role": "lead",
        "action": "explore-change",
        "explore_disposition": "PROPOSAL_READY",
        "propose_disposition": None,
        "result_content": "bounded result",
        "requested_effects": [],
    }


def _effect_request(
    *,
    dispatch_request_comment_id: int = 100,
    dispatch_decision_comment_id: int = 101,
    worker_result: dict[str, object] | None = None,
) -> str:
    raw = json.dumps(worker_result or _worker_result(), sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return "\n".join(
        (
            APPLICATION_REQUEST_MARKER,
            f"Dispatch-Request-Comment-ID: {dispatch_request_comment_id}",
            f"Dispatch-Decision-Comment-ID: {dispatch_decision_comment_id}",
            f"Worker-Result-B64: {encoded}",
        )
    )


def _dispatch_request() -> str:
    return "DISPATCH_REQUEST\nRequested-At: 2026-08-31T11:01:49+08:00"


def _dispatch_decision(*, revision: str = _REVISION, disposition: str = "AUTHORIZE") -> str:
    lines = [
        "DISPATCH_DECISION",
        "Request-Comment-ID: 100",
        f"Default-Branch-Revision: {revision}",
        f"Disposition: {disposition}",
    ]
    if disposition == "AUTHORIZE":
        lines.extend(("Issue: 138", "Role: lead", "Action: explore-change"))
    else:
        lines.append("Reason: no work")
    return "\n".join(lines)


def _event(body: str, *, trusted: bool = True) -> dict[str, object]:
    comment = _connector_comment(102, body)
    if not trusted:
        comment["performed_via_github_app"] = None
    return {
        "action": "created",
        "issue": {"number": _CHECKIN_ISSUE},
        "comment": comment,
    }


def _comments(
    effect_body: str, *, decision_body: str | None = None
) -> list[list[dict[str, object]]]:
    return [
        [
            _connector_comment(100, _dispatch_request()),
            _actions_comment(101, decision_body or _dispatch_decision()),
            _connector_comment(102, effect_body),
        ]
    ]


def test_parse_application_request_decodes_exact_worker_result() -> None:
    body = _effect_request()

    request = parse_application_request(body)

    assert request is not None
    assert request.dispatch_request_comment_id == 100
    assert request.dispatch_decision_comment_id == 101
    assert json.loads(request.raw_worker_result) == _worker_result()


def test_parse_application_request_ignores_unrelated_comment() -> None:
    assert parse_application_request(_dispatch_request()) is None


def test_parse_application_request_rejects_malformed_effect_request() -> None:
    with pytest.raises(ValueError, match="exactly four lines"):
        parse_application_request("EFFECT_REQUEST\nDispatch-Request-Comment-ID: 100")


def test_plan_application_accepts_exact_trusted_dispatch_correlation() -> None:
    body = _effect_request()

    plan = plan_application(
        event=_event(body),
        comments_payload=_comments(body),
        configured_issue_number=_CHECKIN_ISSUE,
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source is not None
    assert (plan.source.issue_number, plan.source.role, plan.source.action) == (
        138,
        "lead",
        "explore-change",
    )
    assert json.loads(plan.raw_worker_result or "") == _worker_result()


def test_plan_application_ignores_non_effect_comment() -> None:
    plan = plan_application(
        event=_event(_dispatch_request()),
        comments_payload=[[]],
        configured_issue_number=_CHECKIN_ISSUE,
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert not plan.should_apply


def test_plan_application_rejects_connector_provenance_bypass() -> None:
    body = _effect_request()

    with pytest.raises(ValueError, match="configured ChatGPT connector"):
        plan_application(
            event=_event(body, trusted=False),
            comments_payload=_comments(body),
            configured_issue_number=_CHECKIN_ISSUE,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_plan_application_rejects_stale_dispatch_revision() -> None:
    body = _effect_request()

    with pytest.raises(ValueError, match="revision is stale"):
        plan_application(
            event=_event(body),
            comments_payload=_comments(
                body,
                decision_body=_dispatch_decision(revision="0" * 40),
            ),
            configured_issue_number=_CHECKIN_ISSUE,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_plan_application_rejects_non_authorizing_dispatch() -> None:
    body = _effect_request()

    with pytest.raises(ValueError, match="requires an AUTHORIZE"):
        plan_application(
            event=_event(body),
            comments_payload=_comments(
                body,
                decision_body=_dispatch_decision(disposition="NO_WORK"),
            ),
            configured_issue_number=_CHECKIN_ISSUE,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_plan_application_rejects_untrusted_dispatch_decision_comment() -> None:
    body = _effect_request()
    comments = _comments(body)
    comments[0][1]["performed_via_github_app"] = None

    with pytest.raises(ValueError, match="missing or untrusted"):
        plan_application(
            event=_event(body),
            comments_payload=comments,
            configured_issue_number=_CHECKIN_ISSUE,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_application_workflow_is_no_api_and_uses_dedicated_write_boundary() -> None:
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")

    assert "issue_comment:" in workflow
    assert "startsWith(github.event.comment.body, 'EFFECT_REQUEST')" in workflow
    assert "contents: write" in workflow
    assert "issues: write" in workflow
    assert "pull-requests: write" in workflow
    assert "scheduled_agent_application_bridge" in workflow
    assert "openai" not in workflow.lower()
    assert "responses" not in workflow.lower()
