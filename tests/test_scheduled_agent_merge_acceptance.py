"""Regressions for #133 application-time merge acceptance."""

from __future__ import annotations

from investment_strategy.scheduled_agent_merge_acceptance import (
    MergeAcceptanceSnapshot,
    merge_acceptance_allows,
)


HEAD = "367ec125f919546443e2f006bec2a1ae1a78d4ce"


def _accepted(**overrides: object) -> MergeAcceptanceSnapshot:
    values: dict[str, object] = {
        "pr_open": True,
        "current_head_sha": HEAD,
        "expected_head_sha": HEAD,
        "reviewer_pass_head_sha": HEAD,
        "required_checks_pass": True,
        "non_closing_linkage": True,
        "contradictory_evidence": False,
        "human_input_fresh": True,
        "complete": True,
    }
    values.update(overrides)
    return MergeAcceptanceSnapshot(**values)  # type: ignore[arg-type]


def test_merge_acceptance_allows_only_fresh_exact_accepted_state() -> None:
    assert merge_acceptance_allows(_accepted())


def test_merge_acceptance_rejects_changed_acceptance_with_unchanged_head() -> None:
    cases = (
        _accepted(reviewer_pass_head_sha="stale"),
        _accepted(required_checks_pass=False),
        _accepted(non_closing_linkage=False),
        _accepted(contradictory_evidence=True),
        _accepted(human_input_fresh=False),
        _accepted(complete=False),
    )
    assert all(not merge_acceptance_allows(case) for case in cases)


def test_merge_acceptance_rejects_closed_or_changed_head() -> None:
    assert not merge_acceptance_allows(_accepted(pr_open=False))
    assert not merge_acceptance_allows(_accepted(current_head_sha="new-head"))
