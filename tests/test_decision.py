from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Mapping, Sequence

import pytest

from investment_strategy.configuration import (
    InMemoryInstrumentRegistry,
    InMemoryParameterSetRegistry,
    StrategyConfigResolver,
)
from investment_strategy.decision import DISCLAIMER, DecisionRequest, DecisionService
from investment_strategy.domain import (
    ActiveAssignment,
    InstrumentConfig,
    MarketState,
    ParameterSet,
)
from investment_strategy.strategies import CodeStrategyRegistry

from .helpers import FixedClock, SpyGateway, TestStrategy, WeekdayCalendar, bars, make_resolver


def make_service(
    strategy: TestStrategy,
    records: Sequence[Mapping[str, object]],
    *,
    now: datetime,
    calendar: WeekdayCalendar | None = None,
    resolver: StrategyConfigResolver | None = None,
) -> tuple[DecisionService, SpyGateway]:
    gateway = SpyGateway(records)
    service = DecisionService(
        resolver=resolver or make_resolver(strategy),
        market_data=gateway,
        calendar=calendar or WeekdayCalendar(),
        clock=FixedClock(now),
    )
    return service, gateway


def test_decision_walking_skeleton_success_and_exact_disclaimer() -> None:
    strategy = TestStrategy(minimum_history=2)
    service, _ = make_service(
        strategy,
        bars(date(2026, 8, 7), 2),
        now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc),
    )
    artifact = service.run(DecisionRequest("00733", date(2026, 8, 10)))
    assert artifact["status"] == "SUCCESS"
    assert artifact["strategy"] == "test-strategy"
    assert artifact["parameter_set"] == "p1"
    assert artifact["resolved_as_of"] == "2026-08-10"
    assert artifact["requested_as_of"] == "2026-08-10"
    assert artifact["git_sha"] == "deadbeef"
    assert artifact["data_quality"] == "PASS"
    assert artifact["strategy_result"]["strategy"] == "test-strategy"
    assert artifact["disclaimer"] == DISCLAIMER


def test_configuration_failure_stops_before_market_data_and_strategy() -> None:
    strategy = TestStrategy()
    resolver = StrategyConfigResolver(
        InMemoryInstrumentRegistry(
            {"00733": InstrumentConfig("00733", ActiveAssignment("missing", "p1"))}
        ),
        InMemoryParameterSetRegistry({"p1": ParameterSet("p1", "missing", {})}),
        CodeStrategyRegistry([]),
        "sha",
    )
    service, gateway = make_service(
        strategy,
        bars(date(2026, 8, 7), 2),
        now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc),
        resolver=resolver,
    )
    artifact = service.run(DecisionRequest("00733", date(2026, 8, 10)))
    assert artifact["failure"]["category"] == "CONFIGURATION_FAILED"
    assert artifact["failure"]["code"] == "STRATEGY_NOT_FOUND"
    assert gateway.calls == 0
    assert strategy.evaluations == 0


def test_future_as_of_fails_before_market_data() -> None:
    strategy = TestStrategy()
    service, gateway = make_service(
        strategy,
        bars(date(2026, 8, 10), 2),
        now=datetime(2026, 8, 11, 10, tzinfo=timezone.utc),
    )
    artifact = service.run(DecisionRequest("00733", date(2026, 8, 12)))
    assert artifact["status"] == "FAILED"
    assert artifact["failure"]["code"] == "INVALID_AS_OF"
    assert artifact["requested_as_of"] == "2026-08-12"
    assert "resolved_as_of" not in artifact
    assert gateway.calls == 0


def test_calendar_only_resolution_does_not_fallback_when_resolved_day_is_missing() -> None:
    strategy = TestStrategy(minimum_history=1)
    service, _ = make_service(
        strategy,
        bars(date(2026, 8, 7), 1),
        now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc),
    )
    artifact = service.run(DecisionRequest("00733", date(2026, 8, 10)))
    assert artifact["status"] == "FAILED"
    assert artifact["failure"]["code"] == "STALE_DATA"
    assert "resolved_as_of" not in artifact


