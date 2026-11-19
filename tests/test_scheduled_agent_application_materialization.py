"""Tests for the single application-owned materialization capability."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import replace
from email.message import Message
from pathlib import Path
from typing import cast

import pytest

import investment_strategy.scheduled_agent_application_bridge as application_bridge
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
    ("role", "action", "path"),
    [
        ("executor", "implement-change", "src/investment_strategy/example.py"),
        ("lead", "resolve-question", f"openspec/changes/{_CHANGE}/tasks.md"),
    ],
)
def test_formally_retired_change_can_request_application_owned_fresh_main_carrier(
    role: str, action: str, path: str
) -> None:
    source = WorkerRequest(169, role, action)
    payload = _payload(expected_change=_CHANGE)
    payload["branch"] = f"agent/{_CHANGE}-supersedes-408"
    payload["pr_number"] = None
    payload["base_sha"] = _BASE
    payload["files"] = [{"path": path, "blob_sha": _BLOB, "expected_sha": _BASE}]
    request = parse_materialization_payload(payload, source)

    assert request.pr_number is None
    assert request.branch == payload["branch"]
    assert request.base_sha == _BASE


@pytest.mark.parametrize(
    ("role", "action", "path"),
    [
        ("lead", "resolve-question", "src/investment_strategy/example.py"),
        ("lead", "propose-change", f"openspec/changes/{_CHANGE}/tasks.md"),
        ("reviewer", "review-openspec", f"openspec/changes/{_CHANGE}/tasks.md"),
    ],
)
def test_supersession_first_carrier_rejects_out_of_capability_or_action(
    role: str, action: str, path: str
) -> None:
    payload = _payload(expected_change=_CHANGE)
    payload["branch"] = f"agent/{_CHANGE}-supersedes-408"
    payload["pr_number"] = None
    payload["files"] = [{"path": path, "blob_sha": _BLOB, "expected_sha": _BASE}]
    with pytest.raises(ValueError, match="requires an exact PR|outside Action capability"):
        parse_materialization_payload(payload, WorkerRequest(169, role, action))


@pytest.mark.parametrize("formal", [True, False])
@pytest.mark.parametrize(
    ("role", "action"),
    [("executor", "implement-change"), ("lead", "resolve-question")],
)
def test_supersession_materializer_creates_only_one_fresh_main_child_and_requires_pr_carrier(
    monkeypatch: pytest.MonkeyPatch, formal: bool, role: str, action: str
) -> None:
    source = WorkerRequest(169, role, action)
    raw = _payload(expected_change=_CHANGE)
    raw["branch"] = f"agent/{_CHANGE}-supersedes-408"
    raw["pr_number"] = None
    if role == "lead":
        raw["files"] = [
            {
                "path": f"openspec/changes/{_CHANGE}/tasks.md",
                "blob_sha": _BLOB,
                "expected_sha": _BASE,
            }
        ]
    request = parse_materialization_payload(raw, source)
    created_head = "c" * 40
    refs: dict[str, str] = {}
    writes: list[tuple[str, object]] = []
    monkeypatch.setattr(
        materialization,
        "qualify_supersession_branch",
        lambda **_kwargs: formal,
    )
    monkeypatch.setattr(
        materialization,
        "_branch_head",
        lambda *_args: refs.get(request.branch),
    )
    monkeypatch.setattr(materialization, "_create_revision", lambda *_args, **_kwargs: created_head)
    monkeypatch.setattr(materialization, "_verify_revision", lambda *_args: None)
    monkeypatch.setattr(materialization, "_matching_prs", lambda *_args: [])

    def fake_github_json(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: object = None,
    ) -> object:
        writes.append((path, payload))
        if path != "git/refs" or method != "POST" or not isinstance(payload, dict):
            raise AssertionError(path)
        assert payload == {"ref": f"refs/heads/{request.branch}", "sha": created_head}
        refs[request.branch] = created_head
        return {"ref": request.branch}

    monkeypatch.setattr(materialization, "_github_json", fake_github_json)
    if formal:
        with pytest.raises(CarrierRequired) as raised:
            materialization._ensure_new_carrier(
                request,
                source,
                repository="owner/repo",
                token=_TOKEN,
                default_branch="main",
                authorization_revision=_BASE,
                supersession=True,
            )
        assert raised.value.plan.operation == "pull-request-create"
        assert raised.value.plan.expected["base_sha"] == _BASE
        assert refs == {request.branch: created_head}
        assert len(writes) == 1
    else:
        with pytest.raises(RuntimeError, match="no formal retirement authority"):
            materialization._ensure_new_carrier(
                request,
                source,
                repository="owner/repo",
                token=_TOKEN,
                default_branch="main",
                authorization_revision=_BASE,
                supersession=True,
            )
        assert not writes


@pytest.mark.parametrize(
    ("failure", "reason"),
    (
        (None, None),
        ("missing-branch", "pending branch is absent"),
        ("overlapping-main", "overlaps default advance"),
        ("unqualified-retirement", "lost formal retirement"),
        ("not-pending", "source dispatch is stale"),
        ("existing-pr", "already has a PR"),
    ),
)
def test_interrupted_supersession_branch_completes_only_missing_pr_after_disjoint_main_advance(
    monkeypatch: pytest.MonkeyPatch,
    failure: str | None,
    reason: str | None,
) -> None:
    source = WorkerRequest(169, "executor", "implement-change")
    payload = _payload(expected_change=_CHANGE)
    payload["branch"] = f"agent/{_CHANGE}-supersedes-408"
    payload["pr_number"] = None
    advanced_main = "d" * 40
    branch_head = "c" * 40
    writes: list[str] = []
    monkeypatch.setattr(
        materialization,
        "_pending_source_is_current",
        lambda *_args, **_kwargs: failure != "not-pending",
    )
    monkeypatch.setattr(materialization, "_current_default_branch", lambda *_args: "main")
    monkeypatch.setattr(materialization, "_ref_head_sha", lambda *_args: advanced_main)
    monkeypatch.setattr(
        materialization,
        "qualify_supersession_branch",
        lambda **_kwargs: failure != "unqualified-retirement",
    )
    monkeypatch.setattr(
        materialization,
        "_branch_head",
        lambda *_args: None if failure == "missing-branch" else branch_head,
    )
    monkeypatch.setattr(materialization, "_verify_revision", lambda *_args: None)
    monkeypatch.setattr(
        materialization,
        "_matching_prs",
        lambda *_args: [{"number": 414}] if failure == "existing-pr" else [],
    )
    monkeypatch.setattr(
        materialization,
        "_proof_ancestry",
        lambda *_args: (
            frozenset({f"openspec/changes/{_CHANGE}/proposal.md"})
            if failure == "overlapping-main"
            else frozenset()
        ),
    )

    def read(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        **_kwargs: object,
    ) -> object:
        if method != "GET":
            writes.append(path)
            raise AssertionError("interrupted carrier must not repeat a Git write")
        if path == "issues/169":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        raise AssertionError(path)

    monkeypatch.setattr(materialization, "_github_json", read)
    with pytest.raises(RuntimeError if reason else CarrierRequired, match=reason) as raised:
        materialization._construct_materialization(
            payload,
            source,
            repository="owner/repo",
            token=_TOKEN,
            current_revision=advanced_main,
            default_branch="main",
            allow_pending_continuation=True,
        )
    if reason is None:
        assert isinstance(raised.value, CarrierRequired)
        assert raised.value.plan.operation == "pull-request-create"
        assert raised.value.plan.expected["base_sha"] == advanced_main
    assert not writes


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


def _prove_git(
    fixture: _ProofGitRepository,
    *,
    accepted_intent: bool = False,
) -> materialization.MaterializationProof:
    return materialization.prove_materialization(
        fixture.payload(),
        fixture.source,
        repository=fixture.repository,
        token=_TOKEN,
        current_revision=fixture.main,
        default_branch="main",
        accepted_authorization_revision=fixture.authorization,
        accepted_intent=accepted_intent,
    )


def test_merged_carrier_new_correction_survives_github_compare_commit_cap(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ancestry/path proof does not need GitHub's complete 310-commit list."""

    historical_base = proof_git.base
    historical_head = proof_git.commit(
        {proof_git.path: "earlier correction"}, "Earlier Change", (historical_base,)
    )
    proof_git.set_head(historical_head)
    merged = proof_git.commit(
        {proof_git.path: "earlier correction"},
        "Merge earlier Change",
        (historical_base, historical_head),
    )
    proof_git.prs[0].update(
        state="closed", merged=True, merged_at="2026-10-03T00:00:00Z", merge_commit_sha=merged
    )
    proof_git.main = proof_git.commit(
        {"README.md": "new unrelated maintenance"}, "Later main", (merged,)
    )
    proof_git.base = proof_git.main
    proof_git.authorization = proof_git.main

    original_comparison = proof_git.comparison

    def capped_comparison(base: str, revision: str) -> dict[str, object]:
        comparison = original_comparison(base, revision)
        if (base, revision) == (historical_base, proof_git.main):
            # Real GitHub: ahead_by=310, commits=250, but a complete 2-path diff.
            comparison["ahead_by"] = 310
            comparison["total_commits"] = 310
            comparison["commits"] = [{"sha": f"{number:040x}"} for number in range(250)]
        return comparison

    monkeypatch.setattr(proof_git, "comparison", capped_comparison)
    proof = _prove_git(proof_git)

    assert proof.disposition == "INCOMPLETE", proof
    assert proof.application_request is not None
    assert proof_git.mutations == []
    # A witness enumerator still may not silently treat 250 of 310 as complete.
    with pytest.raises(materialization._IncompleteGitHubObservation):
        materialization._proof_comparison(
            proof_git.repository, _TOKEN, historical_base, proof_git.main
        )


