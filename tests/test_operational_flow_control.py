"""Contract coverage for the reduced Action-only operational boundary."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_dispatch_selection_is_complete_wip_ordered_and_fail_closed() -> None:
    shared = _normalized(ROOT / "agents/AGENTS.md")
    workflow = _normalized(ROOT / "agents/workflow.md")
    for required in (
        "Selection is complete and provenance-qualified",
        "Formal Change work has priority",
        "WIP=1 violation",
        "Finish-first ordering is deterministic",
        "fail closed",
        "one Action per Scheduled Task wake",
    ):
        assert required in shared or required in workflow


def test_current_state_has_no_independent_role_dimension() -> None:
    shared = _normalized(ROOT / "agents/AGENTS.md")
    assert "Role = role_for(Action)" in shared
    assert "Role is never an independent routing fact" in shared
    assert "exactly one action:<action>" in shared


def test_successors_are_persisted_for_later_wakes() -> None:
    workflow = _normalized(ROOT / "agents/workflow.md")
    for required in (
        "one structured result",
        "next_action(current_action, result)",
        "one successor or terminal state",
        "later fresh wake",
    ):
        assert required in workflow


def test_project_views_and_scheduler_slots_are_not_repository_authority() -> None:
    migration = _normalized(ROOT / "agents/scheduled-task-migration.md")
    assert "presentation only" in migration
    assert "do not participate in dispatch, routing, authority, or gate decisions" in migration
    assert "external product configuration" in migration


def test_capability_failures_are_classified_without_expanding_governance() -> None:
    shared = _normalized(ROOT / "agents/AGENTS.md")
    for required in (
        "semantic authority",
        "application",
        "transport/actuator",
        "implementation defect",
        "missing capability does not imply",
    ):
        assert required in shared
    assert "generic orchestration kernel" in shared
