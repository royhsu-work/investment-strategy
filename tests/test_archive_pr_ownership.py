from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_archive_automation_stops_at_validated_branch_readiness() -> None:
    workflow = _read(".github/workflows/openspec-archive.yml")

    assert "pull-requests: read" in workflow
    assert "pull-requests: write" not in workflow
    assert "git push -u origin HEAD:\"$target_branch\"" in workflow
    assert "gh pr create" not in workflow
    assert "Create final Archive PR with closing linkage" not in workflow


def test_finalize_change_owns_normal_archive_pr_presentation() -> None:
    skill = _read("agents/skills/lifecycle-finalize/SKILL.md")

    for required in (
        "validated `agent/archive-<change>` branch is durably ready",
        "create or reuse the final Archive PR as ordinary lifecycle continuation",
        "Closes #<coordination-issue>",
        "normal success, not `RECOVERY_DECISION_REQUIRED`",
        "`ARCHIVE_PR_READY`",
        "`Reviewer / review-archive`",
    ):
        assert required in skill


def test_normal_archive_pr_path_preserves_independent_final_gates() -> None:
    skill = _read("agents/skills/lifecycle-finalize/SKILL.md")
    governance = _read("agents/AGENTS.md")

    for required in (
        "Reviewer PASS",
        "exact-head Lead authorization",
        "Executor merge preconditions",
        "native Issue close",
        "terminal `finalize-archive` reconstruction",
    ):
        assert required in skill

    assert "Scheduled roles do not define or execute a competing normal `archive-change` action" in governance
