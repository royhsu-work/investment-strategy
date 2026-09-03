"""Run-scoped exact-revision OpenSpec validation and M0 self-hosting application."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.issue_comment_bridge import (
    parse_dispatch_decision,
    parse_dispatch_request,
)
from investment_strategy.scheduled_agent_application_bridge import parse_application_request
from investment_strategy.scheduled_agent_effects import (
    StagedEffect,
    parse_effect_batch,
    topology_allows_successor,
)
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    acquire_current_github_preflight,
    normalize_github_issue,
)
from investment_strategy.workflow_dispatch import classify_dispatch

RESOURCE_REQUEST_MARKER = "VALIDATION_RESOURCE_REQUEST"
WORK_PRODUCT_REQUEST_MARKER = "WORK_PRODUCT_REQUEST"
HANDOFF_COMPLETION_REQUEST_MARKER = "HANDOFF_COMPLETION_REQUEST"
DISPATCH_REQUEST_COMMENT_ID_PREFIX = "Dispatch-Request-Comment-ID: "
DISPATCH_DECISION_COMMENT_ID_PREFIX = "Dispatch-Decision-Comment-ID: "
EFFECT_REQUEST_COMMENT_ID_PREFIX = "Effect-Request-Comment-ID: "
RESULT_COMMENT_ID_PREFIX = "Result-Comment-ID: "
PR_PREFIX = "PR: "
EXPECTED_CHANGE_PREFIX = "Expected-Change: "
MANIFEST_B64_PREFIX = "Manifest-B64: "
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"
_GITHUB_ACTIONS_BOT_LOGIN = "github-actions[bot]"
_GITHUB_ACTIONS_APP_SLUG = "github-actions"
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_M0_WORK_PRODUCT_SOURCES = frozenset(
    {
        ("lead", "propose-change"),
        ("lead", "resolve-question"),
    }
)


@dataclass(frozen=True)
class ValidationResourceRequest:
    """One transport request for a deterministic exact-revision validation resource."""

    dispatch_request_comment_id: int
    dispatch_decision_comment_id: int
    pr_number: int
    expected_change: str


@dataclass(frozen=True)
class ValidationResourcePlan:
    """Validated transport identity bound to one machine-authorized source action."""

    should_validate: bool
    source: WorkerRequest | None = None
    request_comment_id: int | None = None
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
class WorkProductRequest:
    """One M0 content-addressed work-product request."""

    dispatch_request_comment_id: int
    dispatch_decision_comment_id: int
    pr_number: int
    expected_change: str
    manifest: WorkProductManifest


@dataclass(frozen=True)
class WorkProductPlan:
    """Validated transport identity plus untrusted work-product manifest."""

    should_apply: bool
    source: WorkerRequest | None = None
    request_comment_id: int | None = None
    pr_number: int | None = None
    expected_change: str | None = None
    manifest: WorkProductManifest | None = None


@dataclass(frozen=True)
class HandoffCompletionRequest:
    """One deterministic request to finish an already-applied cross-role handoff."""

    dispatch_request_comment_id: int
    dispatch_decision_comment_id: int
    effect_request_comment_id: int
    result_comment_id: int
    expected_change: str


@dataclass(frozen=True)
class HandoffCompletionPlan:
    """Bound source/effect/result evidence for application-owned HANDOFF completion."""

    should_complete: bool
    source: WorkerRequest | None = None
    request_comment_id: int | None = None
    effect_request_comment_id: int | None = None
    result_comment_id: int | None = None
    expected_change: str | None = None
    raw_worker_result: str | None = None


def _positive_decimal(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0 or str(parsed) != value:
        return None
    return parsed


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


def _valid_repo_path(value: object) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def parse_validation_resource_request(body: str) -> ValidationResourceRequest | None:
    """Parse the exact trigger/audit transport shape; no revision is accepted from the caller."""

    lines = body.split("\n")
    if not lines or lines[0] != RESOURCE_REQUEST_MARKER:
        return None
    if len(lines) != 5:
        raise ValueError("VALIDATION_RESOURCE_REQUEST must contain exactly five lines")
    prefixes = (
        DISPATCH_REQUEST_COMMENT_ID_PREFIX,
        DISPATCH_DECISION_COMMENT_ID_PREFIX,
        PR_PREFIX,
        EXPECTED_CHANGE_PREFIX,
    )
    for line, prefix in zip(lines[1:], prefixes, strict=True):
        if not line.startswith(prefix):
            raise ValueError("VALIDATION_RESOURCE_REQUEST field order is invalid")

    dispatch_request_comment_id = _positive_decimal(lines[1][len(prefixes[0]) :])
    dispatch_decision_comment_id = _positive_decimal(lines[2][len(prefixes[1]) :])
    pr_number = _positive_decimal(lines[3][len(prefixes[2]) :])
    expected_change = lines[4][len(prefixes[3]) :]
    if (
        dispatch_request_comment_id is None
        or dispatch_decision_comment_id is None
        or pr_number is None
        or not _valid_change(expected_change)
    ):
        raise ValueError("VALIDATION_RESOURCE_REQUEST identity is invalid")
    return ValidationResourceRequest(
        dispatch_request_comment_id=dispatch_request_comment_id,
        dispatch_decision_comment_id=dispatch_decision_comment_id,
        pr_number=pr_number,
        expected_change=expected_change,
    )


def _parse_manifest(encoded_manifest: str) -> WorkProductManifest:
    if not encoded_manifest or encoded_manifest != encoded_manifest.strip():
        raise ValueError("WORK_PRODUCT_REQUEST manifest is invalid")
    try:
        raw = base64.b64decode(encoded_manifest.encode("ascii"), validate=True).decode("utf-8")
        decoded = json.loads(raw)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise ValueError("WORK_PRODUCT_REQUEST manifest is not valid base64 JSON") from exc
    if not isinstance(decoded, Mapping) or set(decoded) != {
        "branch",
        "base_sha",
        "message",
        "files",
    }:
        raise ValueError("WORK_PRODUCT_REQUEST manifest fields are invalid")
    branch = decoded.get("branch")
    base_sha = decoded.get("base_sha")
    message = decoded.get("message")
    raw_files = decoded.get("files")
    if (
        not _valid_branch(branch)
        or not _valid_sha(base_sha)
        or not isinstance(message, str)
        or not message.strip()
        or not isinstance(raw_files, list)
        or not raw_files
    ):
        raise ValueError("WORK_PRODUCT_REQUEST manifest identity is invalid")

    files: list[WorkProductFile] = []
    seen_paths: set[str] = set()
    for raw_file in raw_files:
        if not isinstance(raw_file, Mapping) or set(raw_file) != {
            "path",
            "blob_sha",
            "expected_sha",
        }:
            raise ValueError("WORK_PRODUCT_REQUEST file manifest is invalid")
        path = raw_file.get("path")
        blob_sha = raw_file.get("blob_sha")
        expected_sha = raw_file.get("expected_sha")
        if (
            not _valid_repo_path(path)
            or not _valid_sha(blob_sha)
            or (expected_sha is not None and not _valid_sha(expected_sha))
        ):
            raise ValueError("WORK_PRODUCT_REQUEST file identity is invalid")
        normalized_path = cast(str, path)
        if normalized_path in seen_paths:
            raise ValueError("WORK_PRODUCT_REQUEST contains duplicate paths")
        seen_paths.add(normalized_path)
        files.append(
            WorkProductFile(
                path=normalized_path,
                blob_sha=cast(str, blob_sha),
                expected_sha=cast(str | None, expected_sha),
            )
        )
    return WorkProductManifest(
        branch=cast(str, branch),
        base_sha=cast(str, base_sha),
        message=cast(str, message),
        files=tuple(files),
    )


def parse_work_product_request(body: str) -> WorkProductRequest | None:
    """Parse the M0 blob-reference request; source/spec content is never carried in the comment."""

    lines = body.split("\n")
    if not lines or lines[0] != WORK_PRODUCT_REQUEST_MARKER:
        return None
    if len(lines) != 6:
        raise ValueError("WORK_PRODUCT_REQUEST must contain exactly six lines")
    prefixes = (
        DISPATCH_REQUEST_COMMENT_ID_PREFIX,
        DISPATCH_DECISION_COMMENT_ID_PREFIX,
        PR_PREFIX,
        EXPECTED_CHANGE_PREFIX,
        MANIFEST_B64_PREFIX,
    )
    for line, prefix in zip(lines[1:], prefixes, strict=True):
        if not line.startswith(prefix):
            raise ValueError("WORK_PRODUCT_REQUEST field order is invalid")
    dispatch_request_comment_id = _positive_decimal(lines[1][len(prefixes[0]) :])
    dispatch_decision_comment_id = _positive_decimal(lines[2][len(prefixes[1]) :])
    pr_number = _positive_decimal(lines[3][len(prefixes[2]) :])
    expected_change = lines[4][len(prefixes[3]) :]
    if (
        dispatch_request_comment_id is None
        or dispatch_decision_comment_id is None
        or pr_number is None
        or not _valid_change(expected_change)
    ):
        raise ValueError("WORK_PRODUCT_REQUEST identity is invalid")
    return WorkProductRequest(
        dispatch_request_comment_id=dispatch_request_comment_id,
        dispatch_decision_comment_id=dispatch_decision_comment_id,
        pr_number=pr_number,
        expected_change=expected_change,
        manifest=_parse_manifest(lines[5][len(prefixes[4]) :]),
    )


def parse_handoff_completion_request(body: str) -> HandoffCompletionRequest | None:
    """Parse the exact IDs needed to complete an already-applied cross-role transfer."""

    lines = body.split("\n")
    if not lines or lines[0] != HANDOFF_COMPLETION_REQUEST_MARKER:
        return None
    if len(lines) != 6:
        raise ValueError("HANDOFF_COMPLETION_REQUEST must contain exactly six lines")
    prefixes = (
        DISPATCH_REQUEST_COMMENT_ID_PREFIX,
        DISPATCH_DECISION_COMMENT_ID_PREFIX,
        EFFECT_REQUEST_COMMENT_ID_PREFIX,
        RESULT_COMMENT_ID_PREFIX,
        EXPECTED_CHANGE_PREFIX,
    )
    for line, prefix in zip(lines[1:], prefixes, strict=True):
        if not line.startswith(prefix):
            raise ValueError("HANDOFF_COMPLETION_REQUEST field order is invalid")
    values = [_positive_decimal(lines[index][len(prefixes[index - 1]) :]) for index in range(1, 5)]
    expected_change = lines[5][len(prefixes[4]) :]
    if any(value is None for value in values) or not _valid_change(expected_change):
        raise ValueError("HANDOFF_COMPLETION_REQUEST identity is invalid")
    return HandoffCompletionRequest(
        dispatch_request_comment_id=cast(int, values[0]),
        dispatch_decision_comment_id=cast(int, values[1]),
        effect_request_comment_id=cast(int, values[2]),
        result_comment_id=cast(int, values[3]),
        expected_change=expected_change,
    )


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, dict) else None


def _flatten_comments(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValueError("comments payload must be a JSON array")
    comments: list[Mapping[str, object]] = []
    for item in value:
        nested_items = item if isinstance(item, list) else [item]
        for nested in nested_items:
            mapping = _as_mapping(nested)
            if mapping is None:
                raise ValueError("comments payload contains a non-object item")
            comments.append(mapping)
    return comments


def _comment_by_id(
    comments: Sequence[Mapping[str, object]], comment_id: int
) -> Mapping[str, object] | None:
    matches = [comment for comment in comments if comment.get("id") == comment_id]
    if len(matches) > 1:
        raise ValueError("comment identity is duplicated")
    return matches[0] if matches else None


def _app_slug(comment: Mapping[str, object]) -> str | None:
    app = _as_mapping(comment.get("performed_via_github_app"))
    slug = None if app is None else app.get("slug")
    return slug if isinstance(slug, str) else None


def _user_login(comment: Mapping[str, object]) -> str | None:
    user = _as_mapping(comment.get("user"))
    login = None if user is None else user.get("login")
    return login if isinstance(login, str) else None


def _trusted_connector_comment(comment: Mapping[str, object]) -> bool:
    return _app_slug(comment) == _CHATGPT_CONNECTOR_APP_SLUG


def _trusted_actions_comment(comment: Mapping[str, object]) -> bool:
    return (
        _user_login(comment) == _GITHUB_ACTIONS_BOT_LOGIN
        and _app_slug(comment) == _GITHUB_ACTIONS_APP_SLUG
    )


def _correlated_source(
    *,
    event: Mapping[str, object],
    comments_payload: object,
    configured_issue_number: int,
    repository: str,
    current_revision: str,
    body: str,
    dispatch_request_comment_id: int,
    dispatch_decision_comment_id: int,
) -> tuple[WorkerRequest, int, list[Mapping[str, object]]]:
    if configured_issue_number <= 0 or "/" not in repository or not current_revision:
        raise ValueError("repository/check-in identity is invalid")
    issue = _as_mapping(event.get("issue"))
    comment = _as_mapping(event.get("comment"))
    if event.get("action") != "created" or issue is None or comment is None:
        raise ValueError("application request event is invalid")
    if "pull_request" in issue or issue.get("number") != configured_issue_number:
        raise ValueError("application request is not on the configured check-in Issue")
    event_comment_id = comment.get("id")
    if (
        not isinstance(event_comment_id, int)
        or event_comment_id <= 0
        or comment.get("body") != body
        or not _trusted_connector_comment(comment)
    ):
        raise ValueError("application request requires the configured ChatGPT connector")

    comments = _flatten_comments(comments_payload)
    durable_request = _comment_by_id(comments, event_comment_id)
    if (
        durable_request is None
        or durable_request.get("body") != body
        or not _trusted_connector_comment(durable_request)
    ):
        raise ValueError("application request is missing from durable transport history")

    dispatch_request_comment = _comment_by_id(comments, dispatch_request_comment_id)
    dispatch_decision_comment = _comment_by_id(comments, dispatch_decision_comment_id)
    if dispatch_request_comment is None or not _trusted_connector_comment(dispatch_request_comment):
        raise ValueError("dispatch request is missing or untrusted")
    dispatch_request_body = dispatch_request_comment.get("body")
    if (
        not isinstance(dispatch_request_body, str)
        or parse_dispatch_request(dispatch_request_body) is None
    ):
        raise ValueError("dispatch request is malformed")
    if dispatch_decision_comment is None or not _trusted_actions_comment(dispatch_decision_comment):
        raise ValueError("dispatch decision is missing or untrusted")
    decision_body = dispatch_decision_comment.get("body")
    if not isinstance(decision_body, str):
        raise ValueError("dispatch decision is malformed")
    decision = parse_dispatch_decision(decision_body)
    if decision is None or decision.request_comment_id != dispatch_request_comment_id:
        raise ValueError("dispatch decision correlation is invalid")
    if decision.default_branch_revision != current_revision:
        raise ValueError("dispatch revision is stale")
    if (
        decision.disposition != "AUTHORIZE"
        or decision.issue_number is None
        or decision.role is None
        or decision.action is None
    ):
        raise ValueError("application request requires an AUTHORIZE dispatch decision")
    return (
        WorkerRequest(
            decision.issue_number,
            decision.role,
            decision.action,
            debt_disposition=decision.debt_disposition,
        ),
        event_comment_id,
        comments,
    )


def plan_validation_resource(
    *,
    event: Mapping[str, object],
    comments_payload: object,
    configured_issue_number: int,
    repository: str,
    current_revision: str,
) -> ValidationResourcePlan:
    """Bind one resource request to its exact trusted machine dispatch decision."""

    comment = _as_mapping(event.get("comment"))
    body = None if comment is None else comment.get("body")
    if not isinstance(body, str):
        return ValidationResourcePlan(False)
    request = parse_validation_resource_request(body)
    if request is None:
        return ValidationResourcePlan(False)
    source, event_comment_id, _ = _correlated_source(
        event=event,
        comments_payload=comments_payload,
        configured_issue_number=configured_issue_number,
        repository=repository,
        current_revision=current_revision,
        body=body,
        dispatch_request_comment_id=request.dispatch_request_comment_id,
        dispatch_decision_comment_id=request.dispatch_decision_comment_id,
    )
    return ValidationResourcePlan(
        True,
        source=source,
        request_comment_id=event_comment_id,
        pr_number=request.pr_number,
        expected_change=request.expected_change,
    )


def plan_work_product_application(
    *,
    event: Mapping[str, object],
    comments_payload: object,
    configured_issue_number: int,
    repository: str,
    current_revision: str,
) -> WorkProductPlan:
    """Bind one blob-reference work product to the exact source dispatch."""

    comment = _as_mapping(event.get("comment"))
    body = None if comment is None else comment.get("body")
    if not isinstance(body, str):
        return WorkProductPlan(False)
    request = parse_work_product_request(body)
    if request is None:
        return WorkProductPlan(False)
    source, event_comment_id, _ = _correlated_source(
        event=event,
        comments_payload=comments_payload,
        configured_issue_number=configured_issue_number,
        repository=repository,
        current_revision=current_revision,
        body=body,
        dispatch_request_comment_id=request.dispatch_request_comment_id,
        dispatch_decision_comment_id=request.dispatch_decision_comment_id,
    )
    return WorkProductPlan(
        True,
        source=source,
        request_comment_id=event_comment_id,
        pr_number=request.pr_number,
        expected_change=request.expected_change,
        manifest=request.manifest,
    )


def plan_handoff_completion(
    *,
    event: Mapping[str, object],
    comments_payload: object,
    configured_issue_number: int,
    repository: str,
    current_revision: str,
) -> HandoffCompletionPlan:
    """Bind a HANDOFF completion request to the exact prior source application."""

    comment = _as_mapping(event.get("comment"))
    body = None if comment is None else comment.get("body")
    if not isinstance(body, str):
        return HandoffCompletionPlan(False)
    request = parse_handoff_completion_request(body)
    if request is None:
        return HandoffCompletionPlan(False)
    source, event_comment_id, comments = _correlated_source(
        event=event,
        comments_payload=comments_payload,
        configured_issue_number=configured_issue_number,
        repository=repository,
        current_revision=current_revision,
        body=body,
        dispatch_request_comment_id=request.dispatch_request_comment_id,
        dispatch_decision_comment_id=request.dispatch_decision_comment_id,
    )
    effect_comment = _comment_by_id(comments, request.effect_request_comment_id)
    if effect_comment is None or not _trusted_connector_comment(effect_comment):
        raise ValueError("HANDOFF completion effect request is missing or untrusted")
    effect_body = effect_comment.get("body")
    if not isinstance(effect_body, str):
        raise ValueError("HANDOFF completion effect request body is missing")
    effect_request = parse_application_request(effect_body)
    if (
        effect_request is None
        or effect_request.dispatch_request_comment_id != request.dispatch_request_comment_id
        or effect_request.dispatch_decision_comment_id != request.dispatch_decision_comment_id
    ):
        raise ValueError("HANDOFF completion effect request correlation is invalid")
    return HandoffCompletionPlan(
        True,
        source=source,
        request_comment_id=event_comment_id,
        effect_request_comment_id=request.effect_request_comment_id,
        result_comment_id=request.result_comment_id,
        expected_change=request.expected_change,
        raw_worker_result=effect_request.raw_worker_result,
    )


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
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
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
        debt_disposition=decision.selected_debt_disposition,
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


def _open_pr_payload(
    *,
    repository: str,
    token: str,
    pr_number: int,
    source: WorkerRequest,
    expected_change: str,
    default_branch: str,
) -> Mapping[str, object]:
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
    if pr is None or pr.get("state") != "open" or pr.get("merged") is True:
        raise RuntimeError("validation resource target PR is not one current open PR")
    head = _as_mapping(pr.get("head"))
    base = _as_mapping(pr.get("base"))
    head_repo = None if head is None else _as_mapping(head.get("repo"))
    base_repo = None if base is None else _as_mapping(base.get("repo"))
    if (
        head is None
        or base is None
        or head_repo is None
        or base_repo is None
        or head_repo.get("full_name") != repository
        or base_repo.get("full_name") != repository
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


def _review_openspec_required(
    source: WorkerRequest,
    *,
    workflow_text: str,
) -> bool:
    review_effect = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps(
            {
                "issue_number": source.issue_number,
                "role": "reviewer",
                "action": "review-openspec",
            },
            sort_keys=True,
        ),
    )
    return topology_allows_successor(workflow_text, source, review_effect)


def resolve_validation_resource_target(
    plan: ValidationResourcePlan,
    *,
    repository: str,
    token: str,
    default_branch: str,
    workflow_text: str,
) -> ValidationResourceTarget:
    """Fresh-reauthorize the source and derive exact R from the current PR, never caller SHA."""

    if (
        not plan.should_validate
        or plan.source is None
        or plan.request_comment_id is None
        or plan.pr_number is None
        or plan.expected_change is None
    ):
        raise RuntimeError("validation resource plan is incomplete")
    if _current_authorized_request(repository, token) != plan.source:
        raise RuntimeError("validation resource source dispatch is stale")
    if not _review_openspec_required(plan.source, workflow_text=workflow_text):
        raise RuntimeError("validation resource is not required by this source topology")

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
        correlation=f"validation-resource-request-{plan.request_comment_id}",
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


def apply_work_product(
    plan: WorkProductPlan,
    *,
    repository: str,
    token: str,
    default_branch: str,
    workflow_text: str,
) -> ValidationResourceTarget:
    """Apply one content-addressed OpenSpec work product as one exact Git commit R."""

    if (
        not plan.should_apply
        or plan.source is None
        or plan.request_comment_id is None
        or plan.pr_number is None
        or plan.expected_change is None
        or plan.manifest is None
    ):
        raise RuntimeError("work-product plan is incomplete")
    if (plan.source.role, plan.source.action) not in _M0_WORK_PRODUCT_SOURCES:
        raise RuntimeError("work-product source action is not authorized")
    if _current_authorized_request(repository, token) != plan.source:
        raise RuntimeError("work-product source dispatch is stale")
    if not _review_openspec_required(plan.source, workflow_text=workflow_text):
        raise RuntimeError("work-product source has no OpenSpec review gate")

    pr = _open_pr_payload(
        repository=repository,
        token=token,
        pr_number=plan.pr_number,
        source=plan.source,
        expected_change=plan.expected_change,
        default_branch=default_branch,
    )
    head = _as_mapping(pr.get("head"))
    current_head = None if head is None else head.get("sha")
    current_branch = None if head is None else head.get("ref")
    if current_head != plan.manifest.base_sha or current_branch != plan.manifest.branch:
        raise RuntimeError("work-product PR head/base identity is stale")

    change_prefix = f"openspec/changes/{plan.expected_change}/"
    for file in plan.manifest.files:
        if not file.path.startswith(change_prefix):
            raise RuntimeError("work-product path escapes the source Change")
        current_sha = _content_sha_at(
            repository,
            token,
            path=file.path,
            revision=plan.manifest.base_sha,
        )
        if current_sha != file.expected_sha:
            raise RuntimeError("work-product expected content SHA is stale")

    base_commit = _as_mapping(
        cast(object, _github_json(repository, token, f"git/commits/{plan.manifest.base_sha}"))
    )
    base_tree = None if base_commit is None else _as_mapping(base_commit.get("tree"))
    base_tree_sha = None if base_tree is None else base_tree.get("sha")
    if not _valid_sha(base_tree_sha):
        raise RuntimeError("work-product base tree identity is incomplete")

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
    tree_sha = None if tree_response is None else tree_response.get("sha")
    if not _valid_sha(tree_sha):
        raise RuntimeError("work-product tree creation returned no SHA")

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
    for file in plan.manifest.files:
        matches = [
            entry
            for raw_entry in tree_entries
            if (entry := _as_mapping(raw_entry)) is not None
            and entry.get("path") == file.path
        ]
        if (
            len(matches) != 1
            or matches[0].get("type") != "blob"
            or matches[0].get("sha") != file.blob_sha
        ):
            raise RuntimeError("work-product referenced blob was not resolved into exact tree path")

    commit_response = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                "git/commits",
                method="POST",
                payload={
                    "message": plan.manifest.message,
                    "tree": cast(str, tree_sha),
                    "parents": [plan.manifest.base_sha],
                },
            ),
        )
    )
    revision = None if commit_response is None else commit_response.get("sha")
    if not _valid_sha(revision):
        raise RuntimeError("work-product commit creation returned no SHA")

    _github_json(
        repository,
        token,
        f"git/refs/heads/{quote(plan.manifest.branch, safe='/')}",
        method="PATCH",
        payload={"sha": cast(str, revision), "force": False},
    )

    if _ref_head_sha(repository, token, plan.manifest.branch) != revision:
        raise RuntimeError("work-product ref postcondition was not observed")
    observed_pr = _as_mapping(
        cast(object, _github_json(repository, token, f"pulls/{plan.pr_number}"))
    )
    observed_head = None if observed_pr is None else _as_mapping(observed_pr.get("head"))
    if (
        observed_pr is None
        or observed_pr.get("state") != "open"
        or observed_head is None
        or observed_head.get("ref") != plan.manifest.branch
        or observed_head.get("sha") != revision
    ):
        raise RuntimeError("work-product PR-head postcondition was not observed")

    observed_commit = _as_mapping(
        cast(object, _github_json(repository, token, f"git/commits/{revision}"))
    )
    observed_tree = None if observed_commit is None else _as_mapping(observed_commit.get("tree"))
    parents = None if observed_commit is None else observed_commit.get("parents")
    parent = None if not isinstance(parents, list) or len(parents) != 1 else _as_mapping(parents[0])
    if (
        observed_commit is None
        or observed_commit.get("sha") != revision
        or observed_tree is None
        or observed_tree.get("sha") != tree_sha
        or parent is None
        or parent.get("sha") != plan.manifest.base_sha
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

    return ValidationResourceTarget(
        repository=repository,
        revision=cast(str, revision),
        correlation=f"work-product-request-{plan.request_comment_id}",
        pr_number=plan.pr_number,
        change=plan.expected_change,
    )


def _routing_target_from_effect(effect: StagedEffect) -> tuple[str, str] | None:
    if effect.kind != "routing-transition":
        return None
    try:
        payload = json.loads(effect.payload_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    role = payload.get("role")
    action = payload.get("action")
    if not isinstance(role, str) or not isinstance(action, str):
        return None
    return role, action


def _requested_result_body(raw_worker_result: str, source: WorkerRequest) -> str:
    batch = parse_effect_batch(raw_worker_result, source)
    bodies: list[str] = []
    for effect in batch.effects:
        if effect.kind != "issue-comment":
            continue
        try:
            payload = json.loads(effect.payload_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping):
            continue
        body = payload.get("body")
        if isinstance(body, str) and body.startswith("## ACTION_RESULT"):
            bodies.append(body)
    if len(bodies) != 1:
        raise RuntimeError("HANDOFF completion requires exactly one source ACTION_RESULT")
    return bodies[0]


def _cross_role_target(raw_worker_result: str, source: WorkerRequest) -> tuple[str, str]:
    batch = parse_effect_batch(raw_worker_result, source)
    targets = [
        target
        for effect in batch.effects
        if (target := _routing_target_from_effect(effect)) is not None and target[0] != source.role
    ]
    if len(targets) != 1:
        raise RuntimeError("HANDOFF completion requires exactly one cross-role routing target")
    return targets[0]


def _handoff_body(
    *,
    source: WorkerRequest,
    target: tuple[str, str],
    change: str,
    result_comment_id: int,
) -> str:
    source_role = source.role.capitalize()
    target_role = target[0].capitalize()
    return "\n".join(
        (
            "## HANDOFF",
            f"Workflow: #{source.issue_number}",
            f"Change: `{change}`",
            f"From: `{source_role} / {source.action}`",
            f"To: `{target_role} / {target[1]}`",
            f"Trigger-Result-Comment-ID: {result_comment_id}",
            f"Revision-Evidence: issuecomment-{result_comment_id}",
            "Source-Routing-Reauthorization: `PASS`",
            "Routing-Mutation: `APPLIED`",
            f"Observed-Target: `{target_role} / {target[1]}`",
            f"Next-Owner: `{target_role}`",
            f"Next-Action: `{target[1]}`",
        )
    )


def complete_cross_role_handoff(
    plan: HandoffCompletionPlan,
    *,
    repository: str,
    token: str,
) -> int:
    """Persist canonical HANDOFF only after fresh observation of the applied target routing."""

    if (
        not plan.should_complete
        or plan.source is None
        or plan.effect_request_comment_id is None
        or plan.result_comment_id is None
        or plan.expected_change is None
        or plan.raw_worker_result is None
    ):
        raise RuntimeError("HANDOFF completion plan is incomplete")
    if (plan.source.role, plan.source.action) not in _M0_WORK_PRODUCT_SOURCES:
        raise RuntimeError("HANDOFF completion source is not an M0 OpenSpec owner")

    target = _cross_role_target(plan.raw_worker_result, plan.source)
    if target != ("reviewer", "review-openspec"):
        raise RuntimeError("HANDOFF completion target is outside the M0 OpenSpec boundary")
    expected_result_body = _requested_result_body(plan.raw_worker_result, plan.source)

    issue = _as_mapping(
        cast(object, _github_json(repository, token, f"issues/{plan.source.issue_number}"))
    )
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        issue is None
        or issue.get("state") != "open"
        or _change_from_issue(issue) != plan.expected_change
        or observation is None
        or not observation.authoritative
        or observation.routing != target
    ):
        raise RuntimeError("HANDOFF target routing postcondition is not current")

    result_comment = _as_mapping(
        cast(object, _github_json(repository, token, f"issues/comments/{plan.result_comment_id}"))
    )
    if (
        result_comment is None
        or result_comment.get("body") != expected_result_body
        or not _trusted_actions_comment(result_comment)
    ):
        raise RuntimeError("HANDOFF source result comment is missing or untrusted")

    body = _handoff_body(
        source=plan.source,
        target=target,
        change=plan.expected_change,
        result_comment_id=plan.result_comment_id,
    )
    page = 1
    matching: list[int] = []
    while True:
        comments = _github_json(
            repository,
            token,
            f"issues/{plan.source.issue_number}/comments?per_page=100&page={page}",
        )
        if not isinstance(comments, list):
            raise RuntimeError("HANDOFF comment observation is incomplete")
        for raw_comment in comments:
            comment = _as_mapping(raw_comment)
            if (
                comment is not None
                and comment.get("body") == body
                and isinstance(comment.get("id"), int)
                and _trusted_actions_comment(comment)
            ):
                matching.append(cast(int, comment["id"]))
        if len(comments) < 100:
            break
        page += 1
    if len(matching) > 1:
        raise RuntimeError("HANDOFF completion is duplicated")
    if len(matching) == 1:
        return matching[0]

    response = _as_mapping(
        cast(
            object,
            _github_json(
                repository,
                token,
                f"issues/{plan.source.issue_number}/comments",
                method="POST",
                payload={"body": body},
            ),
        )
    )
    comment_id = None if response is None else response.get("id")
    if not isinstance(comment_id, int):
        raise RuntimeError("HANDOFF persistence returned no comment id")

    observed_comment = _as_mapping(
        cast(object, _github_json(repository, token, f"issues/comments/{comment_id}"))
    )
    observed_issue = _as_mapping(
        cast(object, _github_json(repository, token, f"issues/{plan.source.issue_number}"))
    )
    observed_state = None if observed_issue is None else normalize_github_issue(observed_issue)
    if (
        observed_comment is None
        or observed_comment.get("body") != body
        or observed_comment.get("id") != comment_id
        or observed_state is None
        or not observed_state.authoritative
        or observed_state.routing != target
    ):
        raise RuntimeError("HANDOFF durable postcondition was not observed")
    return comment_id


def _write_outputs(target: ValidationResourceTarget | None) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    lines = [f"validation_required={'true' if target is not None else 'false'}"]
    if target is not None:
        lines.extend(
            (
                f"validation_target_repository={target.repository}",
                f"validation_target_revision={target.revision}",
                f"validation_correlation={target.correlation}",
                f"validation_pr_number={target.pr_number}",
                f"validation_change={target.change}",
            )
        )
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def _load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--comments-path", required=True)
    parser.add_argument("--check-in-issue", required=True, type=int)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--default-branch", required=True)
    args = parser.parse_args()

    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    event = _as_mapping(_load_json(args.event_path))
    if event is None:
        raise ValueError("GitHub event payload must be an object")
    comments_payload = _load_json(args.comments_path)
    event_comment = _as_mapping(event.get("comment"))
    body = None if event_comment is None else event_comment.get("body")
    if not isinstance(body, str):
        _write_outputs(None)
        return 0

    workflow_text = Path("agents/workflow.md").read_text(encoding="utf-8")
    target: ValidationResourceTarget | None = None
    if body.startswith(RESOURCE_REQUEST_MARKER):
        validation_plan = plan_validation_resource(
            event=event,
            comments_payload=comments_payload,
            configured_issue_number=args.check_in_issue,
            repository=repository,
            current_revision=args.revision,
        )
        if validation_plan.should_validate:
            target = resolve_validation_resource_target(
                validation_plan,
                repository=repository,
                token=token,
                default_branch=args.default_branch,
                workflow_text=workflow_text,
            )
    elif body.startswith(WORK_PRODUCT_REQUEST_MARKER):
        work_product_plan = plan_work_product_application(
            event=event,
            comments_payload=comments_payload,
            configured_issue_number=args.check_in_issue,
            repository=repository,
            current_revision=args.revision,
        )
        if work_product_plan.should_apply:
            target = apply_work_product(
                work_product_plan,
                repository=repository,
                token=token,
                default_branch=args.default_branch,
                workflow_text=workflow_text,
            )
    elif body.startswith(HANDOFF_COMPLETION_REQUEST_MARKER):
        handoff_plan = plan_handoff_completion(
            event=event,
            comments_payload=comments_payload,
            configured_issue_number=args.check_in_issue,
            repository=repository,
            current_revision=args.revision,
        )
        if handoff_plan.should_complete:
            comment_id = complete_cross_role_handoff(
                handoff_plan,
                repository=repository,
                token=token,
            )
            _write_outputs(None)
            print(
                json.dumps(
                    {
                        "resource": "cross-role-handoff",
                        "comment_id": comment_id,
                    },
                    sort_keys=True,
                )
            )
            return 0
    else:
        _write_outputs(None)
        return 0

    _write_outputs(target)
    if target is not None:
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
