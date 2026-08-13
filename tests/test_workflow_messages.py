"""Contract coverage for canonical workflow messages and durable handoff recovery."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESSAGES = ROOT / "agents" / "templates" / "messages.md"
AGENTS = ROOT / "agents" / "AGENTS.md"
MIGRATION = ROOT / "agents" / "scheduled-task-migration.md"

ROLE_FILES = (
    ROOT / "agents" / "roles" / "lead.md",
    ROOT / "agents" / "roles" / "reviewer.md",
    ROOT / "agents" / "roles" / "executor.md",
)
SKILL_FILES = (
    ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md",
    ROOT / "agents" / "skills" / "openspec-review" / "SKILL.md",
    ROOT / "agents" / "skills" / "implementation" / "SKILL.md",
    ROOT / "agents" / "skills" / "implementation-review" / "SKILL.md",
    ROOT / "agents" / "skills" / "lifecycle-finalize" / "SKILL.md",
    ROOT / "agents" / "skills" / "archive-review" / "SKILL.md",
    ROOT / "agents" / "skills" / "merge-pr" / "SKILL.md",
)

CANONICAL_TYPES = (
    "ACTION_RESULT",
    "REVIEW_RESULT",
    "SLICE_CHECKPOINT",
    "MERGE_AUTHORIZATION",
    "MERGE_RESULT",
    "HANDOFF",
    "HUMAN_DECISION_REQUIRED",
    "EXECUTION_EXCEPTION",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _template_section(message_type: str) -> str:
    text = _read(MESSAGES)
    match = re.search(
        rf"^## `{message_type}`\n(?P<body>.*?)(?=^## `|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, message_type
    return " ".join(match.group("body").split())


def test_shared_message_source_defines_exactly_eight_canonical_types() -> None:
    text = _read(MESSAGES)
    headings = tuple(re.findall(r"^## `([A-Z_]+)`$", text, flags=re.MULTILINE))
    assert headings == CANONICAL_TYPES

    normalized = " ".join(text.split())
    for required in (
        "common workflow envelope",
        "Workflow",
        "Change",
        "Action",
        "Result",
        "Revision",
        "presentation/evidence shape",
        "does not redefine routing",
        "parser-dependent message bus",
        "JSON/YAML runtime schema",
        "template engine",
        "hidden workflow state",
    ):
        assert required in normalized

    assert "LIFECYCLE_JOURNAL" not in headings


def test_canonical_templates_preserve_event_specific_evidence() -> None:
    expected_fields = {
        "ACTION_RESULT": ("Result", "Revision", "evidence", "next"),
        "REVIEW_RESULT": ("reviewed revision", "gate evidence", "findings", "next owner"),
        "SLICE_CHECKPOINT": (
            "Slice/task",
            "verified revision",
            "task-marker/checkpoint revision",
            "VERIFY/gate",
            "remaining work",
            "routing",
        ),
        "MERGE_AUTHORIZATION": ("authorized revision", "gate evidence", "merge preconditions"),
        "MERGE_RESULT": ("PR", "exact head", "merge commit", "result", "next"),
        "HANDOFF": (
            "From",
            "To",
            "triggering result",
            "fresh-read source routing",
            "routing mutation",
            "observed target routing",
        ),
        "HUMAN_DECISION_REQUIRED": (
            "requested Human response",
            "options",
            "impact",
            "risk/trade-off",
            "Lead recommendation",
        ),
        "EXECUTION_EXCEPTION": (
            "selected role/action",
            "operation/tool",
            "relevant revision/base",
            "durable mutation",
            "unfinished work boundary",
            "raw observable error",
            "classification",
            "disposition",
            "UNCLASSIFIED_EXECUTION_EXCEPTION",
        ),
    }

    for message_type, fields in expected_fields.items():
        section = _template_section(message_type)
        for field in fields:
            assert field in section, f"{message_type}: {field}"


def test_roles_and_skills_reference_shared_templates_without_private_template_bodies() -> None:
    for path in (*ROLE_FILES, *SKILL_FILES):
        text = _read(path)
        normalized = " ".join(text.split())
        assert "agents/templates/messages.md" in normalized, path
        assert not re.search(r"^## `(ACTION_RESULT|REVIEW_RESULT|SLICE_CHECKPOINT|MERGE_AUTHORIZATION|MERGE_RESULT|HANDOFF|HUMAN_DECISION_REQUIRED|EXECUTION_EXCEPTION)`$", text, re.MULTILINE), path


def test_intermediate_progress_and_status_noise_are_not_supported_message_types() -> None:
    headings = set(re.findall(r"^## `([A-Z_]+)`$", _read(MESSAGES), flags=re.MULTILINE))
    assert headings == set(CANONICAL_TYPES)
    for unsupported in (
        "RED_PROGRESS",
        "GREEN_PROGRESS",
        "REFACTOR_PROGRESS",
        "TEST_TRIGGER",
        "COMPATIBILITY_CORRECTION",
        "LEAD_PROGRESS_POLL",
        "NO_HUMAN_ACTION_REQUIRED",
        "LIFECYCLE_JOURNAL",
    ):
        assert unsupported not in headings


def test_result_evidence_does_not_complete_required_handoff() -> None:
    shared = _normalized(AGENTS)
    implementation = _normalized(ROOT / "agents" / "skills" / "implementation" / "SKILL.md")
    reviewer = _normalized(ROOT / "agents" / "skills" / "openspec-review" / "SKILL.md")

    for required in (
        "result evidence does not by itself complete a required routing handoff",
        "persist result + revision-aware evidence",
        "fresh-read source routing",
        "mutate routing to the target tuple",
        "observe successful routing mutation",
        "persist canonical `HANDOFF`",
        "HANDOFF follows successful routing mutation",
    ):
        assert required in shared

    for text in (implementation, reviewer):
        for required in (
            "already-durable result",
            "source routing still matches",
            "perform only the missing routing mutation",
            "persist canonical `HANDOFF`",
            "do not repeat",
        ):
            assert required in text


def test_typed_boundary_message_satisfies_lifecycle_journal_without_duplicate_meta_comment() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "canonical typed message",
        "satisfies the required lifecycle journal",
        "MUST NOT add a duplicate generic `LIFECYCLE_JOURNAL`",
        "HANDOFF",
        "MERGE_RESULT",
        "ACTION_RESULT",
        "HUMAN_DECISION_REQUIRED",
    ):
        assert required in shared


def test_human_delivery_is_lead_only_decision_required_and_other_wakes_are_silent() -> None:
    shared = _normalized(AGENTS)
    migration = _normalized(MIGRATION)

    for required in (
        "only Lead",
        "`HUMAN_DECISION_REQUIRED`",
        "Human-facing delivery-eligible",
        "Reviewer/Executor",
        "`EXECUTION_EXCEPTION`",
        "ordinary Lead",
        "repository-durable only",
    ):
        assert required in shared

    for required in (
        "ordinary wakes are Human-silent",
        "only",
        "`HUMAN_DECISION_REQUIRED`",
        "associated-conversation",
        "external product configuration",
        "No Human action is required",
        "must not emit",
    ):
        assert required in migration
