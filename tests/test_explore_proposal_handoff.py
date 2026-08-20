from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
REVIEW = ROOT / "agents" / "skills" / "openspec-review" / "SKILL.md"
ADAPTER = ROOT / "agents" / "skills" / "openspec-semantic-adapter.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_shared_governance_owns_explore_to_propose_handoff_invariant() -> None:
    shared = _normalized(AGENTS)

    for required in (
        "exact durable Explore",
        "ACTION_RESULT",
        "PROPOSAL_READY",
        "preserve",
    ):
        assert required in shared


def test_explore_originated_propose_requires_exact_durable_result_reference() -> None:
    change = _normalized(CHANGE)

    for required in (
        "exact durable Explore",
        "ACTION_RESULT",
        "PROPOSAL_READY",
        "preserve",
    ):
        assert required in change


def test_direct_propose_does_not_fabricate_explore_reference() -> None:
    change = _normalized(CHANGE)

    assert "Direct-to-Propose" in change
    assert "synthetic Explore" in change


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


def test_review_rejects_internal_consistency_that_conflicts_with_explore() -> None:
    review = _normalized(REVIEW)

    assert "material contradiction or omission is `FINDINGS`" in review
    assert "internally bidirectionally consistent" in review


def test_faithful_explore_formalization_reaches_ordinary_review_gate() -> None:
    review = _normalized(REVIEW)

    assert "upstream semantic boundary is verified" in review
    assert "ordinary gate" in review


def test_review_does_not_rerun_explore_or_reconstruct_conversation_intent() -> None:
    review = _normalized(REVIEW)

    assert "re-run Explore" in review or "repeat Explore" in review
    assert "conversation" in review


def test_semantic_adapter_does_not_own_explore_handoff_semantics() -> None:
    adapter = _read(ADAPTER)

    assert "Explore-originated" not in adapter
    assert "PROPOSAL_READY" not in adapter
