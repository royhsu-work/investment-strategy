"""Tests for application-owned exact validation/work-product helpers."""

from __future__ import annotations

import base64
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from urllib.parse import unquote
from urllib.request import Request

import pytest

import investment_strategy.scheduled_agent_validation_resource as resource
from investment_strategy.scheduled_agent_application_carrier import (
    ImplementationCarrierQualification,
)
from investment_strategy.scheduled_agent_carrier import CarrierRequired
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from tests.test_scheduled_agent_application_materialization import (
    _accepted_git_carrier,
    _postcondition_git,
    _ProofGitRepository,
    test_canonical_git_proof_survives_disjoint_advance_reconciliation_and_merge,
    test_canonical_replacement_has_its_own_target_and_legal_descendants,
)
from tests.test_scheduled_agent_application_materialization import (
    proof_git as proof_git,
)

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "013510b12c5d3cde869308a319a1e2fb12cdfa60"
_PR_HEAD = "05e1e84523651c6a9bc4ebbe4b275b12dae74dbf"
_CHANGE = "simplify-scheduled-agent-control-plane"
_FIXTURE_VALUE = "fixture-value"


def test_candidate_checkout_uses_actions_compatible_basic_auth() -> None:
    environment = resource._candidate_subprocess_environment(_FIXTURE_VALUE)

    assert environment["GIT_CONFIG_VALUE_0"] == (
        "AUTHORIZATION: basic "
        + base64.b64encode(f"x-access-token:{_FIXTURE_VALUE}".encode()).decode()
    )
    assert "GITHUB_TOKEN" not in environment


def test_github_json_uses_repository_endpoint_for_empty_api_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_urls: list[str] = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self) -> bytes:
            return b'{"default_branch":"main"}'

    def fake_urlopen(request: Request, timeout: int) -> FakeResponse:
        del timeout
        requested_urls.append(cast(str, request.full_url))
        return FakeResponse()

    monkeypatch.setattr(resource, "urlopen", fake_urlopen)

    assert resource._github_json(_REPOSITORY, _FIXTURE_VALUE, "") == {"default_branch": "main"}
    assert requested_urls == [f"https://api.github.com/repos/{_REPOSITORY}"]


def test_pending_source_can_reconcile_one_derived_successor_frontier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(322, "lead", "resolve-question")
    issue = {
        "number": source.issue_number,
        "state": "open",
        "created_at": "2026-09-27T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "action:review-openspec"}],
        "body": "Change: restore-no-work-idle-discovery\n",
    }
    monkeypatch.setattr(resource, "_github_json", lambda *_args, **_kwargs: issue)

    assert not resource._pending_source_is_current(
        _REPOSITORY,
        _FIXTURE_VALUE,
        source,
        "restore-no-work-idle-discovery",
    )
    assert resource._pending_source_is_current(
        _REPOSITORY,
        _FIXTURE_VALUE,
        source,
        "restore-no-work-idle-discovery",
        accepted_successor_routing=("reviewer", "review-openspec"),
    )
    assert not resource._pending_source_is_current(
        _REPOSITORY,
        _FIXTURE_VALUE,
        source,
        "restore-no-work-idle-discovery",
        accepted_successor_routing=("reviewer", "review-implementation"),
    )

    issue["labels"] = []
    assert not resource._pending_source_is_current(
        _REPOSITORY,
        _FIXTURE_VALUE,
        source,
        "restore-no-work-idle-discovery",
    )


def test_blob_text_requires_exact_response_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        resource,
        "_github_json",
        lambda *_args, **_kwargs: {
            "sha": "b" * 40,
            "encoding": "base64",
            "content": "Y2FuZGlkYXRl",
        },
    )

    with pytest.raises(RuntimeError, match="work-product blob text is incomplete"):
        resource._blob_text(_REPOSITORY, _FIXTURE_VALUE, "a" * 40)


def test_implementation_candidate_runs_quality_on_exact_overlaid_blobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = "tests/test_candidate.py"
    candidate = "def test_candidate() -> None:\n    assert True\n"
    commands: list[tuple[str, ...]] = []

    monkeypatch.setattr(resource, "_blob_text", lambda *_args, **_kwargs: candidate)

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        env: Mapping[str, str],
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        commands.append(command)
        if command[0] == "uv" or command == ("git", "rev-parse", "HEAD"):
            assert "GIT_CONFIG_VALUE_0" not in env
        if command == ("git", "rev-parse", "HEAD"):
            return subprocess.CompletedProcess(command, 0, stdout=f"{_REVISION}\n", stderr="")
        if command == ("uv", "run", "pytest"):
            assert (cwd / path).read_text(encoding="utf-8") == candidate
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(resource.subprocess, "run", fake_run)
    file = resource.WorkProductFile(path, "b" * 40, "a" * 40)

    assert resource.verify_implementation_candidate(
        _REPOSITORY,
        _FIXTURE_VALUE,
        base_sha=_REVISION,
        base_ref="agent/example",
        current_revision=_REVISION,
        files=(file,),
    )
    assert commands[:4] == [
        ("git", "init", "--quiet"),
        ("git", "remote", "add", "origin", f"https://github.com/{_REPOSITORY}.git"),
        ("git", "fetch", "--quiet", "--depth=1", "origin", "refs/heads/agent/example"),
        ("git", "checkout", "--quiet", "--detach", _REVISION),
    ]
    assert commands[4:] == [
        ("git", "rev-parse", "HEAD"),
        *resource._IMPLEMENTATION_VERIFICATION_COMMANDS,
    ]


