from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"

ROLE_ACTIONS = {
    "Lead": (
        "propose-change",
        "resolve-question",
        "finalize-change",
        "finalize-archive",
    ),
    "Reviewer": (
        "review-openspec",
        "review-implementation",
        "review-archive",
    ),
    "Executor": ("implement-change", "merge-pr"),
}

EXPECTED_PRIORITY = {
    "Lead": (
        "resolve-question",
        "finalize-archive",
        "finalize-change",
        "propose-change",
    ),
    "Reviewer": ("review-archive", "review-implementation", "review-openspec"),
    "Executor": ("merge-pr", "implement-change"),
}

EXPECTED_SKILLS = {
    ("Lead", "propose-change"): "agents/skills/openspec-change/SKILL.md",
    ("Lead", "resolve-question"): "agents/skills/openspec-change/SKILL.md",
    ("Lead", "finalize-change"): "agents/skills/lifecycle-finalize/SKILL.md",
    ("Lead", "finalize-archive"): "agents/skills/lifecycle-finalize/SKILL.md",
    ("Reviewer", "review-openspec"): "agents/skills/openspec-review/SKILL.md",
    (
        "Reviewer",
        "review-implementation",
    ): "agents/skills/implementation-review/SKILL.md",
    ("Reviewer", "review-archive"): "agents/skills/archive-review/SKILL.md",
    ("Executor", "implement-change"): "agents/skills/implementation/SKILL.md",
    ("Executor", "merge-pr"): "agents/skills/merge-pr/SKILL.md",
}


class Candidate(NamedTuple):
    number: int
    created_at: str
    role: str
    action: str


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _mapping(text: str) -> dict[tuple[str, str], str]:
    pattern = re.compile(
        r"^\| (Lead|Reviewer|Executor) \| `([^`]+)` \| `([^`]+)` \|$",
        re.MULTILINE,
    )
    return {(role, action): skill for role, action, skill in pattern.findall(text)}


def _priority(text: str) -> dict[str, tuple[str, ...]]:
    match = re.search(
        r"Lead\n([^\n]+)\n\nReviewer\n([^\n]+)\n\nExecutor\n([^\n]+)",
        text,
    )
    assert match is not None
    return {
        role: tuple(value.split(" > "))
        for role, value in zip(("Lead", "Reviewer", "Executor"), match.groups(), strict=True)
    }


def _select(text: str, role: str, candidates: list[Candidate]) -> Candidate | None:
    mapping = _mapping(text)
    priority = _priority(text)[role]
    rank = {action: index for index, action in enumerate(priority)}
    eligible = [
        candidate
        for candidate in candidates
        if candidate.role == role and (candidate.role, candidate.action) in mapping
    ]
    if not eligible:
        return None
    return min(eligible, key=lambda item: (rank[item.action], item.created_at, item.number))


def test_shared_governance_and_role_files_exist_with_authority_boundaries() -> None:
    shared = _read(AGENTS / "AGENTS.md")
    for required in (
        "repository default branch",
        "work input. They are not governance",
        "processes at most one eligible Issue",
        "At-least-once execution",
        "state reconstruction",
        "exactly one legal `agent:*` label",
        "persist result + revision-aware evidence",
        "produces no repository noise",
        "not** a mutex, compare-and-swap primitive, or single-flight",
        "OpenSpec Validate",
    ):
        assert required in shared

    lead = _read(AGENTS / "roles/lead.md")
    reviewer = _read(AGENTS / "roles/reviewer.md")
    executor = _read(AGENTS / "roles/executor.md")

    assert "specification authority" in lead
    assert "Do not modify implementation code" in lead
    assert "Do not execute PR merge mutations" in lead
    assert "independent revision-bound verification gates" in reviewer
    assert "Do not modify OpenSpec specification artifacts" in reviewer
    assert "approved implementation work" in executor
    assert "Do not redefine requirements" in executor
    assert "repository automation owns normal" in executor
    assert not (AGENTS / "roles/base.md").exists()


