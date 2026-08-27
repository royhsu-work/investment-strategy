"""Fresh merge-application consumption of the shared native-closing preflight."""

from __future__ import annotations

from dataclasses import dataclass

from investment_strategy.native_closing_preflight import (
    MergePresentationInput,
    MergeStrategy,
    NativeClosingPreflightResult,
    evaluate_native_closing_preflight,
)


@dataclass(frozen=True)
class MergeApplicationEvidence:
    """Exact merge evidence acquired immediately before a merge mutation."""

    repository_full_name: str
    coordination_issue: int
    pr_number: int
    expected_head_sha: str
    observed_head_sha: str
    lifecycle_context: str
    merge_strategy: MergeStrategy
    pr_body: str | None
    commit_messages: tuple[str, ...]
    commit_enumeration_complete: bool
    presentation_complete: bool
    generated_message: str | None


def native_closing_merge_result(
    evidence: MergeApplicationEvidence,
) -> NativeClosingPreflightResult:
    """Evaluate application evidence with the repository-owned deterministic preflight."""

    return evaluate_native_closing_preflight(
        MergePresentationInput(
            repository_full_name=evidence.repository_full_name,
            coordination_issue=evidence.coordination_issue,
            pr_number=evidence.pr_number,
            head_sha=evidence.expected_head_sha,
            observed_head_sha=evidence.observed_head_sha,
            lifecycle_context=evidence.lifecycle_context,
            merge_strategy=evidence.merge_strategy,
            pr_body=evidence.pr_body,
            commit_messages=evidence.commit_messages,
            commit_enumeration_complete=evidence.commit_enumeration_complete,
            presentation_complete=evidence.presentation_complete,
            generated_message=evidence.generated_message,
        )
    )


def native_closing_merge_allows(evidence: MergeApplicationEvidence) -> bool:
    """Return whether fresh application evidence permits the merge mutation."""

    return native_closing_merge_result(evidence).allowed
