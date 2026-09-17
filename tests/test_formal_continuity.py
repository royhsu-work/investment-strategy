from __future__ import annotations

from datetime import date

import pytest

from investment_strategy.data import prepare_bars, validate_continuity_and_freshness
from investment_strategy.domain import ApplicationFailure, MarketDataInstrument

from .helpers import SpyGateway, WeekdayCalendar

INSTRUMENT = MarketDataInstrument("00733", "TWSE")


def records(days: list[date]) -> list[dict[str, object]]:
    return [
        {
            "timestamp": day.isoformat(),
            "open": 10,
            "high": 11,
            "low": 9,
            "close": 10.5,
            "volume": 100,
        }
        for day in days
    ]


def test_gap_before_selected_formal_range_does_not_fail_continuity() -> None:
    normalized = prepare_bars(
        SpyGateway(
            records(
                [
                    date(2026, 1, 5),
                    date(2026, 1, 7),
                    date(2026, 1, 8),
                    date(2026, 1, 9),
                ]
            )
        ),
        INSTRUMENT,
        through=date(2026, 1, 9),
    )
    validate_continuity_and_freshness(
        normalized,
        calendar=WeekdayCalendar(),
        resolved_as_of=date(2026, 1, 9),
        continuity_start=date(2026, 1, 7),
    )


def test_gap_inside_selected_formal_range_still_fails() -> None:
    normalized = prepare_bars(
        SpyGateway(records([date(2026, 1, 5), date(2026, 1, 7), date(2026, 1, 9)])),
        INSTRUMENT,
        through=date(2026, 1, 9),
    )
    with pytest.raises(ApplicationFailure) as exc:
        validate_continuity_and_freshness(
            normalized,
            calendar=WeekdayCalendar(),
            resolved_as_of=date(2026, 1, 9),
            continuity_start=date(2026, 1, 7),
        )
    assert exc.value.failure.code == "DATA_GAP"


def test_freshness_remains_tied_to_resolved_as_of() -> None:
    normalized = prepare_bars(
        SpyGateway(records([date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)])),
        INSTRUMENT,
        through=date(2026, 1, 8),
    )
    with pytest.raises(ApplicationFailure) as exc:
        validate_continuity_and_freshness(
            normalized,
            calendar=WeekdayCalendar(),
            resolved_as_of=date(2026, 1, 8),
            continuity_start=date(2026, 1, 5),
        )
    assert exc.value.failure.code == "STALE_DATA"


def test_extra_older_provider_breadth_does_not_change_selected_history() -> None:
    common = [date(2026, 1, 7), date(2026, 1, 8), date(2026, 1, 9)]
    narrow = prepare_bars(SpyGateway(records(common)), INSTRUMENT, through=date(2026, 1, 9))
    broad = prepare_bars(
        SpyGateway(records([date(2026, 1, 2), date(2026, 1, 5), *common])),
        INSTRUMENT,
        through=date(2026, 1, 9),
    )
    for candidate in (narrow, broad):
        validate_continuity_and_freshness(
            candidate,
            calendar=WeekdayCalendar(),
            resolved_as_of=date(2026, 1, 9),
            continuity_start=date(2026, 1, 7),
        )
    assert tuple(bar for bar in broad if bar.trading_timestamp >= date(2026, 1, 7)) == narrow
