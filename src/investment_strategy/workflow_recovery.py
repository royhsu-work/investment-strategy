from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MergeRecoveryKind(StrEnum):
    IMPLEMENTATION = "implementation"
    ARCHIVE = "archive"


class RecoveryDisposition(StrEnum):
    REPAIR_HANDOFF = "repair-handoff"
    JOURNAL_ONLY = "journal-only"
    FAIL_CLOSED = "fail-closed"


class RecoveryDescendant(StrEnum):
    FINALIZE_CHANGE_RESULT = "finalize-change-result"
    ARCHIVE_BRANCH_READY = "archive-branch-ready"
    ARCHIVE_PR_READY = "archive-pr-ready"
    ARCHIVE_REVIEW = "archive-review"
    ARCHIVE_MERGE = "archive-merge"
    FINALIZE_ARCHIVE = "finalize-archive"
    LIFECYCLE_COMPLETE = "lifecycle-complete"


@dataclass(frozen=True)
class CompletedMergeRecovery:
    kind: MergeRecoveryKind
    merge_completed: bool
    invocation_identity_complete: bool
    descendants: frozenset[RecoveryDescendant] = frozenset()
    descendant_evidence_contradictory: bool = False


_IMPLEMENTATION_CONSUMPTION = frozenset(
    {
        RecoveryDescendant.FINALIZE_CHANGE_RESULT,
        RecoveryDescendant.ARCHIVE_BRANCH_READY,
        RecoveryDescendant.ARCHIVE_PR_READY,
        RecoveryDescendant.ARCHIVE_REVIEW,
        RecoveryDescendant.ARCHIVE_MERGE,
        RecoveryDescendant.FINALIZE_ARCHIVE,
        RecoveryDescendant.LIFECYCLE_COMPLETE,
    }
)
_ARCHIVE_CONSUMPTION = frozenset(
    {
        RecoveryDescendant.FINALIZE_ARCHIVE,
        RecoveryDescendant.LIFECYCLE_COMPLETE,
    }
)


def merge_recovery_disposition(recovery: CompletedMergeRecovery) -> RecoveryDisposition:
    """Decide whether crash recovery may repair routing for one completed merge transition.

    The caller must first reconstruct the specific merge invocation from durable workflow
    evidence. This helper deliberately models only the recovery mutation boundary: a
    causally consumed transition may receive journal-only repair, while an unconsumed
    completed transition may repair its missing handoff. Incomplete or contradictory
    evidence fails closed.
    """
    if not recovery.merge_completed or not recovery.invocation_identity_complete:
        return RecoveryDisposition.FAIL_CLOSED
    if recovery.descendant_evidence_contradictory:
        return RecoveryDisposition.FAIL_CLOSED

    consumption_set = (
        _IMPLEMENTATION_CONSUMPTION
        if recovery.kind is MergeRecoveryKind.IMPLEMENTATION
        else _ARCHIVE_CONSUMPTION
    )
    if recovery.descendants & consumption_set:
        return RecoveryDisposition.JOURNAL_ONLY
    return RecoveryDisposition.REPAIR_HANDOFF
