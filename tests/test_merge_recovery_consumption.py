from pathlib import Path

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
    merge_pr = _flat(_read("agents/skills/merge-pr/SKILL.md"))

    assert "implementation merge recovery" in merge_pr
    assert "Lead / finalize-change" in merge_pr
    assert "ARCHIVE_PR_READY" in merge_pr
    assert "archive review" in merge_pr
    assert "MUST NOT route backward" in merge_pr


def test_archive_merge_recovery_respects_terminal_lifecycle_complete() -> None:
    merge_pr = _flat(_read("agents/skills/merge-pr/SKILL.md"))

    assert "Archive merge recovery" in merge_pr
    assert "LIFECYCLE_COMPLETE" in merge_pr
    assert "terminal history" in merge_pr
    assert "MUST NOT recreate or rewrite terminal routing" in merge_pr


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
