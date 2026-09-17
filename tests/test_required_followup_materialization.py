from pathlib import Path

OPEN_SPEC_EXPLORE = Path("agents/skills/openspec-explore/SKILL.md")
OPEN_SPEC_CHANGE = Path("agents/skills/openspec-change/SKILL.md")
LIFECYCLE_FINALIZE = Path("agents/skills/lifecycle-finalize/SKILL.md")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_required_followup_is_source_bound_and_deduplicated() -> None:
    text = _text(OPEN_SPEC_CHANGE)
    assert "required separate follow-up" in text
    assert "exact durable source decision" in text
    assert "one deduplicated target" in text


def test_optional_or_deferred_prose_creates_no_routing_obligation() -> None:
    for path in (OPEN_SPEC_CHANGE, OPEN_SPEC_EXPLORE, LIFECYCLE_FINALIZE):
        text = _text(path)
        assert "optional" in text.lower()
        assert "deferred" in text.lower()
    assert "optional or deferred prose creates no routing obligation" in _text(OPEN_SPEC_CHANGE)


def test_explore_keeps_current_action_as_the_only_queue_identity() -> None:
    text = _text(OPEN_SPEC_EXPLORE)
    assert "Mapped Action: Lead / explore-change." in text
    assert "Do not create arbitrary Issues" in text
    assert "Repository application owns" in text
    assert "next Action" in text


def test_lifecycle_does_not_turn_followup_or_archive_prose_into_runtime_state() -> None:
    text = _text(LIFECYCLE_FINALIZE)
    assert "no duplicate Change, PR, lifecycle state, recovery state, or control mailbox" in text
    assert "not a lifecycle obligation" in text
