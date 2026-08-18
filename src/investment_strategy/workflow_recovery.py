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


class ReviewerGate(StrEnum):
    IMPLEMENTATION = "review-implementation"
    ARCHIVE = "review-archive"


@dataclass(frozen=True)
class TargetPullRequestEvidence:
    number: int
    head_revision: str
    merged: bool
    merge_commit: str | None
    closes_coordination_issue: bool
    archive_preparation_reviewed: bool = False


@dataclass(frozen=True)
class ReviewerPassEvidence:
    gate: ReviewerGate
    pr_number: int
    revision: str


@dataclass(frozen=True)
class MergeResultEvidence:
    pr_number: int
    accepted_revision: str
    merge_commit: str


@dataclass(frozen=True)
class LifecycleDescendantEvidence:
    change: str
    descendant: RecoveryDescendant
    source_pr_number: int
    source_accepted_revision: str
    source_merge_commit: str
    contradictory: bool = False


@dataclass(frozen=True)
class DurableMergeRecoveryEvidence:
    change: str
    target_pr: TargetPullRequestEvidence
    reviewer_pass: ReviewerPassEvidence
    merge_result: MergeResultEvidence
    descendants: tuple[LifecycleDescendantEvidence, ...] = ()


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


def reconstruct_completed_merge_recovery(
    evidence: DurableMergeRecoveryEvidence,
) -> CompletedMergeRecovery | None:
    """Derive one completed merge invocation from durable workflow evidence.

    The merge kind, identity completeness, and causal descendants are derived from the
    target PR, exact Reviewer PASS, exact merge result, closing/preparation evidence,
    and descendant records bound back to the same recovered transition. A caller cannot
    assert a recovery kind, identity-complete boolean, or descendant set directly.
    """
    target = evidence.target_pr
    review = evidence.reviewer_pass
    merge = evidence.merge_result

    exact_identity = (
        target.merged
        and target.merge_commit is not None
        and review.pr_number == target.number
        and review.revision == target.head_revision
        and merge.pr_number == target.number
        and merge.accepted_revision == target.head_revision
        and merge.merge_commit == target.merge_commit
    )
    if not exact_identity:
        return None

    if review.gate is ReviewerGate.IMPLEMENTATION:
        if target.closes_coordination_issue:
            return None
        kind = MergeRecoveryKind.IMPLEMENTATION
    else:
        if not target.closes_coordination_issue or not target.archive_preparation_reviewed:
            return None
        kind = MergeRecoveryKind.ARCHIVE

    descendants: set[RecoveryDescendant] = set()
    contradictory = False
    for item in evidence.descendants:
        bound_to_recovered_transition = (
            item.change == evidence.change
            and item.source_pr_number == target.number
            and item.source_accepted_revision == target.head_revision
            and item.source_merge_commit == target.merge_commit
        )
        if not bound_to_recovered_transition or item.contradictory:
            contradictory = True
            continue
        descendants.add(item.descendant)

    return CompletedMergeRecovery(
        kind=kind,
        merge_completed=True,
        invocation_identity_complete=True,
        descendants=frozenset(descendants),
        descendant_evidence_contradictory=contradictory,
    )


def merge_recovery_disposition(recovery: CompletedMergeRecovery) -> RecoveryDisposition:
    """Decide whether crash recovery may repair routing for one completed merge transition."""
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


def merge_recovery_disposition_from_evidence(
    evidence: DurableMergeRecoveryEvidence,
) -> RecoveryDisposition:
    """Reconstruct durable evidence first, then decide the legal recovery mutation."""
    recovery = reconstruct_completed_merge_recovery(evidence)
    if recovery is None:
        return RecoveryDisposition.FAIL_CLOSED
    return merge_recovery_disposition(recovery)
