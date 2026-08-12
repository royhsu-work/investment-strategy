from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NoReturn

CHANGE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _fail(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def _validate_change(change: str) -> str:
    if not CHANGE_NAME.fullmatch(change):
        _fail(f"Invalid OpenSpec change name: {change}")
    return change


def _flatten_issues(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        _fail("Issue payload must be a JSON array")
    flattened: list[dict[str, object]] = []
    for item in payload:
        if isinstance(item, list):
            for nested in item:
                if isinstance(nested, dict):
                    flattened.append(nested)
            continue
        if isinstance(item, dict):
            flattened.append(item)
    return flattened


def _has_change_identity(body: str, change: str) -> bool:
    pattern = re.compile(rf"^Change:\s*`?{re.escape(change)}`?$")
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if len(line) >= 2 and line.startswith("`") and line.endswith("`"):
            line = line[1:-1].strip()
        if pattern.fullmatch(line):
            return True
    return False


def _resolve(args: argparse.Namespace) -> None:
    change = _validate_change(args.change)
    try:
        payload = json.loads(Path(args.issues_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"Unable to read GitHub Issue payload: {exc}")

    matches: list[int] = []
    for issue in _flatten_issues(payload):
        if issue.get("pull_request") is not None:
            continue
        number = issue.get("number")
        body = issue.get("body")
        if not isinstance(number, int) or isinstance(number, bool):
            continue
        if isinstance(body, str) and _has_change_identity(body, change):
            matches.append(number)

    if len(matches) != 1:
        rendered = ", ".join(str(number) for number in sorted(matches)) or "none"
        _fail(
            f"Expected exactly one coordination Issue for change {change}; found: {rendered}"
        )

    print(f"issue_number={matches[0]}")


def _render(args: argparse.Namespace) -> None:
    change = _validate_change(args.change)
    if args.issue_number <= 0:
        _fail("Issue number must be positive")
    body = (
        f"Archive OpenSpec change `{change}`.\n\n"
        "This pull request is the repository-owned final archive snapshot. "
        "Its closing linkage is a lifecycle side effect only; independent Reviewer PASS, "
        "Lead exact-revision authorization, unchanged-head verification, and current gates "
        "remain required before merge.\n\n"
        f"Closes #{args.issue_number}\n"
    )
    Path(args.body_file).write_text(body, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive PR coordination-Issue linkage helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("--change", required=True)
    resolve.add_argument("--issues-file", required=True)
    resolve.set_defaults(handler=_resolve)

    render = subparsers.add_parser("render")
    render.add_argument("--change", required=True)
    render.add_argument("--issue-number", required=True, type=int)
    render.add_argument("--body-file", required=True)
    render.set_defaults(handler=_render)

    return parser


def main() -> None:
    args = _parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
