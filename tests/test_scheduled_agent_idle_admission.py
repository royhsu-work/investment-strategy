from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from typing import cast

import pytest

from investment_strategy.scheduled_agent_idle_admission import (
    ACTION_EXPLORE_CHANGE,
    IDLE_REQUEST_MARKER,
    IdleAdmissionResult,
    IdleCandidate,
    IdleDispatchEnvelope,
    admit_idle_request,
    idle_admission_correlation,
    is_exact_no_work,
    make_idle_admission_request,
    parse_idle_admission_request,
    parse_idle_envelope,
    qualify_idle_handoff,
    render_idle_admission_request,
    render_idle_envelope,
)
from investment_strategy.workflow_dispatch import DispatchDecision, ObservationProvenance

REVISION = "a" * 40
DIGEST = "b" * 64
REPOSITORY = "owner/repository"


def _envelope() -> IdleDispatchEnvelope:
    return IdleDispatchEnvelope(
        repository=REPOSITORY,
        default_branch="main",
        request_comment_id=101,
        dispatch_run_id=202,
        dispatch_artifact_id=303,
        dispatch_artifact_sha256=DIGEST,
        default_branch_revision=REVISION,
    )


def _decision(disposition: str = "NO_WORK") -> DispatchDecision:
    return DispatchDecision(
        completeness="COMPLETE",
        observation_provenance=ObservationProvenance.QUALIFIED,
        formal_issue_ids=(),
        preactivation_candidate_ids=(),
        selected_issue_id=None,
        selected_routing=None,
        disposition=cast(object, disposition),  # type: ignore[arg-type]
        reason="no-routed-work" if disposition == "NO_WORK" else "selected-formal-action",
    )


def test_envelope_and_request_are_content_addressed_and_strict() -> None:
    envelope = _envelope()
    candidate = IdleCandidate(
        kind="new",
        source_kind="canonical-requirement",
        source_ref="openspec/spec.md#L10",
        source_revision=REVISION,
        evidence="material gap",
        title="Explore a bounded gap",
        body="Change: unset\n\nEvidence: material gap",
        labels=(ACTION_EXPLORE_CHANGE,),
    )
    request = make_idle_admission_request(envelope, candidate)
    assert request.correlation == idle_admission_correlation(envelope, candidate)
    assert parse_idle_envelope(render_idle_envelope(envelope)) == envelope
    assert parse_idle_admission_request(render_idle_admission_request(request)) == request
    assert parse_idle_admission_request(render_idle_admission_request(request) + "\nextra") is None

    payload = request.payload()
    cast(dict[str, object], payload["candidate"])["unexpected"] = True
    encoded = base64.b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    assert parse_idle_admission_request(f"{IDLE_REQUEST_MARKER}\nRequest-B64: {encoded}") is None


@pytest.mark.parametrize("disposition", ["AUTHORIZE", "FAIL_CLOSED"])
def test_only_exact_no_work_can_cross_idle_boundary(disposition: str) -> None:
    decision = _decision(disposition)
    assert not is_exact_no_work(decision)
    assert not qualify_idle_handoff(decision)
    assert not qualify_idle_handoff(
        DispatchDecision(
            completeness="INDETERMINATE",
            observation_provenance=ObservationProvenance.QUALIFIED,
            formal_issue_ids=(),
            preactivation_candidate_ids=(),
            selected_issue_id=None,
            selected_routing=None,
            disposition="NO_WORK",
            reason="no-routed-work",
        )
    )


def test_no_finding_is_silent_and_does_not_call_writer() -> None:
    request = make_idle_admission_request(_envelope(), IdleCandidate(kind="no-finding"))
    writes: list[Mapping[str, object]] = []
    result = admit_idle_request(
        request,
        read=lambda *_args: (_ for _ in ()).throw(AssertionError("no-finding must not read")),
        write=lambda *_args: writes.append(cast(Mapping[str, object], _args[-1])),
        fresh_dispatch=lambda: _decision(),
    )
    assert result == IdleAdmissionResult("NO_FINDING", "idle-no-finding")
    assert writes == []


