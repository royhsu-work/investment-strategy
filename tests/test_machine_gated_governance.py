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
LEAD = ROOT / "agents" / "roles" / "lead.md"
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


def test_shared_governance_uses_current_routing_debt_not_structural_history_projection() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "complete current set of closed Issues",
        "closed-routing debt",
        "agent:*",
        "action:*",
        "mapped-Action boundary",
        "unrelated labels are preserved",
        "Lead / resolve-question",
    ):
        assert required.lower() in shared.lower()
    for forbidden in (
        "complete bounded structural closed-workflow conflict projection",
        "after structural `CLEAR`",
    ):
        assert forbidden.lower() not in shared.lower()


def test_lead_resolve_question_owns_exact_candidate_debt_disposition() -> None:
    lead = _normalized(LEAD)
    change = _normalized(CHANGE)

    for required in (
        "current closed-routing-debt boundary",
        "exact executable-selected candidate",
        "machine-derived debt disposition",
        "terminal-cleanup",
        "unfinished-recovery",
        "closed + no workflow routing",
    ):
        assert required.lower() in lead.lower()

    for required in (
        "Machine-selected closed-routing debt branch",
        "machine-derived debt disposition",
        "terminal-retirement",
        "terminal-cleanup",
        "unfinished-recovery",
        "exact selected closed-routing-debt candidate",
    ):
        assert required.lower() in change.lower()


def test_current_propose_is_queue_eligible_without_global_admission_state() -> None:
    preflight = _complete(
        RepositoryIssueSnapshot(
            issue_number=137,
            change="unset",
            routing=("lead", "propose-change"),
            created_order=1,
        )
    )

    decision = workflow_dispatch.classify_dispatch(preflight)

    assert decision.disposition == "AUTHORIZE"
    assert decision.preactivation_candidate_ids == (137,)
    assert decision.selected_issue_id == 137
    assert decision.selected_routing == ("lead", "propose-change")


def test_dispatch_exposes_open_selection_without_structural_history_contract() -> None:
    assert hasattr(workflow_dispatch, "classify_open_dispatch")
    debt = RepositoryIssueSnapshot(
        issue_number=124,
        change="require-ci-reobservation-before-async-exit",
        routing=("lead", "finalize-archive"),
        state="closed",
        routing_debt=True,
        terminal_evidence="terminal-history",
    )
    decision = workflow_dispatch.classify_dispatch(_complete(debt))
    assert decision.selected_debt_disposition == "terminal-cleanup"


def test_terminal_retained_routing_is_current_debt_and_preempts_open_formal(
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
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((_terminal_124_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: ((_lifecycle_complete_124_comment(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue",
        lambda repository, token, issue_number: _terminal_124_payload(),
    )

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )
    decision = workflow_dispatch.classify_dispatch(preflight)

    assert decision.disposition == "AUTHORIZE"
    assert decision.formal_issue_ids == (140,)
    assert decision.selected_issue_id == 124
    assert decision.selected_routing == ("lead", "resolve-question")
    assert decision.selected_debt_disposition == "terminal-cleanup"


def test_pre_dynamic_terminal_debt_uses_bounded_legacy_evidence_for_cleanup(
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
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((_legacy_terminal_21_payload(),),),
    )
    lookups: list[str] = []

    def legacy_terminal(change: str, *, repository_root: Path) -> str:
        del repository_root
        lookups.append(change)
        return "terminal-history"

    monkeypatch.setattr(runtime, "_legacy_terminal_evidence_from_checkout", legacy_terminal)

    decision = workflow_dispatch.classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )

    assert lookups == ["align-issue-completion-with-archive"]
    assert decision.selected_issue_id == 21
    assert decision.selected_routing == ("lead", "resolve-question")
    assert decision.selected_debt_disposition == "terminal-cleanup"


def test_pre_dynamic_indeterminate_terminal_debt_fails_closed(
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
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((_legacy_terminal_21_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_legacy_terminal_evidence_from_checkout",
        lambda change, *, repository_root: "indeterminate",
    )

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )

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
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((_terminal_124_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: ((),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue",
        lambda repository, token, issue_number: _terminal_124_payload(),
    )

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )

    assert workflow_dispatch.classify_dispatch(preflight).disposition == "FAIL_CLOSED"
    assert any(item.state == "closed" for item in preflight.issues)
