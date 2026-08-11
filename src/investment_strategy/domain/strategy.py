from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from .configuration import ResolvedStrategyConfig
from .market_data import DailyBar, DataRequirement
from .result import StrategyResult


@dataclass(frozen=True, slots=True)
class StrategyContext:
    instrument: str
    as_of: date
    market_data: tuple[DailyBar, ...]
    resolved_config: ResolvedStrategyConfig


class Strategy(Protocol):
    @property
    def id(self) -> str: ...

    def requirements(self) -> DataRequirement: ...

    def validate_parameters(self, parameters: Mapping[str, object]) -> Mapping[str, object]: ...

    def evaluate(self, context: StrategyContext) -> StrategyResult: ...


def evaluate_strategy(
    strategy: Strategy,
    *,
    instrument: str,
    as_of: date,
    bars: Sequence[DailyBar],
    resolved_config: ResolvedStrategyConfig,
) -> StrategyResult:
    result = strategy.evaluate(
        StrategyContext(
            instrument=instrument,
            as_of=as_of,
            market_data=tuple(bars),
            resolved_config=resolved_config,
        )
    )
    if result.strategy != strategy.id or result.as_of != as_of:
        raise ValueError("strategy result identity/as_of mismatch")
    return result
