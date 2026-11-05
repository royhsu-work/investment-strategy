from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_skip_specs_change_has_empty_purpose_snapshot(tmp_path: Path) -> None:
    changes_root = tmp_path / "openspec" / "changes"
    change_root = changes_root / "change-a"
    change_root.mkdir(parents=True)
    (change_root / ".openspec.yaml").write_text(
        "schema: spec-driven\\nskip_specs: true\\n", encoding="utf-8"
    )
    snapshot = tmp_path / "purpose.json"

    result = _run(
        "purpose-snapshot",
        "--change",
        "change-a",
        "--changes-root",
        str(changes_root),
        "--specs-root",
        str(tmp_path / "openspec" / "specs"),
        "--snapshot-file",
        str(snapshot),
    )

    assert result.returncode == 0
    assert json.loads(snapshot.read_text(encoding="utf-8")) == {
        "change": "change-a",
        "capabilities": [],
    }

    preserve = _run(
        "purpose-preserve",
        "--snapshot-file",
        str(snapshot),
        "--specs-root",
        str(tmp_path / "openspec" / "specs"),
    )
    assert preserve.returncode == 0


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
    assert '--issue-number "$REQUEST_ISSUE"' not in workflow
    assert '"$issue_number" != "$REQUEST_ISSUE"' in workflow
    assert "printf 'issue_number=%s\\n' \"$REQUEST_ISSUE\"" in workflow


