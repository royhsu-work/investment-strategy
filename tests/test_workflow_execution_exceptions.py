"""Contract coverage for shared exception capture and invocation finalization."""

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


def test_shared_exception_capture_contract_applies_to_all_roles_and_actions() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "Shared exception capture and invocation finalization",
        "all three Scheduled Agent roles and all ten normal actions",
        "catchable tool, runtime, and execution failures",
        "persist one canonical `EXECUTION_EXCEPTION`",
        "before relying on a summarized interpretation",
        "raw error message exactly as it was observable",
        "existing safety redaction",
        "selected role/action",
        "attempted operation/tool",
        "relevant revision/base",
        "durable mutation",
        "unfinished work boundary",
        "UNCLASSIFIED_EXECUTION_EXCEPTION",
        "paraphrase or classification-only summary",
    ):
        assert required in shared


def test_canonical_exception_template_keeps_raw_observation_separate() -> None:
    messages = _normalized(MESSAGES)
    for required in (
        "raw observable error exactly as returned",
        "existing platform safety redaction",
        "separate classification",
        "separate disposition",
        "UNCLASSIFIED_EXECUTION_EXCEPTION",
        "attempted operation/tool",
        "relevant revision/base",
        "durable mutation",
        "unfinished work boundary",
        "must not be replaced by a paraphrase or classification-only summary",
    ):
        assert required in messages


def test_locally_recoverable_exception_continues_same_invocation() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "legally recovered within the same authority",
        "local recovery is legal and immediately actionable",
        "perform that recovery",
        "continue the selected action",
        "same invocation",
        "MUST NOT become a voluntary yield point",
    ):
        assert required in shared


def test_nonlocal_catchable_failure_converges_to_lead_handoff() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "preserve completed durable work",
        "action-defined legal blocked/disposition result",
        "`Lead / resolve-question`",
        "captured raw evidence",
        "complete any required routing handoff",
        "canonical `HANDOFF`",
        "MUST NOT invent one universal blocked-result enum",
    ):
        assert required in shared


def test_uncatchable_termination_relies_on_later_reconstruction_without_fabrication() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "truly uncatchable hard termination",
        "later reconstruction",
        "MUST NOT fabricate `EXECUTION_EXCEPTION`",
        "normal at-least-once",
    ):
        assert required in shared


def test_exception_protocol_is_shared_not_copied_into_roles_or_skills() -> None:
    shared = _normalized(AGENTS)
    assert shared.count("Shared exception capture and invocation finalization") == 1

    for path in (*ROLE_FILES, *SKILL_FILES):
        text = _normalized(path)
        assert "## Shared exception capture and invocation finalization" not in text, path

    migration = _normalized(MIGRATION)
    for required in (
        "bootstrap",
        "must not duplicate",
        "exception",
        "finalization",
    ):
        assert required in migration


def test_shared_contract_rejects_generic_fault_retry_machinery() -> None:
    shared = _normalized(AGENTS)
    for prohibited in (
        "universal blocked-result enum",
        "generic retry engine",
        "failure-state machine",
        "retry counter",
        "automatic fault classifier",
        "hidden execution status",
    ):
        assert prohibited in shared
