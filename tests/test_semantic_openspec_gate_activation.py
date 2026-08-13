"""Contract coverage for semantic OpenSpec gates and default-branch template activation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
REVIEWER = ROOT / "agents" / "roles" / "reviewer.md"
OPENSPEC_REVIEW = ROOT / "agents" / "skills" / "openspec-review" / "SKILL.md"
IMPLEMENTATION = ROOT / "agents" / "skills" / "implementation" / "SKILL.md"
IMPLEMENTATION_REVIEW = ROOT / "agents" / "skills" / "implementation-review" / "SKILL.md"
ARCHIVE_REVIEW = ROOT / "agents" / "skills" / "archive-review" / "SKILL.md"
MESSAGES = ROOT / "agents" / "templates" / "messages.md"
MIGRATION = ROOT / "agents" / "scheduled-task-migration.md"
README = ROOT / "README.md"


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_mechanical_validation_does_not_implicitly_stale_semantic_openspec_pass() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "Mechanical OpenSpec validation and semantic OpenSpec review applicability",
        "bookkeeping-only OpenSpec revision",
        "does not stale an applicable semantic OpenSpec PASS",
        "Mechanical validation alone does not create semantic acceptance",
        "material semantic OpenSpec change",
    ):
        assert required in shared


def test_reviewer_openspec_uses_semantic_baseline_and_material_cumulative_coverage() -> None:
    reviewer = _normalized(REVIEWER)
    skill = _normalized(OPENSPEC_REVIEW)
    for required in (
        "semantic OpenSpec baseline B",
        "semantic target R",
        "material semantic changes in `(B, R]`",
    ):
        assert required in reviewer or required in skill
    assert "bookkeeping-only revision does not advance or invalidate the semantic baseline" in skill
    assert "Successful mechanical OpenSpec validation is not semantic PASS evidence" in skill


def test_implementation_completion_routes_to_review_without_semantic_change() -> None:
    implementation = _normalized(IMPLEMENTATION)
    for required in (
        "no material semantic OpenSpec change",
        "directly to `Reviewer / review-implementation`",
        "material semantic OpenSpec change",
        "Lead / resolve-question",
        "Reviewer / review-openspec",
    ):
        assert required in implementation


def test_implementation_and_archive_reviews_remain_exact_current_head_gates() -> None:
    for path in (IMPLEMENTATION_REVIEW, ARCHIVE_REVIEW):
        text = _normalized(path)
        assert "exact-current-head gate" in text, path
        assert "semantic OpenSpec bookkeeping exception does not weaken this gate" in text, path


def test_message_templates_activate_only_from_default_branch_merge() -> None:
    for path in (AGENTS, MESSAGES, MIGRATION, README):
        text = _normalized(path)
        for required in (
            "default-branch merge is the activation boundary",
            "unmerged governance PR",
            "review target/input",
            "must not govern its own current invocation",
        ):
            assert required in text, path


def test_pre_activation_legacy_messages_remain_valid_historical_evidence() -> None:
    messages = _normalized(MESSAGES)
    migration = _normalized(MIGRATION)
    for required in (
        "Pre-activation free-form/legacy messages",
        "then-authoritative default-branch governance",
        "not a retroactive template finding",
    ):
        assert required in messages
        assert required in migration

    shared = _normalized(AGENTS)
    for prohibited in (
        "template-version state",
        "semantic-revision classifier service",
        "review-applicability label",
    ):
        assert prohibited in shared or prohibited in migration
    assert "exactly-once mechanism" in shared
