"""Executable contract tests for Skill-maintenance traceability."""

import re
from pathlib import Path

from investment_strategy.skill_maintenance import (
    SkillChange,
    SkillChangeClass,
    SkillTraceEntry,
    compare_skill_changes,
)


def _entry(
    path: str,
    change_class: SkillChangeClass = SkillChangeClass.MODIFIED,
    *,
    retrospective: bool = False,
    replacement: str | None = None,
) -> SkillTraceEntry:
    return SkillTraceEntry(
        path=path,
        change_class=change_class,
        source="#110 / record-skill-maintenance-traceability",
        responsibility="preserve existing owner while changing the approved action-local procedure",
        rationale="approved repository-governance maintenance",
        replacement=replacement,
        retrospective=retrospective,
    )


def test_one_capability_change_can_declare_two_material_skills() -> None:
    changes = [
        SkillChange("agents/skills/openspec-change/SKILL.md", SkillChangeClass.MODIFIED),
        SkillChange("agents/skills/openspec-review/SKILL.md", SkillChangeClass.MODIFIED),
    ]
    declaration = [_entry(change.path) for change in changes]

    assert compare_skill_changes(changes, declaration) == ()


def test_undeclared_material_skill_change_is_a_finding() -> None:
    path = "agents/skills/implementation-review/SKILL.md"
    changes = [SkillChange(path, SkillChangeClass.MODIFIED)]

    findings = compare_skill_changes(changes, [])

    assert [(finding.path, finding.reason) for finding in findings] == [
        (path, "material Skill change is undeclared")
    ]


def test_non_material_reference_only_edit_creates_no_trace_noise() -> None:
    changes = [
        SkillChange(
            "agents/skills/openspec-review/SKILL.md",
            SkillChangeClass.MODIFIED,
            material=False,
        )
    ]

    assert compare_skill_changes(changes, []) == ()


def test_changed_classification_is_a_finding() -> None:
    path = "agents/skills/merge-pr/SKILL.md"
    changes = [SkillChange(path, SkillChangeClass.REMOVED)]
    declaration = [_entry(path, SkillChangeClass.MODIFIED)]

    findings = compare_skill_changes(changes, declaration)

    expected = "declared Modified but implementation is Removed"
    assert any(expected in finding.reason for finding in findings)


def test_retrospective_entry_is_current_provenance_not_rewritten_history() -> None:
    path = "agents/skills/openspec-change/SKILL.md"
    changes = [SkillChange(path, SkillChangeClass.MODIFIED)]
    declaration = [_entry(path, retrospective=True)]

    assert declaration[0].retrospective is True
    assert compare_skill_changes(changes, declaration) == ()


def test_added_removed_and_decomposition_entries_carry_responsibility_data() -> None:
    entries = [
        _entry("agents/skills/new-skill/SKILL.md", SkillChangeClass.ADDED),
        _entry(
            "agents/skills/old-skill/SKILL.md",
            SkillChangeClass.REMOVED,
            replacement="agents/skills/new-skill/SKILL.md",
        ),
    ]
    changes = [
        SkillChange(entries[0].path, SkillChangeClass.ADDED),
        SkillChange(entries[1].path, SkillChangeClass.REMOVED),
    ]

    assert entries[1].replacement == entries[0].path
    assert compare_skill_changes(changes, entries) == ()


def test_repository_authored_skill_requires_no_fictional_upstream_metadata() -> None:
    entry = _entry("agents/skills/repository-authored/SKILL.md")
    change = SkillChange(entry.path, SkillChangeClass.MODIFIED)

    assert not hasattr(entry, "upstream")
    assert compare_skill_changes([change], [entry]) == ()


def _skill_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _record_skill_proposal() -> str:
    active = Path("openspec/changes/record-skill-maintenance-traceability/proposal.md")
    if active.exists():
        return active.read_text(encoding="utf-8")

    archived = sorted(
        Path("openspec/changes/archive").glob("*-record-skill-maintenance-traceability/proposal.md")
    )
    assert len(archived) == 1
    return archived[0].read_text(encoding="utf-8")


def test_openspec_authoring_owns_skill_maintenance_declaration() -> None:
    text = _skill_text("agents/skills/openspec-change/SKILL.md")

    assert "Skill maintenance traceability" in text
    assert "Lead owns" in text
    assert "materially affected Skill" in text


def test_openspec_review_checks_declaration_completeness() -> None:
    text = _skill_text("agents/skills/openspec-review/SKILL.md")

    assert "Skill maintenance traceability" in text
    assert "undeclared material Skill" in text
    assert "Formatting" in text


def test_implementation_review_compares_exact_head_with_declaration() -> None:
    text = _skill_text("agents/skills/implementation-review/SKILL.md")

    assert "Skill maintenance traceability" in text
    assert "exact implementation head" in text
    assert "differently classified" in text


def _retrospective_rows() -> dict[str, set[str]]:
    proposal = _record_skill_proposal()
    section = proposal.split("### Retrospective repair window: #105 through pre-#110 baseline", 1)[
        1
    ].split("#80 / PR #121", 1)[0]
    rows: dict[str, set[str]] = {}
    for line in section.splitlines():
        if not line.startswith("| #"):
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        source, skill_cell = columns[:2]
        source_issue = source.split(" / ", 1)[0]
        rows[source_issue] = set(re.findall(r"`([^`]+)`", skill_cell))
    return rows


def test_retrospective_window_classifies_every_skill_touching_source_change() -> None:
    assert _retrospective_rows() == {
        "#105": {"openspec-explore", "openspec-change"},
        "#107": {
            "archive-review",
            "implementation-review",
            "implementation",
            "lifecycle-finalize",
            "merge-pr",
            "openspec-change",
            "openspec-review",
        },
        "#86": {"openspec-change", "openspec-review"},
        "#115": {"lifecycle-finalize", "merge-pr"},
        "#112": {"implementation-review", "implementation", "openspec-change"},
    }


def test_retrospective_window_records_evaluated_non_skill_exclusion() -> None:
    proposal = _record_skill_proposal()

    assert (
        "#80 / PR #121 is explicitly evaluated and excluded from retrospective Skill entries "
        "because it did not modify `agents/skills/*`."
    ) in proposal


def test_retrospective_repair_does_not_rewrite_source_archives() -> None:
    source_changes = (
        "enforce-dispatch-cardinality-preflight",
        "disposition-substantive-human-input",
        "preserve-explore-proposal-handoff",
        "align-coordination-issue-close-with-terminal",
        "enforce-invocation-exit-proof",
    )
    archive_root = Path("openspec/changes/archive")

    for change in source_changes:
        proposals = list(archive_root.glob(f"*-{change}/proposal.md"))
        assert len(proposals) == 1, change
        historical_text = proposals[0].read_text(encoding="utf-8")
        assert "record-skill-maintenance-traceability" not in historical_text
