"""Executable workflow-dynamic dispatch preconditions.

This module is the stateless production owner for deterministic work selection.
Normal selection consumes current open-Issue facts plus the complete current set
of closed Issues that still carry workflow routing debt. Retired closed history
is outside normal selection; detailed recovery is candidate-bound.
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
TerminalEvidence = Literal["not-terminal", "terminal-history", "indeterminate"]
DebtDisposition = Literal["terminal-cleanup", "unfinished-recovery"]


class ObservationProvenance(StrEnum):
    """Whether authorization-bearing current fields are invocation-local GitHub facts."""

    QUALIFIED = "QUALIFIED"
    INDETERMINATE = "INDETERMINATE"


class StructuralConflictDisposition(StrEnum):
    """Compatibility enum for the retired broad closed-history screen."""

    CLEAR = "CLEAR"
    POSSIBLE_CONFLICT = "POSSIBLE_CONFLICT"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class RepositoryIssueSnapshot:
    """Normalized Issue facts consumed by production dispatch classifiers."""

    issue_number: int
    change: str
    routing: Routing | None
    state: Literal["open", "closed"] = "open"
    created_order: int = 0
    premature_close_recovery: RecoveryEvidence = "not-candidate"
    terminal_evidence: TerminalEvidence = "not-terminal"
    current_state_provenance: ObservationProvenance = ObservationProvenance.QUALIFIED
    preactivation_eligible: bool = False
    routing_debt: bool = False


@dataclass(frozen=True)
class EnumerationEvidence:
    """Completeness/provenance evidence for one bounded Issue acquisition."""

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
    selected_debt_disposition: DebtDisposition | None = None


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


def _validate_preflight(preflight: DispatchPreflight) -> DispatchDecision | None:
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
    return None


def _eligible_preactivation(issue: RepositoryIssueSnapshot) -> bool:
    if issue.change != "unset" or issue.state != "open":
        return False
    if issue.routing == ("lead", "explore-change"):
        return True
    if issue.routing == ("lead", "propose-change"):
        return issue.preactivation_eligible
    return False


def _is_routing_debt(issue: RepositoryIssueSnapshot) -> bool:
    """Treat full legacy tuples as debt while supporting explicit partial residue."""

    return issue.state == "closed" and (issue.routing_debt or issue.routing is not None)


def classify_open_dispatch(preflight: DispatchPreflight) -> DispatchDecision:
    """Select normal work from a complete provenance-qualified OPEN Issue snapshot.

    Direct-Propose admission is not re-derived here. Runtime must set
    ``preactivation_eligible`` only after consuming the canonical executable
    Human-authority predicate.
    """

    invalid = _validate_preflight(preflight)
    if invalid is not None:
        return invalid

    if any(issue.state != "open" for issue in preflight.issues):
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            reason="normal open-Issue classifier received closed Issue state",
        )

    formal_issues = tuple(
        issue for issue in preflight.issues if issue.change != "unset" and issue.routing is not None
    )
    formal_ids = tuple(sorted(issue.issue_number for issue in formal_issues))

    if len(formal_issues) > 1:
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            formal=formal_ids,
            reason="multiple open formal workflows",
        )
    if len(formal_issues) == 1:
        selected = formal_issues[0]
        return DispatchDecision(
            completeness="COMPLETE",
            observation_provenance=ObservationProvenance.QUALIFIED,
            formal_issue_ids=formal_ids,
            recovery_candidate_ids=(),
            preactivation_candidate_ids=(),
            selected_issue_id=selected.issue_number,
            selected_routing=selected.routing,
            disposition="AUTHORIZE",
            reason="sole open formal workflow with no current routing debt",
        )

    queued = tuple(
        sorted(
            (issue for issue in preflight.issues if _eligible_preactivation(issue)),
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
            reason="no open formal, eligible pre-activation work, or current routing debt",
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
        reason="deterministic eligible pre-activation winner",
    )


def classify_structural_conflicts(preflight: DispatchPreflight) -> StructuralConflictDisposition:
    """Compatibility classifier for callers that still project closed state.

    Any current closed workflow-routing residue is a possible conflict. Retired
    closed history with no routing residue is clear. Production normal dispatch
    no longer invokes this repository-history screen.
    """

    if not preflight.enumeration.complete:
        return StructuralConflictDisposition.INDETERMINATE
    if any(
        issue.current_state_provenance is not ObservationProvenance.QUALIFIED
        for issue in preflight.issues
    ):
        return StructuralConflictDisposition.INDETERMINATE

    for issue in preflight.issues:
        if issue.state != "closed":
            return StructuralConflictDisposition.INDETERMINATE
        if _is_routing_debt(issue):
            return StructuralConflictDisposition.POSSIBLE_CONFLICT
    return StructuralConflictDisposition.CLEAR


def _open_formal_issues(preflight: DispatchPreflight) -> tuple[RepositoryIssueSnapshot, ...]:
    return tuple(
        issue
        for issue in preflight.issues
        if issue.change != "unset" and issue.routing is not None and issue.state == "open"
    )


def _classify_exceptional_dispatch(preflight: DispatchPreflight) -> DispatchDecision:
    """Classify current closed-routing debt with candidate-bound recovery evidence."""

    invalid = _validate_preflight(preflight)
    if invalid is not None:
        return invalid

    formal_issues = _open_formal_issues(preflight)
    formal_ids = tuple(sorted(issue.issue_number for issue in formal_issues))
    if len(formal_issues) > 1:
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            formal=formal_ids,
            reason="multiple open formal workflows",
        )

    debt = tuple(issue for issue in preflight.issues if _is_routing_debt(issue))
    debt_ids = tuple(sorted(issue.issue_number for issue in debt))

    ambiguous = tuple(
        issue
        for issue in debt
        if issue.change == "unset"
        or issue.terminal_evidence == "indeterminate"
        or (
            issue.terminal_evidence != "terminal-history"
            and issue.premature_close_recovery == "indeterminate"
        )
    )
    if ambiguous:
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            formal=formal_ids,
            recovery=debt_ids,
            reason="closed routing debt evidence is ambiguous or contradictory",
        )

    terminal = tuple(issue for issue in debt if issue.terminal_evidence == "terminal-history")
    unfinished = tuple(
        issue
        for issue in debt
        if issue.terminal_evidence == "not-terminal"
        and issue.premature_close_recovery == "qualifying"
    )
    unresolved = tuple(issue for issue in debt if issue not in terminal and issue not in unfinished)
    if unresolved:
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            formal=formal_ids,
            recovery=debt_ids,
            reason="closed routing debt is not classified as terminal or unfinished",
        )

    if terminal:
        selected = min(terminal, key=lambda issue: issue.issue_number)
        return DispatchDecision(
            completeness="COMPLETE",
            observation_provenance=ObservationProvenance.QUALIFIED,
            formal_issue_ids=formal_ids,
            recovery_candidate_ids=debt_ids,
            preactivation_candidate_ids=(),
            selected_issue_id=selected.issue_number,
            selected_routing=("lead", "resolve-question"),
            disposition="AUTHORIZE",
            reason="deterministic terminal closed-routing-debt cleanup candidate",
            selected_debt_disposition="terminal-cleanup",
        )

    if unfinished and formal_issues:
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            formal=formal_ids,
            recovery=debt_ids,
            reason="unfinished closed routing debt conflicts with open formal workflow",
        )
    if len(unfinished) > 1:
        return _fail_closed(
            completeness="COMPLETE",
            provenance=ObservationProvenance.QUALIFIED,
            recovery=debt_ids,
            reason="multiple unfinished closed-routing recovery candidates",
        )
    if len(unfinished) == 1:
        selected = unfinished[0]
        return DispatchDecision(
            completeness="COMPLETE",
            observation_provenance=ObservationProvenance.QUALIFIED,
            formal_issue_ids=(),
            recovery_candidate_ids=debt_ids,
            preactivation_candidate_ids=(),
            selected_issue_id=selected.issue_number,
            selected_routing=("lead", "resolve-question"),
            disposition="AUTHORIZE",
            reason="sole unfinished closed-routing recovery candidate",
            selected_debt_disposition="unfinished-recovery",
        )

    open_preflight = DispatchPreflight(
        issues=tuple(issue for issue in preflight.issues if issue.state == "open"),
        enumeration=EnumerationEvidence(
            observed_count=sum(issue.state == "open" for issue in preflight.issues),
            source_total_count=sum(issue.state == "open" for issue in preflight.issues),
            incomplete_results=False,
            exhausted=True,
            observation_provenance=ObservationProvenance.QUALIFIED,
        ),
    )
    return classify_open_dispatch(open_preflight)


def classify_dispatch(preflight: DispatchPreflight) -> DispatchDecision:
    """Classify a final runtime preflight.

    Open-only preflights use normal selection. A preflight containing closed
    Issues represents the already-entered current routing-debt boundary.
    """

    if any(issue.state == "closed" for issue in preflight.issues):
        return _classify_exceptional_dispatch(preflight)
    return classify_open_dispatch(preflight)


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


def activation_prewrite_authorized(preflight: DispatchPreflight, issue_number: int) -> bool:
    """Authorize the exact Issue for the immediate Propose activation write."""

    return action_entry_authorized(preflight, issue_number, ("lead", "propose-change"))


def activation_postwrite_accepted(
    preflight: DispatchPreflight,
    *,
    issue_number: int,
    expected_change: str,
) -> bool:
    """Accept a Propose activation only from a fresh qualified post-write state."""

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


def activation_accepted(
    preflight: DispatchPreflight,
    *,
    issue_number: int,
    expected_change: str,
) -> bool:
    """Compatibility name for the post-write activation acceptance predicate."""

    return activation_postwrite_accepted(
        preflight,
        issue_number=issue_number,
        expected_change=expected_change,
    )
