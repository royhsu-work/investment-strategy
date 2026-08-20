from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
REVIEW = ROOT / "agents" / "skills" / "openspec-review" / "SKILL.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_explore_originated_propose_requires_exact_durable_result_reference() -> None:
    shared = _normalized(AGENTS)
    change = _normalized(CHANGE)

    for required in (
        "exact durable Explore",
        "ACTION_RESULT",
        "PROPOSAL_READY",
        "preserve",
    ):
        assert required in shared or required in change


def test_direct_propose_does_not_fabricate_explore_reference() -> None:
    shared = _normalized(AGENTS)
    change = _normalized(CHANGE)

    assert "direct-to-Propose" in shared or "Direct-to-Propose" in change
    assert "synthetic Explore" in shared or "synthetic Explore" in change


def test_review_dereferences_explore_result_before_bidirectional_gate() -> None:
    review = _read(REVIEW)
    normalized = " ".join(review.split())

    assert "exact Explore" in normalized
    assert "dereference" in normalized
    assert "preserv" in normalized

    dereference_at = review.lower().find("derefer")
    reverse_at = review.lower().find("reverse traceability")
    assert dereference_at >= 0
    assert reverse_at >= 0
    assert dereference_at < reverse_at


def test_review_does_not_rerun_explore_or_reconstruct_conversation_intent() -> None:
    review = _normalized(REVIEW)

    assert "re-run Explore" in review or "repeat Explore" in review
    assert "conversation" in review
