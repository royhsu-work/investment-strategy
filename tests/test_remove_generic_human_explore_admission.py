from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"


def _governance() -> str:
    return " ".join(AGENTS.read_text(encoding="utf-8").split())


def test_routed_formal_explore_is_origin_neutral_for_queue_eligibility() -> None:
    text = _governance()
    assert "ordinary routed Explore eligibility does not require Human approval" in text
    assert "open `Lead / explore-change + Change: unset`" in text
    assert "origin does not control dispatcher eligibility" in text


def test_formal_wip_and_stable_order_still_dominate_pre_activation_explore() -> None:
    text = _governance()
    assert "formal active or terminal-pending workflow must win over pre-activation intake" in text
    assert "earliest GitHub `created_at`, then lower Issue number" in text


def test_direct_propose_human_admission_remains_distinct() -> None:
    text = _governance()
    assert "Human direct-Propose admission" in text
    assert "issue:<issue-number>:admission:lead:propose-change" in text