@pytest.mark.parametrize("invalid", ["capped-files", "wrong-merge-base"])
def test_long_history_ancestry_preserves_missing_file_and_lineage_guards(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    invalid: str,
) -> None:
    proof_git.main = proof_git.commit(
        {"README.md": "later unrelated maintenance"}, "Later main", (proof_git.base,)
    )
    original_comparison = proof_git.comparison

    def incomplete_comparison(base: str, revision: str) -> dict[str, object]:
        comparison = original_comparison(base, revision)
        comparison["ahead_by"] = 310
        comparison["total_commits"] = 310
        comparison["commits"] = [{"sha": f"{number:040x}"} for number in range(250)]
        if invalid == "capped-files":
            comparison["files"] = [
                {"filename": f"file-{number}", "status": "modified"} for number in range(300)
            ]
        else:
            comparison["merge_base_commit"] = {"sha": "f" * 40}
        return comparison

    monkeypatch.setattr(proof_git, "comparison", incomplete_comparison)
    with pytest.raises((materialization._IncompleteGitHubObservation, RuntimeError)):
        materialization._proof_ancestry(
            proof_git.repository, _TOKEN, proof_git.base, proof_git.main
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
    # Truncated comparison data proves neither missing work nor a conflict.
    expected = "UNKNOWN" if failure == "incomplete-compare" else "CONTRADICTORY"
    assert proof.disposition == expected, proof
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


def _apply_git(
    fixture: _ProofGitRepository,
    *,
    payload: dict[str, object] | None = None,
    accepted_intent: bool = False,
) -> ValidationResourceTarget:
    return materialization.apply_materialization(
        fixture.payload() if payload is None else payload,
        fixture.source,
        repository=fixture.repository,
        token=_TOKEN,
        current_revision=fixture.main,
        default_branch="main",
        accepted_authorization_revision=fixture.authorization,
        accepted_intent=accepted_intent,
    )


def _prove_payload_git(
    fixture: _ProofGitRepository,
    payload: dict[str, object],
    *,
    accepted_intent: bool = False,
) -> materialization.MaterializationProof:
    return materialization.prove_materialization(
        payload,
        fixture.source,
        repository=fixture.repository,
        token=_TOKEN,
        current_revision=fixture.main,
        default_branch="main",
        accepted_authorization_revision=fixture.authorization,
        accepted_intent=accepted_intent,
    )


def test_pending_supersession_read_only_proof_uses_real_git_witness_after_disjoint_advance(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = proof_git
    fixture.source = WorkerRequest(322, "executor", "implement-change")
    fixture.routing = fixture.source.action
    fixture.branch = f"agent/{_CHANGE}-supersedes-408"
    fixture.path = "src/investment_strategy/pending_supersession.py"
    fixture.first_create = True
    fixture.prs.clear()
    child = fixture.commit({fixture.path: "accepted content"}, fixture.message, (fixture.base,))
    fixture.git("update-ref", f"refs/heads/{fixture.branch}", child)
    fixture.main = fixture.commit({"docs/other.md": "unrelated"}, "Unrelated", (fixture.base,))
    monkeypatch.setattr(materialization, "qualify_supersession_branch", lambda **_kw: True)
    monkeypatch.setattr(
        materialization, "_pending_source_is_current", lambda *_args, **_kwargs: True
    )
    request = fixture.payload()
    proof = materialization.prove_materialization(
        request,
        fixture.source,
        repository=fixture.repository,
        token=_TOKEN,
        current_revision=fixture.main,
        default_branch="main",
        accepted_authorization_revision=fixture.base,
        allow_pending_continuation=True,
        accepted_intent=True,
    )
    assert proof.disposition == "INCOMPLETE", proof
    assert fixture.mutations == []


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


def test_committed_executor_witness_is_not_reopened_by_later_default_overlap(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real Git graph: a committed implementation is not an unmerged PR write request."""

    proof_git.source = WorkerRequest(322, "executor", "implement-change")
    proof_git.path = "src/investment_strategy/scheduled_agent_effects.py"
    proof_git.branch = f"agent/{_CHANGE}"
    proof_git.base = proof_git.commit(
        {proof_git.path: "preimage"}, "Executor base", (proof_git.base,)
    )
    proof_git.authorization = proof_git.base
    proof_git.main = proof_git.base
    proof_git.desired = proof_git.blob("accepted implementation")
    proof_git.prs.clear()
    proof_git.install_pr(324, proof_git.branch, proof_git.base)
    accepted = proof_git.commit(
        {proof_git.path: "accepted implementation"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    proof_git.main = proof_git.commit(
        {proof_git.path: "later Application repair"}, "Fix completion", (proof_git.base,)
    )
    proof_git.routing = "review-implementation"
    # This test targets the materialization owner, not the independent
    # implementation carrier review gate.
    monkeypatch.setattr(
        materialization, "_qualified_implementation_decision", lambda *_a, **_k: None
    )
    monkeypatch.setattr(materialization, "_open_pr_payload", lambda **_k: proof_git.prs[0])

    def prove(*, committed: bool) -> materialization.MaterializationProof:
        return materialization.prove_materialization(
            proof_git.payload(),
            proof_git.source,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            default_branch="main",
            accepted_authorization_revision=proof_git.authorization,
            allow_pending_continuation=True,
            accepted_successor_routing=("reviewer", "review-implementation"),
            accepted_intent=True,
            committed_formal_result=committed,
        )

    precommit = prove(committed=False)
    assert precommit.disposition == "CONTRADICTORY", precommit
    assert precommit.reason == "materialization required ancestry is broken"
    completed = prove(committed=True)
    assert completed.disposition == "COMPLETE", completed
    assert completed.witness is not None and completed.witness.revision == accepted
    assert completed.target is not None and completed.target.revision == accepted
    assert proof_git.mutations == []

    # Exercise the actual Application consequence owner, including the
    # already-qualified formal-result correlation and bounded checkpoint.
    # Neither the consequence function nor the materialization observer is stubbed.
    from investment_strategy import scheduled_agent_effects as effects

    monkeypatch.setattr(effects, "_github_json", proof_git.api)
    checkpoint = "\n".join(
        (
            "SLICE_CHECKPOINT",
            "Workflow: #322",
            f"Change: {_CHANGE}",
            "Action: implement-change",
            "Role: executor",
            "Completed-Tasks: 6.1,6.2",
            f"Revision: {proof_git.base}",
            "Application-Correlation: settled-correlation",
            "Gate-Evidence: exact-head validation",
            "Remaining-Approved-Boundary: implementation review and merge",
        )
    )
    raw = json.dumps(
        {
            "issue_number": 322,
            "role": "executor",
            "action": "implement-change",
            "change": _CHANGE,
            "result_kind": "ready",
            "evidence_ref": "accepted-implementation",
            "result_content": "Completed implementation slice.",
            "requested_effects": [
                {"kind": "github-mutation", "payload_json": json.dumps(proof_git.payload())},
                {
                    "kind": "issue-comment",
                    "payload_json": json.dumps({"issue_number": 322, "body": checkpoint}),
                },
            ],
        }
    )
    correlation = effects.formal_application_correlation(
        proof_git.source,
        change=_CHANGE,
        result_kind="ready",
        current_revision=proof_git.main,
        request_comment_id=123,
    )

    def consequence(*, committed: bool, observed_correlation: str) -> bool:
        return effects.consequence_postconditions_complete(
            raw,
            source=proof_git.source,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            authorized_change=_CHANGE,
            request_comment_id=123,
            accepted_authorization_revision=proof_git.authorization,
            allow_pending_continuation=True,
            allow_accepted_successor=True,
            accepted_intent=True,
            observed_application_correlation=observed_correlation,
            formal_result_observed=committed,
        )

    assert not consequence(committed=False, observed_correlation=correlation)
    assert consequence(committed=True, observed_correlation=correlation)
    assert not consequence(committed=True, observed_correlation=correlation + "-stale")
    assert proof_git.mutations == []

    # The same mode cannot turn a different current carrier into the accepted result.
    forged = proof_git.commit(
        {proof_git.path: "unaccepted content"}, "Unaccepted overwrite", (proof_git.base,)
    )
    proof_git.set_head(forged)
    assert prove(committed=True).disposition != "COMPLETE"
    assert proof_git.mutations == []


@pytest.mark.parametrize(
    "formal_state", ["committed", "absent", "wrong-request", "wrong-revision", "unqualified"]
)
def test_native_application_bridge_uses_only_the_exact_committed_executor_result(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    formal_state: str,
) -> None:
    """The native Bridge entrypoint must prove, not assume, the formal commit boundary."""
    import base64
    import hashlib
    import sys
    from datetime import date

    from investment_strategy import scheduled_agent_application_bridge as bridge
    from investment_strategy import scheduled_agent_effects as effects
    from investment_strategy.scheduled_agent_checkin import checkin_title
    from investment_strategy.scheduled_agent_effects import (
        ApplicationDecisionRecord,
        ApplyResult,
        EffectBatch,
        formal_application_correlation,
    )
    from investment_strategy.scheduled_agent_runtime import (
        GitHubIssueObservation,
        acquire_dispatch_preflight,
    )
    from investment_strategy.workflow_dispatch import ObservationProvenance

    source = WorkerRequest(322, "executor", "implement-change")
    proof_git.source = source
    proof_git.path = "src/investment_strategy/scheduled_agent_effects.py"
    proof_git.branch = f"agent/{_CHANGE}"
    proof_git.base = proof_git.commit(
        {proof_git.path: "preimage"}, "Executor base", (proof_git.base,)
    )
    proof_git.authorization = proof_git.base
    proof_git.main = proof_git.base
    proof_git.desired = proof_git.blob("accepted implementation")
    proof_git.prs.clear()
    proof_git.install_pr(324, proof_git.branch, proof_git.base)
    accepted_revision = proof_git.commit(
        {proof_git.path: "accepted implementation"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted_revision)
    proof_git.main = proof_git.commit(
        {proof_git.path: "later Application repair"}, "Fix completion", (proof_git.base,)
    )
    proof_git.routing = "review-implementation"
    monkeypatch.setattr(
        materialization, "_qualified_implementation_decision", lambda *_a, **_k: None
    )
    monkeypatch.setattr(materialization, "_open_pr_payload", lambda **_k: proof_git.prs[0])

    worker = {
        "issue_number": 322,
        "role": "executor",
        "action": "implement-change",
        "change": _CHANGE,
        "result_kind": "ready",
        "evidence_ref": "accepted-implementation",
        "result_content": "Implementation was accepted.",
        "requested_effects": [
            {"kind": "github-mutation", "payload_json": json.dumps(proof_git.payload())},
        ],
    }
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    request_id = 123
    request_body = "\n".join(
        (
            "EFFECT_REQUEST",
            f"Authorization-Revision: {proof_git.authorization}",
            "Worker-Result-B64: " + base64.b64encode(raw.encode()).decode(),
        )
    )
    accepted = ApplicationDecisionRecord(
        request_comment_id=request_id,
        request_body_sha256=hashlib.sha256(request_body.encode()).hexdigest(),
        authorization_revision=proof_git.authorization,
        issue_number=322,
        role=source.role,
        action=source.action,
        change=_CHANGE,
        result_kind="ready",
        disposition="ACCEPTED",
        worker_result_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        raw_worker_result=raw,
        reason="accepted",
    )
    event_file = tmp_path / "event.json"
    event_file.write_text(
        json.dumps(
            {
                "action": "created",
                "issue": {
                    "number": 412,
                    "title": checkin_title(date(2026, 11, 2)),
                    "state": "open",
                    "labels": [],
                },
                "comment": {
                    "id": request_id,
                    "body": request_body,
                    "user": {"login": "proof-owner"},
                    "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
                },
            }
        ),
        encoding="utf-8",
    )
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="ready",
        current_revision=proof_git.authorization,
        request_comment_id=request_id if formal_state != "wrong-request" else request_id + 1,
    )
    formal_revision = proof_git.base if formal_state == "wrong-revision" else accepted_revision
    formal_body = "\n".join(
        (
            "ACTION_RESULT",
            "Workflow: #322",
            f"Change: {_CHANGE}",
            "Role: executor",
            "Action: implement-change",
            "Result: READY",
            f"Revision: {formal_revision}",
            f"Default-Branch-Revision: {proof_git.authorization}",
            f"Application-Correlation: {correlation}",
            "Repository-derived successor: Reviewer / review-implementation",
            "Evidence: accepted implementation",
        )
    )
    comments = (
        []
        if formal_state == "absent"
        else [
            {
                "id": 456,
                "body": formal_body,
                "user": {"login": "github-actions[bot]"},
                "performed_via_github_app": {"slug": "github-actions"},
            }
        ]
    )
    timeline = [
        {"id": 456, "event": "commented", "created_at": "2026-11-02T01:00:00Z"},
        {
            "id": 457,
            "event": "unlabeled",
            "label": {"name": "action:implement-change"},
            "created_at": "2026-11-02T01:01:00Z",
        },
        {
            "id": 458,
            "event": "labeled",
            "label": {"name": "action:review-implementation"},
            "created_at": "2026-11-02T01:02:00Z",
        },
    ]
    if formal_state == "unqualified":
        timeline = timeline[:-1]

    def github_read(repository: str, token: str, path: str, **kwargs: object) -> object:
        if path == "issues/322":
            return proof_git.api(repository, token, path, **kwargs)
        if path.startswith("issues/322/comments?"):
            return comments
        if path.startswith("issues/322/timeline"):
            return timeline
        return proof_git.api(repository, token, path, **kwargs)

    monkeypatch.setattr(bridge, "_github_json", github_read)
    monkeypatch.setattr(effects, "_github_json", proof_git.api)
    monkeypatch.setattr(bridge, "_application_decision_for_request", lambda **_kw: accepted)
    monkeypatch.setattr(bridge, "_accepted_worker_result_for_continuation", lambda **_kw: raw)
    monkeypatch.setattr(bridge, "_fresh_application_worker_result", lambda *_a, **_kw: raw)
    monkeypatch.setattr(bridge, "_accepted_checkpoint_already_durable", lambda *_a, **_kw: True)
    monkeypatch.setattr(bridge, "_record_application_exception", lambda *_a: None)
    monkeypatch.setattr(bridge, "_write_application_recovery_evidence", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_a: acquire_dispatch_preflight(
            observations=(
                GitHubIssueObservation(
                    issue_number=322,
                    change=_CHANGE,
                    routing=("reviewer", "review-implementation"),
                    state="open",
                    created_order=1,
                    authoritative=True,
                    current_state_provenance=ObservationProvenance.QUALIFIED,
                ),
            ),
            source_total_count=1,
            incomplete_results=False,
            exhausted=True,
            human_authorized=True,
        ),
    )
    applied: list[dict[str, object]] = []

    def controlled_stop(_raw: str, **kwargs: object) -> tuple[EffectBatch, ApplyResult]:
        applied.append(kwargs)
        return EffectBatch(source=source, effects=()), ApplyResult(False, "controlled-stop")

    monkeypatch.setattr(bridge, "run_guarded_effect_application", controlled_stop)
    monkeypatch.setenv("GITHUB_REPOSITORY", proof_git.repository)
    monkeypatch.setenv("GITHUB_TOKEN", _TOKEN)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scheduled_agent_application_bridge",
            "--event-path",
            str(event_file),
            "--revision",
            proof_git.main,
            "--default-branch",
            "main",
            "--run-attempt",
            "2",
        ],
    )
    if formal_state == "committed":
        assert bridge.main() == 0
        assert applied == []  # Formally committed history must not replay effects.
    else:
        reason = (
            "committed implementation witness differs from formal result"
            if formal_state == "wrong-revision"
            else "materialization required ancestry is broken"
        )
        with pytest.raises(RuntimeError, match=reason):
            bridge.main()
        assert applied == []
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


def test_accepted_branch_only_consequence_yields_pr_only_plan_after_disjoint_main_advance(
    proof_git: _ProofGitRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The original Git effect already made the accepted commit/ref, not its PR."""
    _first_git_intent(proof_git)
    original_head = _accepted_git_carrier(proof_git)
    proof_git.prs.clear()
    proof_git.main = proof_git.commit({"README.md": "disjoint advance"}, "Main", (proof_git.main,))
    monkeypatch.setattr(materialization, "_pending_source_is_current", lambda *_a, **_k: True)
    proof = materialization.prove_materialization(
        proof_git.payload(),
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        accepted_authorization_revision=proof_git.authorization,
        allow_pending_continuation=True,
        accepted_intent=True,
    )
    assert proof.disposition == "INCOMPLETE"
    plan = proof.carrier_plan
    assert plan is not None
    assert plan.operation == "pull-request-create"
    assert plan.expected["head_sha"] == original_head
    assert plan.expected["base_sha"] == proof_git.main
    assert plan.expected["existing_pr_count"] == 0
    assert (
        application_bridge.AcceptedPostEffectProof("MISSING_PR", "missing PR", plan).continuation
        == "CONTINUE"
    )
    assert proof_git.mutations == []

    # Only a native carrier PR consequence is missing. Never reconstruct the
    # original Git commit/ref, and the canonical proof becomes COMPLETE after it.
    proof_git.install_pr(439, proof_git.branch, original_head)
    completed = materialization.prove_materialization(
        proof_git.payload(),
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        accepted_authorization_revision=proof_git.authorization,
        allow_pending_continuation=True,
        accepted_intent=True,
    )
    assert completed.disposition == "COMPLETE"
    assert proof_git.mutations == []


def test_unaccepted_branch_only_observation_does_not_authorize_pr_plan(
    proof_git: _ProofGitRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    _first_git_intent(proof_git)
    _accepted_git_carrier(proof_git)
    proof_git.prs.clear()
    monkeypatch.setattr(materialization, "_pending_source_is_current", lambda *_a, **_k: True)
    proof = materialization.prove_materialization(
        proof_git.payload(),
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        allow_pending_continuation=True,
        accepted_intent=False,
    )
    assert proof.disposition == "INCOMPLETE"
    assert proof.carrier_plan is None
    assert proof_git.mutations == []


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate-pr",
        "foreign-pr",
        "wrong-ref",
        "changed-content",
        "overlap",
        "incomplete-compare",
        "missing-branch",
    ],
)
def test_accepted_missing_pr_does_not_plan_on_stale_or_ambiguous_github_evidence(
    proof_git: _ProofGitRepository, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    _first_git_intent(proof_git)
    accepted = _accepted_git_carrier(proof_git)
    proof_git.prs.clear()
    proof_git.main = proof_git.commit({"README.md": "advance"}, "Main", (proof_git.main,))
    monkeypatch.setattr(materialization, "_pending_source_is_current", lambda *_a, **_k: True)
    if damage == "duplicate-pr":
        proof_git.install_pr(901, proof_git.branch, accepted)
        proof_git.install_pr(902, proof_git.branch, accepted)
    elif damage == "foreign-pr":
        proof_git.install_pr(901, proof_git.branch, accepted)
        proof_git.prs[0]["body"] = "Refs #999"
    elif damage == "wrong-ref":
        proof_git.failure = "wrong-ref"
    elif damage == "changed-content":
        proof_git.git("update-ref", f"refs/heads/{proof_git.branch}", proof_git.base)
    elif damage == "overlap":
        proof_git.main = proof_git.commit({proof_git.path: "overlap"}, "Overlap", (proof_git.main,))
    elif damage == "incomplete-compare":
        proof_git.failure = "incomplete-compare"
    elif damage == "missing-branch":
        proof_git.git("update-ref", "-d", f"refs/heads/{proof_git.branch}")
    proof = materialization.prove_materialization(
        proof_git.payload(),
        proof_git.source,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        accepted_authorization_revision=proof_git.authorization,
        allow_pending_continuation=True,
        accepted_intent=True,
    )
    assert proof.disposition != "COMPLETE", proof
    plan = proof.carrier_plan
    assert plan is None
    assert proof_git.mutations == []


@pytest.mark.parametrize("read_fault", [None, 500, 502, 503, 504, "timeout"])
@pytest.mark.parametrize("failure_stage", ["branch", "revision"])
def test_accepted_original_effect_recovery_classifies_real_git_then_completes_without_replay(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    read_fault: int | str | None,
    failure_stage: str,
) -> None:
    """The immutable original Git Effect survives a derived formal result.

    Real Git commit/ref objects are already durable, but no PR exists. A
    temporary GitHub read failure cannot trigger a write, and the next fresh
    observation must produce the exact missing-PR-only native carrier plan.
    """
    from urllib.error import HTTPError

    _first_git_intent(proof_git)
    accepted_head = _accepted_git_carrier(proof_git)
    proof_git.prs.clear()
    proof_git.main = proof_git.commit({"README.md": "disjoint advance"}, "Main", (proof_git.main,))
    monkeypatch.setattr(materialization, "_pending_source_is_current", lambda *_a, **_k: True)
    original_effects = [
        {"kind": "github-mutation", "payload_json": json.dumps(proof_git.payload())}
    ]
    original = {
        "issue_number": proof_git.source.issue_number,
        "role": proof_git.source.role,
        "action": proof_git.source.action,
        "change": "unset",
        "result_kind": "ready-for-openspec-review",
        "evidence_ref": "issuecomment-accepted-original",
        "result_content": "accepted first-carrier materialization",
        "requested_effects": original_effects,
    }
    raw = json.dumps(original, sort_keys=True)
    projected = {
        **original,
        "requested_effects": [
            *original_effects,
            {
                "kind": "issue-comment",
                "payload_json": json.dumps({"issue_number": 322, "body": "formal result"}),
            },
        ],
    }
    identity = application_bridge._accepted_activation_effect_identity(
        raw,
        source=proof_git.source,
        change="unset",
        projected_raw=json.dumps(projected, sort_keys=True),
    )
    assert identity.disposition == "EXACT"
    assert identity.projected_index == 0

    record = application_bridge.ApplicationDecisionRecord(
        request_comment_id=100,
        request_body_sha256="0" * 64,
        authorization_revision=proof_git.authorization,
        issue_number=proof_git.source.issue_number,
        role=proof_git.source.role,
        action=proof_git.source.action,
        change="unset",
        result_kind="ready-for-openspec-review",
        disposition="ACCEPTED",
        worker_result_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        raw_worker_result=raw,
        reason="accepted",
    )
    monkeypatch.setattr(
        application_bridge, "_accepted_worker_result_for_continuation", lambda **_k: raw
    )

    def observe() -> application_bridge.AcceptedPostEffectProof:
        return application_bridge._observe_accepted_post_effect_result(
            record=record,
            source=proof_git.source,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            default_branch="main",
        )

    if read_fault is not None:
        original_reader = materialization._github_json
        raised = False

        def intermittent_reader(
            repo: str,
            token: str,
            path: str,
            *,
            method: str = "GET",
            payload: Mapping[str, object] | None = None,
            allow_not_found: bool = False,
        ) -> object:
            nonlocal raised
            prefix = "git/ref/heads/" if failure_stage == "branch" else "compare/"
            if not raised and path.startswith(prefix):
                raised = True
                if read_fault == "timeout":
                    raise TimeoutError("transient GitHub read timeout")
                raise HTTPError(path, int(read_fault), "transient", Message(), None)
            return original_reader(
                repo,
                token,
                path,
                method=method,
                payload=payload,
                allow_not_found=allow_not_found,
            )

        monkeypatch.setattr(materialization, "_github_json", intermittent_reader)
        first = observe()
        assert first.disposition == "INDETERMINATE"
        assert first.carrier_plan is None
        assert raised
        monkeypatch.setattr(materialization, "_github_json", original_reader)

    missing = observe()
    assert missing.disposition == "MISSING_PR", missing
    assert missing.carrier_plan is not None
    assert missing.carrier_plan.operation == "pull-request-create"
    assert missing.carrier_plan.expected["head_sha"] == accepted_head
    assert proof_git.mutations == []

    proof_git.install_pr(439, proof_git.branch, accepted_head)
    assert observe().disposition == "COMPLETE"
    assert proof_git.mutations == []


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


def test_new_materialization_rejects_wrong_preimage_before_acceptance(
    proof_git: _ProofGitRepository,
) -> None:
    payload = proof_git.payload()
    raw_files = cast(list[dict[str, object]], payload["files"])
    raw_files[0]["expected_sha"] = "f" * 40

    proof = _prove_payload_git(proof_git, payload)

    assert proof.disposition == "CONTRADICTORY", proof
    assert proof.reason == "materialization missing work preimage is stale"
    assert proof_git.mutations == []


def test_accepted_zero_write_failure_preserves_exact_declared_base_preimage(
    proof_git: _ProofGitRepository,
) -> None:
    payload = proof_git.payload()
    raw_files = cast(list[dict[str, object]], payload["files"])
    expected_preimage = raw_files[0]["expected_sha"]

    mismatched_payload = {**payload, "files": [{**raw_files[0], "expected_sha": "f" * 40}]}
    with pytest.raises(RuntimeError, match="materialization missing work preimage is stale"):
        _apply_git(proof_git, payload=mismatched_payload, accepted_intent=True)
    assert proof_git.mutations == []

    proof = _prove_payload_git(proof_git, payload, accepted_intent=True)
    assert proof.disposition == "INCOMPLETE", proof
    assert proof.application_request is not None
    assert proof.application_request.files[0].expected_sha == expected_preimage

    proof_git.allow_writes = True
    with pytest.raises(CarrierRequired) as raised:
        _apply_git(proof_git, payload=payload, accepted_intent=True)
    plan = raised.value.plan
    assert plan.force is False
    assert plan.expected["ref_sha"] == proof_git.base
    revision = cast(str, plan.requested["sha"])
    proof_git.set_head(revision)

    completed = _prove_payload_git(proof_git, payload, accepted_intent=True)
    assert completed.disposition == "COMPLETE", completed
    assert completed.witness is not None and completed.witness.revision == revision
    assert raw_files[0]["expected_sha"] == expected_preimage


def test_accepted_preimage_recovery_rejects_changed_carrier_path(
    proof_git: _ProofGitRepository,
) -> None:
    payload = proof_git.payload()
    cast(list[dict[str, object]], payload["files"])[0]["expected_sha"] = "f" * 40
    changed = proof_git.commit(
        {proof_git.path: "unaccepted path change"},
        "Unaccepted path change",
        (proof_git.base,),
    )
    proof_git.set_head(changed)

    proof = _prove_payload_git(proof_git, payload, accepted_intent=True)

    assert proof.disposition == "CONTRADICTORY", proof
    assert proof.reason == "materialization missing work preimage is stale"
    assert proof_git.mutations == []


def test_accepted_write_commit_recovers_exact_parent_preimage(
    proof_git: _ProofGitRepository,
) -> None:
    payload = proof_git.payload()
    cast(list[dict[str, object]], payload["files"])[0]["expected_sha"] = "f" * 40
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)

    proof = _prove_payload_git(proof_git, payload, accepted_intent=True)

    assert proof.disposition == "COMPLETE", proof
    assert proof.witness is not None and proof.witness.revision == accepted
    assert proof.application_request is not None
    assert (
        proof.application_request.files[0].expected_sha
        == proof_git.entries(proof_git.base)[proof_git.path]["sha"]
    )
    assert cast(list[dict[str, object]], payload["files"])[0]["expected_sha"] == "f" * 40
    assert proof_git.mutations == []


def test_accepted_seven_file_manifest_proves_six_effective_changes(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A reviewed, unchanged task checkpoint is not a seventh Git path delta."""

    proof_git.source = WorkerRequest(322, "executor", "implement-change")
    proof_git.routing = "implement-change"
    monkeypatch.setattr(
        materialization, "_qualified_implementation_decision", lambda *_args, **_kwargs: None
    )
    tasks_path = f"openspec/changes/{_CHANGE}/tasks.md"
    unchanged_tasks = "- [x] Previously accepted task\n"
    base = proof_git.commit({tasks_path: unchanged_tasks}, "Earlier checkpoint", (proof_git.base,))
    proof_git.base = base
    proof_git.authorization = base
    proof_git.main = base
    proof_git.set_head(base)

    changed_contents = {
        "src/investment_strategy/scheduled_agent_application_bridge.py": "accepted A",
        "src/investment_strategy/scheduled_agent_effects.py": "accepted B",
        "src/investment_strategy/scheduled_agent_merge_acceptance.py": "accepted C",
        "src/investment_strategy/scheduled_agent_validation_resource.py": "accepted D",
        "tests/test_scheduled_agent_application_bridge.py": "test A",
        "tests/test_scheduled_agent_effects.py": "test B",
    }
    payload = proof_git.payload()
    payload["files"] = [
        {
            "path": path,
            "blob_sha": proof_git.blob(content),
            "expected_sha": proof_git.entries(base).get(path, {}).get("sha"),
        }
        for path, content in changed_contents.items()
    ]
    tasks_sha = proof_git.entries(base)[tasks_path]["sha"]
    cast(list[dict[str, object]], payload["files"]).append(
        {"path": tasks_path, "blob_sha": tasks_sha, "expected_sha": tasks_sha}
    )

    accepted = proof_git.commit(changed_contents, proof_git.message, (base,))
    proof_git.set_head(accepted)
    proof = _prove_payload_git(proof_git, payload, accepted_intent=True)

    assert proof.disposition == "COMPLETE", proof
    assert proof.witness is not None and proof.witness.revision == accepted
    assert proof_git.mutations == []


@pytest.mark.parametrize(
    ("result_kind", "successor_action", "successor_role", "predecessor_failure"),
    [
        ("blocked", "implement-change", "executor", None),
        ("spec-blocker", "resolve-question", "lead", None),
        ("blocked", "implement-change", "executor", "download"),
        ("blocked", "implement-change", "executor", "digest"),
        ("blocked", "implement-change", "executor", "trigger"),
        ("blocked", "implement-change", "executor", "accepted"),
    ],
)
def test_435_accepted_original_git_witness_reobserves_without_replay(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    result_kind: str,
    successor_action: str,
    successor_role: str,
    predecessor_failure: str | None,
) -> None:
    """R9/F2: the native #435-shaped Effect has one immutable Git witness.

    This uses actual Git objects and the real shared Application Effect
    observer. It does not mock the materialization result or persist any
    Formal/Successor artifact: those have separate Application owners.
    """
    import investment_strategy.scheduled_agent_effects as effects

    change = "restore-t1-dispatch-artifact-consumption"
    original = WorkerRequest(435, "executor", "implement-change")
    proof_git.repository = "royhsu-work/investment-strategy"
    proof_git.source = original
    proof_git.routing = original.action
    proof_git.issue_change = change
    proof_git.branch = f"agent/{change}"
    proof_git.message = (
        "test: qualify exact T1 Artifact reads [t1-native-artifact-diagnostic] (Refs #435)"
    )
    pr = proof_git.prs[0]
    pr["number"] = 437
    pr["title"] = f"OpenSpec: {change}"
    pr["body"] = "Refs #435"
    cast(dict[str, object], pr["head"])["ref"] = proof_git.branch
    # The fixture was initialized under its synthetic repository identity.
    # Rebind both native PR repository fields before proving this #435 carrier.
    cast(dict[str, object], pr["head"])["repo"] = {"full_name": proof_git.repository}
    cast(dict[str, object], pr["base"])["repo"] = {"full_name": proof_git.repository}

    paths = (
        "src/investment_strategy/scheduled_agent_carrier.py",
        "src/investment_strategy/scheduled_agent_dispatch_result.py",
        "src/investment_strategy/scheduled_agent_idle_admission.py",
        "tests/test_scheduled_agent_dispatch_result.py",
        "tests/test_scheduled_agent_idle_admission.py",
        ".github/workflows/quality.yml",
        ".github/scripts/diagnose_dispatch_artifact.py",
    )
    proposal_path = f"openspec/changes/{change}/proposal.md"
    preimage = {path: f"historical preimage {index}" for index, path in enumerate(paths[:-1])}
    preimage[proposal_path] = "Approved T1 OpenSpec proposal"
    # The accepted implementation commit is a child of an existing Change
    # carrier; its historical PR already contains the OpenSpec definition.
    base = proof_git.commit(preimage, "Existing T1 carrier baseline", ())
    proof_git.base = base
    proof_git.authorization = base
    proof_git.main = base
    proof_git.set_head(base)
    cast(dict[str, object], pr["base"])["sha"] = base

    desired = {path: f"accepted T1 content {index}" for index, path in enumerate(paths)}
    payload = {
        "issue_number": 435,
        "operation": "application-materialize",
        "expected_change": change,
        "change": change,
        "branch": proof_git.branch,
        "base_sha": base,
        "message": proof_git.message,
        "pr_number": 437,
        "files": [
            {
                "path": path,
                "blob_sha": proof_git.blob(content),
                "expected_sha": proof_git.entries(base).get(path, {}).get("sha"),
            }
            for path, content in desired.items()
        ],
    }
    result = {
        "_semantic_intent_version": 2,
        "issue_number": 435,
        "role": "executor",
        "action": "implement-change",
        "change": change,
        "result_kind": result_kind,
        "evidence_ref": "https://github.com/royhsu-work/investment-strategy/pull/437",
        "result_content": "Accepted seven-file implementation diagnostic; no checkpoint.",
        # Phase A canonicalizes the accepted payload_json, as in the real
        # #435 APPLICATION_DECISION. The earlier WORKER_RESULT transport
        # may use a different key order; Phase B compares ACCEPTED bytes.
        "requested_effects": [
            {"kind": "github-mutation", "payload_json": json.dumps(payload, sort_keys=True)}
        ],
    }
    raw = json.dumps(result, sort_keys=True)
    accepted = application_bridge.ApplicationDecisionRecord(
        request_comment_id=6796616018,
        request_body_sha256="a" * 64,
        authorization_revision=base,
        issue_number=435,
        role=original.role,
        action=original.action,
        change=change,
        result_kind=result_kind,
        disposition="ACCEPTED",
        worker_result_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        raw_worker_result=raw,
        reason="accepted",
    )

    # Recreate the production transport/decision bytes once, instead of a
    # detached accepted-decision hash. The accepted intent is immutable.
    source_body = application_bridge._render_accepted_application_wire(
        application_bridge.ApplicationRequest(
            authorization_revision=base,
            raw_worker_result=raw,
            dispatch_correlation=application_bridge.dispatch_correlation_for(
                proof_git.repository, original, base
            ),
        )
    )
    accepted = replace(
        accepted, request_body_sha256=hashlib.sha256(source_body.encode()).hexdigest()
    )
    decision_body = effects._APPLICATION_DECISION_WIRE.render(
        {
            "Request-Comment": str(accepted.request_comment_id),
            "Request-Body-SHA256": accepted.request_body_sha256,
            "Authorization-Revision": accepted.authorization_revision,
            "Issue": str(accepted.issue_number),
            "Role": accepted.role,
            "Action": accepted.action,
            "Change": accepted.change,
            "Result-Kind": accepted.result_kind,
            "Disposition": accepted.disposition,
            "Worker-Result-SHA256": accepted.worker_result_sha256,
            "Application-Intent-B64": base64.b64encode(raw.encode()).decode(),
            "Reason": accepted.reason,
        }
    )
    assert effects.parse_application_decision(decision_body) == accepted
    decision_digest = hashlib.sha256(decision_body.encode()).hexdigest()
    source_comment = {
        "id": accepted.request_comment_id,
        "body": source_body,
        "created_at": "2026-11-11T13:05:53Z",
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }
    decision_comment = {
        "id": 6796662999,
        "body": decision_body,
        "created_at": "2026-11-11T13:08:00Z",
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }

    # Establish the current Executor route using an earlier Actions Review
    # and its durable label event. The real qualifier must inspect both.
    import investment_strategy.scheduled_agent_runtime as runtime

    prior_source = WorkerRequest(435, "reviewer", "review-implementation")
    prior_correlation = application_bridge.formal_application_correlation(
        prior_source,
        change=change,
        result_kind="findings",
        current_revision=proof_git.main,
        request_comment_id=89989,
    )
    prior_body = "\n".join(
        (
            "REVIEW_RESULT",
            "Workflow: #435",
            f"Change: {change}",
            "Role: reviewer",
            "Action: review-implementation",
            "Result: FINDINGS",
            f"Revision: {proof_git.main}",
            f"Default-Branch-Revision: {proof_git.main}",
            f"Application-Correlation: {prior_correlation}",
            "Repository-derived successor: Executor / implement-change",
            "Evidence: one further implementation slice required",
        )
    )
    prior_comment: dict[str, object] = {
        "id": 89990,
        "body": prior_body,
        "created_at": "2026-11-11T08:20:00Z",
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    prior_timeline: list[dict[str, object]] = [
        {"id": 89990, "event": "commented", "created_at": "2026-11-11T08:20:00Z"},
        {
            "id": 89991,
            "event": "labeled",
            "label": {"name": "action:implement-change"},
            "created_at": "2026-11-11T08:21:00Z",
        },
    ]
    formal_comments: list[dict[str, object]] = []
    formal_comment_posts: list[str] = []
    lose_formal_post_response = {"once": True}
    successor_patches: list[list[str]] = []
    # Source Git bytes are already durable; an out-of-band maintenance repair
    # only restores correct observations. It must never replay Original.
    original_read_fault = {"active": False}

    def native_read(repository: str, token: str, api_path: str, **kwargs: object) -> object:
        if original_read_fault["active"] and api_path == f"git/ref/heads/{proof_git.branch}":
            return {"object": {"sha": base}}
        if api_path == "issues/435":
            if kwargs.get("method") == "PATCH":
                payload = kwargs.get("payload")
                assert isinstance(payload, Mapping)
                labels = payload.get("labels")
                assert labels == [f"action:{successor_action}"]
                assert result_kind == "spec-blocker"
                successor_patches.append(labels)
                proof_git.routing = successor_action
                prior_timeline.extend(
                    [
                        {
                            "id": 90002,
                            "event": "unlabeled",
                            "label": {"name": "action:implement-change"},
                            "created_at": "2026-11-11T13:10:00Z",
                        },
                        {
                            "id": 90003,
                            "event": "labeled",
                            "label": {"name": f"action:{successor_action}"},
                            "created_at": "2026-11-11T13:10:01Z",
                        },
                    ]
                )
            issue = cast(dict[str, object], proof_git.api(repository, token, "issues/322"))
            return {**issue, "number": 435, "body": f"Change: {change}"}
        if api_path.startswith("pulls/437/files?"):
            return [{"filename": proposal_path, "status": "modified"}] + [
                {"filename": item, "status": "modified"} for item in paths
            ]
        if api_path == "issues/435/comments?per_page=100&sort=created&direction=desc":
            return list(reversed([prior_comment, *formal_comments]))
        if api_path == "issues/435/timeline?per_page=100&page=1":
            return [
                *prior_timeline,
                *(
                    [{"id": 90001, "event": "commented", "created_at": "2026-11-11T13:09:00Z"}]
                    if formal_comments
                    else []
                ),
            ]
        if api_path == "issues/435/comments" and kwargs.get("method") == "POST":
            request = cast(dict[str, str], kwargs["payload"])
            formal_comment_posts.append(request["body"])
            comment: dict[str, object] = {
                "id": 90001,
                "body": request["body"],
                "created_at": "2026-11-11T13:09:00Z",
                "user": {"login": "github-actions[bot]"},
                "performed_via_github_app": {"slug": "github-actions"},
            }
            formal_comments.append(comment)
            # Native GitHub accepted the comment; only the client response is
            # lost. This must not authorize the next wake to replay the POST.
            if lose_formal_post_response["once"]:
                lose_formal_post_response["once"] = False
                raise OSError("simulated lost response after formal POST")
            return comment
        if api_path == "issues/comments/90001":
            return formal_comments[0] if formal_comments else None
        return proof_git.api(repository, token, api_path, **kwargs)

    monkeypatch.setattr(materialization, "_github_json", native_read)
    monkeypatch.setattr(validation_resource, "_github_json", native_read)
    monkeypatch.setattr(effects, "_github_json", native_read)
    # The separate OpenSpec review gate is established upstream of this
    # accepted Effect. It is not reimplemented by the Git witness test.
    from investment_strategy import scheduled_agent_application_carrier as application_carrier

    monkeypatch.setattr(application_carrier, "_github_json", native_read)
    if predecessor_failure is None:
        monkeypatch.setattr(
            materialization, "_qualified_implementation_decision", lambda *_a, **_kw: None
        )

    def observe() -> application_bridge.AcceptedPostEffectProof:
        return application_bridge._observe_accepted_post_effect_result(
            record=accepted,
            source=original,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            default_branch="main",
        )

    # The original #435 failure was an Application preparation exception.
    # This fixture starts at the already-validated native Artifact boundary;
    # it does not replace the actual Application domain classifier with a
    # synthetic success result or claim to test Artifact download validation.
    exception = application_bridge.ApplicationExceptionArtifact(
        run_id=43029179128,
        run_attempt=1,
        job_id=130551485662,
        artifact_id=13860996180,
        artifact_digest="sha256:6e635bde715bec5b9d282396655b788c414890c6e8ac3a5f9c34bc5c5701d292",
        request_comment_id=accepted.request_comment_id,
        accepted_decision_sha256="d" * 64,
        failure_evidence_sha256="e" * 64,
        recovery_episode_sha256="f" * 64,
        document={
            "issue_number": 435,
            "role": original.role,
            "action": original.action,
            "change": change,
            "attempted_operation": "application-effect-preparation",
            "mutation_status": "NO_APPLICATION_WRITE_ATTEMPTED",
        },
    )

    def exception_proof(
        evidence: application_bridge.ApplicationExceptionArtifact,
    ) -> application_bridge.AcceptedPostEffectProof:
        with monkeypatch.context() as patch:
            patch.setattr(application_bridge, "_github_json", native_read)
            return application_bridge.classify_application_exception_recovery(
                record=accepted,
                artifact=evidence,
                repository=proof_git.repository,
                token=_TOKEN,
            )

    # A run-local pre-call exception must never imply intent-wide NOT_APPLIED.
    assert exception_proof(exception).disposition == "INDETERMINATE"
    assert (
        exception_proof(
            replace(exception, document={**exception.document, "change": "foreign-change"})
        ).disposition
        == "UNSAFE"
    )
    assert observe().disposition == "INDETERMINATE"  # Missing original Git effect.
    correction = proof_git.commit(
        {"README.md": "independently corrected documentation"},
        "Apply separate maintenance correction",
        (base,),
    )
    proof_git.set_head(correction)
    for _ in range(2):
        pending = exception_proof(exception)
        assert pending.continuation == "OBSERVE", pending
        assert pending.runtime_repair_frontier is not None
        assert pending.runtime_repair_frontier.remaining_obligation == "ORIGINAL_EFFECT"
    assert formal_comment_posts == []
    assert successor_patches == []
    assert proof_git.mutations == []

    witness = proof_git.commit(desired, proof_git.message, (correction,))
    proof_git.set_head(witness)
    # This is a separate maintenance/read-repair boundary, not a replay of
    # the accepted seven-file Effect. The physical Git witness does not change
    # between a defective observation and a later fresh Application check.
    original_read_fault["active"] = True
    unrepaired = observe()
    assert unrepaired.continuation in {"OBSERVE", "REJECT"}, unrepaired
    assert unrepaired.carrier_plan is None
    assert formal_comment_posts == []
    assert successor_patches == []
    assert proof_git.head == witness and proof_git.mutations == []
    original_read_fault["active"] = False
    assert observe().disposition == "COMPLETE"
    assert proof_git.head == witness and proof_git.mutations == []
    comparison = proof_git.comparison(correction, witness)
    assert comparison["ahead_by"] == 1
    assert len(cast(list[dict[str, object]], comparison["files"])) == 7
    canonical = materialization.prove_materialization(
        payload,
        original,
        repository=proof_git.repository,
        token=_TOKEN,
        current_revision=proof_git.main,
        default_branch="main",
        accepted_authorization_revision=base,
        allow_pending_continuation=True,
        accepted_intent=True,
    )
    assert canonical.disposition == "COMPLETE", canonical

    # Two separate fresh observations qualify one and the same original
    # accepted Git effect, without calling its historical mutation again.
    assert observe().disposition == "COMPLETE"
    assert observe().disposition == "COMPLETE"
    assert exception_proof(exception).disposition == "COMPLETE"
    assert proof_git.head == witness
    assert proof_git.mutations == []

    # R2 integration: the native-shaped failed Application attempt must feed
    # the real Bridge completion reader, strict exception Artifact reader and
    # canonical Application/Git postcondition proof. This is the missing
    # source->completion seam, not a second proof owner or an Effect replay.
    import investment_strategy.issue_comment_bridge as dispatch_bridge

    native_run = {
        "id": 43029179128,
        "run_attempt": 1,
        "head_sha": proof_git.main,
        "display_title": "Scheduled Agent Application 6797071043",
        "status": "completed",
        "conclusion": "failure",
    }
    native_job = {
        "id": 130551485662,
        "name": "apply",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "failure",
        "steps": [
            {
                "name": "Freshly authorize and apply repository-owned effects",
                "conclusion": "failure",
            },
            {"name": "Upload exact application recovery evidence", "conclusion": "skipped"},
            {
                "name": "Upload pre-ACCEPT or interrupted application exception evidence",
                "conclusion": "success",
            },
            {"name": "Persist exact external carrier plan", "conclusion": "skipped"},
            {"name": "Upload exact external carrier plan", "conclusion": "skipped"},
            {
                "name": "Persist the derived successor after exact validation",
                "conclusion": "skipped",
            },
            {"name": "Upload final exact application recovery evidence", "conclusion": "skipped"},
        ],
    }
    native_document = {
        "schema": "scheduled-agent-execution-exception/v1",
        "repository": proof_git.repository,
        "issue_number": 435,
        "role": original.role,
        "action": original.action,
        "change": change,
        "revision": proof_git.main,
        "request_comment_id": accepted.request_comment_id,
        "trigger_comment_id": 6797071043,
        "run_id": native_run["id"],
        "run_attempt": 1,
        "attempted_operation": "application-effect-preparation",
        "exception_type": "RuntimeError",
        "raw_error": "accepted implementation checkpoint identity is incomplete",
        "raw_traceback": "sanitized test fixture",
        "mutation_status": "NO_APPLICATION_WRITE_ATTEMPTED",
        "unfinished_boundary": "application-effect-preparation",
        "classification": "UNCLASSIFIED_EXECUTION_EXCEPTION",
    }
    artifact_bytes = json.dumps(native_document, sort_keys=True).encode()
    native_artifact = {
        "id": 13860996180,
        "name": "application-execution-exception.json",
        "expired": False,
        "digest": "sha256:" + hashlib.sha256(artifact_bytes).hexdigest(),
        "workflow_run": {"id": native_run["id"], "head_sha": proof_git.main},
    }
    read_paths: list[str] = []
    continuation_comments: list[dict[str, object]] = []
    transient_source_read = {"unavailable": False}
    actor = {"login": "royhsu-work", "id": 77, "type": "User"}
    repair_comment = {
        "id": 90008,
        "user": actor,
        "performed_via_github_app": None,
        "issue_url": f"https://api.github.com/repos/{proof_git.repository}/issues/435",
        "body": dispatch_bridge.RUNTIME_REPAIR_REQUEST_WIRE.render(
            {
                "Issue": "435",
                "Change": change,
                "Action": original.action,
                "Accepted-Request-Comment": str(accepted.request_comment_id),
                "Accepted-Decision-SHA256": decision_digest,
                "Repair-PR": "443",
                "Repair-HEAD": proof_git.main,
            }
        ),
    }
    repair_event = {
        "action": "created",
        "repository": {"full_name": proof_git.repository, "default_branch": "main"},
        "issue": {"number": 435},
        "sender": actor,
        "comment": repair_comment,
    }
    maintenance_pr = {
        "number": 443,
        "state": "open",
        "merged": False,
        "head": {"sha": proof_git.main, "repo": {"full_name": proof_git.repository}},
        "base": {"ref": "main", "repo": {"full_name": proof_git.repository}},
    }

    def bridge_read(repository: str, token: str, path: str, **kwargs: object) -> object:
        assert kwargs.get("method", "GET") == "GET"
        read_paths.append(path)
        if path.startswith("actions/workflows/scheduled-agent-application.yml/runs?"):
            return {
                "total_count": 1,
                "workflow_runs": [native_run] if "page=1" in path else [],
            }
        if path == "actions/runs/43029179128":
            return native_run
        if path == "actions/runs/43029179128/attempts/1/jobs":
            return {"total_count": 1, "jobs": [native_job]}
        if path == "actions/runs/43029179128/artifacts?per_page=100":
            return {"total_count": 1, "artifacts": [native_artifact]}
        if path.startswith("issues/435/comments?sort=created&direction=asc&per_page=100"):
            if transient_source_read["unavailable"]:
                raise OSError("temporary native source inventory failure")
            return [prior_comment, decision_comment, *formal_comments]
        if path.startswith("issues/435/comments?sort=created&per_page=100&page="):
            return (
                [prior_comment, decision_comment, *formal_comments]
                if path.endswith("page=1")
                else []
            )
        if path.startswith("issues/448/comments?sort=created&direction=asc&per_page=100"):
            return continuation_comments
        if path.startswith("issues/comments?sort=created&direction=asc&since="):
            return continuation_comments
        if path == "issues/comments/6796616018":
            return source_comment
        if path == "issues/448":
            return {
                "number": 448,
                "title": "[Agent Runtime] 2026-11-17",
                "state": "open",
                "labels": [],
            }
        if path == "issues/comments/90007":
            return next((item for item in continuation_comments if item["id"] == 90007), None)
        if path == "issues/comments/90008":
            return repair_comment
        if path == "pulls/443":
            return maintenance_pr
        return native_read(repository, token, path, **kwargs)

    def artifact_read(repository: str, token: str, path: str) -> bytes:
        assert repository == proof_git.repository and token == _TOKEN
        assert path == "actions/artifacts/13860996180/zip"
        return artifact_bytes

    def native_completion() -> dispatch_bridge.ApplicationCompletion:
        return dispatch_bridge._application_job(
            proof_git.repository,
            _TOKEN,
            accepted.request_comment_id,
            read=bridge_read,
            record=accepted,
            transport_comment_ids=(6797071043,),
            accepted_decision_sha256=decision_digest,
            current_revision=proof_git.main,
        )

    with monkeypatch.context() as patch:
        # Only outbound GitHub data transport is injected. Artifact shape,
        # Application typed proof and native Bridge selection remain real.
        patch.setattr(application_bridge, "_github_json", bridge_read)
        patch.setattr(dispatch_bridge, "read_github_artifact_bytes", artifact_read)
        # Even a qualified native Exception Artifact cannot promote a stale
        # original Git observation to Application continuation authority.
        original_read_fault["active"] = True
        before_repair = native_completion()
        assert before_repair.state != "COMPLETE", before_repair
        assert before_repair.qualified_carrier is None
        assert proof_git.head == witness and proof_git.mutations == []
        original_read_fault["active"] = False

        def repair_admission(
            event: Mapping[str, object],
        ) -> dispatch_bridge.RuntimeRepairAdmission | None:
            return dispatch_bridge.qualify_runtime_repair_admission(
                event,
                repository=proof_git.repository,
                token=_TOKEN,
                current_revision=proof_git.main,
                read=bridge_read,
                # Exercise the real native job/Artifact reader on the exact ACCEPT.
                qualify=lambda *_a, **_kw: native_completion(),
            )

        def observe_read_fault(
            path: str, observation: object, *, initial_issue_read: bool = False
        ) -> dispatch_bridge.ApplicationCompletion:
            def validation_read(
                repository: str, token: str, api_path: str, **kwargs: object
            ) -> object:
                return (
                    observation
                    if api_path == path
                    else native_read(repository, token, api_path, **kwargs)
                )

            with monkeypatch.context() as validation:
                reader = materialization if initial_issue_read else validation_resource
                validation.setattr(reader, "_github_json", validation_read)
                result = native_completion()
                assert result.accepted_proof is not None
                if result.accepted_proof.disposition == "INDETERMINATE":
                    assert repair_admission(repair_event) is None
                assert formal_comment_posts == successor_patches == proof_git.mutations == []
                return result

        incomplete_reads: tuple[tuple[str, object], ...] = (
            ("", {}),
            ("git/ref/heads/main", {"object": {}}),
        )
        for path, observation in incomplete_reads:
            incomplete = observe_read_fault(path, observation)
            assert incomplete.accepted_proof is not None
            assert incomplete.accepted_proof.disposition == "INDETERMINATE", incomplete
            original_proof = incomplete.accepted_proof.original_effect_proof
            assert original_proof is not None and original_proof.disposition == "UNKNOWN"
            assert native_completion().reason == "application-completion-continuation-required"

        for path, observation in (
            ("", {"default_branch": "other-main"}),
            ("git/ref/heads/main", {"object": {"sha": "f" * 40}}),
        ):
            different = observe_read_fault(path, observation)
            assert different.accepted_proof is not None
            assert different.accepted_proof.disposition == "UNSAFE", different
            original_proof = different.accepted_proof.original_effect_proof
            assert original_proof is not None and original_proof.disposition == "CONFLICT"

        issue_path = "issues/435"
        source_issue = cast(
            dict[str, object], native_read(proof_git.repository, _TOKEN, issue_path)
        )
        for initial_issue_read in (True, False):
            for observation in (
                None,
                {key: value for key, value in source_issue.items() if key != "state"},
                {key: value for key, value in source_issue.items() if key != "body"},
            ):
                incomplete = observe_read_fault(
                    issue_path, observation, initial_issue_read=initial_issue_read
                )
                assert incomplete.accepted_proof is not None
                assert incomplete.accepted_proof.disposition == "INDETERMINATE", incomplete
                original_proof = incomplete.accepted_proof.original_effect_proof
                assert original_proof is not None and original_proof.disposition == "UNKNOWN"
            assert native_completion().reason == "application-completion-continuation-required"
            for override in ({"number": 999}, {"state": "closed"}):
                different = observe_read_fault(
                    issue_path, {**source_issue, **override}, initial_issue_read=initial_issue_read
                )
                assert different.accepted_proof is not None
                assert different.accepted_proof.disposition == "UNSAFE", different
                original_proof = different.accepted_proof.original_effect_proof
                assert original_proof is not None and original_proof.disposition == "CONFLICT"

        # Contradictory PR metadata is durable even though the Original Git
        # commit is intact. The conflict needs independent maintenance.
        previous_base = pr["base"]
        pr["base"] = {**cast(dict[str, object], previous_base), "ref": "other-base"}
        conflict = native_completion()
        assert conflict.state == "INVALID", conflict
        assert conflict.accepted_proof is not None
        assert conflict.accepted_proof.disposition == "UNSAFE", conflict
        assert (
            repair_admission(
                {
                    **repair_event,
                    "comment": {**repair_comment, "performed_via_github_app": {"id": 1}},
                }
            )
            is None
        )
        admission = repair_admission(repair_event)
        assert admission is not None
        assert admission.frontier_proof.disposition == "CONFLICT"
        assert admission.frontier_proof.remaining_obligation == "ORIGINAL_EFFECT"
        assert (
            dispatch_bridge._runtime_repair_admission_document(
                admission, repository=proof_git.repository
            )["effect_authority"]
            == "NONE"
        )
        assert formal_comment_posts == successor_patches == proof_git.mutations == []

        # Stand-in for an independently authorized external disposition. Only
        # simulated GitHub metadata changes; no old Git write is replayed.
        pr["base"] = previous_base
        if predecessor_failure is not None:
            proof_git.main = proof_git.commit(
                {paths[0]: "conflicting maintenance delivered to main"},
                "Maintenance squash merge",
                (base,),
            )
            import subprocess

            git_integration = subprocess.run(  # noqa: S603 - local fixture commits
                [  # noqa: S607 - repository test uses the installed Git executable
                    "git",
                    "-C",
                    str(proof_git.directory),
                    "merge-tree",
                    "--write-tree",
                    proof_git.main,
                    witness,
                ],
                capture_output=True,
                check=False,
            )
            assert git_integration.returncode == 1
            pr["mergeable"] = False
            pr["mergeable_state"] = "dirty"
            composite = materialization.prove_materialization(
                payload,
                original,
                repository=proof_git.repository,
                token=_TOKEN,
                current_revision=proof_git.main,
                default_branch="main",
                accepted_authorization_revision=base,
                allow_pending_continuation=True,
                accepted_intent=True,
            )
            assert composite.disposition == "CONTRADICTORY" and composite.target is None
        completed = native_completion()
        assert completed.state == "RESUMABLE", completed
        assert completed.reason == "application-completion-continuation-required"
        if predecessor_failure is not None:
            assert (
                composite.historical_witness is not None
                and composite.historical_witness.revision == witness
            )
        assert isinstance(
            completed.recovery_artifact, application_bridge.ApplicationExceptionArtifact
        )
        assert completed.recovery_artifact.artifact_id == 13860996180
        assert completed.recovery_artifact.request_comment_id == 6796616018
        assert completed.recovery_artifact.accepted_decision_sha256 == decision_digest
        assert proof_git.head == witness and proof_git.mutations == []
        assert "actions/runs/43029179128/attempts/1/jobs" in read_paths

        # The *same* qualified failed Application now emits its actual
        # repository wire, and the next wake re-reads the exact predecessor.
        continuation_body = dispatch_bridge._application_continuation_body(
            repository=proof_git.repository,
            token=_TOKEN,
            source=original,
            request_comment_id=accepted.request_comment_id,
            predecessor_evidence=completed.recovery_artifact,
            read=bridge_read,
        )
        assert isinstance(continuation_body, str)
        parsed_continuation = application_bridge.parse_application_continuation_request(
            continuation_body
        )
        assert parsed_continuation is not None
        assert parsed_continuation.accepted_decision_sha256 == decision_digest
        assert parsed_continuation.predecessor_artifact_id == 13860996180
        continuation_comments.append(
            {
                "id": 90007,
                "issue_url": f"https://api.github.com/repos/{proof_git.repository}/issues/448",
                "body": continuation_body,
                "created_at": "2026-11-17T05:37:00Z",
                "updated_at": "2026-11-17T05:37:00Z",
                "user": {"login": "royhsu-work"},
                "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
            }
        )

        def fresh_predecessor() -> (
            application_bridge.ApplicationRecoveryArtifact
            | application_bridge.ApplicationExceptionArtifact
            | None
        ):
            return application_bridge.qualify_application_continuation_predecessor(
                proof_git.repository,
                _TOKEN,
                parsed_continuation,
                current_comment_id=90007,
                transport_issue_number=448,
                read=bridge_read,
                artifact_reader=artifact_read,
            )

        qualified = fresh_predecessor()
        assert isinstance(qualified, application_bridge.ApplicationExceptionArtifact)
        assert qualified == completed.recovery_artifact
        assert qualified.accepted_decision_sha256 == decision_digest
        assert proof_git.mutations == []
        # Duplicated/foreign native sources never authorize a second consumer.
        continuation_comments.append({**continuation_comments[0], "id": 90008})
        assert fresh_predecessor() is None
        continuation_comments.pop()
        decision_comment["body"] = decision_body.replace(
            f"Change: {change}", "Change: unrelated", 1
        )
        assert fresh_predecessor() is None
        decision_comment["body"] = decision_body
        transient_source_read["unavailable"] = True
        with pytest.raises(OSError, match="temporary native source inventory failure"):
            fresh_predecessor()
        transient_source_read["unavailable"] = False
        assert fresh_predecessor() == qualified
        # A reobservation cannot emit another request for an existing lineage.
        assert (
            dispatch_bridge._application_continuation_body(
                repository=proof_git.repository,
                token=_TOKEN,
                source=original,
                request_comment_id=accepted.request_comment_id,
                predecessor_evidence=qualified,
                read=bridge_read,
            )
            is None
        )
        accepted_from_continuation = effects.parse_application_decision(decision_comment["body"])
        assert accepted_from_continuation == accepted

        # A tampered native Artifact cannot inherit the positive Git witness
        # as permission for Formal/Successor or an Original Effect retry.
        native_artifact["digest"] = "sha256:" + "0" * 64
        unqualified = native_completion()
        assert unqualified.state == "INVALID"
        assert unqualified.reason == "application-completion-recovery-evidence-unavailable"
        assert proof_git.mutations == []

    # Restore the native Artifact after the adversarial digest test. The
    # independent entrypoint below must verify the original qualified bytes,
    # not inherit this intentionally corrupted fixture state.
    native_artifact["digest"] = "sha256:" + hashlib.sha256(artifact_bytes).hexdigest()

    # Formal and Successor now consume the exact parsed accepted source that
    # qualified the predecessor at the fresh continuation wake, not a detached
    # worker fixture or a new worker decision.
    assert (
        accepted_from_continuation.worker_result_sha256
        == hashlib.sha256(accepted_from_continuation.raw_worker_result.encode()).hexdigest()
    )
    # Original-effect completion is not a Formal result. Reuse the already
    # source-proven Git witness as the fresh carrier revision and exercise the
    # real Application-owned formal projection, not a mocked Formal status.
    if predecessor_failure is None:
        monkeypatch.setattr(
            application_bridge, "_machine_result_revision", lambda *_a, **_kw: witness
        )

    def project_formal() -> str:
        return application_bridge._fresh_application_worker_result(
            accepted_from_continuation.raw_worker_result,
            source=original,
            change=change,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            default_branch="main",
            request_comment_id=accepted.request_comment_id,
        )

    projection = project_formal()
    projected = application_bridge.parse_effect_batch(
        projection, original, authorized_change=change
    )
    assert len(projected.effects) == 2
    original_effect, formal_effect = projected.effects
    assert original_effect.kind == "github-mutation"
    assert json.loads(original_effect.payload_json) == payload
    assert formal_effect.kind == "issue-comment"
    formal = cast(str, json.loads(formal_effect.payload_json)["body"])
    assert formal.splitlines()[0] == "ACTION_RESULT"
    assert "Workflow: #435" in formal.splitlines()
    assert f"Result: {result_kind.upper().replace('-', '_')}" in formal.splitlines()
    assert f"Revision: {witness}" in formal.splitlines()
    assert (
        f"Repository-derived successor: {successor_role.capitalize()} / {successor_action}"
        in formal.splitlines()
    )
    correlation = application_bridge.formal_application_correlation(
        original,
        change=change,
        result_kind=result_kind,
        current_revision=proof_git.main,
        request_comment_id=accepted.request_comment_id,
    )
    assert f"Application-Correlation: {correlation}" in formal.splitlines()
    assert "SLICE_CHECKPOINT" not in projection
    assert project_formal() == projection
    assert proof_git.mutations == []

    # R1: enter through the real guarded Application effect owner while
    # Original is already source-proven and Formal is still absent. Its first
    # non-idempotent Formal POST succeeds at GitHub but loses the HTTP response.
    # The next independent process must read/reconcile that exact Formal and
    # derive the still-needed Successor without retrying either original write.
    import investment_strategy.scheduled_agent_merge_acceptance as merge_acceptance
    from investment_strategy.workflow_dispatch import classify_dispatch

    api_root = f"https://api.github.com/repos/{proof_git.repository}"
    preflight_read_paths: list[str] = []

    def runtime_page(url: str, token: str) -> tuple[Mapping[str, object], ...]:
        assert token == _TOKEN and url.startswith(api_root + "/")
        path = url.removeprefix(api_root + "/")
        preflight_read_paths.append(path)
        if path == "issues?state=all&per_page=100&page=1":
            issue = native_read(proof_git.repository, token, "issues/435")
            assert isinstance(issue, Mapping)
            return (issue,)
        if path == "issues/435/comments?per_page=100&sort=created&direction=desc":
            return tuple(reversed([prior_comment, *formal_comments]))
        if path == "issues/435/timeline?per_page=100&page=1":
            timeline = native_read(
                proof_git.repository, token, "issues/435/timeline?per_page=100&page=1"
            )
            assert isinstance(timeline, list)
            return tuple(timeline)
        raise AssertionError(f"unexpected runtime preflight GET: {path}")

    def runtime_object(url: str, token: str) -> Mapping[str, object]:
        assert token == _TOKEN
        preflight_read_paths.append(url.removeprefix(api_root))
        if url == api_root:
            return {"default_branch": "main"}
        if url == api_root + "/git/ref/heads/main":
            return {"object": {"sha": proof_git.main}}
        if url.startswith(api_root + "/compare/"):
            left, right = url.removeprefix(api_root + "/compare/").split("...")
            return proof_git.comparison(left, right)
        raise AssertionError(f"unexpected preflight identity GET: {url}")

    monkeypatch.setattr(runtime, "_github_get_list_page", runtime_page)
    monkeypatch.setattr(runtime, "_github_get_object", runtime_object)
    # All decision consumers use the genuine preflight + classifier; only
    # outbound GitHub GETs are replaced with native-shaped fixture payloads.
    monkeypatch.setattr(
        merge_acceptance,
        "acquire_current_github_preflight",
        runtime.acquire_current_github_preflight,
    )
    monkeypatch.setattr(
        effects,
        "acquire_current_github_preflight",
        runtime.acquire_current_github_preflight,
    )
    qualified_preflight = runtime.acquire_current_github_preflight(proof_git.repository, _TOKEN)
    dispatch = classify_dispatch(qualified_preflight)
    assert dispatch.disposition == "AUTHORIZE", dispatch
    assert dispatch.selected_issue_id == 435
    assert dispatch.selected_routing == ("executor", "implement-change")
    route_event = prior_timeline.pop()
    try:
        rejected = classify_dispatch(
            runtime.acquire_current_github_preflight(proof_git.repository, _TOKEN)
        )
        assert rejected.disposition == "FAIL_CLOSED", rejected
    finally:
        prior_timeline.append(route_event)
    assert (
        classify_dispatch(
            runtime.acquire_current_github_preflight(proof_git.repository, _TOKEN)
        ).disposition
        == "AUTHORIZE"
    )

    def guarded(
        *, reconcile_only: bool = False, uncertain_effect_index: int | None = None
    ) -> tuple[effects.EffectBatch, effects.ApplyResult]:
        return merge_acceptance.run_guarded_effect_application(
            projection,
            source=original,
            repository=proof_git.repository,
            token=_TOKEN,
            current_revision=proof_git.main,
            request_comment_id=accepted.request_comment_id,
            authorized_change=change,
            authorization_revision=accepted.authorization_revision,
            allow_pending_continuation=True,
            accepted_intent=True,
            reconcile_only=reconcile_only,
            uncertain_effect_index=uncertain_effect_index,
        )

    def new_application() -> effects.GitHubEffectAdapter:
        return effects.GitHubEffectAdapter(
            proof_git.repository,
            _TOKEN,
            original,
            authorized_change=change,
            current_revision=proof_git.main,
            expected_result_kind=result_kind,
            request_comment_id=accepted.request_comment_id,
            authorization_revision=accepted.authorization_revision,
            allow_pending_continuation=True,
            accepted_intent=True,
        )

    first = new_application()
    assert first.observe_postcondition(original_effect)
    assert first.guard(formal_effect)
    assert not first.observe_postcondition(formal_effect)
    assert formal_comment_posts == []

    # A fresh Application process uses the same immutable accepted source.
    # The second run represents a new native run attempt of the SAME event,
    # not a fabricated second Dispatch request or a second recovery owner.
    event = {
        "action": "created",
        "issue": {
            "number": 448,
            "title": "[Agent Runtime] 2026-11-17",
            "state": "open",
            "labels": [],
        },
        "comment": dict(continuation_comments[0]),
    }
    event_path = tmp_path / "435-continuation-event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    actual_owner: Callable[..., tuple[effects.EffectBatch, effects.ApplyResult]] = (
        application_bridge.run_guarded_effect_application
    )

    def native_continuation_attempt(
        attempt: int,
    ) -> tuple[int, list[tuple[effects.EffectBatch, effects.ApplyResult]]]:
        entered: list[tuple[effects.EffectBatch, effects.ApplyResult]] = []

        def traced_owner(
            raw_worker_result: str, **kwargs: object
        ) -> tuple[effects.EffectBatch, effects.ApplyResult]:
            outcome = actual_owner(raw_worker_result, **kwargs)
            entered.append(outcome)
            return outcome

        with monkeypatch.context() as fresh_entry:
            fresh_entry.setattr(application_bridge, "_github_json", bridge_read)
            fresh_entry.setattr(application_bridge, "read_github_artifact_bytes", artifact_read)
            fresh_entry.setattr(
                application_bridge,
                "acquire_current_github_preflight",
                runtime.acquire_current_github_preflight,
            )
            fresh_entry.setattr(application_bridge, "run_guarded_effect_application", traced_owner)
            fresh_entry.setenv("GITHUB_REPOSITORY", proof_git.repository)
            fresh_entry.setenv("GITHUB_TOKEN", _TOKEN)
            fresh_entry.setenv("GITHUB_RUN_ID", "43029179129")
            fresh_entry.setenv("GITHUB_OUTPUT", str(tmp_path / f"435-entry-output-{attempt}"))
            fresh_entry.setattr(
                application_bridge.sys,
                "argv",
                [
                    "application-bridge",
                    "--event-path",
                    str(event_path),
                    "--revision",
                    proof_git.main,
                    "--default-branch",
                    "main",
                    "--run-attempt",
                    str(attempt),
                    "--recovery-evidence-path",
                    str(tmp_path / f"435-entry-recovery-{attempt}.json"),
                    "--exception-evidence-path",
                    str(tmp_path / f"435-entry-exception-{attempt}.json"),
                ],
            )
            code = application_bridge.main()
        return code, entered

    # Formal POST succeeds at GitHub but its client response is lost.
    if predecessor_failure is not None:
        original_bridge_reader = bridge_read
        original_artifact_reader = artifact_read
        fault_path = {
            "trigger": "issues/comments/90007",
            "accepted": "issues/435/comments?sort=created&direction=asc",
            "download": "actions/artifacts/13860996180/zip",
            "digest": "actions/artifacts/13860996180/zip",
        }[predecessor_failure]
        failed_paths: list[str] = []

        def fail_observation(path: str) -> None:
            if path.partition("&per_page=100")[0] == fault_path and not failed_paths:
                failed_paths.append(fault_path)
                raise OSError("temporary continuation evidence read failure")

        def interrupted_bridge_read(
            repository: str, token: str, path: str, **kwargs: object
        ) -> object:
            fail_observation(path)
            return original_bridge_reader(repository, token, path, **kwargs)

        def interrupted_artifact_read(repository: str, token: str, path: str) -> bytes:
            fail_observation(path)
            return original_artifact_reader(repository, token, path)

        bridge_read = interrupted_bridge_read
        artifact_read = interrupted_artifact_read
        with pytest.raises(
            (OSError, ValueError),
            match="temporary continuation evidence read failure|decision evidence is unavailable",
        ):
            native_continuation_attempt(1)
        assert failed_paths == [fault_path]
        bridge_read = original_bridge_reader
        artifact_read = original_artifact_reader
        restored = artifact_read(proof_git.repository, _TOKEN, "actions/artifacts/13860996180/zip")
        assert "sha256:" + hashlib.sha256(restored).hexdigest() == native_artifact["digest"]
        failed = json.loads((tmp_path / "435-entry-exception-1.json").read_text())
        assert failed["trigger_comment_id"] == 90007
        assert failed["mutation_status"] == "NO_APPLICATION_WRITE_ATTEMPTED"
        assert not formal_comment_posts and not successor_patches and not proof_git.mutations
        pr["mergeable"] = False
        with monkeypatch.context() as fresh:
            fresh.setattr(application_bridge, "_github_json", bridge_read)
            repeated_transport = dispatch_bridge._application_continuation_body(
                repository=proof_git.repository,
                token=_TOKEN,
                source=original,
                request_comment_id=accepted.request_comment_id,
                predecessor_evidence=completed.recovery_artifact,
                read=bridge_read,
            )
        assert repeated_transport is None
        next_bytes = (tmp_path / "435-entry-exception-1.json").read_bytes()
        next_digest = "sha256:" + hashlib.sha256(next_bytes).hexdigest()
        new_run_id, new_artifact_id, new_job_id = 43029179129, 13860996181, 130551485663
        next_run = dict(
            native_run,
            id=new_run_id,
            head_sha=proof_git.main,
            display_title="Scheduled Agent Application 90007",
        )
        next_job = dict(native_job, id=new_job_id)
        next_metadata = dict(
            native_artifact,
            id=new_artifact_id,
            digest=next_digest,
            workflow_run={"id": new_run_id, "head_sha": proof_git.main},
        )
        root_id = 43026063126
        root_run = dict(
            native_run,
            id=root_id,
            display_title=f"Scheduled Agent Application {accepted.request_comment_id}",
        )
        historical_body = application_bridge.render_application_continuation_request(
            repository=proof_git.repository,
            issue_number=original.issue_number,
            original_request_comment_id=accepted.request_comment_id,
            accepted_decision_sha256=decision_digest,
            predecessor_run_id=root_id,
            predecessor_run_attempt=1,
            predecessor_job_id=130540945992,
            predecessor_artifact_id=13857063093,
            predecessor_artifact_digest="sha256:" + "1" * 64,
            failure_evidence_sha256="2" * 64,
            recovery_episode_sha256=parsed_continuation.recovery_episode_sha256,
        )
        historical_comment = {
            **continuation_comments[0],
            "id": 6797071043,
            "body": historical_body,
            "created_at": "2026-11-11T13:26:00Z",
        }
        continuation_comments.insert(0, historical_comment)
        run_inventory = [next_run, native_run, root_run]
        original_bridge_read = bridge_read
        original_artifact_read = artifact_read

        def next_read(repository: str, token: str, path: str, **kwargs: object) -> object:
            if path == "issues/comments/90009":
                return next_comment
            if path.startswith("actions/workflows/scheduled-agent-application.yml/runs?"):
                return {
                    "total_count": len(run_inventory),
                    "workflow_runs": run_inventory if "page=1" in path else [],
                }
            if path == f"actions/runs/{new_run_id}":
                return next_run
            if path == f"actions/runs/{new_run_id}/attempts/1/jobs":
                return {"total_count": 1, "jobs": [next_job]}
            if path == f"actions/runs/{new_run_id}/artifacts?per_page=100":
                return {"total_count": 1, "artifacts": [next_metadata]}
            return original_bridge_read(repository, token, path, **kwargs)

        def next_download(repository: str, token: str, path: str) -> bytes:
            if path == f"actions/artifacts/{new_artifact_id}/zip":
                return next_bytes
            raw = original_artifact_read(repository, token, path)
            return raw + b" " if predecessor_failure == "digest" else raw

        with monkeypatch.context() as redispatch:
            redispatch.setattr(application_bridge, "_github_json", next_read)
            redispatch.setattr(dispatch_bridge, "read_github_artifact_bytes", next_download)
            redispatch.setattr(application_bridge, "read_github_artifact_bytes", next_download)
            known_issue = cast(
                Mapping[str, object], native_read(proof_git.repository, _TOKEN, "issues/435")
            )
            known_comments = (prior_comment, decision_comment)
            known_timeline = tuple(
                cast(
                    list[Mapping[str, object]],
                    native_read(
                        proof_git.repository, _TOKEN, "issues/435/timeline?per_page=100&page=1"
                    ),
                )
            )

            def inspect_frontier() -> tuple[
                tuple[int, ...] | None, dispatch_bridge.ApplicationCompletion
            ]:
                leaf = dispatch_bridge._continuation_transport_comment_ids(
                    repository=proof_git.repository,
                    owner="royhsu-work",
                    source=original,
                    record=accepted,
                    issue_comments=known_comments,
                    recent_comments=tuple(continuation_comments),
                    token=_TOKEN,
                    read=next_read,
                )
                result = dispatch_bridge._accepted_application_state(
                    repository=proof_git.repository,
                    token=_TOKEN,
                    source=original,
                    record=accepted,
                    issue_comments=known_comments,
                    lifecycle_events=known_timeline,
                    current_issue=known_issue,
                    current_revision=proof_git.main,
                    read=next_read,
                    continuation_transport_comment_ids=leaf,
                    recent_comments=tuple(continuation_comments),
                )
                return leaf, result

            run_inventory.pop()
            missing, missing_result = inspect_frontier()
            assert (
                missing is None
                and missing_result.reason == "application-completion-continuation-chain-incomplete"
            )
            run_inventory.append(root_run)
            duplicate = {**continuation_comments[-1], "id": 90010}
            continuation_comments.append(duplicate)
            run_inventory.append(
                dict(next_run, id=43029179131, display_title="Scheduled Agent Application 90010")
            )
            fork, fork_result = inspect_frontier()
            assert (
                fork == (90007, 90010)
                and fork_result.reason == "application-completion-continuation-chain-ambiguous"
            )
            continuation_comments.pop()
            run_inventory.pop()
            trigger_comment = continuation_comments[-1]
            trigger_comment["updated_at"] = "2026-11-17T05:45:00Z"
            changed_leaf, changed_trigger = inspect_frontier()
            assert changed_leaf == (90007,)
            assert changed_trigger.state == "INVALID"
            assert changed_trigger.accepted_proof is not None
            assert changed_trigger.accepted_proof.reason == "continuation trigger was edited"
            trigger_comment["updated_at"] = trigger_comment["created_at"]
            leaf, next_completion = inspect_frontier()
            assert leaf == (90007,)
            if predecessor_failure == "digest":
                assert next_completion.state == "RESUMABLE"
                assert next_completion.reason == "application-completion-exception-observing"
                assert next_completion.accepted_proof is not None
                assert next_completion.accepted_proof.continuation == "OBSERVE"
                assert next_completion.recovery_artifact is not None
                assert (
                    dispatch_bridge._application_continuation_body(
                        repository=proof_git.repository,
                        token=_TOKEN,
                        source=original,
                        request_comment_id=accepted.request_comment_id,
                        predecessor_evidence=next_completion.recovery_artifact,
                        read=next_read,
                    )
                    is None
                )
                assert (
                    not formal_comment_posts and not successor_patches and not proof_git.mutations
                )
                return
            assert next_completion.state == "RESUMABLE", next_completion
            assert next_completion.recovery_artifact is not None
            assert next_completion.recovery_artifact.artifact_id == new_artifact_id
            next_body = dispatch_bridge._application_continuation_body(
                repository=proof_git.repository,
                token=_TOKEN,
                source=original,
                request_comment_id=accepted.request_comment_id,
                predecessor_evidence=next_completion.recovery_artifact,
                read=next_read,
            )
        assert isinstance(next_body, str)
        new_wire = application_bridge.parse_application_continuation_request(next_body)
        assert new_wire is not None
        assert new_wire.continuation_correlation != parsed_continuation.continuation_correlation
        assert (
            new_wire.predecessor_run_id == new_run_id
            and new_wire.predecessor_artifact_id == new_artifact_id
        )
        assert new_wire.recovery_episode_sha256 == parsed_continuation.recovery_episode_sha256
        next_comment = {
            **continuation_comments[-1],
            "id": 90009,
            "body": next_body,
            "created_at": "2026-11-17T05:49:00Z",
        }
        continuation_comments.append(next_comment)
        event["comment"] = next_comment
        event_path.write_text(json.dumps(event), encoding="utf-8")
        bridge_read, artifact_read = next_read, next_download
        final_exit, journal = native_continuation_attempt(1)
        assert final_exit == 1 and len(journal) == 1
        assert journal[0][1].recovery_evidence is not None
        assert len(formal_comment_posts) == 1
        with monkeypatch.context() as repeated_wake:
            repeated_wake.setattr(application_bridge, "_github_json", next_read)
            repeated_wake.setattr(application_bridge, "read_github_artifact_bytes", next_download)
            assert (
                dispatch_bridge._application_continuation_body(
                    repository=proof_git.repository,
                    token=_TOKEN,
                    source=original,
                    request_comment_id=accepted.request_comment_id,
                    predecessor_evidence=next_completion.recovery_artifact,
                    read=next_read,
                )
                is None
            )
        proof_git.main = proof_git.commit(
            {"README.md": "advance after lost Formal response"},
            "Post-Formal main advance",
            (proof_git.main,),
        )
        resumed_exit, resumed_journal = native_continuation_attempt(2)
        assert resumed_exit == 0 and resumed_journal == []
        assert len(formal_comment_posts) == 1 and not successor_patches and not proof_git.mutations
        return
    first_exit, entered = native_continuation_attempt(1)
    assert first_exit == 1
    assert len(entered) == 1
    initial_batch, interrupted = entered[0]
    assert len(initial_batch.effects) == 2
    assert not interrupted.applied
    assert interrupted.recovery_evidence is not None
    assert interrupted.recovery_evidence.failed_effect_index == 1
    assert interrupted.recovery_evidence.write_call_entered is True
    assert interrupted.recovery_evidence.mutation_status == "unknown"
    assert interrupted.recovery_evidence.completed_effect_indexes == (0,)
    assert formal_comment_posts == [formal]
    assert len(formal_comments) == 1
    assert proof_git.head == witness
    assert proof_git.mutations == []

    # A separately reconstructed Application has no invocation-local write
    # receipt. Its existing Effect owner must positively observe Original and
    # Formal, then complete/verify only the derived Successor.
    next_wake = new_application()
    assert next_wake.observe_postcondition(original_effect)
    assert next_wake.observe_postcondition(formal_effect)
    successor = effects.StagedEffect(
        "routing-transition",
        json.dumps({"issue_number": 435, "action": successor_action}),
        derived=True,
    )
    assert next_wake.guard(successor)
    # The distinct-action variant still has a missing successor label after
    # Formal became durable. Recovery must write ONLY the missing transition;
    # the same-action variant instead has an already-durable successor.
    second_exit, resumed_entries = native_continuation_attempt(2)
    assert second_exit == 0
    if result_kind == "blocked":
        assert resumed_entries == []
        assert successor_patches == []
    else:
        assert len(resumed_entries) == 1
        _, resume_result = resumed_entries[0]
        assert resume_result.applied, resume_result
        assert successor_patches == [[f"action:{successor_action}"]]
    assert new_application().observe_postcondition(formal_effect)
    assert new_application().observe_postcondition(successor)
    assert formal_comment_posts == [formal]
    assert proof_git.mutations == []

    # The historical same-action case also remains idempotent when directly
    # revisiting its original Effect owner.
    if result_kind == "blocked":
        final_batch, repeated = guarded()
        assert repeated.applied, repeated
        assert len(final_batch.effects) == 2
    assert formal_comment_posts == [formal]
    assert proof_git.head == witness
    assert proof_git.mutations == []

    assert preflight_read_paths.count("issues?state=all&per_page=100&page=1") >= 4
    assert "issues/435/timeline?per_page=100&page=1" in preflight_read_paths

    # A durable original is not a durable Formal or Successor.
    assert (
        application_bridge.AcceptedPostEffectProof(
            "COMPLETE", "original observed"
        ).runtime_repair_frontier
        is None
    )


def test_accepted_noop_manifest_still_rejects_unrelated_commit_delta(
    proof_git: _ProofGitRepository,
) -> None:
    """No-op tolerance must not admit any path outside effective accepted writes."""

    tasks_path = f"openspec/changes/{_CHANGE}/tasks.md"
    base = proof_git.commit({tasks_path: "unchanged"}, "Earlier checkpoint", (proof_git.base,))
    proof_git.base = base
    proof_git.authorization = base
    proof_git.main = base
    proof_git.set_head(base)

    payload = proof_git.payload()
    tasks_sha = proof_git.entries(base)[tasks_path]["sha"]
    cast(list[dict[str, object]], payload["files"]).append(
        {"path": tasks_path, "blob_sha": tasks_sha, "expected_sha": tasks_sha}
    )
    accepted = proof_git.commit(
        {proof_git.path: "accepted content", "unrelated.txt": "unapproved"},
        proof_git.message,
        (base,),
    )
    proof_git.set_head(accepted)

    proof = _prove_payload_git(proof_git, payload, accepted_intent=True)

    assert proof.disposition == "CONTRADICTORY", proof
    assert proof.witness is None
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


@pytest.mark.parametrize("default_advances", [False, True])
def test_content_only_construction_and_proof_use_exact_actual_branch_parent(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    default_advances: bool,
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
    if default_advances:
        proof_git.main = proof_git.commit(
            {"README.md": "another disjoint main advance"}, "Advance again", (proof_git.main,)
        )
    proof_git.allow_writes = True
    assert _prove_git(proof_git).disposition == "INCOMPLETE"
    with pytest.raises(CarrierRequired) as raised:
        _apply_git(proof_git)
    plan = raised.value.plan
    assert plan.expected["ref_sha"] == branch_parent
    assert plan.requested["commit_parents"] == [branch_parent]
    proof_git.set_head(cast(str, plan.requested["sha"]))
    result = _prove_git(proof_git)
    assert result.disposition == "COMPLETE", result
    assert result.witness is not None
    assert result.witness.revisions.mutation_preimage == branch_parent
    assert (
        proof_git.entries(proof_git.head)["README.md"]["sha"]
        == proof_git.entries(branch_parent)["README.md"]["sha"]
    )
    written = list(proof_git.mutations)
    _apply_git(proof_git)
    assert proof_git.mutations == written


@pytest.fixture
def diverged_content_only_git(proof_git: _ProofGitRepository) -> _ProofGitRepository:
    common = proof_git.base
    proof_git.base = proof_git.commit({"README.md": "carrier change"}, "Carrier", (common,))
    proof_git.set_head(proof_git.base)
    proof_git.main = proof_git.commit({"README.md": "main change"}, "Main", (common,))
    proof_git.authorization = proof_git.main
    return proof_git


def test_s1_content_only_construction_preserves_unrelated_paths(
    diverged_content_only_git: _ProofGitRepository,
) -> None:
    fixture = diverged_content_only_git
    parent_entries = fixture.entries(fixture.head)
    assert _prove_git(fixture, accepted_intent=True).disposition == "INCOMPLETE"
    fixture.allow_writes = True
    with pytest.raises(CarrierRequired) as raised:
        _apply_git(fixture, accepted_intent=True)
    plan = raised.value.plan
    assert plan.expected["ref_sha"] == fixture.head
    assert plan.requested["force"] is False
    assert plan.requested["commit_parents"] == [fixture.head]
    entries = fixture.entries(cast(str, plan.requested["sha"]))
    assert entries.pop(fixture.path)["sha"] == fixture.desired
    parent_entries.pop(fixture.path)
    assert entries == parent_entries
    assert fixture.mutations == ["git/trees", "git/commits"]


@pytest.mark.parametrize("conflicting", [False, True])
def test_s1_content_only_witness_survives_native_integration_outcome(
    proof_git: _ProofGitRepository,
    conflicting: bool,
) -> None:
    import subprocess

    fixture = proof_git
    middle = "".join(f"unchanged {index}\n" for index in range(8))
    common = fixture.commit(
        {"README.md": f"left\n{middle}right\n"}, "Integration base", (fixture.base,)
    )
    fixture.base = fixture.commit(
        {"README.md": f"carrier left\n{middle}right\n"}, "Carrier", (common,)
    )
    main_readme = f"main left\n{middle}right\n" if conflicting else f"left\n{middle}main right\n"
    fixture.main = fixture.commit({"README.md": main_readme}, "Main", (common,))
    fixture.authorization = fixture.main
    fixture.set_head(fixture.base)
    accepted = fixture.commit({fixture.path: "accepted content"}, fixture.message, (fixture.head,))
    fixture.set_head(accepted)
    integration = subprocess.run(  # noqa: S603 - fixed fixture Git arguments
        ["git", "-C", str(fixture.directory), "merge-tree", "--write-tree", fixture.main, accepted],  # noqa: S607
        capture_output=True,
        check=False,
    )
    assert integration.returncode == int(conflicting), integration.stdout
    assert fixture.head == accepted
    proof = _prove_git(fixture, accepted_intent=True)
    assert proof.disposition == "COMPLETE", proof
    assert proof.witness is not None and proof.witness.revision == accepted
    _apply_git(fixture, accepted_intent=True)
    assert fixture.mutations == []


def test_s1_content_write_rejects_mismatched_accepted_preimage(
    proof_git: _ProofGitRepository,
) -> None:
    payload = proof_git.payload()
    cast(list[dict[str, object]], payload["files"])[0]["expected_sha"] = proof_git.blob(
        "different preimage"
    )
    with pytest.raises(RuntimeError, match="preimage|expected content SHA"):
        _apply_git(proof_git, payload=payload, accepted_intent=True)
    assert proof_git.mutations == []


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


def test_workflow_file_implementation_delegates_git_objects_to_existing_carrier(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A workflow-file manifest never reaches the scoped Actions Git writes."""
    import investment_strategy.scheduled_agent_application_carrier as carrier

    proof_git.source = WorkerRequest(322, "executor", "implement-change")
    proof_git.routing = proof_git.source.action
    proof_git.path = f"openspec/changes/{_CHANGE}/tasks.md"
    proof_git.base = proof_git.commit(
        {proof_git.path: "- [ ] 1.1 Implement\n"}, "Approved tasks", (proof_git.base,)
    )
    proof_git.main = proof_git.authorization = proof_git.base
    proof_git.set_head(proof_git.base)
    proof_git.desired = proof_git.blob("- [x] 1.1 Implement\n")
    workflow_path = ".github/workflows/scheduled-agent-checkin.yml"
    workflow_blob = proof_git.blob("name: Runtime shard rollover\n")
    payload = proof_git.payload()
    cast(list[dict[str, object]], payload["files"]).append(
        {"path": workflow_path, "blob_sha": workflow_blob, "expected_sha": None}
    )
    monkeypatch.setattr(proof_git, "payload", lambda: payload)
    monkeypatch.setattr(carrier, "_github_json", proof_git.api)

    # This must succeed without allowing the application to write even Git
    # objects. Every requested path and blob stays fixed in the one plan.
    assert _prove_git(proof_git).disposition == "INCOMPLETE"
    with pytest.raises(CarrierRequired) as raised:
        _apply_git(proof_git)
    plan = raised.value.plan
    assert proof_git.mutations == []
    assert plan.operation == "pull-request-head-update"
    assert plan.force is False
    assert plan.expected["ref_sha"] == proof_git.base
    assert plan.expected["default_branch_sha"] == proof_git.main
    assert plan.expected["file_preimages"] == [
        {"path": proof_git.path, "sha": proof_git.entries(proof_git.base)[proof_git.path]["sha"]},
        {"path": workflow_path, "sha": None},
    ]
    assert plan.requested["commit_parents"] == [proof_git.base]
    assert plan.requested["base_tree_sha"] == proof_git.git(
        "rev-parse", f"{proof_git.base}^{{tree}}"
    )
    assert {
        entry["path"]: entry["sha"]
        for entry in cast(list[dict[str, object]], plan.requested["tree_elements"])
    } == {
        proof_git.path: proof_git.desired,
        workflow_path: workflow_blob,
    }

    # Simulate the already-configured connector's exact tree/commit/ref
    # actuator. The repository-owned proof, not its return value, completes
    # application materialization on a later fresh read.
    proof_git.allow_writes = True
    tree = cast(
        dict[str, str],
        proof_git.write(
            "git/trees",
            {
                "base_tree": plan.requested["base_tree_sha"],
                "tree": plan.requested["tree_elements"],
            },
        ),
    )
    commit = cast(
        dict[str, str],
        proof_git.write(
            "git/commits",
            {
                "tree": tree["sha"],
                "parents": plan.requested["commit_parents"],
                "message": plan.requested["commit_message"],
            },
        ),
    )
    proof_git.set_head(commit["sha"])
    proof = _prove_git(proof_git)
    assert proof.disposition == "COMPLETE", proof
    assert proof.target is not None and proof.target.revision == commit["sha"]
    before = list(proof_git.mutations)
    assert _apply_git(proof_git) == proof.target
    assert proof_git.mutations == before


def test_workflow_object_carrier_preserves_disjoint_main_and_rejects_stale_preimages(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import investment_strategy.scheduled_agent_application_carrier as carrier

    proof_git.source = WorkerRequest(322, "executor", "implement-change")
    proof_git.routing = proof_git.source.action
    proof_git.path = f"openspec/changes/{_CHANGE}/tasks.md"
    proof_git.base = proof_git.commit(
        {proof_git.path: "- [ ] 1.1 Implement\n"}, "Approved tasks", (proof_git.base,)
    )
    carrier_head = proof_git.base
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint main advance"}, "Advance main", (carrier_head,)
    )
    proof_git.authorization = proof_git.main
    proof_git.set_head(carrier_head)
    proof_git.desired = proof_git.blob("- [x] 1.1 Implement\n")
    workflow_path = ".github/workflows/scheduled-agent-checkin.yml"
    workflow_blob = proof_git.blob("name: New event trigger\n")
    payload = proof_git.payload()
    cast(list[dict[str, object]], payload["files"]).append(
        {"path": workflow_path, "blob_sha": workflow_blob, "expected_sha": None}
    )
    monkeypatch.setattr(proof_git, "payload", lambda: payload)
    monkeypatch.setattr(carrier, "_github_json", proof_git.api)

    with pytest.raises(CarrierRequired) as raised:
        _apply_git(proof_git)
    plan = raised.value.plan
    assert proof_git.mutations == []
    assert plan.expected["ref_sha"] == carrier_head
    assert plan.expected["default_branch_sha"] == proof_git.main
    assert plan.requested["commit_parents"] == [carrier_head, proof_git.main]
    entries = {
        entry["path"]: entry["sha"]
        for entry in cast(list[dict[str, object]], plan.requested["tree_elements"])
    }
    assert entries["README.md"] == proof_git.entries(proof_git.main)["README.md"]["sha"]
    assert entries[proof_git.path] == proof_git.desired
    assert entries[workflow_path] == workflow_blob

    proof_git.allow_writes = True
    tree = cast(
        dict[str, str],
        proof_git.write(
            "git/trees",
            {
                "base_tree": plan.requested["base_tree_sha"],
                "tree": plan.requested["tree_elements"],
            },
        ),
    )
    commit = cast(
        dict[str, str],
        proof_git.write(
            "git/commits",
            {
                "tree": tree["sha"],
                "parents": plan.requested["commit_parents"],
                "message": plan.requested["commit_message"],
            },
        ),
    )
    proof_git.set_head(commit["sha"])
    complete = _prove_git(proof_git)
    assert complete.disposition == "COMPLETE", complete
    assert proof_git.entries(proof_git.head)["README.md"]["sha"] == entries["README.md"]

    # A subsequent accepted request must not reuse the old plan against a
    # changed task preimage, even though a disjoint default advance was legal.
    stale = dict(payload)
    stale["files"] = [dict(file) for file in cast(list[dict[str, object]], payload["files"])]
    proof_git.set_head(carrier_head)
    competing = proof_git.commit(
        {proof_git.path: "- [ ] different task\n"}, "Concurrent task change", (carrier_head,)
    )
    proof_git.set_head(competing)
    before = list(proof_git.mutations)
    with pytest.raises(RuntimeError):
        _apply_git(proof_git, payload=stale)
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


def test_bad_accepted_preimage_preserves_witness_across_legal_second_commit(
    proof_git: _ProofGitRepository,
) -> None:
    """A historical manifest error and a later legal commit are distinct identities."""
    payload = proof_git.payload()
    files = cast(list[dict[str, object]], payload["files"])
    historical_bad_sha = "f" * 40
    files[0]["expected_sha"] = historical_bad_sha
    first_parent = proof_git.base
    first_commit = proof_git.commit(
        {proof_git.path: "accepted content"},
        proof_git.message,
        (first_parent,),
    )
    proof_git.set_head(first_commit)
    first_proof = _prove_payload_git(proof_git, payload, accepted_intent=True)
    assert first_proof.disposition == "COMPLETE", first_proof
    assert first_proof.witness is not None
    assert first_proof.witness.revision == first_commit
    assert first_proof.witness.revisions.mutation_preimage == first_parent

    # A disjoint default-branch revision and a second, same-Change edit cannot
    # invalidate the first immutable witness or reuse the old physical preimage.
    proof_git.main = proof_git.commit(
        {"README.md": "a newer default-branch revision"},
        "Disjoint default advance",
        (proof_git.main,),
    )
    second_parent = proof_git.head
    second_commit = proof_git.commit(
        {proof_git.path: "qualified later correction"},
        "Correct same Change",
        (second_parent,),
    )
    proof_git.set_head(second_commit)
    evolved = _prove_payload_git(proof_git, payload, accepted_intent=True)
    assert evolved.disposition == "COMPLETE", evolved
    assert evolved.target is not None and evolved.target.revision == second_commit
    assert evolved.witness is not None and evolved.witness.revision == first_commit
    assert evolved.witness.revisions.mutation_preimage == first_parent
    assert files[0]["expected_sha"] == historical_bad_sha
    assert proof_git.mutations == []


def test_partial_manifest_blob_match_is_not_a_complete_materialization_witness(
    proof_git: _ProofGitRepository,
) -> None:
    """One later matching blob does not prove a multi-file accepted effect."""
    payload = proof_git.payload()
    files = cast(list[dict[str, object]], payload["files"])
    files.append(
        {
            "path": f"openspec/changes/{_CHANGE}/tasks.md",
            "blob_sha": proof_git.blob("accepted tasks"),
            "expected_sha": None,
        }
    )
    partial = proof_git.commit(
        {proof_git.path: "accepted content"},
        "Later legal correction of one file",
        (proof_git.base,),
    )
    proof_git.set_head(partial)

    proof = _prove_payload_git(proof_git, payload, accepted_intent=True)

    assert proof.disposition != "COMPLETE", proof
    assert proof.witness is None
    assert proof_git.mutations == []


def test_six_file_322_shape_preserves_witness_after_second_legal_commit(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A six-file Executor shape must retain W after a fresh later commit.

    The task path is namespaced to the test Change; other five paths model the
    accepted #322 manifest. Synthetic blobs do not prove historical completion.
    """
    proof_git.source = WorkerRequest(322, "executor", "implement-change")
    proof_git.routing = "implement-change"
    monkeypatch.setattr(
        materialization, "_qualified_implementation_decision", lambda *_args, **_kwargs: None
    )
    paths = (
        f"openspec/changes/{_CHANGE}/tasks.md",
        "src/investment_strategy/scheduled_agent_application_bridge.py",
        "src/investment_strategy/scheduled_agent_effects.py",
        "src/investment_strategy/scheduled_agent_merge_acceptance.py",
        "tests/test_scheduled_agent_application_bridge.py",
        "tests/test_scheduled_agent_effects.py",
    )
    desired = {path: f"accepted content for {index}" for index, path in enumerate(paths)}
    payload = proof_git.payload()
    payload["files"] = [
        {
            "path": path,
            "blob_sha": proof_git.blob(desired[path]),
            # The final incorrect expected value models the real historical
            # mismatch; the actual Git tree remains the only preimage authority.
            "expected_sha": "a84065b222bb18b8adb56113b866484743f0e1a2" if index == 5 else None,
        }
        for index, path in enumerate(paths)
    ]
    initial_parent = proof_git.base
    first_commit = proof_git.commit(desired, proof_git.message, (initial_parent,))
    proof_git.set_head(first_commit)
    first = _prove_payload_git(proof_git, payload, accepted_intent=True)
    assert first.disposition == "COMPLETE", first
    assert first.witness is not None and first.witness.revision == first_commit

    second_commit = proof_git.commit(
        {paths[0]: "later legal task checkpoint"}, "Next Action", (first_commit,)
    )
    proof_git.set_head(second_commit)
    successor = _prove_payload_git(proof_git, payload, accepted_intent=True)
    assert successor.disposition == "COMPLETE", successor
    assert successor.target is not None and successor.target.revision == second_commit
    assert successor.witness is not None and successor.witness.revision == first_commit
    assert successor.witness.revisions.mutation_preimage == initial_parent
    assert proof_git.mutations == []


@pytest.mark.parametrize(
    "read_error",
    [
        OSError("authoritative issue observation unavailable"),
        json.JSONDecodeError("source response JSON truncated", "{", 0),
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid response bytes"),
    ],
)
def test_canonical_unavailable_github_observation_is_unknown_not_conflict(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    read_error: Exception,
) -> None:
    """An unknown read is neither a safe missing effect nor a proven conflict."""
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    api = proof_git.api

    def unavailable(repository: str, token: str, path: str, **kwargs: object) -> object:
        if path == "issues/322":
            raise read_error
        return api(repository, token, path, **kwargs)

    monkeypatch.setattr(materialization, "_github_json", unavailable)
    proof = _prove_git(proof_git)
    assert proof.disposition == "UNKNOWN", proof
    assert proof.witness is None
    assert proof.target is None
    assert proof.reason == str(read_error)
    with pytest.raises(RuntimeError):
        _apply_git(proof_git)
    assert proof_git.mutations == []


@pytest.mark.parametrize(
    "broken_source",
    (
        "carrier-pr-list",
        "matching-pr-list",
        "malformed-pr-entry",
        "commit-comparison",
        "commit-enumeration",
        "git-commit",
        "branch-ref",
    ),
)
def test_incomplete_source_shaped_materialization_proof_is_unknown(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    broken_source: str,
) -> None:
    """Truncated GitHub observations cannot become a proven semantic conflict."""
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    original_api = proof_git.api

    def incomplete_source(repository: str, token: str, path: str, **kwargs: object) -> object:
        observed = original_api(repository, token, path, **kwargs)
        if (
            broken_source == "carrier-pr-list"
            and path.startswith("pulls?")
            and "state=open" in path
        ):
            return {"unexpected": "incomplete pagination"}
        if (
            broken_source == "matching-pr-list"
            and path.startswith("pulls?")
            and "state=all" in path
        ):
            return {"unexpected": "incomplete pagination"}
        if (
            broken_source == "malformed-pr-entry"
            and path.startswith("pulls?")
            and "state=all" in path
        ):
            return [None]
        if broken_source == "commit-comparison" and path.startswith("compare/"):
            assert isinstance(observed, dict)
            return {key: value for key, value in observed.items() if key != "files"}
        if broken_source == "commit-enumeration" and path.startswith("compare/"):
            assert isinstance(observed, dict)
            return {**observed, "commits": []} if observed["ahead_by"] else observed
        if broken_source == "git-commit" and path == f"git/commits/{accepted}":
            assert isinstance(observed, dict)
            return {key: value for key, value in observed.items() if key != "parents"}
        if broken_source == "branch-ref" and path == f"git/ref/heads/{proof_git.branch}":
            return {"object": {}}
        return observed

    monkeypatch.setattr(materialization, "_github_json", incomplete_source)
    proof = _prove_git(proof_git)
    assert proof.disposition == "UNKNOWN", (broken_source, proof)
    assert proof.target is None and proof.witness is None
    assert proof.reason
    assert not proof_git.mutations


@pytest.mark.parametrize("broken_source", ("pr-head", "pr-base", "content-sha"))
def test_imported_reader_incomplete_github_observation_is_unknown(
    proof_git: _ProofGitRepository,
    monkeypatch: pytest.MonkeyPatch,
    broken_source: str,
) -> None:
    """Imported readers must not turn missing authoritative source fields into conflicts."""
    accepted = proof_git.commit(
        {proof_git.path: "accepted content"}, proof_git.message, (proof_git.base,)
    )
    proof_git.set_head(accepted)
    original_api = proof_git.api

    def incomplete(repository: str, token: str, path: str, **kwargs: object) -> object:
        observed = original_api(repository, token, path, **kwargs)
        if broken_source in {"pr-head", "pr-base"} and path == "pulls/324":
            assert isinstance(observed, dict)
            missing = "head" if broken_source == "pr-head" else "base"
            return {key: value for key, value in observed.items() if key != missing}
        if broken_source == "content-sha" and path.startswith("contents/"):
            return {"type": "file", "encoding": "base64"}
        return observed

    monkeypatch.setattr(materialization, "_github_json", incomplete)
    monkeypatch.setattr(validation_resource, "_github_json", incomplete)
    proof = _prove_git(proof_git)
    assert proof.disposition == "UNKNOWN", (broken_source, proof)
    assert proof.target is None and proof.witness is None
    assert proof.reason
    assert proof_git.mutations == []
