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
                "base_commit": {"sha": old_base},
                "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
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
                "base_commit": {"sha": old_base},
                "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
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
                "base_commit": {"sha": old_base},
                "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
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
                "base_commit": {"sha": old_base},
                "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
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


@pytest.mark.parametrize(
    ("overlap", "incomplete_pr_discovery", "expected_error"),
    (
        (True, False, "first-carrier base overlaps"),
        (False, True, "PR discovery is incomplete"),
    ),
)
def test_pending_first_carrier_rejects_overlap_and_incomplete_all_head_pr_discovery(
    monkeypatch: pytest.MonkeyPatch,
    overlap: bool,
    incomplete_pr_discovery: bool,
    expected_error: str,
) -> None:
    old_base = "a" * 40
    current_default = "b" * 40
    carrier_head = "c" * 40
    source = WorkerRequest(234, "lead", "propose-change")
    request = parse_materialization_payload(_payload(issue_number=source.issue_number), source)
    path = request.files[0].path
    pr_discovery_reads = 0
    mutation_calls: list[str] = []

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        **_kwargs: object,
    ) -> object:
        nonlocal pr_discovery_reads
        if method != "GET":
            mutation_calls.append(f"{method} {api_path}")
        if api_path == f"compare/{old_base}...{current_default}":
            return {"status": "ahead", "base_commit": {"sha": old_base}}
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
                "files": [{"filename": path}],
            }
        if api_path.startswith("pulls?"):
            from urllib.parse import parse_qs

            parameters = parse_qs(api_path.partition("?")[2])
            assert parameters.get("state") == ["all"]
            assert parameters.get("head") == [f"royhsu-work:{request.branch}"]
            assert "base" not in parameters
            pr_discovery_reads += 1
            return [{}] * 100 if incomplete_pr_discovery else []
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
        lambda *_args, **_kwargs: {path} if overlap else {"src/unrelated.py"},
    )
    monkeypatch.setattr(
        materialization,
        "_content_sha_at",
        lambda _repo, _token, *, path, revision: _BLOB if revision == carrier_head else None,
    )

    with pytest.raises(RuntimeError, match=expected_error):
        materialization._pending_new_carrier(
            request,
            source,
            repository="royhsu-work/investment-strategy",
            token=_BASE,
            default_branch="main",
            current_revision=current_default,
        )

    assert pr_discovery_reads == (0 if overlap else 1)
    assert mutation_calls == []


