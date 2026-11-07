from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from investment_strategy.scheduled_agent_formal_qualification import (
    QualificationDecision,
    build_qualification_input,
    qualify_current_formal_consequence,
)
from investment_strategy.scheduled_agent_formal_result import parse_formal_result
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
    application_revision: str | None = None,
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
            f"{role}:{action}:{result}:{application_revision or default_revision}"
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
    authorization_ancestry: tuple[tuple[str, str], ...] = (),
    allow_successor_frontier: bool = False,
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
        authorization_ancestry=authorization_ancestry,
        allow_successor_frontier=allow_successor_frontier,
    )
    return qualify_current_formal_consequence(qualification_input)


def test_exact_322_human_handoff_allows_only_accepted_ready_interval() -> None:
    """A Human detour can bind one real READY, never an unsigned substitute."""

    change = "restore-no-work-idle-discovery"
    previous = _comment(
        6567424875,
        action="review-implementation",
        role="reviewer",
        result="findings",
        successor="Executor / implement-change",
        request_id=6567405847,
        change=change,
        issue_number=322,
    )
    ready = _comment(
        6573000001,
        action="implement-change",
        role="executor",
        result="ready",
        successor="Reviewer / review-implementation",
        request_id=6568245475,
        revision="ddd6b3f5a19b879e427aee313334aeab6a43a241",
        change=change,
        issue_number=322,
    )
    handoff: dict[str, object] = {
        "id": 6569195457,
        "user": {"login": "royhsu-work"},
        "body": "## #322 一次性 Lead 接管紀錄",
    }
    timeline = _lifecycle_events([previous, ready])
    timeline.extend(
        [
            {
                "id": 10030,
                "event": "unlabeled",
                "created_at": "2026-09-12T00:00:03Z",
                "label": {"name": "action:implement-change"},
            },
            {
                "id": 10031,
                "event": "labeled",
                "created_at": "2026-09-12T00:00:03Z",
                "label": {"name": "action:resolve-question"},
            },
            {
                "id": 10032,
                "event": "unlabeled",
                "created_at": "2026-09-12T00:00:04Z",
                "label": {"name": "action:resolve-question"},
            },
            {
                "id": 10033,
                "event": "labeled",
                "created_at": "2026-09-12T00:00:04Z",
                "label": {"name": "action:implement-change"},
            },
        ]
    )
    for supplied in ([previous, ready], [previous, handoff, ready]):
        qualification = build_qualification_input(
            issue_number=322,
            change=change,
            state="open",
            current_routing=("reviewer", "review-implementation"),
            comments=supplied,
            current_revision=_REVISION,
            lifecycle_events=timeline,
        )
        decision = qualify_current_formal_consequence(qualification)
        assert decision.qualified is (len(supplied) == 3), decision.reason
    pending_timeline = _lifecycle_events([previous, ready], pending=True)
    pending_timeline.extend(timeline[-4:])
    pending = build_qualification_input(
        issue_number=322,
        change=change,
        state="open",
        current_routing=("executor", "implement-change"),
        comments=[previous, handoff, ready],
        current_revision=_REVISION,
        mode="pending",
        source_routing=("executor", "implement-change"),
        expected_routing=("reviewer", "review-implementation"),
        expected_result_kind="ready",
        expected_application_correlation=(
            f"application:6568245475:322:{change}:executor:implement-change:ready:{_REVISION}"
        ),
        lifecycle_events=pending_timeline,
    )
    pending_decision = qualify_current_formal_consequence(pending)
    assert pending_decision.qualified, pending_decision.reason
    assert not qualify_current_formal_consequence(
        replace(pending, one_time_human_handoff=False)
    ).qualified
    next_review = _comment(
        6573000100,
        action="review-implementation",
        role="reviewer",
        result="pass",
        successor="Executor / merge-implementation-pr",
        request_id=6573000050,
        change=change,
        issue_number=322,
    )
    future_timeline = _lifecycle_events([previous, ready, next_review])
    future_timeline.extend(timeline[-4:])
    following = build_qualification_input(
        issue_number=322,
        change=change,
        state="open",
        current_routing=("executor", "merge-implementation-pr"),
        comments=[previous, handoff, ready, next_review],
        current_revision=_REVISION,
        lifecycle_events=future_timeline,
    )
    assert qualify_current_formal_consequence(following).qualified
    handoff["user"] = {"login": "untrusted-user"}
    bad = build_qualification_input(
        issue_number=322,
        change=change,
        state="open",
        current_routing=("reviewer", "review-implementation"),
        comments=[previous, handoff, ready],
        current_revision=_REVISION,
        lifecycle_events=timeline,
    )
    assert not qualify_current_formal_consequence(bad).qualified


