"""Regressions for pre-workflow-dynamic closed routing debt."""

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


def _legacy_terminal_18_payload() -> dict[str, object]:
    return {
        "number": 18,
        "state": "closed",
        "state_reason": "completed",
        "body": "## Workflow identity\n\nChange: establish-scheduled-role-agent-workflow\n",
        "labels": [{"name": "agent:lead"}, {"name": "action:finalize-archive"}],
        "created_at": "2026-08-12T08:09:42Z",
        "closed_at": "2026-08-12T12:03:46Z",
        "comments": 26,
    }


def test_pre_dynamic_terminal_routing_debt_is_selected_for_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runtime, "_github_open_issue_pages", lambda repository, token: ((_formal_140_payload(),),))
    monkeypatch.setattr(
        runtime,
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((_legacy_terminal_18_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_legacy_terminal_evidence_from_checkout",
        lambda change, *, repository_root: "terminal-history",
    )

    decision = workflow_dispatch.classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )

    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 18
    assert decision.selected_routing == ("lead", "resolve-question")
    assert decision.selected_debt_disposition == "terminal-cleanup"


def test_pre_dynamic_unproven_terminal_debt_stays_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runtime, "_github_open_issue_pages", lambda repository, token: ((_formal_140_payload(),),))
    monkeypatch.setattr(
        runtime,
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((_legacy_terminal_18_payload(),),),
    )
    lookups: list[str] = []

    def exceptional_lookup(change: str, *, repository_root: Path) -> str:
        del repository_root
        lookups.append(change)
        return "indeterminate"

    monkeypatch.setattr(runtime, "_legacy_terminal_evidence_from_checkout", exceptional_lookup)

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )

    assert lookups == ["establish-scheduled-role-agent-workflow"]
    assert workflow_dispatch.classify_dispatch(preflight).disposition == "FAIL_CLOSED"
