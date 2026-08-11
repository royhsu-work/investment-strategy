from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import NoReturn

CHANGE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VALID_PROGRESS_STATES = {"complete", "in-progress", "no-tasks"}


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


def _classify(args: argparse.Namespace) -> None:
    if args.event_name == "workflow_dispatch":
        if not args.manual_change:
            _fail("workflow_dispatch requires --manual-change")
        change = _validate_change_name(args.manual_change)
        _emit(action="evaluate", change=change, reason="manual-dispatch")
        return

    if args.event_name != "pull_request":
        _fail(f"Unsupported event: {args.event_name}")

    if not _parse_bool(args.merged):
        _emit(action="noop", change="", reason="not-merged")
        return

    if args.head_ref.startswith("agent/archive-"):
        _emit(action="noop", change="", reason="archive-pr")
        return

    candidates = _active_candidates(Path(args.changed_files), Path(args.changes_root))
    if not candidates:
        _emit(action="noop", change="", reason="no-active-change")
        return
    if len(candidates) > 1:
        _fail("Ambiguous OpenSpec archive scope: " + ", ".join(candidates))

    _emit(action="evaluate", change=candidates[0], reason="single-active-change")


def _load_change_progress(list_file: Path, change: str) -> tuple[str, int, int]:
    try:
        payload = json.loads(list_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"Unable to read OpenSpec list JSON: {exc}")

    changes = payload.get("changes") if isinstance(payload, dict) else None
    if not isinstance(changes, list):
        _fail("OpenSpec list JSON must contain a changes array")

    matches = [
        entry
        for entry in changes
        if isinstance(entry, dict) and entry.get("name") == change
    ]
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

    if args.event_name == "pull_request":
        _emit(
            should_archive="false",
            reason="change-incomplete",
            completed_tasks=str(completed),
            total_tasks=str(total),
        )
        return
    if args.event_name == "workflow_dispatch":
        _fail("Manual archive requires a Complete OpenSpec change")
    _fail(f"Unsupported event: {args.event_name}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenSpec archive workflow helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser("classify")
    classify.add_argument("--event-name", required=True)
    classify.add_argument("--merged", default="false")
    classify.add_argument("--head-ref", default="")
    classify.add_argument("--changed-files", default="")
    classify.add_argument("--changes-root", default="openspec/changes")
    classify.add_argument("--manual-change")
    classify.set_defaults(handler=_classify)

    completion = subparsers.add_parser("completion")
    completion.add_argument("--event-name", required=True)
    completion.add_argument("--change", required=True)
    completion.add_argument("--list-file", required=True)
    completion.set_defaults(handler=_completion)

    return parser


def main() -> None:
    args = _parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
