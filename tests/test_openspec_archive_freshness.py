"""Git fixture proof that existing Archive branches cannot silently replay stale source."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/openspec_archive.py"
CHANGE = "demo-change"


def _git(repo: Path, *args: str) -> str:
    executable = shutil.which("git")
    assert executable is not None
    result = subprocess.run(  # noqa: S603 - fixed executable, isolated fixture repository
        [executable, *args], cwd=repo, check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


def _script(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter/repository script, fixture cwd
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


def _change_file(repo: Path, name: str, content: str) -> None:
    path = repo / "openspec/changes" / CHANGE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _archive_copy(repo: Path) -> None:
    original = repo / "openspec/changes" / CHANGE
    archive = repo / "openspec/changes/archive" / f"2026-11-07-{CHANGE}"
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(original), str(archive))


@pytest.fixture
def history(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "fixture@example.com")
    _git(repo, "config", "user.name", "Fixture")
    _change_file(repo, "tasks.md", "- [x] earlier work\n")
    _change_file(repo, "proposal.md", "Proposal\n")
    (repo / "README.md").write_text("Unrelated documentation\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "original Change")
    _git(repo, "switch", "-qc", f"agent/archive-{CHANGE}")
    _archive_copy(repo)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "old archive")
    stale = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "-q", "main")
    _change_file(repo, "tasks.md", "- [x] earlier work\n- [x] new approved task\n")
    _change_file(repo, "design.md", "New reviewed design\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "new task slice")
    source = _git(repo, "rev-parse", "HEAD")
    return repo, source, stale


def _plan(repo: Path, source: str, branch: str = "") -> subprocess.CompletedProcess[str]:
    return _script(
        repo,
        "branch-plan",
        "--change",
        CHANGE,
        "--source-revision",
        source,
        "--existing-ref",
        branch,
    )


def test_old_archive_branch_with_previous_tasks_must_be_reconciled(
    history: tuple[Path, str, str],
) -> None:
    repo, source, stale = history
    result = _plan(repo, source, stale)
    assert result.returncode == 0, result.stderr
    assert "mode=reconcile" in result.stdout
    assert f"existing_head={stale}" in result.stdout

    # The retained old branch becomes an immutable second parent; the new
    # artifact is generated from current main, never force-pushed over history.
    _git(repo, "switch", "-qc", "fresh-archive")
    _git(repo, "merge", "-s", "ours", "--no-ff", "--no-commit", stale)
    _archive_copy(repo)
    result = _script(repo, "verify-source", "--change", CHANGE, "--source-revision", source)
    assert result.returncode == 0, result.stderr
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "new archive")
    fresh = _git(repo, "rev-parse", "HEAD")
    assert _git(repo, "rev-list", "--parents", "-n", "1", fresh).split() == [
        fresh,
        source,
        stale,
    ]
    _git(repo, "switch", "-q", "main")
    result = _plan(repo, source, fresh)
    assert result.returncode == 0, result.stderr
    assert "mode=reuse" in result.stdout


def test_archive_reconciliation_rejects_unrelated_branch_writes(
    history: tuple[Path, str, str],
) -> None:
    repo, source, _stale = history
    _git(repo, "switch", "-q", f"agent/archive-{CHANGE}")
    (repo / "README.md").write_text("Unexpected branch edit\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "unrelated edit")
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "-q", "main")
    result = _plan(repo, source, head)
    assert result.returncode != 0
    assert "unrelated or conflicting" in result.stderr


def test_archive_reconstruction_rejects_wrong_new_change_bytes(
    history: tuple[Path, str, str],
) -> None:
    repo, source, _stale = history
    _archive_copy(repo)
    target = repo / "openspec/changes/archive" / f"2026-11-07-{CHANGE}" / "tasks.md"
    target.write_text("- [x] only the earlier tasks\n", encoding="utf-8")
    result = _script(repo, "verify-source", "--change", CHANGE, "--source-revision", source)
    assert result.returncode != 0
    assert "differ from current" in result.stderr


def test_new_archive_source_is_exact_current_main(
    history: tuple[Path, str, str],
) -> None:
    repo, source, stale = history
    wrong = _plan(repo, stale)
    assert wrong.returncode != 0
    assert "exact current checked-out main" in wrong.stderr
    new = _plan(repo, source)
    assert new.returncode == 0
    assert "mode=new" in new.stdout
