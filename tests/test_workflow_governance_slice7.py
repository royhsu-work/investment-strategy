"""Slice 7 governance contract checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split())


def test_lead_systemic_coherence_contract() -> None:
    lead = _text("agents/roles/lead.md")
    assert "systemic coherence" in lead
    assert "bounded blast-radius analysis" in lead
    assert "sibling actions" in lead
    assert "root cause" in lead
    assert "narrowest correct ownership layer" in lead
    assert "progress polling" in lead


def test_idle_advisory_uses_recent_issue_lens() -> None:
    shared = _text("agents/AGENTS.md")
    assert "preceding 7 days" in shared
    assert "created or materially active" in shared


def test_openspec_review_is_reverse_first() -> None:
    review = _text("agents/skills/openspec-review/SKILL.md")
    reverse = "tasks → design → specs → proposal"
    forward = "proposal → specs → design → tasks"
    assert review.index(reverse) < review.index(forward)
    assert "reverse-first" in review
    assert "both directions" in review
