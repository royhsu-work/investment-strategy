"""Machine-gated Scheduled Agent governance and production dispatch regressions."""

from __future__ import annotations

from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_runtime as runtime
import investment_strategy.workflow_dispatch as workflow_dispatch
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RepositoryIssueSnapshot,
)

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
MESSAGES = ROOT / "agents" / "templates" / "messages.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"
CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split()).replace("- ", "-")


def _complete(*issues: RepositoryIssueSnapshot) -> DispatchPreflight:
    count = len(issues)
    return DispatchPreflight(
        issues=issues,
        enumeration=EnumerationEvidence(
            observed_count=count,
            source_total_count=count,
            incomplete_results=False,
            exhausted=True,
            observation_provenance=ObservationProvenance.QUALIFIED,
        ),
    )


def _formal_140_payload() -> dict[str, object]:
    return {
        "number": 140,
        "state": "open",
        "body": "Change: validate-no-api-issue-comment-bridge",
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:implement-change"},
        ],
        "created_at": "2026-08-23T11:39:39Z",
        "closed_at": None,
    }


def _terminal_124_payload() -> dict[str, object]:
    return {
        "number": 124,
        "state": "closed",
        "state_reason": "completed",
        "body": "Change: require-ci-reobservation-before-async-exit",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-archive"},
        ],
        "created_at": "2026-08-21T05:56:01Z",
        "closed_at": "2026-08-21T09:33:25Z",
        # GitHub currently reports 23 even though the REST comment list exposes
        # the terminal journal as the 22nd/last visible comment.
        "comments": 23,
    }


def _lifecycle_complete_124_comment() -> dict[str, object]:
    return {
        "id": 5368139311,
        "body": (
            "## ACTION_RESULT\n\n"
            "Workflow: #124\n"
            "Change: `require-ci-reobservation-before-async-exit`\n"
            "Action: `Lead / finalize-archive`\n"
            "Result: `LIFECYCLE_COMPLETE`\n"
            "Revision: final archive revision"
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": "2026-08-21T09:33:16Z",
        "updated_at": "2026-08-21T09:33:16Z",
    }


def _legacy_terminal_21_payload() -> dict[str, object]:
    return {
        "number": 21,
        "state": "closed",
        "state_reason": "completed",
        "body": ("## Workflow identity\n\n`Change: align-issue-completion-with-archive`\n"),
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:merge-pr"},
        ],
        "created_at": "2026-08-12T11:42:38Z",
        "closed_at": "2026-08-12T23:51:29Z",
        "comments": 20,
    }


def _legacy_archive_merge_21_comment(
    *, created_at: str = "2026-08-12T23:51:35Z"
) -> dict[str, object]:
    return {
        "id": 5274149383,
        "body": (
            "Executor / merge-pr — ARCHIVE MERGED\n\n"
            "Change: `align-issue-completion-with-archive`\n"
            "Archive PR: #27\n"
            "Authorized exact revision: `bcd52fae6367799d3e6a803834ed654f82cf4e82`\n\n"
            "Merge executed with "
            "`expected_head_sha=bcd52fae6367799d3e6a803834ed654f82cf4e82` and succeeded. "
            "GitHub merge result commit: `40d48d61842fd5a1ab379f36d489857c1943e278`.\n\n"
            "Outcome: Archive PR merge is durable. "
            "Handoff target: Lead / `finalize-archive` to reconstruct terminal state."
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": created_at,
        "updated_at": created_at,
    }


def test_mapped_worker_requires_machine_pre_model_dispatch_after_cutover() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "before any mapped model invocation",
        "repository-owned executable dispatch is the only normal-selection authority",
        "only the returned exact Issue/role/action may determine the mapped model worker",
        "requested durable effects",
        "repository-owned application fresh-reauthorizes",
        "fresh global dispatch",
    ):
        assert required.lower() in shared.lower()


def test_fixed_role_slots_and_issue_comment_transition_commands_are_not_runtime_authority() -> None:
    shared = _normalized(AGENTS)
    for forbidden in (
        "fixed invocation role for the remainder of that run",
        "continue the target action under the fixed invocation role",
    ):
        assert forbidden not in shared
    for required in (
        "dynamic",
        "single scheduled wake",
        "Issue comments",
        "not",
        "authorization",
    ):
        assert required in shared


def test_shared_apply_boundary_owns_durable_messages_and_redispatch() -> None:
    messages = _normalized(MESSAGES)
    for required in (
        "Machine-gated worker/application boundary",
        "invocation-local output",
        "repository-owned application code",
        "fresh-reauthorizes",
        "fresh executable dispatch",
        "fresh mapped model invocation",
    ):
        assert required.lower() in messages.lower()