def test_implementation_candidate_failure_is_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resource, "_blob_text", lambda *_args, **_kwargs: "candidate\n")

    def fake_run(
        command: tuple[str, ...],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs
        return subprocess.CompletedProcess(
            command,
            1 if command == ("uv", "run", "ruff", "format", "--check", ".") else 0,
            stdout=f"{_REVISION}\n" if command == ("git", "rev-parse", "HEAD") else "",
            stderr="",
        )

    monkeypatch.setattr(resource.subprocess, "run", fake_run)
    file = resource.WorkProductFile("src/candidate.py", "b" * 40, "a" * 40)

    assert not resource.verify_implementation_candidate(
        _REPOSITORY,
        _FIXTURE_VALUE,
        base_sha=_REVISION,
        current_revision=_REVISION,
        files=(file,),
    )


def test_validation_plan_has_no_transport_or_comment_correlation() -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    plan = resource.ValidationResourcePlan(
        True,
        source=source,
        pr_number=178,
        expected_change=_CHANGE,
    )
    assert set(plan.__dataclass_fields__) == {
        "should_validate",
        "source",
        "pr_number",
        "expected_change",
    }


def test_resource_derives_current_pr_head_after_fresh_reauthorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    plan = resource.ValidationResourcePlan(
        True,
        source=source,
        pr_number=178,
        expected_change=_CHANGE,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_: source)

    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "issues/138":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178":
            return {
                "number": 178,
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {
                    "sha": _PR_HEAD,
                    "ref": f"agent/{_CHANGE}",
                    "repo": {"full_name": _REPOSITORY},
                },
                "base": {
                    "ref": "main",
                    "sha": _REVISION,
                    "repo": {"full_name": _REPOSITORY},
                },
            }
        if api_path == "pulls/178/files?per_page=100":
            return [
                {"filename": f"openspec/changes/{_CHANGE}/proposal.md"},
                {"filename": f"openspec/changes/{_CHANGE}/design.md"},
                {"filename": f"openspec/changes/{_CHANGE}/tasks.md"},
            ]
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    target = resource.resolve_validation_resource_target(
        plan,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        default_branch="main",
    )

    assert target.repository == _REPOSITORY
    assert target.revision == _PR_HEAD
    assert target.correlation == "effect-request-138"
    assert target.pr_number == 178
    assert target.change == _CHANGE
    assert target.validation_required


def test_resource_rejects_source_without_review_openspec_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    plan = resource.ValidationResourcePlan(
        True,
        source=source,
        pr_number=178,
        expected_change=_CHANGE,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_: source)

    with pytest.raises(RuntimeError, match="not required by the current Action gate"):
        resource.resolve_validation_resource_target(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
        )


def test_implementation_validation_target_reuses_carrier_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(229, "reviewer", "review-implementation")
    branch = f"agent/{_CHANGE}-continuation-178"
    decision = ImplementationCarrierQualification(
        disposition="QUALIFIED",
        reason="fixture-qualified-continuation",
        repository=_REPOSITORY,
        issue_number=source.issue_number,
        change=_CHANGE,
        action=source.action,
        pr_number=178,
        branch=branch,
        head_sha=_PR_HEAD,
        default_branch="main",
        default_revision=_REVISION,
        historical_pr_number=178,
    )
    plan = resource.ValidationResourcePlan(
        True,
        source=source,
        pr_number=178,
        expected_change=_CHANGE,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_args: source)
    monkeypatch.setattr(
        resource,
        "_implementation_carrier_decision",
        lambda *_args, **_kwargs: decision,
    )

    target = resource.resolve_validation_resource_target(
        plan,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        default_branch="main",
    )

    assert target.revision == _PR_HEAD
    assert target.pr_number == 178
    assert target.branch == branch


def test_executor_task_marker_is_the_only_nonreview_openspec_work_product() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    task_path = f"openspec/changes/{_CHANGE}/tasks.md"
    task_file = resource.WorkProductFile(task_path, "b" * 40, "a" * 40)
    design_file = resource.WorkProductFile(
        f"openspec/changes/{_CHANGE}/design.md", "b" * 40, "a" * 40
    )
    assert resource._is_executor_task_bookkeeping(source, _CHANGE, (task_file,))
    assert not resource._is_executor_task_bookkeeping(source, _CHANGE, (design_file,))
    assert not resource._is_executor_task_bookkeeping(source, _CHANGE, (task_file, design_file))


def test_executor_config_authoring_is_narrowly_bound() -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    reviewer = WorkerRequest(138, "reviewer", "review-openspec")
    config_file = resource.WorkProductFile("openspec/config.yaml", "b" * 40, "a" * 40)
    task_file = resource.WorkProductFile(f"openspec/changes/{_CHANGE}/tasks.md", "b" * 40, "a" * 40)
    spec_file = resource.WorkProductFile(
        "openspec/specs/repository-governance/spec.md", "b" * 40, "a" * 40
    )

    assert resource._is_executor_config_authoring(source, _CHANGE, (config_file,))
    assert not resource._is_executor_config_authoring(source, _CHANGE, (config_file, task_file))
    assert not resource._is_executor_config_authoring(source, _CHANGE, (spec_file,))
    assert not resource._is_executor_config_authoring(reviewer, _CHANGE, (config_file,))


def test_executor_task_marker_update_accepts_only_monotonic_checkbox_changes() -> None:
    current = "- [ ] 2.1 first implementation task\n- [ ] 2.2 second implementation task\n"
    valid = "- [x] 2.1 first implementation task\n- [ ] 2.2 second implementation task\n"
    assert resource._task_marker_update_is_monotonic(current, valid)

    invalid_candidates = (
        current,
        ("- [x] 2.1 renamed implementation task\n- [ ] 2.2 second implementation task\n"),
        (
            "- [x] 2.1 first implementation task\n"
            "- [ ] 2.2 second implementation task\n"
            "- [ ] 2.3 added task\n"
        ),
        "- [x] 2.1 first implementation task\n",
        ("- [ ] 2.2 second implementation task\n- [x] 2.1 first implementation task\n"),
    )
    assert all(
        not resource._task_marker_update_is_monotonic(current, candidate)
        for candidate in invalid_candidates
    )

    previously_checked = valid
    unchecked = current
    assert not resource._task_marker_update_is_monotonic(previously_checked, unchecked)


def test_task_checkpoint_matches_only_first_incomplete_slice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_path = f"openspec/changes/{_CHANGE}/tasks.md"
    current = (
        "## Slice 1 — first\n"
        "- [ ] 1.1 first task\n"
        "- [ ] 1.2 second task\n"
        "## Slice 2 — later\n"
        "- [ ] 2.1 later task\n"
    )
    valid = current.replace("- [ ] 1.1", "- [x] 1.1").replace("- [ ] 1.2", "- [x] 1.2")
    multi_slice = valid.replace("- [ ] 2.1", "- [x] 2.1")
    candidate = valid
    task_file = resource.WorkProductFile(task_path, "b" * 40, _REVISION)

    monkeypatch.setattr(
        resource,
        "_content_sha_at",
        lambda *_args, **_kwargs: _REVISION,
    )
    monkeypatch.setattr(resource, "_content_text_at", lambda *_args, **_kwargs: current)
    monkeypatch.setattr(
        resource,
        "_blob_text",
        lambda *_args, **_kwargs: candidate,
    )

    assert resource.task_checkpoint_is_exact(
        _REPOSITORY,
        _FIXTURE_VALUE,
        expected_change=_CHANGE,
        base_sha=_REVISION,
        file=task_file,
        completed_task_ids=("1.1", "1.2"),
    )

    candidate = multi_slice
    assert not resource.task_checkpoint_is_exact(
        _REPOSITORY,
        _FIXTURE_VALUE,
        expected_change=_CHANGE,
        base_sha=_REVISION,
        file=task_file,
        completed_task_ids=("1.1", "1.2"),
    )

    candidate = current.replace("- [ ] 1.1", "- [x] 1.1")
    assert not resource.task_checkpoint_is_exact(
        _REPOSITORY,
        _FIXTURE_VALUE,
        expected_change=_CHANGE,
        base_sha=_REVISION,
        file=task_file,
        completed_task_ids=("1.1",),
    )


def test_task_checkpoint_accepts_standard_openspec_numbered_slices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_path = f"openspec/changes/{_CHANGE}/tasks.md"
    current = (
        "# Tasks: example\n\n"
        "## 1. first\n"
        "- [ ] 1.1 first task\n"
        "- [ ] 1.2 second task\n"
        "## 2. later\n"
        "- [ ] 2.1 later task\n"
    )
    valid = current.replace("- [ ] 1.1", "- [x] 1.1").replace("- [ ] 1.2", "- [x] 1.2")
    multi_slice = valid.replace("- [ ] 2.1", "- [x] 2.1")
    task_file = resource.WorkProductFile(task_path, "b" * 40, _REVISION)

    monkeypatch.setattr(resource, "_content_sha_at", lambda *_args, **_kwargs: _REVISION)
    monkeypatch.setattr(resource, "_content_text_at", lambda *_args, **_kwargs: current)
    monkeypatch.setattr(resource, "_blob_text", lambda *_args, **_kwargs: valid)
    assert resource.task_checkpoint_is_exact(
        _REPOSITORY,
        _FIXTURE_VALUE,
        expected_change=_CHANGE,
        base_sha=_REVISION,
        file=task_file,
        completed_task_ids=("1.1", "1.2"),
    )

    monkeypatch.setattr(resource, "_blob_text", lambda *_args, **_kwargs: multi_slice)
    assert not resource.task_checkpoint_is_exact(
        _REPOSITORY,
        _FIXTURE_VALUE,
        expected_change=_CHANGE,
        base_sha=_REVISION,
        file=task_file,
        completed_task_ids=("1.1", "1.2"),
    )


def test_constructor_apply_work_product_rejects_non_monotonic_task_marker_before_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    task_path = f"openspec/changes/{_CHANGE}/tasks.md"
    plan = _work_product_plan(
        source=source,
        path=task_path,
        blob_sha="b" * 40,
        expected_sha="a" * 40,
    )
    current = "- [ ] 2.1 first implementation task\n- [ ] 2.2 second implementation task\n"
    invalid = "- [x] 2.1 renamed implementation task\n- [ ] 2.2 second implementation task\n"
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_: source)
    monkeypatch.setattr(
        resource,
        "_open_pr_payload",
        lambda **_: {
            "number": 178,
            "state": "open",
            "merged": False,
            "body": "Refs #138\\n",
            "head": {
                "sha": _PR_HEAD,
                "ref": f"agent/{_CHANGE}",
                "repo": {"full_name": _REPOSITORY},
            },
            "base": {
                "ref": "main",
                "sha": _REVISION,
                "repo": {"full_name": _REPOSITORY},
            },
        },
    )
    monkeypatch.setattr(
        resource,
        "_ref_head_sha",
        lambda _repository, _token, branch: _REVISION if branch == "main" else _PR_HEAD,
    )
    monkeypatch.setattr(
        resource,
        "_default_branch_is_ancestor",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        resource,
        "_content_sha_at",
        lambda *_args, **_kwargs: "a" * 40,
    )
    monkeypatch.setattr(
        resource,
        "_content_text_at",
        lambda *_args, **_kwargs: current,
    )
    monkeypatch.setattr(resource, "_blob_text", lambda *_args, **_kwargs: invalid)

    def fail_github_json(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("task guard must run before GitHub tree construction")

    monkeypatch.setattr(resource, "_github_json", fail_github_json)
    with pytest.raises(RuntimeError, match="monotonic checkbox-only"):
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=_REVISION,
        )


