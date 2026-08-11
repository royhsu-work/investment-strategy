from __future__ import annotations

import pytest

from investment_strategy.backtest import AssignmentMode, parse_backtest_request
from investment_strategy.decision import parse_decision_request
from investment_strategy.domain import RequestRejected


def test_decision_request_accepts_symbol_and_optional_as_of() -> None:
    request = parse_decision_request({"symbol": "00733", "as_of": "2026-08-10"})
    assert request.symbol == "00733"
    assert request.as_of is not None and request.as_of.isoformat() == "2026-08-10"


@pytest.mark.parametrize("extra", [{"strategy": "x"}, {"parameter_set": "p"}])
def test_decision_rejects_research_overrides(extra: dict[str, str]) -> None:
    with pytest.raises(RequestRejected):
        parse_decision_request({"symbol": "00733", **extra})


def test_backtest_active_shape() -> None:
    request = parse_backtest_request(
        {
            "symbol": "00733",
            "mode": "ACTIVE",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        }
    )
    assert request.mode is AssignmentMode.ACTIVE
    assert request.strategy is None
    assert request.parameter_set is None


def test_backtest_explicit_shape() -> None:
    request = parse_backtest_request(
        {
            "symbol": "00733",
            "mode": "EXPLICIT",
            "strategy": "test",
            "parameter_set": "p1",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        }
    )
    assert request.mode is AssignmentMode.EXPLICIT
    assert request.strategy == "test"
    assert request.parameter_set == "p1"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "symbol": "00733",
            "mode": "ACTIVE",
            "strategy": "test",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
        {
            "symbol": "00733",
            "mode": "ACTIVE",
            "parameter_set": "p1",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
        {
            "symbol": "00733",
            "mode": "EXPLICIT",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
        {
            "symbol": "00733",
            "mode": "EXPLICIT",
            "strategy": "test",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
        {
            "symbol": "00733",
            "mode": "EXPLICIT",
            "parameter_set": "p1",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
    ],
)
def test_invalid_backtest_union_is_rejected_before_application(
    payload: dict[str, str],
) -> None:
    with pytest.raises(RequestRejected):
        parse_backtest_request(payload)
