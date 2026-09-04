from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_RELEASE = "v1.9.0"
UPSTREAM_COMMIT = "2826b8889e5223a9a8095d4428b60b56597e1020"
REQUIREMENT = "Preserve surviving scenarios"
ARCHIVE_HELPER = Path(__file__).with_name("openspec_archive.py").resolve()


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("openspec")
    if executable is None:
        raise SystemExit("openspec executable is not installed")
    return subprocess.run(  # noqa: S603 - resolved executable and repository-owned fixture args
        [executable, *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def _run_archive_helper(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter and repository-owned helper
        [sys.executable, str(ARCHIVE_HELPER), *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _canonical() -> str:
    return f"""## Purpose

Executable compatibility fixture.

## Requirements

### Requirement: {REQUIREMENT}
The system SHALL preserve every still-applicable scenario when a requirement is modified.

#### Scenario: Primary behavior
- **WHEN** the requirement is evaluated
- **THEN** the primary behavior remains present

#### Scenario: Surviving scenario
- **WHEN** a MODIFIED delta changes the requirement
- **THEN** this surviving scenario remains present
"""


def _delta(*, complete: bool) -> str:
    surviving = (
        """

#### Scenario: Surviving scenario
- **WHEN** a MODIFIED delta changes the requirement
- **THEN** this surviving scenario remains present
"""
        if complete
        else ""
    )
    return f"""## Purpose

Executable compatibility fixture.

## MODIFIED Requirements

### Requirement: {REQUIREMENT}
The system SHALL preserve every still-applicable scenario when a requirement is modified.

#### Scenario: Primary behavior
- **WHEN** the requirement is evaluated
- **THEN** the primary behavior remains present{surviving}
"""


def _artifact_files(change: Path) -> None:
    _write(
        change / "proposal.md",
        "# Change: executable compatibility fixture\n\n"
        "## Why\n\nQualify the pinned OpenSpec executable.\n\n"
        "## What Changes\n\n- Preserve all scenarios in a MODIFIED requirement.\n\n"
        "## Impact\n\n- Test fixture only.\n",
    )
    _write(
        change / "design.md",
        "# Design\n\nUse the smallest executable compatibility fixture.\n",
    )
    _write(
        change / "tasks.md",
        "# Tasks\n\n## 1. Compatibility\n\n"
        "- [x] 1.1 Validate the executable compatibility fixture.\n",
    )


def _fixture(root: Path) -> tuple[Path, Path]:
    openspec = root / "openspec"
    _write(openspec / "config.yaml", "schema: spec-driven\n")
    _write(openspec / "specs/compatibility/spec.md", _canonical())

    incomplete = openspec / "changes/incomplete-modified"
    complete = openspec / "changes/complete-modified"
    for change in (incomplete, complete):
        _artifact_files(change)
    _write(incomplete / "specs/compatibility/spec.md", _delta(complete=False))
    _write(complete / "specs/compatibility/spec.md", _delta(complete=True))
    return incomplete, complete


def _purpose_spec(purpose: str) -> str:
    return f"""## Purpose

{purpose}

## Requirements

### Requirement: Purpose fixture
The system SHALL keep Purpose exact.

#### Scenario: Purpose remains exact
- **WHEN** archive postconditions run
- **THEN** the approved Purpose remains exact
"""


def _delta_purpose(purpose: str) -> str:
    return f"""## Purpose

{purpose}

## ADDED Requirements

### Requirement: Purpose fixture
The system SHALL keep Purpose exact.

#### Scenario: Purpose remains exact
- **WHEN** archive postconditions run
- **THEN** the approved Purpose remains exact
"""


def _purpose_snapshot(root: Path, change: str, snapshot: Path) -> subprocess.CompletedProcess[str]:
    return _run_archive_helper(
        root,
        "purpose-snapshot",
        "--change",
        change,
        "--snapshot-file",
        str(snapshot),
    )


def _purpose_preserve(root: Path, snapshot: Path) -> subprocess.CompletedProcess[str]:
    return _run_archive_helper(
        root,
        "purpose-preserve",
        "--snapshot-file",
        str(snapshot),
    )


def _assert_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        raise SystemExit(
            f"{label} must succeed; exit={result.returncode}\n{result.stdout}\n{result.stderr}"
        )


def _assert_failure(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode == 0:
        raise SystemExit(f"{label} must fail closed")


def _qualify_purpose_postcondition(root: Path) -> None:
    changes = root / "openspec/changes"
    specs = root / "openspec/specs"

    new_change = "valid-new-purpose"
    new_capability = "new-purpose-capability"
    new_purpose = "Approved new capability Purpose."
    _write(changes / new_change / "specs" / new_capability / "spec.md", _delta_purpose(new_purpose))
    new_snapshot = root / "valid-new-purpose.json"
    _assert_success(_purpose_snapshot(root, new_change, new_snapshot), new_change)
    generated = f"TBD - created by archiving change {new_change}. Update Purpose after archive."
    _write(specs / new_capability / "spec.md", _purpose_spec(generated))
    _assert_success(_purpose_preserve(root, new_snapshot), new_change)
    preserved = (specs / new_capability / "spec.md").read_text(encoding="utf-8")
    if new_purpose not in preserved or generated in preserved:
        raise SystemExit("valid-new-purpose did not restore the approved Purpose")

    existing_change = "valid-existing-purpose"
    existing_capability = "existing-purpose-capability"
    existing_purpose = "Existing canonical Purpose."
    _write(specs / existing_capability / "spec.md", _purpose_spec(existing_purpose))
    _write(
        changes / existing_change / "specs" / existing_capability / "spec.md",
        _delta_purpose("Delta Purpose does not replace existing canonical Purpose."),
    )
    existing_snapshot = root / "valid-existing-purpose.json"
    _assert_success(_purpose_snapshot(root, existing_change, existing_snapshot), existing_change)
    _assert_success(_purpose_preserve(root, existing_snapshot), existing_change)

    blank_change = "blank-purpose"
    blank_capability = "blank-purpose-capability"
    _write(specs / blank_capability / "spec.md", _purpose_spec("Stable Purpose."))
    _write(
        changes / blank_change / "specs" / blank_capability / "spec.md",
        _delta_purpose("Delta Purpose."),
    )
    blank_snapshot = root / "blank-purpose.json"
    _assert_success(_purpose_snapshot(root, blank_change, blank_snapshot), blank_change)
    _write(
        specs / blank_capability / "spec.md",
        _purpose_spec("Stable Purpose.").replace("Stable Purpose.", ""),
    )
    _assert_failure(_purpose_preserve(root, blank_snapshot), blank_change)

    drift_change = "drifted-purpose"
    drift_capability = "drifted-purpose-capability"
    _write(specs / drift_capability / "spec.md", _purpose_spec("Stable existing Purpose."))
    _write(
        changes / drift_change / "specs" / drift_capability / "spec.md",
        _delta_purpose("Delta Purpose."),
    )
    drift_snapshot = root / "drifted-purpose.json"
    _assert_success(_purpose_snapshot(root, drift_change, drift_snapshot), drift_change)
    _write(specs / drift_capability / "spec.md", _purpose_spec("Drifted Purpose."))
    _assert_failure(_purpose_preserve(root, drift_snapshot), drift_change)

    unexpected_change = "unexpected-generated-purpose"
    unexpected_capability = "unexpected-generated-capability"
    approved_purpose = "Approved Purpose for unexpected-generated fixture."
    _write(
        changes / unexpected_change / "specs" / unexpected_capability / "spec.md",
        _delta_purpose(approved_purpose),
    )
    unexpected_snapshot = root / "unexpected-generated-purpose.json"
    _assert_success(
        _purpose_snapshot(root, unexpected_change, unexpected_snapshot),
        unexpected_change,
    )
    wrong_generated = (
        "TBD - created by archiving change another-change. Update Purpose after archive."
    )
    _write(specs / unexpected_capability / "spec.md", _purpose_spec(wrong_generated))
    _assert_failure(_purpose_preserve(root, unexpected_snapshot), unexpected_change)


def main() -> int:
    # Execute OpenSpec and the repository archive guard; do not reproduce either parser.
    with tempfile.TemporaryDirectory(prefix="openspec-compat-") as directory:
        root = Path(directory)
        incomplete, _complete = _fixture(root)

        rejected = _run(
            root,
            "validate",
            "incomplete-modified",
            "--type",
            "change",
            "--strict",
            "--json",
            "--no-interactive",
        )
        rejected_output = f"{rejected.stdout}\n{rejected.stderr}".lower()
        if rejected.returncode == 0 or "scenario" not in rejected_output:
            raise SystemExit(
                "incomplete-modified must be rejected for dropping a surviving scenario; "
                f"exit={rejected.returncode}\n{rejected.stdout}\n{rejected.stderr}"
            )

        accepted = _run(
            root,
            "validate",
            "complete-modified",
            "--type",
            "change",
            "--strict",
            "--json",
            "--no-interactive",
        )
        if accepted.returncode != 0:
            raise SystemExit(
                "complete-modified must pass strict validation; "
                f"exit={accepted.returncode}\n{accepted.stdout}\n{accepted.stderr}"
            )

        shutil.rmtree(incomplete)
        archived = _run(root, "archive", "complete-modified", "--yes")
        if archived.returncode != 0:
            raise SystemExit(
                "complete-modified must archive successfully; "
                f"exit={archived.returncode}\n{archived.stdout}\n{archived.stderr}"
            )

        canonical_path = root / "openspec/specs/compatibility/spec.md"
        canonical = canonical_path.read_text(encoding="utf-8")
        surviving = "#### Scenario: Surviving scenario"
        if canonical.count("#### Scenario:") != 2 or surviving not in canonical:
            raise SystemExit("archive canonicalization lost the surviving scenario")
        if (root / "openspec/changes/complete-modified").exists():
            raise SystemExit("archive left the complete-modified change active")
        archive_root = root / "openspec/changes/archive"
        if not list(archive_root.glob("*-complete-modified")):
            raise SystemExit("archive did not produce the expected archived change directory")

        _qualify_purpose_postcondition(root)

    print(f"qualified OpenSpec {UPSTREAM_RELEASE} at {UPSTREAM_COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
