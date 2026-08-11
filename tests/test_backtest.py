from __future__ import annotations

import inspect
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from investment_strategy.backtest import (
    AssignmentMode,
    BacktestRequest,
    BacktestService,
    serialize_backtest_artifact,
)
from investment_strategy.configuration import (
    InMemoryInstrumentRegistry,
    InMemoryParameterSetRegistry,
    StrategyConfigResolver,
)
from investment_strategy.decision import DISCLAIMER, DecisionRequest, DecisionService
from investment_strategy.domain import (
    InstrumentConfig,
    ParameterSet,
    StrategyContext,
    StrategyResult,
)
from investment_strategy.strategies import CodeStrategyRegistry

from .helpers import FixedClock, SpyGateway, TestStrategy, WeekdayCalendar, bars, make_resolver


def make_backtest(
    strategy: TestStrategy,
    records: Sequence[Mapping[str, object]],
    *,
    resolver: StrategyConfigResolver | None = None,
    calendar: WeekdayCalendar | None = None,
    now: datetime | None = None,
) -> tuple[BacktestService, SpyGateway]:
    gateway = SpyGateway(records)
    service = BacktestService(
        resolver=resolver or make_resolver(strategy),
        market_data=gateway,
        calendar=calendar or WeekdayCalendar(),
        clock=FixedClock(now or datetime(2026, 8, 11, 18, tzinfo=UTC)),
    )
    return service, gateway


def active_request(start: date, end: date) -> BacktestRequest:
    return BacktestRequest("00733", AssignmentMode.ACTIVE, start, end)


def test_backtest_walking_skeleton_is_chronological_and_analytical_only() -> None:
    strategy = TestStrategy(minimum_history=2)
    records = bars(date(2026, 8, 5), 5)
    service, _ = make_backtest(strategy, records)
    artifact = service.run(active_request(date(2026, 8, 7), date(2026, 8, 11)))
    assert artifact["status"] == "SUCCESS"
    assert artifact["disclaimer"] == DISCLAIMER
    dates = [entry["date"] for entry in artifact["timeline"]]
    assert dates == ["2026-08-07", "2026-08-10", "2026-08-11"]
    text = str(artifact).lower()
    for forbidden in ("fill", "position", "cash", "pnl", "return", "drawdown"):
        assert forbidden not in text


def test_decision_and_backtest_share_equivalent_strategy_evaluation() -> None:
    records = bars(date(2026, 8, 5), 4)
    decision_strategy = TestStrategy(minimum_history=2)
    decision = DecisionService(
        resolver=make_resolver(decision_strategy),
        market_data=SpyGateway(records),
        calendar=WeekdayCalendar(),
        clock=FixedClock(datetime(2026, 8, 10, 18, tzinfo=UTC)),
    ).run(DecisionRequest("00733", date(2026, 8, 10)))

    backtest_strategy = TestStrategy(minimum_history=2)
    backtest, _ = make_backtest(backtest_strategy, records)
    replay = backtest.run(active_request(date(2026, 8, 10), date(2026, 8, 10)))
    assert decision["strategy_result"] == replay["timeline"][0]["strategy_result"]


def test_future_loaded_data_cannot_affect_historical_backtest_point() -> None:
    records = bars(date(2026, 8, 5), 5)
    future = dict(records[-1])
    future["timestamp"] = "2026-08-12"
    future["high"] = 1
    records.append(future)
    strategy = TestStrategy(minimum_history=1)
    service, _ = make_backtest(strategy, records)
    artifact = service.run(active_request(date(2026, 8, 10), date(2026, 8, 10)))
    assert artifact["status"] == "SUCCESS"