def test_existing_archive_branch_must_rebuild_against_fresh_source() -> None:
    """A syntactically valid old archive cannot substitute for today's Change."""

    workflow = (ROOT / ".github/workflows/openspec-archive.yml").read_text(encoding="utf-8")
    # This was the #322 regression: the branch existed from an older main,
    # so the producer silently skipped both the archive and its commit.
    assert "steps.branch.outputs.existing == 'false'" not in workflow
    assert 'openspec archive "$CHANGE" --yes' in workflow
    assert "git push --force" not in workflow
    assert '2) old_head=""' in workflow
    assert "Archive branch lookup unavailable" in workflow


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(  # noqa: S603, S607 - only test-owned Git fixtures
        ["git", *arguments],  # noqa: S607
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _archive_publish_script() -> str:
    workflow = (ROOT / ".github/workflows/openspec-archive.yml").read_text(encoding="utf-8")
    section = workflow.split("      - name: Commit and push archive branch\n", 1)[1]
    section = section.split("\n      - name: ", 1)[0]
    lines = section.split("        run: |\n", 1)[1].splitlines()
    return "\n".join(line[10:] if line.startswith("          ") else line for line in lines)


def _archive_git_fixture(
    tmp_path: Path,
    *,
    unrelated: bool = False,
    conflict: bool = False,
    ambiguous: bool = False,
) -> tuple[Path, str, str, Path]:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    remote.mkdir()
    work.mkdir()
    _git(remote, "init", "--bare", "--initial-branch=main")
    _git(work, "init", "--initial-branch=main")
    _git(work, "config", "user.name", "Archive test")
    _git(work, "config", "user.email", "archive@example.test")
    _git(work, "remote", "add", "origin", str(remote))

    change = work / "openspec/changes/change-a"
    change.mkdir(parents=True)
    (change / "proposal.md").write_text("approved proposal\n", encoding="utf-8")
    (change / "tasks.md").write_text("old tasks\n", encoding="utf-8")
    script = work / ".github/scripts/openspec_archive.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script)
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "base")
    _git(work, "push", "origin", "main")

    _git(work, "switch", "-c", "agent/archive-change-a")
    old_archive = work / "openspec/changes/archive/2026-11-01-change-a"
    old_archive.parent.mkdir(parents=True)
    shutil.move(str(change), old_archive)
    if ambiguous:
        second_archive = old_archive.parent / "2026-11-02-change-a"
        shutil.copytree(old_archive, second_archive)
    if unrelated:
        (work / "notes.txt").write_text("preserve me\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "old archive")
    old_head = _git(work, "rev-parse", "HEAD")
    _git(work, "push", "origin", "HEAD:agent/archive-change-a")

    _git(work, "switch", "main")
    (change / "tasks.md").write_text("current approved tasks\n", encoding="utf-8")
    if conflict:
        (work / "notes.txt").write_text("different main edit\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "new main")
    source_sha = _git(work, "rev-parse", "HEAD")
    _git(work, "push", "origin", "main")

    _git(work, "switch", "--detach", "HEAD")
    new_archive = work / "openspec/changes/archive/2026-11-04-change-a"
    shutil.move(str(change), new_archive)
    return work, source_sha, old_head, remote


@pytest.mark.parametrize(
    ("unrelated", "conflict", "ambiguous"),
    [(False, False, False), (True, False, False), (True, True, False), (False, False, True)],
)
def test_archive_producer_refreshes_old_branch_without_forcing_or_losing_unrelated_changes(
    tmp_path: Path, unrelated: bool, conflict: bool, ambiguous: bool
) -> None:
    work, source_sha, old_head, remote = _archive_git_fixture(
        tmp_path, unrelated=unrelated, conflict=conflict, ambiguous=ambiguous
    )
    environment = dict(os.environ)
    environment.update(CHANGE="change-a", SOURCE_SHA=source_sha, OLD_HEAD=old_head)
    result = subprocess.run(  # noqa: S603, S607 - exact repository-owned workflow step
        ["bash", "-euo", "pipefail", "-c", _archive_publish_script()],  # noqa: S607
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    new_head = _git(remote, "rev-parse", "refs/heads/agent/archive-change-a")
    if ambiguous:
        assert result.returncode != 0
        assert "missing or ambiguous Change history" in result.stdout
        assert new_head == old_head
        return
    if conflict:
        assert result.returncode != 0
        assert "Conflicting unrelated archive branch path" in result.stdout
        assert new_head == old_head
        return
    assert result.returncode == 0, result.stderr + result.stdout
    assert new_head != old_head
    _git(work, "merge-base", "--is-ancestor", old_head, new_head)
    _git(work, "merge-base", "--is-ancestor", source_sha, new_head)
    assert (
        _git(work, "show", f"{new_head}:openspec/changes/archive/2026-11-04-change-a/tasks.md")
        == "current approved tasks"
    )
    if unrelated:
        assert _git(work, "show", f"{new_head}:notes.txt") == "preserve me"


def test_archive_producer_reuses_current_source_without_second_commit(
    tmp_path: Path,
) -> None:
    """Replaying the approved source must not move the archive head."""

    work, source_sha, old_head, remote = _archive_git_fixture(tmp_path)
    environment = dict(os.environ)
    environment.update(CHANGE="change-a", SOURCE_SHA=source_sha, OLD_HEAD=old_head)
    first = subprocess.run(  # noqa: S603, S607 - exact repository-owned workflow step
        ["bash", "-euo", "pipefail", "-c", _archive_publish_script()],  # noqa: S607
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr + first.stdout
    published_head = _git(remote, "rev-parse", "refs/heads/agent/archive-change-a")

    # Re-evaluate the exact same main on another day. A second OpenSpec CLI
    # archive can choose a different YYYY-MM-DD directory, but this is still
    # the same approved Change and must reuse its already-current branch.
    _git(work, "switch", "--detach", source_sha)
    change = work / "openspec/changes/change-a"
    later_archive = work / "openspec/changes/archive/2026-11-05-change-a"
    later_archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(change), later_archive)
    environment["OLD_HEAD"] = published_head
    second = subprocess.run(  # noqa: S603, S607 - exact repository-owned workflow step
        ["bash", "-euo", "pipefail", "-c", _archive_publish_script()],  # noqa: S607
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode == 0, second.stderr + second.stdout
    assert _git(remote, "rev-parse", "refs/heads/agent/archive-change-a") == published_head
    assert "Already-current archive branch" in second.stdout


def test_archive_producer_rejects_current_source_with_conflicting_canonical_effects(
    tmp_path: Path,
) -> None:
    """Matching archived Change bytes cannot conceal a divergent canonical spec."""

    work, source_sha, old_head, remote = _archive_git_fixture(tmp_path)
    environment = dict(os.environ)
    environment.update(CHANGE="change-a", SOURCE_SHA=source_sha, OLD_HEAD=old_head)
    first = subprocess.run(  # noqa: S603, S607 - exact repository-owned workflow step
        ["bash", "-euo", "pipefail", "-c", _archive_publish_script()],  # noqa: S607
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr + first.stdout
    published_head = _git(remote, "rev-parse", "refs/heads/agent/archive-change-a")

    _git(work, "switch", "--detach", source_sha)
    change = work / "openspec/changes/change-a"
    later_archive = work / "openspec/changes/archive/2026-11-05-change-a"
    later_archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(change), later_archive)
    canonical = work / "openspec/specs/change-a/spec.md"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text("unexpected canonical revision\n", encoding="utf-8")
    environment["OLD_HEAD"] = published_head
    second = subprocess.run(  # noqa: S603, S607 - exact repository-owned workflow step
        ["bash", "-euo", "pipefail", "-c", _archive_publish_script()],  # noqa: S607
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode != 0
    assert "conflicting canonical spec effects" in second.stdout
    assert _git(remote, "rev-parse", "refs/heads/agent/archive-change-a") == published_head


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
