from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_readme_is_orientation_not_competing_runtime_protocol() -> None:
    readme = _read(ROOT / "README.md")
    assert "Authoritative Scheduled-Agent runtime governance" in readme
    assert "agents/AGENTS.md" in readme
    assert "Reviewer / review-openspec" not in readme
    assert "Lead / finalize-archive" not in readme


def test_same_invocation_exact_resource_settle_is_not_immediate_external_wait() -> None:
    shared = _read(AGENTS / "AGENTS.md")
    assert "first nonterminal observation" in shared
    assert "bounded same-invocation observation" in shared
    assert "same exact resource" in shared
    assert "does not by itself prove a cross-invocation external asynchronous wait" in shared
    assert "no durable timer" in shared


def test_scheduler_topology_is_external_not_a_three_slot_requirement() -> None:
    migration = _read(AGENTS / "scheduled-task-migration.md")
    assert "current deployment note" in migration
    assert "three wake slots" not in migration
    assert "Exact slot count/topology/cadence" in migration
    assert "external product configuration" in migration


def test_final_archive_merge_requires_known_temporary_cleanup_first() -> None:
    finalize = _read(AGENTS / "skills/lifecycle-finalize/SKILL.md")
    merge = _read(AGENTS / "skills/merge-pr/SKILL.md")

    assert "known terminal cleanup obligations" in finalize
    assert "before archive `MERGE_AUTHORIZED`" in finalize
    assert "before the final Archive PR merge mutation" in merge
    assert "temporary integration/recovery branches" in merge
    assert "do not merge" in merge
