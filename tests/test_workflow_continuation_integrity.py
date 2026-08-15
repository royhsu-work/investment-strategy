from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_required_deferred_follow_up_has_one_shared_semantic_boundary() -> None:
    shared = _read("agents/AGENTS.md")
    assert "required deferred follow-up" in shared
    assert "ordinary out-of-scope" in shared
    assert "source coordination Issue/Change" in shared
    assert "exact defer decision" in shared
    assert "MUST NOT Human-admit" in shared


def test_required_deferred_follow_up_is_enforced_at_review_and_finalization() -> None:
    lead = _read("agents/roles/lead.md")
    review = _read("agents/skills/openspec-review/SKILL.md")
    finalize = _read("agents/skills/lifecycle-finalize/SKILL.md")

    assert "create or reuse" in lead and "required deferred follow-up" in lead
    assert "required deferred follow-up" in review
    assert "missing" in review and "tracker" in review
    assert "ordinary out-of-scope" in review.lower()
    assert "required deferred follow-up" in finalize
    assert "LIFECYCLE_COMPLETE" in finalize
    assert "tracker" in finalize
