from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

S603_SITES = {
    "tests/test_archive_pr_linkage.py": ".github/scripts/archive_pr_linkage.py",
    "tests/test_openspec_archive_automation.py": ".github/scripts/openspec_archive.py",
    "tests/test_openspec_archive_purpose.py": ".github/scripts/openspec_archive.py",
}


def _attribute_path(node: ast.AST) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return tuple(reversed(parts))


def _contains_unvalidated_external_source(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in {"request", "event", "issue"}:
            return True
        if isinstance(child, ast.Attribute):
            path = _attribute_path(child)
            if path in {
                ("os", "environ"),
                ("sys", "argv"),
                ("sys", "stdin"),
            }:
                return True
            if path is not None and path[0] in {"request", "event", "issue"}:
                return True
        if isinstance(child, ast.Call):
            path = _attribute_path(child.func)
            if path in {
                ("os", "getenv"),
                ("os", "environ", "get"),
            }:
                return True
            if path is not None and path[-1] in {"read_text", "read_bytes"}:
                return True
            if isinstance(child.func, ast.Name) and child.func.id in {"input", "open"}:
                return True
    return False


def _contains_tainted_name(node: ast.AST, tainted_names: set[str]) -> bool:
    return any(
        isinstance(child, ast.Name) and child.id in tainted_names for child in ast.walk(node)
    )


def _function_has_unvalidated_run_arguments(function: ast.FunctionDef) -> bool:
    tainted_names: set[str] = set()
    assignments = [
        node
        for node in ast.walk(function)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr))
    ]

    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            if isinstance(assignment, ast.Assign):
                value = assignment.value
                targets = assignment.targets
            elif isinstance(assignment, ast.AnnAssign):
                if assignment.value is None:
                    continue
                value = assignment.value
                targets = [assignment.target]
            else:
                value = assignment.value
                targets = [assignment.target]

            if not (
                _contains_unvalidated_external_source(value)
                or _contains_tainted_name(value, tainted_names)
            ):
                continue

            assigned_names = {
                child.id
                for target in targets
                for child in ast.walk(target)
                if isinstance(child, ast.Name)
            }
            new_names = assigned_names - tainted_names
            if new_names:
                tainted_names.update(new_names)
                changed = True

    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "_run":
            continue
        for arg in node.args:
            if _contains_unvalidated_external_source(arg) or _contains_tainted_name(
                arg, tainted_names
            ):
                return True
    return False


def _find_run_helper(tree: ast.Module) -> ast.FunctionDef:
    helpers: list[ast.FunctionDef] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_run":
            helpers.append(node)
    assert len(helpers) == 1
    return helpers[0]


def _find_subprocess_run(helper: ast.FunctionDef) -> ast.Call:
    calls = [
        node
        for node in ast.walk(helper)
        if isinstance(node, ast.Call) and _attribute_path(node.func) == ("subprocess", "run")
    ]
    assert len(calls) == 1
    return calls[0]


def _assert_fixed_s603_helper(path: Path, expected_script: str) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    helper = _find_run_helper(tree)
    run_call = _find_subprocess_run(helper)

    assert "# noqa: S603 - fixed interpreter and repository-owned script" in source
    assert f'SCRIPT = ROOT / "{expected_script}"' in source
    assert helper.args.args == []
    assert helper.args.vararg is not None
    assert helper.args.vararg.arg == "args"

    assert len(run_call.args) == 1
    command = run_call.args[0]
    assert isinstance(command, ast.List)
    assert len(command.elts) == 3
    assert _attribute_path(command.elts[0]) == ("sys", "executable")

    script_arg = command.elts[1]
    assert isinstance(script_arg, ast.Call)
    assert isinstance(script_arg.func, ast.Name)
    assert script_arg.func.id == "str"
    assert len(script_arg.args) == 1
    assert isinstance(script_arg.args[0], ast.Name)
    assert script_arg.args[0].id == "SCRIPT"

    passthrough = command.elts[2]
    assert isinstance(passthrough, ast.Starred)
    assert isinstance(passthrough.value, ast.Name)
    assert passthrough.value.id == "args"

    shell_keywords = [keyword for keyword in run_call.keywords if keyword.arg == "shell"]
    assert not shell_keywords or all(
        isinstance(keyword.value, ast.Constant) and keyword.value.value is False
        for keyword in shell_keywords
    )

    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    assert all(not _function_has_unvalidated_run_arguments(function) for function in functions)


def test_current_s603_helpers_preserve_fixed_execution_and_trust_boundaries() -> None:
    for relative_path, expected_script in S603_SITES.items():
        _assert_fixed_s603_helper(ROOT / relative_path, expected_script)


def test_external_argument_detector_rejects_direct_and_indirect_unvalidated_sources() -> None:
    fixture = ast.parse(
        """
import os
import sys
from pathlib import Path

def direct() -> None:
    _run(os.environ["ISSUE_VALUE"])
    _run(os.getenv("REQUEST_VALUE"))
    _run(sys.argv[1])
    _run(input())
    _run(open("external.txt").read())
    _run(Path("external.txt").read_text())
    _run(issue.body)

def indirect() -> None:
    value = os.getenv("REQUEST_VALUE")
    alias = value
    filesystem_value = Path("external.txt").read_text()
    issue_value = issue.body
    _run(alias)
    _run(filesystem_value)
    _run(issue_value)
"""
    )
    functions = [node for node in fixture.body if isinstance(node, ast.FunctionDef)]

    assert len(functions) == 2
    assert all(_function_has_unvalidated_run_arguments(function) for function in functions)