def test_accepted_intent_reconciles_after_successor_lifecycle_binding() -> None:
    comment = _comment(
        1,
        action="finalize-change",
        role="lead",
        result="archive-ready",
        successor="Reviewer / review-archive",
        request_id=10,
    )
    correlation = f"application:10:229:{_CHANGE}:lead:finalize-change:archive-ready:{_REVISION}"
    decision = _decision(
        [comment],
        current_routing=("reviewer", "review-archive"),
        mode="pending",
        expected_routing=("reviewer", "review-archive"),
        source_routing=("lead", "finalize-change"),
        expected_result_kind="archive-ready",
        expected_application_correlation=correlation,
        lifecycle_events=_lifecycle_events([comment], pending=False),
        allow_successor_frontier=True,
    )
    assert decision.provenance is ObservationProvenance.QUALIFIED


def test_accepted_intent_reconciles_duplicate_formal_result_without_new_label() -> None:
    historical_revision = "b" * 40
    first = _comment(
        1,
        action="finalize-change",
        role="lead",
        result="archive-ready",
        successor="Reviewer / review-archive",
        request_id=10,
        revision=historical_revision,
        default_revision=historical_revision,
        application_revision=historical_revision,
    )
    retry = _comment(
        2,
        action="finalize-change",
        role="lead",
        result="archive-ready",
        successor="Reviewer / review-archive",
        request_id=10,
        revision=historical_revision,
        default_revision=historical_revision,
        application_revision=_REVISION,
    )
    correlation = f"application:10:229:{_CHANGE}:lead:finalize-change:archive-ready:{_REVISION}"
    decision = _decision(
        [first, retry],
        current_routing=("reviewer", "review-archive"),
        mode="pending",
        expected_routing=("reviewer", "review-archive"),
        source_routing=("lead", "finalize-change"),
        expected_result_kind="archive-ready",
        expected_application_correlation=correlation,
        lifecycle_events=_lifecycle_events([first, retry], pending=True),
        authorization_ancestry=((historical_revision, _REVISION),),
        allow_successor_frontier=True,
    )
    assert decision.provenance is ObservationProvenance.QUALIFIED
    assert decision.reason == "accepted-successor-postcondition-qualified"


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


def test_exact_close_unroute_reopen_restore_preserves_bound_route() -> None:
    comment = _comment(
        20,
        action="propose-change",
        role="lead",
        result="ready-for-openspec-review",
        successor="Reviewer / review-openspec",
        request_id=20,
    )
    lifecycle_events = [
        {"id": 20, "event": "commented", "created_at": "2026-09-18T06:14:36Z"},
        {
            "id": 21,
            "event": "unlabeled",
            "created_at": "2026-09-18T06:14:53Z",
            "label": {"name": "action:propose-change"},
        },
        {
            "id": 22,
            "event": "labeled",
            "created_at": "2026-09-18T06:14:53Z",
            "label": {"name": "action:review-openspec"},
        },
        {"id": 23, "event": "closed", "created_at": "2026-09-18T07:36:58Z"},
        {
            "id": 24,
            "event": "unlabeled",
            "created_at": "2026-09-18T07:36:58Z",
            "label": {"name": "action:review-openspec"},
        },
        {"id": 25, "event": "reopened", "created_at": "2026-09-18T07:58:06Z"},
        {
            "id": 26,
            "event": "labeled",
            "created_at": "2026-09-18T07:58:06Z",
            "label": {"name": "action:review-openspec"},
        },
    ]
    decision = _decision(
        [comment],
        current_routing=("reviewer", "review-openspec"),
        lifecycle_events=lifecycle_events,
    )
    assert decision.provenance is ObservationProvenance.QUALIFIED
    assert decision.reason == "current-formal-route-qualified"


