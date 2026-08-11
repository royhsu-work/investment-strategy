from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from investment_strategy.domain.failures import data_failure

TAIPEI = ZoneInfo("Asia/Taipei")
COMPLETION_TIME = time(13, 33)
PRODUCTION_OVERRIDES: Mapping[date, bool] = {}


class CalendarEngine(Protocol):
    first_session: object
    last_session: object

    def is_session(self, day: date) -> bool: ...

    def sessions_in_range(self, start: date, end: date) -> Sequence[object]: ...


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    to_pydatetime = getattr(value, "to_pydatetime", None)
    if callable(to_pydatetime):
        converted = to_pydatetime()
        if isinstance(converted, datetime):
            return converted.date()
    raise TypeError(f"unsupported calendar date value: {value!r}")


def _default_engine() -> Any:
    import exchange_calendars as xcals  # type: ignore[import-untyped]

    return xcals.get_calendar("XTAI")


class TaiwanTradingCalendar:
    def __init__(
        self,
        *,
        engine: CalendarEngine | None = None,
        overrides: Mapping[date, bool] | None = None,
    ) -> None:
        self._engine = engine or _default_engine()
        self._overrides = dict(PRODUCTION_OVERRIDES if overrides is None else overrides)

    def market_date(self, now: datetime) -> date:
        return now.astimezone(TAIPEI).date()

    def _ensure_supported(self, start: date, end: date | None = None) -> None:
        finish = end or start
        try:
            first = _as_date(self._engine.first_session)
            last = _as_date(self._engine.last_session)
        except Exception as exc:
            raise data_failure("CALENDAR_UNAVAILABLE", "XTAI calendar bounds unavailable") from exc
        if start < first or finish > last:
            raise data_failure(
                "CALENDAR_UNAVAILABLE",
                f"XTAI calendar cannot establish required range {start}..{finish}",
            )

    def is_trading_day(self, day: date) -> bool:
        self._ensure_supported(day)
        if day in self._overrides:
            return self._overrides[day]
        try:
            return bool(self._engine.is_session(day))
        except Exception as exc:
            raise data_failure("CALENDAR_UNAVAILABLE", f"XTAI unavailable for {day}") from exc

    def previous_trading_day(self, day: date) -> date:
        self._ensure_supported(day)
        current = day - timedelta(days=1)
        while True:
            if self.is_trading_day(current):
                return current
            current -= timedelta(days=1)

    def latest_completed_trading_day(self, now: datetime) -> date:
        today = self.market_date(now)
        if self.is_trading_day(today) and self.is_session_complete(today, now):
            return today
        return self.previous_trading_day(today)

    def trading_days(self, start: date, end: date) -> Sequence[date]:
        self._ensure_supported(start, end)
        try:
            engine_days = {_as_date(value) for value in self._engine.sessions_in_range(start, end)}
        except Exception as exc:
            raise data_failure(
                "CALENDAR_UNAVAILABLE", f"XTAI unavailable for range {start}..{end}"
            ) from exc
        for day, is_session in self._overrides.items():
            if start <= day <= end:
                if is_session:
                    engine_days.add(day)
                else:
                    engine_days.discard(day)
        return tuple(sorted(engine_days))

    def is_session_complete(self, day: date, now: datetime) -> bool:
        self._ensure_supported(day)
        today = self.market_date(now)
        if day < today:
            return True
        if day > today:
            return False
        if not self.is_trading_day(day):
            return False
        local_now = now.astimezone(TAIPEI)
        return local_now.time().replace(tzinfo=None) >= COMPLETION_TIME
