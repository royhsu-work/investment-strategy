"""Repository-owned daily Scheduled-Agent runtime shard rollover."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from urllib.error import HTTPError, URLError
from typing import cast
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

_TAIPEI = ZoneInfo("Asia/Taipei")
_CHECKIN_TITLE_PREFIX = "[Agent Runtime] "
_CHECKIN_MARKER = "<!-- scheduled-agent-runtime-checkin -->"
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ALLOWED_HTTP_METHODS = {"GET", "POST", "PATCH"}


class CheckinDisposition(StrEnum):
    """The only rollover states exposed to the workflow."""

    SELECTED = "selected"
    MISSING = "missing"
    CREATE = "create"
    RETIRE = "retire"
    FAIL_CLOSED = "fail-closed"


@dataclass(frozen=True, slots=True)
class ShardSelection:
    """Fresh current-day shard selection."""

    disposition: CheckinDisposition
    issue_number: int | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RolloverPlan:
    """Fresh daily rollover plan with exact retirement targets."""

    disposition: CheckinDisposition
    today: date
    current_issue_number: int | None
    retire_issue_numbers: tuple[int, ...]
    reason: str | None = None


def taipei_day(value: datetime | None = None) -> date:
    """Return the governed local calendar day for an aware instant."""

    current = datetime.now(UTC) if value is None else value
    if current.tzinfo is None:
        raise ValueError("taipei_day requires an aware datetime")
    return current.astimezone(_TAIPEI).date()


def checkin_title(day: date) -> str:
    """Render the canonical non-workflow runtime shard title."""

    if isinstance(day, datetime):
        raise TypeError("checkin_title requires a date, not datetime")
    return f"{_CHECKIN_TITLE_PREFIX}{day.isoformat()}"


def checkin_body(day: date) -> str:
    """Render a bounded body with no workflow identity fields."""

    if isinstance(day, datetime):
        raise TypeError("checkin_body requires a date, not datetime")
    return "\n".join(
        (
            _CHECKIN_MARKER,
            "Timezone: Asia/Taipei",
            f"Local date: {day.isoformat()}",
            "Purpose: repository-owned scheduled-agent wake transport.",
        )
    ) + "\n"


def _positive_issue_number(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _issue_number(value: object) -> int | None:
    if not _positive_issue_number(value):
        return None
    return cast(int, value)


def _label_names(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    names: list[str] = []
    for label in value:
        if isinstance(label, str):
            names.append(label)
            continue
        if not isinstance(label, Mapping) or not isinstance(label.get("name"), str):
            return None
        names.append(cast(str, label["name"]))
    return tuple(names)


def _title_day(value: object) -> date | None:
    if not isinstance(value, str) or not value.startswith(_CHECKIN_TITLE_PREFIX):
        return None
    raw_day = value[len(_CHECKIN_TITLE_PREFIX) :]
    try:
        parsed = date.fromisoformat(raw_day)
    except ValueError:
        return None
    if checkin_title(parsed) != value:
        return None
    return parsed


def parse_checkin_day(payload: Mapping[str, object]) -> date | None:
    """Return the local-date identity only for a non-workflow Issue shape."""

    if "pull_request" in payload or not _positive_issue_number(payload.get("number")):
        return None
    day = _title_day(payload.get("title"))
    labels = _label_names(payload.get("labels"))
    if day is None or labels is None:
        return None
    if any(name.startswith(("agent:", "action:")) for name in labels):
        return None
    return day


def is_runtime_checkin_issue(payload: Mapping[str, object]) -> bool:
    """Accept open or closed shards so an in-flight request can finish after rollover."""

    return parse_checkin_day(payload) is not None


def _looks_like_runtime_issue(payload: Mapping[str, object]) -> bool:
    if "pull_request" in payload:
        return False
    title = payload.get("title")
    return isinstance(title, str) and title.startswith(_CHECKIN_TITLE_PREFIX)


def _invalid(reason: str) -> ShardSelection:
    return ShardSelection(CheckinDisposition.FAIL_CLOSED, reason=reason)


def select_current_shard(
    payloads: Sequence[Mapping[str, object]],
    day: date,
) -> ShardSelection:
    """Select exactly one open current-day shard from a fresh Issue snapshot."""

    current: list[Mapping[str, object]] = []
    expected_title = checkin_title(day)
    for payload in payloads:
        if "pull_request" in payload or payload.get("title") != expected_title:
            continue
        if parse_checkin_day(payload) is None:
            return _invalid("invalid-shard-identity")
        if payload.get("state") not in {"open", "closed"}:
            return _invalid("invalid-shard-state")
        current.append(payload)

    if len(current) > 1:
        return _invalid("duplicate-current-day")
    if not current:
        return ShardSelection(CheckinDisposition.MISSING)

    payload = current[0]
    issue_number = _issue_number(payload.get("number"))
    if issue_number is None:
        return _invalid("invalid-shard-identity")
    if payload.get("state") != "open":
        return _invalid("current-day-not-open")
    return ShardSelection(CheckinDisposition.SELECTED, issue_number=issue_number)


def _invalid_rollover(today: date, reason: str) -> RolloverPlan:
    return RolloverPlan(
        disposition=CheckinDisposition.FAIL_CLOSED,
        today=today,
        current_issue_number=None,
        retire_issue_numbers=(),
        reason=reason,
    )


def plan_rollover(
    payloads: Sequence[Mapping[str, object]],
    today: date,
) -> RolloverPlan:
    """Plan rollover from an invocation-local all-state Issues snapshot."""

    parsed_shards: list[tuple[int, date, str]] = []
    seen_numbers: set[int] = set()
    for payload in payloads:
        if not _looks_like_runtime_issue(payload):
            continue
        parsed = parse_checkin_day(payload)
        state = payload.get("state")
        issue_number = _issue_number(payload.get("number"))
        if parsed is None or issue_number is None:
            return _invalid_rollover(today, "invalid-shard-identity")
        if state not in {"open", "closed"}:
            return _invalid_rollover(today, "invalid-shard-state")
        if issue_number in seen_numbers:
            return _invalid_rollover(today, "duplicate-shard-identity")
        seen_numbers.add(issue_number)
        if parsed > today:
            return _invalid_rollover(today, "future-shard-identity")
        parsed_shards.append((issue_number, parsed, cast(str, state)))

    selection = select_current_shard(payloads, today)
    if selection.disposition is CheckinDisposition.FAIL_CLOSED:
        return _invalid_rollover(today, selection.reason or "invalid-current-shard")

    retire = tuple(
        sorted(
            issue_number
            for issue_number, shard_day, state in parsed_shards
            if shard_day < today and state == "open"
        )
    )
    if selection.disposition is CheckinDisposition.SELECTED:
        disposition = CheckinDisposition.RETIRE if retire else CheckinDisposition.SELECTED
        return RolloverPlan(
            disposition=disposition,
            today=today,
            current_issue_number=selection.issue_number,
            retire_issue_numbers=retire,
        )
    return RolloverPlan(
        disposition=CheckinDisposition.CREATE,
        today=today,
        current_issue_number=None,
        retire_issue_numbers=retire,
    )


def _github_json(
    repository: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
) -> object:
    if not _REPOSITORY_PATTERN.fullmatch(repository):
        raise RuntimeError("GITHUB_REPOSITORY has an invalid owner/name shape")
    if not path.startswith("/") or method not in _ALLOWED_HTTP_METHODS:
        raise RuntimeError("unsupported GitHub API request shape")
    request_data = (
        None
        if payload is None
        else json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "investment-strategy-scheduled-agent",
    }
    if request_data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(
        f"https://api.github.com/repos/{repository}{path}",
        data=request_data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"GitHub API {method} {path} failed with HTTP {exc.code}") from exc
    except (URLError, TimeoutError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"GitHub API {method} {path} returned invalid data") from exc


def _github_issues(repository: str, token: str) -> tuple[Mapping[str, object], ...]:
    """Fresh-read all Issues, including closed shards and PR-shaped entries."""

    page = 1
    issues: list[Mapping[str, object]] = []
    while True:
        raw = _github_json(
            repository,
            token,
            f"/issues?state=all&per_page=100&page={page}",
        )
        if not isinstance(raw, list):
            raise RuntimeError("GitHub Issues API returned a non-list page")
        page_items: list[Mapping[str, object]] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise RuntimeError("GitHub Issues API returned a malformed item")
            page_items.append(cast(Mapping[str, object], item))
        issues.extend(page_items)
        if len(page_items) < 100:
            return tuple(issues)
        page += 1


def _github_issue(repository: str, token: str, issue_number: int) -> Mapping[str, object]:
    raw = _github_json(repository, token, f"/issues/{issue_number}")
    if not isinstance(raw, Mapping):
        raise RuntimeError("GitHub Issue API returned a non-object")
    return cast(Mapping[str, object], raw)


def _verify_shard(
    payload: Mapping[str, object],
    *,
    day: date,
    expected_state: str,
) -> int:
    issue_number = _issue_number(payload.get("number"))
    if (
        issue_number is None
        or parse_checkin_day(payload) != day
        or payload.get("state") != expected_state
    ):
        raise RuntimeError("GitHub shard postcondition was not observed")
    return issue_number


def _create_shard(repository: str, token: str, day: date) -> int:
    raw = _github_json(
        repository,
        token,
        "/issues",
        method="POST",
        payload={"title": checkin_title(day), "body": checkin_body(day)},
    )
    if not isinstance(raw, Mapping):
        raise RuntimeError("GitHub shard creation returned a non-object")
    return _verify_shard(cast(Mapping[str, object], raw), day=day, expected_state="open")


def _close_shard(repository: str, token: str, issue_number: int, day: date) -> None:
    raw = _github_json(
        repository,
        token,
        f"/issues/{issue_number}",
        method="PATCH",
        payload={"state": "closed", "state_reason": "completed"},
    )
    if not isinstance(raw, Mapping):
        raise RuntimeError("GitHub shard retirement returned a non-object")
    observed = _verify_shard(cast(Mapping[str, object], raw), day=day, expected_state="closed")
    if observed != issue_number:
        raise RuntimeError("GitHub shard retirement returned the wrong Issue")


def _fresh_rollover(
    repository: str,
    token: str,
    today: date,
) -> tuple[tuple[Mapping[str, object], ...], RolloverPlan]:
    issues = _github_issues(repository, token)
    return issues, plan_rollover(issues, today)


def _require_plan(plan: RolloverPlan) -> None:
    if plan.disposition is CheckinDisposition.FAIL_CLOSED:
        raise RuntimeError(plan.reason or "daily shard rollover failed closed")


def _retire_exact_targets(
    repository: str,
    token: str,
    today: date,
    *,
    current_issue_number: int,
    target_issue_numbers: tuple[int, ...],
) -> list[int]:
    remaining = set(target_issue_numbers)
    retired: list[int] = []
    while remaining:
        _, plan = _fresh_rollover(repository, token, today)
        _require_plan(plan)
        if (
            plan.current_issue_number != current_issue_number
            or set(plan.retire_issue_numbers) != remaining
        ):
            raise RuntimeError("daily shard rollover became stale before retirement")
        target = min(remaining)
        observed = _github_issue(repository, token, target)
        if (
            _issue_number(observed.get("number")) != target
            or parse_checkin_day(observed) is None
            or parse_checkin_day(observed) >= today
            or observed.get("state") != "open"
        ):
            raise RuntimeError("daily shard retirement target became stale")
        _close_shard(repository, token, target, parse_checkin_day(observed))
        remaining.remove(target)
        retired.append(target)
    return retired


def main() -> int:
    """Establish today's shard, then retire only freshly authorized old open shards."""

    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    today = taipei_day()
    _, plan = _fresh_rollover(repository, token, today)
    _require_plan(plan)

    created_issue: int | None = None
    retired: list[int] = []
    if plan.disposition is CheckinDisposition.CREATE:
        created_issue = _create_shard(repository, token, today)
        issues, plan = _fresh_rollover(repository, token, today)
        _require_plan(plan)
        if plan.current_issue_number != created_issue:
            raise RuntimeError("created shard was not the unique current-day shard")
        del issues
    elif plan.disposition is CheckinDisposition.SELECTED:
        if plan.current_issue_number is None:
            raise RuntimeError("selected shard has no Issue number")
    elif plan.disposition is CheckinDisposition.RETIRE:
        if plan.current_issue_number is None:
            raise RuntimeError("retirement plan has no current Issue number")

    if plan.retire_issue_numbers:
        if plan.current_issue_number is None:
            raise RuntimeError("retirement plan has no current-day shard")
        retired = _retire_exact_targets(
            repository,
            token,
            today,
            current_issue_number=plan.current_issue_number,
            target_issue_numbers=plan.retire_issue_numbers,
        )

    final_issues, final_plan = _fresh_rollover(repository, token, today)
    if (
        final_plan.disposition is not CheckinDisposition.SELECTED
        or final_plan.current_issue_number is None
        or final_plan.retire_issue_numbers
    ):
        raise RuntimeError("daily shard rollover postcondition was not observed")
    if created_issue is not None and final_plan.current_issue_number != created_issue:
        raise RuntimeError("created shard identity changed")
    print(
        json.dumps(
            {
                "day": today.isoformat(),
                "current_issue": final_plan.current_issue_number,
                "created_issue": created_issue,
                "retired_issues": retired,
                "observed_issue_count": len(final_issues),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
