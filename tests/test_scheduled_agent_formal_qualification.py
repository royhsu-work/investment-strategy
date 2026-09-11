from __future__ import annotations

from investment_strategy.scheduled_agent_formal_qualification import (
    QualificationDecision,
    build_qualification_input,
    qualify_current_formal_consequence,
)
from investment_strategy.workflow_dispatch import ObservationProvenance

_CHANGE = "qualify-active-formal-consequences"
_REVISION = "a" * 40


def _comment(
    comment_id: int,
    *,
    action: str,
    role: str,
    result: str,
    successor: str | None,
    request_id: int,
    revision: str = _REVISION,
    default_revision: str = _REVISION,
    change: str = _CHANGE,
    issue_number: int = 229,
    performed_by_actions: bool = True,
) -> dict[str, object]:
    lines = [
        (
            "REVIEW_RESULT"
            if action.startswith("review-")
            else "MERGE_RESULT"
            if action.startswith("merge-")
            else "ACTION_RESULT"
        ),
        f"Workflow: #{issue_number}",
        f"Change: {change}",
        f"Action: {action}",
        f"Role: {role}",
        f"Result: {result.upper().replace('-', '_')}",
        f"Revision: {revision}",
        f"Default-Branch-Revision: {default_revision}",
        (
            f"Application-Correlation: application:{request_id}:{issue_number}:{change}:"
            f"{role}:{action}:{result}:{revision}"
        ),
    ]
    if successor is not None:
        lines.append(f"Repository-derived successor: {successor}")
    comment: dict[str, object] = {"id": comment_id, "body": "\n".join(lines)}
    if performed_by_actions:
        comment.update(
            {
                "user": {"login": "github-actions[bot]"},
                "performed_via_github_app": {"slug": "github-actions"},
            }
        )
    else:
        comment.update(
            {
                "user": {"login": "royhsu-work"},
                "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
            }
        )
    return comment


def _decision(
    comments: list[dict[str, object]],
    *,
    current_routing: tuple[str, str] | None,
    state: str = "open",
    mode: str = "current",
    expected_routing: tuple[str, str] | None = None,
    source_routing: tuple[str, str] | None = None,
    expected_result_kind: str | None = None,
    expected_application_correlation: str | None = None,
) -> QualificationDecision:
    qualification_input = build_qualification_input(
        issue_number=229,
        change=_CHANGE,
        state=state,
        current_routing=current_routing,
        comments=comments,
        current_revision=_REVISION,
        mode=mode,  # type: ignore[arg-type]
        expected_routing=expected_routing,
        source_routing=source_routing,
        expected_result_kind=expected_result_kind,
        expected_application_correlation=expected_application_correlation,
    )
    return qualify_current_formal_consequence(qualification_input)


def test_current_route_requires_complete_repository_owned_binding() -> None:
    comment = _comment(
        1,
        action="finalize-change",
        role="lead",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=10,
    )
    assert _decision(
        [comment],
        current_routing=("executor", "implement-change"),
    ).provenance is ObservationProvenance.QUALIFIED

    incomplete = dict(comment)
    incomplete["body"] = str(comment["body"]).replace(
        f"Default-Branch-Revision: {_REVISION}\n",
        "",
    )
    assert _decision(
        [incomplete],
        current_routing=("executor", "implement-change"),
    ).provenance is ObservationProvenance.INDETERMINATE


def test_equality_only_or_connector_state_fails_closed() -> None:
    assert (
        _decision([], current_routing=("executor", "implement-change")).provenance
        is ObservationProvenance.INDETERMINATE
    )
    connector = _comment(
        1,
        action="finalize-change",
        role="lead",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=10,
        performed_by_actions=False,
    )
    assert _decision(
        [connector],
        current_routing=("executor", "implement-change"),
    ).provenance is ObservationProvenance.INDETERMINATE


def test_aba_supersession_uses_the_latest_complete_lifecycle_suffix() -> None:
    comments = [
        _comment(
            1,
            action="implement-change",
            role="executor",
            result="spec-blocker",
            successor="Lead / resolve-question",
            request_id=1,
        ),
        _comment(
            2,
            action="resolve-question",
            role="lead",
            result="ready-for-openspec-review",
            successor="Reviewer / review-openspec",
            request_id=2,
        ),
        _comment(
            3,
            action="review-openspec",
            role="reviewer",
            result="findings",
            successor="Lead / resolve-question",
            request_id=3,
        ),
    ]
    assert _decision(
        comments,
        current_routing=("lead", "resolve-question"),
    ).provenance is ObservationProvenance.QUALIFIED

    comments[-1] = _comment(
        3,
        action="review-openspec",
        role="reviewer",
        result="pass",
        successor="Executor / implement-change",
        request_id=4,
    )
    assert _decision(
        comments,
        current_routing=("lead", "resolve-question"),
    ).provenance is ObservationProvenance.INDETERMINATE


def test_pending_successor_uses_the_same_binding_decision_shape() -> None:
    comment = _comment(
        5,
        action="implement-change",
        role="executor",
        result="ready",
        successor="Reviewer / review-implementation",
        request_id=55,
    )
    correlation = (
        f"application:55:229:{_CHANGE}:executor:implement-change:ready:{_REVISION}"
    )
    assert _decision(
        [comment],
        current_routing=("executor", "implement-change"),
        mode="pending",
        expected_routing=("reviewer", "review-implementation"),
        source_routing=("executor", "implement-change"),
        expected_result_kind="ready",
        expected_application_correlation=correlation,
    ).provenance is ObservationProvenance.QUALIFIED


def test_current_terminal_requires_a_repository_owned_terminal_result() -> None:
    terminal = _comment(
        6,
        action="finalize-change",
        role="lead",
        result="no-go",
        successor=None,
        request_id=66,
    )
    assert _decision(
        [terminal],
        current_routing=None,
        state="closed",
    ).provenance is ObservationProvenance.QUALIFIED
    assert _decision(
        [terminal],
        current_routing=None,
        state="open",
    ).provenance is ObservationProvenance.INDETERMINATE


def test_change_unset_remains_pre_activation_compatible() -> None:
    qualification_input = build_qualification_input(
        issue_number=229,
        change="unset",
        state="open",
        current_routing=("lead", "explore-change"),
        comments=(),
        current_revision=None,
    )
    assert qualify_current_formal_consequence(
        qualification_input
    ).provenance is ObservationProvenance.QUALIFIED