def test_constructor_apply_work_product_reuses_continuation_carrier_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Continuation branch identity comes from the shared carrier owner."""

    source = WorkerRequest(229, "executor", "implement-change")
    continuation_branch = f"agent/{_CHANGE}-continuation-178"
    plan = resource.WorkProductPlan(
        True,
        source=source,
        pr_number=178,
        expected_change=_CHANGE,
        manifest=resource.WorkProductManifest(
            branch=continuation_branch,
            base_sha=_REVISION,
            message="Continue implementation after the merged carrier",
            files=(
                resource.WorkProductFile(
                    path="src/investment_strategy/example.py",
                    blob_sha="b" * 40,
                    expected_sha="a" * 40,
                ),
            ),
        ),
    )
    decisions: list[tuple[WorkerRequest, str, int]] = []

    def fake_decision(
        decision_source: WorkerRequest,
        *,
        repository: str,
        token: str,
        default_branch: str,
        expected_change: str,
        pr_number: int,
    ) -> ImplementationCarrierQualification:
        assert (repository, token, default_branch) == (_REPOSITORY, _FIXTURE_VALUE, "main")
        decisions.append((decision_source, expected_change, pr_number))
        return ImplementationCarrierQualification(
            disposition="QUALIFIED",
            reason="fixture-qualified-continuation",
            repository=repository,
            issue_number=decision_source.issue_number,
            change=expected_change,
            action=decision_source.action,
            pr_number=pr_number,
            branch=continuation_branch,
            head_sha=_PR_HEAD,
            default_branch=default_branch,
            default_revision=_REVISION,
            historical_pr_number=178,
        )

    class _ReachedOpenPR(RuntimeError):
        pass

    def fail_open_pr(**kwargs: object) -> Mapping[str, object]:
        assert kwargs["expected_branch"] == continuation_branch
        raise _ReachedOpenPR

    monkeypatch.setattr(resource, "_ref_head_sha", lambda *_args, **_kwargs: _REVISION)
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_args: source)
    monkeypatch.setattr(resource, "_implementation_carrier_decision", fake_decision)
    monkeypatch.setattr(resource, "_open_pr_payload", fail_open_pr)

    with pytest.raises(_ReachedOpenPR):
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=_REVISION,
        )

    assert decisions == [(source, _CHANGE, 178)]


def _work_product_plan(
    *,
    source: WorkerRequest,
    path: str,
    blob_sha: str,
    expected_sha: str | None,
) -> resource.WorkProductPlan:
    return resource.WorkProductPlan(
        True,
        source=source,
        pr_number=178,
        expected_change=_CHANGE,
        manifest=resource.WorkProductManifest(
            branch=f"agent/{_CHANGE}",
            base_sha=_PR_HEAD,
            message="Correct #138 N-1 ordering",
            files=(
                resource.WorkProductFile(
                    path=path,
                    blob_sha=blob_sha,
                    expected_sha=expected_sha,
                ),
            ),
        ),
    )


def test_constructor_apply_work_product_builds_one_tree_and_one_commit_then_observes_exact_r(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    expected_sha = "a" * 40
    blob_sha = "b" * 40
    tree_sha = "c" * 40
    revision = "d" * 40
    path = f"openspec/changes/{_CHANGE}/design.md"
    plan = _work_product_plan(
        source=source,
        path=path,
        blob_sha=blob_sha,
        expected_sha=expected_sha,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_: source)
    head_sha = _PR_HEAD
    tree_payloads: list[object] = []
    commit_payloads: list[object] = []

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        nonlocal head_sha
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        del allow_not_found
        if api_path == "" and method == "GET":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main" and method == "GET":
            return {"object": {"sha": _REVISION}}
        if api_path == f"compare/{_REVISION}...{_PR_HEAD}" and method == "GET":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "merge_base_commit": {"sha": _REVISION},
                "files": [{"filename": path}],
                "commits": [{"sha": _PR_HEAD}],
            }
        if api_path == "issues/138" and method == "GET":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178" and method == "GET":
            return {
                "number": 178,
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {
                    "sha": head_sha,
                    "ref": f"agent/{_CHANGE}",
                    "repo": {"full_name": _REPOSITORY},
                },
                "base": {
                    "ref": "main",
                    "sha": _REVISION,
                    "repo": {"full_name": _REPOSITORY},
                },
            }
        if api_path == "pulls/178/files?per_page=100" and method == "GET":
            return [{"filename": path}]
        if api_path.startswith(f"contents/{path}?") and method == "GET":
            return {"sha": expected_sha if f"ref={_PR_HEAD}" in api_path else blob_sha}
        if api_path == f"git/commits/{_PR_HEAD}" and method == "GET":
            return {"sha": _PR_HEAD, "tree": {"sha": "e" * 40}, "parents": []}
        if api_path == "git/trees" and method == "POST":
            tree_payloads.append(payload)
            return {"sha": tree_sha}
        if api_path == f"git/trees/{tree_sha}?recursive=1" and method == "GET":
            return {
                "sha": tree_sha,
                "truncated": False,
                "tree": [{"path": path, "type": "blob", "sha": blob_sha}],
            }
        if api_path == "git/commits" and method == "POST":
            commit_payloads.append(payload)
            return {"sha": revision}
        if api_path == f"git/refs/heads/agent/{_CHANGE}" and method == "PATCH":
            assert payload == {"sha": revision, "force": False}
            head_sha = revision
            return {"object": {"sha": revision}}
        if api_path == f"git/ref/heads/agent/{_CHANGE}" and method == "GET":
            return {"object": {"sha": head_sha}}
        if api_path == f"git/commits/{revision}" and method == "GET":
            return {
                "sha": revision,
                "message": "Correct #138 N-1 ordering",
                "tree": {"sha": tree_sha},
                "parents": [{"sha": _PR_HEAD}],
            }
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    with pytest.raises(CarrierRequired) as raised:
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=_REVISION,
        )

    carrier_plan = raised.value.plan
    assert carrier_plan.operation == "pull-request-head-update"
    assert carrier_plan.requested["sha"] == revision
    assert carrier_plan.requested["force"] is False
    assert len(tree_payloads) == 1
    assert len(commit_payloads) == 1
    assert commit_payloads[0] == {
        "message": "Correct #138 N-1 ordering",
        "tree": tree_sha,
        "parents": [_PR_HEAD],
    }


def test_constructor_apply_work_product_builds_same_change_replacement_after_merged_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    expected_sha = "a" * 40
    blob_sha = "b" * 40
    tree_sha = "c" * 40
    revision = "d" * 40
    merge_commit = "e" * 40
    replacement_branch = f"agent/{_CHANGE}-continuation-178"
    path = "src/investment_strategy/example.py"
    plan = resource.WorkProductPlan(
        True,
        source=source,
        pr_number=178,
        expected_change=_CHANGE,
        manifest=resource.WorkProductManifest(
            branch=f"agent/{_CHANGE}",
            base_sha=_REVISION,
            message="Continue #138 after merged carrier",
            files=(resource.WorkProductFile(path, blob_sha, expected_sha),),
        ),
    )
    old_pr = {
        "number": 178,
        "state": "closed",
        "merged": True,
        "merged_at": "2026-09-09T00:00:00Z",
        "merge_commit_sha": merge_commit,
        "body": "Implementation\n\nRefs #138\n",
        "head": {
            "ref": f"agent/{_CHANGE}",
            "sha": _PR_HEAD,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": _REVISION,
            "repo": {"full_name": _REPOSITORY},
        },
    }
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_: source)

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        del payload
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        if api_path == "issues/138":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178":
            return old_pr
        if api_path == "pulls/178/files?per_page=100":
            return [{"filename": f"openspec/changes/{_CHANGE}/design.md"}]
        if api_path == f"compare/{merge_commit}...{_REVISION}":
            return {"status": "ahead", "ahead_by": 1, "behind_by": 0}
        if api_path == f"compare/{_PR_HEAD}...{_REVISION}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": _PR_HEAD},
                "commits": [{"sha": _REVISION}],
                "total_commits": 1,
            }
        if api_path == f"compare/{_REVISION}...{_PR_HEAD}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "base_commit": {"sha": _REVISION},
                "commits": [{"sha": _PR_HEAD}],
                "total_commits": 1,
            }
        if api_path == f"compare/{_REVISION}...{_REVISION}":
            return {"status": "identical", "ahead_by": 0, "behind_by": 0}
        if api_path.startswith("pulls?state=open"):
            assert replacement_branch.replace("/", "%2F") in api_path
            return []
        if unquote(api_path) == f"git/ref/heads/{replacement_branch}":
            if allow_not_found:
                return None
            return {"object": {"sha": revision}}
        if api_path.startswith(f"contents/{path}?"):
            return {"sha": blob_sha if f"ref={revision}" in api_path else expected_sha}
        if api_path == f"git/commits/{_REVISION}":
            return {"sha": _REVISION, "tree": {"sha": "f" * 40}, "parents": []}
        if api_path == "git/trees" and method == "POST":
            return {"sha": tree_sha}
        if api_path == f"git/trees/{tree_sha}?recursive=1":
            return {
                "sha": tree_sha,
                "truncated": False,
                "tree": [{"path": path, "type": "blob", "sha": blob_sha}],
            }
        if api_path == "git/commits" and method == "POST":
            return {"sha": revision}
        if api_path == "git/refs" and method == "POST":
            return {"object": {"sha": revision}}
        if api_path == f"git/commits/{revision}":
            return {
                "sha": revision,
                "message": "Continue #138 after merged carrier",
                "tree": {"sha": tree_sha},
                "parents": [{"sha": _REVISION}],
            }
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    with pytest.raises(CarrierRequired) as raised:
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=_REVISION,
        )

    carrier_plan = raised.value.plan
    assert carrier_plan.operation == "pull-request-create"
    assert carrier_plan.requested["head"] == replacement_branch
    assert carrier_plan.expected["historical_pull_request"] == 178


def test_constructor_existing_replacement_reconciles_after_disjoint_default_advance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exact replacement carrier is reconciled when main advances disjointly."""

    source = WorkerRequest(322, "lead", "resolve-question")
    change = "restore-no-work-idle-discovery"
    accepted_base = "1" * 40
    current_main = "2" * 40
    historical_head = "3" * 40
    historical_merge_commit = "4" * 40
    replacement_head = "5" * 40
    tree_sha = "6" * 40
    reconciled_revision = "7" * 40
    historical_branch = f"agent/{change}-continuation-324"
    replacement_branch = f"agent/{change}-continuation-347"
    path = f"openspec/changes/{change}/proposal.md"
    expected_sha = "8" * 40
    blob_sha = "9" * 40
    manifest = resource.WorkProductManifest(
        branch=historical_branch,
        base_sha=accepted_base,
        message="Correct #322 NO_WORK idle completion semantics",
        files=(resource.WorkProductFile(path, blob_sha, expected_sha),),
    )
    plan = resource.WorkProductPlan(
        True,
        source=source,
        pr_number=347,
        expected_change=change,
        manifest=manifest,
    )
    historical_pr = {
        "number": 347,
        "state": "closed",
        "merged": True,
        "merged_at": "2026-10-01T00:00:00Z",
        "merge_commit_sha": historical_merge_commit,
        "body": "Continue OpenSpec change.\n\nRefs #322\n",
        "head": {
            "ref": historical_branch,
            "sha": historical_head,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": accepted_base,
            "repo": {"full_name": _REPOSITORY},
        },
    }
    replacement_pr = {
        "number": 353,
        "state": "open",
        "merged": False,
        "draft": False,
        "body": "Continue OpenSpec change.\n\nRefs #322\n",
        "head": {
            "ref": replacement_branch,
            "sha": replacement_head,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": accepted_base,
            "repo": {"full_name": _REPOSITORY},
        },
    }
    decision = resource.ImplementationCarrierQualification(
        disposition="QUALIFIED",
        reason="continuation-carrier-qualified",
        repository=_REPOSITORY,
        issue_number=322,
        change=change,
        action=source.action,
        pr_number=347,
        branch=historical_branch,
        head_sha=historical_head,
        default_branch="main",
        default_revision=current_main,
        historical_pr_number=324,
    )
    default_paths = [{"README.md"}]
    mutations: list[tuple[str, dict[str, object] | None]] = []

    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_args: source)
    monkeypatch.setattr(
        resource,
        "_change_carrier_decision",
        lambda *_args, **_kwargs: decision,
    )
    monkeypatch.setattr(
        resource,
        "_open_pr_payload",
        lambda **kwargs: historical_pr if kwargs["pr_number"] == 347 else replacement_pr,
    )
    monkeypatch.setattr(
        resource,
        "_open_prs_for_branch",
        lambda *_args, branch, **_kwargs: (
            ({"number": 353},) if branch == replacement_branch else ()
        ),
    )
    monkeypatch.setattr(
        resource,
        "_ref_head_sha",
        lambda _repository, _token, ref, **_kwargs: (
            current_main
            if ref == "main"
            else replacement_head
            if ref == replacement_branch
            else historical_head
        ),
    )
    monkeypatch.setattr(
        resource,
        "_default_branch_is_ancestor",
        lambda _repository, _token, *, default_revision, revision: (
            default_revision == historical_merge_commit and revision == current_main
        ),
    )
    monkeypatch.setattr(
        resource,
        "_ancestor_comparison_paths",
        lambda _repository, _token, *, base_sha, revision: (
            set(default_paths[0])
            if base_sha == accepted_base and revision == current_main
            else set()
        ),
    )
    monkeypatch.setattr(
        resource,
        "_revision_matches_manifest",
        lambda _repository, _token, *, base_sha, revision, manifest: (
            base_sha == accepted_base
            and revision == replacement_head
            and manifest.files[0].path == path
        ),
    )
    monkeypatch.setattr(
        resource,
        "_manifest_content_matches",
        lambda _repository, _token, *, revision, manifest: (
            revision in {replacement_head, reconciled_revision}
            and manifest.files[0].blob_sha == blob_sha
        ),
    )
    monkeypatch.setattr(
        resource,
        "_is_reconciled_work_product_revision",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        resource,
        "_content_sha_at",
        lambda _repository, _token, **kwargs: (
            blob_sha
            if kwargs["path"] == path and kwargs["revision"] == reconciled_revision
            else expected_sha
        ),
    )

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        **_kwargs: object,
    ) -> object:
        if method != "GET":
            mutations.append((api_path, payload))
        if api_path == f"git/commits/{current_main}" and method == "GET":
            return {"sha": current_main, "tree": {"sha": "a" * 40}}
        if api_path == "git/trees" and method == "POST":
            assert payload == {
                "base_tree": "a" * 40,
                "tree": [
                    {
                        "path": path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_sha,
                    }
                ],
            }
            return {"sha": tree_sha}
        if api_path == f"git/trees/{tree_sha}?recursive=1" and method == "GET":
            return {
                "sha": tree_sha,
                "truncated": False,
                "tree": [{"path": path, "type": "blob", "sha": blob_sha}],
            }
        if api_path == "git/commits" and method == "POST":
            assert payload == {
                "message": "Correct #322 NO_WORK idle completion semantics",
                "tree": tree_sha,
                "parents": [replacement_head, current_main],
            }
            return {"sha": reconciled_revision}
        if api_path == f"git/commits/{reconciled_revision}" and method == "GET":
            return {
                "sha": reconciled_revision,
                "message": "Correct #322 NO_WORK idle completion semantics",
                "tree": {"sha": tree_sha},
                "parents": [{"sha": replacement_head}, {"sha": current_main}],
            }
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)

    with pytest.raises(CarrierRequired) as raised:
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=current_main,
        )

    carrier_plan = raised.value.plan
    assert carrier_plan.operation == "pull-request-head-update"
    assert carrier_plan.requested["sha"] == reconciled_revision
    assert carrier_plan.requested["expected_head_sha"] == replacement_head
    assert carrier_plan.requested["commit_parents"] == [replacement_head, current_main]

    mutations.clear()
    default_paths[0] = {path}
    with pytest.raises(RuntimeError, match="replacement work-product base is not current"):
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=current_main,
        )
    assert mutations == []


