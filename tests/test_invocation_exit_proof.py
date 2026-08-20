from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Evidence:
    red_established: bool = False
    actionable_validation_failure: bool = False
    verified_slice_with_remaining_work: bool = False


def _shared_governance() -> str:
    return (ROOT / "agents/AGENTS.md").read_text(encoding="utf-8")


def _classify(evidence: Evidence) -> str:
    governance = _shared_governance()
    positive_exit_contract = (
        "positively classify" in governance
        and "Exit Proof" in governance
        and "If no legal Exit" in governance
    )
    explicit_non_exit_evidence = (
        evidence.red_established
        or evidence.actionable_validation_failure
        or evidence.verified_slice_with_remaining_work
    )
    if positive_exit_contract and explicit_non_exit_evidence:
        return "CONTINUE"
    return "UNPROVEN"


def test_red_with_known_green_requires_continuation() -> None:
    assert _classify(Evidence(red_established=True)) == "CONTINUE"


def test_failed_but_actionable_validation_requires_continuation() -> None:
    assert _classify(Evidence(actionable_validation_failure=True)) == "CONTINUE"


def test_verified_slice_with_remaining_work_requires_continuation() -> None:
    assert _classify(Evidence(verified_slice_with_remaining_work=True)) == "CONTINUE"
