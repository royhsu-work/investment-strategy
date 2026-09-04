"""Regression coverage for Scheduled Agent issue-comment application ingress."""

from __future__ import annotations

import base64
import json
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

import investment_strategy.scheduled_agent_application_bridge as bridge
from investment_strategy.scheduled_agent_application_bridge import (
    APPLICATION_REQUEST_MARKER,
    parse_application_request,
    plan_application,
    prepare_exact_openspec_validation,
    prove_exact_openspec_validation,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "4e3241d7d84a64012bf3b6218442128a4cb48d7a"
_CHECKIN_ISSUE = 142
_BRANCH = "agent/simplify-scheduled-agent-control-plane"
_BEFORE = "1111111111111111111111111111111111111111"
_COMMIT_ONE = "2222222222222222222222222222222222222222"
_AFTER = "3333333333333333333333333333333333333333"
_FIXTURE_VALUE = "fixture-value"


def _app(slug: str) -> dict[str, object]:
    return {"slug": slug}


def _user(login: str) -> dict[str, object]:
    return {"login": login}


def _connector_comment(comment_id: int, body: str) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": _user("royhsu-work"),
        "performed_via_github_app": _app("chatgpt-codex-connector"),
    }


def _actions_comment(comment_id: int, body: str) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": _user("github-actions[bot]"),
        "performed_via_github_app": _app("github-actions"),
    }


def _worker_result() -> dict[str, object]:
    return {
        "issue_number": 138,
        "role": "lead",
        "action": "explore-change",
        "explore_disposition": "PROPOSAL_READY",
        "propose_disposition": None,
        "result_content": "bounded result",
        "requested_effects": [],
    }


