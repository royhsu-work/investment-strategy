from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from investment_strategy.domain.failures import data_failure
from investment_strategy.domain.market_data import DailyBar

from .ports import MarketDataGateway

MANDATORY_FIELDS = ("open", "high", "low", "close", "volume")


def acquire_candidates(
    gateway: MarketDataGateway, symbol: str
) -> tuple[Mapping[str, object], ...]:
    try:
        records = tuple(gateway.load_daily(symbol))
    except Exception as exc:
        raise data_failure("DATA_UNAVAILABLE", f"market data unavailable for {symbol}") from exc
    if not records:
        raise data_failure("DATA_UNAVAILABLE", f"market data unavailable for {symbol}")
    return records


def normalize_trading_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            if "T" in text or " " in text:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            return date.fromisoformat(text)
        except ValueError as exc:
            raise data_failure("VALIDATION_ERROR", f"invalid timestamp: {value!r}") from exc
    raise data_failure("VALIDATION_ERROR", f"invalid timestamp: {value!r}")


def classify_and_bound(
    candidates: Sequence[Mapping[str, object]], *, through: date
) -> tuple[tuple[date, Mapping[str, object]], ...]:
    bounded: list[tuple[date, Mapping[str, object]]] = []
    for record in candidates:
        if "timestamp" not in record:
            raise data_failure("VALIDATION_ERROR", "historical observation is missing timestamp")
        trading_day = normalize_trading_date(record["timestamp"])
        if trading_day <= through:
            bounded.append((trading_day, record))
    return tuple(bounded)


def _decimal(value: object, field: str) -> Decimal:
    if value is None:
        raise data_failure("MISSING_REQUIRED_FIELD", f"missing required field: {field}")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise data_failure("VALIDATION_ERROR", f"invalid numeric value for {field}") from exc


def normalize_daily_bars(
    classified: Sequence[tuple[date, Mapping[str, object]]],
) -> tuple[DailyBar, ...]:
    bars: list[DailyBar] = []
    for trading_day, record in classified:
        for field in MANDATORY_FIELDS:
            if field not in record or record[field] is None:
                raise data_failure("MISSING_REQUIRED_FIELD", f"missing required field: {field}")
        open_ = _decimal(record["open"], "open")
        high = _decimal(record["high"], "high")
        low = _decimal(record["low"], "low")
        close = _decimal(record["close"], "close")
        volume = _decimal(record["volume"], "volume")
        if any(price <= 0 for price in (open_, high, low, close)):
            raise data_failure("INVALID_OHLC", f"non-positive OHLC on {trading_day}")
        if high < max(open_, low, close) or low > min(open_, high, close):
            raise data_failure("INVALID_OHLC", f"invalid OHLC relationship on {trading_day}")
        if volume < 0:
            raise data_failure("VALIDATION_ERROR", f"negative volume on {trading_day}")
        bars.append(
            DailyBar(
                trading_timestamp=trading_day,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )

    bars.sort(key=lambda bar: bar.trading_timestamp)
    seen: set[date] = set()
    for bar in bars:
        if bar.trading_timestamp in seen:
            raise data_failure(
                "DUPLICATE_TIMESTAMP",
                f"duplicate timestamp: {bar.trading_timestamp.isoformat()}",
            )
        seen.add(bar.trading_timestamp)
    return tuple(bars)


def prepare_bars(
    gateway: MarketDataGateway,
    symbol: str,
    *,
    through: date,
) -> tuple[DailyBar, ...]:
    candidates = acquire_candidates(gateway, symbol)
    classified = classify_and_bound(candidates, through=through)
    # Candidates were acquired; an empty bounded set is not reclassified as DATA_UNAVAILABLE.
    return normalize_daily_bars(classified)
