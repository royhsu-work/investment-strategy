"""Machine-gated Scheduled Agent runtime acquisition and worker authorization.

This module is the smallest orchestration surface required by #133 Slice 4A. It
normalizes invocation-local authoritative GitHub observations into the pure
``workflow_dispatch`` classifier and constructs a worker request only from an
``AUTHORIZE`` decision. Trigger metadata is intentionally non-authoritative.

GitHub I/O itself remains outside this module; callers must pass observations
that were obtained during the current execution and explicitly state whether
the repository-wide enumeration was complete.
"""

from __future__ import annotations

from dataclasses import dataclass

from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RepositoryIssueSnapshot,
    Routing,
    classify_dispatch,
)


@dataclass(frozen=True)
class GitHubIssueObservation:
    """Invocation-local normalized GitHub Issue observation."""

    issue_number: int
    change: str
    routing: Routing | None
    state: str
    created_order: int
    authoritative: bool


@dataclass(frozen=True)
class RuntimeTrigger:
    """Non-authoritative wake metadata.

    Optional fields exist only so tests and manual wake adapters can prove that
    trigger values never override classifier-selected workflow identity.
    """

    requested_issue: int | None = None
    requested_role: str | None = None
    requested_action: str | None = None


@dataclass(frozen=True)
class WorkerRequest:
    """Exact machine-authorized mapped worker identity for one invocation."""

    issue_number: int
    role: str
    action: str


def acquire_dispatch_preflight(
    *,
    observations: tuple[GitHubIssueObservation, ...],
    source_total_count: int | None,
    incomplete_results: bool,
    exhausted: bool,
) -> DispatchPreflight:
    """Normalize current GitHub observations into the production preflight.

    Any unqualified observation is retained but marked indeterminate so the
    pure classifier fails closed rather than substituting history or cache.
    """

    issues = tuple(
        RepositoryIssueSnapshot(
            issue_number=observation.issue_number,
            change=observation.change,
            routing=observation.routing,
            state="open" if observation.state == "open" else "closed",
            created_order=observation.created_order,
            current_state_provenance=(
                ObservationProvenance.QUALIFIED
                if observation.authoritative
                else ObservationProvenance.INDETERMINATE
            ),
        )
        for observation in observations
    )
    return DispatchPreflight(
        issues=issues,
        enumeration=EnumerationEvidence(
            observed_count=len(observations),
            source_total_count=source_total_count,
            incomplete_results=incomplete_results,
            exhausted=exhausted,
            observation_provenance=(
                ObservationProvenance.QUALIFIED
                if all(observation.authoritative for observation in observations)
                else ObservationProvenance.INDETERMINATE
            ),
        ),
    )


def authorize_worker_request(
    preflight: DispatchPreflight,
    trigger: RuntimeTrigger,
) -> WorkerRequest | None:
    """Construct one exact worker request only from classifier authorization."""

    del trigger
    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id is None
        or decision.selected_routing is None
    ):
        return None

    role, action = decision.selected_routing
    return WorkerRequest(
        issue_number=decision.selected_issue_id,
        role=role,
        action=action,
    )
