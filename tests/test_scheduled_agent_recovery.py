"""Contract tests for constrained scheduled-agent recovery hardening."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = ROOT / "agents" / "roles" / "executor.md"
IMPLEMENTATION = ROOT / "agents" / "skills" / "implementation" / "SKILL.md"


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


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
    ):
        assert required in role or required in skill

    assert "force update" not in skill.lower()


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