def test_restoration_to_a_different_route_remains_unqualified() -> None:
    comment = _comment(
        20,
        action="propose-change",
        role="lead",
        result="ready-for-openspec-review",
        successor="Reviewer / review-openspec",
        request_id=20,
    )
    lifecycle_events = [
        {"id": 20, "event": "commented", "created_at": "2026-09-18T06:14:36Z"},
        {
            "id": 21,
            "event": "unlabeled",
            "created_at": "2026-09-18T06:14:53Z",
            "label": {"name": "action:propose-change"},
        },
        {
            "id": 22,
            "event": "labeled",
            "created_at": "2026-09-18T06:14:53Z",
            "label": {"name": "action:review-openspec"},
        },
        {"id": 23, "event": "closed", "created_at": "2026-09-18T07:36:58Z"},
        {
            "id": 24,
            "event": "unlabeled",
            "created_at": "2026-09-18T07:36:58Z",
            "label": {"name": "action:review-openspec"},
        },
        {"id": 25, "event": "reopened", "created_at": "2026-09-18T07:58:06Z"},
        {
            "id": 26,
            "event": "labeled",
            "created_at": "2026-09-18T07:58:06Z",
            "label": {"name": "action:implement-change"},
        },
    ]
    assert (
        _decision(
            [comment],
            current_routing=("reviewer", "review-openspec"),
            lifecycle_events=lifecycle_events,
        ).provenance
        is ObservationProvenance.INDETERMINATE
    )


def test_pending_historical_result_accepts_newer_application_revision() -> None:
    historical_revision = "b" * 40
    application_revision = "c" * 40
    comment = _comment(
        5,
        action="implement-change",
        role="executor",
        result="ready",
        successor="Reviewer / review-implementation",
        request_id=55,
        revision=historical_revision,
        default_revision=historical_revision,
        application_revision=application_revision,
    )
    correlation = (
        f"application:55:229:{_CHANGE}:executor:implement-change:ready:{application_revision}"
    )
    decision = _decision(
        [comment],
        current_routing=("executor", "implement-change"),
        mode="pending",
        expected_routing=("reviewer", "review-implementation"),
        source_routing=("executor", "implement-change"),
        expected_result_kind="ready",
        expected_application_correlation=correlation,
        authorization_ancestry=((historical_revision, _REVISION),),
    )
    assert decision.provenance is ObservationProvenance.QUALIFIED


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


def test_pending_formal_ignores_unrelated_human_label_without_relaxing_action_guard() -> None:
    comment = _comment(
        5,
        action="implement-change",
        role="executor",
        result="ready",
        successor="Reviewer / review-implementation",
        request_id=55,
    )
    correlation = f"application:55:229:{_CHANGE}:executor:implement-change:ready:{_REVISION}"
    lifecycle = [
        {
            "id": 4,
            "event": "labeled",
            "created_at": "2026-09-12T00:00:00Z",
            "label": {"name": "human:approved"},
        },
        *_lifecycle_events([comment], pending=True),
    ]

    def decide(events: list[dict[str, object]]) -> QualificationDecision:
        return _decision(
            [comment],
            current_routing=("executor", "implement-change"),
            mode="pending",
            expected_routing=("reviewer", "review-implementation"),
            source_routing=("executor", "implement-change"),
            expected_result_kind="ready",
            expected_application_correlation=correlation,
            lifecycle_events=events,
        )

    assert decide(lifecycle).provenance is ObservationProvenance.QUALIFIED
    malformed = [
        {**lifecycle[0], "label": {"name": "action:not-a-real-action"}},
        *lifecycle[1:],
    ]
    assert decide(malformed).provenance is ObservationProvenance.INDETERMINATE


