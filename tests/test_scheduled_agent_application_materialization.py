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
from investment_strategy.scheduled_agent_carrier import CarrierRequired
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


def test_initial_carrier_resume_after_disjoint_default_advance_is_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_base = "a" * 40
    current_default = "b" * 40
    carrier_head = "c" * 40
    blob_sha = _BLOB
    path = f"openspec/changes/{_CHANGE}/proposal.md"
    request = MaterializationRequest(
        issue_number=234,
        expected_change="unset",
        change=_CHANGE,
        branch=f"agent/{_CHANGE}",
        base_sha=old_base,
        message="OpenSpec proposal",
        files=(WorkProductFile(path, blob_sha, None),),
        pr_number=None,
    )
    repository = "royhsu-work/investment-strategy"
    pr = {
        "number": 271,
        "state": "open",
        "merged": False,
        "title": f"OpenSpec: {_CHANGE}",
        "body": "Formalize the change.\n\nRefs #234",
        "head": {
            "ref": request.branch,
            "sha": carrier_head,
            "repo": {"full_name": repository},
        },
        "base": {
            "ref": "main",
            "sha": old_base,
            "repo": {"full_name": repository},
        },
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        **_kwargs: object,
    ) -> object:
        if api_path == f"compare/{old_base}...{current_default}":
            return {"status": "ahead", "base_commit": {"sha": old_base}}
        if api_path == f"git/ref/heads/{request.branch}":
            return {"object": {"sha": carrier_head}}
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "commits": [{"sha": carrier_head}],
                "files": [{"filename": path}],
            }
        if api_path == f"contents/{path}?ref={carrier_head}":
            return {"sha": blob_sha}
        if api_path == f"contents/{path}?ref={old_base}":
            return None
        if api_path.startswith(f"contents/openspec/changes/{_CHANGE}?"):
            return None
        if api_path.startswith("pulls?"):
            return [pr]
        if api_path.startswith(f"contents/openspec/changes/{_CHANGE}?"):
            return None
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
    monkeypatch.setattr(
        materialization,
        "_comparison_file_paths",
        lambda *_args, **_kwargs: {"src/investment_strategy/repair.py"},
    )

    revision, pr_number = materialization._pending_new_carrier(
        request,
        WorkerRequest(234, "lead", "propose-change"),
        repository=repository,
        token=_BASE,
        default_branch="main",
        current_revision=current_default,
    )

    assert (revision, pr_number) == (carrier_head, 271)


def test_first_carrier_postcondition_uses_the_canonical_disjoint_continuation_observer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_base = "a" * 40
    current_default = "b" * 40
    carrier_head = "c" * 40
    blob_sha = _BLOB
    repository = "royhsu-work/investment-strategy"
    source = WorkerRequest(234, "lead", "propose-change")
    payload = _payload(issue_number=source.issue_number)
    path = f"openspec/changes/{_CHANGE}/proposal.md"
    issue = {"state": "open", "body": "Change: unset\n"}
    pr = {
        "number": 271,
        "state": "open",
        "merged": False,
        "title": f"OpenSpec: {_CHANGE}",
        "body": "Formalize the change.\n\nRefs #234",
        "head": {
            "ref": f"agent/{_CHANGE}",
            "sha": carrier_head,
            "repo": {"full_name": repository},
        },
        "base": {
            "ref": "main",
            "sha": old_base,
            "repo": {"full_name": repository},
        },
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        **_kwargs: object,
    ) -> object:
        if api_path == f"issues/{source.issue_number}":
            return issue
        if api_path == f"pulls/{pr['number']}":
            return pr
        if api_path.startswith("pulls?"):
            return [pr]
        if api_path.startswith(f"contents/openspec/changes/{_CHANGE}?"):
            return None
        if api_path == f"compare/{old_base}...{current_default}":
            return {
                "status": "ahead",
                "base_commit": {"sha": old_base},
            }
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "commits": [{"sha": carrier_head}],
                "files": [{"filename": path}],
            }
        if api_path == f"contents/{path}?ref={carrier_head}":
            return {"sha": blob_sha}
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main":
            return {"object": {"sha": current_default}}
        if api_path == f"git/ref/heads/agent/{_CHANGE}":
            return {"object": {"sha": carrier_head}}
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(materialization, "_pending_source_is_current", lambda *_args: True)
    monkeypatch.setattr(materialization, "_current_default_branch", lambda *_args: "main")
    monkeypatch.setattr(materialization, "_ref_head_sha", lambda *_args: current_default)
    monkeypatch.setattr(materialization, "_branch_head", lambda *_args: carrier_head)
    monkeypatch.setattr(
        materialization,
        "_comparison_file_paths",
        lambda *_args, **_kwargs: {"src/unrelated.py"},
    )
    monkeypatch.setattr(
        materialization,
        "_content_sha_at",
        lambda _repo, _token, *, path, revision: blob_sha if revision == carrier_head else None,
    )

    target = materialization.observe_materialization_target(
        payload,
        source,
        repository=repository,
        token=_BASE,
        current_revision=current_default,
        default_branch="main",
        allow_pending_continuation=True,
    )

    assert target == ValidationResourceTarget(
        repository=repository,
        revision=carrier_head,
        correlation=f"effect-request-{source.issue_number}",
        pr_number=271,
        change=_CHANGE,
        validation_required=True,
        branch=f"agent/{_CHANGE}",
    )
    assert materialization.materialization_postcondition(
        payload,
        source,
        repository=repository,
        token=_BASE,
        current_revision=current_default,
        default_branch="main",
        target=target,
        allow_pending_continuation=True,
    )


