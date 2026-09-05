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