def test_pending_forward_result_ignores_closed_reopened_history_with_stable_action() -> None:
    """A later accepted result may advance across unrelated admin-only history."""
    reviewed = _comment(
        10,
        action="review-implementation",
        role="reviewer",
        result="findings",
        successor="Executor / implement-change",
        request_id=41,
    )
    ready = _comment(
        20,
        action="implement-change",
        role="executor",
        result="ready",
        successor="Reviewer / review-implementation",
        request_id=55,
    )
    lifecycle = _lifecycle_events([reviewed, ready], pending=True)
    lifecycle[-1]["created_at"] = "2026-09-12T00:00:09Z"
    lifecycle.extend(
        [
            {
                "id": 100,
                "event": "labeled",
                "created_at": "2026-09-12T00:00:03Z",
                "label": {"name": "human:approved"},
            },
            {"id": 101, "event": "closed", "created_at": "2026-09-12T00:00:04Z"},
            {"id": 102, "event": "reopened", "created_at": "2026-09-12T00:00:04Z"},
            {"id": 103, "event": "closed", "created_at": "2026-09-12T00:00:06Z"},
            {"id": 104, "event": "reopened", "created_at": "2026-09-12T00:00:07Z"},
        ]
    )
    correlation = f"application:55:229:{_CHANGE}:executor:implement-change:ready:{_REVISION}"

    def decide(events: list[dict[str, object]]) -> QualificationDecision:
        return _decision(
            [reviewed, ready],
            current_routing=("executor", "implement-change"),
            mode="pending",
            expected_routing=("reviewer", "review-implementation"),
            source_routing=("executor", "implement-change"),
            expected_result_kind="ready",
            expected_application_correlation=correlation,
            lifecycle_events=events,
        )

    assert decide(lifecycle).provenance is ObservationProvenance.QUALIFIED
    # An actual routing change between close and reopen is not inert history.
    unsafe = [
        *lifecycle,
        {
            "id": 105,
            "event": "labeled",
            "created_at": "2026-09-12T00:00:08Z",
            "label": {"name": "action:resolve-question"},
        },
    ]
    assert decide(unsafe).provenance is ObservationProvenance.INDETERMINATE


def test_pending_historical_result_requires_explicit_descendant_binding() -> None:
    historical_revision = "b" * 40
    comment = _comment(
        5,
        action="implement-change",
        role="executor",
        result="ready",
        successor="Reviewer / review-implementation",
        request_id=55,
        revision=historical_revision,
        default_revision=historical_revision,
    )
    correlation = (
        f"application:55:229:{_CHANGE}:executor:implement-change:ready:{historical_revision}"
    )
    lifecycle_events = _lifecycle_events([comment], pending=True)
    without_ancestry = _decision(
        [comment],
        current_routing=("executor", "implement-change"),
        mode="pending",
        expected_routing=("reviewer", "review-implementation"),
        source_routing=("executor", "implement-change"),
        expected_result_kind="ready",
        expected_application_correlation=correlation,
        lifecycle_events=lifecycle_events,
    )
    assert without_ancestry.provenance is ObservationProvenance.INDETERMINATE

    with_ancestry = _decision(
        [comment],
        current_routing=("executor", "implement-change"),
        mode="pending",
        expected_routing=("reviewer", "review-implementation"),
        source_routing=("executor", "implement-change"),
        expected_result_kind="ready",
        expected_application_correlation=correlation,
        lifecycle_events=lifecycle_events,
        authorization_ancestry=((historical_revision, _REVISION),),
    )
    assert with_ancestry.provenance is ObservationProvenance.QUALIFIED


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


def test_administrative_recovery_chains_into_later_pending_formal_result() -> None:
    recovery_revision = "c" * 40
    formal_revision = "d" * 40
    recovery = _recovery_comment(revision=recovery_revision)
    formal = _comment(
        60,
        action="resolve-question",
        role="lead",
        result="ready-for-openspec-review",
        successor="Reviewer / review-openspec",
        request_id=902,
        revision=formal_revision,
        default_revision=formal_revision,
    )
    lifecycle = [
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
        {"id": 60, "event": "commented", "created_at": "2026-09-16T01:00:03Z"},
    ]
    correlation = (
        f"application:902:229:{_CHANGE}:lead:resolve-question:"
        f"ready-for-openspec-review:{formal_revision}"
    )
    qualification_input = build_qualification_input(
        issue_number=229,
        change=_CHANGE,
        state="open",
        current_routing=("lead", "resolve-question"),
        comments=[recovery, formal],
        current_revision=_REVISION,
        mode="pending",
        expected_routing=("reviewer", "review-openspec"),
        source_routing=("lead", "resolve-question"),
        expected_result_kind="ready-for-openspec-review",
        expected_application_correlation=correlation,
        lifecycle_events=lifecycle,
        authorization_ancestry=(
            (recovery_revision, _REVISION),
            (formal_revision, _REVISION),
        ),
    )
    decision = qualify_current_formal_consequence(qualification_input)
    assert decision.provenance is ObservationProvenance.QUALIFIED
    assert decision.reason == "pending-successor-qualified"


