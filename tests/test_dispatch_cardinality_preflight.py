"""Fixture-driven RED coverage for #105 dispatch cardinality preflight."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"


@dataclass(frozen=True)
class WorkflowIssue:
    number: int
    change: str
    routing: tuple[str, str] | None
    state: Literal["open", "closed"] = "open"
    created_order: int = 0


@dataclass(frozen=True)
class Snapshot:
    issues: tuple[WorkflowIssue, ...]
    complete: bool


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


def test_partial_enumeration_is_indeterminate_even_when_only_queue_is_visible() -> None:
    snapshot = Snapshot(
        issues=(WorkflowIssue(41, "unset", ("lead", "explore-change")),),
        complete=False,
    )
    assert classify(snapshot) == ("indeterminate", None)


def test_two_formal_workflows_fail_closed_without_winner_selection() -> None:
    snapshot = Snapshot(
        issues=(
            WorkflowIssue(50, "first", ("executor", "implement-change"), created_order=1),
            WorkflowIssue(51, "second", ("reviewer", "review-openspec"), created_order=2),
        ),
        complete=True,
    )
    assert classify(snapshot) == ("fail-closed", None)


def test_terminal_pending_work_wins_over_pre_activation_queue() -> None:
    snapshot = Snapshot(
        issues=(
            WorkflowIssue(
                60,
                "archiving",
                ("lead", "finalize-archive"),
                state="closed",
            ),
            WorkflowIssue(61, "unset", ("lead", "explore-change")),
        ),
        complete=True,
    )
    assert classify(snapshot) == ("formal", 60)


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
