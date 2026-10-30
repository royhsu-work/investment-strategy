from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Literal, cast
from urllib.parse import parse_qs, urlsplit

import pytest

from investment_strategy import issue_comment_bridge as bridge
from investment_strategy import scheduled_agent_carrier as carrier
from investment_strategy.scheduled_agent_checkin import checkin_title
from investment_strategy.scheduled_agent_idle_admission import (
    IdleCandidate,
    IdleDispatchEnvelope,
    make_idle_admission_request,
    parse_idle_admission_event,
    qualify_idle_handoff,
    render_idle_admission_request,
)
from investment_strategy.workflow_dispatch import (
    DispatchDecision,
    ObservationProvenance,
    Routing,
)

WORKFLOW_PATH = Path(".github/workflows/scheduled-agent-bridge.yml")
REQUEST_BODY = "DISPATCH_REQUEST\nRequested-At: 2026-09-03T03:45:00Z"
REVISION = "cb8f9ec12d826e0d71897a4c73ece961d00df59e"
_RECOVERY_TEST_FIELDS = {
    "predecessor_run_id": 7001,
    "predecessor_run_attempt": 1,
    "predecessor_job_id": 7002,
    "predecessor_artifact_id": 7003,
    "predecessor_artifact_digest": "sha256:" + "1" * 64,
    "failure_evidence_sha256": "2" * 64,
    "recovery_episode_sha256": "3" * 64,
}


def test_workflow_run_history_reads_beyond_filtered_thousand_without_weakening_identity() -> None:
    """A 1,000-result search cap must not hide an older matching Action run."""

    application_title = bridge.render_application_run_name(901)
    dispatch_title = bridge.render_dispatch_run_name(902)
    runs = [
        {
            "id": index,
            "event": "push" if index == 1 else "issue_comment",
            "display_title": (
                application_title
                if index in {1, 1206}
                else dispatch_title
                if index == 1205
                else "unrelated"
            ),
        }
        for index in range(1, 1207)
    ]
    paths: list[str] = []

    def read(repository: str, token: str, path: str) -> object:
        assert repository == "royhsu-work/investment-strategy"
        assert token
        paths.append(path)
        query = parse_qs(urlsplit(path).query)
        page = int(query["page"][0])
        filtered = query.get("event") == ["issue_comment"]
        selected = [run for run in runs if run["event"] == "issue_comment"] if filtered else runs
        return {
            "total_count": len(selected),
            "workflow_runs": selected[(page - 1) * 100 : page * 100],
        }

    assert [
        run["id"]
        for run in bridge._application_runs(  # noqa: SLF001
            "royhsu-work/investment-strategy", "token", 901, read=read
        )
        or ()
    ] == [1206]
    assert [
        run["id"]
        for run in bridge._dispatch_runs_for_request(  # noqa: SLF001
            "royhsu-work/investment-strategy", "token", 902, read=read
        )
        or ()
    ] == [1205]
    assert any("event=issue_comment" in path for path in paths)
    assert any("event=issue_comment" not in path for path in paths)


def test_workflow_run_history_fails_closed_on_concurrent_pagination_drift() -> None:
    def read(repository: str, token: str, path: str) -> object:
        query = parse_qs(urlsplit(path).query)
        page = int(query["page"][0])
        filtered = query.get("event") == ["issue_comment"]
        count = 1201 if filtered else 1202
        if not filtered and page == 2:
            count += 1
        return {
            "total_count": count,
            "workflow_runs": [
                {"id": index, "event": "issue_comment", "display_title": "unrelated"}
                for index in range((page - 1) * 100 + 1, min(page * 100, count) + 1)
            ],
        }

    assert (
        bridge._application_runs(  # noqa: SLF001
            "royhsu-work/investment-strategy", "token", 901, read=read
        )
        is None
    )


def test_unfiltered_workflow_history_rejects_missing_event_provenance() -> None:
    runs: list[dict[str, object]] = [
        {"id": index, "event": "issue_comment", "display_title": "other"}
        for index in range(1, 1102)
    ]
    runs[101]["event"] = None
    runs[101]["display_title"] = bridge.render_application_run_name(901)

    def read(repository: str, token: str, path: str) -> object:
        query = parse_qs(urlsplit(path).query)
        page = int(query["page"][0])
        selected = (
            [run for run in runs if run["event"] == "issue_comment"]
            if query.get("event") == ["issue_comment"]
            else runs
        )
        return {
            "total_count": len(selected),
            "workflow_runs": selected[(page - 1) * 100 : page * 100],
        }

    assert (
        bridge._application_runs(  # noqa: SLF001
            "royhsu-work/investment-strategy", "token", 901, read=read
        )
        is None
    )


@pytest.mark.parametrize("fault", ["short", "duplicate", "changed_count"])
def test_small_workflow_run_history_requires_complete_stable_pages(fault: str) -> None:
    def read(repository: str, token: str, path: str) -> object:
        query = parse_qs(urlsplit(path).query)
        page = int(query["page"][0])
        count = 102 if fault == "changed_count" and page == 2 else 101
        runs = (
            [{"id": n, "display_title": "other"} for n in range(1, 101)]
            if page == 1
            else []
            if fault == "short"
            else [{"id": 1 if fault == "duplicate" else 101, "display_title": "other"}]
        )
        return {"total_count": count, "workflow_runs": runs}

    assert (
        bridge._application_runs(  # noqa: SLF001
            "royhsu-work/investment-strategy", "token", 901, read=read
        )
        is None
    )


def test_prior_dispatch_handoff_indexes_run_history_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = (91, 92)
    artifacts: dict[int, bytes] = {
        request_id + 500: json.dumps(
            {
                "schema": bridge.DISPATCH_RESULT_SCHEMA,
                "request_comment_id": request_id,
                "default_branch_revision": REVISION,
                "disposition": "AUTHORIZE",
                "issue_number": 322,
                "action": "review-implementation",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        for request_id in previous
    }
    history_reads = 0

    def read(repository: str, token: str, path: str) -> object:
        nonlocal history_reads
        if path.startswith("actions/workflows/scheduled-agent-bridge.yml/runs?"):
            history_reads += 1
            return {
                "total_count": 2,
                "workflow_runs": [
                    {
                        "id": request_id + 400,
                        "display_title": bridge.render_dispatch_run_name(request_id),
                        "status": "completed",
                        "head_sha": REVISION,
                    }
                    for request_id in previous
                ],
            }
        for request_id in previous:
            if path == f"actions/runs/{request_id + 400}/artifacts?per_page=100":
                raw = artifacts[request_id + 500]
                return {
                    "total_count": 1,
                    "artifacts": [
                        {
                            "id": request_id + 500,
                            "name": "dispatch-result.json",
                            "expired": False,
                            "digest": f"sha256:{hashlib.sha256(raw).hexdigest()}",
                            "workflow_run": {"id": request_id + 400, "head_sha": REVISION},
                        }
                    ],
                }
        raise AssertionError(path)

    monkeypatch.setattr(
        bridge,
        "read_github_artifact_bytes",
        lambda repository, token, path: artifacts[int(path.split("/")[2])],
    )
    assert (
        bridge._prior_dispatch_handoff_reason(  # noqa: SLF001
            "owner/repo",
            "token",
            recent_comments=tuple(
                _trusted_connector_comment(
                    request_id, "DISPATCH_REQUEST\nRequested-At: 2026-10-30T00:00:00Z"
                )
                for request_id in previous
            ),
            owner="owner",
            current_dispatch_request_comment_id=93,
            plan_id="carrier-plan-" + "e" * 64,
            read=read,
        )
        is None
    )
    assert history_reads == 1


def _event(
    *,
    issue_number: int = 142,
    comment_id: int = 987,
    body: str = REQUEST_BODY,
    state: Literal["open", "closed"] = "open",
    labels: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "action": "created",
        "issue": {
            "number": issue_number,
            "title": checkin_title(date(2026, 9, 3)),
            "state": state,
            "labels": [] if labels is None else labels,
        },
        "comment": {"id": comment_id, "body": body},
    }


def _decision(
    disposition: Literal["AUTHORIZE", "NO_WORK", "FAIL_CLOSED"],
    *,
    issue_number: int | None = None,
    routing: Routing | None = None,
) -> DispatchDecision:
    return DispatchDecision(
        completeness="COMPLETE",
        observation_provenance=ObservationProvenance.QUALIFIED,
        formal_issue_ids=(() if issue_number is None else (issue_number,)),
        preactivation_candidate_ids=(),
        selected_issue_id=issue_number,
        selected_routing=routing,
        disposition=disposition,
        reason="test decision",
    )


def test_bridge_is_run_scoped_transport_without_mailbox_semantics() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "issue_comment:" in workflow
    assert "types: [created]" in workflow
    assert "run-name: Scheduled Agent Dispatch ${{ github.event.comment.id }}" in workflow
    assert "issues: read" in workflow
    assert "actions: write" in workflow
    assert "application_resume_job_id" not in bridge.BridgePlan.__dataclass_fields__
    assert "Resume exact incomplete application before semantic dispatch" not in workflow
    assert "/rerun" not in workflow  # completed application jobs are never re-executed
    assert "ref: ${{ github.event.repository.default_branch }}" in workflow
    assert "persist-credentials: false" in workflow
    assert "uv run python -m investment_strategy.issue_comment_bridge" in workflow
    assert '--result-payload "$RUNNER_TEMP/dispatch-result.json"' in workflow
    assert "actions/upload-artifact@v7" in workflow
    assert "name: dispatch-result.json" in workflow
    assert "archive: false" in workflow
    assert "Build plaintext JSON dispatch result" not in workflow
    assert "DISPATCH_DECISION" not in workflow
    assert "BEGIN_SCHEDULED_AGENT_DISPATCH_RESULT" not in workflow
    assert "END_SCHEDULED_AGENT_DISPATCH_RESULT" not in workflow
    for forbidden in ("AGENT_RUNTIME_CHECKIN_ISSUE", "--comments-path", "ISSUE_NUMBER"):
        assert forbidden not in workflow


def test_request_and_run_name_parsers_require_exact_identity() -> None:
    request = bridge.parse_dispatch_request(REQUEST_BODY)
    assert request is not None
    assert request.requested_at == "2026-09-03T03:45:00Z"
    assert bridge.render_dispatch_run_name(987) == "Scheduled Agent Dispatch 987"
    assert bridge.parse_dispatch_run_name("Scheduled Agent Dispatch 987") == 987
    assert bridge.parse_dispatch_run_name("Scheduled Agent Dispatch 0987") is None
    assert bridge.render_application_run_name(654) == "Scheduled Agent Application 654"
    assert bridge.parse_application_run_name("Scheduled Agent Application 654") == 654
    assert bridge.parse_application_run_name("Scheduled Agent Application 0654") is None

    for body in (
        "DISPATCH_REQUEST",
        "DISPATCH_REQUEST\nRequested-At:",
        f"{REQUEST_BODY}\nExtra: nope",
        " DISPATCH_REQUEST\nRequested-At: 2026-09-03T03:45:00Z",
    ):
        assert bridge.parse_dispatch_request(body) is None


def test_dispatch_result_document_round_trips_one_machine_decision() -> None:
    decision = _decision(
        "AUTHORIZE",
        issue_number=138,
        routing=("executor", "implement-change"),
    )
    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=decision,
    )
    payload = json.loads(rendered)

    assert payload == {
        "schema": "scheduled-agent-dispatch-result/v1",
        "request_comment_id": 987,
        "default_branch_revision": REVISION,
        "disposition": "AUTHORIZE",
        "issue_number": 138,
        "action": "implement-change",
    }
    assert "role" not in payload

    parsed = bridge.parse_dispatch_result_document(rendered)
    assert parsed.issue_number == 138
    assert parsed.role == "executor"
    assert parsed.action == "implement-change"


def test_dispatch_result_document_rejects_invalid_action_and_extra_role() -> None:
    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=_decision(
            "AUTHORIZE",
            issue_number=138,
            routing=("executor", "merge-implementation-pr"),
        ),
    )
    payload = json.loads(rendered)

    payload["action"] = "merge-pr"
    with pytest.raises(RuntimeError, match="Action is invalid"):
        bridge.parse_dispatch_result_document(json.dumps(payload))

    payload["action"] = "merge-implementation-pr"
    payload["role"] = "executor"
    with pytest.raises(RuntimeError, match="schema is invalid"):
        bridge.parse_dispatch_result_document(json.dumps(payload))


@pytest.mark.parametrize("disposition", ["NO_WORK", "FAIL_CLOSED"])
def test_non_authorizing_decisions_have_no_selected_work(
    disposition: Literal["NO_WORK", "FAIL_CLOSED"],
) -> None:
    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=_decision(disposition),
    )
    parsed = bridge.parse_dispatch_result_document(rendered)
    assert parsed.disposition == disposition
    assert parsed.issue_number is None
    assert parsed.action is None
    assert parsed.reason == "test decision"


def test_retry_limit_dispatch_result_carries_one_content_addressed_continuation() -> None:
    continuation = bridge.render_application_continuation_request(
        repository="owner/repo",
        issue_number=138,
        original_request_comment_id=987,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=7001,
        predecessor_run_attempt=1,
        predecessor_job_id=7002,
        predecessor_artifact_id=7003,
        predecessor_artifact_digest="sha256:" + "1" * 64,
        failure_evidence_sha256="2" * 64,
        recovery_episode_sha256="3" * 64,
    )
    decision = _decision("FAIL_CLOSED")
    decision = DispatchDecision(
        completeness=decision.completeness,
        observation_provenance=decision.observation_provenance,
        formal_issue_ids=decision.formal_issue_ids,
        preactivation_candidate_ids=decision.preactivation_candidate_ids,
        selected_issue_id=decision.selected_issue_id,
        selected_routing=decision.selected_routing,
        disposition=decision.disposition,
        reason="application-completion-continuation-required",
    )

    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=decision,
        application_continuation=continuation,
    )
    parsed = bridge.parse_dispatch_result_document(rendered)

    assert parsed.application_continuation == continuation
    with pytest.raises(ValueError, match="only valid"):
        bridge.render_dispatch_result_document(
            request_comment_id=987,
            default_branch_revision=REVISION,
            decision=_decision("NO_WORK"),
            application_continuation=continuation,
        )
    malformed = json.loads(rendered)
    malformed["application_continuation"] = "APPLICATION_CONTINUATION\nmalformed"
    with pytest.raises(RuntimeError, match="application continuation"):
        bridge.parse_dispatch_result_document(json.dumps(malformed))


def test_production_shaped_no_work_bootstrap_reaches_one_typed_idle_ingress() -> None:
    """The bridge artifact is consumed once, then Lead's candidate is typed."""

    decision_fixture = _decision("NO_WORK")
    no_work = DispatchDecision(
        completeness=decision_fixture.completeness,
        observation_provenance=decision_fixture.observation_provenance,
        formal_issue_ids=decision_fixture.formal_issue_ids,
        preactivation_candidate_ids=decision_fixture.preactivation_candidate_ids,
        selected_issue_id=decision_fixture.selected_issue_id,
        selected_routing=decision_fixture.selected_routing,
        disposition=decision_fixture.disposition,
        reason="no-routed-work",
    )
    artifact = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=no_work,
    )
    parsed = bridge.parse_dispatch_result_document(artifact)
    assert parsed.disposition == "NO_WORK"
    assert qualify_idle_handoff(no_work)

    envelope = IdleDispatchEnvelope(
        repository="owner/repo",
        default_branch="main",
        request_comment_id=parsed.request_comment_id,
        dispatch_run_id=202,
        dispatch_artifact_id=303,
        dispatch_artifact_sha256="a" * 64,
        default_branch_revision=parsed.default_branch_revision,
    )
    candidate = IdleCandidate(
        kind="new",
        source_kind="canonical-requirement",
        source_ref="openspec/spec.md#idle",
        source_revision=REVISION,
        evidence="bounded production-shaped finding",
        title="Explore the bounded finding",
        body="Change: unset\n\nEvidence: bounded production-shaped finding",
        labels=("action:explore-change",),
    )
    request = make_idle_admission_request(envelope, candidate)
    body = render_idle_admission_request(request)
    event = {
        "action": "created",
        "issue": {
            "number": 77,
            "title": "[Agent Runtime] 2026-09-29",
            "state": "open",
            "labels": [],
        },
        "comment": {
            "id": 404,
            "body": body,
            "user": {"login": "owner"},
            "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
        },
    }
    assert parse_idle_admission_event(event, repository="owner/repo") == request

    for disposition in ("AUTHORIZE", "FAIL_CLOSED"):
        decision = _decision(cast(Literal["AUTHORIZE", "FAIL_CLOSED"], disposition))
        assert not qualify_idle_handoff(decision)


def test_dispatch_plan_uses_only_current_day_shard_identity() -> None:
    decision = _decision(
        "AUTHORIZE",
        issue_number=138,
        routing=("executor", "implement-change"),
    )
    plan = bridge.plan_dispatch_decision(
        event=_event(),
        default_branch_revision=REVISION,
        decision=decision,
    )
    assert plan.should_emit is True
    assert plan.issue_number == 142
    assert plan.request_comment_id == 987
    assert plan.result_body is not None
    payload = json.loads(plan.result_body)
    assert payload["issue_number"] == 138
    assert payload["action"] == "implement-change"
    assert "role" not in payload

    formal_shard = _event(labels=[{"name": "action:implement-change"}])
    assert (
        bridge.plan_dispatch_decision(
            event=formal_shard,
            default_branch_revision=REVISION,
            decision=_decision("NO_WORK"),
        ).should_emit
        is False
    )


def test_production_dispatch_delegates_to_fresh_runtime_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight = object()
    decision = _decision("NO_WORK")
    observed: dict[str, object] = {}

    def fake_acquire(repository: str, token: str) -> object:
        observed["repository"] = repository
        observed["token"] = token
        return preflight

    def fake_classify(value: object) -> DispatchDecision:
        observed["preflight"] = value
        return decision

    monkeypatch.setattr(bridge, "acquire_current_github_preflight", fake_acquire)
    monkeypatch.setattr(bridge, "classify_dispatch", fake_classify)

    assert bridge.acquire_production_dispatch_decision("owner/repo", "token") is decision
    assert observed == {
        "repository": "owner/repo",
        "token": "token",
        "preflight": preflight,
    }


def test_shard_date_is_timezone_bound_and_not_workflow_state() -> None:
    from investment_strategy.scheduled_agent_checkin import parse_checkin_day, taipei_day

    assert taipei_day(datetime(2026, 9, 2, 16, 30, tzinfo=UTC)) == date(2026, 9, 3)
    payload = {
        "number": 142,
        "title": checkin_title(date(2026, 9, 3)),
        "state": "open",
        "labels": [],
    }
    assert parse_checkin_day(payload) == date(2026, 9, 3)
    assert parse_checkin_day({**payload, "labels": [{"name": "action:implement-change"}]}) is None


def _effect_request_comment(
    *,
    comment_id: int,
    created_at: str,
    action: str = "explore-change",
    role: str = "lead",
    result_kind: str = "proposal-ready",
    issue_number: int = 138,
    change: str = "unset",
    authorization_revision: str = REVISION,
) -> dict[str, object]:
    import base64

    worker_result = {
        "issue_number": issue_number,
        "role": role,
        "action": action,
        "change": change,
        "result_kind": result_kind,
        "evidence_ref": "same-evidence",
        "result_content": "same semantic payload",
        "requested_effects": [],
    }
    raw = json.dumps(worker_result, sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return {
        "id": comment_id,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                f"Authorization-Revision: {authorization_revision}",
                f"Worker-Result-B64: {encoded}",
            )
        ),
        "created_at": created_at,
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }


def _application_decision_comment(
    request: dict[str, object],
    *,
    disposition: str = "ACCEPTED",
    comment_id: int = 700,
) -> dict[str, object]:
    body = request["body"]
    assert isinstance(body, str)
    lines = body.splitlines()
    authorization_revision = lines[1].removeprefix("Authorization-Revision: ")
    encoded = lines[2].removeprefix("Worker-Result-B64: ")
    raw = base64.b64decode(encoded.encode("ascii"), validate=True).decode("utf-8")
    worker = json.loads(raw)
    return {
        "id": comment_id,
        "body": "\n".join(
            (
                "APPLICATION_DECISION",
                f"Request-Comment: {request['id']}",
                f"Request-Body-SHA256: {hashlib.sha256(body.encode('utf-8')).hexdigest()}",
                f"Authorization-Revision: {authorization_revision}",
                f"Issue: {worker['issue_number']}",
                f"Role: {worker['role']}",
                f"Action: {worker['action']}",
                f"Change: {worker['change']}",
                f"Result-Kind: {worker['result_kind']}",
                f"Disposition: {disposition}",
                f"Worker-Result-SHA256: {hashlib.sha256(raw.encode('utf-8')).hexdigest()}",
                f"Application-Intent-B64: {encoded}",
                "Reason: test",
            )
        ),
        "created_at": "2026-09-18T01:30:00Z",
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }


def _current_source_issue() -> dict[str, object]:
    return {
        "number": 138,
        "title": checkin_title(date(2026, 9, 3)),
        "state": "open",
        "created_at": "2026-09-17T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "action:explore-change"}],
        "body": "Change: unset",
    }