def test_pending_first_carrier_with_missing_pr_emits_only_current_main_pr_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_base = "a" * 40
    current_default = "b" * 40
    carrier_head = "c" * 40
    blob_sha = _BLOB
    source = WorkerRequest(234, "lead", "propose-change")
    payload = _payload(issue_number=source.issue_number)
    path = f"openspec/changes/{_CHANGE}/proposal.md"
    issue = {"state": "open", "body": "Change: unset\n"}
    mutation_calls: list[str] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        **_kwargs: object,
    ) -> object:
        if method != "GET":
            mutation_calls.append(f"{method} {api_path}")
        if api_path == f"issues/{source.issue_number}":
            return issue
        if api_path == f"compare/{old_base}...{current_default}":
            return {"status": "ahead", "base_commit": {"sha": old_base}}
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "commits": [{"sha": carrier_head}],
                "files": [{"filename": path}],
            }
        if api_path.startswith("pulls?"):
            return []
        if api_path.startswith(f"contents/openspec/changes/{_CHANGE}?"):
            return None
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(materialization, "_pending_source_is_current", lambda *_args: True)
    monkeypatch.setattr(materialization, "_current_default_branch", lambda *_args: "main")
    monkeypatch.setattr(materialization, "_ref_head_sha", lambda *_args: current_default)
    monkeypatch.setattr(materialization, "_branch_head", lambda *_args: carrier_head)
    monkeypatch.setattr(
        materialization,
        "_comparison_file_paths",
        lambda *_args, **_kwargs: {"src/unrelated.py"},
    )
    monkeypatch.setattr(
        materialization,
        "_content_sha_at",
        lambda _repo, _token, *, path, revision: blob_sha if revision == carrier_head else None,
    )

    with pytest.raises(CarrierRequired) as raised:
        materialization.apply_materialization(
            payload,
            source,
            repository="royhsu-work/investment-strategy",
            token=_BASE,
            current_revision=current_default,
            default_branch="main",
            allow_pending_continuation=True,
        )

    assert raised.value.plan.operation == "pull-request-create"
    assert raised.value.plan.authorization_revision == current_default
    assert raised.value.plan.target == {
        "head_ref": f"agent/{_CHANGE}",
        "base_ref": "main",
        "repository": "royhsu-work/investment-strategy",
    }
    assert raised.value.plan.expected["head_sha"] == carrier_head
    assert raised.value.plan.expected["existing_pr_count"] == 0
    assert raised.value.plan.expected["base_sha"] == current_default
    assert raised.value.plan.force is False
    assert mutation_calls == []


@pytest.mark.parametrize("pr_count", (1, 2))
def test_pending_first_carrier_rejects_wrong_or_duplicate_pr_carriers(
    monkeypatch: pytest.MonkeyPatch,
    pr_count: int,
) -> None:
    old_base = "a" * 40
    current_default = "b" * 40
    carrier_head = "c" * 40
    blob_sha = _BLOB
    source = WorkerRequest(234, "lead", "propose-change")
    request = parse_materialization_payload(_payload(issue_number=source.issue_number), source)
    path = request.files[0].path
    wrong_base_pr = {
        "number": 271,
        "state": "open",
        "merged": False,
        "title": f"OpenSpec: {_CHANGE}",
        "body": "Formalize the change.\n\nRefs #234",
        "head": {
            "ref": request.branch,
            "sha": carrier_head,
            "repo": {"full_name": "royhsu-work/investment-strategy"},
        },
        "base": {
            "ref": "release",
            "sha": old_base,
            "repo": {"full_name": "royhsu-work/investment-strategy"},
        },
    }

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        **_kwargs: object,
    ) -> object:
        if api_path == f"compare/{old_base}...{current_default}":
            return {"status": "ahead", "base_commit": {"sha": old_base}}
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "commits": [{"sha": carrier_head}],
                "files": [{"filename": path}],
            }
        if api_path.startswith("pulls?"):
            from urllib.parse import parse_qs

            parameters = parse_qs(api_path.partition("?")[2])
            assert "base" not in parameters
            assert parameters.get("head") == [f"royhsu-work:{request.branch}"]
            return [wrong_base_pr] * pr_count
        if api_path.startswith(f"contents/openspec/changes/{_CHANGE}?"):
            return None
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(
        materialization,
        "_comparison_file_paths",
        lambda *_args, **_kwargs: {"src/unrelated.py"},
    )
    monkeypatch.setattr(
        materialization,
        "_content_sha_at",
        lambda _repo, _token, *, path, revision: blob_sha if revision == carrier_head else None,
    )
    monkeypatch.setattr(materialization, "_branch_head", lambda *_args: carrier_head)

    with pytest.raises(RuntimeError, match="pending carrier"):
        materialization._pending_new_carrier(
            request,
            source,
            repository="royhsu-work/investment-strategy",
            token=_BASE,
            default_branch="main",
            current_revision=current_default,
        )


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
