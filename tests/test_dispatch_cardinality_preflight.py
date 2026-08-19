"""Fixture-driven regression coverage for #105 dispatch cardinality preflight."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
MIGRATION = ROOT / "agents" / "scheduled-task-migration.md"

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


@dataclass(frozen=True)
class WorkflowIssue:
    number: int
    change: str
    routing: Routing | None
    state: Literal["open", "closed"] = "open"
    created_order: int = 0


@dataclass(frozen=True)
class Snapshot:
    issues: tuple[WorkflowIssue, ...]
    complete: bool


@dataclass(frozen=True)
class ActivationAttempt:
    issue_number: int
    change: str
    routing: Routing = ("lead", "propose-change")


def classify(snapshot: Snapshot) -> tuple[str, int | None]:
    """Test-only model of the approved four-way dispatch decision table."""
    if not snapshot.complete:
        return ("indeterminate", None)

    formal = [
        issue
        for issue in snapshot.issues
        if issue.change != "unset" and issue.routing is not None and issue.state == "open"
    ]
    terminal = [
        issue
        for issue in snapshot.issues
        if issue.change != "unset"
        and issue.routing == ("lead", "finalize-archive")
        and issue.state == "closed"
    ]
    active = formal + terminal
    if len(active) > 1:
        return ("fail-closed", None)
    if len(active) == 1:
        return ("formal", active[0].number)

    queued = sorted(
        (
            issue
            for issue in snapshot.issues
            if issue.change == "unset"
            and issue.state == "open"
            and issue.routing in {("lead", "explore-change"), ("lead", "propose-change")}
        ),
        key=lambda issue: (issue.created_order, issue.number),
    )
    return ("pre-activation", queued[0].number if queued else None)


def action_entry_allowed(snapshot: Snapshot, issue_number: int, routing: Routing) -> bool:
    """Model the mapped-action defense after a wake selected an Issue."""
    disposition, selected = classify(snapshot)
    if routing in {("lead", "explore-change"), ("lead", "propose-change")}:
        return disposition == "pre-activation" and selected == issue_number
    return disposition == "formal" and selected == issue_number


def activate(snapshot: Snapshot, attempt: ActivationAttempt) -> Snapshot | None:
    """Model Propose's immediate pre-write activation boundary."""
    if not action_entry_allowed(snapshot, attempt.issue_number, attempt.routing):
        return None
    issues = tuple(
        replace(issue, change=attempt.change) if issue.number == attempt.issue_number else issue
        for issue in snapshot.issues
    )
    return Snapshot(issues=issues, complete=snapshot.complete)


def activation_still_valid(snapshot: Snapshot, issue_number: int) -> bool:
    """Model Propose's post-write complete-cardinality stale check."""
    return classify(snapshot) == ("formal", issue_number)


def test_zero_formal_work_selects_oldest_combined_pre_activation_candidate() -> None:
    snapshot = Snapshot(
        issues=(
            WorkflowIssue(20, "unset", ("lead", "propose-change"), created_order=2),
            WorkflowIssue(19, "unset", ("lead", "explore-change"), created_order=1),
        ),
        complete=True,
    )
    assert classify(snapshot) == ("pre-activation", 19)


def test_one_formal_work_wins_over_queued_explore() -> None:
    snapshot = Snapshot(
        issues=(
            WorkflowIssue(30, "active-change", ("executor", "implement-change")),
            WorkflowIssue(31, "unset", ("lead", "explore-change"), created_order=0),
        ),
        complete=True,
    )
    assert classify(snapshot) == ("formal", 30)
    assert not action_entry_allowed(snapshot, 31, ("lead", "explore-change"))


def test_selected_explore_stops_when_formal_work_appears_before_action_entry() -> None:
    selected = WorkflowIssue(40, "unset", ("lead", "explore-change"), created_order=1)
    initial = Snapshot(issues=(selected,), complete=True)
    assert action_entry_allowed(initial, 40, ("lead", "explore-change"))

    fresh = Snapshot(
        issues=(
            selected,
            WorkflowIssue(39, "already-active", ("executor", "implement-change")),
        ),
        complete=True,
    )
    assert classify(fresh) == ("formal", 39)
    assert not action_entry_allowed(fresh, 40, ("lead", "explore-change"))


def test_selected_explore_stops_when_fresh_enumeration_is_indeterminate() -> None:
    selected = WorkflowIssue(41, "unset", ("lead", "explore-change"))
    fresh = Snapshot(issues=(selected,), complete=False)
    assert classify(fresh) == ("indeterminate", None)
    assert not action_entry_allowed(fresh, 41, ("lead", "explore-change"))


def test_partial_enumeration_is_indeterminate_even_when_only_queue_is_visible() -> None:
    snapshot = Snapshot(
        issues=(WorkflowIssue(42, "unset", ("lead", "explore-change")),),
        complete=False,
    )
    assert classify(snapshot) == ("indeterminate", None)


