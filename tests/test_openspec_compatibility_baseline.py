from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / ".github/openspec-version"
VALIDATE_WORKFLOW = ROOT / ".github/workflows/openspec-validate.yml"
ARCHIVE_WORKFLOW = ROOT / ".github/workflows/openspec-archive.yml"
COMPATIBILITY_HARNESS = ROOT / ".github/scripts/openspec_compatibility.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_validation_and_archive_share_qualified_openspec_version_source() -> None:
    assert VERSION_FILE.is_file(), "OpenSpec executable version must have one repository-owned SSOT"
    assert _read(VERSION_FILE).strip() == "1.9.0"

    for workflow in (VALIDATE_WORKFLOW, ARCHIVE_WORKFLOW):
        text = _read(workflow)
        assert ".github/openspec-version" in text
        assert "@fission-ai/openspec@1.3.1" not in text
        assert "@fission-ai/openspec@1.9.0" not in text


def test_no_governed_workflow_independently_pins_openspec() -> None:
    workflow_dir = ROOT / ".github/workflows"
    governed = [VALIDATE_WORKFLOW, ARCHIVE_WORKFLOW]
    version = _read(VERSION_FILE).strip()

    for workflow in governed:
        text = _read(workflow)
        assert f"@fission-ai/openspec@{version}" not in text

    for workflow in workflow_dir.glob("*.yml"):
        if workflow in governed:
            continue
        assert "@fission-ai/openspec@" not in _read(workflow)


def test_validation_runs_executable_compatibility_harness() -> None:
    assert COMPATIBILITY_HARNESS.is_file(), (
        "qualified baseline needs executable compatibility fixtures"
    )
    workflow = _read(VALIDATE_WORKFLOW)
    assert ".github/scripts/openspec_compatibility.py" in workflow

    harness = _read(COMPATIBILITY_HARNESS)
    for required in (
        "incomplete-modified",
        "complete-modified",
        "openspec validate",
        "surviving scenario",
        "UPSTREAM_RELEASE = \"v1.9.0\"",
        "2826b8889e5223a9a8095d4428b60b56597e1020",
    ):
        assert required in harness
