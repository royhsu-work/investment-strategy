"""Independent, fail-closed archive branch provenance and snapshot qualification."""

from __future__ import annotations

import hashlib
import io
import json
import re
from collections.abc import Callable, Mapping
from urllib.parse import quote
from zipfile import BadZipFile, ZipFile

from investment_strategy.scheduled_agent_carrier import read_github_artifact_bytes

_SHA = re.compile(r"^[0-9a-f]{40}$")
_CHANGE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_ARCHIVE_DATE = r"\d{4}-\d{2}-\d{2}"
_ARCHIVE_WORKFLOW = ".github/workflows/openspec-archive.yml"
_ARCHIVE_ARTIFACT = "openspec-archive-handoff"
_ARCHIVE_HANDOFF_FILE = "archive-handoff.json"
_MAX_HANDOFF_ZIP = 65_536


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


def archive_stale_branch_is_recoverable(
    read: Callable[[str, str, str], object],
    *,
    repository: str,
    token: str,
    change: str,
    source_revision: str,
    archive_revision: str,
) -> bool:
    """Recognize only a single historical Change archive on common source ancestry.

    This is *not* archive readiness: it merely permits the existing producer to
    regenerate a stale ref non-forcibly. Foreign or competing roots fail closed.
    """
    if (
        _CHANGE.fullmatch(change) is None
        or _SHA.fullmatch(source_revision) is None
        or _SHA.fullmatch(archive_revision) is None
    ):
        return False
    comparison = read(repository, token, f"compare/{source_revision}...{archive_revision}")
    if not isinstance(comparison, Mapping) or comparison.get("status") not in {
        "ahead",
        "behind",
        "diverged",
        "identical",
    }:
        return False
    merge_base = comparison.get("merge_base_commit")
    if not isinstance(merge_base, Mapping) or not isinstance(merge_base.get("sha"), str):
        return False
    if _SHA.fullmatch(merge_base["sha"]) is None:
        return False
    source = _blobs(read(repository, token, f"git/trees/{source_revision}?recursive=1"))
    archive = _blobs(read(repository, token, f"git/trees/{archive_revision}?recursive=1"))
    if source is None or archive is None:
        return False
    active = f"openspec/changes/{change}/"
    approved = {path.removeprefix(active) for path in source if path.startswith(active)}
    if not approved or any(path.startswith(active) for path in archive):
        return False
    root_pattern = re.compile(
        rf"^openspec/changes/archive/({_ARCHIVE_DATE}-{re.escape(change)})/(.+)$"
    )
    roots: set[str] = set()
    old_files: set[str] = set()
    for path in archive:
        match = root_pattern.fullmatch(path)
        if match is not None:
            roots.add(match.group(1))
            old_files.add(match.group(2))
    return len(roots) == 1 and old_files == approved


def _download_archive_handoff(repository: str, token: str, artifact_id: int) -> bytes:
    """Read one bounded artifact from the fixed GitHub API host."""
    return read_github_artifact_bytes(repository, token, f"actions/artifacts/{artifact_id}/zip")


