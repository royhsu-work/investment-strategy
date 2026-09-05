"""Application-owned Change/work-product materialization for one effect ingress.

The semantic worker may request only content-addressed blob references.  This
module turns those references into a repository-owned carrier or exact
validation target after fresh repository authorization.  It deliberately has
no Issue-comment protocol and never consumes a dispatch Artifact.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from urllib.parse import quote, urlencode

from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_validation_resource import (
    ValidationResourcePlan,
    ValidationResourceTarget,
    WorkProductFile,
    WorkProductManifest,
    WorkProductPlan,
    _as_mapping,
    _change_from_issue,
    _content_sha_at,
    _current_authorized_request,
    _current_default_branch,
    _github_json,
    _open_pr_payload,
    _ref_head_sha,
    _review_openspec_required,
    _source_branch,
    _valid_branch,
    _valid_repo_path,
    _valid_sha,
    apply_work_product,
    resolve_validation_resource_target,
    work_product_path_allowed,
)

_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_ISSUE_LINK = re.compile(r"(?mi)^\s*Refs\s+#([0-9]+)\s*$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_MATERIALIZATION_OPERATION = "application-materialize"


@dataclass(frozen=True)
class MaterializationRequest:
    """Untrusted content-addressed materialization input from a worker result."""

    issue_number: int
    expected_change: str
    change: str
    branch: str
    base_sha: str
    message: str
    files: tuple[WorkProductFile, ...]
    pr_number: int | None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _valid_change(value: object, *, allow_unset: bool = False) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and (allow_unset or value != "unset")
        and not any(character.isspace() for character in value)
    )


def parse_materialization_payload(
    payload: Mapping[str, object],
    source: WorkerRequest,
) -> MaterializationRequest:
    """Validate the single generic materialization capability envelope."""

    allowed = {
        "issue_number",
        "operation",
        "expected_change",
        "change",
        "branch",
        "base_sha",
        "message",
        "files",
        "pr_number",
    }
    if set(payload) - allowed or payload.get("operation") != _MATERIALIZATION_OPERATION:
        raise ValueError("application materialization payload shape is invalid")
    if payload.get("issue_number") != source.issue_number:
        raise ValueError("application materialization Issue identity is invalid")
    expected_change = payload.get("expected_change")
    change = payload.get("change")
    branch = payload.get("branch")
    base_sha = payload.get("base_sha")
    message = payload.get("message")
    raw_files = payload.get("files")
    pr_number = payload.get("pr_number")
    if (
        not _valid_change(expected_change, allow_unset=True)
        or not _valid_change(change)
        or not _valid_branch(branch)
        or not _valid_sha(base_sha)
        or not isinstance(message, str)
        or not message.strip()
        or not isinstance(raw_files, list)
        or (pr_number is not None and _positive_int(pr_number) is None)
    ):
        raise ValueError("application materialization identity is invalid")
    if branch != _source_branch(change):
        raise ValueError("application materialization branch is not bound to Change")

    files: list[WorkProductFile] = []
    seen_paths: set[str] = set()
    for raw_file in raw_files:
        if not isinstance(raw_file, Mapping) or set(raw_file) != {
            "path",
            "blob_sha",
            "expected_sha",
        }:
            raise ValueError("application materialization file manifest is invalid")
        path = raw_file.get("path")
        blob_sha = raw_file.get("blob_sha")
        expected_sha = raw_file.get("expected_sha")
        if (
            not _valid_repo_path(path)
            or not _valid_sha(blob_sha)
            or (expected_sha is not None and not _valid_sha(expected_sha))
        ):
            raise ValueError("application materialization file identity is invalid")
        normalized_path = cast(str, path)
        if normalized_path in seen_paths:
            raise ValueError("application materialization contains duplicate paths")
        seen_paths.add(normalized_path)
        files.append(
            WorkProductFile(
                path=normalized_path,
                blob_sha=cast(str, blob_sha),
                expected_sha=cast(str | None, expected_sha),
            )
        )

    normalized_expected = cast(str, expected_change)
    normalized_pr = None if pr_number is None else cast(int, pr_number)
    if normalized_expected == "unset":
        if source != WorkerRequest(source.issue_number, "lead", "propose-change"):
            raise ValueError("first Change materialization is only legal for Lead / propose-change")
        if (
            normalized_pr is not None
            or not files
            or any(file.expected_sha is not None for file in files)
        ):
            raise ValueError("first Change materialization must create only new paths")
        prefix = f"openspec/changes/{cast(str, change)}/"
        if any(not file.path.startswith(prefix) for file in files):
            raise ValueError("first Change materialization path is outside the Change")
    else:
        if normalized_pr is None:
            raise ValueError("existing Change materialization requires an exact PR")
        if normalized_expected != change:
            raise ValueError("existing Change materialization Change identity is inconsistent")
        if files and not all(
            work_product_path_allowed(source, normalized_expected, file.path) for file in files
        ):
            raise ValueError("existing Change materialization path is outside Action capability")

    return MaterializationRequest(
        issue_number=source.issue_number,
        expected_change=normalized_expected,
        change=cast(str, change),
        branch=cast(str, branch),
        base_sha=cast(str, base_sha),
        message=message,
        files=tuple(files),
        pr_number=normalized_pr,
    )


def materialization_requires_validation(
    request: MaterializationRequest,
    source: WorkerRequest,
) -> bool:
    """Derive exact OpenSpec validation need from the requested capability."""

    if not request.files:
        return True
    return any(file.path.startswith("openspec/") for file in request.files) and (
        _review_openspec_required(source)
    )


def _branch_head(repository: str, token: str, branch: str) -> str | None:
    payload = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                f"git/ref/heads/{quote(branch, safe='/')}",
                allow_not_found=True,
            ),
        )
    )
    if payload is None:
        return None
    obj = _as_mapping(payload.get("object"))
    sha = None if obj is None else obj.get("sha")
    if not _valid_sha(sha):
        raise RuntimeError("application materialization branch observation is incomplete")
    return cast(str, sha)


def _matching_prs(
    repository: str,
    token: str,
    branch: str,
    default_branch: str,
) -> list[Mapping[str, object]]:
    owner = repository.split("/", 1)[0]
    query = urlencode(
        {"state": "all", "head": f"{owner}:{branch}", "base": default_branch, "per_page": 100}
    )
    raw = _github_json(repository, token, f"pulls?{query}")
    if not isinstance(raw, list) or len(raw) >= 100:
        raise RuntimeError("application materialization PR discovery is incomplete")
    result: list[Mapping[str, object]] = []
    for item in raw:
        payload = _as_mapping(item)
        if payload is None:
            raise RuntimeError("application materialization PR discovery is malformed")
        result.append(payload)
    return result


def _pr_matches(
    pr: Mapping[str, object],
    *,
    repository: str,
    branch: str,
    default_branch: str,
    revision: str,
    issue_number: int,
    change: str,
) -> bool:
    head = _as_mapping(pr.get("head"))
    base = _as_mapping(pr.get("base"))
    head_repo = None if head is None else _as_mapping(head.get("repo"))
    base_repo = None if base is None else _as_mapping(base.get("repo"))
    body = pr.get("body")
    title = pr.get("title")
    if not isinstance(body, str) or not isinstance(title, str):
        return False
    issue_link = _ISSUE_LINK.search(body)
    return bool(
        pr.get("state") == "open"
        and pr.get("merged") is not True
        and head is not None
        and base is not None
        and head_repo is not None
        and base_repo is not None
        and head_repo.get("full_name") == repository
        and base_repo.get("full_name") == repository
        and head.get("ref") == branch
        and head.get("sha") == revision
        and base.get("ref") == default_branch
        and f"OpenSpec: {change}" in title
        and issue_link is not None
        and int(issue_link.group(1)) == issue_number
    )


def _verify_revision(
    repository: str,
    token: str,
    request: MaterializationRequest,
    revision: str,
) -> None:
    comparison = _as_mapping(
        cast(object, _github_json(repository, token, f"compare/{request.base_sha}...{revision}"))
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
        raise RuntimeError("application materialization revision is not one commit on the base")
    observed_paths: set[str] = set()
    for raw_file in files:
        observed_file = _as_mapping(raw_file)
        filename = None if observed_file is None else observed_file.get("filename")
        if not isinstance(filename, str):
            raise RuntimeError("application materialization revision file evidence is incomplete")
        observed_paths.add(filename)
    if observed_paths != {file.path for file in request.files}:
        raise RuntimeError("application materialization revision contains unrelated paths")
    for file in request.files:
        if _content_sha_at(repository, token, path=file.path, revision=revision) != file.blob_sha:
            raise RuntimeError(
                "application materialization revision does not resolve requested blobs"
            )


def _create_revision(
    repository: str,
    token: str,
    request: MaterializationRequest,
) -> str:
    commit = _as_mapping(
        cast(object, _github_json(repository, token, f"git/commits/{request.base_sha}"))
    )
    base_tree = None if commit is None else _as_mapping(commit.get("tree"))
    base_tree_sha = None if base_tree is None else base_tree.get("sha")
    if not _valid_sha(base_tree_sha):
        raise RuntimeError("application materialization base tree identity is incomplete")
    tree = _as_mapping(
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
                        {"path": f.path, "mode": "100644", "type": "blob", "sha": f.blob_sha}
                        for f in request.files
                    ],
                },
            ),
        )
    )
    tree_sha = None if tree is None else tree.get("sha")
    if not _valid_sha(tree_sha):
        raise RuntimeError("application materialization tree creation returned no SHA")
    created = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                "git/commits",
                method="POST",
                payload={
                    "message": request.message,
                    "tree": cast(str, tree_sha),
                    "parents": [request.base_sha],
                },
            ),
        )
    )
    revision = None if created is None else created.get("sha")
    if not _valid_sha(revision):
        raise RuntimeError("application materialization commit creation returned no SHA")
    return cast(str, revision)


def _ensure_new_carrier(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    default_branch: str,
) -> tuple[str, int]:
    for file in request.files:
        if (
            _content_sha_at(
                repository,
                token,
                path=file.path,
                revision=request.base_sha,
            )
            is not None
        ):
            raise RuntimeError(
                "application materialization first-carrier path already exists at base"
            )
    existing_directory = _github_json(
        repository,
        token,
        f"contents/openspec/changes/{quote(request.change, safe='')}?"
        f"{urlencode({'ref': request.base_sha})}",
        allow_not_found=True,
    )
    if existing_directory is not None:
        raise RuntimeError("application materialization Change directory already exists at base")
    revision = _branch_head(repository, token, request.branch)
    if revision is None:
        revision = _create_revision(repository, token, request)
        _github_json(
            repository,
            token,
            "git/refs",
            method="POST",
            payload={"ref": f"refs/heads/{request.branch}", "sha": revision},
        )
        if _branch_head(repository, token, request.branch) != revision:
            raise RuntimeError("application materialization branch postcondition was not observed")
    _verify_revision(repository, token, request, revision)

    prs = _matching_prs(repository, token, request.branch, default_branch)
    if len(prs) > 1:
        raise RuntimeError("application materialization found duplicate Change PR carriers")
    if not prs:
        created = _as_mapping(
            cast(
                object,
                _github_json(
                    repository,
                    token,
                    "pulls",
                    method="POST",
                    payload={
                        "title": f"OpenSpec: {request.change}",
                        "body": (
                            f"Formalize OpenSpec change `{request.change}`.\n\n"
                            f"Refs #{source.issue_number}"
                        ),
                        "head": request.branch,
                        "base": default_branch,
                        "draft": False,
                    },
                ),
            )
        )
        number = None if created is None else created.get("number")
        if _positive_int(number) is None:
            raise RuntimeError("application materialization PR creation returned no identity")
        fresh = _as_mapping(cast(object, _github_json(repository, token, f"pulls/{number}")))
        if fresh is None:
            raise RuntimeError("application materialization PR postcondition is unavailable")
        prs = [fresh]
    pr = prs[0]
    number = pr.get("number")
    if _positive_int(number) is None or not _pr_matches(
        pr,
        repository=repository,
        branch=request.branch,
        default_branch=default_branch,
        revision=revision,
        issue_number=source.issue_number,
        change=request.change,
    ):
        raise RuntimeError("application materialization Change PR identity is invalid")
    return revision, cast(int, number)


def _persist_change(
    request: MaterializationRequest,
    *,
    repository: str,
    token: str,
) -> None:
    issue = _as_mapping(
        cast(object, _github_json(repository, token, f"issues/{request.issue_number}"))
    )
    if issue is None or issue.get("state") != "open":
        raise RuntimeError("application materialization source Issue is not open")
    current = _change_from_issue(issue)
    if current == request.change:
        return
    if current != "unset":
        raise RuntimeError("application materialization source Change is no longer unset")
    body = issue.get("body")
    if not isinstance(body, str) or _CHANGE_LINE.findall(body) != ["unset"]:
        raise RuntimeError("application materialization source Change line is ambiguous")
    updated, count = _CHANGE_LINE.subn(f"Change: {request.change}", body, count=1)
    if count != 1:
        raise RuntimeError("application materialization Change update is ambiguous")
    _github_json(
        repository,
        token,
        f"issues/{request.issue_number}",
        method="PATCH",
        payload={"body": updated},
    )
    fresh = _as_mapping(
        cast(object, _github_json(repository, token, f"issues/{request.issue_number}"))
    )
    if fresh is None or _change_from_issue(fresh) != request.change:
        raise RuntimeError("application materialization Change postcondition was not observed")


def _target(
    request: MaterializationRequest,
    *,
    repository: str,
    revision: str,
    pr_number: int,
    validation_required: bool,
) -> ValidationResourceTarget:
    return ValidationResourceTarget(
        repository=repository,
        revision=revision,
        correlation=f"effect-request-{request.issue_number}",
        pr_number=pr_number,
        change=request.change,
        validation_required=validation_required,
    )


def _existing_target(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    default_branch: str,
) -> ValidationResourceTarget:
    if request.pr_number is None:
        raise RuntimeError("existing Change materialization requires an exact PR")
    plan = WorkProductPlan(
        True,
        source=source,
        pr_number=request.pr_number,
        expected_change=request.expected_change,
        manifest=WorkProductManifest(
            branch=request.branch,
            base_sha=request.base_sha,
            message=request.message,
            files=request.files,
        ),
    )
    if request.files:
        target = apply_work_product(
            plan,
            repository=repository,
            token=token,
            default_branch=default_branch,
        )
    else:
        target = resolve_validation_resource_target(
            ValidationResourcePlan(
                True,
                source=source,
                pr_number=request.pr_number,
                expected_change=request.expected_change,
            ),
            repository=repository,
            token=token,
            default_branch=default_branch,
        )
    return ValidationResourceTarget(
        repository=target.repository,
        revision=target.revision,
        correlation=f"effect-request-{request.issue_number}",
        pr_number=target.pr_number,
        change=target.change,
        validation_required=materialization_requires_validation(request, source),
    )


def apply_materialization(
    payload: Mapping[str, object],
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    promote_change: bool = False,
    validated_revision: str | None = None,
) -> ValidationResourceTarget:
    """Freshly authorize and apply one generic carrier/materialization effect."""

    request = parse_materialization_payload(payload, source)
    if _current_authorized_request(repository, token) != source:
        raise RuntimeError("application materialization source dispatch is stale")
    if _current_default_branch(repository, token) != default_branch:
        raise RuntimeError("application materialization default branch changed")
    if _ref_head_sha(repository, token, default_branch) != current_revision:
        raise RuntimeError("application materialization default-branch revision is stale")

    issue = _as_mapping(
        cast(object, _github_json(repository, token, f"issues/{source.issue_number}"))
    )
    if (
        issue is None
        or issue.get("state") != "open"
        or _change_from_issue(issue) != request.expected_change
    ):
        raise RuntimeError("application materialization Issue/Change identity changed")

    if request.expected_change == "unset":
        if request.base_sha != current_revision:
            raise RuntimeError("application materialization first-carrier base is stale")
        revision, pr_number = _ensure_new_carrier(
            request,
            source,
            repository=repository,
            token=token,
            default_branch=default_branch,
        )
        target = _target(
            request,
            repository=repository,
            revision=revision,
            pr_number=pr_number,
            validation_required=True,
        )
        if promote_change:
            if validated_revision != target.revision:
                raise RuntimeError("application materialization validation revision is stale")
            _persist_change(request, repository=repository, token=token)
        return target

    target = _existing_target(
        request,
        source,
        repository=repository,
        token=token,
        default_branch=default_branch,
    )
    return target


def materialization_postcondition(
    payload: Mapping[str, object],
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    target: ValidationResourceTarget | None,
) -> bool:
    """Observe the exact carrier/PR/Change postcondition after application."""

    if target is None:
        return False
    try:
        request = parse_materialization_payload(payload, source)
        if request.expected_change == "unset" and request.base_sha != current_revision:
            return False
        if _current_default_branch(repository, token) != default_branch:
            return False
        if _ref_head_sha(repository, token, default_branch) != current_revision:
            return False
        issue = _as_mapping(
            cast(object, _github_json(repository, token, f"issues/{source.issue_number}"))
        )
        if issue is None or issue.get("state") != "open":
            return False
        current_change = _change_from_issue(issue)
        if current_change not in {request.expected_change, request.change}:
            return False
        if _branch_head(repository, token, request.branch) != target.revision:
            return False
        pr = _as_mapping(cast(object, _github_json(repository, token, f"pulls/{target.pr_number}")))
        if pr is None:
            return False
        if request.expected_change == "unset":
            return _pr_matches(
                pr,
                repository=repository,
                branch=request.branch,
                default_branch=default_branch,
                revision=target.revision,
                issue_number=source.issue_number,
                change=request.change,
            )
        current = _open_pr_payload(
            repository=repository,
            token=token,
            pr_number=target.pr_number,
            source=source,
            expected_change=request.expected_change,
            default_branch=default_branch,
        )
        head = _as_mapping(current.get("head"))
        return head is not None and head.get("sha") == target.revision
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError):
        return False


def observe_materialization_target(
    payload: Mapping[str, object],
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
) -> ValidationResourceTarget:
    """Resolve the exact carrier revision after a materialization effect."""

    request = parse_materialization_payload(payload, source)
    if _current_authorized_request(repository, token) != source:
        raise RuntimeError("application materialization source dispatch is stale")
    if _current_default_branch(repository, token) != default_branch:
        raise RuntimeError("application materialization default branch changed")
    if _ref_head_sha(repository, token, default_branch) != current_revision:
        raise RuntimeError("application materialization default-branch revision is stale")
    if request.expected_change == "unset":
        if request.base_sha != current_revision:
            raise RuntimeError("application materialization first-carrier base is stale")
        revision = _branch_head(repository, token, request.branch)
        if revision is None:
            raise RuntimeError("application materialization branch is unavailable")
        prs = _matching_prs(repository, token, request.branch, default_branch)
        if len(prs) != 1:
            raise RuntimeError("application materialization carrier count is not exactly one")
        pr = prs[0]
        number = pr.get("number")
        if _positive_int(number) is None or not _pr_matches(
            pr,
            repository=repository,
            branch=request.branch,
            default_branch=default_branch,
            revision=revision,
            issue_number=source.issue_number,
            change=request.change,
        ):
            raise RuntimeError("application materialization carrier postcondition is invalid")
        _verify_revision(repository, token, request, revision)
        return _target(
            request,
            repository=repository,
            revision=revision,
            pr_number=cast(int, number),
            validation_required=True,
        )

    if request.pr_number is None:
        raise RuntimeError("application materialization validation target lacks PR")
    target = resolve_validation_resource_target(
        ValidationResourcePlan(
            True,
            source=source,
            pr_number=request.pr_number,
            expected_change=request.expected_change,
        ),
        repository=repository,
        token=token,
        default_branch=default_branch,
    )
    return ValidationResourceTarget(
        repository=target.repository,
        revision=target.revision,
        correlation=f"effect-request-{source.issue_number}",
        pr_number=target.pr_number,
        change=target.change,
        validation_required=materialization_requires_validation(request, source),
    )


def find_materialization_payload(
    payload: Mapping[str, object],
    source: WorkerRequest,
) -> MaterializationRequest | None:
    """Return a validated materialization request, if this is that effect."""

    if payload.get("operation") != _MATERIALIZATION_OPERATION:
        return None
    return parse_materialization_payload(payload, source)


__all__ = [
    "MaterializationRequest",
    "apply_materialization",
    "find_materialization_payload",
    "materialization_postcondition",
    "materialization_requires_validation",
    "observe_materialization_target",
    "parse_materialization_payload",
]
