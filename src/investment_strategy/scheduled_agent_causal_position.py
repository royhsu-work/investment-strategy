"""Bounded causal-position helpers for pre-activation Scheduled Agent state."""

from __future__ import annotations

import re
from collections.abc import Mapping

_CAUSE_REF_VALUE = re.compile(r"^issuecomment-([1-9][0-9]*)$")
_CHANGE_LINE = re.compile(r"^Change:\s*([^\s]+)\s*$")
_CAUSE_LINE = re.compile(r"^Cause-Ref:\s*(.*?)\s*$")


def _top_level_line_indexes(body: str) -> tuple[tuple[int, str], ...]:
    """Return unfenced Markdown lines with their source indexes."""

    result: list[tuple[int, str]] = []
    fence_char: str | None = None
    for index, raw_line in enumerate(body.splitlines(keepends=True)):
        line = raw_line.rstrip("\r\n")
        stripped = line.lstrip()
        marker = stripped[0] if stripped.startswith(("```", "~~~")) else None
        if marker is not None:
            if fence_char is None:
                fence_char = marker
            elif marker == fence_char:
                fence_char = None
            continue
        if fence_char is None:
            result.append((index, line))
    return tuple(result)


def cause_ref_from_issue_body(body: object) -> tuple[int | None, bool]:
    """Return the exact top-level causal comment id plus structural validity."""

    if not isinstance(body, str):
        return None, False
    values: list[str] = []
    for _, line in _top_level_line_indexes(body):
        match = _CAUSE_LINE.fullmatch(line)
        if match is not None:
            values.append(match.group(1))
    if not values:
        return None, True
    if len(values) != 1:
        return None, False
    match = _CAUSE_REF_VALUE.fullmatch(values[0])
    if match is None:
        return None, False
    return int(match.group(1)), True


def bind_issue_cause_ref(body: object, comment_id: int) -> str | None:
    """Insert or replace one top-level Cause-Ref while preserving unrelated body text."""

    if not isinstance(body, str) or comment_id <= 0:
        return None

    lines = body.splitlines(keepends=True)
    top_level = _top_level_line_indexes(body)
    change_indexes = [index for index, line in top_level if _CHANGE_LINE.fullmatch(line)]
    cause_indexes = [index for index, line in top_level if _CAUSE_LINE.fullmatch(line)]
    if len(change_indexes) != 1 or len(cause_indexes) > 1:
        return None

    cause_line = f"Cause-Ref: issuecomment-{comment_id}"
    if cause_indexes:
        index = cause_indexes[0]
        raw = lines[index]
        ending = "\r\n" if raw.endswith("\r\n") else "\n" if raw.endswith("\n") else ""
        lines[index] = cause_line + ending
        return "".join(lines)

    change_index = change_indexes[0]
    raw_change = lines[change_index]
    if raw_change.endswith("\r\n"):
        ending = "\r\n"
    elif raw_change.endswith("\n"):
        ending = "\n"
    else:
        ending = "\n"
        lines[change_index] = raw_change + ending
    lines.insert(change_index + 1, cause_line + ending)
    return "".join(lines)


def proposal_ready_result_body(body: object, issue_number: int) -> bool:
    """Recognize the canonical Explore PROPOSAL_READY ACTION_RESULT envelope."""

    if not isinstance(body, str) or issue_number <= 0:
        return False
    lines = body.splitlines()
    expected = [
        f"Workflow: #{issue_number}",
        "Change: unset",
        "Action: Lead / explore-change",
        "Result: PROPOSAL_READY",
    ]
    for index, line in enumerate(lines):
        if line == "## ACTION_RESULT" and lines[index + 1 : index + 5] == expected:
            return True
    return False


def requested_proposal_ready_comment_payload(
    payload_json: str,
    *,
    issue_number: int,
) -> bool:
    """Validate an invocation-local issue-comment payload as the causal Explore result."""

    import json

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return False
    return (
        isinstance(payload, Mapping)
        and set(payload) == {"issue_number", "body"}
        and payload.get("issue_number") == issue_number
        and proposal_ready_result_body(payload.get("body"), issue_number)
    )


def trusted_proposal_ready_comment(
    payload: Mapping[str, object],
    *,
    issue_number: int,
    repository_owner: str,
    expected_comment_id: int,
) -> bool:
    """Validate one exact durable causal comment without scanning Issue history."""

    if payload.get("id") != expected_comment_id:
        return False
    issue_url = payload.get("issue_url")
    if not isinstance(issue_url, str) or not issue_url.endswith(f"/issues/{issue_number}"):
        return False
    user = payload.get("user")
    if not isinstance(user, Mapping):
        return False
    actor = user.get("login")
    trusted_owner = actor == repository_owner and payload.get("author_association") == "OWNER"
    trusted_runtime = actor == "github-actions[bot]"
    return (trusted_owner or trusted_runtime) and proposal_ready_result_body(
        payload.get("body"), issue_number
    )
