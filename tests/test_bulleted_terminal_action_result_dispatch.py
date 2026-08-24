"""Regression for canonical ACTION_RESULT fields rendered as Markdown bullets."""

from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_runtime as runtime
import investment_strategy.workflow_dispatch as workflow_dispatch


def _formal_140_payload() -> dict[str, object]:
    return {
        "number": 140,
        "state": "open",
        "body": "Change: validate-no-api-issue-comment-bridge",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-change"},
        ],
        "created_at": "2026-08-23T11:39:39Z",
        "closed_at": None,
    }


def _terminal_105_payload() -> dict[str, object]:
    return {
        "number": 105,
        "state": "closed",
        "state_reason": "completed",
        "body": "Change: enforce-dispatch-cardinality-preflight\n",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-archive"},
            {"name": "human:approved"},
        ],
        "created_at": "2026-08-19T15:20:19Z",
        "closed_at": "2026-08-19T21:30:18Z",
        "comments": 41,
    }


def _bulleted_lifecycle_complete_105_comment() -> dict[str, object]:
    return {
        "id": 5348437664,
        "body": (
            "## ACTION_RESULT\n\n"
            "- Workflow: #105\n"
            "- Change: `enforce-dispatch-cardinality-preflight`\n"
            "- Action: `Lead / finalize-archive`\n"
            "- Result: `LIFECYCLE_COMPLETE`\n"
            "- Revision: Archive PR #108 exact reviewed head "
            "`38d2e9c90bf72e710d9e43cc55a7b6d18c36f845`; merge commit "
            "`77ba3d9b746dc05f562626d13937f9c672996ba9`\n"
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": "2026-08-19T21:31:00Z",
        "updated_at": "2026-08-19T21:31:00Z",
    }


def test_bulleted_pre_alignment_completion_clears_without_archived_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((_formal_140_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_closed_issue_pages",
        lambda repository, token: ((_terminal_105_payload(),),),
    )

    def structural_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        assert url.endswith("/issues/105/comments?per_page=100&page=1")
        return (_bulleted_lifecycle_complete_105_comment(),)

    monkeypatch.setattr(runtime, "_github_get_list_page", structural_page)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("proven terminal history must not inspect archived Change")

    monkeypatch.setattr(runtime, "_legacy_terminal_evidence_from_checkout", forbidden)
    monkeypatch.setattr(runtime, "_github_issue_comment_pages", forbidden)
    monkeypatch.setattr(runtime, "_github_issue", forbidden)

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )
    decision = workflow_dispatch.classify_dispatch(preflight)

    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 140
    assert decision.selected_routing == ("lead", "finalize-change")
    assert all(item.state == "open" for item in preflight.issues)


def test_bulleted_fields_do_not_allow_duplicate_terminal_identity() -> None:
    comment = _bulleted_lifecycle_complete_105_comment()
    comment["body"] = f"{comment['body']}\nWorkflow: #105\n"

    assert not runtime._valid_lifecycle_complete_comment(
        comment,
        issue_number=105,
        change="enforce-dispatch-cardinality-preflight",
        repository_owner="royhsu-work",
    )
