"""Application-owned pre-activation OpenSpec Change formalization."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import quote, urlencode

from investment_strategy.issue_comment_bridge import MachineDispatchDecision
from investment_strategy.scheduled_agent_dispatch_result import fetch_dispatch_result
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_validation_resource import (
    ValidationResourceTarget,
    WorkProductManifest,
    _as_mapping,
    _change_from_issue,
    _content_sha_at,
    _current_authorized_request,
    _current_default_branch,
    _fresh_event_observation,
    _github_json,
    _open_pr_payload,
    _parse_manifest,
    _ref_head_sha,
    _review_openspec_required,
    _source_branch,
    _valid_sha,
    work_product_path_allowed,
)

FORMALIZE_CHANGE_REQUEST_MARKER = "FORMALIZE_CHANGE_REQUEST"
_DISPATCH_REQUEST_PREFIX = "Dispatch-Request-Comment-ID: "
_DISPATCH_RUN_PREFIX = "Dispatch-Run-ID: "
_PROPOSED_CHANGE_PREFIX = "Proposed-Change: "
_MANIFEST_PREFIX = "Manifest-B64: "
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")


@dataclass(frozen=True)
class FormalizeChangeRequest:
    dispatch_request_comment_id: int
    dispatch_run_id: int
    proposed_change: str
    manifest: WorkProductManifest


def _positive_decimal(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 and str(parsed) == value else None


def parse_formalize_change_request(body: str) -> FormalizeChangeRequest | None:
    """Parse one exact request for the first formal Change carrier."""

    lines = body.split("\n")
    if not lines or lines[0] != FORMALIZE_CHANGE_REQUEST_MARKER:
        return None
    if len(lines) != 5:
        raise ValueError("FORMALIZE_CHANGE_REQUEST must contain exactly five lines")
    prefixes = (
        _DISPATCH_REQUEST_PREFIX,
        _DISPATCH_RUN_PREFIX,
        _PROPOSED_CHANGE_PREFIX,
        _MANIFEST_PREFIX,
    )
    if any(not line.startswith(prefix) for line, prefix in zip(lines[1:], prefixes, strict=True)):
        raise ValueError("FORMALIZE_CHANGE_REQUEST field order is invalid")
    request_id = _positive_decimal(lines[1][len(prefixes[0]) :])
    run_id = _positive_decimal(lines[2][len(prefixes[1]) :])
    change = lines[3][len(prefixes[2]) :]
    if request_id is None or run_id is None or _source_branch(change) is None:
        raise ValueError("FORMALIZE_CHANGE_REQUEST identity is invalid")
    return FormalizeChangeRequest(
        dispatch_request_comment_id=request_id,
        dispatch_run_id=run_id,
        proposed_change=change,
        manifest=_parse_manifest(lines[4][len(prefixes[3]) :]),
    )


def source_from_dispatch(
    request: FormalizeChangeRequest,
    dispatch: MachineDispatchDecision,
    current_revision: str,
) -> WorkerRequest:
    """Bind the request to one exact machine-authorized source Action."""

    if dispatch.request_comment_id != request.dispatch_request_comment_id:
        raise ValueError("formalization dispatch correlation is invalid")
    if dispatch.default_branch_revision != current_revision:
        raise ValueError("formalization dispatch revision is stale")
    if (
        dispatch.disposition != "AUTHORIZE"
        or dispatch.issue_number is None
        or dispatch.role is None
        or dispatch.action is None
    ):
        raise ValueError("formalization requires an AUTHORIZE dispatch result")
    return WorkerRequest(dispatch.issue_number, dispatch.role, dispatch.action)


def _issue(repository: str, token: str, issue_number: int) -> Mapping[str, object]:
    payload = _as_mapping(cast(object, _github_json(repository, token, f"issues/{issue_number}")))
    if payload is None or payload.get("number") != issue_number or payload.get("state") != "open":
        raise RuntimeError("formalization source Issue is not an open exact target")
    return payload


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
        raise RuntimeError("formalization branch observation is incomplete")
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
        raise RuntimeError("formalization PR discovery is incomplete")
    result: list[Mapping[str, object]] = []
    for item in raw:
        payload = _as_mapping(item)
        if payload is None:
            raise RuntimeError("formalization PR discovery is malformed")
        result.append(payload)
    return result


def _verify_revision(
    repository: str,
    token: str,
    base_sha: str,
    revision: str,
    manifest: WorkProductManifest,
) -> None:
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
        raise RuntimeError("formalization revision is not one commit on the authorized base")
    observed_paths = {
        cast(str, payload.get("filename"))
        for item in files
        if (payload := _as_mapping(item)) is not None and isinstance(payload.get("filename"), str)
    }
    expected_paths = {file.path for file in manifest.files}
    if len(observed_paths) != len(files) or observed_paths != expected_paths:
        raise RuntimeError("formalization revision contains unrelated or missing paths")
    if any(
        _content_sha_at(repository, token, path=file.path, revision=revision) != file.blob_sha
        for file in manifest.files
    ):
        raise RuntimeError("formalization revision does not resolve the requested blobs")


def _create_revision(repository: str, token: str, manifest: WorkProductManifest) -> str:
    commit = _as_mapping(
        cast(object, _github_json(repository, token, f"git/commits/{manifest.base_sha}"))
    )
    base_tree = None if commit is None else _as_mapping(commit.get("tree"))
    base_tree_sha = None if base_tree is None else base_tree.get("sha")
    if not _valid_sha(base_tree_sha):
        raise RuntimeError("formalization base tree identity is incomplete")
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
                        for f in manifest.files
                    ],
                },
            ),
        )
    )
    tree_sha = None if tree is None else tree.get("sha")
    if not _valid_sha(tree_sha):
        raise RuntimeError("formalization tree creation returned no SHA")
    created = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                "git/commits",
                method="POST",
                payload={
                    "message": manifest.message,
                    "tree": cast(str, tree_sha),
                    "parents": [manifest.base_sha],
                },
            ),
        )
    )
    revision = None if created is None else created.get("sha")
    if not _valid_sha(revision):
        raise RuntimeError("formalization commit creation returned no SHA")
    return cast(str, revision)


def _ensure_revision(
    repository: str,
    token: str,
    branch: str,
    manifest: WorkProductManifest,
) -> str:
    revision = _branch_head(repository, token, branch)
    if revision is None:
        revision = _create_revision(repository, token, manifest)
        _github_json(
            repository,
            token,
            "git/refs",
            method="POST",
            payload={"ref": f"refs/heads/{branch}", "sha": revision},
        )
        if _ref_head_sha(repository, token, branch) != revision:
            raise RuntimeError("formalization ref postcondition was not observed")
    _verify_revision(repository, token, manifest.base_sha, revision, manifest)
    return revision


def _pr_valid(
    pr: Mapping[str, object],
    repository: str,
    branch: str,
    default_branch: str,
    revision: str,
    issue_number: int,
) -> bool:
    head = _as_mapping(pr.get("head"))
    base = _as_mapping(pr.get("base"))
    head_repo = None if head is None else _as_mapping(head.get("repo"))
    base_repo = None if base is None else _as_mapping(base.get("repo"))
    body = pr.get("body")
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
        and isinstance(body, str)
        and re.search(rf"(?mi)^\s*Refs\s+#{issue_number}\s*$", body) is not None
    )


def _ensure_pr(
    repository: str,
    token: str,
    branch: str,
    default_branch: str,
    revision: str,
    source: WorkerRequest,
    change: str,
) -> int:
    prs = _matching_prs(repository, token, branch, default_branch)
    if len(prs) > 1:
        raise RuntimeError("formalization found duplicate lifecycle PR carriers")
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
                        "title": f"OpenSpec: {change}",
                        "body": (
                            f"Formalize OpenSpec change `{change}`.\n\n"
                            f"Refs #{source.issue_number}"
                        ),
                        "head": branch,
                        "base": default_branch,
                        "draft": False,
                    },
                ),
            )
        )
        number = None if created is None else created.get("number")
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise RuntimeError("formalization PR creation returned no exact identity")
        fresh = _as_mapping(cast(object, _github_json(repository, token, f"pulls/{number}")))
        if fresh is None:
            raise RuntimeError("formalization PR postcondition is unavailable")
        prs = [fresh]
    pr = prs[0]
    number = pr.get("number")
    if (
        isinstance(number, bool)
        or not isinstance(number, int)
        or number <= 0
        or not _pr_valid(pr, repository, branch, default_branch, revision, source.issue_number)
    ):
        raise RuntimeError("formalization lifecycle PR identity is invalid")
    return number


def _persist_change(repository: str, token: str, source: WorkerRequest, change: str) -> None:
    issue = _issue(repository, token, source.issue_number)
    current = _change_from_issue(issue)
    if current == change:
        return
    if current != "unset" or _current_authorized_request(repository, token) != source:
        raise RuntimeError("formalization source changed before Issue identity mutation")
    body = issue.get("body")
    if not isinstance(body, str) or _CHANGE_LINE.findall(body) != ["unset"]:
        raise RuntimeError("formalization source Issue Change line is ambiguous")
    updated, count = _CHANGE_LINE.subn(f"Change: {change}", body, count=1)
    if count != 1:
        raise RuntimeError("formalization source Issue Change update is ambiguous")
    _github_json(
        repository,
        token,
        f"issues/{source.issue_number}",
        method="PATCH",
        payload={"body": updated},
    )
    if _change_from_issue(_issue(repository, token, source.issue_number)) != change:
        raise RuntimeError("formalization Issue Change postcondition was not observed")


def apply_change_formalization(
    request: FormalizeChangeRequest,
    source: WorkerRequest,
    request_comment_id: int,
    *,
    repository: str,
    token: str,
    default_branch: str,
) -> ValidationResourceTarget:
    """Construct or reconcile the first Change branch/PR/Issue identity."""

    change = request.proposed_change
    manifest = request.manifest
    branch = _source_branch(change)
    if source.role != "lead" or source.action != "propose-change":
        raise RuntimeError("formalization is only legal for Lead / propose-change")
    if _current_authorized_request(repository, token) != source:
        raise RuntimeError("formalization source dispatch is stale")
    if _current_default_branch(repository, token) != default_branch:
        raise RuntimeError("formalization default branch changed")
    if branch is None or manifest.branch != branch:
        raise RuntimeError("formalization branch is not bound to proposed Change")
    if _ref_head_sha(repository, token, default_branch) != manifest.base_sha:
        raise RuntimeError("formalization base revision is stale")
    if not manifest.files or not all(
        work_product_path_allowed(source, change, file.path) for file in manifest.files
    ):
        raise RuntimeError("formalization path is outside propose-change capability")
    if not _review_openspec_required(source):
        raise RuntimeError("formalization source has no OpenSpec review gate")
    if any(file.expected_sha is not None for file in manifest.files):
        raise RuntimeError("formalization can create only new Change paths")
    if any(
        _content_sha_at(repository, token, path=file.path, revision=manifest.base_sha) is not None
        for file in manifest.files
    ):
        raise RuntimeError("formalization Change path already exists at the base revision")
    current_change = _change_from_issue(_issue(repository, token, source.issue_number))
    if current_change not in {"unset", change}:
        raise RuntimeError("formalization source Issue has a conflicting Change identity")

    revision = _ensure_revision(repository, token, branch, manifest)
    pr_number = _ensure_pr(
        repository, token, branch, default_branch, revision, source, change
    )
    _persist_change(repository, token, source, change)
    pr = _open_pr_payload(
        repository=repository,
        token=token,
        pr_number=pr_number,
        source=source,
        expected_change=change,
        default_branch=default_branch,
    )
    head = _as_mapping(pr.get("head"))
    if head is None or head.get("sha") != revision:
        raise RuntimeError("formalization exact PR-head postcondition was not observed")
    return ValidationResourceTarget(
        repository=repository,
        revision=revision,
        correlation=f"formalize-change-request-{request_comment_id}",
        pr_number=pr_number,
        change=change,
    )


def _write_outputs(target: ValidationResourceTarget | None) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    lines = [f"validation_required={'true' if target is not None else 'false'}"]
    if target is not None:
        lines += [
            f"validation_target_repository={target.repository}",
            f"validation_target_revision={target.revision}",
            f"validation_correlation={target.correlation}",
            f"validation_pr_number={target.pr_number}",
            f"validation_change={target.change}",
        ]
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--default-branch", required=True)
    args = parser.parse_args()
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
    event = _as_mapping(json.loads(Path(args.event_path).read_text(encoding="utf-8")))
    if event is None:
        raise ValueError("GitHub event payload must be an object")
    comment = _as_mapping(event.get("comment"))
    body = None if comment is None else comment.get("body")
    if not isinstance(body, str):
        _write_outputs(None)
        return 0
    request = parse_formalize_change_request(body)
    if request is None:
        _write_outputs(None)
        return 0
    comment_id, _ = _fresh_event_observation(event, body, repository, token)
    dispatch = fetch_dispatch_result(
        repository,
        token,
        request_comment_id=request.dispatch_request_comment_id,
        run_id=request.dispatch_run_id,
        current_revision=args.revision,
    )
    source = source_from_dispatch(request, dispatch, args.revision)
    target = apply_change_formalization(
        request,
        source,
        comment_id,
        repository=repository,
        token=token,
        default_branch=args.default_branch,
    )
    _write_outputs(target)
    print(
        json.dumps(
            {
                "resource": "openspec-exact-validation",
                "repository": target.repository,
                "revision": target.revision,
                "correlation": target.correlation,
                "pr_number": target.pr_number,
                "change": target.change,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