def _preactivation_admission() -> list[dict[str, object]]:
    """Authoritative current-route admission for first pre-activation tests."""

    return [
        {
            "id": 42,
            "event": "labeled",
            "created_at": "2026-09-18T00:00:00Z",
            "label": {"name": "action:explore-change"},
        }
    ]


def _formal_frontier_comment(
    comment_id: int,
    *,
    action: str,
    role: str,
    result: str,
    successor: str,
    request_id: int,
    change: str,
    issue_number: int = 138,
    revision: str = REVISION,
) -> dict[str, object]:
    body = "\n".join(
        (
            "ACTION_RESULT",
            f"Workflow: #{issue_number}",
            f"Change: {change}",
            f"Action: {action}",
            f"Role: {role}",
            f"Result: {result.upper().replace('-', '_')}",
            f"Revision: {revision}",
            f"Default-Branch-Revision: {revision}",
            "Application-Correlation: "
            f"application:{request_id}:{issue_number}:{change}:{role}:{action}:{result}:{revision}",
            f"Repository-derived successor: {successor}",
        )
    )
    return {
        "id": comment_id,
        "body": body,
        "created_at": f"2026-09-18T02:00:{comment_id // 10:02d}Z",
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }


def _frontier_lifecycle(
    transitions: list[tuple[int, str, str | None]],
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for index, (comment_id, current_action, successor_action) in enumerate(transitions):
        second = index + 1
        events.append(
            {
                "id": comment_id,
                "event": "commented",
                "created_at": f"2026-09-18T02:00:{comment_id // 10:02d}Z",
            }
        )
        if successor_action is None:
            continue
        # A -> A has no label write at the second occurrence.  The formal
        # qualifier proves that recurrence from the preceding bound result.
        if second > 1 and successor_action == current_action:
            continue
        events.extend(
            (
                {
                    "id": 1000 + index * 2,
                    "event": "unlabeled",
                    "created_at": f"2026-09-18T02:00:{comment_id // 10 + 1:02d}Z",
                    "label": {"name": f"action:{current_action}"},
                },
                {
                    "id": 1001 + index * 2,
                    "event": "labeled",
                    "created_at": f"2026-09-18T02:00:{comment_id // 10 + 1:02d}Z",
                    "label": {"name": f"action:{successor_action}"},
                },
            )
        )
    return events


@pytest.mark.parametrize(
    ("topology", "formal_comments", "transitions"),
    (
        (
            "A->A",
            (
                _formal_frontier_comment(
                    80,
                    action="implement-change",
                    role="executor",
                    result="more-implementation-required",
                    successor="Executor / implement-change",
                    request_id=80,
                    change="recurrence-a-a",
                ),
                _formal_frontier_comment(
                    100,
                    action="implement-change",
                    role="executor",
                    result="more-implementation-required",
                    successor="Executor / implement-change",
                    request_id=100,
                    change="recurrence-a-a",
                ),
            ),
            [
                (80, "review-implementation", "implement-change"),
                (100, "implement-change", "implement-change"),
            ],
        ),
        (
            "A->B->A",
            (
                _formal_frontier_comment(
                    80,
                    action="implement-change",
                    role="executor",
                    result="spec-blocker",
                    successor="Lead / resolve-question",
                    request_id=80,
                    change="recurrence-a-b-a",
                ),
                _formal_frontier_comment(
                    100,
                    action="resolve-question",
                    role="lead",
                    result="ready",
                    successor="Executor / implement-change",
                    request_id=100,
                    change="recurrence-a-b-a",
                ),
            ),
            [
                (80, "implement-change", "resolve-question"),
                (100, "resolve-question", "implement-change"),
            ],
        ),
    ),
)
def test_historical_same_action_application_does_not_block_current_frontier(
    topology: str,
    formal_comments: tuple[dict[str, object], ...],
    transitions: list[tuple[int, str, str | None]],
) -> None:
    del topology
    source = bridge.WorkerRequest(138, "executor", "implement-change")
    change = str(formal_comments[-1]["body"]).split("Change: ", 1)[1].splitlines()[0]
    historical_request = _effect_request_comment(
        comment_id=50,
        created_at="2026-09-18T01:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="more-implementation-required",
        issue_number=138,
        change=change,
    )
    historical_decision = _application_decision_comment(historical_request, comment_id=60)
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:implement-change"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [historical_request]
        if path.startswith("issues/138/comments?"):
            return [historical_decision, *formal_comments]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle(transitions)
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_same_action_frontier_acceptance_binds_its_own_formal_result() -> None:
    source = bridge.WorkerRequest(138, "executor", "implement-change")
    change = "recurrence-a-a-current"
    current_request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="more-implementation-required",
        issue_number=138,
        change=change,
    )
    decision = _application_decision_comment(current_request, comment_id=91)
    predecessor = _formal_frontier_comment(
        80,
        action="implement-change",
        role="executor",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=70,
        change=change,
    )
    current = _formal_frontier_comment(
        100,
        action="implement-change",
        role="executor",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=90,
        change=change,
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:implement-change"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [current_request]
        if path.startswith("issues/138/comments?"):
            return [decision, predecessor, current]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle(
                [
                    (80, "review-implementation", "implement-change"),
                    (100, "implement-change", "implement-change"),
                ]
            )
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion.state == "COMPLETE"
    assert completion.reason == "application-completion-complete"
    assert completion.request_comment_id == 90


@pytest.mark.parametrize("duplicate_count", (1, 2, 3))
def test_duplicate_formal_reemission_of_one_accepted_intent_releases_successor(
    duplicate_count: int,
) -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
    change = f"duplicate-formal-intent-{duplicate_count}"
    request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="finalize-change",
        role="lead",
        result_kind="archive-ready",
        issue_number=138,
        change=change,
    )
    decision = _application_decision_comment(request, comment_id=91)
    formal_comments = [
        _formal_frontier_comment(
            100 + index * 10,
            action="finalize-change",
            role="lead",
            result="archive-ready",
            successor="Reviewer / review-archive",
            request_id=90,
            change=change,
        )
        for index in range(duplicate_count)
    ]
    lifecycle = _frontier_lifecycle([(100, "finalize-change", "review-archive")])
    lifecycle.extend(
        {
            "id": 100 + index * 10,
            "event": "commented",
            "created_at": f"2026-09-18T02:00:{12 + index:02d}Z",
        }
        for index in range(1, duplicate_count)
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, *formal_comments]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return lifecycle
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_accepted_intent_qualifies_formal_result_after_safe_main_advance() -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
    formal_revision = "b" * 40
    advanced_revision = "a" * 40
    change = "formal-evidence-descendant-proof"
    request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="finalize-change",
        role="lead",
        result_kind="archive-ready",
        issue_number=138,
        change=change,
        authorization_revision=REVISION,
    )
    decision = _application_decision_comment(request, comment_id=91)
    formal = _formal_frontier_comment(
        100,
        action="finalize-change",
        role="lead",
        result="archive-ready",
        successor="Reviewer / review-archive",
        request_id=90,
        change=change,
    )
    body = str(formal["body"])
    formal["body"] = (
        body.replace(f"Revision: {REVISION}", f"Revision: {formal_revision}")
        .replace(
            f"Default-Branch-Revision: {REVISION}",
            f"Default-Branch-Revision: {formal_revision}",
        )
        .replace(
            f":{REVISION}\nRepository-derived successor:",
            f":{formal_revision}\nRepository-derived successor:",
        )
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "finalize-change", "review-archive")])
        if path in {
            f"compare/{REVISION}...{advanced_revision}",
            f"compare/{formal_revision}...{advanced_revision}",
        }:
            base_sha = path.removeprefix("compare/").split("...")[0]
            return {"status": "ahead", "base_commit": {"sha": base_sha}}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=advanced_revision,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_accepted_formal_result_waits_for_consequence_postconditions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
    change = "archive-postcondition-recovery"
    requested_effects = [
        {
            "kind": "issue-comment",
            "payload_json": json.dumps(
                {
                    "issue_number": 138,
                    "body": (
                        "ARCHIVE_REQUEST\n"
                        "Workflow: #138\n"
                        f"Change: {change}\n"
                        "Action: finalize-change\n"
                        f"Revision: {REVISION}"
                    ),
                },
                sort_keys=True,
            ),
        },
        {
            "kind": "github-mutation",
            "payload_json": json.dumps(
                {
                    "issue_number": 138,
                    "operation": "workflow-dispatch",
                    "workflow_id": "openspec-archive.yml",
                    "ref": "main",
                    "inputs": {
                        "change": change,
                        "issue": "138",
                        "revision": REVISION,
                        "request_key": f"archive-138-{REVISION}",
                    },
                },
                sort_keys=True,
            ),
        },
    ]
    worker = {
        "issue_number": 138,
        "role": "lead",
        "action": "finalize-change",
        "change": change,
        "result_kind": "archive-ready",
        "evidence_ref": "archive-evidence",
        "result_content": "archive evidence",
        "requested_effects": requested_effects,
    }
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    request = {
        "id": 90,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                f"Authorization-Revision: {REVISION}",
                f"Worker-Result-B64: {encoded}",
            )
        ),
        "created_at": "2026-09-18T02:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }
    decision = _application_decision_comment(request, comment_id=91)
    formal = _formal_frontier_comment(
        100,
        action="finalize-change",
        role="lead",
        result="archive-ready",
        successor="Reviewer / review-archive",
        request_id=90,
        change=change,
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }
    monkeypatch.setattr(
        bridge,
        "consequence_postconditions_complete",
        lambda *_args, **_kwargs: False,
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "finalize-change", "review-archive")])
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 90",
                        "status": "completed",
                        "conclusion": "success",
                        "run_attempt": 1,
                    }
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/777/jobs":
            return {
                "jobs": [
                    {
                        "id": 888,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ]
            }
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-successor-pending"
    assert completion.request_comment_id == 90
    assert completion.job_id is None


def test_completed_formal_result_at_safe_ancestor_is_not_resumed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
    formal_revision = "b" * 40
    advanced_revision = "a" * 40
    change = "formal-result-safe-ancestor"
    request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="finalize-change",
        role="lead",
        result_kind="archive-ready",
        issue_number=138,
        change=change,
        authorization_revision=REVISION,
    )
    decision = _application_decision_comment(request, comment_id=91)
    formal = _formal_frontier_comment(
        100,
        action="finalize-change",
        role="lead",
        result="archive-ready",
        successor="Reviewer / review-archive",
        request_id=90,
        change=change,
    )
    body = str(formal["body"])
    formal["body"] = (
        body.replace(f"Revision: {REVISION}", f"Revision: {formal_revision}")
        .replace(
            f"Default-Branch-Revision: {REVISION}",
            f"Default-Branch-Revision: {formal_revision}",
        )
        .replace(
            f":{REVISION}\nRepository-derived successor:",
            f":{formal_revision}\nRepository-derived successor:",
        )
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }
    observed_revisions: list[str] = []
    observed_accepted_intent: list[bool] = []

    def fake_postconditions(*_args: object, **kwargs: object) -> bool:
        revision = cast(str, kwargs["current_revision"])
        observed_revisions.append(revision)
        observed_accepted_intent.append(cast(bool, kwargs["accepted_intent"]))
        return revision == formal_revision

    monkeypatch.setattr(bridge, "consequence_postconditions_complete", fake_postconditions)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "finalize-change", "review-archive")])
        if path in {
            f"compare/{REVISION}...{advanced_revision}",
            f"compare/{formal_revision}...{advanced_revision}",
        }:
            base_sha = path.removeprefix("compare/").split("...")[0]
            return {"status": "ahead", "base_commit": {"sha": base_sha}}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=advanced_revision,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion(
        "NONE",
        "application-completion-none",
    )
    assert observed_revisions == [advanced_revision]
    assert observed_accepted_intent == [True]


def test_predecessor_is_not_resumed_after_merged_successor_consumes_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(234, "reviewer", "review-archive")
    worker = bridge.parse_worker_result(
        json.dumps(
            {
                "issue_number": 234,
                "role": "reviewer",
                "action": "review-archive",
                "change": "archive-change",
                "result_kind": "pass",
                "evidence_ref": "pr#313@head",
                "result_content": "review pass",
                "requested_effects": [],
            }
        ),
        source,
        authorized_change="archive-change",
    )

    class Observation:
        routing = ("executor", "merge-archive-pr")

    monkeypatch.setattr(bridge, "normalize_github_issue", lambda _issue: Observation())
    monkeypatch.setattr(
        bridge,
        "merged_pr_readiness_complete",
        lambda **kwargs: kwargs["action"] == "merge-archive-pr",
    )

    assert bridge._successor_consequence_supersedes(
        repository="owner/repo",
        token=str(REVISION),
        source=source,
        worker=worker,
        current_issue={},
        change="archive-change",
        current_revision=REVISION,
    )


@pytest.mark.parametrize(
    ("predecessor_disposition", "disposition"),
    [
        ("ACCEPTED", "ACCEPTED"),
        ("ACCEPTED", "REJECTED"),
        ("REJECTED", "REJECTED"),
        (None, "REJECTED"),
    ],
)
def test_completed_predecessor_acceptance_does_not_compete_with_new_frontier(
    disposition: str,
    predecessor_disposition: str | None,
) -> None:
    source = bridge.WorkerRequest(138, "executor", "implement-change")
    change = "recurrence-a-a-new-occurrence"
    predecessor_request = _effect_request_comment(
        comment_id=70,
        created_at="2026-09-18T01:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="more-implementation-required",
        issue_number=138,
        change=change,
    )
    predecessor_decision = _application_decision_comment(
        predecessor_request, comment_id=71, disposition=predecessor_disposition or "ACCEPTED"
    )
    predecessor_frontier = _formal_frontier_comment(
        80,
        action="implement-change",
        role="executor",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=70,
        change=change,
    )
    current_request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T03:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="more-implementation-required",
        issue_number=138,
        change=change,
    )
    current_decision = _application_decision_comment(
        current_request, comment_id=91, disposition=disposition
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:implement-change"}],
        "body": f"Change: {change}",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [predecessor_request, current_request]
        if path.startswith("issues/138/comments?"):
            return [
                *([] if predecessor_disposition is None else [predecessor_decision]),
                predecessor_frontier,
                current_decision,
            ]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(80, "review-implementation", "implement-change")])
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 90",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 1,
                    }
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/777/jobs":
            return {"jobs": [{"id": 888, "name": "apply"}]}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 4, 0, tzinfo=UTC),
    )

    if predecessor_disposition != "ACCEPTED":
        # A missing or explicitly rejected owner cannot prove a consequence.
        assert completion.state == "INVALID"
        assert completion.reason == "application-completion-consequence-without-acceptance"
        return
    assert completion.state == ("INVALID" if disposition == "ACCEPTED" else "REJECTED")
    assert completion.reason == (
        "application-completion-recovery-evidence-missing"
        if disposition == "ACCEPTED"
        else "application-completion-rejected"
    )
    assert completion.request_comment_id == 90
    assert completion.job_id is None


def test_current_frontier_reuses_formal_ancestry_after_main_advances() -> None:
    source = bridge.WorkerRequest(138, "executor", "implement-change")
    advanced_revision = "a" * 40
    formal = _formal_frontier_comment(
        100,
        action="implement-change",
        role="executor",
        result="more-implementation-required",
        successor="Executor / implement-change",
        request_id=90,
        change="frontier-main-advance",
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:implement-change"}],
        "body": "Change: frontier-main-advance",
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return []
        if path.startswith("issues/138/comments?"):
            return [formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "implement-change", "implement-change")])
        if path == f"compare/{REVISION}...{advanced_revision}":
            return {"status": "ahead", "base_commit": {"sha": REVISION}}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=advanced_revision,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_preaccept_live_application_run_is_not_redispatched() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
        authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "in_progress",
                        "run_attempt": 1,
                    }
                ]
            }
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-preaccept-in-progress"
    assert completion.job_id is None


def _completion_matrix_reader(
    requests: list[dict[str, object]],
    *,
    live_ids: set[int] | None = None,
    accepted_ids: set[int] | None = None,
    rejected_ids: set[int] | None = None,
    terminal_conclusion: str = "failure",
) -> bridge.GitHubReader:
    live_ids = set() if live_ids is None else live_ids
    accepted_ids = set() if accepted_ids is None else accepted_ids
    rejected_ids = set() if rejected_ids is None else rejected_ids
    request_ids = [int(cast(int, request["id"])) for request in requests]
    decisions = [
        _application_decision_comment(
            request,
            disposition="ACCEPTED" if int(cast(int, request["id"])) in accepted_ids else "REJECTED",
            comment_id=700 + index,
        )
        for index, request in enumerate(requests)
        if int(cast(int, request["id"])) in accepted_ids
        or int(cast(int, request["id"])) in rejected_ids
    ]
    run_by_request = {request_id: 9000 + index for index, request_id in enumerate(request_ids)}
    runs = [
        {
            "id": run_by_request[cast(int, request["id"])],
            "display_title": f"Scheduled Agent Application {request['id']}",
            "status": "in_progress" if request["id"] in live_ids else "completed",
            "conclusion": None if request["id"] in live_ids else terminal_conclusion,
            "run_attempt": 1,
        }
        for request in requests
    ]

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return requests
        if path.startswith("issues/138/comments?"):
            return decisions
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": runs}
        if path.startswith("actions/runs/") and path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path.startswith("actions/runs/") and path.endswith("/jobs"):
            run_id = int(path.split("/")[2])
            return {
                "jobs": [
                    {
                        "id": run_id + 100,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": terminal_conclusion,
                    }
                ]
            }
        raise AssertionError(path)

    return fake_read


@pytest.mark.parametrize(
    ("changed", "expected_state", "expected_reason"),
    [
        (None, "INVALID", "application-completion-execution-exception-requires-lead"),
        (
            "README.md",
            "INVALID",
            "application-completion-execution-exception-requires-lead",
        ),
        (
            "src/investment_strategy/scheduled_agent_application_bridge.py",
            "REJECTED",
            "application-completion-terminal-no-accept",
        ),
    ],
)
def test_preaccept_exception_blocks_unchanged_code_but_recovers_after_application_repair(
    changed: str | None, expected_state: str, expected_reason: str
) -> None:
    """A stable executable defect does not cause hourly semantic redispatch."""

    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request_revision = bridge._APPLICATION_DECISION_PROTOCOL_REVISION
    current_revision = request_revision if changed is None else "a" * 40
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
        authorization_revision=request_revision,
    )
    exception_body = "\n".join(
        (
            "EXECUTION_EXCEPTION",
            "Workflow: #138",
            "Change: unset",
            "Action: explore-change",
            "Role: lead",
            f"Revision: {request_revision}",
            "Request-Comment-ID: 654",
            "Run-ID: 9000",
            "Run-Attempt: 1",
            "Exception-Correlation: application:9000:1:654",
            "Mutation-Outcome: NO_APPLICATION_WRITE_ATTEMPTED",
            "Classification: UNCLASSIFIED_EXECUTION_EXCEPTION",
        )
    )
    exception_comment = {
        "id": 701,
        "body": exception_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    base_read = _completion_matrix_reader([request])

    def read(repository: str, token: str, path: str) -> object:
        if path.startswith("issues/138/comments?"):
            return [exception_comment]
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9000,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "completed",
                        "conclusion": "failure",
                        "head_sha": request_revision,
                        "run_attempt": 1,
                    }
                ]
            }
        if path == f"compare/{request_revision}...{current_revision}":
            return {
                "status": "ahead",
                "base_commit": {"sha": request_revision},
                "files": [{"filename": changed}],
            }
        return base_read(repository, token, path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=current_revision,
        read=read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )
    assert (completion.state, completion.reason) == (expected_state, expected_reason)
    assert completion.request_comment_id == 654


@pytest.mark.parametrize(
    ("attempts", "latest_attempt", "repaired", "expected"),
    [
        ((1, 2), 2, False, "BLOCKED"),
        ((1, 2), 2, True, "REPAIRED"),
        ((1,), 2, True, "REPAIRED"),
        ((1, 1), 2, True, "INVALID"),
        ((1, 3), 2, True, "INVALID"),
    ],
)
def test_preaccept_execution_exception_distinguishes_reruns_from_duplicate_receipts(
    attempts: tuple[int, ...], latest_attempt: int, repaired: bool, expected: str
) -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    revision = bridge._APPLICATION_DECISION_PROTOCOL_REVISION
    current_revision = "a" * 40 if repaired else revision
    comments = []
    for index, attempt in enumerate(attempts):
        comments.append(
            {
                "id": 800 + index,
                "user": {"login": "github-actions[bot]"},
                "performed_via_github_app": {"slug": "github-actions"},
                "body": "\n".join(
                    (
                        "EXECUTION_EXCEPTION",
                        "Workflow: #138",
                        "Change: unset",
                        "Action: explore-change",
                        "Role: lead",
                        f"Revision: {revision}",
                        "Request-Comment-ID: 654",
                        "Run-ID: 9000",
                        f"Run-Attempt: {attempt}",
                        f"Exception-Correlation: application:9000:{attempt}:654",
                        "Mutation-Outcome: NO_APPLICATION_WRITE_ATTEMPTED",
                        "Classification: UNCLASSIFIED_EXECUTION_EXCEPTION",
                    )
                ),
            }
        )

    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9000,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": latest_attempt,
                    }
                ]
            }
        if path == f"compare/{revision}...{current_revision}":
            return {
                "status": "ahead",
                "base_commit": {"sha": revision},
                "files": [
                    {"filename": "src/investment_strategy/scheduled_agent_application_bridge.py"}
                ],
            }
        raise AssertionError(path)

    result = bridge._preaccept_exception_repair_status(
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=654,
        issue_comments=tuple(comments),
        current_revision=current_revision,
        read=read,
    )
    assert result == expected


