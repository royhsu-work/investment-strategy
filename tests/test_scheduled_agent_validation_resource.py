"""Regression coverage for the application-owned exact-revision validation resource."""

from __future__ import annotations

import base64
import json
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

import investment_strategy.scheduled_agent_validation_resource as resource
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "013510b12c5d3cde869308a319a1e2fb12cdfa60"
_PR_HEAD = "05e1e84523651c6a9bc4ebbe4b275b12dae74dbf"
_CHANGE = "simplify-scheduled-agent-control-plane"
_FIXTURE_VALUE = "fixture-value"


def _app(slug: str) -> dict[str, object]:
    return {"slug": slug}


def _comment(comment_id: int, body: str, *, actions: bool = False) -> dict[str, object]:
    app_slug = "github-actions" if actions else "chatgpt-codex-connector"
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": "github-actions[bot]" if actions else "royhsu-work"},
        "performed_via_github_app": _app(app_slug),
    }


def _resource_body() -> str:
    return "\n".join(
        (
            "VALIDATION_RESOURCE_REQUEST",
            "Dispatch-Request-Comment-ID: 100",
            "Dispatch-Decision-Comment-ID: 101",
            "PR: 178",
            f"Expected-Change: {_CHANGE}",
        )
    )


def _dispatch_request() -> str:
    return "DISPATCH_REQUEST\nRequested-At: 2026-09-01T17:41:00+08:00"


def _dispatch_decision(*, revision: str = _REVISION) -> str:
    return "\n".join(
        (
            "DISPATCH_DECISION",
            "Request-Comment-ID: 100",
            f"Default-Branch-Revision: {revision}",
            "Disposition: AUTHORIZE",
            "Issue: 138",
            "Role: lead",
            "Action: resolve-question",
        )
    )


def _event(body: str | None = None, *, comment_id: int = 102) -> dict[str, object]:
    request_body = body or _resource_body()
    return {
        "action": "created",
        "issue": {"number": 142},
        "comment": _comment(comment_id, request_body),
    }


def _comments(
    *,
    body: str | None = None,
    comment_id: int = 102,
    revision: str = _REVISION,
    extras: list[dict[str, object]] | None = None,
) -> list[list[dict[str, object]]]:
    request_body = body or _resource_body()
    return [
        [
            _comment(100, _dispatch_request()),
            _comment(101, _dispatch_decision(revision=revision), actions=True),
            *(extras or []),
            _comment(comment_id, request_body),
        ]
    ]


def test_resource_request_contains_no_caller_revision() -> None:
    parsed = resource.parse_validation_resource_request(_resource_body())

    assert parsed is not None
    assert parsed.pr_number == 178
    assert parsed.expected_change == _CHANGE
    assert not hasattr(parsed, "revision")


