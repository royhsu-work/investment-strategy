from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from investment_strategy.domain.failures import data_failure
from investment_strategy.domain.market_data import DailyBar

from .calendar import TradingCalendar


def validate_continuity_and_freshness(
    bars: Sequence[DailyBar], *, calendar: TradingCalendar, resolved_as_of: date
) -> None:
    if not bars:
        raise data_failure("STALE_DATA", f"no bounded data through {resolved_as_of}")

    actual = {bar.trading_timestamp for bar in bars}
    first = bars[0].trading_timestamp
    last = bars[-1].trading_timestamp
    for expected in calendar.trading_days(first, last):
        if expected not in actual:
            raise data_failure("DATA_GAP", f"missing expected trading day {expected}")

    if last != resolved_as_of:
        raise data_failure(
            "STALE_DATA",
            f"latest observation {last} does not match resolved as-of {resolved_as_of}",
        )


def ensure_minimum_history(bars: Sequence[DailyBar], minimum_history: int) -> None:
    if len(bars) < minimum_history:
        raise data_failure(
            "INSUFFICIENT_HISTORY",
            f"requires {minimum_history} observations but only {len(bars)} are available",
        )
