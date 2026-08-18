from pathlib import Path

from investment_strategy.workflow_recovery import (
    CompletedMergeRecovery,
    MergeRecoveryKind,
    RecoveryDescendant,
    RecoveryDisposition,
    merge_recovery_disposition,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_shared_recovery_guard_blocks_consumed_transition_routing_regression() -> None:
    shared = _flat(_read("agents/AGENTS.md"))

    assert "causal-descendant evidence" in shared
    assert "specific recovered transition" in shared
    assert "MUST NOT rewrite canonical routing" in shared
    assert "missing non-routing journal evidence" in shared


def test_implementation_merge_recovery_treats_archive_lifecycle_as_consumption() -> None:
    recovery = CompletedMergeRecovery(
        kind=MergeRecoveryKind.IMPLEMENTATION,
        merge_completed=True,
        invocation_identity_complete=True,
        descendants=frozenset(
            {
                RecoveryDescendant.ARCHIVE_PR_READY,
                RecoveryDescendant.ARCHIVE_REVIEW,
            }
        ),
    )

    assert merge_recovery_disposition(recovery) is RecoveryDisposition.JOURNAL_ONLY


def test_archive_merge_recovery_respects_terminal_lifecycle_complete() -> None:
    recovery = CompletedMergeRecovery(
        kind=MergeRecoveryKind.ARCHIVE,
        merge_completed=True,
        invocation_identity_complete=True,
        descendants=frozenset({RecoveryDescendant.LIFECYCLE_COMPLETE}),
    )

    assert merge_recovery_disposition(recovery) is RecoveryDisposition.JOURNAL_ONLY


def test_unconsumed_completed_merge_can_repair_missing_handoff() -> None:
    recovery = CompletedMergeRecovery(
        kind=MergeRecoveryKind.IMPLEMENTATION,
        merge_completed=True,
        invocation_identity_complete=True,
    )

    assert merge_recovery_disposition(recovery) is RecoveryDisposition.REPAIR_HANDOFF


def test_incomplete_or_contradictory_recovery_evidence_fails_closed() -> None:
    missing_identity = CompletedMergeRecovery(
        kind=MergeRecoveryKind.IMPLEMENTATION,
        merge_completed=True,
        invocation_identity_complete=False,
    )
    contradictory = CompletedMergeRecovery(
        kind=MergeRecoveryKind.ARCHIVE,
        merge_completed=True,
        invocation_identity_complete=True,
        descendant_evidence_contradictory=True,
    )

    assert merge_recovery_disposition(missing_identity) is RecoveryDisposition.FAIL_CLOSED
    assert merge_recovery_disposition(contradictory) is RecoveryDisposition.FAIL_CLOSED


def test_consumed_recovery_guard_is_not_generic_forward_only_state() -> None:
    shared = _flat(_read("agents/AGENTS.md"))
    merge_pr = _flat(_read("agents/skills/merge-pr/SKILL.md"))
    combined = f"{shared} {merge_pr}"

    assert "transition-specific" in combined
    assert "legitimate correction loops" in combined
    assert "does not introduce" in combined
    for forbidden in (
        "routing phase field",
        "routing context field",
        "sequence counter",
        "generic forward-only lifecycle rule",
    ):
        assert forbidden not in combined
