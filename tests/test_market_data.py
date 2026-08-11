from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pytest

from investment_strategy.data import prepare_bars, validate_continuity_and_freshness
from investment_strategy.domain import ApplicationFailure, MarketDataInstrument

from .helpers import SpyGateway, WeekdayCalendar, bars

INSTRUMENT = MarketDataInstrument("X", "TWSE")


def failure_code(exc: pytest.ExceptionInfo[ApplicationFailure]) -> str:
    assert exc.value.failure.category.value == "DATA_FAILED"
    return exc.value.failure.code


def test_reverse_provider_order_normalizes_to_chronological() -> None:
    gateway = SpyGateway(bars(date(2026, 1, 5), 3, reverse=True))
    result = prepare_bars(gateway, INSTRUMENT, through=date(2026, 1, 7))
    assert [bar.trading_timestamp for bar in result] == [
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
    ]


def test_duplicate_timestamp_fails() -> None:
    records = bars(date(2026, 1, 5), 2)
    records.append(dict(records[0]))
    with pytest.raises(ApplicationFailure) as exc:
        prepare_bars(SpyGateway(records), INSTRUMENT, through=date(2026, 1, 6))
    assert failure_code(exc) == "DUPLICATE_TIMESTAMP"


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda row: row.pop("volume"), "MISSING_REQUIRED_FIELD"),
        (lambda row: row.__setitem__("volume", -1), "VALIDATION_ERROR"),
        (lambda row: row.__setitem__("high", 1), "INVALID_OHLC"),
        (lambda row: row.__setitem__("open", 0), "INVALID_OHLC"),
        (lambda row: row.__setitem__("timestamp", "not-a-date"), "VALIDATION_ERROR"),
    ],
)
def test_structural_validation_codes(
    mutate: Callable[[dict[str, object]], object],
    code: str,
) -> None:
    records = bars(date(2026, 1, 5), 1)
    mutate(records[0])
    with pytest.raises(ApplicationFailure) as exc:
        prepare_bars(SpyGateway(records), INSTRUMENT, through=date(2026, 1, 5))
    assert failure_code(exc) == code


def test_provider_failure_and_zero_candidates_are_data_unavailable() -> None:
    for gateway in (SpyGateway([], error=RuntimeError("offline")), SpyGateway([])):
        with pytest.raises(ApplicationFailure) as exc:
            prepare_bars(gateway, INSTRUMENT, through=date(2026, 1, 5))
        assert failure_code(exc) == "DATA_UNAVAILABLE"


def test_acquired_invalid_observation_is_not_reclassified_as_unavailable() -> None:
    record = {"timestamp": "bad", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1}
    with pytest.raises(ApplicationFailure) as exc:
        prepare_bars(SpyGateway([record]), INSTRUMENT, through=date(2026, 1, 5))
    assert failure_code(exc) == "VALIDATION_ERROR"


def test_timestamp_known_future_invalid_row_does_not_contaminate_historical_validation() -> None:
    records = bars(date(2026, 1, 5), 3)
    future = dict(records[-1])
    future["timestamp"] = "2026-01-08"
    future["high"] = 1
    records.append(future)
    result = prepare_bars(SpyGateway(records), INSTRUMENT, through=date(2026, 1, 7))
    assert len(result) == 3
    assert result[-1].trading_timestamp == date(2026, 1, 7)


def test_weekend_and_holiday_are_not_gaps_but_missing_trading_day_is() -> None:
    calendar = WeekdayCalendar(holidays={date(2026, 1, 12)})
    records = [
        {"timestamp": "2026-01-09", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1},
        {"timestamp": "2026-01-13", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1},
    ]
    normalized = prepare_bars(SpyGateway(records), INSTRUMENT, through=date(2026, 1, 13))
    validate_continuity_and_freshness(
        normalized, calendar=calendar, resolved_as_of=date(2026, 1, 13)
    )

    gap_records = bars(date(2026, 1, 5), 3)
    del gap_records[1]
    normalized_gap = prepare_bars(SpyGateway(gap_records), INSTRUMENT, through=date(2026, 1, 7))
    with pytest.raises(ApplicationFailure) as exc:
        validate_continuity_and_freshness(
            normalized_gap,
            calendar=WeekdayCalendar(),
            resolved_as_of=date(2026, 1, 7),
        )
    assert failure_code(exc) == "DATA_GAP"


def test_missing_latest_required_completed_day_is_stale() -> None:
    normalized = prepare_bars(
        SpyGateway(bars(date(2026, 1, 5), 2)),
        INSTRUMENT,
        through=date(2026, 1, 7),
    )
    with pytest.raises(ApplicationFailure) as exc:
        validate_continuity_and_freshness(
            normalized,
            calendar=WeekdayCalendar(),
            resolved_as_of=date(2026, 1, 7),
        )
    assert failure_code(exc) == "STALE_DATA"
