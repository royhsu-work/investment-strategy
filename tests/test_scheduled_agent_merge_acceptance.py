"""Regressions for application-time merge acceptance."""

from __future__ import annotations

import json

import pytest

import investment_strategy.scheduled_agent_merge_acceptance as merge_acceptance
from investment_strategy.native_closing_preflight import (
    MergePresentationInput,
    MergeStrategy,
    NativeClosingPreflightResult,
    evaluate_native_closing_preflight,
    has_native_closing_reference,
)
from investment_strategy.scheduled_agent_merge_acceptance import (
    MergeAcceptanceSnapshot,
    merge_acceptance_allows,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    EnumerationEvidence,
    ObservationProvenance,
    RepositoryIssueSnapshot,
)

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
            "action": "merge-implementation-pr",
            "change": "prevent-native-closing-bypass",
            "result_kind": "merged",
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


def _merge_dispatch_preflight() -> DispatchPreflight:
    return DispatchPreflight(
        issues=(
            RepositoryIssueSnapshot(
                issue_number=159,
                change="prevent-native-closing-bypass",
                routing=("executor", "merge-implementation-pr"),  # type: ignore[arg-type]
                created_order=1,
            ),
        ),
        enumeration=EnumerationEvidence(
            observed_count=1,
            source_total_count=1,
            incomplete_results=False,
            exhausted=True,
            observation_provenance=ObservationProvenance.QUALIFIED,
        ),
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


def test_merge_acceptance_allows_explicit_historical_merged_carrier() -> None:
    accepted = _accepted(
        pr_open=False,
        historical_merged_carrier_allowed=True,
    )
    assert merge_acceptance_allows(accepted)
    assert not merge_acceptance_allows(
        _accepted(
            pr_open=False,
            historical_merged_carrier_allowed=True,
            current_head_sha="new-head",
        )
    )


def test_merge_action_requires_its_matching_review_action() -> None:
    comments = (
        {
            "id": 1,
            "created_at": "2026-08-27T06:00:00Z",
            "body": (f"Action: Reviewer / review-archive\nResult: PASS\nRevision: {HEAD}"),
        },
    )

    implementation = merge_acceptance._latest_matching_pass(
        comments,
        HEAD,
        required_review_action="review-implementation",
    )
    archive = merge_acceptance._latest_matching_pass(
        comments,
        HEAD,
        required_review_action="review-archive",
    )

    assert implementation[0] is None
    assert archive[0] == HEAD


def test_review_pass_carries_current_default_branch_revision() -> None:
    default_revision = "a" * 40
    comments = (
        {
            "id": 1,
            "created_at": "2026-08-27T06:00:00Z",
            "body": (
                "Action: Reviewer / review-implementation\n"
                "Result: PASS\n"
                f"Revision: {HEAD}\n"
                f"Default-Branch-Revision: {default_revision}"
            ),
        },
    )
    record = merge_acceptance._latest_matching_pass(
        comments,
        HEAD,
        required_review_action="review-implementation",
    )
    assert record[0] == HEAD
    assert record[5] == default_revision


def test_historical_merged_carrier_requires_current_main_ancestry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_revision = "a" * 40
    merge_commit = "b" * 40
    repository = "owner/repo"
    payload = {
        "state": "closed",
        "merged": True,
        "merge_commit_sha": merge_commit,
        "merged_at": "2026-08-27T06:00:00Z",
        "head": {
            "ref": "agent/prevent-native-closing-bypass",
            "sha": HEAD,
            "repo": {"full_name": repository},
        },
        "base": {
            "ref": "main",
            "repo": {"full_name": repository},
        },
    }
    reads: list[str] = []

    def fake_github_json(_repository: str, _token: str, path: str) -> object:
        reads.append(path)
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": current_revision}}
        if path == f"compare/{merge_commit}...main":
            return {"status": "ahead", "behind_by": 0}
        raise AssertionError(f"unexpected GitHub read: {path}")

    monkeypatch.setattr(merge_acceptance, "_github_json", fake_github_json)
    assert merge_acceptance._historical_merged_carrier_allowed(
        payload,
        repository=repository,
        token="",
        expected_head_sha=HEAD,
        current_revision=current_revision,
        expected_branch="agent/prevent-native-closing-bypass",
    )
    assert reads == ["", "git/ref/heads/main", f"compare/{merge_commit}...main"]


def test_native_close_recurrence_is_rejected_before_durable_merge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(issue_number=159, role="executor", action="merge-implementation-pr")
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
    )

    assert not result.applied
    assert result.reason == "fresh merge acceptance rejected"