def _github_root(path: str) -> object:
    if path == "":
        return {"default_branch": "main"}
    if path == "git/ref/heads/main":
        return {"object": {"sha": REVISION}}
    if path == "actions/runs/202":
        return {
            "id": 202,
            "name": "Scheduled Agent Dispatch 101",
            "path": ".github/workflows/scheduled-agent-bridge.yml",
            "event": "issue_comment",
            "head_sha": REVISION,
            "status": "completed",
            "conclusion": "success",
        }
    if path == "actions/runs/202/artifacts?per_page=100":
        return {
            "artifacts": [
                {
                    "id": 303,
                    "name": "dispatch-result.json",
                    "expired": False,
                    "digest": f"sha256:{DIGEST}",
                }
            ]
        }
    raise AssertionError(path)


def test_existing_candidate_is_admitted_once_and_preserves_unrelated_state() -> None:
    current: dict[str, object] = {
        "number": 11,
        "state": "open",
        "title": "Existing finding",
        "body": "Description without a Change line",
        "labels": [{"name": "bug"}, {"name": "advisory:idle"}],
    }
    request = make_idle_admission_request(
        _envelope(),
        IdleCandidate(
            kind="existing",
            source_kind="workflow-friction",
            source_ref="run:55",
            source_revision=REVISION,
            evidence="repeated failure",
            issue_number=11,
        ),
    )
    writes: list[tuple[str, Mapping[str, object]]] = []

    def read(_repository: str, _token: str, path: str) -> object:
        if path in {"", "git/ref/heads/main"}:
            return _github_root(path)
        if path.startswith("actions/runs/"):
            return _github_root(path)
        if path == "issues/11":
            return current
        raise AssertionError(path)

    def write(_repository: str, _token: str, path: str, payload: Mapping[str, object]) -> object:
        writes.append((path, payload))
        current["body"] = payload["body"]
        current["labels"] = [{"name": name} for name in cast(list[str], payload["labels"])]
        return current

    result = admit_idle_request(request, read=read, write=write, fresh_dispatch=lambda: _decision())
    assert result.state == "ADMITTED"
    assert len(writes) == 1
    assert writes[0][0] == "issues/11"
    assert writes[0][1]["labels"] == ["bug", "advisory:idle", ACTION_EXPLORE_CHANGE]
    assert cast(str, current["body"]).startswith("Change: unset\n")

    second = admit_idle_request(request, read=read, write=write, fresh_dispatch=lambda: _decision())
    assert second.state == "ALREADY_ADMITTED"
    assert len(writes) == 1


def test_existing_candidate_fails_closed_when_normal_work_wins_before_write() -> None:
    issue = {
        "number": 12,
        "state": "open",
        "body": "Change: unset\n",
        "labels": [{"name": "action:propose-change"}],
    }
    request = make_idle_admission_request(
        _envelope(),
        IdleCandidate(
            kind="existing",
            source_kind="required-defer",
            source_ref="issue:9",
            source_revision=REVISION,
            evidence="linked obligation",
            issue_number=12,
        ),
    )
    writes: list[object] = []

    def read(_repository: str, _token: str, path: str) -> object:
        if path in {"", "git/ref/heads/main"}:
            return _github_root(path)
        if path.startswith("actions/runs/"):
            return _github_root(path)
        if path == "issues/12":
            return issue
        raise AssertionError(path)

    result = admit_idle_request(
        request,
        read=read,
        write=lambda *_args: writes.append(_args[-1]),
        fresh_dispatch=lambda: _decision("AUTHORIZE"),
    )
    assert result.state == "FAIL_CLOSED"
    assert writes == []


