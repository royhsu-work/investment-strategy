from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from investment_strategy.domain.failures import RequestRejected


class AssignmentMode(StrEnum):
    ACTIVE = "ACTIVE"
    EXPLICIT = "EXPLICIT"


@dataclass(frozen=True, slots=True)
class BacktestRequest:
    symbol: str
    mode: AssignmentMode
    start_date: date
    end_date: date
    strategy: str | None = None
    parameter_set: str | None = None


def _iso_date(value: object, field: str) -> date:
    if not isinstance(value, str):
        raise RequestRejected(f"{field} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RequestRejected(f"{field} must be an ISO date string") from exc


def parse_backtest_request(payload: Mapping[str, object]) -> BacktestRequest:
    allowed = {"symbol", "mode", "strategy", "parameter_set", "start_date", "end_date"}
    extra = set(payload) - allowed
    if extra:
        raise RequestRejected(f"unsupported Backtest fields: {', '.join(sorted(extra))}")
    symbol = payload.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        raise RequestRejected("symbol is required")
    try:
        mode = AssignmentMode(str(payload.get("mode")))
    except ValueError as exc:
        raise RequestRejected("mode must be ACTIVE or EXPLICIT") from exc
    start_date = _iso_date(payload.get("start_date"), "start_date")
    end_date = _iso_date(payload.get("end_date"), "end_date")
    raw_strategy = payload.get("strategy")
    raw_parameter_set = payload.get("parameter_set")

    if mode is AssignmentMode.ACTIVE:
        if raw_strategy is not None or raw_parameter_set is not None:
            raise RequestRejected("ACTIVE mode forbids strategy and parameter_set")
        return BacktestRequest(symbol.strip(), mode, start_date, end_date)

    if not isinstance(raw_strategy, str) or not raw_strategy.strip():
        raise RequestRejected("EXPLICIT mode requires strategy")
    if not isinstance(raw_parameter_set, str) or not raw_parameter_set.strip():
        raise RequestRejected("EXPLICIT mode requires parameter_set")
    return BacktestRequest(
        symbol.strip(),
        mode,
        start_date,
        end_date,
        strategy=raw_strategy.strip(),
        parameter_set=raw_parameter_set.strip(),
    )
