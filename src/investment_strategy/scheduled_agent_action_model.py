"""Small executable Action model for the Scheduled-Agent shadow boundary.

This module contains mechanical workflow facts only. It does not perform GitHub
I/O, select a carrier, execute a worker, or persist a successor.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch
from types import MappingProxyType


class ActionModelError(ValueError):
    """Base error for invalid machine workflow inputs."""


class UnknownAction(ActionModelError):
    """Raised when an input is not in the finite Action vocabulary."""


class InvalidTransition(ActionModelError):
    """Raised when a typed result is not legal for the current Action."""


class InvalidTypedResult(ActionModelError):
    """Raised when a worker result is outside the bounded result envelope."""


class Role(StrEnum):
    LEAD = "lead"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"


class Action(StrEnum):
    EXPLORE_CHANGE = "explore-change"
    PROPOSE_CHANGE = "propose-change"
    RESOLVE_QUESTION = "resolve-question"
    FINALIZE_CHANGE = "finalize-change"
    FINALIZE_ARCHIVE = "finalize-archive"
    REVIEW_OPENSPEC = "review-openspec"
    REVIEW_IMPLEMENTATION = "review-implementation"
    REVIEW_ARCHIVE = "review-archive"
    IMPLEMENT_CHANGE = "implement-change"
    MERGE_IMPLEMENTATION_PR = "merge-implementation-pr"
    MERGE_ARCHIVE_PR = "merge-archive-pr"


class ResultKind(StrEnum):
    PROPOSAL_READY = "proposal-ready"
    RESEARCH_REQUIRED = "research-required"
    HUMAN_DECISION_REQUIRED = "human-decision-required"
    NO_CHANGE_REQUIRED = "no-change-required"
    NO_GO = "no-go"
    READY_FOR_OPENSPEC_REVIEW = "ready-for-openspec-review"
    FINDINGS = "findings"
    PASS = "pass"  # noqa: S105
    READY = "ready"
    SPEC_BLOCKER = "spec-blocker"
    MORE_IMPLEMENTATION_REQUIRED = "more-implementation-required"
    ARCHIVE_READY = "archive-ready"
    LIFECYCLE_COMPLETE = "lifecycle-complete"
    MERGED = "merged"
    LIFECYCLE_VIOLATION = "lifecycle-violation"
    BLOCKED = "blocked"


class IssueState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class SelectionDisposition(StrEnum):
    AUTHORIZE = "authorize"
    NO_WORK = "no-work"
    FAIL_CLOSED = "fail-closed"


class ObservationProvenance(StrEnum):
    QUALIFIED = "qualified"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class TypedResult:
    """Bounded worker result; it carries no target, successor, or retry authority."""

    kind: ResultKind
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ResultKind):
            raise InvalidTypedResult("result kind is not in the finite result vocabulary")
        if self.evidence_ref is not None and (
            not isinstance(self.evidence_ref, str)
            or not self.evidence_ref.strip()
            or any(character.isspace() for character in self.evidence_ref)
        ):
            raise InvalidTypedResult("result evidence reference is invalid")


@dataclass(frozen=True, slots=True)
class IssueObservation:
    """One fresh coordination-Issue observation supplied to deterministic selection."""

    issue_number: int
    state: IssueState | str
    change: str | None
    action: Action | str | None
    created_order: int = 0


@dataclass(frozen=True, slots=True)
class AuthoritativeObservations:
    """Complete, provenance-qualified observations consumed by select_work."""

    issues: tuple[IssueObservation, ...]
    complete: bool = True
    provenance: ObservationProvenance | str = ObservationProvenance.QUALIFIED


@dataclass(frozen=True, slots=True)
class SelectionDecision:
    """Deterministic selection outcome; no worker-provided authority is included."""

    disposition: SelectionDisposition
    issue_number: int | None
    action: Action | None
    role: Role | None
    reason: str


@dataclass(frozen=True, slots=True)
class EffectObservation:
    """Identity facts needed for exact application reauthorization."""

    issue_number: int
    observed_issue_number: int
    expected_change: str
    observed_change: str
    expected_action: Action | str
    observed_action: Action | str | None
    expected_revision: str
    observed_revision: str


ACTION_ROLE: Mapping[Action, Role] = MappingProxyType(
    {
        Action.EXPLORE_CHANGE: Role.LEAD,
        Action.PROPOSE_CHANGE: Role.LEAD,
        Action.RESOLVE_QUESTION: Role.LEAD,
        Action.FINALIZE_CHANGE: Role.LEAD,
        Action.FINALIZE_ARCHIVE: Role.LEAD,
        Action.REVIEW_OPENSPEC: Role.REVIEWER,
        Action.REVIEW_IMPLEMENTATION: Role.REVIEWER,
        Action.REVIEW_ARCHIVE: Role.REVIEWER,
        Action.IMPLEMENT_CHANGE: Role.EXECUTOR,
        Action.MERGE_IMPLEMENTATION_PR: Role.EXECUTOR,
        Action.MERGE_ARCHIVE_PR: Role.EXECUTOR,
    }
)


TRANSITIONS: Mapping[Action, Mapping[ResultKind, Action | None]] = MappingProxyType(
    {
        Action.EXPLORE_CHANGE: MappingProxyType(
            {
                ResultKind.PROPOSAL_READY: Action.PROPOSE_CHANGE,
                ResultKind.RESEARCH_REQUIRED: Action.EXPLORE_CHANGE,
                ResultKind.HUMAN_DECISION_REQUIRED: Action.RESOLVE_QUESTION,
                ResultKind.NO_CHANGE_REQUIRED: None,
                ResultKind.NO_GO: None,
                ResultKind.BLOCKED: Action.EXPLORE_CHANGE,
            }
        ),
        Action.PROPOSE_CHANGE: MappingProxyType(
            {
                ResultKind.READY_FOR_OPENSPEC_REVIEW: Action.REVIEW_OPENSPEC,
                ResultKind.RESEARCH_REQUIRED: Action.EXPLORE_CHANGE,
                ResultKind.HUMAN_DECISION_REQUIRED: Action.RESOLVE_QUESTION,
                ResultKind.NO_GO: None,
                ResultKind.BLOCKED: Action.PROPOSE_CHANGE,
            }
        ),
        Action.RESOLVE_QUESTION: MappingProxyType(
            {
                ResultKind.READY_FOR_OPENSPEC_REVIEW: Action.REVIEW_OPENSPEC,
                ResultKind.READY: Action.IMPLEMENT_CHANGE,
                ResultKind.RESEARCH_REQUIRED: Action.EXPLORE_CHANGE,
                ResultKind.HUMAN_DECISION_REQUIRED: Action.RESOLVE_QUESTION,
                ResultKind.NO_GO: None,
                ResultKind.BLOCKED: Action.RESOLVE_QUESTION,
            }
        ),
        Action.FINALIZE_CHANGE: MappingProxyType(
            {
                ResultKind.MORE_IMPLEMENTATION_REQUIRED: Action.IMPLEMENT_CHANGE,
                ResultKind.ARCHIVE_READY: Action.REVIEW_ARCHIVE,
                ResultKind.HUMAN_DECISION_REQUIRED: Action.FINALIZE_CHANGE,
                ResultKind.NO_GO: None,
                ResultKind.BLOCKED: Action.FINALIZE_CHANGE,
            }
        ),
        Action.FINALIZE_ARCHIVE: MappingProxyType(
            {
                ResultKind.LIFECYCLE_COMPLETE: None,
                ResultKind.HUMAN_DECISION_REQUIRED: Action.FINALIZE_ARCHIVE,
                ResultKind.BLOCKED: Action.FINALIZE_ARCHIVE,
            }
        ),
        Action.REVIEW_OPENSPEC: MappingProxyType(
            {
                ResultKind.PASS: Action.IMPLEMENT_CHANGE,
                ResultKind.FINDINGS: Action.RESOLVE_QUESTION,
                ResultKind.HUMAN_DECISION_REQUIRED: Action.RESOLVE_QUESTION,
                ResultKind.NO_GO: None,
                ResultKind.BLOCKED: Action.REVIEW_OPENSPEC,
            }
        ),
        Action.REVIEW_IMPLEMENTATION: MappingProxyType(
            {
                ResultKind.PASS: Action.MERGE_IMPLEMENTATION_PR,
                ResultKind.FINDINGS: Action.IMPLEMENT_CHANGE,
                ResultKind.SPEC_BLOCKER: Action.RESOLVE_QUESTION,
                ResultKind.HUMAN_DECISION_REQUIRED: Action.RESOLVE_QUESTION,
                ResultKind.BLOCKED: Action.REVIEW_IMPLEMENTATION,
            }
        ),
        Action.REVIEW_ARCHIVE: MappingProxyType(
            {
                ResultKind.PASS: Action.MERGE_ARCHIVE_PR,
                ResultKind.FINDINGS: Action.FINALIZE_CHANGE,
                ResultKind.HUMAN_DECISION_REQUIRED: Action.FINALIZE_CHANGE,
                ResultKind.NO_GO: None,
                ResultKind.BLOCKED: Action.REVIEW_ARCHIVE,
            }
        ),
        Action.IMPLEMENT_CHANGE: MappingProxyType(
            {
                ResultKind.READY: Action.REVIEW_IMPLEMENTATION,
                ResultKind.SPEC_BLOCKER: Action.RESOLVE_QUESTION,
                ResultKind.MORE_IMPLEMENTATION_REQUIRED: Action.IMPLEMENT_CHANGE,
                ResultKind.HUMAN_DECISION_REQUIRED: Action.RESOLVE_QUESTION,
                ResultKind.BLOCKED: Action.IMPLEMENT_CHANGE,
            }
        ),
        Action.MERGE_IMPLEMENTATION_PR: MappingProxyType(
            {
                ResultKind.MERGED: Action.FINALIZE_CHANGE,
                ResultKind.LIFECYCLE_VIOLATION: Action.RESOLVE_QUESTION,
                ResultKind.BLOCKED: Action.MERGE_IMPLEMENTATION_PR,
            }
        ),
        Action.MERGE_ARCHIVE_PR: MappingProxyType(
            {
                ResultKind.MERGED: Action.FINALIZE_ARCHIVE,
                ResultKind.LIFECYCLE_VIOLATION: Action.FINALIZE_CHANGE,
                ResultKind.BLOCKED: Action.MERGE_ARCHIVE_PR,
            }
        ),
    }
)


def _coerce_action(value: Action | str) -> Action:
    if isinstance(value, Action):
        return value
    if not isinstance(value, str):
        raise UnknownAction("action is not a string")
    try:
        return Action(value)
    except ValueError as exc:
        raise UnknownAction(f"unknown action: {value}") from exc


def role_for(action: Action | str) -> Role:
    """Derive semantic owner solely from the finite Action."""

    normalized = _coerce_action(action)
    return ACTION_ROLE[normalized]


def next_action(current_action: Action | str, result: TypedResult) -> Action | None:
    """Derive one legal successor or terminal state from a typed result."""

    if not isinstance(result, TypedResult):
        raise InvalidTypedResult("worker result is not a TypedResult")
    normalized = _coerce_action(current_action)
    transition = TRANSITIONS[normalized]
    try:
        return transition[result.kind]
    except KeyError as exc:
        raise InvalidTransition(
            f"result {result.kind.value} is not legal for {normalized.value}"
        ) from exc


def _selection(
    disposition: SelectionDisposition,
    reason: str,
    issue_number: int | None = None,
    action: Action | None = None,
) -> SelectionDecision:
    return SelectionDecision(
        disposition=disposition,
        issue_number=issue_number,
        action=action,
        role=None if action is None else role_for(action),
        reason=reason,
    )


def _is_unset_change(change: str | None) -> bool:
    return change is None or change == "unset"


def _valid_change(change: object) -> bool:
    return (
        isinstance(change, str)
        and bool(change)
        and change == change.strip()
        and change != "unset"
        and not any(character.isspace() for character in change)
    )


def _valid_revision(revision: object) -> bool:
    return isinstance(revision, str) and fullmatch(r"[0-9a-f]{40}", revision) is not None


def select_work(observations: AuthoritativeObservations) -> SelectionDecision:
    """Select one current Action from complete, qualified observations.

    Formal Change work has priority over pre-activation work. More than one
    formal active candidate is a WIP violation and fails closed. Preactivation
    candidates use a stable creation/order tie-break.
    """

    if not observations.complete or observations.provenance != ObservationProvenance.QUALIFIED:
        return _selection(SelectionDisposition.FAIL_CLOSED, "observations-unqualified")

    seen_issue_numbers: set[int] = set()
    formal: list[tuple[IssueObservation, Action]] = []
    preactivation: list[tuple[IssueObservation, Action]] = []

    for issue in observations.issues:
        if (
            not isinstance(issue.issue_number, int)
            or isinstance(issue.issue_number, bool)
            or issue.issue_number <= 0
            or issue.issue_number in seen_issue_numbers
        ):
            return _selection(SelectionDisposition.FAIL_CLOSED, "issue-identity-invalid")
        seen_issue_numbers.add(issue.issue_number)

        if issue.state not in {IssueState.OPEN, IssueState.CLOSED}:
            return _selection(SelectionDisposition.FAIL_CLOSED, "issue-state-invalid")
        if not _is_unset_change(issue.change) and not _valid_change(issue.change):
            return _selection(SelectionDisposition.FAIL_CLOSED, "change-identity-invalid")
        if not isinstance(issue.created_order, int) or isinstance(issue.created_order, bool):
            return _selection(SelectionDisposition.FAIL_CLOSED, "ordering-invalid")

        normalized_action: Action | None = None
        if issue.action is not None:
            try:
                normalized_action = _coerce_action(issue.action)
            except UnknownAction:
                return _selection(SelectionDisposition.FAIL_CLOSED, "action-invalid")

        if issue.state != IssueState.OPEN:
            continue

        has_change = not _is_unset_change(issue.change)
        if has_change and normalized_action is None:
            return _selection(SelectionDisposition.FAIL_CLOSED, "formal-action-missing")
        if not has_change and normalized_action not in {
            None,
            Action.EXPLORE_CHANGE,
            Action.PROPOSE_CHANGE,
        }:
            return _selection(SelectionDisposition.FAIL_CLOSED, "action-requires-change")

        if has_change and normalized_action is not None:
            formal.append((issue, normalized_action))
        elif normalized_action is not None:
            preactivation.append((issue, normalized_action))

    if len(formal) > 1:
        return _selection(SelectionDisposition.FAIL_CLOSED, "wip-more-than-one")
    if formal:
        issue, action = formal[0]
        return _selection(
            SelectionDisposition.AUTHORIZE,
            "selected-formal-action",
            issue.issue_number,
            action,
        )
    if preactivation:
        issue, action = min(
            preactivation,
            key=lambda candidate: (candidate[0].created_order, candidate[0].issue_number),
        )
        return _selection(
            SelectionDisposition.AUTHORIZE,
            "selected-preactivation-action",
            issue.issue_number,
            action,
        )
    return _selection(SelectionDisposition.NO_WORK, "no-routed-work")


def effect_is_current(observation: EffectObservation) -> bool:
    """Return true only when all exact reauthorization identities still match."""

    if (
        not isinstance(observation.issue_number, int)
        or isinstance(observation.issue_number, bool)
        or observation.issue_number <= 0
        or observation.observed_issue_number != observation.issue_number
        or not _valid_change(observation.expected_change)
        or observation.observed_change != observation.expected_change
        or not _valid_revision(observation.expected_revision)
        or observation.observed_revision != observation.expected_revision
    ):
        return False
    if observation.observed_action is None:
        return False
    try:
        expected_action = _coerce_action(observation.expected_action)
        observed_action = _coerce_action(observation.observed_action)
    except UnknownAction:
        return False
    return expected_action is observed_action