def test_stale_default_branch_revision_is_rejected_before_idle_write() -> None:
    request = make_idle_admission_request(
        _envelope(),
        IdleCandidate(
            kind="existing",
            source_kind="friction",
            source_ref="run:56",
            source_revision=REVISION,
            evidence="repeated failure",
            issue_number=13,
        ),
    )
    writes: list[object] = []

    def read(_repository: str, _token: str, path: str) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path == "issues/13":
            return {
                "number": 13,
                "state": "open",
                "body": "Description",
                "labels": [],
            }
        if path.startswith("actions/runs/"):
            return _github_root(path)
        if path == "git/ref/heads/main":
            return {"object": {"sha": "c" * 40}}
        raise AssertionError(path)

    result = admit_idle_request(
        request,
        read=read,
        write=lambda *_args: writes.append(_args[-1]),
        fresh_dispatch=lambda: _decision(),
    )
    assert result.state == "STALE"
    assert result.reason == "idle-source-revision-stale"
    assert writes == []


def test_new_candidate_forms_one_complete_tuple_and_reconciles_next_wake() -> None:
    request = make_idle_admission_request(
        _envelope(),
        IdleCandidate(
            kind="new",
            source_kind="canonical-requirement",
            source_ref="openspec/spec.md#L10",
            source_revision=REVISION,
            evidence="material gap",
            title="New bounded finding",
            body="Change: unset\n\nEvidence: material gap",
            labels=(ACTION_EXPLORE_CHANGE,),
        ),
    )
    issues: list[dict[str, object]] = []
    writes: list[Mapping[str, object]] = []

    def read(_repository: str, _token: str, path: str) -> object:
        if path in {"", "git/ref/heads/main"}:
            return _github_root(path)
        if path.startswith("actions/runs/"):
            return _github_root(path)
        if path == "issues?state=open&per_page=100&page=1":
            return issues
        if path == "issues/77":
            return issues[0]
        raise AssertionError(path)

    def write(_repository: str, _token: str, path: str, payload: Mapping[str, object]) -> object:
        writes.append(payload)
        issue = {
            "number": 77,
            "state": "open",
            "title": payload["title"],
            "body": payload["body"],
            "labels": [{"name": label} for label in cast(list[str], payload["labels"])],
        }
        issues.append(issue)
        return issue

    result = admit_idle_request(request, read=read, write=write, fresh_dispatch=lambda: _decision())
    assert result.state == "ADMITTED"
    assert len(writes) == 1
    assert writes[0]["labels"] == [ACTION_EXPLORE_CHANGE]
    assert f"Idle-Admission-Correlation: {request.correlation}" in cast(str, writes[0]["body"])
    assert len(issues) == 1

    second = admit_idle_request(request, read=read, write=write, fresh_dispatch=lambda: _decision())
    assert second.state == "ALREADY_ADMITTED"
    assert len(writes) == 1


def test_new_ambiguous_write_fails_closed_without_blind_retry() -> None:
    request = make_idle_admission_request(
        _envelope(),
        IdleCandidate(
            kind="new",
            source_kind="friction",
            source_ref="run:88",
            source_revision=REVISION,
            evidence="repeated failure",
            title="Ambiguous finding",
            body="Change: unset",
            labels=(ACTION_EXPLORE_CHANGE,),
        ),
    )
    writes = 0

    def read(_repository: str, _token: str, path: str) -> object:
        if path in {"", "git/ref/heads/main"}:
            return _github_root(path)
        if path.startswith("actions/runs/"):
            return _github_root(path)
        if path == "issues?state=open&per_page=100&page=1":
            return []
        raise AssertionError(path)

    def write(*_args: object) -> object:
        nonlocal writes
        writes += 1
        raise RuntimeError("response lost")

    result = admit_idle_request(request, read=read, write=write, fresh_dispatch=lambda: _decision())
    assert result.state == "AMBIGUOUS"
    assert result.mutation_attempted
    assert writes == 1


def test_stale_candidate_source_is_rejected_before_repository_reads() -> None:
    with pytest.raises(ValueError):
        make_idle_admission_request(
            _envelope(),
            IdleCandidate(
                kind="new",
                source_kind="friction",
                source_ref="run:89",
                source_revision="c" * 40,
                evidence="stale",
                title="Stale",
                body="Change: unset",
                labels=(ACTION_EXPLORE_CHANGE,),
            ),
        )
