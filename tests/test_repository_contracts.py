from __future__ import annotations

import json
from pathlib import Path

from investment_strategy.backtest import parse_backtest_request
from investment_strategy.decision import DISCLAIMER, parse_decision_request

ROOT = Path(__file__).resolve().parents[1]


def test_repository_request_examples_match_boundaries() -> None:
    decision = json.loads((ROOT / "requests/decision.json").read_text(encoding="utf-8"))
    backtest = json.loads((ROOT / "requests/backtest.json").read_text(encoding="utf-8"))
    assert parse_decision_request(decision).symbol == "00733"
    assert parse_backtest_request(backtest).mode.value == "ACTIVE"
    assert "period" not in backtest


def test_readme_documents_canonical_contracts_and_disclaimer() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert DISCLAIMER in text
    for required in (
        "MarketState",
        "StrategyResult",
        "entry_plan",
        "exit_plan",
        "OHLCV",
        "intraday overlay",
        "ACTIVE",
        "EXPLICIT",
        "SUCCESS",
        "FAILED",
        "Git revision",
        "analytical Backtest",
        "ChatGPT Chat / Work",
        "Serverless-style execution",
        "本專案及其產生之所有內容僅供個人研究、學習與策略驗證用途",
        "任何投資決策均應由使用者自行評估並承擔相關風險",
    ):
        assert required in text


def test_workflow_scaffolds_match_analytical_semantics() -> None:
    decision = (ROOT / ".github/workflows/decision.yml").read_text(encoding="utf-8")
    backtest = (ROOT / ".github/workflows/backtest.yml").read_text(encoding="utf-8")
    openspec = (ROOT / ".github/workflows/openspec-validate.yml").read_text(encoding="utf-8")
    assert "as_of" in decision
    assert "mode" in backtest and "start_date" in backtest and "end_date" in backtest
    assert "fill simulation" not in backtest.lower()
    assert (
        "live provider/calendar/production-strategy composition is intentionally deferred"
        in decision.lower()
    )
    assert "openspec validate --all --strict --json --no-interactive" in openspec