@pytest.mark.parametrize("count", (1, 2, 3))
@pytest.mark.parametrize("terminal_conclusion", ("failure", "cancelled", "timed_out", "skipped"))
def test_terminal_preactcept_candidates_do_not_compete_by_raw_cardinality(
    count: int, terminal_conclusion: str
) -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654 + index,
            created_at=f"2026-09-18T01:0{index}:00Z",
            authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        )
        for index in range(count)
    ]

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=_completion_matrix_reader(requests, terminal_conclusion=terminal_conclusion),
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "REJECTED"
    assert completion.reason == "application-completion-terminal-no-accept"
    assert completion.state != "AMBIGUOUS"


def test_terminal_preactcept_candidate_survives_archived_authorization_revision() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
        authorization_revision="5ef5fd95e57c563a03a96df85248cdb4f3c5f502",
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9000,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/9000/jobs":
            return {
                "jobs": [
                    {
                        "id": 9100,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        if path.startswith("compare/"):
            raise OSError("archived commit is no longer observable")
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "REJECTED"
    assert completion.reason == "application-completion-terminal-no-accept"


def test_terminal_noise_plus_one_live_candidate_waits_for_live_ingress() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654 + index,
            created_at=f"2026-09-18T01:0{index}:00Z",
            authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        )
        for index in range(3)
    ]

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=_completion_matrix_reader(requests, live_ids={656}),
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-preaccept-in-progress"
    assert completion.request_comment_id == 656


def test_rejected_noise_plus_one_live_candidate_does_not_release_ownership() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654 + index,
            created_at=f"2026-09-18T01:0{index}:00Z",
            authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        )
        for index in range(3)
    ]

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=_completion_matrix_reader(
            requests,
            live_ids={656},
            rejected_ids={654, 655},
        ),
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.request_comment_id == 656


def test_terminal_noise_plus_one_accepted_intent_owns_continuation() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654 + index,
            created_at=f"2026-09-18T01:0{index}:00Z",
            authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        )
        for index in range(3)
    ]

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=_completion_matrix_reader(requests, accepted_ids={654}),
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-recovery-evidence-missing"
    assert completion.request_comment_id == 654
    assert completion.job_id is None


def test_deleted_ingress_after_accept_uses_immutable_intent() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )
    decision = _application_decision_comment(request)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return []
        if path.startswith("issues/138/comments?"):
            return [decision]
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "in_progress",
                        "run_attempt": 1,
                    }
                ]
            }
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.request_comment_id == 654
    assert completion.reason == "application-completion-in-progress"


def test_edited_ingress_after_accept_cannot_block_immutable_intent() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    original = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )
    edited = {**original, "body": "EFFECT_REQUEST\nmalformed-after-accept"}
    decision = _application_decision_comment(original)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [edited]
        if path.startswith("issues/138/comments?"):
            return [decision]
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "in_progress",
                        "run_attempt": 1,
                    }
                ]
            }
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "RESUMABLE"
    assert completion.request_comment_id == 654
    assert completion.reason == "application-completion-in-progress"


def test_missing_acceptance_is_not_resumed_before_semantic_replay() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": []}
        if path.startswith("compare/"):
            return {}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-preaccept-evidence-unknown"


def test_unrelated_legacy_request_does_not_poison_current_source() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    unrelated = _effect_request_comment(
        comment_id=653,
        created_at="2026-09-18T00:59:00Z",
        issue_number=999,
    )
    body = unrelated["body"]
    assert isinstance(body, str)
    encoded = body.splitlines()[2].removeprefix("Worker-Result-B64: ")
    unrelated["body"] = "\n".join(
        (
            "EFFECT_REQUEST",
            "Dispatch-Request-Comment-ID: 100",
            "Dispatch-Run-ID: 200",
            f"Worker-Result-B64: {encoded}",
        )
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [unrelated]
        if path.startswith("issues/138/comments?"):
            return []
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "NONE"
    assert completion.reason == "application-completion-none"


def test_historical_raw_request_is_source_filtered_before_frontier_read() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    unrelated = {
        "id": 652,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                "Workflow: #234",
                "Action: resolve-question",
                "Worker-Result: legacy raw payload",
            )
        ),
        "created_at": "2026-09-17T12:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [unrelated]
        if path.startswith("issues/138/comments?"):
            return []
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_malformed_legacy_encoded_source_is_filtered_before_frontier_read() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")

    def legacy_comment(comment_id: int, raw_worker_result: str) -> dict[str, object]:
        encoded = base64.b64encode(raw_worker_result.encode("utf-8")).decode("ascii")
        return {
            "id": comment_id,
            "body": "\n".join(
                (
                    "EFFECT_REQUEST",
                    "Dispatch-Request-Comment-ID: 100",
                    "Dispatch-Decision-Comment-ID: 200",
                    f"Worker-Result-B64: {encoded}",
                )
            ),
            "created_at": "2026-09-17T12:00:00Z",
            "user": {"login": "owner"},
            "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
        }

    malformed_json = legacy_comment(
        657,
        '{"issue_number": 999, "role": "executor", "action": "merge-pr", '
        '"result_content": "unterminated',
    )
    obsolete_identity = legacy_comment(
        658,
        json.dumps(
            {
                "issue_nuber": 998,
                "role": "executor",
                "action": "merge-pr",
                "result_content": "obsolete action vocabulary",
                "requested_effects": [],
            }
        ),
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [malformed_json, obsolete_identity]
        if path.startswith("issues/138/comments?"):
            return []
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_truncated_legacy_encoded_source_is_filtered_before_frontier_read() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    raw_worker_result = json.dumps(
        {
            "issue_number": 999,
            "role": "lead",
            "action": "explore-change",
            "result_content": "historical payload " + ("x" * 7000),
            "requested_effects": [],
        },
        separators=(",", ":"),
    )
    encoded = base64.b64encode(raw_worker_result.encode("utf-8")).decode("ascii")
    truncated = encoded[:160] + "..."
    unrelated = {
        "id": 659,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                "Dispatch-Request-Comment-ID: 100",
                "Dispatch-Decision-Comment-ID: 200",
                f"Worker-Result-B64: {truncated}",
            )
        ),
        "created_at": "2026-09-17T12:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [unrelated]
        if path.startswith("issues/138/comments?"):
            return []
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_preactivation_ingress_before_routing_admission_is_historical() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    historical = _effect_request_comment(
        comment_id=653,
        created_at="2026-09-17T23:59:59Z",
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [historical]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_unbound_terminal_transport_is_inert_history() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    unbound = {
        "id": 654,
        "body": "EFFECT_REQUEST\nlegacy malformed transport",
        "created_at": "2026-09-18T01:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [unbound]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9654,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 1,
                    }
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/9654/jobs":
            return {
                "jobs": [
                    {
                        "id": 9754,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion("NONE", "application-completion-none")


def test_unbound_live_transport_blocks_without_source_ownership() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    unbound = {
        "id": 655,
        "body": "EFFECT_REQUEST\nlegacy malformed transport",
        "created_at": "2026-09-18T01:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [unbound]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9655,
                        "display_title": "Scheduled Agent Application 655",
                        "status": "in_progress",
                        "run_attempt": 1,
                    }
                ]
            }
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion(
        "INVALID",
        "application-completion-unbound-transport-unresolved",
    )


def test_raw_current_source_request_is_classified_after_source_binding() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = {
        "id": 656,
        "body": "\n".join(
            (
                "EFFECT_REQUEST",
                "Workflow: #138",
                "Action: explore-change",
                "Worker-Result: legacy raw payload",
            )
        ),
        "created_at": "2026-09-18T01:00:00Z",
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 9656,
                        "display_title": "Scheduled Agent Application 656",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 1,
                    }
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/9656/jobs":
            return {
                "jobs": [
                    {
                        "id": 9756,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion(
        "REJECTED",
        "application-completion-terminal-no-accept",
        request_comment_id=656,
    )


def test_same_source_malformed_legacy_request_still_fails_closed() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    malformed = _effect_request_comment(
        comment_id=653,
        created_at="2026-09-18T00:59:00Z",
    )
    body = malformed["body"]
    assert isinstance(body, str)
    encoded = body.splitlines()[2].removeprefix("Worker-Result-B64: ")
    malformed["body"] = "\n".join(
        (
            "EFFECT_REQUEST",
            "Dispatch-Request-Comment-ID: 100",
            "Dispatch-Run-ID: 200",
            f"Worker-Result-B64: {encoded}",
        )
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [malformed]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": []}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-preaccept-evidence-unknown"


def test_protocol_request_without_acceptance_returns_source_ownership() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-19T06:08:00Z",
        authorization_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
    )

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return []
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": []}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=fake_read,
        now=datetime(2026, 9, 19, 7, 0, tzinfo=UTC),
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-preaccept-evidence-unknown"


def test_preprotocol_inert_request_is_retired_without_semantic_replay() -> None:
    source = bridge.WorkerRequest(234, "lead", "resolve-question")
    legacy_revision = "6ffd99baee9289090b5c2178a5ce6801d8f1f335"
    change = "source-decision-explore-materialization"
    request = _effect_request_comment(
        comment_id=5729806158,
        created_at="2026-09-18T12:09:34Z",
        action="resolve-question",
        role="lead",
        result_kind="ready-for-openspec-review",
        issue_number=234,
        change=change,
        authorization_revision=legacy_revision,
    )
    issue = {
        "number": 234,
        "state": "open",
        "created_at": "2026-09-09T10:59:41Z",
        "closed_at": None,
        "labels": [{"name": "action:resolve-question"}],
        "body": f"Change: {change}",
    }
    predecessor = {
        "id": 10,
        "body": "\n".join(
            (
                "ACTION_RESULT",
                "Workflow: #234",
                f"Change: {change}",
                "Role: executor",
                "Action: implement-change",
                "Result: SPEC_BLOCKER",
                f"Revision: {bridge._APPLICATION_DECISION_PROTOCOL_REVISION}",
                f"Default-Branch-Revision: {bridge._APPLICATION_DECISION_PROTOCOL_REVISION}",
                "Application-Correlation: "
                f"application:1:234:{change}:executor:implement-change:spec-blocker:"
                f"{bridge._APPLICATION_DECISION_PROTOCOL_REVISION}",
                "Repository-derived successor: Lead / resolve-question",
            )
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    predecessor_timeline = [
        {"id": 10, "event": "commented", "created_at": "2026-09-18T12:00:00Z"},
        {
            "id": 11,
            "event": "unlabeled",
            "created_at": "2026-09-18T12:00:01Z",
            "label": {"name": "action:implement-change"},
        },
        {
            "id": 12,
            "event": "labeled",
            "created_at": "2026-09-18T12:00:01Z",
            "label": {"name": "action:resolve-question"},
        },
    ]

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/234/comments?"):
            return [predecessor]
        if path.startswith("issues/234/timeline?"):
            return predecessor_timeline
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 5729806158",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 1,
                    }
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/777/jobs":
            return {
                "jobs": [
                    {
                        "id": 888,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        if path == f"compare/{legacy_revision}...{bridge._APPLICATION_DECISION_PROTOCOL_REVISION}":
            return {"status": "ahead", "base_commit": {"sha": legacy_revision}}
        if path == "issues/234":
            return issue
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=bridge._APPLICATION_DECISION_PROTOCOL_REVISION,
        read=fake_read,
        now=datetime(2026, 9, 19, 7, 0, tzinfo=UTC),
    )

    assert completion.state == "REJECTED"
    assert completion.reason == "application-completion-rejected"
    assert completion.request_comment_id == 5729806158


def test_one_accepted_intent_is_resumed_before_semantic_replay() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )
    decision = _application_decision_comment(request)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision]
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 654",
                        "status": "completed",
                        "run_attempt": 1,
                    }
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/777/jobs":
            return {"jobs": [{"id": 888, "name": "apply"}]}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-recovery-evidence-missing"
    assert completion.request_comment_id == 654
    assert completion.job_id is None


@pytest.mark.parametrize(
    (
        "current_action",
        "application_run_count",
        "accepted_decision_count",
        "trusted_accepted_decision",
        "expected",
    ),
    (
        (
            "propose-change",
            1,
            1,
            True,
            ("INVALID", "application-completion-recovery-evidence-missing"),
        ),
        (
            "propose-change",
            2,
            1,
            True,
            ("INVALID", "application-completion-run-identity-ambiguous"),
        ),
        (
            "propose-change",
            1,
            2,
            True,
            ("AMBIGUOUS", "application-completion-invalid-frontier-accepted-intents-ambiguous"),
        ),
        (
            "review-openspec",
            1,
            1,
            True,
            ("INVALID", "application-completion-current-frontier-invalid"),
        ),
        (
            "propose-change",
            1,
            1,
            False,
            ("INVALID", "application-completion-current-frontier-invalid"),
        ),
    ),
)
def test_current_accepted_application_stops_replaying_after_repeated_failed_attempt(
    current_action: str,
    application_run_count: int,
    accepted_decision_count: int,
    trusted_accepted_decision: bool,
    expected: tuple[str, str],
) -> None:
    """Stop replay after the exact production prefix has already been retried."""

    current_revision = "e617a05ada51af9ff8f20697bbf07c4bfc8ec19e"
    authorization_revision = "2e00e236f24ba41302c9ba18c685acdf4cebe4ed"
    source = bridge.WorkerRequest(322, "lead", "propose-change")

    def request(comment_id: int, action: str, result_kind: str) -> dict[str, object]:
        item = _effect_request_comment(
            comment_id=comment_id,
            created_at="2026-09-22T16:51:57Z",
            issue_number=322,
            action=action,
            role="lead",
            result_kind=result_kind,
            authorization_revision=authorization_revision,
        )
        body = cast(str, item["body"])
        lines = body.splitlines()
        raw = base64.b64decode(lines[2].removeprefix("Worker-Result-B64: ")).decode("utf-8")
        worker = json.loads(raw)
        worker["_semantic_intent_version"] = 2
        encoded = base64.b64encode(
            json.dumps(worker, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        item["body"] = "\n".join((lines[0], lines[1], f"Worker-Result-B64: {encoded}"))
        return item

    explore_request = request(5780481954, "explore-change", "proposal-ready")
    explore_decision = _application_decision_comment(
        explore_request,
        comment_id=5780489187,
    )
    explore_decision["created_at"] = "2026-09-22T16:52:28Z"
    explore_result = _formal_frontier_comment(
        5780489851,
        action="explore-change",
        role="lead",
        result="proposal-ready",
        successor="Lead / propose-change",
        request_id=5780481954,
        change="unset",
        issue_number=322,
        revision=current_revision,
    )
    explore_result["created_at"] = "2026-09-22T16:52:31Z"

    accepted_request = request(5781255019, "propose-change", "ready-for-openspec-review")
    accepted_decision = _application_decision_comment(
        accepted_request,
        comment_id=5781260361,
    )
    accepted_decision["created_at"] = "2026-09-22T17:48:32Z"
    if not trusted_accepted_decision:
        accepted_decision["user"] = {"login": "attacker"}
        accepted_decision.pop("performed_via_github_app", None)
    # This is the observed current GitHub ACTION_RESULT: its application
    # correlation is absent, so it cannot qualify the accepted intent.
    uncorrelated_result = {
        "id": 5781309198,
        "created_at": "2026-09-22T17:52:19Z",
        "body": "\n".join(
            (
                "ACTION_RESULT",
                "Workflow: #322",
                "Change: unset",
                "Role: lead",
                "Action: propose-change",
                "Result: READY_FOR_OPENSPEC_REVIEW",
                f"Revision: {current_revision}",
                f"Default-Branch-Revision: {current_revision}",
                "Evidence: ACTION_RESULT Workflow: #322 Change: unset",
            )
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    issue = {
        "number": 322,
        "title": "Explore restoring NO_WORK idle discovery after Action-only dispatch",
        "state": "open",
        "created_at": "2026-09-22T15:39:54Z",
        "closed_at": None,
        "labels": [{"name": f"action:{current_action}"}],
        "body": "Change: unset",
    }
    lifecycle = [
        {
            "id": 31612089246,
            "event": "labeled",
            "created_at": "2026-09-22T15:39:56Z",
            "label": {"name": "action:explore-change"},
        },
        {"id": 5780489187, "event": "commented", "created_at": "2026-09-22T16:52:28Z"},
        {"id": 5780489851, "event": "commented", "created_at": "2026-09-22T16:52:31Z"},
        {
            "id": 31616529231,
            "event": "unlabeled",
            "created_at": "2026-09-22T16:52:34Z",
            "label": {"name": "action:explore-change"},
        },
        {
            "id": 31616529287,
            "event": "labeled",
            "created_at": "2026-09-22T16:52:34Z",
            "label": {"name": "action:propose-change"},
        },
        {"id": 5781260361, "event": "commented", "created_at": "2026-09-22T17:48:32Z"},
        {"id": 5781309198, "event": "commented", "created_at": "2026-09-22T17:52:19Z"},
        {
            "id": 31620014721,
            "event": "unlabeled",
            "created_at": "2026-09-22T17:52:21Z",
            "label": {"name": "action:propose-change"},
        },
        {
            "id": 31620014750,
            "event": "labeled",
            "created_at": "2026-09-22T17:52:21Z",
            "label": {"name": "action:review-openspec"},
        },
        {
            "id": 31647225754,
            "event": "unlabeled",
            "created_at": "2026-09-23T03:05:36Z",
            "label": {"name": "action:review-openspec"},
        },
        {
            "id": 31647225775,
            "event": "labeled",
            "created_at": "2026-09-23T03:05:36Z",
            "label": {"name": "action:propose-change"},
        },
    ]

    issue_comment_list = [explore_decision, explore_result, accepted_decision, uncorrelated_result]
    if accepted_decision_count == 2:
        issue_comment_list.append(
            {
                **accepted_decision,
                "id": 5781260362,
                "created_at": "2026-09-22T17:48:33Z",
            }
        )
    application_run_reads = 0

    def fake_read(_repository: str, _token: str, path: str) -> object:
        nonlocal application_run_reads
        if path.startswith("issues/comments?"):
            return [explore_request, accepted_request]
        if path.startswith("issues/322/comments?"):
            return issue_comment_list
        if path == "issues/322":
            return issue
        if path.startswith("issues/322/timeline?"):
            return lifecycle
        if path.startswith("compare/"):
            base = path.removeprefix("compare/").split("...", 1)[0]
            return {"status": "ahead", "base_commit": {"sha": base}}
        if path.startswith("actions/workflows/"):
            application_run_reads += 1
            return {
                "workflow_runs": [
                    {
                        "id": 35762997171 + index,
                        "display_title": "Scheduled Agent Application 5781255019",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 6,
                    }
                    for index in range(application_run_count)
                ]
            }
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == "actions/runs/35762997171/jobs":
            return {"jobs": [{"id": 107028234822, "name": "apply"}]}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=current_revision,
        read=fake_read,
        now=datetime(2026, 9, 23, 4, 0, tzinfo=UTC),
    )

    assert (completion.state, completion.reason) == expected
    if expected[0] == "RESUMABLE":
        assert completion.request_comment_id == 5781255019
        assert completion.job_id == 107028234822
    elif expected[1] in {
        "application-completion-run-identity-ambiguous",
        "application-completion-rerun-limit",
        "application-completion-continuation-required",
        "application-completion-recovery-evidence-missing",
    }:
        assert application_run_reads > 0
    else:
        assert application_run_reads == 0


def test_live_322_accepted_request_does_not_resume_completed_failed_application_job() -> None:
    """A repeated #322 application attempt must stop the scheduled retry loop."""

    fixture_path = Path(__file__).parent / "fixtures" / "issue322-application-recovery.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    revision = cast(str, fixture["source_revision"])
    request = cast(dict[str, object], fixture["request_comment"])
    issue = cast(dict[str, object], fixture["issue"])
    issue_comments = cast(list[dict[str, object]], fixture["issue_comments"])
    lifecycle = cast(list[dict[str, object]], fixture["timeline"])
    comparisons = cast(dict[str, dict[str, object]], fixture["comparisons"])
    run = cast(dict[str, object], fixture["application_run"])
    job = cast(dict[str, object], fixture["application_job"])
    request_id = cast(int, request["id"])
    run_id = cast(int, run["id"])
    job_id = cast(int, job["id"])
    source = bridge.WorkerRequest(322, "lead", "resolve-question")
    observed: list[str] = []

    def fake_read(_repository: str, _token: str, path: str) -> object:
        observed.append(path)
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/322/comments?"):
            return issue_comments
        if path == "issues/322":
            return issue
        if path.startswith("issues/322/timeline?"):
            return lifecycle
        if path.startswith("compare/"):
            base = path.removeprefix("compare/").split("...", 1)[0]
            if base == revision:
                return {
                    "status": "identical",
                    "base_commit": {"sha": revision},
                    "ahead_by": 0,
                    "behind_by": 0,
                    "files": [],
                }
            return comparisons[base]
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": [run]}
        if path.endswith("/artifacts?per_page=100"):
            return {"total_count": 0, "artifacts": []}
        if path == f"actions/runs/{run_id}/jobs":
            return {"jobs": [job]}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "royhsu-work/investment-strategy",
        "fixture",
        source=source,
        current_revision=revision,
        read=fake_read,
        now=datetime(2026, 9, 24, 13, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion(
        "INVALID",
        "application-completion-recovery-evidence-missing",
        request_comment_id=request_id,
    )
    assert request_id == 5810765007
    assert run_id == 35976411803
    assert job_id == 107664011251
    assert run["run_attempt"] == 7
    assert any(path.startswith("actions/workflows/") for path in observed)
    assert f"actions/runs/{run_id}/jobs" in observed


def test_new_evidence_continues_past_the_former_attempt_threshold() -> None:
    source = bridge.WorkerRequest(322, "lead", "resolve-question")
    request = _effect_request_comment(
        comment_id=5810765007,
        created_at="2026-09-23T03:00:00Z",
        issue_number=322,
        action=source.action,
        role=source.role,
        result_kind="ready-for-openspec-review",
    )
    decision = _application_decision_comment(request, comment_id=5810765008)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/322/comments?"):
            return [decision]
        raise AssertionError(path)

    accepted_sha256 = hashlib.sha256(cast(str, decision["body"]).encode("utf-8")).hexdigest()
    predecessor = bridge.ApplicationRecoveryArtifact(
        run_id=7001,
        run_attempt=1,
        job_id=7002,
        artifact_id=7003,
        artifact_digest="sha256:" + "1" * 64,
        request_comment_id=5810765007,
        accepted_decision_sha256=accepted_sha256,
        failure_evidence_sha256="2" * 64,
        recovery_episode_sha256="3" * 64,
        recovery_attempt=4,
        continuation_eligible=True,
        document={"prior_failure_evidence_sha256": ["6" * 64, "7" * 64, "8" * 64]},
    )
    body = bridge._application_continuation_body(
        repository="owner/repo",
        token=REVISION,
        source=source,
        request_comment_id=5810765007,
        predecessor_evidence=predecessor,
        read=fake_read,
    )

    assert body is not None
    parsed = bridge.parse_application_continuation_request(body)
    assert parsed is not None
    assert parsed.issue_number == source.issue_number
    assert parsed.original_request_comment_id == 5810765007
    assert (
        parsed.accepted_decision_sha256
        == hashlib.sha256(cast(str, decision["body"]).encode("utf-8")).hexdigest()
    )

    repeated = bridge.ApplicationRecoveryArtifact(
        run_id=7002,
        run_attempt=1,
        job_id=7003,
        artifact_id=7004,
        artifact_digest="sha256:" + "4" * 64,
        request_comment_id=5810765007,
        accepted_decision_sha256=accepted_sha256,
        failure_evidence_sha256="2" * 64,
        recovery_episode_sha256="3" * 64,
        recovery_attempt=5,
        continuation_eligible=True,
        document={"prior_failure_evidence_sha256": ["6" * 64, "7" * 64, "8" * 64, "2" * 64]},
    )
    assert (
        bridge._application_continuation_body(
            repository="owner/repo",
            token=REVISION,
            source=source,
            request_comment_id=5810765007,
            predecessor_evidence=repeated,
            read=fake_read,
        )
        is None
    )


def test_rejected_intent_returns_ownership_to_later_semantic_dispatch() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    request = _effect_request_comment(
        comment_id=654,
        created_at="2026-09-18T01:00:00Z",
    )
    decision = _application_decision_comment(request, disposition="REJECTED")

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision]
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "REJECTED"
    assert completion.reason == "application-completion-rejected"


def test_distinct_accepted_requests_never_alias_by_equal_payload() -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    requests = [
        _effect_request_comment(
            comment_id=654,
            created_at="2026-09-18T01:00:00Z",
        ),
        _effect_request_comment(
            comment_id=655,
            created_at="2026-09-18T01:01:00Z",
        ),
    ]
    decisions = [
        _application_decision_comment(requests[0], comment_id=700),
        _application_decision_comment(requests[1], comment_id=701),
    ]

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return requests
        if path.startswith("issues/138/comments?"):
            return decisions
        if path == "issues/138":
            return _current_source_issue()
        if path.startswith("issues/138/timeline?"):
            return _preactivation_admission()
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=fake_read,
        now=datetime(2026, 9, 18, 2, 0, tzinfo=UTC),
    )

    assert completion.state == "AMBIGUOUS"
    assert completion.reason == "application-completion-accepted-ambiguous"


def test_completed_formal_result_uses_fresh_revision_for_postconditions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(138, "reviewer", "review-archive")
    formal_evidence_revision = "b" * 40
    application_observation_revision = "c" * 40
    advanced_revision = "a" * 40
    change = "formal-result-observation-revision"
    request = _effect_request_comment(
        comment_id=90,
        created_at="2026-09-18T02:00:00Z",
        action="finalize-change",
        role="lead",
        result_kind="archive-ready",
        issue_number=138,
        change=change,
        authorization_revision=REVISION,
    )
    decision = _application_decision_comment(request, comment_id=91)
    formal = _formal_frontier_comment(
        100,
        action="finalize-change",
        role="lead",
        result="archive-ready",
        successor="Reviewer / review-archive",
        request_id=90,
        change=change,
    )
    body = str(formal["body"])
    formal["body"] = (
        body.replace(f"Revision: {REVISION}", f"Revision: {formal_evidence_revision}")
        .replace(
            f"Default-Branch-Revision: {REVISION}",
            f"Default-Branch-Revision: {formal_evidence_revision}",
        )
        .replace(
            f":{REVISION}\nRepository-derived successor:",
            f":{application_observation_revision}\nRepository-derived successor:",
        )
    )
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:review-archive"}],
        "body": f"Change: {change}",
    }
    observed_revisions: list[str] = []

    def fake_postconditions(*_args: object, **kwargs: object) -> bool:
        revision = cast(str, kwargs["current_revision"])
        observed_revisions.append(revision)
        return revision == application_observation_revision

    monkeypatch.setattr(bridge, "consequence_postconditions_complete", fake_postconditions)

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision, formal]
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return _frontier_lifecycle([(100, "finalize-change", "review-archive")])
        if path in {
            f"compare/{REVISION}...{advanced_revision}",
            f"compare/{formal_evidence_revision}...{advanced_revision}",
            f"compare/{application_observation_revision}...{advanced_revision}",
        }:
            base_sha = path.removeprefix("compare/").split("...")[0]
            return {"status": "ahead", "base_commit": {"sha": base_sha}}
        raise AssertionError(path)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=advanced_revision,
        read=fake_read,
        now=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )

    assert completion == bridge.ApplicationCompletion(
        "NONE",
        "application-completion-none",
    )
    assert observed_revisions == [advanced_revision]


def _carrier_plan_fixture(authorization_revision: str = REVISION) -> carrier.CarrierPlan:
    return carrier.make_carrier_plan(
        repository="owner/repo",
        issue_number=322,
        change="restore-no-work-idle-discovery",
        action="implement-change",
        authorization_revision=authorization_revision,
        operation="pull-request-head-update",
        target={
            "repository": "owner/repo",
            "pull_request_number": 353,
            "ref": "refs/heads/agent/change",
        },
        expected={"ref_sha": "a" * 40},
        requested={
            "ref": "refs/heads/agent/change",
            "sha": "b" * 40,
            "force": False,
        },
        expected_postcondition={
            "ref": "refs/heads/agent/change",
            "ref_sha": "b" * 40,
            "pull_request_number": 353,
            "pull_request_head_sha": "b" * 40,
        },
    )


def _accepted_carrier_record() -> bridge.ApplicationDecisionRecord:
    return bridge.ApplicationDecisionRecord(
        request_comment_id=90,
        request_body_sha256="1" * 64,
        authorization_revision=REVISION,
        issue_number=322,
        role="executor",
        action="implement-change",
        change="restore-no-work-idle-discovery",
        result_kind="more-implementation-required",
        disposition="ACCEPTED",
        worker_result_sha256="2" * 64,
        raw_worker_result="{}",
        reason="application accepted",
    )


def _qualified_recovery_fixture(
    *,
    accepted_decision_sha256: str = "a" * 64,
    run_id: int = 777,
    run_attempt: int = 1,
    job_id: int = 888,
    artifact_id: int = 999,
    request_comment_id: int = 90,
    recovery_attempt: int = 1,
    continuation_eligible: bool = True,
    prior_failures: tuple[str, ...] = (),
) -> bridge.ApplicationRecoveryArtifact:
    return bridge.ApplicationRecoveryArtifact(
        run_id=run_id,
        run_attempt=run_attempt,
        job_id=job_id,
        artifact_id=artifact_id,
        artifact_digest="sha256:" + "3" * 64,
        request_comment_id=request_comment_id,
        accepted_decision_sha256=accepted_decision_sha256,
        failure_evidence_sha256="4" * 64,
        recovery_episode_sha256="5" * 64,
        recovery_attempt=recovery_attempt,
        continuation_eligible=continuation_eligible,
        document={"prior_failure_evidence_sha256": list(prior_failures)},
    )


def _trusted_connector_comment(comment_id: int, body: str) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": "owner"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }


def _carrier_outcome_fixture(
    plan: carrier.CarrierPlan,
    recovery: bridge.ApplicationRecoveryArtifact,
    *,
    carrier_artifact_id: int,
    carrier_artifact_digest: str,
    outcome: Literal["COMPLETE", "REFUSED"] = "COMPLETE",
) -> carrier.CarrierOutcomeReport:
    complete = outcome == "COMPLETE"
    return carrier.CarrierOutcomeReport(
        repository="owner/repo",
        issue_number=322,
        request_comment_id=90,
        accepted_decision_sha256=recovery.accepted_decision_sha256,
        continuation_correlation=bridge.application_continuation_correlation(
            "owner/repo",
            322,
            90,
            recovery.accepted_decision_sha256,
            recovery.run_id,
            recovery.run_attempt,
            recovery.job_id,
            recovery.artifact_id,
            recovery.artifact_digest,
            recovery.failure_evidence_sha256,
            recovery.recovery_episode_sha256,
        ),
        predecessor_run_id=recovery.run_id,
        predecessor_run_attempt=recovery.run_attempt,
        predecessor_job_id=recovery.job_id,
        recovery_artifact_id=recovery.artifact_id,
        recovery_artifact_digest=recovery.artifact_digest,
        failure_evidence_sha256=recovery.failure_evidence_sha256,
        recovery_episode_sha256=recovery.recovery_episode_sha256,
        carrier_artifact_id=carrier_artifact_id,
        carrier_artifact_digest=carrier_artifact_digest,
        plan_id=plan.plan_id,
        operation=plan.operation,
        outcome=outcome,
        mutation_status="COMPLETED" if complete else "NO_WRITE",
        precondition="MATCH",
        observed_precondition_json=json.dumps(
            dict(plan.expected), sort_keys=True, separators=(",", ":")
        ),
        postcondition="COMPLETE" if complete else "INCOMPLETE",
        unfinished_boundary="none" if complete else "carrier-operation",
        failure_code="none" if complete else "connector-refused",
        failure_summary="none" if complete else "connector refused",
    )


def _carrier_dispatch_result_bytes(
    qualified: carrier.QualifiedCarrierPlan,
    *,
    request_comment_id: int = 91,
) -> bytes:
    continuation = bridge.render_application_continuation_request(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=90,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=777,
        predecessor_run_attempt=1,
        predecessor_job_id=888,
        predecessor_artifact_id=997,
        predecessor_artifact_digest="sha256:" + "3" * 64,
        failure_evidence_sha256="4" * 64,
        recovery_episode_sha256="5" * 64,
    )
    payload = {
        "schema": bridge.DISPATCH_RESULT_SCHEMA,
        "request_comment_id": request_comment_id,
        "default_branch_revision": REVISION,
        "disposition": "FAIL_CLOSED",
        "reason": "application-completion-carrier-required",
        "application_continuation": continuation,
        "qualified_carrier": carrier.qualified_carrier_document(qualified),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _carrier_completion_reader(
    *,
    carrier_digest: str,
    dispatch_bytes: bytes | None = None,
) -> bridge.GitHubReader:
    dispatch_digest = (
        None if dispatch_bytes is None else f"sha256:{hashlib.sha256(dispatch_bytes).hexdigest()}"
    )

    def read(_repository: str, _token: str, path: str) -> object:
        if path == f"compare/{REVISION}...{REVISION}":
            return {"status": "identical", "base_commit": {"sha": REVISION}}
        if path.startswith("actions/workflows/scheduled-agent-application.yml/runs?"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 90",
                        "status": "completed",
                        "run_attempt": 1,
                        "head_sha": REVISION,
                    }
                ]
            }
        if path == "actions/runs/777/jobs":
            return {
                "jobs": [
                    {
                        "id": 888,
                        "name": "apply",
                        "steps": [
                            {
                                "name": "Upload exact external carrier plan",
                                "conclusion": "success",
                            }
                        ],
                    }
                ]
            }
        if path == "actions/runs/777/artifacts?per_page=100":
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 999,
                        "name": "carrier-plan.json",
                        "expired": False,
                        "digest": carrier_digest,
                        "workflow_run": {"id": 777, "head_sha": REVISION},
                    }
                ],
            }
        if path.startswith("actions/workflows/scheduled-agent-bridge.yml/runs?"):
            if dispatch_bytes is None:
                return {"workflow_runs": []}
            return {
                "workflow_runs": [
                    {
                        "id": 555,
                        "display_title": "Scheduled Agent Dispatch 91",
                        "status": "completed",
                        "conclusion": "success",
                        "head_sha": REVISION,
                    }
                ]
            }
        if path == "actions/runs/555/artifacts?per_page=100" and dispatch_bytes is not None:
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 556,
                        "name": "dispatch-result.json",
                        "expired": False,
                        "digest": dispatch_digest,
                        "workflow_run": {"id": 555, "head_sha": REVISION},
                    }
                ],
            }
        raise AssertionError(path)

    return read