def _unbound_formal_comment(*, comment_id: int, change: str) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": (
            "ACTION_RESULT\n"
            "Workflow: #229\n"
            f"Change: {change}\n"
            "Action: explore-change\n"
            "Role: lead\n"
            "Result: PROPOSAL_READY\n"
            f"Revision: {_REVISION}\n"
            f"Default-Branch-Revision: {_REVISION}"
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }


def test_administrative_recovery_ignores_historical_preactivation_formal_shape() -> None:
    historical = _unbound_formal_comment(comment_id=40, change="unset")
    lifecycle = [
        {"id": 40, "event": "commented", "created_at": "2026-09-16T00:59:59Z"},
        *_recovery_lifecycle(),
    ]
    qualification_input = build_qualification_input(
        issue_number=229,
        change=_CHANGE,
        state="open",
        current_routing=("lead", "resolve-question"),
        comments=[historical, _recovery_comment()],
        current_revision=_REVISION,
        lifecycle_events=lifecycle,
    )
    decision = qualify_current_formal_consequence(qualification_input)
    assert decision.provenance is ObservationProvenance.QUALIFIED
    assert decision.reason == "current-administrative-recovery-route-qualified"


def test_administrative_recovery_rejects_unbound_current_change_formal_shape() -> None:
    competing = _unbound_formal_comment(comment_id=40, change=_CHANGE)
    lifecycle = [
        {"id": 40, "event": "commented", "created_at": "2026-09-16T00:59:59Z"},
        *_recovery_lifecycle(),
    ]
    qualification_input = build_qualification_input(
        issue_number=229,
        change=_CHANGE,
        state="open",
        current_routing=("lead", "resolve-question"),
        comments=[competing, _recovery_comment()],
        current_revision=_REVISION,
        lifecycle_events=lifecycle,
    )
    decision = qualify_current_formal_consequence(qualification_input)
    assert decision.provenance is ObservationProvenance.INDETERMINATE
    assert decision.reason == "administrative-recovery-competing-formal-evidence"


