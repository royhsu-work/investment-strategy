from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_readme_is_orientation_not_competing_runtime_protocol() -> None:
    readme = _normalized(ROOT / "README.md")
    assert "Authoritative Scheduled-Agent shared runtime governance" in readme
    assert "authoritative runtime workflow topology" in readme
    assert "agents/AGENTS.md" in readme
    assert "agents/workflow.md" in readme
    assert "README 只提供 Human/contributor 導覽" in readme
    assert "不複製 Scheduled-Agent runtime protocol 或 lifecycle topology" in readme
    assert "下列名稱僅作 Human 搜尋與流程導覽" in readme


def test_shared_governance_declares_rule_category_ownership() -> None:
    shared = _normalized(AGENTS / "AGENTS.md")
    for required in (
        "README.md` is the Human/contributor entry point",
        "agents/workflow.md` owns end-to-end Scheduled-Agent runtime workflow topology",
        "agents/AGENTS.md` owns shared Scheduled-Agent runtime execution protocol",
        "agents/roles/*.md` own role mission, authority, ownership",
        "agents/skills/*` own action-specific executable procedure",
        "openspec/config.yaml` owns OpenSpec authoring/validation conventions",
        "openspec/specs/*` contain approved capability requirements",
        "archived changes are historical provenance/traceability only",
        "external product configuration",
        "synchronization-by-convention",
    ):
        assert required in shared


def test_same_invocation_exact_resource_settle_is_not_immediate_external_wait() -> None:
    shared = _normalized(AGENTS / "AGENTS.md")
    assert "first nonterminal observation" in shared
    assert "subsequent fresh observation" in shared
    assert "same exact target/resource" in shared
    assert "created or triggered by the current selected action" in shared
    assert "caused by or required for the current selected action" not in shared
    assert "does not by itself prove a cross-invocation external asynchronous wait" in shared
    assert "no other immediately actionable same-authority work remains" in shared
    assert "MUST NOT introduce a durable timer" in shared


def test_scheduler_topology_is_external_not_a_three_slot_requirement() -> None:
    migration = _normalized(AGENTS / "scheduled-task-migration.md")
    assert "Current deployment note" in migration
    assert "three wake slots" not in migration
    assert "Exact slot count/topology/cadence" in migration
    assert "external product configuration" in migration
    assert "permanent minimum-slot requirement" in migration


def test_final_archive_merge_requires_known_temporary_cleanup_first() -> None:
    finalize = _normalized(AGENTS / "skills/lifecycle-finalize/SKILL.md")
    merge = _normalized(AGENTS / "skills/merge-pr/SKILL.md")

    assert "known terminal cleanup obligations" in finalize
    assert "complete before `Reviewer / review-archive`" in finalize
    assert "before the final Archive PR merge mutation" in merge
    assert "temporary correction/recovery branches" in merge
    assert "do not merge" in merge


def test_repository_governance_canonical_spec_preserves_archiveable_purpose() -> None:
    spec_path = ROOT / "openspec/specs/repository-governance/spec.md"
    spec = _read(spec_path)
    assert spec.count("## Purpose") == 1
    purpose = spec.split("## Purpose", 1)[1].split("## Requirements", 1)[0].strip()
    assert purpose
