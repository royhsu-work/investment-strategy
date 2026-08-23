"""Regressions for #133 application-time merge acceptance."""

from __future__ import annotations

from investment_strategy.scheduled_agent_effects import ApplyResult
from investment_strategy.scheduled_agent_merge_acceptance import (
    LiveRuntimeEvidence,
    MergeAcceptanceSnapshot,
    merge_acceptance_allows,
    render_live_runtime_evidence,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest

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
        _accepted(contradictory_evidence=True),
        _accepted(human_input_fresh=False),
        _accepted(complete=False),
    )
    assert all(not merge_acceptance_allows(case) for case in cases)


def test_merge_acceptance_rejects_closed_or_changed_head() -> None:
    assert not merge_acceptance_allows(_accepted(pr_open=False))
    assert not merge_acceptance_allows(_accepted(current_head_sha="new-head"))


def test_live_runtime_evidence_binds_exact_run_revision_and_apply_outcome() -> None:
    source = WorkerRequest(133, "executor", "implement-change")
    evidence = LiveRuntimeEvidence(
        run_id="123456789",
        run_attempt="2",
        revision=HEAD,
        event_name="schedule",
        source=source,
        result=ApplyResult(
            applied=True,
            reason="applied",
            continuation=WorkerRequest(133, "reviewer", "review-implementation"),
        ),
    )

    body = render_live_runtime_evidence(evidence)

    assert "LIVE_RUNTIME_EVIDENCE" in body
    assert "Actions run: `123456789` (attempt `2`)" in body
    assert f"Revision: `{HEAD}`" in body
    assert "Trigger: `schedule`" in body
    assert "Dispatch: `AUTHORIZE` → `#133 / Executor / implement-change`" in body
    assert "Model invocation: `completed`" in body
    assert "Apply: `applied` (`applied`)" in body
    assert "Continuation: `#133 / Reviewer / review-implementation`" in body
    assert "Audit evidence only; this comment is not dispatch authorization." in body
