from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_archive_merge_uses_non_closing_linkage_and_keeps_issue_open() -> None:
    governance = read("agents/AGENTS.md")
    merge_skill = read("agents/skills/merge-pr/SKILL.md")
    lifecycle = read("agents/skills/lifecycle-finalize/SKILL.md")

    assert "final Archive PR" in governance
    assert "non-closing" in governance
    assert "Refs #" in governance
    assert "Archive merge" in merge_skill
    assert "remains open" in merge_skill
    assert "LIFECYCLE_COMPLETE" in lifecycle
    assert "close" in lifecycle
    complete_at = lifecycle.index("LIFECYCLE_COMPLETE")
    close_at = lifecycle.index("close", complete_at)
    assert complete_at < close_at


def test_closed_issue_is_terminal_only_after_lifecycle_complete() -> None:
    governance = read("agents/AGENTS.md")

    assert "closed coordination Issue" in governance
    assert "terminal history" in governance
    assert "LIFECYCLE_COMPLETE" in governance
    assert "premature-close" in governance


def test_normal_path_does_not_require_closed_terminal_pending() -> None:
    governance = read("agents/AGENTS.md")

    assert "normal" in governance
    assert "terminal-pending" in governance
    assert "closed" in governance
    assert "happy path" in governance or "normal path" in governance
