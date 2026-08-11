from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

import yaml

from investment_strategy.domain.configuration import ActiveAssignment, InstrumentConfig


class InstrumentRegistry(Protocol):
    def get(self, symbol: str) -> InstrumentConfig | None: ...


class InMemoryInstrumentRegistry:
    def __init__(self, instruments: Mapping[str, InstrumentConfig]) -> None:
        self._instruments = dict(instruments)

    def get(self, symbol: str) -> InstrumentConfig | None:
        return self._instruments.get(symbol)


class YamlInstrumentRegistry:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def get(self, symbol: str) -> InstrumentConfig | None:
        payload = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        instruments = payload.get("instruments", {})
        raw = instruments.get(symbol)
        if raw is None:
            return None
        active_raw = raw.get("active") if isinstance(raw, dict) else None
        active = None
        if active_raw is not None:
            active = ActiveAssignment(
                strategy=str(active_raw["strategy"]),
                parameter_set=str(active_raw["parameter_set"]),
            )
        return InstrumentConfig(symbol=symbol, active=active)
