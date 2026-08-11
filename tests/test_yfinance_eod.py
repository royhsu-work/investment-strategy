from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pytest

from investment_strategy.data import prepare_bars
from investment_strategy.domain import ApplicationFailure, MarketDataInstrument
from investment_strategy.infrastructure.yfinance_eod import YFinanceEodGateway


class FakeFrame:
    def __init__(self, rows: list[tuple[object, Mapping[str, object]]]) -> None:
        self._rows = rows

    @property
    def empty(self) -> bool:
        return not self._rows

    def iterrows(self) -> list[tuple[object, Mapping[str, object]]]:
        return self._rows


class CapturingLoader:
    def __init__(self, frame: FakeFrame | None = None, error: Exception | None = None) -> None:
        self.frame = frame or FakeFrame([])
        self.error = error
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __call__(self, ticker: str, **kwargs: object) -> Any:
        self.calls.append((ticker, dict(kwargs)))
        if self.error is not None:
            raise self.error
        return self.frame


@pytest.mark.parametrize(
    ("instrument", "ticker"),
    [
        (MarketDataInstrument("00733", "TWSE"), "00733.TW"),
        (MarketDataInstrument("00679B", "TPEX"), "00679B.TWO"),
    ],
)
def test_provider_ticker_mapping_is_adapter_only(
    instrument: MarketDataInstrument, ticker: str
) -> None:
    loader = CapturingLoader(
        FakeFrame(
            [
                (
                    "2026-08-10",
                    {"Open": 10, "High": 11, "Low": 9, "Close": 10.5, "Volume": 100},
                )
            ]
        )
    )
    records = YFinanceEodGateway(history_loader=loader).load_daily(instrument)

    assert loader.calls[0][0] == ticker
    assert records == (
        {
            "timestamp": "2026-08-10",
            "open": 10,
            "high": 11,
            "low": 9,
            "close": 10.5,
            "volume": 100,
        },
    )


def test_source_native_daily_history_is_passed_through_without_adapter_transformation() -> None:
    loader = CapturingLoader(
        FakeFrame(
            [
                (
                    "2026-08-10",
                    {
                        "Open": 10.125,
                        "High": 11.375,
                        "Low": 9.625,
                        "Close": 10.875,
                        "Adj Close": 99.0,
                        "Volume": 123_456,
                        "Dividends": 1,
                        "Stock Splits": 2,
                        "Repaired?": True,
                    },
                )
            ]
        )
    )
    records = YFinanceEodGateway(history_loader=loader).load_daily(
        MarketDataInstrument("00733", "TWSE")
    )

    _, kwargs = loader.calls[0]
    assert kwargs == {
        "period": "max",
        "interval": "1d",
        "prepost": False,
        "auto_adjust": False,
        "back_adjust": False,
        "repair": False,
        "actions": False,
        "rounding": False,
        "raise_errors": True,
    }
    assert records == (
        {
            "timestamp": "2026-08-10",
            "open": 10.125,
            "high": 11.375,
            "low": 9.625,
            "close": 10.875,
            "volume": 123_456,
        },
    )


def test_candidate_conversion_does_not_fill_missing_or_invalid_values() -> None:
    loader = CapturingLoader(
        FakeFrame(
            [
                (
                    "2026-08-10",
                    {"Open": 10, "High": 11, "Low": 9, "Close": 10.5},
                )
            ]
        )
    )
    records = YFinanceEodGateway(history_loader=loader).load_daily(
        MarketDataInstrument("00733", "TWSE")
    )
    assert "volume" not in records[0]

    with pytest.raises(ApplicationFailure) as exc:
        prepare_bars(
            YFinanceEodGateway(history_loader=loader),
            MarketDataInstrument("00733", "TWSE"),
            through=date(2026, 8, 10),
        )
    assert exc.value.failure.code == "MISSING_REQUIRED_FIELD"


def test_adapter_exception_and_empty_response_reach_data_unavailable() -> None:
    instrument = MarketDataInstrument("00733", "TWSE")
    for loader in (CapturingLoader(error=RuntimeError("offline")), CapturingLoader()):
        with pytest.raises(ApplicationFailure) as exc:
            prepare_bars(
                YFinanceEodGateway(history_loader=loader),
                instrument,
                through=date(2026, 8, 10),
            )
        assert exc.value.failure.code == "DATA_UNAVAILABLE"
