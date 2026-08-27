"""Deterministic GitHub-native closing-reference classification."""

from __future__ import annotations

import re

_CLOSING_KEYWORDS = r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"
_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")


def has_native_closing_reference(
    text: str,
    *,
    repository_full_name: str,
    coordination_issue: int,
) -> bool:
    """Return whether *text* closes the exact coordination Issue.

    GitHub recognizes closing keywords case-insensitively when followed by an
    Issue reference. This classifier is deliberately identity-scoped: it
    accepts shorthand references for the current repository and fully
    qualified references only for that same repository. Code examples are
    presentation, not effective closing grammar for this repository guard.
    """
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
