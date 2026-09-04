"""Pure identity rules for bounded Scheduled-Agent runtime check-in shards."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

_TAIPEI = ZoneInfo("Asia/Taipei")
_CHECKIN_TITLE_PREFIX = "[Agent Runtime] "


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


def _positive_issue_number(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


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
        names.append(label["name"])
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
