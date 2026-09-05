from dataclasses import replace
from pathlib import Path

import pytest

from investment_strategy.scheduled_agent_action_model import (
    ACTION_ROLE,
    Action,
    AuthoritativeObservations,
    EffectObservation,
    InvalidTransition,
    InvalidTypedResult,
    IssueObservation,
    ObservationProvenance,
    ResultKind,
    Role,
    SelectionDisposition,
    ShadowComparison,
    ShadowDivergence,
    TypedResult,
    effect_is_current,
    next_action,
    render_workflow_presentation,
    role_for,
    select_work,
    shadow_compare_selection,
)


def test_action_vocabulary_derives_roles_and_rejects_generic_merge() -> None:
    assert set(ACTION_ROLE) == set(Action)
    assert role_for(Action.REVIEW_OPENSPEC) is Role.REVIEWER
    assert role_for("merge-archive-pr") is Role.EXECUTOR
    with pytest.raises(ValueError):
        role_for("merge-pr")


@pytest.mark.parametrize(
    ("current", "result", "successor"),
    [
        (
            Action.IMPLEMENT_CHANGE,
            ResultKind.SPEC_BLOCKER,
            Action.RESOLVE_QUESTION,
        ),
        (
            Action.FINALIZE_CHANGE,
            ResultKind.SPEC_BLOCKER,
            Action.RESOLVE_QUESTION,
        ),
        (
            Action.RESOLVE_QUESTION,
            ResultKind.LIFECYCLE_READY,
            Action.FINALIZE_CHANGE,
        ),
        (
            Action.REVIEW_OPENSPEC,
            ResultKind.PASS,
            Action.IMPLEMENT_CHANGE,
        ),
        (
            Action.REVIEW_IMPLEMENTATION,
            ResultKind.PASS,
            Action.MERGE_IMPLEMENTATION_PR,
        ),
        (
            Action.REVIEW_ARCHIVE,
            ResultKind.PASS,
            Action.MERGE_ARCHIVE_PR,
        ),
        (
            Action.MERGE_IMPLEMENTATION_PR,
            ResultKind.MERGED,
            Action.FINALIZE_CHANGE,
        ),
        (
            Action.MERGE_ARCHIVE_PR,
            ResultKind.MERGED,
            Action.FINALIZE_ARCHIVE,
        ),
        (Action.FINALIZE_ARCHIVE, ResultKind.LIFECYCLE_COMPLETE, None),
    ],
)
def test_next_action_is_a_single_deterministic_transition(
    current: Action,
    result: ResultKind,
    successor: Action | None,
) -> None:
    assert next_action(current, TypedResult(result)) is successor


def test_invalid_transition_fails_closed() -> None:
    with pytest.raises(InvalidTransition):
        next_action(Action.IMPLEMENT_CHANGE, TypedResult(ResultKind.PASS))


@pytest.mark.parametrize(
    ("current", "result"),
    [
        (Action.FINALIZE_CHANGE, ResultKind.LIFECYCLE_READY),
        (Action.RESOLVE_QUESTION, ResultKind.SPEC_BLOCKER),
    ],
)
def test_unrelated_lifecycle_results_remain_illegal(current: Action, result: ResultKind) -> None:
    with pytest.raises(InvalidTransition):
        next_action(current, TypedResult(result))


def test_typed_result_has_no_successor_or_target_authority() -> None:
    assert set(TypedResult.__dataclass_fields__) == {"kind", "evidence_ref"}
    with pytest.raises(InvalidTypedResult):
        TypedResult("pass")  # type: ignore[arg-type]


def test_select_work_derives_role_from_one_formal_action() -> None:
    decision = select_work(
        AuthoritativeObservations(
            issues=(
                IssueObservation(
                    issue_number=138,
                    state="open",
                    change="simplify-scheduled-agent-control-plane",
                    action=Action.REVIEW_OPENSPEC,
                ),
            )
        )
    )
    assert decision.disposition is SelectionDisposition.AUTHORIZE
    assert decision.issue_number == 138
    assert decision.action is Action.REVIEW_OPENSPEC
    assert decision.role is Role.REVIEWER


def test_select_work_uses_deterministic_preactivation_order() -> None:
    decision = select_work(
        AuthoritativeObservations(
            issues=(
                IssueObservation(12, "open", None, Action.EXPLORE_CHANGE, 2),
                IssueObservation(11, "open", "unset", Action.PROPOSE_CHANGE, 1),
            )
        )
    )
    assert decision.issue_number == 11
    assert decision.action is Action.PROPOSE_CHANGE
    assert decision.role is Role.LEAD


@pytest.mark.parametrize(
    "observations",
    [
        AuthoritativeObservations(
            issues=(
                IssueObservation(1, "open", "first", Action.IMPLEMENT_CHANGE),
                IssueObservation(2, "open", "second", Action.IMPLEMENT_CHANGE),
            )
        ),
        AuthoritativeObservations(issues=(IssueObservation(1, "open", "active", None),)),
        AuthoritativeObservations(
            issues=(IssueObservation(1, "open", None, Action.REVIEW_OPENSPEC),)
        ),
        AuthoritativeObservations(
            issues=(IssueObservation(1, "open", "active", "action:not-real"),)
        ),
        AuthoritativeObservations(
            issues=(IssueObservation(1, "open", "active", Action.IMPLEMENT_CHANGE),),
            complete=False,
        ),
        AuthoritativeObservations(
            issues=(IssueObservation(1, "open", "active", Action.IMPLEMENT_CHANGE),),
            provenance=ObservationProvenance.INDETERMINATE,
        ),
    ],
)
def test_selection_fails_closed_for_ambiguous_or_unqualified_state(
    observations: AuthoritativeObservations,
) -> None:
    decision = select_work(observations)
    assert decision.disposition is SelectionDisposition.FAIL_CLOSED
    assert decision.issue_number is None
    assert decision.action is None
    assert decision.role is None


