from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest

from investment_strategy.domain import (
    DataFrequency,
    DataRequirement,
    DailyBar,
    EntryPlan,
    ExitPlan,
    MarketState,
    ResolvedStrategyConfig,
    StrategyContext,
    StrategyResult,
)


def test_only_daily_frequency_is_exposed() -> None:
    assert list(DataFrequency) == [DataFrequency.DAILY]
    assert DataRequirement(DataFrequency.DAILY, 20).minimum_history == 20


def test_common_market_states_are_exactly_the_four_approved_values() -> None:
    assert {state.value for state in MarketState} == {
        "NEUTRAL",
        "ACCUMULATION",
        "TREND",
        "REVERSAL_RISK",
    }


def test_core_values_are_immutable_and_do_not_contain_execution_state() -> None:
    config = ResolvedStrategyConfig("X", "S", "P", {"threshold": 1}, "sha")
    bar = DailyBar(
        date(2026, 1, 2), *(Decimal(str(v)) for v in (10, 11, 9, 10.5, 100))
    )
    context = StrategyContext("X", date(2026, 1, 2), (bar,), config)
    result = StrategyResult(
        "S",
        date(2026, 1, 2),
        MarketState.TREND,
        EntryPlan((10.0,), ("condition",)),
        ExitPlan((9.0,), ("protect",)),
        {"regime": "strategy-specific"},
        {"model": "strategy-specific"},
    )
    for value in (DataRequirement(DataFrequency.DAILY, 1), config, bar, context, result):
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            value.__setattr__("x", 1)
    assert not hasattr(context, "cash")
    assert not hasattr(context, "position")
    assert not hasattr(context, "average_cost")
    assert not hasattr(context, "benchmark")
    assert not hasattr(result, "fill")
    assert not hasattr(result, "pnl")
    assert result.exit_plan.dynamic_levels == (9.0,)