@pytest.mark.parametrize(
    ("plan_revision", "ancestry_status", "eligible"),
    [
        (REVISION, "ahead", True),
        ("d" * 40, "ahead", True),
        ("d" * 40, "behind", False),
        ("d" * 40, None, False),
    ],
)
def test_completed_application_prefers_saved_qualified_carrier_over_producer_resume(
    monkeypatch: pytest.MonkeyPatch,
    plan_revision: str,
    ancestry_status: str | None,
    eligible: bool,
) -> None:
    plan = _carrier_plan_fixture(plan_revision)
    raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    digest = f"sha256:{hashlib.sha256(raw).hexdigest()}"

    def fake_read(_repository: str, _token: str, path: str) -> object:
        if path == f"compare/{REVISION}...{plan_revision}":
            return {"status": ancestry_status, "base_commit": {"sha": REVISION}}
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 777,
                        "display_title": "Scheduled Agent Application 90",
                        "status": "completed",
                        "run_attempt": 1,
                        "head_sha": REVISION,
                    }
                ]
            }
        if path == "actions/runs/777/jobs":
            return {
                "jobs": [
                    {
                        "id": 888,
                        "name": "apply",
                        "steps": [
                            {
                                "name": "Upload exact external carrier plan",
                                "conclusion": "success",
                            }
                        ],
                    }
                ]
            }
        if path == "actions/runs/777/artifacts?per_page=100":
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 999,
                        "name": "carrier-plan.json",
                        "expired": False,
                        "digest": digest,
                        "workflow_run": {"id": 777, "head_sha": REVISION},
                    }
                ],
            }
        raise AssertionError(path)

    recovery = _qualified_recovery_fixture()
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )
    monkeypatch.setattr(bridge, "read_github_artifact_bytes", lambda *_args: raw)
    completion = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=fake_read,
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
    )

    if not eligible:
        assert completion.state == "INVALID"
        assert completion.reason == "application-completion-carrier-evidence-invalid"
        assert completion.qualified_carrier is None
        assert completion.job_id is None
        return
    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-carrier-required"
    assert completion.job_id is None
    assert completion.qualified_carrier is not None
    assert completion.qualified_carrier.plan == plan
    assert completion.qualified_carrier.artifact_digest == digest


def test_completed_application_consumes_only_exact_complete_carrier_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _carrier_plan_fixture()
    carrier_raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    carrier_digest = f"sha256:{hashlib.sha256(carrier_raw).hexdigest()}"
    recovery = _qualified_recovery_fixture(artifact_id=997)
    report = _carrier_outcome_fixture(
        plan,
        recovery,
        carrier_artifact_id=999,
        carrier_artifact_digest=carrier_digest,
    )
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )
    previous_dispatch = _carrier_dispatch_result_bytes(qualified)
    comments = (
        _trusted_connector_comment(
            91,
            "DISPATCH_REQUEST\nRequested-At: 2026-10-08T05:49:00Z",
        ),
        _trusted_connector_comment(
            92,
            carrier.render_carrier_outcome_report(report),
        ),
    )
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )

    def read_artifact(_repository: str, _token: str, path: str) -> bytes:
        if path == "actions/artifacts/999/zip":
            return carrier_raw
        if path == "actions/artifacts/556/zip":
            return previous_dispatch
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "read_github_artifact_bytes", read_artifact)
    completion = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=_carrier_completion_reader(
            carrier_digest=carrier_digest,
            dispatch_bytes=previous_dispatch,
        ),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recent_comments=comments,
        current_dispatch_request_comment_id=100,
    )

    assert completion.state == "RESUMABLE"
    assert completion.reason == "application-completion-continuation-required"
    assert completion.qualified_carrier is None
    assert completion.recovery_artifact == recovery


def test_completed_application_blocks_a_previous_unreported_carrier_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _carrier_plan_fixture()
    carrier_raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    carrier_digest = f"sha256:{hashlib.sha256(carrier_raw).hexdigest()}"
    recovery = _qualified_recovery_fixture(artifact_id=997)
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )
    previous_dispatch = _carrier_dispatch_result_bytes(qualified)
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )

    def read_artifact(_repository: str, _token: str, path: str) -> bytes:
        if path == "actions/artifacts/999/zip":
            return carrier_raw
        if path == "actions/artifacts/556/zip":
            return previous_dispatch
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "read_github_artifact_bytes", read_artifact)
    completion = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=_carrier_completion_reader(
            carrier_digest=carrier_digest,
            dispatch_bytes=previous_dispatch,
        ),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recent_comments=(
            _trusted_connector_comment(
                91,
                "DISPATCH_REQUEST\nRequested-At: 2026-10-08T05:49:00Z",
            ),
        ),
        current_dispatch_request_comment_id=100,
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-carrier-outcome-missing"
    assert completion.qualified_carrier is None


def test_completed_application_blocks_refused_carrier_outcome_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _carrier_plan_fixture()
    carrier_raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    carrier_digest = f"sha256:{hashlib.sha256(carrier_raw).hexdigest()}"
    recovery = _qualified_recovery_fixture(artifact_id=997)
    report = _carrier_outcome_fixture(
        plan,
        recovery,
        carrier_artifact_id=999,
        carrier_artifact_digest=carrier_digest,
        outcome="REFUSED",
    )
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )
    monkeypatch.setattr(
        bridge,
        "read_github_artifact_bytes",
        lambda *_args: carrier_raw,
    )
    completion = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=_carrier_completion_reader(carrier_digest=carrier_digest),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recent_comments=(
            _trusted_connector_comment(
                92,
                carrier.render_carrier_outcome_report(report),
            ),
        ),
        current_dispatch_request_comment_id=100,
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-carrier-outcome-incomplete"
    assert completion.qualified_carrier is None


def test_completed_application_distinguishes_absent_from_incomplete_carrier_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _accepted_carrier_record()
    recovery = _qualified_recovery_fixture(
        recovery_attempt=4,
        prior_failures=("6" * 64, "7" * 64, "8" * 64),
    )
    monkeypatch.setattr(
        bridge,
        "read_application_recovery_artifact",
        lambda *_args, **_kwargs: recovery,
    )

    def reader(total_count: int) -> bridge.GitHubReader:
        def fake_read(_repository: str, _token: str, path: str) -> object:
            if path.startswith("actions/workflows/"):
                return {
                    "workflow_runs": [
                        {
                            "id": 777,
                            "display_title": "Scheduled Agent Application 90",
                            "status": "completed",
                            "run_attempt": 50,
                            "head_sha": REVISION,
                        }
                    ]
                }
            if path == "actions/runs/777/jobs":
                return {"jobs": [{"id": 888, "name": "apply"}]}
            if path == "actions/runs/777/artifacts?per_page=100":
                return {"total_count": total_count, "artifacts": []}
            raise AssertionError(path)

        return fake_read

    absent = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=reader(0),
        record=record,
        accepted_decision_sha256="a" * 64,
    )
    incomplete = bridge._application_job(
        "owner/repo",
        "token",
        90,
        read=reader(1),
        record=record,
        accepted_decision_sha256="a" * 64,
    )

    assert (absent.state, absent.reason, absent.job_id) == (
        "RESUMABLE",
        "application-completion-continuation-required",
        None,
    )
    assert (incomplete.state, incomplete.reason) == (
        "INVALID",
        "application-completion-carrier-evidence-invalid",
    )


