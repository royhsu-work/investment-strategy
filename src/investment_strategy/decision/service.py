from __future__ import annotations

from typing import Any

from investment_strategy.configuration.resolver import StrategyConfigResolver
from investment_strategy.data.calendar import TradingCalendar
from investment_strategy.data.normalize import prepare_bars
from investment_strategy.data.ports import Clock, IntradaySnapshotGateway, MarketDataGateway
from investment_strategy.data.validate import (
    ensure_minimum_history,
    validate_continuity_and_freshness,
)
from investment_strategy.domain.failures import ApplicationFailure, strategy_failure
from investment_strategy.domain.strategy import evaluate_strategy

from .artifact import build_decision_failure, build_decision_success
from .as_of import is_current_formal_decision, resolve_decision_as_of
from .intraday import build_intraday_overlay, parse_snapshot
from .request import DecisionRequest


class DecisionService:
    def __init__(
        self,
        *,
        resolver: StrategyConfigResolver,
        market_data: MarketDataGateway,
        calendar: TradingCalendar,
        clock: Clock,
        intraday: IntradaySnapshotGateway | None = None,
    ) -> None:
        self._resolver = resolver
        self._market_data = market_data
        self._calendar = calendar
        self._clock = clock
        self._intraday = intraday

    def run(self, request: DecisionRequest) -> dict[str, Any]:
        now = self._clock.now()
        try:
            resolved_as_of = resolve_decision_as_of(request.as_of, now=now, calendar=self._calendar)
            strategy, config = self._resolver.resolve_active(request.symbol)
            requirement = strategy.requirements()
            bars = prepare_bars(self._market_data, request.symbol, through=resolved_as_of)
            validate_continuity_and_freshness(
                bars,
                calendar=self._calendar,
                resolved_as_of=resolved_as_of,
            )
            ensure_minimum_history(bars, requirement.minimum_history)
            try:
                result = evaluate_strategy(
                    strategy,
                    instrument=request.symbol,
                    as_of=resolved_as_of,
                    bars=bars,
                    resolved_config=config,
                )
            except ApplicationFailure:
                raise
            except Exception as exc:
                raise strategy_failure(
                    "STRATEGY_EVALUATION_ERROR",
                    f"strategy evaluation failed: {exc}",
                ) from exc

            overlay = None
            if self._intraday is not None and is_current_formal_decision(
                request.as_of,
                now=now,
                calendar=self._calendar,
                resolved_as_of=resolved_as_of,
            ):
                try:
                    raw_snapshot = self._intraday.load_snapshot(request.symbol)
                except Exception:
                    raw_snapshot = None
                snapshot = parse_snapshot(
                    raw_snapshot,
                    expected_session=self._calendar.market_date(now),
                )
                if snapshot is not None:
                    overlay = build_intraday_overlay(snapshot, result).to_dict()

            return build_decision_success(
                instrument=request.symbol,
                requested_as_of=request.as_of,
                resolved_as_of=resolved_as_of,
                strategy=config.strategy,
                parameter_set=config.parameter_set,
                git_sha=config.git_sha,
                strategy_result=result,
                intraday_overlay=overlay,
            )
        except ApplicationFailure as exc:
            return build_decision_failure(
                instrument=request.symbol,
                requested_as_of=request.as_of,
                git_sha=self._resolver.git_sha,
                failure=exc.failure,
            )
