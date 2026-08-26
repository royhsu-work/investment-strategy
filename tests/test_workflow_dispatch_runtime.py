"""Runtime dispatch precondition regressions."""

from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_runtime as runtime
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    RuntimeTrigger,
    acquire_dispatch_preflight,
    authorize_worker_request,
)
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RepositoryIssueSnapshot,
    Routing,
    action_entry_authorized,
    activation_accepted,
    classify_dispatch,
)


def issue(
    number: int,
    change: str,
    routing: Routing | None,
    *,
    created_order: int = 0,
    provenance: ObservationProvenance = ObservationProvenance.QUALIFIED,
    preactivation_eligible: bool = False,
) -> RepositoryIssueSnapshot:
    return RepositoryIssueSnapshot(
        issue_number=number,
        change=change,
        routing=routing,
        state="open",
        created_order=created_order,
        current_state_provenance=provenance,
        preactivation_eligible=preactivation_eligible,
    )


def complete(*issues: RepositoryIssueSnapshot) -> DispatchPreflight:
    return DispatchPreflight(
        issues=issues,
        enumeration=EnumerationEvidence(
            observed_count=len(issues),
            source_total_count=len(issues),
            incomplete_results=False,
            exhausted=True,
            observation_provenance=ObservationProvenance.QUALIFIED,
        ),
    )


def observation(number: int, change: str, routing: Routing | None) -> GitHubIssueObservation:
    return GitHubIssueObservation(
        issue_number=number,
        change=change,
        routing=routing,
        state="open",
        created_order=number,
        authoritative=True,
    )


def test_active_workflow_blocks_queued_explore() -> None:
    preflight = complete(
        issue(100, "complete-required-followup-materialization", ("lead", "finalize-change")),
        issue(130, "unset", ("lead", "explore-change"), created_order=1),
    )
    decision = classify_dispatch(preflight)
    assert decision.formal_issue_ids == (100,)
    assert decision.selected_issue_id == 100
    assert decision.disposition == "AUTHORIZE"
    assert not action_entry_authorized(preflight, 130, ("lead", "explore-change"))


def test_named_100_130_recurrence_cannot_enter_explore() -> None:
    preflight = complete(
        issue(100, "complete-required-followup-materialization", ("lead", "finalize-change")),
        issue(130, "unset", ("lead", "explore-change"), created_order=130),
    )
    assert not action_entry_authorized(preflight, 130, ("lead", "explore-change"))


def test_explore_rejects_different_winner_and_stale_routing() -> None:
    different_winner = complete(
        issue(19, "unset", ("lead", "explore-change"), created_order=1),
        issue(20, "unset", ("lead", "explore-change"), created_order=2),
    )
    assert not action_entry_authorized(different_winner, 20, ("lead", "explore-change"))
    assert not action_entry_authorized(different_winner, 19, ("lead", "propose-change"))


def test_explore_rejects_indeterminate_current_routing_provenance() -> None:
    preflight = complete(
        issue(
            130,
            "unset",
            ("lead", "explore-change"),
            provenance=ObservationProvenance.INDETERMINATE,
        )
    )
    assert not action_entry_authorized(preflight, 130, ("lead", "explore-change"))


def test_removed_current_routing_is_not_restored_from_history() -> None:
    decision = classify_dispatch(
        complete(
            issue(130, "bound-ci-observation-by-execution-opportunity", None),
            issue(133, "enforce-runtime-dispatch-preconditions", ("executor", "implement-change")),
        )
    )
    assert decision.formal_issue_ids == (133,)
    assert decision.selected_issue_id == 133


def test_unqualified_current_state_fails_closed() -> None:
    decision = classify_dispatch(
        complete(
            issue(
                130,
                "bound-ci-observation-by-execution-opportunity",
                ("lead", "resolve-question"),
                provenance=ObservationProvenance.INDETERMINATE,
            )
        )
    )
    assert decision.disposition == "FAIL_CLOSED"
    assert decision.observation_provenance == ObservationProvenance.INDETERMINATE


def test_incomplete_enumeration_fails_closed() -> None:
    preflight = DispatchPreflight(
        issues=(issue(133, "unset", ("lead", "explore-change")),),
        enumeration=EnumerationEvidence(
            observed_count=1,
            source_total_count=2,
            incomplete_results=False,
            exhausted=False,
            observation_provenance=ObservationProvenance.QUALIFIED,
        ),
    )
    decision = classify_dispatch(preflight)
    assert decision.completeness == "INDETERMINATE"
    assert decision.disposition == "FAIL_CLOSED"
    assert not action_entry_authorized(preflight, 133, ("lead", "explore-change"))


