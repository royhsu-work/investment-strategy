from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_implementation_pass_routes_directly_to_executor_merge() -> None:
    implementation_review = _read("agents/skills/implementation-review/SKILL.md")
    merge_pr = _read("agents/skills/merge-pr/SKILL.md")

    assert "`PASS` → `Executor / merge-pr`" in implementation_review
    assert "Reviewer PASS" in merge_pr
    assert "Lead authorization" not in merge_pr


def test_normal_implementation_merge_has_no_lead_authorization_hop() -> None:
    finalize = _read("agents/skills/lifecycle-finalize/SKILL.md")
    executor = _read("agents/roles/executor.md")

    assert "MERGE_AUTHORIZED" not in executor
    assert "Before merge authorization" not in finalize


def test_archive_preparation_is_complete_before_reviewer_handoff() -> None:
    finalize = _read("agents/skills/lifecycle-finalize/SKILL.md")
    archive_review = _read("agents/skills/archive-review/SKILL.md")

    assert "before `Reviewer / review-archive`" in finalize
    assert "required deferred follow-up" in finalize
    assert "temporary correction/recovery" in finalize
    assert "Lead preparation evidence" in archive_review


def test_archive_pass_routes_directly_to_executor_merge() -> None:
    archive_review = _read("agents/skills/archive-review/SKILL.md")

    assert "`PASS` → `Executor / merge-pr`" in archive_review


def test_shared_merge_contract_consumes_reviewer_pass_without_lead_token() -> None:
    shared = _read("agents/AGENTS.md")

    assert "Reviewer PASS for revision R" in shared
    assert "Lead MERGE_AUTHORIZED for revision R" not in shared
    assert "current PR head == R" in shared
    assert "required gate remains valid and non-contradictory" in shared
