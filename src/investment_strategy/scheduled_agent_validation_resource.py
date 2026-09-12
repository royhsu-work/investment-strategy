"""Application-owned exact validation and content-addressed work-product helpers."""

from __future__ import annotations

import base64
import binascii
import json
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal, cast, overload
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_action_model import TRANSITIONS
from investment_strategy.scheduled_agent_action_model import (
    Action as ModelAction,
)
from investment_strategy.scheduled_agent_carrier import (
    CarrierPlan,
    CarrierRequired,
    carrier_pr_identity,
    make_carrier_plan,
)
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    acquire_current_github_preflight,
)
from investment_strategy.workflow_dispatch import classify_dispatch

_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_TASK_LINE = re.compile(r"^- \[(?P<state>[ x])\] (?P<id>\d+(?:\.\d+)+)\b")
_SLICE_HEADING = re.compile(r"^## Slice (?P<number>[1-9][0-9]*)\b")
_ACCEPTED_CHECK_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})
_OPEN_SPEC_AUTHORING_SOURCES = frozenset(
    {
        ("lead", "propose-change"),
        ("lead", "resolve-question"),
    }
)


@dataclass(frozen=True)
class ValidationResourcePlan:
    """Application-owned validation target bound to one fresh source action."""

    should_validate: bool
    source: WorkerRequest | None = None
    pr_number: int | None = None
    expected_change: str | None = None


@dataclass(frozen=True)
class ValidationResourceTarget:
    """Fresh exact PR-head target derived by repository application."""

    repository: str
    revision: str
    correlation: str
    pr_number: int
    change: str
    validation_required: bool = True


@dataclass(frozen=True)
class WorkProductFile:
    """One content-addressed file replacement in an M0 work-product manifest."""

    path: str
    blob_sha: str
    expected_sha: str | None


@dataclass(frozen=True)
class WorkProductManifest:
    """Untrusted semantic-worker work-product references; never repository authority."""

    branch: str
    base_sha: str
    message: str
    files: tuple[WorkProductFile, ...]


@dataclass(frozen=True)
class WorkProductPlan:
    """Application-owned work-product materialization plan."""

    should_apply: bool
    source: WorkerRequest | None = None
    pr_number: int | None = None
    expected_change: str | None = None
    manifest: WorkProductManifest | None = None


def _valid_change(value: str) -> bool:
    return (
        bool(value)
        and value == value.strip()
        and not any(character.isspace() for character in value)
    )


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _valid_branch(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not value.startswith("refs/")
        and ".." not in value
        and "//" not in value
    )


def _source_branch(change: object) -> str | None:
    if not isinstance(change, str) or change in {"", "unset"}:
        return None
    branch = f"agent/{change}"
    return branch if _valid_branch(branch) else None


def _replacement_branch(change: str, historical_pr_number: int) -> str:
    """Derive one deterministic same-Change branch after a merged carrier."""

    return f"agent/{change}-continuation-{historical_pr_number}"


def _valid_repo_path(value: object) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def work_product_path_allowed(
    source: WorkerRequest,
    expected_change: str,
    path: str,
) -> bool:
    """Authorize a manifest path from the current Action's mutation capability."""

    if (
        not _valid_change(expected_change)
        or expected_change == "unset"
        or not _valid_repo_path(path)
    ):
        return False

    change_prefix = f"openspec/changes/{expected_change}/"
    source_identity = (source.role, source.action)
    if source_identity in _OPEN_SPEC_AUTHORING_SOURCES:
        return path.startswith(change_prefix) or path == "openspec/config.yaml"
    if source_identity == ("executor", "implement-change"):
        if path.startswith("openspec/changes/"):
            return path.startswith(change_prefix)
        return True
    return False


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _github_json(
    repository: str,
    token: str,
    api_path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
    allow_not_found: bool = False,
) -> object | None:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    normalized_path = api_path.lstrip("/")
    api_url = f"https://api.github.com/repos/{repository}"
    if normalized_path:
        api_url = f"{api_url}/{normalized_path}"
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        api_url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
            raw = response.read()
    except HTTPError as exc:
        if allow_not_found and exc.code == 404:
            return None
        raise
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def _current_authorized_request(repository: str, token: str) -> WorkerRequest | None:
    decision = classify_dispatch(acquire_current_github_preflight(repository, token))
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id is None
        or decision.selected_routing is None
    ):
        return None
    role, action = decision.selected_routing
    return WorkerRequest(
        decision.selected_issue_id,
        role,
        action,
    )


def _change_from_issue(payload: Mapping[str, object]) -> str | None:
    body = payload.get("body")
    if not isinstance(body, str):
        return None
    matches = _CHANGE_LINE.findall(body)
    return matches[0] if len(matches) == 1 else None


def _pr_has_nonclosing_issue_link(body: object, issue_number: int) -> bool:
    if not isinstance(body, str):
        return False
    pattern = re.compile(rf"(?mi)^\s*Refs\s+#{issue_number}\s*$")
    return pattern.search(body) is not None


def _current_default_branch(repository: str, token: str) -> str:
    payload = _as_mapping(cast(object, _github_json(repository, token, "")))
    branch = None if payload is None else payload.get("default_branch")
    if not _valid_branch(branch):
        raise RuntimeError("validation resource repository default branch is incomplete")
    return cast(str, branch)


def _is_historical_merged_carrier(payload: Mapping[str, object]) -> bool:
    merged_at = payload.get("merged_at")
    return (
        payload.get("state") == "closed"
        and payload.get("merged") is True
        and _valid_sha(payload.get("merge_commit_sha"))
        and isinstance(merged_at, str)
        and bool(merged_at.strip())
    )