def test_zero_formal_work_selects_oldest_preactivation_candidate() -> None:
    decision = classify_dispatch(
        complete(
            issue(
                20,
                "unset",
                ("lead", "propose-change"),
                created_order=2,
                preactivation_eligible=True,
            ),
            issue(19, "unset", ("lead", "explore-change"), created_order=1),
        )
    )
    assert decision.preactivation_candidate_ids == (19, 20)
    assert decision.selected_issue_id == 19
    assert decision.selected_routing == ("lead", "explore-change")


def test_propose_prewrite_requires_same_issue_authorization() -> None:
    preflight = complete(
        issue(19, "unset", ("lead", "explore-change"), created_order=1),
        issue(
            20,
            "unset",
            ("lead", "propose-change"),
            created_order=2,
            preactivation_eligible=True,
        ),
    )
    assert not action_entry_authorized(preflight, 20, ("lead", "propose-change"))


def test_postwrite_activation_is_accepted_only_for_expected_sole_formal_issue() -> None:
    postwrite = complete(
        issue(133, "enforce-runtime-dispatch-preconditions", ("lead", "propose-change"))
    )
    assert activation_accepted(
        postwrite,
        issue_number=133,
        expected_change="enforce-runtime-dispatch-preconditions",
    )


def test_postwrite_multiple_active_has_no_accepted_activation() -> None:
    postwrite = complete(
        issue(100, "complete-required-followup-materialization", ("lead", "finalize-change")),
        issue(133, "enforce-runtime-dispatch-preconditions", ("lead", "propose-change")),
    )
    assert not activation_accepted(
        postwrite,
        issue_number=133,
        expected_change="enforce-runtime-dispatch-preconditions",
    )


def test_postwrite_provenance_incomplete_has_no_accepted_activation() -> None:
    postwrite = complete(
        issue(
            133,
            "enforce-runtime-dispatch-preconditions",
            ("lead", "propose-change"),
            provenance=ObservationProvenance.INDETERMINATE,
        )
    )
    assert not activation_accepted(
        postwrite,
        issue_number=133,
        expected_change="enforce-runtime-dispatch-preconditions",
    )


def test_postwrite_wrong_change_has_no_accepted_activation() -> None:
    postwrite = complete(issue(133, "other-change", ("lead", "propose-change")))
    assert not activation_accepted(
        postwrite,
        issue_number=133,
        expected_change="enforce-runtime-dispatch-preconditions",
    )


def test_runtime_acquisition_requires_complete_authoritative_observations() -> None:
    preflight = acquire_dispatch_preflight(
        observations=(
            observation(
                133,
                "enforce-runtime-dispatch-preconditions",
                ("executor", "implement-change"),
            ),
        ),
        source_total_count=2,
        incomplete_results=False,
        exhausted=False,
    )
    assert classify_dispatch(preflight).disposition == "FAIL_CLOSED"


def test_runtime_does_not_construct_worker_request_for_fail_closed_or_no_work() -> None:
    incomplete = acquire_dispatch_preflight(
        observations=(
            observation(
                133,
                "enforce-runtime-dispatch-preconditions",
                ("executor", "implement-change"),
            ),
        ),
        source_total_count=2,
        incomplete_results=False,
        exhausted=False,
    )
    assert authorize_worker_request(incomplete, RuntimeTrigger()) is None

    no_work = acquire_dispatch_preflight(
        observations=(),
        source_total_count=0,
        incomplete_results=False,
        exhausted=True,
    )
    assert authorize_worker_request(no_work, RuntimeTrigger()) is None


def test_one_wake_uses_classifier_selected_issue_role_action_not_trigger_metadata() -> None:
    preflight = acquire_dispatch_preflight(
        observations=(
            observation(
                133,
                "enforce-runtime-dispatch-preconditions",
                ("executor", "implement-change"),
            ),
        ),
        source_total_count=1,
        incomplete_results=False,
        exhausted=True,
    )
    request = authorize_worker_request(
        preflight,
        RuntimeTrigger(
            requested_issue=137,
            requested_role="lead",
            requested_action="explore-change",
        ),
    )
    assert request is not None
    assert (request.issue_number, request.role, request.action) == (
        133,
        "executor",
        "implement-change",
    )


def test_runtime_100_130_recurrence_invokes_only_current_formal_work() -> None:
    preflight = acquire_dispatch_preflight(
        observations=(
            observation(
                100,
                "complete-required-followup-materialization",
                ("lead", "finalize-change"),
            ),
            observation(130, "unset", ("lead", "explore-change")),
        ),
        source_total_count=2,
        incomplete_results=False,
        exhausted=True,
    )
    request = authorize_worker_request(preflight, RuntimeTrigger())
    assert request is not None
    assert (request.issue_number, request.role, request.action) == (100, "lead", "finalize-change")