def test_select_work_returns_no_work_for_unrouted_issues() -> None:
    decision = select_work(
        AuthoritativeObservations(
            issues=(
                IssueObservation(1, "open", None, None),
                IssueObservation(2, "closed", None, None),
            )
        )
    )
    assert decision.disposition is SelectionDisposition.NO_WORK
    assert decision.reason == "no-routed-work"


def test_effect_identity_guard_rejects_stale_revision_or_action() -> None:
    revision = "a" * 40
    current = EffectObservation(
        issue_number=138,
        observed_issue_number=138,
        expected_change="simplify-scheduled-agent-control-plane",
        observed_change="simplify-scheduled-agent-control-plane",
        expected_action=Action.IMPLEMENT_CHANGE,
        observed_action=Action.IMPLEMENT_CHANGE,
        expected_revision=revision,
        observed_revision=revision,
    )
    assert effect_is_current(current)
    assert not effect_is_current(replace(current, observed_revision="b" * 40))
    assert not effect_is_current(replace(current, observed_action=Action.RESOLVE_QUESTION))


def test_workflow_presentation_is_exactly_model_generated() -> None:
    workflow = Path("agents/workflow.md").read_text(encoding="utf-8")
    start_marker = "<!-- BEGIN GENERATED ACTION MODEL -->"
    end_marker = "<!-- END GENERATED ACTION MODEL -->"
    start = workflow.index(start_marker)
    end = workflow.index(end_marker, start) + len(end_marker)
    observed = workflow[start:end] + "\n"
    assert observed == render_workflow_presentation()


@pytest.mark.parametrize(
    ("observations", "expected_disposition", "expected_reason"),
    [
        (
            AuthoritativeObservations(
                issues=(IssueObservation(1, "open", "active", Action.IMPLEMENT_CHANGE),)
            ),
            SelectionDisposition.AUTHORIZE,
            "selected-formal-action",
        ),
        (
            AuthoritativeObservations(
                issues=(
                    IssueObservation(12, "open", None, Action.EXPLORE_CHANGE, 2),
                    IssueObservation(11, "open", "unset", Action.PROPOSE_CHANGE, 1),
                )
            ),
            SelectionDisposition.AUTHORIZE,
            "selected-preactivation-action",
        ),
        (
            AuthoritativeObservations(
                issues=(
                    IssueObservation(
                        1,
                        "closed",
                        "closed-debt",
                        Action.IMPLEMENT_CHANGE,
                        routing_debt=True,
                    ),
                ),
            ),
            SelectionDisposition.FAIL_CLOSED,
            "closed-routing-debt",
        ),
        (
            AuthoritativeObservations(
                issues=(IssueObservation(1, "open", "stale", Action.IMPLEMENT_CHANGE),),
                complete=False,
            ),
            SelectionDisposition.FAIL_CLOSED,
            "observations-unqualified",
        ),
        (
            AuthoritativeObservations(
                issues=(
                    IssueObservation(1, "open", "replay", Action.IMPLEMENT_CHANGE),
                    IssueObservation(1, "open", "replay", Action.IMPLEMENT_CHANGE),
                )
            ),
            SelectionDisposition.FAIL_CLOSED,
            "issue-identity-invalid",
        ),
        (
            AuthoritativeObservations(
                issues=(
                    IssueObservation(1, "open", "first", Action.IMPLEMENT_CHANGE),
                    IssueObservation(2, "open", "second", Action.REVIEW_OPENSPEC),
                )
            ),
            SelectionDisposition.FAIL_CLOSED,
            "wip-more-than-one",
        ),
    ],
)
def test_shadow_comparison_covers_current_selection_cases(
    observations: AuthoritativeObservations,
    expected_disposition: SelectionDisposition,
    expected_reason: str,
) -> None:
    expected = select_work(observations)
    comparison = shadow_compare_selection(observations, expected)
    assert isinstance(comparison, ShadowComparison)
    assert comparison.matches
    assert comparison.divergences == ()
    assert comparison.expected.disposition is expected_disposition
    assert comparison.expected.reason == expected_reason


def test_shadow_comparison_preserves_exact_divergence_evidence() -> None:
    observations = AuthoritativeObservations(
        issues=(IssueObservation(1, "open", "active", Action.IMPLEMENT_CHANGE),)
    )
    expected = select_work(observations)
    observed = replace(expected, issue_number=999)

    comparison = shadow_compare_selection(observations, observed)

    assert not comparison.matches
    assert comparison.divergences == (ShadowDivergence("issue_number", "1", "999"),)
    assert comparison.expected == expected
    assert comparison.observed == observed


def test_selection_enforces_human_authority_and_finish_first() -> None:
    observations = AuthoritativeObservations(
        issues=(
            IssueObservation(1, "open", "active", Action.IMPLEMENT_CHANGE),
            IssueObservation(2, "open", None, Action.EXPLORE_CHANGE, 1),
        )
    )
    assert select_work(observations).issue_number == 1
    assert select_work(replace(observations, human_authorized=False)).disposition is (
        SelectionDisposition.FAIL_CLOSED
    )


# Connector-carried exact-head replay remains application-authorized.
