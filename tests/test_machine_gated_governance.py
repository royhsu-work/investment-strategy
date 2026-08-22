"""Machine-gated Scheduled Agent governance regressions for #133 Slice 4D."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
MESSAGES = ROOT / "agents" / "templates" / "messages.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"
CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_mapped_worker_requires_machine_pre_model_dispatch_after_cutover() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "before any mapped model invocation",
        "repository-owned executable precondition",
        "model worker",
        "MUST NOT select or override",
        "requested durable effects",
        "repository-owned application",
        "fresh-reauthorizes",
        "fresh mapped model invocation",
    ):
        assert required in shared


def test_fixed_role_slots_and_issue_comment_transition_commands_are_not_runtime_authority() -> None:
    shared = _normalized(AGENTS)
    for forbidden in (
        "fixed invocation role for the remainder of that run",
        "continue the target action under the fixed invocation role",
    ):
        assert forbidden not in shared
    for required in (
        "dynamic",
        "single scheduled wake",
        "Issue comments",
        "not",
        "authorization",
    ):
        assert required in shared


def test_shared_apply_boundary_owns_durable_messages_and_redispatch() -> None:
    messages = _normalized(MESSAGES)
    for required in (
        "Machine-gated worker/application boundary",
        "invocation-local output",
        "repository-owned application code",
        "fresh-reauthorizes",
        "fresh executable dispatch",
        "fresh mapped model invocation",
    ):
        assert required in messages


def test_lead_workers_consume_machine_identity_and_request_durable_effects() -> None:
    explore = _normalized(EXPLORE)
    change = _normalized(CHANGE)

    for required in (
        "Machine-gated runtime boundary",
        "MUST NOT run `workflow_dispatch.py`",
        "requested durable effect",
        "fresh model invocation",
    ):
        assert required in explore

    for required in (
        "Machine-gated runtime boundary",
        "application-time effect boundary",
        "no durable GitHub write authority",
        "fresh mapped model invocation",
    ):
        assert required in change
