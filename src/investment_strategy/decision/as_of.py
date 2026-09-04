from __future__ import annotations

from datetime import date, datetime

from investment_strategy.data.calendar import TradingCalendar
from investment_strategy.domain.failures import configuration_failure


def resolve_decision_as_of(
    requested: date | None,
    *,
    now: datetime,
    calendar: TradingCalendar,
) -> date:
    today = calendar.market_date(now)
    if requested is None:
        return calendar.latest_completed_trading_day(now)
    if requested > today:
        raise configuration_failure("INVALID_AS_OF", "requested as_of is in the future")
    if requested == today:
        if calendar.is_trading_day(requested) and calendar.is_session_complete(requested, now):
            return requested
        return calendar.previous_trading_day(requested)
    if calendar.is_trading_day(requested):
        return requested
    return calendar.previous_trading_day(requested)


def is_current_formal_decision(
    requested: date | None,
    *,
    now: datetime,
    calendar: TradingCalendar,
    resolved_as_of: date,
) -> bool:
    today = calendar.market_date(now)
    if not calendar.is_trading_day(today) or calendar.is_session_complete(today, now):
        return False
    if requested is not None and requested != today:
        return False
    return resolved_as_of == calendar.previous_trading_day(today)
