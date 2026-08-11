from __future__ import annotations

from datetime import date
from typing import Any

from investment_strategy.configuration.resolver import StrategyConfigResolver
from investment_strategy.data.calendar import TradingCalendar
from investment_strategy.data.normalize import prepare_bars
from investment_strategy.data.ports import Clock, MarketDataGateway
from investment_strategy.data.validate import validate_continuity_and_freshness
from investment_strategy.domain.failures import (
    ApplicationFailure,
    configuration_failure,
    data_failure,
    strategy_failure,
)
from investment_strategy.domain.strategy import evaluate_strategy

from .artifact import build_backtest_failure, build_backtest_success
from .request import AssignmentMode, BacktestRequest


class BacktestService:
    def __init__(
        self,
        *,
        resolver: StrategyConfigResolver,
        market_data: MarketDataGateway,
        calendar: TradingCalendar,
        clock: Clock,
    ) -> None:
        self._resolver = resolver
        self._market_data = market_data
        self._calendar = calendar
        self._clock = clock

    def _evaluation_dates(self, request: BacktestRequest) -> tuple[date, ...]:
        now = self._clock.now()
        today = self._calendar.market_date(now)
        if request.start_date > request.end_date or request.end_date > today:
            raise configuration_failure(
                "INVALID_BACKTEST_RANGE",
                "Backtest range is invalid or extends into the future",
            )
        days: list[date] = []
        for day in self._calendar.trading_days(request.start_date, request.end_date):
            if day < today or self._calendar.is_session_complete(day, now):
                days.append(day)
        if not days:
            raise configuration_failure(
                "INVALID_BACKTEST_RANGE",
                "Backtest range contains no completed trading day",
            )
        return tuple(days)

    def run(self, request: BacktestRequest) -> dict[str, Any]:
        try:
            evaluation_dates = self._evaluation_dates(request)
            market_instrument = self._resolver.resolve_market_data_instrument(request.symbol)
            if request.mode is AssignmentMode.ACTIVE:
                strategy, config = self._resolver.resolve_active(request.symbol)
            else:
                assert request.strategy is not None
                assert request.parameter_set is not None
                strategy, config = self._resolver.resolve_explicit(
                    request.symbol,
                    request.strategy,
                    request.parameter_set,
                )

            requirement = strategy.requirements()
            last_evaluation = evaluation_dates[-1]
            bars = prepare_bars(self._market_data, market_instrument, through=last_evaluation)
            validate_continuity_and_freshness(
                bars,
                calendar=self._calendar,
                resolved_as_of=last_evaluation,
            )

            timeline: list[dict[str, Any]] = []
            eligible_count = 0
            for evaluation_date in evaluation_dates:
                bounded = tuple(bar for bar in bars if bar.trading_timestamp <= evaluation_date)
                if len(bounded) < requirement.minimum_history:
                    timeline.append({"date": evaluation_date.isoformat(), "status": "WARMUP"})
                    continue
                eligible_count += 1
                try:
                    result = evaluate_strategy(
                        strategy,
                        instrument=request.symbol,
                        as_of=evaluation_date,
                        bars=bounded,
                        resolved_config=config,
                    )
                except ApplicationFailure:
                    raise
                except Exception as exc:
                    raise strategy_failure(
                        "STRATEGY_EVALUATION_ERROR",
                        f"strategy evaluation failed at {evaluation_date}: {exc}",
                    ) from exc
                timeline.append(
                    {
                        "date": evaluation_date.isoformat(),
                        "status": "EVALUATED",
                        "strategy_result": result.to_dict(),
                    }
                )

            if eligible_count == 0:
                raise data_failure(
                    "INSUFFICIENT_HISTORY",
                    "no requested completed trading day satisfied minimum history",
                )

            return build_backtest_success(
                request=request,
                strategy=config.strategy,
                parameter_set=config.parameter_set,
                git_sha=config.git_sha,
                timeline=timeline,
            )
        except ApplicationFailure as exc:
            return build_backtest_failure(
                request=request,
                git_sha=self._resolver.git_sha,
                failure=exc.failure,
            )