def test_reconciliation_overlays_default_only_changes_on_a_stale_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = f"openspec/changes/{_CHANGE}/design.md"
    manifest = resource.WorkProductManifest(
        branch=f"agent/{_CHANGE}",
        base_sha=_PR_HEAD,
        message="Correct #138 N-1 ordering",
        files=(
            resource.WorkProductFile(
                path=path,
                blob_sha="b" * 40,
                expected_sha="a" * 40,
            ),
        ),
    )
    default_only_path = "README.md"
    default_sha = "f" * 40
    carrier_sha = "g" * 40
    merge_base = "e" * 40
    requested_urls: list[str] = []

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        del method, payload, allow_not_found
        requested_urls.append(api_path)
        if api_path == f"compare/{_REVISION}...{_PR_HEAD}":
            return {
                "status": "diverged",
                "merge_base_commit": {"sha": merge_base},
            }
        if api_path == f"compare/{merge_base}...{_REVISION}":
            return {"files": [{"filename": default_only_path, "status": "modified"}]}
        if api_path == f"compare/{merge_base}...{_PR_HEAD}":
            return {"files": []}
        if api_path.startswith(f"contents/{default_only_path}?"):
            return {"sha": default_sha}
        if api_path.startswith(f"contents/{default_only_path}?") and "ref=" in api_path:
            return {"sha": carrier_sha}
        raise AssertionError(api_path)

    def fake_content_sha(
        _repository: str,
        _token: str,
        *,
        path: str,
        revision: str,
    ) -> str | None:
        assert path == default_only_path
        return default_sha if revision == _REVISION else carrier_sha

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    monkeypatch.setattr(resource, "_content_sha_at", fake_content_sha)

    elements = resource._reconciliation_tree_elements(
        _REPOSITORY,
        _FIXTURE_VALUE,
        default_revision=_REVISION,
        carrier_revision=_PR_HEAD,
        manifest=manifest,
    )

    assert elements == [
        {
            "path": default_only_path,
            "mode": "100644",
            "type": "blob",
            "sha": default_sha,
        },
        {
            "path": path,
            "mode": "100644",
            "type": "blob",
            "sha": "b" * 40,
        },
    ]