def test_invalid_ranges_fail_before_market_data() -> None:
    strategy = TestStrategy(minimum_history=1)
    service, gateway = make_backtest(strategy, bars(date(2026, 8, 10), 2))
    for request in (
        active_request(date(2026, 8, 10), date(2026, 8, 9)),
        active_request(date(2026, 8, 10), date(2026, 8, 12)),
        active_request(date(2026, 8, 8), date(2026, 8, 9)),
    ):
        artifact = service.run(request)
        assert artifact["status"] == "FAILED"
        assert artifact["failure"]["code"] == "INVALID_BACKTEST_RANGE"
    assert gateway.calls == 0
    assert strategy.evaluations == 0


def test_non_trading_endpoints_are_not_clamped_outside_interval() -> None:
    strategy = TestStrategy(minimum_history=1)
    service, _ = make_backtest(strategy, bars(date(2026, 8, 7), 2))
    artifact = service.run(active_request(date(2026, 8, 8), date(2026, 8, 10)))
    assert artifact["status"] == "SUCCESS"
    assert [item["date"] for item in artifact["timeline"]] == ["2026-08-10"]


def test_incomplete_current_day_is_excluded_from_range() -> None:
    strategy = TestStrategy(minimum_history=1)
    calendar = WeekdayCalendar(session_complete=False)
    service, _ = make_backtest(
        strategy,
        bars(date(2026, 8, 10), 2),
        calendar=calendar,
        now=datetime(2026, 8, 11, 10, tzinfo=UTC),
    )
    artifact = service.run(active_request(date(2026, 8, 10), date(2026, 8, 11)))
    assert artifact["status"] == "SUCCESS"
    assert [item["date"] for item in artifact["timeline"]] == ["2026-08-10"]


def test_backtest_current_day_uses_calendar_market_timezone() -> None:
    strategy = TestStrategy(minimum_history=1)
    calendar = WeekdayCalendar(
        session_complete=False,
        market_timezone=ZoneInfo("Asia/Taipei"),
    )
    service, _ = make_backtest(
        strategy,
        bars(date(2026, 8, 10), 1),
        calendar=calendar,
        now=datetime(2026, 8, 10, 16, 30, tzinfo=UTC),
    )
    artifact = service.run(active_request(date(2026, 8, 10), date(2026, 8, 11)))
    assert artifact["status"] == "SUCCESS"
    assert [item["date"] for item in artifact["timeline"]] == ["2026-08-10"]


def test_active_missing_assignment_fails_before_data() -> None:
    strategy = TestStrategy("S", minimum_history=1)
    resolver = StrategyConfigResolver(
        InMemoryInstrumentRegistry({"00733": InstrumentConfig("00733", listing_venue="TWSE")}),
        InMemoryParameterSetRegistry({"P": ParameterSet("P", "S", {"threshold": 1})}),
        CodeStrategyRegistry([strategy]),
        "sha",
    )
    service, gateway = make_backtest(strategy, bars(date(2026, 8, 10), 1), resolver=resolver)
    artifact = service.run(active_request(date(2026, 8, 10), date(2026, 8, 10)))
    assert artifact["failure"]["code"] == "ACTIVE_STRATEGY_NOT_CONFIGURED"
    assert gateway.calls == 0


def test_explicit_assignment_works_without_active_and_does_not_mutate_instrument() -> None:
    a = TestStrategy("A", minimum_history=1)
    b = TestStrategy("B", minimum_history=1)
    instrument = InstrumentConfig("00733", None, "TWSE")
    resolver = StrategyConfigResolver(
        InMemoryInstrumentRegistry({"00733": instrument}),
        InMemoryParameterSetRegistry(
            {
                "A1": ParameterSet("A1", "A", {"threshold": 1}),
                "B1": ParameterSet("B1", "B", {"threshold": 1}),
            }
        ),
        CodeStrategyRegistry([a, b]),
        "sha",
    )
    service, _ = make_backtest(b, bars(date(2026, 8, 10), 1), resolver=resolver)
    request = BacktestRequest(
        "00733",
        AssignmentMode.EXPLICIT,
        date(2026, 8, 10),
        date(2026, 8, 10),
        strategy="B",
        parameter_set="B1",
    )
    artifact = service.run(request)
    assert artifact["status"] == "SUCCESS"
    assert artifact["strategy"] == "B"
    assert artifact["parameter_set"] == "B1"
    assert instrument.active is None


