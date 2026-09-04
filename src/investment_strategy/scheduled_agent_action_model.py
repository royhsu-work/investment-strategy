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
class ActionSource:
    """Exact Issue/Change/Action authorization identity for one application."""

    issue_number: int
    change: str
    action: Action
    authorization_revision: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.issue_number, int)
            or isinstance(self.issue_number, bool)
            or self.issue_number <= 0
        ):
            raise ValueError("source Issue identity is invalid")
        if (
            not isinstance(self.change, str)
            or not self.change.strip()
            or any(character.isspace() for character in self.change)
        ):
            raise ValueError("source Change identity is invalid")
        if not isinstance(self.action, Action):
            raise UnknownAction("source Action identity is invalid")
        if not _valid_revision(self.authorization_revision):
            raise ValueError("source authorization revision is invalid")


@dataclass(frozen=True, slots=True)
class ActionObservation:
    """Fresh current-state facts used to reauthorize one Action result."""

    issue_number: int
    change: str
    action: Action | str | None
    revision: str
    provenance: ObservationProvenance | str = ObservationProvenance.QUALIFIED
    human_authorized: bool = True
    state: IssueState | str = IssueState.OPEN


@dataclass(frozen=True, slots=True)
class BoundedActionResult:
    """Typed result bound to one source identity without target authority."""

    issue_number: int
    change: str
    action: Action
    result: TypedResult

    def __post_init__(self) -> None:
        if (
            not isinstance(self.issue_number, int)
            or isinstance(self.issue_number, bool)
            or self.issue_number <= 0
        ):
            raise InvalidTypedResult("result Issue identity is invalid")
        if (
            not isinstance(self.change, str)
            or not self.change.strip()
            or any(character.isspace() for character in self.change)
        ):
            raise InvalidTypedResult("result Change identity is invalid")
        if not isinstance(self.action, Action):
            raise InvalidTypedResult("result Action identity is invalid")
        if not isinstance(self.result, TypedResult):
            raise InvalidTypedResult("result payload is not typed")


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
    human_authorized: bool = True


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


