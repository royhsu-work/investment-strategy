"""Executable Action-only dispatch for the Scheduled-Agent control plane.

This module owns the small deterministic selection boundary. Role is derived
from Action; GitHub transport, semantic workers, and durable mutation live in
separate modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from investment_strategy.scheduled_agent_action_model import (
    Action as ModelAction,
    AuthoritativeObservations,
    IssueObservation,
    ObservationProvenance as ModelObservationProvenance,
    SelectionDecision,
    SelectionDisposition as ModelSelectionDisposition,
    select_work,
    shadow_compare_selection,
    role_for,
)

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
    "merge-implementation-pr",
    "merge-archive-pr",
]
Routing = tuple[Role, Action]


class ObservationProvenance(StrEnum):
    """Whether authorization-bearing observations are complete and qualified."""

    QUALIFIED = "QUALIFIED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class RepositoryIssueSnapshot:
    """Fresh Issue facts; routing is a derived compatibility view of Action."""

    issue_number: int
    change: str
    routing: Routing | None
    state: Literal["open", "closed"] = "open"
    created_order: int = 0
    current_state_provenance: ObservationProvenance = ObservationProvenance.QUALIFIED


@dataclass(frozen=True)
class EnumerationEvidence:
    """Completeness and provenance for one Issue enumeration."""

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
    """Complete current-state input for one Action selection."""

    issues: tuple[RepositoryIssueSnapshot, ...]
    enumeration: EnumerationEvidence
    human_authorized: bool = True


@dataclass(frozen=True)
class DispatchDecision:
    """Machine decision; no worker, successor, or retry authority."""

    completeness: Literal["COMPLETE", "INDETERMINATE"]
    observation_provenance: ObservationProvenance
    formal_issue_ids: tuple[int, ...]
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
    preactivation: tuple[int, ...] = (),
    reason: str,
) -> DispatchDecision:
    return DispatchDecision(
        completeness=completeness,
        observation_provenance=provenance,
        formal_issue_ids=formal,
        preactivation_candidate_ids=preactivation,
        selected_issue_id=None,
        selected_routing=None,
        disposition="FAIL_CLOSED",
        reason=reason,
    )


def _model_observations(preflight: DispatchPreflight) -> AuthoritativeObservations:
    provenance = ModelObservationProvenance.QUALIFIED
    if (
        preflight.enumeration.observation_provenance is not ObservationProvenance.QUALIFIED
        or any(
            issue.current_state_provenance is not ObservationProvenance.QUALIFIED
            for issue in preflight.issues
        )
    ):
        provenance = ModelObservationProvenance.INDETERMINATE

    return AuthoritativeObservations(
        issues=tuple(
            IssueObservation(
                issue_number=issue.issue_number,
                state=issue.state,
                change=issue.change,
                action=None if issue.routing is None else issue.routing[1],
                created_order=issue.created_order,
            )
            for issue in preflight.issues
        ),
        complete=preflight.enumeration.complete,
        provenance=provenance,
        human_authorized=preflight.human_authorized,
    )


def _decision_metadata(
    observations: AuthoritativeObservations,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    formal = tuple(
        sorted(
            issue.issue_number
            for issue in observations.issues
            if issue.state == "open" and issue.change not in {None, "unset"}
        )
    )
    preactivation = tuple(
        sorted(
            issue.issue_number
            for issue in observations.issues
            if issue.state == "open"
            and issue.change in {None, "unset"}
            and issue.action in {ModelAction.EXPLORE_CHANGE, ModelAction.PROPOSE_CHANGE}
        )
    )
    return formal, preactivation


def _public_provenance(
    preflight: DispatchPreflight,
    observations: AuthoritativeObservations,
) -> ObservationProvenance:
    if observations.provenance is ModelObservationProvenance.INDETERMINATE:
        return ObservationProvenance.INDETERMINATE
    return preflight.enumeration.observation_provenance


def classify_dispatch(preflight: DispatchPreflight) -> DispatchDecision:
    """Select exactly one current Action from the executable model."""

    observations = _model_observations(preflight)
    selected = select_work(observations)
    formal, preactivation = _decision_metadata(observations)
    completeness: Literal["COMPLETE", "INDETERMINATE"] = (
        "COMPLETE" if preflight.enumeration.complete else "INDETERMINATE"
    )
    provenance = _public_provenance(preflight, observations)

    if selected.disposition is ModelSelectionDisposition.AUTHORIZE:
        if selected.issue_number is None or selected.action is None or selected.role is None:
            return _fail_closed(
                completeness=completeness,
                provenance=provenance,
                formal=formal,
                preactivation=preactivation,
                reason="action-model-authorize-identity-incomplete",
            )
        return DispatchDecision(
            completeness=completeness,
            observation_provenance=provenance,
            formal_issue_ids=formal,
            preactivation_candidate_ids=preactivation,
            selected_issue_id=selected.issue_number,
            selected_routing=(selected.role.value, selected.action.value),
            disposition="AUTHORIZE",
            reason=selected.reason,
        )

    if selected.disposition is ModelSelectionDisposition.NO_WORK:
        return DispatchDecision(
            completeness=completeness,
            observation_provenance=provenance,
            formal_issue_ids=formal,
            preactivation_candidate_ids=preactivation,
            selected_issue_id=None,
            selected_routing=None,
            disposition="NO_WORK",
            reason=selected.reason,
        )

    return _fail_closed(
        completeness=completeness,
        provenance=provenance,
        formal=formal,
        preactivation=preactivation,
        reason=selected.reason,
    )


def action_model_shadow(preflight: DispatchPreflight):
    """Compare the production decision with the same pure executable model."""

    observations = _model_observations(preflight)
    expected = select_work(observations)
    observed = SelectionDecision(
        disposition=expected.disposition,
        issue_number=expected.issue_number,
        action=expected.action,
        role=expected.role,
        reason=expected.reason,
    )
    return shadow_compare_selection(observations, observed)


def action_entry_authorized(
    preflight: DispatchPreflight,
    issue_number: int,
    routing: Routing,
) -> bool:
    """Return whether the exact Action entry is currently authorized."""

    decision = classify_dispatch(preflight)
    if decision.disposition != "AUTHORIZE" or decision.selected_issue_id != issue_number:
        return False
    if decision.selected_routing != routing:
        return False
    try:
        return role_for(routing[1]).value == routing[0]
    except ValueError:
        return False


def activation_prewrite_authorized(
    preflight: DispatchPreflight,
    issue_number: int,
) -> bool:
    """Authorize the exact pre-activation Propose action."""

    return action_entry_authorized(preflight, issue_number, ("lead", "propose-change"))


def activation_postwrite_accepted(
    preflight: DispatchPreflight,
    *,
    issue_number: int,
    expected_change: str,
) -> bool:
    """Accept a fresh immutable Change activation postcondition."""

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
    """Compatibility name for the activation postcondition."""

    return activation_postwrite_accepted(
        preflight,
        issue_number=issue_number,
        expected_change=expected_change,
    )
