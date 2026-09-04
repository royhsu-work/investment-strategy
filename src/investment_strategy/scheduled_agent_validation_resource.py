"""Run-scoped exact-revision OpenSpec validation resource for Scheduled Agent application."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.request import Request, urlopen

from investment_strategy.issue_comment_bridge import (
    parse_dispatch_decision,
    parse_dispatch_request,
)
from investment_strategy.scheduled_agent_effects import StagedEffect, topology_allows_successor
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    acquire_current_github_preflight,
)
from investment_strategy.workflow_dispatch import classify_dispatch

RESOURCE_REQUEST_MARKER = "VALIDATION_RESOURCE_REQUEST"
DISPATCH_REQUEST_COMMENT_ID_PREFIX = "Dispatch-Request-Comment-ID: "
DISPATCH_DECISION_COMMENT_ID_PREFIX = "Dispatch-Decision-Comment-ID: "
PR_PREFIX = "PR: "
EXPECTED_CHANGE_PREFIX = "Expected-Change: "
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"
_GITHUB_ACTIONS_BOT_LOGIN = "github-actions[bot]"
_GITHUB_ACTIONS_APP_SLUG = "github-actions"
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")


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


def _positive_decimal(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0 or str(parsed) != value:
        return None
    return parsed


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
        or not expected_change
        or expected_change != expected_change.strip()
        or any(character.isspace() for character in expected_change)
    ):
        raise ValueError("VALIDATION_RESOURCE_REQUEST identity is invalid")
    return ValidationResourceRequest(
        dispatch_request_comment_id=dispatch_request_comment_id,
        dispatch_decision_comment_id=dispatch_decision_comment_id,
        pr_number=pr_number,
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


def plan_validation_resource(
    *,
    event: Mapping[str, object],
    comments_payload: object,
    configured_issue_number: int,
    repository: str,
    current_revision: str,
) -> ValidationResourcePlan:
    """Bind one resource request to its exact trusted machine dispatch decision."""

    if event.get("action") != "created":
        return ValidationResourcePlan(False)
    issue = _as_mapping(event.get("issue"))
    comment = _as_mapping(event.get("comment"))
    if issue is None or comment is None or issue.get("number") != configured_issue_number:
        return ValidationResourcePlan(False)
    body = comment.get("body")
    if not isinstance(body, str):
        return ValidationResourcePlan(False)
    request = parse_validation_resource_request(body)
    if request is None:
        return ValidationResourcePlan(False)
    event_comment_id = comment.get("id")
    if (
        not isinstance(event_comment_id, int)
        or event_comment_id <= 0
        or not _trusted_connector_comment(comment)
    ):
        raise ValueError("validation resource request requires the configured ChatGPT connector")

    comments = _flatten_comments(comments_payload)
    durable_request = _comment_by_id(comments, event_comment_id)
    if (
        durable_request is None
        or durable_request.get("body") != body
        or not _trusted_connector_comment(durable_request)
    ):
        raise ValueError("validation resource request is missing from durable transport history")

    dispatch_request_comment = _comment_by_id(comments, request.dispatch_request_comment_id)
    dispatch_decision_comment = _comment_by_id(comments, request.dispatch_decision_comment_id)
    if dispatch_request_comment is None or not _trusted_connector_comment(dispatch_request_comment):
        raise ValueError("validation resource dispatch request is missing or untrusted")
    dispatch_request_body = dispatch_request_comment.get("body")
    if (
        not isinstance(dispatch_request_body, str)
        or parse_dispatch_request(dispatch_request_body) is None
    ):
        raise ValueError("validation resource dispatch request is malformed")
    if dispatch_decision_comment is None or not _trusted_actions_comment(dispatch_decision_comment):
        raise ValueError("validation resource dispatch decision is missing or untrusted")
    dispatch_decision_body = dispatch_decision_comment.get("body")
    if not isinstance(dispatch_decision_body, str):
        raise ValueError("validation resource dispatch decision is malformed")
    decision = parse_dispatch_decision(dispatch_decision_body)
    if decision is None or decision.request_comment_id != request.dispatch_request_comment_id:
        raise ValueError("validation resource dispatch decision correlation is invalid")
    if decision.default_branch_revision != current_revision:
        raise ValueError("validation resource dispatch revision is stale")
    if (
        decision.disposition != "AUTHORIZE"
        or decision.issue_number is None
        or decision.role is None
        or decision.action is None
    ):
        raise ValueError("validation resource requires an AUTHORIZE dispatch decision")

    return ValidationResourcePlan(
        True,
        source=WorkerRequest(
            decision.issue_number,
            decision.role,
            decision.action,
            debt_disposition=decision.debt_disposition,
        ),
        request_comment_id=event_comment_id,
        pr_number=request.pr_number,
        expected_change=request.expected_change,
    )


def _github_json(repository: str, token: str, api_path: str) -> object:
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        return json.loads(response.read().decode("utf-8"))


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


def _open_pr_target(
    *,
    repository: str,
    token: str,
    pr_number: int,
    source: WorkerRequest,
    expected_change: str,
    default_branch: str,
) -> str:
    issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    if (
        issue is None
        or issue.get("state") != "open"
        or _change_from_issue(issue) != expected_change
    ):
        raise RuntimeError("validation resource source Issue/Change identity changed")

    pr = _as_mapping(_github_json(repository, token, f"pulls/{pr_number}"))
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

    revision = head.get("sha")
    if not isinstance(revision, str) or not revision:
        raise RuntimeError("validation resource target PR head is incomplete")
    return revision


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

    review_effect = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps(
            {
                "issue_number": plan.source.issue_number,
                "role": "reviewer",
                "action": "review-openspec",
            },
            sort_keys=True,
        ),
    )
    if not topology_allows_successor(workflow_text, plan.source, review_effect):
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
    plan = plan_validation_resource(
        event=event,
        comments_payload=_load_json(args.comments_path),
        configured_issue_number=args.check_in_issue,
        repository=repository,
        current_revision=args.revision,
    )
    if not plan.should_validate:
        _write_outputs(None)
        return 0

    target = resolve_validation_resource_target(
        plan,
        repository=repository,
        token=token,
        default_branch=args.default_branch,
        workflow_text=Path("agents/workflow.md").read_text(encoding="utf-8"),
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