def test_nine_actions_map_once_to_a_reduced_reusable_skill_set() -> None:
    shared = _read(AGENTS / "AGENTS.md")
    mapping = _mapping(shared)
    assert mapping == EXPECTED_SKILLS
    assert len(mapping) == 9
    assert set(mapping) == {
        (role, action) for role, actions in ROLE_ACTIONS.items() for action in actions
    }
    skills = {skill for skill in mapping.values()}
    assert len(skills) == 7
    assert len(skills) < len(mapping)
    for skill in skills:
        assert (ROOT / skill).is_file()
    assert "archive-change" not in {action for _, action in mapping}


def test_deterministic_discovery_uses_fixed_priority_and_stable_tie_breakers() -> None:
    shared = _read(AGENTS / "AGENTS.md")
    assert _priority(shared) == EXPECTED_PRIORITY
    assert "earlier GitHub `created_at` wins" in shared
    assert "lower numeric Issue" in shared
    assert "Model-derived urgency" in shared

    candidates = [
        Candidate(5, "2026-08-01T00:00:00Z", "Executor", "implement-change"),
        Candidate(30, "2026-08-10T00:00:00Z", "Executor", "merge-pr"),
    ]
    assert _select(shared, "Executor", candidates) == candidates[1]

    same_action = [
        Candidate(9, "2026-08-02T00:00:00Z", "Lead", "resolve-question"),
        Candidate(8, "2026-08-01T00:00:00Z", "Lead", "resolve-question"),
        Candidate(7, "2026-08-01T00:00:00Z", "Lead", "resolve-question"),
    ]
    assert _select(shared, "Lead", same_action) == same_action[2]

    invalid = [Candidate(1, "2026-01-01T00:00:00Z", "Executor", "review-openspec")]
    assert _select(shared, "Executor", invalid) is None


def test_review_and_finalize_skills_preserve_upstream_gate_contracts() -> None:
    openspec_review = _read(AGENTS / "skills/openspec-review/SKILL.md")
    implementation_review = _read(AGENTS / "skills/implementation-review/SKILL.md")
    archive_review = _read(AGENTS / "skills/archive-review/SKILL.md")
    finalize = _read(AGENTS / "skills/lifecycle-finalize/SKILL.md")

    for required in (
        "proposal → specs → design → tasks",
        "tasks → design → specs → proposal",
        "README.md",
        "openspec/config.yaml",
        "PASS",
        "FINDINGS",
        "exact reviewed revision",
    ):
        assert required in openspec_review

    for required in (
        "exact current implementation PR head",
        "project gates",
        "IMPLEMENTATION_FINDINGS",
        "SPEC_FINDINGS",
        "approved OpenSpec contract",
    ):
        assert required in implementation_review

    for required in (
        "correct merged default-branch source state",
        "canonical specs",
        "archive history",
        "unrelated repository changes",
        "strict OpenSpec validation",
    ):
        assert required in archive_review

    for required in (
        "Reviewer implementation `PASS`",
        "MERGE_AUTHORIZED",
        "MORE_IMPLEMENTATION_REQUIRED",
        "WAITING_FOR_ARCHIVE_AUTOMATION",
        "Reviewer archive `PASS`",
        "observed `closed` state",
    ):
        assert required in finalize


def test_routing_concurrency_revision_and_crash_recovery_fail_closed() -> None:
    shared = _read(AGENTS / "AGENTS.md")
    merge = _read(AGENTS / "skills/merge-pr/SKILL.md")

    for required in (
        "Zero, multiple, contradictory, or illegal routing labels",
        "Unrelated labels are preserved",
        "not** a mutex, compare-and-swap primitive, or single-flight",
        "contradictory evidence",
        "does not attempt a duplicate merge",
    ):
        assert required in shared

    for required in (
        "Reviewer `PASS` exists for the exact revision R",
        "Lead `MERGE_AUTHORIZED` exists for the exact same revision R",
        "target PR current head still equals R",
        "Reviewer PASS alone is insufficient",
        "Before attempting the mutation",
        "do not retry the merge",
    ):
        assert required in merge


