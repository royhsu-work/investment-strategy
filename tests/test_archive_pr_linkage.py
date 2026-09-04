from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/archive_pr_linkage.py"
WORKFLOW = ROOT / ".github/workflows/openspec-archive.yml"
MERGE_SKILL = ROOT / "agents/skills/merge-pr/SKILL.md"
LIFECYCLE_SKILL = ROOT / "agents/skills/lifecycle-finalize/SKILL.md"
AGENTS = ROOT / "agents/AGENTS.md"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter and repository-owned script
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_issues(path: Path, issues: list[dict[str, object]]) -> None:
    path.write_text(json.dumps([issues]), encoding="utf-8")


def test_resolve_requires_exactly_one_coordination_issue_for_change(tmp_path: Path) -> None:
    issues = tmp_path / "issues.json"
    _write_issues(
        issues,
        [
            {
                "number": 21,
                "body": "## Workflow identity\n\n`Change: change-a`\n",
                "state": "open",
                "pull_request": None,
            },
            {
                "number": 22,
                "body": "Change: `different-change`",
                "state": "open",
                "pull_request": None,
            },
        ],
    )
    result = _run("resolve", "--change", "change-a", "--issues-file", str(issues))
    assert result.returncode == 0
    assert "issue_number=21" in result.stdout


def test_resolve_fails_closed_on_ambiguous_coordination_issue(tmp_path: Path) -> None:
    issues = tmp_path / "issues.json"
    _write_issues(
        issues,
        [
            {
                "number": 21,
                "body": "Change: `change-a`",
                "state": "open",
                "pull_request": None,
            },
            {
                "number": 23,
                "body": "Change: change-a",
                "state": "open",
                "pull_request": None,
            },
        ],
    )
    result = _run("resolve", "--change", "change-a", "--issues-file", str(issues))
    assert result.returncode != 0
    assert "exactly one coordination Issue" in result.stderr


def test_resolve_fails_closed_on_prematurely_closed_coordination_issue(
    tmp_path: Path,
) -> None:
    issues = tmp_path / "issues.json"
    _write_issues(
        issues,
        [
            {
                "number": 21,
                "body": "Change: `change-a`",
                "state": "closed",
                "pull_request": None,
            }
        ],
    )
    result = _run("resolve", "--change", "change-a", "--issues-file", str(issues))
    assert result.returncode != 0
    assert "Coordination Issue #21" in result.stderr
    assert "must be open before Archive PR creation" in result.stderr


def test_render_archive_pr_body_contains_only_expected_non_closing_linkage(
    tmp_path: Path,
) -> None:
    body = tmp_path / "archive-pr.md"
    result = _run(
        "render",
        "--change",
        "change-a",
        "--issue-number",
        "21",
        "--body-file",
        str(body),
    )
    assert result.returncode == 0
    rendered = body.read_text(encoding="utf-8")
    assert "Archive OpenSpec change `change-a`." in rendered
    assert "Refs #21" in rendered
    assert rendered.count("Refs #21") == 1
    assert "Closes #21" not in rendered
    assert "coordination Issue remains open" in rendered
    assert "Reviewer PASS" in rendered
    assert "Lead terminal finalization" in rendered


def test_archive_workflow_owns_linkage_observation_and_carrier_delegation() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    lifecycle_skill = LIFECYCLE_SKILL.read_text(encoding="utf-8")
    merge_skill = MERGE_SKILL.read_text(encoding="utf-8")
    for required in (
        "issues: read",
        "pull-requests: read",
        "issue_comment:",
        "ARCHIVE_REQUEST",
        "archive_pr_linkage.py resolve",
        "archive_pr_linkage.py render",
        "gh pr list",
        "ready-for-legal-carrier",
        'git push -u origin HEAD:"$target_branch"',
    ):
        assert required in workflow
    for forbidden in (
        "pull-requests: write",
        "gh pr create",
    ):
        assert forbidden not in workflow
    for required in (
        "archive preparation",
        "Refs #<coordination-issue>",
        "Reviewer / review-archive",
        "coordination Issue",
    ):
        assert required in lifecycle_skill
    for required in (
        "merge-archive-pr",
        "non-closing linkage",
        "same persistent coordination Issue",
        "fails closed",
    ):
        assert required in merge_skill


def test_finalize_archive_keeps_terminal_result_before_later_wake() -> None:
    skill = " ".join(LIFECYCLE_SKILL.read_text(encoding="utf-8").split())
    assert "lifecycle-complete" in skill
    assert "finalize-archive" in skill
    assert "successor executes only on a later wake" in skill


def test_premature_coordination_issue_closure_stays_blocked() -> None:
    skill = " ".join(LIFECYCLE_SKILL.read_text(encoding="utf-8").split())
    assert "premature close" in skill
    assert "blocked" in skill
