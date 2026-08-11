from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class MarketState(StrEnum):
    NEUTRAL = "NEUTRAL"
    ACCUMULATION = "ACCUMULATION"
    TREND = "TREND"
    REVERSAL_RISK = "REVERSAL_RISK"


@dataclass(frozen=True, slots=True)
class EntryPlan:
    levels: tuple[float, ...] = ()
    triggers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExitPlan:
    dynamic_levels: tuple[float, ...] = ()
    triggers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StrategyResult:
    strategy: str
    as_of: date
    market_state: MarketState
    entry_plan: EntryPlan = EntryPlan()
    exit_plan: ExitPlan = ExitPlan()
    signals: Mapping[str, object] = MappingProxyType({})
    diagnostics: Mapping[str, object] = MappingProxyType({})
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "signals", MappingProxyType(dict(self.signals)))
        object.__setattr__(self, "diagnostics", MappingProxyType(dict(self.diagnostics)))

    def to_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "as_of": self.as_of.isoformat(),
            "market_state": self.market_state.value,
            "entry_plan": {
                "levels": list(self.entry_plan.levels),
                "triggers": list(self.entry_plan.triggers),
            },
            "exit_plan": {
                "dynamic_levels": list(self.exit_plan.dynamic_levels),
                "triggers": list(self.exit_plan.triggers),
            },
            "signals": dict(self.signals),
            "diagnostics": dict(self.diagnostics),
            "reasons": list(self.reasons),
        }