@pytest.mark.parametrize(
    ("requested", "session_complete", "expected"),
    [
        (date(2026, 8, 7), True, "2026-08-07"),
        (date(2026, 8, 9), True, "2026-08-07"),
        (date(2026, 8, 11), False, "2026-08-10"),
        (date(2026, 8, 11), True, "2026-08-11"),
    ],
)
def test_decision_as_of_resolution(
    requested: date, session_complete: bool, expected: str
) -> None:
    strategy = TestStrategy(minimum_history=1)
    calendar = WeekdayCalendar(session_complete=session_complete)
    through = date.fromisoformat(expected)
    records = bars(date(2026, 8, 7), 3)
    service, _ = make_service(
        strategy,
        records,
        now=datetime(2026, 8, 11, 15, tzinfo=timezone.utc),
        calendar=calendar,
    )
    artifact = service.run(DecisionRequest("00733", requested))
    assert artifact["status"] == "SUCCESS"
    assert artifact["resolved_as_of"] == through.isoformat()


def test_omitted_as_of_uses_latest_completed_trading_day() -> None:
    strategy = TestStrategy(minimum_history=1)
    calendar = WeekdayCalendar(session_complete=False)
    service, _ = make_service(
        strategy,
        bars(date(2026, 8, 7), 2),
        now=datetime(2026, 8, 11, 10, tzinfo=timezone.utc),
        calendar=calendar,
    )
    artifact = service.run(DecisionRequest("00733"))
    assert artifact["resolved_as_of"] == "2026-08-10"
    assert "requested_as_of" not in artifact


def test_minimum_history_is_threshold_not_truncation() -> None:
    strategy = TestStrategy(minimum_history=2)
    service, _ = make_service(
        strategy,
        bars(date(2026, 8, 5), 4),
        now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc),
    )
    artifact = service.run(DecisionRequest("00733", date(2026, 8, 10)))
    assert artifact["status"] == "SUCCESS"
    assert strategy.last_context is not None
    assert len(strategy.last_context.market_data) == 4


def test_insufficient_history_fails_without_strategy_or_neutral_substitute() -> None:
    strategy = TestStrategy(minimum_history=3, state=MarketState.NEUTRAL)
    service, _ = make_service(
        strategy,
        bars(date(2026, 8, 7), 2),
        now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc),
    )
    artifact = service.run(DecisionRequest("00733", date(2026, 8, 10)))
    assert artifact["failure"]["code"] == "INSUFFICIENT_HISTORY"
    assert strategy.evaluations == 0
    assert "strategy_result" not in artifact


def test_valid_neutral_is_successful() -> None:
    strategy = TestStrategy(minimum_history=1, state=MarketState.NEUTRAL)
    service, _ = make_service(
        strategy,
        bars(date(2026, 8, 10), 1),
        now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc),
    )
    artifact = service.run(DecisionRequest("00733", date(2026, 8, 10)))
    assert artifact["status"] == "SUCCESS"
    assert artifact["strategy_result"]["market_state"] == "NEUTRAL"


def test_strategy_failure_uses_canonical_failed_artifact() -> None:
    strategy = TestStrategy(minimum_history=1, fail=True)
    service, _ = make_service(
        strategy,
        bars(date(2026, 8, 10), 1),
        now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc),
    )
    artifact = service.run(DecisionRequest("00733", date(2026, 8, 10)))
    assert artifact["status"] == "FAILED"
    assert artifact["failure"]["category"] == "STRATEGY_FAILED"
    assert artifact["failure"]["code"] == "STRATEGY_EVALUATION_ERROR"
    assert artifact["failure"]["reason"]
    assert "strategy_result" not in artifact
    assert "strategy" not in artifact
    assert artifact["disclaimer"] == DISCLAIMER
