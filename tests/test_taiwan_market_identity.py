from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from investment_strategy.backtest import AssignmentMode, BacktestRequest, BacktestService
from investment_strategy.configuration import (
    InMemoryInstrumentRegistry,
    InMemoryParameterSetRegistry,
    StrategyConfigResolver,
    YamlInstrumentRegistry,
)
from investment_strategy.decision import DecisionRequest, DecisionService
from investment_strategy.domain import (
    ActiveAssignment,
    InstrumentConfig,
    MarketDataInstrument,
    ParameterSet,
)
from investment_strategy.strategies import CodeStrategyRegistry

from .helpers import FixedClock, SpyGateway, TestStrategy, WeekdayCalendar, bars


def make_resolver(symbol: str, venue: str | None, strategy: TestStrategy) -> StrategyConfigResolver:
    return StrategyConfigResolver(
        InMemoryInstrumentRegistry(
            {
                symbol: InstrumentConfig(
                    symbol=symbol,
                    active=ActiveAssignment(strategy.id, "p1"),
                    listing_venue=venue,
                )
            }
        ),
        InMemoryParameterSetRegistry(
            {"p1": ParameterSet("p1", strategy.id, {"threshold": 1})}
        ),
        CodeStrategyRegistry([strategy]),
        "sha",
    )


@pytest.mark.parametrize(
    ("symbol", "venue", "service_kind"),
    [
        ("00733", "TWSE", "decision"),
        ("00679B", "TPEX", "backtest"),
    ],
)
def test_services_load_provider_neutral_market_identity_but_strategy_stays_symbol_only(
    symbol: str, venue: str, service_kind: str
) -> None:
    strategy = TestStrategy(minimum_history=1)
    resolver = make_resolver(symbol, venue, strategy)
    gateway = SpyGateway(bars(date(2026, 8, 10), 2))
    calendar = WeekdayCalendar()
    clock = FixedClock(datetime(2026, 8, 11, 18, tzinfo=UTC))

    if service_kind == "decision":
        artifact = DecisionService(
            resolver=resolver,
            market_data=gateway,
            calendar=calendar,
            clock=clock,
        ).run(DecisionRequest(symbol, date(2026, 8, 11)))
    else:
        artifact = BacktestService(
            resolver=resolver,
            market_data=gateway,
            calendar=calendar,
            clock=clock,
        ).run(
            BacktestRequest(
                symbol,
                AssignmentMode.ACTIVE,
                date(2026, 8, 11),
                date(2026, 8, 11),
            )
        )

    assert artifact["status"] == "SUCCESS"
    assert gateway.last_instrument == MarketDataInstrument(symbol=symbol, listing_venue=venue)
    assert strategy.last_context is not None
    assert strategy.last_context.instrument == symbol
    assert not hasattr(strategy.last_context, "listing_venue")
    assert not hasattr(strategy.last_context.resolved_config, "market_data_instrument")


@pytest.mark.parametrize(
    ("venue", "expected"),
    [
        (None, "LISTING_VENUE_NOT_CONFIGURED"),
        ("00733.TW", "UNSUPPORTED_LISTING_VENUE"),
        ("NYSE", "UNSUPPORTED_LISTING_VENUE"),
    ],
)
def test_invalid_listing_venue_fails_before_market_data_and_strategy(
    venue: str | None, expected: str
) -> None:
    strategy = TestStrategy(minimum_history=1)
    gateway = SpyGateway(bars(date(2026, 8, 10), 1))
    artifact = DecisionService(
        resolver=make_resolver("00733", venue, strategy),
        market_data=gateway,
        calendar=WeekdayCalendar(),
        clock=FixedClock(datetime(2026, 8, 10, 18, tzinfo=UTC)),
    ).run(DecisionRequest("00733", date(2026, 8, 10)))

    assert artifact["status"] == "FAILED"
    assert artifact["failure"]["category"] == "CONFIGURATION_FAILED"
    assert artifact["failure"]["code"] == expected
    assert gateway.calls == 0
    assert strategy.evaluations == 0


def test_yaml_registry_loads_venue_independently_of_active_assignment(tmp_path: Path) -> None:
    path = tmp_path / "instruments.yaml"
    path.write_text(
        "instruments:\n"
        "  '00733':\n"
        "    listing_venue: TWSE\n"
        "    active:\n"
        "      strategy: demo\n"
        "      parameter_set: demo-v1\n"
        "  '00679B':\n"
        "    listing_venue: TPEX\n",
        encoding="utf-8",
    )
    registry = YamlInstrumentRegistry(path)

    twse = registry.get("00733")
    tpex = registry.get("00679B")
    assert twse is not None and twse.listing_venue == "TWSE"
    assert tpex is not None and tpex.listing_venue == "TPEX"
    assert tpex.active is None