def test_constructor_apply_work_product_reconciles_diverged_default_branch_with_two_parents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    expected_sha = "a" * 40
    blob_sha = "b" * 40
    tree_sha = "c" * 40
    revision = "d" * 40
    merge_base = "e" * 40
    path = f"openspec/changes/{_CHANGE}/design.md"
    default_only_path = "README.md"
    plan = _work_product_plan(
        source=source,
        path=path,
        blob_sha=blob_sha,
        expected_sha=expected_sha,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_: source)
    commit_payloads: list[object] = []

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        del allow_not_found
        if api_path == "" and method == "GET":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main" and method == "GET":
            return {"object": {"sha": _REVISION}}
        if api_path == f"compare/{_REVISION}...{_PR_HEAD}" and method == "GET":
            return {
                "status": "diverged",
                "ahead_by": 1,
                "behind_by": 1,
                "merge_base_commit": {"sha": merge_base},
            }
        if api_path == f"compare/{merge_base}...{_REVISION}" and method == "GET":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "files": [{"filename": default_only_path, "status": "modified"}],
            }
        if api_path == f"compare/{merge_base}...{_PR_HEAD}" and method == "GET":
            return {"status": "identical", "ahead_by": 0, "behind_by": 0, "files": []}
        if api_path == "issues/138" and method == "GET":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178" and method == "GET":
            return {
                "number": 178,
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {
                    "sha": _PR_HEAD,
                    "ref": f"agent/{_CHANGE}",
                    "repo": {"full_name": _REPOSITORY},
                },
                "base": {
                    "ref": "main",
                    "sha": "f" * 40,
                    "repo": {"full_name": _REPOSITORY},
                },
            }
        if api_path == "pulls/178/files?per_page=100" and method == "GET":
            return [{"filename": path}]
        if api_path.startswith(f"contents/{path}?") and method == "GET":
            ref = api_path.rsplit("ref=", 1)[-1]
            if ref == _PR_HEAD:
                return {"sha": expected_sha}
            if ref == revision:
                return {"sha": blob_sha}
            raise AssertionError(f"unexpected manifest ref: {ref}")
        if api_path.startswith(f"contents/{default_only_path}?") and method == "GET":
            return {"sha": "f" * 40}
        if api_path == f"git/commits/{_PR_HEAD}" and method == "GET":
            return {"sha": _PR_HEAD, "tree": {"sha": "e" * 40}, "parents": []}
        if api_path == "git/trees" and method == "POST":
            return {"sha": tree_sha}
        if api_path == f"git/trees/{tree_sha}?recursive=1" and method == "GET":
            return {
                "sha": tree_sha,
                "truncated": False,
                "tree": [{"path": path, "type": "blob", "sha": blob_sha}],
            }
        if api_path == f"git/ref/heads/agent/{_CHANGE}" and method == "GET":
            return {"object": {"sha": _PR_HEAD}}
        if api_path == "git/commits" and method == "POST":
            commit_payloads.append(payload)
            return {"sha": revision}
        if api_path == f"git/commits/{revision}" and method == "GET":
            return {
                "sha": revision,
                "message": "Correct #138 N-1 ordering",
                "tree": {"sha": tree_sha},
                "parents": [{"sha": _PR_HEAD}, {"sha": _REVISION}],
            }
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    with pytest.raises(CarrierRequired) as raised:
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=_REVISION,
        )

    carrier_plan = raised.value.plan
    assert carrier_plan.expected["ref_sha"] == _PR_HEAD
    assert carrier_plan.requested["expected_head_sha"] == _PR_HEAD
    assert carrier_plan.requested["force"] is False
    assert carrier_plan.requested["commit_parents"] == [_PR_HEAD, _REVISION]
    assert len(commit_payloads) == 1
    assert commit_payloads[0] == {
        "message": "Correct #138 N-1 ordering",
        "tree": tree_sha,
        "parents": [_PR_HEAD, _REVISION],
    }


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    (
        (None, None),
        ("duplicate-pr", "historical PR identity is ambiguous"),
        ("overlap", "overlaps default-branch changes"),
        ("non-ancestor", "ancestry evidence is incomplete"),
        ("changed-content", "expected content SHA is stale"),
        ("rename-overlap", "overlaps default-branch changes"),
    ),
)
def test_constructor_accepted_322_work_product_recovers_safe_historical_pr_base(
    monkeypatch: pytest.MonkeyPatch,
    failure: str | None,
    expected_error: str | None,
) -> None:
    """Use #322's accepted base/head identities as a production-shaped regression."""

    source = WorkerRequest(322, "lead", "resolve-question")
    change = "restore-no-work-idle-discovery"
    historical_base = "2e00e236f24ba41302c9ba18c685acdf4cebe4ed"
    authorization_revision = "d019fdc604e8a7fa40e2f3e6436a12b076658057"
    carrier_head = "adf0b293fe0d263281e02b79b5dde63f0b2f93e4"
    branch = f"agent/{change}"
    tree_sha = "c" * 40
    revision = "d" * 40
    default_only_path = "src/investment_strategy/scheduled_agent_effects.py"
    manifest_values = (
        (
            f"openspec/changes/{change}/proposal.md",
            "bdeffd94ff01c7f3e2fd4e8e12c3b535b9df6932",
            "6003d898fae7c40c59d08e3023ed131baf41b383",
        ),
        (
            f"openspec/changes/{change}/design.md",
            "8096b24682c77d37e177e68e3460712af7de3325",
            "05cfb1579bb4a7c6480f180e9a7e025fdb5fde27",
        ),
        (
            f"openspec/changes/{change}/tasks.md",
            "4e428b3ead7ef6aa0de6cabfaef4885932a28d22",
            "331dc671ea6fa05c8fb2d40cc3f6dc65a31a6f0a",
        ),
        (
            f"openspec/changes/{change}/specs/scheduled-agent-workflow/spec.md",
            "d1861dd5b6a190f821fdf99ec7bb2d36fe5db208",
            "a8ec4b39e5287651ad58cf2b2e0e1a31113cdf06",
        ),
    )
    paths = {path for path, _blob, _expected in manifest_values}
    pr = {
        "number": 324,
        "state": "open",
        "merged": False,
        "draft": False,
        "title": f"OpenSpec: {change}",
        "body": f"Formalize OpenSpec change `{change}`.\n\nRefs #322",
        "head": {
            "ref": branch,
            "sha": carrier_head,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": historical_base,
            "repo": {"full_name": _REPOSITORY},
        },
    }
    manifest = resource.WorkProductManifest(
        branch=branch,
        base_sha=authorization_revision,
        message="Resolve exact-head OpenSpec findings for #322",
        files=tuple(
            resource.WorkProductFile(path, blob, expected)
            for path, blob, expected in manifest_values
        ),
    )
    plan = resource.WorkProductPlan(
        True,
        source=source,
        pr_number=324,
        expected_change=change,
        manifest=manifest,
    )
    commit_payloads: list[dict[str, object] | None] = []

    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_args: source)
    monkeypatch.setattr(resource, "_open_pr_payload", lambda **_kwargs: pr)
    monkeypatch.setattr(
        resource,
        "_open_prs_for_branch",
        lambda *_args, **_kwargs: (pr, pr) if failure == "duplicate-pr" else (pr,),
    )

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        del allow_not_found
        if api_path == "" and method == "GET":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main" and method == "GET":
            return {"object": {"sha": authorization_revision}}
        if api_path == f"git/ref/heads/{branch}" and method == "GET":
            return {"object": {"sha": carrier_head}}
        if api_path == f"compare/{historical_base}...{authorization_revision}" and method == "GET":
            return {
                "status": "diverged" if failure == "non-ancestor" else "ahead",
                "ahead_by": 0 if failure == "non-ancestor" else 25,
                "behind_by": 1 if failure == "non-ancestor" else 0,
                "base_commit": {"sha": historical_base},
                "files": (
                    [{"filename": f"openspec/changes/{change}/proposal.md", "status": "modified"}]
                    if failure == "overlap"
                    else [
                        {
                            "filename": "src/investment_strategy/renamed_validation_resource.py",
                            "previous_filename": default_only_path,
                            "status": "renamed",
                        }
                        if failure == "rename-overlap"
                        else {"filename": default_only_path, "status": "modified"}
                    ]
                ),
            }
        if api_path == f"compare/{historical_base}...{carrier_head}" and method == "GET":
            return {
                "status": "ahead",
                "ahead_by": 3,
                "behind_by": 0,
                "base_commit": {"sha": historical_base},
                "files": (
                    [
                        {"filename": default_only_path, "status": "modified"},
                        *({"filename": path, "status": "added"} for path in sorted(paths)),
                    ]
                    if failure in {"overlap", "rename-overlap"}
                    else [{"filename": path, "status": "added"} for path in sorted(paths)]
                ),
            }
        if api_path == f"compare/{authorization_revision}...{carrier_head}" and method == "GET":
            return {
                "status": "diverged",
                "ahead_by": 3,
                "behind_by": 25,
                "merge_base_commit": {"sha": historical_base},
            }
        if api_path == f"git/commits/{carrier_head}" and method == "GET":
            return {
                "sha": carrier_head,
                "tree": {"sha": "e" * 40},
                "parents": [{"sha": historical_base}],
            }
        if api_path == "git/trees" and method == "POST":
            return {"sha": tree_sha}
        if api_path == f"git/trees/{tree_sha}?recursive=1" and method == "GET":
            return {
                "sha": tree_sha,
                "truncated": False,
                "tree": [
                    {"path": path, "type": "blob", "sha": blob}
                    for path, blob, _expected in manifest_values
                ],
            }
        if api_path == "git/commits" and method == "POST":
            commit_payloads.append(payload)
            return {"sha": revision}
        if api_path == f"git/commits/{revision}" and method == "GET":
            return {
                "sha": revision,
                "message": manifest.message,
                "tree": {"sha": tree_sha},
                "parents": [{"sha": carrier_head}, {"sha": authorization_revision}],
            }
        if api_path.startswith("contents/") and method == "GET":
            path = api_path.split("?", 1)[0].removeprefix("contents/")
            ref = api_path.rsplit("ref=", 1)[-1]
            by_path = {path: (blob, expected) for path, blob, expected in manifest_values}
            if path not in by_path:
                return None
            blob, expected = by_path[path]
            if ref == authorization_revision:
                return None
            if ref == carrier_head and failure == "changed-content":
                return {"sha": "f" * 40}
            return {"sha": expected if ref == carrier_head else blob if ref == revision else None}
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    monkeypatch.setattr(
        resource,
        "_reconciliation_tree_elements",
        lambda *_args, **_kwargs: [
            {"path": path, "mode": "100644", "type": "blob", "sha": blob}
            for path, blob, _expected in manifest_values
        ],
    )

    if expected_error is not None:
        with pytest.raises(RuntimeError, match=expected_error):
            resource._construct_work_product(
                plan,
                repository=_REPOSITORY,
                token=_FIXTURE_VALUE,
                default_branch="main",
                authorization_revision=authorization_revision,
            )
        assert commit_payloads == []
        return

    with pytest.raises(CarrierRequired) as raised:
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=authorization_revision,
        )

    assert raised.value.plan.operation == "pull-request-head-update"
    assert raised.value.plan.requested["commit_parents"] == [
        carrier_head,
        authorization_revision,
    ]
    assert commit_payloads == [
        {
            "message": manifest.message,
            "tree": tree_sha,
            "parents": [carrier_head, authorization_revision],
        }
    ]


