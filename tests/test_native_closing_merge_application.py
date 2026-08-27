"""Regressions for native-closing preflight consumption at merge application."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

import investment_strategy.native_closing_merge_application as application
from investment_strategy.native_closing_merge_application import (
    MergeApplicationEvidence,
    acquire_native_closing_merge_result,
    native_closing_merge_allows,
)
from investment_strategy.native_closing_preflight import (
    MergeStrategy,
    NativeClosingDisposition,
)

HEAD = "a" * 40
STALE = "b" * 40
REPOSITORY = "royhsu-work/investment-strategy"


def _evidence(**overrides: object) -> MergeApplicationEvidence:
    values: dict[str, object] = {
        "repository_full_name": REPOSITORY,
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


def _repository_settings() -> Mapping[str, object]:
    return {
        "allow_merge_commit": True,
        "allow_squash_merge": True,
        "allow_rebase_merge": True,
        "merge_commit_title": "MERGE_MESSAGE",
        "merge_commit_message": "PR_TITLE",
        "squash_merge_commit_title": "COMMIT_OR_PR_TITLE",
        "squash_merge_commit_message": "COMMIT_MESSAGES",
    }


def _patch_github(
    monkeypatch: pytest.MonkeyPatch,
    *,
    observed_head: str = HEAD,
    commit_messages: tuple[str, ...] = ("Implement approved behavior",),
    declared_commit_count: int | None = None,
    pr_title: str = "OpenSpec: prevent native closing bypass",
) -> None:
    pr: Mapping[str, object] = {
        "head": {"sha": observed_head, "label": "royhsu-work:agent/prevent-native-closing-bypass"},
        "title": pr_title,
        "body": "Refs #159",
        "commits": len(commit_messages) if declared_commit_count is None else declared_commit_count,
    }

    def fake_github_json(repository: str, token: str, api_path: str = "") -> object:
        del token
        assert repository == REPOSITORY
        if api_path == "pulls/167":
            return pr
        if not api_path:
            return _repository_settings()
        raise AssertionError(f"unexpected API path: {api_path}")

    def fake_paged_list(
        repository: str,
        token: str,
        api_path: str,
    ) -> tuple[Mapping[str, object], ...]:
        del token
        assert repository == REPOSITORY
        assert api_path == "pulls/167/commits"
        return tuple({"commit": {"message": message}} for message in commit_messages)

    monkeypatch.setattr(application, "_github_json", fake_github_json)
    monkeypatch.setattr(application, "_paged_github_list", fake_paged_list)


def test_fresh_acquisition_rejects_included_native_closing_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_github(monkeypatch, commit_messages=("Resolve #159",))

    result = acquire_native_closing_merge_result(
        repository=REPOSITORY,
        token=HEAD,
        coordination_issue=159,
        pr_number=167,
        expected_head_sha=HEAD,
        lifecycle_context="implementation",
        merge_strategy=MergeStrategy.MERGE,
    )

    assert result.disposition is NativeClosingDisposition.REJECT


def test_fresh_acquisition_rejects_stale_head_or_incomplete_commit_enumeration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_github(monkeypatch, observed_head=STALE)
    stale = acquire_native_closing_merge_result(
        repository=REPOSITORY,
        token=HEAD,
        coordination_issue=159,
        pr_number=167,
        expected_head_sha=HEAD,
        lifecycle_context="implementation",
        merge_strategy=MergeStrategy.MERGE,
    )

    _patch_github(monkeypatch, declared_commit_count=2)
    incomplete = acquire_native_closing_merge_result(
        repository=REPOSITORY,
        token=HEAD,
        coordination_issue=159,
        pr_number=167,
        expected_head_sha=HEAD,
        lifecycle_context="implementation",
        merge_strategy=MergeStrategy.MERGE,
    )

    assert stale.disposition is NativeClosingDisposition.FAIL_CLOSED
    assert incomplete.disposition is NativeClosingDisposition.FAIL_CLOSED


def test_selected_squash_presentation_is_recomputed_from_current_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_github(monkeypatch, commit_messages=("Fixes #159",))

    result = acquire_native_closing_merge_result(
        repository=REPOSITORY,
        token=HEAD,
        coordination_issue=159,
        pr_number=167,
        expected_head_sha=HEAD,
        lifecycle_context="archive",
        merge_strategy=MergeStrategy.SQUASH,
    )

    assert result.disposition is NativeClosingDisposition.REJECT
