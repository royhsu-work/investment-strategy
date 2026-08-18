from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

HUMAN_ACTOR = "royhsu-work"
APPROVAL_LABEL = "human:approved"
INTAKE_APPROVAL_LABEL = "intake:approved"
DECISION_REF_PREFIX = "Human-Decision-For: "
EXPLORE_ADMISSION_PREFIX = "Admission: "
EXPLORE_ADMISSION_DECLARATION = "Admission: Lead / explore-change"
CHANGE_PREFIX = "Change: "
CHANGE_UNSET_DECLARATION = "Change: unset"
EXPLORE_AGENT_LABEL = "agent:lead"
EXPLORE_ACTION_LABEL = "action:explore-change"


class HumanDecisionBoundary(StrEnum):
    EXPLORE_ADMISSION = "explore-admission"
    PROPOSE_ADMISSION = "propose-admission"
    ADVISORY_ADMISSION = "advisory-admission"
    ESCALATION_RESPONSE = "escalation-response"


@dataclass(frozen=True)
class DecisionComment:
    id: int
    created_at: datetime
    updated_at: datetime
    author: str
    body: str
    provenance_available: bool
    performed_via_github_app: str | None


@dataclass(frozen=True)
class LabelEvent:
    id: int
    created_at: datetime
    actor: str
    label: str
    provenance_available: bool
    performed_via_github_app: str | None


@dataclass(frozen=True)
class IssueCreation:
    id: int
    created_at: datetime
    updated_at: datetime
    author: str
    body: str
    provenance_available: bool
    performed_via_github_app: str | None


def explore_admission_ref(issue_number: int) -> str:
    return f"issue:{_positive_id(issue_number, 'issue_number')}:admission:lead:explore-change"


def propose_admission_ref(issue_number: int) -> str:
    return f"issue:{_positive_id(issue_number, 'issue_number')}:admission:lead:propose-change"


def advisory_admission_ref(issue_number: int) -> str:
    return f"issue:{_positive_id(issue_number, 'issue_number')}:advisory-admission"


def escalation_response_ref(comment_id: int) -> str:
    return f"issuecomment:{_positive_id(comment_id, 'comment_id')}"


def decision_ref_for_boundary(
    boundary: HumanDecisionBoundary | str,
    *,
    issue_number: int | None = None,
    escalation_comment_id: int | None = None,
) -> str:
    try:
        boundary = HumanDecisionBoundary(boundary)
    except ValueError as exc:
        raise ValueError("unmapped Human-reserved boundary") from exc

    if boundary is HumanDecisionBoundary.EXPLORE_ADMISSION:
        return explore_admission_ref(_required_id(issue_number, "issue_number"))
    if boundary is HumanDecisionBoundary.PROPOSE_ADMISSION:
        return propose_admission_ref(_required_id(issue_number, "issue_number"))
    if boundary is HumanDecisionBoundary.ADVISORY_ADMISSION:
        return advisory_admission_ref(_required_id(issue_number, "issue_number"))
    if boundary is HumanDecisionBoundary.ESCALATION_RESPONSE:
        return escalation_response_ref(_required_id(escalation_comment_id, "escalation_comment_id"))
    raise AssertionError("all HumanDecisionBoundary members must be mapped")


def _required_id(value: int | None, field: str) -> int:
    if value is None:
        raise ValueError(f"{field} is required for this Human-reserved boundary")
    return _positive_id(value, field)


