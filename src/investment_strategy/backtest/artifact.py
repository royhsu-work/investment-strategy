from __future__ import annotations

from investment_strategy.decision.artifact import DISCLAIMER
from investment_strategy.domain.failures import Failure

from .request import BacktestRequest


def build_backtest_success(
    *,
    request: BacktestRequest,
    strategy: str,
    parameter_set: str,
    git_sha: str,
    timeline: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "status": "SUCCESS",
        "instrument": request.symbol,
        "assignment_mode": request.mode.value,
        "strategy": strategy,
        "parameter_set": parameter_set,
        "git_sha": git_sha,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "validation_status": "PASS",
        "timeline": timeline,
        "disclaimer": DISCLAIMER,
    }


def build_backtest_failure(
    *,
    request: BacktestRequest,
    git_sha: str,
    failure: Failure,
) -> dict[str, object]:
    return {
        "status": "FAILED",
        "instrument": request.symbol,
        "assignment_mode": request.mode.value,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "git_sha": git_sha,
        "failure": failure.to_dict(),
        "disclaimer": DISCLAIMER,
    }
