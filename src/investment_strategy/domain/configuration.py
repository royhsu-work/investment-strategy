from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class ActiveAssignment:
    strategy: str
    parameter_set: str


@dataclass(frozen=True, slots=True)
class MarketDataInstrument:
    symbol: str
    listing_venue: str


@dataclass(frozen=True, slots=True)
class InstrumentConfig:
    symbol: str
    active: ActiveAssignment | None = None
    listing_venue: str | None = None


@dataclass(frozen=True, slots=True)
class ParameterSet:
    id: str
    strategy: str
    parameters: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True, slots=True)
class ResolvedStrategyConfig:
    symbol: str
    strategy: str
    parameter_set: str
    resolved_parameters: Mapping[str, object]
    git_sha: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "resolved_parameters",
            MappingProxyType(dict(self.resolved_parameters)),
        )
