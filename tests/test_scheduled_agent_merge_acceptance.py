"""Regressions for #133 application-time merge acceptance."""

from __future__ import annotations

import sys

import investment_strategy.scheduled_agent_merge_acceptance as acceptance
from investment_strategy.scheduled_agent_live_evidence import (
    LiveRuntimeEvidence,
    render_live_runtime_evidence,
)
from investment_strategy.scheduled_agent_merge_acceptance import (
    MergeAcceptanceSnapshot,
    merge_acceptance_allows,
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


def test_apply_rejects_when_default_branch_advanced_before_effect_application(
    monkeypatch, tmp_path
) -> None:
    worker_result = tmp_path / "scheduled-agent-result.json"
    worker_result.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GITHUB_REPOSITORY", "royhsu-work/investment-strategy")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("AUTHORIZED_ISSUE", "133")
    monkeypatch.setenv("AUTHORIZED_ROLE", "executor")
    monkeypatch.setenv("AUTHORIZED_ACTION", "implement-change")
    monkeypatch.setenv("RUNTIME_REVISION", HEAD)
    monkeypatch.setenv("DEFAULT_BRANCH", "main")
    monkeypatch.setattr(sys, "argv", ["scheduled_agent_merge_acceptance", str(worker_result)])
    monkeypatch.setattr(
        acceptance,
        "_github_json",
        lambda repository, token, api_path: {"commit": {"sha": STALE_HEAD}},
    )

    effect_application_called = False

    def unexpected_effect_application(*args, **kwargs):
        nonlocal effect_application_called
        effect_application_called = True
        raise AssertionError("stale runtime revision must reject before effect application")

    monkeypatch.setattr(
        acceptance,
        "run_guarded_effect_application",
        unexpected_effect_application,
    )

    assert acceptance.main() == 1
    assert not effect_application_called


def test_live_runtime_evidence_binds_exact_run_revision_and_apply_outcome() -> None:
    source = WorkerRequest(133, "executor", "implement-change")
    evidence = LiveRuntimeEvidence(
        run_id="123456789",
        run_attempt="2",
        revision=HEAD,
        event_name="schedule",
        source=source,
        applied=True,
        continuation=WorkerRequest(133, "reviewer", "review-implementation"),
    )

    body = render_live_runtime_evidence(evidence)

    assert "LIVE_RUNTIME_EVIDENCE" in body
    assert "Actions run: `123456789` (attempt `2`)" in body
    assert f"Revision: `{HEAD}`" in body
    assert "Trigger: `schedule`" in body
    assert "Dispatch: `AUTHORIZE` → `#133 / Executor / implement-change`" in body
    assert "Model invocation: `completed`" in body
    assert "Apply: `applied`" in body
    assert "Continuation: `#133 / Reviewer / review-implementation`" in body
    assert "Audit evidence only; this comment is not dispatch authorization." in body
