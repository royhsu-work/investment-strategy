"""Read-only OpenSpec archive provenance checks shared by application owners.

An archive is a derived snapshot of the *current* active Change.  The
presence of a branch or a PR cannot independently establish that provenance.
"""

from __future__ import annotations

import re
from collections.abc import Mapping


def archive_tree_matches_change(source_tree: object, archive_tree: object, change: str) -> bool:
    """Require a complete, byte-identical archived copy of the source Change.

    Git blob object IDs identify exact bytes.  An incomplete/truncated GitHub
    tree or multiple historical archive directories cannot prove the source.
    """

    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", change) is None:
        return False
    if not isinstance(source_tree, Mapping) or not isinstance(archive_tree, Mapping):
        return False
    if source_tree.get("truncated") is not False or archive_tree.get("truncated") is not False:
        return False

    def blobs(payload: Mapping[str, object]) -> dict[str, str] | None:
        items = payload.get("tree")
        if not isinstance(items, list):
            return None
        result: dict[str, str] = {}
        for item in items:
            if not isinstance(item, Mapping):
                return None
            path = item.get("path")
            if not isinstance(path, str) or path in result:
                return None
            if item.get("type") != "blob":
                continue
            sha = item.get("sha")
            if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
                return None
            result[path] = sha
        return result

    source_files = blobs(source_tree)
    archived_files = blobs(archive_tree)
    if source_files is None or archived_files is None:
        return False
    source_prefix = f"openspec/changes/{change}/"
    active = {
        path.removeprefix(source_prefix): sha
        for path, sha in source_files.items()
        if path.startswith(source_prefix)
    }
    if not active or "tasks.md" not in active:
        return False
    if any(path.startswith(source_prefix) for path in archived_files):
        return False
    archive_prefix = "openspec/changes/archive/"
    archive_paths: dict[str, dict[str, str]] = {}
    for path, sha in archived_files.items():
        if not path.startswith(archive_prefix):
            continue
        rest = path.removeprefix(archive_prefix)
        directory, separator, filename = rest.partition("/")
        if separator and directory.endswith(f"-{change}"):
            archive_paths.setdefault(directory, {})[filename] = sha
    return len(archive_paths) == 1 and next(iter(archive_paths.values())) == active
