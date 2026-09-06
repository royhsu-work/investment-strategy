"""Tests for the single application-owned materialization capability."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_application_materialization as materialization
import investment_strategy.scheduled_agent_validation_resource as validation_resource
from investment_strategy.scheduled_agent_application_materialization import (
    materialization_postcondition,
    materialization_requires_validation,
    parse_materialization_payload,
)
from investment_strategy.scheduled_agent_effect_contract import (
    allowed_github_mutation_operations,
)
from investment_strategy.scheduled_agent_effects import (
    StagedEffect,
    supported_effect_guard,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_validation_resource import (
    ValidationResourceTarget,
    WorkProductFile,
    WorkProductManifest,
    WorkProductPlan,
    apply_work_product,
    work_product_path_allowed,
)

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


def test_lead_openspec_authoring_can_update_only_the_existing_config_owner() -> None:
    for action in ("propose-change", "resolve-question"):
        source = WorkerRequest(169, "lead", action)
        assert work_product_path_allowed(source, _CHANGE, "openspec/config.yaml")
        assert work_product_path_allowed(source, _CHANGE, f"openspec/changes/{_CHANGE}/proposal.md")
        assert not work_product_path_allowed(
            source, _CHANGE, "openspec/specs/repository-governance/spec.md"
        )
        assert not work_product_path_allowed(
            source, _CHANGE, "src/investment_strategy/scheduled_agent_validation_resource.py"
        )
        assert not work_product_path_allowed(source, _CHANGE, "openspec/config.yaml.bak")

        payload = _payload(
            expected_change=_CHANGE,
            files=[
                {
                    "path": "openspec/config.yaml",
                    "blob_sha": _BLOB,
                    "expected_sha": None,
                }
            ],
        )
        payload["pr_number"] = 201
        request = parse_materialization_payload(payload, source)
        assert materialization_requires_validation(request, source)


def test_executor_cannot_materialize_repository_level_openspec_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(169, "executor", "implement-change")
    config_file = WorkProductFile(
        path="openspec/config.yaml",
        blob_sha=_BLOB,
        expected_sha=None,
    )
    manifest = WorkProductManifest(
        branch=f"agent/{_CHANGE}",
        base_sha=_BASE,
        message="bootstrap capability repair",
        files=(config_file,),
    )
    plan = WorkProductPlan(
        should_apply=True,
        source=source,
        pr_number=201,
        expected_change=_CHANGE,
        manifest=manifest,
    )

    monkeypatch.setattr(validation_resource, "_ref_head_sha", lambda *args: _BASE)
    monkeypatch.setattr(validation_resource, "_current_authorized_request", lambda *args: source)

    executor_bookkeeping = validation_resource._is_executor_task_bookkeeping(
        source,
        _CHANGE,
        (config_file,),
    )
    assert executor_bookkeeping is False
    assert validation_resource._review_openspec_required(source) is False
    with pytest.raises(RuntimeError, match="no required OpenSpec review gate"):
        apply_work_product(
            plan,
            repository="royhsu-work/investment-strategy",
            token=_BASE,
            default_branch="main",
            authorization_revision=_BASE,
        )


def test_post_merge_task_materialization_is_exactly_one_default_branch_task_marker() -> None:
    source = WorkerRequest(169, "executor", "implement-change")
    task_path = f"openspec/changes/{_CHANGE}/tasks.md"
    files = (validation_resource.WorkProductFile(task_path, _BLOB, _BASE),)

    assert validation_resource.is_post_merge_task_bookkeeping(
        source,
        _CHANGE,
        "main",
        files,
        default_branch="main",
    )
    assert not validation_resource.is_post_merge_task_bookkeeping(
        source,
        _CHANGE,
        "other",
        files,
        default_branch="main",
    )
    assert not validation_resource.is_post_merge_task_bookkeeping(
        source,
        _CHANGE,
        "main",
        (
            validation_resource.WorkProductFile(
                "openspec/changes/other-change/design.md",
                _BLOB,
                _BASE,
            ),
        ),
        default_branch="main",
    )

    payload = _payload(
        expected_change=_CHANGE,
        files=[
            {
                "path": task_path,
                "blob_sha": _BLOB,
                "expected_sha": _BASE,
            }
        ],
    )
    payload["branch"] = "main"
    payload["pr_number"] = 210
    request = parse_materialization_payload(payload, source)
    assert request.branch == "main"

    payload["files"] = [
        {
            "path": "openspec/changes/other-change/design.md",
            "blob_sha": _BLOB,
            "expected_sha": _BASE,
        }
    ]
    payload["branch"] = f"agent/{_CHANGE}"
    with pytest.raises(ValueError, match="outside Action capability"):
        parse_materialization_payload(payload, source)


def test_post_merge_task_postcondition_accepts_existing_replay_after_intervening_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(180, "executor", "implement-change")
    current_revision = "c" * 40
    task_path = f"openspec/changes/{_CHANGE}/tasks.md"
    payload = _payload(
        expected_change=_CHANGE,
        issue_number=180,
        files=[
            {
                "path": task_path,
                "blob_sha": _BLOB,
                "expected_sha": _BASE,
            }
        ],
    )
    payload["branch"] = "main"
    payload["message"] = f"Reconcile implementation-ready task marker for {_CHANGE}"
    payload["pr_number"] = 210
    target = ValidationResourceTarget(
        repository="royhsu-work/investment-strategy",
        revision=current_revision,
        correlation="effect-request-180",
        pr_number=210,
        change=_CHANGE,
        validation_required=False,
    )

    monkeypatch.setattr(materialization, "_current_default_branch", lambda *args: "main")
    monkeypatch.setattr(materialization, "_ref_head_sha", lambda *args: current_revision)

    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        assert repository == "royhsu-work/investment-strategy"
        assert token == _BASE
        assert api_path == "issues/180"
        return {"state": "open", "body": f"Change: {_CHANGE}\n"}

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(
        materialization,
        "_revision_matches_manifest",
        lambda *args, **kwargs: False,
    )
    observed: list[tuple[str, str, str, str, str]] = []

    def fake_task_reconciliation(
        repository: str,
        token: str,
        *,
        base_sha: str,
        revision: str,
        file: WorkProductFile,
    ) -> bool:
        observed.append((repository, token, base_sha, revision, file.path))
        return True

    monkeypatch.setattr(
        materialization,
        "_task_marker_reconciliation_is_present",
        fake_task_reconciliation,
    )

    assert materialization_postcondition(
        payload,
        source,
        repository="royhsu-work/investment-strategy",
        token=_BASE,
        current_revision=current_revision,
        default_branch="main",
        target=target,
    )
    assert observed == [
        (
            "royhsu-work/investment-strategy",
            _BASE,
            _BASE,
            current_revision,
            task_path,
        )
    ]
