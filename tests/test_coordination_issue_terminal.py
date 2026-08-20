from dataclasses import dataclass
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class TerminalDisposition(Enum):
    ACTIVE = "active"
    FINISH_CLOSE = "finish-close"
    REOBSERVE_CLOSE = "reobserve-close"
    PREMATURE_CLOSE = "premature-close"
    TERMINAL_HISTORY = "terminal-history"


@dataclass(frozen=True)
class TerminalState:
    issue_open: bool
    lifecycle_complete: bool
    close_observed: bool


def classify_terminal_state(state: TerminalState) -> TerminalDisposition:
    """Deterministic executable model of the approved terminal/recovery contract."""
    if state.issue_open:
        if state.close_observed:
            raise ValueError("an open Issue cannot already have observed final close")
        if state.lifecycle_complete:
            return TerminalDisposition.FINISH_CLOSE
        return TerminalDisposition.ACTIVE

    if not state.lifecycle_complete:
        return TerminalDisposition.PREMATURE_CLOSE
    if not state.close_observed:
        return TerminalDisposition.REOBSERVE_CLOSE
    return TerminalDisposition.TERMINAL_HISTORY


def counts_as_formal_wip(state: TerminalState) -> bool:
    return classify_terminal_state(state) != TerminalDisposition.TERMINAL_HISTORY


def test_archive_merge_uses_non_closing_linkage_and_keeps_issue_open() -> None:
    governance = read("agents/AGENTS.md")
    merge_skill = read("agents/skills/merge-pr/SKILL.md")
    lifecycle = read("agents/skills/lifecycle-finalize/SKILL.md")

    assert "final Archive PR" in governance
    assert "non-closing" in governance
    assert "Refs #" in governance
    assert "Archive merge" in merge_skill
    assert "remains open" in merge_skill
    assert "LIFECYCLE_COMPLETE" in lifecycle
    assert "close" in lifecycle
    complete_at = lifecycle.index("LIFECYCLE_COMPLETE")
    close_at = lifecycle.index("close", complete_at)
    assert complete_at < close_at


def test_durable_completion_with_missing_close_remains_actionable() -> None:
    state = TerminalState(
        issue_open=True,
        lifecycle_complete=True,
        close_observed=False,
    )

    assert classify_terminal_state(state) is TerminalDisposition.FINISH_CLOSE
    assert counts_as_formal_wip(state)


def test_closed_completion_without_reobservation_requires_reobservation() -> None:
    state = TerminalState(
        issue_open=False,
        lifecycle_complete=True,
        close_observed=False,
    )

    assert classify_terminal_state(state) is TerminalDisposition.REOBSERVE_CLOSE
    assert counts_as_formal_wip(state)


def test_premature_close_without_valid_completion_is_recovery_input() -> None:
    state = TerminalState(
        issue_open=False,
        lifecycle_complete=False,
        close_observed=True,
    )

    assert classify_terminal_state(state) is TerminalDisposition.PREMATURE_CLOSE
    assert counts_as_formal_wip(state)


def test_closed_with_valid_completion_is_terminal_history_not_formal_wip() -> None:
    state = TerminalState(
        issue_open=False,
        lifecycle_complete=True,
        close_observed=True,
    )

    assert classify_terminal_state(state) is TerminalDisposition.TERMINAL_HISTORY
    assert not counts_as_formal_wip(state)


def test_open_unfinished_issue_is_normal_active_work() -> None:
    state = TerminalState(
        issue_open=True,
        lifecycle_complete=False,
        close_observed=False,
    )

    assert classify_terminal_state(state) is TerminalDisposition.ACTIVE
    assert counts_as_formal_wip(state)


def test_contradictory_open_and_close_observed_state_fails_closed() -> None:
    state = TerminalState(
        issue_open=True,
        lifecycle_complete=True,
        close_observed=True,
    )

    try:
        classify_terminal_state(state)
    except ValueError as exc:
        assert "open Issue" in str(exc)
    else:
        raise AssertionError("contradictory durable terminal state must fail closed")