def test_qualified_carrier_consumer_executes_connector_and_skips_complete() -> None:
    plan = _carrier_plan_fixture()
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest="sha256:" + "3" * 64,
        plan=plan,
    )
    remote = {"sha": "a" * 40}
    calls: list[str] = []

    def qualify(_qualified: carrier.QualifiedCarrierPlan) -> carrier.CarrierQualification:
        return "COMPLETE" if remote["sha"] == "b" * 40 else "ELIGIBLE"

    def connector(exact_plan: carrier.CarrierPlan) -> None:
        calls.append(exact_plan.plan_id)
        remote["sha"] = cast(str, exact_plan.requested["sha"])

    assert (
        carrier.consume_qualified_carrier(qualified, qualify=qualify, connector=connector)
        == "executed-complete"
    )
    assert calls == [plan.plan_id]
    assert (
        carrier.consume_qualified_carrier(qualified, qualify=qualify, connector=connector)
        == "already-complete"
    )
    assert calls == [plan.plan_id]


def test_qualified_carrier_consumer_reconciles_lost_response_without_resend() -> None:
    plan = _carrier_plan_fixture()
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest="sha256:" + "4" * 64,
        plan=plan,
    )
    remote = {"sha": "a" * 40}
    calls = 0

    def qualify(_qualified: carrier.QualifiedCarrierPlan) -> carrier.CarrierQualification:
        return "COMPLETE" if remote["sha"] == "b" * 40 else "ELIGIBLE"

    def connector(exact_plan: carrier.CarrierPlan) -> None:
        nonlocal calls
        calls += 1
        remote["sha"] = cast(str, exact_plan.requested["sha"])
        raise TimeoutError("response lost after server write")

    assert (
        carrier.consume_qualified_carrier(qualified, qualify=qualify, connector=connector)
        == "reconciled-complete"
    )
    assert calls == 1


def test_carrier_outcome_report_round_trips_exact_lineage() -> None:
    report = carrier.CarrierOutcomeReport(
        repository="owner/repo",
        issue_number=322,
        request_comment_id=90,
        accepted_decision_sha256="a" * 64,
        continuation_correlation="b" * 64,
        predecessor_run_id=777,
        predecessor_run_attempt=1,
        predecessor_job_id=888,
        recovery_artifact_id=997,
        recovery_artifact_digest="sha256:" + "3" * 64,
        failure_evidence_sha256="4" * 64,
        recovery_episode_sha256="5" * 64,
        carrier_artifact_id=999,
        carrier_artifact_digest="sha256:" + "6" * 64,
        plan_id=_carrier_plan_fixture().plan_id,
        operation="pull-request-head-update",
        outcome="COMPLETE",
        mutation_status="COMPLETED",
        precondition="MATCH",
        observed_precondition_json=json.dumps(
            dict(_carrier_plan_fixture().expected), sort_keys=True, separators=(",", ":")
        ),
        postcondition="COMPLETE",
        unfinished_boundary="none",
        failure_code="none",
        failure_summary="none",
    )

    body = carrier.render_carrier_outcome_report(report)

    assert body.splitlines()[0] == "APPLICATION_CARRIER_OUTCOME"
    assert carrier.parse_carrier_outcome_report(body) == report


def test_carrier_outcome_report_rejects_malformed_evidence_and_parses_shape_only() -> None:
    report = carrier.CarrierOutcomeReport(
        repository="owner/repo",
        issue_number=322,
        request_comment_id=90,
        accepted_decision_sha256="a" * 64,
        continuation_correlation="b" * 64,
        predecessor_run_id=777,
        predecessor_run_attempt=1,
        predecessor_job_id=888,
        recovery_artifact_id=997,
        recovery_artifact_digest="sha256:" + "3" * 64,
        failure_evidence_sha256="4" * 64,
        recovery_episode_sha256="5" * 64,
        carrier_artifact_id=999,
        carrier_artifact_digest="sha256:" + "6" * 64,
        plan_id=_carrier_plan_fixture().plan_id,
        operation="pull-request-head-update",
        outcome="COMPLETE",
        mutation_status="COMPLETED",
        precondition="MATCH",
        observed_precondition_json=json.dumps(
            dict(_carrier_plan_fixture().expected), sort_keys=True, separators=(",", ":")
        ),
        postcondition="COMPLETE",
        unfinished_boundary="none",
        failure_code="none",
        failure_summary="none",
    )
    body = carrier.render_carrier_outcome_report(report)

    assert carrier.parse_carrier_outcome_report(body + "\n") is None
    assert (
        carrier.parse_carrier_outcome_report(
            body.replace("Postcondition: COMPLETE", "Postcondition: UNKNOWN")
        )
        is None
    )
    other_repository_body = body.replace("Repository: owner/repo", "Repository: other/repo")
    assert carrier.parse_carrier_outcome_report(other_repository_body) is not None

    short_report = replace(report, observed_precondition_json='{"a":1}')
    short_body = carrier.render_carrier_outcome_report(short_report)
    encoded_line = next(
        line
        for line in short_body.splitlines()
        if line.startswith("Observed-Precondition-JSON-B64: ")
    )
    encoded = encoded_line.removeprefix("Observed-Precondition-JSON-B64: ")
    assert len(encoded) % 4 == 2
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    final_index = alphabet.index(encoded[-1])
    noncanonical_index = (final_index & 0b110000) | ((final_index + 1) & 0b001111)
    noncanonical = encoded[:-1] + alphabet[noncanonical_index]
    padding = "=" * (-len(encoded) % 4)
    assert base64.urlsafe_b64decode(encoded + padding) == base64.urlsafe_b64decode(
        noncanonical + padding
    )
    assert (
        carrier.parse_carrier_outcome_report(
            short_body.replace(encoded_line, encoded_line.removesuffix(encoded) + noncanonical)
        )
        is None
    )


def test_carrier_documents_reject_tampering_and_dispatch_round_trips_handoff() -> None:
    plan = _carrier_plan_fixture()
    document = carrier.carrier_plan_document(plan)
    tampered = dict(document)
    tampered_requested = dict(cast(dict[str, object], document["requested"]))
    tampered_requested["sha"] = "c" * 40
    tampered["requested"] = tampered_requested
    with pytest.raises(ValueError, match="content address"):
        carrier.parse_carrier_plan_document(tampered)

    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest="sha256:" + "5" * 64,
        plan=plan,
    )
    continuation = bridge.render_application_continuation_request(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=90,
        accepted_decision_sha256="6" * 64,
        predecessor_run_id=7001,
        predecessor_run_attempt=1,
        predecessor_job_id=7002,
        predecessor_artifact_id=7003,
        predecessor_artifact_digest="sha256:" + "1" * 64,
        failure_evidence_sha256="2" * 64,
        recovery_episode_sha256="3" * 64,
    )
    failed = _decision("FAIL_CLOSED")
    failed = DispatchDecision(
        completeness=failed.completeness,
        observation_provenance=failed.observation_provenance,
        formal_issue_ids=failed.formal_issue_ids,
        preactivation_candidate_ids=failed.preactivation_candidate_ids,
        selected_issue_id=None,
        selected_routing=None,
        disposition="FAIL_CLOSED",
        reason="application-completion-carrier-required",
    )
    rendered = bridge.render_dispatch_result_document(
        request_comment_id=987,
        default_branch_revision=REVISION,
        decision=failed,
        application_continuation=continuation,
        qualified_carrier=qualified,
    )
    parsed = bridge.parse_dispatch_result_document(rendered)

    assert parsed.application_continuation == continuation
    assert parsed.qualified_carrier == qualified


def test_continuation_chain_selects_one_leaf_and_preserves_branches() -> None:
    latest_runs = (
        {
            "id": 700,
            "display_title": "Scheduled Agent Application 90",
            "run_attempt": 50,
        },
        {
            "id": 701,
            "display_title": "Scheduled Agent Application 101",
            "run_attempt": 1,
        },
        {
            "id": 702,
            "display_title": "Scheduled Agent Application 102",
            "run_attempt": 1,
        },
    )
    linear_leaf = bridge._continuation_leaf_comment_ids(
        request_comment_id=90,
        continuation_predecessors={101: (700, 1), 102: (701, 1)},
        workflow_runs=latest_runs,
    )
    assert linear_leaf == (102,)

    branched_leaves = bridge._continuation_leaf_comment_ids(
        request_comment_id=90,
        continuation_predecessors={101: (700, 50), 102: (700, 50)},
        workflow_runs=latest_runs,
    )
    assert branched_leaves == (101, 102)

    incomplete = bridge._continuation_leaf_comment_ids(
        request_comment_id=90,
        continuation_predecessors={101: (700, 1)},
        workflow_runs=(latest_runs[0],),
    )
    assert incomplete is None


def test_322_legacy_continuation_transports_are_not_new_failure_qualified_transitions() -> None:
    """Old continuation transports cannot qualify a new failure transition."""

    body = (
        "APPLICATION_CONTINUATION\n"
        "Issue: 322\n"
        "Original-Request-Comment: 6019133874\n"
        "Accepted-Decision-SHA256: "
        "9c545558249285ec6d4fa632970dfa7157774d75bf2b6e46889e240a175cbd54\n"
        "Continuation-Correlation: "
        "54ae08a7d74fc4a73820abce47a38c49b918827d905e1725b3cd9d869a41bb5a"
    )

    # Actual #364 and #365 comments use the same five-line legacy envelope.
    # Recognizing their run names is read-only historical reconstruction;
    # it cannot invent predecessor run/job, artifact, or fresh failure digest.
    for comment_id in (6029741785, 6047718564):
        title = f"Scheduled Agent Application {comment_id}"
        assert bridge.parse_application_run_name(title) == comment_id
        assert bridge.parse_application_continuation_request(body) is None

    assert (
        bridge._continuation_leaf_comment_ids(
            request_comment_id=6019133874,
            continuation_predecessors={},
            workflow_runs=(),
        )
        == ()
    )


def test_application_continuation_binds_exact_failure_transition() -> None:
    render = bridge.render_application_continuation_request
    first = render(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=987,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=12345,
        predecessor_run_attempt=2,
        predecessor_job_id=23456,
        predecessor_artifact_id=34567,
        predecessor_artifact_digest="sha256:" + "b" * 64,
        failure_evidence_sha256="c" * 64,
        recovery_episode_sha256="d" * 64,
    )
    duplicate = render(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=987,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=12345,
        predecessor_run_attempt=2,
        predecessor_job_id=23456,
        predecessor_artifact_id=34567,
        predecessor_artifact_digest="sha256:" + "b" * 64,
        failure_evidence_sha256="c" * 64,
        recovery_episode_sha256="d" * 64,
    )
    parsed = bridge.parse_application_continuation_request(first)

    assert first == duplicate
    assert parsed is not None
    assert getattr(parsed, "predecessor_run_id", None) == 12345
    assert getattr(parsed, "predecessor_run_attempt", None) == 2
    assert getattr(parsed, "predecessor_job_id", None) == 23456
    assert getattr(parsed, "predecessor_artifact_id", None) == 34567
    assert getattr(parsed, "predecessor_artifact_digest", None) == "sha256:" + "b" * 64
    assert getattr(parsed, "failure_evidence_sha256", None) == "c" * 64
    assert getattr(parsed, "recovery_episode_sha256", None) == "d" * 64

    next_body = render(
        repository="owner/repo",
        issue_number=322,
        original_request_comment_id=987,
        accepted_decision_sha256="a" * 64,
        predecessor_run_id=12346,
        predecessor_run_attempt=1,
        predecessor_job_id=23457,
        predecessor_artifact_id=34568,
        predecessor_artifact_digest="sha256:" + "e" * 64,
        failure_evidence_sha256="f" * 64,
        recovery_episode_sha256="d" * 64,
    )
    next_parsed = bridge.parse_application_continuation_request(next_body)

    assert next_body != first
    assert next_parsed is not None
    assert getattr(next_parsed, "recovery_episode_sha256", None) == getattr(
        parsed, "recovery_episode_sha256", None
    )
    assert getattr(next_parsed, "continuation_correlation", None) != getattr(
        parsed, "continuation_correlation", None
    )


def test_unreported_carrier_handoff_is_found_before_later_noncarrier_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _carrier_plan_fixture()
    carrier_raw = json.dumps(
        carrier.carrier_plan_document(plan),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    carrier_digest = f"sha256:{hashlib.sha256(carrier_raw).hexdigest()}"
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )
    older_result = _carrier_dispatch_result_bytes(
        qualified,
        request_comment_id=91,
    )
    newer_result = bridge.render_dispatch_result_document(
        request_comment_id=98,
        default_branch_revision=REVISION,
        decision=_decision("FAIL_CLOSED"),
    ).encode("utf-8")
    artifacts = {
        5601: older_result,
        5602: newer_result,
    }
    digests = {
        artifact_id: f"sha256:{hashlib.sha256(raw).hexdigest()}"
        for artifact_id, raw in artifacts.items()
    }

    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("actions/workflows/scheduled-agent-bridge.yml/runs?"):
            return {
                "workflow_runs": [
                    {
                        "id": 555,
                        "display_title": bridge.render_dispatch_run_name(91),
                        "status": "completed",
                        "head_sha": REVISION,
                    },
                    {
                        "id": 558,
                        "display_title": bridge.render_dispatch_run_name(98),
                        "status": "completed",
                        "head_sha": REVISION,
                    },
                ]
            }
        if path == "actions/runs/555/artifacts?per_page=100":
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 5601,
                        "name": "dispatch-result.json",
                        "expired": False,
                        "digest": digests[5601],
                        "workflow_run": {"id": 555, "head_sha": REVISION},
                    }
                ],
            }
        if path == "actions/runs/558/artifacts?per_page=100":
            return {
                "total_count": 1,
                "artifacts": [
                    {
                        "id": 5602,
                        "name": "dispatch-result.json",
                        "expired": False,
                        "digest": digests[5602],
                        "workflow_run": {"id": 558, "head_sha": REVISION},
                    }
                ],
            }
        raise AssertionError(path)

    monkeypatch.setattr(
        bridge,
        "read_github_artifact_bytes",
        lambda _repository, _token, path: artifacts[int(path.split("/")[2])],
    )
    status = bridge._prior_dispatch_handoff_reason(
        "owner/repo",
        "token",
        recent_comments=(
            _trusted_connector_comment(91, REQUEST_BODY),
            _trusted_connector_comment(98, REQUEST_BODY),
        ),
        owner="owner",
        current_dispatch_request_comment_id=100,
        plan_id=plan.plan_id,
        read=read,
    )

    assert status == "application-completion-carrier-outcome-missing"


def test_qualifier_uses_full_runtime_shard_history_for_prior_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = bridge.WorkerRequest(138, "lead", "explore-change")
    change = "runtime-shard-history-beyond-thirty-days"
    request = _effect_request_comment(
        comment_id=102,
        created_at="2026-09-18T01:00:00Z",
        action="explore-change",
        role="lead",
        issue_number=138,
        change=change,
    )
    decision = _application_decision_comment(request, comment_id=103)
    issue = {
        **_current_source_issue(),
        "labels": [{"name": "action:explore-change"}],
        "body": f"Change: {change}",
    }
    first_page = [
        {
            "id": comment_id,
            "body": "unrelated runtime comment",
            "created_at": "2026-06-01T00:00:00Z",
            "user": {"login": "human"},
        }
        for comment_id in range(1, 101)
    ]
    older_request = {
        **_trusted_connector_comment(
            101,
            "DISPATCH_REQUEST\nRequested-At: 2026-07-01T00:00:00Z",
        ),
        "created_at": "2026-07-01T00:00:00Z",
    }
    current_request = _trusted_connector_comment(
        104,
        "DISPATCH_REQUEST\nRequested-At: 2026-10-08T00:00:00Z",
    )
    shard_query_paths: list[str] = []
    captured_runtime_comments: list[tuple[Mapping[str, object], ...]] = []

    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("issues/comments?"):
            return [request]
        if path.startswith("issues/138/comments?"):
            return [decision]
        if path.startswith("issues/142/comments?"):
            shard_query_paths.append(path)
            assert "since=" not in path
            if path.endswith("page=1"):
                return first_page
            if path.endswith("page=2"):
                return [older_request, current_request]
            raise AssertionError(path)
        if path == "issues/138":
            return issue
        if path.startswith("issues/138/timeline?"):
            return []
        raise AssertionError(path)

    def no_frontier(**_kwargs: object) -> tuple[None, bool]:
        return None, False

    def no_continuations(**_kwargs: object) -> tuple[int, ...]:
        return ()

    def capture_runtime_comments(
        *,
        recent_comments: tuple[Mapping[str, object], ...],
        **_kwargs: object,
    ) -> bridge.ApplicationCompletion:
        captured_runtime_comments.append(recent_comments)
        return bridge.ApplicationCompletion("INVALID", "captured-runtime-history")

    monkeypatch.setattr(bridge, "_derive_frontier", no_frontier)
    monkeypatch.setattr(bridge, "_continuation_transport_comment_ids", no_continuations)
    monkeypatch.setattr(bridge, "_accepted_application_state", capture_runtime_comments)

    completion = bridge.qualify_application_completion(
        "owner/repo",
        "token",
        source=source,
        current_revision=REVISION,
        read=read,
        current_dispatch_request_comment_id=104,
        current_dispatch_issue_number=142,
        now=datetime(2026, 10, 8, tzinfo=UTC),
    )

    assert completion.reason == "captured-runtime-history"
    assert len(shard_query_paths) == 2
    assert shard_query_paths[0].endswith("page=1")
    assert shard_query_paths[1].endswith("page=2")
    assert len(captured_runtime_comments) == 1
    runtime_comments = captured_runtime_comments[0]
    assert len(runtime_comments) == 102
    assert tuple(comment["id"] for comment in runtime_comments[-2:]) == (101, 104)
    assert runtime_comments[-2]["created_at"] == "2026-07-01T00:00:00Z"

    status = bridge._prior_dispatch_handoff_reason(
        "owner/repo",
        "token",
        recent_comments=runtime_comments,
        owner="owner",
        current_dispatch_request_comment_id=104,
        plan_id=_carrier_plan_fixture().plan_id,
        read=lambda _repository, _token, path: (
            {"workflow_runs": []}
            if path.startswith("actions/workflows/scheduled-agent-bridge.yml/runs?")
            else (_ for _ in ()).throw(AssertionError(path))
        ),
    )
    assert status == "application-completion-carrier-prior-dispatch-incomplete"


def test_prior_dispatch_without_a_visible_run_fails_closed_before_carrier_reissue() -> None:
    status = bridge._prior_dispatch_handoff_reason(
        "owner/repo",
        "token",
        recent_comments=(_trusted_connector_comment(91, REQUEST_BODY),),
        owner="owner",
        current_dispatch_request_comment_id=100,
        plan_id=_carrier_plan_fixture().plan_id,
        read=lambda _repository, _token, path: (
            {"workflow_runs": []}
            if path.startswith("actions/workflows/scheduled-agent-bridge.yml/runs?")
            else (_ for _ in ()).throw(AssertionError(path))
        ),
    )

    assert status == "application-completion-carrier-prior-dispatch-incomplete"


def test_malformed_prior_dispatch_handoff_cannot_disappear_from_history() -> None:
    """An orphaned connector dispatch marker is not proof of no prior plan."""
    reads: list[str] = []

    def read(_repository: str, _token: str, path: str) -> object:
        reads.append(path)
        return {"workflow_runs": []}

    status = bridge._prior_dispatch_handoff_reason(
        "owner/repo",
        "token",
        recent_comments=(
            _trusted_connector_comment(90, f"{REQUEST_BODY}\nExtra: orphaned"),
            _trusted_connector_comment(91, REQUEST_BODY),
        ),
        owner="owner",
        current_dispatch_request_comment_id=100,
        plan_id=_carrier_plan_fixture().plan_id,
        read=read,
    )

    assert status == "application-completion-carrier-prior-dispatch-incomplete"
    assert reads == []


