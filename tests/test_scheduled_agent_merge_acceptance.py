"""Regressions for application-time merge acceptance."""

from __future__ import annotations

import pytest

from investment_strategy.native_closing_preflight import has_native_closing_reference
from investment_strategy.scheduled_agent_merge_acceptance import (
    MergeAcceptanceSnapshot,
    merge_acceptance_allows,
)

HEAD = "367ec125f919546443e2f006bec2a1ae1a78d4ce"
STALE_HEAD = "0000000000000000000000000000000000000000"


def _accepted(**overrides: object) -> MergeAcceptanceSnapshot:
    values: dict[str, object] = {
        "pr_open": True,
        "current_head_sha": HEAD,
        "expected_head_sha": HEAD,
        "reviewer_pass_head_sha": HEAD,
        "required_checks_pass": True,
        "non_closing_linkage": True,
        "native_closing_preflight_allowed": True,
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
        _accepted(reviewer_pass_head_sha=STALE_HEAD),
        _accepted(required_checks_pass=False),
        _accepted(non_closing_linkage=False),
        _accepted(native_closing_preflight_allowed=False),
        _accepted(contradictory_evidence=True),
        _accepted(human_input_fresh=False),
        _accepted(complete=False),
    )
    assert all(not merge_acceptance_allows(case) for case in cases)


def test_merge_acceptance_rejects_closed_or_changed_head() -> None:
    assert not merge_acceptance_allows(_accepted(pr_open=False))
    assert not merge_acceptance_allows(_accepted(current_head_sha="new-head"))


@pytest.mark.parametrize(
    "text",
    (
        "Resolve #159",
        "resolves #159.",
        "Resolved: #159",
        "Fix #159",
        "fixes: #159",
        "Fixed #159,",
        "Close #159",
        "closes: #159",
        "Closed #159.",
    ),
)
def test_native_closing_classifier_detects_exact_coordination_issue(text: str) -> None:
    assert has_native_closing_reference(
        text,
        repository_full_name="royhsu-work/investment-strategy",
        coordination_issue=159,
    )


@pytest.mark.parametrize(
    "text",
    (
        "Refs #159",
        "Related to #159",
        "Resolve #158",
        "Fixes #160",
        "The word resolve appears without an issue reference.",
        "`Resolve #159`",
        "```text\nResolve #159\n```",
    ),
)
def test_native_closing_classifier_preserves_non_closing_and_code_boundaries(text: str) -> None:
    assert not has_native_closing_reference(
        text,
        repository_full_name="royhsu-work/investment-strategy",
        coordination_issue=159,
    )


def test_native_closing_classifier_matches_same_repository_qualified_reference() -> None:
    assert has_native_closing_reference(
        "Resolves royhsu-work/investment-strategy#159",
        repository_full_name="royhsu-work/investment-strategy",
        coordination_issue=159,
    )
    assert not has_native_closing_reference(
        "Resolves other/repository#159",
        repository_full_name="royhsu-work/investment-strategy",
        coordination_issue=159,
    )
