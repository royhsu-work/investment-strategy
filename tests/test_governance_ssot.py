from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_readme_is_orientation_and_names_authority_surfaces() -> None:
    readme = _normalized(ROOT / "README.md")
    for required in (
        "Authoritative Scheduled-Agent shared runtime governance",
        "agents/AGENTS.md",
        "agents/workflow.md",
        "README is Human/",
        "does not duplicate the runtime protocol",
        "Role = role_for(Action)",
        "merge-implementation-pr",
        "merge-archive-pr",
    ):
        assert required in readme


def test_shared_governance_separates_role_action_and_capability() -> None:
    shared = _normalized(AGENTS / "AGENTS.md")
    for required in (
        "Role is semantic responsibility",
        "Action is the one unit of workflow work",
        "Capability is repository application or mutation power",
        "Role = role_for(Action)",
        "Issue lifecycle state",
        "one immutable Change identity",
        "exactly one action:<action>",
    ):
        assert required in shared


def test_shared_governance_defines_one_wake_and_fresh_application() -> None:
    shared = _normalized(AGENTS / "AGENTS.md")
    for required in (
        "one bounded semantic Action",
        "next_action(current_action, result)",
        "later fresh wake",
        "fresh-reads the Issue",
        "postcondition observation",
        "stale, concurrent, duplicated, incomplete, ambiguous, contradictory",
        "fail closed",
    ):
        assert required in shared
    assert "worker cannot select an Issue, Role, Action, target, successor, retry, or success" in shared


def test_shared_governance_keeps_independent_safety_boundaries() -> None:
    shared = _normalized(AGENTS / "AGENTS.md")
    for required in (
        "Human authority",
        "WIP=1",
        "finish-first",
        "Exact-R validation",
        "content-addressed",
        "independent Reviewer",
        "exact head",
        "Mutation carriers are replaceable actuators",
    ):
        assert required in shared
    assert "No write is used as a read" in shared


def test_daily_transport_is_bounded_and_external_configuration_stays_external() -> None:
    migration = _normalized(AGENTS / "scheduled-task-migration.md")
    for required in (
        "Asia/Taipei daily shard",
        "one exact Actions run",
        "one structured result",
        "bounded transport only",
        "external product configuration",
        "Project/Kanban fields are presentation only",
    ):
        assert required in migration


def test_archive_and_merge_have_separate_explicit_actions() -> None:
    lifecycle = _normalized(AGENTS / "skills/lifecycle-finalize/SKILL.md")
    archive = _normalized(AGENTS / "skills/archive-review/SKILL.md")
    merge = _normalized(AGENTS / "skills/merge-pr/SKILL.md")
    assert "archive preparation" in lifecycle
    assert "merge-archive-pr" in archive
    assert "merge-implementation-pr" in merge
    assert "merge-archive-pr" in merge
    assert "generic merge label" in merge


def test_repository_governance_canonical_spec_preserves_archiveable_purpose() -> None:
    spec_path = ROOT / "openspec/specs/repository-governance/spec.md"
    spec = _read(spec_path)
    assert spec.count("## Purpose") == 1
    purpose = spec.split("## Purpose", 1)[1].split("## Requirements", 1)[0].strip()
    assert purpose