def _open_pr_payload(
    *,
    repository: str,
    token: str,
    pr_number: int,
    source: WorkerRequest,
    expected_change: str,
    default_branch: str,
    allow_historical_merged_carrier: bool = False,
    expected_branch: str | None = None,
) -> Mapping[str, object]:
    if _current_default_branch(repository, token) != default_branch:
        raise RuntimeError("validation resource repository default branch changed")
    branch = _source_branch(expected_change) if expected_branch is None else expected_branch
    if branch is None:
        raise RuntimeError("validation resource Change branch is invalid")

    issue = _as_mapping(
        cast(object, _github_json(repository, token, f"issues/{source.issue_number}"))
    )
    if (
        issue is None
        or issue.get("state") != "open"
        or _change_from_issue(issue) != expected_change
    ):
        raise RuntimeError("validation resource source Issue/Change identity changed")

    pr = _as_mapping(cast(object, _github_json(repository, token, f"pulls/{pr_number}")))
    if pr is None or not (
        (pr.get("state") == "open" and pr.get("merged") is not True)
        or (allow_historical_merged_carrier and _is_historical_merged_carrier(pr))
    ):
        raise RuntimeError("validation resource target PR is not an allowed current carrier")
    head = _as_mapping(pr.get("head"))
    base = _as_mapping(pr.get("base"))
    head_repo = None if head is None else _as_mapping(head.get("repo"))
    base_repo = None if base is None else _as_mapping(base.get("repo"))
    if (
        pr.get("number") != pr_number
        or head is None
        or base is None
        or head_repo is None
        or base_repo is None
        or head_repo.get("full_name") != repository
        or base_repo.get("full_name") != repository
        or head.get("ref") != branch
        or base.get("ref") != default_branch
        or not _pr_has_nonclosing_issue_link(pr.get("body"), source.issue_number)
    ):
        raise RuntimeError("validation resource target PR linkage is invalid")

    files = _github_json(repository, token, f"pulls/{pr_number}/files?per_page=100")
    if not isinstance(files, list) or not files or len(files) >= 100:
        raise RuntimeError("validation resource target PR file evidence is incomplete")
    change_prefix = f"openspec/changes/{expected_change}/"
    active_change_names: set[str] = set()
    has_expected_change = False
    for raw_file in files:
        file_payload = _as_mapping(raw_file)
        filename = None if file_payload is None else file_payload.get("filename")
        if not isinstance(filename, str):
            raise RuntimeError("validation resource target PR file evidence is malformed")
        if filename.startswith(change_prefix):
            has_expected_change = True
        if filename.startswith("openspec/changes/"):
            remainder = filename.removeprefix("openspec/changes/")
            change_name = remainder.split("/", 1)[0]
            if change_name and change_name != "archive":
                active_change_names.add(change_name)
    continuation_prefix = f"agent/{expected_change}-continuation-"
    continuation_suffix = (
        None if expected_branch is None else expected_branch.removeprefix(continuation_prefix)
    )
    is_deterministic_continuation = (
        expected_branch is not None
        and expected_branch.startswith(continuation_prefix)
        and continuation_suffix is not None
        and re.fullmatch(r"[1-9][0-9]*", continuation_suffix) is not None
    )
    if is_deterministic_continuation:
        if any(name != expected_change for name in active_change_names):
            raise RuntimeError("validation resource continuation contains competing active Change")
    elif not has_expected_change or active_change_names != {expected_change}:
        raise RuntimeError(
            "validation resource target PR does not uniquely represent the source Change"
        )
    return pr


def _open_pr_target(
    *,
    repository: str,
    token: str,
    pr_number: int,
    source: WorkerRequest,
    expected_change: str,
    default_branch: str,
    expected_branch: str | None = None,
) -> str:
    pr = _open_pr_payload(
        repository=repository,
        token=token,
        pr_number=pr_number,
        source=source,
        expected_change=expected_change,
        default_branch=default_branch,
        expected_branch=expected_branch,
    )
    head = _as_mapping(pr.get("head"))
    revision = None if head is None else head.get("sha")
    if not _valid_sha(revision):
        raise RuntimeError("validation resource target PR head is incomplete")
    return cast(str, revision)


def _open_prs_for_branch(
    repository: str,
    token: str,
    *,
    branch: str,
    default_branch: str,
) -> tuple[Mapping[str, object], ...]:
    """Observe all open PRs for one exact repository branch/base pair."""

    owner = repository.split("/", 1)[0]
    query = urlencode(
        {
            "state": "open",
            "head": f"{owner}:{branch}",
            "base": default_branch,
            "per_page": 100,
        }
    )
    payload = _github_json(repository, token, f"pulls?{query}")
    if not isinstance(payload, list) or len(payload) >= 100:
        raise RuntimeError("validation resource replacement carrier discovery is incomplete")
    result: list[Mapping[str, object]] = []
    for raw in payload:
        item = _as_mapping(raw)
        if item is None:
            raise RuntimeError("validation resource replacement carrier discovery is malformed")
        result.append(item)
    return tuple(result)


def _review_openspec_required(source: WorkerRequest) -> bool:
    """Derive the OpenSpec review gate from the executable Action model."""

    try:
        action = ModelAction(source.action)
    except ValueError:
        return False
    successors = TRANSITIONS[action].values()
    return any(successor is ModelAction.REVIEW_OPENSPEC for successor in successors)


def _is_executor_task_bookkeeping(
    source: WorkerRequest,
    expected_change: str,
    files: tuple[WorkProductFile, ...],
) -> bool:
    """Allow only the approved non-semantic task-marker update from implementation."""

    return (
        source.role == "executor"
        and source.action == "implement-change"
        and len(files) == 1
        and files[0].path == f"openspec/changes/{expected_change}/tasks.md"
    )


def _executor_task_file(
    source: WorkerRequest,
    expected_change: str,
    files: tuple[WorkProductFile, ...],
) -> WorkProductFile | None:
    """Return the one task file allowed in an implementation manifest."""

    if not _is_executor_task_bookkeeping(source, expected_change, files):
        return None
    task_path = f"openspec/changes/{expected_change}/tasks.md"
    return next(file for file in files if file.path == task_path)


def _is_executor_config_authoring(
    source: WorkerRequest,
    expected_change: str,
    files: tuple[WorkProductFile, ...],
) -> bool:
    """Allow only the canonical task-authoring owner after OpenSpec approval."""

    return (
        source.role == "executor"
        and source.action == "implement-change"
        and len(files) == 1
        and files[0].path == "openspec/config.yaml"
        and _valid_change(expected_change)
    )


def _task_marker_delta(current: str, candidate: str) -> tuple[str, ...] | None:
    """Return the ordered unchecked-to-checked task IDs in one candidate file."""

    current_lines = current.splitlines(keepends=True)
    candidate_lines = candidate.splitlines(keepends=True)
    if len(current_lines) != len(candidate_lines):
        return None

    changed_ids: list[str] = []
    for current_line, candidate_line in zip(current_lines, candidate_lines, strict=True):
        if current_line == candidate_line:
            continue
        current_match = _TASK_LINE.match(current_line)
        candidate_match = _TASK_LINE.match(candidate_line)
        if (
            current_match is None
            or candidate_match is None
            or current_match.group("state") != " "
            or candidate_match.group("state") != "x"
            or current_match.group("id") != candidate_match.group("id")
            or candidate_line != "- [x]" + current_line[5:]
        ):
            return None
        changed_ids.append(current_match.group("id"))
    if not changed_ids or len(changed_ids) != len(set(changed_ids)):
        return None
    return tuple(changed_ids)


