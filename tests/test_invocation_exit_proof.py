from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Evidence:
    red_established: bool = False
    actionable_validation_failure: bool = False
    verified_slice_with_remaining_work: bool = False
    exact_resource_status: str | None = None
    exact_resource_unconsumable: bool = False
    same_role_successor: bool = False
    cross_role_handoff_completed: bool = False
    workflow_terminal: bool = False
    human_authority_boundary: bool = False
    stale_precondition: bool = False
    ambiguous_or_contradictory_state: bool = False
    hard_execution_boundary: bool = False
    same_authority_recovery_available: bool = False
    attempted_return: bool = False


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _classify(evidence: Evidence) -> str:
    if (
        evidence.red_established
        or evidence.actionable_validation_failure
        or evidence.verified_slice_with_remaining_work
    ):
        return "CONTINUE"

    if evidence.exact_resource_status in {"absent", "queued", "in_progress"}:
        if evidence.exact_resource_unconsumable:
            return "ASYNC_WAIT"
        return "CONTINUE"

    if evidence.same_role_successor:
        return "CONTINUE"

    if evidence.cross_role_handoff_completed:
        return "CROSS_ROLE_HANDOFF"

    if evidence.workflow_terminal:
        return "TERMINAL"

    if evidence.human_authority_boundary:
        return "HUMAN_BOUNDARY"

    if evidence.stale_precondition:
        return "STALE"

    if evidence.ambiguous_or_contradictory_state:
        return "AMBIGUOUS"

    if evidence.hard_execution_boundary:
        if evidence.same_authority_recovery_available:
            return "CONTINUE"
        return "HARD_BOUNDARY"

    if evidence.attempted_return:
        return "RETURN_REJECTED"

    return "CONTINUE"


def test_shared_owner_and_action_consumers_are_integrated() -> None:
    governance = _read("agents/AGENTS.md")
    assert "positively classify" in governance
    assert "If no legal Exit class is proven" in governance
    assert "Exit Proof is an internal execution precondition" in governance

    for path in (
        "agents/skills/implementation/SKILL.md",
        "agents/skills/openspec-change/SKILL.md",
        "agents/skills/implementation-review/SKILL.md",
    ):
        assert "consume the shared Invocation Exit Proof invariant" in _read(path)


def test_red_with_known_green_requires_continuation() -> None:
    assert _classify(Evidence(red_established=True)) == "CONTINUE"


def test_failed_but_actionable_validation_requires_continuation() -> None:
    assert _classify(Evidence(actionable_validation_failure=True)) == "CONTINUE"


def test_verified_slice_with_remaining_work_requires_continuation() -> None:
    assert _classify(Evidence(verified_slice_with_remaining_work=True)) == "CONTINUE"


def test_first_nonterminal_exact_resource_observation_requires_continuation() -> None:
    for status in ("absent", "queued", "in_progress"):
        assert _classify(Evidence(exact_resource_status=status)) == "CONTINUE"


def test_genuine_unconsumable_exact_resource_wait_may_exit() -> None:
    assert (
        _classify(
            Evidence(
                exact_resource_status="in_progress",
                exact_resource_unconsumable=True,
            )
        )
        == "ASYNC_WAIT"
    )


def test_immediately_actionable_lead_same_role_successor_continues() -> None:
    assert _classify(Evidence(same_role_successor=True)) == "CONTINUE"


def test_completed_reviewer_cross_role_handoff_may_exit() -> None:
    assert _classify(Evidence(cross_role_handoff_completed=True)) == "CROSS_ROLE_HANDOFF"


def test_stale_precondition_may_exit_fail_closed() -> None:
    assert _classify(Evidence(stale_precondition=True)) == "STALE"


def test_hard_boundary_requires_unavailable_same_authority_recovery() -> None:
    assert (
        _classify(
            Evidence(
                hard_execution_boundary=True,
                same_authority_recovery_available=True,
            )
        )
        == "CONTINUE"
    )
    assert _classify(Evidence(hard_execution_boundary=True)) == "HARD_BOUNDARY"


def test_attempted_return_without_positive_exit_is_rejected() -> None:
    assert _classify(Evidence(attempted_return=True)) == "RETURN_REJECTED"


def test_terminal_and_human_exit_require_positive_evidence() -> None:
    assert _classify(Evidence(workflow_terminal=True)) == "TERMINAL"
    assert _classify(Evidence(human_authority_boundary=True)) == "HUMAN_BOUNDARY"


def test_ambiguous_state_exit_requires_positive_evidence() -> None:
    assert _classify(Evidence(ambiguous_or_contradictory_state=True)) == "AMBIGUOUS"


def test_exit_classes_do_not_exist_without_their_evidence() -> None:
    assert _classify(Evidence(attempted_return=True)) == "RETURN_REJECTED"
    assert (
        _classify(Evidence(exact_resource_status="in_progress", attempted_return=True))
        == "CONTINUE"
    )
    assert (
        _classify(
            Evidence(
                hard_execution_boundary=True,
                same_authority_recovery_available=True,
                attempted_return=True,
            )
        )
        == "CONTINUE"
    )
