from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from investment_strategy.backtest import AssignmentMode, BacktestRequest, BacktestService
from investment_strategy.decision import DecisionRequest, DecisionService
from investment_strategy.infrastructure.taiwan_calendar import TaiwanTradingCalendar
from investment_strategy.infrastructure.yfinance_eod import YFinanceEodGateway

from .helpers import FixedClock, TestStrategy, make_resolver


class FakeFrame:
    def __init__(self, rows: list[tuple[date, dict[str, object]]]) -> None:
        self._rows = rows
        self.empty = not rows

    def iterrows(self) -> list[tuple[date, dict[str, object]]]:
        return self._rows


class FakeTaiwanEngine:
    first_session = date(2020, 1, 2)
    last_session = date(2030, 12, 31)

    def __init__(self, sessions: set[date]) -> None:
        self.sessions = sessions

    def is_session(self, day: date) -> bool:
        return day in self.sessions

    def sessions_in_range(self, start: date, end: date) -> tuple[date, ...]:
        return tuple(sorted(day for day in self.sessions if start <= day <= end))


def provider_rows(days: list[date]) -> FakeFrame:
    rows: list[tuple[date, dict[str, object]]] = []
    for index, day in enumerate(days):
        price = 50 + index
        rows.append(
            (
                day,
                {
                    "Open": price,
                    "High": price + 2,
                    "Low": price - 1,
                    "Close": price + 1,
                    "Volume": 1_000 + index,
                    "Adj Close": 9_999,
                },
            )
        )
    return FakeFrame(rows)


def history_loader_for(frame: FakeFrame, calls: list[tuple[str, dict[str, object]]]) -> Any:
    def load(ticker: str, **kwargs: object) -> FakeFrame:
        calls.append((ticker, dict(kwargs)))
        return frame

    return load


def test_decision_composes_taiwan_calendar_and_concrete_eod_adapter() -> None:
    sessions = {date(2026, 8, 7), date(2026, 8, 10), date(2026, 8, 11)}
    calendar = TaiwanTradingCalendar(engine=FakeTaiwanEngine(sessions))
    calls: list[tuple[str, dict[str, object]]] = []
    gateway = YFinanceEodGateway(
        history_loader=history_loader_for(
            provider_rows([date(2026, 8, 7), date(2026, 8, 10), date(2026, 8, 11)]),
            calls,
        )
    )
    strategy = TestStrategy(minimum_history=2)
    artifact = DecisionService(
        resolver=make_resolver(strategy, listing_venue="TWSE"),
        market_data=gateway,
        calendar=calendar,
        clock=FixedClock(datetime(2026, 8, 11, 6, 0, tzinfo=UTC)),
    ).run(DecisionRequest("00733", date(2026, 8, 10)))

    assert artifact["status"] == "SUCCESS"
    assert calls[0][0] == "00733.TW"
    assert strategy.last_context is not None
    assert [bar.trading_timestamp for bar in strategy.last_context.market_data] == [
        date(2026, 8, 7),
        date(2026, 8, 10),
    ]
    assert strategy.last_context.instrument == "00733"
    assert not hasattr(strategy.last_context, "listing_venue")
    assert "Adj Close" not in str(strategy.last_context.market_data)


def test_backtest_composition_preserves_warmup_chronology_and_provider_isolation() -> None:
    days = [
        date(2026, 8, 5),
        date(2026, 8, 6),
        date(2026, 8, 7),
        date(2026, 8, 10),
        date(2026, 8, 11),
    ]
    calendar = TaiwanTradingCalendar(engine=FakeTaiwanEngine(set(days)))
    calls: list[tuple[str, dict[str, object]]] = []
    gateway = YFinanceEodGateway(history_loader=history_loader_for(provider_rows(days), calls))
    strategy = TestStrategy(minimum_history=3)
    artifact = BacktestService(
        resolver=make_resolver(strategy, symbol="00679B", listing_venue="TPEX"),
        market_data=gateway,
        calendar=calendar,
        clock=FixedClock(datetime(2026, 8, 11, 6, 0, tzinfo=UTC)),
    ).run(
        BacktestRequest(
            "00679B",
            AssignmentMode.ACTIVE,
            date(2026, 8, 5),
            date(2026, 8, 11),
        )
    )

    assert artifact["status"] == "SUCCESS"
    assert calls[0][0] == "00679B.TWO"
    assert [item["status"] for item in artifact["timeline"]] == [
        "WARMUP",
        "WARMUP",
        "EVALUATED",
        "EVALUATED",
        "EVALUATED",
    ]
    assert strategy.last_context is not None
    assert strategy.last_context.instrument == "00679B"
    assert not hasattr(strategy.last_context, "listing_venue")


def test_incomplete_current_session_is_excluded_from_formal_decision_input() -> None:
    sessions = {date(2026, 8, 10), date(2026, 8, 11)}
    calendar = TaiwanTradingCalendar(engine=FakeTaiwanEngine(sessions))
    gateway = YFinanceEodGateway(
        history_loader=history_loader_for(
            provider_rows([date(2026, 8, 10), date(2026, 8, 11)]), []
        )
    )
    strategy = TestStrategy(minimum_history=1)
    artifact = DecisionService(
        resolver=make_resolver(strategy),
        market_data=gateway,
        calendar=calendar,
        clock=FixedClock(datetime(2026, 8, 11, 5, 0, tzinfo=UTC)),
    ).run(DecisionRequest("00733"))

    assert artifact["status"] == "SUCCESS"
    assert artifact["resolved_as_of"] == "2026-08-10"
    assert strategy.last_context is not None
    assert [bar.trading_timestamp for bar in strategy.last_context.market_data] == [
        date(2026, 8, 10)
    ]


def test_missing_latest_completed_session_remains_stale_data() -> None:
    sessions = {date(2026, 8, 10), date(2026, 8, 11)}
    calendar = TaiwanTradingCalendar(engine=FakeTaiwanEngine(sessions))
    gateway = YFinanceEodGateway(
        history_loader=history_loader_for(provider_rows([date(2026, 8, 10)]), [])
    )
    strategy = TestStrategy(minimum_history=1)
    artifact = DecisionService(
        resolver=make_resolver(strategy),
        market_data=gateway,
        calendar=calendar,
        clock=FixedClock(datetime(2026, 8, 11, 6, 0, tzinfo=UTC)),
    ).run(DecisionRequest("00733", date(2026, 8, 11)))

    assert artifact["status"] == "FAILED"
    assert artifact["failure"]["category"] == "DATA_FAILED"
    assert artifact["failure"]["code"] == "STALE_DATA"
    assert strategy.evaluations == 0


def test_calendar_unavailable_is_not_rewritten_as_market_data_failure() -> None:
    calendar = TaiwanTradingCalendar(engine=FakeTaiwanEngine({date(2026, 8, 10)}))
    gateway = YFinanceEodGateway(
        history_loader=history_loader_for(provider_rows([date(2026, 8, 10)]), [])
    )
    strategy = TestStrategy(minimum_history=1)
    artifact = BacktestService(
        resolver=make_resolver(strategy),
        market_data=gateway,
        calendar=calendar,
        clock=FixedClock(datetime(2031, 1, 2, 6, 0, tzinfo=UTC)),
    ).run(
        BacktestRequest(
            "00733",
            AssignmentMode.ACTIVE,
            date(2031, 1, 2),
            date(2031, 1, 2),
        )
    )

    assert artifact["status"] == "FAILED"
    assert artifact["failure"]["category"] == "DATA_FAILED"
    assert artifact["failure"]["code"] == "CALENDAR_UNAVAILABLE"
    assert strategy.evaluations == 0
