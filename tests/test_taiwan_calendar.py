from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import yaml

from investment_strategy.domain import ApplicationFailure
from investment_strategy.infrastructure.taiwan_calendar import (
    PRODUCTION_OVERRIDES,
    TaiwanTradingCalendar,
)


class FakeEngine:
    first_session = date(2026, 1, 2)
    last_session = date(2026, 12, 31)

    def __init__(self, sessions: set[date]) -> None:
        self.sessions = sessions

    def is_session(self, day: date) -> bool:
        return day in self.sessions

    def sessions_in_range(self, start: date, end: date) -> tuple[date, ...]:
        return tuple(sorted(day for day in self.sessions if start <= day <= end))


SESSIONS = {
    date(2026, 1, 2),
    date(2026, 1, 5),
    date(2026, 1, 6),
    date(2026, 1, 7),
    date(2026, 1, 8),
    date(2026, 1, 9),
}


def test_market_date_uses_asia_taipei() -> None:
    calendar = TaiwanTradingCalendar(engine=FakeEngine(SESSIONS))
    assert calendar.market_date(datetime(2026, 1, 4, 16, 30, tzinfo=UTC)) == date(2026, 1, 5)


def test_engine_sessions_and_non_sessions_are_preserved_without_duplicate_calendar() -> None:
    calendar = TaiwanTradingCalendar(engine=FakeEngine(SESSIONS))
    assert calendar.is_trading_day(date(2026, 1, 5))
    assert not calendar.is_trading_day(date(2026, 1, 4))


def test_completion_boundary_is_conservative_1333_taipei() -> None:
    calendar = TaiwanTradingCalendar(engine=FakeEngine(SESSIONS))
    before = datetime(2026, 1, 5, 5, 32, tzinfo=UTC)
    after = datetime(2026, 1, 5, 5, 33, tzinfo=UTC)
    assert not calendar.is_session_complete(date(2026, 1, 5), before)
    assert calendar.is_session_complete(date(2026, 1, 5), after)
    assert calendar.latest_completed_trading_day(before) == date(2026, 1, 2)
    assert calendar.latest_completed_trading_day(after) == date(2026, 1, 5)


def test_engine_unavailable_range_maps_to_calendar_unavailable() -> None:
    calendar = TaiwanTradingCalendar(engine=FakeEngine(SESSIONS))
    with pytest.raises(ApplicationFailure) as exc:
        calendar.trading_days(date(2025, 12, 31), date(2026, 1, 5))
    assert exc.value.failure.code == "CALENDAR_UNAVAILABLE"


def test_repository_override_wins_and_engine_is_used_without_override() -> None:
    calendar = TaiwanTradingCalendar(
        engine=FakeEngine(SESSIONS),
        overrides={date(2026, 1, 5): False, date(2026, 1, 10): True},
    )
    assert not calendar.is_trading_day(date(2026, 1, 5))
    assert calendar.is_trading_day(date(2026, 1, 10))
    assert calendar.is_trading_day(date(2026, 1, 6))


def test_approved_official_regressions_match_pinned_xtai_plus_sparse_overrides() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "taiwan_calendar_regressions.yaml"
    payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    calendar = TaiwanTradingCalendar()

    observed: dict[date, bool] = {}
    for case in payload["cases"]:
        day = date.fromisoformat(case["date"])
        expected = bool(case["expected_session"])
        observed[day] = calendar.is_trading_day(day)
        assert observed[day] is expected
        assert case["retrieval_date"] == "2026-08-11"
        assert case["sources"]
        assert case["evidence_note"]

    assert {date(2018, 3, 31): True} == PRODUCTION_OVERRIDES
