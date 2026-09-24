"""Tests for application-owned exact validation/work-product helpers."""

from __future__ import annotations

import base64
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from urllib.request import Request

import pytest

import investment_strategy.scheduled_agent_validation_resource as resource
from investment_strategy.scheduled_agent_application_carrier import (
    ImplementationCarrierQualification,
)
from investment_strategy.scheduled_agent_carrier import CarrierRequired
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "013510b12c5d3cde869308a319a1e2fb12cdfa60"
_PR_HEAD = "05e1e84523651c6a9bc4ebbe4b275b12dae74dbf"
_CHANGE = "simplify-scheduled-agent-control-plane"
_FIXTURE_VALUE = "fixture-value"


def test_reconciliation_file_comparison_includes_renamed_path_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_sha = "a" * 40
    revision = "b" * 40
    requested: list[str] = []

    def fake_github_json(_repository: str, _token: str, api_path: str) -> object:
        requested.append(api_path)
        return {
            "files": [
                {
                    "filename": "src/new_name.py",
                    "previous_filename": "src/old_name.py",
                    "status": "renamed",
                }
            ]
        }

    monkeypatch.setattr(resource, "_github_json", fake_github_json)

    paths = resource._comparison_file_paths(
        _REPOSITORY,
        _FIXTURE_VALUE,
        base_sha=base_sha,
        revision=revision,
    )

    assert requested == [f"compare/{base_sha}...{revision}"]
    assert paths == {"src/old_name.py", "src/new_name.py"}


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


def test_apply_work_product_rejects_non_monotonic_task_marker_before_tree(
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
        resource.apply_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            authorization_revision=_REVISION,
        )


