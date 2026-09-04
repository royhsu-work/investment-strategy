from pathlib import Path

from investment_strategy.workflow_recovery import (
    DurableMergeRecoveryEvidence,
    LifecycleDescendantEvidence,
    MergeResultEvidence,
    RecoveryDescendant,
    RecoveryDisposition,
    ReviewerGate,
    ReviewerPassEvidence,
    TargetPullRequestEvidence,
    merge_recovery_disposition_from_evidence,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _implementation_evidence(
    *descendants: LifecycleDescendantEvidence,
) -> DurableMergeRecoveryEvidence:
    return DurableMergeRecoveryEvidence(
        change="allow-human-created-explore-admission",
        target_pr=TargetPullRequestEvidence(
            number=89,
            head_revision="impl-head",
            merged=True,
            merge_commit="impl-merge",
            closes_coordination_issue=False,
        ),
        reviewer_pass=ReviewerPassEvidence(
            gate=ReviewerGate.IMPLEMENTATION,
            pr_number=89,
            revision="impl-head",
        ),
        merge_result=MergeResultEvidence(
            pr_number=89,
            accepted_revision="impl-head",
            merge_commit="impl-merge",
        ),
        descendants=descendants,
    )


def _archive_evidence(
    *descendants: LifecycleDescendantEvidence,
) -> DurableMergeRecoveryEvidence:
    return DurableMergeRecoveryEvidence(
        change="allow-human-created-explore-admission",
        target_pr=TargetPullRequestEvidence(
            number=90,
            head_revision="archive-head",
            merged=True,
            merge_commit="archive-merge",
            closes_coordination_issue=True,
            archive_preparation_reviewed=True,
        ),
        reviewer_pass=ReviewerPassEvidence(
            gate=ReviewerGate.ARCHIVE,
            pr_number=90,
            revision="archive-head",
        ),
        merge_result=MergeResultEvidence(
            pr_number=90,
            accepted_revision="archive-head",
            merge_commit="archive-merge",
        ),
        descendants=descendants,
    )


def test_shared_recovery_guard_blocks_consumed_transition_routing_regression() -> None:
    shared = _flat(_read("agents/AGENTS.md"))

    assert "causal-descendant evidence" in shared
    assert "specific recovered transition" in shared
    assert "MUST NOT rewrite canonical routing" in shared
    assert "missing non-routing journal evidence" in shared


def test_88_implementation_recovery_derives_consumption_from_durable_descendants() -> None:
    archive_pr_ready = LifecycleDescendantEvidence(
        change="allow-human-created-explore-admission",
        descendant=RecoveryDescendant.ARCHIVE_PR_READY,
        source_pr_number=89,
        source_accepted_revision="impl-head",
        source_merge_commit="impl-merge",
    )
    archive_review = LifecycleDescendantEvidence(
        change="allow-human-created-explore-admission",
        descendant=RecoveryDescendant.ARCHIVE_REVIEW,
        source_pr_number=89,
        source_accepted_revision="impl-head",
        source_merge_commit="impl-merge",
    )

    assert (
        merge_recovery_disposition_from_evidence(
            _implementation_evidence(archive_pr_ready, archive_review)
        )
        is RecoveryDisposition.JOURNAL_ONLY
    )


def test_archive_merge_recovery_derives_terminal_consumption() -> None:
    lifecycle_complete = LifecycleDescendantEvidence(
        change="allow-human-created-explore-admission",
        descendant=RecoveryDescendant.LIFECYCLE_COMPLETE,
        source_pr_number=90,
        source_accepted_revision="archive-head",
        source_merge_commit="archive-merge",
    )

    assert (
        merge_recovery_disposition_from_evidence(_archive_evidence(lifecycle_complete))
        is RecoveryDisposition.JOURNAL_ONLY
    )


def test_unconsumed_completed_merge_can_repair_missing_handoff() -> None:
    assert (
        merge_recovery_disposition_from_evidence(_implementation_evidence())
        is RecoveryDisposition.REPAIR_HANDOFF
    )


def test_recovery_kind_is_derived_from_reviewer_gate_and_linkage() -> None:
    closing_implementation_pr = DurableMergeRecoveryEvidence(
        change="change",
        target_pr=TargetPullRequestEvidence(
            number=7,
            head_revision="head",
            merged=True,
            merge_commit="merge",
            closes_coordination_issue=True,
        ),
        reviewer_pass=ReviewerPassEvidence(
            gate=ReviewerGate.IMPLEMENTATION,
            pr_number=7,
            revision="head",
        ),
        merge_result=MergeResultEvidence(
            pr_number=7,
            accepted_revision="head",
            merge_commit="merge",
        ),
    )
    archive_without_reviewed_preparation = DurableMergeRecoveryEvidence(
        change="change",
        target_pr=TargetPullRequestEvidence(
            number=8,
            head_revision="head",
            merged=True,
            merge_commit="merge",
            closes_coordination_issue=True,
            archive_preparation_reviewed=False,
        ),
        reviewer_pass=ReviewerPassEvidence(
            gate=ReviewerGate.ARCHIVE,
            pr_number=8,
            revision="head",
        ),
        merge_result=MergeResultEvidence(
            pr_number=8,
            accepted_revision="head",
            merge_commit="merge",
        ),
    )

    assert (
        merge_recovery_disposition_from_evidence(closing_implementation_pr)
        is RecoveryDisposition.FAIL_CLOSED
    )
    assert (
        merge_recovery_disposition_from_evidence(archive_without_reviewed_preparation)
        is RecoveryDisposition.FAIL_CLOSED
    )


def test_incomplete_exact_identity_or_unbound_descendant_fails_closed() -> None:
    mismatched_review = DurableMergeRecoveryEvidence(
        change="change",
        target_pr=TargetPullRequestEvidence(
            number=7,
            head_revision="head",
            merged=True,
            merge_commit="merge",
            closes_coordination_issue=False,
        ),
        reviewer_pass=ReviewerPassEvidence(
            gate=ReviewerGate.IMPLEMENTATION,
            pr_number=7,
            revision="stale-head",
        ),
        merge_result=MergeResultEvidence(
            pr_number=7,
            accepted_revision="head",
            merge_commit="merge",
        ),
    )
    unbound_descendant = LifecycleDescendantEvidence(
        change="other-change",
        descendant=RecoveryDescendant.ARCHIVE_PR_READY,
        source_pr_number=89,
        source_accepted_revision="impl-head",
        source_merge_commit="impl-merge",
    )

    assert (
        merge_recovery_disposition_from_evidence(mismatched_review)
        is RecoveryDisposition.FAIL_CLOSED
    )
    assert (
        merge_recovery_disposition_from_evidence(_implementation_evidence(unbound_descendant))
        is RecoveryDisposition.FAIL_CLOSED
    )


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
