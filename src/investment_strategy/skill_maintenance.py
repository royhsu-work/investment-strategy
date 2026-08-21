"""Deterministic helpers for repository Skill-maintenance traceability.

This module is deliberately small: it evaluates concrete changed-Skill facts against
an approved maintenance declaration.  It does not decide OpenSpec scope, infer
semantic materiality from a diff, or replace Reviewer judgment.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class SkillChangeClass(StrEnum):
    """Approved maintenance classification for a repository Skill."""

    ADDED = "Added"
    MODIFIED = "Modified"
    REMOVED = "Removed"


@dataclass(frozen=True)
class SkillChange:
    """Observed implementation fact after materiality has been judged."""

    path: str
    change_class: SkillChangeClass
    material: bool = True


@dataclass(frozen=True)
class SkillTraceEntry:
    """Approved durable maintenance declaration for one material Skill change."""

    path: str
    change_class: SkillChangeClass
    source: str
    responsibility: str
    rationale: str
    replacement: str | None = None
    retrospective: bool = False


@dataclass(frozen=True)
class TraceFinding:
    """One deterministic mismatch between implementation facts and declaration."""

    path: str
    reason: str


def validate_trace_entry(entry: SkillTraceEntry) -> tuple[TraceFinding, ...]:
    """Validate fields whose necessity follows directly from the approved contract."""

    findings: list[TraceFinding] = []
    if not entry.path.startswith("agents/skills/"):
        findings.append(TraceFinding(entry.path, "trace path is not a repository Skill"))
    if not entry.source.strip():
        findings.append(TraceFinding(entry.path, "approved source/reference is required"))
    if not entry.responsibility.strip():
        findings.append(TraceFinding(entry.path, "responsibility treatment is required"))
    if not entry.rationale.strip():
        findings.append(TraceFinding(entry.path, "rationale is required"))
    return tuple(findings)


def compare_skill_changes(
    changes: Iterable[SkillChange],
    declaration: Iterable[SkillTraceEntry],
) -> tuple[TraceFinding, ...]:
    """Compare material Skill changes with the approved declaration.

    Materiality and semantic classification are upstream review judgments.  Once
    supplied, this function makes completeness, duplicate, and classification checks
    deterministic.  Non-material edits intentionally create no declaration duty.
    """

    change_list = list(changes)
    entry_list = list(declaration)
    findings: list[TraceFinding] = []

    entries_by_path: dict[str, list[SkillTraceEntry]] = {}
    for entry in entry_list:
        entries_by_path.setdefault(entry.path, []).append(entry)
        findings.extend(validate_trace_entry(entry))

    for path, entries in entries_by_path.items():
        if len(entries) > 1:
            findings.append(TraceFinding(path, "duplicate maintenance declarations"))

    material_by_path = {change.path: change for change in change_list if change.material}
    for path, change in material_by_path.items():
        entries = entries_by_path.get(path, [])
        if not entries:
            findings.append(TraceFinding(path, "material Skill change is undeclared"))
            continue
        if len(entries) == 1 and entries[0].change_class != change.change_class:
            findings.append(
                TraceFinding(
                    path,
                    f"declared {entries[0].change_class.value} but implementation is {change.change_class.value}",
                )
            )

    for path in entries_by_path:
        if path not in material_by_path:
            findings.append(TraceFinding(path, "declaration has no corresponding material Skill change"))

    return tuple(findings)
