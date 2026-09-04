"""Read-only adapter for exact run-scoped Scheduled-Agent dispatch results."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from investment_strategy.issue_comment_bridge import (
    MachineDispatchDecision,
    parse_dispatch_run_name,
    parse_run_scoped_dispatch_result,
)

_SHA = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_LOG_REDIRECT_SUFFIX = ".actions.githubusercontent.com"


class _NoRedirect(HTTPRedirectHandler):
    """Expose the signed GitHub log redirect without forwarding the API bearer token."""

    def http_error_302(self, req, fp, code, msg, headers):
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


def _github_text(repository: str, token: str, api_path: str) -> str:
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
        with build_opener(_NoRedirect).open(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except HTTPError as exc:
        if exc.code != 302:
            raise RuntimeError("exact dispatch run log read failed") from exc
        location = exc.headers.get("Location")
        parsed = urlsplit(location) if isinstance(location, str) else None
        if (
            parsed is None
            or parsed.scheme != "https"
            or parsed.hostname is None
            or not parsed.hostname.endswith(_LOG_REDIRECT_SUFFIX)
        ):
            raise RuntimeError("exact dispatch run log redirect is not trusted") from exc
        redirected_request = Request(  # noqa: S310 - location is validated as a GitHub Actions host
            location,
            headers={"Accept": "application/octet-stream"},
        )
        try:
            with urlopen(redirected_request, timeout=30) as response:  # noqa: S310 - location is validated as a GitHub Actions host
                return response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError, UnicodeError) as redirect_exc:
            raise RuntimeError("exact dispatch run log response is invalid") from redirect_exc
    except (URLError, TimeoutError, UnicodeError) as exc:
        raise RuntimeError("exact dispatch run log response is invalid") from exc


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def fetch_dispatch_result(
    repository: str,
    token: str,
    *,
    request_comment_id: int,
    run_id: int,
    current_revision: str,
) -> MachineDispatchDecision:
    """Read exactly one successful bridge run and its one structured result."""

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

    jobs_payload = _as_mapping(
        _github_json(repository, token, f"actions/runs/{run_id}/jobs?per_page=100")
    )
    jobs = None if jobs_payload is None else jobs_payload.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 1:
        raise RuntimeError("exact dispatch run must contain one bridge job")
    job = _as_mapping(jobs[0])
    job_id = None if job is None else _positive_int(job.get("id"))
    if (
        job is None
        or job.get("name") != "bridge"
        or job.get("status") != "completed"
        or job.get("conclusion") != "success"
        or job_id is None
    ):
        raise RuntimeError("exact dispatch bridge job is incomplete")

    result = parse_run_scoped_dispatch_result(
        _github_text(repository, token, f"actions/jobs/{job_id}/logs"),
        request_comment_id=request_comment_id,
    )
    if result is None or result.default_branch_revision != current_revision:
        raise RuntimeError("exact dispatch result is missing, ambiguous, or stale")
    return result
