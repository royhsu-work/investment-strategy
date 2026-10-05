"""Tests for the single application-owned materialization capability."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

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
_TOKEN = "test-token"  # noqa: S105


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


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    (
        (None, None),
        ("ref-mismatch", "PR/ref head identity is stale"),
        ("duplicate-pr", "carrier identity is ambiguous"),
        ("missing-default-history", "omits authorized default history"),
        ("unproven-historical-base", "comparison is not an ancestor"),
        ("stale-open-base", "authorization base is stale"),
    ),
)
def test_existing_change_observer_reconstructs_only_exact_current_carrier(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    failure: str | None,
    expected_error: str | None,
) -> None:
    accepted = _accepted_git_carrier(proof_git)
    if failure == "ref-mismatch":
        proof_git.failure = "wrong-ref"
    elif failure == "duplicate-pr":
        proof_git.failure = "duplicate-pr"
    elif failure in {"missing-default-history", "unproven-historical-base"}:
        api = proof_git.api

        def incomplete(repository: str, token: str, path: str, **kwargs: object) -> object:
            response = api(repository, token, path, **kwargs)
            if path.startswith("compare/"):
                response = dict(cast(dict[str, object], response))
                response["base_commit"] = {"sha": "0" * 40}
            return response

        monkeypatch.setattr(materialization, "_github_json", incomplete)
    elif failure == "stale-open-base":
        # A durable accepted witness survives a legal disjoint main advance.
        proof_git.main = proof_git.commit({"README.md": "advance"}, "Main", (proof_git.main,))
    if failure not in {None, "stale-open-base"}:
        with pytest.raises(RuntimeError):
            _observe_git(proof_git)
    else:
        target = _observe_git(proof_git)
        assert target.revision == accepted
    assert proof_git.mutations == []


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
        if api_path == f"compare/{old_base}...{old_base}":
            return {
                "status": "identical",
                "ahead_by": 0,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "files": [],
            }
        if api_path == f"compare/{old_base}...{current_default}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "files": [{"filename": "src/investment_strategy/repair.py", "status": "modified"}],
            }
        if api_path == f"git/ref/heads/{request.branch}":
            return {"object": {"sha": carrier_head}}
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
                "files": [{"filename": path, "status": "added"}],
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
    proof_git: _ProofGitRepository,
) -> None:
    _first_git_intent(proof_git)
    accepted = _accepted_git_carrier(proof_git)
    proof_git.main = proof_git.commit({"README.md": "advance"}, "Main", (proof_git.main,))
    target = _observe_git(proof_git)
    assert target.revision == accepted
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


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
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "files": [{"filename": "src/unrelated.py", "status": "modified"}],
            }
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
                "files": [{"filename": path, "status": "added"}],
            }
        if api_path.startswith("pulls?"):
            return []
        if api_path.startswith(f"contents/openspec/changes/{_CHANGE}?"):
            return None
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
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
        materialization._construct_materialization(
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
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "files": [{"filename": "src/unrelated.py", "status": "modified"}],
            }
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
                "files": [{"filename": path, "status": "added"}],
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
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
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
            changed_path = path if overlap else "src/unrelated.py"
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "files": [{"filename": changed_path, "status": "modified"}],
            }
        if api_path == f"compare/{old_base}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "commits": [{"sha": carrier_head, "parents": [{"sha": old_base}]}],
                "files": [{"filename": path, "status": "added"}],
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
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
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
def test_first_carrier_lineage_primitive_preserves_exact_intent_after_same_path_updates(
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
            return {
                "status": "ahead",
                "ahead_by": 12,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "files": [
                    {"filename": path, "status": "modified"} for path in sorted(default_paths)
                ],
            }
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
            changed_files = [{"filename": path, "status": "added"} for path in paths]
            if invalid_evidence == "unrelated-path":
                changed_files.append({"filename": "src/unrelated.py", "status": "added"})
            if invalid_evidence == "duplicate-path":
                changed_files.append({"filename": paths[0], "status": "modified"})
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
                "files": [{"filename": path, "status": "added"} for path in paths],
            }
        if api_path == f"compare/{first_commit}...{middle_commit}":
            delta: dict[str, object] = {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": first_commit},
                "commits": [{"sha": middle_commit, "parents": [{"sha": first_commit}]}],
                "files": [{"filename": path, "status": "modified"} for path in paths],
            }
            if invalid_evidence == "missing-delta-base":
                delta.pop("base_commit")
            elif invalid_evidence == "wrong-delta-commit":
                delta["commits"] = [{"sha": wrong_head, "parents": [{"sha": first_commit}]}]
            elif invalid_evidence == "duplicate-delta-path":
                delta["files"] = [
                    {"filename": paths[0], "status": "modified"},
                    {"filename": paths[0], "status": "modified"},
                ]
            elif invalid_evidence == "unrelated-delta-path":
                delta["files"] = [{"filename": "src/unrelated.py", "status": "added"}]
            return delta
        if api_path == f"compare/{middle_commit}...{carrier_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": middle_commit},
                "commits": [{"sha": carrier_head, "parents": [{"sha": middle_commit}]}],
                "files": [{"filename": path, "status": "modified"} for path in paths[:-1]],
            }
        if api_path == f"compare/{middle_commit}...{wrong_head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": middle_commit},
                "commits": [{"sha": wrong_head, "parents": [{"sha": middle_commit}]}],
                "files": [{"filename": path, "status": "modified"} for path in paths],
            }
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
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
        with pytest.raises(RuntimeError):
            materialization._verify_existing_pr_revision_lineage(
                repository, _BASE, request, carrier_head
            )
        return
    materialization._verify_existing_pr_revision_lineage(repository, _BASE, request, carrier_head)


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
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": old_base},
                "files": [{"filename": "src/unrelated.py", "status": "modified"}],
            }
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
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
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
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
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


def test_completed_carrier_is_not_a_prospective_write_preimage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_base, carrier_head = "a" * 40, "c" * 40
    path = f"openspec/changes/{_CHANGE}/tasks.md"
    request = MaterializationRequest(
        234,
        _CHANGE,
        _CHANGE,
        f"agent/{_CHANGE}",
        old_base,
        "Accepted implementation",
        (WorkProductFile(path, "e" * 40, "d" * 40),),
        271,
    )

    def read(_repository: str, _token: str, api_path: str, **_kwargs: object) -> object:
        if api_path.startswith("compare/"):
            return {"status": "ahead", "behind_by": 0}
        if api_path == f"contents/{path}?ref={carrier_head}":
            return {"sha": "e" * 40}
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", read)
    monkeypatch.setattr(validation_resource, "_github_json", read)
    with pytest.raises(RuntimeError, match="expected content is stale"):
        _verify_implementation_manifest_freshness(
            request,
            repository="royhsu-work/investment-strategy",
            token=_BASE,
            current_revision="b" * 40,
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
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
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


def test_pending_first_carrier_rejects_incomplete_default_ancestry_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_base = "a" * 40
    current_default = "b" * 40
    carrier_head = "c" * 40
    source = WorkerRequest(234, "lead", "propose-change")
    request = parse_materialization_payload(_payload(issue_number=source.issue_number), source)
    path = request.files[0].path

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
                "files": [{"filename": path, "status": "added"}],
            }
        if api_path.startswith("pulls?"):
            return []
        if api_path.startswith("contents/openspec/changes/"):
            return None
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
    monkeypatch.setattr(
        materialization,
        "_comparison_file_paths",
        lambda *_args, **_kwargs: {"src/unrelated.py"},
    )
    monkeypatch.setattr(
        materialization,
        "_content_sha_at",
        lambda _repo, _token, *, path, revision: _BLOB if revision == carrier_head else None,
    )
    monkeypatch.setattr(materialization, "_branch_head", lambda *_args: carrier_head)

    with pytest.raises(RuntimeError, match="first-carrier base is not an ancestor"):
        materialization._pending_new_carrier(
            request,
            source,
            repository="royhsu-work/investment-strategy",
            token=_BASE,
            default_branch="main",
            current_revision=current_default,
        )


@pytest.mark.parametrize(
    ("status", "previous_filename"),
    ((None, None), ("copied", None), ("renamed", "src/unrelated.py")),
    ids=("missing-status", "unknown-status", "rename-into-manifest"),
)
def test_first_carrier_revision_rejects_incomplete_or_renamed_file_evidence(
    monkeypatch: pytest.MonkeyPatch,
    status: str | None,
    previous_filename: str | None,
) -> None:
    source = WorkerRequest(234, "lead", "propose-change")
    request = parse_materialization_payload(_payload(issue_number=source.issue_number), source)
    carrier_head = "c" * 40
    path = request.files[0].path
    file_entry = {"filename": path}
    if status is not None:
        file_entry["status"] = status
    if previous_filename is not None:
        file_entry["previous_filename"] = previous_filename

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        **_kwargs: object,
    ) -> object:
        assert api_path == f"compare/{_BASE}...{carrier_head}"
        return {
            "status": "ahead",
            "ahead_by": 1,
            "behind_by": 0,
            "base_commit": {"sha": _BASE},
            "commits": [{"sha": carrier_head, "parents": [{"sha": _BASE}]}],
            "files": [file_entry],
        }

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
    monkeypatch.setattr(
        materialization,
        "_content_sha_at",
        lambda _repo, _token, *, path, revision: _BLOB if revision == carrier_head else None,
    )

    with pytest.raises(RuntimeError, match="file evidence|unrelated paths"):
        materialization._verify_revision(
            "royhsu-work/investment-strategy",
            _BASE,
            request,
            carrier_head,
        )


def test_existing_first_carrier_rejects_renamed_descendant_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = "a" * 40
    first = "b" * 40
    head = "c" * 40
    path = f"openspec/changes/{_CHANGE}/proposal.md"
    request = MaterializationRequest(
        issue_number=234,
        expected_change=_CHANGE,
        change=_CHANGE,
        branch=f"agent/{_CHANGE}",
        base_sha=base,
        message="Keep the exact first carrier commit",
        files=(WorkProductFile(path, _BLOB, None),),
        pr_number=271,
    )

    def comparison(
        base_sha: str,
        revision: str,
        *,
        commits: list[dict[str, object]],
        files: list[dict[str, str]],
    ) -> dict[str, object]:
        return {
            "status": "ahead",
            "ahead_by": len(commits),
            "behind_by": 0,
            "base_commit": {"sha": base_sha},
            "commits": commits,
            "files": files,
        }

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        **_kwargs: object,
    ) -> object:
        if api_path == f"compare/{base}...{head}":
            return comparison(
                base,
                head,
                commits=[
                    {"sha": first, "parents": [{"sha": base}]},
                    {"sha": head, "parents": [{"sha": first}]},
                ],
                files=[{"filename": path, "status": "added"}],
            )
        if api_path == f"compare/{base}...{first}":
            return comparison(
                base,
                first,
                commits=[{"sha": first, "parents": [{"sha": base}]}],
                files=[{"filename": path, "status": "added"}],
            )
        if api_path == f"compare/{first}...{head}":
            return comparison(
                first,
                head,
                commits=[{"sha": head, "parents": [{"sha": first}]}],
                files=[
                    {
                        "filename": path,
                        "previous_filename": "src/unrelated.py",
                        "status": "renamed",
                    }
                ],
            )
        raise AssertionError(api_path)

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    monkeypatch.setattr(validation_resource, "_github_json", fake_github_json)
    monkeypatch.setattr(
        materialization,
        "_content_sha_at",
        lambda _repo, _token, *, path, revision: _BLOB if path == request.files[0].path else None,
    )

    with pytest.raises(RuntimeError, match="descendant.*unrelated|descendant paths"):
        materialization._verify_existing_pr_revision_lineage(
            "royhsu-work/investment-strategy",
            _BASE,
            request,
            head,
        )


def test_existing_materialization_observer_accepts_direct_carrier_commit_on_current_main(
    proof_git: _ProofGitRepository,
) -> None:
    test_canonical_proof_accepts_357_shape_without_treating_pr_preimage_as_main(proof_git)
    target = _observe_git(proof_git)
    assert target.revision == proof_git.head
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


def test_existing_materialization_observer_recovers_disjoint_historical_base(
    proof_git: _ProofGitRepository,
) -> None:
    _accepted_git_carrier(proof_git)
    proof_git.main = proof_git.commit({"README.md": "advance"}, "Main", (proof_git.main,))
    target = _observe_git(proof_git)
    assert _postcondition_git(proof_git, target=target)
    assert _apply_git(proof_git) == target
    assert proof_git.mutations == []


def test_live_322_disjoint_advance_accepts_exact_materialization_postcondition(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Production shape retained through all consumers, with actual Git objects.
    test_canonical_consumers_share_proof_across_evolution_and_successor(proof_git, monkeypatch)


def test_live_322_merged_carrier_observer_recovers_exact_target(
    proof_git: _ProofGitRepository,
) -> None:
    test_canonical_git_proof_survives_disjoint_advance_reconciliation_and_merge(proof_git)
    target = _observe_git(proof_git)
    assert _apply_git(proof_git) == target
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


def test_merged_lead_carrier_observer_reconstructs_deterministic_replacement(
    proof_git: _ProofGitRepository,
) -> None:
    test_canonical_replacement_has_its_own_target_and_legal_descendants(proof_git, False)
    target = _observe_git(proof_git)
    assert target.pr_number == 353
    assert _apply_git(proof_git) == target
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


def test_merged_lead_carrier_observer_rejects_ambiguous_replacement(
    proof_git: _ProofGitRepository,
) -> None:
    test_canonical_replacement_has_its_own_target_and_legal_descendants(proof_git, False)
    proof_git.prs.append(dict(proof_git.prs[1], number=777))
    with pytest.raises(RuntimeError, match="ambiguous"):
        _observe_git(proof_git)
    assert proof_git.mutations == []


def test_merged_lead_carrier_observer_accepts_reconciled_stale_replacement(
    proof_git: _ProofGitRepository,
) -> None:
    test_canonical_replacement_has_its_own_target_and_legal_descendants(proof_git, True)
    target = _observe_git(proof_git)
    assert target.pr_number == 353
    assert _apply_git(proof_git) == target
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


class _ProofGitRepository:
    """Expose actual Git objects through the read-only GitHub response contract."""

    repository = "proof-owner/proof-repository"
    branch = f"agent/{_CHANGE}"
    path = f"openspec/changes/{_CHANGE}/proposal.md"
    message = "Materialize accepted proof fixture"
    source = WorkerRequest(322, "lead", "resolve-question")

    def __init__(self, directory: Path) -> None:
        import subprocess

        self.directory = directory
        self.directory.mkdir()
        subprocess.run(["git", "init", "-q", str(directory)], check=True)  # noqa: S603, S607 - fixed fixture command
        self.git("config", "user.name", "Proof fixture")
        self.git("config", "user.email", "proof@example.test")
        self.base = self.commit({self.path: "preimage", "README.md": "baseline"}, "Initial", ())
        self.authorization = self.base
        self.main = self.base
        self.head = self.base
        self.prs: list[dict[str, object]] = []
        self.mutations: list[str] = []
        self.desired = self.blob("accepted content")
        self.failure: str | None = None
        self.issue_change = _CHANGE
        self.first_create = False
        self.allow_writes = False
        self.interrupt_after: str | None = None
        self.created_objects: dict[str, str] = {}
        self.routing = self.source.action
        self.install_pr(324, self.branch, self.base)

    def git(self, *args: str, stdin: str | None = None) -> str:
        import subprocess

        completed = subprocess.run(  # noqa: S603 - fixed fixture Git argument array
            ["git", "-C", str(self.directory), *args],  # noqa: S607 - Git fixture executable
            input=stdin,
            text=True,
            capture_output=True,
            check=True,
        )
        return completed.stdout.strip()

    def blob(self, content: str) -> str:
        return self.git("hash-object", "-w", "--stdin", stdin=content)

    def entries(self, revision: str) -> dict[str, dict[str, object]]:
        entries: dict[str, dict[str, object]] = {}
        for line in self.git("ls-tree", "-r", revision).splitlines():
            metadata, path = line.split("\t")
            mode, kind, sha = metadata.split()
            entries[path] = {"path": path, "mode": mode, "type": kind, "sha": sha}
        return entries

    def commit(self, content: dict[str, str], message: str, parents: tuple[str, ...]) -> str:
        import os
        import subprocess

        index = self.directory / "temporary-index"
        index.unlink(missing_ok=True)
        environment = dict(os.environ, GIT_INDEX_FILE=str(index))

        def run(*args: str, stdin: str | None = None) -> str:
            result = subprocess.run(  # noqa: S603 - fixed fixture Git argument array
                ["git", "-C", str(self.directory), *args],  # noqa: S607 - Git fixture executable
                env=environment,
                input=stdin,
                text=True,
                capture_output=True,
                check=True,
            )
            return result.stdout.strip()

        if parents:
            run("read-tree", parents[0])
        for path, value in content.items():
            run("update-index", "--add", "--cacheinfo", f"100644,{self.blob(value)},{path}")
        tree = run("write-tree")
        args = ["commit-tree", tree]
        for parent in parents:
            args.extend(("-p", parent))
        return run(*args, stdin=message)

    def install_pr(self, number: int, branch: str, head: str, *, merged: bool = False) -> None:
        self.git("update-ref", f"refs/heads/{branch}", head)
        self.prs.append(
            {
                "number": number,
                "state": "closed" if merged else "open",
                "merged": merged,
                "merged_at": "2026-10-03T00:00:00Z" if merged else None,
                "title": f"OpenSpec: {_CHANGE}",
                "body": "Refs #322",
                "head": {"ref": branch, "sha": head, "repo": {"full_name": self.repository}},
                "base": {"ref": "main", "sha": self.main, "repo": {"full_name": self.repository}},
            }
        )

    def set_head(self, revision: str) -> None:
        self.head = revision
        self.git("update-ref", f"refs/heads/{self.branch}", revision)
        cast(dict[str, object], self.prs[0]["head"])["sha"] = revision

    def payload(self) -> dict[str, object]:
        return {
            "issue_number": 322,
            "operation": "application-materialize",
            "expected_change": self.issue_change,
            "change": _CHANGE,
            "branch": self.branch,
            "base_sha": self.base,
            "message": self.message,
            "pr_number": None if self.first_create else 324,
            "files": [
                {
                    "path": self.path,
                    "blob_sha": self.desired,
                    "expected_sha": self.entries(self.base).get(self.path, {}).get("sha"),
                }
            ],
        }

    def comparison(self, base: str, revision: str) -> dict[str, object]:
        merge_base = self.git("merge-base", base, revision)
        ahead = int(self.git("rev-list", "--count", f"{base}..{revision}"))
        behind = int(self.git("rev-list", "--count", f"{revision}..{base}"))
        commits = self.git(
            "rev-list", "--reverse", "--topo-order", f"{base}..{revision}"
        ).splitlines()
        files: list[dict[str, object]] = []
        for line in self.git("diff", "--name-status", merge_base, revision).splitlines():
            status, path = line.split("\t")
            files.append(
                {"filename": path, "status": {"A": "added", "D": "removed"}.get(status, "modified")}
            )
        result: dict[str, object] = {
            "base_commit": {"sha": base},
            "merge_base_commit": {"sha": merge_base},
            "ahead_by": ahead,
            "behind_by": behind,
            "total_commits": ahead,
            "status": "diverged"
            if ahead and behind
            else "ahead"
            if ahead
            else "behind"
            if behind
            else "identical",
            "commits": [
                {
                    "sha": sha,
                    "parents": [
                        {"sha": parent}
                        for parent in self.git("show", "-s", "--format=%P", sha).split()
                    ],
                }
                for sha in commits
            ],
            "files": files,
        }
        if self.failure == "incomplete-compare":
            result["commits"] = []
        return result

    def api(self, repository: str, token: str, path: str, **kwargs: object) -> object:
        import base64
        from urllib.parse import parse_qs, unquote, urlsplit

        assert repository == self.repository
        if kwargs.get("method", "GET") != "GET":
            self.mutations.append(path)
            if not self.allow_writes:
                raise AssertionError("proof must not write")
            return self.write(path, cast(dict[str, object], kwargs["payload"]))
        if path == "":
            return {"default_branch": "main"}
        if path == "issues/322":
            return {
                "number": 322,
                "state": "open",
                "body": f"Change: {self.issue_change}",
                "created_at": "2026-09-01T00:00:00Z",
                "closed_at": None,
                "labels": [{"name": f"action:{self.routing}"}],
            }
        if path.startswith("git/ref/heads/"):
            branch = unquote(path.removeprefix("git/ref/heads/"))
            if branch == "main":
                revision = self.main
            else:
                try:
                    revision = self.git("rev-parse", "--verify", f"refs/heads/{branch}")
                except Exception:
                    if kwargs.get("allow_not_found"):
                        return None
                    raise
            if self.failure == "wrong-ref" and branch == self.branch:
                revision = self.base
            return {"object": {"sha": revision}}
        if path.startswith("pulls?"):
            query = parse_qs(urlsplit(path).query)
            filter_branch = None if "head" not in query else query["head"][0].split(":", 1)[1]
            state = query.get("state", ["all"])[0]
            matches = [
                pr
                for pr in self.prs
                if (
                    (
                        filter_branch is None
                        or cast(dict[str, object], pr["head"])["ref"] == filter_branch
                    )
                    and (state == "all" or pr["state"] == state)
                )
            ]
            return matches * 2 if self.failure == "duplicate-pr" else matches
        if path.startswith("pulls/"):
            segments = path.split("/")
            if len(segments) > 2:
                return [{"filename": self.path, "status": "modified"}]
            return next(pr for pr in self.prs if pr["number"] == int(segments[1]))
        if path.startswith("compare/"):
            base, revision = path.removeprefix("compare/").split("...")
            return self.comparison(base, revision)
        if path.startswith("git/blobs/"):
            sha = path.removeprefix("git/blobs/")
            return {
                "sha": sha,
                "encoding": "base64",
                "content": base64.b64encode(self.git("cat-file", "blob", sha).encode()).decode(),
            }
        if path.startswith("git/commits/"):
            revision = path.removeprefix("git/commits/")
            return {
                "sha": revision,
                "tree": {"sha": self.git("rev-parse", f"{revision}^{{tree}}")},
                "message": self.git("show", "-s", "--format=%B", revision),
                "parents": [
                    {"sha": sha} for sha in self.git("show", "-s", "--format=%P", revision).split()
                ],
            }
        if path.startswith("git/trees/"):
            tree = path.removeprefix("git/trees/").split("?")[0]
            return {"sha": tree, "truncated": False, "tree": list(self.entries(tree).values())}
        if path.startswith("contents/"):
            parsed = urlsplit(path)
            filename = unquote(parsed.path.removeprefix("contents/"))
            revision = parse_qs(parsed.query)["ref"][0]
            entries = self.entries(revision)
            content_entry = entries.get(filename)
            if content_entry is None:
                directory_entries = [
                    value for key, value in entries.items() if key.startswith(filename + "/")
                ]
                return directory_entries or None
            return {
                "sha": content_entry["sha"],
                "type": "file",
                "encoding": "base64",
                "content": base64.b64encode(
                    self.git("show", f"{revision}:{filename}").encode()
                ).decode(),
            }

        raise AssertionError(f"unimplemented read {path}")

    def write(self, path: str, payload: dict[str, object]) -> object:
        import os
        import subprocess

        if path == "git/trees":
            index = self.directory / "construction-index"
            index.unlink(missing_ok=True)
            environment = dict(os.environ, GIT_INDEX_FILE=str(index))

            def run(*args: str) -> str:
                result = subprocess.run(  # noqa: S603 - application fixture arguments
                    ["git", "-C", str(self.directory), *args],  # noqa: S607
                    env=environment,
                    text=True,
                    capture_output=True,
                    check=True,
                )
                return result.stdout.strip()

            run("read-tree", cast(str, payload["base_tree"]))
            for element in cast(list[dict[str, object]], payload["tree"]):
                filename = cast(str, element["path"])
                sha = element["sha"]
                if sha is None:
                    run("update-index", "--force-remove", filename)
                else:
                    run(
                        "update-index",
                        "--add",
                        "--cacheinfo",
                        f"{element['mode']},{sha},{filename}",
                    )
            sha = run("write-tree")
        elif path == "git/commits":
            args = ["commit-tree", cast(str, payload["tree"])]
            for parent in cast(list[str], payload["parents"]):
                args.extend(("-p", parent))
            sha = self.git(*args, stdin=cast(str, payload["message"]))
        elif path == "git/refs":
            ref, sha = cast(str, payload["ref"]), cast(str, payload["sha"])
            self.git("update-ref", ref, sha)
            self.created_objects[path] = sha
            if self.interrupt_after == path:
                raise RuntimeError(f"fixture interruption after {path}")
            return {"ref": ref, "object": {"sha": sha}}
        else:
            raise AssertionError(f"unimplemented fixture mutation {path}")
        self.created_objects[path] = sha
        if self.interrupt_after == path:
            raise RuntimeError(f"fixture interruption after {path}")
        return {"sha": sha}


@pytest.fixture
def proof_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _ProofGitRepository:
    fixture = _ProofGitRepository(tmp_path / "proof-git")
    monkeypatch.setattr(materialization, "_github_json", fixture.api)
    monkeypatch.setattr(validation_resource, "_github_json", fixture.api)
    monkeypatch.setattr(
        materialization, "_current_authorized_request", lambda *_args: fixture.source
    )
    monkeypatch.setattr(
        validation_resource, "_current_authorized_request", lambda *_args: fixture.source
    )
    return fixture


def _prove_git(fixture: _ProofGitRepository) -> materialization.MaterializationProof:
    return materialization.prove_materialization(
        fixture.payload(),
        fixture.source,
        repository=fixture.repository,
        token=_TOKEN,
        current_revision=fixture.main,
        default_branch="main",
        accepted_authorization_revision=fixture.authorization,
    )


def test_canonical_proof_separates_current_target_from_immutable_git_witness(
    proof_git: _ProofGitRepository,
) -> None:
    initial = _prove_git(proof_git)
    assert initial.disposition == "INCOMPLETE", initial
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    complete = _prove_git(proof_git)
    assert complete.disposition == "COMPLETE", complete
    assert complete.witness is not None and complete.witness.revision == accepted
    later = proof_git.commit(
        {proof_git.path: "legal correction"}, "Correct same Change", (accepted,)
    )
    proof_git.set_head(later)
    evolved = _prove_git(proof_git)
    assert evolved.disposition == "COMPLETE", evolved
    assert evolved.target is not None and evolved.target.revision == later
    assert evolved.witness is not None and evolved.witness.revision == accepted
    assert proof_git.mutations == []


@pytest.mark.parametrize(
    "failure",
    [
        "wrong-blob",
        "wrong-ref",
        "duplicate-pr",
        "overlap",
        "incomplete-compare",
        "unrelated-overwrite",
    ],
)
def test_canonical_git_proof_preserves_conflicts(
    proof_git: _ProofGitRepository,
    failure: str,
) -> None:
    value = "wrong content" if failure == "wrong-blob" else "accepted content"
    accepted = proof_git.commit({proof_git.path: value}, proof_git.message, (proof_git.base,))
    proof_git.set_head(accepted)
    if failure == "overlap":
        proof_git.main = proof_git.commit(
            {proof_git.path: "conflicting main"}, "Main overlap", (proof_git.base,)
        )
    elif failure == "unrelated-overwrite":
        proof_git.set_head(
            proof_git.commit(
                {"README.md": "lost unrelated baseline"}, "Bad descendant", (accepted,)
            )
        )
    else:
        proof_git.failure = failure
    proof = _prove_git(proof_git)
    assert proof.disposition == "CONTRADICTORY", proof
    assert proof.reason
    assert proof_git.mutations == []


def test_canonical_git_proof_survives_disjoint_advance_reconciliation_and_merge(
    proof_git: _ProofGitRepository,
) -> None:
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint advance"}, "Main advance", (proof_git.base,)
    )
    assert _prove_git(proof_git).disposition == "COMPLETE"
    reconciliation = proof_git.commit(
        {"README.md": "disjoint advance"},
        f"Reconcile default-branch ancestry for {_CHANGE}",
        (accepted, proof_git.main),
    )
    proof_git.set_head(reconciliation)
    reconciled = _prove_git(proof_git)
    assert reconciled.disposition == "COMPLETE", reconciled
    assert reconciled.witness is not None and reconciled.witness.revision == accepted
    correction = proof_git.commit(
        {proof_git.path: "later one parent correction"}, "Correction", (reconciliation,)
    )
    proof_git.set_head(correction)
    assert _prove_git(proof_git).disposition == "COMPLETE"
    merge = proof_git.commit(
        {proof_git.path: "later one parent correction"}, "Merge", (proof_git.main, correction)
    )
    proof_git.main = merge
    proof_git.prs[0].update(
        state="closed", merged=True, merged_at="2026-10-03T00:00:00Z", merge_commit_sha=merge
    )
    merged = _prove_git(proof_git)
    assert merged.disposition == "COMPLETE", merged
    assert merged.target is not None and merged.target.revision == merge
    assert merged.witness is not None and merged.witness.revision == accepted
    assert proof_git.mutations == []


def _first_git_intent(fixture: _ProofGitRepository) -> None:
    fixture.first_create = True
    fixture.issue_change = "unset"
    fixture.source = WorkerRequest(322, "lead", "propose-change")
    fixture.routing = fixture.source.action
    fixture.base = fixture.commit({"README.md": "baseline"}, "Empty Change baseline", ())
    fixture.authorization = fixture.base
    fixture.main = fixture.base
    fixture.set_head(fixture.base)
    cast(dict[str, object], fixture.prs[0]["base"])["sha"] = fixture.base


@pytest.mark.parametrize("lifecycle", ["open", "closed", "draft"])
def test_canonical_first_carrier_requires_original_qualified_lifecycle(
    proof_git: _ProofGitRepository,
    lifecycle: str,
) -> None:
    _first_git_intent(proof_git)
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    if lifecycle == "closed":
        proof_git.prs[0]["state"] = "closed"
    if lifecycle == "draft":
        proof_git.prs[0]["draft"] = True
    proof = _prove_git(proof_git)
    assert proof.disposition == ("COMPLETE" if lifecycle == "open" else "CONTRADICTORY"), proof
    assert proof_git.mutations == []


def test_every_materialization_consumer_uses_current_target_after_legal_correction(
    proof_git: _ProofGitRepository,
) -> None:
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    previous = _prove_git(proof_git)
    assert previous.disposition == "COMPLETE", previous
    corrected = proof_git.commit(
        {proof_git.path: "later approved correction"}, "Same Change correction", (accepted,)
    )
    proof_git.set_head(corrected)
    current = _prove_git(proof_git)
    assert current.disposition == "COMPLETE", current
    assert current.witness is not None and current.witness.revision == accepted
    assert current.target is not None and current.target.revision == corrected
    assert proof_git.entries(corrected)[proof_git.path]["sha"] != proof_git.desired
    assert _apply_git(proof_git) == current.target
    assert (
        materialization.observe_materialization_target(
            proof_git.payload(),
            proof_git.source,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            default_branch="main",
            accepted_authorization_revision=proof_git.authorization,
        )
        == current.target
    )
    assert materialization.materialization_postcondition(
        proof_git.payload(),
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        target=previous.target,
        accepted_authorization_revision=proof_git.authorization,
    )
    assert proof_git.mutations == []


def test_canonical_first_create_rejects_existing_accepted_preimage(
    proof_git: _ProofGitRepository,
) -> None:
    proof_git.first_create = True
    proof_git.issue_change = "unset"
    proof_git.source = WorkerRequest(322, "lead", "propose-change")
    payload = proof_git.payload()
    cast(list[dict[str, object]], payload["files"])[0]["expected_sha"] = None
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    proof = materialization.prove_materialization(
        payload,
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        accepted_authorization_revision=proof_git.base,
    )
    assert proof.disposition == "CONTRADICTORY", proof
    assert proof_git.mutations == []


def test_canonical_missing_first_carrier_does_not_authorize_known_overlap(
    proof_git: _ProofGitRepository,
) -> None:
    _first_git_intent(proof_git)
    proof_git.prs.clear()
    proof_git.git("update-ref", "-d", f"refs/heads/{proof_git.branch}")
    proof_git.main = proof_git.commit(
        {proof_git.path: "overlapping main"}, "Overlap", (proof_git.base,)
    )
    proof = _prove_git(proof_git)
    assert proof.disposition == "CONTRADICTORY", proof
    assert proof_git.mutations == []


@pytest.mark.parametrize("advance_before_materialization", [False, True])
def test_canonical_replacement_has_its_own_target_and_legal_descendants(
    proof_git: _ProofGitRepository,
    advance_before_materialization: bool,
) -> None:
    original_head = proof_git.commit(
        {proof_git.path: "preimage"}, "Earlier Change", (proof_git.base,)
    )
    proof_git.set_head(original_head)
    merged_original = proof_git.commit(
        {proof_git.path: "preimage"}, "Merge earlier Change", (proof_git.main, original_head)
    )
    proof_git.main = merged_original
    proof_git.prs[0].update(
        state="closed",
        merged=True,
        merged_at="2026-10-03T00:00:00Z",
        merge_commit_sha=merged_original,
    )
    proof_git.base = merged_original
    if advance_before_materialization:
        proof_git.main = proof_git.commit(
            {"README.md": "safe advance"}, "Advance", (proof_git.main,)
        )
    replacement = validation_resource._replacement_branch(_CHANGE, 324)
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.main,)
    )
    proof_git.install_pr(353, replacement, accepted)
    proof = _prove_git(proof_git)
    assert proof.disposition == "COMPLETE", proof
    assert proof.target is not None and proof.target.pr_number == 353
    assert proof.witness is not None and proof.witness.revision == accepted
    correction = proof_git.commit(
        {proof_git.path: "replacement correction"}, "Correct replacement", (accepted,)
    )
    cast(dict[str, object], proof_git.prs[1]["head"])["sha"] = correction
    proof_git.git("update-ref", f"refs/heads/{replacement}", correction)
    evolved = _prove_git(proof_git)
    assert evolved.disposition == "COMPLETE", evolved
    assert evolved.target is not None and evolved.target.revision == correction
    assert evolved.witness is not None and evolved.witness.revision == accepted
    assert proof_git.mutations == []


def test_canonical_proof_accepts_357_shape_without_treating_pr_preimage_as_main(
    proof_git: _ProofGitRepository,
) -> None:
    branch_preimage = proof_git.commit(
        {proof_git.path: "preimage"}, "Earlier branch work", (proof_git.base,)
    )
    proof_git.main = proof_git.commit(
        {"README.md": "current default"}, "Default advance", (proof_git.base,)
    )
    reconciliation = proof_git.commit(
        {"README.md": "current default"},
        f"Reconcile default-branch ancestry for {_CHANGE}",
        (branch_preimage, proof_git.main),
    )
    proof_git.base = reconciliation
    proof_git.authorization = proof_git.main
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (reconciliation,)
    )
    proof_git.set_head(accepted)
    proof = _prove_git(proof_git)
    assert proof.disposition == "COMPLETE", proof
    assert proof.witness is not None
    assert proof.witness.revisions.accepted_authorization == proof_git.main
    assert proof.witness.revisions.mutation_preimage == reconciliation
    assert proof.witness.revisions.current_default == proof_git.main
    assert proof_git.mutations == []


def test_canonical_correction_then_reconciliation_keeps_old_witness_without_replay(
    proof_git: _ProofGitRepository,
) -> None:
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    correction = proof_git.commit(
        {proof_git.path: "qualified later content"}, "Correction", (accepted,)
    )
    proof_git.set_head(correction)
    assert _prove_git(proof_git).disposition == "COMPLETE"
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint advance"}, "Advance", (proof_git.main,)
    )
    reconciled = proof_git.commit(
        {"README.md": "disjoint advance"},
        f"Reconcile default-branch ancestry for {_CHANGE}",
        (correction, proof_git.main),
    )
    proof_git.set_head(reconciled)
    proof = _prove_git(proof_git)
    assert proof.disposition == "COMPLETE", proof
    assert proof.target is not None and proof.target.revision == reconciled
    assert proof.witness is not None and proof.witness.revision == accepted
    assert proof_git.entries(reconciled)[proof_git.path]["sha"] != proof_git.desired
    assert proof_git.mutations == []


def test_canonical_missing_replacement_stays_incomplete_after_disjoint_main_advance(
    proof_git: _ProofGitRepository,
) -> None:
    original_head = proof_git.commit(
        {proof_git.path: "preimage"}, "Earlier Change", (proof_git.base,)
    )
    proof_git.set_head(original_head)
    merged_original = proof_git.commit(
        {proof_git.path: "preimage"}, "Merge", (proof_git.main, original_head)
    )
    proof_git.main = merged_original
    proof_git.base = merged_original
    proof_git.authorization = merged_original
    proof_git.prs[0].update(
        state="closed",
        merged=True,
        merged_at="2026-10-03T00:00:00Z",
        merge_commit_sha=merged_original,
    )
    assert _prove_git(proof_git).disposition == "INCOMPLETE"
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint advance"}, "Advance", (proof_git.main,)
    )
    incomplete = _prove_git(proof_git)
    assert incomplete.disposition == "INCOMPLETE", incomplete
    proof_git.main = proof_git.commit(
        {proof_git.path: "conflicting default"}, "Overlap", (proof_git.main,)
    )
    conflict = _prove_git(proof_git)
    assert conflict.disposition == "CONTRADICTORY", conflict
    assert proof_git.mutations == []


def _apply_git(fixture: _ProofGitRepository) -> ValidationResourceTarget:
    return materialization.apply_materialization(
        fixture.payload(),
        fixture.source,
        repository=fixture.repository,
        token=_TOKEN,
        current_revision=fixture.main,
        default_branch="main",
        accepted_authorization_revision=fixture.authorization,
    )


def test_apply_then_fresh_proof_and_every_read_consumer_reuses_git_consequence(
    proof_git: _ProofGitRepository,
) -> None:
    proof_git.allow_writes = True
    with pytest.raises(CarrierRequired) as raised:
        _apply_git(proof_git)
    plan = raised.value.plan
    revision = cast(str, plan.requested["sha"])
    assert plan.force is False
    assert plan.expected["ref_sha"] == proof_git.base
    assert plan.expected["commit_parents"] == [proof_git.base]
    assert proof_git.mutations == ["git/trees", "git/commits"]
    # The actuator uses only the immutable application plan after observing
    # its exact preconditions. No worker makes a target or successor choice.
    assert proof_git.head == plan.expected["ref_sha"]
    proof_git.set_head(revision)
    completed = _prove_git(proof_git)
    assert completed.disposition == "COMPLETE", completed
    before = list(proof_git.mutations)
    assert _apply_git(proof_git) == completed.target
    observed = materialization.observe_materialization_target(
        proof_git.payload(),
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        accepted_authorization_revision=proof_git.authorization,
    )
    assert observed == completed.target
    assert materialization.materialization_postcondition(
        proof_git.payload(),
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        target=None,
        accepted_authorization_revision=proof_git.authorization,
    )
    assert proof_git.mutations == before


@pytest.mark.parametrize(
    "prefix",
    [
        "accepted-decision",
        "blob",
        "git/trees",
        "git/commits",
        "CarrierRequired",
        "branch-ref",
        "PR-carrier",
        "successor-routing",
    ],
)
def test_first_materialization_interruption_prefixes_reconstruct_from_fresh_git(
    proof_git: _ProofGitRepository,
    prefix: str,
) -> None:
    _first_git_intent(proof_git)
    proof_git.prs.clear()
    proof_git.git("update-ref", "-d", f"refs/heads/{proof_git.branch}")
    payload = proof_git.payload()
    proof_git.allow_writes = True
    proof_git.interrupt_after = prefix if prefix in {"git/trees", "git/commits"} else None
    if prefix in {"accepted-decision", "blob"}:
        pass
    elif prefix in {"git/trees", "git/commits"}:
        with pytest.raises(RuntimeError, match="fixture interruption"):
            _apply_git(proof_git)
    else:
        with pytest.raises(CarrierRequired) as raised:
            _apply_git(proof_git)
        revision = cast(str, raised.value.plan.requested["head_sha"])
        assert proof_git.git("rev-parse", f"refs/heads/{proof_git.branch}") == revision
        if prefix not in {"CarrierRequired", "branch-ref"}:
            proof_git.install_pr(324, proof_git.branch, revision)
        if prefix == "successor-routing":
            proof_git.issue_change = _CHANGE
            proof_git.routing = "review-openspec"
    expected = (
        "INCOMPLETE"
        if prefix
        in {
            "accepted-decision",
            "blob",
            "git/trees",
            "git/commits",
            "CarrierRequired",
            "branch-ref",
        }
        else "COMPLETE"
    )
    before = list(proof_git.mutations)
    # Recreate proof with a new invocation and only durable repository reads.
    proof = materialization.prove_materialization(
        payload,
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        accepted_authorization_revision=proof_git.authorization,
        allow_pending_continuation=True,
        accepted_successor_routing=("reviewer", "review-openspec")
        if prefix == "successor-routing"
        else None,
    )
    assert proof.disposition == expected, proof
    assert proof_git.mutations == before
    if prefix in {"CarrierRequired", "branch-ref"}:
        proof_git.interrupt_after = None
        with pytest.raises(CarrierRequired) as missing_pr:
            _apply_git(proof_git)
        assert missing_pr.value.plan.operation == "pull-request-create"
        assert proof_git.mutations == before


def _git_worker_result(fixture: _ProofGitRepository, payload: dict[str, object]) -> str:
    return json.dumps(
        {
            "issue_number": 322,
            "role": fixture.source.role,
            "action": fixture.source.action,
            "change": _CHANGE,
            "result_kind": "ready-for-openspec-review",
            "evidence_ref": "accepted-intent-proof",
            "result_content": "Bounded accepted Change",
            "requested_effects": [{"kind": "github-mutation", "payload_json": json.dumps(payload)}],
        }
    )


def test_canonical_consumers_share_proof_across_evolution_and_successor(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import investment_strategy.scheduled_agent_effects as effects

    monkeypatch.setattr(effects, "_github_json", proof_git.api)
    payload = proof_git.payload()
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    initial_target = _apply_git(proof_git)
    correction = proof_git.commit(
        {proof_git.path: "later corrected content"}, "Correction", (accepted,)
    )
    proof_git.set_head(correction)
    proof_git.main = proof_git.commit({"README.md": "disjoint advance"}, "Main", (proof_git.main,))
    raw = _git_worker_result(proof_git, payload)
    for successor in (False, True):
        if successor:
            proof_git.routing = "review-openspec"
        assert materialization.materialization_postcondition(
            payload,
            proof_git.source,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            default_branch="main",
            target=initial_target,
            accepted_authorization_revision=proof_git.authorization,
            allow_pending_continuation=True,
        ) is (not successor)
        assert effects.consequence_postconditions_complete(
            raw,
            source=proof_git.source,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            authorized_change=_CHANGE,
            accepted_authorization_revision=proof_git.authorization,
            allow_pending_continuation=True,
            allow_accepted_successor=successor,
        )
    assert proof_git.mutations == []


@pytest.mark.parametrize(
    "failure",
    [
        "wrong-blob",
        "wrong-ref",
        "duplicate-pr",
        "overlap",
        "incomplete-compare",
        "unrelated-overwrite",
    ],
)
def test_contradictory_proof_blocks_apply_without_repository_mutation(
    proof_git: _ProofGitRepository,
    failure: str,
) -> None:
    accepted = proof_git.commit(
        {proof_git.path: "wrong content" if failure == "wrong-blob" else "accepted content"},
        proof_git.message,
        (proof_git.base,),
    )
    proof_git.set_head(accepted)
    if failure == "overlap":
        proof_git.main = proof_git.commit(
            {proof_git.path: "overlapping main"}, "Conflict", (proof_git.main,)
        )
    elif failure == "unrelated-overwrite":
        proof_git.set_head(
            proof_git.commit({"README.md": "overwrite"}, "Bad correction", (accepted,))
        )
    else:
        proof_git.failure = failure
    proof_git.allow_writes = True
    with pytest.raises(RuntimeError):
        _apply_git(proof_git)
    assert proof_git.mutations == []


def test_canonical_proof_rejects_competing_active_change_carrier(
    proof_git: _ProofGitRepository,
) -> None:
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    competing = validation_resource._replacement_branch(_CHANGE, 123)
    proof_git.install_pr(777, competing, accepted)
    proof = _prove_git(proof_git)
    assert proof.disposition == "CONTRADICTORY", proof
    assert proof_git.mutations == []


def test_canonical_main_snapshot_requires_qualified_same_change_carrier_witness(
    proof_git: _ProofGitRepository,
) -> None:
    original = proof_git.commit({proof_git.path: "preimage"}, "Earlier Change", (proof_git.base,))
    proof_git.set_head(original)
    merged = proof_git.commit(
        {proof_git.path: "preimage"}, "Merge earlier Change", (proof_git.main, original)
    )
    proof_git.main = merged
    proof_git.base = merged
    proof_git.authorization = merged
    proof_git.prs[0].update(
        state="closed", merged=True, merged_at="2026-10-03T00:00:00Z", merge_commit_sha=merged
    )
    # Exact accepted-looking content on main alone does not bind a PR carrier.
    proof_git.main = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (merged,)
    )
    proof = _prove_git(proof_git)
    assert proof.disposition == "CONTRADICTORY", proof
    assert proof_git.mutations == []


def _accepted_git_carrier(fixture: _ProofGitRepository) -> str:
    accepted = fixture.commit({fixture.path: "accepted content"}, fixture.message, (fixture.base,))
    fixture.set_head(accepted)
    return accepted


def _observe_git(fixture: _ProofGitRepository) -> ValidationResourceTarget:
    return materialization.observe_materialization_target(
        fixture.payload(),
        fixture.source,
        repository=fixture.repository,
        token=_TOKEN,
        current_revision=fixture.main,
        default_branch="main",
        accepted_authorization_revision=fixture.authorization,
    )


def _postcondition_git(
    fixture: _ProofGitRepository, *, target: ValidationResourceTarget | None
) -> bool:
    return materialization.materialization_postcondition(
        fixture.payload(),
        fixture.source,
        repository=fixture.repository,
        token=_TOKEN,
        current_revision=fixture.main,
        default_branch="main",
        accepted_authorization_revision=fixture.authorization,
        target=target,
    )


def test_declared_main_base_uses_actual_branch_write_preimage(
    proof_git: _ProofGitRepository,
) -> None:
    branch_parent = proof_git.commit(
        {proof_git.path: "branch preimage"}, "Earlier correction", (proof_git.base,)
    )
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint main"}, "Default advance", (proof_git.base,)
    )
    proof_git.base = proof_git.main
    proof_git.authorization = proof_git.main
    accepted = proof_git.commit(
        {proof_git.path: "accepted content", "README.md": "disjoint main"},
        proof_git.message,
        (branch_parent, proof_git.main),
    )
    proof_git.set_head(accepted)
    payload = proof_git.payload()
    cast(list[dict[str, object]], payload["files"])[0]["expected_sha"] = proof_git.entries(
        branch_parent
    )[proof_git.path]["sha"]
    result = materialization.prove_materialization(
        payload,
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        accepted_authorization_revision=proof_git.authorization,
    )
    assert result.disposition == "COMPLETE", result
    assert result.witness is not None
    assert result.witness.revisions.carrier_base == proof_git.main
    assert result.witness.revisions.mutation_preimage == branch_parent
    cast(list[dict[str, object]], payload["files"])[0]["expected_sha"] = proof_git.entries(
        proof_git.main
    )[proof_git.path]["sha"]
    stale = materialization.prove_materialization(
        payload,
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        accepted_authorization_revision=proof_git.authorization,
    )
    assert stale.disposition == "CONTRADICTORY", stale
    assert proof_git.mutations == []


def test_missing_first_branch_recovers_after_disjoint_default_advance(
    proof_git: _ProofGitRepository,
) -> None:
    proof_git.source = WorkerRequest(322, "lead", "propose-change")
    proof_git.routing = proof_git.source.action
    proof_git.issue_change = "unset"
    proof_git.first_create = True
    proof_git.prs.clear()
    proof_git.git("update-ref", "-d", f"refs/heads/{proof_git.branch}")
    proof_git.base = proof_git.commit({"README.md": "baseline"}, "Empty Change base", ())
    proof_git.authorization = proof_git.base
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint advance"}, "Main advance", (proof_git.base,)
    )
    proof_git.allow_writes = True
    assert _prove_git(proof_git).disposition == "INCOMPLETE"
    with pytest.raises(CarrierRequired) as raised:
        materialization.apply_materialization(
            proof_git.payload(),
            proof_git.source,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            default_branch="main",
            accepted_authorization_revision=proof_git.authorization,
            allow_pending_continuation=True,
        )
    assert raised.value.plan.operation == "pull-request-create"
    assert proof_git.mutations == ["git/trees", "git/commits", "git/refs"]


def test_missing_reconciliation_constructs_on_exact_actual_branch_parent(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch_parent = proof_git.commit(
        {proof_git.path: "branch preimage"},
        "Earlier correction",
        (proof_git.base,),
    )
    proof_git.set_head(branch_parent)
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint main"},
        "Main advance",
        (proof_git.base,),
    )
    proof_git.base = proof_git.main
    proof_git.authorization = proof_git.main
    payload = proof_git.payload()
    cast(list[dict[str, object]], payload["files"])[0]["expected_sha"] = proof_git.entries(
        branch_parent
    )[proof_git.path]["sha"]
    monkeypatch.setattr(proof_git, "payload", lambda: payload)
    proof_git.allow_writes = True
    assert _prove_git(proof_git).disposition == "INCOMPLETE"
    with pytest.raises(CarrierRequired) as raised:
        _apply_git(proof_git)
    plan = raised.value.plan
    assert plan.expected["ref_sha"] == branch_parent
    assert plan.requested["commit_parents"] == [branch_parent, proof_git.main]
    proof_git.set_head(cast(str, plan.requested["sha"]))
    result = _prove_git(proof_git)
    assert result.disposition == "COMPLETE", result
    assert result.witness is not None
    assert result.witness.revisions.mutation_preimage == branch_parent
    assert (
        proof_git.entries(proof_git.head)["README.md"]["sha"]
        == (proof_git.entries(proof_git.main)["README.md"]["sha"])
    )
    written = list(proof_git.mutations)
    _apply_git(proof_git)
    assert proof_git.mutations == written


def test_actual_implementation_constructor_is_proved_by_fresh_consumers(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import investment_strategy.scheduled_agent_application_carrier as carrier

    proof_git.source = WorkerRequest(322, "executor", "implement-change")
    proof_git.routing = proof_git.source.action
    proof_git.path = f"openspec/changes/{_CHANGE}/tasks.md"
    proof_git.base = proof_git.commit(
        {proof_git.path: "## Slice\n- [ ] 1.1 Implement the slice\n"},
        "Approved tasks",
        (proof_git.base,),
    )
    proof_git.main = proof_git.base
    proof_git.authorization = proof_git.base
    proof_git.set_head(proof_git.base)
    proof_git.desired = proof_git.blob("## Slice\n- [x] 1.1 Implement the slice\n")
    proof_git.allow_writes = True
    monkeypatch.setattr(carrier, "_github_json", proof_git.api)
    with pytest.raises(CarrierRequired) as raised:
        _apply_git(proof_git)
    assert raised.value.plan.requested["commit_parents"] == [proof_git.base]
    proof_git.set_head(cast(str, raised.value.plan.requested["sha"]))
    proof = _prove_git(proof_git)
    assert proof.disposition == "COMPLETE", proof
    before = list(proof_git.mutations)
    _apply_git(proof_git)
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == before


@pytest.mark.parametrize("prefix", ["decision", "tree", "commit", "ref", "pr", "merge"])
def test_separate_process_reconstructs_only_persisted_git_evidence(
    proof_git: _ProofGitRepository,
    prefix: str,
) -> None:
    import json
    import os
    import subprocess
    import sys

    proof_git.source = WorkerRequest(322, "lead", "propose-change")
    proof_git.routing = proof_git.source.action
    proof_git.issue_change = "unset"
    proof_git.first_create = True
    proof_git.base = proof_git.commit({"README.md": "baseline"}, "Empty first base", ())
    proof_git.main = proof_git.authorization = proof_git.base
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"},
        proof_git.message,
        (proof_git.base,),
    )
    proof_git.prs.clear()
    if prefix in {"pr", "merge"}:
        proof_git.install_pr(324, proof_git.branch, accepted)
    elif prefix == "ref":
        proof_git.git("update-ref", f"refs/heads/{proof_git.branch}", accepted)
    else:
        proof_git.git("update-ref", "-d", f"refs/heads/{proof_git.branch}")
    if prefix == "merge":
        proof_git.main = proof_git.commit({}, "Merge", (proof_git.main, accepted))
        proof_git.prs[0].update(
            state="closed",
            merged=True,
            merged_at="2026-10-04T00:00:00Z",
            merge_commit_sha=proof_git.main,
        )
    snapshot = {
        "directory": str(proof_git.directory),
        "base": proof_git.base,
        "authorization": proof_git.authorization,
        "main": proof_git.main,
        "head": proof_git.head,
        "prs": proof_git.prs,
        "desired": proof_git.desired,
        "issue_change": proof_git.issue_change,
        "first_create": proof_git.first_create,
        "routing": proof_git.routing,
    }
    script = """
