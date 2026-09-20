"""Tests for the single application-owned materialization capability."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_application_materialization as materialization
import investment_strategy.scheduled_agent_validation_resource as validation_resource
from investment_strategy.scheduled_agent_application_materialization import (
    MaterializationRequest,
    _verify_implementation_manifest_freshness,
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


def test_interrupted_carrier_resume_accepts_its_ancestor_base_after_default_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_base = "a" * 40
    current_default = "b" * 40
    carrier_head = "c" * 40
    expected_sha = "d" * 40
    blob_sha = "e" * 40
    path = f"openspec/changes/{_CHANGE}/tasks.md"
    request = MaterializationRequest(
        issue_number=234,
        expected_change=_CHANGE,
        change=_CHANGE,
        branch=f"agent/{_CHANGE}",
        base_sha=old_base,
        message="Resume the accepted implementation intent",
        files=(WorkProductFile(path, blob_sha, expected_sha),),
        pr_number=271,
    )

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        **_kwargs: object,
    ) -> object:
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {"status": "ahead", "behind_by": 0}
        if api_path == f"contents/{path}?ref={old_base}":
            return {"sha": expected_sha}
        if api_path == f"contents/{path}?ref={carrier_head}":
            return {"sha": blob_sha}
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
    _verify_implementation_manifest_freshness(
        request,
        repository="royhsu-work/investment-strategy",
        token=_BASE,
        current_revision=current_default,
        carrier_head=carrier_head,
    )


def test_interrupted_carrier_resume_rejects_a_nonancestor_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_base = "a" * 40
    carrier_head = "c" * 40
    request = MaterializationRequest(
        issue_number=234,
        expected_change=_CHANGE,
        change=_CHANGE,
        branch=f"agent/{_CHANGE}",
        base_sha=old_base,
        message="Reject an unrelated implementation intent",
        files=(),
        pr_number=271,
    )

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        **_kwargs: object,
    ) -> object:
        assert api_path == f"compare/{old_base}...{carrier_head}"
        return {"status": "diverged", "behind_by": 1}

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    with pytest.raises(RuntimeError, match="not an ancestor of carrier"):
        _verify_implementation_manifest_freshness(
            request,
            repository="royhsu-work/investment-strategy",
            token=_BASE,
            current_revision="b" * 40,
            carrier_head=carrier_head,
        )


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


def test_executor_cannot_materialize_noncanonical_repository_level_openspec_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(169, "executor", "implement-change")
    config_file = WorkProductFile(
        path="openspec/specs/repository-governance/spec.md",
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


def test_executor_can_checkpoint_tasks_with_non_openspec_implementation_files() -> None:
    source = WorkerRequest(234, "executor", "implement-change")
    task_file = WorkProductFile(
        f"openspec/changes/{_CHANGE}/tasks.md",
        _BLOB,
        _BLOB,
    )
    implementation_file = WorkProductFile(
        "agents/AGENTS.md",
        _BLOB,
        _BLOB,
    )
    request = MaterializationRequest(
        issue_number=234,
        expected_change=_CHANGE,
        change=_CHANGE,
        branch=f"agent/{_CHANGE}",
        base_sha=_BASE,
        message="checkpoint verified implementation work",
        files=(task_file, implementation_file),
        pr_number=271,
    )

    assert materialization._implementation_manifest_capability_allowed(request, source)

    noncanonical_request = MaterializationRequest(
        issue_number=234,
        expected_change=_CHANGE,
        change=_CHANGE,
        branch=f"agent/{_CHANGE}",
        base_sha=_BASE,
        message="checkpoint with unrelated OpenSpec semantics",
        files=(
            task_file,
            WorkProductFile(
                f"openspec/changes/{_CHANGE}/design.md",
                _BLOB,
                _BLOB,
            ),
        ),
        pr_number=271,
    )

    assert not materialization._implementation_manifest_capability_allowed(
        noncanonical_request,
        source,
    )
