"""Regressions for application-time merge acceptance."""

from __future__ import annotations

import json

import pytest

import investment_strategy.scheduled_agent_merge_acceptance as merge_acceptance
from investment_strategy.native_closing_preflight import has_native_closing_reference
from investment_strategy.scheduled_agent_merge_acceptance import (
    MergeAcceptanceSnapshot,
    merge_acceptance_allows,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest

HEAD = "367ec125f919546443e2f006bec2a1ae1a78d4ce"
STALE_HEAD = "0000000000000000000000000000000000000000"
CORRECTED_HEAD = "1111111111111111111111111111111111111111"


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


def _merge_worker_result() -> str:
    return json.dumps(
        {
            "issue_number": 159,
            "role": "executor",
            "action": "merge-pr",
            "result_content": "MERGE_RESULT",
            "requested_effects": [
                {
                    "kind": "github-mutation",
                    "payload_json": json.dumps(
                        {
                            "issue_number": 159,
                            "operation": "pull-request-merge",
                            "number": 167,
                            "expected_head_sha": HEAD,
                            "merge_method": "merge",
                        }
                    ),
                }
            ],
        }
    )


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


def test_corrected_successor_requires_new_exact_head_review_checks_and_preflight() -> None:
    old_review = _accepted(
        current_head_sha=CORRECTED_HEAD,
        expected_head_sha=CORRECTED_HEAD,
        reviewer_pass_head_sha=HEAD,
    )
    new_review_without_checks = _accepted(
        current_head_sha=CORRECTED_HEAD,
        expected_head_sha=CORRECTED_HEAD,
        reviewer_pass_head_sha=CORRECTED_HEAD,
        required_checks_pass=False,
    )
    new_review_without_preflight = _accepted(
        current_head_sha=CORRECTED_HEAD,
        expected_head_sha=CORRECTED_HEAD,
        reviewer_pass_head_sha=CORRECTED_HEAD,
        native_closing_preflight_allowed=False,
    )
    fully_regated = _accepted(
        current_head_sha=CORRECTED_HEAD,
        expected_head_sha=CORRECTED_HEAD,
        reviewer_pass_head_sha=CORRECTED_HEAD,
    )

    assert not merge_acceptance_allows(old_review)
    assert not merge_acceptance_allows(new_review_without_checks)
    assert not merge_acceptance_allows(new_review_without_preflight)
    assert merge_acceptance_allows(fully_regated)


def test_native_close_recurrence_is_rejected_before_durable_merge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(issue_number=159, role="executor", action="merge-pr")
    rejected = _accepted(native_closing_preflight_allowed=False)
    monkeypatch.setattr(
        merge_acceptance,
        "acquire_merge_acceptance_snapshot",
        lambda **_kwargs: rejected,
    )

    def forbidden_durable_apply(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("durable merge application must not run after preflight rejection")

    monkeypatch.setattr(merge_acceptance, "run_effect_application", forbidden_durable_apply)

    _batch, result = merge_acceptance.run_guarded_effect_application(
        _merge_worker_result(),
        source=source,
        repository="royhsu-work/investment-strategy",
        token=HEAD,
        workflow_text="unused before rejection",
    )

    assert not result.applied
    assert result.reason == "fresh merge acceptance rejected"


def test_merge_effect_rechecks_acceptance_after_initial_clearance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(issue_number=159, role="executor", action="merge-pr")
    snapshots = iter((_accepted(), _accepted(native_closing_preflight_allowed=False)))
    monkeypatch.setattr(
        merge_acceptance,
        "acquire_merge_acceptance_snapshot",
        lambda **_kwargs: next(snapshots),
    )

    def fake_run_effect_application(
        raw_worker_result: str,
        *,
        source: WorkerRequest,
        repository: str,
        token: str,
        workflow_text: str,
        pre_apply_guard: object | None = None,
    ) -> tuple[object, object]:
        del repository, token, workflow_text
        batch = merge_acceptance.parse_effect_batch(raw_worker_result, source)
        assert callable(pre_apply_guard)
        allowed = pre_apply_guard(batch.effects[0])
        assert allowed is False
        return batch, merge_acceptance.ApplyResult(False, "effect precondition became stale")

    monkeypatch.setattr(merge_acceptance, "run_effect_application", fake_run_effect_application)

    _batch, result = merge_acceptance.run_guarded_effect_application(
        _merge_worker_result(),
        source=source,
        repository="royhsu-work/investment-strategy",
        token=HEAD,
        workflow_text="current workflow",
    )

    assert not result.applied
    assert result.reason == "effect precondition became stale"


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
