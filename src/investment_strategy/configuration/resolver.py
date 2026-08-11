from __future__ import annotations

from investment_strategy.domain.configuration import InstrumentConfig, ResolvedStrategyConfig
from investment_strategy.domain.failures import configuration_failure
from investment_strategy.domain.strategy import Strategy
from investment_strategy.strategies.registry import CodeStrategyRegistry

from .instruments import InstrumentRegistry
from .parameter_sets import ParameterSetRegistry


class StrategyConfigResolver:
    def __init__(
        self,
        instruments: InstrumentRegistry,
        parameter_sets: ParameterSetRegistry,
        strategies: CodeStrategyRegistry,
        git_sha: str,
    ) -> None:
        self._instruments = instruments
        self._parameter_sets = parameter_sets
        self._strategies = strategies
        self._git_sha = git_sha

    @property
    def git_sha(self) -> str:
        return self._git_sha

    def resolve_active(self, symbol: str) -> tuple[Strategy, ResolvedStrategyConfig]:
        instrument = self._resolve_instrument(symbol)
        if instrument.active is None:
            raise configuration_failure(
                "ACTIVE_STRATEGY_NOT_CONFIGURED",
                f"instrument {symbol} has no active strategy assignment",
            )
        return self._resolve_pair(symbol, instrument.active.strategy, instrument.active.parameter_set)

    def resolve_explicit(
        self, symbol: str, strategy_id: str, parameter_set_id: str
    ) -> tuple[Strategy, ResolvedStrategyConfig]:
        self._resolve_instrument(symbol)
        return self._resolve_pair(symbol, strategy_id, parameter_set_id)

    def _resolve_instrument(self, symbol: str) -> InstrumentConfig:
        instrument = self._instruments.get(symbol)
        if instrument is None:
            raise configuration_failure(
                "INSTRUMENT_NOT_FOUND", f"instrument {symbol} is not configured"
            )
        return instrument

    def _resolve_pair(
        self, symbol: str, strategy_id: str, parameter_set_id: str
    ) -> tuple[Strategy, ResolvedStrategyConfig]:
        strategy = self._strategies.get(strategy_id)
        if strategy is None:
            raise configuration_failure(
                "STRATEGY_NOT_FOUND", f"strategy {strategy_id} is not available"
            )

        parameter_set = self._parameter_sets.get(parameter_set_id)
        if parameter_set is None:
            raise configuration_failure(
                "PARAMETER_SET_NOT_FOUND",
                f"parameter set {parameter_set_id} is not configured",
            )
        if parameter_set.strategy != strategy_id:
            raise configuration_failure(
                "STRATEGY_PARAMETER_MISMATCH",
                f"parameter set {parameter_set_id} belongs to {parameter_set.strategy}, not {strategy_id}",
            )
        try:
            resolved_parameters = strategy.validate_parameters(parameter_set.parameters)
        except (TypeError, ValueError) as exc:
            raise configuration_failure(
                "INVALID_STRATEGY_PARAMETERS",
                f"invalid parameters for strategy {strategy_id}: {exc}",
            ) from exc

        return strategy, ResolvedStrategyConfig(
            symbol=symbol,
            strategy=strategy_id,
            parameter_set=parameter_set_id,
            resolved_parameters=resolved_parameters,
            git_sha=self._git_sha,
        )
