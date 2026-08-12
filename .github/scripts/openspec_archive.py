from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import NoReturn

CHANGE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VALID_PROGRESS_STATES = {"complete", "in-progress", "no-tasks"}
GENERATED_PURPOSE = re.compile(
    r"^TBD - created by archiving change [a-z0-9][a-z0-9-]*\. Update Purpose after archive\.$"
)


def _fail(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def _emit(**values: str) -> None:
    for key, value in values.items():
        print(f"{key}={value}")


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    _fail(f"Expected boolean true/false, got: {value}")


def _validate_change_name(change: str) -> str:
    if not CHANGE_NAME.fullmatch(change):
        _fail(f"Invalid OpenSpec change name: {change}")
    return change


def _active_candidates(changed_files: Path, changes_root: Path) -> list[str]:
    if not changed_files.is_file():
        _fail(f"Changed-file list does not exist: {changed_files}")
    if not changes_root.is_dir():
        _fail(f"OpenSpec changes root does not exist: {changes_root}")

    candidates: set[str] = set()
    for raw_path in changed_files.read_text(encoding="utf-8").splitlines():
        path = PurePosixPath(raw_path)
        parts = path.parts
        if len(parts) < 4 or parts[:2] != ("openspec", "changes"):
            continue
        change = parts[2]
        if change == "archive" or not CHANGE_NAME.fullmatch(change):
            continue
        if (changes_root / change).is_dir():
            candidates.add(change)
    return sorted(candidates)


def _recovery_change(head_ref: str, changes_root: Path) -> str:
    prefix = "agent/"
    if not head_ref.startswith(prefix):
        _fail("Recovery archive requires head branch agent/<change>")
    change = _validate_change_name(head_ref.removeprefix(prefix))
    if not (changes_root / change).is_dir():
        _fail(f"Recovery change is not active: {change}")
    return change


def _classify(args: argparse.Namespace) -> None:
    if args.event_name == "workflow_dispatch":
        if not args.manual_change:
            _fail("workflow_dispatch requires --manual-change")
        change = _validate_change_name(args.manual_change)
        _emit(action="evaluate", change=change, mode="manual", reason="manual-dispatch")
        return

    if args.event_name != "pull_request":
        _fail(f"Unsupported event: {args.event_name}")

    if not _parse_bool(args.merged):
        _emit(action="noop", change="", mode="normal", reason="not-merged")
        return

    if args.head_ref.startswith("agent/archive-"):
        _emit(action="noop", change="", mode="normal", reason="archive-pr")
        return

    changes_root = Path(args.changes_root)
    same_repository = args.head_repo == args.base_repo
    recovery = _parse_bool(args.recovery)

    if recovery:
        if not same_repository:
            _fail("Recovery archive requires a same-repository PR")
        change = _recovery_change(args.head_ref, changes_root)
        _emit(action="evaluate", change=change, mode="recovery", reason="explicit-recovery")
        return

    candidates = _active_candidates(Path(args.changed_files), changes_root)
    if not candidates:
        _emit(action="noop", change="", mode="normal", reason="no-active-change")
        return
    if not same_repository:
        _fail(
            "Unsupported automatic archive source: OpenSpec candidate came from a fork; "
            "use the base-repository recovery/manual path"
        )
    if len(candidates) > 1:
        _fail("Ambiguous OpenSpec archive scope: " + ", ".join(candidates))

    _emit(action="evaluate", change=candidates[0], mode="normal", reason="single-active-change")


def _is_change_entry(entry: object, change: str) -> bool:
    return isinstance(entry, dict) and entry.get("name") == change


def _load_change_progress(list_file: Path, change: str) -> tuple[str, int, int]:
    try:
        payload = json.loads(list_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"Unable to read OpenSpec list JSON: {exc}")

    changes = payload.get("changes") if isinstance(payload, dict) else None
    if not isinstance(changes, list):
        _fail("OpenSpec list JSON must contain a changes array")

    matches = [entry for entry in changes if _is_change_entry(entry, change)]
    if len(matches) != 1:
        _fail(f"Change {change} not present in OpenSpec active change list")

    entry = matches[0]
    status = entry.get("status")
    completed = entry.get("completedTasks")
    total = entry.get("totalTasks")
    if status not in VALID_PROGRESS_STATES:
        _fail(f"Unexpected OpenSpec status for {change}: {status}")
    if not isinstance(completed, int) or isinstance(completed, bool) or completed < 0:
        _fail(f"Invalid completedTasks for {change}: {completed}")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        _fail(f"Invalid totalTasks for {change}: {total}")
    if completed > total:
        _fail(f"Invalid task progress for {change}: {completed}/{total}")
    if status == "complete" and (total == 0 or completed != total):
        _fail(f"Inconsistent complete task progress for {change}: {completed}/{total}")
    if status == "no-tasks" and (completed != 0 or total != 0):
        _fail(f"Inconsistent no-tasks progress for {change}: {completed}/{total}")

    return status, completed, total


def _completion(args: argparse.Namespace) -> None:
    change = _validate_change_name(args.change)
    status, completed, total = _load_change_progress(Path(args.list_file), change)

    if status == "complete":
        _emit(
            should_archive="true",
            reason="change-complete",
            completed_tasks=str(completed),
            total_tasks=str(total),
        )
        return

    if args.mode == "normal":
        _emit(
            should_archive="false",
            reason="change-incomplete",
            completed_tasks=str(completed),
            total_tasks=str(total),
        )
        return
    if args.mode == "manual":
        _fail("Manual archive requires a Complete OpenSpec change")
    if args.mode == "recovery":
        _fail("Recovery archive requires a Complete OpenSpec change")
    _fail(f"Unsupported archive mode: {args.mode}")


def _purpose_parts(
    path: Path, *, expected_requirements_heading: bool
) -> tuple[str, list[str], int, int]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _fail(f"Unable to read OpenSpec spec {path}: {exc}")

    purpose_headers = [index for index, line in enumerate(lines) if line.strip() == "## Purpose"]
    if len(purpose_headers) != 1:
        _fail(f"{path} must contain exactly one ## Purpose section")

    start = purpose_headers[0]
    next_headings = [
        index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")
    ]
    if not next_headings:
        _fail(f"{path} Purpose must be followed by another top-level section")
    end = next_headings[0]
    if expected_requirements_heading and lines[end].strip() != "## Requirements":
        _fail(f"{path} canonical Purpose must be followed by ## Requirements")

    purpose = "\n".join(lines[start + 1 : end]).strip()
    if not purpose:
        _fail(f"{path} has an empty ## Purpose section")
    return purpose, lines, start, end


def _is_generated_purpose(purpose: str) -> bool:
    return GENERATED_PURPOSE.fullmatch(purpose) is not None


def _delta_capabilities(change_root: Path) -> list[tuple[str, Path]]:
    specs_root = change_root / "specs"
    if not specs_root.is_dir():
        _fail(f"OpenSpec change has no specs directory: {specs_root}")

    capabilities: list[tuple[str, Path]] = []
    for child in sorted(specs_root.iterdir()):
        if not child.is_dir() or not CHANGE_NAME.fullmatch(child.name):
            continue
        spec = child / "spec.md"
        if spec.is_file():
            capabilities.append((child.name, spec))
    if not capabilities:
        _fail(f"OpenSpec change has no delta capability specs: {specs_root}")
    return capabilities


def _purpose_snapshot(args: argparse.Namespace) -> None:
    change = _validate_change_name(args.change)
    change_root = Path(args.changes_root) / change
    if not change_root.is_dir():
        _fail(f"OpenSpec change is not active: {change}")

    canonical_root = Path(args.specs_root)
    entries: list[dict[str, str]] = []
    for capability, delta_spec in _delta_capabilities(change_root):
        canonical_spec = canonical_root / capability / "spec.md"
        if canonical_spec.is_file():
            canonical_purpose, _, _, _ = _purpose_parts(
                canonical_spec, expected_requirements_heading=True
            )
            entries.append(
                {
                    "capability": capability,
                    "kind": "existing",
                    "expected_purpose": canonical_purpose,
                }
            )
            continue

        delta_purpose, _, _, _ = _purpose_parts(delta_spec, expected_requirements_heading=False)
        if _is_generated_purpose(delta_purpose):
            _fail(f"New capability {capability} delta Purpose is an OpenSpec generated placeholder")
        entries.append(
            {
                "capability": capability,
                "kind": "new",
                "expected_purpose": delta_purpose,
            }
        )

    snapshot = {"change": change, "capabilities": entries}
    Path(args.snapshot_file).write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_purpose_snapshot(snapshot_file: Path) -> tuple[str, list[dict[str, str]]]:
    try:
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"Unable to read Purpose snapshot: {exc}")
    if not isinstance(payload, dict):
        _fail("Purpose snapshot must be a JSON object")
    change = payload.get("change")
    if not isinstance(change, str):
        _fail("Purpose snapshot is missing change")
    _validate_change_name(change)
    entries = payload.get("capabilities")
    if not isinstance(entries, list) or not entries:
        _fail("Purpose snapshot must contain capabilities")

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            _fail("Purpose snapshot capability entry must be an object")
        capability = entry.get("capability")
        kind = entry.get("kind")
        expected = entry.get("expected_purpose")
        if not isinstance(capability, str) or not CHANGE_NAME.fullmatch(capability):
            _fail(f"Invalid Purpose snapshot capability: {capability}")
        if capability in seen:
            _fail(f"Duplicate Purpose snapshot capability: {capability}")
        seen.add(capability)
        if kind not in {"new", "existing"}:
            _fail(f"Invalid Purpose snapshot kind for {capability}: {kind}")
        if not isinstance(expected, str) or not expected.strip():
            _fail(f"Invalid expected Purpose for {capability}")
        normalized.append(
            {
                "capability": capability,
                "kind": kind,
                "expected_purpose": expected.strip(),
            }
        )
    return change, normalized


