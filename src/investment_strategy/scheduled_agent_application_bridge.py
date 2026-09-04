"""Run-scoped ingress for repository-owned Scheduled Agent effect application."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.request import Request, urlopen

from investment_strategy.issue_comment_bridge import MachineDispatchDecision
from investment_strategy.scheduled_agent_checkin import is_runtime_checkin_issue
from investment_strategy.scheduled_agent_dispatch_result import fetch_dispatch_result
from investment_strategy.scheduled_agent_merge_acceptance import run_guarded_effect_application
from investment_strategy.scheduled_agent_runtime import WorkerRequest


APPLICATION_REQUEST_MARKER = "EFFECT_REQUEST"
DISPATCH_REQUEST_COMMENT_ID_PREFIX = "Dispatch-Request-Comment-ID: "
DISPATCH_RUN_ID_PREFIX = "Dispatch-Run-ID: "
WORKER_RESULT_B64_PREFIX = "Worker-Result-B64: "
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"


@dataclass(frozen=True)
class ApplicationRequest:
    """One transport request bound to one exact prior machine dispatch run."""

    dispatch_request_comment_id: int
    dispatch_run_id: int
    raw_worker_result: str


@dataclass(frozen=True)
class ApplicationPlan:
    """Validated application input or an unrelated-comment no-op."""

    should_apply: bool
    source: WorkerRequest | None = None
    raw_worker_result: str | None = None
    effect_request_comment_id: int | None = None


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
    prefixes = (
        DISPATCH_REQUEST_COMMENT_ID_PREFIX,
        DISPATCH_RUN_ID_PREFIX,
        WORKER_RESULT_B64_PREFIX,
    )
    for line, prefix in zip(lines[1:], prefixes, strict=True):
        if not line.startswith(prefix):
            raise ValueError("EFFECT_REQUEST field order is invalid")

    request_comment_id = _positive_decimal(lines[1][len(prefixes[0]) :])
    dispatch_run_id = _positive_decimal(lines[2][len(prefixes[1]) :])
    encoded_result = lines[3][len(prefixes[2]) :]
    if request_comment_id is None or dispatch_run_id is None or not encoded_result:
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
        dispatch_run_id=dispatch_run_id,
        raw_worker_result=raw_worker_result,
    )


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


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


def plan_application(
    *,
    event: Mapping[str, object],
    request: ApplicationRequest,
    dispatch_result: MachineDispatchDecision,
    repository: str,
    current_revision: str,
) -> ApplicationPlan:
    """Validate event identity and one run-scoped dispatch result."""

    if "/" not in repository or not current_revision:
        raise ValueError("repository and current revision are required")
    issue = _as_mapping(event.get("issue"))
    event_comment = _as_mapping(event.get("comment"))
    if event.get("action") != "created" or issue is None or event_comment is None:
        return ApplicationPlan(False)
    if "pull_request" in issue or not is_runtime_checkin_issue(issue):
        return ApplicationPlan(False)

    body = event_comment.get("body")
    if not isinstance(body, str) or parse_application_request(body) != request:
        raise ValueError("EFFECT_REQUEST event body does not match parsed request")
    repository_owner = repository.split("/", 1)[0]
    if not _trusted_connector_comment(event_comment, repository_owner):
        raise ValueError("EFFECT_REQUEST must originate from the configured ChatGPT connector")
    event_comment_id = _positive_int(event_comment.get("id"))
    if event_comment_id is None:
        raise ValueError("EFFECT_REQUEST event comment id is invalid")
    if request.dispatch_request_comment_id != dispatch_result.request_comment_id:
        raise ValueError("EFFECT_REQUEST request does not match dispatch result")
    if dispatch_result.default_branch_revision != current_revision:
        raise ValueError("DISPATCH_DECISION revision is stale")
    if (
        dispatch_result.disposition != "AUTHORIZE"
        or dispatch_result.issue_number is None
        or dispatch_result.role is None
        or dispatch_result.action is None
    ):
        raise ValueError("EFFECT_REQUEST requires an AUTHORIZE dispatch result")

    return ApplicationPlan(
        should_apply=True,
        source=WorkerRequest(
            issue_number=dispatch_result.issue_number,
            role=dispatch_result.role,
            action=dispatch_result.action,
        ),
        raw_worker_result=request.raw_worker_result,
        effect_request_comment_id=event_comment_id,
    )


def _github_json(repository: str, token: str, api_path: str) -> object:
    request = Request(
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        return json.loads(response.read().decode("utf-8"))


def _fresh_event_observation(
    event: Mapping[str, object],
    body: str,
    repository: str,
    token: str,
) -> tuple[int, int]:
    issue = _as_mapping(event.get("issue"))
    comment = _as_mapping(event.get("comment"))
    if event.get("action") != "created" or issue is None or comment is None:
        raise ValueError("application request event is invalid")
    if "pull_request" in issue or not is_runtime_checkin_issue(issue):
        raise ValueError("application request event is not a control shard comment")

    comment_id = _positive_int(comment.get("id"))
    issue_number = _positive_int(issue.get("number"))
    owner = repository.split("/", 1)[0] if "/" in repository else ""
    if (
        comment_id is None
        or issue_number is None
        or comment.get("body") != body
        or not _trusted_connector_comment(comment, owner)
    ):
        raise ValueError("application request event identity is invalid")

    observed_comment = _as_mapping(
        _github_json(repository, token, f"issues/comments/{comment_id}")
    )
    if (
        observed_comment is None
        or observed_comment.get("id") != comment_id
        or observed_comment.get("body") != body
        or not _trusted_connector_comment(observed_comment, owner)
    ):
        raise ValueError("application request current comment observation is incomplete")

    observed_issue = _as_mapping(_github_json(repository, token, f"issues/{issue_number}"))
    if (
        observed_issue is None
        or observed_issue.get("number") != issue_number
        or not is_runtime_checkin_issue(observed_issue)
    ):
        raise ValueError("application request current shard observation is invalid")
    return comment_id, issue_number


def _load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    """Apply one structured worker result through the write-authorized boundary."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    event = _as_mapping(_load_json(args.event_path))
    if event is None:
        raise RuntimeError("GitHub event payload must be an object")
    event_comment = _as_mapping(event.get("comment"))
    body = None if event_comment is None else event_comment.get("body")
    if not isinstance(body, str):
        return 0
    request = parse_application_request(body)
    if request is None:
        return 0

    _fresh_event_observation(event, body, repository, token)
    dispatch_result = fetch_dispatch_result(
        repository,
        token,
        request_comment_id=request.dispatch_request_comment_id,
        run_id=request.dispatch_run_id,
        current_revision=args.revision,
    )
    plan = plan_application(
        event=event,
        request=request,
        dispatch_result=dispatch_result,
        repository=repository,
        current_revision=args.revision,
    )
    if not plan.should_apply:
        return 0
    if (
        plan.source is None
        or plan.raw_worker_result is None
        or plan.effect_request_comment_id is None
    ):
        raise RuntimeError("application plan is missing validated source/result identity")

    batch, result = run_guarded_effect_application(
        plan.raw_worker_result,
        source=plan.source,
        repository=repository,
        token=token,
        current_revision=args.revision,
    )
    print(
        json.dumps(
            {
                "applied": result.applied,
                "reason": result.reason,
                "effects": len(batch.effects),
                "effect_request_comment_id": plan.effect_request_comment_id,
            },
            sort_keys=True,
        )
    )
    return 0 if result.applied else 1


if __name__ == "__main__":
    raise SystemExit(main())
