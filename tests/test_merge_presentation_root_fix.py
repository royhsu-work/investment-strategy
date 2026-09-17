from investment_strategy.native_closing_merge_application import (
    _generated_merge_message,
)
from investment_strategy.native_closing_preflight import (
    MergePresentationInput,
    MergeStrategy,
    NativeClosingDisposition,
    evaluate_native_closing_preflight,
    explicit_merge_presentation,
)
from investment_strategy.scheduled_agent_application_materialization import (
    materialization_message_is_safe,
)
from investment_strategy.scheduled_agent_effects import _github_mutation_structurally_valid
from investment_strategy.scheduled_agent_runtime import WorkerRequest

REPOSITORY = "royhsu-work/investment-strategy"
ISSUE = 159
HEAD = "a" * 40
TITLE = "OpenSpec: prevent native closing bypass"
MESSAGE = "Refs #159"


def _presentation_input(**overrides: object) -> MergePresentationInput:
    values: dict[str, object] = {
        "repository_full_name": REPOSITORY,
        "coordination_issue": ISSUE,
        "pr_number": 167,
        "head_sha": HEAD,
        "observed_head_sha": HEAD,
        "lifecycle_context": "implementation",
        "merge_strategy": MergeStrategy.SQUASH,
        "pr_body": "Refs #159",
        "commit_messages": ("Resolve #159",),
        "commit_enumeration_complete": True,
        "presentation_complete": True,
        "generated_message": f"{TITLE}\n\n{MESSAGE}",
        "commit_title": TITLE,
        "commit_message": MESSAGE,
    }
    values.update(overrides)
    return MergePresentationInput(**values)  # type: ignore[arg-type]


def test_explicit_merge_presentation_is_one_exact_plan() -> None:
    assert explicit_merge_presentation(TITLE, MESSAGE) == (f"{TITLE}\n\n{MESSAGE}", True)
    assert explicit_merge_presentation(None, None) == (None, True)
    assert explicit_merge_presentation(TITLE, None)[1] is False
    assert explicit_merge_presentation(TITLE + "\n", MESSAGE)[1] is False
    assert explicit_merge_presentation(TITLE, " " + MESSAGE)[1] is False


def test_explicit_squash_plan_allows_safe_presentation_of_unsafe_history() -> None:
    result = evaluate_native_closing_preflight(_presentation_input())
    assert result.disposition is NativeClosingDisposition.ALLOW

    unsafe = evaluate_native_closing_preflight(
        _presentation_input(
            commit_message="Resolves #159",
            generated_message=f"{TITLE}\n\nResolves #159",
        )
    )
    assert unsafe.disposition is NativeClosingDisposition.REJECT


def test_application_reconstructs_explicit_squash_presentation() -> None:
    pr = {
        "title": TITLE,
        "body": "Refs #159",
        "head": {
            "ref": "agent/prevent-native-closing-bypass",
            "repo": {"owner": {"login": "royhsu-work"}},
        },
    }
    settings = {
        "allow_merge_commit": True,
        "allow_squash_merge": True,
        "allow_rebase_merge": True,
        "merge_commit_title": "MERGE_MESSAGE",
        "merge_commit_message": "PR_TITLE",
        "squash_merge_commit_title": "COMMIT_OR_PR_TITLE",
        "squash_merge_commit_message": "COMMIT_MESSAGES",
    }
    generated, complete = _generated_merge_message(
        repository=settings,
        pr=pr,
        pr_number=167,
        strategy=MergeStrategy.SQUASH,
        commit_messages=("Resolve #159",),
        commit_title=TITLE,
        commit_message=MESSAGE,
    )
    assert complete
    assert generated == f"{TITLE}\n\n{MESSAGE}"


def test_merge_effect_contract_carries_both_presentation_fields() -> None:
    source = WorkerRequest(ISSUE, "executor", "merge-implementation-pr")
    base = {
        "issue_number": ISSUE,
        "operation": "pull-request-merge",
        "number": 167,
        "expected_head_sha": HEAD,
        "merge_method": "squash",
    }
    assert _github_mutation_structurally_valid(
        source,
        {**base, "commit_title": TITLE, "commit_message": MESSAGE},
    )
    assert not _github_mutation_structurally_valid(
        source,
        {**base, "commit_title": TITLE},
    )
    assert not _github_mutation_structurally_valid(
        source,
        {**base, "merge_method": "rebase", "commit_title": TITLE, "commit_message": MESSAGE},
    )


def test_materialization_producer_keeps_issue_open() -> None:
    assert materialization_message_is_safe(
        "Implement approved Change",
        repository=REPOSITORY,
        issue_number=ISSUE,
    )
    assert not materialization_message_is_safe(
        "Resolve #159",
        repository=REPOSITORY,
        issue_number=ISSUE,
    )
