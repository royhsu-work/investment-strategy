"""Run-scoped machine dispatch transport."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from investment_strategy.scheduled_agent_action_model import Action as ModelAction
from investment_strategy.scheduled_agent_action_model import role_for
from investment_strategy.scheduled_agent_checkin import is_runtime_checkin_issue
from investment_strategy.scheduled_agent_runtime import acquire_current_github_preflight
from investment_strategy.workflow_dispatch import DispatchDecision, classify_dispatch

REQUEST_MARKER = "DISPATCH_REQUEST"
REQUESTED_AT_PREFIX = "Requested-At: "
RUN_NAME_PREFIX = "Scheduled Agent Dispatch "
RUN_RESULT_START_MARKER = "BEGIN_SCHEDULED_AGENT_DISPATCH_RESULT"
RUN_RESULT_END_MARKER = "END_SCHEDULED_AGENT_DISPATCH_RESULT"
DECISION_MARKER = "DISPATCH_DECISION"
REQUEST_COMMENT_ID_PREFIX = "Request-Comment-ID: "
DEFAULT_BRANCH_REVISION_PREFIX = "Default-Branch-Revision: "
DISPOSITION_PREFIX = "Disposition: "
ISSUE_PREFIX = "Issue: "
ROLE_PREFIX = "Role: "
ACTION_PREFIX = "Action: "
REASON_PREFIX = "Reason: "
BRIDGE_OK = "BRIDGE_OK"
_DECISION_DISPOSITIONS = {"AUTHORIZE", "NO_WORK", "FAIL_CLOSED"}
_ROLES = {"lead", "reviewer", "executor"}
_MAX_REASON_LENGTH = 240


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


def render_dispatch_decision(
    *,
    request_comment_id: int,
    default_branch_revision: str,
    decision: DispatchDecision,
) -> str:
    if request_comment_id <= 0 or not default_branch_revision.strip():
        raise ValueError("dispatch result identity is invalid")
    if decision.disposition not in _DECISION_DISPOSITIONS:
        raise ValueError("unsupported dispatch disposition")
    lines = [
        DECISION_MARKER,
        f"{REQUEST_COMMENT_ID_PREFIX}{request_comment_id}",
        f"{DEFAULT_BRANCH_REVISION_PREFIX}{default_branch_revision}",
        f"{DISPOSITION_PREFIX}{decision.disposition}",
    ]
    if decision.disposition == "AUTHORIZE":
        if decision.selected_issue_id is None or decision.selected_routing is None:
            raise ValueError("AUTHORIZE requires one Action")
        role, action = decision.selected_routing
        lines.extend(
            (
                f"{ISSUE_PREFIX}{decision.selected_issue_id}",
                f"{ROLE_PREFIX}{role}",
                f"{ACTION_PREFIX}{action}",
            )
        )
        try:
            if role_for(ModelAction(action)).value != role:
                raise ValueError("dispatch role is not derived from Action")
        except ValueError as exc:
            raise ValueError("dispatch Action is invalid") from exc
    else:
        if decision.selected_issue_id is not None or decision.selected_routing is not None:
            raise ValueError("non-authorizing result carries selected work")
        if (
            len(decision.reason) == 0
            or decision.reason != decision.reason.strip()
            or "\n" in decision.reason
            or len(decision.reason) > _MAX_REASON_LENGTH
        ):
            raise ValueError("dispatch reason is invalid")
        lines.append(f"{REASON_PREFIX}{decision.reason}")
    return "\n".join(lines)


def render_run_scoped_dispatch_result(
    *,
    request_comment_id: int,
    default_branch_revision: str,
    decision: DispatchDecision,
) -> str:
    body = render_dispatch_decision(
        request_comment_id=request_comment_id,
        default_branch_revision=default_branch_revision,
        decision=decision,
    )
    return f"{RUN_RESULT_START_MARKER}\n{body}\n{RUN_RESULT_END_MARKER}"


def parse_run_scoped_dispatch_result(
    log: str,
    *,
    request_comment_id: int,
) -> MachineDispatchDecision | None:
    if request_comment_id <= 0:
        return None
    lines = log.splitlines()
    starts = [index for index, line in enumerate(lines) if line == RUN_RESULT_START_MARKER]
    ends = [index for index, line in enumerate(lines) if line == RUN_RESULT_END_MARKER]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        return None
    body = "\n".join(lines[starts[0] + 1 : ends[0]])
    decision = parse_dispatch_decision(body)
    if decision is None or decision.request_comment_id != request_comment_id:
        return None
    return decision


def parse_dispatch_decision(body: str) -> MachineDispatchDecision | None:
    lines = body.split("\n")
    if len(lines) not in {4, 5, 7} or lines[0] != DECISION_MARKER:
        return None
    if not lines[1].startswith(REQUEST_COMMENT_ID_PREFIX):
        return None
    raw_id = lines[1][len(REQUEST_COMMENT_ID_PREFIX) :]
    try:
        request_id = int(raw_id)
    except ValueError:
        return None
    if request_id <= 0 or str(request_id) != raw_id:
        return None
    if not lines[2].startswith(DEFAULT_BRANCH_REVISION_PREFIX):
        return None
    revision = lines[2][len(DEFAULT_BRANCH_REVISION_PREFIX) :]
    if not revision or revision != revision.strip():
        return None
    if not lines[3].startswith(DISPOSITION_PREFIX):
        return None
    disposition = lines[3][len(DISPOSITION_PREFIX) :]
    if disposition not in _DECISION_DISPOSITIONS:
        return None
    if disposition != "AUTHORIZE":
        if len(lines) not in {4, 5}:
            return None
        if len(lines) == 5 and (
            not lines[4].startswith(REASON_PREFIX)
            or not lines[4][len(REASON_PREFIX) :].strip()
            or len(lines[4][len(REASON_PREFIX) :]) > _MAX_REASON_LENGTH
        ):
            return None
        reason = None if len(lines) == 4 else lines[4][len(REASON_PREFIX) :]
        return MachineDispatchDecision(request_id, revision, disposition, reason=reason)

    if len(lines) != 7:
        return None
    if not lines[4].startswith(ISSUE_PREFIX):
        return None
    raw_issue = lines[4][len(ISSUE_PREFIX) :]
    try:
        issue_number = int(raw_issue)
    except ValueError:
        return None
    if issue_number <= 0 or str(issue_number) != raw_issue:
        return None
    if not lines[5].startswith(ROLE_PREFIX) or not lines[6].startswith(ACTION_PREFIX):
        return None
    role = lines[5][len(ROLE_PREFIX) :]
    action = lines[6][len(ACTION_PREFIX) :]
    if role not in _ROLES or not action or action != action.strip():
        return None
    try:
        parsed_action = ModelAction(action)
    except ValueError:
        return None
    if role_for(parsed_action).value != role:
        return None
    return MachineDispatchDecision(
        request_id,
        revision,
        disposition,
        issue_number=issue_number,
        role=role,
        action=action,
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
) -> BridgePlan:
    identity = _request_identity(event)
    if identity is None:
        return BridgePlan(False)
    issue_number, request_comment_id = identity
    return BridgePlan(
        should_emit=True,
        issue_number=issue_number,
        request_comment_id=request_comment_id,
        result_body=render_dispatch_decision(
            request_comment_id=request_comment_id,
            default_branch_revision=default_branch_revision,
            decision=decision,
        ),
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
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_result_payload(path: Path, plan: BridgePlan) -> None:
    if plan.should_emit and plan.result_body is not None:
        path.write_text(json.dumps({"body": plan.result_body}) + "\n", encoding="utf-8")


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
        plan = plan_dispatch_decision(
            event=event,
            default_branch_revision=args.revision,
            decision=acquire_production_dispatch_decision(repository, token),
        )
    _write_outputs(args.github_output, plan)
    _write_result_payload(args.result_payload, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
