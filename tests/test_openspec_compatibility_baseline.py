from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / ".github/openspec-version"
VALIDATE_WORKFLOW = ROOT / ".github/workflows/openspec-validate.yml"
ARCHIVE_WORKFLOW = ROOT / ".github/workflows/openspec-archive.yml"


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
    version = _read(VERSION_FILE).strip() if VERSION_FILE.exists() else ""

    for workflow in governed:
        text = _read(workflow)
        assert f"@fission-ai/openspec@{version}" not in text

    for workflow in workflow_dir.glob("*.yml"):
        if workflow in governed:
            continue
        assert "@fission-ai/openspec@" not in _read(workflow)
