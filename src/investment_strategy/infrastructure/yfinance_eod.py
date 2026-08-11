from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from investment_strategy.domain.configuration import MarketDataInstrument

HistoryLoader = Callable[..., Any]

_SUFFIX_BY_VENUE = {"TWSE": ".TW", "TPEX": ".TWO"}
_HISTORY_OPTIONS: dict[str, object] = {
    "period": "max",
    "interval": "1d",
    "prepost": False,
    "auto_adjust": False,
    "back_adjust": False,
    "repair": False,
    "actions": False,
    "rounding": False,
    "raise_errors": True,
}
_PROVIDER_COLUMNS = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}


def _default_history_loader(ticker: str, **kwargs: object) -> Any:
    import yfinance as yf  # type: ignore[import-untyped]

    return yf.Ticker(ticker).history(**kwargs)


def _timestamp_value(value: object) -> object:
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return value


class YFinanceEodGateway:
    """Reported daily OHLCV acquisition; period=max controls breadth, not formal scope."""

    def __init__(self, *, history_loader: HistoryLoader | None = None) -> None:
        self._history_loader = history_loader or _default_history_loader

    def load_daily(self, instrument: MarketDataInstrument) -> Sequence[Mapping[str, object]]:
        suffix = _SUFFIX_BY_VENUE[instrument.listing_venue]
        frame = self._history_loader(instrument.symbol + suffix, **_HISTORY_OPTIONS)
        if getattr(frame, "empty", False):
            return ()

        candidates: list[Mapping[str, object]] = []
        for index, row in frame.iterrows():
            candidate: dict[str, object] = {"timestamp": _timestamp_value(index)}
            for provider_name, canonical_name in _PROVIDER_COLUMNS.items():
                if provider_name in row:
                    candidate[canonical_name] = row[provider_name]
            candidates.append(candidate)
        return tuple(candidates)
