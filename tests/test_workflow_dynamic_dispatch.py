from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"


def _governance() -> str:
    return AGENTS.read_text(encoding="utf-8")


def _normalized_governance() -> str:
    return " ".join(_governance().split())


def test_dispatch_mode_has_one_authoritative_marker() -> None:
    text = _governance()
    markers = re.findall(
        r"^Scheduled-Dispatch-Mode: (fixed-role|workflow-dynamic)$",
        text,
        re.MULTILINE,
    )
    assert markers == ["fixed-role"]


def test_fixed_role_mode_preserves_legacy_role_local_discovery() -> None:
    text = _normalized_governance()
    for required in (
        "fixed-role",
        "legacy externally assigned role",
        "role-local action priority",
        "earlier GitHub `created_at` wins",
        "lower numeric Issue number wins",
    ):
        assert required in text


def test_dynamic_mode_selects_role_from_single_active_workflow() -> None:
    text = _normalized_governance()
    for required in (
        "workflow-dynamic",
        "exactly one active workflow",
        "valid routing tuple",
        "determines the invocation role/action and mapped skill",
        "global urgency",
        "second workflow DAG",
    ):
        assert required in text


def test_dynamic_dispatch_fails_closed_for_invalid_or_multiple_active_workflows() -> None:
    text = _normalized_governance()
    for required in (
        "multiple active workflows",
        "fail closed",
        "invalid routing",
        "MUST NOT guess",
    ):
        assert required in text


def test_invocation_role_is_immutable_after_dynamic_dispatch() -> None:
    text = _normalized_governance()
    for required in (
        "invocation role MUST remain fixed",
        "current invocation MUST end",
        "does not redispatch",
    ):
        assert required in text
