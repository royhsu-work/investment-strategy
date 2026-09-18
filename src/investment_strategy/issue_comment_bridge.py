"""Run-scoped machine dispatch transport."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_action_model import Action as ModelAction
from investment_strategy.scheduled_agent_action_model import next_action, role_for
from investment_strategy.scheduled_agent_application_bridge import parse_application_request
from investment_strategy.scheduled_agent_checkin import is_runtime_checkin_issue
from investment_strategy.scheduled_agent_effects import (
    ApplicationDecisionRecord,
    ApplicationOutcomeRecord,
    parse_application_decision,
    parse_application_outcome,
)
from investment_strategy.scheduled_agent_formal_qualification import (
    build_qualification_input,
    qualify_current_formal_consequence,
)
from investment_strategy.scheduled_agent_formal_result import parse_formal_result
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    acquire_current_github_preflight,
    is_github_actions_comment,
    normalize_github_issue,
)
from investment_strategy.scheduled_agent_worker import (
    WorkerActionResult,
    parse_worker_result,
)
from investment_strategy.workflow_dispatch import (
    DispatchDecision,
    DispatchPreflight,
    classify_dispatch,
)

REQUEST_MARKER = "DISPATCH_REQUEST"
REQUESTED_AT_PREFIX = "Requested-At: "
RUN_NAME_PREFIX = "Scheduled Agent Dispatch "
APPLICATION_RUN_NAME_PREFIX = "Scheduled Agent Application "
DISPATCH_RESULT_SCHEMA = "scheduled-agent-dispatch-result/v1"
_APPLICATION_WORKFLOW = "scheduled-agent-application.yml"
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"
_FORMAL_RESULT_MARKERS = frozenset({"ACTION_RESULT", "REVIEW_RESULT", "MERGE_RESULT"})
_DECISION_DISPOSITIONS = {"AUTHORIZE", "NO_WORK", "FAIL_CLOSED"}
_MAX_REASON_LENGTH = 240
_MAX_RESULT_BYTES = 16_384
_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class DispatchRequest:
    requested_at: str


@dataclass(frozen=True)
class MachineDispatchDecision:
    request_comment_id: int
    default_branch_revision: str
    disposition: str
    issue_number: int | None = None
    role: str | None = None
    action: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class BridgePlan:
    should_emit: bool
    issue_number: int | None = None
    request_comment_id: int | None = None
    result_body: str | None = None
    application_resume_job_id: int | None = None


@dataclass(frozen=True)
class ApplicationCompletion:
    state: Literal["NONE", "REJECTED", "RESUMABLE", "COMPLETE", "ABORTED", "INVALID", "AMBIGUOUS"]
    reason: str
    request_comment_id: int | None = None
    job_id: int | None = None


GitHubReader = Callable[[str, str, str], object | None]


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _valid_reason(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and "\n" not in value
        and len(value) <= _MAX_REASON_LENGTH
    )


def parse_dispatch_request(body: str) -> DispatchRequest | None:
    lines = body.split("\n")
    if len(lines) != 2 or lines[0] != REQUEST_MARKER:
        return None
    if not lines[1].startswith(REQUESTED_AT_PREFIX):
        return None
    requested_at = lines[1][len(REQUESTED_AT_PREFIX) :]
    if not requested_at or requested_at != requested_at.strip():
        return None
    if body != f"{REQUEST_MARKER}\n{REQUESTED_AT_PREFIX}{requested_at}":
        return None
    return DispatchRequest(requested_at=requested_at)


def render_dispatch_run_name(request_comment_id: int) -> str:
    if request_comment_id <= 0:
        raise ValueError("request_comment_id must be positive")
    return f"{RUN_NAME_PREFIX}{request_comment_id}"


def parse_dispatch_run_name(run_name: str) -> int | None:
    if not run_name.startswith(RUN_NAME_PREFIX):
        return None
    raw = run_name[len(RUN_NAME_PREFIX) :]
    try:
        parsed = int(raw)
    except ValueError:
        return None
    return parsed if parsed > 0 and str(parsed) == raw else None


def render_application_run_name(request_comment_id: int) -> str:
    if request_comment_id <= 0:
        raise ValueError("request_comment_id must be positive")
    return f"{APPLICATION_RUN_NAME_PREFIX}{request_comment_id}"


def parse_application_run_name(run_name: str) -> int | None:
    if not run_name.startswith(APPLICATION_RUN_NAME_PREFIX):
        return None
    raw = run_name[len(APPLICATION_RUN_NAME_PREFIX) :]
    try:
        parsed = int(raw)
    except ValueError:
        return None
    return parsed if parsed > 0 and str(parsed) == raw else None


def _github_json(repository: str, token: str, api_path: str) -> object | None:
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        raw = response.read()
    return None if not raw else json.loads(raw.decode("utf-8"))


def _paged_list(
    repository: str,
    token: str,
    api_path: str,
    *,
    read: GitHubReader,
) -> tuple[Mapping[str, object], ...]:
    items: list[Mapping[str, object]] = []
    page = 1
    separator = "&" if "?" in api_path else "?"
    while True:
        payload = read(repository, token, f"{api_path}{separator}per_page=100&page={page}")
        if not isinstance(payload, list):
            raise RuntimeError("application completion evidence list is incomplete")
        for raw in payload:
            if not isinstance(raw, Mapping):
                raise RuntimeError("application completion evidence list is malformed")
            items.append(cast(Mapping[str, object], raw))
        if len(payload) < 100:
            return tuple(items)
        page += 1


def _comment_time(comment: Mapping[str, object]) -> str | None:
    value = comment.get("created_at")
    return value if isinstance(value, str) and value else None


def _trusted_connector_comment(comment: Mapping[str, object], owner: str) -> bool:
    user = comment.get("user")
    app = comment.get("performed_via_github_app")
    return (
        isinstance(user, Mapping)
        and user.get("login") == owner
        and isinstance(app, Mapping)
        and app.get("slug") == _CHATGPT_CONNECTOR_APP_SLUG
    )


def _completion_source(
    preflight: DispatchPreflight,
    decision: DispatchDecision,
) -> WorkerRequest | None:
    if (
        decision.disposition == "AUTHORIZE"
        and decision.selected_issue_id is not None
        and decision.selected_routing is not None
    ):
        role, action = decision.selected_routing
        return WorkerRequest(decision.selected_issue_id, role, action)
    if (
        decision.disposition != "FAIL_CLOSED"
        or decision.reason != "observations-unqualified"
        or preflight.human_authorized is not True
        or preflight.enumeration.incomplete_results
        or not preflight.enumeration.exhausted
        or preflight.enumeration.source_total_count is None
        or preflight.enumeration.observed_count != preflight.enumeration.source_total_count
    ):
        return None

    routed = tuple(
        issue for issue in preflight.issues if issue.state == "open" and issue.routing is not None
    )
    formal = tuple(issue for issue in routed if issue.change not in {"", "unset"})
    if len(formal) > 1:
        return None
    if formal:
        issue = formal[0]
    elif routed:
        issue = min(routed, key=lambda item: (item.created_order, item.issue_number))
    else:
        return None
    routing = issue.routing
    if routing is None:
        return None
    role, action = routing
    return WorkerRequest(issue.issue_number, role, action)


def _formal_result_records(
    comments: tuple[Mapping[str, object], ...],
) -> tuple[tuple[str, str], ...]:
    records: list[tuple[str, str]] = []
    for comment in comments:
        if not is_github_actions_comment(comment):
            continue
        body = comment.get("body")
        created_at = _comment_time(comment)
        if not isinstance(body, str) or created_at is None:
            continue
        marker = body.splitlines()[:1]
        if not marker or marker[0].removeprefix("## ").strip() not in _FORMAL_RESULT_MARKERS:
            continue
        records.append((created_at, body))
    return tuple(records)


def _application_job(
    repository: str,
    token: str,
    request_comment_id: int,
    *,
    read: GitHubReader,
) -> ApplicationCompletion:
    """Locate the one exact application run for an accepted intent."""

    title = render_application_run_name(request_comment_id)
    page = 1
    matches: list[Mapping[str, object]] = []
    while True:
        query = urlencode({"event": "issue_comment", "per_page": 100, "page": page})
        payload = read(
            repository,
            token,
            f"actions/workflows/{quote(_APPLICATION_WORKFLOW, safe='')}/runs?{query}",
        )
        if not isinstance(payload, Mapping):
            return ApplicationCompletion("INVALID", "application-completion-run-list-incomplete")
        raw_runs = payload.get("workflow_runs")
        if not isinstance(raw_runs, list):
            return ApplicationCompletion("INVALID", "application-completion-run-list-incomplete")
        for raw in raw_runs:
            if isinstance(raw, Mapping) and raw.get("display_title") == title:
                matches.append(cast(Mapping[str, object], raw))
        if matches or len(raw_runs) < 100:
            break
        page += 1

    if len(matches) != 1:
        reason = (
            "application-completion-run-unavailable"
            if not matches
            else "application-completion-run-ambiguous"
        )
        return ApplicationCompletion("INVALID", reason, request_comment_id=request_comment_id)

    run = matches[0]
    run_id = _positive_int(run.get("id"))
    run_attempt = _positive_int(run.get("run_attempt"))
    if run_id is None or run_attempt is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-run-identity-incomplete",
            request_comment_id=request_comment_id,
        )
    if run.get("status") != "completed":
        return ApplicationCompletion(
            "RESUMABLE",
            "application-completion-in-progress",
            request_comment_id=request_comment_id,
        )
    if run_attempt >= 50:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-rerun-limit",
            request_comment_id=request_comment_id,
        )

    jobs_payload = read(repository, token, f"actions/runs/{run_id}/jobs")
    if not isinstance(jobs_payload, Mapping) or not isinstance(jobs_payload.get("jobs"), list):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-job-list-incomplete",
            request_comment_id=request_comment_id,
        )
    jobs = [
        item
        for item in cast(list[object], jobs_payload["jobs"])
        if isinstance(item, Mapping) and item.get("name") == "apply"
    ]
    if len(jobs) != 1:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-job-identity-ambiguous",
            request_comment_id=request_comment_id,
        )
    job_id = _positive_int(cast(Mapping[str, object], jobs[0]).get("id"))
    if job_id is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-job-identity-incomplete",
            request_comment_id=request_comment_id,
        )
    return ApplicationCompletion(
        "RESUMABLE",
        "application-completion-resuming",
        request_comment_id=request_comment_id,
        job_id=job_id,
    )


def _application_decisions(
    comments: tuple[Mapping[str, object], ...],
) -> tuple[ApplicationDecisionRecord, ...]:
    return tuple(
        record
        for comment in comments
        if is_github_actions_comment(comment)
        for record in (parse_application_decision(comment.get("body")),)
        if record is not None
    )


def _application_outcomes(
    comments: tuple[Mapping[str, object], ...],
) -> tuple[ApplicationOutcomeRecord, ...]:
    return tuple(
        record
        for comment in comments
        if is_github_actions_comment(comment)
        for record in (parse_application_outcome(comment.get("body")),)
        if record is not None
    )


def _application_worker_for_record(
    record: ApplicationDecisionRecord,
    source: WorkerRequest,
) -> WorkerActionResult | None:
    """Validate the immutable intent payload against its decision metadata."""

    if (
        record.issue_number != source.issue_number
        or record.role != source.role
        or record.action != source.action
        or record.disposition not in {"ACCEPTED", "REJECTED"}
    ):
        return None
    try:
        worker = parse_worker_result(record.raw_worker_result, source)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.worker_result_sha256
        != hashlib.sha256(record.raw_worker_result.encode("utf-8")).hexdigest()
        or worker.change != record.change
        or worker.typed_result.result.kind.value != record.result_kind
        or worker.typed_result.action.value != source.action
    ):
        return None
    return worker


def _authorization_ancestry(
    repository: str,
    token: str,
    *,
    authorization_revision: str,
    current_revision: str,
    read: GitHubReader,
) -> tuple[tuple[str, str], ...] | None:
    if authorization_revision == current_revision:
        return ()
    comparison = read(
        repository,
        token,
        f"compare/{authorization_revision}...{current_revision}",
    )
    base_commit = comparison.get("base_commit") if isinstance(comparison, Mapping) else None
    if (
        not isinstance(comparison, Mapping)
        or comparison.get("status") != "ahead"
        or not isinstance(base_commit, Mapping)
        or base_commit.get("sha") != authorization_revision
    ):
        return None
    return ((authorization_revision, current_revision),)


def _formal_consequence(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    record: ApplicationDecisionRecord,
    worker: WorkerActionResult,
    issue_comments: tuple[Mapping[str, object], ...],
    lifecycle_events: tuple[Mapping[str, object], ...],
    current_issue: Mapping[str, object],
    current_revision: str,
    read: GitHubReader,
    mode: Literal["current", "pending"],
    authorization_ancestry: tuple[tuple[str, str], ...],
) -> bool:
    observation = normalize_github_issue(current_issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != source.issue_number
        or observation.state not in {"open", "closed"}
        or observation.change == ""
    ):
        return False
    try:
        successor = next_action(worker.typed_result.action, worker.typed_result.result)
    except (TypeError, ValueError):
        return False
    expected_terminal = successor is None
    expected_routing = None if successor is None else (role_for(successor).value, successor.value)
    effective_change: str | None = record.change
    if effective_change == "unset" and observation.change != "unset":
        effective_change = observation.change
    prefix = f"application:{record.request_comment_id}:{source.issue_number}:"
    matching_comments: list[Mapping[str, object]] = []
    matching_events = []
    for comment in issue_comments:
        event = parse_formal_result(comment, current_revision=current_revision)
        if (
            event is not None
            and event.valid
            and event.issue_number == source.issue_number
            and event.role == source.role
            and event.action == source.action
            and event.result_kind == record.result_kind
            and (
                (effective_change is None or effective_change == "unset")
                and event.change not in {"", "unset"}
                or event.change == effective_change
            )
            and event.application_correlation is not None
            and event.application_correlation.startswith(prefix)
        ):
            matching_comments.append(comment)
            matching_events.append(event)
    if len(matching_comments) > 1:
        return False
    if not matching_comments or len(matching_events) != 1:
        return False
    if effective_change in {None, "unset"}:
        effective_change = matching_events[0].change

    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=effective_change,
        state=observation.state,
        current_routing=observation.routing,
        comments=matching_comments,
        current_revision=current_revision,
        mode=mode,
        expected_routing=expected_routing,
        expected_terminal=expected_terminal,
        source_routing=(source.role, source.action),
        expected_result_kind=record.result_kind,
        expected_application_correlation=(
            matching_events[0].application_correlation if mode == "pending" else None
        ),
        lifecycle_events=lifecycle_events,
        authorization_ancestry=authorization_ancestry,
    )
    return qualify_current_formal_consequence(qualification).qualified


def _accepted_application_state(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    record: ApplicationDecisionRecord,
    outcome: ApplicationOutcomeRecord | None,
    issue_comments: tuple[Mapping[str, object], ...],
    lifecycle_events: tuple[Mapping[str, object], ...],
    current_issue: Mapping[str, object],
    current_revision: str,
    read: GitHubReader,
) -> ApplicationCompletion:
    worker = _application_worker_for_record(record, source)
    if worker is None or record.disposition != "ACCEPTED":
        return ApplicationCompletion(
            "INVALID",
            "application-completion-accepted-intent-invalid",
            request_comment_id=record.request_comment_id,
        )
    if outcome is not None:
        if (
            outcome.request_comment_id != record.request_comment_id
            or outcome.request_body_sha256 != record.request_body_sha256
            or outcome.authorization_revision != record.authorization_revision
            or outcome.issue_number != record.issue_number
            or outcome.role != record.role
            or outcome.action != record.action
            or outcome.change != record.change
            or outcome.result_kind != record.result_kind
            or outcome.worker_result_sha256 != record.worker_result_sha256
        ):
            return ApplicationCompletion(
                "INVALID",
                "application-completion-outcome-identity-invalid",
                request_comment_id=record.request_comment_id,
            )
        if outcome.outcome == "ABORTED":
            return ApplicationCompletion(
                "ABORTED",
                "application-completion-aborted",
                request_comment_id=record.request_comment_id,
            )
        ancestry = _authorization_ancestry(
            repository,
            token,
            authorization_revision=record.authorization_revision,
            current_revision=current_revision,
            read=read,
        )
        if ancestry is None:
            return ApplicationCompletion(
                "INVALID",
                "application-completion-stale",
                request_comment_id=record.request_comment_id,
            )
        if not _formal_consequence(
            repository=repository,
            token=token,
            source=source,
            record=record,
            worker=worker,
            issue_comments=issue_comments,
            lifecycle_events=lifecycle_events,
            current_issue=current_issue,
            current_revision=current_revision,
            read=read,
            mode="current",
            authorization_ancestry=ancestry,
        ):
            if _formal_consequence(
                repository=repository,
                token=token,
                source=source,
                record=record,
                worker=worker,
                issue_comments=issue_comments,
                lifecycle_events=lifecycle_events,
                current_issue=current_issue,
                current_revision=current_revision,
                read=read,
                mode="pending",
                authorization_ancestry=ancestry,
            ):
                return ApplicationCompletion(
                    "RESUMABLE",
                    "application-completion-outcome-pending",
                    request_comment_id=record.request_comment_id,
                )
            return ApplicationCompletion(
                "INVALID",
                "application-completion-complete-postcondition-invalid",
                request_comment_id=record.request_comment_id,
            )
        return ApplicationCompletion(
            "COMPLETE",
            "application-completion-complete",
            request_comment_id=record.request_comment_id,
        )

    ancestry = _authorization_ancestry(
        repository,
        token,
        authorization_revision=record.authorization_revision,
        current_revision=current_revision,
        read=read,
    )
    if ancestry is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-stale",
            request_comment_id=record.request_comment_id,
        )
    observation = normalize_github_issue(current_issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != source.issue_number
        or observation.change not in {record.change, "unset"}
        or observation.state not in {"open", "closed"}
    ):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-current-issue-invalid",
            request_comment_id=record.request_comment_id,
        )
    try:
        successor = next_action(worker.typed_result.action, worker.typed_result.result)
    except (TypeError, ValueError):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-result-transition-invalid",
            request_comment_id=record.request_comment_id,
        )
    expected_routing = None if successor is None else (role_for(successor).value, successor.value)
    if observation.state == "closed":
        return ApplicationCompletion(
            "INVALID",
            "application-completion-routing-without-formal",
            request_comment_id=record.request_comment_id,
        )
    if observation.routing == (source.role, source.action):
        return _application_job(
            repository,
            token,
            record.request_comment_id,
            read=read,
        )
    if successor is not None and observation.routing == expected_routing:
        return ApplicationCompletion(
            "RESUMABLE",
            "application-completion-outcome-pending",
            request_comment_id=record.request_comment_id,
        )
    return ApplicationCompletion(
        "INVALID",
        "application-completion-current-routing-invalid",
        request_comment_id=record.request_comment_id,
    )


def qualify_application_completion(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    current_revision: str,
    read: GitHubReader = _github_json,
    now: datetime | None = None,
) -> ApplicationCompletion:
    """Return one exhaustive consequence disposition from durable evidence."""

    current_time = datetime.now(UTC) if now is None else now.astimezone(UTC)
    owner = repository.split("/", 1)[0]
    since = (current_time - timedelta(days=30)).isoformat(timespec="seconds").replace("+00:00", "Z")
    recent = _paged_list(
        repository,
        token,
        f"issues/comments?{urlencode({'sort': 'created', 'direction': 'asc', 'since': since})}",
        read=read,
    )
    issue_comments = _paged_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created&direction=asc",
        read=read,
    )
    decisions = _application_decisions(issue_comments)
    outcomes = _application_outcomes(issue_comments)
    relevant_decisions = [
        record
        for record in decisions
        if record.issue_number == source.issue_number
        and record.role == source.role
        and record.action == source.action
    ]
    grouped_outcomes: dict[int, list[ApplicationOutcomeRecord]] = {}
    for outcome_record in outcomes:
        if outcome_record.request_comment_id > 0:
            grouped_outcomes.setdefault(outcome_record.request_comment_id, []).append(
                outcome_record
            )

    malformed_request = False
    request_ids: set[int] = set()
    for comment in recent:
        if not _trusted_connector_comment(comment, owner):
            continue
        body = comment.get("body")
        if not isinstance(body, str):
            continue
        if body.splitlines()[:1] != ["EFFECT_REQUEST"]:
            continue
        comment_id = _positive_int(comment.get("id"))
        if comment_id is None:
            malformed_request = True
            continue
        try:
            request = parse_application_request(body)
            if request is None:
                malformed_request = True
                continue
            decoded = json.loads(request.raw_worker_result)
            if not isinstance(decoded, Mapping):
                malformed_request = True
                continue
            candidate = WorkerRequest(
                cast(int, decoded.get("issue_number")),
                cast(str, decoded.get("role")),
                cast(str, decoded.get("action")),
            )
            if candidate == source:
                request_ids.add(comment_id)
        except (TypeError, ValueError, json.JSONDecodeError):
            malformed_request = True

    if malformed_request:
        return ApplicationCompletion("INVALID", "application-completion-request-invalid")

    # Every accepted/rejected record is exact evidence. Multiple accepted
    # records for one current source are competing intents, even if payloads
    # compare equal.
    accepted = [record for record in relevant_decisions if record.disposition == "ACCEPTED"]
    rejected = [record for record in relevant_decisions if record.disposition == "REJECTED"]
    if len(accepted) > 1:
        return ApplicationCompletion("AMBIGUOUS", "application-completion-accepted-ambiguous")
    if len(accepted) == 0:
        if rejected:
            return ApplicationCompletion("REJECTED", "application-completion-rejected")
        if request_ids:
            # A valid exact request with no durable Phase-A decision never crossed
            # the acceptance linearization point. It is invalid to resume it.
            return ApplicationCompletion("INVALID", "application-completion-acceptance-missing")
        return ApplicationCompletion("NONE", "application-completion-none")

    record = accepted[0]
    if request_ids and any(request_id != record.request_comment_id for request_id in request_ids):
        return ApplicationCompletion(
            "AMBIGUOUS",
            "application-completion-request-binding-ambiguous",
        )
    outcome_matches = grouped_outcomes.get(record.request_comment_id, [])
    if len(outcome_matches) > 1:
        return ApplicationCompletion("AMBIGUOUS", "application-completion-outcome-ambiguous")

    issue = read(repository, token, f"issues/{source.issue_number}")
    if not isinstance(issue, Mapping):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-current-issue-unavailable",
            request_comment_id=record.request_comment_id,
        )
    lifecycle = (
        _paged_list(
            repository,
            token,
            f"issues/{source.issue_number}/timeline",
            read=read,
        )
        if outcome_matches
        else ()
    )
    return _accepted_application_state(
        repository=repository,
        token=token,
        source=source,
        record=record,
        outcome=outcome_matches[0] if outcome_matches else None,
        issue_comments=issue_comments,
        lifecycle_events=lifecycle,
        current_issue=cast(Mapping[str, object], issue),
        current_revision=current_revision,
        read=read,
    )


def render_dispatch_result_document(
    *,
    request_comment_id: int,
    default_branch_revision: str,
    decision: DispatchDecision,
) -> str:
    """Render the one canonical plaintext JSON result owned by an exact bridge run."""

    if request_comment_id <= 0 or _SHA.fullmatch(default_branch_revision) is None:
        raise ValueError("dispatch result identity is invalid")
    if decision.disposition not in _DECISION_DISPOSITIONS:
        raise ValueError("unsupported dispatch disposition")

    payload: dict[str, object] = {
        "schema": DISPATCH_RESULT_SCHEMA,
        "request_comment_id": request_comment_id,
        "default_branch_revision": default_branch_revision,
        "disposition": decision.disposition,
    }
    if decision.disposition == "AUTHORIZE":
        issue_number = decision.selected_issue_id
        if (
            isinstance(issue_number, bool)
            or not isinstance(issue_number, int)
            or issue_number <= 0
            or decision.selected_routing is None
        ):
            raise ValueError("AUTHORIZE requires one Issue and Action")
        role, action = decision.selected_routing
        try:
            parsed_action = ModelAction(action)
        except ValueError as exc:
            raise ValueError("dispatch Action is invalid") from exc
        if role_for(parsed_action).value != role:
            raise ValueError("dispatch role is not derived from Action")
        payload.update({"issue_number": issue_number, "action": action})
    else:
        if decision.selected_issue_id is not None or decision.selected_routing is not None:
            raise ValueError("non-authorizing result carries selected work")
        if not _valid_reason(decision.reason):
            raise ValueError("dispatch reason is invalid")
        payload["reason"] = decision.reason

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def parse_dispatch_result_document(raw: bytes | str) -> MachineDispatchDecision:
    """Strictly parse the canonical plaintext JSON dispatch-result contract."""

    if isinstance(raw, bytes):
        if not raw or len(raw) > _MAX_RESULT_BYTES:
            raise RuntimeError("exact dispatch result artifact size is invalid")
        try:
            document = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("exact dispatch result artifact is not UTF-8 JSON") from exc
    else:
        encoded = raw.encode("utf-8")
        if not encoded or len(encoded) > _MAX_RESULT_BYTES:
            raise RuntimeError("exact dispatch result artifact size is invalid")
        document = raw

    try:
        decoded = json.loads(document)
    except json.JSONDecodeError as exc:
        raise RuntimeError("exact dispatch result artifact is not UTF-8 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise RuntimeError("exact dispatch result artifact must be a JSON object")
    payload = cast(Mapping[str, object], decoded)

    disposition = payload.get("disposition")
    if disposition not in _DECISION_DISPOSITIONS:
        raise RuntimeError("exact dispatch result disposition is invalid")
    common_keys = {
        "schema",
        "request_comment_id",
        "default_branch_revision",
        "disposition",
    }
    expected_keys = (
        common_keys | {"issue_number", "action"}
        if disposition == "AUTHORIZE"
        else common_keys | {"reason"}
    )
    if set(payload) != expected_keys or payload.get("schema") != DISPATCH_RESULT_SCHEMA:
        raise RuntimeError("exact dispatch result schema is invalid")

    request_comment_id = _positive_int(payload.get("request_comment_id"))
    revision = payload.get("default_branch_revision")
    if (
        request_comment_id is None
        or not isinstance(revision, str)
        or _SHA.fullmatch(revision) is None
    ):
        raise RuntimeError("exact dispatch result identity is invalid")

    if disposition == "AUTHORIZE":
        issue_number = _positive_int(payload.get("issue_number"))
        action = payload.get("action")
        if issue_number is None or not isinstance(action, str):
            raise RuntimeError("AUTHORIZE dispatch result is incomplete")
        try:
            parsed_action = ModelAction(action)
        except ValueError as exc:
            raise RuntimeError("AUTHORIZE dispatch Action is invalid") from exc
        return MachineDispatchDecision(
            request_comment_id=request_comment_id,
            default_branch_revision=revision,
            disposition=disposition,
            issue_number=issue_number,
            role=role_for(parsed_action).value,
            action=action,
        )

    reason = payload.get("reason")
    if not _valid_reason(reason):
        raise RuntimeError("non-authorizing dispatch reason is invalid")
    return MachineDispatchDecision(
        request_comment_id=request_comment_id,
        default_branch_revision=revision,
        disposition=disposition,
        reason=cast(str, reason),
    )


def _request_identity(event: Mapping[str, object]) -> tuple[int, int] | None:
    if event.get("action") != "created":
        return None
    issue = event.get("issue")
    comment = event.get("comment")
    if not isinstance(issue, Mapping) or not isinstance(comment, Mapping):
        return None
    if "pull_request" in issue or not is_runtime_checkin_issue(cast(Mapping[str, object], issue)):
        return None
    issue_number = issue.get("number")
    comment_id = comment.get("id")
    body = comment.get("body")
    if (
        not isinstance(issue_number, int)
        or isinstance(issue_number, bool)
        or issue_number <= 0
        or not isinstance(comment_id, int)
        or isinstance(comment_id, bool)
        or comment_id <= 0
        or not isinstance(body, str)
        or parse_dispatch_request(body) is None
    ):
        return None
    return issue_number, comment_id


def plan_dispatch_decision(
    *,
    event: Mapping[str, object],
    default_branch_revision: str,
    decision: DispatchDecision,
    application_resume_job_id: int | None = None,
) -> BridgePlan:
    identity = _request_identity(event)
    if identity is None:
        return BridgePlan(False)
    issue_number, request_comment_id = identity
    return BridgePlan(
        should_emit=True,
        issue_number=issue_number,
        request_comment_id=request_comment_id,
        result_body=render_dispatch_result_document(
            request_comment_id=request_comment_id,
            default_branch_revision=default_branch_revision,
            decision=decision,
        ),
        application_resume_job_id=application_resume_job_id,
    )


def acquire_production_dispatch_decision(repository: str, token: str) -> DispatchDecision:
    return classify_dispatch(acquire_current_github_preflight(repository, token))


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a JSON object")
    return cast(Mapping[str, object], value)


def _write_outputs(path: Path, plan: BridgePlan) -> None:
    lines = [f"should_emit={'true' if plan.should_emit else 'false'}"]
    if plan.issue_number is not None:
        lines.append(f"issue_number={plan.issue_number}")
    if plan.request_comment_id is not None:
        lines.append(f"request_comment_id={plan.request_comment_id}")
    if plan.application_resume_job_id is not None:
        lines.append(f"application_resume_job_id={plan.application_resume_job_id}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_result_payload(path: Path, plan: BridgePlan) -> None:
    if plan.should_emit and plan.result_body is not None:
        path.write_text(plan.result_body + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan one run-scoped dispatch result")
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    parser.add_argument("--result-payload", type=Path, required=True)
    args = parser.parse_args()

    event = _require_mapping(json.loads(args.event_path.read_text(encoding="utf-8")), "event")
    identity = _request_identity(event)
    if identity is None:
        plan = BridgePlan(False)
    else:
        repository = os.environ.get("GITHUB_REPOSITORY")
        token = os.environ.get("GITHUB_TOKEN")
        if not repository or not token:
            raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
        preflight = acquire_current_github_preflight(repository, token)
        decision = classify_dispatch(preflight)
        source = _completion_source(preflight, decision)
        completion = (
            ApplicationCompletion("NONE", "application-completion-none")
            if source is None
            else qualify_application_completion(
                repository,
                token,
                source=source,
                current_revision=args.revision,
            )
        )
        resume_job_id = None
        if completion.state in {"RESUMABLE", "INVALID", "AMBIGUOUS"}:
            decision = replace(
                decision,
                selected_issue_id=None,
                selected_routing=None,
                disposition="FAIL_CLOSED",
                reason=completion.reason,
            )
            resume_job_id = completion.job_id
        plan = plan_dispatch_decision(
            event=event,
            default_branch_revision=args.revision,
            decision=decision,
            application_resume_job_id=resume_job_id,
        )
    _write_outputs(args.github_output, plan)
    _write_result_payload(args.result_payload, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