def test_replayed_reconciled_work_product_returns_current_target_without_new_commit(
    proof_git: _ProofGitRepository,
) -> None:
    accepted = _accepted_git_carrier(proof_git)
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint advance"}, "Advance", (proof_git.main,)
    )
    target = _apply_public_work_product(proof_git)
    assert target.revision == accepted
    assert _apply_public_work_product(proof_git) == target
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


def test_replayed_accepted_manifest_is_idempotent_on_current_reconciled_pr_head(
    proof_git: _ProofGitRepository,
) -> None:
    accepted = _accepted_git_carrier(proof_git)
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint advance"}, "Advance", (proof_git.main,)
    )
    target = _apply_public_work_product(proof_git)
    assert target.revision == accepted
    assert _apply_public_work_product(proof_git) == target
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


def test_constructor_work_product_rejects_stale_current_file_before_git_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    path = f"openspec/changes/{_CHANGE}/design.md"
    plan = _work_product_plan(
        source=source,
        path=path,
        blob_sha="b" * 40,
        expected_sha="a" * 40,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_: source)

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        **_kwargs: object,
    ) -> object:
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        if api_path == f"git/ref/heads/agent/{_CHANGE}":
            return {"object": {"sha": _PR_HEAD}}
        if api_path == f"compare/{_REVISION}...{_PR_HEAD}":
            return {"status": "ahead", "ahead_by": 1, "behind_by": 0}
        if api_path == "issues/138":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178":
            return {
                "number": 178,
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {
                    "sha": _PR_HEAD,
                    "ref": f"agent/{_CHANGE}",
                    "repo": {"full_name": _REPOSITORY},
                },
                "base": {
                    "ref": "main",
                    "sha": _REVISION,
                    "repo": {"full_name": _REPOSITORY},
                },
            }
        if api_path == "pulls/178/files?per_page=100":
            return [{"filename": path}]
        if api_path.startswith(f"contents/{path}?"):
            return {"sha": "f" * 40}
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    with pytest.raises(RuntimeError, match="expected content SHA is stale"):
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=_REVISION,
        )


