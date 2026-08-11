from __future__ import annotations

from pathlib import Path

import pytest

from investment_strategy.configuration import (
    InMemoryInstrumentRegistry,
    InMemoryParameterSetRegistry,
    StrategyConfigResolver,
    YamlInstrumentRegistry,
    YamlParameterSetRegistry,
)
from investment_strategy.domain import (
    ActiveAssignment,
    ApplicationFailure,
    InstrumentConfig,
    ParameterSet,
)
from investment_strategy.strategies import CodeStrategyRegistry

from .helpers import TestStrategy


def assert_config_failure(exc: pytest.ExceptionInfo[ApplicationFailure], code: str) -> None:
    assert exc.value.failure.category.value == "CONFIGURATION_FAILED"
    assert exc.value.failure.code == code


def test_resolver_selects_configured_active_assignment_not_first_registry_entry() -> None:
    a = TestStrategy("A")
    b = TestStrategy("B")
    resolver = StrategyConfigResolver(
        InMemoryInstrumentRegistry(
            {"X": InstrumentConfig("X", ActiveAssignment("B", "B1"))}
        ),
        InMemoryParameterSetRegistry(
            {
                "A1": ParameterSet("A1", "A", {"threshold": 1}),
                "B1": ParameterSet("B1", "B", {"threshold": 2}),
            }
        ),
        CodeStrategyRegistry([a, b]),
        "sha",
    )
    strategy, config = resolver.resolve_active("X")
    assert strategy.id == "B"
    assert config.strategy == "B"
    assert config.parameter_set == "B1"
    assert config.resolved_parameters["threshold"] == 2


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("instrument", "INSTRUMENT_NOT_FOUND"),
        ("active", "ACTIVE_STRATEGY_NOT_CONFIGURED"),
        ("strategy", "STRATEGY_NOT_FOUND"),
        ("parameter", "PARAMETER_SET_NOT_FOUND"),
        ("mismatch", "STRATEGY_PARAMETER_MISMATCH"),
        ("invalid", "INVALID_STRATEGY_PARAMETERS"),
    ],
)
def test_configuration_failure_codes(kind: str, expected: str) -> None:
    strategy = TestStrategy("S")
    instruments = {"X": InstrumentConfig("X", ActiveAssignment("S", "P"))}
    parameter_sets = {"P": ParameterSet("P", "S", {"threshold": 1})}
    strategies = [strategy]
    if kind == "instrument":
        instruments = {}
    elif kind == "active":
        instruments = {"X": InstrumentConfig("X")}
    elif kind == "strategy":
        strategies = []
    elif kind == "parameter":
        parameter_sets = {}
    elif kind == "mismatch":
        parameter_sets = {"P": ParameterSet("P", "OTHER", {"threshold": 1})}
    elif kind == "invalid":
        parameter_sets = {"P": ParameterSet("P", "S", {"threshold": 0})}

    resolver = StrategyConfigResolver(
        InMemoryInstrumentRegistry(instruments),
        InMemoryParameterSetRegistry(parameter_sets),
        CodeStrategyRegistry(strategies),
        "sha",
    )
    with pytest.raises(ApplicationFailure) as exc:
        resolver.resolve_active("X")
    assert_config_failure(exc, expected)


def test_yaml_registry_adapters(tmp_path: Path) -> None:
    instruments = tmp_path / "instruments.yaml"
    params = tmp_path / "parameter_sets.yaml"
    instruments.write_text(
        "instruments:\n  '00733':\n    active:\n      strategy: demo\n      parameter_set: demo-v1\n",
        encoding="utf-8",
    )
    params.write_text(
        "parameter_sets:\n  demo-v1:\n    strategy: demo\n    parameters:\n      threshold: 3\n",
        encoding="utf-8",
    )
    instrument = YamlInstrumentRegistry(instruments).get("00733")
    parameter = YamlParameterSetRegistry(params).get("demo-v1")
    assert instrument is not None and instrument.active is not None
    assert instrument.active.strategy == "demo"
    assert parameter is not None and parameter.parameters["threshold"] == 3
