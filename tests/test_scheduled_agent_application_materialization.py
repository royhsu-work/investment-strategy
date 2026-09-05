"""Tests for the single application-owned materialization capability."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from investment_strategy.scheduled_agent_application_materialization import (
    materialization_requires_validation,
    parse_materialization_payload,
)
from investment_strategy.scheduled_agent_effect_contract import (
    allowed_github_mutation_operations,
)
from investment_strategy.scheduled_agent_effects import StagedEffect, supported_effect_guard
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_CHANGE = "restore-lifecycle-finalization-correction-routing"
_BASE = "a" * 40
_BLOB = "b" * 40


def _payload(
    *,
    expected_change: str = "unset",
    issue_number: int = 169,
    files: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "issue_number": issue_number,
        "operation": "application-materialize",
        "expected_change": expected_change,
        "change": _CHANGE,
        "branch": f"agent/{_CHANGE}",
        "base_sha": _BASE,
        "message": "OpenSpec: restore lifecycle finalization correction routing",
        "files": files
        if files is not None
        else [
            {
                "path": f"openspec/changes/{_CHANGE}/proposal.md",
                "blob_sha": _BLOB,
                "expected_sha": None,
            }
        ],
    }


def test_first_change_carrier_is_an_application_materialization_not_a_request_family() -> None:
    source = WorkerRequest(169, "lead", "propose-change")
    request = parse_materialization_payload(_payload(), source)

    assert request.expected_change == "unset"
    assert request.change == _CHANGE
    assert request.pr_number is None
    assert materialization_requires_validation(request, source)
    assert "FORMALIZE_CHANGE_REQUEST" not in Path(
        "src/investment_strategy/scheduled_agent_application_materialization.py"
    ).read_text(encoding="utf-8")


def test_existing_change_materialization_requires_current_pr_and_preserves_expected_shas() -> None:
    source = WorkerRequest(169, "lead", "resolve-question")
    payload = _payload(
        expected_change=_CHANGE,
    )
    payload["pr_number"] = 201
    request = parse_materialization_payload(payload, source)

    assert request.pr_number == 201
    assert request.files[0].expected_sha is None
    assert materialization_requires_validation(request, source)


def test_first_change_materialization_rejects_worker_role_or_existing_identity() -> None:
    with pytest.raises(ValueError, match="only legal for Lead / propose-change"):
        parse_materialization_payload(
            _payload(),
            WorkerRequest(169, "executor", "implement-change"),
        )

    existing = _payload(expected_change=_CHANGE)
    with pytest.raises(ValueError, match="requires an exact PR"):
        parse_materialization_payload(existing, WorkerRequest(169, "lead", "propose-change"))


def test_materialization_effect_is_bounded_to_mapped_actions() -> None:
    source = WorkerRequest(169, "lead", "propose-change")
    effect = StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(_payload()),
    )
    assert supported_effect_guard(source, effect)
    assert "application-materialize" in allowed_github_mutation_operations("lead", "propose-change")
    assert "application-materialize" in allowed_github_mutation_operations(
        "executor", "implement-change"
    )


def test_legacy_application_protocols_are_not_in_runtime_surface() -> None:
    runtime = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "src/investment_strategy/scheduled_agent_application_bridge.py",
            "src/investment_strategy/scheduled_agent_validation_resource.py",
            ".github/workflows/scheduled-agent-application.yml",
        )
    )
    for marker in (
        "FORMALIZE_CHANGE_REQUEST",
        "WORK_PRODUCT_REQUEST",
        "VALIDATION_RESOURCE_REQUEST",
        "Dispatch-Request-Comment-ID",
        "Dispatch-Run-ID",
    ):
        assert marker not in runtime