def test_plan_resource_binds_exact_machine_dispatch() -> None:
    plan = resource.plan_validation_resource(
        event=_event(),
        comments_payload=_comments(),
        configured_issue_number=142,
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_validate
    assert plan.source == WorkerRequest(138, "lead", "resolve-question")
    assert plan.request_comment_id == 102
    assert plan.pr_number == 178
    assert plan.expected_change == _CHANGE


def test_plan_resource_rejects_stale_dispatch_revision() -> None:
    with pytest.raises(ValueError, match="dispatch revision is stale"):
        resource.plan_validation_resource(
            event=_event(),
            comments_payload=_comments(revision="0" * 40),
            configured_issue_number=142,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_resource_derives_already_current_pr_head_after_fresh_reauthorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    plan = resource.ValidationResourcePlan(
        True,
        source=source,
        request_comment_id=102,
        pr_number=178,
        expected_change=_CHANGE,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda repository, token: source)

    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        if api_path == "issues/138":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178":
            return {
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {
                    "sha": _PR_HEAD,
                    "ref": f"agent/{_CHANGE}",
                    "repo": {"full_name": _REPOSITORY},
                },
                "base": {"ref": "main", "repo": {"full_name": _REPOSITORY}},
            }
        if api_path == "pulls/178/files?per_page=100":
            return [
                {"filename": f"openspec/changes/{_CHANGE}/proposal.md"},
                {"filename": f"openspec/changes/{_CHANGE}/design.md"},
                {"filename": f"openspec/changes/{_CHANGE}/tasks.md"},
            ]
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)
    workflow = (
        "| `Lead / resolve-question` | material semantic correction ready | "
        "`Reviewer / review-openspec` |\n"
    )

    target = resource.resolve_validation_resource_target(
        plan,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        default_branch="main",
        workflow_text=workflow,
    )

    assert target.repository == _REPOSITORY
    assert target.revision == _PR_HEAD
    assert target.correlation == "validation-resource-request-102"
    assert target.pr_number == 178
    assert target.change == _CHANGE


def test_resource_rejects_source_without_review_openspec_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    plan = resource.ValidationResourcePlan(
        True,
        source=source,
        request_comment_id=102,
        pr_number=178,
        expected_change=_CHANGE,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda repository, token: source)

    with pytest.raises(RuntimeError, match="not required by this source topology"):
        resource.resolve_validation_resource_target(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            workflow_text=(
                "| `Executor / implement-change` | implementation READY | "
                "`Reviewer / review-implementation` |\n"
            ),
        )


def test_resource_rejects_pr_that_mixes_another_active_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    plan = resource.ValidationResourcePlan(
        True,
        source=source,
        request_comment_id=102,
        pr_number=178,
        expected_change=_CHANGE,
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda repository, token: source)

    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        del repository, token
        if api_path == "issues/138":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178":
            return {
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {"sha": _PR_HEAD, "repo": {"full_name": _REPOSITORY}},
                "base": {"ref": "main", "repo": {"full_name": _REPOSITORY}},
            }
        if api_path == "pulls/178/files?per_page=100":
            return [
                {"filename": f"openspec/changes/{_CHANGE}/proposal.md"},
                {"filename": "openspec/changes/unrelated-change/proposal.md"},
            ]
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)

    with pytest.raises(RuntimeError, match="uniquely represent the source Change"):
        resource.resolve_validation_resource_target(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            workflow_text=(
                "| `Lead / resolve-question` | material semantic correction ready | "
                "`Reviewer / review-openspec` |\n"
            ),
        )


def _work_product_body(
    *,
    base_sha: str = _PR_HEAD,
    expected_sha: str = "a" * 40,
    blob_sha: str = "b" * 40,
) -> str:
    manifest = {
        "branch": f"agent/{_CHANGE}",
        "base_sha": base_sha,
        "message": "Correct #138 N-1 ordering",
        "files": [
            {
                "path": f"openspec/changes/{_CHANGE}/design.md",
                "blob_sha": blob_sha,
                "expected_sha": expected_sha,
            }
        ],
    }
    encoded = base64.b64encode(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).decode()
    return "\n".join(
        (
            "WORK_PRODUCT_REQUEST",
            "Dispatch-Request-Comment-ID: 100",
            "Dispatch-Decision-Comment-ID: 101",
            "PR: 178",
            f"Expected-Change: {_CHANGE}",
            f"Manifest-B64: {encoded}",
        )
    )


def test_work_product_request_carries_only_blob_references() -> None:
    parsed = resource.parse_work_product_request(_work_product_body())

    assert parsed is not None
    assert parsed.manifest.base_sha == _PR_HEAD
    assert parsed.manifest.files[0].path.endswith("/design.md")
    assert parsed.manifest.files[0].blob_sha == "b" * 40
    assert not hasattr(parsed.manifest.files[0], "content")


