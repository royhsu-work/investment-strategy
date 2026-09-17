"""Contract coverage for shared exception evidence and finalization."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
MESSAGES = ROOT / "agents" / "templates" / "messages.md"
MIGRATION = ROOT / "agents" / "scheduled-task-migration.md"

ROLE_FILES = (
    ROOT / "agents" / "roles" / "lead.md",
    ROOT / "agents" / "roles" / "reviewer.md",
    ROOT / "agents" / "roles" / "executor.md",
)
SKILL_FILES = tuple((ROOT / "agents" / "skills").glob("*/SKILL.md"))


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_shared_exception_contract_preserves_raw_evidence() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "Shared exception capture and invocation finalization",
        "catchable tool, runtime, or execution failure",
        "raw error exactly as observable",
        "selected Issue/Action",
        "attempted operation/tool",
        "whether durable mutation completed",
        "unfinished boundary",
        "EXECUTION_EXCEPTION",
        "uncatchable termination",
    ):
        assert required in shared


def test_exception_message_surface_keeps_raw_and_classification_separate() -> None:
    messages = _normalized(MESSAGES)
    for required in (
        "raw observable error after platform safety redaction",
        "exact Action",
        "attempted operation/tool",
        "whether any mutation completed",
        "separate classification and disposition",
    ):
        assert required in messages


def test_local_recovery_remains_inside_current_authority() -> None:
    shared = _normalized(AGENTS)
    assert "locally recoverable failure is repaired within the current semantic authority" in shared
    assert "immediately actionable" in shared
    assert "An uncatchable termination is reconstructed later" in shared


def test_exception_protocol_is_shared_not_duplicated_into_roles_or_skills() -> None:
    shared = _normalized(AGENTS)
    assert shared.count("Shared exception capture and invocation finalization") == 1
    for path in (*ROLE_FILES, *SKILL_FILES):
        assert "## Shared exception capture and invocation finalization" not in _normalized(path)
    migration = _normalized(MIGRATION)
    assert "bootstrap prompt" in migration
    assert "exception" in migration


def test_shared_contract_rejects_generic_control_machinery() -> None:
    shared = _normalized(AGENTS)
    for prohibited in (
        "second workflow graph",
        "generic orchestration kernel",
        "lock/lease/retry counter",
        "mailbox authority",
    ):
        assert prohibited in shared