def test_application_workflow_has_one_effect_ingress_and_no_legacy_families() -> None:
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")
    source = Path("src/investment_strategy/scheduled_agent_validation_resource.py").read_text(
        encoding="utf-8"
    )
    assert workflow.count("startsWith(github.event.comment.body, 'EFFECT_REQUEST')") == 1
    for forbidden in (
        "VALIDATION_RESOURCE_REQUEST",
        "WORK_PRODUCT_REQUEST",
        "FORMALIZE_CHANGE_REQUEST",
        "Dispatch-Request-Comment-ID",
        "Dispatch-Run-ID",
    ):
        assert forbidden not in workflow
        assert forbidden not in source


def test_task_checkpoint_accepts_fresh_observation_of_previously_durable_slice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_path = f"openspec/changes/{_CHANGE}/tasks.md"
    current = (
        "## Slice 1 — first\n"
        "- [x] 1.1 first task\n"
        "- [x] 1.2 second task\n"
        "## Slice 2 — later\n"
        "- [ ] 2.1 later task\n"
    )
    task_file = resource.WorkProductFile(task_path, "a" * 40, "a" * 40)

    monkeypatch.setattr(resource, "_content_sha_at", lambda *_args, **_kwargs: "a" * 40)
    monkeypatch.setattr(resource, "_content_text_at", lambda *_args, **_kwargs: current)
    monkeypatch.setattr(resource, "_blob_text", lambda *_args, **_kwargs: current)

    assert resource.task_checkpoint_is_exact(
        _REPOSITORY,
        _FIXTURE_VALUE,
        expected_change=_CHANGE,
        base_sha=_REVISION,
        file=task_file,
        completed_task_ids=("1.1", "1.2"),
    )
    assert not resource.task_checkpoint_is_exact(
        _REPOSITORY,
        _FIXTURE_VALUE,
        expected_change=_CHANGE,
        base_sha=_REVISION,
        file=task_file,
        completed_task_ids=("2.1",),
    )


_CONTINUATION_CHANGE = "qualify-active-formal-consequences"
_CONTINUATION_BRANCH = f"agent/{_CONTINUATION_CHANGE}-continuation-232"
_CONTINUATION_PR_BODY = (
    "Continue OpenSpec change " + _CONTINUATION_CHANGE + " after the merged carrier.\n\nRefs #229"
)


def _open_continuation_with_files(
    monkeypatch: pytest.MonkeyPatch,
    files: list[dict[str, str]],
    *,
    carrier_decision: ImplementationCarrierQualification | None = None,
    allow_reconciliation: bool = False,
) -> Mapping[str, object]:
    source = WorkerRequest(229, "executor", "implement-change")

    monkeypatch.setattr(resource, "_current_default_branch", lambda *_args: "main")

    def fake_github_json(_repository: str, _token: str, api_path: str) -> object:
        if api_path == "issues/229":
            return {"state": "open", "body": f"Change: {_CONTINUATION_CHANGE}\n"}
        if api_path == "pulls/236":
            return {
                "number": 236,
                "state": "open",
                "merged": False,
                "body": _CONTINUATION_PR_BODY,
                "head": {
                    "ref": _CONTINUATION_BRANCH,
                    "sha": "b" * 40,
                    "repo": {"full_name": _REPOSITORY},
                },
                "base": {
                    "ref": "main",
                    "sha": "a" * 40,
                    "repo": {"full_name": _REPOSITORY},
                },
            }
        if api_path == "pulls/236/files?per_page=100":
            return files
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    if carrier_decision is None:
        carrier_decision = ImplementationCarrierQualification(
            disposition="QUALIFIED",
            reason="fixture-qualified-continuation",
            repository=_REPOSITORY,
            issue_number=source.issue_number,
            change=_CONTINUATION_CHANGE,
            action=source.action,
            pr_number=236,
            branch=_CONTINUATION_BRANCH,
            head_sha="b" * 40,
            default_branch="main",
            default_revision="a" * 40,
            historical_pr_number=232,
        )
    monkeypatch.setattr(
        resource,
        "_implementation_carrier_decision",
        lambda *_args, **_kwargs: carrier_decision,
    )
    return resource._open_pr_payload(
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        pr_number=236,
        source=source,
        expected_change=_CONTINUATION_CHANGE,
        default_branch="main",
        expected_branch=_CONTINUATION_BRANCH,
        allow_reconciliation=allow_reconciliation,
    )


def test_code_only_deterministic_continuation_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = [
        {"filename": "src/investment_strategy/scheduled_agent_formal_qualification.py"},
        {"filename": "tests/test_scheduled_agent_formal_qualification.py"},
    ]
    payload = _open_continuation_with_files(monkeypatch, files)
    assert payload["number"] == 236


def test_deterministic_continuation_rejects_competing_active_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = [
        {"filename": "src/investment_strategy/scheduled_agent_formal_qualification.py"},
        {"filename": "openspec/changes/other-active-change/proposal.md"},
    ]
    with pytest.raises(
        RuntimeError,
        match="continuation carrier is not qualified",
    ):
        _open_continuation_with_files(
            monkeypatch,
            files,
            carrier_decision=ImplementationCarrierQualification(
                disposition="INDETERMINATE",
                reason="carrier-competing-active-change",
                repository=_REPOSITORY,
                issue_number=229,
                change=_CONTINUATION_CHANGE,
                action="implement-change",
                pr_number=236,
                branch=_CONTINUATION_BRANCH,
                head_sha="b" * 40,
                default_branch="main",
                default_revision="a" * 40,
                historical_pr_number=232,
            ),
        )


def test_validation_requires_qualified_continuation_unless_reconciling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = ImplementationCarrierQualification(
        disposition="RECONCILIATION_REQUIRED",
        reason="carrier-pr-base-is-stale",
        repository=_REPOSITORY,
        issue_number=229,
        change=_CONTINUATION_CHANGE,
        action="implement-change",
        pr_number=236,
        branch=_CONTINUATION_BRANCH,
        head_sha="b" * 40,
        default_branch="main",
        default_revision="a" * 40,
        historical_pr_number=232,
    )
    files = [
        {"filename": "src/investment_strategy/scheduled_agent_formal_qualification.py"},
    ]
    with pytest.raises(RuntimeError, match="continuation carrier is not qualified"):
        _open_continuation_with_files(
            monkeypatch,
            files,
            carrier_decision=decision,
        )
    payload = _open_continuation_with_files(
        monkeypatch,
        files,
        carrier_decision=decision,
        allow_reconciliation=True,
    )
    assert payload["number"] == 236


def test_apply_work_product_reuses_current_head_without_commit_when_ancestry_diverged(
    proof_git: _ProofGitRepository,
) -> None:
    accepted = _accepted_git_carrier(proof_git)
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint advance"}, "Advance", (proof_git.main,)
    )
    target = _apply_public_work_product(proof_git)
    assert target.revision == accepted
    assert _apply_public_work_product(proof_git) == target
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


@pytest.mark.parametrize(
    "files",
    [
        [{"filename": "src/file.py"}],
        [{"filename": "src/file.py", "status": "rewritten"}],
        [
            {"filename": "src/file.py", "status": "modified"},
            {"filename": "src/file.py", "status": "modified"},
        ],
    ],
    ids=("missing-status", "unknown-status", "duplicate-filename"),
)
def test_comparison_file_paths_reject_malformed_or_duplicate_entries(
    monkeypatch: pytest.MonkeyPatch,
    files: list[dict[str, str]],
) -> None:
    monkeypatch.setattr(
        resource,
        "_github_json",
        lambda *_args, **_kwargs: {"files": files},
    )

    with pytest.raises(RuntimeError, match="comparison is malformed"):
        resource._comparison_file_paths(
            _REPOSITORY,
            _FIXTURE_VALUE,
            base_sha=_REVISION,
            revision=_PR_HEAD,
        )


def test_live_322_accepted_manifest_on_existing_pr_head_recovers_after_interruption(
    proof_git: _ProofGitRepository,
) -> None:
    accepted = _accepted_git_carrier(proof_git)
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint advance"}, "Advance", (proof_git.main,)
    )
    target = _apply_public_work_product(proof_git)
    assert target.revision == accepted
    assert _apply_public_work_product(proof_git) == target
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


