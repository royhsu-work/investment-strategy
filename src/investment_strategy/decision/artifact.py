from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from investment_strategy.domain.failures import Failure
from investment_strategy.domain.result import StrategyResult
from investment_strategy.serialization import serialize_public_artifact

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
    intraday_overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
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
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "status": "FAILED",
        "instrument": instrument,
        "git_sha": git_sha,
        "failure": failure.to_dict(),
        "disclaimer": DISCLAIMER,
    }
    if requested_as_of is not None:
        artifact["requested_as_of"] = requested_as_of.isoformat()
    return artifact


def serialize_decision_artifact(artifact: Mapping[str, Any]) -> str:
    return serialize_public_artifact(artifact)
