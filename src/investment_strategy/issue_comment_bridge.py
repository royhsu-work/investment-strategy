from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

REQUEST_MARKER = "DISPATCH_REQUEST"
REQUESTED_AT_PREFIX = "Requested-At: "
RESULT_MARKER = "DISPATCH_RESULT"
REQUEST_COMMENT_ID_PREFIX = "Request-Comment-ID: "
DEFAULT_BRANCH_REVISION_PREFIX = "Default-Branch-Revision: "
RESULT_PREFIX = "Result: "
BRIDGE_OK = "BRIDGE_OK"


@dataclass(frozen=True)
class DispatchRequest:
    requested_at: str


@dataclass(frozen=True)
class DispatchResult:
    request_comment_id: int
    default_branch_revision: str
    result: str


@dataclass(frozen=True)
class BridgePlan:
    should_post: bool
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


def parse_dispatch_result(body: str) -> DispatchResult | None:
    lines = body.split("\n")
    if len(lines) != 4 or lines[0] != RESULT_MARKER:
        return None
    if not lines[1].startswith(REQUEST_COMMENT_ID_PREFIX):
        return None
    if not lines[2].startswith(DEFAULT_BRANCH_REVISION_PREFIX):
        return None
    if lines[3] != f"{RESULT_PREFIX}{BRIDGE_OK}":
        return None

    raw_request_comment_id = lines[1][len(REQUEST_COMMENT_ID_PREFIX) :]
    try:
        request_comment_id = int(raw_request_comment_id)
    except ValueError:
        return None
    if request_comment_id <= 0 or str(request_comment_id) != raw_request_comment_id:
        return None

    revision = lines[2][len(DEFAULT_BRANCH_REVISION_PREFIX) :]
    if not revision or revision != revision.strip():
        return None

    return DispatchResult(
        request_comment_id=request_comment_id,
        default_branch_revision=revision,
        result=BRIDGE_OK,
    )


def render_dispatch_result(*, request_comment_id: int, default_branch_revision: str) -> str:
    if request_comment_id <= 0:
        raise ValueError("request_comment_id must be positive")
    if not default_branch_revision or default_branch_revision != default_branch_revision.strip():
        raise ValueError("default_branch_revision must be non-empty and trimmed")
    return (
        f"{RESULT_MARKER}\n"
        f"{REQUEST_COMMENT_ID_PREFIX}{request_comment_id}\n"
        f"{DEFAULT_BRANCH_REVISION_PREFIX}{default_branch_revision}\n"
        f"{RESULT_PREFIX}{BRIDGE_OK}"
    )


def _as_mapping(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, dict):
        return None
    return cast(Mapping[str, object], value)


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _request_identity(
    *, event: Mapping[str, object], configured_issue_number: int
) -> tuple[int, int] | None:
    if configured_issue_number <= 0 or event.get("action") != "created":
        return None

    issue = _as_mapping(event.get("issue"))
    comment = _as_mapping(event.get("comment"))
    if issue is None or comment is None or "pull_request" in issue:
        return None

    issue_number = _positive_int(issue.get("number"))
    comment_id = _positive_int(comment.get("id"))
    body = comment.get("body")
    if issue_number != configured_issue_number or comment_id is None or not isinstance(body, str):
        return None
    if parse_dispatch_request(body) is None:
        return None
    return issue_number, comment_id


def _has_correlated_result(
    existing_comments: Sequence[Mapping[str, object]], request_comment_id: int
) -> bool:
    for comment in existing_comments:
        body = comment.get("body")
        if not isinstance(body, str):
            continue
        result = parse_dispatch_result(body)
        if result is not None and result.request_comment_id == request_comment_id:
            return True
    return False


def plan_bridge(
    *,
    event: Mapping[str, object],
    existing_comments: Sequence[Mapping[str, object]],
    configured_issue_number: int,
    default_branch_revision: str,
) -> BridgePlan:
    identity = _request_identity(
        event=event,
        configured_issue_number=configured_issue_number,
    )
    if identity is None:
        return BridgePlan(should_post=False)

    issue_number, request_comment_id = identity
    if _has_correlated_result(existing_comments, request_comment_id):
        return BridgePlan(
            should_post=False,
            issue_number=issue_number,
            request_comment_id=request_comment_id,
        )

    return BridgePlan(
        should_post=True,
        issue_number=issue_number,
        request_comment_id=request_comment_id,
        result_body=render_dispatch_result(
            request_comment_id=request_comment_id,
            default_branch_revision=default_branch_revision,
        ),
    )


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_mapping(value: object, *, name: str) -> Mapping[str, object]:
    mapping = _as_mapping(value)
    if mapping is None:
        raise ValueError(f"{name} must be a JSON object")
    return mapping


def _flatten_comments(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValueError("comments payload must be a JSON array")

    comments: list[Mapping[str, object]] = []
    for item in value:
        if isinstance(item, list):
            for nested in item:
                mapping = _as_mapping(nested)
                if mapping is None:
                    raise ValueError("comments page contains a non-object item")
                comments.append(mapping)
            continue
        mapping = _as_mapping(item)
        if mapping is None:
            raise ValueError("comments payload contains a non-object item")
        comments.append(mapping)
    return comments


def _write_outputs(path: Path, plan: BridgePlan) -> None:
    lines = [f"should_post={'true' if plan.should_post else 'false'}"]
    if plan.issue_number is not None:
        lines.append(f"issue_number={plan.issue_number}")
    if plan.request_comment_id is not None:
        lines.append(f"request_comment_id={plan.request_comment_id}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_result_payload(path: Path, plan: BridgePlan) -> None:
    if not plan.should_post or plan.result_body is None:
        return
    path.write_text(json.dumps({"body": plan.result_body}) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan one no-API issue-comment bridge result")
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--comments-path", type=Path, required=True)
    parser.add_argument("--check-in-issue", type=int, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    parser.add_argument("--result-payload", type=Path, required=True)
    args = parser.parse_args()

    event = _require_mapping(_load_json(args.event_path), name="event")
    comments = _flatten_comments(_load_json(args.comments_path))
    plan = plan_bridge(
        event=event,
        existing_comments=comments,
        configured_issue_number=args.check_in_issue,
        default_branch_revision=args.revision,
    )
    _write_outputs(args.github_output, plan)
    _write_result_payload(args.result_payload, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