def _task_slices(content: str) -> tuple[tuple[tuple[str, bool], ...], ...] | None:
    """Parse non-empty, uniquely identified task slices in source order."""

    slices: list[list[tuple[str, bool]]] = []
    current_slice: list[tuple[str, bool]] | None = None
    seen_ids: set[str] = set()
    for line in content.splitlines():
        if _SLICE_HEADING.match(line) is not None:
            current_slice = []
            slices.append(current_slice)
            continue
        task = _TASK_LINE.match(line)
        if task is None:
            continue
        if current_slice is None:
            return None
        task_id = task.group("id")
        if task_id in seen_ids:
            return None
        seen_ids.add(task_id)
        current_slice.append((task_id, task.group("state") == "x"))

    if not slices or any(not task_slice for task_slice in slices):
        return None
    return tuple(tuple(task_slice) for task_slice in slices)


def _first_incomplete_slice_task_ids(content: str) -> tuple[str, ...] | None:
    """Return the complete unchecked task set of the first incomplete slice."""

    slices = _task_slices(content)
    if slices is None:
        return None
    for task_slice in slices:
        pending = tuple(task_id for task_id, checked in task_slice if not checked)
        if pending:
            return pending
    return ()


def _previous_completed_slice_task_ids(content: str) -> tuple[str, ...] | None:
    """Return the immediately preceding fully checked slice before the first incomplete one."""

    slices = _task_slices(content)
    if slices is None:
        return None
    for index, task_slice in enumerate(slices):
        if any(not checked for _task_id, checked in task_slice):
            if index == 0 or any(not checked for _task_id, checked in slices[index - 1]):
                return None
            return tuple(task_id for task_id, _checked in slices[index - 1])
    return None


def _task_marker_update_is_monotonic(current: str, candidate: str) -> bool:
    """Accept only a non-empty, checkbox-only monotonic task update."""

    return _task_marker_delta(current, candidate) is not None


def task_checkpoint_is_exact(
    repository: str,
    token: str,
    *,
    expected_change: str,
    base_sha: str,
    file: WorkProductFile,
    completed_task_ids: tuple[str, ...],
) -> bool:
    """Prove one task checkpoint completes exactly the first incomplete slice."""

    if (
        file.expected_sha is None
        or file.path != f"openspec/changes/{expected_change}/tasks.md"
        or _content_sha_at(
            repository,
            token,
            path=file.path,
            revision=base_sha,
        )
        != file.expected_sha
    ):
        return False
    try:
        current = _content_text_at(repository, token, path=file.path, revision=base_sha)
        candidate = _blob_text(repository, token, file.blob_sha)
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError):
        return False
    changed_ids = _task_marker_delta(current, candidate)
    if changed_ids is None:
        return (
            current == candidate
            and _previous_completed_slice_task_ids(current) == completed_task_ids
        )
    first_incomplete_ids = _first_incomplete_slice_task_ids(current)
    return (
        first_incomplete_ids is not None
        and changed_ids == completed_task_ids
        and completed_task_ids == first_incomplete_ids
    )


def resolve_validation_resource_target(
    plan: ValidationResourcePlan,
    *,
    repository: str,
    token: str,
    default_branch: str,
) -> ValidationResourceTarget:
    """Fresh-reauthorize the source and derive exact R from the current PR."""

    if (
        not plan.should_validate
        or plan.source is None
        or plan.pr_number is None
        or plan.expected_change is None
    ):
        raise RuntimeError("validation resource plan is incomplete")
    if _current_authorized_request(repository, token) != plan.source:
        raise RuntimeError("validation resource source dispatch is stale")
    if not _review_openspec_required(plan.source):
        raise RuntimeError("validation resource is not required by the current Action gate")

    revision = _open_pr_target(
        repository=repository,
        token=token,
        pr_number=plan.pr_number,
        source=plan.source,
        expected_change=plan.expected_change,
        default_branch=default_branch,
    )
    return ValidationResourceTarget(
        repository=repository,
        revision=revision,
        correlation=f"effect-request-{plan.source.issue_number}",
        pr_number=plan.pr_number,
        change=plan.expected_change,
    )


def _content_sha_at(
    repository: str,
    token: str,
    *,
    path: str,
    revision: str,
) -> str | None:
    encoded_path = quote(path, safe="/")
    state = _github_json(
        repository,
        token,
        f"contents/{encoded_path}?{urlencode({'ref': revision})}",
        allow_not_found=True,
    )
    if state is None:
        return None
    payload = _as_mapping(state)
    sha = None if payload is None else payload.get("sha")
    if not _valid_sha(sha):
        raise RuntimeError("work-product current content identity is incomplete")
    return cast(str, sha)


def _content_text_at(
    repository: str,
    token: str,
    *,
    path: str,
    revision: str,
) -> str:
    encoded_path = quote(path, safe="/")
    state = _github_json(
        repository,
        token,
        f"contents/{encoded_path}?{urlencode({'ref': revision})}",
        allow_not_found=False,
    )
    payload = _as_mapping(state)
    content = None if payload is None else payload.get("content")
    encoding = None if payload is None else payload.get("encoding")
    if not isinstance(content, str) or encoding != "base64":
        raise RuntimeError("work-product current content text is incomplete")
    try:
        return base64.b64decode("".join(content.split()), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise RuntimeError("work-product current content is not valid UTF-8") from exc


def _blob_text(repository: str, token: str, blob_sha: str) -> str:
    payload = _as_mapping(cast(object, _github_json(repository, token, f"git/blobs/{blob_sha}")))
    content = None if payload is None else payload.get("content")
    encoding = None if payload is None else payload.get("encoding")
    if not isinstance(content, str) or encoding != "base64":
        raise RuntimeError("work-product blob text is incomplete")
    try:
        return base64.b64decode("".join(content.split()), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise RuntimeError("work-product blob is not valid UTF-8") from exc


@overload
def _ref_head_sha(
    repository: str,
    token: str,
    branch: str,
    *,
    allow_not_found: Literal[False] = False,
) -> str: ...


@overload
def _ref_head_sha(
    repository: str,
    token: str,
    branch: str,
    *,
    allow_not_found: Literal[True],
) -> str | None: ...


def _ref_head_sha(
    repository: str,
    token: str,
    branch: str,
    *,
    allow_not_found: bool = False,
) -> str | None:
    state = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                f"git/ref/heads/{quote(branch, safe='/')}",
                allow_not_found=allow_not_found,
            ),
        )
    )
    if state is None and allow_not_found:
        return None
    obj = None if state is None else _as_mapping(state.get("object"))
    sha = None if obj is None else obj.get("sha")
    if not _valid_sha(sha):
        raise RuntimeError("work-product ref observation is incomplete")
    return cast(str, sha)


