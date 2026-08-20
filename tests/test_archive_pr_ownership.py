from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _normalized(path: str) -> str:
    return " ".join(_read(path).split())


def test_archive_automation_stops_at_validated_branch_readiness() -> None:
    workflow = _read(".github/workflows/openspec-archive.yml")
    assert "pull-requests: read" in workflow
    assert "pull-requests: write" not in workflow
    assert 'git push -u origin HEAD:"$target_branch"' in workflow
    assert "gh pr create" not in workflow
    assert "Create final Archive PR with closing linkage" not in workflow


def test_finalize_change_owns_normal_archive_pr_presentation() -> None:
    skill = _read("agents/skills/lifecycle-finalize/SKILL.md")
    governance = _read("agents/AGENTS.md")
    for required in (
        "validated `agent/archive-<change>` branch is durably ready",
        "create or reuse the final Archive PR as ordinary lifecycle continuation",
        "Refs #<coordination-issue>",
        "normal success, not `RECOVERY_DECISION_REQUIRED`",
        "`ARCHIVE_PR_READY`",
        "`Reviewer / review-archive`",
    ):
        assert required in skill
    for required in (
        "validated archive-branch push",
        "`Lead / finalize-change` owns normal final Archive PR presentation",
        "normal repository-automation success",
        "MUST NOT be classified as archive failure or `RECOVERY_DECISION_REQUIRED`",
        "durable final Archive PR ready → route `Reviewer / review-archive`",
    ):
        assert required in governance


def test_normal_archive_pr_path_preserves_independent_final_gates() -> None:
    skill = _normalized("agents/skills/lifecycle-finalize/SKILL.md")
    archive_review = _normalized("agents/skills/archive-review/SKILL.md")
    merge_skill = _normalized("agents/skills/merge-pr/SKILL.md")
    for required in (
        "preparation evidence",
        "independent Reviewer PASS",
        "Executor merge preconditions",
        "non-closing linkage",
        "terminal `finalize-archive` reconstruction",
    ):
        assert required in skill
    assert "`PASS` → `Executor / merge-pr`" in archive_review
    for required in (
        "Reviewer `PASS` exists for the exact revision R",
        "Lead preparation evidence",
        "repository-approved non-closing linkage",
        "predeclared safely deletable",
    ):
        assert required in merge_skill
