from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

UPSTREAM_RELEASE = "v1.9.0"
UPSTREAM_COMMIT = "2826b8889e5223a9a8095d4428b60b56597e1020"
REQUIREMENT = "Preserve surviving scenarios"


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed OpenSpec executable with repository-owned fixture arguments
        ["openspec", *args],
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
    surviving = """

#### Scenario: Surviving scenario
- **WHEN** a MODIFIED delta changes the requirement
- **THEN** this surviving scenario remains present
""" if complete else ""
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
    _write(change / "design.md", "# Design\n\nUse the smallest executable compatibility fixture.\n")
    _write(
        change / "tasks.md",
        "# Tasks\n\n## 1. Compatibility\n\n- [x] 1.1 Validate the executable compatibility fixture.\n",
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


def main() -> int:
    # The qualification intentionally executes `openspec validate` rather than reproducing OpenSpec parsing.
    with tempfile.TemporaryDirectory(prefix="openspec-compat-") as directory:
        root = Path(directory)
        incomplete, complete = _fixture(root)

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
                "incomplete-modified must be rejected specifically for dropping a surviving scenario; "
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

        canonical = (root / "openspec/specs/compatibility/spec.md").read_text(encoding="utf-8")
        if canonical.count("#### Scenario:") != 2 or "#### Scenario: Surviving scenario" not in canonical:
            raise SystemExit("archive canonicalization lost the surviving scenario")
        if (root / "openspec/changes/complete-modified").exists():
            raise SystemExit("archive left the complete-modified change active")
        if not list((root / "openspec/changes/archive").glob("*-complete-modified")):
            raise SystemExit("archive did not produce the expected archived change directory")

    print(f"qualified OpenSpec {UPSTREAM_RELEASE} at {UPSTREAM_COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
