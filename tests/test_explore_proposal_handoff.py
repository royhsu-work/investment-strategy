from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
REVIEW = ROOT / "agents" / "skills" / "openspec-review" / "SKILL.md"
ADAPTER = ROOT / "agents" / "skills" / "openspec-semantic-adapter.md"


class ReviewDisposition(Enum):
    ORDINARY_GATE = "ordinary-gate"
    FINDINGS = "findings"


@dataclass(frozen=True)
class ExploreResult:
    comment_id: int
    decided_scope: frozenset[str]
    constraints: frozenset[str]
    exclusions: frozenset[str]
    selected_direction: str


@dataclass(frozen=True)
class FormalizedTarget:
    explore_result_comment_id: int | None
    decided_scope: frozenset[str]
    constraints: frozenset[str]
    exclusions: frozenset[str]
    selected_direction: str
    internally_consistent: bool = True


def _classify_explore_preservation(
    *,
    origin: str,
    explore_result: ExploreResult | None,
    target: FormalizedTarget,
) -> ReviewDisposition:
    """Executable fixture for the approved Explore-preservation review decision."""
    if origin == "direct-propose":
        if target.explore_result_comment_id is not None:
            return ReviewDisposition.FINDINGS
        return ReviewDisposition.ORDINARY_GATE

    if origin != "explore":
        raise ValueError(f"unsupported origin: {origin}")
    if explore_result is None:
        return ReviewDisposition.FINDINGS
    if target.explore_result_comment_id != explore_result.comment_id:
        return ReviewDisposition.FINDINGS

    preserves_material_boundary = (
        explore_result.decided_scope <= target.decided_scope
        and explore_result.constraints <= target.constraints
        and explore_result.exclusions <= target.exclusions
        and target.selected_direction == explore_result.selected_direction
    )
    if not preserves_material_boundary:
        return ReviewDisposition.FINDINGS

    return ReviewDisposition.ORDINARY_GATE


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _explore_result() -> ExploreResult:
    return ExploreResult(
        comment_id=5352138330,
        decided_scope=frozenset({"preserve-explore-result"}),
        constraints=frozenset({"reviewer-does-not-rerun-explore"}),
        exclusions=frozenset({"no-synthetic-explore-for-direct-propose"}),
        selected_direction="exact-result-reference",
    )


def _faithful_target() -> FormalizedTarget:
    return FormalizedTarget(
        explore_result_comment_id=5352138330,
        decided_scope=frozenset({"preserve-explore-result"}),
        constraints=frozenset({"reviewer-does-not-rerun-explore"}),
        exclusions=frozenset({"no-synthetic-explore-for-direct-propose"}),
        selected_direction="exact-result-reference",
    )


def test_shared_governance_owns_explore_to_propose_handoff_invariant() -> None:
    shared = _normalized(AGENTS)

    for required in (
        "exact durable Explore",
        "ACTION_RESULT",
        "PROPOSAL_READY",
        "preserve",
    ):
        assert required in shared


def test_explore_originated_propose_requires_exact_durable_result_reference() -> None:
    change = _normalized(CHANGE)

    for required in (
        "exact durable Explore",
        "ACTION_RESULT",
        "PROPOSAL_READY",
        "preserve",
    ):
        assert required in change


def test_direct_propose_does_not_fabricate_explore_reference() -> None:
    direct_target = FormalizedTarget(
        explore_result_comment_id=None,
        decided_scope=frozenset({"direct-scope"}),
        constraints=frozenset(),
        exclusions=frozenset(),
        selected_direction="direct-direction",
    )

    assert (
        _classify_explore_preservation(
            origin="direct-propose",
            explore_result=None,
            target=direct_target,
        )
        is ReviewDisposition.ORDINARY_GATE
    )

    synthetic_target = FormalizedTarget(
        explore_result_comment_id=5352138330,
        decided_scope=direct_target.decided_scope,
        constraints=direct_target.constraints,
        exclusions=direct_target.exclusions,
        selected_direction=direct_target.selected_direction,
    )
    assert (
        _classify_explore_preservation(
            origin="direct-propose",
            explore_result=None,
            target=synthetic_target,
        )
        is ReviewDisposition.FINDINGS
    )


def test_review_dereferences_explore_result_before_bidirectional_gate() -> None:
    review = _read(REVIEW)
    normalized = " ".join(review.split())

    assert "exact Explore" in normalized
    assert "dereference" in normalized
    assert "preserv" in normalized

    dereference_at = review.lower().find("derefer")
    reverse_at = review.lower().find("reverse traceability")
    assert dereference_at >= 0
    assert reverse_at >= 0
    assert dereference_at < reverse_at