def _replace_purpose(path: Path, expected: str, lines: list[str], start: int, end: int) -> None:
    replacement = lines[: start + 1] + ["", expected, ""] + lines[end:]
    path.write_text("\n".join(replacement).rstrip() + "\n", encoding="utf-8")


def _purpose_preserve(args: argparse.Namespace) -> None:
    change, entries = _load_purpose_snapshot(Path(args.snapshot_file))
    canonical_root = Path(args.specs_root)

    for entry in entries:
        capability = entry["capability"]
        kind = entry["kind"]
        expected = entry["expected_purpose"]
        canonical_spec = canonical_root / capability / "spec.md"
        if not canonical_spec.is_file():
            _fail(f"Canonical spec missing after archive: {canonical_spec}")

        actual, lines, start, end = _purpose_parts(
            canonical_spec, expected_requirements_heading=True
        )

        if kind == "existing":
            if actual != expected:
                _fail(
                    f"Existing canonical Purpose changed for {capability}: "
                    "archive must preserve it exactly"
                )
            if _is_generated_purpose(actual):
                _fail(f"Canonical Purpose placeholder remains for {capability}")
            continue

        if actual == expected:
            continue
        expected_generated = (
            f"TBD - created by archiving change {change}. Update Purpose after archive."
        )
        if actual != expected_generated:
            _fail(f"Unexpected canonical Purpose transformation for new capability {capability}")

        _replace_purpose(canonical_spec, expected, lines, start, end)
        verified, _, _, _ = _purpose_parts(canonical_spec, expected_requirements_heading=True)
        if verified != expected:
            _fail(f"Canonical Purpose preservation failed for {capability}")
        if _is_generated_purpose(verified):
            _fail(f"Canonical Purpose placeholder remains for {capability}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenSpec archive workflow helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser("classify")
    classify.add_argument("--event-name", required=True)
    classify.add_argument("--merged", default="false")
    classify.add_argument("--head-ref", default="")
    classify.add_argument("--head-repo", default="")
    classify.add_argument("--base-repo", default="")
    classify.add_argument("--recovery", default="false")
    classify.add_argument("--changed-files", default="")
    classify.add_argument("--changes-root", default="openspec/changes")
    classify.add_argument("--manual-change")
    classify.set_defaults(handler=_classify)

    completion = subparsers.add_parser("completion")
    completion.add_argument("--mode", choices=("normal", "recovery", "manual"), required=True)
    completion.add_argument("--change", required=True)
    completion.add_argument("--list-file", required=True)
    completion.set_defaults(handler=_completion)

    purpose_snapshot = subparsers.add_parser("purpose-snapshot")
    purpose_snapshot.add_argument("--change", required=True)
    purpose_snapshot.add_argument("--changes-root", default="openspec/changes")
    purpose_snapshot.add_argument("--specs-root", default="openspec/specs")
    purpose_snapshot.add_argument("--snapshot-file", required=True)
    purpose_snapshot.set_defaults(handler=_purpose_snapshot)

    purpose_preserve = subparsers.add_parser("purpose-preserve")
    purpose_preserve.add_argument("--snapshot-file", required=True)
    purpose_preserve.add_argument("--specs-root", default="openspec/specs")
    purpose_preserve.set_defaults(handler=_purpose_preserve)

    return parser


def main() -> None:
    args = _parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
