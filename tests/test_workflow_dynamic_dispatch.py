from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
OPEN_SPEC_CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _governance() -> str:
    return _read(AGENTS)


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_dispatch_mode_has_one_authoritative_marker() -> None:
    text = _governance()
    markers = re.findall(
        r"^Scheduled-Dispatch-Mode: (fixed-role|workflow-dynamic)$",
        text,
        re.MULTILINE,
    )
    assert markers == ["fixed-role"]


def test_fixed_role_mode_preserves_legacy_role_local_discovery() -> None:
    text = _normalized(AGENTS)
    for required in (
        "fixed-role",
        "legacy externally assigned role",
        "role-local action priority",
        "earlier GitHub `created_at` wins",
        "lower numeric Issue number wins",
    ):
        assert required in text


def test_dynamic_mode_selects_role_from_single_active_workflow() -> None:
    text = _normalized(AGENTS)
    for required in (
        "workflow-dynamic",
        "Exactly one active workflow",
        "valid routing tuple",
        "determines the invocation role/action and mapped skill",
        "global urgency",
        "second workflow DAG",
    ):
        assert required in text


def test_dynamic_dispatch_fails_closed_for_invalid_or_multiple_active_workflows() -> None:
    text = _normalized(AGENTS)
    for required in (
        "multiple active workflows",
        "fail closed",
        "invalid routing",
        "MUST NOT guess",
    ):
        assert required in text


def test_invocation_role_is_immutable_after_dynamic_dispatch() -> None:
    text = _normalized(AGENTS)
    for required in (
        "invocation role MUST remain fixed",
        "current invocation MUST end",
        "does not redispatch",
    ):
        assert required in text


def test_change_identity_defines_single_active_workflow_and_queued_proposals() -> None:
    text = _normalized(AGENTS)
    for required in (
        "persisted non-`unset` `Change:` identity",
        "active workflow",
        "at most one",
        "`Change: unset`",
        "queued pre-activation",
        "MUST NOT count as an active workflow",
    ):
        assert required in text


def test_queued_activation_is_deterministic_and_refuses_second_active_change() -> None:
    text = _normalized(AGENTS)
    for required in (
        "MUST NOT activate a queued proposal while another active workflow exists",
        "earliest GitHub `created_at`",
        "lower Issue number",
        "persists its immutable Change identity",
    ):
        assert required in text


def test_activation_overlap_uses_first_valid_write_and_stale_run_termination() -> None:
    shared = _normalized(AGENTS)
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "first-valid-write-wins",
        "re-read",
        "stale",
        "lock",
        "claim",
        "lease",
        "heartbeat",
    ):
        assert required in shared
    for required in (
        "reconstruct active workflow state before persisting an unset Change identity",
        "first valid activation",
        "re-read durable state",
        "stop as stale",
    ):
        assert required in change
