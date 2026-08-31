"""Issue-comment ingress for repository-owned Scheduled Agent effect application."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from investment_strategy.issue_comment_bridge import (
    parse_dispatch_decision,
    parse_dispatch_request,
)
from investment_strategy.scheduled_agent_merge_acceptance import run_guarded_effect_application
from investment_strategy.scheduled_agent_runtime import WorkerRequest

APPLICATION_REQUEST_MARKER = "EFFECT_REQUEST"
DISPATCH_REQUEST_COMMENT_ID_PREFIX = "Dispatch-Request-Comment-ID: "
DISPATCH_DECISION_COMMENT_ID_PREFIX = "Dispatch-Decision-Comment-ID: "
WORKER_RESULT_B64_PREFIX = "Worker-Result-B64: "
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"
_GITHUB_ACTIONS_BOT_LOGIN = "github-actions[bot]"
_GITHUB_ACTIONS_APP_SLUG = "github-actions"


@dataclass(frozen=True)
class ApplicationRequest:
    """One transport request bound to one prior machine dispatch decision."""

    dispatch_request_comment_id: int
    dispatch_decision_comment_id: int
    raw_worker_result: str


@dataclass(frozen=True)
class ApplicationPlan:
    """Validated application input or an unrelated-comment no-op."""

    should_apply: bool
    source: WorkerRequest | None = None
    raw_worker_result: str | None = None


def _positive_decimal(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0 or str(parsed) != value:
        return None
    return parsed


def parse_application_request(body: str) -> ApplicationRequest | None:
    """Parse the exact bounded EFFECT_REQUEST transport format."""

    lines = body.split("\n")
    if not lines or lines[0] != APPLICATION_REQUEST_MARKER:
        return None
    if len(lines) != 4:
        raise ValueError("EFFECT_REQUEST must contain exactly four lines")
    if not lines[1].startswith(DISPATCH_REQUEST_COMMENT_ID_PREFIX):
        raise ValueError("EFFECT_REQUEST dispatch request id is missing")
    if not lines[2].startswith(DISPATCH_DECISION_COMMENT_ID_PREFIX):
        raise ValueError("EFFECT_REQUEST dispatch decision id is missing")
    if not lines[3].startswith(WORKER_RESULT_B64_PREFIX):
        raise ValueError("EFFECT_REQUEST worker result is missing")

    request_comment_id = _positive_decimal(
        lines[1][len(DISPATCH_REQUEST_COMMENT_ID_PREFIX) :]
    )
    decision_comment_id = _positive_decimal(
        lines[2][len(DISPATCH_DECISION_COMMENT_ID_PREFIX) :]
    )
    encoded_result = lines[3][len(WORKER_RESULT_B64_PREFIX) :]
    if request_comment_id is None or decision_comment_id is None or not encoded_result:
        raise ValueError("EFFECT_REQUEST identity is invalid")
    if encoded_result != encoded_result.strip():
        raise ValueError("EFFECT_REQUEST worker result must be trimmed")

    try:
        raw_worker_result = base64.b64decode(encoded_result.encode("ascii"), validate=True).decode(
            "utf-8"
        )
        decoded = json.loads(raw_worker_result)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise ValueError("EFFECT_REQUEST worker result is not valid base64 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("EFFECT_REQUEST worker result must decode to a JSON object")

    return ApplicationRequest(
        dispatch_request_comment_id=request_comment_id,
        dispatch_decision_comment_id=decision_comment_id,
        raw_worker_result=raw_worker_result,
    )


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _flatten_comments(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("comments payload must be an array")

    items: list[Mapping[str, object]] = []
    for page_or_comment in value:
        if isinstance(page_or_comment, Mapping):
            items.append(cast(Mapping[str, object], page_or_comment))
            continue
        if not isinstance(page_or_comment, Sequence) or isinstance(page_or_comment, (str, bytes)):
            raise ValueError("comments payload contains a malformed page")
        for comment in page_or_comment:
            if not isinstance(comment, Mapping):
                raise ValueError("comments payload contains a malformed comment")
            items.append(cast(Mapping[str, object], comment))
    return tuple(items)


def _app_slug(payload: Mapping[str, object]) -> str | None:
    app = _as_mapping(payload.get("performed_via_github_app"))
    slug = None if app is None else app.get("slug")
    return slug if isinstance(slug, str) else None


def _actor_login(payload: Mapping[str, object]) -> str | None:
    user = _as_mapping(payload.get("user"))
    login = None if user is None else user.get("login")
    return login if isinstance(login, str) else None


def _trusted_connector_comment(comment: Mapping[str, object], repository_owner: str) -> bool:
    return (
        _actor_login(comment) == repository_owner
        and _app_slug(comment) == _CHATGPT_CONNECTOR_APP_SLUG
    )


def _trusted_actions_comment(comment: Mapping[str, object]) -> bool:
    return (
        _actor_login(comment) == _GITHUB_ACTIONS_BOT_LOGIN
        and _app_slug(comment) == _GITHUB_ACTIONS_APP_SLUG
    )


def _comment_by_id(
    comments: tuple[Mapping[str, object], ...], comment_id: int
) -> Mapping[str, object] | None:
    matches = [comment for comment in comments if comment.get("id") == comment_id]
    if len(matches) != 1:
        return None
    return matches[0]


def plan_application(
    *,
    event: Mapping[str, object],
    comments_payload: object,
    configured_issue_number: int,
    repository: str,
    current_revision: str,
) -> ApplicationPlan:
    """Validate transport provenance/correlation before invoking the effect boundary."""

    if configured_issue_number <= 0:
        raise ValueError("configured check-in Issue must be positive")
    if "/" not in repository or not current_revision:
        raise ValueError("repository and current revision are required")

    issue = _as_mapping(event.get("issue"))
    event_comment = _as_mapping(event.get("comment"))
    if event.get("action") != "created" or issue is None or event_comment is None:
        return ApplicationPlan(False)
    if "pull_request" in issue or _positive_int(issue.get("number")) != configured_issue_number:
        return ApplicationPlan(False)

    body = event_comment.get("body")
    if not isinstance(body, str):
        return ApplicationPlan(False)
    request = parse_application_request(body)
    if request is None:
        return ApplicationPlan(False)

    repository_owner = repository.split("/", 1)[0]
    if not _trusted_connector_comment(event_comment, repository_owner):
        raise ValueError("EFFECT_REQUEST must originate from the configured ChatGPT connector")
    event_comment_id = _positive_int(event_comment.get("id"))
    if event_comment_id is None:
        raise ValueError("EFFECT_REQUEST event comment id is invalid")

    comments = _flatten_comments(comments_payload)
    observed_event_comment = _comment_by_id(comments, event_comment_id)
    if (
        observed_event_comment is None
        or observed_event_comment.get("body") != body
        or not _trusted_connector_comment(observed_event_comment, repository_owner)
    ):
        raise ValueError("EFFECT_REQUEST current comment observation is incomplete")

    dispatch_request_comment = _comment_by_id(comments, request.dispatch_request_comment_id)
    if dispatch_request_comment is None or not _trusted_connector_comment(
        dispatch_request_comment, repository_owner
    ):
        raise ValueError("correlated DISPATCH_REQUEST is missing or untrusted")
    dispatch_request_body = dispatch_request_comment.get("body")
    if (
        not isinstance(dispatch_request_body, str)
        or parse_dispatch_request(dispatch_request_body) is None
    ):
        raise ValueError("correlated DISPATCH_REQUEST is malformed")

    dispatch_decision_comment = _comment_by_id(comments, request.dispatch_decision_comment_id)
    if dispatch_decision_comment is None or not _trusted_actions_comment(dispatch_decision_comment):
        raise ValueError("correlated DISPATCH_DECISION is missing or untrusted")
    decision_body = dispatch_decision_comment.get("body")
    if not isinstance(decision_body, str):
        raise ValueError("correlated DISPATCH_DECISION body is missing")
    decision = parse_dispatch_decision(decision_body)
    if decision is None:
        raise ValueError("correlated DISPATCH_DECISION is malformed")
    if decision.request_comment_id != request.dispatch_request_comment_id:
        raise ValueError("DISPATCH_DECISION does not correlate to the requested dispatch")
    if decision.default_branch_revision != current_revision:
        raise ValueError("DISPATCH_DECISION revision is stale")
    if (
        decision.disposition != "AUTHORIZE"
        or decision.issue_number is None
        or decision.role is None
        or decision.action is None
    ):
        raise ValueError("EFFECT_REQUEST requires an AUTHORIZE dispatch decision")

    return ApplicationPlan(
        should_apply=True,
        source=WorkerRequest(
            issue_number=decision.issue_number,
            role=decision.role,
            action=decision.action,
            debt_disposition=decision.debt_disposition,
        ),
        raw_worker_result=request.raw_worker_result,
    )


def _load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    """Apply one correlated worker result through the existing repository effect boundary."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--comments-path", required=True)
    parser.add_argument("--check-in-issue", required=True, type=int)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    event = _load_json(args.event_path)
    if not isinstance(event, Mapping):
        raise RuntimeError("GitHub event payload must be an object")
    comments_payload = _load_json(args.comments_path)
    plan = plan_application(
        event=cast(Mapping[str, object], event),
        comments_payload=comments_payload,
        configured_issue_number=args.check_in_issue,
        repository=repository,
        current_revision=args.revision,
    )
    if not plan.should_apply:
        return 0
    if plan.source is None or plan.raw_worker_result is None:
        raise RuntimeError("application plan is missing validated source/result")

    workflow_text = Path("agents/workflow.md").read_text(encoding="utf-8")
    _, result = run_guarded_effect_application(
        plan.raw_worker_result,
        source=plan.source,
        repository=repository,
        token=token,
        workflow_text=workflow_text,
    )
    print(json.dumps({"applied": result.applied, "reason": result.reason}, sort_keys=True))
    return 0 if result.applied else 1


if __name__ == "__main__":
    raise SystemExit(main())