def _positive_id(value: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _timestamp(value: object, field: str) -> datetime:
    raw = _string(value, field)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc


def _raw_app_provenance(raw: Mapping[str, object]) -> tuple[bool, str | None]:
    if "performed_via_github_app" not in raw:
        return False, None
    app = raw["performed_via_github_app"]
    return True, None if app is None else "github_app"


def decision_comment_from_raw(raw: Mapping[str, object]) -> DecisionComment:
    user = _mapping(raw.get("user"), "user")
    provenance_available, app = _raw_app_provenance(raw)
    return DecisionComment(
        id=_integer(raw.get("id"), "id"),
        created_at=_timestamp(raw.get("created_at"), "created_at"),
        updated_at=_timestamp(raw.get("updated_at"), "updated_at"),
        author=_string(user.get("login"), "user.login"),
        body=_string(raw.get("body"), "body"),
        provenance_available=provenance_available,
        performed_via_github_app=app,
    )


def label_event_from_raw(raw: Mapping[str, object]) -> LabelEvent:
    if raw.get("event") != "labeled":
        raise ValueError("only labeled events can establish approval authority")
    actor = _mapping(raw.get("actor"), "actor")
    label = _mapping(raw.get("label"), "label")
    provenance_available, app = _raw_app_provenance(raw)
    return LabelEvent(
        id=_integer(raw.get("id"), "id"),
        created_at=_timestamp(raw.get("created_at"), "created_at"),
        actor=_string(actor.get("login"), "actor.login"),
        label=_string(label.get("name"), "label.name"),
        provenance_available=provenance_available,
        performed_via_github_app=app,
    )


def issue_creation_from_raw(raw: Mapping[str, object]) -> IssueCreation:
    user = _mapping(raw.get("user"), "user")
    provenance_available, app = _raw_app_provenance(raw)
    return IssueCreation(
        id=_integer(raw.get("id"), "id"),
        created_at=_timestamp(raw.get("created_at"), "created_at"),
        updated_at=_timestamp(raw.get("updated_at"), "updated_at"),
        author=_string(user.get("login"), "user.login"),
        body=_string(raw.get("body"), "body"),
        provenance_available=provenance_available,
        performed_via_github_app=app,
    )


def parse_decision_ref(body: str) -> str | None:
    refs = [
        line.removeprefix(DECISION_REF_PREFIX).strip()
        for line in body.splitlines()
        if line.startswith(DECISION_REF_PREFIX)
    ]
    if len(refs) != 1 or not refs[0]:
        return None
    return refs[0]


def _has_exact_explore_creation_declaration(body: str) -> bool:
    admission_lines = [
        line.strip() for line in body.splitlines() if line.startswith(EXPLORE_ADMISSION_PREFIX)
    ]
    change_lines = [line.strip() for line in body.splitlines() if line.startswith(CHANGE_PREFIX)]
    return admission_lines == [EXPLORE_ADMISSION_DECLARATION] and change_lines == [
        CHANGE_UNSET_DECLARATION
    ]


def _creation_declaration_history_is_reconstructable(creation: IssueCreation) -> bool:
    """Conservatively prove the current body is still the raw creation-time body.

    GitHub's normal Issue object exposes the current body but not historical body revisions. Until a
    stronger immutable creation-history surface is supplied, any post-creation Issue update makes the
    creation-bound shortcut non-qualifying. This intentionally prefers a false negative plus the existing
    Human-decision fallback over trusting a caller assertion about mutation history.
    """
    return creation.updated_at == creation.created_at


def _is_human_provenance(
    actor: str,
    provenance_available: bool,
    performed_via_github_app: str | None,
) -> bool:
    return actor == HUMAN_ACTOR and provenance_available and performed_via_github_app is None


def is_human_created_explore_admission(
    *,
    creation: IssueCreation,
    current_agent_label: str,
    current_action_label: str,
) -> bool:
    """Evaluate only the narrow initial Human-created Formal Explore admission path."""
    return (
        _creation_declaration_history_is_reconstructable(creation)
        and current_agent_label == EXPLORE_AGENT_LABEL
        and current_action_label == EXPLORE_ACTION_LABEL
        and _is_human_provenance(
            creation.author,
            creation.provenance_available,
            creation.performed_via_github_app,
        )
        and _has_exact_explore_creation_declaration(creation.body)
    )


def _qualifying_comments(comments: tuple[DecisionComment, ...]) -> tuple[DecisionComment, ...]:
    return tuple(
        comment
        for comment in comments
        if _is_human_provenance(
            comment.author,
            comment.provenance_available,
            comment.performed_via_github_app,
        )
        and parse_decision_ref(comment.body) is not None
    )


def is_human_decision_approved(
    *,
    expected_ref: str,
    approval_label_present: bool,
    comments: tuple[DecisionComment, ...],
    label_events: tuple[LabelEvent, ...],
) -> bool:
    """Evaluate provenance-bound Human authority without persistent approval state."""
    if not expected_ref or not approval_label_present:
        return False

    qualifying_comments = _qualifying_comments(comments)
    expected_comments = tuple(
        comment
        for comment in qualifying_comments
        if parse_decision_ref(comment.body) == expected_ref
    )
    if not expected_comments:
        return False

    latest_expected = max(expected_comments, key=lambda item: (item.created_at, item.id))
    qualifying_events = tuple(
        event
        for event in label_events
        if event.label == APPROVAL_LABEL
        and _is_human_provenance(
            event.actor,
            event.provenance_available,
            event.performed_via_github_app,
        )
    )

    for event in sorted(
        qualifying_events,
        key=lambda item: (item.created_at, item.id),
        reverse=True,
    ):
        candidates = tuple(
            comment for comment in qualifying_comments if comment.created_at < event.created_at
        )
        if not candidates:
            continue
        bound = max(candidates, key=lambda item: (item.created_at, item.id))
        if parse_decision_ref(bound.body) != expected_ref:
            continue
        if bound != latest_expected:
            continue
        if bound.updated_at > event.created_at:
            continue
        return True

    return False


def is_human_explore_admission_approved(
    *,
    issue_number: int,
    creation: IssueCreation,
    current_agent_label: str,
    current_action_label: str,
    approval_label_present: bool,
    comments: tuple[DecisionComment, ...],
    label_events: tuple[LabelEvent, ...],
) -> bool:
    """Initial Explore admission accepts creation-bound proof or the existing general proof."""
    if is_human_created_explore_admission(
        creation=creation,
        current_agent_label=current_agent_label,
        current_action_label=current_action_label,
    ):
        return True
    return is_human_decision_approved(
        expected_ref=explore_admission_ref(issue_number),
        approval_label_present=approval_label_present,
        comments=comments,
        label_events=label_events,
    )


def is_human_advisory_admission_approved(
    *,
    issue_number: int,
    intake_approval_label_present: bool,
    human_approval_label_present: bool,
    comments: tuple[DecisionComment, ...],
    label_events: tuple[LabelEvent, ...],
) -> bool:
    """Advisory admission needs both the distinct intake capability and Human proof."""
    if not intake_approval_label_present:
        return False
    return is_human_decision_approved(
        expected_ref=advisory_admission_ref(issue_number),
        approval_label_present=human_approval_label_present,
        comments=comments,
        label_events=label_events,
    )
