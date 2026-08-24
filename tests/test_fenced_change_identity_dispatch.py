"""Regressions for canonical Issue Change identity outside Markdown examples."""

from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_runtime as runtime
from investment_strategy.workflow_dispatch import classify_dispatch


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


def _closed_93_payload() -> dict[str, object]:
    return {
        "number": 93,
        "state": "closed",
        "state_reason": "completed",
        "body": (
            "Change: remove-generic-human-explore-admission\n\n"
            "## Normal workflow example\n\n"
            "```text\n"
            "Change: unset\n"
            "```\n"
        ),
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-archive"},
            {"name": "human:approved"},
        ],
        "comments": 29,
        "created_at": "2026-08-18T17:28:23Z",
        "closed_at": "2026-08-19T12:51:55Z",
    }


def _complete_93_comment() -> dict[str, object]:
    return {
        "id": 5342618433,
        "body": (
            "## ACTION_RESULT\n\n"
            "Workflow: #93\n"
            "Change: `remove-generic-human-explore-admission`\n"
            "Action: `Lead / finalize-archive`\n"
            "Result: `LIFECYCLE_COMPLETE`\n"
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": "2026-08-19T13:12:12Z",
        "updated_at": "2026-08-19T13:12:12Z",
    }


def test_fenced_change_example_does_not_poison_closed_structural_dispatch(
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
        lambda repository, token: ((_closed_93_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_last_visible_issue_comment",
        lambda repository, token, **kwargs: _complete_93_comment(),
    )

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("closed Change forensics must not run for fenced examples")

    monkeypatch.setattr(runtime, "_acquire_detailed_exceptional_preflight", forbidden)
    monkeypatch.setattr(runtime, "_legacy_terminal_evidence_from_checkout", forbidden)

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )
    decision = classify_dispatch(preflight)
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 140
    assert decision.selected_routing == ("lead", "finalize-change")


def test_multiple_top_level_change_fields_remain_indeterminate() -> None:
    payload = _closed_93_payload()
    payload["body"] = (
        "Change: remove-generic-human-explore-admission\nChange: attacker-controlled-second-value\n"
    )

    observation = runtime.normalize_github_issue(payload)
    assert observation is not None
    assert observation.change == "unset"
    assert not observation.authoritative
