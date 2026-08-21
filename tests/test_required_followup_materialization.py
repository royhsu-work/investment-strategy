from pathlib import Path

OPEN_SPEC_CHANGE = Path("agents/skills/openspec-change/SKILL.md")
LIFECYCLE_FINALIZE = Path("agents/skills/lifecycle-finalize/SKILL.md")


def _openspec_change_text() -> str:
    return OPEN_SPEC_CHANGE.read_text(encoding="utf-8")


def _lifecycle_finalize_text() -> str:
    return LIFECYCLE_FINALIZE.read_text(encoding="utf-8")


def test_required_followup_success_requires_routing_complete_observation() -> None:
    text = _openspec_change_text()

    assert "reconstruct the approved source obligation and all matching trackers" in text
    assert "exactly one matching tracker" in text
    assert "fresh-read the tracker after the routing mutation" in text
    assert "success only after" in text
    assert "`Change: unset`" in text
    assert "`agent:lead + action:explore-change`" in text


def test_required_followup_unique_incomplete_tracker_is_repaired_idempotently() -> None:
    text = _openspec_change_text()

    assert "If no matching tracker exists" in text
    assert "If exactly one matching tracker exists" in text
    assert "repair only the missing durable fields or routing" in text
    assert "do not create a duplicate" in text


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
