"""Production-shaped compatibility regressions for pre-machine-dispatch terminal history."""

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


def _install_pages(monkeypatch: pytest.MonkeyPatch, comment: dict[str, object]) -> None:
    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((_formal_140_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_closed_issue_pages",
        lambda repository, token: ((_terminal_124_payload(),),),
    )

    def structural_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        assert url.endswith("/issues/124/comments?per_page=100&page=1")
        return (comment,)

    monkeypatch.setattr(runtime, "_github_get_list_page", structural_page)


def test_pre_dispatch_124_terminal_history_clears_without_archived_change_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_pages(monkeypatch, _terminal_124_comment())

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("proven pre-dispatch terminal history must not inspect archived Change")

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


def test_edited_pre_dispatch_completion_does_not_gain_historical_clearance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_pages(monkeypatch, _terminal_124_comment(updated_at="2026-08-24T12:07:00Z"))
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