def test_live_322_merged_carrier_is_reconciled_without_replacement(
    proof_git: _ProofGitRepository,
) -> None:
    test_canonical_git_proof_survives_disjoint_advance_reconciliation_and_merge(proof_git)
    target = _apply_public_work_product(proof_git)
    assert target.revision == proof_git.main
    assert _apply_public_work_product(proof_git) == target
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


def test_merged_carrier_recovers_exact_manifest_from_same_change_successor(
    proof_git: _ProofGitRepository,
) -> None:
    test_canonical_replacement_has_its_own_target_and_legal_descendants(proof_git, False)
    head = cast(dict[str, object], proof_git.prs[1]["head"])["sha"]
    merge = proof_git.commit(
        {proof_git.path: "replacement correction"},
        "Merge successor",
        (proof_git.main, cast(str, head)),
    )
    proof_git.main = merge
    proof_git.prs[1].update(
        state="closed", merged=True, merged_at="2026-10-03T00:00:00Z", merge_commit_sha=merge
    )
    target = _apply_public_work_product(proof_git)
    assert target.revision == merge
    assert target.pr_number == 353
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


def test_live_322_manifest_recovers_after_disjoint_default_advance(
    proof_git: _ProofGitRepository,
) -> None:
    accepted = _accepted_git_carrier(proof_git)
    proof_git.main = proof_git.commit(
        {"README.md": "disjoint advance"}, "Advance", (proof_git.main,)
    )
    target = _apply_public_work_product(proof_git)
    assert target.revision == accepted
    assert _apply_public_work_product(proof_git) == target
    assert _postcondition_git(proof_git, target=None)
    assert proof_git.mutations == []


@pytest.mark.parametrize(
    ("status", "previous_filename"),
    ((None, None), ("copied", None), ("renamed", "src/unrelated.py")),
    ids=("missing-status", "unknown-status", "rename-into-manifest"),
)
def test_revision_matches_manifest_rejects_incomplete_or_renamed_paths(
    monkeypatch: pytest.MonkeyPatch,
    status: str | None,
    previous_filename: str | None,
) -> None:
    base = "a" * 40
    revision = "b" * 40
    path = f"openspec/changes/{_CHANGE}/proposal.md"
    blob = "c" * 40
    entry = {"filename": path}
    if status is not None:
        entry["status"] = status
    if previous_filename is not None:
        entry["previous_filename"] = previous_filename
    manifest = resource.WorkProductManifest(
        branch=f"agent/{_CHANGE}",
        base_sha=base,
        message="Verify exact manifest paths",
        files=(resource.WorkProductFile(path, blob, "d" * 40),),
    )

    def fake_github_json(
        _repository: str,
        _token: str,
        api_path: str,
        **_kwargs: object,
    ) -> object:
        if api_path == f"compare/{base}...{revision}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "commits": [{"sha": revision}],
                "files": [entry],
            }
        if api_path == f"git/commits/{revision}":
            return {
                "sha": revision,
                "message": manifest.message,
                "parents": [{"sha": base}],
            }
        raise AssertionError(api_path)

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    monkeypatch.setattr(resource, "_content_sha_at", lambda *_args, **_kwargs: blob)

    assert not resource._revision_matches_manifest(
        _REPOSITORY,
        _FIXTURE_VALUE,
        base_sha=base,
        revision=revision,
        manifest=manifest,
    )


def test_constructor_lead_materialization_bases_next_continuation_on_merged_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(322, "lead", "resolve-question")
    change = "restore-no-work-idle-discovery"
    historical_branch = f"agent/{change}-continuation-324"
    next_branch = f"agent/{change}-continuation-347"
    base = "a" * 40
    historical_head = "b" * 40
    merge_commit = "c" * 40
    path = f"openspec/changes/{change}/proposal.md"
    decision = resource.ImplementationCarrierQualification(
        disposition="HISTORICAL_MERGED",
        reason="merged-continuation-carrier-qualified",
        repository=_REPOSITORY,
        issue_number=322,
        change=change,
        action=source.action,
        pr_number=347,
        branch=historical_branch,
        head_sha=historical_head,
        default_branch="main",
        default_revision=base,
        historical_pr_number=324,
    )
    plan = resource.WorkProductPlan(
        True,
        source=source,
        pr_number=347,
        expected_change=change,
        manifest=resource.WorkProductManifest(
            branch=historical_branch,
            base_sha=base,
            message="Correct #322 semantics",
            files=(resource.WorkProductFile(path, "d" * 40, "e" * 40),),
        ),
    )
    merged_pr = {
        "number": 347,
        "state": "closed",
        "merged": True,
        "merged_at": "2026-09-29T00:00:00Z",
        "merge_commit_sha": merge_commit,
        "body": "Continue the Change.\n\nRefs #322",
        "head": {
            "ref": historical_branch,
            "sha": historical_head,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": base,
            "repo": {"full_name": _REPOSITORY},
        },
    }

    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_args: source)
    monkeypatch.setattr(
        resource,
        "_ref_head_sha",
        lambda _repo, _token, ref, **_kwargs: base if ref == "main" else historical_head,
    )
    monkeypatch.setattr(resource, "_change_carrier_decision", lambda *_args, **_kwargs: decision)
    monkeypatch.setattr(resource, "_open_pr_payload", lambda **_kwargs: merged_pr)
    monkeypatch.setattr(resource, "_default_branch_is_ancestor", lambda *_args, **_kwargs: True)

    class _ReachedNextContinuation(RuntimeError):
        pass

    def capture_open_prs(
        _repository: str,
        _token: str,
        *,
        branch: str,
        default_branch: str,
    ) -> tuple[object, ...]:
        assert branch == next_branch
        assert default_branch == "main"
        raise _ReachedNextContinuation

    monkeypatch.setattr(resource, "_open_prs_for_branch", capture_open_prs)

    with pytest.raises(_ReachedNextContinuation):
        resource._construct_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=base,
        )


def test_review_openspec_consumes_shared_qualified_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(322, "reviewer", "review-openspec")
    change = "restore-no-work-idle-discovery"
    branch = f"agent/{change}-continuation-347"
    head = "b" * 40
    decision = resource.ImplementationCarrierQualification(
        disposition="QUALIFIED",
        reason="continuation-carrier-qualified",
        repository=_REPOSITORY,
        issue_number=322,
        change=change,
        action=source.action,
        pr_number=352,
        branch=branch,
        head_sha=head,
        default_branch="main",
        default_revision="a" * 40,
        historical_pr_number=347,
    )
    plan = resource.ValidationResourcePlan(
        True,
        source=source,
        pr_number=352,
        expected_change=change,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_args: source)
    monkeypatch.setattr(resource, "_change_carrier_decision", lambda *_args, **_kwargs: decision)

    assert resource.resolve_validation_resource_target(
        plan,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        default_branch="main",
    ) == resource.ValidationResourceTarget(
        repository=_REPOSITORY,
        revision=head,
        correlation="effect-request-322",
        pr_number=352,
        change=change,
        branch=branch,
    )


def _apply_public_work_product(fixture: _ProofGitRepository) -> resource.ValidationResourceTarget:
    payload = fixture.payload()
    files = tuple(
        resource.WorkProductFile(
            cast(str, file["path"]),
            cast(str, file["blob_sha"]),
            cast(str | None, file["expected_sha"]),
        )
        for file in cast(list[dict[str, object]], payload["files"])
    )
    plan = resource.WorkProductPlan(
        True,
        fixture.source,
        324,
        _CHANGE,
        resource.WorkProductManifest(fixture.branch, fixture.base, fixture.message, files),
    )
    # The fixture's immutable Change, not this module's unrelated fixture Change.
    plan = resource.WorkProductPlan(
        True, fixture.source, 324, cast(str, payload["change"]), plan.manifest
    )
    return resource.apply_work_product(
        plan,
        repository=fixture.repository,
        token=_FIXTURE_VALUE,
        default_branch="main",
        authorization_revision=fixture.main,
        accepted_authorization_revision=fixture.authorization,
    )
