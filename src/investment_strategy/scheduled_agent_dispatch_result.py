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
    parse_run_scoped_dispatch_result,
)

_SHA = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_LOG_REDIRECT_HOST = re.compile(
    r"^(?:[a-z0-9-]+\.actions\.githubusercontent\.com|productionresultssa[0-9]+\.blob\.core\.windows\.net)$"
)


class _NoRedirect(HTTPRedirectHandler):
    """Expose the signed GitHub log redirect without forwarding the API bearer token."""

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
        if not isinstance(location, str):
            raise RuntimeError("exact dispatch run log redirect is not trusted") from exc
        parsed = urlsplit(location)
        host = parsed.hostname.lower() if parsed.hostname is not None else None
        if (
            parsed.scheme != "https"
            or host is None
            or _LOG_REDIRECT_HOST.fullmatch(host) is None
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