def _revision_matches_manifest(
    repository: str,
    token: str,
    *,
    base_sha: str,
    revision: str,
    manifest: WorkProductManifest,
) -> bool:
    """Recognize an already-applied exact manifest without creating another commit."""

    comparison = _as_mapping(
        cast(object, _github_json(repository, token, f"compare/{base_sha}...{revision}"))
    )
    files = None if comparison is None else comparison.get("files")
    commits = None if comparison is None else comparison.get("commits")
    if (
        comparison is None
        or comparison.get("status") != "ahead"
        or comparison.get("ahead_by") != 1
        or comparison.get("behind_by") != 0
        or not isinstance(commits, list)
        or len(commits) != 1
        or not isinstance(files, list)
    ):
        return False
    paths: set[str] = set()
    for raw_file in files:
        file = _as_mapping(raw_file)
        filename = None if file is None else file.get("filename")
        if not isinstance(filename, str):
            return False
        paths.add(filename)
    if paths != {file.path for file in manifest.files}:
        return False
    commit = _as_mapping(cast(object, _github_json(repository, token, f"git/commits/{revision}")))
    parents = None if commit is None else commit.get("parents")
    parent = None if not isinstance(parents, list) or len(parents) != 1 else _as_mapping(parents[0])
    if (
        commit is None
        or commit.get("sha") != revision
        or commit.get("message") != manifest.message
        or parent is None
        or parent.get("sha") != base_sha
    ):
        return False
    return all(
        _content_sha_at(repository, token, path=file.path, revision=revision) == file.blob_sha
        for file in manifest.files
    )


def _comparison_file_paths(
    repository: str,
    token: str,
    *,
    base_sha: str,
    revision: str,
) -> set[str]:
    comparison = _as_mapping(
        cast(object, _github_json(repository, token, f"compare/{base_sha}...{revision}"))
    )
    files = None if comparison is None else comparison.get("files")
    if (
        comparison is None
        or comparison.get("too_large") is True
        or not isinstance(files, list)
        or len(files) >= 300
    ):
        raise RuntimeError("work-product reconciliation file comparison is incomplete")
    paths: set[str] = set()
    for raw_file in files:
        file = _as_mapping(raw_file)
        filename = None if file is None else file.get("filename")
        if not isinstance(filename, str) or not filename:
            raise RuntimeError("work-product reconciliation file comparison is malformed")
        paths.add(filename)
    return paths


def _default_branch_is_ancestor(
    repository: str,
    token: str,
    *,
    default_revision: str,
    revision: str,
) -> bool:
    comparison = _as_mapping(
        cast(
            object,
            _github_json(repository, token, f"compare/{default_revision}...{revision}"),
        )
    )
    status = None if comparison is None else comparison.get("status")
    behind_by = None if comparison is None else comparison.get("behind_by")
    if (
        comparison is None
        or status not in {"ahead", "behind", "diverged", "identical"}
        or not isinstance(behind_by, int)
        or isinstance(behind_by, bool)
        or behind_by < 0
    ):
        raise RuntimeError("work-product default-branch ancestry observation is incomplete")
    return behind_by == 0


def _manifest_content_matches(
    repository: str,
    token: str,
    *,
    revision: str,
    manifest: WorkProductManifest,
) -> bool:
    return bool(manifest.files) and all(
        _content_sha_at(repository, token, path=file.path, revision=revision) == file.blob_sha
        for file in manifest.files
    )


def _manifest_expected_content_matches_base(
    repository: str,
    token: str,
    *,
    base_sha: str,
    manifest: WorkProductManifest,
) -> bool:
    """Verify every supplied expected SHA still describes the requested base."""

    return bool(manifest.files) and all(
        file.expected_sha is None
        or _content_sha_at(repository, token, path=file.path, revision=base_sha)
        == file.expected_sha
        for file in manifest.files
    )


def _reconciliation_message(change: str) -> str:
    return f"Reconcile default-branch ancestry for {change}"


def _is_reconciled_work_product_revision(
    repository: str,
    token: str,
    *,
    base_sha: str,
    revision: str,
    manifest: WorkProductManifest,
    authorization_revision: str,
    seen: frozenset[str] = frozenset(),
) -> bool:
    """Recognize an application-built two-parent reconciliation commit."""

    if revision in seen:
        return False
    commit = _as_mapping(cast(object, _github_json(repository, token, f"git/commits/{revision}")))
    parents = None if commit is None else commit.get("parents")
    if (
        commit is None
        or not isinstance(parents, list)
        or len(parents) != 2
        or not _manifest_content_matches(
            repository,
            token,
            revision=revision,
            manifest=manifest,
        )
    ):
        return False
    parent_shas: list[str] = []
    for raw_parent in parents:
        parent = _as_mapping(raw_parent)
        parent_sha = None if parent is None else parent.get("sha")
        if not _valid_sha(parent_sha):
            return False
        parent_shas.append(cast(str, parent_sha))
    if not _default_branch_is_ancestor(
        repository,
        token,
        default_revision=parent_shas[1],
        revision=authorization_revision,
    ):
        return False
    if parent_shas[0] == base_sha:
        return commit.get("message") == manifest.message
    if commit.get("message") != _reconciliation_message(manifest.branch.removeprefix("agent/")):
        return False
    try:
        reconciled_paths = _comparison_file_paths(
            repository,
            token,
            base_sha=authorization_revision,
            revision=revision,
        )
    except RuntimeError:
        reconciled_paths = set()
    if reconciled_paths == {file.path for file in manifest.files}:
        return True
    if _revision_matches_manifest(
        repository,
        token,
        base_sha=base_sha,
        revision=parent_shas[0],
        manifest=manifest,
    ):
        return True
    return _is_reconciled_work_product_revision(
        repository,
        token,
        base_sha=base_sha,
        revision=parent_shas[0],
        manifest=manifest,
        authorization_revision=authorization_revision,
        seen=seen | {revision},
    )