def archive_producer_state(
    read: Callable[[str, str, str], object],
    *,
    repository: str,
    token: str,
    issue_number: int,
    change: str,
    source_revision: str,
    default_branch: str,
    archive_revision: str | None,
    download: Callable[[str, str, int], bytes] | None = None,
) -> str:
    """Qualify one exact existing producer request and its durable archive head.

    `absent` may derive one workflow dispatch, `pending` must never duplicate it,
    and only `success` permits the archive PR/readiness consequence. Any
    incomplete or contradictory evidence is `conflict`, never a weaker state.
    """
    if (
        not isinstance(issue_number, int)
        or isinstance(issue_number, bool)
        or issue_number <= 0
        or _CHANGE.fullmatch(change) is None
        or _SHA.fullmatch(source_revision) is None
        or (archive_revision is not None and _SHA.fullmatch(archive_revision) is None)
        or not default_branch
        or not re.fullmatch(r"[A-Za-z0-9._/-]+", default_branch)
    ):
        return "conflict"
    request_key = f"archive-{issue_number}-{source_revision}"
    expected_title = f"OpenSpec Archive {request_key}"
    workflow = quote("openspec-archive.yml", safe="")
    branch = quote(default_branch, safe="")
    candidates: list[Mapping[str, object]] = []
    page = 1
    while True:
        payload = read(
            repository,
            token,
            f"actions/workflows/{workflow}/runs?event=workflow_dispatch"
            f"&branch={branch}&per_page=100&page={page}",
        )
        if not isinstance(payload, Mapping) or not isinstance(payload.get("workflow_runs"), list):
            return "conflict"
        runs = payload["workflow_runs"]
        if any(not isinstance(run, Mapping) for run in runs):
            return "conflict"
        candidates.extend(run for run in runs if run.get("display_title") == expected_title)
        if len(runs) < 100:
            break
        page += 1
        if page > 100:  # An unbounded or changing result set is not qualified evidence.
            return "conflict"
    if not candidates:
        return "absent"
    if len(candidates) != 1:
        return "conflict"
    run = candidates[0]
    run_id = run.get("id")
    run_attempt = run.get("run_attempt")
    if (
        not isinstance(run_id, int)
        or isinstance(run_id, bool)
        or run_id <= 0
        or not isinstance(run_attempt, int)
        or isinstance(run_attempt, bool)
        or run_attempt <= 0
        or run.get("event") != "workflow_dispatch"
        or run.get("path") != _ARCHIVE_WORKFLOW
        or run.get("head_branch") != default_branch
        or run.get("head_sha") != source_revision
    ):
        return "conflict"
    if run.get("status") in {"queued", "in_progress", "requested", "waiting", "pending"}:
        return "pending"
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        return "conflict"
    if archive_revision is None:
        return "conflict"
    artifacts = read(
        repository,
        token,
        f"actions/runs/{run_id}/artifacts?name={_ARCHIVE_ARTIFACT}&per_page=100",
    )
    if not isinstance(artifacts, Mapping) or not isinstance(artifacts.get("artifacts"), list):
        return "conflict"
    entries = artifacts["artifacts"]
    if len(entries) != 1 or not isinstance(entries[0], Mapping):
        return "conflict"
    item = entries[0]
    artifact_id = item.get("id")
    digest = item.get("digest")
    if (
        not isinstance(artifact_id, int)
        or isinstance(artifact_id, bool)
        or artifact_id <= 0
        or item.get("name") != _ARCHIVE_ARTIFACT
        or item.get("expired") is not False
        or not isinstance(digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None
    ):
        return "conflict"
    try:
        contents = (
            _download_archive_handoff(repository, token, artifact_id)
            if download is None
            else download(repository, token, artifact_id)
        )
        if len(contents) > _MAX_HANDOFF_ZIP or hashlib.sha256(contents).hexdigest() != digest[7:]:
            return "conflict"
        with ZipFile(io.BytesIO(contents)) as archive:
            if archive.namelist() != [_ARCHIVE_HANDOFF_FILE]:
                return "conflict"
            if archive.getinfo(_ARCHIVE_HANDOFF_FILE).file_size > 4096:
                return "conflict"
            handoff = json.loads(archive.read(_ARCHIVE_HANDOFF_FILE))
    except (OSError, ValueError, TypeError, BadZipFile, KeyError, RuntimeError):
        return "conflict"
    return (
        "success"
        if handoff
        == {
            "schema": "openspec-archive-handoff/v1",
            "run_id": run_id,
            "run_attempt": run_attempt,
            "issue_number": issue_number,
            "change": change,
            "source_revision": source_revision,
            "request_key": request_key,
            "branch": f"agent/archive-{change}",
            "head_sha": archive_revision,
        }
        else "conflict"
    )