@pytest.mark.parametrize(
    "invalid_evidence",
    (
        None,
        "unrelated-path",
        "duplicate-path",
        "missing-base",
        "wrong-base",
        "broken-parent",
        "wrong-last-commit",
        "missing-delta-base",
        "wrong-delta-commit",
        "duplicate-delta-path",
        "unrelated-delta-path",
        "initial-content",
        "missing-last-commit",
        "missing-path",
    ),
)
def test_existing_first_carrier_pr_reuses_exact_intent_commit_after_same_path_updates(
    monkeypatch: pytest.MonkeyPatch,
    invalid_evidence: str | None,
) -> None:
    old_base = "2e00e236f24ba41302c9ba18c685acdf4cebe4ed"
    current_default = "817176cd1b74f8bc04c1e480e0b5335514c5e4ee"
    first_commit = "aad3caedd8db1a4dbba13bc9769d5960b8c8a2fd"
    middle_commit = "23f90022a525413c23e6eb546cda0ba72ea84728"
    carrier_head = "adf0b293fe0d263281e02b79b5dde63f0b2f93e4"
    wrong_head = "f" * 40
    source = WorkerRequest(322, "lead", "propose-change")
    change = "restore-no-work-idle-discovery"
    paths = (
        f"openspec/changes/{change}/proposal.md",
        f"openspec/changes/{change}/design.md",
        f"openspec/changes/{change}/specs/scheduled-agent-workflow/spec.md",
        f"openspec/changes/{change}/tasks.md",
    )
    blobs = tuple(
        sha
        for sha in (
            "1899d3fc4311a07ffb49a81bcd67ff0efb40bac8",
            "bbe2ed3b576f543e6cad29f1575be65f2ec8db0d",
            "c4509de555fd088b6f08ce8ad255226226e25ab2",
            "c9dcf15e6e536985620cc6c8dbccaf6700b46867",
        )
    )
    head_blobs = (
        "6003d898fae7c40c59d08e3023ed131baf41b383",
        "05cfb1579bb4a7c6480f180e9a7e025fdb5fde27",
        "a8ec4b39e5287651ad58cf2b2e0e1a31113cdf06",
        "331dc671ea6fa05c8fb2d40cc3f6dc65a31a6f0a",
    )
    request = MaterializationRequest(
        issue_number=source.issue_number,
        expected_change="unset",
        change=change,
        branch=f"agent/{change}",
        base_sha=old_base,
        message="OpenSpec proposal and design for NO_WORK idle handoff",
        files=tuple(
            WorkProductFile(path, blob, None) for path, blob in zip(paths, blobs, strict=True)
        ),
        pr_number=None,
    )
    repository = "royhsu-work/investment-strategy"
    payload = {
        "issue_number": source.issue_number,
        "operation": "application-materialize",
        "expected_change": "unset",
        "change": change,
        "branch": request.branch,
        "base_sha": old_base,
        "message": request.message,
        "files": [
            {"path": path, "blob_sha": blob, "expected_sha": None}
            for path, blob in zip(paths, blobs, strict=True)
        ],
    }
    pr = {
        "number": 324,
        "state": "open",
        "merged": False,
        "title": f"OpenSpec: {change}",
        "body": f"Formalize OpenSpec change `{change}`.\n\nRefs #322",
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
    default_paths = {
        "src/investment_strategy/issue_comment_bridge.py",
        "src/investment_strategy/scheduled_agent_application_bridge.py",
        "src/investment_strategy/scheduled_agent_application_materialization.py",
        "src/investment_strategy/scheduled_agent_effects.py",
        "tests/test_issue_comment_bridge.py",
        "tests/test_scheduled_agent_application_bridge.py",
        "tests/test_scheduled_agent_application_materialization.py",
        "tests/test_scheduled_agent_effects.py",
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
            commits = [
                {"sha": first_commit, "parents": [{"sha": old_base}]},
                {
                    "sha": middle_commit,
                    "parents": [
                        {"sha": old_base if invalid_evidence == "broken-parent" else first_commit}
                    ],
                },
                {"sha": carrier_head, "parents": [{"sha": middle_commit}]},
            ]
            changed_files = [{"filename": path} for path in paths]
            if invalid_evidence == "unrelated-path":
                changed_files.append({"filename": "src/unrelated.py"})
            if invalid_evidence == "duplicate-path":
                changed_files.append({"filename": paths[0]})
            if invalid_evidence == "missing-base":
                return {
                    "status": "ahead",
                    "ahead_by": 3,
                    "behind_by": 0,
                    "commits": commits,
                    "files": changed_files,
                }
            if invalid_evidence == "wrong-base":
                return {
                    "status": "ahead",
                    "ahead_by": 3,
                    "behind_by": 0,
                    "base_commit": {"sha": "f" * 40},
                    "commits": commits,
                    "files": changed_files,
                }
            if invalid_evidence == "wrong-last-commit":
                commits[-1] = {"sha": wrong_head, "parents": [{"sha": middle_commit}]}
            if invalid_evidence == "missing-last-commit":
                commits = commits[:-1]
            if invalid_evidence in {"wrong-last-commit", "missing-last-commit"}:
                return {
                    "status": "ahead",
                    "ahead_by": 3,
                    "behind_by": 0,
                    "base_commit": {"sha": old_base},
                    "commits": commits,
                    "files": changed_files,
                }
            return {
                "status": "ahead",
                "ahead_by": 3,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "commits": commits,
                "files": changed_files,
            }
        if api_path == f"compare/{old_base}...{first_commit}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "commits": [{"sha": first_commit, "parents": [{"sha": old_base}]}],
                "files": [{"filename": path} for path in paths],
            }
        if api_path == f"compare/{first_commit}...{middle_commit}":
            delta: dict[str, object] = {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": first_commit},
                "commits": [{"sha": middle_commit, "parents": [{"sha": first_commit}]}],
                "files": [{"filename": path} for path in paths],
            }
            if invalid_evidence == "missing-delta-base":
                delta.pop("base_commit")
            elif invalid_evidence == "wrong-delta-commit":
                delta["commits"] = [{"sha": wrong_head, "parents": [{"sha": first_commit}]}]
            elif invalid_evidence == "duplicate-delta-path":
                delta["files"] = [{"filename": paths[0]}, {"filename": paths[0]}]
            elif invalid_evidence == "unrelated-delta-path":
                delta["files"] = [{"filename": "src/unrelated.py"}]
            return delta
        if api_path == f"compare/{middle_commit}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": middle_commit},
                "commits": [{"sha": carrier_head, "parents": [{"sha": middle_commit}]}],
                "files": [{"filename": path} for path in paths[:-1]],
            }
        if api_path == f"compare/{middle_commit}...{wrong_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": middle_commit},
                "commits": [{"sha": wrong_head, "parents": [{"sha": middle_commit}]}],
                "files": [{"filename": path} for path in paths],
            }
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(
        materialization,
        "_comparison_file_paths",
        lambda *_a, **_k: default_paths,
    )
    monkeypatch.setattr(
        materialization,
        "_verify_new_carrier_base_is_empty",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(materialization, "_branch_head", lambda *_a: carrier_head)
    monkeypatch.setattr(materialization, "_pending_source_is_current", lambda *_a: True)
    monkeypatch.setattr(materialization, "_current_default_branch", lambda *_a: "main")
    monkeypatch.setattr(materialization, "_ref_head_sha", lambda *_a: current_default)
    monkeypatch.setattr(materialization, "_matching_prs", lambda *_a: [pr])
    monkeypatch.setattr(
        materialization,
        "_content_sha_at",
        lambda _repo, _token, *, path, revision: (
            blobs[paths.index(path)]
            if revision == first_commit and invalid_evidence != "initial-content"
            else None
            if revision == carrier_head and invalid_evidence == "missing-path" and path == paths[-1]
            else head_blobs[paths.index(path)]
            if revision == carrier_head
            else "d" * 40
        ),
    )

    if invalid_evidence is not None:
        message = {
            "unrelated-path": "PR contains unrelated or missing paths",
            "duplicate-path": "PR path evidence is incomplete",
            "missing-base": "PR lineage is incomplete",
            "wrong-base": "PR lineage is incomplete",
            "broken-parent": "PR ancestry is not linear",
            "wrong-last-commit": "PR head is not the final accepted descendant",
            "missing-delta-base": "PR descendant evidence is incomplete",
            "wrong-delta-commit": "PR descendant evidence is incomplete",
            "duplicate-delta-path": "PR descendant paths are incomplete",
            "unrelated-delta-path": "PR descendant changes unrelated paths",
            "initial-content": "does not resolve requested blobs",
            "missing-last-commit": "PR lineage is incomplete",
            "missing-path": "PR head is missing a manifest path",
        }[invalid_evidence]
        with pytest.raises(RuntimeError, match=message):
            materialization.observe_materialization_target(
                payload,
                source,
                repository=repository,
                token=_BASE,
                current_revision=current_default,
                default_branch="main",
                allow_pending_continuation=True,
            )
        return

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
        pr_number=324,
        change=change,
        validation_required=True,
        branch=request.branch,
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


def test_multi_commit_first_carrier_branch_without_exact_pr_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_base = "2e00e236f24ba41302c9ba18c685acdf4cebe4ed"
    current_default = "6586b5e6b40d84717b73fb7548d778e177fd826f"
    carrier_head = "adf0b293fe0d263281e02b79b5dde63f0b2f93e4"
    source = WorkerRequest(322, "lead", "propose-change")
    request = parse_materialization_payload(
        {
            **_payload(issue_number=source.issue_number),
            "base_sha": old_base,
        },
        source,
    )

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
                "ahead_by": 3,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "commits": [{"sha": "e" * 40}] * 3,
                "files": [{"filename": request.files[0].path}],
            }
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(
        materialization,
        "_comparison_file_paths",
        lambda *_a, **_k: {"src/owner.py"},
    )
    monkeypatch.setattr(
        materialization,
        "_verify_new_carrier_base_is_empty",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(materialization, "_branch_head", lambda *_a: carrier_head)
    monkeypatch.setattr(materialization, "_matching_prs", lambda *_a: [])

    with pytest.raises(RuntimeError, match="not one commit on the base"):
        materialization._pending_new_carrier(
            request,
            source,
            repository="royhsu-work/investment-strategy",
            token=_BASE,
            default_branch="main",
            current_revision=current_default,
        )


@pytest.mark.parametrize(
    ("invalid_evidence", "expected_error"),
    (
        ("missing-base", "not one commit on the base"),
        ("wrong-base", "not one commit on the base"),
        ("wrong-head", "not one commit on the base"),
        ("missing-parent", "not one commit on the base"),
        ("wrong-parent", "not one commit on the base"),
        ("duplicate-path", "file evidence is incomplete"),
        ("missing-path", "contains unrelated paths"),
    ),
)
def test_branch_ref_without_pr_requires_exact_compare_identity_and_manifest(
    monkeypatch: pytest.MonkeyPatch,
    invalid_evidence: str,
    expected_error: str,
) -> None:
    old_base = "a" * 40
    carrier_head = "c" * 40
    path = f"openspec/changes/{_CHANGE}/proposal.md"
    source = WorkerRequest(234, "lead", "propose-change")
    request = MaterializationRequest(
        issue_number=source.issue_number,
        expected_change="unset",
        change=_CHANGE,
        branch=f"agent/{_CHANGE}",
        base_sha=old_base,
        message="Resume the accepted first-carrier intent",
        files=(WorkProductFile(path, _BLOB, None),),
        pr_number=None,
    )
    comparison: dict[str, object] = {
        "status": "ahead",
        "ahead_by": 1,
        "behind_by": 0,
        "base_commit": {"sha": old_base},
        "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
        "files": [{"filename": path}],
    }
    if invalid_evidence == "missing-base":
        comparison.pop("base_commit")
    elif invalid_evidence == "wrong-base":
        comparison["base_commit"] = {"sha": "d" * 40}
    elif invalid_evidence == "wrong-head":
        comparison["commits"] = [{"sha": "d" * 40, "parents": [{"sha": old_base}]}]
    elif invalid_evidence == "missing-parent":
        comparison["commits"] = [{"sha": carrier_head}]
    elif invalid_evidence == "wrong-parent":
        comparison["commits"] = [{"sha": carrier_head, "parents": [{"sha": "d" * 40}]}]
    elif invalid_evidence == "duplicate-path":
        comparison["files"] = [{"filename": path}, {"filename": path}]
    elif invalid_evidence == "missing-path":
        comparison["files"] = []
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
        assert api_path == f"compare/{old_base}...{carrier_head}"
        return comparison

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(
        materialization,
        "_content_sha_at",
        lambda _repo, _token, *, path, revision: (
            _BLOB if path == request.files[0].path and revision == carrier_head else None
        ),
    )

    with pytest.raises(RuntimeError, match=expected_error):
        materialization._verify_revision(
            "royhsu-work/investment-strategy",
            _BASE,
            request,
            carrier_head,
        )

    assert mutation_calls == []


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
