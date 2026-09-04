from investment_strategy.native_closing_preflight import (
    MergePresentationInput,
    MergeStrategy,
    NativeClosingDisposition,
    evaluate_native_closing_preflight,
)

REPO = "royhsu-work/investment-strategy"
ISSUE = 159
HEAD = "a" * 40


def _input(**overrides: object) -> MergePresentationInput:
    values: dict[str, object] = {
        "repository_full_name": REPO,
        "coordination_issue": ISSUE,
        "pr_number": 167,
        "head_sha": HEAD,
        "observed_head_sha": HEAD,
        "lifecycle_context": "implementation",
        "merge_strategy": MergeStrategy.MERGE,
        "pr_body": "Refs #159",
        "commit_messages": ("Implement classifier",),
        "commit_enumeration_complete": True,
        "presentation_complete": True,
        "generated_message": "Merge pull request #167\n\nOpenSpec: prevent native closing bypass",
    }
    values.update(overrides)
    return MergePresentationInput(**values)  # type: ignore[arg-type]


def test_merge_preflight_requires_complete_exact_head_evidence() -> None:
    commits = evaluate_native_closing_preflight(_input(commit_enumeration_complete=False))
    presentation = evaluate_native_closing_preflight(_input(presentation_complete=False))
    stale_head = evaluate_native_closing_preflight(_input(observed_head_sha="b" * 40))

    assert commits.disposition is NativeClosingDisposition.FAIL_CLOSED
    assert presentation.disposition is NativeClosingDisposition.FAIL_CLOSED
    assert stale_head.disposition is NativeClosingDisposition.FAIL_CLOSED


def test_merge_commit_checks_pr_body_commits_and_generated_message() -> None:
    safe = evaluate_native_closing_preflight(_input())
    commit_close = evaluate_native_closing_preflight(_input(commit_messages=("Resolve #159",)))
    body_close = evaluate_native_closing_preflight(_input(pr_body="Closes #159"))
    generated_close = evaluate_native_closing_preflight(_input(generated_message="Fixes #159"))

    assert safe.allowed
    assert not commit_close.allowed
    assert not body_close.allowed
    assert not generated_close.allowed


def test_squash_checks_effective_generated_message_inputs() -> None:
    safe = evaluate_native_closing_preflight(
        _input(
            merge_strategy=MergeStrategy.SQUASH,
            generated_message="OpenSpec: prevent native closing bypass\n\nRefs #159",
        )
    )
    closing = evaluate_native_closing_preflight(
        _input(
            merge_strategy=MergeStrategy.SQUASH,
            generated_message="OpenSpec: prevent native closing bypass\n\nResolves #159",
        )
    )

    assert safe.allowed
    assert not closing.allowed


def test_squash_scans_only_commit_messages_that_reach_effective_presentation() -> None:
    discarded_commit_message = evaluate_native_closing_preflight(
        _input(
            merge_strategy=MergeStrategy.SQUASH,
            commit_messages=("Resolve #159",),
            generated_message="OpenSpec: prevent native closing bypass\n\nRefs #159",
        )
    )
    propagated_commit_message = evaluate_native_closing_preflight(
        _input(
            merge_strategy=MergeStrategy.SQUASH,
            commit_messages=("Resolve #159",),
            generated_message="OpenSpec: prevent native closing bypass\n\nResolve #159",
        )
    )

    assert discarded_commit_message.allowed
    assert propagated_commit_message.disposition is NativeClosingDisposition.REJECT


def test_rebase_checks_every_effective_commit_message() -> None:
    safe = evaluate_native_closing_preflight(
        _input(
            merge_strategy=MergeStrategy.REBASE,
            generated_message=None,
            commit_messages=("Refs #159", "Continue implementation"),
        )
    )
    closing = evaluate_native_closing_preflight(
        _input(
            merge_strategy=MergeStrategy.REBASE,
            generated_message=None,
            commit_messages=("Refs #159", "Resolve #159"),
        )
    )

    assert safe.allowed
    assert not closing.allowed


def test_strategy_specific_presentation_must_be_unambiguous() -> None:
    merge = evaluate_native_closing_preflight(
        _input(merge_strategy=MergeStrategy.MERGE, generated_message=None)
    )
    squash = evaluate_native_closing_preflight(
        _input(merge_strategy=MergeStrategy.SQUASH, generated_message=None)
    )
    rebase = evaluate_native_closing_preflight(
        _input(merge_strategy=MergeStrategy.REBASE, generated_message=None)
    )

    assert not merge.allowed
    assert not squash.allowed
    assert rebase.allowed


def test_unrelated_issue_closing_reference_remains_allowed() -> None:
    result = evaluate_native_closing_preflight(
        _input(
            pr_body="Closes #999",
            commit_messages=("Fixes #998",),
            generated_message="Resolves #997",
        )
    )
    assert result.allowed
