"""Structured-result and first-activation application boundary tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

import pytest

import investment_strategy.scheduled_agent_application_bridge as bridge
from investment_strategy.scheduled_agent_action_model import ResultKind
from investment_strategy.scheduled_agent_effects import EffectBatch, formal_application_correlation
from investment_strategy.scheduled_agent_runtime import GitHubIssueObservation, WorkerRequest
from investment_strategy.scheduled_agent_validation_resource import ValidationResourceTarget
from investment_strategy.scheduled_agent_worker import parse_worker_result

_REVISION = "4e3241d7d84a64012bf3b6218442128a4cb48d7a"
_TARGET_REVISION = "b" * 40
_CHANGE = "prefix-safe-formal-activation"


def _raw(**overrides: object) -> str:
    payload: dict[str, object] = {
        "issue_number": 138,
        "role": "executor",
        "action": "implement-change",
        "change": "simplify-scheduled-agent-control-plane",
        "result_kind": "ready",
        "evidence_ref": "issuecomment-typed-result",
        "result_content": "semantic evidence",
        "requested_effects": [],
    }
    payload.update(overrides)
    return json.dumps(payload)


def _activation_result(
    *,
    requested_effects: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "issue_number": 138,
        "role": "lead",
        "action": "propose-change",
        "change": "unset",
        "result_kind": "ready-for-openspec-review",
        "evidence_ref": "issuecomment-proposal-ready",
        "result_content": (
            "ACTION_RESULT\n"
            "Workflow: #138\n"
            "Change: unset\n"
            "Action: propose-change\n"
            "Role: lead\n"
            "Result: READY_FOR_OPENSPEC_REVIEW\n"
            f"Revision: {_REVISION}\n"
            f"Default-Branch-Revision: {_REVISION}\n"
            "Evidence-Ref: issuecomment-proposal-ready\n"
            "Proposal: exact bounded proposal\n"
        ),
        "requested_effects": requested_effects or [],
    }


def _activation_materialization() -> dict[str, object]:
    return {
        "issue_number": 138,
        "operation": "application-materialize",
        "expected_change": "unset",
        "change": _CHANGE,
        "branch": f"agent/{_CHANGE}",
        "base_sha": _REVISION,
        "message": "formalize bounded proposal",
        "files": [
            {
                "path": f"openspec/changes/{_CHANGE}/.openspec.yaml",
                "blob_sha": "a" * 40,
                "expected_sha": None,
            }
        ],
        "pr_number": None,
    }


def test_parser_accepts_one_exact_typed_result() -> None:
    request = WorkerRequest(138, "executor", "implement-change")
    result = parse_worker_result(_raw(), request)
    assert result.issue_number == 138
    assert result.action == "implement-change"
    assert result.typed_result.result.kind is ResultKind.READY
    assert result.requested_effects == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"issue_number": 139},
        {"role": "lead"},
        {"action": "unknown-action"},
        {"result_kind": "not-a-result"},
        {"requested_effects": "not-a-list"},
    ],
)
def test_parser_rejects_identity_or_vocabulary_mismatch(overrides: dict[str, object]) -> None:
    request = WorkerRequest(138, "executor", "implement-change")
    with pytest.raises(ValueError):
        parse_worker_result(_raw(**overrides), request)


def test_parser_preserves_requested_effect_as_untrusted_data() -> None:
    request = WorkerRequest(138, "executor", "implement-change")
    raw = _raw(
        requested_effects=[
            {"kind": "issue-comment", "payload_json": '{"issue_number":138,"body":"evidence"}'}
        ]
    )
    result = parse_worker_result(raw, request)
    assert result.requested_effects[0].kind == "issue-comment"


def test_worker_module_has_no_model_or_actions_runtime() -> None:
    source = Path("src/investment_strategy/scheduled_agent_worker.py").read_text(encoding="utf-8")
    for forbidden in ("OPENAI_API", "Responses", "WorkerToolRuntime", "subprocess"):
        assert forbidden not in source


def test_first_activation_result_is_application_bound_to_exact_change_revision() -> None:
    source = WorkerRequest(138, "lead", "propose-change")
    worker = parse_worker_result(json.dumps(_activation_result()), source)

    body, correlation, successor = bridge._activation_result_body(
        worker,
        source=source,
        change=_CHANGE,
        result_revision=_TARGET_REVISION,
        current_revision=_REVISION,
        request_comment_id=901,
    )

    assert "Change: unset" not in body
    assert f"Change: {_CHANGE}" in body
    assert f"Revision: {_TARGET_REVISION}" in body
    assert f"Default-Branch-Revision: {_REVISION}" in body
    assert "Repository-derived successor: Reviewer / review-openspec" in body
    assert successor == ("reviewer", "review-openspec")
    assert correlation == formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="ready-for-openspec-review",
        current_revision=_REVISION,
        request_comment_id=901,
    )
    assert f"Application-Correlation: {correlation}" in body


def test_validation_passed_first_activation_does_not_promote_inside_materialization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = WorkerRequest(138, "lead", "propose-change")
    materialization = _activation_materialization()
    worker_payload = _activation_result(
        requested_effects=[
            {
                "kind": "github-mutation",
                "payload_json": json.dumps(materialization, sort_keys=True),
            }
        ]
    )
    raw = json.dumps(worker_payload)
    target = ValidationResourceTarget(
        repository="royhsu-work/investment-strategy",
        revision=_TARGET_REVISION,
        correlation="effect-request-138",
        pr_number=247,
        change=_CHANGE,
        validation_required=True,
        branch=f"agent/{_CHANGE}",
    )
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"comment": {"body": "EFFECT_REQUEST"}}),
        encoding="utf-8",
    )
    calls: list[tuple[bool, bool, str | None]] = []
    completions: list[ValidationResourceTarget] = []

    monkeypatch.setenv("GITHUB_REPOSITORY", "royhsu-work/investment-strategy")
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setattr(bridge, "_fresh_event_observation", lambda *_args: None)
    monkeypatch.setattr(
        bridge,
        "parse_application_request",
        lambda _body: bridge.ApplicationRequest(_REVISION, raw),
    )
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: cast(object, None),
    )
    monkeypatch.setattr(
        bridge,
        "plan_application",
        lambda **_kwargs: bridge.ApplicationPlan(
            True,
            source=source,
            raw_worker_result=raw,
            request_comment_id=901,
        ),
    )
    monkeypatch.setattr(
        bridge,
        "observe_materialization_target",
        lambda *_args, **_kwargs: target,
    )

    def fake_run(
        _raw: str,
        *,
        apply_derived: bool,
        materialization_promote_change: bool,
        validated_materialization_revision: str | None,
        **_kwargs: object,
    ) -> tuple[EffectBatch, bridge.ApplyResult]:
        calls.append(
            (
                apply_derived,
                materialization_promote_change,
                validated_materialization_revision,
            )
        )
        return EffectBatch(source=source, effects=()), bridge.ApplyResult(True, "applied")

    monkeypatch.setattr(bridge, "run_guarded_effect_application", fake_run)
    monkeypatch.setattr(
        bridge,
        "_complete_first_activation",
        lambda **kwargs: completions.append(cast(ValidationResourceTarget, kwargs["target"])),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scheduled_agent_application_bridge",
            "--event-path",
            str(event_path),
            "--revision",
            _REVISION,
            "--default-branch",
            "main",
            "--validation-passed",
            "--validated-revision",
            _TARGET_REVISION,
        ],
    )

    assert bridge.main() == 0
    assert calls == [(False, False, _TARGET_REVISION)]
    assert completions == [target]


def test_first_activation_promotes_change_and_successor_in_one_issue_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "propose-change")
    raw = json.dumps(_activation_result())
    target = ValidationResourceTarget(
        repository="royhsu-work/investment-strategy",
        revision=_TARGET_REVISION,
        correlation="effect-request-138",
        pr_number=247,
        change=_CHANGE,
        validation_required=True,
        branch=f"agent/{_CHANGE}",
    )
    issue: dict[str, object] = {
        "number": 138,
        "state": "open",
        "body": "Change: unset\nPreserve: yes\n",
        "labels": [{"name": "action:propose-change"}, {"name": "keep-me"}],
    }
    patches: list[dict[str, object]] = []

    def fake_normalize(payload: object) -> GitHubIssueObservation | None:
        if not isinstance(payload, dict):
            return None
        body = payload.get("body")
        labels = payload.get("labels")
        if not isinstance(body, str) or not isinstance(labels, list):
            return None
        change = _CHANGE if f"Change: {_CHANGE}" in body else "unset"
        names = {
            item if isinstance(item, str) else item.get("name")
            for item in labels
            if isinstance(item, str)
            or (isinstance(item, dict) and isinstance(item.get("name"), str))
        }
        action = "review-openspec" if "action:review-openspec" in names else "propose-change"
        role = "reviewer" if action == "review-openspec" else "lead"
        return GitHubIssueObservation(
            issue_number=138,
            change=change,
            routing=cast(tuple[str, str], (role, action)),
            state="open",
            created_order=1,
            authoritative=True,
        )

    def fake_github(
        _repository: str,
        _token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: object = None,
    ) -> object:
        assert api_path == "issues/138"
        if method == "PATCH":
            assert isinstance(payload, dict)
            patches.append(dict(payload))
            issue.update(payload)
        return issue

    monkeypatch.setattr(bridge, "_fresh_preactivation_source", lambda *_args: None)
    monkeypatch.setattr(bridge, "_existing_activation_correlation", lambda **_kwargs: None)
    monkeypatch.setattr(bridge, "_persist_activation_result", lambda *_args, **_kwargs: 777)
    monkeypatch.setattr(bridge, "_formal_qualification", lambda **_kwargs: True)
    monkeypatch.setattr(
        bridge,
        "observe_materialization_target",
        lambda *_args, **_kwargs: target,
    )
    monkeypatch.setattr(bridge, "_github_json", fake_github)
    monkeypatch.setattr(bridge, "normalize_github_issue", fake_normalize)

    bridge._complete_first_activation(
        raw_worker_result=raw,
        materialization=_activation_materialization(),
        target=target,
        source=source,
        repository="royhsu-work/investment-strategy",
        token="token",
        current_revision=_REVISION,
        default_branch="main",
        request_comment_id=901,
    )

    assert len(patches) == 1
    patch = patches[0]
    assert patch["body"] == f"Change: {_CHANGE}\nPreserve: yes\n"
    assert patch["labels"] == ["keep-me", "action:review-openspec"]


def test_existing_pending_first_activation_result_is_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "propose-change")
    worker = parse_worker_result(json.dumps(_activation_result()), source)
    body, correlation, _successor = bridge._activation_result_body(
        worker,
        source=source,
        change=_CHANGE,
        result_revision=_TARGET_REVISION,
        current_revision=_REVISION,
        request_comment_id=800,
    )
    comment = {
        "id": 812,
        "body": body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }

    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda *_args, **_kwargs: (comment,),
    )
    monkeypatch.setattr(bridge, "_formal_qualification", lambda **_kwargs: True)

    assert bridge._existing_activation_correlation(
        repository="royhsu-work/investment-strategy",
        token="token",
        source=source,
        change=_CHANGE,
        result_revision=_TARGET_REVISION,
        current_revision=_REVISION,
        result_kind="ready-for-openspec-review",
        successor_routing=("reviewer", "review-openspec"),
    ) == correlation
