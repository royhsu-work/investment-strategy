"""Executable workflow-dynamic dispatch preconditions.

This module is a stateless adapter for the dispatch semantics owned by
``agents/AGENTS.md``. It deliberately performs no GitHub I/O and owns no
workflow state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

Role = Literal["lead", "reviewer", "executor"]
Action = Literal[
    "explore-change",
    "propose-change",
    "resolve-question",
    "finalize-change",
    "finalize-archive",
    "review-openspec",
    "review-implementation",
    "review-archive",
    "implement-change",
    "merge-pr",
]
Routing = tuple[Role, Action]
RecoveryEvidence = Literal["not-candidate", "qualifying", "indeterminate"]


class ObservationProvenance(StrEnum):
    """Whether authorization-bearing current fields are invocation-local GitHub facts."""

    QUALIFIED = "QUALIFIED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class RepositoryIssueSnapshot:
    """Normalized Issue facts consumed by the pure classifier."""

    issue_number: int
    change: str
    routing: Routing | None
    state: Literal["open", "closed"] = "open"
    created_order: int = 0
    premature_close_recovery: RecoveryEvidence = "not-candidate"
    current_state_provenance: ObservationProvenance = ObservationProvenance.QUALIFIED


@dataclass(frozen=True)
class EnumerationEvidence:
    """Completeness/provenance evidence for repository-wide Issue acquisition."""

    observed_count: int
    source_total_count: int | None
    incomplete_results: bool
    exhausted: bool
    observation_provenance: ObservationProvenance

    @property
    def complete(self) -> bool:
        return (
            self.observation_provenance is ObservationProvenance.QUALIFIED
            and not self.incomplete_results
            and self.exhausted
            and self.source_total_count is not None
            and self.observed_count == self.source_total_count
        )


@dataclass(frozen=True)
class DispatchPreflight:
    """Complete normalized input for one dispatch/precondition decision."""

    issues: tuple[RepositoryIssueSnapshot, ...]
    enumeration: EnumerationEvidence


@dataclass(frozen=True)
class DispatchDecision:
    """Structured authorization result shared by runtime and regressions."""

    completeness: Literal["COMPLETE", "INDETERMINATE"]
    observation_provenance: ObservationProvenance
    formal_issue_ids: tuple[int, ...]
    recovery_candidate_ids: tuple[int, ...]
    preactivation_candidate_ids: tuple[int, ...]
    selected_issue_id: int | None
    selected_routing: Routing | None
    disposition: Literal["AUTHORIZE", "FAIL_CLOSED", "NO_WORK"]
    reason: str


def _fail_closed(
    *,
    completeness: Literal["COMPLETE", "INDETERMINATE"],
    provenance: ObservationProvenance,
    formal: tuple[int, ...] = (),
    recovery: tuple[int, ...] = (),
    preactivation: tuple[int, ...] = (),
    reason: str,
) -> DispatchDecision:
    return DispatchDecision(
        completeness=completeness,
        observation_provenance=provenance,
        formal_issue_ids=formal,
        recovery_candidate_ids=recovery,
        preactivation_candidate_ids=preactivation,
        selected_issue_id=None,
        selected_routing=None,
        disposition="FAIL_CLOSED",
        reason=reason,
    )


def classify_dispatch(preflight: DispatchPreflight) -> DispatchDecision:
    """Classify one complete, provenance-qualified repository snapshot.

    Missing completeness or current-state provenance fails closed. Historical
    routing is intentionally not an input: callers must normalize only current
    GitHub state into ``routing``.
    """

    if not preflight.enumeration.complete:
        return _fail_closed(
            completeness="INDETERMINATE",
            provenance=preflight.enumeration.observation_provenance,
            reason="repository enumeration is incomplete or unqualified",
        )

    if any(
        issue.current_state_provenance is not ObservationProvenance.QUALIFIED
        for issue in preflight.issues
    ):
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.INDETERMINATE,
            reason="authorization-bearing current Issue state is unqualified",
        )

    formal_issues = tuple(
        issue
        for issue in preflight.issues
        if issue.change != "unset" and issue.routing is not None and issue.state == "open"
    )
    terminal_pending = tuple(
        issue
        for issue in preflight.issues
        if issue.change != "unset"
        and issue.routing == ("lead", "finalize-archive")
        and issue.state == "closed"
    )
    active = formal_issues + terminal_pending
    formal_ids = tuple(sorted(issue.issue_number for issue in active))

    if len(active) > 1:
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            formal=formal_ids,
            reason="multiple formal workflows",
        )
    if len(active) == 1:
        selected = active[0]
        return DispatchDecision(
            completeness="COMPLETE",
            observation_provenance=ObservationProvenance.QUALIFIED,
            formal_issue_ids=formal_ids,
            recovery_candidate_ids=(),
            preactivation_candidate_ids=(),
            selected_issue_id=selected.issue_number,
            selected_routing=selected.routing,
            disposition="AUTHORIZE",
            reason="sole formal workflow",
        )

    recovery_indeterminate = tuple(
        issue
        for issue in preflight.issues
        if issue.state == "closed"
        and issue.change != "unset"
        and issue.routing is not None
        and issue.routing != ("lead", "finalize-archive")
        and issue.premature_close_recovery == "indeterminate"
    )
    if recovery_indeterminate:
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            reason="premature-close recovery evidence is indeterminate",
        )

    recovery = tuple(
        issue
        for issue in preflight.issues
        if issue.state == "closed"
        and issue.change != "unset"
        and issue.routing is not None
        and issue.routing != ("lead", "finalize-archive")
        and issue.premature_close_recovery == "qualifying"
    )
    recovery_ids = tuple(sorted(issue.issue_number for issue in recovery))
    if len(recovery) > 1:
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            recovery=recovery_ids,
            reason="multiple premature-close recovery candidates",
        )
    if len(recovery) == 1:
        selected = recovery[0]
        return DispatchDecision(
            completeness="COMPLETE",
            observation_provenance=ObservationProvenance.QUALIFIED,
            formal_issue_ids=(),
            recovery_candidate_ids=recovery_ids,
            preactivation_candidate_ids=(),
            selected_issue_id=selected.issue_number,
            selected_routing=("lead", "resolve-question"),
            disposition="AUTHORIZE",
            reason="sole premature-close recovery candidate",
        )

    queued = tuple(
        sorted(
            (
                issue
                for issue in preflight.issues
                if issue.change == "unset"
                and issue.state == "open"
                and issue.routing in {("lead", "explore-change"), ("lead", "propose-change")}
            ),
            key=lambda issue: (issue.created_order, issue.issue_number),
        )
    )
    queued_ids = tuple(issue.issue_number for issue in queued)
    if not queued:
        return DispatchDecision(
            completeness="COMPLETE",
            observation_provenance=ObservationProvenance.QUALIFIED,
            formal_issue_ids=(),
            recovery_candidate_ids=(),
            preactivation_candidate_ids=(),
            selected_issue_id=None,
            selected_routing=None,
            disposition="NO_WORK",
            reason="no formal, recovery, or pre-activation work",
        )

    selected = queued[0]
    return DispatchDecision(
        completeness="COMPLETE",
        observation_provenance=ObservationProvenance.QUALIFIED,
        formal_issue_ids=(),
        recovery_candidate_ids=(),
        preactivation_candidate_ids=queued_ids,
        selected_issue_id=selected.issue_number,
        selected_routing=selected.routing,
        disposition="AUTHORIZE",
        reason="deterministic pre-activation winner",
    )


def action_entry_authorized(
    preflight: DispatchPreflight, issue_number: int, routing: Routing
) -> bool:
    """Return whether the executable decision authorizes this exact mapped action."""

    decision = classify_dispatch(preflight)
    return (
        decision.disposition == "AUTHORIZE"
        and decision.selected_issue_id == issue_number
        and decision.selected_routing == routing
    )


def activation_accepted(
    preflight: DispatchPreflight,
    *,
    issue_number: int,
    expected_change: str,
) -> bool:
    """Return whether a Propose activation is accepted after its durable write.

    The caller must supply a fresh post-write repository reconstruction. The
    activation is accepted only when the executable classifier authorizes the
    same Issue as the sole formal workflow, the current route remains Propose,
    the persisted Change identity matches the expected activation, and every
    authorization-bearing field remains provenance-qualified.
    """

    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.formal_issue_ids != (issue_number,)
        or decision.selected_issue_id != issue_number
        or decision.selected_routing != ("lead", "propose-change")
    ):
        return False

    matches = tuple(issue for issue in preflight.issues if issue.issue_number == issue_number)
    if len(matches) != 1:
        return False
    activated = matches[0]
    return (
        activated.state == "open"
        and activated.change == expected_change
        and activated.routing == ("lead", "propose-change")
        and activated.current_state_provenance is ObservationProvenance.QUALIFIED
    )
