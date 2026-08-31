"""Regressions for the bounded pre-activation causal-position bootstrap."""

from __future__ import annotations

import json
from typing import cast

import pytest

import investment_strategy.scheduled_agent_effects as effects
from investment_strategy.scheduled_agent_causal_position import (
    bind_issue_cause_ref,
    cause_ref_from_issue_body,
)
from investment_strategy.scheduled_agent_effects import (
    GitHubEffectAdapter,
    StagedEffect,
    parse_effect_batch,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest


def _result_body(issue_number: int = 168) -> str:
    return (
        "## ACTION_RESULT\n"
        f"Workflow: #{issue_number}\n"
        "Change: unset\n"
        "Action: Lead / explore-change\n"
        "Result: PROPOSAL_READY\n"
        "\nEvidence: bounded.\n"
    )


def _durable_comment(comment_id: int, issue_number: int = 168) -> dict[str, object]:
    return {
        "id": comment_id,
        "issue_url": (
            f"https://api.github.com/repos/royhsu-work/investment-strategy/issues/{issue_number}"
        ),
        "body": _result_body(issue_number),
        "user": {"login": "github-actions[bot]"},
        "author_association": "CONTRIBUTOR",
    }


def _issue(*, action: str, body: str) -> dict[str, object]:
    return {
        "number": 168,
        "state": "open",
        "body": body,
        "created_at": "2026-08-31T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "agent:lead"}, {"name": f"action:{action}"}],
    }


def _activation(body: str) -> StagedEffect:
    return StagedEffect(
        kind="github-mutation",
        payload_json=json.dumps(
            {
                "issue_number": 168,
                "operation": "issue-update",
                "fields": {"body": "Change: causal-bootstrap\n"},
                "expected": {"body": body},
            }
        ),
    )


def test_cause_ref_insertion_preserves_unrelated_and_fenced_text() -> None:
    original = (
        "Change: unset\n\n## Intent\nKeep this text.\n```text\nCause-Ref: issuecomment-999\n```\n"
    )

    updated = bind_issue_cause_ref(original, 42)

    assert updated == (
        "Change: unset\n"
        "Cause-Ref: issuecomment-42\n"
        "\n"
        "## Intent\n"
        "Keep this text.\n"
        "```text\n"
        "Cause-Ref: issuecomment-999\n"
        "```\n"
    )
    assert cause_ref_from_issue_body(updated) == (42, True)


def test_duplicate_or_malformed_top_level_cause_ref_fails_closed() -> None:
    duplicate = "Change: unset\nCause-Ref: issuecomment-1\nCause-Ref: issuecomment-2\n"
    malformed = "Change: unset\nCause-Ref: latest\n"

    assert cause_ref_from_issue_body(duplicate) == (None, False)
    assert bind_issue_cause_ref(duplicate, 3) is None
    assert cause_ref_from_issue_body(malformed) == (None, False)


def test_proposal_ready_batch_binds_derived_route_to_invocation_result_payload() -> None:
    source = WorkerRequest(168, "lead", "explore-change")
    comment_payload = json.dumps({"issue_number": 168, "body": _result_body()})
    raw = json.dumps(
        {
            "issue_number": 168,
            "role": "lead",
            "action": "explore-change",
            "explore_disposition": "PROPOSAL_READY",
            "propose_disposition": None,
            "result_content": "bounded result",
            "requested_effects": [{"kind": "issue-comment", "payload_json": comment_payload}],
        }
    )

    batch = parse_effect_batch(raw, source)
    route = batch.effects[-1]

    assert route.kind == "routing-transition"
    assert route.derived is True
    assert route.cause_payload_json == comment_payload


def test_propose_uses_exact_cause_without_scanning_multiple_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = "Change: unset\nCause-Ref: issuecomment-22\n"
    issue = _issue(action="propose-change", body=body)
    calls: list[str] = []

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
        calls.append(f"{method} {api_path}")
        if api_path == "issues/168" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path == "issues/comments/22" and method == "GET":
            return _durable_comment(22)
        if api_path.startswith("issues/168/comments"):
            raise AssertionError("explicit Cause-Ref must not scan historical comments")
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        "royhsu-work/investment-strategy",
        "token",
        WorkerRequest(168, "lead", "propose-change"),
    )

    assert adapter.guard(_activation(body))
    assert "GET issues/comments/22" in calls


def test_wrong_explicit_cause_fails_without_falling_back_to_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = "Change: unset\nCause-Ref: issuecomment-22\n"
    issue = _issue(action="propose-change", body=body)

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
        if api_path == "issues/168" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path == "issues/comments/22" and method == "GET":
            wrong = _durable_comment(22)
            wrong_body = cast(str, wrong["body"])
            wrong["body"] = wrong_body.replace("PROPOSAL_READY", "NO_GO")
            return wrong
        if api_path.startswith("issues/168/comments"):
            raise AssertionError("invalid explicit Cause-Ref must fail, not search history")
        raise AssertionError(f"unexpected GitHub call: {method} {api_path}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        "royhsu-work/investment-strategy",
        "token",
        WorkerRequest(168, "lead", "propose-change"),
    )

    assert not adapter.guard(_activation(body))


def test_explore_route_persists_exact_new_comment_cause_before_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issue = _issue(action="explore-change", body="Change: unset\n\nIntent remains.\n")
    comment_payload = json.dumps({"issue_number": 168, "body": _result_body()})
    comment = StagedEffect(kind="issue-comment", payload_json=comment_payload)
    route = StagedEffect(
        kind="routing-transition",
        payload_json=json.dumps(
            {"issue_number": 168, "role": "lead", "action": "propose-change"},
            sort_keys=True,
        ),
        derived=True,
        cause_payload_json=comment_payload,
    )
    mutations: list[str] = []

    def fake_github_json(
        repository: str,
        token: str,
        api_path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        del repository, token, allow_not_found
        if api_path == "issues/168" and method == "GET":
            return json.loads(json.dumps(issue))
        if api_path == "issues/168/comments" and method == "POST":
            mutations.append("comment")
            return {"id": 33}
        if api_path == "issues/comments/33" and method == "GET":
            return _durable_comment(33)
        if api_path == "issues/168" and method == "PATCH":
            assert payload is not None and isinstance(payload.get("body"), str)
            mutations.append("cause")
            issue["body"] = payload["body"]
            return json.loads(json.dumps(issue))
        if api_path == "issues/168/labels/action%3Aexplore-change" and method == "DELETE":
            mutations.append("remove-route")
            labels = cast(list[dict[str, object]], issue["labels"])
            issue["labels"] = [item for item in labels if item.get("name") != "action:explore-change"]
            return None
        if api_path == "issues/168/labels" and method == "POST":
            assert payload == {"labels": ["action:propose-change"]}
            mutations.append("add-route")
            labels = cast(list[dict[str, object]], issue["labels"])
            labels.append({"name": "action:propose-change"})
            return json.loads(json.dumps(issue))
        raise AssertionError(f"unexpected GitHub call: {method} {api_path} {payload!r}")

    monkeypatch.setattr(effects, "_github_json", fake_github_json)
    adapter = GitHubEffectAdapter(
        "royhsu-work/investment-strategy",
        "token",
        WorkerRequest(168, "lead", "explore-change"),
    )

    assert adapter.guard(comment)
    assert adapter.guard(route)
    adapter.apply(comment)
    assert adapter.observe_postcondition(comment)
    adapter.apply(route)
    assert adapter.observe_postcondition(route)

    assert cause_ref_from_issue_body(issue["body"]) == (33, True)
    assert mutations == ["comment", "cause", "remove-route", "add-route"]
