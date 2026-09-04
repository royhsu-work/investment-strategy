from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

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
DEBT_DISPOSITION_PREFIX = "Debt-Disposition: "
REASON_PREFIX = "Reason: "
BRIDGE_OK = "BRIDGE_OK"
_DECISION_DISPOSITIONS = {"AUTHORIZE", "NO_WORK", "FAIL_CLOSED"}
_DEBT_DISPOSITIONS = {"terminal-cleanup", "unfinished-recovery"}
_ROLES = {"lead", "reviewer", "executor"}
_GITHUB_ACTIONS_BOT_LOGIN = "github-actions[bot]"
_GITHUB_ACTIONS_APP_SLUG = "github-actions"
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
    debt_disposition: str | None = None
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
    raw_request_comment_id = run_name[len(RUN_NAME_PREFIX) :]
    return _parse_positive_decimal(raw_request_comment_id)


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


def _parse_positive_decimal(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0 or str(parsed) != value:
        return None
    return parsed


def _parse_revision(line: str) -> str | None:
    if not line.startswith(DEFAULT_BRANCH_REVISION_PREFIX):
        return None
    revision = line[len(DEFAULT_BRANCH_REVISION_PREFIX) :]
    if not revision or revision != revision.strip():
        return None
    return revision


def _parse_reason(line: str) -> str | None:
    if not line.startswith(REASON_PREFIX):
        return None
    reason = line[len(REASON_PREFIX) :]
    if (
        not reason
        or reason != reason.strip()
        or "\r" in reason
        or "\n" in reason
        or len(reason) > _MAX_REASON_LENGTH
    ):
        return None
    return reason


def parse_dispatch_decision(body: str) -> MachineDispatchDecision | None:
    lines = body.split("\n")
    if len(lines) not in {4, 5, 7, 8} or lines[0] != DECISION_MARKER:
        return None
    if not lines[1].startswith(REQUEST_COMMENT_ID_PREFIX):
        return None
    request_comment_id = _parse_positive_decimal(lines[1][len(REQUEST_COMMENT_ID_PREFIX) :])
    revision = _parse_revision(lines[2])
    if request_comment_id is None or revision is None:
        return None
    if not lines[3].startswith(DISPOSITION_PREFIX):
        return None

    disposition = lines[3][len(DISPOSITION_PREFIX) :]
    if disposition not in _DECISION_DISPOSITIONS:
        return None
    if disposition != "AUTHORIZE":
        if len(lines) not in {4, 5}:
            return None
        reason = None if len(lines) == 4 else _parse_reason(lines[4])
        if len(lines) == 5 and reason is None:
            return None
        return MachineDispatchDecision(
            request_comment_id=request_comment_id,
            default_branch_revision=revision,
            disposition=disposition,
            reason=reason,
        )

    if len(lines) not in {7, 8}:
        return None
    if not lines[4].startswith(ISSUE_PREFIX):
        return None
    issue_number = _parse_positive_decimal(lines[4][len(ISSUE_PREFIX) :])
    if issue_number is None or not lines[5].startswith(ROLE_PREFIX):
        return None
    role = lines[5][len(ROLE_PREFIX) :]
    if role not in _ROLES or not lines[6].startswith(ACTION_PREFIX):
        return None
    action = lines[6][len(ACTION_PREFIX) :]
    if not action or action != action.strip():
        return None

    debt_disposition = None
    if len(lines) == 8:
        if not lines[7].startswith(DEBT_DISPOSITION_PREFIX):
            return None
        debt_disposition = lines[7][len(DEBT_DISPOSITION_PREFIX) :]
        if debt_disposition not in _DEBT_DISPOSITIONS:
            return None
        if role != "lead" or action != "resolve-question":
            return None

    return MachineDispatchDecision(
        request_comment_id=request_comment_id,
        default_branch_revision=revision,
        disposition=disposition,
        issue_number=issue_number,
        role=role,
        action=action,
        debt_disposition=debt_disposition,
    )


def _validate_result_identity(request_comment_id: int, default_branch_revision: str) -> None:
    if request_comment_id <= 0:
        raise ValueError("request_comment_id must be positive")
    if not default_branch_revision or default_branch_revision != default_branch_revision.strip():
        raise ValueError("default_branch_revision must be non-empty and trimmed")


def _validated_reason(reason: str) -> str:
    if (
        not reason
        or reason != reason.strip()
        or "\r" in reason
        or "\n" in reason
        or len(reason) > _MAX_REASON_LENGTH
    ):
        raise ValueError("dispatch reason must be one non-empty bounded line")
    return reason


def render_dispatch_decision(
    *,
    request_comment_id: int,
    default_branch_revision: str,
    decision: DispatchDecision,
) -> str:
    _validate_result_identity(request_comment_id, default_branch_revision)
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
            raise ValueError("AUTHORIZE requires one machine-selected Issue/Role/Action tuple")
        role, action = decision.selected_routing
        lines.extend(
            (
                f"{ISSUE_PREFIX}{decision.selected_issue_id}",
                f"{ROLE_PREFIX}{role}",
                f"{ACTION_PREFIX}{action}",
            )
        )
        if decision.selected_debt_disposition is not None:
            if (
                decision.selected_debt_disposition not in _DEBT_DISPOSITIONS
                or role != "lead"
                or action != "resolve-question"
            ):
                raise ValueError("debt disposition requires Lead / resolve-question authorization")
            lines.append(f"{DEBT_DISPOSITION_PREFIX}{decision.selected_debt_disposition}")
    else:
        if decision.selected_issue_id is not None or decision.selected_routing is not None:
            raise ValueError("NO_WORK/FAIL_CLOSED must not carry an Issue/Role/Action tuple")
        if decision.selected_debt_disposition is not None:
            raise ValueError("NO_WORK/FAIL_CLOSED must not carry a debt disposition")
        lines.append(f"{REASON_PREFIX}{_validated_reason(decision.reason)}")
    return "\n".join(lines)


def _as_mapping(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, dict):
        return None
    return cast(Mapping[str, object], value)


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _request_identity(*, event: Mapping[str, object]) -> tuple[int, int] | None:
    if event.get("action") != "created":
        return None

    issue = _as_mapping(event.get("issue"))
    comment = _as_mapping(event.get("comment"))
    if issue is None or comment is None or not is_runtime_checkin_issue(issue):
        return None

    issue_number = _positive_int(issue.get("number"))
    comment_id = _positive_int(comment.get("id"))
    body = comment.get("body")
    if issue_number is None or comment_id is None or not isinstance(body, str):
        return None
    if parse_dispatch_request(body) is None:
        return None
    return issue_number, comment_id


def _is_github_actions_comment(comment: Mapping[str, object]) -> bool:
    user = _as_mapping(comment.get("user"))
    app = _as_mapping(comment.get("performed_via_github_app"))
    return (
        user is not None
        and user.get("login") == _GITHUB_ACTIONS_BOT_LOGIN
        and user.get("type") == "Bot"
        and app is not None
        and app.get("slug") == _GITHUB_ACTIONS_APP_SLUG
    )


def plan_bridge(
    *,
    event: Mapping[str, object],
    existing_comments: Sequence[Mapping[str, object]],
    configured_issue_number: int,
    default_branch_revision: str,
) -> BridgePlan:
    existing_plan, identity = _plan_identity(
        event=event,
        existing_comments=existing_comments,
        configured_issue_number=configured_issue_number,
    )
    if existing_plan is not None:
        return existing_plan
    issue_number, request_comment_id = _require_pending_identity(identity)
    return BridgePlan(
        should_post=True,
        issue_number=issue_number,
        request_comment_id=request_comment_id,
        result_body=render_dispatch_result(
            request_comment_id=request_comment_id,
            default_branch_revision=default_branch_revision,
        ),
    )


def plan_dispatch_decision(
    *,
    event: Mapping[str, object],
    default_branch_revision: str,
    decision: DispatchDecision,
) -> BridgePlan:
    identity = _request_identity(event=event)
    if identity is None:
        return BridgePlan(should_emit=False)

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
    preflight = acquire_current_github_preflight(repository, token)
    return classify_dispatch(preflight)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_mapping(value: object, *, name: str) -> Mapping[str, object]:
    mapping = _as_mapping(value)
    if mapping is None:
        raise ValueError(f"{name} must be a JSON object")
    return mapping


def _write_outputs(path: Path, plan: BridgePlan) -> None:
    lines = [f"should_emit={'true' if plan.should_emit else 'false'}"]
    if plan.issue_number is not None:
        lines.append(f"issue_number={plan.issue_number}")
    if plan.request_comment_id is not None:
        lines.append(f"request_comment_id={plan.request_comment_id}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_result_payload(path: Path, plan: BridgePlan) -> None:
    if not plan.should_emit or plan.result_body is None:
        return
    path.write_text(json.dumps({"body": plan.result_body}) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan one run-scoped machine dispatch result")
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    parser.add_argument("--result-payload", type=Path, required=True)
    args = parser.parse_args()

    event = _require_mapping(_load_json(args.event_path), name="event")
    identity = _request_identity(event=event)
    if identity is None:
        plan = BridgePlan(should_emit=False)
    else:
        repository = os.environ.get("GITHUB_REPOSITORY")
        token = os.environ.get("GITHUB_TOKEN")
        if not repository or not token:
            raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
        decision = acquire_production_dispatch_decision(repository, token)
        plan = plan_dispatch_decision(
            event=event,
            default_branch_revision=args.revision,
            decision=decision,
        )

    _write_outputs(args.github_output, plan)
    _write_result_payload(args.result_payload, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
