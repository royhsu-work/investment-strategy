from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class DataFrequency(StrEnum):
    DAILY = "DAILY"


@dataclass(frozen=True, slots=True)
class DataRequirement:
    frequency: DataFrequency
    minimum_history: int

    def __post_init__(self) -> None:
        if self.frequency is not DataFrequency.DAILY:
            raise ValueError("only DAILY data frequency is supported")
        if self.minimum_history <= 0:
            raise ValueError("minimum_history must be positive")


@dataclass(frozen=True, slots=True)
class DailyBar:
    trading_timestamp: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
