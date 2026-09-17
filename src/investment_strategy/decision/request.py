from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from investment_strategy.domain.failures import RequestRejected


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    symbol: str
    as_of: date | None = None


def parse_decision_request(payload: Mapping[str, object]) -> DecisionRequest:
    allowed = {"symbol", "as_of"}
    extra = set(payload) - allowed
    if extra:
        raise RequestRejected(f"unsupported Decision fields: {', '.join(sorted(extra))}")
    symbol = payload.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        raise RequestRejected("symbol is required")
    raw_as_of = payload.get("as_of")
    as_of = None
    if raw_as_of is not None:
        if not isinstance(raw_as_of, str):
            raise RequestRejected("as_of must be an ISO date string")
        try:
            as_of = date.fromisoformat(raw_as_of)
        except ValueError as exc:
            raise RequestRejected("as_of must be an ISO date string") from exc
    return DecisionRequest(symbol=symbol.strip(), as_of=as_of)
