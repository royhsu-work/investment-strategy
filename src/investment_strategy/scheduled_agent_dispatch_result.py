"""Read-only adapter for exact run-scoped Scheduled-Agent dispatch results."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from investment_strategy.issue_comment_bridge import (
    MachineDispatchDecision,
    parse_dispatch_run_name,
)
from investment_strategy.scheduled_agent_action_model import Action as ModelAction
from investment_strategy.scheduled_agent_action_model import role_for

_SHA = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ARTIFACT_REDIRECT_HOST = re.compile(
    r"^(?:[a-z0-9-]+\.actions\.githubusercontent\.com|productionresultssa[0-9]+\.blob\.core\.windows\.net)$"
)
_ARTIFACT_NAME = "dispatch-result.json"
_SCHEMA = "scheduled-agent-dispatch-result/v1"
_MAX_RESULT_BYTES = 16_384
_MAX_REASON_LENGTH = 240
_DECISION_DISPOSITIONS = {"AUTHORIZE", "NO_WORK", "FAIL_CLOSED"}


class _NoRedirect(HTTPRedirectHandler):
    """Expose a signed GitHub artifact redirect without forwarding the API bearer token."""

    def http_error_302(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
    ) -> None:
        raise HTTPError(req.full_url, code, msg, headers, fp)


def _github_json(repository: str, token: str, api_path: str) -> object:
    if _REPOSITORY.fullmatch(repository) is None or not token:
        raise RuntimeError("repository/token identity is invalid")
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError("exact dispatch run API read failed") from exc
    except (URLError, TimeoutError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("exact dispatch run API response is invalid") from exc


def _github_bytes(repository: str, token: str, api_path: str) -> bytes:
    if _REPOSITORY.fullmatch(repository) is None or not token:
        raise RuntimeError("repository/token identity is invalid")
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        headers={
            "Accept": "application/octet-stream",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with build_opener(_NoRedirect).open(request, timeout=30) as response:
            return response.read()
    except HTTPError as exc:
        if exc.code != 302:
            raise RuntimeError("exact dispatch artifact read failed") from exc
        location = exc.headers.get("Location")
        if not isinstance(location, str):
            raise RuntimeError("exact dispatch artifact redirect is not trusted") from exc
        parsed = urlsplit(location)
        host = parsed.hostname.lower() if parsed.hostname is not None else None
        if (
            parsed.scheme != "https"
            or host is None
            or _ARTIFACT_REDIRECT_HOST.fullmatch(host) is None
        ):
            raise RuntimeError("exact dispatch artifact redirect is not trusted") from exc
        redirected_request = Request(  # noqa: S310 - validated GitHub Actions host
            location,
            headers={"Accept": "application/octet-stream"},
        )
        try:
            with urlopen(  # noqa: S310 - validated GitHub Actions host
                redirected_request,
                timeout=30,
            ) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as redirect_exc:
            raise RuntimeError("exact dispatch artifact response is invalid") from redirect_exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("exact dispatch artifact response is invalid") from exc


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _parse_dispatch_result_document(raw: bytes) -> MachineDispatchDecision:
    if not raw or len(raw) > _MAX_RESULT_BYTES:
        raise RuntimeError("exact dispatch result artifact size is invalid")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("exact dispatch result artifact is not UTF-8 JSON") from exc
    payload = _as_mapping(decoded)
    if payload is None:
        raise RuntimeError("exact dispatch result artifact must be a JSON object")

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
    if set(payload) != expected_keys or payload.get("schema") != _SCHEMA:
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
    if (
        not isinstance(reason, str)
        or not reason
        or reason != reason.strip()
        or "\n" in reason
        or len(reason) > _MAX_REASON_LENGTH
    ):
        raise RuntimeError("non-authorizing dispatch reason is invalid")
    return MachineDispatchDecision(
        request_comment_id=request_comment_id,
        default_branch_revision=revision,
        disposition=disposition,
        reason=reason,
    )


def fetch_dispatch_result(
    repository: str,
    token: str,
    *,
    request_comment_id: int,
    run_id: int,
    current_revision: str,
) -> MachineDispatchDecision:
    """Read exactly one successful bridge run and its one structured Artifact result."""

    if request_comment_id <= 0 or run_id <= 0 or _SHA.fullmatch(current_revision) is None:
        raise RuntimeError("exact dispatch run identity is invalid")

    run = _as_mapping(_github_json(repository, token, f"actions/runs/{run_id}"))
    run_name = None if run is None else run.get("name")
    if (
        run is None
        or _positive_int(run.get("id")) != run_id
        or not isinstance(run_name, str)
        or parse_dispatch_run_name(run_name) != request_comment_id
        or run.get("path") != ".github/workflows/scheduled-agent-bridge.yml"
        or run.get("event") != "issue_comment"
        or run.get("head_sha") != current_revision
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
    ):
        raise RuntimeError("exact dispatch run identity or completion is invalid")

    artifacts_payload = _as_mapping(
        _github_json(repository, token, f"actions/runs/{run_id}/artifacts?per_page=100")
    )
    artifacts = None if artifacts_payload is None else artifacts_payload.get("artifacts")
    total_count = None if artifacts_payload is None else artifacts_payload.get("total_count")
    if (
        not isinstance(artifacts, list)
        or isinstance(total_count, bool)
        or not isinstance(total_count, int)
        or total_count != len(artifacts)
    ):
        raise RuntimeError("exact dispatch artifact listing is incomplete")

    candidates: list[Mapping[str, object]] = []
    for artifact in artifacts:
        artifact_mapping = _as_mapping(artifact)
        if artifact_mapping is None:
            raise RuntimeError("exact dispatch artifact listing is invalid")
        if artifact_mapping.get("name") == _ARTIFACT_NAME:
            candidates.append(artifact_mapping)
    if len(candidates) != 1:
        raise RuntimeError("exact dispatch run must contain one dispatch-result.json Artifact")

    artifact = candidates[0]
    artifact_id = _positive_int(artifact.get("id"))
    if artifact_id is None or artifact.get("expired") is not False:
        raise RuntimeError("exact dispatch result Artifact is expired or invalid")

    result = _parse_dispatch_result_document(
        _github_bytes(repository, token, f"actions/artifacts/{artifact_id}/zip")
    )
    if (
        result.request_comment_id != request_comment_id
        or result.default_branch_revision != current_revision
    ):
        raise RuntimeError("exact dispatch result is missing, ambiguous, or stale")
    return result