def test_preroll_satisfies_history_but_is_not_emitted() -> None:
    strategy = TestStrategy(minimum_history=3)
    service, _ = make_backtest(strategy, bars(date(2026, 8, 5), 4))
    artifact = service.run(active_request(date(2026, 8, 10), date(2026, 8, 10)))
    assert artifact["status"] == "SUCCESS"
    assert len(artifact["timeline"]) == 1
    assert artifact["timeline"][0]["date"] == "2026-08-10"
    assert artifact["timeline"][0]["status"] == "EVALUATED"
    assert artifact["timeline"][0]["strategy_result"]["diagnostics"]["history"] == 4


def test_warmup_is_distinct_and_mixed_range_can_succeed() -> None:
    strategy = TestStrategy(minimum_history=3)
    service, _ = make_backtest(strategy, bars(date(2026, 8, 5), 4))
    artifact = service.run(active_request(date(2026, 8, 5), date(2026, 8, 10)))
    assert artifact["status"] == "SUCCESS"
    statuses = [item["status"] for item in artifact["timeline"]]
    assert statuses == ["WARMUP", "WARMUP", "EVALUATED", "EVALUATED"]


def test_all_warmup_fails_without_successful_empty_timeline() -> None:
    strategy = TestStrategy(minimum_history=5)
    service, _ = make_backtest(strategy, bars(date(2026, 8, 5), 3))
    artifact = service.run(active_request(date(2026, 8, 5), date(2026, 8, 7)))
    assert artifact["status"] == "FAILED"
    assert artifact["failure"]["code"] == "INSUFFICIENT_HISTORY"
    assert "timeline" not in artifact


def test_invalid_required_data_fails_instead_of_skipping() -> None:
    records = bars(date(2026, 8, 5), 3)
    records[1]["volume"] = -1
    strategy = TestStrategy(minimum_history=1)
    service, _ = make_backtest(strategy, records)
    artifact = service.run(active_request(date(2026, 8, 5), date(2026, 8, 7)))
    assert artifact["status"] == "FAILED"
    assert artifact["failure"]["category"] == "DATA_FAILED"
    assert strategy.evaluations == 0


def test_strategy_failure_is_fail_fast_and_partial_timeline_is_not_public_success() -> None:
    class FailSecond(TestStrategy):
        def evaluate(self, context: StrategyContext) -> StrategyResult:
            if self.evaluations == 1:
                self.fail = True
            return super().evaluate(context)

    strategy = FailSecond(minimum_history=1)
    service, _ = make_backtest(strategy, bars(date(2026, 8, 5), 3))
    artifact = service.run(active_request(date(2026, 8, 5), date(2026, 8, 7)))
    assert artifact["status"] == "FAILED"
    assert artifact["failure"]["category"] == "STRATEGY_FAILED"
    assert "timeline" not in artifact


def test_backtest_success_and_failure_artifacts_serialize_to_json() -> None:
    strategy = TestStrategy(minimum_history=1)
    service, _ = make_backtest(strategy, bars(date(2026, 8, 10), 1))

    success = service.run(active_request(date(2026, 8, 10), date(2026, 8, 10)))
    assert json.loads(serialize_backtest_artifact(success)) == success

    failure = service.run(active_request(date(2026, 8, 12), date(2026, 8, 12)))
    assert failure["status"] == "FAILED"
    assert json.loads(serialize_backtest_artifact(failure)) == failure


def test_backtest_has_no_execution_simulator_dependency() -> None:
    import investment_strategy.backtest.service as service_module

    source = inspect.getsource(service_module).lower()
    assert "execution" not in source
    assert "fill" not in source
