"""Tests for application-owned exact validation/work-product helpers."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from urllib.request import Request

import pytest

import investment_strategy.scheduled_agent_validation_resource as resource
from investment_strategy.scheduled_agent_carrier import CarrierRequired
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "013510b12c5d3cde869308a319a1e2fb12cdfa60"
_PR_HEAD = "05e1e84523651c6a9bc4ebbe4b275b12dae74dbf"
_CHANGE = "simplify-scheduled-agent-control-plane"
_FIXTURE_VALUE = "fixture-value"


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
    files: list[dict[str, object]],
) -> object:
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
    return resource._open_pr_payload(
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        pr_number=236,
        source=source,
        expected_change=_CONTINUATION_CHANGE,
        default_branch="main",
        expected_branch=_CONTINUATION_BRANCH,
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
        match="continuation contains competing active Change",
    ):
        _open_continuation_with_files(monkeypatch, files)
