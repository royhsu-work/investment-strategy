"""RED regressions for native-closing preflight consumption at merge application."""

from __future__ import annotations

from investment_strategy.native_closing_merge_application import (
    MergeApplicationEvidence,
    native_closing_merge_allows,
)
from investment_strategy.native_closing_preflight import MergeStrategy

HEAD = "a" * 40
STALE = "b" * 40


def _evidence(**overrides: object) -> MergeApplicationEvidence:
    values: dict[str, object] = {
        "repository_full_name": "royhsu-work/investment-strategy",
        "coordination_issue": 159,
        "pr_number": 167,
        "expected_head_sha": HEAD,
        "observed_head_sha": HEAD,
        "lifecycle_context": "implementation",
        "merge_strategy": MergeStrategy.MERGE,
        "pr_body": "Refs #159",
        "commit_messages": ("Implement approved behavior",),
        "commit_enumeration_complete": True,
        "presentation_complete": True,
        "generated_message": "Merge pull request #167\n\nRefs #159",
    }
    values.update(overrides)
    return MergeApplicationEvidence(**values)  # type: ignore[arg-type]


def test_merge_application_consumes_shared_native_closing_preflight() -> None:
    assert native_closing_merge_allows(_evidence())
    assert not native_closing_merge_allows(
        _evidence(commit_messages=("Resolve #159",))
    )


def test_merge_application_rejects_stale_or_incomplete_presentation() -> None:
    assert not native_closing_merge_allows(_evidence(observed_head_sha=STALE))
    assert not native_closing_merge_allows(_evidence(commit_enumeration_complete=False))
    assert not native_closing_merge_allows(_evidence(presentation_complete=False))


def test_merge_application_rejects_changed_effective_merge_message() -> None:
    assert not native_closing_merge_allows(
        _evidence(generated_message="Merge pull request #167\n\nFixes #159")
    )


def test_final_archive_merge_remains_non_closing() -> None:
    assert not native_closing_merge_allows(
        _evidence(
            lifecycle_context="archive",
            merge_strategy=MergeStrategy.SQUASH,
            generated_message="Finalize archive\n\nCloses #159",
        )
    )
