from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Mapping, Sequence

from investment_strategy.configuration import (
    InMemoryInstrumentRegistry,
    InMemoryParameterSetRegistry,
    StrategyConfigResolver,
)
from investment_strategy.domain import (
    ActiveAssignment,
    DataFrequency,
    DataRequirement,
    EntryPlan,
    ExitPlan,
    InstrumentConfig,
    MarketState,
    ParameterSet,
    StrategyContext,
    StrategyResult,
)
from investment_strategy.strategies import CodeStrategyRegistry


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class WeekdayCalendar:
    def __init__(
        self, *, session_complete: bool = True, holidays: set[date] | None = None
    ) -> None:
        self.session_complete = session_complete
        self.holidays = holidays or set()

    def is_trading_day(self, day: date) -> bool:
        return day.weekday() < 5 and day not in self.holidays

    def previous_trading_day(self, day: date) -> date:
        current = day - timedelta(days=1)
        while not self.is_trading_day(current):
            current -= timedelta(days=1)
        return current

    def latest_completed_trading_day(self, now: datetime) -> date:
        today = now.date()
        if self.is_trading_day(today) and self.is_session_complete(today, now):
            return today
        return self.previous_trading_day(today)

    def trading_days(self, start: date, end: date) -> Sequence[date]:
        days: list[date] = []
        current = start
        while current <= end:
            if self.is_trading_day(current):
                days.append(current)
            current += timedelta(days=1)
        return days

    def is_session_complete(self, day: date, now: datetime) -> bool:
        if day < now.date():
            return True
        if day > now.date():
            return False
        return self.session_complete


class SpyGateway:
    def __init__(
        self,
        records: Sequence[Mapping[str, object]],
        *,
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.calls = 0

    def load_daily(self, symbol: str) -> Sequence[Mapping[str, object]]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.records


class SnapshotGateway:
    def __init__(self, snapshot: Mapping[str, object] | None) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def load_snapshot(self, symbol: str) -> Mapping[str, object] | None:
        self.calls += 1
        return self.snapshot


@dataclass
class TestStrategy:
    __test__ = False
    strategy_id: str = "test-strategy"
    minimum_history: int = 2
    state: MarketState = MarketState.ACCUMULATION
    fail: bool = False
    evaluations: int = 0
    last_context: StrategyContext | None = None

    @property
    def id(self) -> str:
        return self.strategy_id

    def requirements(self) -> DataRequirement:
        return DataRequirement(DataFrequency.DAILY, self.minimum_history)

    def validate_parameters(self, parameters: Mapping[str, object]) -> Mapping[str, object]:
        threshold = parameters.get("threshold", 1)
        if not isinstance(threshold, int) or threshold <= 0:
            raise ValueError("threshold must be a positive int")
        return {"threshold": threshold}

    def evaluate(self, context: StrategyContext) -> StrategyResult:
        self.evaluations += 1
        self.last_context = context
        if self.fail:
            raise RuntimeError("boom")
        return StrategyResult(
            strategy=self.id,
            as_of=context.as_of,
            market_state=self.state,
            entry_plan=EntryPlan(levels=(10.0,), triggers=("entry",)),
            exit_plan=ExitPlan(dynamic_levels=(12.0,), triggers=("protect",)),
            signals={"regime": "test-only"},
            diagnostics={"history": len(context.market_data)},
            reasons=("deterministic fixture",),
        )


def make_resolver(
    strategy: TestStrategy,
    *,
    symbol: str = "00733",
    active: bool = True,
    parameter_owner: str | None = None,
    parameter_values: Mapping[str, object] | None = None,
    include_strategy: bool = True,
    include_parameter: bool = True,
    git_sha: str = "deadbeef",
) -> StrategyConfigResolver:
    instrument = InstrumentConfig(
        symbol=symbol,
        active=(ActiveAssignment(strategy.id, "p1") if active else None),
    )
    parameters = {}
    if include_parameter:
        parameters["p1"] = ParameterSet(
            "p1",
            parameter_owner or strategy.id,
            parameter_values or {"threshold": 1},
        )
    strategies = [strategy] if include_strategy else []
    return StrategyConfigResolver(
        InMemoryInstrumentRegistry({symbol: instrument}),
        InMemoryParameterSetRegistry(parameters),
        CodeStrategyRegistry(strategies),
        git_sha,
    )


def bars(start: date, count: int, *, reverse: bool = False) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    current = start
    while len(records) < count:
        if current.weekday() < 5:
            price = 10 + len(records)
            records.append(
                {
                    "timestamp": current.isoformat(),
                    "open": price,
                    "high": price + 1,
                    "low": price - 1,
                    "close": price + 0.5,
                    "volume": 1000 + len(records),
                }
            )
        current += timedelta(days=1)
    if reverse:
        records.reverse()
    return records


UTC = timezone.utc
