"""Regressions for terminal history created before terminal-aligned Issue closure."""

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


def _historical_terminal_25_payload() -> dict[str, object]:
    return {
        "number": 25,
        "state": "closed",
        "state_reason": "completed",
        "body": "Change: workflow-dynamic-scheduled-dispatch\n",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-archive"},
        ],
        "created_at": "2026-08-12T11:43:55Z",
        "closed_at": "2026-08-13T19:49:10Z",
        "comments": 134,
    }


def _lifecycle_complete_25_comment(
    *,
    created_at: str = "2026-08-13T20:10:09Z",
    updated_at: str | None = None,
) -> dict[str, object]:
    return {
        "id": 5289357012,
        "body": (
            "## ACTION_RESULT\n\n"
            "Workflow: #25\n"
            "Change: `workflow-dynamic-scheduled-dispatch`\n"
            "Action: `Lead / finalize-archive`\n"
            "Result: `LIFECYCLE_COMPLETE`\n"
            "Revision: Archive PR #33 exact head "
            "`786680176324f396322e4d1bb2f77b63be97bb48`; merge commit "
            "`ed767ca645e782bea96154044d02c45e4bef2cbf`\n"
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": created_at,
        "updated_at": updated_at or created_at,
    }


def test_pre_alignment_post_close_completion_is_structurally_terminal(
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
        lambda repository, token: ((_historical_terminal_25_payload(),),),
    )

    def structural_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        assert url.endswith("/issues/25/comments?per_page=100&page=2")
        return (_lifecycle_complete_25_comment(),)

    monkeypatch.setattr(runtime, "_github_get_list_page", structural_page)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("proven historical terminal must not inspect archived Change")

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


def test_post_alignment_post_close_completion_does_not_clear_structurally(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    historical = _historical_terminal_25_payload()
    historical["closed_at"] = "2026-08-21T00:00:00Z"

    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((_formal_140_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_closed_issue_pages",
        lambda repository, token: ((historical,),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_get_list_page",
        lambda url, token: (_lifecycle_complete_25_comment(created_at="2026-08-21T00:01:00Z"),),
    )
    monkeypatch.setattr(
        runtime,
        "_legacy_terminal_evidence_from_checkout",
        lambda change, *, repository_root: "indeterminate",
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: ((),),
    )

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )

    assert workflow_dispatch.classify_dispatch(preflight).disposition == "FAIL_CLOSED"
    assert any(item.state == "closed" for item in preflight.issues)