class ApplicationDisposition(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


class ApplicationRejectionKind(StrEnum):
    OBSERVATION_UNQUALIFIED = "observation-unqualified"
    HUMAN_AUTHORITY_MISSING = "human-authority-missing"
    RESULT_ISSUE_MISMATCH = "result-issue-mismatch"
    RESULT_CHANGE_MISMATCH = "result-change-mismatch"
    RESULT_ACTION_MISMATCH = "result-action-mismatch"
    CURRENT_ISSUE_MISMATCH = "current-issue-mismatch"
    CURRENT_CHANGE_MISMATCH = "current-change-mismatch"
    CURRENT_ACTION_INVALID = "current-action-invalid"
    CURRENT_ACTION_MISMATCH = "current-action-mismatch"
    CURRENT_STATE_INVALID = "current-state-invalid"
    DEFAULT_BRANCH_REVISION_MISMATCH = "default-branch-revision-mismatch"
    ILLEGAL_TRANSITION = "illegal-transition"


@dataclass(frozen=True, slots=True)
class ApplicationRejection:
    """Machine-readable failed guard with exact expected/observed evidence."""

    classification: ApplicationRejectionKind
    expected: str
    observed: str


@dataclass(frozen=True, slots=True)
class ActionApplicationDecision:
    """One typed application decision; successor execution is never included."""

    disposition: ApplicationDisposition
    source: ActionSource
    result: BoundedActionResult
    successor: Action | None
    successor_role: Role | None
    rejection: ApplicationRejection | None = None

    @property
    def accepted(self) -> bool:
        return self.disposition is ApplicationDisposition.ACCEPT


@dataclass(frozen=True, slots=True)
class ShadowDivergence:
    """Exact field-level evidence when shadow selection differs from observation."""

    field: str
    expected: str
    observed: str


@dataclass(frozen=True, slots=True)
class ShadowComparison:
    """No-mutation comparison between executable selection and observed selection."""

    expected: SelectionDecision
    observed: SelectionDecision | None
    divergences: tuple[ShadowDivergence, ...]

    @property
    def matches(self) -> bool:
        return not self.divergences


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

    if (
        not isinstance(observations.complete, bool)
        or not observations.complete
        or observations.provenance != ObservationProvenance.QUALIFIED
    ):
        return _selection(SelectionDisposition.FAIL_CLOSED, "observations-unqualified")
    if not isinstance(observations.human_authorized, bool) or not observations.human_authorized:
        return _selection(SelectionDisposition.FAIL_CLOSED, "human-authority-missing")

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


_DECISION_FIELDS = ("disposition", "issue_number", "action", "role")


def _decision_evidence(value: object) -> str:
    if isinstance(value, StrEnum):
        return value.value
    if value is None:
        return "null"
    return str(value)


def shadow_compare_selection(
    observations: AuthoritativeObservations,
    observed: SelectionDecision | None = None,
) -> ShadowComparison:
    """Compare pure selection with an observed decision without applying effects."""

    expected = select_work(observations)
    if observed is None:
        return ShadowComparison(expected=expected, observed=None, divergences=())

    divergences = tuple(
        ShadowDivergence(
            field=field,
            expected=_decision_evidence(getattr(expected, field)),
            observed=_decision_evidence(getattr(observed, field)),
        )
        for field in _DECISION_FIELDS
        if getattr(expected, field) != getattr(observed, field)
    )
    return ShadowComparison(
        expected=expected,
        observed=observed,
        divergences=divergences,
    )


@dataclass(frozen=True, slots=True)
class WakeAuthorization:
    """One fresh wake's selected Action and its derived semantic Role."""

    issue_number: int
    action: Action
    role: Role


def authorize_one_wake(
    observations: AuthoritativeObservations,
) -> WakeAuthorization | None:
    """Return one model-authorized Action or no work; never execute a successor."""

    decision = select_work(observations)
    if (
        decision.disposition is not SelectionDisposition.AUTHORIZE
        or decision.issue_number is None
        or decision.action is None
    ):
        return None
    return WakeAuthorization(
        issue_number=decision.issue_number,
        action=decision.action,
        role=role_for(decision.action),
    )


def _application_rejection(
    source: ActionSource,
    result: BoundedActionResult,
    classification: ApplicationRejectionKind,
    expected: object,
    observed: object,
) -> ActionApplicationDecision:
    return ActionApplicationDecision(
        disposition=ApplicationDisposition.REJECT,
        source=source,
        result=result,
        successor=None,
        successor_role=None,
        rejection=ApplicationRejection(
            classification=classification,
            expected=_decision_evidence(expected),
            observed=_decision_evidence(observed),
        ),
    )


def plan_action_application(
    source: ActionSource,
    result: BoundedActionResult,
    current: ActionObservation,
) -> ActionApplicationDecision:
    """Freshly reauthorize one typed result and derive at most one successor."""

    if current.provenance != ObservationProvenance.QUALIFIED:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.OBSERVATION_UNQUALIFIED,
            ObservationProvenance.QUALIFIED,
            current.provenance,
        )
    if current.human_authorized is not True:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.HUMAN_AUTHORITY_MISSING,
            True,
            current.human_authorized,
        )
    if result.issue_number != source.issue_number:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.RESULT_ISSUE_MISMATCH,
            source.issue_number,
            result.issue_number,
        )
    if result.change != source.change:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.RESULT_CHANGE_MISMATCH,
            source.change,
            result.change,
        )
    if result.action != source.action:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.RESULT_ACTION_MISMATCH,
            source.action,
            result.action,
        )
    if current.issue_number != source.issue_number:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.CURRENT_ISSUE_MISMATCH,
            source.issue_number,
            current.issue_number,
        )
    if current.change != source.change:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.CURRENT_CHANGE_MISMATCH,
            source.change,
            current.change,
        )
    if current.state != IssueState.OPEN:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.CURRENT_STATE_INVALID,
            IssueState.OPEN,
            current.state,
        )
    if current.action is None:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.CURRENT_ACTION_INVALID,
            source.action,
            None,
        )
    try:
        current_action = _coerce_action(current.action)
    except UnknownAction:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.CURRENT_ACTION_INVALID,
            source.action,
            current.action,
        )
    if current_action != source.action:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.CURRENT_ACTION_MISMATCH,
            source.action,
            current_action,
        )
    if current.revision != source.authorization_revision:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.DEFAULT_BRANCH_REVISION_MISMATCH,
            source.authorization_revision,
            current.revision,
        )
    try:
        successor = next_action(source.action, result.result)
    except InvalidTransition:
        return _application_rejection(
            source,
            result,
            ApplicationRejectionKind.ILLEGAL_TRANSITION,
            "legal-transition",
            result.result.kind,
        )
    return ActionApplicationDecision(
        disposition=ApplicationDisposition.ACCEPT,
        source=source,
        result=result,
        successor=successor,
        successor_role=None if successor is None else role_for(successor),
    )


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


_PRESENTATION_START = "<!-- BEGIN GENERATED ACTION MODEL -->"
_PRESENTATION_END = "<!-- END GENERATED ACTION MODEL -->"


def render_workflow_presentation() -> str:
    """Render the stable Human-readable projection of the executable model."""

    lines = [
        _PRESENTATION_START,
        "## Executable Action model (generated)",
        "",
        "### Action to Role",
        "| Action | Role |",
        "| --- | --- |",
    ]
    for action, role in ACTION_ROLE.items():
        lines.append(f"| `{action.value}` | `{role.value}` |")
    lines.extend(
        (
            "",
            "### Typed-result transitions",
            "| Current Action | Result | Successor |",
            "| --- | --- | --- |",
        )
    )
    for action in Action:
        for result, successor in TRANSITIONS[action].items():
            target = "terminal" if successor is None else successor.value
            lines.append(f"| `{action.value}` | `{result.value}` | `{target}` |")
    lines.append(_PRESENTATION_END)
    return "\n".join(lines) + "\n"
