from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_archive_automation_stops_at_validated_branch_readiness() -> None:
    workflow = _read(".github/workflows/openspec-archive.yml")
    assert "pull-requests: read" in workflow
    assert "pull-requests: write" not in workflow
    assert 'git push -u origin HEAD:"$target_branch"' in workflow
    assert "gh pr create" not in workflow


def test_finalize_change_prepares_archive_review_without_merging() -> None:
    skill = _read("agents/skills/lifecycle-finalize/SKILL.md")
    governance = _read("agents/AGENTS.md")
    for required in (
        "archive preparation",
        "exact Change/Issue linkage",
        "non-closing linkage",
        "Reviewer / review-archive",
        "does not perform normal PR merge mutation",
    ):
        assert required in skill
    assert "independent Reviewer" in governance


def test_archive_review_and_merge_keep_independent_gates() -> None:
    archive = " ".join(_read("agents/skills/archive-review/SKILL.md").split())
    merge = " ".join(_read("agents/skills/merge-pr/SKILL.md").split())
    assert "derives merge-archive-pr" in archive
    for required in (
        "independent Reviewer PASS",
        "non-closing linkage",
        "archive preparation",
        "fails closed",
    ):
        assert required in merge
