from __future__ import annotations

from datetime import date

from investment_strategy.domain.failures import Failure
from investment_strategy.domain.result import StrategyResult

DISCLAIMER = "僅為個人研究與策略驗證，不構成任何形式之投資建議。"


def build_decision_success(
    *,
    instrument: str,
    requested_as_of: date | None,
    resolved_as_of: date,
    strategy: str,
    parameter_set: str,
    git_sha: str,
    strategy_result: StrategyResult,
    intraday_overlay: dict[str, object] | None = None,
) -> dict[str, object]:
    artifact: dict[str, object] = {
        "status": "SUCCESS",
        "instrument": instrument,
        "resolved_as_of": resolved_as_of.isoformat(),
        "strategy": strategy,
        "parameter_set": parameter_set,
        "git_sha": git_sha,
        "data_quality": "PASS",
        "strategy_result": strategy_result.to_dict(),
        "disclaimer": DISCLAIMER,
    }
    if requested_as_of is not None:
        artifact["requested_as_of"] = requested_as_of.isoformat()
    if intraday_overlay is not None:
        artifact["intraday_overlay"] = intraday_overlay
    return artifact


def build_decision_failure(
    *,
    instrument: str,
    requested_as_of: date | None,
    git_sha: str,
    failure: Failure,
) -> dict[str, object]:
    artifact: dict[str, object] = {
        "status": "FAILED",
        "instrument": instrument,
        "git_sha": git_sha,
        "failure": failure.to_dict(),
        "disclaimer": DISCLAIMER,
    }
    if requested_as_of is not None:
        artifact["requested_as_of"] = requested_as_of.isoformat()
    return artifact
