"""Persist exact live Scheduled Agent run evidence after fresh effect application."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_runtime import WorkerRequest


@dataclass(frozen=True)
class LiveRuntimeEvidence:
    """Audit-only identity and post-application evidence for one live worker invocation."""

    run_id: str
    run_attempt: str
    revision: str
    event_name: str
    source: WorkerRequest
    applied: bool
    continuation: WorkerRequest | None = None


def _display_request(request: WorkerRequest) -> str:
    return f"#{request.issue_number} / {request.role.title()} / {request.action}"


def render_live_runtime_evidence(evidence: LiveRuntimeEvidence) -> str:
    """Render durable audit evidence without creating an authorization surface."""

    continuation = (
        "none" if evidence.continuation is None else _display_request(evidence.continuation)
    )
    apply_state = "applied" if evidence.applied else "rejected"
    return "\n".join(
        (
            "<!-- scheduled-agent-live-runtime-evidence -->",
            "### LIVE_RUNTIME_EVIDENCE",
            f"- Actions run: `{evidence.run_id}` (attempt `{evidence.run_attempt}`)",
            f"- Revision: `{evidence.revision}`",
            f"- Trigger: `{evidence.event_name}`",
            f"- Dispatch: `AUTHORIZE` → `{_display_request(evidence.source)}`",
            "- Model invocation: `completed`",
            f"- Apply: `{apply_state}`",
            f"- Continuation: `{continuation}`",
            "- Audit evidence only; this comment is not dispatch authorization.",
        )
    )


def _github_json(
    repository: str,
    token: str,
    api_path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
) -> object:
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
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        return json.loads(response.read().decode("utf-8"))


def persist_live_runtime_evidence(
    repository: str,
    token: str,
    evidence: LiveRuntimeEvidence,
) -> int:
    """Create and fresh-observe the audit comment before reporting persistence success."""

    body = render_live_runtime_evidence(evidence)
    created = _github_json(
        repository,
        token,
        f"issues/{evidence.source.issue_number}/comments",
        method="POST",
        payload={"body": body},
    )
    if not isinstance(created, Mapping) or not isinstance(created.get("id"), int):
        raise RuntimeError("live runtime evidence comment creation returned no comment id")
    comment_id = cast(int, created["id"])

    observed = _github_json(repository, token, f"issues/comments/{comment_id}")
    if not isinstance(observed, Mapping) or observed.get("body") != body:
        raise RuntimeError("live runtime evidence comment postcondition was not observed")
    return comment_id


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required for live runtime evidence")
    return value


def _worker_request_from_environment(prefix: str) -> WorkerRequest:
    issue = _required_environment(f"{prefix}_ISSUE")
    role = _required_environment(f"{prefix}_ROLE")
    action = _required_environment(f"{prefix}_ACTION")
    try:
        issue_number = int(issue)
    except ValueError as exc:
        raise RuntimeError(f"{prefix}_ISSUE must be an integer") from exc
    return WorkerRequest(issue_number, role, action)


def evidence_from_environment() -> LiveRuntimeEvidence:
    """Build evidence only from same-run GitHub Actions/application outputs."""

    source = _worker_request_from_environment("AUTHORIZED")
    applied = _required_environment("APPLY_APPLIED") == "true"
    if not applied:
        raise RuntimeError("live runtime evidence persists only after accepted application")

    continuation: WorkerRequest | None = None
    if os.environ.get("CONTINUATION_REQUIRED") == "true":
        continuation = _worker_request_from_environment("CONTINUATION")

    return LiveRuntimeEvidence(
        run_id=_required_environment("GITHUB_RUN_ID"),
        run_attempt=_required_environment("GITHUB_RUN_ATTEMPT"),
        revision=_required_environment("RUNTIME_REVISION"),
        event_name=_required_environment("GITHUB_EVENT_NAME"),
        source=source,
        applied=applied,
        continuation=continuation,
    )


def main() -> int:
    """Persist one accepted live-run evidence record through the apply job's write boundary."""

    repository = _required_environment("GITHUB_REPOSITORY")
    token = _required_environment("GITHUB_TOKEN")
    evidence = evidence_from_environment()
    comment_id = persist_live_runtime_evidence(repository, token, evidence)
    print(json.dumps({"comment_id": comment_id, "run_id": evidence.run_id}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
