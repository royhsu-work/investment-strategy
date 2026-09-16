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
            f"{role}:{action}:{result}:{default_revision}"
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


def _lifecycle_events(
    comments: list[dict[str, object]],
    *,
    pending: bool = False,
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    current_label = "action:explore-change"
    for index, comment in enumerate(comments):
        comment_id = comment["id"]
        assert isinstance(comment_id, int)
        comment_time = f"2026-09-12T00:00:{index * 4 + 1:02d}Z"
        events.append(
            {
                "id": comment_id,
                "event": "commented",
                "created_at": comment_time,
            }
        )
        if pending and index == len(comments) - 1:
            continue
        body = comment["body"]
        assert isinstance(body, str)
        successor_lines = [
            line for line in body.splitlines() if line.startswith("Repository-derived successor: ")
        ]
        if successor_lines:
            target = successor_lines[0].split("/", 1)[1].split()[0]
            events.extend(
                [
                    {
                        "id": 10000 + index * 10,
                        "event": "unlabeled",
                        "created_at": f"2026-09-12T00:00:{index * 4 + 2:02d}Z",
                        "label": {"name": current_label},
                    },
                    {
                        "id": 10001 + index * 10,
                        "event": "labeled",
                        "created_at": f"2026-09-12T00:00:{index * 4 + 2:02d}Z",
                        "label": {"name": f"action:{target}"},
                    },
                ]
            )
            current_label = f"action:{target}"
        else:
            events.extend(
                [
                    {
                        "id": 10000 + index * 10,
                        "event": "unlabeled",
                        "created_at": f"2026-09-12T00:00:{index * 4 + 2:02d}Z",
                        "label": {"name": current_label},
                    },
                    {
                        "id": 10001 + index * 10,
                        "event": "closed",
                        "created_at": f"2026-09-12T00:00:{index * 4 + 2:02d}Z",
                    },
                ]
            )
    return events


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
    lifecycle_events: list[dict[str, object]] | None = None,
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
        lifecycle_events=(
            _lifecycle_events(comments, pending=mode == "pending")
            if lifecycle_events is None
            else lifecycle_events
        ),
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
    assert (
        _decision(
            [comment],
            current_routing=("executor", "implement-change"),
        ).provenance
        is ObservationProvenance.QUALIFIED
    )

    incomplete = dict(comment)
    incomplete["body"] = str(comment["body"]).replace(
        f"Default-Branch-Revision: {_REVISION}\n",
        "",
    )
    assert (
        _decision(
            [incomplete],
            current_routing=("executor", "implement-change"),
        ).provenance
        is ObservationProvenance.INDETERMINATE
    )


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
    assert (
        _decision(
            [connector],
            current_routing=("executor", "implement-change"),
        ).provenance
        is ObservationProvenance.INDETERMINATE
    )


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
    assert (
        _decision(
            comments,
            current_routing=("lead", "resolve-question"),
        ).provenance
        is ObservationProvenance.QUALIFIED
    )

    comments[-1] = _comment(
        3,
        action="review-openspec",
        role="reviewer",
        result="pass",
        successor="Executor / implement-change",
        request_id=4,
    )
    assert (
        _decision(
            comments,
            current_routing=("lead", "resolve-question"),
        ).provenance
        is ObservationProvenance.INDETERMINATE
    )


def test_aba_lifecycle_events_reject_unbound_route_replay() -> None:
    comment = _comment(
        10,
        action="implement-change",
        role="executor",
        result="spec-blocker",
        successor="Lead / resolve-question",
        request_id=10,
    )
    lifecycle_events = [
        {"id": 10, "event": "commented", "created_at": "2026-09-12T01:00:01Z"},
        {
            "id": 11,
            "event": "unlabeled",
            "created_at": "2026-09-12T01:00:02Z",
            "label": {"name": "action:implement-change"},
        },
        {
            "id": 12,
            "event": "labeled",
            "created_at": "2026-09-12T01:00:02Z",
            "label": {"name": "action:resolve-question"},
        },
        {
            "id": 13,
            "event": "unlabeled",
            "created_at": "2026-09-12T01:00:03Z",
            "label": {"name": "action:resolve-question"},
        },
        {
            "id": 14,
            "event": "labeled",
            "created_at": "2026-09-12T01:00:03Z",
            "label": {"name": "action:review-openspec"},
        },
        {
            "id": 15,
            "event": "unlabeled",
            "created_at": "2026-09-12T01:00:04Z",
            "label": {"name": "action:review-openspec"},
        },
        {
            "id": 16,
            "event": "labeled",
            "created_at": "2026-09-12T01:00:04Z",
            "label": {"name": "action:resolve-question"},
        },
    ]
    assert (
        _decision(
            [comment],
            current_routing=("lead", "resolve-question"),
            lifecycle_events=lifecycle_events,
        ).provenance
        is ObservationProvenance.INDETERMINATE
    )


def test_pending_successor_uses_the_same_binding_decision_shape() -> None:
    comment = _comment(
        5,
        action="implement-change",
        role="executor",
        result="ready",
        successor="Reviewer / review-implementation",
        request_id=55,
    )
    correlation = f"application:55:229:{_CHANGE}:executor:implement-change:ready:{_REVISION}"
    assert (
        _decision(
            [comment],
            current_routing=("executor", "implement-change"),
            mode="pending",
            expected_routing=("reviewer", "review-implementation"),
            source_routing=("executor", "implement-change"),
            expected_result_kind="ready",
            expected_application_correlation=correlation,
        ).provenance
        is ObservationProvenance.QUALIFIED
    )


def test_historical_default_revision_is_allowed_but_latest_must_match() -> None:
    historical_revision = "b" * 40
    comments = [
        _comment(
            1,
            action="finalize-change",
            role="lead",
            result="more-implementation-required",
            successor="Executor / implement-change",
            request_id=1,
            revision="c" * 40,
            default_revision=historical_revision,
        ),
        _comment(
            2,
            action="implement-change",
            role="executor",
            result="ready",
            successor="Reviewer / review-implementation",
            request_id=2,
            revision="d" * 40,
            default_revision=_REVISION,
        ),
    ]
    assert (
        _decision(
            comments,
            current_routing=("reviewer", "review-implementation"),
        ).provenance
        is ObservationProvenance.QUALIFIED
    )

    comments[-1] = _comment(
        2,
        action="implement-change",
        role="executor",
        result="ready",
        successor="Reviewer / review-implementation",
        request_id=2,
        revision="d" * 40,
        default_revision=historical_revision,
    )
    assert (
        _decision(
            comments,
            current_routing=("reviewer", "review-implementation"),
        ).provenance
        is ObservationProvenance.INDETERMINATE
    )


def test_current_terminal_requires_a_repository_owned_terminal_result() -> None:
    terminal = _comment(
        6,
        action="finalize-change",
        role="lead",
        result="no-go",
        successor=None,
        request_id=66,
    )
    assert (
        _decision(
            [terminal],
            current_routing=None,
            state="closed",
        ).provenance
        is ObservationProvenance.QUALIFIED
    )
    assert (
        _decision(
            [terminal],
            current_routing=None,
            state="open",
        ).provenance
        is ObservationProvenance.INDETERMINATE
    )


def test_legacy_implementation_checkpoint_reconstructs_completion() -> None:
    finding = _comment(
        1,
        action="review-implementation",
        role="reviewer",
        result="findings",
        successor="Executor / implement-change",
        request_id=1,
    )
    checkpoint = {
        "id": 2,
        "body": (
            "SLICE_CHECKPOINT\n"
            "Workflow: #229\n"
            f"Change: {_CHANGE}\n"
            "Action: implement-change\n"
            "Role: executor\n"
            "Completed-Tasks: 2.1, 2.2, 2.3, 2.4, 2.5\n"
            f"Revision: {_REVISION}\n"
            "Application-Correlation: application:2:229:"
            f"{_CHANGE}:executor:implement-change:ready:{_REVISION}\n"
            "Gate-Evidence: exact-head VERIFY\n"
            "Remaining-Approved-Boundary: review-implementation required"
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    lifecycle_events = [
        {"id": 1, "event": "commented", "created_at": "2026-09-12T00:00:01Z"},
        {
            "id": 10,
            "event": "unlabeled",
            "created_at": "2026-09-12T00:00:02Z",
            "label": {"name": "action:review-implementation"},
        },
        {
            "id": 11,
            "event": "labeled",
            "created_at": "2026-09-12T00:00:02Z",
            "label": {"name": "action:implement-change"},
        },
        {"id": 2, "event": "commented", "created_at": "2026-09-12T00:00:03Z"},
        {
            "id": 12,
            "event": "unlabeled",
            "created_at": "2026-09-12T00:00:04Z",
            "label": {"name": "action:implement-change"},
        },
        {
            "id": 13,
            "event": "labeled",
            "created_at": "2026-09-12T00:00:04Z",
            "label": {"name": "action:review-implementation"},
        },
    ]
    assert (
        _decision(
            [finding, checkpoint],
            current_routing=("reviewer", "review-implementation"),
            lifecycle_events=lifecycle_events,
        ).provenance
        is ObservationProvenance.QUALIFIED
    )


def test_change_unset_remains_pre_activation_compatible() -> None:
    qualification_input = build_qualification_input(
        issue_number=229,
        change="unset",
        state="open",
        current_routing=("lead", "explore-change"),
        comments=(),
        current_revision=None,
    )
    assert (
        qualify_current_formal_consequence(qualification_input).provenance
        is ObservationProvenance.QUALIFIED
    )


def _recovery_comment(
    *,
    comment_id: int = 50,
    revision: str = _REVISION,
    performed_by_actions: bool = True,
) -> dict[str, object]:
    comment: dict[str, object] = {
        "id": comment_id,
        "body": (
            "APPLICATION_RECOVERY\n"
            "Workflow: #229\n"
            f"Change: {_CHANGE}\n"
            "Source: Lead / propose-change\n"
            "Target: Lead / resolve-question\n"
            f"Default-Branch-Revision: {revision}\n"
            f"Failed-Authorization-Revision: {'b' * 40}\n"
            "Request-Comment-ID: 901\n"
            "Reason: partial-first-activation"
        ),
    }
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


def _recovery_lifecycle(*, superseded: bool = False) -> list[dict[str, object]]:
    events: list[dict[str, object]] = [
        {"id": 50, "event": "commented", "created_at": "2026-09-16T01:00:01Z"},
        {
            "id": 51,
            "event": "unlabeled",
            "created_at": "2026-09-16T01:00:02Z",
            "label": {"name": "action:propose-change"},
        },
        {
            "id": 52,
            "event": "labeled",
            "created_at": "2026-09-16T01:00:02Z",
            "label": {"name": "action:resolve-question"},
        },
    ]
    if superseded:
        events.extend(
            [
                {
                    "id": 53,
                    "event": "unlabeled",
                    "created_at": "2026-09-16T01:00:03Z",
                    "label": {"name": "action:resolve-question"},
                },
                {
                    "id": 54,
                    "event": "labeled",
                    "created_at": "2026-09-16T01:00:03Z",
                    "label": {"name": "action:review-openspec"},
                },
            ]
        )
    return events


def test_administrative_recovery_qualifies_only_exact_actions_owned_binding() -> None:
    qualification_input = build_qualification_input(
        issue_number=229,
        change=_CHANGE,
        state="open",
        current_routing=("lead", "resolve-question"),
        comments=[_recovery_comment()],
        current_revision=_REVISION,
        lifecycle_events=_recovery_lifecycle(),
    )
    decision = qualify_current_formal_consequence(qualification_input)
    assert decision.provenance is ObservationProvenance.QUALIFIED
    assert decision.reason == "current-administrative-recovery-route-qualified"

    connector_input = build_qualification_input(
        issue_number=229,
        change=_CHANGE,
        state="open",
        current_routing=("lead", "resolve-question"),
        comments=[_recovery_comment(performed_by_actions=False)],
        current_revision=_REVISION,
        lifecycle_events=_recovery_lifecycle(),
    )
    assert (
        qualify_current_formal_consequence(connector_input).provenance
        is ObservationProvenance.INDETERMINATE
    )


def test_administrative_recovery_rejects_stale_or_superseded_binding() -> None:
    stale_input = build_qualification_input(
        issue_number=229,
        change=_CHANGE,
        state="open",
        current_routing=("lead", "resolve-question"),
        comments=[_recovery_comment(revision="c" * 40)],
        current_revision=_REVISION,
        lifecycle_events=_recovery_lifecycle(),
    )
    assert (
        qualify_current_formal_consequence(stale_input).provenance
        is ObservationProvenance.INDETERMINATE
    )

    superseded_input = build_qualification_input(
        issue_number=229,
        change=_CHANGE,
        state="open",
        current_routing=("lead", "resolve-question"),
        comments=[_recovery_comment()],
        current_revision=_REVISION,
        lifecycle_events=_recovery_lifecycle(superseded=True),
    )
    assert (
        qualify_current_formal_consequence(superseded_input).provenance
        is ObservationProvenance.INDETERMINATE
    )