def test_propose_pre_write_refuses_activation_when_active_work_appears() -> None:
    candidate = WorkflowIssue(45, "unset", ("lead", "propose-change"), created_order=1)
    initial = Snapshot(issues=(candidate,), complete=True)
    assert activate(initial, ActivationAttempt(45, "candidate-change")) is not None

    fresh = Snapshot(
        issues=(
            candidate,
            WorkflowIssue(44, "existing-change", ("reviewer", "review-openspec")),
        ),
        complete=True,
    )
    assert activate(fresh, ActivationAttempt(45, "candidate-change")) is None
    assert fresh.issues[0].change == "unset"


def test_propose_post_write_stops_when_competing_activation_creates_two_actives() -> None:
    first = WorkflowIssue(47, "unset", ("lead", "propose-change"), created_order=1)
    second = WorkflowIssue(48, "unset", ("lead", "propose-change"), created_order=2)
    initial = Snapshot(issues=(first, second), complete=True)
    activated = activate(initial, ActivationAttempt(47, "first-change"))
    assert activated is not None
    assert activation_still_valid(activated, 47)

    contradicted = Snapshot(
        issues=(
            activated.issues[0],
            replace(second, change="competing-change"),
        ),
        complete=True,
    )
    assert classify(contradicted) == ("fail-closed", None)
    assert not activation_still_valid(contradicted, 47)


def test_two_formal_workflows_fail_closed_without_winner_selection() -> None:
    snapshot = Snapshot(
        issues=(
            WorkflowIssue(50, "first", ("executor", "implement-change"), created_order=1),
            WorkflowIssue(51, "second", ("reviewer", "review-openspec"), created_order=2),
        ),
        complete=True,
    )
    assert classify(snapshot) == ("fail-closed", None)


def test_two_formal_workflows_prevent_every_normal_mapped_action() -> None:
    routes: tuple[Routing, ...] = (
        ("lead", "explore-change"),
        ("lead", "propose-change"),
        ("lead", "resolve-question"),
        ("lead", "finalize-change"),
        ("lead", "finalize-archive"),
        ("reviewer", "review-openspec"),
        ("reviewer", "review-implementation"),
        ("reviewer", "review-archive"),
        ("executor", "implement-change"),
        ("executor", "merge-pr"),
    )
    for route in routes:
        snapshot = Snapshot(
            issues=(
                WorkflowIssue(60, "first", route),
                WorkflowIssue(61, "second", ("executor", "implement-change")),
            ),
            complete=True,
        )
        assert not action_entry_allowed(snapshot, 60, route)


def test_two_formal_workflows_fail_closed_independent_of_order_or_priority() -> None:
    snapshot = Snapshot(
        issues=(
            WorkflowIssue(2, "newer", ("lead", "finalize-change"), created_order=99),
            WorkflowIssue(1, "older", ("executor", "merge-pr"), created_order=1),
        ),
        complete=True,
    )
    assert classify(snapshot) == ("fail-closed", None)
    assert classify(Snapshot(tuple(reversed(snapshot.issues)), complete=True)) == (
        "fail-closed",
        None,
    )


def test_multiple_active_failure_does_not_mutate_change_or_routing() -> None:
    issues = (
        WorkflowIssue(70, "first", ("executor", "implement-change")),
        WorkflowIssue(71, "second", ("reviewer", "review-openspec")),
    )
    snapshot = Snapshot(issues=issues, complete=True)
    before = snapshot
    assert classify(snapshot) == ("fail-closed", None)
    assert snapshot == before


def test_terminal_pending_work_wins_over_pre_activation_queue() -> None:
    snapshot = Snapshot(
        issues=(
            WorkflowIssue(
                80,
                "archiving",
                ("lead", "finalize-archive"),
                state="closed",
            ),
            WorkflowIssue(81, "unset", ("lead", "explore-change")),
        ),
        complete=True,
    )
    assert classify(snapshot) == ("formal", 80)


def test_shared_governance_exposes_concrete_complete_preflight_procedure() -> None:
    text = " ".join(AGENTS.read_text(encoding="utf-8").split())
    for required in (
        "complete repository-wide durable Issue snapshot",
        "observable enumeration completeness",
        "partial page",
        "role-local",
        "candidate-local",
        "indeterminate",
        "only then",
        "mapped Skill",
    ):
        assert required in text


def test_parked_or_reset_work_restarts_from_current_main_not_old_readiness() -> None:
    governance = " ".join(AGENTS.read_text(encoding="utf-8").split())
    orientation = " ".join(MIGRATION.read_text(encoding="utf-8").split())
    for required in (
        "later wake reconstructs the repaired current repository from scratch",
        "stale PASS/readiness",
    ):
        assert required in governance
    for required in (
        "parked/reset work",
        "then-current `main`",
        "Former PASS/readiness evidence remains historical evidence only",
        "fresh repository-wide reconstruction",
        "not a second recovery or dispatch rule",
    ):
        assert required in orientation
