"""Application-owned Change/work-product materialization for one effect ingress.

The semantic worker may request only content-addressed blob references. This
module turns those references into a repository-owned carrier or exact
validation target after fresh repository authorization. It deliberately has
no Issue-comment protocol and never consumes a dispatch Artifact.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Literal, cast
from urllib.parse import quote, urlencode

from investment_strategy.native_closing_preflight import has_native_closing_reference
from investment_strategy.scheduled_agent_application_carrier import (
    ImplementationCarrierQualification,
    _claimed_open_carriers,
    _historical_carriers,
    qualify_implementation_carrier,
)
from investment_strategy.scheduled_agent_carrier import (
    CarrierPlan,
    CarrierRequired,
    carrier_pr_identity,
    make_carrier_plan,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_validation_resource import (
    ValidationResourcePlan,
    ValidationResourceTarget,
    WorkProductFile,
    WorkProductManifest,
    WorkProductPlan,
    _ancestor_comparison_paths,
    _as_mapping,
    _blob_text,
    _change_carrier_decision,
    _change_from_issue,
    _comparison_file_paths,
    _comparison_paths_from_file_entries,
    _construct_work_product,
    _content_sha_at,
    _content_text_at,
    _current_authorized_request,
    _current_default_branch,
    _github_json,
    _is_executor_config_authoring,
    _is_executor_task_and_implementation_materialization,
    _is_executor_task_bookkeeping,
    _is_historical_merged_carrier,
    _open_pr_payload,
    _pending_source_is_current,
    _ref_head_sha,
    _replacement_branch,
    _review_openspec_required,
    _source_branch,
    _task_marker_update_is_monotonic,
    _valid_branch,
    _valid_repo_path,
    _valid_sha,
    completed_task_bookkeeping_is_current,
    resolve_validation_resource_target,
    work_product_path_allowed,
)

_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_ISSUE_LINK = re.compile(r"(?mi)^\s*Refs\s+#([0-9]+)\s*$")
_MATERIALIZATION_OPERATION = "application-materialize"
_IMPLEMENTATION_ACTION = "implement-change"


def materialization_message_is_safe(
    message: str,
    *,
    repository: str,
    issue_number: int,
) -> bool:
    """Return whether a producer commit message preserves the source Issue."""
    return not has_native_closing_reference(
        message,
        repository_full_name=repository,
        coordination_issue=issue_number,
    )


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


@dataclass(frozen=True)
class MaterializationRevisions:
    """Authorization, declared base, actual write parent and fresh default differ."""

    accepted_authorization: str
    carrier_base: str
    mutation_preimage: str
    current_default: str


@dataclass(frozen=True)
class MaterializationWitness:
    """Immutable accepted content, independent of the current validation target."""

    revision: str
    desired_blobs: tuple[tuple[str, str], ...]
    revisions: MaterializationRevisions


@dataclass(frozen=True)
class MaterializationProof:
    disposition: Literal["COMPLETE", "INCOMPLETE", "CONTRADICTORY"]
    target: ValidationResourceTarget | None = None
    witness: MaterializationWitness | None = None
    reason: str | None = None
    application_request: MaterializationRequest | None = None

    def __post_init__(self) -> None:
        if self.disposition == "COMPLETE":
            if self.target is None or self.witness is None or self.reason is not None:
                raise ValueError("complete materialization requires target and witness")
        elif self.target is not None or self.witness is not None:
            raise ValueError("unproved materialization cannot carry a target or witness")
        elif self.disposition == "CONTRADICTORY" and not self.reason:
            raise ValueError("contradictory materialization requires a reason")


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
    """Validate the structural materialization envelope, not carrier semantics."""

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
        # First-carrier creation remains intentionally strict. Continuation
        # qualification applies only after immutable Change identity exists.
        if branch != _source_branch(change):
            raise ValueError("first Change materialization branch is not bound to Change")
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
        # Branch identity is intentionally structural here. The application
        # carrier qualifier owns semantic initial/continuation eligibility.
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
) -> list[Mapping[str, object]]:
    owner = repository.split("/", 1)[0]
    query = urlencode({"state": "all", "head": f"{owner}:{branch}", "per_page": 100})
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
    base_revision: str | None = None,
    require_openspec_title: bool = True,
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
        and (base_revision is None or base.get("sha") == base_revision)
        and (not require_openspec_title or f"OpenSpec: {change}" in title)
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
    base_commit = None if comparison is None else _as_mapping(comparison.get("base_commit"))
    files = None if comparison is None else comparison.get("files")
    commits = None if comparison is None else comparison.get("commits")
    commit = _as_mapping(commits[0]) if isinstance(commits, list) and len(commits) == 1 else None
    parents = None if commit is None else commit.get("parents")
    parent = _as_mapping(parents[0]) if isinstance(parents, list) and len(parents) == 1 else None
    if (
        comparison is None
        or comparison.get("status") != "ahead"
        or _positive_int(comparison.get("ahead_by")) != 1
        or comparison.get("behind_by") != 0
        or comparison.get("too_large") is True
        or not _valid_sha(revision)
        or base_commit is None
        or base_commit.get("sha") != request.base_sha
        or commit is None
        or commit.get("sha") != revision
        or not isinstance(parents, list)
        or len(parents) != 1
        or parent is None
        or parent.get("sha") != request.base_sha
        or not isinstance(files, list)
        or len(files) >= 300
    ):
        raise RuntimeError("application materialization revision is not one commit on the base")
    try:
        observed_paths = _comparison_paths_from_file_entries(
            files,
            malformed_error="application materialization revision file evidence is incomplete",
        )
    except RuntimeError as exc:
        raise RuntimeError(
            "application materialization revision file evidence is incomplete"
        ) from exc
    if observed_paths != {file.path for file in request.files}:
        raise RuntimeError("application materialization revision contains unrelated paths")
    for file in request.files:
        if _content_sha_at(repository, token, path=file.path, revision=revision) != file.blob_sha:
            raise RuntimeError(
                "application materialization revision does not resolve requested blobs"
            )


def _verify_existing_pr_revision_lineage(
    repository: str,
    token: str,
    request: MaterializationRequest,
    revision: str,
) -> None:
    """Verify an existing PR still descends from its exact accepted first commit.

    An open first-carrier PR may receive later commits that refine the same
    OpenSpec Change while review is pending. Reuse that carrier only when the
    immutable accepted manifest is the first exact commit, every descendant
    is linear and changes only manifest paths, and every current manifest path
    is present at the observed head. A branch without its exact PR remains
    subject to ``_verify_revision``'s single-commit rule.
    """

    expected_paths = {file.path for file in request.files}
    comparison = _as_mapping(
        cast(object, _github_json(repository, token, f"compare/{request.base_sha}...{revision}"))
    )
    base_commit = None if comparison is None else _as_mapping(comparison.get("base_commit"))
    commits = None if comparison is None else comparison.get("commits")
    files = None if comparison is None else comparison.get("files")
    ahead_by = None if comparison is None else _positive_int(comparison.get("ahead_by"))
    if (
        comparison is None
        or comparison.get("status") != "ahead"
        or comparison.get("behind_by") != 0
        or base_commit is None
        or base_commit.get("sha") != request.base_sha
        or ahead_by is None
        or ahead_by > 32
        or not isinstance(commits, list)
        or len(commits) != ahead_by
        or ahead_by < 1
        or not isinstance(files, list)
        or len(files) >= 300
    ):
        raise RuntimeError("application materialization PR lineage is incomplete")

    changed_paths = _comparison_paths_from_file_entries(
        files,
        malformed_error="application materialization PR path evidence is incomplete",
    )
    if changed_paths != expected_paths:
        raise RuntimeError("application materialization PR contains unrelated or missing paths")

    previous = request.base_sha
    observed_commits: set[str] = set()
    for index, raw_commit in enumerate(commits):
        commit = _as_mapping(raw_commit)
        sha = None if commit is None else commit.get("sha")
        parents = None if commit is None else commit.get("parents")
        parent = (
            _as_mapping(parents[0]) if isinstance(parents, list) and len(parents) == 1 else None
        )
        if (
            not _valid_sha(sha)
            or sha in observed_commits
            or not isinstance(parents, list)
            or len(parents) != 1
            or parent is None
            or parent.get("sha") != previous
        ):
            raise RuntimeError("application materialization PR ancestry is not linear")
        observed_commits.add(cast(str, sha))
        if index == 0:
            _verify_revision(repository, token, request, cast(str, sha))
        else:
            delta = _as_mapping(
                cast(object, _github_json(repository, token, f"compare/{previous}...{sha}"))
            )
            delta_base = None if delta is None else _as_mapping(delta.get("base_commit"))
            delta_commits = None if delta is None else delta.get("commits")
            delta_files = None if delta is None else delta.get("files")
            delta_commit = (
                _as_mapping(delta_commits[0])
                if isinstance(delta_commits, list) and len(delta_commits) == 1
                else None
            )
            delta_parents = None if delta_commit is None else delta_commit.get("parents")
            delta_parent = (
                _as_mapping(delta_parents[0])
                if isinstance(delta_parents, list) and len(delta_parents) == 1
                else None
            )
            if (
                delta is None
                or delta.get("status") != "ahead"
                or _positive_int(delta.get("ahead_by")) != 1
                or delta.get("behind_by") != 0
                or delta_base is None
                or delta_base.get("sha") != previous
                or not isinstance(delta_commits, list)
                or len(delta_commits) != 1
                or delta_commit is None
                or delta_commit.get("sha") != sha
                or not isinstance(delta_parents, list)
                or len(delta_parents) != 1
                or delta_parent is None
                or delta_parent.get("sha") != previous
                or not isinstance(delta_files, list)
                or not delta_files
                or len(delta_files) >= 300
                or delta.get("too_large") is True
            ):
                raise RuntimeError(
                    "application materialization PR descendant evidence is incomplete"
                )
            delta_paths = _comparison_paths_from_file_entries(
                delta_files,
                malformed_error="application materialization PR descendant paths are incomplete",
            )
            if not delta_paths.issubset(expected_paths):
                raise RuntimeError(
                    "application materialization PR descendant changes unrelated paths"
                )
        previous = cast(str, sha)

    if previous != revision:
        raise RuntimeError(
            "application materialization PR head is not the final accepted descendant"
        )
    for file in request.files:
        if not _valid_sha(_content_sha_at(repository, token, path=file.path, revision=revision)):
            raise RuntimeError("application materialization PR head is missing a manifest path")


def _create_revision(
    repository: str,
    token: str,
    request: MaterializationRequest,
    before_write: Callable[[], None] | None = None,
) -> str:
    commit = _as_mapping(
        cast(object, _github_json(repository, token, f"git/commits/{request.base_sha}"))
    )
    base_tree = None if commit is None else _as_mapping(commit.get("tree"))
    base_tree_sha = None if base_tree is None else base_tree.get("sha")
    if not _valid_sha(base_tree_sha):
        raise RuntimeError("application materialization base tree identity is incomplete")
    if before_write is not None:
        before_write()
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
    if before_write is not None:
        before_write()
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


def _verify_new_carrier_base_is_empty(
    request: MaterializationRequest,
    *,
    repository: str,
    token: str,
) -> None:
    """Recheck that immutable first-carrier intent only adds new Change paths."""

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


def _new_carrier_pr_plan(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    default_branch: str,
    authorization_revision: str,
    revision: str,
) -> CarrierPlan:
    title = f"OpenSpec: {request.change}"
    body = f"Formalize OpenSpec change `{request.change}`.\n\nRefs #{source.issue_number}"
    return make_carrier_plan(
        repository=repository,
        issue_number=source.issue_number,
        change=request.change,
        action=source.action,
        authorization_revision=authorization_revision,
        operation="pull-request-create",
        target={
            "head_ref": request.branch,
            "base_ref": default_branch,
            "repository": repository,
        },
        expected={
            "head_ref": request.branch,
            "head_sha": revision,
            "base_ref": default_branch,
            "base_sha": authorization_revision,
            "existing_pr_count": 0,
        },
        requested={
            "title": title,
            "body": body,
            "head": request.branch,
            "base": default_branch,
            "draft": False,
            "head_sha": revision,
        },
        expected_postcondition={
            "repository": repository,
            "issue_number": source.issue_number,
            "state": "open",
            "merged": False,
            "title": title,
            "body": body,
            "draft": False,
            "head_ref": request.branch,
            "head_sha": revision,
            "base_ref": default_branch,
            "base_sha": authorization_revision,
        },
    )


def _ensure_new_carrier(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    default_branch: str,
    authorization_revision: str,
    before_write: Callable[[], None] | None = None,
) -> tuple[str, int]:
    _verify_new_carrier_base_is_empty(request, repository=repository, token=token)
    revision = _branch_head(repository, token, request.branch)
    if revision is None:
        revision = _create_revision(repository, token, request, before_write=before_write)
        if before_write is not None:
            before_write()
        existing_head = _branch_head(repository, token, request.branch)
        if existing_head is not None and existing_head != revision:
            raise RuntimeError("application materialization branch changed before ref creation")
        if existing_head is None:
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

    prs = _matching_prs(repository, token, request.branch)
    if len(prs) > 1:
        raise RuntimeError("application materialization found duplicate Change PR carriers")
    if not prs:
        raise CarrierRequired(
            _new_carrier_pr_plan(
                request,
                source,
                repository=repository,
                default_branch=default_branch,
                authorization_revision=authorization_revision,
                revision=revision,
            )
        )
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
        base_revision=authorization_revision,
    ):
        raise RuntimeError("application materialization Change PR identity is invalid")
    return revision, cast(int, number)


def _pending_new_carrier(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    default_branch: str,
    current_revision: str,
    before_write: Callable[[], None] | None = None,
) -> tuple[str, int]:
    """Reconcile an existing first carrier after a disjoint default-branch advance."""

    try:
        default_paths = _ancestor_comparison_paths(
            repository,
            token,
            base_sha=request.base_sha,
            revision=current_revision,
        )
    except RuntimeError as exc:
        raise RuntimeError(
            "application materialization first-carrier base is not an ancestor"
        ) from exc
    carrier_paths = {file.path for file in request.files}
    if default_paths.intersection(carrier_paths):
        raise RuntimeError(
            "application materialization first-carrier base overlaps default-branch changes"
        )

    _verify_new_carrier_base_is_empty(request, repository=repository, token=token)

    revision = _branch_head(repository, token, request.branch)
    if revision is None:
        return _ensure_new_carrier(
            request,
            source,
            repository=repository,
            token=token,
            default_branch=default_branch,
            authorization_revision=current_revision,
            before_write=before_write,
        )
    prs = _matching_prs(repository, token, request.branch)
    if len(prs) > 1:
        raise RuntimeError("application materialization pending carrier count is ambiguous")
    if not prs:
        # Before PR creation the branch-ref interruption prefix remains exact:
        # only the one accepted content commit may be resumed.
        _verify_revision(repository, token, request, revision)
        raise CarrierRequired(
            _new_carrier_pr_plan(
                request,
                source,
                repository=repository,
                default_branch=default_branch,
                authorization_revision=current_revision,
                revision=revision,
            )
        )
    pr = prs[0]
    number = pr.get("number")
    base = _as_mapping(pr.get("base"))
    base_revision = None if base is None else base.get("sha")
    if (
        _positive_int(number) is None
        or not _pr_matches(
            pr,
            repository=repository,
            branch=request.branch,
            default_branch=default_branch,
            revision=revision,
            issue_number=source.issue_number,
            change=request.change,
        )
        or not _valid_sha(base_revision)
        or base_revision not in {request.base_sha, current_revision}
    ):
        raise RuntimeError("application materialization pending carrier identity is invalid")
    _verify_existing_pr_revision_lineage(repository, token, request, revision)
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
    branch: str | None = None,
) -> ValidationResourceTarget:
    return ValidationResourceTarget(
        repository=repository,
        revision=revision,
        correlation=f"effect-request-{request.issue_number}",
        pr_number=pr_number,
        change=request.change,
        validation_required=validation_required,
        branch=request.branch if branch is None else branch,
    )


def _implementation_manifest_capability_allowed(
    request: MaterializationRequest,
    source: WorkerRequest,
) -> bool:
    if not request.files:
        return True
    if not all(
        work_product_path_allowed(source, request.expected_change, file.path)
        for file in request.files
    ):
        return False
    if not any(file.path.startswith("openspec/") for file in request.files):
        return True
    return (
        _is_executor_task_bookkeeping(
            source,
            request.expected_change,
            request.files,
        )
        or _is_executor_task_and_implementation_materialization(
            source,
            request.expected_change,
            request.files,
        )
        or _is_executor_config_authoring(
            source,
            request.expected_change,
            request.files,
        )
    )


def _qualified_implementation_decision(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
) -> ImplementationCarrierQualification:
    if request.pr_number is None:
        raise RuntimeError("implementation materialization requires an exact PR")
    decision = qualify_implementation_carrier(
        repository=repository,
        token=token,
        source=source,
        change=request.expected_change,
        pr_number=request.pr_number,
        current_revision=current_revision,
    )
    if (
        decision.disposition not in {"QUALIFIED", "RECONCILIATION_REQUIRED", "HISTORICAL_MERGED"}
        or decision.branch != request.branch
        or decision.head_sha is None
        or decision.pr_number != request.pr_number
    ):
        raise RuntimeError(f"implementation carrier is not eligible: {decision.reason}")
    if decision.disposition == "HISTORICAL_MERGED" and (
        request.base_sha != decision.head_sha
        or not completed_task_bookkeeping_is_current(
            repository,
            token,
            change=request.change,
            revision=decision.head_sha,
            files=request.files,
        )
    ):
        raise RuntimeError(
            "historical implementation only permits unchanged complete task observation"
        )
    return decision


def _revision_tree_snapshot(
    repository: str,
    token: str,
    revision: str,
) -> tuple[str, dict[str, Mapping[str, object]]]:
    commit = _as_mapping(cast(object, _github_json(repository, token, f"git/commits/{revision}")))
    tree = None if commit is None else _as_mapping(commit.get("tree"))
    tree_sha = None if tree is None else tree.get("sha")
    if not _valid_sha(tree_sha):
        raise RuntimeError("implementation carrier tree identity is incomplete")
    payload = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                f"git/trees/{tree_sha}?recursive=1",
            ),
        )
    )
    raw_entries = None if payload is None else payload.get("tree")
    if (
        payload is None
        or payload.get("sha") != tree_sha
        or payload.get("truncated") is True
        or not isinstance(raw_entries, list)
    ):
        raise RuntimeError("implementation carrier tree observation is incomplete")
    entries: dict[str, Mapping[str, object]] = {}
    for raw_entry in raw_entries:
        entry = _as_mapping(raw_entry)
        path = None if entry is None else entry.get("path")
        mode = None if entry is None else entry.get("mode")
        entry_type = None if entry is None else entry.get("type")
        sha = None if entry is None else entry.get("sha")
        if (
            not isinstance(path, str)
            or not isinstance(mode, str)
            or not isinstance(entry_type, str)
            or not isinstance(sha, str)
            or path in entries
        ):
            raise RuntimeError("implementation carrier tree entry is malformed")
        entries[cast(str, path)] = cast(Mapping[str, object], entry)
    return cast(str, tree_sha), entries


def _tree_entry_identity(
    entry: Mapping[str, object] | None,
) -> tuple[object, object, object] | None:
    if entry is None:
        return None
    return entry.get("mode"), entry.get("type"), entry.get("sha")


def _fresh_implementation_write_authorization(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    default_branch: str,
    current_revision: str,
    expected_head: str,
) -> None:
    if _ref_head_sha(repository, token, default_branch) != current_revision:
        raise RuntimeError("implementation materialization default branch changed")
    if _current_authorized_request(repository, token) != source:
        raise RuntimeError("implementation materialization source dispatch changed")
    decision = _qualified_implementation_decision(
        request,
        source,
        repository=repository,
        token=token,
        current_revision=current_revision,
    )
    if decision.head_sha != expected_head:
        raise RuntimeError("implementation carrier head changed before mutation")


def _verify_implementation_manifest_freshness(
    request: MaterializationRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    carrier_head: str,
) -> None:
    if request.base_sha not in {current_revision, carrier_head}:
        comparison = _as_mapping(
            cast(
                object,
                _github_json(
                    repository,
                    token,
                    f"compare/{request.base_sha}...{carrier_head}",
                ),
            )
        )
        if (
            comparison is None
            or comparison.get("status") != "ahead"
            or comparison.get("behind_by") != 0
        ):
            raise RuntimeError("implementation manifest base is not an ancestor of carrier")
    for file in request.files:
        if _content_sha_at(repository, token, path=file.path, revision=carrier_head) != (
            file.expected_sha
        ):
            raise RuntimeError("implementation manifest expected content is stale")
        if file.path == f"openspec/changes/{request.change}/tasks.md" and (
            file.blob_sha != file.expected_sha
        ):
            current = _content_text_at(repository, token, path=file.path, revision=carrier_head)
            candidate = _blob_text(repository, token, file.blob_sha)
            if not _task_marker_update_is_monotonic(current, candidate):
                raise RuntimeError("implementation task update must be monotonic checkbox-only")


def _manifest_is_current(
    request: MaterializationRequest,
    *,
    repository: str,
    token: str,
    revision: str,
) -> bool:
    return all(
        _content_sha_at(repository, token, path=file.path, revision=revision) == file.blob_sha
        for file in request.files
    )


def _reconciliation_overlay(
    request: MaterializationRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    carrier_head: str,
) -> tuple[str, list[dict[str, object]]]:
    comparison = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                f"compare/{current_revision}...{carrier_head}",
            ),
        )
    )
    merge_base = None if comparison is None else _as_mapping(comparison.get("merge_base_commit"))
    merge_base_sha = None if merge_base is None else merge_base.get("sha")
    if not _valid_sha(merge_base_sha):
        raise RuntimeError("implementation reconciliation merge-base is incomplete")

    default_changed = _comparison_file_paths(
        repository,
        token,
        base_sha=cast(str, merge_base_sha),
        revision=current_revision,
    )
    carrier_changed = _comparison_file_paths(
        repository,
        token,
        base_sha=cast(str, merge_base_sha),
        revision=carrier_head,
    )
    carrier_tree_sha, carrier_entries = _revision_tree_snapshot(repository, token, carrier_head)
    _default_tree_sha, default_entries = _revision_tree_snapshot(
        repository,
        token,
        current_revision,
    )
    manifest_paths = {file.path for file in request.files}
    for path in (default_changed & carrier_changed) - manifest_paths:
        if _tree_entry_identity(default_entries.get(path)) != _tree_entry_identity(
            carrier_entries.get(path)
        ):
            raise RuntimeError("implementation reconciliation has an unresolved overlapping change")

    tree_elements: list[dict[str, object]] = []
    for path in sorted(default_changed - manifest_paths):
        default_entry = default_entries.get(path)
        carrier_entry = carrier_entries.get(path)
        if _tree_entry_identity(default_entry) == _tree_entry_identity(carrier_entry):
            continue
        if default_entry is None:
            if carrier_entry is None:
                continue
            tree_elements.append(
                {
                    "path": path,
                    "mode": carrier_entry["mode"],
                    "type": carrier_entry["type"],
                    "sha": None,
                }
            )
            continue
        if default_entry.get("type") != "blob":
            raise RuntimeError("implementation reconciliation default change is not a blob")
        tree_elements.append(
            {
                "path": path,
                "mode": default_entry["mode"],
                "type": "blob",
                "sha": default_entry["sha"],
            }
        )

    for file in request.files:
        carrier_entry = carrier_entries.get(file.path)
        default_entry = default_entries.get(file.path)
        mode = "100644"
        if carrier_entry is not None and carrier_entry.get("type") == "blob":
            mode = cast(str, carrier_entry["mode"])
        elif default_entry is not None and default_entry.get("type") == "blob":
            mode = cast(str, default_entry["mode"])
        tree_elements.append(
            {
                "path": file.path,
                "mode": mode,
                "type": "blob",
                "sha": file.blob_sha,
            }
        )
    return carrier_tree_sha, tree_elements


def _implementation_carrier_plan(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    default_branch: str,
    current_revision: str,
    current_head: str,
    revision: str,
    tree_sha: str,
    parents: list[str],
    message: str,
) -> CarrierPlan:
    if request.pr_number is None:
        raise RuntimeError("implementation carrier plan requires an exact PR")
    pr = _as_mapping(cast(object, _github_json(repository, token, f"pulls/{request.pr_number}")))
    if pr is None:
        raise RuntimeError("implementation carrier PR observation is unavailable")
    carrier_ref = f"refs/heads/{request.branch}"
    return make_carrier_plan(
        repository=repository,
        issue_number=source.issue_number,
        change=request.expected_change,
        action=source.action,
        authorization_revision=current_revision,
        operation="pull-request-head-update",
        target={
            "repository": repository,
            "pull_request_number": request.pr_number,
            "ref": carrier_ref,
        },
        expected={
            "ref": carrier_ref,
            "ref_sha": current_head,
            "pull_request": carrier_pr_identity(pr),
            "commit_parents": parents,
            "commit_tree_sha": tree_sha,
            "commit_message": message,
        },
        requested={
            "ref": carrier_ref,
            "sha": revision,
            "force": False,
            "pull_request_number": request.pr_number,
            "expected_head_sha": current_head,
            "commit_parents": parents,
            "commit_tree_sha": tree_sha,
            "commit_message": message,
        },
        expected_postcondition={
            "ref": carrier_ref,
            "ref_sha": revision,
            "pull_request_number": request.pr_number,
            "pull_request_head_sha": revision,
            "state": "open",
            "merged": False,
            "commit_sha": revision,
            "commit_parents": parents,
            "commit_tree_sha": tree_sha,
            "commit_message": message,
            "base_ref": default_branch,
        },
    )


def _materialize_implementation_target(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    default_branch: str,
    current_revision: str,
) -> ValidationResourceTarget:
    if source.action != _IMPLEMENTATION_ACTION or source.role != "executor":
        raise RuntimeError("implementation carrier materialization source is invalid")
    if not _implementation_manifest_capability_allowed(request, source):
        raise RuntimeError("work-product source has no required OpenSpec review gate")
    decision = _qualified_implementation_decision(
        request,
        source,
        repository=repository,
        token=token,
        current_revision=current_revision,
    )
    current_head = cast(str, decision.head_sha)
    _verify_implementation_manifest_freshness(
        request,
        repository=repository,
        token=token,
        current_revision=current_revision,
        carrier_head=current_head,
    )
    if decision.disposition == "RECONCILIATION_REQUIRED" and current_head != current_revision:
        base_tree_sha, tree_elements = _reconciliation_overlay(
            request,
            repository=repository,
            token=token,
            current_revision=current_revision,
            carrier_head=current_head,
        )
        parents = [current_head, current_revision]
        message = request.message
    else:
        base_tree_sha, _carrier_entries = _revision_tree_snapshot(
            repository,
            token,
            current_head,
        )
        tree_elements = [
            {
                "path": file.path,
                "mode": "100644",
                "type": "blob",
                "sha": file.blob_sha,
            }
            for file in request.files
        ]
        parents = [current_head]
        message = request.message

    tree_sha = base_tree_sha
    if tree_elements:
        _fresh_implementation_write_authorization(
            request,
            source,
            repository=repository,
            token=token,
            default_branch=default_branch,
            current_revision=current_revision,
            expected_head=current_head,
        )
        tree = _as_mapping(
            cast(
                object,
                _github_json(
                    repository,
                    token,
                    "git/trees",
                    method="POST",
                    payload={"base_tree": base_tree_sha, "tree": tree_elements},
                ),
            )
        )
        observed_tree_sha = None if tree is None else tree.get("sha")
        if not _valid_sha(observed_tree_sha):
            raise RuntimeError("implementation materialization tree creation returned no SHA")
        tree_sha = cast(str, observed_tree_sha)

    _fresh_implementation_write_authorization(
        request,
        source,
        repository=repository,
        token=token,
        default_branch=default_branch,
        current_revision=current_revision,
        expected_head=current_head,
    )
    created = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                "git/commits",
                method="POST",
                payload={"message": message, "tree": tree_sha, "parents": parents},
            ),
        )
    )
    revision = None if created is None else created.get("sha")
    if not _valid_sha(revision):
        raise RuntimeError("implementation materialization commit creation returned no SHA")
    revision = cast(str, revision)

    observed = _as_mapping(cast(object, _github_json(repository, token, f"git/commits/{revision}")))
    observed_tree = None if observed is None else _as_mapping(observed.get("tree"))
    raw_parents = None if observed is None else observed.get("parents")
    observed_parents: list[str] = []
    if isinstance(raw_parents, list):
        for raw_parent in raw_parents:
            parent = _as_mapping(raw_parent)
            parent_sha = None if parent is None else parent.get("sha")
            if not _valid_sha(parent_sha):
                raise RuntimeError("implementation materialization commit parent is incomplete")
            observed_parents.append(cast(str, parent_sha))
    if (
        observed is None
        or observed.get("sha") != revision
        or observed.get("message") != message
        or observed_tree is None
        or observed_tree.get("sha") != tree_sha
        or observed_parents != parents
        or not _manifest_is_current(
            request,
            repository=repository,
            token=token,
            revision=revision,
        )
    ):
        raise RuntimeError("implementation materialization commit postcondition was not observed")
    if _ref_head_sha(repository, token, request.branch) != current_head:
        raise RuntimeError("implementation carrier moved before carrier handoff")
    if _ref_head_sha(repository, token, default_branch) != current_revision:
        raise RuntimeError("implementation default branch moved before carrier handoff")

    raise CarrierRequired(
        _implementation_carrier_plan(
            request,
            source,
            repository=repository,
            token=token,
            default_branch=default_branch,
            current_revision=current_revision,
            current_head=current_head,
            revision=revision,
            tree_sha=tree_sha,
            parents=parents,
            message=message,
        )
    )


def _existing_target(
    request: MaterializationRequest,
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    default_branch: str,
    authorization_revision: str,
    allow_pending_continuation: bool = False,
    before_write: Callable[[], None] | None = None,
) -> ValidationResourceTarget:
    if request.pr_number is None:
        raise RuntimeError("existing Change materialization requires an exact PR")
    if source.role == "executor" and source.action == _IMPLEMENTATION_ACTION:
        return _materialize_implementation_target(
            request,
            source,
            repository=repository,
            token=token,
            default_branch=default_branch,
            current_revision=authorization_revision,
        )
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
        target = _construct_work_product(
            plan,
            repository=repository,
            token=token,
            default_branch=default_branch,
            authorization_revision=authorization_revision,
            allow_pending_continuation=allow_pending_continuation,
            before_write=before_write,
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
            allow_pending_continuation=allow_pending_continuation,
        )
    return ValidationResourceTarget(
        repository=target.repository,
        revision=target.revision,
        correlation=f"effect-request-{request.issue_number}",
        pr_number=target.pr_number,
        change=target.change,
        validation_required=materialization_requires_validation(request, source),
        branch=target.branch,
    )


def _construct_materialization(
    request: MaterializationRequest | Mapping[str, object],
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    promote_change: bool = False,
    validated_revision: str | None = None,
    allow_pending_continuation: bool = False,
    before_write: Callable[[], None] | None = None,
) -> ValidationResourceTarget:
    """Freshly authorize and apply one generic carrier/materialization effect."""

    if isinstance(request, Mapping):
        request = parse_materialization_payload(request, source)
    if not materialization_message_is_safe(
        request.message,
        repository=repository,
        issue_number=source.issue_number,
    ):
        raise RuntimeError("application materialization commit message is not non-closing")
    if (
        not allow_pending_continuation and _current_authorized_request(repository, token) != source
    ) or (
        allow_pending_continuation
        and not _pending_source_is_current(
            repository,
            token,
            source,
            request.expected_change,
        )
    ):
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
            if not allow_pending_continuation:
                raise RuntimeError("application materialization first-carrier base is stale")
            revision, pr_number = _pending_new_carrier(
                request,
                source,
                repository=repository,
                token=token,
                default_branch=default_branch,
                current_revision=current_revision,
                before_write=before_write,
            )
        else:
            revision, pr_number = _ensure_new_carrier(
                request,
                source,
                repository=repository,
                token=token,
                default_branch=default_branch,
                authorization_revision=current_revision,
                before_write=before_write,
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

    return _existing_target(
        request,
        source,
        repository=repository,
        token=token,
        default_branch=default_branch,
        authorization_revision=current_revision,
        allow_pending_continuation=allow_pending_continuation,
        before_write=before_write,
    )


def apply_materialization(
    payload: Mapping[str, object],
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    accepted_authorization_revision: str | None = None,
    promote_change: bool = False,
    validated_revision: str | None = None,
    allow_pending_continuation: bool = False,
    accepted_intent: bool = False,
) -> ValidationResourceTarget:
    """Only proven missing work reaches the constructor; fresh proof owns its result."""
    proof = prove_materialization(
        payload,
        source,
        repository=repository,
        token=token,
        current_revision=current_revision,
        default_branch=default_branch,
        accepted_authorization_revision=accepted_authorization_revision,
        allow_pending_continuation=allow_pending_continuation,
        accepted_intent=accepted_intent,
    )
    if proof.disposition == "CONTRADICTORY":
        raise RuntimeError(proof.reason)

    def before_write() -> None:
        fresh = prove_materialization(
            payload,
            source,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
            accepted_authorization_revision=accepted_authorization_revision,
            allow_pending_continuation=allow_pending_continuation,
            accepted_intent=accepted_intent,
        )
        if fresh.disposition != "INCOMPLETE":
            raise RuntimeError(fresh.reason or "materialization no longer requires mutation")

    if proof.disposition == "INCOMPLETE":
        request = proof.application_request or parse_materialization_payload(payload, source)
        _construct_materialization(
            request,
            source,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
            promote_change=False,
            validated_revision=validated_revision,
            allow_pending_continuation=allow_pending_continuation,
            before_write=before_write,
        )
        # A successful API/constructor result is never completion authority.
        proof = prove_materialization(
            payload,
            source,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
            accepted_authorization_revision=accepted_authorization_revision,
            allow_pending_continuation=allow_pending_continuation,
            accepted_intent=accepted_intent,
        )
    if proof.disposition != "COMPLETE" or proof.target is None:
        raise RuntimeError(
            proof.reason or "materialization constructor postcondition is incomplete"
        )
    request = proof.application_request or parse_materialization_payload(payload, source)
    if promote_change and request.expected_change == "unset":
        # Promotion is a separate validated Issue consequence, not replay of
        # the completed tree/ref/PR. The bridge owns atomic formal activation.
        if validated_revision != proof.target.revision:
            raise RuntimeError("application materialization validation revision is stale")
        _persist_change(request, repository=repository, token=token)
    return proof.target


def _proof_comparison(
    repository: str,
    token: str,
    base_revision: str,
    revision: str,
) -> tuple[Mapping[str, object], tuple[str, ...], frozenset[str]]:
    """Read a complete graph/path observation; missing evidence never means missing work."""
    comparison = _as_mapping(
        _github_json(repository, token, f"compare/{base_revision}...{revision}")
    )
    base = None if comparison is None else _as_mapping(comparison.get("base_commit"))
    merge_base = None if comparison is None else _as_mapping(comparison.get("merge_base_commit"))
    raw_commits = None if comparison is None else comparison.get("commits")
    raw_files = None if comparison is None else comparison.get("files")
    ahead = None if comparison is None else comparison.get("ahead_by")
    behind = None if comparison is None else comparison.get("behind_by")
    if (
        comparison is None
        or base is None
        or base.get("sha") != base_revision
        or merge_base is None
        or not _valid_sha(merge_base.get("sha"))
        or comparison.get("too_large") is True
        or not isinstance(ahead, int)
        or isinstance(ahead, bool)
        or ahead < 0
        or not isinstance(behind, int)
        or isinstance(behind, bool)
        or behind < 0
        or not isinstance(raw_commits, list)
        or len(raw_commits) != ahead
        or comparison.get("total_commits") != ahead
        or not isinstance(raw_files, list)
        or len(raw_files) >= 300
    ):
        raise RuntimeError("materialization graph observation is incomplete")
    expected_status = (
        "diverged"
        if ahead and behind
        else "ahead"
        if ahead
        else "behind"
        if behind
        else "identical"
    )
    if comparison.get("status") != expected_status:
        raise RuntimeError("materialization graph observations contradict")
    commits: list[str] = []
    for raw in raw_commits:
        commit = _as_mapping(raw)
        sha = None if commit is None else commit.get("sha")
        if not _valid_sha(sha) or sha in commits:
            raise RuntimeError("materialization graph commit enumeration is incomplete")
        commits.append(cast(str, sha))
    if commits and commits[-1] != revision:
        raise RuntimeError("materialization graph terminal revision contradicts target")
    if not ahead and not behind and base_revision != revision:
        raise RuntimeError("materialization identical graph revisions contradict")
    paths = _comparison_paths_from_file_entries(
        raw_files, malformed_error="materialization graph paths are incomplete"
    )
    return comparison, tuple(commits), frozenset(paths)


def _proof_ancestry(repository: str, token: str, ancestor: str, revision: str) -> frozenset[str]:
    comparison, _commits, paths = _proof_comparison(repository, token, ancestor, revision)
    if comparison.get("behind_by") != 0:
        raise RuntimeError("materialization required ancestry is broken")
    return paths


def _proof_commit(
    repository: str, token: str, revision: str
) -> tuple[Mapping[str, object], tuple[str, ...]]:
    commit = _as_mapping(_github_json(repository, token, f"git/commits/{revision}"))
    tree = None if commit is None else _as_mapping(commit.get("tree"))
    raw_parents = None if commit is None else commit.get("parents")
    if (
        commit is None
        or commit.get("sha") != revision
        or tree is None
        or not _valid_sha(tree.get("sha"))
        or not isinstance(raw_parents, list)
        or not raw_parents
        or not isinstance(commit.get("message"), str)
    ):
        raise RuntimeError("materialization commit observation is incomplete")
    parents: list[str] = []
    for raw in raw_parents:
        parent = _as_mapping(raw)
        sha = None if parent is None else parent.get("sha")
        if not _valid_sha(sha) or sha in parents:
            raise RuntimeError("materialization commit parent observation is incomplete")
        parents.append(cast(str, sha))
    return commit, tuple(parents)


def _proof_overlay(
    request: MaterializationRequest,
    *,
    repository: str,
    token: str,
    parents: tuple[str, ...],
    revision: str,
    current_revision: str,
    preserve_carrier_content: bool = False,
) -> None:
    """Verify application construction without replaying a historical accepted blob."""
    if len(parents) != 2:
        raise RuntimeError("materialization reconciliation parent identity contradicts")
    _proof_ancestry(repository, token, parents[1], current_revision)
    comparison, _commits, _paths = _proof_comparison(repository, token, parents[1], parents[0])
    merge_base = cast(Mapping[str, object], comparison["merge_base_commit"])
    _proof_ancestry(repository, token, cast(str, merge_base["sha"]), parents[0])
    _proof_ancestry(repository, token, cast(str, merge_base["sha"]), parents[1])
    overlay_request = request
    if preserve_carrier_content:
        current_files: list[WorkProductFile] = []
        for file in request.files:
            sha = _content_sha_at(repository, token, path=file.path, revision=parents[0])
            if sha is None:
                raise RuntimeError("materialization descendant removes an accepted Change path")
            current_files.append(WorkProductFile(file.path, sha, file.expected_sha))
        overlay_request = MaterializationRequest(
            request.issue_number,
            request.expected_change,
            request.change,
            request.branch,
            request.base_sha,
            request.message,
            tuple(current_files),
            request.pr_number,
        )
    _tree, elements = _reconciliation_overlay(
        overlay_request,
        repository=repository,
        token=token,
        current_revision=parents[1],
        carrier_head=parents[0],
    )
    _old_tree, expected = _revision_tree_snapshot(repository, token, parents[0])
    expected = {path: entry for path, entry in expected.items() if entry.get("type") != "tree"}
    for element in elements:
        path = cast(str, element["path"])
        if element["sha"] is None:
            expected.pop(path, None)
        else:
            expected[path] = element
    _actual_tree, actual = _revision_tree_snapshot(repository, token, revision)
    actual = {path: entry for path, entry in actual.items() if entry.get("type") != "tree"}
    if expected.keys() != actual.keys() or any(
        _tree_entry_identity(expected[path]) != _tree_entry_identity(actual[path])
        for path in expected
    ):
        raise RuntimeError("materialization reconciliation overwrites unrelated content")


def _proof_witness(
    request: MaterializationRequest,
    *,
    repository: str,
    token: str,
    revision: str,
    current_revision: str,
) -> str | None:
    """Find accepted content in the complete carrier graph, never in a local API result."""
    comparison, commits, _paths = _proof_comparison(repository, token, request.base_sha, revision)
    if comparison.get("behind_by") != 0:
        return None
    desired_paths = frozenset(file.path for file in request.files)
    witness: str | None = None
    if (
        request.files
        and all(file.blob_sha == file.expected_sha for file in request.files)
        and _manifest_is_current(
            request, repository=repository, token=token, revision=request.base_sha
        )
    ):
        witness = request.base_sha
    for sha in commits:
        commit, parents = _proof_commit(repository, token, sha)
        if witness is None:
            # Snapshot equality alone does not prove the accepted mutation. Its exact
            # message, write parent, changed paths, and desired objects must agree.
            if commit.get("message") != request.message:
                continue
            if parents[0] != request.base_sha:
                parent_relation, _commits, parent_paths = _proof_comparison(
                    repository, token, request.base_sha, parents[0]
                )
                if parent_relation.get("behind_by") == 0:
                    if parent_paths.intersection(desired_paths):
                        raise RuntimeError(
                            "materialization write parent overlaps accepted preimage"
                        )
                elif len(parents) != 2:
                    continue
                else:
                    _proof_ancestry(repository, token, request.base_sha, parents[1])
            for file in request.files:
                if (
                    _content_sha_at(repository, token, path=file.path, revision=parents[0])
                    != file.expected_sha
                ):
                    raise RuntimeError("materialization write parent has stale content")
            if not _manifest_is_current(request, repository=repository, token=token, revision=sha):
                raise RuntimeError("materialization accepted commit has wrong desired blobs")
            if len(parents) == 1:
                delta = _proof_ancestry(repository, token, parents[0], sha)
                if delta != desired_paths:
                    raise RuntimeError("materialization accepted mutation changes unrelated paths")
            else:
                _proof_overlay(
                    request,
                    repository=repository,
                    token=token,
                    parents=parents,
                    revision=sha,
                    current_revision=current_revision,
                )
            witness = sha
    if witness is not None:
        _proof_ancestry(repository, token, witness, revision)
    return witness


def _request_with_observed_preimage(
    request: MaterializationRequest,
    *,
    repository: str,
    token: str,
    revision: str,
) -> MaterializationRequest:
    """Project the exact observed write preimage without changing accepted intent."""

    files: list[WorkProductFile] = []
    for file in request.files:
        observed = _content_sha_at(repository, token, path=file.path, revision=revision)
        if observed is not None and not _valid_sha(observed):
            raise RuntimeError("materialization observed preimage identity is invalid")
        files.append(WorkProductFile(file.path, file.blob_sha, observed))
    return replace(request, files=tuple(files))


def _accepted_preimage_projection(
    request: MaterializationRequest,
    *,
    repository: str,
    token: str,
    current_carrier_revision: str,
    merged: bool,
    accepted_intent: bool,
) -> MaterializationRequest:
    """Recover an accepted exact-base write guard from authoritative Git objects.

    The accepted worker result remains immutable. For missing work, the PR
    head must still equal its declared base. For completed work, exactly one
    direct child must carry the accepted message, exact path delta, and desired
    blobs. Other branch evolution is never normalized.
    """

    if (
        not accepted_intent
        or merged
        or request.expected_change == "unset"
        or request.pr_number is None
    ):
        return request

    if current_carrier_revision == request.base_sha:
        projected = _request_with_observed_preimage(
            request,
            repository=repository,
            token=token,
            revision=request.base_sha,
        )
        if any(
            actual.expected_sha != original.expected_sha
            for actual, original in zip(projected.files, request.files, strict=True)
        ):
            return projected
        return request

    comparison, commits, _paths = _proof_comparison(
        repository, token, request.base_sha, current_carrier_revision
    )
    if comparison.get("behind_by") != 0:
        return request
    desired_paths = frozenset(file.path for file in request.files)
    candidates: list[MaterializationRequest] = []
    for revision in commits:
        commit, parents = _proof_commit(repository, token, revision)
        if len(parents) != 1 or parents[0] != request.base_sha:
            continue
        if commit.get("message") != request.message:
            continue
        if _proof_ancestry(repository, token, request.base_sha, revision) != desired_paths:
            continue
        projected = _request_with_observed_preimage(
            request,
            repository=repository,
            token=token,
            revision=request.base_sha,
        )
        if _manifest_is_current(
            projected,
            repository=repository,
            token=token,
            revision=revision,
        ):
            candidates.append(projected)
    if len(candidates) > 1:
        raise RuntimeError("materialization accepted write preimage recovery is ambiguous")
    return candidates[0] if candidates else request


def prove_materialization(
    payload: Mapping[str, object],
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    accepted_authorization_revision: str | None = None,
    allow_pending_continuation: bool = False,
    accepted_successor_routing: tuple[str, str] | None = None,
    accepted_intent: bool = False,
) -> MaterializationProof:
    """The sole read-only owner of materialized durable consequence completion.

    Carrier qualification supplies identity, topology supplies graph/witness
    facts. Neither can independently manufacture a positive completion result.
    Only fully observed missing work returns INCOMPLETE; read failures and
    incomplete/contradictory observations return CONTRADICTORY.
    """
    try:
        request = parse_materialization_payload(payload, source)
        if (
            source.role == "executor"
            and source.action == _IMPLEMENTATION_ACTION
            and not (_implementation_manifest_capability_allowed(request, source))
        ):
            raise RuntimeError("work-product source has no required OpenSpec review gate")
        accepted_revision = accepted_authorization_revision or current_revision
        if not all(
            _valid_sha(value)
            for value in (
                accepted_revision,
                request.base_sha,
                current_revision,
            )
        ):
            raise RuntimeError("materialization revision identities are incomplete")
        if not materialization_message_is_safe(
            request.message, repository=repository, issue_number=source.issue_number
        ):
            raise RuntimeError("materialization accepted message is closing")
        if _current_default_branch(repository, token) != default_branch:
            raise RuntimeError("materialization default branch identity changed")
        if _ref_head_sha(repository, token, default_branch) != current_revision:
            raise RuntimeError("materialization current default revision changed")
        issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
        if (
            issue is None
            or issue.get("number") != source.issue_number
            or issue.get("state") != "open"
        ):
            raise RuntimeError("materialization source Issue identity changed")
        actual_change = _change_from_issue(issue)
        legal_changes = {request.expected_change}
        if request.expected_change == "unset":
            legal_changes.add(request.change)
        if actual_change not in legal_changes:
            raise RuntimeError("materialization immutable Change identity changed")
        if allow_pending_continuation:
            source_current = _pending_source_is_current(
                repository,
                token,
                source,
                cast(str, actual_change),
                accepted_successor_routing=accepted_successor_routing,
            )
        else:
            source_current = _current_authorized_request(repository, token) == source
        if not source_current:
            raise RuntimeError("materialization source dispatch is stale")
        if source.role == "executor" and source.action == _IMPLEMENTATION_ACTION:
            _qualified_implementation_decision(
                request,
                source,
                repository=repository,
                token=token,
                current_revision=current_revision,
            )
        default_advance = _proof_ancestry(repository, token, accepted_revision, current_revision)
        if request.expected_change == "unset":
            _tree, preimage_entries = _revision_tree_snapshot(repository, token, request.base_sha)
            prefix = f"openspec/changes/{request.change}/"
            if any(path.startswith(prefix) for path in preimage_entries):
                raise RuntimeError("materialization first Change already exists at preimage")
        if request.expected_change == "unset" and request.base_sha != accepted_revision:
            raise RuntimeError("materialization first-carrier authorization identity contradicts")
        branch = request.branch
        number = request.pr_number
        missing_replacement = False
        claimed = _claimed_open_carriers(
            repository,
            token,
            issue_number=source.issue_number,
            change=request.change,
            default_branch=default_branch,
            read=_github_json,
        )
        if len(claimed) > 1:
            raise RuntimeError("materialization competing Change carriers are ambiguous")
        head = _branch_head(repository, token, branch)
        prs = _matching_prs(repository, token, branch)
        if len(prs) > 1:
            raise RuntimeError("materialization carrier identity is ambiguous")
        if number is None:
            if not prs:
                if claimed:
                    raise RuntimeError(
                        "materialization missing intended carrier has competing identity"
                    )
                if default_advance.intersection(file.path for file in request.files):
                    raise RuntimeError("materialization missing carrier overlaps default advance")
                if head is not None:
                    witness = _proof_witness(
                        request,
                        repository=repository,
                        token=token,
                        revision=head,
                        current_revision=current_revision,
                    )
                    if witness is None or witness != head:
                        raise RuntimeError(
                            "materialization orphan branch contradicts accepted intent"
                        )
                return MaterializationProof("INCOMPLETE", application_request=request)
            number = _positive_int(prs[0].get("number"))
            if number is None:
                raise RuntimeError("materialization carrier number is incomplete")
            pr = prs[0]
        else:
            if len(prs) != 1 or prs[0].get("number") != number:
                raise RuntimeError("materialization intended PR identity contradicts discovery")
            pr = _open_pr_payload(
                repository=repository,
                token=token,
                pr_number=number,
                source=source,
                expected_change=request.expected_change,
                default_branch=default_branch,
                expected_branch=branch,
                allow_historical_merged_carrier=True,
                allow_reconciliation=True,
            )
        pr_head = _as_mapping(pr.get("head"))
        pr_base = _as_mapping(pr.get("base"))
        revision = None if pr_head is None else pr_head.get("sha")
        base_revision = None if pr_base is None else pr_base.get("sha")
        merged = _is_historical_merged_carrier(pr)
        if (not merged and pr.get("state") != "open") or pr.get("draft") is True:
            raise RuntimeError("materialization carrier lifecycle is not qualified")
        identity_pr = dict(pr)
        identity_pr.update(state="open", merged=False)
        if (
            not _valid_sha(revision)
            or not _valid_sha(base_revision)
            or not _pr_matches(
                identity_pr,
                repository=repository,
                branch=branch,
                default_branch=default_branch,
                revision=cast(str, revision),
                issue_number=source.issue_number,
                change=request.change,
                require_openspec_title=request.expected_change == "unset",
            )
        ):
            raise RuntimeError("materialization carrier linkage is invalid")
        _proof_ancestry(repository, token, cast(str, base_revision), current_revision)
        if not merged and head != revision:
            raise RuntimeError("materialization PR/ref head identity contradicts")
        if merged:
            merge_revision = pr.get("merge_commit_sha")
            if not _valid_sha(merge_revision):
                raise RuntimeError("materialization merge identity is incomplete")
            _proof_ancestry(repository, token, cast(str, merge_revision), current_revision)
            _proof_ancestry(repository, token, cast(str, revision), cast(str, merge_revision))
            replacement = _replacement_branch(request.change, number)
            replacements = _matching_prs(repository, token, replacement)
            if len(replacements) > 1:
                raise RuntimeError("materialization replacement carrier is ambiguous")
            if replacements:
                replacement_number = _positive_int(replacements[0].get("number"))
                if replacement_number is None:
                    raise RuntimeError("materialization replacement identity is incomplete")
                decision = _change_carrier_decision(
                    source,
                    repository=repository,
                    token=token,
                    default_branch=default_branch,
                    expected_change=request.change,
                    pr_number=replacement_number,
                )
                if decision.disposition not in {
                    "QUALIFIED",
                    "RECONCILIATION_REQUIRED",
                    "HISTORICAL_MERGED",
                } or (
                    decision.pr_number != replacement_number
                    or decision.branch != replacement
                    or not _valid_sha(decision.head_sha)
                ):
                    raise RuntimeError("materialization replacement carrier is not qualified")
                if decision.disposition == "HISTORICAL_MERGED":
                    replacement_pr = _as_mapping(
                        _github_json(repository, token, f"pulls/{replacement_number}")
                    )
                    replacement_merge = (
                        None if replacement_pr is None else replacement_pr.get("merge_commit_sha")
                    )
                    if not _valid_sha(replacement_merge):
                        raise RuntimeError(
                            "materialization replacement merge identity is incomplete"
                        )
                    _proof_ancestry(
                        repository,
                        token,
                        cast(str, decision.head_sha),
                        cast(str, replacement_merge),
                    )
                    _proof_ancestry(
                        repository, token, cast(str, replacement_merge), current_revision
                    )
                    branch, number, revision = replacement, replacement_number, current_revision
                    merged = True
                else:
                    if _branch_head(repository, token, replacement) != decision.head_sha:
                        raise RuntimeError(
                            "materialization replacement PR/ref identity contradicts"
                        )
                    branch, number, revision = replacement, replacement_number, decision.head_sha
                    merged = False
            else:
                # A merged descendant is a current consumer target. The accepted
                # witness may be in the original carrier or a qualified successor.
                revision = current_revision
                missing_replacement = True
                orphan = _branch_head(repository, token, replacement)
                if orphan is not None:
                    orphan_witness = _proof_witness(
                        request,
                        repository=repository,
                        token=token,
                        revision=orphan,
                        current_revision=current_revision,
                    )
                    if orphan_witness is None or orphan_witness != orphan:
                        raise RuntimeError(
                            "materialization orphan replacement contradicts accepted intent"
                        )
                    _proof_ancestry(repository, token, current_revision, orphan)
        if (
            not merged
            and any(
                _content_sha_at(repository, token, path=file.path, revision=cast(str, revision))
                is None
                for file in request.files
            )
            and revision != request.base_sha
        ):
            raise RuntimeError("materialization current carrier is missing an accepted path")
        if not merged and (len(claimed) != 1 or claimed[0].get("number") != number):
            raise RuntimeError("materialization current carrier cardinality contradicts")
        if merged and claimed:
            raise RuntimeError("materialization merged target has a competing active carrier")
        revision = cast(str, revision)
        request = _accepted_preimage_projection(
            request,
            repository=repository,
            token=token,
            current_carrier_revision=revision,
            merged=merged,
            accepted_intent=accepted_intent,
        )
        witness_revision: str | None
        if not request.files:
            witness_revision = revision
        else:
            witness_revision = _proof_witness(
                request,
                repository=repository,
                token=token,
                revision=revision,
                current_revision=current_revision,
            )
        if witness_revision is None:
            if request.expected_change == "unset":
                raise RuntimeError("materialization existing first carrier has no accepted witness")
            if not merged:
                if revision != request.base_sha:
                    if request.base_sha != accepted_revision:
                        raise RuntimeError(
                            "materialization missing work has unqualified write parent"
                        )
                    relation, _commits, _paths = _proof_comparison(
                        repository, token, current_revision, revision
                    )
                    fork = cast(Mapping[str, object], relation["merge_base_commit"])
                    main_paths = _proof_ancestry(
                        repository, token, cast(str, fork["sha"]), current_revision
                    )
                    branch_paths = _proof_ancestry(
                        repository, token, cast(str, fork["sha"]), revision
                    )
                    if main_paths.intersection(file.path for file in request.files):
                        raise RuntimeError("materialization missing work overlaps default advance")
                    for path in main_paths & branch_paths:
                        if _content_sha_at(
                            repository, token, path=path, revision=current_revision
                        ) != (_content_sha_at(repository, token, path=path, revision=revision)):
                            raise RuntimeError(
                                "materialization missing work has conflicting histories"
                            )
                elif default_advance.intersection(file.path for file in request.files):
                    raise RuntimeError("materialization missing work overlaps default advance")
                for file in request.files:
                    if _content_sha_at(repository, token, path=file.path, revision=revision) != (
                        file.expected_sha
                    ):
                        raise RuntimeError("materialization missing work preimage is stale")
                return MaterializationProof("INCOMPLETE", application_request=request)
            if missing_replacement:
                advance = _proof_ancestry(repository, token, request.base_sha, current_revision)
                if advance.intersection(file.path for file in request.files):
                    raise RuntimeError(
                        "materialization missing replacement overlaps default advance"
                    )
                for file in request.files:
                    if _content_sha_at(
                        repository, token, path=file.path, revision=current_revision
                    ) != (file.expected_sha):
                        raise RuntimeError("materialization missing replacement preimage is stale")
                return MaterializationProof("INCOMPLETE", application_request=request)
            raise RuntimeError("materialization accepted consequence has no qualified witness")
        if merged:
            history = _historical_carriers(
                repository,
                token,
                issue_number=source.issue_number,
                change=request.change,
                default_branch=default_branch,
                default_revision=current_revision,
                read=_github_json,
            )
            if history is None:
                raise RuntimeError("materialization merged carrier history is ambiguous")
            witness_carriers: list[int] = []
            for historical_number, historical_pr in history:
                historical_head = _as_mapping(historical_pr.get("head"))
                historical_revision = (
                    None if historical_head is None else historical_head.get("sha")
                )
                if not _valid_sha(historical_revision):
                    raise RuntimeError("materialization historical carrier head is incomplete")
                relation, _commits, _paths = _proof_comparison(
                    repository, token, witness_revision, cast(str, historical_revision)
                )
                if relation.get("behind_by") == 0:
                    historical_merge = historical_pr.get("merge_commit_sha")
                    if not _valid_sha(historical_merge):
                        raise RuntimeError(
                            "materialization historical merge identity is incomplete"
                        )
                    _proof_ancestry(
                        repository,
                        token,
                        cast(str, historical_revision),
                        cast(str, historical_merge),
                    )
                    _proof_ancestry(
                        repository, token, cast(str, historical_merge), current_revision
                    )
                    witness_carriers.append(historical_number)
            if not witness_carriers:
                raise RuntimeError("materialization witness has no qualified same-Change carrier")
        # The witness remains immutable. Legal descendants are proved per
        # commit, so importing disjoint main history is not mistaken for a
        # semantic edit by this source Action.
        _proof_ancestry(repository, token, witness_revision, revision)
        if default_advance.intersection(file.path for file in request.files):
            _proof_ancestry(repository, token, witness_revision, current_revision)
        # Compare current default against carrier history without confusing the
        # mutation preimage with a historical default-branch base.
        comparison, _commits, _paths = _proof_comparison(
            repository, token, current_revision, revision
        )
        merge_base = cast(Mapping[str, object], comparison["merge_base_commit"])
        default_paths = _proof_ancestry(
            repository, token, cast(str, merge_base["sha"]), current_revision
        )
        carrier_paths = _proof_ancestry(repository, token, cast(str, merge_base["sha"]), revision)
        for path in default_paths & carrier_paths:
            if _content_sha_at(repository, token, path=path, revision=current_revision) != (
                _content_sha_at(repository, token, path=path, revision=revision)
            ):
                raise RuntimeError("materialization carrier overlaps default-branch changes")
        # A reconciliation after the accepted mutation must preserve the exact
        # application overlay, even when its final desired blobs were later changed.
        _lineage, descendants, _paths = _proof_comparison(
            repository, token, witness_revision, revision
        )
        for descendant in descendants:
            commit, parents = _proof_commit(repository, token, descendant)
            if len(parents) == 2 and commit.get("message") == (
                f"Reconcile default-branch ancestry for {request.change}"
            ):
                _proof_overlay(
                    request,
                    repository=repository,
                    token=token,
                    parents=parents,
                    revision=descendant,
                    current_revision=current_revision,
                    preserve_carrier_content=True,
                )
                continue
            relation, _commits, _paths = _proof_comparison(
                repository, token, witness_revision, descendant
            )
            if relation.get("behind_by") != 0 or merged:
                # A second-parent/default-history commit is admitted only by
                # its observed ancestry to the fresh default branch.
                _proof_ancestry(repository, token, descendant, current_revision)
                continue
            if len(parents) != 1:
                raise RuntimeError("materialization descendant merge is not application-built")
            delta = _proof_ancestry(repository, token, parents[0], descendant)
            if any(not work_product_path_allowed(source, request.change, path) for path in delta):
                raise RuntimeError("materialization descendant changes unrelated paths")
        target = _target(
            request,
            repository=repository,
            revision=revision,
            pr_number=number,
            branch=branch,
            validation_required=materialization_requires_validation(request, source),
        )
        mutation_preimage = request.base_sha
        if witness_revision != request.base_sha:
            _commit, witness_parents = _proof_commit(repository, token, witness_revision)
            mutation_preimage = witness_parents[0]
        revisions = MaterializationRevisions(
            accepted_revision, request.base_sha, mutation_preimage, current_revision
        )
        immutable_witness = MaterializationWitness(
            witness_revision, tuple((file.path, file.blob_sha) for file in request.files), revisions
        )
        return MaterializationProof(
            "COMPLETE",
            target=target,
            witness=immutable_witness,
            application_request=request,
        )
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as error:
        return MaterializationProof("CONTRADICTORY", reason=str(error))


def materialization_postcondition(
    payload: Mapping[str, object],
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    target: ValidationResourceTarget | None = None,
    accepted_authorization_revision: str | None = None,
    allow_pending_continuation: bool = False,
    accepted_intent: bool = False,
) -> bool:
    """The invocation target is a validation hint; fresh proof owns completion."""
    return (
        prove_materialization(
            payload,
            source,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
            accepted_authorization_revision=accepted_authorization_revision,
            allow_pending_continuation=allow_pending_continuation,
            accepted_intent=accepted_intent,
        ).disposition
        == "COMPLETE"
    )


def observe_materialization_target(
    payload: Mapping[str, object],
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    accepted_authorization_revision: str | None = None,
    allow_pending_continuation: bool = False,
    accepted_successor_routing: tuple[str, str] | None = None,
    accepted_intent: bool = False,
) -> ValidationResourceTarget:
    """Reconstruct the current qualified target using the canonical proof."""
    proof = prove_materialization(
        payload,
        source,
        repository=repository,
        token=token,
        current_revision=current_revision,
        default_branch=default_branch,
        accepted_authorization_revision=accepted_authorization_revision,
        allow_pending_continuation=allow_pending_continuation,
        accepted_successor_routing=accepted_successor_routing,
        accepted_intent=accepted_intent,
    )
    if proof.disposition != "COMPLETE" or proof.target is None:
        raise RuntimeError(proof.reason or "application materialization is incomplete")
    return proof.target


def find_materialization_payload(
    payload: Mapping[str, object],
    source: WorkerRequest,
) -> MaterializationRequest | None:
    """Return a structurally validated materialization request, if applicable."""

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
