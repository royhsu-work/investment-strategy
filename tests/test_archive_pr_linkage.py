from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/archive_pr_linkage.py"
WORKFLOW = ROOT / ".github/workflows/openspec-archive.yml"
MERGE_SKILL = ROOT / "agents/skills/merge-pr/SKILL.md"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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
            {"number": 21, "body": "## Workflow identity\n\n`Change: change-a`\n", "pull_request": None},
            {"number": 22, "body": "Change: `different-change`", "pull_request": None},
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
            {"number": 21, "body": "Change: `change-a`", "pull_request": None},
            {"number": 23, "body": "Change: change-a", "pull_request": None},
        ],
    )

    result = _run("resolve", "--change", "change-a", "--issues-file", str(issues))

    assert result.returncode != 0
    assert "exactly one coordination Issue" in result.stderr


def test_render_archive_pr_body_contains_only_expected_closing_linkage(tmp_path: Path) -> None:
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
    assert "Closes #21" in rendered
    assert rendered.count("Closes #21") == 1
    assert "lifecycle side effect only" in rendered
    assert "Reviewer PASS" in rendered
    assert "remain required before merge" in rendered
    assert "MERGE_AUTHORIZED" not in rendered


def test_archive_workflow_and_merge_skill_enforce_archive_linkage_boundary() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    merge_skill = MERGE_SKILL.read_text(encoding="utf-8")

    for required in (
        "issues: read",
        "pull-requests: write",
        "archive_pr_linkage.py resolve",
        "archive_pr_linkage.py render",
        "gh pr create",
        'Closes #',
    ):
        assert required in workflow

    for required in (
        "final Archive PR",
        "repository-approved closing linkage",
        "same persistent coordination Issue",
        "never provides merge authority",
        "do not merge",
    ):
        assert required in merge_skill