def _content_effect(*, path: str, message: str, content: str) -> dict[str, str]:
    return {
        "kind": "github-mutation",
        "payload_json": json.dumps(
            {
                "issue_number": 138,
                "operation": "contents-upsert",
                "path": path,
                "branch": _BRANCH,
                "message": message,
                "content": content,
                "expected_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            },
            sort_keys=True,
        ),
    }


def _ref_create_effect(*, sha: str = _BEFORE) -> dict[str, str]:
    return {
        "kind": "github-mutation",
        "payload_json": json.dumps(
            {
                "issue_number": 138,
                "operation": "ref-create",
                "ref": f"refs/heads/{_BRANCH}",
                "sha": sha,
            },
            sort_keys=True,
        ),
    }


def _propose_worker_result() -> dict[str, object]:
    return {
        "issue_number": 138,
        "role": "lead",
        "action": "propose-change",
        "explore_disposition": None,
        "propose_disposition": None,
        "result_content": "formal correction",
        "requested_effects": [
            _content_effect(
                path="openspec/changes/simplify-scheduled-agent-control-plane/proposal.md",
                message="Update formal proposal",
                content="proposal\n",
            ),
            _content_effect(
                path="openspec/changes/simplify-scheduled-agent-control-plane/design.md",
                message="Update formal design",
                content="design\n",
            ),
        ],
    }


def _resolve_worker_result() -> dict[str, object]:
    worker_result = _propose_worker_result()
    worker_result["action"] = "resolve-question"
    return worker_result


def _effect_request(
    *,
    dispatch_request_comment_id: int = 100,
    dispatch_run_id: int = 200,
    worker_result: dict[str, object] | None = None,
) -> str:
    raw = json.dumps(worker_result or _worker_result(), sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return "\n".join(
        (
            APPLICATION_REQUEST_MARKER,
            f"Dispatch-Request-Comment-ID: {dispatch_request_comment_id}",
            f"Dispatch-Run-ID: {dispatch_run_id}",
            f"Worker-Result-B64: {encoded}",
        )
    )


def _dispatch_request() -> str:
    return "DISPATCH_REQUEST\nRequested-At: 2026-08-31T11:01:49+08:00"


def _dispatch_decision(*, revision: str = _REVISION, disposition: str = "AUTHORIZE") -> str:
    lines = [
        "DISPATCH_DECISION",
        "Request-Comment-ID: 100",
        f"Default-Branch-Revision: {revision}",
        f"Disposition: {disposition}",
    ]
    if disposition == "AUTHORIZE":
        lines.extend(("Issue: 138", "Role: lead", "Action: explore-change"))
    else:
        lines.append("Reason: no work")
    return "\n".join(lines)


def _event(body: str, *, trusted: bool = True) -> dict[str, object]:
    comment = _connector_comment(102, body)
    if not trusted:
        comment["performed_via_github_app"] = None
    return {
        "action": "created",
        "issue": {
            "number": _CHECKIN_ISSUE,
            "title": "[Agent Runtime] 2026-09-03",
            "state": "open",
            "labels": [],
        },
        "comment": comment,
    }


def _comments(
    effect_body: str, *, decision_body: str | None = None
) -> list[list[dict[str, object]]]:
    return [
        [
            _connector_comment(100, _dispatch_request()),
            _actions_comment(101, decision_body or _dispatch_decision()),
            _connector_comment(102, effect_body),
        ]
    ]


def test_parse_application_request_decodes_exact_worker_result() -> None:
    body = _effect_request()

    request = parse_application_request(body)

    assert request is not None
    assert request.dispatch_request_comment_id == 100
    assert request.dispatch_run_id == 200
    assert json.loads(request.raw_worker_result) == _worker_result()


def test_parse_application_request_ignores_unrelated_comment() -> None:
    assert parse_application_request(_dispatch_request()) is None


def test_parse_application_request_rejects_malformed_effect_request() -> None:
    with pytest.raises(ValueError, match="exactly four lines"):
        pardef test_plan_application_accepts_exact_run_result() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None
    decision = bridge.parse_dispatch_decision(_dispatch_decision())
    assert decision is not None

    plan = plan_application(
        event=_event(body),
        request=request,
        dispatch_result=decision,
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source is not None
    assert (plan.source.issue_number, plan.source.role, plan.source.action) == (
        138,
        "lead",
        "explore-change",
    )
    assert plan.effect_request_comment_id == 102
    assert json.loads(plan.raw_worker_result or "") == _worker_result()


def test_plan_application_ignores_non_effect_comment() -> None:
    body = "DISPATCH_REQUEST\nRequested-At: now"
    request = bridge.ApplicationRequest(_REQUEST_ID, _RUN_ID, "{}")
    decision = bridge.parse_dispatch_decision(_dispatch_decision())
    assert decision is not None
    plan = plan_application(
        event=_event(body),
        request=request,
        dispatch_result=decision,
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )
    assert not plan.should_apply


def test_plan_application_rejects_connector_provenance_bypass() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None
    decision = bridge.parse_dispatch_decision(_dispatch_decision())
    assert decision is not None

    with pytest.raises(ValueError, match="configured ChatGPT connector"):
        plan_application(
            event=_event(body, trusted=False),
            request=request,
            dispatch_result=decision,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_plan_application_rejects_stale_dispatch_revision() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None
    decision = bridge.parse_dispatch_decision(_dispatch_decision(revision="0" * 40))
    assert decision is not None

    with pytest.raises(ValueError, match="revision is stale"):
        plan_application(
            event=_event(body),
            request=request,
            dispatch_result=decision,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_plan_application_rejects_non_authorizing_dispatch() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None
    decision = bridge.parse_dispatch_decision(_dispatch_decision(disposition="NO_WORK"))
    assert decision is not None

    with pytest.raises(ValueError, match="requires an AUTHORIZE"):
        plan_application(
            event=_event(body),
            request=request,
            dispatch_result=decision,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


 repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_prepare_and_prove_exact_openspec_validation_from_application_commit_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch_heads = iter((_BEFORE, _AFTER))
    proposal_path = "openspec/changes/simplify-scheduled-agent-control-plane/proposal.md"
    design_path = "openspec/changes/simplify-scheduled-agent-control-plane/design.md"

    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        if api_path == "branches/agent%2Fsimplify-scheduled-agent-control-plane":
            return {"commit": {"sha": next(branch_heads)}}
        if api_path == f"compare/{_BEFORE}...{_AFTER}":
            return {
                "status": "ahead",
                "total_commits": 2,
                "commits": [{"sha": _COMMIT_ONE}, {"sha": _AFTER}],
            }
        if api_path == f"commits/{_COMMIT_ONE}":
            return {
                "sha": _COMMIT_ONE,
                "commit": {"message": "Update formal proposal"},
                "parents": [{"sha": _BEFORE}],
                "files": [
                    {
                        "filename": proposal_path,
                        "status": "modified",
                        "sha": bridge._git_blob_sha("proposal\n"),
                    }
                ],
            }
        if api_path == f"commits/{_AFTER}":
            return {
                "sha": _AFTER,
                "commit": {"message": "Update formal design"},
                "parents": [{"sha": _COMMIT_ONE}],
                "files": [
                    {
                        "filename": design_path,
                        "status": "modified",
                        "sha": bridge._git_blob_sha("design\n"),
                    }
                ],
            }
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(bridge, "_github_json", fake_github_json)
    raw = json.dumps(_propose_worker_result(), sort_keys=True)
    source = WorkerRequest(138, "lead", "propose-change")

    probe = prepare_exact_openspec_validation(
        raw,
        source=source,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
    )

    assert probe is not None
    assert probe.branch == _BRANCH
    assert probe.before_sha == _BEFORE
    assert [mutation.path for mutation in probe.mutations] == [proposal_path, design_path]

    target = prove_exact_openspec_validation(
        probe,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        correlation="effect-request-102",
    )

    assert target.repository == _REPOSITORY
    assert target.revision == _AFTER
    assert target.correlation == "effect-request-102"


def test_prepare_exact_openspec_validation_accepts_topology_eligible_resolve_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        if api_path == "branches/agent%2Fsimplify-scheduled-agent-control-plane":
            return {"commit": {"sha": _BEFORE}}
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(bridge, "_github_json", fake_github_json)
    probe = prepare_exact_openspec_validation(
        json.dumps(_resolve_worker_result(), sort_keys=True),
        source=WorkerRequest(138, "lead", "resolve-question"),
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
        workflow_text=(
            "| `Lead / resolve-question` | semantic correction ready | "
            "`Reviewer / review-openspec` |\n"
        ),
    )

    assert probe is not None
    assert probe.branch == _BRANCH
    assert probe.before_sha == _BEFORE


def test_prepare_exact_openspec_validation_accepts_matching_ref_create_for_new_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_result = _propose_worker_result()
    requested_effects = worker_result["requested_effects"]
    assert isinstance(requested_effects, list)
    worker_result["requested_effects"] = [_ref_create_effect(), *requested_effects]

    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        if api_path == "branches/agent%2Fsimplify-scheduled-agent-control-plane":
            raise HTTPError(
                url="https://api.github.test/branch",
                code=404,
                msg="Not Found",
                hdrs=Message(),
                fp=None,
            )
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(bridge, "_github_json", fake_github_json)
    probe = prepare_exact_openspec_validation(
        json.dumps(worker_result, sort_keys=True),
        source=WorkerRequest(138, "lead", "propose-change"),
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
    )

    assert probe is not None
    assert probe.branch == _BRANCH
    assert probe.before_sha == _BEFORE


def test_prepare_exact_openspec_validation_rejects_missing_branch_without_ref_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        assert repository == _REPOSITORY
        assert token == _FIXTURE_VALUE
        if api_path == "branches/agent%2Fsimplify-scheduled-agent-control-plane":
            raise HTTPError(
                url="https://api.github.test/branch",
                code=404,
                msg="Not Found",
                hdrs=Message(),
                fp=None,
            )
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(bridge, "_github_json", fake_github_json)
    with pytest.raises(RuntimeError, match="absent without a matching ref-create"):
        prepare_exact_openspec_validation(
            json.dumps(_propose_worker_result(), sort_keys=True),
            source=WorkerRequest(138, "lead", "propose-change"),
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
        )


def test_exact_openspec_validation_fails_closed_on_interleaved_branch_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch_heads = iter((_BEFORE, _AFTER))

    def fake_github_json(repository: str, token: str, api_path: str) -> object:
        del repository, token
        if api_path == "branches/agent%2Fsimplify-scheduled-agent-control-plane":
            return {"commit": {"sha": next(branch_heads)}}
        if api_path == f"compare/{_BEFORE}...{_AFTER}":
            return {
                "status": "ahead",
                "total_commits": 3,
                "commits": [
                    {"sha": _COMMIT_ONE},
                    {"sha": "4444444444444444444444444444444444444444"},
                    {"sha": _AFTER},
                ],
            }
        raise AssertionError(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(bridge, "_github_json", fake_github_json)
    raw = json.dumps(_propose_worker_result(), sort_keys=True)
    source = WorkerRequest(138, "lead", "propose-change")
    probe = prepare_exact_openspec_validation(
        raw,
        source=source,
        repository=_REPOSITORY,
        token=_FIXTURE_VALUE,
    )
    assert probe is not None

    with pytest.raises(RuntimeError, match="unexpected commit sequence"):
        prove_exact_openspec_validation(
            probe,
            repository=_REPOSITORY,
            token=_FIXTURE_VALUE,
            correlation="effect-request-102",
        )


def test_application_workflow_is_no_api_and_uses_dedicated_write_boundary() -> None:
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")

    assert "issue_comment:" in workflow
    assert "startsWith(github.event.comment.body, 'EFFECT_REQUEST')" in workflow
    assert "startsWith(github.event.comment.body, 'VALIDATION_RESOURCE_REQUEST')" in workflow
    assert "contents: write" in workflow
    assert "issues: write" in workflow
    assert "pull-requests: write" in workflow
    assert "id: apply" in workflow
    assert "validation_required" in workflow
    assert "validation_target_repository" in workflow
    assert "validation_target_revision" in workflow
    assert "validation_correlation" in workflow
    assert "scheduled_agent_application_bridge" in workflow
    assert "scheduled_agent_validation_resource" in workflow
    assert "Checkout exact validation target" in workflow
    assert "openspec validate --all --strict --json --no-interactive" in workflow
    assert "actions/workflows/openspec-validate.yml/dispatches" not in workflow
    assert "openai" not in workflow.lower()
    assert "responses" not in workflow.lower()
