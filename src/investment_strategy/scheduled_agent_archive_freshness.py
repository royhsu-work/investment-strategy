"""Independent, fail-closed archive branch provenance and snapshot qualification."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

_SHA = re.compile(r"^[0-9a-f]{40}$")
_CHANGE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_ARCHIVE_DATE = r"\d{4}-\d{2}-\d{2}"


def _blobs(payload: object) -> dict[str, str] | None:
    if not isinstance(payload, Mapping) or payload.get("truncated") is not False:
        return None
    tree = payload.get("tree")
    if not isinstance(tree, list):
        return None
    result: dict[str, str] = {}
    for entry in tree:
        if not isinstance(entry, Mapping):
            return None
        if entry.get("type") != "blob":
            continue
        path = entry.get("path")
        sha = entry.get("sha")
        if not isinstance(path, str) or not isinstance(sha, str) or not _SHA.fullmatch(sha):
            return None
        if path in result:
            return None
        result[path] = sha
    return result


def archive_branch_matches_current_change(
    read: Callable[[str, str, str], object],
    *,
    repository: str,
    token: str,
    change: str,
    source_revision: str,
    archive_revision: str,
) -> bool:
    """Verify source ancestry and byte-identical archived Change at the observed head.

    Both tree reads are mandatory, complete observations. A stale, ambiguous,
    truncated or source-disconnected branch can never become a PR consequence.
    """
    if (
        _CHANGE.fullmatch(change) is None
        or _SHA.fullmatch(source_revision) is None
        or _SHA.fullmatch(archive_revision) is None
    ):
        return False
    comparison = read(repository, token, f"compare/{source_revision}...{archive_revision}")
    if not isinstance(comparison, Mapping):
        return False
    base_commit = comparison.get("base_commit")
    if (
        comparison.get("status") not in {"ahead", "identical"}
        or comparison.get("behind_by") != 0
        or not isinstance(base_commit, Mapping)
        or base_commit.get("sha") != source_revision
    ):
        return False
    source = _blobs(read(repository, token, f"git/trees/{source_revision}?recursive=1"))
    archive = _blobs(read(repository, token, f"git/trees/{archive_revision}?recursive=1"))
    if source is None or archive is None:
        return False

    active_prefix = f"openspec/changes/{change}/"
    approved_files = {
        path.removeprefix(active_prefix): sha
        for path, sha in source.items()
        if path.startswith(active_prefix)
    }
    if not approved_files or any(path.startswith(active_prefix) for path in archive):
        return False
    archive_pattern = re.compile(
        rf"^openspec/changes/archive/({_ARCHIVE_DATE}-{re.escape(change)})/(.+)$"
    )
    archive_roots: set[str] = set()
    archived_files: dict[str, str] = {}
    for path, sha in archive.items():
        match = archive_pattern.fullmatch(path)
        if match is not None:
            archive_roots.add(match.group(1))
            archived_files[match.group(2)] = sha
    if len(archive_roots) != 1 or archived_files != approved_files:
        return False

    delta_pattern = re.compile(r"^specs/([a-z0-9][a-z0-9-]*)/spec\.md$")
    for relative_path in approved_files:
        match = delta_pattern.fullmatch(relative_path)
        if match is None:
            continue
        canonical = f"openspec/specs/{match.group(1)}/spec.md"
        if canonical not in archive:
            return False
    return True