def test_apply_work_product_reuses_continuation_carrier_decision(
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
        resource.apply_work_product(
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


def test_apply_work_product_builds_one_tree_and_one_commit_then_observes_exact_r(
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
        resource.apply_work_product(
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


def test_apply_work_product_builds_same_change_replacement_after_merged_carrier(
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
        if api_path == f"compare/{_REVISION}...{_REVISION}":
            return {"status": "identical", "ahead_by": 0, "behind_by": 0}
        if api_path.startswith("pulls?state=open"):
            assert replacement_branch.replace("/", "%2F") in api_path
            return []
        if api_path == f"git/ref/heads/{replacement_branch}":
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
        resource.apply_work_product(
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
            return {"files": [{"filename": default_only_path}]}
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


def test_apply_work_product_reconciles_diverged_default_branch_with_two_parents(
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
                "files": [{"filename": default_only_path}],
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
        resource.apply_work_product(
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


def test_replayed_reconciled_work_product_returns_current_target_without_new_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    blob_sha = "b" * 40
    reconciled_revision = "f" * 40
    path = f"openspec/changes/{_CHANGE}/design.md"
    plan = _work_product_plan(
        source=source,
        path=path,
        blob_sha=blob_sha,
        expected_sha="a" * 40,
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
        del method, payload, allow_not_found
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        if api_path == f"git/ref/heads/agent/{_CHANGE}":
            return {"object": {"sha": reconciled_revision}}
        if api_path == f"compare/{_REVISION}...{reconciled_revision}":
            return {"status": "ahead", "ahead_by": 2, "behind_by": 0}
        if api_path == f"compare/{_PR_HEAD}...{reconciled_revision}":
            return {
                "status": "ahead",
                "ahead_by": 2,
                "behind_by": 0,
                "files": [{"filename": path}],
                "commits": [{"sha": reconciled_revision}],
            }
        if api_path == f"compare/{_REVISION}...{_REVISION}":
            return {"status": "identical", "ahead_by": 0, "behind_by": 0}
        if api_path == "issues/138":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178":
            return {
                "number": 178,
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {
                    "sha": reconciled_revision,
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
            return {"sha": blob_sha}
        if api_path == f"git/commits/{reconciled_revision}":
            return {
                "sha": reconciled_revision,
                "message": "Correct #138 N-1 ordering",
                "tree": {"sha": "c" * 40},
                "parents": [{"sha": _PR_HEAD}, {"sha": _REVISION}],
            }
        raise AssertionError(f"unexpected GitHub call: {api_path}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    target = resource.apply_work_product(
        plan,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        default_branch="main",
        authorization_revision=_REVISION,
    )

    assert target.revision == reconciled_revision
    assert target.pr_number == 178
    assert commit_payloads == []


def test_work_product_rejects_stale_current_file_before_git_construction(
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
        resource.apply_work_product(
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(229, "executor", "implement-change")
    base_sha = "a" * 40
    merge_commit = "b" * 40
    historical_head = "c" * 40
    current_head = "d" * 40
    expected_sha = "e" * 40
    blob_sha = "f" * 40
    path = f"openspec/changes/{_CONTINUATION_CHANGE}/tasks.md"
    replacement_branch = _CONTINUATION_BRANCH
    message = "Stage 2: materialize verified qualification implementation; checkpoint pending"
    plan = resource.WorkProductPlan(
        True,
        source=source,
        pr_number=232,
        expected_change=_CONTINUATION_CHANGE,
        manifest=resource.WorkProductManifest(
            branch=f"agent/{_CONTINUATION_CHANGE}",
            base_sha=base_sha,
            message=message,
            files=(resource.WorkProductFile(path, blob_sha, expected_sha),),
        ),
    )
    historical_pr = {
        "number": 232,
        "state": "closed",
        "merged": True,
        "merged_at": "2026-09-10T00:00:00Z",
        "merge_commit_sha": merge_commit,
        "body": "Stage 1\n\nRefs #229\n",
        "head": {
            "ref": f"agent/{_CONTINUATION_CHANGE}",
            "sha": historical_head,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": base_sha,
            "repo": {"full_name": _REPOSITORY},
        },
    }
    replacement_pr = {
        "number": 236,
        "state": "open",
        "merged": False,
        "body": _CONTINUATION_PR_BODY,
        "head": {
            "ref": replacement_branch,
            "sha": current_head,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": base_sha,
            "repo": {"full_name": _REPOSITORY},
        },
    }
    tree_payloads: list[object] = []
    commit_payloads: list[object] = []

    monkeypatch.setattr(resource, "_current_authorized_request", lambda *_args: source)
    monkeypatch.setattr(
        resource,
        "_implementation_carrier_decision",
        lambda *_args, **_kwargs: ImplementationCarrierQualification(
            disposition="RECONCILIATION_REQUIRED",
            reason="fixture-continuation-reconciliation",
            repository=_REPOSITORY,
            issue_number=source.issue_number,
            change=_CONTINUATION_CHANGE,
            action=source.action,
            pr_number=236,
            branch=replacement_branch,
            head_sha=current_head,
            default_branch="main",
            default_revision=base_sha,
            historical_pr_number=232,
        ),
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
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main":
            return {"object": {"sha": base_sha}}
        if api_path == "issues/229":
            return {"state": "open", "body": f"Change: {_CONTINUATION_CHANGE}\n"}
        if api_path == "pulls/232":
            return historical_pr
        if api_path == "pulls/232/files?per_page=100":
            return [{"filename": f"openspec/changes/{_CONTINUATION_CHANGE}/design.md"}]
        if api_path == f"compare/{merge_commit}...{base_sha}":
            return {"status": "ahead", "ahead_by": 1, "behind_by": 0}
        if api_path.startswith("pulls?state=open"):
            return [replacement_pr]
        if api_path == "pulls/236":
            return replacement_pr
        if api_path == "pulls/236/files?per_page=100":
            return [{"filename": path}]
        if api_path == f"git/ref/heads/{replacement_branch}":
            return {"object": {"sha": current_head}}
        if api_path == f"compare/{base_sha}...{current_head}":
            return {
                "status": "diverged",
                "ahead_by": 2,
                "behind_by": 1,
                "files": [{"filename": path}],
                "commits": [{"sha": historical_head}, {"sha": current_head}],
            }
        if api_path == f"git/commits/{current_head}":
            return {
                "sha": current_head,
                "tree": {"sha": "1" * 40},
                "parents": [{"sha": historical_head}],
            }
        if api_path.startswith(f"contents/{path}?"):
            revision = api_path.rsplit("ref=", 1)[-1]
            return {"sha": expected_sha if revision == base_sha else blob_sha}
        if api_path == "git/trees" and method == "POST":
            tree_payloads.append(payload)
            return {"sha": "2" * 40}
        if api_path == "git/trees/" + "2" * 40 + "?recursive=1":
            return {
                "sha": "2" * 40,
                "truncated": False,
                "tree": [{"path": path, "type": "blob", "sha": blob_sha}],
            }
        if api_path == "git/commits" and method == "POST":
            commit_payloads.append(payload)
            return {"sha": "3" * 40}
        if api_path == "git/commits/" + "3" * 40:
            return {
                "sha": "3" * 40,
                "message": message,
                "tree": {"sha": "2" * 40},
                "parents": [{"sha": current_head}],
            }
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)

    target = resource.apply_work_product(
        plan,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        default_branch="main",
        authorization_revision=base_sha,
    )

    assert target.revision == current_head
    assert target.pr_number == 236
    assert target.change == _CONTINUATION_CHANGE
    assert tree_payloads == []
    assert commit_payloads == []