import json, sys
from pathlib import Path
import investment_strategy.scheduled_agent_application_materialization as owner
import investment_strategy.scheduled_agent_validation_resource as resource
from tests.test_scheduled_agent_application_materialization import _ProofGitRepository
snapshot = json.loads(sys.stdin.read())
remote = object.__new__(_ProofGitRepository)
remote.__dict__.update(snapshot)
remote.directory = Path(remote.directory)
remote.failure = None
remote.mutations = []
remote.allow_writes = False
from investment_strategy.scheduled_agent_runtime import WorkerRequest
remote.source = WorkerRequest(322, "lead", "propose-change")
owner._github_json = resource._github_json = remote.api
owner._current_authorized_request = lambda *args: remote.source
resource._current_authorized_request = owner._current_authorized_request
proof = owner.prove_materialization(remote.payload(), remote.source,
    repository=remote.repository, token="fixture", current_revision=remote.main,
    default_branch="main", accepted_authorization_revision=remote.authorization)
print(json.dumps({"status": proof.disposition, "reason": proof.reason, "writes": remote.mutations}))
"""
    result = subprocess.run(  # noqa: S603 - isolated fresh proof process, fixed script
        [sys.executable, "-c", script],
        input=json.dumps(snapshot),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(Path.cwd() / "src")},
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    expected = "COMPLETE" if prefix in {"pr", "merge"} else "INCOMPLETE"
    assert observed["status"] == expected, observed
    assert observed["writes"] == []


@pytest.mark.parametrize("advance", [False, True])
def test_actual_missing_replacement_constructor_and_fresh_proof(
    proof_git: _ProofGitRepository,
    advance: bool,
) -> None:
    original_head = proof_git.commit({}, "Earlier Change", (proof_git.base,))
    proof_git.set_head(original_head)
    merged = proof_git.commit({}, "Merge earlier Change", (proof_git.main, original_head))
    proof_git.main = proof_git.base = proof_git.authorization = merged
    proof_git.prs[0].update(
        state="closed", merged=True, merged_at="2026-10-04T00:00:00Z", merge_commit_sha=merged
    )
    if advance:
        proof_git.main = proof_git.commit({"README.md": "later main"}, "Advance", (merged,))
    proof_git.allow_writes = True
    assert _prove_git(proof_git).disposition == "INCOMPLETE"
    with pytest.raises(CarrierRequired) as raised:
        _apply_git(proof_git)
    plan = raised.value.plan
    assert plan.operation == "pull-request-create"
    replacement = cast(str, plan.target["head_ref"])
    revision = cast(str, plan.requested["head_sha"])
    assert proof_git.git("show", "-s", "--format=%P", revision) == proof_git.main
    proof_git.install_pr(353, replacement, revision)
    proof = _prove_git(proof_git)
    assert proof.disposition == "COMPLETE", proof
    assert proof.target is not None and proof.target.pr_number == 353
    assert proof.witness is not None and proof.witness.revision == revision
    writes = list(proof_git.mutations)
    assert _apply_git(proof_git) == proof.target
    assert proof_git.mutations == writes


@pytest.mark.parametrize("carrier", ["first", "replacement"])
@pytest.mark.parametrize("changed", ["main", "issue", "source", "ref"])
def test_concurrent_change_after_commit_rejects_direct_ref_creation(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    carrier: str,
    changed: str,
) -> None:
    if carrier == "first":
        _first_git_intent(proof_git)
        proof_git.prs.clear()
        proof_git.git("update-ref", "-d", f"refs/heads/{proof_git.branch}")
    else:
        previous = proof_git.commit({}, "Earlier Change", (proof_git.base,))
        proof_git.set_head(previous)
        merged = proof_git.commit({}, "Merge earlier Change", (proof_git.main, previous))
        proof_git.main = proof_git.base = proof_git.authorization = merged
        proof_git.prs[0].update(
            state="closed", merged=True, merged_at="2026-10-04T00:00:00Z", merge_commit_sha=merged
        )
    proof_git.allow_writes = True
    original_api = proof_git.api

    def concurrent_api(repository: str, token: str, path: str = "", **kwargs: object) -> object:
        result = original_api(repository, token, path, **kwargs)
        if path == "git/commits" and kwargs.get("method") == "POST":
            if changed == "main":
                proof_git.main = proof_git.commit(
                    {"README.md": "Concurrent"}, "Advance", (proof_git.main,)
                )
            elif changed == "issue":
                proof_git.issue_change = "different-change"
            elif changed == "ref":
                branch = (
                    proof_git.branch
                    if carrier == "first"
                    else validation_resource._replacement_branch(_CHANGE, 324)
                )
                proof_git.git(
                    "update-ref", f"refs/heads/{branch}", cast(dict[str, str], result)["sha"]
                )
            else:
                monkeypatch.setattr(materialization, "_current_authorized_request", lambda *_: None)
        return result

    monkeypatch.setattr(materialization, "_github_json", concurrent_api)
    monkeypatch.setattr(validation_resource, "_github_json", concurrent_api)
    if changed == "ref":
        with pytest.raises(CarrierRequired):
            _apply_git(proof_git)
    else:
        with pytest.raises(RuntimeError, match="changed|stale"):
            _apply_git(proof_git)
    assert "git/commits" in proof_git.mutations
    assert "git/refs" not in proof_git.mutations
