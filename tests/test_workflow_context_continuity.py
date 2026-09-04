"""Contract coverage for authoritative continuity and cumulative Reviewer coverage."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
README = ROOT / "README.md"
REVIEWER = ROOT / "agents" / "roles" / "reviewer.md"
CHANGE_SKILL = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
OPENSPEC_REVIEW = ROOT / "agents" / "skills" / "openspec-review" / "SKILL.md"
IMPLEMENTATION_REVIEW = ROOT / "agents" / "skills" / "implementation-review" / "SKILL.md"
ARCHIVE_REVIEW = ROOT / "agents" / "skills" / "archive-review" / "SKILL.md"

ROLE_FILES = tuple((ROOT / "agents" / "roles").glob("*.md"))
SKILL_FILES = tuple((ROOT / "agents" / "skills").glob("*/SKILL.md"))


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_shared_context_continuity_applies_to_all_ten_actions() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "Authoritative context continuity and evidence consumption",
        "all ten normal actions",
        "still-applicable durable evidence",
        "Simple recency does not consume evidence",
        "authoritative supersession",
        "durable resolution",
        "applicable independent gate acceptance",
        "lifecycle completion",
        "action-specific legal consumption event",
    ):
        assert required in shared


def test_cross_issue_provenance_is_dereferenced_not_replaced_by_summary() -> None:
    for path in (CHANGE_SKILL, OPENSPEC_REVIEW):
        text = _normalized(path)
        for required in (
            "declared upstream authoritative decision/gate references",
            "dereference",
            "cross-Issue summary",
            "orientation",
            "not replacement authority",
        ):
            assert required in text, path


def test_reviewer_role_owns_cumulative_baseline_to_target_coverage() -> None:
    reviewer = _normalized(REVIEWER)
    for required in (
        "last valid independent review baseline B",
        "exact current target R",
        "every material unreviewed change in `(B, R]`",
        "complete current state at R",
        "Intermediate readiness",
        "mechanical validation",
        "unreviewed revision",
        "MUST NOT advance B",
    ):
        assert required in reviewer


def test_each_reviewer_gate_specializes_baseline_and_current_target() -> None:
    for path in (OPENSPEC_REVIEW, IMPLEMENTATION_REVIEW, ARCHIVE_REVIEW):
        text = _normalized(path)
        for required in (
            "accepted baseline B",
            "current target R",
            "material unreviewed changes in `(B, R]`",
            "complete current state at R",
        ):
            assert required in text, path


def test_readme_explains_snapshot_vs_unresolved_evidence_and_b_to_r_coverage() -> None:
    readme = _normalized(README)
    for required in (
        "current snapshot semantics",
        "unresolved durable-evidence semantics",
        "cross-Issue summary is orientation rather than replacement authority",
        "Reviewer `B → R` cumulative-coverage rule",
    ):
        assert required in readme


def test_shared_contract_does_not_become_generic_context_runtime_state() -> None:
    shared = _normalized(AGENTS)
    readme = _normalized(README)
    for prohibited_machinery in (
        "message queue",
        "event-sourcing engine",
        "hidden context cache",
        "sequence number/label",
        "pending-review state",
        "consumed-evidence flag",
        "second workflow DAG",
    ):
        assert prohibited_machinery in shared or prohibited_machinery in readme

    heading = "## Authoritative context continuity and evidence consumption"
    for path in (*ROLE_FILES, *SKILL_FILES):
        assert heading not in _normalized(path), path
