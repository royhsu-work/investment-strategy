"""Repository-owned daily Scheduled-Agent runtime shard rollover."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

_TAIPEI = ZoneInfo("Asia/Taipei")
_CHECKIN_TITLE_PREFIX = "[Agent Runtime] "
_CHECKIN_MARKER = "<!-- scheduled-agent-runtime-checkin -->"
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ALLOWED_HTTP_METHODS = {"GET", "POST", "PATCH"}
_CREATE_POSTCONDITION_ATTEMPTS = 10
_CREATE_POSTCONDITION_DELAY_SECONDS = 1.0
_ROLLOVER_REQUEST = re.compile(
    r"\AROLLOVER_REQUEST\nRequested-Day: ([0-9]{4}-[0-9]{2}-[0-9]{2})\n"
    r"Source-Shard: ([1-9][0-9]*)\n\Z"
)
_TRUSTED_EXTERNAL_APP = "chatgpt-codex-connector"


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


@dataclass(frozen=True, slots=True)
class RolloverHandoff:
    """Ephemeral pre-dispatch decision, never a workflow or Check-in state."""

    source_issue_number: int | None = None
    current_issue_number: int | None = None
    already_requested: bool = False
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
    return (
        "\n".join(
            (
                _CHECKIN_MARKER,
                "Timezone: Asia/Taipei",
                f"Local date: {day.isoformat()}",
                "Purpose: repository-owned scheduled-agent wake transport.",
            )
        )
        + "\n"
    )


def rollover_request_body(day: date, source_issue_number: int) -> str:
    """Render the bounded comment handed to the existing Check-in owner."""

    if not _positive_issue_number(source_issue_number) or isinstance(day, datetime):
        raise ValueError("rollover request requires an exact day and source Issue")
    return (
        f"ROLLOVER_REQUEST\nRequested-Day: {day.isoformat()}\nSource-Shard: {source_issue_number}\n"
    )


def parse_rollover_request(body: object) -> tuple[date, int] | None:
    """Reject near matches, extra fields, noncanonical dates and missing newlines."""

    if not isinstance(body, str):
        return None
    match = _ROLLOVER_REQUEST.fullmatch(body)
    if match is None:
        return None
    try:
        day = date.fromisoformat(match.group(1))
        issue_number = int(match.group(2))
    except ValueError:
        return None
    if day.isoformat() != match.group(1) or not _positive_issue_number(issue_number):
        return None
    return day, issue_number


def _trusted_external_comment(comment: Mapping[str, object], actor_login: str) -> bool:
    user = comment.get("user")
    app = comment.get("performed_via_github_app")
    return (
        isinstance(user, Mapping)
        and user.get("login") == actor_login
        and isinstance(app, Mapping)
        and app.get("slug") == _TRUSTED_EXTERNAL_APP
    )


def plan_rollover_handoff(
    payloads: Sequence[Mapping[str, object]],
    today: date,
    *,
    commentable_issue_numbers: frozenset[int],
    comments_by_issue: Mapping[int, Sequence[Mapping[str, object]]],
    actor_login: str,
) -> RolloverHandoff:
    """Choose an older shard only from complete externally verified observations.

    The agent must independently establish real comment capability, gather every
    all-state Issue/comment page and fresh-recheck before writing.  This pure
    selector has no GitHub write capability and cannot authorize dispatch.
    """

    if not actor_login or not all(_positive_issue_number(n) for n in commentable_issue_numbers):
        return RolloverHandoff(reason="comment-authority-incomplete")
    plan = plan_rollover(payloads, today)
    if plan.disposition is CheckinDisposition.FAIL_CLOSED:
        return RolloverHandoff(reason=plan.reason or "invalid-runtime-shards")
    if plan.current_issue_number is not None:
        return RolloverHandoff(current_issue_number=plan.current_issue_number)

    older: list[tuple[date, int, bool]] = []
    seen_dates: set[date] = set()
    for payload in payloads:
        if not _looks_like_runtime_issue(payload):
            continue
        day = parse_checkin_day(payload)
        number = _issue_number(payload.get("number"))
        if day is None or number is None or day >= today:
            return RolloverHandoff(reason="invalid-runtime-identity")
        if day in seen_dates:
            return RolloverHandoff(reason="duplicate-runtime-date")
        seen_dates.add(day)
        locked = payload.get("locked")
        if not isinstance(locked, bool):
            return RolloverHandoff(reason="runtime-comment-capability-incomplete")
        if number not in comments_by_issue:
            return RolloverHandoff(reason="runtime-comment-history-incomplete")
        older.append((day, number, locked))

    already_requested = False
    for _day, number, _locked in older:
        for comment in comments_by_issue[number]:
            body = comment.get("body")
            if not isinstance(body, str):
                return RolloverHandoff(reason="runtime-comment-incomplete")
            if not body.startswith("ROLLOVER_REQUEST"):
                continue
            parsed = parse_rollover_request(body)
            if parsed is None:
                return RolloverHandoff(reason="ambiguous-rollover-request")
            requested_day, requested_source = parsed
            if requested_day != today:
                continue
            if requested_source != number or not _trusted_external_comment(comment, actor_login):
                return RolloverHandoff(reason="unqualified-rollover-request")
            if already_requested:
                return RolloverHandoff(reason="duplicate-rollover-request")
            already_requested = True
    if already_requested:
        return RolloverHandoff(already_requested=True)

    eligible = sorted(
        (day, number)
        for day, number, locked in older
        if not locked and number in commentable_issue_numbers
    )
    if not eligible:
        return RolloverHandoff(reason="no-unique-commentable-older-shard")
    return RolloverHandoff(source_issue_number=eligible[-1][1])


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


def _github_comments(
    repository: str, token: str, issue_number: int
) -> tuple[Mapping[str, object], ...]:
    """Collect complete, ordered GitHub comment evidence without guessing pages."""

    page = 1
    comments: list[Mapping[str, object]] = []
    while True:
        raw = _github_json(
            repository, token, f"/issues/{issue_number}/comments?per_page=100&page={page}"
        )
        if not isinstance(raw, list):
            raise RuntimeError("GitHub Issue comments are incomplete")
        for item in raw:
            if not isinstance(item, Mapping):
                raise RuntimeError("GitHub Issue comment is malformed")
            comments.append(cast(Mapping[str, object], item))
        if len(raw) < 100:
            return tuple(comments)
        page += 1


def qualify_rollover_comment_event(
    repository: str,
    token: str,
    event: Mapping[str, object],
    *,
    today: date,
    actor_login: str,
) -> int | None:
    """Check one real external created event before using ordinary Check-in.

    The event itself gives no mutation authority: re-read the exact comment,
    source Issue, all-state shards and same-day request history first.
    """

    event_repo = event.get("repository")
    sender = event.get("sender")
    event_issue = event.get("issue")
    event_comment = event.get("comment")
    if (
        event.get("action") != "created"
        or not isinstance(event_repo, Mapping)
        or event_repo.get("full_name") != repository
        or not isinstance(sender, Mapping)
        or sender.get("login") != actor_login
        or not isinstance(event_issue, Mapping)
        or "pull_request" in event_issue
        or not isinstance(event_comment, Mapping)
        or not actor_login
    ):
        return None
    source_number = _issue_number(event_issue.get("number"))
    comment_id = _issue_number(event_comment.get("id"))
    parsed = parse_rollover_request(event_comment.get("body"))
    if source_number is None or comment_id is None or parsed != (today, source_number):
        return None

    observed_comment = _github_json(repository, token, f"/issues/comments/{comment_id}")
    if (
        not isinstance(observed_comment, Mapping)
        or observed_comment.get("id") != comment_id
        or observed_comment.get("body") != event_comment.get("body")
        or not _trusted_external_comment(observed_comment, actor_login)
    ):
        return None
    fresh_source = _github_issue(repository, token, source_number)
    source_day = parse_checkin_day(fresh_source)
    if (
        _issue_number(fresh_source.get("number")) != source_number
        or source_day is None
        or source_day >= today
        or fresh_source.get("title") != event_issue.get("title")
        or fresh_source.get("locked") is not False
        or fresh_source.get("state") not in {"open", "closed"}
    ):
        return None

    issues = _github_issues(repository, token)
    full_plan = plan_rollover(issues, today)
    if full_plan.disposition is CheckinDisposition.FAIL_CLOSED:
        return None
    older = tuple(
        issue
        for issue in issues
        if _looks_like_runtime_issue(issue)
        and parse_checkin_day(issue) is not None
        and cast(date, parse_checkin_day(issue)) < today
    )
    if source_number not in {_issue_number(item.get("number")) for item in older}:
        return None
    # A created event proves this source was externally commentable.  A more
    # recent unlocked older shard makes this source selection stale, even if
    # that shard's capability is not yet provable from event metadata.
    available = sorted(
        (cast(date, parse_checkin_day(item)), _issue_number(item.get("number")))
        for item in older
        if item.get("locked") is False
    )
    if not available or available[-1][1] != source_number:
        return None
    comments_by_issue: dict[int, tuple[Mapping[str, object], ...]] = {}
    for item in older:
        number = _issue_number(item.get("number"))
        if number is None:
            return None
        comments_by_issue[number] = _github_comments(repository, token, number)
    handoff = plan_rollover_handoff(
        older,
        today,
        commentable_issue_numbers=frozenset({source_number}),
        comments_by_issue=comments_by_issue,
        actor_login=actor_login,
    )
    if not handoff.already_requested or handoff.reason is not None:
        return None
    same_day = [
        comment
        for comment in comments_by_issue[source_number]
        if parse_rollover_request(comment.get("body")) == (today, source_number)
    ]
    if len(same_day) != 1 or same_day[0].get("id") != comment_id:
        return None
    return source_number


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


def _create_or_reconcile_shard(repository: str, token: str, today: date) -> int:
    """On an ambiguous create response, observe; never blindly replay POST."""

    try:
        return _create_shard(repository, token, today)
    except RuntimeError:
        _, plan = _fresh_rollover(repository, token, today)
        _require_plan(plan)
        if plan.current_issue_number is None:
            raise
        return plan.current_issue_number


def _observe_created_shard(
    repository: str,
    token: str,
    today: date,
    created_issue: int,
) -> RolloverPlan:
    """Observe a newly created shard across bounded GitHub read-after-write lag."""

    for attempt in range(_CREATE_POSTCONDITION_ATTEMPTS):
        _, plan = _fresh_rollover(repository, token, today)
        _require_plan(plan)
        if plan.current_issue_number == created_issue:
            return plan
        if plan.disposition is not CheckinDisposition.CREATE:
            raise RuntimeError("created shard was not the unique current-day shard")
        if attempt + 1 < _CREATE_POSTCONDITION_ATTEMPTS:
            time.sleep(_CREATE_POSTCONDITION_DELAY_SECONDS)
    raise RuntimeError("created shard postcondition was not observed")


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
        target_day = parse_checkin_day(observed)
        if (
            _issue_number(observed.get("number")) != target
            or target_day is None
            or target_day >= today
            or observed.get("state") != "open"
        ):
            raise RuntimeError("daily shard retirement target became stale")
        _close_shard(repository, token, target, target_day)
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
    if os.environ.get("GITHUB_EVENT_NAME") == "issue_comment":
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        actor_login = os.environ.get("GITHUB_ACTOR")
        if not event_path or not actor_login:
            raise RuntimeError("comment event identity is incomplete")
        with open(event_path, encoding="utf-8") as handle:
            event = json.load(handle)
        if not isinstance(event, Mapping):
            raise RuntimeError("comment event is malformed")
        source = qualify_rollover_comment_event(
            repository,
            token,
            event,
            today=today,
            actor_login=actor_login,
        )
        if source is None:
            print(json.dumps({"event": "rollover-request-ignored"}, sort_keys=True))
            return 0

    _, plan = _fresh_rollover(repository, token, today)
    _require_plan(plan)

    created_issue: int | None = None
    retired: list[int] = []
    if plan.disposition is CheckinDisposition.CREATE:
        created_issue = _create_or_reconcile_shard(repository, token, today)
        plan = _observe_created_shard(repository, token, today, created_issue)
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
