"""Executable contract tests for Skill-maintenance traceability."""

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