def test_runtime_does_not_invoke_second_propose_while_formal_wip_exists() -> None:
    preflight = acquire_dispatch_preflight(
        observations=(
            observation(
                100,
                "complete-required-followup-materialization",
                ("lead", "finalize-change"),
            ),
            observation(137, "unset", ("lead", "propose-change")),
        ),
        source_total_count=2,
        incomplete_results=False,
        exhausted=True,
    )
    request = authorize_worker_request(preflight, RuntimeTrigger())
    assert request is not None
    assert request.issue_number == 100


def _queued_propose_payload(
    number: int = 158,
    *,
    created_at: str = "2026-08-25T17:46:32Z",
) -> dict[str, object]:
    return {
        "number": number,
        "state": "open",
        "body": "Change: unset",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:propose-change"},
        ],
        "created_at": created_at,
        "closed_at": None,
    }


def _queued_explore_payload(
    number: int = 159,
    *,
    created_at: str = "2026-08-25T18:54:19Z",
) -> dict[str, object]:
    return {
        "number": number,
        "state": "open",
        "body": "Change: unset",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:explore-change"},
        ],
        "created_at": created_at,
        "closed_at": None,
    }


def _explore_action_result_comment(
    *,
    issue_number: int = 158,
    result: str = "PROPOSAL_READY",
    actor: str = "github-actions[bot]",
    author_association: str = "NONE",
) -> dict[str, object]:
    return {
        "id": 5422771356,
        "body": (
            "## ACTION_RESULT\n\n"
            f"Workflow: #{issue_number}\n"
            "Change: `unset`\n"
            "Action: `Lead / explore-change`\n"
            f"Result: `{result}`\n"
            "Revision: `8be1f1dd9168b0db1301297d70b0c1e47a1e111f`"
        ),
        "user": {"login": actor},
        "author_association": author_association,
        "created_at": "2026-08-26T08:39:28Z",
        "updated_at": "2026-08-26T08:39:28Z",
    }


def test_explore_originated_propose_is_eligible_without_direct_human_admission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    successor = _queued_propose_payload()
    later_explore = _queued_explore_payload()
    proposal_ready = _explore_action_result_comment()

    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((successor, later_explore),),
    )
    monkeypatch.setattr(runtime, "_github_closed_routing_issue_pages", lambda repository, token: ())
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: (
            ((proposal_ready,),) if issue_number == 158 else ((),)
        ),
    )

    def forbidden_events(*args: object, **kwargs: object) -> object:
        raise AssertionError("Explore-originated Propose must not require Human admission events")

    monkeypatch.setattr(runtime, "_github_issue_event_pages", forbidden_events)

    decision = classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )
    assert decision.disposition == "AUTHORIZE"
    assert decision.preactivation_candidate_ids == (158, 159)
    assert decision.selected_issue_id == 158
    assert decision.selected_routing == ("lead", "propose-change")


def test_untrusted_explore_result_does_not_qualify_propose_successor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    successor = _queued_propose_payload()
    later_explore = _queued_explore_payload()
    untrusted = _explore_action_result_comment(actor="untrusted-user")

    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((successor, later_explore),),
    )
    monkeypatch.setattr(runtime, "_github_closed_routing_issue_pages", lambda repository, token: ())
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: ((untrusted,),) if issue_number == 158 else ((),),
    )

    decision = classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )
    assert decision.disposition == "AUTHORIZE"
    assert decision.preactivation_candidate_ids == (159,)
    assert decision.selected_issue_id == 159
    assert decision.selected_routing == ("lead", "explore-change")


def _closed_routed_issue_payload(*, state_reason: str = "completed") -> dict[str, object]:
    return {
        "number": 133,
        "state": "closed",
        "state_reason": state_reason,
        "body": "Change: enforce-runtime-dispatch-preconditions",
        "labels": [
            {"name": "agent:executor"},
            {"name": "action:implement-change"},
        ],
        "created_at": "2026-08-21T17:21:27Z",
        "closed_at": "2026-08-23T12:14:54Z",
    }


def _queued_140_payload() -> dict[str, object]:
    return {
        "number": 140,
        "state": "open",
        "body": "Change: unset",
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:explore-change"},
        ],
        "created_at": "2026-08-23T11:39:39Z",
        "closed_at": None,
    }


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


