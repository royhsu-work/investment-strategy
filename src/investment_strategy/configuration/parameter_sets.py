from __future__ import annotations

from pathlib import Path
from typing import Mapping, Protocol

import yaml

from investment_strategy.domain.configuration import ParameterSet


class ParameterSetRegistry(Protocol):
    def get(self, parameter_set_id: str) -> ParameterSet | None: ...


class InMemoryParameterSetRegistry:
    def __init__(self, parameter_sets: Mapping[str, ParameterSet]) -> None:
        self._parameter_sets = dict(parameter_sets)

    def get(self, parameter_set_id: str) -> ParameterSet | None:
        return self._parameter_sets.get(parameter_set_id)


class YamlParameterSetRegistry:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def get(self, parameter_set_id: str) -> ParameterSet | None:
        payload = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        parameter_sets = payload.get("parameter_sets", {})
        raw = parameter_sets.get(parameter_set_id)
        if raw is None:
            return None
        return ParameterSet(
            id=parameter_set_id,
            strategy=str(raw["strategy"]),
            parameters=dict(raw.get("parameters", {})),
        )
