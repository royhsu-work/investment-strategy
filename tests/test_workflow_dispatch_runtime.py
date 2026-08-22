"""Runtime dispatch precondition regressions for #133."""

from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RepositoryIssueSnapshot,
    classify_dispatch,
)


def issue(
    number: int,
    change: str,
    routing: tuple[str, str] | None,
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
    decision = classify_dispatch(
        complete(
            issue(100, "complete-required-followup-materialization", ("lead", "finalize-change")),
            issue(130, "unset", ("lead", "explore-change"), created_order=1),
        )
    )
    assert decision.formal_issue_ids == (100,)
    assert decision.selected_issue_id == 100
    assert decision.disposition == "AUTHORIZE"


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
