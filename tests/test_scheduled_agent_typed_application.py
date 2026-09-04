"""Tests for the Action-only typed application and one-wake boundary."""

import json
from dataclasses import replace

import pytest

from investment_strategy.scheduled_agent_action_model import (
    Action,
    ActionApplicationDecision,
    ActionObservation,
    ActionSource,
    ApplicationDisposition,
    ApplicationRejectionKind,
    AuthoritativeObservations,
    BoundedActionResult,
    IssueObservation,
    ObservationProvenance,
    ResultKind,
    Role,
    TypedResult,
    authorize_one_wake,
    plan_action_application,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_worker import parse_worker_result


_REVISION = "a" * 40
_CHANGE = "simplify-scheduled-agent-control-plane"


def _source(action: Action = Action.IMPLEMENT_CHANGE) -> ActionSource:
    return ActionSource(
        issue_number=138,
        change=_CHANGE,
        action=action,
        authorization_revision=_REVISION,
    )


def _result(
    action: Action = Action.IMPLEMENT_CHANGE,
    kind: ResultKind = ResultKind.SPEC_BLOCKER,
    *,
    issue_number: int = 138,
    change: str = _CHANGE,
) -> BoundedActionResult:
    return BoundedActionResult(
        issue_number=issue_number,
        change=change,
        action=action,
        result=TypedResult(kind, evidence_ref="issuecomment-typed-result"),
    )


def _observation(
    action: Action | str | None = Action.IMPLEMENT_CHANGE,
    *,
    issue_number: int = 138,
    change: str = _CHANGE,
    revision: str = _REVISION,
    provenance: ObservationProvenance = ObservationProvenance.QUALIFIED,
    human_authorized: bool = True,
) -> ActionObservation:
    return ActionObservation(
        issue_number=issue_number,
        change=change,
        action=action,
        revision=revision,
        provenance=provenance,
        human_authorized=human_authorized,
    )


def test_one_wake_derives_role_from_selected_action() -> None:
    authorization = authorize_one_wake(
        AuthoritativeObservations(
            issues=(
                IssueObservation(
                    issue_number=138,
                    state="open",
                    change=_CHANGE,
                    action=Action.REVIEW_OPENSPEC,
                ),
            )
        )
    )

    assert authorization is not None
    assert authorization.issue_number == 138
    assert authorization.action is Action.REVIEW_OPENSPEC
    assert authorization.role is Role.REVIEWER
    assert set(authorization.__dataclass_fields__) == {"issue_number", "action", "role"}


def test_bounded_result_has_no_target_or_successor_authority() -> None:
    assert set(BoundedActionResult.__dataclass_fields__) == {
        "issue_number",
        "change",
        "action",
        "result",
    }


def test_typed_application_derives_unique_successor_without_execution() -> None:
    decision = plan_action_application(
        _source(),
        _result(),
        _observation(),
    )

    assert isinstance(decision, ActionApplicationDecision)
    assert decision.disposition is ApplicationDisposition.ACCEPT
    assert decision.accepted
    assert decision.successor is Action.RESOLVE_QUESTION
    assert decision.successor_role is Role.LEAD
    assert "execute_successor" not in decision.__dataclass_fields__


def test_same_role_successor_is_persisted_for_a_later_wake() -> None:
    decision = plan_action_application(
        _source(),
        _result(kind=ResultKind.MORE_IMPLEMENTATION_REQUIRED),
        _observation(),
    )

    assert decision.accepted
    assert decision.successor is Action.IMPLEMENT_CHANGE
    assert decision.successor_role is Role.EXECUTOR


def test_cross_role_successor_is_derived_without_role_input() -> None:
    source = _source(Action.REVIEW_IMPLEMENTATION)
    result = _result(Action.REVIEW_IMPLEMENTATION, ResultKind.PASS)
    decision = plan_action_application(
        source,
        result,
        _observation(Action.REVIEW_IMPLEMENTATION),
    )

    assert decision.accepted
    assert decision.successor is Action.MERGE_IMPLEMENTATION_PR
    assert decision.successor_role is Role.EXECUTOR


@pytest.mark.parametrize(
    ("field", "value", "classification"),
    [
        ("issue_number", 999, ApplicationRejectionKind.RESULT_ISSUE_MISMATCH),
        ("change", "other-change", ApplicationRejectionKind.RESULT_CHANGE_MISMATCH),
        ("action", Action.REVIEW_OPENSPEC, ApplicationRejectionKind.RESULT_ACTION_MISMATCH),
    ],
)
def test_result_identity_mismatch_fails_closed(
    field: str,
    value: object,
    classification: ApplicationRejectionKind,
) -> None:
    result = replace(_result(), **{field: value})
    decision = plan_action_application(_source(), result, _observation())

    assert not decision.accepted
    assert decision.rejection is not None
    assert decision.rejection.classification is classification
    assert decision.rejection.expected
    assert decision.rejection.observed


@pytest.mark.parametrize(
    ("observation", "classification"),
    [
        (
            _observation(issue_number=999),
            ApplicationRejectionKind.CURRENT_ISSUE_MISMATCH,
        ),
        (
            _observation(change="other-change"),
            ApplicationRejectionKind.CURRENT_CHANGE_MISMATCH,
        ),
        (
            _observation(action="review-openspec"),
            ApplicationRejectionKind.CURRENT_ACTION_MISMATCH,
        ),
        (
            _observation(revision="b" * 40),
            ApplicationRejectionKind.DEFAULT_BRANCH_REVISION_MISMATCH,
        ),
        (
            _observation(provenance=ObservationProvenance.INDETERMINATE),
            ApplicationRejectionKind.OBSERVATION_UNQUALIFIED,
        ),
        (
            _observation(human_authorized=False),
            ApplicationRejectionKind.HUMAN_AUTHORITY_MISSING,
        ),
    ],
)
def test_current_observation_mismatch_fails_closed(
    observation: ActionObservation,
    classification: ApplicationRejectionKind,
) -> None:
    decision = plan_action_application(_source(), _result(), observation)

    assert not decision.accepted
    assert decision.rejection is not None
    assert decision.rejection.classification is classification


def test_illegal_typed_transition_fails_closed() -> None:
    decision = plan_action_application(
        _source(),
        _result(kind=ResultKind.PASS),
        _observation(),
    )

    assert not decision.accepted
    assert decision.rejection is not None
    assert decision.rejection.classification is ApplicationRejectionKind.ILLEGAL_TRANSITION


def test_worker_parser_binds_optional_typed_result_to_authorized_source() -> None:
    raw = json.dumps(
        {
            "issue_number": 138,
            "role": "executor",
            "action": "implement-change",
            "change": _CHANGE,
            "result_kind": "spec-blocker",
            "evidence_ref": "issuecomment-typed-result",
            "explore_disposition": None,
            "propose_disposition": None,
            "result_content": "bounded typed result",
            "requested_effects": [],
        }
    )

    result = parse_worker_result(
        raw,
        WorkerRequest(138, "executor", "implement-change"),
    )

    assert result.typed_result is not None
    assert result.typed_result.issue_number == 138
    assert result.typed_result.change == _CHANGE
    assert result.typed_result.action is Action.IMPLEMENT_CHANGE
    assert result.typed_result.result.kind is ResultKind.SPEC_BLOCKER
