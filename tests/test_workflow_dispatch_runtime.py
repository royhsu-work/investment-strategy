"""Runtime dispatch precondition regressions for #133."""

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
) -> RepositoryIssueSnapshot:
    return RepositoryIssueSnapshot(
        issue_number=number,
        change=change,
        routing=routing,
        state="open",
        created_order=created_order,
        current_state_provenance=provenance,
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
            issue(20, "unset", ("lead", "propose-change"), created_order=2),
            issue(19, "unset", ("lead", "explore-change"), created_order=1),
        )
    )
    assert decision.preactivation_candidate_ids == (19, 20)
    assert decision.selected_issue_id == 19
    assert decision.selected_routing == ("lead", "explore-change")


def test_propose_prewrite_requires_same_issue_authorization() -> None:
    preflight = complete(
        issue(19, "unset", ("lead", "explore-change"), created_order=1),
        issue(20, "unset", ("lead", "propose-change"), created_order=2),
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