def test_unanswered_human_question_wait_is_derived_before_semantic_ingress() -> None:
    change = "human-wait-test"
    formal = _formal_frontier_comment(
        100,
        action="resolve-question",
        role="lead",
        result="human-decision-required",
        successor="Lead / resolve-question",
        request_id=90,
        change=change,
    )
    formal["updated_at"] = formal["created_at"]
    predecessor = _formal_frontier_comment(
        80,
        action="implement-change",
        role="executor",
        result="spec-blocker",
        successor="Lead / resolve-question",
        request_id=70,
        change=change,
    )
    predecessor["updated_at"] = predecessor["created_at"]
    current_issue = {
        "number": 138,
        "title": "Human wait regression",
        "state": "open",
        "created_at": "2026-09-17T00:00:00Z",
        "closed_at": None,
        "body": f"Change: {change}",
        "labels": [{"name": "action:resolve-question"}],
        "updated_at": formal["created_at"],
    }
    timeline = [
        {"id": 80, "event": "commented", "created_at": predecessor["created_at"]},
        {
            "id": 998,
            "event": "unlabeled",
            "created_at": "2026-09-18T02:00:09Z",
            "label": {"name": "action:implement-change"},
        },
        {
            "id": 999,
            "event": "labeled",
            "created_at": "2026-09-18T02:00:09Z",
            "label": {"name": "action:resolve-question"},
        },
        {"id": 100, "event": "commented", "created_at": formal["created_at"]},
    ]
    comments = [predecessor, formal]

    def read(_repository: str, _token: str, path: str) -> object:
        if path == "issues/138":
            return current_issue
        if path.startswith("issues/138/comments?"):
            return comments
        if path.startswith("issues/138/timeline?"):
            return timeline
        if path == f"compare/{REVISION}...{'d' * 40}":
            return {"status": "ahead", "base_commit": {"sha": REVISION}}
        raise AssertionError(path)

    source = bridge.WorkerRequest(138, "lead", "resolve-question")
    fixture_value = "unused-by-fake-reader"
    qualification = bridge.build_qualification_input(
        issue_number=138,
        change=change,
        state="open",
        current_routing=("lead", "resolve-question"),
        comments=tuple(comments),
        current_revision=REVISION,
        lifecycle_events=tuple(timeline),
    )
    assert bridge.qualify_current_formal_consequence(qualification).qualified, (
        bridge.qualify_current_formal_consequence(qualification)
    )
    frontier, qualified = bridge._derive_frontier(
        repository="owner/repo",
        token=fixture_value,
        source=source,
        current_issue=current_issue,
        issue_comments=tuple(comments),
        lifecycle_events=tuple(timeline),
        current_revision=REVISION,
        read=read,
    )
    assert qualified, frontier
    assert (
        bridge.derive_unanswered_human_wait(
            "owner/repo",
            fixture_value,
            source=source,
            current_revision=REVISION,
            read=read,
        )
        is True
    )
    # The exact unchanged request never receives semantic ingress on a later wake.
    decision = _decision("AUTHORIZE", issue_number=138, routing=("lead", "resolve-question"))
    suppressed = bridge.apply_derived_human_wait(
        decision,
        repository="owner/repo",
        token=fixture_value,
        current_revision=REVISION,
        read=read,
    )
    assert suppressed.disposition == "FAIL_CLOSED"
    assert suppressed.reason == "human-question-awaiting-new-evidence"
    machine = bridge.plan_dispatch_decision(
        event=_event(),
        default_branch_revision=REVISION,
        decision=suppressed,
    )
    assert machine.should_emit
    assert machine.result_body is not None
    machine_result = json.loads(machine.result_body)
    assert machine_result["disposition"] == "FAIL_CLOSED"
    assert "action" not in machine_result
    assert "issue_number" not in machine_result

    comments.append(
        {
            "id": 101,
            "created_at": "2026-09-18T02:00:11Z",
            "updated_at": "2026-09-18T02:00:11Z",
            "body": "Please continue",
            "user": {"login": "human"},
            "performed_via_github_app": None,
        }
    )
    current_issue["updated_at"] = "2026-09-18T02:00:11Z"
    resumed = bridge.apply_derived_human_wait(
        decision,
        repository="owner/repo",
        token=fixture_value,
        current_revision=REVISION,
        read=read,
    )
    assert resumed == decision

    comments.pop()
    current_issue["updated_at"] = formal["created_at"]
    timeline.append({"id": 1002, "event": "renamed", "created_at": "2026-09-18T02:00:11Z"})
    assert (
        bridge.apply_derived_human_wait(
            decision,
            repository="owner/repo",
            token=fixture_value,
            current_revision=REVISION,
            read=read,
        )
        == decision
    )
    timeline.pop()
    # A new authoritative main revision is conservatively re-evaluated, not
    # silenced by the old unanswered question.
    assert (
        bridge.apply_derived_human_wait(
            decision,
            repository="owner/repo",
            token=fixture_value,
            current_revision="d" * 40,
            read=read,
        )
        == decision
    )


def test_unanswered_human_wait_never_suppresses_other_actions() -> None:
    decision = _decision("AUTHORIZE", issue_number=138, routing=("executor", "implement-change"))
    fixture_value = "unused-by-fake-reader"
    assert (
        bridge.apply_derived_human_wait(
            decision,
            repository="owner/repo",
            token=fixture_value,
            current_revision=REVISION,
            read=lambda *_args: pytest.fail("irrelevant actions must not read Human wait evidence"),
        )
        == decision
    )


def test_carrier_outcome_consumer_blocks_duplicate_identical_reports() -> None:
    plan = _carrier_plan_fixture()
    recovery = _qualified_recovery_fixture(artifact_id=997)
    carrier_digest = "sha256:" + "6" * 64
    report_body = carrier.render_carrier_outcome_report(
        _carrier_outcome_fixture(
            plan,
            recovery,
            carrier_artifact_id=999,
            carrier_artifact_digest=carrier_digest,
        )
    )
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )

    outcome, reason = bridge._carrier_outcome_status(
        recent_comments=(
            _trusted_connector_comment(92, report_body),
            _trusted_connector_comment(93, report_body),
        ),
        owner="owner",
        repository="owner/repo",
        source=bridge.WorkerRequest(322, "executor", "implement-change"),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recovery_artifact=recovery,
        qualified_carrier=qualified,
    )

    assert outcome == "BLOCKED"
    assert reason == "application-completion-carrier-outcome-ambiguous"


@pytest.mark.parametrize("missing_plan_id", [False, True])
@pytest.mark.parametrize("contradictory_first", [False, True])
def test_carrier_outcome_blocks_same_lineage_plan_conflict_even_with_complete_report(
    missing_plan_id: bool,
    contradictory_first: bool,
) -> None:
    plan = _carrier_plan_fixture()
    recovery = _qualified_recovery_fixture(artifact_id=997)
    carrier_digest = "sha256:" + "6" * 64
    report = _carrier_outcome_fixture(
        plan,
        recovery,
        carrier_artifact_id=999,
        carrier_artifact_digest=carrier_digest,
    )
    valid_body = carrier.render_carrier_outcome_report(report)
    if missing_plan_id:
        contradictory_body = valid_body.replace(f"Plan-ID: {report.plan_id}\n", "")
        expected_reason = "application-completion-carrier-outcome-invalid"
    else:
        contradictory_body = carrier.render_carrier_outcome_report(
            replace(report, plan_id="carrier-plan-" + "f" * 64)
        )
        expected_reason = "application-completion-carrier-outcome-plan-reused"
    assert contradictory_body != valid_body
    bodies = (
        (contradictory_body, valid_body)
        if contradictory_first
        else (valid_body, contradictory_body)
    )
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )

    outcome, reason = bridge._carrier_outcome_status(
        recent_comments=tuple(
            _trusted_connector_comment(92 + index, body) for index, body in enumerate(bodies)
        ),
        owner="owner",
        repository="owner/repo",
        source=bridge.WorkerRequest(322, "executor", "implement-change"),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recovery_artifact=recovery,
        qualified_carrier=qualified,
    )

    assert outcome == "BLOCKED"
    assert reason == expected_reason


def test_carrier_outcome_consumer_ignores_unrelated_repository_lineage() -> None:
    plan = _carrier_plan_fixture()
    recovery = _qualified_recovery_fixture(artifact_id=997)
    carrier_digest = "sha256:" + "6" * 64
    report = replace(
        _carrier_outcome_fixture(
            plan,
            recovery,
            carrier_artifact_id=999,
            carrier_artifact_digest=carrier_digest,
        ),
        repository="other/repo",
    )
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest=carrier_digest,
        plan=plan,
    )

    outcome, reason = bridge._carrier_outcome_status(
        recent_comments=(
            _trusted_connector_comment(
                92,
                carrier.render_carrier_outcome_report(report),
            ),
        ),
        owner="owner",
        repository="owner/repo",
        source=bridge.WorkerRequest(322, "executor", "implement-change"),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recovery_artifact=recovery,
        qualified_carrier=qualified,
    )

    assert outcome == "NONE"
    assert reason is None


def test_carrier_outcome_cannot_claim_matching_precondition_with_other_observation() -> None:
    plan = _carrier_plan_fixture()
    recovery = _qualified_recovery_fixture(artifact_id=997)
    report = _carrier_outcome_fixture(
        plan,
        recovery,
        carrier_artifact_id=999,
        carrier_artifact_digest="sha256:" + "6" * 64,
    )
    mismatched_report = replace(
        report,
        observed_precondition_json=json.dumps(
            {"ref_sha": "c" * 40},
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    qualified = carrier.QualifiedCarrierPlan(
        request_comment_id=90,
        run_id=777,
        run_attempt=1,
        artifact_id=999,
        artifact_digest="sha256:" + "6" * 64,
        plan=plan,
    )

    outcome, reason = bridge._carrier_outcome_status(
        recent_comments=(
            _trusted_connector_comment(
                92,
                carrier.render_carrier_outcome_report(mismatched_report),
            ),
        ),
        owner="owner",
        repository="owner/repo",
        source=bridge.WorkerRequest(322, "executor", "implement-change"),
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
        recovery_artifact=recovery,
        qualified_carrier=qualified,
    )

    assert outcome == "BLOCKED"
    assert reason == "application-completion-carrier-outcome-invalid"


@pytest.mark.parametrize(
    ("run_id", "run_attempt", "job_id", "transport_comment_id"),
    [
        (37484224666, 1, 112340001372, None),
        (37484224666, 2, 112577054083, None),
        (37563005754, 2, 112607809410, 6029741785),
        (37693412638, 1, 113038961936, 6047718564),
    ],
)
@pytest.mark.parametrize("upload_step_present", [False, True])
def test_completed_legacy_application_job_preserves_historical_identity_without_replay(
    monkeypatch: pytest.MonkeyPatch,
    run_id: int,
    run_attempt: int,
    job_id: int,
    transport_comment_id: int | None,
    upload_step_present: bool,
) -> None:
    """Original and legacy continuation attempts cannot replay the same accepted intent."""
    request_id = 6019133874
    transport_id = request_id if transport_comment_id is None else transport_comment_id
    run_head = (
        "ac7aebd7c2ac81b3227986350544307cadb221cc"
        if transport_comment_id is None
        else "cd8d45f64e901cdb8e5e8b42358d6081a293d08f"
    )
    steps = [
        {"name": "Set up job", "conclusion": "success"},
        {
            "name": "Freshly authorize and apply repository-owned effects",
            "conclusion": "failure",
        },
    ]
    if upload_step_present:
        steps.append(
            {"name": "Upload exact application recovery evidence", "conclusion": "skipped"}
        )
    steps.append({"name": "Complete job", "conclusion": "success"})
    requested: list[str] = []

    def read(_repo: str, _token: str, path: str) -> object:
        requested.append(path)
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": run_id,
                        "display_title": f"Scheduled Agent Application {transport_id}",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": run_attempt,
                        "head_sha": run_head,
                    }
                ]
            }
        if path == f"actions/runs/{run_id}/jobs":
            return {
                "jobs": [
                    {
                        "id": job_id,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
                        "steps": steps,
                    }
                ]
            }
        raise AssertionError(f"unexpected read: {path}")

    monkeypatch.setattr(
        bridge, "read_application_recovery_artifact", lambda *_args, **_kwargs: None
    )
    completion = bridge._application_job(
        "royhsu-work/investment-strategy",
        "test-token",
        request_id,
        read=read,
        record=replace(
            _accepted_carrier_record(),
            request_comment_id=request_id,
            authorization_revision="ac7aebd7c2ac81b3227986350544307cadb221cc",
            result_kind="ready",
        ),
        accepted_decision_sha256="9c545558249285ec6d4fa632970dfa7157774d75bf2b6e46889e240a175cbd54",
        transport_comment_ids=(() if transport_comment_id is None else (transport_comment_id,)),
    )

    assert completion.state == "INVALID"
    assert completion.request_comment_id == request_id
    if upload_step_present:
        assert completion.reason == "application-completion-recovery-evidence-missing"
        assert completion.job_id is None
    else:
        assert completion.reason == "application-completion-legacy-recovery-upload-unavailable"
        assert completion.job_id == job_id
    assert requested == [
        "actions/workflows/scheduled-agent-application.yml/runs?event=issue_comment&per_page=100&page=1",
        f"actions/runs/{run_id}/jobs",
    ]
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "/rerun" not in workflow