def test_merge_effect_rechecks_acceptance_on_real_application_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(issue_number=159, role="executor", action="merge-implementation-pr")
    generated_messages = iter(
        (
            "Merge pull request #167\n\nRefs #159",
            "Merge pull request #167\n\nResolve #159",
        )
    )
    comments: tuple[dict[str, object], ...] = (
        {
            "id": 1,
            "created_at": "2026-08-27T06:00:00Z",
            "body": (
                "## REVIEW_RESULT\n"
                "Action: `Reviewer / review-implementation`\n"
                "Result: `PASS`\n"
                f"Revision: `{HEAD}`"
            ),
            "user": {"login": "royhsu-work"},
            "performed_via_github_app": {"id": 1},
        },
    )

    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        del repository, token
        if api_path == "pulls/167":
            return {
                "state": "open",
                "head": {"sha": HEAD},
                "body": "Refs #159",
            }
        if api_path == f"commits/{HEAD}/check-runs?per_page=100":
            return {
                "total_count": 2,
                "check_runs": [
                    {"status": "completed", "conclusion": "success"},
                    {"status": "completed", "conclusion": "success"},
                ],
            }
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    def fake_native_closing_result(
        *,
        repository: str,
        token: str,
        coordination_issue: int,
        pr_number: int,
        expected_head_sha: str,
        lifecycle_context: str,
        merge_strategy: MergeStrategy,
    ) -> NativeClosingPreflightResult:
        del token
        return evaluate_native_closing_preflight(
            MergePresentationInput(
                repository_full_name=repository,
                coordination_issue=coordination_issue,
                pr_number=pr_number,
                head_sha=expected_head_sha,
                observed_head_sha=expected_head_sha,
                lifecycle_context=lifecycle_context,
                merge_strategy=merge_strategy,
                pr_body="Refs #159",
                commit_messages=("Safe implementation commit",),
                commit_enumeration_complete=True,
                presentation_complete=True,
                generated_message=next(generated_messages),
            )
        )

    monkeypatch.setattr(merge_acceptance, "_github_json", fake_github_json)
    monkeypatch.setattr(
        merge_acceptance,
        "_paged_github_list",
        lambda *_args, **_kwargs: comments,
    )
    monkeypatch.setattr(
        merge_acceptance,
        "acquire_native_closing_merge_result",
        fake_native_closing_result,
    )
    monkeypatch.setattr(
        merge_acceptance,
        "acquire_current_github_preflight",
        lambda *_args, **_kwargs: _merge_dispatch_preflight(),
    )
    monkeypatch.setattr(
        merge_acceptance.GitHubEffectAdapter,
        "_source_still_current",
        lambda _self: True,
    )
    monkeypatch.setattr(
        merge_acceptance.GitHubEffectAdapter,
        "_guard_github_mutation",
        lambda _self, _payload: True,
    )

    applied: list[object] = []

    def forbidden_apply(_self: object, effect: object) -> None:
        applied.append(effect)
        raise AssertionError("merge adapter must not run after mutation-adjacent rejection")

    monkeypatch.setattr(merge_acceptance.GitHubEffectAdapter, "apply", forbidden_apply)
    monkeypatch.setattr(
        merge_acceptance.GitHubEffectAdapter,
        "observe_postcondition",
        lambda _self, _effect: True,
    )

    _batch, result = merge_acceptance.run_guarded_effect_application(
        _merge_worker_result(),
        source=source,
        repository="royhsu-work/investment-strategy",
        token=HEAD,
        current_revision=HEAD,
    )

    assert not result.applied
    assert result.reason == "effect precondition became stale"
    assert applied == []


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


def test_run_effect_application_forwards_current_revision_to_effect_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(issue_number=159, role="executor", action="merge-implementation-pr")
    captured: dict[str, object] = {}

    class FakeAdapter:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args
            captured.update(kwargs)

        def guard(self, _effect: object) -> bool:
            return True

        def apply(self, _effect: object) -> None:
            return None

        def observe_postcondition(self, _effect: object) -> bool:
            return True

    monkeypatch.setattr(merge_acceptance, "GitHubEffectAdapter", FakeAdapter)
    monkeypatch.setattr(
        merge_acceptance,
        "apply_effect_batch",
        lambda *args, **kwargs: merge_acceptance.ApplyResult(True, "applied"),
    )

    _batch, result = merge_acceptance.run_effect_application(
        _merge_worker_result(),
        source=source,
        repository="royhsu-work/investment-strategy",
        token="token",
        current_revision=HEAD,
    )

    assert result.applied
    assert captured["current_revision"] == HEAD