def _retirement_comment(*, app: object | None = None) -> dict[str, object]:
    return {
        "id": 5385902831,
        "body": (
            "Human administrative retirement: abandon Change "
            "enforce-runtime-dispatch-preconditions. Do not recover or resume #133. "
            "Remaining runtime-enforcement work is superseded by #140."
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": "2026-08-23T12:05:21Z",
        "updated_at": "2026-08-23T12:05:21Z",
        "performed_via_github_app": app,
    }


def _closed_terminal_research_payload() -> dict[str, object]:
    return {
        "number": 141,
        "state": "closed",
        "state_reason": "completed",
        "body": "Change: unset",
        "labels": [{"name": "action:explore-change"}],
        "created_at": "2026-08-25T14:00:00Z",
        "closed_at": "2026-08-25T14:30:00Z",
    }


def _terminal_research_comment(result: str = "NO_CHANGE_REQUIRED") -> dict[str, object]:
    return {
        "id": 5412000000,
        "body": (
            "## ACTION_RESULT\n\n"
            "Workflow: #141\n"
            "Change: `unset`\n"
            "Action: `Lead / explore-change`\n"
            f"Result: `{result}`\n"
            "Revision: `00a0e5a2c8068077faf5d18980e4a6f84f72f74e`"
        ),
        "user": {"login": "github-actions[bot]"},
        "author_association": "NONE",
        "created_at": "2026-08-25T14:29:00Z",
        "updated_at": "2026-08-25T14:29:00Z",
    }


def test_interrupted_terminal_research_debt_routes_candidate_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "openspec" / "changes").mkdir(parents=True)
    debt = _closed_terminal_research_payload()
    comments = ((_terminal_research_comment(),),)

    monkeypatch.setattr(runtime, "_github_open_issue_pages", lambda repository, token: ())
    monkeypatch.setattr(
        runtime,
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((debt,),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: comments if issue_number == 141 else (),
    )
    monkeypatch.setattr(runtime, "_github_issue", lambda repository, token, issue_number: debt)

    decision = classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 141
    assert decision.selected_routing == ("lead", "resolve-question")
    assert decision.selected_debt_disposition == "terminal-cleanup"


def test_sole_formal_with_no_current_routing_debt_skips_detailed_forensics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((_formal_140_payload(),),),
    )
    monkeypatch.setattr(runtime, "_github_closed_routing_issue_pages", lambda repository, token: ())

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("retired closed history must not trigger detailed forensics")

    monkeypatch.setattr(runtime, "_github_issue_comment_pages", forbidden)
    monkeypatch.setattr(runtime, "_legacy_terminal_evidence_from_checkout", forbidden)
    monkeypatch.setattr(runtime, "_github_issue", forbidden)

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )
    decision = classify_dispatch(preflight)
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 140
    assert decision.selected_routing == ("executor", "implement-change")
    assert all(item.state == "open" for item in preflight.issues)


def test_sole_formal_current_routing_debt_enters_candidate_bound_detailed_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    debt = _closed_routed_issue_payload()
    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((_formal_140_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((debt,),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: ((),),
    )
    monkeypatch.setattr(runtime, "_github_issue", lambda repository, token, issue_number: debt)

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )
    assert classify_dispatch(preflight).disposition == "FAIL_CLOSED"
    assert any(item.state == "closed" for item in preflight.issues)


def test_human_retirement_routes_exact_closed_debt_candidate_for_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "openspec" / "changes").mkdir(parents=True)
    debt = _closed_routed_issue_payload(state_reason="not_planned")
    comments = ((_retirement_comment(),),)

    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((_queued_140_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((debt,),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: comments if issue_number == 133 else (),
    )
    monkeypatch.setattr(runtime, "_github_issue", lambda repository, token, issue_number: debt)

    decision = classify_dispatch(
        runtime.acquire_current_github_preflight(
            "royhsu-work/investment-strategy",
            "token",
            repository_root=tmp_path,
        )
    )
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 133
    assert decision.selected_routing == ("lead", "resolve-question")
    assert decision.selected_debt_disposition == "terminal-cleanup"


def test_app_authored_retirement_does_not_release_closed_routing_debt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "openspec" / "changes").mkdir(parents=True)
    debt = _closed_routed_issue_payload(state_reason="not_planned")
    comments = ((_retirement_comment(app={"id": 1144995}),),)

    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((_queued_140_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_closed_routing_issue_pages",
        lambda repository, token: ((debt,),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_issue_comment_pages",
        lambda repository, token, issue_number: comments if issue_number == 133 else (),
    )
    monkeypatch.setattr(runtime, "_github_issue", lambda repository, token, issue_number: debt)

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )
    assert classify_dispatch(preflight).disposition == "FAIL_CLOSED"
