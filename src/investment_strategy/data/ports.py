from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class MarketDataGateway(Protocol):
    def load_daily(self, symbol: str) -> Sequence[Mapping[str, object]]: ...


class IntradaySnapshotGateway(Protocol):
    def load_snapshot(self, symbol: str) -> Mapping[str, object] | None: ...
