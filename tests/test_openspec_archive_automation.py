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
    status_path = tmp_path / "status.json"
    status_path.write_text(json.dumps({"isComplete": False}), encoding="utf-8")

    result = _run(
        "completion",
        "--event-name",
        "pull_request",
        "--status-file",
        str(status_path),
    )

    assert result.returncode == 0
    assert "should_archive=false" in result.stdout
    assert "reason=change-incomplete" in result.stdout


def test_incomplete_manual_archive_fails_loudly(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    status_path.write_text(json.dumps({"isComplete": False}), encoding="utf-8")

    result = _run(
        "completion",
        "--event-name",
        "workflow_dispatch",
        "--status-file",
        str(status_path),
    )

    assert result.returncode != 0
    assert "Manual archive requires a Complete OpenSpec change" in result.stderr


def test_complete_change_is_eligible_for_archive(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    status_path.write_text(json.dumps({"isComplete": True}), encoding="utf-8")

    result = _run(
        "completion",
        "--event-name",
        "pull_request",
        "--status-file",
        str(status_path),
    )

    assert result.returncode == 0
    assert "should_archive=true" in result.stdout
    assert "reason=change-complete" in result.stdout
