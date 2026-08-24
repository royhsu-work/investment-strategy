"""Regressions for pre-workflow-dynamic finalize-archive terminal history."""

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


def _legacy_terminal_18_payload() -> dict[str, object]:
    return {
        "number": 18,
        "state": "closed",
        "state_reason": "completed",
        "body": ("## Workflow identity\n\nChange: establish-scheduled-role-agent-workflow\n"),
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-archive"},
        ],
        "created_at": "2026-08-12T08:09:42Z",
        "closed_at": "2026-08-12T12:03:46Z",
        "comments": 26,
    }


def _legacy_final_archive_18_comment() -> dict[str, object]:
    return {
        "id": 5266550577,
        "body": (
            "## Lead — final archive confirmation\n\n"
            "Role: Lead\n"
            "Action: `finalize-archive`\n"
            "Change: `establish-scheduled-role-agent-workflow`\n"
            "Archive PR: #20\n"
            "Authorized/reviewed archive head: "
            "`a082c5157340ada41a3dd632bcb28cb0a6c56948`\n"
            "Archive merge commit / current `main` HEAD: "
            "`d7b59b3ecdd84a400b6ed39ca0223ca8102f20d5`\n"
            "Result: **ARCHIVE_CONFIRMED_ON_DEFAULT_BRANCH**\n\n"
            "Final remaining mutation for #18 is the explicit Lead coordination-Issue close."
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": "2026-08-12T12:03:34Z",
        "updated_at": "2026-08-12T12:03:34Z",
    }


def test_pre_dynamic_finalize_archive_terminal_is_structurally_clear_without_archive_lookup(
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
        lambda repository, token: ((_legacy_terminal_18_payload(),),),
    )

    def structural_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        assert url.endswith("/issues/18/comments?per_page=100&page=1")
        return (_legacy_final_archive_18_comment(),)

    monkeypatch.setattr(runtime, "_github_get_list_page", structural_page)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("proven pre-dynamic terminal history must not read archived Change")

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


def test_pre_dynamic_finalize_archive_completed_without_trusted_marker_stays_nonclear(
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
        lambda repository, token: ((_legacy_terminal_18_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_get_list_page",
        lambda url, token: (
            {
                "id": 1,
                "body": "not a trusted final archive terminal marker",
                "user": {"login": "royhsu-work"},
                "author_association": "OWNER",
                "created_at": "2026-08-12T12:03:34Z",
                "updated_at": "2026-08-12T12:03:34Z",
            },
        ),
    )
    archive_lookups: list[str] = []

    def exceptional_lookup(change: str, *, repository_root: Path) -> str:
        del repository_root
        archive_lookups.append(change)
        return "indeterminate"

    monkeypatch.setattr(runtime, "_legacy_terminal_evidence_from_checkout", exceptional_lookup)

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )

    assert archive_lookups == ["establish-scheduled-role-agent-workflow"]
    assert workflow_dispatch.classify_dispatch(preflight).disposition == "FAIL_CLOSED"
