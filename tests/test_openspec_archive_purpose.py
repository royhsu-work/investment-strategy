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


def _write_delta(path: Path, purpose: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"## Purpose\n\n{purpose}\n\n## ADDED Requirements\n\n"
        "### Requirement: Example\nThe system SHALL preserve behavior.\n",
        encoding="utf-8",
    )


def _write_canonical(path: Path, purpose: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"## Purpose\n\n{purpose}\n\n## Requirements\n\n"
        "### Requirement: Example\nThe system SHALL preserve behavior.\n",
        encoding="utf-8",
    )


def _snapshot(tmp_path: Path) -> tuple[Path, Path, Path]:
    changes_root = tmp_path / "openspec" / "changes"
    specs_root = tmp_path / "openspec" / "specs"
    snapshot = tmp_path / "purpose.json"
    return changes_root, specs_root, snapshot


def test_new_capability_generated_placeholder_is_replaced_exactly(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    approved = "Approved provider-neutral capability purpose."
    _write_delta(changes_root / "change-a/specs/new-cap/spec.md", approved)

    result = _run(
        "purpose-snapshot",
        "--change",
        "change-a",
        "--changes-root",
        str(changes_root),
        "--specs-root",
        str(specs_root),
        "--snapshot-file",
        str(snapshot),
    )
    assert result.returncode == 0

    canonical = specs_root / "new-cap/spec.md"
    _write_canonical(
        canonical,
        "TBD - created by archiving change change-a. Update Purpose after archive.",
    )
    result = _run(
        "purpose-preserve",
        "--snapshot-file",
        str(snapshot),
        "--specs-root",
        str(specs_root),
    )

    assert result.returncode == 0
    assert f"## Purpose\n\n{approved}\n\n## Requirements" in canonical.read_text(encoding="utf-8")


def test_purpose_replacement_preserves_requirements_and_scenarios_exactly(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    approved = "Approved purpose."
    _write_delta(changes_root / "change-a/specs/new-cap/spec.md", approved)
    assert (
        _run(
            "purpose-snapshot",
            "--change",
            "change-a",
            "--changes-root",
            str(changes_root),
            "--specs-root",
            str(specs_root),
            "--snapshot-file",
            str(snapshot),
        ).returncode
        == 0
    )

    canonical = specs_root / "new-cap/spec.md"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    requirements_suffix = (
        "## Requirements\n\n"
        "### Requirement: Preserve exact suffix\n"
        "The system SHALL retain this requirement text exactly.\n\n"
        "#### Scenario: Exact content survives\n"
        "- **WHEN** Purpose preservation runs\n"
        "- **THEN** this scenario text and spacing remain unchanged\n"
    )
    canonical.write_text(
        "## Purpose\n\n"
        "TBD - created by archiving change change-a. Update Purpose after archive.\n\n"
        + requirements_suffix,
        encoding="utf-8",
    )
    before = canonical.read_text(encoding="utf-8")
    before_suffix = before[before.index("## Requirements") :]

    result = _run(
        "purpose-preserve",
        "--snapshot-file",
        str(snapshot),
        "--specs-root",
        str(specs_root),
    )

    after = canonical.read_text(encoding="utf-8")
    after_suffix = after[after.index("## Requirements") :]
    assert result.returncode == 0
    assert after_suffix == before_suffix == requirements_suffix


def test_new_capability_exact_approved_purpose_is_accepted(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    approved = "Approved purpose."
    _write_delta(changes_root / "change-a/specs/new-cap/spec.md", approved)
    assert (
        _run(
            "purpose-snapshot",
            "--change",
            "change-a",
            "--changes-root",
            str(changes_root),
            "--specs-root",
            str(specs_root),
            "--snapshot-file",
            str(snapshot),
        ).returncode
        == 0
    )
    _write_canonical(specs_root / "new-cap/spec.md", approved)

    result = _run(
        "purpose-preserve",
        "--snapshot-file",
        str(snapshot),
        "--specs-root",
        str(specs_root),
    )
    assert result.returncode == 0


def test_new_capability_unknown_purpose_transformation_fails(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    _write_delta(changes_root / "change-a/specs/new-cap/spec.md", "Approved purpose.")
    assert (
        _run(
            "purpose-snapshot",
            "--change",
            "change-a",
            "--changes-root",
            str(changes_root),
            "--specs-root",
            str(specs_root),
            "--snapshot-file",
            str(snapshot),
        ).returncode
        == 0
    )
    _write_canonical(specs_root / "new-cap/spec.md", "Unexpected upstream rewrite.")

    result = _run(
        "purpose-preserve",
        "--snapshot-file",
        str(snapshot),
        "--specs-root",
        str(specs_root),
    )
    assert result.returncode != 0
    assert "Unexpected canonical Purpose transformation" in result.stderr


def test_existing_capability_purpose_must_remain_immutable(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    _write_delta(changes_root / "change-a/specs/existing-cap/spec.md", "Delta purpose ignored.")
    _write_canonical(specs_root / "existing-cap/spec.md", "Stable canonical purpose.")
    assert (
        _run(
            "purpose-snapshot",
            "--change",
            "change-a",
            "--changes-root",
            str(changes_root),
            "--specs-root",
            str(specs_root),
            "--snapshot-file",
            str(snapshot),
        ).returncode
        == 0
    )
    _write_canonical(specs_root / "existing-cap/spec.md", "Changed purpose.")

    result = _run(
        "purpose-preserve",
        "--snapshot-file",
        str(snapshot),
        "--specs-root",
        str(specs_root),
    )
    assert result.returncode != 0
    assert "Existing canonical Purpose changed" in result.stderr


def test_new_capability_missing_purpose_fails_before_archive(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    delta = changes_root / "change-a/specs/new-cap/spec.md"
    delta.parent.mkdir(parents=True, exist_ok=True)
    delta.write_text(
        "## ADDED Requirements\n\n### Requirement: Example\nThe system SHALL work.\n",
        encoding="utf-8",
    )

    result = _run(
        "purpose-snapshot",
        "--change",
        "change-a",
        "--changes-root",
        str(changes_root),
        "--specs-root",
        str(specs_root),
        "--snapshot-file",
        str(snapshot),
    )
    assert result.returncode != 0
    assert "exactly one ## Purpose" in result.stderr


def test_new_capability_empty_purpose_fails_before_archive(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    delta = changes_root / "change-a/specs/new-cap/spec.md"
    delta.parent.mkdir(parents=True, exist_ok=True)
    delta.write_text(
        "## Purpose\n\n   \n\t\n## ADDED Requirements\n\n"
        "### Requirement: Example\nThe system SHALL work.\n",
        encoding="utf-8",
    )

    result = _run(
        "purpose-snapshot",
        "--change",
        "change-a",
        "--changes-root",
        str(changes_root),
        "--specs-root",
        str(specs_root),
        "--snapshot-file",
        str(snapshot),
    )
    assert result.returncode != 0
    assert "has an empty ## Purpose section" in result.stderr


def test_new_capability_generated_delta_placeholder_fails_before_archive(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    _write_delta(
        changes_root / "change-a/specs/new-cap/spec.md",
        "TBD - created by archiving change change-a. Update Purpose after archive.",
    )

    result = _run(
        "purpose-snapshot",
        "--change",
        "change-a",
        "--changes-root",
        str(changes_root),
        "--specs-root",
        str(specs_root),
        "--snapshot-file",
        str(snapshot),
    )
    assert result.returncode != 0
    assert "delta Purpose is an OpenSpec generated placeholder" in result.stderr


def test_duplicate_delta_purpose_fails_before_archive(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    delta = changes_root / "change-a/specs/new-cap/spec.md"
    delta.parent.mkdir(parents=True, exist_ok=True)
    delta.write_text(
        "## Purpose\n\nFirst.\n\n## Purpose\n\nSecond.\n\n"
        "## ADDED Requirements\n\n### Requirement: Example\nThe system SHALL work.\n",
        encoding="utf-8",
    )

    result = _run(
        "purpose-snapshot",
        "--change",
        "change-a",
        "--changes-root",
        str(changes_root),
        "--specs-root",
        str(specs_root),
        "--snapshot-file",
        str(snapshot),
    )
    assert result.returncode != 0
    assert "exactly one ## Purpose" in result.stderr


def test_canonical_shape_guard_requires_requirements_after_purpose(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    _write_delta(changes_root / "change-a/specs/new-cap/spec.md", "Approved purpose.")
    assert (
        _run(
            "purpose-snapshot",
            "--change",
            "change-a",
            "--changes-root",
            str(changes_root),
            "--specs-root",
            str(specs_root),
            "--snapshot-file",
            str(snapshot),
        ).returncode
        == 0
    )
    canonical = specs_root / "new-cap/spec.md"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(
        "## Purpose\n\n"
        "TBD - created by archiving change change-a. Update Purpose after archive.\n\n"
        "## Notes\n\nUnexpected shape.\n",
        encoding="utf-8",
    )

    result = _run(
        "purpose-preserve",
        "--snapshot-file",
        str(snapshot),
        "--specs-root",
        str(specs_root),
    )
    assert result.returncode != 0
    assert "canonical Purpose must be followed by ## Requirements" in result.stderr


def test_snapshot_records_existing_and_new_capabilities(tmp_path: Path) -> None:
    changes_root, specs_root, snapshot = _snapshot(tmp_path)
    _write_delta(changes_root / "change-a/specs/new-cap/spec.md", "New approved purpose.")
    _write_delta(changes_root / "change-a/specs/existing-cap/spec.md", "Delta purpose.")
    _write_canonical(specs_root / "existing-cap/spec.md", "Existing canonical purpose.")

    result = _run(
        "purpose-snapshot",
        "--change",
        "change-a",
        "--changes-root",
        str(changes_root),
        "--specs-root",
        str(specs_root),
        "--snapshot-file",
        str(snapshot),
    )
    assert result.returncode == 0
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    entries = {entry["capability"]: entry for entry in payload["capabilities"]}
    assert entries["new-cap"] == {
        "capability": "new-cap",
        "kind": "new",
        "expected_purpose": "New approved purpose.",
    }
    assert entries["existing-cap"] == {
        "capability": "existing-cap",
        "kind": "existing",
        "expected_purpose": "Existing canonical purpose.",
    }


def test_readme_documents_purpose_compatibility_guard() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for required in (
        "Pinned OpenSpec CLI 在本 repository 已觀察到",
        "canonical Purpose 必須精確等於 approved delta Purpose",
        "existing canonical capability 的 Purpose 必須保持不變",
        "pinned CLI compatibility guard",
        "不改寫 Requirements / Scenarios",
    ):
        assert required in readme
