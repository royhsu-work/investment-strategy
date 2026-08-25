"""Regressions for closed routing debt from before terminal-aligned Issue closure."""

from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_runtime as runtime
import investment_strategy.workflow_dispatch as workflow_dispatch


def _formal_140_payload() -> dict[str, object]:
    return {
        "number": 140,
        "state": "open",
        "body": "Change: validate-no-api-issue-comment-bridge",
        "labels": [{"name": "agent:lead"}, {"name": "action:finalize-change"}],
        "created_at": "2026-08-23T11:39:39Z",
        "closed_at": None,
    }


def _historical_terminal_25_payload() -> dict[str, object]:
    return {
        "number": 25,
        "state": "closed",
        "state_reason": "completed",
        "body": "Change: workflow-dynamic-scheduled-dispatch\n",
        "labels": [{"name": "agent:lead"}, {"name": "action:finalize-archive"}],
        "created_at": "2026-08-12T11:43:55Z",
        "closed_at": "2026-08-13T19:49:10Z",
        "comments": 134,
    }


def _lifecycle_complete_25_comment(*, head: str = "786680176324f396322e4d1bb2f77b63be97bb48") -> dict[str, object]:
    return {
        "id": 5289357012,
        "body": (
            "## ACTION_RESULT\n\n"
            "Workflow: #25\n"
            "Change: `workflow-dynamic-scheduled-dispatch`\n"
            "Action: `Lead / finalize-archive`\n"
            "Result: `LIFECYCLE_COMPLETE`\n"
            "Revision: Archive PR #33 exact head "
            f"`{head}`; merge commit `ed767ca645e782bea96154044d02c45e4bef2cbf`\n"
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": "2026-08-13T20:10:09Z",
        "updated_at": "2026-08-13T20:10:09Z",
    }


def _install_debt(
    monkeypatch: pytest.MonkeyPatch,
    comments: tuple[dict[str, object], ...],
) -> None:
    monkeypatch.setattr(runtime, "_github_open_issue_pages", lambda repository, token: ((_formal_140_payload(),),))
    monkeypatch.setattr(
        runtime,
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((_historical_terminal_25_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: (comments,),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue",
        lambda repository, token, issue_number: _historical_terminal_25_payload(),
    )


def test_pre_alignment_terminal_debt_with_compatible_completion_routes_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_debt(monkeypatch, (_lifecycle_complete_25_comment(),))

    decision = workflow_dispatch.classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )

    assert decision.disposition == "AUTHORIZE"
    assert decision.formal_issue_ids == (140,)
    assert decision.selected_issue_id == 25
    assert decision.selected_routing == ("lead", "resolve-question")
    assert decision.selected_debt_disposition == "terminal-cleanup"


def test_conflicting_terminal_identities_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_debt(
        monkeypatch,
        (
            _lifecycle_complete_25_comment(),
            _lifecycle_complete_25_comment(head="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
        ),
    )

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )

    assert workflow_dispatch.classify_dispatch(preflight).disposition == "FAIL_CLOSED"
    assert any(item.state == "closed" for item in preflight.issues)