def _verify_default_only_content(
    repository: str,
    token: str,
    *,
    default_revision: str,
    branch_revision: str,
) -> None:
    """Ensure reconciliation does not discard default-only changes."""

    comparison = _as_mapping(
        cast(
            object,
            _github_json(repository, token, f"compare/{default_revision}...{branch_revision}"),
        )
    )
    merge_base = None if comparison is None else _as_mapping(comparison.get("merge_base_commit"))
    merge_base_sha = None if merge_base is None else merge_base.get("sha")
    if not _valid_sha(merge_base_sha):
        raise RuntimeError("work-product reconciliation merge-base identity is incomplete")

    default_paths = _comparison_file_paths(
        repository,
        token,
        base_sha=cast(str, merge_base_sha),
        revision=default_revision,
    )
    branch_paths = _comparison_file_paths(
        repository,
        token,
        base_sha=cast(str, merge_base_sha),
        revision=branch_revision,
    )
    for path in default_paths - branch_paths:
        if _content_sha_at(repository, token, path=path, revision=default_revision) != (
            _content_sha_at(repository, token, path=path, revision=branch_revision)
        ):
            raise RuntimeError("work-product reconciliation would discard default-branch content")


def _exact_head_checks_pass(repository: str, token: str, head_sha: str) -> bool:
    payload = _as_mapping(
        cast(
            object,
            _github_json(repository, token, f"commits/{head_sha}/check-runs?per_page=100"),
        )
    )
    total_count = None if payload is None else payload.get("total_count")
    raw_runs = None if payload is None else payload.get("check_runs")
    if (
        not isinstance(total_count, int)
        or isinstance(total_count, bool)
        or total_count <= 0
        or not isinstance(raw_runs, list)
        or total_count != len(raw_runs)
    ):
        return False
    return all(
        isinstance(run, Mapping)
        and run.get("status") == "completed"
        and run.get("conclusion") in _ACCEPTED_CHECK_CONCLUSIONS
        for run in raw_runs
    )


def _replacement_carrier_plan(
    *,
    repository: str,
    issue_number: int,
    change: str,
    action: str,
    authorization_revision: str,
    branch: str,
    revision: str,
    default_branch: str,
    historical_pr_number: int,
) -> CarrierPlan:
    """Build the existing pull-request carrier plan for merged-history continuation."""

    title = f"OpenSpec: {change} continuation"
    body = f"Continue OpenSpec change `{change}` after the merged carrier.\n\nRefs #{issue_number}"
    return make_carrier_plan(
        repository=repository,
        issue_number=issue_number,
        change=change,
        action=action,
        authorization_revision=authorization_revision,
        operation="pull-request-create",
        target={
            "head_ref": branch,
            "base_ref": default_branch,
            "repository": repository,
            "historical_pull_request": historical_pr_number,
        },
        expected={
            "head_ref": branch,
            "head_sha": revision,
            "base_ref": default_branch,
            "base_sha": authorization_revision,
            "existing_pr_count": 0,
            "historical_pull_request": historical_pr_number,
        },
        requested={
            "title": title,
            "body": body,
            "head": branch,
            "base": default_branch,
            "draft": False,
            "head_sha": revision,
        },
        expected_postcondition={
            "repository": repository,
            "issue_number": issue_number,
            "state": "open",
            "merged": False,
            "title": title,
            "body": body,
            "draft": False,
            "head_ref": branch,
            "head_sha": revision,
            "base_ref": default_branch,
            "base_sha": authorization_revision,
        },
    )


