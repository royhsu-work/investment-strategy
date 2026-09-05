"""Application-owned exact validation and content-addressed work-product helpers."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import cast
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_action_model import TRANSITIONS
from investment_strategy.scheduled_agent_action_model import (
    Action as ModelAction,
)
from investment_strategy.scheduled_agent_carrier import (
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
        return path.startswith(change_prefix)
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
) -> Mapping[str, object]:
    if _current_default_branch(repository, token) != default_branch:
        raise RuntimeError("validation resource repository default branch changed")
    expected_branch = _source_branch(expected_change)
    if expected_branch is None:
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
        or head.get("ref") != expected_branch
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
    if not has_expected_change or active_change_names != {expected_change}:
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
) -> str:
    pr = _open_pr_payload(
        repository=repository,
        token=token,
        pr_number=pr_number,
        source=source,
        expected_change=expected_change,
        default_branch=default_branch,
    )
    head = _as_mapping(pr.get("head"))
    revision = None if head is None else head.get("sha")
    if not _valid_sha(revision):
        raise RuntimeError("validation resource target PR head is incomplete")
    return cast(str, revision)


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


def _ref_head_sha(repository: str, token: str, branch: str) -> str:
    state = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                f"git/ref/heads/{quote(branch, safe='/')}",
            ),
        )
    )
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
    replay_manifest = False
    if current_head != plan.manifest.base_sha:
        if historical_merged_carrier:
            raise RuntimeError("work-product cannot update a historical merged carrier")
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
        if not manifest_applied and not reconciled:
            raise RuntimeError("work-product PR head/base identity is stale")
        replay_manifest = True
    if historical_merged_carrier:
        raise RuntimeError("work-product PR head/base identity is stale")

    needs_default_reconciliation = not default_branch_is_ancestor
    if needs_default_reconciliation:
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

    base_commit = _as_mapping(
        cast(object, _github_json(repository, token, f"git/commits/{current_head}"))
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

    if _ref_head_sha(repository, token, plan.manifest.branch) != current_head:
        raise RuntimeError("work-product branch base changed before carrier handoff")
    if _ref_head_sha(repository, token, default_branch) != authorization_revision:
        raise RuntimeError("work-product default branch changed before carrier handoff")
    if _current_authorized_request(repository, token) != plan.source:
        raise RuntimeError("work-product source dispatch changed before carrier handoff")

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

    if _ref_head_sha(repository, token, plan.manifest.branch) != current_head:
        raise RuntimeError("work-product branch base changed before carrier handoff")
    if _ref_head_sha(repository, token, default_branch) != authorization_revision:
        raise RuntimeError("work-product default branch changed before carrier handoff")
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
