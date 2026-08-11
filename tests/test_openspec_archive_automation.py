from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/openspec_archive.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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
        "--changed-files",
        str(files_path),
        "--changes-root",
        str(changes_root),
    )


def _completion(
    tmp_path: Path,
    *,
    event_name: str,
    status: str,
    completed_tasks: int,
    total_tasks: int,
) -> subprocess.CompletedProcess[str]:
    list_path = tmp_path / "changes.json"
    list_path.write_text(
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
    return _run(
        "completion",
        "--event-name",
        event_name,
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


def test_classifier_uses_changed_files_not_branch_name(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        head_ref="totally-unrelated-branch-name",
        changed_files=("openspec/changes/change-a/tasks.md",),
        active_changes=("change-a",),
    )

    assert result.returncode == 0
    assert "action=evaluate" in result.stdout
    assert "change=change-a" in result.stdout


def test_touched_change_that_is_not_active_on_main_is_ignored(tmp_path: Path) -> None:
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


def test_incomplete_pr_change_is_noop(tmp_path: Path) -> None:
    result = _completion(
        tmp_path,
        event_name="pull_request",
        status="in-progress",
        completed_tasks=3,
        total_tasks=4,
    )

    assert result.returncode == 0
    assert "should_archive=false" in result.stdout
    assert "reason=change-incomplete" in result.stdout


def test_no_tasks_pr_change_is_not_complete(tmp_path: Path) -> None:
    result = _completion(
        tmp_path,
        event_name="pull_request",
        status="no-tasks",
        completed_tasks=0,
        total_tasks=0,
    )

    assert result.returncode == 0
    assert "should_archive=false" in result.stdout


def test_incomplete_manual_archive_fails_loudly(tmp_path: Path) -> None:
    result = _completion(
        tmp_path,
        event_name="workflow_dispatch",
        status="in-progress",
        completed_tasks=3,
        total_tasks=4,
    )

    assert result.returncode != 0
    assert "Manual archive requires a Complete OpenSpec change" in result.stderr


def test_complete_change_is_eligible_for_archive(tmp_path: Path) -> None:
    result = _completion(
        tmp_path,
        event_name="pull_request",
        status="complete",
        completed_tasks=4,
        total_tasks=4,
    )

    assert result.returncode == 0
    assert "should_archive=true" in result.stdout
    assert "reason=change-complete" in result.stdout


def test_completion_fails_when_change_is_missing_from_openspec_list(tmp_path: Path) -> None:
    list_path = tmp_path / "changes.json"
    list_path.write_text(json.dumps({"changes": []}), encoding="utf-8")

    result = _run(
        "completion",
        "--event-name",
        "pull_request",
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
        "pull_request:",
        "- closed",
        "pull-requests: read",
        "ref: main",
        "gh api --paginate",
        "openspec list --json",
        "openspec validate",
        "git ls-remote --exit-code --heads",
        "openspec archive",
        "agent/archive-$CHANGE",
    ):
        assert required in workflow
    assert "git push --force" not in workflow
    assert "git push -f" not in workflow


def test_readme_documents_state_driven_archive_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for required in (
        "Merged-PR archive classifier",
        "branch convention",
        "archive routing 不依賴 branch name",
        "0 個 active candidate",
        ">1 active touched",
        "Complete` 是 repository-level implementation completion signal",
        "workflow_dispatch` 保留為 recovery / migration fallback",
    ):
        assert required in readme
