"""Deterministic GitHub-native closing-reference merge preflight."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_CLOSING_KEYWORDS = r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"
_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")


class MergeStrategy(StrEnum):
    """Repository merge strategies with distinct effective presentation."""

    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


class NativeClosingDisposition(StrEnum):
    """Deterministic preflight result."""

    ALLOW = "ALLOW"
    REJECT = "REJECT"
    FAIL_CLOSED = "FAIL_CLOSED"


def explicit_merge_presentation(
    commit_title: str | None,
    commit_message: str | None,
) -> tuple[str | None, bool]:
    """Return one exact GitHub commit presentation when explicitly supplied."""
    if commit_title is None and commit_message is None:
        return None, True
    if not isinstance(commit_title, str) or not isinstance(commit_message, str):
        return None, False
    if (
        not commit_title
        or commit_title != commit_title.strip()
        or "\r" in commit_title
        or "\n" in commit_title
        or not commit_message
        or commit_message != commit_message.strip()
        or "\r" in commit_message
    ):
        return None, False
    return f"{commit_title}\n\n{commit_message}".rstrip(), True


@dataclass(frozen=True)
class MergePresentationInput:
    """Provenance-bound effective presentation for one exact PR head."""

    repository_full_name: str
    coordination_issue: int
    pr_number: int
    head_sha: str
    observed_head_sha: str
    lifecycle_context: str
    merge_strategy: MergeStrategy
    pr_body: str | None
    commit_messages: tuple[str, ...]
    commit_enumeration_complete: bool
    presentation_complete: bool
    generated_message: str | None
    commit_title: str | None = None
    commit_message: str | None = None


@dataclass(frozen=True)
class NativeClosingPreflightResult:
    """Result consumed by review and fresh merge application."""

    disposition: NativeClosingDisposition
    offending_surface: str | None = None

    @property
    def allowed(self) -> bool:
        return self.disposition is NativeClosingDisposition.ALLOW


def has_native_closing_reference(
    text: str,
    *,
    repository_full_name: str,
    coordination_issue: int,
) -> bool:
    """Return whether *text* closes the exact coordination Issue."""
    if coordination_issue <= 0:
        raise ValueError("coordination_issue must be positive")
    if not repository_full_name or repository_full_name.count("/") != 1:
        raise ValueError("repository_full_name must be owner/repository")

    effective_text = _FENCED_CODE.sub("", text)
    effective_text = _INLINE_CODE.sub("", effective_text)
    repository = re.escape(repository_full_name)
    issue = re.escape(str(coordination_issue))
    reference = rf"(?:(?:{repository})?#){issue}\b"
    pattern = re.compile(
        rf"\b{_CLOSING_KEYWORDS}\b\s*:?\s*{reference}",
        re.IGNORECASE,
    )
    return pattern.search(effective_text) is not None


def evaluate_native_closing_preflight(
    evidence: MergePresentationInput,
) -> NativeClosingPreflightResult:
    """Evaluate complete exact-head effective merge presentation."""
    if (
        not evidence.commit_enumeration_complete
        or not evidence.presentation_complete
        or evidence.head_sha != evidence.observed_head_sha
        or not evidence.head_sha
        or evidence.pr_number <= 0
        or not evidence.lifecycle_context
        or evidence.pr_body is None
    ):
        return NativeClosingPreflightResult(NativeClosingDisposition.FAIL_CLOSED)

    explicit_message, explicit_complete = explicit_merge_presentation(
        evidence.commit_title,
        evidence.commit_message,
    )
    if not explicit_complete:
        return NativeClosingPreflightResult(NativeClosingDisposition.FAIL_CLOSED)

    if evidence.merge_strategy in {MergeStrategy.MERGE, MergeStrategy.SQUASH}:
        if (
            evidence.generated_message is None
            or explicit_message is not None
            and evidence.generated_message != explicit_message
        ):
            return NativeClosingPreflightResult(NativeClosingDisposition.FAIL_CLOSED)
    elif evidence.merge_strategy is MergeStrategy.REBASE:
        if evidence.generated_message is not None or explicit_message is not None:
            return NativeClosingPreflightResult(NativeClosingDisposition.FAIL_CLOSED)
    else:
        return NativeClosingPreflightResult(NativeClosingDisposition.FAIL_CLOSED)

    surfaces: list[tuple[str, str]] = [("pr_body", evidence.pr_body)]
    if evidence.merge_strategy in {MergeStrategy.MERGE, MergeStrategy.REBASE}:
        surfaces.extend(
            (f"commit[{index}]", message) for index, message in enumerate(evidence.commit_messages)
        )
    if evidence.generated_message is not None:
        surfaces.append(("generated_message", evidence.generated_message))

    for surface, text in surfaces:
        if has_native_closing_reference(
            text,
            repository_full_name=evidence.repository_full_name,
            coordination_issue=evidence.coordination_issue,
        ):
            return NativeClosingPreflightResult(
                NativeClosingDisposition.REJECT,
                offending_surface=surface,
            )

    return NativeClosingPreflightResult(NativeClosingDisposition.ALLOW)
