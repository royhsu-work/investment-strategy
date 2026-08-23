"""Observable dispatch-evidence regressions for the #133 live canary."""

from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    RuntimeTrigger,
    acquire_dispatch_preflight,
    authorize_worker_request,
    serialize_dispatch_evidence,
)


def test_dispatch_evidence_exposes_complete_acquisition_and_classifier_provenance() -> None:
    preflight = acquire_dispatch_preflight(
        observations=(
            GitHubIssueObservation(
                issue_number=133,
                change="enforce-runtime-dispatch-preconditions",
                routing=("executor", "implement-change"),
                state="open",
                created_order=1,
                authoritative=True,
            ),
        ),
        source_total_count=1,
        incomplete_results=False,
        exhausted=True,
    )
    request = authorize_worker_request(preflight, RuntimeTrigger())

    evidence = serialize_dispatch_evidence(request, preflight)

    assert evidence["completeness"] == "COMPLETE"
    assert evidence["observation_provenance"] == "QUALIFIED"
    assert evidence["enumeration"] == {
        "observed_count": 1,
        "source_total_count": 1,
        "incomplete_results": False,
        "exhausted": True,
        "observation_provenance": "QUALIFIED",
        "complete": True,
    }
    assert evidence["disposition"] == "AUTHORIZE"
    assert evidence["formal_issue_ids"] == (133,)
    assert evidence["selected_issue_id"] == 133
    assert evidence["selected_routing"] == ("executor", "implement-change")