@pytest.mark.parametrize("prior_blocked", [False, True])
@pytest.mark.parametrize("unrelated_invalid_recovery", [False, True])
def test_accepted_merge_application_recovery_binds_successor_and_later_lead_work(
    prior_blocked: bool,
    unrelated_invalid_recovery: bool,
) -> None:
    """An immutable ACCEPTED MERGED intent is not republished as LIFECYCLE_VIOLATION."""

    review = _comment(
        100,
        action="review-implementation",
        role="reviewer",
        result="pass",
        successor="Executor / merge-implementation-pr",
        request_id=50,
    )
    accepted_body = "\n".join(
        (
            "APPLICATION_DECISION",
            "Request-Comment: 51",
            "Disposition: ACCEPTED",
            "Result-Kind: merged",
            "Issue: 229",
            "Role: executor",
            "Action: merge-implementation-pr",
            f"Change: {_CHANGE}",
        )
    )
    accepted = {
        "id": 101,
        "body": accepted_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    recovery = {
        "id": 102,
        "body": "\n".join(
            (
                "APPLICATION_RECOVERY",
                "Workflow: #229",
                f"Change: {_CHANGE}",
                "Source: Executor / merge-implementation-pr",
                "Target: Lead / resolve-question",
                f"Default-Branch-Revision: {_REVISION}",
                f"Failed-Authorization-Revision: {_REVISION}",
                "Request-Comment-ID: 51",
                "Accepted-Decision-SHA256: " + hashlib.sha256(accepted_body.encode()).hexdigest(),
                "Failure-Evidence-SHA256: " + "f" * 64,
                "PR-Number: 418",
                "PR-Head-SHA: " + _REVISION,
                "Reason: accepted-merge-precondition-rejected",
            )
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    timeline: list[dict[str, object]] = [
        {"id": 100, "event": "commented", "created_at": "2026-09-16T01:00:00Z"},
        {
            "id": 201,
            "event": "labeled",
            "created_at": "2026-09-16T01:00:01Z",
            "label": {"name": "action:merge-implementation-pr"},
        },
        {"id": 101, "event": "commented", "created_at": "2026-09-16T01:00:02Z"},
        {"id": 102, "event": "commented", "created_at": "2026-09-16T01:00:03Z"},
        {
            "id": 202,
            "event": "unlabeled",
            "created_at": "2026-09-16T01:00:04Z",
            "label": {"name": "action:merge-implementation-pr"},
        },
        {
            "id": 203,
            "event": "labeled",
            "created_at": "2026-09-16T01:00:04Z",
            "label": {"name": "action:resolve-question"},
        },
    ]
    comments = [review, accepted, recovery]
    if unrelated_invalid_recovery:
        # A malformed, older recovery from another episode is historical
        # context, not a current gate that can permanently stall the latest
        # independently proven merge handoff.
        comments.insert(
            0,
            {
                "id": 98,
                "body": "APPLICATION_RECOVERY\nReason: partial-first-activation",
                "user": {"login": "github-actions[bot]"},
                "performed_via_github_app": {"slug": "github-actions"},
            },
        )
        timeline.insert(
            0,
            {"id": 98, "event": "commented", "created_at": "2026-09-16T00:59:59Z"},
        )
    if prior_blocked:
        comments.insert(
            1,
            _comment(
                300,
                action="merge-implementation-pr",
                role="executor",
                result="blocked",
                successor="Executor / merge-implementation-pr",
                request_id=49,
            ),
        )
        timeline.insert(
            2,
            {"id": 300, "event": "commented", "created_at": "2026-09-16T01:00:01Z"},
        )
    qualified = qualify_current_formal_consequence(
        build_qualification_input(
            issue_number=229,
            change=_CHANGE,
            state="open",
            current_routing=("lead", "resolve-question"),
            comments=comments,
            current_revision=_REVISION,
            lifecycle_events=timeline,
        )
    )
    assert qualified.provenance is ObservationProvenance.QUALIFIED, qualified.reason
    assert qualified.reason == "current-administrative-recovery-route-qualified"

    lead = _comment(
        103,
        action="resolve-question",
        role="lead",
        result="ready",
        successor="Executor / implement-change",
        request_id=52,
    )
    timeline.extend(
        [
            {"id": 103, "event": "commented", "created_at": "2026-09-16T01:00:05Z"},
            {
                "id": 204,
                "event": "unlabeled",
                "created_at": "2026-09-16T01:00:06Z",
                "label": {"name": "action:resolve-question"},
            },
            {
                "id": 205,
                "event": "labeled",
                "created_at": "2026-09-16T01:00:06Z",
                "label": {"name": "action:implement-change"},
            },
        ]
    )
    continued = qualify_current_formal_consequence(
        build_qualification_input(
            issue_number=229,
            change=_CHANGE,
            state="open",
            current_routing=("executor", "implement-change"),
            comments=[*comments, lead],
            current_revision=_REVISION,
            lifecycle_events=timeline,
        )
    )
    assert continued.provenance is ObservationProvenance.QUALIFIED, continued.reason
    assert continued.reason == "current-formal-route-qualified"


def test_application_owned_lowercase_successor_is_reconciled() -> None:
    revision = _REVISION
    correlation = f"application:7:229:unset:lead:explore-change:proposal-ready:{revision}"
    payload = {
        "id": 701,
        "body": "\n".join(
            (
                "ACTION_RESULT",
                "Workflow: #229",
                "Change: unset",
                "Role: lead",
                "Action: explore-change",
                "Result: PROPOSAL_READY",
                f"Revision: {revision}",
                f"Default-Branch-Revision: {revision}",
                f"Application-Correlation: {correlation}",
                "Repository-derived successor: lead / propose-change",
            )
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }

    event = parse_formal_result(payload, current_revision=revision)

    assert event is not None
    assert event.valid
    assert event.successor == ("lead", "propose-change")
