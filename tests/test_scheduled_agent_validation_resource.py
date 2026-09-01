"""Regression coverage for the application-owned exact-revision validation resource."""

from __future__ import annotations

from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_validation_resource as resource
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "013510b12c5d3cde869308a319a1e2fb12cdfa60"
_PR_HEAD = "05e1e84523651c6a9bc4ebbe4b275b12dae74dbf"
_CHANGE = "simplify-scheduled-agent-control-plane"


def _app(slug: str) -> dict[str, object]:
    return {"slug": slug}


def _comment(comment_id: int, body: str, *, actions: bool = False) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": "github-actions[bot]" if actions else "royhsu-work"},
        "performed_via_github_app": _app("github-actions" if actions else "chatgpt-codex-connector"),
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


def _event() -> dict[str, object]:
    return {
        "action": "created",
        "issue": {"number": 142},
        "comment": _comment(102, _resource_body()),
    }


def _comments(*, revision: str = _REVISION) -> list[list[dict[str, object]]]:
    return [
        [
            _comment(100, _dispatch_request()),
            _comment(101, _dispatch_decision(revision=revision), actions=True),
            _comment(102, _resource_body()),
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
        assert token == "fixture-token"
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
        token="fixture-token",
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
            token="fixture-token",
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
            token="fixture-token",
            default_branch="main",
            workflow_text=(
                "| `Lead / resolve-question` | material semantic correction ready | "
                "`Reviewer / review-openspec` |\n"
            ),
        )


def test_application_workflow_runs_validation_inline_without_secondary_dispatch() -> None:
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")

    assert "VALIDATION_RESOURCE_REQUEST" in workflow
    assert "scheduled_agent_validation_resource" in workflow
    assert "Checkout exact validation target" in workflow
    assert "validator_checkout_head" in workflow
    assert "openspec_compatibility.py" in workflow
    assert "openspec validate --all --strict --json --no-interactive" in workflow
    assert "actions/workflows/openspec-validate.yml/dispatches" not in workflow