def test_lead_workers_consume_machine_identity_and_request_durable_effects() -> None:
    explore = _normalized(EXPLORE)
    change = _normalized(CHANGE)

    for required in (
        "Machine-gated runtime boundary",
        "MUST NOT run `workflow_dispatch.py`",
        "requested durable effect",
        "fresh mapped model invocation",
    ):
        assert required in explore

    for required in (
        "Machine-gated runtime boundary",
        "application-time effect boundary",
        "no durable GitHub write authority",
        "fresh mapped model invocation",
    ):
        assert required in change


def test_direct_propose_is_not_queue_eligible_without_executable_admission() -> None:
    preflight = _complete(
        RepositoryIssueSnapshot(
            issue_number=137,
            change="unset",
            routing=("lead", "propose-change"),
            created_order=1,
        )
    )

    decision = workflow_dispatch.classify_dispatch(preflight)

    assert decision.disposition == "NO_WORK"
    assert decision.preactivation_candidate_ids == ()


def test_dispatch_exposes_open_selection_and_structural_conflict_surfaces() -> None:
    assert hasattr(workflow_dispatch, "classify_open_dispatch")
    assert hasattr(workflow_dispatch, "StructuralConflictDisposition")
    assert hasattr(workflow_dispatch, "classify_structural_conflicts")


def test_terminal_retained_routing_is_structurally_clear_without_detailed_forensics(
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
        lambda repository, token: ((_terminal_124_payload(),),),
    )

    def structural_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        assert url.endswith("/issues/124/comments?per_page=100&page=1")
        return (_lifecycle_complete_124_comment(),)

    monkeypatch.setattr(runtime, "_github_get_list_page", structural_page)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("detailed closed-workflow forensics must not run for terminal history")

    monkeypatch.setattr(runtime, "_github_issue_comment_pages", forbidden)
    monkeypatch.setattr(runtime, "_legacy_terminal_evidence_from_checkout", forbidden)
    monkeypatch.setattr(runtime, "_github_issue", forbidden)

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )
    decision = workflow_dispatch.classify_dispatch(preflight)

    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 140
    assert decision.selected_routing == ("executor", "implement-change")
    assert all(item.state == "open" for item in preflight.issues)


def test_pre_dynamic_archive_merge_terminal_is_structurally_clear_without_archive_lookup(
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
        lambda repository, token: ((_legacy_terminal_21_payload(),),),
    )

    def structural_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        assert url.endswith("/issues/21/comments?per_page=100&page=1")
        return (_legacy_archive_merge_21_comment(),)

    monkeypatch.setattr(runtime, "_github_get_list_page", structural_page)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("proven legacy terminal history must not read archived Change")

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
    assert decision.selected_routing == ("executor", "implement-change")
    assert all(item.state == "open" for item in preflight.issues)


def test_pre_dynamic_archive_merge_marker_created_after_cutover_stays_nonclear(
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
        lambda repository, token: ((_legacy_terminal_21_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_get_list_page",
        lambda url, token: (
            _legacy_archive_merge_21_comment(created_at="2026-08-14T00:00:00Z"),
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

    assert archive_lookups == ["align-issue-completion-with-archive"]
    assert workflow_dispatch.classify_dispatch(preflight).disposition == "FAIL_CLOSED"


def test_pre_dynamic_completed_without_archive_merge_marker_stays_nonclear(
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
        lambda repository, token: ((_legacy_terminal_21_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_get_list_page",
        lambda url, token: (
            {
                "id": 1,
                "body": "not an archive merge terminal marker",
                "user": {"login": "royhsu-work"},
                "author_association": "OWNER",
                "created_at": "2026-08-12T23:51:35Z",
                "updated_at": "2026-08-12T23:51:35Z",
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

    assert archive_lookups == ["align-issue-completion-with-archive"]
    assert workflow_dispatch.classify_dispatch(preflight).disposition == "FAIL_CLOSED"


def test_closed_finalize_archive_without_completion_marker_stays_nonclear(
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
        lambda repository, token: ((_terminal_124_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_get_list_page",
        lambda url, token: (
            {
                "id": 1,
                "body": "not lifecycle complete",
                "user": {"login": "royhsu-work"},
                "author_association": "OWNER",
                "created_at": "2026-08-21T09:33:16Z",
                "updated_at": "2026-08-21T09:33:16Z",
            },
        ),
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
