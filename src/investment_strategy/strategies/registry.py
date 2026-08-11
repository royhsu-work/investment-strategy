from __future__ import annotations

from typing import Iterable

from investment_strategy.domain.strategy import Strategy


class CodeStrategyRegistry:
    def __init__(self, strategies: Iterable[Strategy] = ()) -> None:
        self._strategies = {strategy.id: strategy for strategy in strategies}

    def get(self, strategy_id: str) -> Strategy | None:
        return self._strategies.get(strategy_id)
