from __future__ import annotations

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


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with YAML frontmatter"
    _, raw, _ = text.split("---", 2)
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict), f"{path} frontmatter must be a mapping"
    return parsed


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