def test_plan_work_product_binds_same_exact_dispatch_without_file_content() -> None:
    body = _work_product_body()
    plan = resource.plan_work_product_application(
        event=_event(body),
        comments_payload=_comments(body=body),
        configured_issue_number=142,
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source == WorkerRequest(138, "lead", "resolve-question")
    assert plan.pr_number == 178
    assert plan.manifest is not None
    assert plan.manifest.files[0].blob_sha == "b" * 40


def test_apply_work_product_builds_one_tree_and_one_commit_then_observes_exact_r(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    expected_sha = "a" * 40
    blob_sha = "b" * 40
    tree_sha = "c" * 40
    revision = "d" * 40
    path = f"openspec/changes/{_CHANGE}/design.md"
    plan = resource.WorkProductPlan(
        True,
        source=source,
        request_comment_id=102,
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
    monkeypatch.setattr(resource, "_current_authorized_request", lambda repository, token: source)
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
        if api_path == "issues/138" and method == "GET":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178" and method == "GET":
            return {
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {
                    "sha": head_sha,
                    "ref": f"agent/{_CHANGE}",
                    "repo": {"full_name": _REPOSITORY},
                },
                "base": {"ref": "main", "repo": {"full_name": _REPOSITORY}},
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
    workflow = (
        "| `Lead / resolve-question` | material semantic correction ready | "
        "`Reviewer / review-openspec` |\n"
    )

    target = resource.apply_work_product(
        plan,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        default_branch="main",
        workflow_text=workflow,
    )

    assert target.revision == revision
    assert target.correlation == "work-product-request-102"
    assert len(tree_payloads) == 1
    assert len(commit_payloads) == 1
    assert commit_payloads[0] == {
        "message": "Correct #138 N-1 ordering",
        "tree": tree_sha,
        "parents": [_PR_HEAD],
    }


def test_apply_work_product_rejects_unresolvable_blob_before_commit_or_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    expected_sha = "a" * 40
    blob_sha = "b" * 40
    path = f"openspec/changes/{_CHANGE}/design.md"
    plan = resource.WorkProductPlan(
        True,
        source=source,
        request_comment_id=102,
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
    monkeypatch.setattr(resource, "_current_authorized_request", lambda repository, token: source)

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        del repository, token, payload, allow_not_found
        if api_path == "issues/138" and method == "GET":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178" and method == "GET":
            return {
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {
                    "sha": _PR_HEAD,
                    "ref": f"agent/{_CHANGE}",
                    "repo": {"full_name": _REPOSITORY},
                },
                "base": {"ref": "main", "repo": {"full_name": _REPOSITORY}},
            }
        if api_path == "pulls/178/files?per_page=100" and method == "GET":
            return [{"filename": path}]
        if api_path.startswith(f"contents/{path}?") and method == "GET":
            return {"sha": expected_sha}
        if api_path == f"git/commits/{_PR_HEAD}" and method == "GET":
            return {"sha": _PR_HEAD, "tree": {"sha": "e" * 40}, "parents": []}
        if api_path == "git/trees" and method == "POST":
            raise HTTPError(
                "https://api.github.com/repos/example/repo/git/trees",
                422,
                "Validation Failed",
                Message(),
                None,
            )
        if api_path == "git/commits" and method == "POST":
            raise AssertionError("commit must not be created after tree resolution failure")
        if method == "PATCH":
            raise AssertionError("ref must not be updated after tree resolution failure")
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)

    with pytest.raises(RuntimeError, match="referenced blob is unavailable"):
        resource.apply_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            workflow_text=(
                "| `Lead / resolve-question` | material semantic correction ready | "
                "`Reviewer / review-openspec` |\n"
            ),
        )


def test_apply_work_product_rejects_stale_current_file_before_git_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    plan = resource.WorkProductPlan(
        True,
        source=source,
        request_comment_id=102,
        pr_number=178,
        expected_change=_CHANGE,
        manifest=resource.WorkProductManifest(
            branch=f"agent/{_CHANGE}",
            base_sha=_PR_HEAD,
            message="Correct #138 N-1 ordering",
            files=(
                resource.WorkProductFile(
                    path=f"openspec/changes/{_CHANGE}/design.md",
                    blob_sha="b" * 40,
                    expected_sha="a" * 40,
                ),
            ),
        ),
    )
    monkeypatch.setattr(resource, "_current_authorized_request", lambda repository, token: source)

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        del repository, token, payload, allow_not_found
        if api_path == "issues/138":
            return {"state": "open", "body": f"Change: {_CHANGE}\n"}
        if api_path == "pulls/178":
            return {
                "state": "open",
                "merged": False,
                "body": "Refs #138\n",
                "head": {
                    "sha": _PR_HEAD,
                    "ref": f"agent/{_CHANGE}",
                    "repo": {"full_name": _REPOSITORY},
                },
                "base": {"ref": "main", "repo": {"full_name": _REPOSITORY}},
            }
        if api_path == "pulls/178/files?per_page=100":
            return [{"filename": f"openspec/changes/{_CHANGE}/design.md"}]
        if api_path.startswith(f"contents/openspec/changes/{_CHANGE}/design.md?"):
            return {"sha": "f" * 40}
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)

    with pytest.raises(RuntimeError, match="expected content SHA is stale"):
        resource.apply_work_product(
            plan,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            default_branch="main",
            workflow_text=(
                "| `Lead / resolve-question` | material semantic correction ready | "
                "`Reviewer / review-openspec` |\n"
            ),
        )


def test_complete_cross_role_handoff_derives_body_from_applied_result_and_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    result_body = (
        "## ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: Lead / resolve-question\n"
        "Result: READY_FOR_OPENSPEC_REVIEW\n"
        f"Revision: {'d' * 40}\n"
    )
    raw_worker_result = json.dumps(
        {
            "issue_number": 138,
            "role": "lead",
            "action": "resolve-question",
            "result_content": "ready",
            "requested_effects": [
                {
                    "kind": "issue-comment",
                    "payload_json": json.dumps(
                        {"issue_number": 138, "body": result_body},
                        sort_keys=True,
                    ),
                },
                {
                    "kind": "routing-transition",
                    "payload_json": json.dumps(
                        {
                            "issue_number": 138,
                            "role": "reviewer",
                            "action": "review-openspec",
                        },
                        sort_keys=True,
                    ),
                },
            ],
        },
        sort_keys=True,
    )
    plan = resource.HandoffCompletionPlan(
        True,
        source=source,
        request_comment_id=104,
        effect_request_comment_id=103,
        result_comment_id=555,
        expected_change=_CHANGE,
        raw_worker_result=raw_worker_result,
    )
    posted_body: str | None = None

    def current_issue() -> dict[str, object]:
        return {
            "number": 138,
            "state": "open",
            "body": f"Change: {_CHANGE}\nCause-Ref: issuecomment-1\n",
            "created_at": "2026-08-22T17:18:32Z",
            "closed_at": None,
            "labels": [
                {"name": "agent:reviewer"},
                {"name": "action:review-openspec"},
            ],
        }

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        nonlocal posted_body
        del repository, token, allow_not_found
        if api_path == "issues/138" and method == "GET":
            return current_issue()
        if api_path == "issues/comments/555" and method == "GET":
            return _comment(555, result_body, actions=True)
        if api_path == "issues/138/comments?per_page=100&page=1" and method == "GET":
            return []
        if api_path == "issues/138/comments" and method == "POST":
            assert payload is not None
            body = payload.get("body")
            assert isinstance(body, str)
            posted_body = body
            return {"id": 777}
        if api_path == "issues/comments/777" and method == "GET":
            assert posted_body is not None
            return {"id": 777, "body": posted_body}
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(resource, "_github_json", fake_github_json)

    comment_id = resource.complete_cross_role_handoff(
        plan,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
    )

    assert comment_id == 777
    assert posted_body is not None
    assert "## HANDOFF" in posted_body
    assert "From: `Lead / resolve-question`" in posted_body
    assert "To: `Reviewer / review-openspec`" in posted_body
    assert "Trigger-Result-Comment-ID: 555" in posted_body


def test_application_workflow_runs_validation_inline_without_secondary_dispatch() -> None:
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")
    skill = Path("agents/skills/openspec-change/SKILL.md").read_text(encoding="utf-8")

    assert "VALIDATION_RESOURCE_REQUEST" in workflow
    assert "WORK_PRODUCT_REQUEST" in workflow
    assert "HANDOFF_COMPLETION_REQUEST" in workflow
    assert "scheduled_agent_validation_resource" in workflow
    assert "Checkout exact validation target" in workflow
    assert "validator_checkout_head" in workflow
    assert "openspec_compatibility.py" in workflow
    assert "openspec validate --all --strict --json --no-interactive" in workflow
    assert "actions/workflows/openspec-validate.yml/dispatches" not in workflow
    assert "unreferenced Git blobs only" in skill
    assert "MUST NOT create a Git tree or commit" in skill
