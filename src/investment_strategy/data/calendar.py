from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol


class TradingCalendar(Protocol):
    def is_trading_day(self, day: date) -> bool: ...

    def previous_trading_day(self, day: date) -> date: ...

    def latest_completed_trading_day(self, now: datetime) -> date: ...

    def trading_days(self, start: date, end: date) -> Sequence[date]: ...

    def is_session_complete(self, day: date, now: datetime) -> bool: ...
