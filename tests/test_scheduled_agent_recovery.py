"""Contract tests for constrained scheduled-agent recovery hardening."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
EXECUTOR = ROOT / "agents" / "roles" / "executor.md"
OPEN_SPEC_CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
IMPLEMENTATION = ROOT / "agents" / "skills" / "implementation" / "SKILL.md"
LIFECYCLE_FINALIZE = ROOT / "agents" / "skills" / "lifecycle-finalize" / "SKILL.md"


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_external_async_wait_resume_requires_fresh_awaited_resource() -> None:
    governance = _normalized(AGENTS)
    for required in (
        "specific awaited resource",
        "historical `in_progress`",
        "cannot by itself justify another yield",
        "work-conserving",
    ):
        assert required in governance


def test_identical_retry_requires_changed_evidence_or_different_legal_path() -> None:
    governance = _normalized(AGENTS)
    for required in (
        "identical operation",
        "material precondition",
        "different legal repository operation",
        "Scheduled Task output",
        "not durable workflow state",
    ):
        assert required in governance


def test_constrained_branch_integration_is_executor_owned_and_non_force() -> None:
    role = _normalized(EXECUTOR)
    skill = _normalized(IMPLEMENTATION)

    for required in (
        "constrained branch integration",
        "fresh-read the implementation PR head and default-branch head",
        "semantics-preserving integration correction",
        "non-force",
        "new head invalidates exact-head readiness evidence",
        "Lead / resolve-question",
        "Do not force update the implementation branch",
    ):
        assert required in role or required in skill


def test_constrained_integration_requires_verifiable_tree_and_changed_head_gates() -> None:
    skill = _normalized(IMPLEMENTATION)
    for required in (
        "resulting tree",
        "approved OpenSpec meaning",
        "current quality gates",
        "Reviewer / review-implementation",
        "cannot safely complete",
        "EXECUTION_EXCEPTION",
    ):
        assert required in skill


def test_implementation_pr_must_be_ready_before_review_handoff() -> None:
    role = _normalized(EXECUTOR)
    skill = _normalized(IMPLEMENTATION)
    for required in (
        "Draft-to-Ready",
        "same current head",
        "Draft PR MUST NOT be handed",
        "EXECUTION_EXCEPTION",
    ):
        assert required in role or required in skill


def test_human_notified_is_idempotent_historical_analytics_only() -> None:
    governance = _normalized(AGENTS)
    lead = _normalized(LEAD)
    skill = _normalized(OPEN_SPEC_CHANGE)
    combined = " ".join((governance, lead, skill))
    for required in (
        "idempotently ensure",
        "human:notified",
        "historical",
        "analytics-only",
        "does not participate in routing",
        "ordinary resolution does not remove it",
    ):
        assert required in combined


def test_temporary_recovery_branch_cleanup_is_safe_and_terminally_verified() -> None:
    governance = _normalized(AGENTS)
    executor = _normalized(EXECUTOR)
    implementation = _normalized(IMPLEMENTATION)
    finalize = _normalized(LIFECYCLE_FINALIZE)
    combined = " ".join((governance, executor, implementation, finalize))
    for required in (
        "workflow-owned temporary",
        "open PR head or base",
        "no unique commits",
        "ahead_by == 0",
        "durable reconstructable reason",
        "LIFECYCLE_COMPLETE",
        "broad `agent/*` garbage collection",
    ):
        assert required in combined