def apply_work_product(
    plan: WorkProductPlan,
    *,
    repository: str,
    token: str,
    default_branch: str,
    authorization_revision: str,
) -> ValidationResourceTarget:
    """Construct one exact commit and hand open-PR head movement to a carrier."""

    if (
        not plan.should_apply
        or plan.source is None
        or plan.pr_number is None
        or plan.expected_change is None
        or plan.manifest is None
    ):
        raise RuntimeError("work-product plan is incomplete")
    if not _valid_sha(authorization_revision):
        raise RuntimeError("work-product authorization revision is incomplete")
    if _ref_head_sha(repository, token, default_branch) != authorization_revision:
        raise RuntimeError("work-product default-branch authorization is stale")
    if _current_authorized_request(repository, token) != plan.source:
        raise RuntimeError("work-product source dispatch is stale")
    expected_branch = _source_branch(plan.expected_change)
    if expected_branch is None or plan.manifest.branch != expected_branch:
        raise RuntimeError("work-product branch is not bound to source Change")
    if not plan.manifest.files or not all(
        work_product_path_allowed(plan.source, plan.expected_change, file.path)
        for file in plan.manifest.files
    ):
        raise RuntimeError("work-product path is outside source Action capability")
    if any(file.path.startswith("openspec/") for file in plan.manifest.files) and not (
        _review_openspec_required(plan.source)
        or _is_executor_task_bookkeeping(
            plan.source,
            plan.expected_change,
            plan.manifest.files,
        )
        or _is_executor_config_authoring(
            plan.source,
            plan.expected_change,
            plan.manifest.files,
        )
    ):
        raise RuntimeError("work-product source has no required OpenSpec review gate")

    pr = _open_pr_payload(
        repository=repository,
        token=token,
        pr_number=plan.pr_number,
        source=plan.source,
        expected_change=plan.expected_change,
        default_branch=default_branch,
        allow_historical_merged_carrier=True,
    )
    head = _as_mapping(pr.get("head"))
    pr_head_sha = None if head is None else head.get("sha")
    current_branch = None if head is None else head.get("ref")
    if not _valid_sha(pr_head_sha):
        raise RuntimeError("work-product PR head identity is incomplete")
    if current_branch != expected_branch:
        raise RuntimeError("work-product PR branch identity is stale")
    base = _as_mapping(pr.get("base"))
    if base is None or base.get("ref") != default_branch:
        raise RuntimeError("work-product PR base identity is stale")
    historical_merged_carrier = _is_historical_merged_carrier(pr)
    replacement_branch: str | None = None
    replacement_ref_exists = False
    replacement_pr: Mapping[str, object] | None = None
    replacement_pr_number: int | None = None
    replacement_reconciliation_required = False
    current_carrier_is_materialized = replacement_branch is None
    current_target_pr_number: int | None = plan.pr_number
    if historical_merged_carrier:
        merge_commit_sha = pr.get("merge_commit_sha")
        if not _valid_sha(merge_commit_sha) or not _default_branch_is_ancestor(
            repository,
            token,
            default_revision=cast(str, merge_commit_sha),
            revision=authorization_revision,
        ):
            raise RuntimeError("work-product historical carrier is not in current default history")
        if plan.manifest.base_sha != authorization_revision:
            raise RuntimeError("replacement work-product base is not current default branch")
        replacement_branch = _replacement_branch(plan.expected_change, plan.pr_number)
        replacement_prs = _open_prs_for_branch(
            repository,
            token,
            branch=replacement_branch,
            default_branch=default_branch,
        )
        if len(replacement_prs) > 1:
            raise RuntimeError("work-product replacement carrier is ambiguous")
        if replacement_prs:
            replacement_pr = _open_pr_payload(
                repository=repository,
                token=token,
                pr_number=cast(int, replacement_prs[0]["number"]),
                source=plan.source,
                expected_change=plan.expected_change,
                default_branch=default_branch,
                expected_branch=replacement_branch,
            )
            raw_replacement_number = replacement_pr.get("number")
            if (
                isinstance(raw_replacement_number, bool)
                or not isinstance(raw_replacement_number, int)
                or raw_replacement_number <= 0
            ):
                raise RuntimeError("work-product replacement carrier number is incomplete")
            replacement_pr_number = raw_replacement_number
            replacement_head = _as_mapping(replacement_pr.get("head"))
            replacement_revision = None if replacement_head is None else replacement_head.get("sha")
            if not _valid_sha(replacement_revision):
                raise RuntimeError("work-product replacement carrier head is incomplete")
            if _revision_matches_manifest(
                repository,
                token,
                base_sha=plan.manifest.base_sha,
                revision=cast(str, replacement_revision),
                manifest=plan.manifest,
            ):
                return ValidationResourceTarget(
                    repository=repository,
                    revision=cast(str, replacement_revision),
                    correlation=f"effect-request-{plan.source.issue_number}",
                    pr_number=replacement_pr_number,
                    change=plan.expected_change,
                )
            replacement_reconciliation_required = True
        replacement_ref_head = _ref_head_sha(
            repository,
            token,
            replacement_branch,
            allow_not_found=True,
        )
        replacement_ref_exists = replacement_ref_head is not None
        replacement_pr_head = _as_mapping(
            None if replacement_pr is None else replacement_pr.get("head")
        )
        replacement_pr_revision = (
            None if replacement_pr_head is None else replacement_pr_head.get("sha")
        )
        if (
            replacement_ref_exists
            and replacement_pr is not None
            and replacement_ref_head != replacement_pr_revision
        ):
            raise RuntimeError("work-product replacement PR/ref head identity is stale")
        if replacement_ref_head is not None and _revision_matches_manifest(
            repository,
            token,
            base_sha=plan.manifest.base_sha,
            revision=replacement_ref_head,
            manifest=plan.manifest,
        ):
            raise CarrierRequired(
                _replacement_carrier_plan(
                    repository=repository,
                    issue_number=plan.source.issue_number,
                    change=plan.expected_change,
                    action=plan.source.action,
                    authorization_revision=authorization_revision,
                    branch=replacement_branch,
                    revision=replacement_ref_head,
                    default_branch=default_branch,
                    historical_pr_number=plan.pr_number,
                )
            )
        current_ref_head = replacement_ref_head
        current_head = authorization_revision if current_ref_head is None else current_ref_head
        default_branch_is_ancestor = _default_branch_is_ancestor(
            repository,
            token,
            default_revision=authorization_revision,
            revision=current_head,
        )
        current_carrier_is_materialized = (
            replacement_pr is not None
            and replacement_pr_number is not None
            and replacement_ref_exists
        )
        current_target_pr_number = replacement_pr_number
    else:
        current_ref_head = _ref_head_sha(repository, token, expected_branch)
        if current_ref_head != pr_head_sha:
            raise RuntimeError("work-product PR/ref head identity is stale")
        current_head = current_ref_head
        default_branch_is_ancestor = _default_branch_is_ancestor(
            repository,
            token,
            default_revision=authorization_revision,
            revision=current_head,
        )
    if (
        current_carrier_is_materialized
        and current_target_pr_number is not None
        and _manifest_expected_content_matches_base(
            repository,
            token,
            base_sha=plan.manifest.base_sha,
            manifest=plan.manifest,
        )
        and _manifest_content_matches(
            repository,
            token,
            revision=current_head,
            manifest=plan.manifest,
        )
    ):
        return ValidationResourceTarget(
            repository=repository,
            revision=current_head,
            correlation=f"effect-request-{plan.source.issue_number}",
            pr_number=current_target_pr_number,
            change=plan.expected_change,
        )
    replay_manifest = False
    if current_head != plan.manifest.base_sha:
        manifest_applied = _revision_matches_manifest(
            repository,
            token,
            base_sha=plan.manifest.base_sha,
            revision=current_head,
            manifest=plan.manifest,
        )
        reconciled = _is_reconciled_work_product_revision(
            repository,
            token,
            base_sha=plan.manifest.base_sha,
            revision=current_head,
            manifest=plan.manifest,
            authorization_revision=authorization_revision,
        )
        if default_branch_is_ancestor and (manifest_applied or reconciled):
            return ValidationResourceTarget(
                repository=repository,
                revision=current_head,
                correlation=f"effect-request-{plan.source.issue_number}",
                pr_number=plan.pr_number,
                change=plan.expected_change,
            )
        if not manifest_applied and not reconciled and not replacement_reconciliation_required:
            raise RuntimeError("work-product PR head/base identity is stale")
        if manifest_applied or reconciled:
            replay_manifest = True
    needs_default_reconciliation = not default_branch_is_ancestor
    reconcile_replacement_from_default = (
        needs_default_reconciliation
        and replacement_reconciliation_required
        and replacement_branch is not None
        and replacement_ref_exists
    )
    if needs_default_reconciliation and not reconcile_replacement_from_default:
        _verify_default_only_content(
            repository,
            token,
            default_revision=authorization_revision,
            branch_revision=current_head,
        )

    if not replay_manifest:
        for file in plan.manifest.files:
            current_sha = _content_sha_at(
                repository,
                token,
                path=file.path,
                revision=plan.manifest.base_sha,
            )
            if current_sha != file.expected_sha:
                raise RuntimeError("work-product expected content SHA is stale")
            task_file = _executor_task_file(
                plan.source,
                plan.expected_change,
                plan.manifest.files,
            )
            if task_file is not None and file.path == task_file.path:
                current = _content_text_at(
                    repository,
                    token,
                    path=file.path,
                    revision=plan.manifest.base_sha,
                )
                candidate = _blob_text(repository, token, file.blob_sha)
                if current != candidate and not _task_marker_update_is_monotonic(
                    current, candidate
                ):
                    raise RuntimeError(
                        "work-product task marker update must be a monotonic checkbox-only update"
                    )

    tree_base_revision = (
        authorization_revision if reconcile_replacement_from_default else current_head
    )
    base_commit = _as_mapping(
        cast(object, _github_json(repository, token, f"git/commits/{tree_base_revision}"))
    )
    base_tree = None if base_commit is None else _as_mapping(base_commit.get("tree"))
    base_tree_sha = None if base_tree is None else base_tree.get("sha")
    if not _valid_sha(base_tree_sha):
        raise RuntimeError("work-product base tree identity is incomplete")

    tree_sha = cast(str, base_tree_sha)
    if not replay_manifest:
        try:
            tree_response = _as_mapping(
                cast(
                    object,
                    _github_json(
                        repository,
                        token,
                        "git/trees",
                        method="POST",
                        payload={
                            "base_tree": cast(str, base_tree_sha),
                            "tree": [
                                {
                                    "path": file.path,
                                    "mode": "100644",
                                    "type": "blob",
                                    "sha": file.blob_sha,
                                }
                                for file in plan.manifest.files
                            ],
                        },
                    ),
                )
            )
        except HTTPError as exc:
            if exc.code in {404, 422}:
                raise RuntimeError(
                    "work-product referenced blob is unavailable to application tree construction"
                ) from exc
            raise
        observed_tree_sha = None if tree_response is None else tree_response.get("sha")
        if not _valid_sha(observed_tree_sha):
            raise RuntimeError("work-product tree creation returned no SHA")
        tree_sha = cast(str, observed_tree_sha)

    observed_tree = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                f"git/trees/{tree_sha}?recursive=1",
            ),
        )
    )
    tree_entries = None if observed_tree is None else observed_tree.get("tree")
    if (
        observed_tree is None
        or observed_tree.get("sha") != tree_sha
        or observed_tree.get("truncated") is True
        or not isinstance(tree_entries, list)
    ):
        raise RuntimeError("work-product tree postcondition is incomplete")
    if not replay_manifest:
        for file in plan.manifest.files:
            matches = [
                entry
                for raw_entry in tree_entries
                if (entry := _as_mapping(raw_entry)) is not None and entry.get("path") == file.path
            ]
            if (
                len(matches) != 1
                or matches[0].get("type") != "blob"
                or matches[0].get("sha") != file.blob_sha
            ):
                raise RuntimeError(
                    "work-product referenced blob was not resolved into exact tree path"
                )

    materialization_branch = (
        plan.manifest.branch if replacement_branch is None else replacement_branch
    )
    if replacement_branch is None:
        observed_materialization_head: str | None = _ref_head_sha(
            repository,
            token,
            materialization_branch,
        )
        if observed_materialization_head != current_head:
            raise RuntimeError("work-product branch base changed before carrier handoff")
    else:
        observed_materialization_head = (
            _ref_head_sha(repository, token, materialization_branch)
            if replacement_ref_exists
            else _ref_head_sha(
                repository,
                token,
                materialization_branch,
                allow_not_found=True,
            )
        )
        if replacement_ref_exists and observed_materialization_head != current_head:
            raise RuntimeError(
                "replacement work-product branch base changed before carrier handoff"
            )
    if _ref_head_sha(repository, token, default_branch) != authorization_revision:
        raise RuntimeError("work-product default branch changed before carrier handoff")
    if _current_authorized_request(repository, token) != plan.source:
        raise RuntimeError("work-product source dispatch changed before carrier handoff")

    if (
        _is_executor_task_bookkeeping(
            plan.source,
            plan.expected_change,
            plan.manifest.files,
        )
        and (
            task_file := _executor_task_file(
                plan.source,
                plan.expected_change,
                plan.manifest.files,
            )
        )
        is not None
        and task_file.expected_sha is not None
        and task_file.blob_sha == task_file.expected_sha
    ):
        return ValidationResourceTarget(
            repository=repository,
            revision=current_head,
            correlation=f"effect-request-{plan.source.issue_number}",
            pr_number=plan.pr_number,
            change=plan.expected_change,
        )

    commit_message = (
        _reconciliation_message(plan.expected_change) if replay_manifest else plan.manifest.message
    )
    commit_parents = [current_head]
    if needs_default_reconciliation:
        commit_parents.append(authorization_revision)

    commit_response = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                "git/commits",
                method="POST",
                payload={
                    "message": commit_message,
                    "tree": cast(str, tree_sha),
                    "parents": commit_parents,
                },
            ),
        )
    )
    revision = None if commit_response is None else commit_response.get("sha")
    if not _valid_sha(revision):
        raise RuntimeError("work-product commit creation returned no SHA")

    if replacement_branch is not None and not replacement_ref_exists:
        created_ref = _as_mapping(
            cast(
                object,
                _github_json(
                    repository,
                    token,
                    "git/refs",
                    method="POST",
                    payload={
                        "ref": f"refs/heads/{replacement_branch}",
                        "sha": cast(str, revision),
                    },
                ),
            )
        )
        created_object = None if created_ref is None else _as_mapping(created_ref.get("object"))
        if (
            created_object is None
            or created_object.get("sha") != revision
            or _ref_head_sha(repository, token, replacement_branch) != revision
        ):
            raise RuntimeError("replacement work-product branch postcondition was not observed")

    if replacement_branch is None:
        if _ref_head_sha(repository, token, plan.manifest.branch) != current_head:
            raise RuntimeError("work-product branch base changed before carrier handoff")
    elif (
        replacement_ref_exists
        and _ref_head_sha(repository, token, replacement_branch) != current_head
    ):
        raise RuntimeError("replacement work-product branch base changed before carrier handoff")
    if _ref_head_sha(repository, token, default_branch) != authorization_revision:
        raise RuntimeError("work-product default branch changed before carrier handoff")
    if replacement_branch is not None:
        observed_commit = _as_mapping(
            cast(object, _github_json(repository, token, f"git/commits/{revision}"))
        )
        observed_commit_tree = (
            None if observed_commit is None else _as_mapping(observed_commit.get("tree"))
        )
        parents = None if observed_commit is None else observed_commit.get("parents")
        replacement_parent_shas: list[str] = []
        if isinstance(parents, list):
            for raw_parent in parents:
                parent = _as_mapping(raw_parent)
                parent_sha = None if parent is None else parent.get("sha")
                if not _valid_sha(parent_sha):
                    raise RuntimeError("replacement work-product commit parent is incomplete")
                replacement_parent_shas.append(cast(str, parent_sha))
        if (
            observed_commit is None
            or observed_commit.get("sha") != revision
            or observed_commit.get("message") != commit_message
            or observed_commit_tree is None
            or observed_commit_tree.get("sha") != tree_sha
            or replacement_parent_shas != commit_parents
        ):
            raise RuntimeError("replacement work-product commit postcondition was not observed")
        for file in plan.manifest.files:
            if (
                _content_sha_at(
                    repository,
                    token,
                    path=file.path,
                    revision=cast(str, revision),
                )
                != file.blob_sha
            ):
                raise RuntimeError("replacement work-product file postcondition was not observed")
        if replacement_pr is None or replacement_pr_number is None:
            raise CarrierRequired(
                _replacement_carrier_plan(
                    repository=repository,
                    issue_number=plan.source.issue_number,
                    change=plan.expected_change,
                    action=plan.source.action,
                    authorization_revision=authorization_revision,
                    branch=replacement_branch,
                    revision=cast(str, revision),
                    default_branch=default_branch,
                    historical_pr_number=plan.pr_number,
                )
            )
        carrier_ref = f"refs/heads/{replacement_branch}"
        carrier_plan = make_carrier_plan(
            repository=repository,
            issue_number=plan.source.issue_number,
            change=plan.expected_change,
            action=plan.source.action,
            authorization_revision=authorization_revision,
            operation="pull-request-head-update",
            target={
                "repository": repository,
                "pull_request_number": replacement_pr_number,
                "ref": carrier_ref,
            },
            expected={
                "ref": carrier_ref,
                "ref_sha": current_head,
                "pull_request": carrier_pr_identity(replacement_pr),
                "commit_parents": commit_parents,
                "commit_tree_sha": cast(str, tree_sha),
                "commit_message": commit_message,
            },
            requested={
                "ref": carrier_ref,
                "sha": cast(str, revision),
                "force": False,
                "pull_request_number": replacement_pr_number,
                "expected_head_sha": current_head,
                "commit_parents": commit_parents,
                "commit_tree_sha": cast(str, tree_sha),
                "commit_message": commit_message,
            },
            expected_postcondition={
                "ref": carrier_ref,
                "ref_sha": cast(str, revision),
                "pull_request_number": replacement_pr_number,
                "pull_request_head_sha": cast(str, revision),
                "state": "open",
                "merged": False,
                "commit_sha": cast(str, revision),
                "commit_parents": commit_parents,
                "commit_tree_sha": cast(str, tree_sha),
                "commit_message": commit_message,
            },
        )
        raise CarrierRequired(carrier_plan)
    observed_pr: Mapping[str, object] | None = None
    observed_head: Mapping[str, object] | None = None
    for attempt in range(10):
        observed_pr = _open_pr_payload(
            repository=repository,
            token=token,
            pr_number=plan.pr_number,
            source=plan.source,
            expected_change=plan.expected_change,
            default_branch=default_branch,
            allow_historical_merged_carrier=True,
        )
        observed_head = _as_mapping(observed_pr.get("head"))
        if (
            observed_head is not None
            and observed_head.get("ref") == expected_branch
            and observed_head.get("sha") == current_head
            and carrier_pr_identity(observed_pr) == carrier_pr_identity(pr)
        ):
            break
        if attempt < 9:
            time.sleep(1)
    if (
        observed_pr is None
        or observed_head is None
        or observed_head.get("ref") != expected_branch
        or observed_head.get("sha") != current_head
        or carrier_pr_identity(observed_pr) != carrier_pr_identity(pr)
    ):
        raise RuntimeError("work-product PR-head postcondition was not observed")

    observed_commit = _as_mapping(
        cast(object, _github_json(repository, token, f"git/commits/{revision}"))
    )
    observed_tree = None if observed_commit is None else _as_mapping(observed_commit.get("tree"))
    parents = None if observed_commit is None else observed_commit.get("parents")
    observed_parent_shas: list[str] = []
    if isinstance(parents, list):
        for raw_parent in parents:
            parent = _as_mapping(raw_parent)
            parent_sha = None if parent is None else parent.get("sha")
            if not _valid_sha(parent_sha):
                raise RuntimeError("work-product commit parent identity is incomplete")
            observed_parent_shas.append(cast(str, parent_sha))
    if (
        observed_commit is None
        or observed_commit.get("sha") != revision
        or observed_commit.get("message") != commit_message
        or observed_tree is None
        or observed_tree.get("sha") != tree_sha
        or observed_parent_shas != commit_parents
    ):
        raise RuntimeError("work-product commit postcondition was not observed")
    for file in plan.manifest.files:
        if (
            _content_sha_at(
                repository,
                token,
                path=file.path,
                revision=cast(str, revision),
            )
            != file.blob_sha
        ):
            raise RuntimeError("work-product file postcondition was not observed")

    plan_id = make_carrier_plan(
        repository=repository,
        issue_number=plan.source.issue_number,
        change=plan.expected_change,
        action=plan.source.action,
        authorization_revision=authorization_revision,
        operation="pull-request-head-update",
        target={
            "repository": repository,
            "pull_request_number": plan.pr_number,
            "ref": f"refs/heads/{plan.manifest.branch}",
        },
        expected={
            "ref": f"refs/heads/{plan.manifest.branch}",
            "ref_sha": current_head,
            "pull_request": carrier_pr_identity(pr),
            "commit_parents": commit_parents,
            "commit_tree_sha": cast(str, tree_sha),
            "commit_message": commit_message,
        },
        requested={
            "ref": f"refs/heads/{plan.manifest.branch}",
            "sha": cast(str, revision),
            "force": False,
            "pull_request_number": plan.pr_number,
            "expected_head_sha": current_head,
            "commit_parents": commit_parents,
            "commit_tree_sha": cast(str, tree_sha),
            "commit_message": commit_message,
        },
        expected_postcondition={
            "ref": f"refs/heads/{plan.manifest.branch}",
            "ref_sha": cast(str, revision),
            "pull_request_number": plan.pr_number,
            "pull_request_head_sha": cast(str, revision),
            "state": "open",
            "merged": False,
            "commit_sha": cast(str, revision),
            "commit_parents": commit_parents,
            "commit_tree_sha": cast(str, tree_sha),
            "commit_message": commit_message,
        },
    )
    raise CarrierRequired(plan_id)
