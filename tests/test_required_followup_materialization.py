from pathlib import Path

OPEN_SPEC_EXPLORE = Path("agents/skills/openspec-explore/SKILL.md")
OPEN_SPEC_CHANGE = Path("agents/skills/openspec-change/SKILL.md")
LIFECYCLE_FINALIZE = Path("agents/skills/lifecycle-finalize/SKILL.md")
CHANGE_PROPOSAL = Path(
    "openspec/changes/preserve-required-followup-materialization/proposal.md"
)
CHANGE_SPEC = Path(
    "openspec/changes/preserve-required-followup-materialization/specs/"
    "scheduled-agent-workflow/spec.md"
)


def _openspec_explore_text() -> str:
    return OPEN_SPEC_EXPLORE.read_text(encoding="utf-8")


def _openspec_change_text() -> str:
    return OPEN_SPEC_CHANGE.read_text(encoding="utf-8")


def _lifecycle_finalize_text() -> str:
    return LIFECYCLE_FINALIZE.read_text(encoding="utf-8")


def test_required_followup_success_requires_routing_complete_observation() -> None:
    text = _openspec_change_text()

    assert "reconstruct the approved source obligation and all matching trackers" in text
    assert "exactly one matching tracker" in text
    assert "fresh-reads the tracker" in text
    assert "recognizes success only after" in text
    assert "`Change: unset`" in text
    assert "`agent:lead + action:explore-change`" in text


def test_required_followup_unique_incomplete_tracker_is_repaired_idempotently() -> None:
    text = _openspec_change_text()

    assert "If no matching tracker exists" in text
    assert "If exactly one matching tracker exists" in text
    assert "request repair only of the missing durable fields/routing" in text
    assert "do not request a duplicate" in text


def test_required_followup_ambiguous_matches_fail_closed() -> None:
    text = _openspec_change_text()

    assert "If multiple or ambiguous matching trackers exist" in text
    assert "fail closed" in text
    assert "must not choose a winner" in text


def test_required_followup_does_not_infer_authority_from_prose() -> None:
    text = _openspec_change_text()

    expected = (
        "Ordinary out-of-scope, non-goal, optional, or merely deferred prose does not "
        "create or route a tracker."
    )
    assert expected in text


def test_explore_classifies_required_followup_before_materialization() -> None:
    text = _openspec_explore_text()

    for required in (
        "ordinary deferred / optional / non-goal",
        "required separate follow-up",
        "already-tracked separate work",
        "persist the `PROPOSAL_READY` `ACTION_RESULT` before requesting tracker materialization",
    ):
        assert required in text


def test_explore_required_followup_requires_routing_complete_postcondition_before_propose() -> None:
    text = _openspec_explore_text()

    assert "fresh observation proves the tracker is source-linked" in text
    assert "`Change: unset`" in text
    assert "`agent:lead + action:explore-change`" in text
    assert "MUST NOT request routing to `Lead / propose-change`" in text


def test_explore_replays_same_required_followup_decision_idempotently() -> None:
    text = _openspec_explore_text()

    for required in (
        "same exact durable Explore result",
        "exactly one matching but incomplete tracker",
        "reuse the complete tracker",
        "multiple or ambiguous matching trackers",
        "fail closed",
        "must not create a duplicate",
    ):
        assert required in text


def test_explore_does_not_promote_deferred_wording_into_required_followup() -> None:
    text = _openspec_explore_text()

    assert "presentation wording does not create or erase the classification" in text
    assert "ordinary deferred / optional / non-goal" in text


def test_change_contract_keeps_required_followup_scope_bounded() -> None:
    proposal = CHANGE_PROPOSAL.read_text(encoding="utf-8")
    delta = CHANGE_SPEC.read_text(encoding="utf-8")

    assert "agents/skills/openspec-explore/SKILL.md" in proposal
    assert "agents/skills/openspec-change/SKILL.md" in proposal
    assert "No Skill is Added or Removed" in proposal
    assert "Reviewer and lifecycle Skills retain their existing" in proposal
    assert "retrospective tracker creation for #140 or #155" in proposal
    assert "adds no new Reviewer producer authority or lifecycle topology" in delta


def test_lifecycle_preparation_repairs_only_unique_required_tracker() -> None:
    text = _lifecycle_finalize_text()

    assert "same routing-complete required-follow-up postcondition" in text
    assert "exactly one matching incomplete required tracker" in text
    assert "repair only its missing durable fields or canonical routing" in text
    assert "Multiple or ambiguous matching trackers fail closed" in text
    assert "`agent:lead + action:explore-change`" in text


def test_lifecycle_preparation_does_not_route_optional_or_prose_only_work() -> None:
    text = _lifecycle_finalize_text()

    assert "Ordinary out-of-scope, non-goal," in text
    optional_rule = (
        "optional, or merely deferred prose creates no materialization or routing obligation."
    )
    assert optional_rule in text
