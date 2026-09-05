"""Run-scoped machine dispatch transport."""

from __future__ import annotations

import argparse
import json
import os
import re
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
DISPATCH_RESULT_SCHEMA = "scheduled-agent-dispatch-result/v1"
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
