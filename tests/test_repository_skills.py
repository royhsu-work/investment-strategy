from __future__ import annotations

import runpy
from collections.abc import Callable
from pathlib import Path

import yaml

MAPPED_REPOSITORY_SKILLS = (
    "archive-review",
    "implementation-review",
    "implementation",
    "lifecycle-finalize",
    "merge-pr",
    "openspec-change",
    "openspec-explore",
    "openspec-review",
)

EXPECTED_ACTION_DECLARATIONS = {
    "archive-review": "Mapped Action: Reviewer / review-archive.",
    "implementation-review": "Mapped Action: Reviewer / review-implementation.",
    "implementation": "Mapped Action: Executor / implement-change.",
    "lifecycle-finalize": "Mapped Actions: Lead / finalize-change and Lead / finalize-archive.",
    "merge-pr": (
        "Mapped Actions: Executor / merge-implementation-pr and Executor / merge-archive-pr."
    ),
    "openspec-change": "Mapped Actions: Lead / propose-change and Lead / resolve-question.",
    "openspec-explore": "Mapped Action: Lead / explore-change.",
    "openspec-review": "Mapped Action: Reviewer / review-openspec.",
}

UPSTREAM_REVISION = "2826b8889e5223a9a8095d4428b60b56597e1020"
UPSTREAM_DERIVED_SKILLS = {
    "archive-review": "skills/openspec-archive-change/",
    "implementation-review": "skills/openspec-verify-change/",
    "implementation": "skills/openspec-apply-change/",
    "lifecycle-finalize": "skills/openspec-archive-change/",
    "merge-pr": "skills/openspec-archive-change/",
    "openspec-change": "skills/openspec-propose/",
    "openspec-explore": "skills/openspec-explore/",
}


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with YAML frontmatter"
    _, raw, _ = text.split("---", 2)
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict), f"{path} frontmatter must be a mapping"
    return parsed


def _adopted_validator() -> Callable[[Path], tuple[bool, str]]:
    namespace = runpy.run_path("agents/skills/skill-creator/scripts/quick_validate.py")
    validate = namespace["validate_skill"]
    assert callable(validate)
    return validate


def test_mapped_repository_skills_have_standard_frontmatter() -> None:
    root = Path("agents/skills")
    names: list[str] = []

    for skill in MAPPED_REPOSITORY_SKILLS:
        metadata = _frontmatter(root / skill / "SKILL.md")
        name = metadata.get("name")
        description = metadata.get("description")
        assert isinstance(name, str) and name.strip(), f"{skill} requires a non-empty name"
        assert isinstance(description, str) and description.strip(), (
            f"{skill} requires a non-empty description"
        )
        assert name == skill, f"{skill} must keep stable package name metadata"
        names.append(name)

    assert len(names) == len(set(names)), "mapped repository Skill names must be unique"


def test_mapped_repository_skills_pass_adopted_quick_validation() -> None:
    root = Path("agents/skills")
    validate = _adopted_validator()

    for skill in MAPPED_REPOSITORY_SKILLS:
        valid, message = validate(root / skill)
        assert valid, f"{skill} failed adopted skill-creator validation: {message}"


def test_openspec_derived_skills_have_reconstructable_upstream_ledgers() -> None:
    root = Path("agents/skills")

    for skill, upstream_path in UPSTREAM_DERIVED_SKILLS.items():
        ledger_path = root / skill / "UPSTREAM.md"
        assert ledger_path.is_file(), f"{skill} requires Skill-local UPSTREAM.md provenance"
        ledger = ledger_path.read_text(encoding="utf-8")
        assert "Fission-AI/OpenSpec" in ledger
        assert UPSTREAM_REVISION in ledger
        assert upstream_path in ledger
        assert "## Relationship" in ledger
        assert "## Added responsibilities" in ledger
        assert "## Deleted or omitted responsibilities" in ledger
        assert "## Modified responsibilities" in ledger
        assert "Maintenance implication" in ledger


def test_repository_original_openspec_review_does_not_fabricate_upstream_mapping() -> None:
    assert not Path("agents/skills/openspec-review/UPSTREAM.md").exists()


def test_standard_metadata_and_provenance_preserve_existing_action_ownership() -> None:
    root = Path("agents/skills")

    for skill, expected in EXPECTED_ACTION_DECLARATIONS.items():
        body = (root / skill / "SKILL.md").read_text(encoding="utf-8")
        assert expected in body, f"{skill} must preserve its mapped role/action declaration"


def test_semantic_adapter_remains_a_separate_follow_up_resource() -> None:
    root = Path("agents/skills")
    assert (root / "openspec-semantic-adapter.md").is_file()
    assert not (root / "openspec-semantic-adapter" / "SKILL.md").exists()