def test_persistent_lifecycle_archive_boundary_and_human_admission_are_documented() -> None:
    shared = _read(AGENTS / "AGENTS.md")
    labels = _read(AGENTS / "labels.md")

    for required in (
        "one persistent coordination Issue",
        "immutable after Lead persists it",
        "MORE_IMPLEMENTATION_REQUIRED",
        "Complete/eligible under the README archive contract",
        "do not define or execute a competing normal `archive-change` action",
        "At most one open",
        "`advisory:idle` Issue",
        "at most three recommendations",
        "no routing tuple",
        "`intake:approved`",
        "MUST NEVER add, remove, restore, or manufacture it",
    ):
        assert required in shared

    for required in (
        "agent:lead",
        "agent:reviewer",
        "agent:executor",
        "advisory:idle",
        "intake:approved",
        "Human/maintainer",
    ):
        assert required in labels


def test_final_completion_requires_observed_issue_closure_and_supports_recovery() -> None:
    shared = _read(AGENTS / "AGENTS.md")
    finalize = _read(AGENTS / "skills/lifecycle-finalize/SKILL.md")

    for required in (
        'PASS, completion comment, or statement that an Issue "may be closed" is not completion',
        "Issue close",
        "Only the observed closed Issue state completes",
        "next Lead run reconstructs the completed archive",
    ):
        assert required in shared

    assert "perform the GitHub coordination Issue close mutation" in finalize
    assert "idempotently performs the missing" in finalize


def test_readme_aligns_role_gates_multi_pr_archive_and_final_closure() -> None:
    readme = _read(ROOT / "README.md")
    for required in (
        "Reviewer / review-openspec",
        "Reviewer / review-implementation",
        "Lead / finalize-change",
        "Executor / merge-pr",
        "MORE_IMPLEMENTATION_REQUIRED",
        "Reviewer / review-archive",
        "Lead / finalize-archive",
        "GitHub native close via final Archive PR closing linkage",
        "intake:approved",
        "不是** mutex、CAS 或 single-flight",
        "validator checkout `HEAD`",
        "run.head_sha` 只是 association metadata",
        "synthetic merge revision",
        "Scheduled Role 不另建 normal `archive-change` mutation",
    ):
        assert required in readme


def test_governance_does_not_add_parallel_workflow_engine_state() -> None:
    shared = _read(AGENTS / "AGENTS.md")
    implementation = _read(AGENTS / "skills/implementation/SKILL.md")

    assert "no central workflow engine" in shared
    assert "exactly-once mechanism" in shared
    assert "status:in-progress" in shared
    assert "generic DAG executor" in implementation
    assert "normal OpenSpec archive mutation" in implementation


def test_task_completion_markers_persist_at_verified_slice_boundary() -> None:
    shared = " ".join(_read(AGENTS / "AGENTS.md").split())
    executor = " ".join(_read(AGENTS / "roles/executor.md").split())
    implementation = " ".join(_read(AGENTS / "skills/implementation/SKILL.md").split())
    readme = " ".join(_read(ROOT / "README.md").split())

    for required in (
        "task checkboxes are durable completion evidence",
        "after the slice's required `VERIFY` succeeds",
        "before starting the next slice or handing off",
        "must not be deferred until the end of the whole change",
        "does not require a dedicated commit for each individual checkbox",
        "previously verified slices remain durable",
    ):
        assert required in shared

    assert "persist all satisfied task-completion markers for that verified slice" in executor
    assert "before starting the next slice or handing off" in executor

    for required in (
        "persist all satisfied task markers for that verified slice",
        "Do not defer completed markers across verified slices",
        "does not require a commit per checkbox",
        "reconstruct the active slice",
    ):
        assert required in implementation

    assert "verified vertical-slice checkpoint" in readme
    assert "`VERIFY` 成功後" in readme
    assert "開始下一個 slice 或 handoff 前更新該 slice 已滿足的 markers" in readme
