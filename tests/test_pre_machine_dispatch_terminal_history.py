"""Production-shaped regressions for pre-machine-dispatch closed routing debt."""

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


def _terminal_124_payload() -> dict[str, object]:
    return {
        "number": 124,
        "state": "closed",
        "state_reason": "completed",
        "body": "Change: require-ci-reobservation-before-async-exit\n",
        "labels": [{"name": "agent:lead"}, {"name": "action:finalize-archive"}],
        "created_at": "2026-08-21T05:56:01Z",
        "closed_at": "2026-08-21T09:33:25Z",
        "comments": 23,
    }


def _terminal_124_comment(*, updated_at: str = "2026-08-21T09:34:08Z") -> dict[str, object]:
    return {
        "id": 5368139311,
        "body": (
            "## ACTION_RESULT\n\n"
            "Workflow: #124\n"
            "Change: `require-ci-reobservation-before-async-exit`\n"
            "Action: `Lead / finalize-archive`\n"
            "Result: `LIFECYCLE_COMPLETE`\n"
            "Revision: final Archive PR #127 exact reviewed/merged head "
            "`d9401afb2992de0b274f267040bbdde4b4f75dad`\n"
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": "2026-08-21T09:34:08Z",
        "updated_at": updated_at,
    }


def _install_current_debt(
    monkeypatch: pytest.MonkeyPatch,
    comment: dict[str, object],
) -> None:
    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((_formal_140_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((_terminal_124_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: ((comment,),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue",
        lambda repository, token, issue_number: _terminal_124_payload(),
    )


def test_pre_dispatch_terminal_journal_routes_candidate_local_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_current_debt(monkeypatch, _terminal_124_comment())

    decision = workflow_dispatch.classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )

    assert decision.disposition == "AUTHORIZE"
    assert decision.formal_issue_ids == (140,)
    assert decision.selected_issue_id == 124
    assert decision.selected_routing == ("lead", "resolve-question")
    assert decision.selected_debt_disposition == "terminal-cleanup"


def test_compatible_terminal_journal_replay_still_routes_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_current_debt(
        monkeypatch,
        _terminal_124_comment(updated_at="2026-08-24T12:07:00Z"),
    )

    decision = workflow_dispatch.classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )

    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 124
    assert decision.selected_debt_disposition == "terminal-cleanup"
