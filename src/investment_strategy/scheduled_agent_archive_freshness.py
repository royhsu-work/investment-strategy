"""Read-only OpenSpec archive provenance checks shared by application owners.

An archive is a derived snapshot of the *current* active Change.  The
presence of a branch or a PR cannot independently establish that provenance.
"""

from __future__ import annotations

import re
from collections.abc import Mapping


def archive_tree_evidence_complete(payload: object) -> bool:
    """Separate malformed or truncated Git evidence from a proven stale snapshot."""

    if not isinstance(payload, Mapping) or payload.get("truncated") is not False:
        return False
    items = payload.get("tree")
    if not isinstance(items, list):
        return False
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            return False
        path = item.get("path")
        if not isinstance(path, str) or path in seen:
            return False
        seen.add(path)
        if item.get("type") == "blob" and (
            not isinstance(item.get("sha"), str)
            or re.fullmatch(r"[0-9a-f]{40}", item["sha"]) is None
        ):
            return False
    return True


def archive_tree_matches_change(source_tree: object, archive_tree: object, change: str) -> bool:
    """Require a complete, byte-identical archived copy of the source Change.

    Git blob object IDs identify exact bytes.  An incomplete/truncated GitHub
    tree or multiple historical archive directories cannot prove the source.
    """

    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", change) is None:
        return False
    if not archive_tree_evidence_complete(source_tree) or not archive_tree_evidence_complete(
        archive_tree
    ):
        return False
    if not isinstance(source_tree, Mapping) or not isinstance(archive_tree, Mapping):
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
    archive_file_paths: set[str] = set()
    for path, sha in archived_files.items():
        if not path.startswith(archive_prefix):
            continue
        rest = path.removeprefix(archive_prefix)
        directory, separator, filename = rest.partition("/")
        if separator and directory.endswith(f"-{change}"):
            archive_paths.setdefault(directory, {})[filename] = sha
            archive_file_paths.add(path)
    if len(archive_paths) != 1 or next(iter(archive_paths.values())) != active:
        return False

    # Archive may remove its active source, add its exact historical snapshot,
    # and update canonical specs named by this approved Change.  Any other
    # blob mutation is not an OpenSpec archive consequence, even if its PR is
    # absent or its branch happens to be descended from current main.
    approved_canonical = {
        f"openspec/specs/{parts[1]}/spec.md"
        for relative in active
        if (parts := relative.split("/"))[:1] == ["specs"]
        and len(parts) == 3
        and parts[2] == "spec.md"
    }
    changed_paths = {
        path
        for path in set(source_files) | set(archived_files)
        if source_files.get(path) != archived_files.get(path)
    }
    return changed_paths <= (
        {source_prefix + relative for relative in active} | archive_file_paths | approved_canonical
    )