def test_recovery_artifact_read_failure_is_not_legacy_missing_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed authoritative evidence read is not proof that the artifact never existed."""

    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 37563005754,
                        "display_title": "Scheduled Agent Application 90",
                        "status": "completed",
                        "conclusion": "failure",
                        "run_attempt": 1,
                        "head_sha": REVISION,
                    }
                ]
            }
        if path == "actions/runs/37563005754/jobs":
            return {
                "jobs": [
                    {
                        "id": 112607809410,
                        "name": "apply",
                        "status": "completed",
                        "conclusion": "failure",
                        "steps": [
                            {
                                "name": "Freshly authorize and apply repository-owned effects",
                                "conclusion": "failure",
                            },
                            {"name": "Complete job", "conclusion": "success"},
                        ],
                    }
                ]
            }
        raise AssertionError(f"unexpected read: {path}")

    def failed_evidence_read(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("incomplete GitHub artifact listing")

    monkeypatch.setattr(bridge, "read_application_recovery_artifact", failed_evidence_read)
    completion = bridge._application_job(
        "royhsu-work/investment-strategy",
        "test-token",
        90,
        read=read,
        record=_accepted_carrier_record(),
        accepted_decision_sha256="a" * 64,
    )

    assert completion.state == "INVALID"
    assert completion.reason == "application-completion-recovery-evidence-unavailable"
    assert completion.job_id is None


@pytest.mark.parametrize("terminal", ["cancelled", "timed_out", "skipped"])
def test_pending_capacity_cancel_before_accept_recovers_on_fresh_dispatch(
    terminal: str,
) -> None:
    """A cancelled pending apply job is not ACCEPT; later selection stays executable."""
    request_comment_id = 56789

    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 90001,
                        "display_title": f"Scheduled Agent Application {request_comment_id}",
                        "run_attempt": 1,
                        "status": "completed",
                        "conclusion": terminal,
                    }
                ]
            }
        if path == "actions/runs/90001/jobs":
            return {
                "jobs": [
                    {"id": 90002, "name": "apply", "status": "completed", "conclusion": terminal}
                ]
            }
        raise AssertionError(path)

    incomplete = bridge._preaccept_application_state(
        "royhsu-work/investment-strategy",
        "token",
        request_comment_id,
        read=read,
    )
    assert incomplete is not None
    assert incomplete.state == "REJECTED"
    assert incomplete.reason == "application-completion-preaccept-terminal-no-accept"

    from investment_strategy.scheduled_agent_runtime import (
        GitHubIssueObservation,
        acquire_dispatch_preflight,
    )
    from investment_strategy.workflow_dispatch import classify_dispatch

    preflight = acquire_dispatch_preflight(
        observations=(
            GitHubIssueObservation(
                issue_number=322,
                change="restore-no-work-idle-discovery",
                routing=("executor", "implement-change"),
                state="open",
                created_order=1,
                authoritative=True,
            ),
        ),
        source_total_count=1,
        incomplete_results=False,
        exhausted=True,
        human_authorized=True,
    )
    decision = classify_dispatch(preflight)
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 322
    assert decision.selected_routing == ("executor", "implement-change")
    fresh = bridge.plan_dispatch_decision(
        event=_event(),
        default_branch_revision=REVISION,
        decision=decision,
    )
    assert fresh.should_emit and fresh.result_body is not None
    rendered = json.loads(fresh.result_body)
    assert rendered["disposition"] == "AUTHORIZE"
    assert rendered["action"] == "implement-change"
    assert rendered["request_comment_id"] == 987


def test_capacity_run_unobservable_fails_closed_not_false_no_accept() -> None:
    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": []}
        raise AssertionError(path)

    result = bridge._preaccept_application_state(
        "royhsu-work/investment-strategy", "token", 56789, read=read
    )
    assert result is not None
    assert result.state == "INVALID"
    assert result.reason == "application-completion-run-not-yet-observable"


@pytest.mark.parametrize("conclusion", ("cancelled", "timed_out", "skipped"))
def test_preactcept_cancel_before_apply_job_is_terminal_no_accept(
    conclusion: str,
) -> None:
    """A uniquely canceled first run with conclusively zero jobs did not apply."""
    request_id = 67891

    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 90021,
                        "display_title": f"Scheduled Agent Application {request_id}",
                        "run_attempt": 1,
                        "status": "completed",
                        "conclusion": conclusion,
                    }
                ]
            }
        if path == "actions/runs/90021/jobs":
            return {"total_count": 0, "jobs": []}
        raise AssertionError(path)

    result = bridge._preaccept_application_state(
        "royhsu-work/investment-strategy",
        "token",
        request_id,
        read=read,
    )
    assert result is not None
    assert result.state == "REJECTED"
    assert result.reason == "application-completion-preaccept-terminal-no-accept"


@pytest.mark.parametrize(
    ("run_attempt", "conclusion", "total_count"),
    [
        (1, "failure", 0),
        (2, "cancelled", 0),
        (1, "cancelled", None),
        (1, "cancelled", 1),
        (True, "cancelled", 0),
        (1.0, "cancelled", 0),
    ],
)
def test_unqualified_no_apply_job_never_proves_terminal_no_accept(
    run_attempt: int | float | bool,
    conclusion: str,
    total_count: int | None,
) -> None:
    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 90021,
                        "display_title": "Scheduled Agent Application 67891",
                        "run_attempt": run_attempt,
                        "status": "completed",
                        "conclusion": conclusion,
                    }
                ]
            }
        if path == "actions/runs/90021/jobs":
            return {"total_count": total_count, "jobs": []}
        raise AssertionError(path)

    result = bridge._preaccept_application_state(
        "royhsu-work/investment-strategy", "token", 67891, read=read
    )
    assert result is not None
    assert result.state == "INVALID"


@pytest.mark.parametrize(
    ("job_ids", "expected_state"),
    [
        ((2101, 2101), "INVALID"),
        ((2101, None), "INVALID"),
        ((2101, 2102), "REJECTED"),
    ],
)
def test_no_apply_job_inventory_requires_unique_positive_ids(
    job_ids: tuple[int | None, int | None],
    expected_state: str,
) -> None:
    """A complete no-apply inventory must identify every job uniquely."""
    request_id = 67891

    def read(_repository: str, _token: str, path: str) -> object:
        if path.startswith("actions/workflows/"):
            return {
                "workflow_runs": [
                    {
                        "id": 90021,
                        "display_title": f"Scheduled Agent Application {request_id}",
                        "run_attempt": 1,
                        "status": "completed",
                        "conclusion": "cancelled",
                    }
                ]
            }
        if path == "actions/runs/90021/jobs":
            return {
                "total_count": 2,
                "jobs": [
                    {"id": job_ids[0], "name": "prepare"},
                    {"id": job_ids[1], "name": "idle-admission"},
                ],
            }
        raise AssertionError(path)

    result = bridge._preaccept_application_state(
        "royhsu-work/investment-strategy", "token", request_id, read=read
    )
    assert result is not None
    assert result.state == expected_state


_RECOVERY_R = "54af6323d224c96e42792b6fe83fd31158b88e8c"
_RECOVERY_BASE = "5d5edd88357824722887ce9eba8da96b08f2aeb3"
_RECOVERY_REVIEW_ID = "PRR_kwDOT0Uyc88AAAABTsE88Q"
_RECOVERY_OLD_R = "553eccce7169785c6836abc1a03dee8fdf1b33ba"


def _recovery_review_sources() -> dict[str, object]:
    reviewed_at = "2026-10-22T14:58:07Z"
    human_at = "2026-10-22T15:13:01Z"
    receipt = (
        "RECOVERY_OPENSPEC_REVIEW\n"
        "Repository: royhsu-work/investment-strategy\n"
        "Issue: 322\n"
        "Change: restore-no-work-idle-discovery\n"
        "PR: 340\n"
        f"Revision: {_RECOVERY_R}\n"
        f"Baseline: {_RECOVERY_BASE}\n"
        "Human-Decision-Comment: 6313995887\n"
        "Validator-Run: 39795457767\n"
        "Disposition: PASS\n\nIndependent semantic re-review."
    )
    decision_ref = f"issue:322:recovery-openspec-review:{_RECOVERY_R}:{_RECOVERY_REVIEW_ID}"
    return {
        "reviews": [
            {
                "id": 5616254193,
                "node_id": _RECOVERY_REVIEW_ID,
                "user": {"login": "royhsu-work"},
                "commit_id": _RECOVERY_R,
                "submitted_at": reviewed_at,
                "state": "COMMENTED",
                "body": receipt,
            }
        ],
        "commit": {"author": {"login": "royhsu-work"}},
        "original_human_comment": {
            "id": 6313995887,
            "user": {"login": "royhsu-work"},
            "body": "Marker: HUMAN_APPROVED_FORWARD_RECOVERY_CONVERGENCE_20261021",
            "created_at": "2026-10-21T10:42:08Z",
            "updated_at": "2026-10-21T10:42:08Z",
            "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
        },
        "issue_comments": [
            {
                "id": 6344199684,
                "user": {"login": "royhsu-work"},
                "body": f"Human-Decision-For: {decision_ref}\n"
                "Recovery-Review-Independence: separately-reviewed\n",
                "created_at": human_at,
                "updated_at": human_at,
                "performed_via_github_app": None,
            }
        ],
        "events": [
            {
                "id": 33964035959,
                "event": "labeled",
                "actor": {"login": "royhsu-work"},
                "label": {"name": "human:approved"},
                "created_at": "2026-10-22T15:13:33Z",
                "performed_via_github_app": None,
            }
        ],
        "validator": {"id": 39795457767, "conclusion": "success"},
        "validator_job": {"id": 119881578427, "name": "validate", "conclusion": "success"},
        "validator_log": (
            "validation_target_repository=royhsu-work/investment-strategy\n"
            f"validation_target_sha={_RECOVERY_R}\n"
            f"validator_checkout_head={_RECOVERY_R}\n"
            "Run openspec validate --all --strict --json --no-interactive\n"
            '"totals": { "items": 8, "passed": 8, "failed": 0 }'
        ),
        "comparison": {"status": "identical"},
        "baseline_comparison": {"status": "ahead", "base_commit": {"sha": _RECOVERY_BASE}},
        "reviewed_blobs": {"openspec/changes/restore-no-work-idle-discovery/design.md": "a" * 40},
        "current_blobs": {"openspec/changes/restore-no-work-idle-discovery/design.md": "a" * 40},
        "threads": [],
    }


def _recovery_prior_findings() -> dict[str, object]:
    """The actual historical old-revision FINDINGS preceding the reviewed PASS."""
    current = cast(list[dict[str, object]], _recovery_review_sources()["reviews"])[0]
    return {
        **current,
        "id": 5613393788,
        "node_id": "PRR_kwDOT0Uyc88AAAABTpWXfA",
        "commit_id": _RECOVERY_OLD_R,
        "submitted_at": "2026-10-22T12:10:00Z",
        "body": cast(str, current["body"])
        .replace(_RECOVERY_R, _RECOVERY_OLD_R)
        .replace("Disposition: PASS", "Disposition: FINDINGS"),
    }


def test_322_recovery_review_latest_revision_pass_supersedes_historical_findings_red() -> None:
    evidence = _recovery_review_sources()
    cast(list[dict[str, object]], evidence["reviews"]).insert(0, _recovery_prior_findings())
    result = bridge.qualify_recovery_openspec_review(
        repository="royhsu-work/investment-strategy",
        issue_number=322,
        change="restore-no-work-idle-discovery",
        pr_number=340,
        head_sha=_RECOVERY_R,
        approval_label_present=True,
        **evidence,
    )
    assert result.disposition == "COMPLETE", result.reason
    assert result.revision == _RECOVERY_R


@pytest.mark.parametrize("case", ["same-revision-conflict", "later-findings"])
def test_322_review_keeps_applicable_duplicate_and_latest_findings_blocked(case: str) -> None:
    evidence = _recovery_review_sources()
    earlier = _recovery_prior_findings()
    if case == "same-revision-conflict":
        earlier["commit_id"] = _RECOVERY_R
        earlier["body"] = cast(str, earlier["body"]).replace(_RECOVERY_OLD_R, _RECOVERY_R)
    else:
        earlier["submitted_at"] = "2026-10-22T16:00:00Z"
    cast(list[dict[str, object]], evidence["reviews"]).insert(0, earlier)
    result = bridge.qualify_recovery_openspec_review(
        repository="royhsu-work/investment-strategy",
        issue_number=322,
        change="restore-no-work-idle-discovery",
        pr_number=340,
        head_sha=_RECOVERY_R,
        approval_label_present=True,
        **evidence,
    )
    assert result.disposition == "CONFLICT"


def test_322_recovery_review_human_attestation_adoption_red() -> None:
    evidence = _recovery_review_sources()
    result = bridge.qualify_recovery_openspec_review(
        repository="royhsu-work/investment-strategy",
        issue_number=322,
        change="restore-no-work-idle-discovery",
        pr_number=340,
        head_sha=_RECOVERY_R,
        approval_label_present=True,
        **evidence,
    )
    assert result.disposition == "COMPLETE"
    assert result.review_id == _RECOVERY_REVIEW_ID


def test_322_recovery_original_human_reference_can_be_connector_recorded() -> None:
    """The original decision reference is not the reserved Human attestation."""

    evidence = _recovery_review_sources()
    cast(dict[str, object], evidence["original_human_comment"])["performed_via_github_app"] = {
        "slug": "chatgpt-codex-connector"
    }
    result = bridge.qualify_recovery_openspec_review(
        repository="royhsu-work/investment-strategy",
        issue_number=322,
        change="restore-no-work-idle-discovery",
        pr_number=340,
        head_sha=_RECOVERY_R,
        approval_label_present=True,
        **evidence,
    )
    assert result.disposition == "COMPLETE", result.reason


def test_322_review_adopts_disjoint_code_only_descendant_without_sha_lock() -> None:
    sources = _recovery_review_sources()
    head = "b" * 40
    sources["comparison"] = {"status": "ahead", "base_commit": {"sha": _RECOVERY_R}}
    result = bridge.qualify_recovery_openspec_review(
        repository="royhsu-work/investment-strategy",
        issue_number=322,
        change="restore-no-work-idle-discovery",
        pr_number=340,
        head_sha=head,
        approval_label_present=True,
        **sources,
    )
    assert result.disposition == "COMPLETE"
    assert result.revision == _RECOVERY_R


def test_322_distinct_authenticated_review_actor_needs_no_same_login_attestation() -> None:
    sources = _recovery_review_sources()
    cast(list[dict[str, object]], sources["reviews"])[0]["user"] = {
        "login": "separate-independent-reviewer"
    }
    sources["issue_comments"] = []
    sources["events"] = []
    result = bridge.qualify_recovery_openspec_review(
        repository="royhsu-work/investment-strategy",
        issue_number=322,
        change="restore-no-work-idle-discovery",
        pr_number=340,
        head_sha=_RECOVERY_R,
        approval_label_present=False,
        **sources,
    )
    assert result.disposition == "COMPLETE"


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing-attestation", "UNKNOWN"),
        ("edited-attestation", "UNKNOWN"),
        ("connector-attestation", "UNKNOWN"),
        ("competing-attestation", "CONFLICT"),
        ("missing-approval", "UNKNOWN"),
        ("wrong-checkout", "CONFLICT"),
        ("changed-normative-blob", "CONFLICT"),
        ("findings", "CONFLICT"),
        ("unresolved-thread", "CONFLICT"),
        ("missing-original-human", "UNKNOWN"),
        ("wrong-baseline", "CONFLICT"),
    ],
)
def test_322_recovery_review_rejects_unqualified_sources_red(mutation: str, expected: str) -> None:
    evidence = _recovery_review_sources()
    comments = cast(list[dict[str, object]], evidence["issue_comments"])
    if mutation == "missing-attestation":
        comments.clear()
    elif mutation == "edited-attestation":
        comments[0]["updated_at"] = "2026-10-22T15:14:00Z"
    elif mutation == "connector-attestation":
        comments[0]["performed_via_github_app"] = {"slug": "chatgpt-codex-connector"}
    elif mutation == "competing-attestation":
        comments.append({**comments[0], "id": 6344199685})
    elif mutation == "missing-approval":
        evidence["events"] = []
    elif mutation == "wrong-checkout":
        evidence["validator_log"] = cast(str, evidence["validator_log"]).replace(
            f"validator_checkout_head={_RECOVERY_R}", "validator_checkout_head=" + "b" * 40
        )
    elif mutation == "changed-normative-blob":
        evidence["current_blobs"] = {
            "openspec/changes/restore-no-work-idle-discovery/design.md": "b" * 40
        }
    elif mutation == "findings":
        cast(list[dict[str, object]], evidence["reviews"])[0]["body"] = cast(
            str, cast(list[dict[str, object]], evidence["reviews"])[0]["body"]
        ).replace("Disposition: PASS", "Disposition: FINDINGS")
    elif mutation == "unresolved-thread":
        evidence["threads"] = [
            {
                "is_resolved": False,
                "is_outdated": False,
                "comments": [{"body": "RECOVERY_OPENSPEC_FINDING material"}],
            }
        ]
    elif mutation == "missing-original-human":
        evidence["original_human_comment"] = None
    elif mutation == "wrong-baseline":
        evidence["baseline_comparison"] = {"status": "diverged"}
    result = bridge.qualify_recovery_openspec_review(
        repository="royhsu-work/investment-strategy",
        issue_number=322,
        change="restore-no-work-idle-discovery",
        pr_number=340,
        head_sha=_RECOVERY_R,
        approval_label_present=True,
        **evidence,
    )
    assert result.disposition == expected, result.reason


def test_322_review_source_reader_adopts_exact_r_without_formal_result() -> None:
    """Exercise the actual reader/consumer path, including trees and executed log."""
    sources = _recovery_review_sources()
    cast(list[dict[str, object]], sources["reviews"]).insert(0, _recovery_prior_findings())
    paths: list[str] = []

    def read(_repository: str, _token: str, path: str) -> object:
        paths.append(path)
        if path == "pulls/340/reviews?per_page=100&page=1":
            return sources["reviews"]
        if path == f"commits/{_RECOVERY_R}":
            return sources["commit"]
        if path == "issues/comments/6313995887":
            return sources["original_human_comment"]
        if path == "issues/322/timeline?per_page=100&page=1":
            return sources["events"]
        if path == "actions/runs/39795457767":
            return sources["validator"]
        if path == "actions/runs/39795457767/jobs?per_page=100":
            return {"total_count": 1, "jobs": [sources["validator_job"]]}
        if path == f"compare/{_RECOVERY_BASE}...{_RECOVERY_R}":
            return sources["baseline_comparison"]
        if path == f"git/commits/{_RECOVERY_R}":
            return {"tree": {"sha": "c" * 40}}
        if path == f"git/trees/{'c' * 40}?recursive=1":
            return {
                "truncated": False,
                "tree": [
                    {
                        "type": "blob",
                        "path": "openspec/changes/restore-no-work-idle-discovery/design.md",
                        "sha": "a" * 40,
                    }
                ],
            }
        raise AssertionError(f"unexpected source: {path}")

    result = bridge.read_recovery_openspec_review(
        "royhsu-work/investment-strategy",
        "token",
        head_sha=_RECOVERY_R,
        approval_label_present=True,
        issue_comments=tuple(cast(list[dict[str, object]], sources["issue_comments"])),
        read=read,
        log_read=lambda *_: cast(str, sources["validator_log"]),
        thread_read=lambda *_: [],
    )
    assert result.disposition == "COMPLETE"
    assert result.review_id == _RECOVERY_REVIEW_ID
    assert "issues/322/timeline?per_page=100&page=1" in paths
    assert f"git/trees/{'c' * 40}?recursive=1" in paths


@pytest.mark.parametrize(
    ("unfinished", "expected"),
    [(True, "INCOMPLETE"), (False, "COMPLETE")],
)
@pytest.mark.parametrize("duplicate_checks", [False, True])
@pytest.mark.parametrize("duplicate_formal", [False, True])
@pytest.mark.parametrize("target_state", ["ok", "unreadable", "conflict", "missing-effect"])
@pytest.mark.parametrize("carrier_merged", [False, True])
def test_original_ready_preformal_entry_has_no_result_cycle(
    unfinished: bool,
    expected: str,
    duplicate_checks: bool,
    duplicate_formal: bool,
    target_state: str,
    carrier_merged: bool,
) -> None:
    """Real accepted-result parser, live consumer and absent ACTION_RESULT shape."""
    request = _effect_request_comment(
        comment_id=6019133874,
        created_at="2026-10-07T02:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="ready",
        issue_number=322,
        change="restore-no-work-idle-discovery",
    )
    decision = _application_decision_comment(request, comment_id=6019173711)
    record = bridge.parse_application_decision(decision["body"])
    assert record is not None
    tasks = (
        "## 0G. Forward Recovery\n"
        f"- [{' ' if unfinished else 'x'}] 0.42 **RED:** regression\n"
        "- [x] 0.43 **GREEN:** implementation\n"
        "- [x] 0.44 **REFACTOR/VERIFY:** gates\n"
    )
    issue = {
        "number": 322,
        "title": "Explore restoring NO_WORK idle discovery after Action-only dispatch",
        "state": "open",
        "created_at": "2026-09-22T15:39:54Z",
        "closed_at": None,
        "body": "Change: restore-no-work-idle-discovery",
        "labels": [
            {"name": "action:implement-change"},
            {"name": "human:approved"},
        ],
    }
    head = "d" * 40
    merge_sha = "7" * 40
    task_sha = "f" * 40
    correction_files = {
        "openspec/changes/restore-no-work-idle-discovery/tasks.md": task_sha,
        "src/investment_strategy/issue_comment_bridge.py": "a" * 40,
        "src/investment_strategy/scheduled_agent_effects.py": "b" * 40,
        "tests/test_issue_comment_bridge.py": "c" * 40,
        "tests/test_scheduled_agent_effects.py": "e" * 40,
    }
    comments = [decision]
    if duplicate_formal:
        raw = bridge._application_owned_worker_result(
            record.raw_worker_result,
            source=bridge.WorkerRequest(322, "executor", "implement-change"),
            change="restore-no-work-idle-discovery",
            current_revision=_RECOVERY_BASE,
            result_revision=head,
            request_comment_id=6019133874,
        )
        worker = bridge.parse_worker_result(
            raw, bridge.WorkerRequest(322, "executor", "implement-change")
        )
        result_body = json.loads(worker.requested_effects[-1].payload_json)["body"]
        comments.extend(
            [
                {
                    "id": 6300000000 + index,
                    "body": result_body,
                    "created_at": f"2026-10-22T16:00:0{index}Z",
                    "user": {"login": "github-actions[bot]"},
                    "performed_via_github_app": {"slug": "github-actions"},
                }
                for index in (1, 2)
            ]
        )

    def read(_repository: str, _token: str, path: str) -> object:
        if path == "pulls/340":
            return {
                "number": 340,
                "state": "closed" if carrier_merged else "open",
                "merged": carrier_merged,
                "merged_at": "2026-10-23T15:54:38Z" if carrier_merged else None,
                "merge_commit_sha": merge_sha if carrier_merged else None,
                "draft": False,
                "head": {
                    "sha": head,
                    "ref": "agent/report-materialization-postcondition-failure",
                    "repo": {"full_name": "royhsu-work/investment-strategy"},
                },
                "base": {
                    "ref": "main",
                    "sha": "1" * 40 if carrier_merged else _RECOVERY_BASE,
                    "repo": {"full_name": "royhsu-work/investment-strategy"},
                },
            }
        if path == "git/ref/heads/agent/report-materialization-postcondition-failure":
            if carrier_merged:
                raise AssertionError("merged recovery must not require deleted source ref")
            if target_state == "unreadable":
                return None
            return {
                "object": {"sha": head if target_state in {"ok", "missing-effect"} else "b" * 40}
            }
        if path == (
            "contents/openspec/changes/restore-no-work-idle-discovery/tasks.md?ref=" + head
        ):
            return {
                "encoding": "base64",
                "content": base64.b64encode(tasks.encode()).decode(),
                "sha": task_sha,
            }
        if path == f"compare/{_RECOVERY_R}...{head}":
            return {
                "status": "ahead",
                "ahead_by": 1,
                "base_commit": {"sha": _RECOVERY_R},
                "commits": [{"sha": head}],
                "files": [
                    {"filename": name, "sha": sha, "status": "modified"}
                    for name, sha in correction_files.items()
                    if target_state != "missing-effect"
                    or name != "tests/test_scheduled_agent_effects.py"
                ],
            }
        if path == f"git/commits/{head}":
            return {
                "sha": head,
                "parents": [{"sha": _RECOVERY_R}],
                "tree": {"sha": "9" * 40},
            }
        if path == f"git/commits/{merge_sha}":
            if target_state == "unreadable":
                return None
            return {
                "sha": merge_sha,
                "parents": [
                    {"sha": _RECOVERY_BASE},
                    {"sha": "b" * 40 if target_state == "conflict" else head},
                ],
            }
        if path == f"compare/{merge_sha}...{merge_sha}":
            return {
                "status": "identical",
                "behind_by": 0,
                "base_commit": {"sha": merge_sha},
            }
        if path == f"git/trees/{'9' * 40}?recursive=1":
            return {
                "truncated": False,
                "tree": [
                    {"type": "blob", "path": name, "sha": sha}
                    for name, sha in correction_files.items()
                ],
            }
        if path == f"commits/{head}/check-runs?per_page=100":
            checks = [
                {
                    "name": name,
                    "head_sha": head,
                    "conclusion": "success",
                    "details_url": (
                        "https://github.com/royhsu-work/investment-strategy/"
                        "actions/runs/39795457767/job/119881578427"
                    ),
                }
                for name in ("quality", "validate")
            ]
            if duplicate_checks:
                checks.extend([dict(check) for check in checks])
            return {
                "total_count": len(checks),
                "check_runs": checks,
            }
        if path == "actions/jobs/119881578427":
            return {"id": 119881578427, "name": "validate", "conclusion": "success"}
        raise AssertionError(path)

    result = bridge.qualify_original_322_pre_formal(
        repository="royhsu-work/investment-strategy",
        token=REVISION,
        source=bridge.WorkerRequest(322, "executor", "implement-change"),
        record=record,
        issue_comments=tuple(comments),
        current_issue=issue,
        current_revision=merge_sha if carrier_merged else _RECOVERY_BASE,
        read=read,
        expected_decision_digest=hashlib.sha256(cast(str, decision["body"]).encode()).hexdigest(),
    )
    target_disposition = (
        "CONFLICT"
        if target_state == "conflict"
        else "UNKNOWN"
        if target_state == "unreadable"
        else expected
    )
    assert result.disposition == ("CONFLICT" if duplicate_formal else target_disposition), (
        result.predicates
    )
    assert dict(result.predicates)["F"] == ("CONFLICT" if duplicate_formal else "COMPLETE")
    assert dict(result.predicates)["S"] == "COMPLETE"  # no old checkpoint replay
    assert result.blocking_predicates == tuple(
        name
        for name in ("M", "F")
        if (name == "M" and (unfinished or target_state in {"unreadable", "conflict"}))
        or (name == "F" and duplicate_formal)
    )


@pytest.mark.parametrize("lost_after_formal_post", [False, True])
def test_original_322_exit_materializes_once_then_reconciles_without_replay(
    monkeypatch: pytest.MonkeyPatch,
    lost_after_formal_post: bool,
) -> None:
    """The actual application entry never replays the accepted physical plan."""
    request = _effect_request_comment(
        comment_id=6019133874,
        created_at="2026-10-07T02:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="ready",
        issue_number=322,
        change="restore-no-work-idle-discovery",
    )
    decision = _application_decision_comment(request, comment_id=6019173711)
    comments = [decision]
    issue = {
        "number": 322,
        "title": "Explore restoring NO_WORK idle discovery after Action-only dispatch",
        "state": "open",
        "created_at": "2026-09-22T15:39:54Z",
        "closed_at": None,
        "body": "Change: restore-no-work-idle-discovery",
        "labels": [{"name": "action:implement-change"}, {"name": "human:approved"}],
    }

    def read(_repository: str, _token: str, path: str) -> object:
        if path == "issues/322/comments?sort=created&direction=asc&per_page=100&page=1":
            return list(comments)
        if path == "issues/322":
            return dict(issue)
        if path == "pulls/340":
            return {"head": {"sha": _RECOVERY_R}}
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_authorization_ancestry", lambda *_args, **_kw: ())
    monkeypatch.setattr(
        bridge,
        "_materialization_effects",
        lambda *_args, **_kwargs: ({"operation": "application-materialize"},),
    )
    monkeypatch.setattr(
        bridge,
        "find_materialization_payload",
        lambda *_args: SimpleNamespace(change="restore-no-work-idle-discovery", pr_number=353),
    )
    monkeypatch.setattr(
        bridge,
        "qualify_implementation_carrier",
        lambda **kwargs: (
            SimpleNamespace(
                disposition="HISTORICAL_MERGED",
                head_sha="e" * 40,  # Not the maintenance PR #340 HEAD.
            )
            if kwargs["pr_number"] == 353
            else None
        ),
    )
    monkeypatch.setattr(
        bridge,
        "qualify_original_322_pre_formal",
        lambda **_kw: bridge.RecoveryPreFormalQualification(
            "COMPLETE", tuple((name, "COMPLETE") for name in "IRMVSF")
        ),
    )
    requested: list[list[str]] = []

    def apply(raw: str, **kwargs: object) -> tuple[object, bridge.ApplyResult]:
        assert kwargs["original_322_recovery"] is True
        assert kwargs["accepted_intent"] is True
        worker = bridge.parse_worker_result(
            raw,
            bridge.WorkerRequest(322, "executor", "implement-change"),
            authorized_change="restore-no-work-idle-discovery",
        )
        effects = [effect.kind for effect in worker.requested_effects]
        requested.append(effects)
        if effects:
            payload = json.loads(worker.requested_effects[0].payload_json)
            comments.append(
                {
                    "id": 6999999999,
                    "body": payload["body"],
                    "created_at": "2026-10-22T17:00:00Z",
                    "user": {"login": "github-actions[bot]"},
                    "performed_via_github_app": {"slug": "github-actions"},
                }
            )
            if lost_after_formal_post:
                return object(), bridge.ApplyResult(False, "response-lost-after-formal")
        issue["labels"] = [
            {"name": "action:review-implementation"},
            {"name": "human:approved"},
        ]
        return object(), bridge.ApplyResult(True, "applied")

    first = bridge.apply_original_322_recovery_exit(
        "royhsu-work/investment-strategy",
        "token",
        current_revision=_RECOVERY_BASE,
        read=read,
        effect_apply=apply,
    )
    assert first.state == ("INVALID" if lost_after_formal_post else "COMPLETE"), first
    assert requested == [["issue-comment"]]
    assert "Revision: " + "e" * 40 in str(comments[-1]["body"])
    assert "Revision: " + _RECOVERY_R not in str(comments[-1]["body"])
    second = bridge.apply_original_322_recovery_exit(
        "royhsu-work/investment-strategy",
        "token",
        current_revision=_RECOVERY_BASE,
        read=read,
        effect_apply=apply,
    )
    assert second.state == "COMPLETE", second
    assert requested == ([["issue-comment"], []] if lost_after_formal_post else [["issue-comment"]])


@pytest.mark.parametrize(
    "scenario",
    [
        "normal",
        "merged",
        "production-history",
        "lost-response",
        "disjoint",
        "conflict",
        "incomplete",
        "unknown",
        "no-current-approval",
        "missing-current-file",
    ],
)
def test_original_322_recovery_exit_real_owners_from_ready_to_successor(
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
) -> None:
    """Real application/review/effect/dispatch owners; only GitHub I/O is simulated."""
    from investment_strategy import scheduled_agent_effects as effects
    from investment_strategy import scheduled_agent_runtime as runtime

    repository = "royhsu-work/investment-strategy"
    head = "d" * 40
    merge_sha = "7" * 40
    head_tree = "9" * 40
    review_tree = "8" * 40
    task_sha = "f" * 40
    correction_files = {
        "openspec/changes/restore-no-work-idle-discovery/tasks.md": task_sha,
        "src/investment_strategy/issue_comment_bridge.py": "a" * 40,
        "src/investment_strategy/scheduled_agent_effects.py": "b" * 40,
        "tests/test_issue_comment_bridge.py": "c" * 40,
        "tests/test_scheduled_agent_effects.py": "e" * 40,
    }
    tasks = "\n".join(
        (
            "## 0G. Forward Recovery",
            "- [x] 0.42 **RED:** regression",
            "- [x] 0.43 **GREEN:** implement",
            "- [x] 0.44 **REFACTOR/VERIFY:** gates",
        )
    )
    original_fixture = json.loads(
        Path("tests/fixtures/issue322-application-recovery.json").read_text(encoding="utf-8")
    )
    decision = cast(dict[str, object], original_fixture["original_accepted_decision"])
    record = bridge.parse_application_decision(decision["body"])
    assert record is not None
    assert record.request_comment_id == 6019133874
    assert hashlib.sha256(cast(str, decision["body"]).encode()).hexdigest() == (
        "9c545558249285ec6d4fa632970dfa7157774d75bf2b6e46889e240a175cbd54"
    )
    # The original accepted intent includes non-idempotent physical effects;
    # only its formal projection may run in this recovery.
    assert len(json.loads(record.raw_worker_result)["requested_effects"]) == 2
    evidence = _recovery_review_sources()
    cast(list[dict[str, object]], evidence["reviews"]).insert(0, _recovery_prior_findings())
    merged_carrier = scenario in {"merged", "production-history"}
    issue: dict[str, object] = {
        "number": 322,
        "title": "Explore restoring NO_WORK idle discovery after Action-only dispatch",
        "state": "open",
        "created_at": "2026-09-22T15:39:54Z",
        "closed_at": None,
        "body": "Change: restore-no-work-idle-discovery",
        "labels": [{"name": "action:implement-change"}, {"name": "human:approved"}],
    }
    if scenario == "no-current-approval":
        issue["labels"] = [{"name": "action:implement-change"}]
    comments: list[dict[str, object]] = [
        decision,
        *cast(list[dict[str, object]], evidence["issue_comments"]),
    ]
    timeline: list[dict[str, object]] = list(cast(list[dict[str, object]], evidence["events"]))
    if scenario == "production-history":
        # Actual #322 boundary: a previous formal FINDINGS, followed by an
        # unchanged action route, an unrelated Human label, and two automatic
        # close/reopen cycles before the new accepted READY projection.
        previous = {
            "id": 6014954647,
            "body": (
                "REVIEW_RESULT\nWorkflow: #322\n"
                "Change: restore-no-work-idle-discovery\n"
                "Role: reviewer\nAction: review-implementation\nResult: FINDINGS\n"
                f"Revision: {head}\nDefault-Branch-Revision: {merge_sha}\n"
                "Application-Correlation: application:6014936846:322:"
                "restore-no-work-idle-discovery:reviewer:review-implementation:"
                f"findings:{merge_sha}\n"
                "Repository-derived successor: Executor / implement-change"
            ),
            "created_at": "2026-10-06T11:09:52Z",
            "updated_at": "2026-10-06T11:09:52Z",
            "user": {"login": "github-actions[bot]"},
            "performed_via_github_app": {"slug": "github-actions"},
        }
        comments.insert(0, previous)
        timeline[:0] = [
            {"id": 6014954647, "event": "commented", "created_at": "2026-10-06T11:09:52Z"},
            {
                "id": 32592174244,
                "event": "unlabeled",
                "created_at": "2026-10-06T11:10:04Z",
                "label": {"name": "action:review-implementation"},
            },
            {
                "id": 32592174308,
                "event": "labeled",
                "created_at": "2026-10-06T11:10:04Z",
                "label": {"name": "action:implement-change"},
                "actor": {"login": "github-actions[bot]"},
                "performed_via_github_app": {"slug": "github-actions"},
            },
        ]
        timeline.append(
            {"id": 34556655624, "event": "closed", "created_at": "2026-10-29T06:57:35Z"}
        )
        timeline.append(
            {"id": 34556840412, "event": "reopened", "created_at": "2026-10-29T07:00:23Z"}
        )
    if merged_carrier:
        # Exact production consequence of the one-time merge: GitHub closed
        # #322 through a historic commit keyword, then it was reopened with
        # its action labels unchanged. Neither event is an ACTION_RESULT.
        timeline.extend(
            (
                {
                    "id": 34068056850,
                    "event": "closed",
                    "created_at": "2026-10-23T15:54:42Z",
                    "commit_id": "553eccce7169785c6836abc1a03dee8fdf1b33ba",
                },
                {
                    "id": 34068301236,
                    "event": "reopened",
                    "created_at": "2026-10-23T15:57:23Z",
                },
            )
        )
    if scenario == "production-history":
        timeline.sort(key=lambda item: (cast(str, item["created_at"]), cast(int, item["id"])))
    comment_posts = 0
    route_patches = 0
    posted_at = (
        "2026-10-29T09:21:48Z"
        if scenario == "production-history"
        else "2026-10-23T16:00:01Z"
        if merged_carrier
        else "2026-10-22T16:00:01Z"
    )
    unlabel_at = (
        "2026-10-29T09:21:49Z"
        if scenario == "production-history"
        else "2026-10-23T16:00:02Z"
        if merged_carrier
        else "2026-10-22T16:00:02Z"
    )
    label_at = (
        "2026-10-29T09:21:50Z"
        if scenario == "production-history"
        else "2026-10-23T16:00:03Z"
        if merged_carrier
        else "2026-10-22T16:00:03Z"
    )

    def read(_repository: str, _token: str, path: str) -> object:
        assert _repository == repository
        if path == "":
            return {"default_branch": "main"}
        if path == "issues/322":
            return dict(issue)
        if path == "issues/322/comments?sort=created&direction=asc&per_page=100&page=1":
            return list(comments)
        if path.startswith("issues/322/comments?per_page=100&sort=created&direction=desc"):
            return list(reversed(comments))
        if path == "issues/322/timeline?per_page=100&page=1":
            return list(timeline)
        if path == "issues/comments/6313995887":
            return evidence["original_human_comment"]
        if path.startswith("issues/comments/"):
            comment_id = int(path.rsplit("/", 1)[1])
            return next((dict(item) for item in comments if item["id"] == comment_id), None)
        if path == "pulls/340":
            return {
                "number": 340,
                "state": "closed" if merged_carrier else "open",
                "merged": merged_carrier,
                "merged_at": "2026-10-23T15:54:38Z" if merged_carrier else None,
                "merge_commit_sha": merge_sha if merged_carrier else None,
                "draft": False,
                "head": {
                    "sha": head,
                    "ref": "agent/report-materialization-postcondition-failure",
                    "repo": {"full_name": repository},
                },
                "base": {
                    "ref": "main",
                    "sha": "1" * 40 if merged_carrier else _RECOVERY_BASE,
                    "repo": {"full_name": repository},
                },
            }
        if path == "git/ref/heads/agent/report-materialization-postcondition-failure":
            if merged_carrier:
                raise AssertionError("merged PR's deleted head ref must not be required")
            return {"object": {"sha": head}}
        if path == "git/ref/heads/main":
            return {"object": {"sha": merge_sha if merged_carrier else _RECOVERY_BASE}}
        if path == f"contents/openspec/changes/restore-no-work-idle-discovery/tasks.md?ref={head}":
            return {
                "encoding": "base64",
                "content": base64.b64encode(tasks.encode()).decode(),
                "sha": task_sha,
            }
        if path == "pulls/340/reviews?per_page=100&page=1":
            return evidence["reviews"]
        if path == f"commits/{_RECOVERY_R}":
            return evidence["commit"]
        if path == "actions/runs/39795457767":
            return evidence["validator"]
        if path == "actions/runs/39795457767/jobs?per_page=100":
            return {"total_count": 1, "jobs": [evidence["validator_job"]]}
        if path == "actions/jobs/119881578427":
            return evidence["validator_job"]
        if path == "actions/jobs/111111111111":
            return {"id": 111111111111, "name": "validate", "conclusion": "success"}
        if path == f"compare/{_RECOVERY_BASE}...{_RECOVERY_R}":
            return evidence["baseline_comparison"]
        if path == f"compare/{_RECOVERY_R}...{head}":
            if scenario == "unknown":
                return None
            compared_files = [
                {"filename": name, "sha": sha, "status": "modified"}
                for name, sha in correction_files.items()
                if scenario != "incomplete" or name != "tests/test_scheduled_agent_effects.py"
            ]
            if scenario in {"disjoint", "conflict"}:
                compared_files.append(
                    {
                        "filename": "README.md",
                        "sha": "6" * 40 if scenario == "disjoint" else "5" * 40,
                        "status": "modified",
                    }
                )
            return {
                "status": "ahead",
                "ahead_by": 1,
                "base_commit": {"sha": _RECOVERY_R},
                "commits": [{"sha": head}],
                "files": compared_files,
            }
        expected_current_sha = merge_sha if merged_carrier else _RECOVERY_BASE
        if path == f"compare/{record.authorization_revision}...{expected_current_sha}":
            return {
                "status": "ahead",
                "behind_by": 0,
                "base_commit": {"sha": record.authorization_revision},
            }
        if path == f"git/commits/{merge_sha}":
            return {"sha": merge_sha, "parents": [{"sha": _RECOVERY_BASE}, {"sha": head}]}
        if path == f"compare/{merge_sha}...{merge_sha}":
            return {
                "status": "identical",
                "behind_by": 0,
                "base_commit": {"sha": merge_sha},
            }
        if path == f"git/commits/{_RECOVERY_R}":
            return {"tree": {"sha": review_tree}}
        if path == f"git/commits/{head}":
            return {
                "sha": head,
                "parents": [{"sha": _RECOVERY_R}],
                "tree": {"sha": head_tree},
            }
        if path == f"git/trees/{review_tree}?recursive=1":
            return {
                "truncated": False,
                "tree": [
                    {
                        "type": "blob",
                        "path": "openspec/changes/restore-no-work-idle-discovery/design.md",
                        "sha": "7" * 40,
                    }
                ],
            }
        if path == f"git/trees/{head_tree}?recursive=1":
            return {
                "truncated": False,
                "tree": [
                    {
                        "type": "blob",
                        "path": "openspec/changes/restore-no-work-idle-discovery/design.md",
                        "sha": "7" * 40,
                    },
                    *[
                        {"type": "blob", "path": name, "sha": sha}
                        for name, sha in correction_files.items()
                        if scenario != "missing-current-file"
                        or name != "src/investment_strategy/scheduled_agent_effects.py"
                    ],
                    {"type": "blob", "path": "README.md", "sha": "6" * 40},
                ],
            }
        if path == f"commits/{head}/check-runs?per_page=100":
            checks = [
                {
                    "name": name,
                    "head_sha": head,
                    "conclusion": "success",
                    "details_url": f"https://github.com/{repository}/actions/runs/39795457767/job/111111111111",
                }
                for name in ("quality", "validate")
            ]
            return {"total_count": 2, "check_runs": checks}
        raise AssertionError(f"unexpected GitHub read: {path}")

    def github_io(
        repo: str,
        token: str,
        path: str,
        *,
        method: str = "GET",
        payload: Mapping[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object:
        nonlocal comment_posts, route_patches
        assert isinstance(allow_not_found, bool)
        if method == "POST" and path == "issues/322/comments":
            assert payload is not None and isinstance(payload.get("body"), str)
            comment_posts += 1
            comment = {
                "id": 6900000000,
                "body": payload["body"],
                "created_at": posted_at,
                "updated_at": posted_at,
                "user": {"login": "github-actions[bot]"},
                "performed_via_github_app": {"slug": "github-actions"},
            }
            comments.append(comment)
            timeline.append(
                {"id": 6900000000, "event": "commented", "created_at": comment["created_at"]}
            )
            if scenario == "lost-response":
                raise OSError("GitHub saved formal comment; client response lost")
            return comment
        if method == "PATCH" and path == "issues/322":
            assert payload is not None
            assert "action:review-implementation" in cast(list[str], payload["labels"])
            issue["labels"] = [{"name": label} for label in cast(list[str], payload["labels"])]
            timeline.extend(
                (
                    {
                        "id": 6900000001,
                        "event": "unlabeled",
                        "created_at": unlabel_at,
                        "label": {"name": "action:implement-change"},
                    },
                    {
                        "id": 6900000002,
                        "event": "labeled",
                        "created_at": label_at,
                        "label": {"name": "action:review-implementation"},
                        "actor": {"login": "github-actions[bot]"},
                        "performed_via_github_app": {"slug": "github-actions"},
                    },
                )
            )
            route_patches += 1
            return dict(issue)
        assert method == "GET"
        return read(repo, token, path)

    def transport_list(url: str, token: str) -> tuple[Mapping[str, object], ...]:
        assert token == REVISION
        assert url.startswith(f"https://api.github.com/repos/{repository}/")
        path = url.split(f"/{repository}/", 1)[1]
        if path == "issues?state=all&per_page=100&page=1":
            return (dict(issue),)
        if path == "issues/322/comments?per_page=100&sort=created&direction=desc":
            return tuple(reversed(comments))
        if path == "issues/322/timeline?per_page=100&page=1":
            return tuple(timeline)
        raise AssertionError(f"unexpected runtime listing: {path}")

    def transport_object(url: str, token: str) -> Mapping[str, object]:
        assert token == REVISION
        path = url.split(f"/{repository}", 1)[1].removeprefix("/")
        result = read(repository, token, path)
        assert isinstance(result, Mapping)
        return result

    def checkout_log(_repo: str, _token: str, job_id: int) -> str:
        assert job_id in {119881578427, 111111111111}
        log = cast(str, evidence["validator_log"])
        return log if job_id == 119881578427 else log.replace(_RECOVERY_R, head)

    monkeypatch.setattr(bridge, "_github_json", github_io)
    monkeypatch.setattr(
        bridge,
        "qualify_implementation_carrier",
        lambda **kwargs: (
            SimpleNamespace(
                disposition="HISTORICAL_MERGED" if merged_carrier else "QUALIFIED",
                head_sha=head,
            )
            if kwargs["pr_number"] == 353
            else None
        ),
    )
    monkeypatch.setattr(effects, "_github_json", github_io)
    monkeypatch.setattr(runtime, "_github_get_list_page", transport_list)
    monkeypatch.setattr(runtime, "_github_get_object", transport_object)
    review_defaults = bridge.read_recovery_openspec_review.__kwdefaults__
    assert review_defaults is not None
    monkeypatch.setitem(review_defaults, "log_read", checkout_log)
    monkeypatch.setitem(review_defaults, "thread_read", lambda *_: [])

    def invoke() -> bridge.ApplicationCompletion:
        return bridge.apply_original_322_recovery_exit(
            repository,
            REVISION,
            current_revision=merge_sha if merged_carrier else _RECOVERY_BASE,
            read=github_io,
            effect_apply=bridge.run_guarded_effect_application,
        )

    adoption = bridge.read_recovery_openspec_review(
        repository,
        REVISION,
        head_sha=head,
        approval_label_present=True,
        issue_comments=tuple(comments),
        read=github_io,
        log_read=checkout_log,
        thread_read=lambda *_: [],
    )
    assert adoption.disposition == ("UNKNOWN" if scenario == "unknown" else "COMPLETE"), adoption
    pre = bridge.qualify_original_322_pre_formal(
        repository=repository,
        token=REVISION,
        source=bridge.WorkerRequest(322, "executor", "implement-change"),
        record=record,
        issue_comments=tuple(comments),
        current_issue=issue,
        current_revision=merge_sha if merged_carrier else _RECOVERY_BASE,
        read=github_io,
    )
    # The deliberately conflicting, incomplete or unavailable historical
    # review-to-correction compare is irrelevant to this fresh formal effect.
    # A qualified current carrier and task frontier remain mandatory.
    assert pre.disposition == (
        "CONFLICT"
        if scenario == "no-current-approval"
        else "INCOMPLETE"
        if scenario == "missing-current-file"
        else "COMPLETE"
    ), pre.predicates
    assert "V" not in dict(pre.predicates)
    first = invoke()
    assert first.state == (
        "INVALID"
        if scenario in {"lost-response", "no-current-approval", "missing-current-file"}
        else "COMPLETE"
    ), first
    if scenario in {"no-current-approval", "missing-current-file"}:
        assert comment_posts == 0
        assert route_patches == 0
        return
    assert comment_posts == 1
    assert route_patches == (0 if scenario == "lost-response" else 1)
    second = invoke()
    assert second.state == "COMPLETE", second
    assert comment_posts == 1  # fresh-read reconciliation, no duplicate formal write
    assert route_patches == 1
    assert "action:review-implementation" in [
        label["name"] for label in cast(list[dict[str, object]], issue["labels"])
    ]
    fresh_wake = runtime.classify_dispatch(
        runtime.acquire_current_github_preflight(repository, REVISION)
    )
    assert fresh_wake.disposition == "AUTHORIZE", fresh_wake
    assert fresh_wake.selected_issue_id == 322
    assert fresh_wake.selected_routing == ("reviewer", "review-implementation")


def test_original_322_exit_incomplete_does_not_call_effect_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _effect_request_comment(
        comment_id=6019133874,
        created_at="2026-10-07T02:00:00Z",
        action="implement-change",
        role="executor",
        result_kind="ready",
        issue_number=322,
        change="restore-no-work-idle-discovery",
    )
    decision = _application_decision_comment(request, comment_id=6019173711)

    def read(_repository: str, _token: str, path: str) -> object:
        if path == "issues/322/comments?sort=created&direction=asc&per_page=100&page=1":
            return [decision]
        if path == "issues/322":
            return {"number": 322}
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_authorization_ancestry", lambda *_args, **_kw: ())
    monkeypatch.setattr(
        bridge,
        "qualify_original_322_pre_formal",
        lambda **_kw: bridge.RecoveryPreFormalQualification(
            "INCOMPLETE",
            (
                ("I", "COMPLETE"),
                ("R", "COMPLETE"),
                ("M", "INCOMPLETE"),
                ("V", "COMPLETE"),
                ("S", "COMPLETE"),
                ("F", "COMPLETE"),
            ),
        ),
    )
    result = bridge.apply_original_322_recovery_exit(
        "royhsu-work/investment-strategy",
        "token",
        current_revision=_RECOVERY_BASE,
        read=read,
        effect_apply=lambda *_args, **_kw: pytest.fail("incomplete must have NO_WRITE"),
    )
    assert result.state == "INVALID"
    assert result.reason == "recovery-exit-incomplete-M"