def test_review_rejects_internal_consistency_that_conflicts_with_explore() -> None:
    explore = _explore_result()
    faithful = _faithful_target()
    contradictory = FormalizedTarget(
        explore_result_comment_id=faithful.explore_result_comment_id,
        decided_scope=faithful.decided_scope,
        constraints=faithful.constraints,
        exclusions=faithful.exclusions,
        selected_direction="rewrite-without-exact-result-preservation",
        internally_consistent=True,
    )

    assert contradictory.internally_consistent is True
    assert (
        _classify_explore_preservation(
            origin="explore",
            explore_result=explore,
            target=contradictory,
        )
        is ReviewDisposition.FINDINGS
    )


def test_review_rejects_omitted_explore_constraint_despite_internal_consistency() -> None:
    explore = _explore_result()
    faithful = _faithful_target()
    omitted_constraint = FormalizedTarget(
        explore_result_comment_id=faithful.explore_result_comment_id,
        decided_scope=faithful.decided_scope,
        constraints=frozenset(),
        exclusions=faithful.exclusions,
        selected_direction=faithful.selected_direction,
        internally_consistent=True,
    )

    assert omitted_constraint.internally_consistent is True
    assert (
        _classify_explore_preservation(
            origin="explore",
            explore_result=explore,
            target=omitted_constraint,
        )
        is ReviewDisposition.FINDINGS
    )


def test_faithful_explore_formalization_reaches_ordinary_review_gate() -> None:
    assert (
        _classify_explore_preservation(
            origin="explore",
            explore_result=_explore_result(),
            target=_faithful_target(),
        )
        is ReviewDisposition.ORDINARY_GATE
    )


def test_missing_or_wrong_explore_result_reference_fails_closed() -> None:
    explore = _explore_result()
    faithful = _faithful_target()

    missing_reference = FormalizedTarget(
        explore_result_comment_id=None,
        decided_scope=faithful.decided_scope,
        constraints=faithful.constraints,
        exclusions=faithful.exclusions,
        selected_direction=faithful.selected_direction,
    )
    wrong_reference = FormalizedTarget(
        explore_result_comment_id=explore.comment_id + 1,
        decided_scope=faithful.decided_scope,
        constraints=faithful.constraints,
        exclusions=faithful.exclusions,
        selected_direction=faithful.selected_direction,
    )

    for target in (missing_reference, wrong_reference):
        assert (
            _classify_explore_preservation(
                origin="explore",
                explore_result=explore,
                target=target,
            )
            is ReviewDisposition.FINDINGS
        )


def test_review_does_not_rerun_explore_or_reconstruct_conversation_intent() -> None:
    review = _normalized(REVIEW)

    assert "re-run Explore" in review or "repeat Explore" in review
    assert "conversation" in review


def test_semantic_adapter_does_not_own_explore_handoff_semantics() -> None:
    adapter = _read(ADAPTER)

    assert "Explore-originated" not in adapter
    assert "PROPOSAL_READY" not in adapter


def test_propose_preserves_required_followup_and_tracker_outside_current_scope() -> None:
    change = _normalized(CHANGE)

    for required in (
        "For an Explore-originated required separate follow-up",
        "preserve the required-follow-up classification",
        "routing-complete tracker",
        "outside the current Change implementation scope",
    ):
        assert required in change


def test_propose_rejects_missing_or_ambiguous_required_tracker() -> None:
    change = _normalized(CHANGE)

    missing_tracker = (
        "If no matching tracker exists for an Explore-originated required separate follow-up"
    )
    assert missing_tracker in change
    assert "multiple or ambiguous matching trackers for that Explore decision" in change
    assert "fail closed" in change


def test_propose_repairs_only_unique_incomplete_explore_tracker() -> None:
    change = _normalized(CHANGE)

    assert "exactly one matching but incomplete Explore-originated tracker" in change
    assert "repair only the missing durable fields/routing" in change
    assert "must not create a duplicate" in change


def test_propose_does_not_upgrade_or_downgrade_from_presentation_wording() -> None:
    change = _normalized(CHANGE)

    presentation_rule = (
        "presentation wording does not create or erase the required-follow-up classification"
    )
    assert presentation_rule in change
    assert "Deferred work" in change
    assert "out of scope" in change
