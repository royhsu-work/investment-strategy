from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/openspec_archive.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter and repository-owned script
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _classify(
    tmp_path: Path,
    *,
    merged: bool = True,
    head_ref: str = "feature/arbitrary-name",
    head_repo: str = "owner/repo",
    base_repo: str = "owner/repo",
    recovery: bool = False,
    changed_files: tuple[str, ...] = (),
    active_changes: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    changes_root = tmp_path / "openspec" / "changes"
    changes_root.mkdir(parents=True)
    for change in active_changes:
        (changes_root / change).mkdir()

    files_path = tmp_path / "changed-files.txt"
    files_path.write_text("\n".join(changed_files), encoding="utf-8")

    return _run(
        "classify",
        "--event-name",
        "pull_request",
        "--merged",
        str(merged).lower(),
        "--head-ref",
        head_ref,
        "--head-repo",
        head_repo,
        "--base-repo",
        base_repo,
        "--recovery",
        str(recovery).lower(),
        "--changed-files",
        str(files_path),
        "--changes-root",
        str(changes_root),
    )


def _write_change_list(
    path: Path,
    *,
    status: str,
    completed_tasks: int,
    total_tasks: int,
) -> None:
    path.write_text(
        json.dumps(
            {
                "changes": [
                    {
                        "name": "change-a",
                        "completedTasks": completed_tasks,
                        "totalTasks": total_tasks,
                        "status": status,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _completion(
    tmp_path: Path,
    *,
    mode: str,
    status: str,
    completed_tasks: int,
    total_tasks: int,
) -> subprocess.CompletedProcess[str]:
    list_path = tmp_path / "changes.json"
    _write_change_list(
        list_path,
        status=status,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
    )
    return _run(
        "completion",
        "--mode",
        mode,
        "--change",
        "change-a",
        "--list-file",
        str(list_path),
    )


def test_closed_unmerged_pr_is_successful_noop(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        merged=False,
        changed_files=("openspec/changes/change-a/tasks.md",),
        active_changes=("change-a",),
    )

    assert result.returncode == 0
    assert "action=noop" in result.stdout
    assert "reason=not-merged" in result.stdout


def test_archive_pr_is_unconditional_noop(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        head_ref="agent/archive-change-a",
        recovery=True,
        changed_files=("openspec/changes/change-a/tasks.md",),
        active_changes=("change-a",),
    )

    assert result.returncode == 0
    assert "action=noop" in result.stdout
    assert "reason=archive-pr" in result.stdout


def test_ordinary_pr_without_active_change_path_is_noop(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        changed_files=("README.md", "src/investment_strategy/domain/models.py"),
        active_changes=("change-a",),
    )

    assert result.returncode == 0
    assert "action=noop" in result.stdout
    assert "reason=no-active-change" in result.stdout


def test_normal_classifier_uses_changed_files_not_branch_name(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        head_ref="totally-unrelated-branch-name",
        changed_files=("openspec/changes/change-a/tasks.md",),
        active_changes=("change-a",),
    )

    assert result.returncode == 0
    assert "action=evaluate" in result.stdout
    assert "change=change-a" in result.stdout
    assert "mode=normal" in result.stdout


def test_touched_change_that_is_not_active_in_snapshot_is_ignored(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        changed_files=("openspec/changes/already-archived/tasks.md",),
        active_changes=("different-active-change",),
    )

    assert result.returncode == 0
    assert "action=noop" in result.stdout
    assert "reason=no-active-change" in result.stdout


def test_multiple_active_changes_fail_as_ambiguous(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        changed_files=(
            "openspec/changes/change-a/tasks.md",
            "openspec/changes/change-b/tasks.md",
        ),
        active_changes=("change-a", "change-b"),
    )

    assert result.returncode != 0
    assert "Ambiguous OpenSpec archive scope" in result.stderr
    assert "change-a" in result.stderr
    assert "change-b" in result.stderr


def test_unrelated_fork_pr_remains_noop(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        head_repo="external/fork",
        changed_files=("README.md",),
        active_changes=("change-a",),
    )

    assert result.returncode == 0
    assert "action=noop" in result.stdout
    assert "reason=no-active-change" in result.stdout


def test_fork_pr_with_active_candidate_fails_as_unsupported(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        head_repo="external/fork",
        changed_files=("openspec/changes/change-a/tasks.md",),
        active_changes=("change-a",),
    )

    assert result.returncode != 0
    assert "Unsupported automatic archive source" in result.stderr
    assert "recovery/manual" in result.stderr


def test_fork_pr_with_multiple_active_candidates_fails_as_unsupported(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        head_repo="external/fork",
        changed_files=(
            "openspec/changes/change-a/tasks.md",
            "openspec/changes/change-b/tasks.md",
        ),
        active_changes=("change-a", "change-b"),
    )

    assert result.returncode != 0
    assert "Unsupported automatic archive source" in result.stderr
    assert "Ambiguous OpenSpec archive scope" not in result.stderr
    assert "recovery/manual" in result.stderr


def test_same_repository_recovery_selects_change_from_agent_branch(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        recovery=True,
        head_ref="agent/change-a",
        changed_files=("README.md",),
        active_changes=("change-a",),
    )

    assert result.returncode == 0
    assert "action=evaluate" in result.stdout
    assert "change=change-a" in result.stdout
    assert "mode=recovery" in result.stdout


def test_recovery_requires_same_repository_source(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        recovery=True,
        head_ref="agent/change-a",
        head_repo="external/fork",
        active_changes=("change-a",),
    )

    assert result.returncode != 0
    assert "Recovery archive requires a same-repository PR" in result.stderr


def test_recovery_requires_valid_agent_change_selector(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        recovery=True,
        head_ref="feature/change-a",
        active_changes=("change-a",),
    )

    assert result.returncode != 0
    assert "Recovery archive requires head branch agent/<change>" in result.stderr


def test_recovery_requires_selected_active_change(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        recovery=True,
        head_ref="agent/change-a",
        active_changes=("change-b",),
    )

    assert result.returncode != 0
    assert "Recovery change is not active" in result.stderr


def test_incomplete_normal_change_is_noop(tmp_path: Path) -> None:
    result = _completion(
        tmp_path,
        mode="normal",
        status="in-progress",
        completed_tasks=3,
        total_tasks=4,
    )

    assert result.returncode == 0
    assert "should_archive=false" in result.stdout
    assert "reason=change-incomplete" in result.stdout


def test_no_tasks_normal_change_is_not_complete(tmp_path: Path) -> None:
    result = _completion(
        tmp_path,
        mode="normal",
        status="no-tasks",
        completed_tasks=0,
        total_tasks=0,
    )

    assert result.returncode == 0
    assert "should_archive=false" in result.stdout


def test_incomplete_manual_archive_fails_loudly(tmp_path: Path) -> None:
    result = _completion(
        tmp_path,
        mode="manual",
        status="in-progress",
        completed_tasks=3,
        total_tasks=4,
    )

    assert result.returncode != 0
    assert "Manual archive requires a Complete OpenSpec change" in result.stderr


def test_incomplete_recovery_archive_fails_loudly(tmp_path: Path) -> None:
    result = _completion(
        tmp_path,
        mode="recovery",
        status="in-progress",
        completed_tasks=3,
        total_tasks=4,
    )

    assert result.returncode != 0
    assert "Recovery archive requires a Complete OpenSpec change" in result.stderr


def test_complete_change_is_eligible_for_archive(tmp_path: Path) -> None:
    result = _completion(
        tmp_path,
        mode="normal",
        status="complete",
        completed_tasks=4,
        total_tasks=4,
    )

    assert result.returncode == 0
    assert "should_archive=true" in result.stdout
    assert "reason=change-complete" in result.stdout


def test_earlier_merge_snapshot_stays_incomplete_after_later_completion(tmp_path: Path) -> None:
    earlier = tmp_path / "earlier-snapshot.json"
    later = tmp_path / "later-main.json"
    _write_change_list(earlier, status="in-progress", completed_tasks=3, total_tasks=4)
    _write_change_list(later, status="complete", completed_tasks=4, total_tasks=4)

    result = _run(
        "completion",
        "--mode",
        "normal",
        "--change",
        "change-a",
        "--list-file",
        str(earlier),
    )

    assert json.loads(later.read_text(encoding="utf-8"))["changes"][0]["status"] == "complete"
    assert result.returncode == 0
    assert "should_archive=false" in result.stdout
    assert "reason=change-incomplete" in result.stdout


def test_completion_fails_when_change_is_missing_from_openspec_list(tmp_path: Path) -> None:
    list_path = tmp_path / "changes.json"
    list_path.write_text(json.dumps({"changes": []}), encoding="utf-8")

    result = _run(
        "completion",
        "--mode",
        "normal",
        "--change",
        "change-a",
        "--list-file",
        str(list_path),
    )

    assert result.returncode != 0
    assert "not present in OpenSpec active change list" in result.stderr


def test_archive_workflow_keeps_reviewed_lifecycle_guards() -> None:
    workflow = (ROOT / ".github/workflows/openspec-archive.yml").read_text(encoding="utf-8")

    for required in (
        "workflow_dispatch:",
        "run-name: OpenSpec Archive",
        "request_key",
        "issue:",
        "revision:",
        "issue_comment:",
        "- created",
        "pull_request:",
        "- closed",
        "pull-requests: read",
        "cancel-in-progress: false",
        "ARCHIVE_REQUEST",
        "github.event.pull_request.merged && github.event.pull_request.merge_commit_sha",
        "github.event.pull_request.head.repo.full_name",
        "github.event.pull_request.base.repo.full_name",
        "openspec-archive-recovery",
        "gh api --paginate",
        "openspec list --json",
        "openspec validate",
        "git ls-remote --exit-code --heads",
        "openspec archive",
        "agent/archive-$CHANGE",
        'git push -u origin HEAD:"$target_branch"',
    ):
        assert required in workflow
    assert "queue: max" not in workflow
    assert "pull-requests: write" not in workflow
    assert "Create final Archive PR with closing linkage" not in workflow
    assert "gh pr create" not in workflow
    assert "ref: main" not in workflow
    assert "git push --force" not in workflow
    assert "git push -f" not in workflow
    assert "pull_request_target:" not in workflow


def test_readme_documents_state_driven_archive_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for required in (
        "Merged-PR archive classifier",
        "branch convention",
        "archive routing 不依賴 branch name",
        "0 個 active candidate",
        ">1 active touched",
        "Complete` 是 repository-level implementation completion signal",
        "triggering merge snapshot",
        "openspec-archive-recovery",
        "same-repository",
        "unsupported automatic source",
        "cancel-in-progress: false",
        "in-flight request/run/result chain",
        "application-owned `workflow_dispatch` actuator",
        "GITHUB_TOKEN 寫入的 issue-comment",
        "workflow_dispatch` 也保留給 recovery / migration fallback",
    ):
        assert required in readme
