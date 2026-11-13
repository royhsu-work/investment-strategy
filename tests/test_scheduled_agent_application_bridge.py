"""Regression coverage for fresh repository-authorized application ingress."""

from __future__ import annotations

import base64
import hashlib
import importlib
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import FrozenInstanceError, replace
from datetime import date
from email.message import Message
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Literal, cast
from urllib.error import HTTPError
from urllib.request import Request

import pytest

import investment_strategy.scheduled_agent_application_bridge as bridge
import investment_strategy.scheduled_agent_carrier as carrier
import investment_strategy.scheduled_agent_runtime as runtime
from investment_strategy.scheduled_agent_action_model import (
    ApplicationRejection,
    ApplicationRejectionKind,
)
from investment_strategy.scheduled_agent_application_bridge import (
    APPLICATION_REQUEST_MARKER,
    AUTHORIZATION_REVISION_PREFIX,
    ApplicationRequest,
    application_continuation_correlation,
    parse_application_continuation_request,
    parse_application_request,
    plan_application,
    render_application_continuation_request,
)
from investment_strategy.scheduled_agent_carrier import CarrierRequired, make_carrier_plan
from investment_strategy.scheduled_agent_checkin import checkin_title
from investment_strategy.scheduled_agent_effects import (
    ApplicationDecisionRecord,
    EffectBatch,
    EffectRecoveryEvidence,
    GitHubEffectAdapter,
    StagedEffect,
    formal_application_correlation,
)
from investment_strategy.scheduled_agent_formal_qualification import (
    QualificationDecision,
    QualificationInput,
)
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    WorkerRequest,
    acquire_dispatch_preflight,
)
from investment_strategy.scheduled_agent_validation_resource import ValidationResourceTarget
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    ObservationProvenance,
    Routing,
)

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "4e3241d7d84a64012bf3b6218442128a4cb48d7a"
_CHANGE = "qualify-active-formal-consequences"
_TEST_PREDECESSOR_RUN_ID = 9001
_TEST_PREDECESSOR_RUN_ATTEMPT = 1
_TEST_PREDECESSOR_JOB_ID = 9002
_TEST_PREDECESSOR_ARTIFACT_ID = 9003
_TEST_PREDECESSOR_ARTIFACT_DIGEST = "sha256:" + "1" * 64
_TEST_FAILURE_EVIDENCE_SHA256 = "2" * 64
_TEST_RECOVERY_EPISODE_SHA256 = "3" * 64


@pytest.mark.parametrize(
    ("case", "expected_count"),
    [
        ("complete-default", 1),
        ("missing-job-attempt-valid", 1),
        ("complete-zero", 0),
        ("refreshed-complete", 2),
        ("paginated-complete", 101),
        ("missing-total", None),
        ("truncated-default", None),
        ("short-explicit-page", None),
        ("changed-page-count", None),
        ("duplicate-cross-page-id", None),
        ("wrong-cross-page-attempt", None),
        ("wrong-cross-page-run", None),
        ("unreadable-page", None),
    ],
)
def test_actions_job_inventory_requires_complete_exact_pages(
    case: str, expected_count: int | None
) -> None:
    """Only the shared, count-qualified source reader can prove job uniqueness."""

    run_id, run_attempt = 90001, 2
    observed: list[str] = []
    apply = {"id": 1, "name": "apply", "run_attempt": run_attempt}
    idle = {"id": 2, "name": "idle-admission", "run_attempt": run_attempt}
    hundred = [apply, idle] + [
        {"id": index, "name": "idle-admission", "run_attempt": run_attempt}
        for index in range(3, 101)
    ]

    def read(_repo: str, _token: str, path: str) -> object:
        observed.append(path)
        if path == f"actions/runs/{run_id}/attempts/{run_attempt}/jobs":
            if case == "complete-zero":
                return {"total_count": 0, "jobs": []}
            if case == "missing-total":
                return {"jobs": [apply]}
            if case == "complete-default":
                return {"total_count": 1, "jobs": [apply]}
            if case == "missing-job-attempt-valid":
                return {"total_count": 1, "jobs": [{"id": 1, "name": "apply", "run_id": run_id}]}
            if case == "truncated-default":
                return {"total_count": 2, "jobs": [apply]}
            return {"total_count": 2 if case == "refreshed-complete" else 101, "jobs": [apply]}
        if path == f"actions/runs/{run_id}/attempts/{run_attempt}/jobs?per_page=100&page=1":
            if case == "refreshed-complete":
                return {"total_count": 2, "jobs": [apply, idle]}
            if case == "truncated-default":
                return {"total_count": 2, "jobs": [apply]}
            if case == "short-explicit-page":
                return {"total_count": 101, "jobs": [apply]}
            return {"total_count": 101, "jobs": hundred}
        if path == f"actions/runs/{run_id}/attempts/{run_attempt}/jobs?per_page=100&page=2":
            if case == "unreadable-page":
                raise OSError("temporary read failure")
            if case == "changed-page-count":
                return {
                    "total_count": 102,
                    "jobs": [{"id": 101, "name": "apply", "run_attempt": 2}],
                }
            if case == "duplicate-cross-page-id":
                return {"total_count": 101, "jobs": [apply]}
            if case == "wrong-cross-page-attempt":
                return {
                    "total_count": 101,
                    "jobs": [{"id": 101, "name": "apply", "run_attempt": 1}],
                }
            if case == "wrong-cross-page-run":
                return {
                    "total_count": 101,
                    "jobs": [{"id": 101, "name": "apply", "run_id": run_id + 1}],
                }
            return {
                "total_count": 101,
                "jobs": [{"id": 101, "name": "idle-admission", "run_attempt": 2}],
            }
        raise AssertionError(path)

    qualified = carrier.github_complete_run_jobs(
        _REPOSITORY,
        "token",
        run_id=run_id,
        run_attempt=run_attempt,
        read=read,
    )
    assert (None if qualified is None else qualified.total_count) == expected_count
    if case in {"missing-total", "complete-default", "complete-zero", "missing-job-attempt-valid"}:
        assert observed == [f"actions/runs/{run_id}/attempts/{run_attempt}/jobs"]


def test_application_job_proof_is_immutable_and_independent_of_page_layout() -> None:
    """Reordering or a complete page split cannot change one admitted apply identity."""

    run_id, attempt = 880, 2
    endpoint = f"actions/runs/{run_id}/attempts/{attempt}/jobs"
    apply: dict[str, object] = {
        "id": 7,
        "name": "apply",
        "run_id": run_id,
        "run_attempt": attempt,
        "status": "completed",
        "conclusion": "failure",
        "steps": [{"name": "Persist exact external carrier plan", "conclusion": "skipped"}],
    }
    idle = [{"id": number, "name": "idle-admission"} for number in range(10, 110)]
    jobs = [apply, *idle]

    def paginated(_repo: str, _token: str, path: str) -> object:
        if path == endpoint:
            return {"total_count": 101, "jobs": [apply]}
        if path == f"{endpoint}?per_page=100&page=1":
            return {"total_count": 101, "jobs": idle}
        if path == f"{endpoint}?per_page=100&page=2":
            return {"total_count": 101, "jobs": [apply]}
        raise AssertionError(path)

    # A 101-item response on the default page cannot be a valid single page.
    # Use the same complete evidence with two different explicit page layouts.
    def explicit_reordered(_repo: str, _token: str, path: str) -> object:
        if path == endpoint:
            return {"total_count": 101, "jobs": [apply]}
        if path == f"{endpoint}?per_page=100&page=1":
            return {"total_count": 101, "jobs": list(reversed(jobs))[:100]}
        if path == f"{endpoint}?per_page=100&page=2":
            return {"total_count": 101, "jobs": list(reversed(jobs))[100:]}
        raise AssertionError(path)

    one = carrier.github_complete_run_jobs(
        _REPOSITORY, "token", run_id=run_id, run_attempt=attempt, read=paginated
    )
    reordered = carrier.github_complete_run_jobs(
        _REPOSITORY, "token", run_id=run_id, run_attempt=attempt, read=explicit_reordered
    )
    assert one is not None and reordered is not None
    assert one == reordered
    assert one.total_count == 101
    assert one.single_apply == carrier.QualifiedApplicationJob(
        7, "completed", "failure", (("Persist exact external carrier plan", "skipped"),)
    )
    with pytest.raises(FrozenInstanceError):
        one.single_apply.status = "success"  # type: ignore[misc,union-attr]
    cast(list[dict[str, str]], apply["steps"])[0]["conclusion"] = "success"
    assert one.single_apply == reordered.single_apply


def test_application_job_cardinality_and_temporary_read_failure_never_guess() -> None:
    """A second apply invalidates uniqueness; failure is not absence and can recover."""

    endpoint = "actions/runs/990/attempts/1/jobs"
    unique = {"id": 11, "name": "apply", "run_attempt": 1}
    duplicate = {"id": 12, "name": "apply", "run_attempt": 1}
    calls = 0

    def intermittent(_repo: str, _token: str, path: str) -> object:
        nonlocal calls
        assert path == endpoint
        calls += 1
        if calls == 1:
            raise OSError("transient GitHub GET failure")
        return {"total_count": 1, "jobs": [unique]}

    first = carrier.github_complete_run_jobs(
        _REPOSITORY, "token", run_id=990, run_attempt=1, read=intermittent
    )
    second = carrier.github_complete_run_jobs(
        _REPOSITORY, "token", run_id=990, run_attempt=1, read=intermittent
    )
    assert first is None  # indeterminate read, not proof of zero jobs
    assert second is not None and second.single_apply is not None
    assert second.single_apply.id == 11

    def observed(_repo: str, _token: str, path: str) -> object:
        assert path == endpoint
        return {"total_count": 2, "jobs": [duplicate, unique]}

    multiple = carrier.github_complete_run_jobs(
        _REPOSITORY, "token", run_id=990, run_attempt=1, read=observed
    )
    assert multiple is not None and multiple.total_count == 2
    assert tuple(job.id for job in multiple.apply_jobs) == (11, 12)
    assert multiple.single_apply is None


@pytest.mark.parametrize(
    ("module_name", "reader_kind"),
    [
        ("scheduled_agent_runtime", "object"),
        ("scheduled_agent_runtime", "list"),
        ("scheduled_agent_application_bridge", "json"),
        ("scheduled_agent_effects", "json"),
        ("issue_comment_bridge", "json"),
        ("scheduled_agent_application_carrier", "json"),
        ("scheduled_agent_dispatch_result", "json"),
        ("scheduled_agent_validation_resource", "json"),
        ("scheduled_agent_merge_acceptance", "json"),
        ("scheduled_agent_checkin", "json"),
        ("scheduled_agent_idle_admission", "json"),
        ("native_closing_merge_application", "json"),
    ],
)
@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_every_standard_github_get_uses_one_bounded_transport_contract(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    reader_kind: str,
    status: int,
) -> None:
    """Prevent another read adapter from silently bypassing the shared retry."""

    module = importlib.import_module(f"investment_strategy.{module_name}")
    requests: list[str] = []
    delays: list[float] = []

    def open_request(request: Request, *, timeout: int) -> BytesIO:
        assert timeout == 30
        requests.append(request.get_method())
        assert request.get_method() == "GET"
        if len(requests) < 3:
            raise HTTPError(request.full_url, status, "transient", Message(), None)
        return BytesIO(b"[]" if reader_kind == "list" else b"{}")

    monkeypatch.setattr(module, "urlopen", open_request)
    monkeypatch.setattr(module.time, "sleep", delays.append)
    if reader_kind == "object":
        result = module._github_get_object("https://api.github.com/repos/example/repo", "token")
    elif reader_kind == "list":
        result = module._github_get_list_page(
            "https://api.github.com/repos/example/repo/issues", "token"
        )
    else:
        result = module._github_json(_REPOSITORY, "token", "/issues/9")
    assert result == (() if reader_kind == "list" else {})
    assert requests == ["GET", "GET", "GET"]
    assert delays == [0.25, 0.5]


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_shared_github_transport_rejects_non_get_before_network(method: str) -> None:
    request = Request("https://api.github.com/repos/example/repo", method=method)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("non-GET attempted through the retryable transport")

    with pytest.raises(ValueError, match="only supports GET"):
        carrier.github_read_bytes_with_retry(request, open_request=forbidden, wait=forbidden)


@pytest.mark.parametrize(
    ("actor", "slug", "expected"),
    [
        ("royhsu-work", "chatgpt-codex-connector", True),
        ("github-actions[bot]", "github-actions", False),
        ("royhsu-work", "github-actions", False),
        ("someone-else", "chatgpt-codex-connector", False),
    ],
)
def test_shared_github_app_provenance_preserves_exact_identity(
    actor: str, slug: str, expected: bool
) -> None:
    comment: dict[str, object] = {
        "user": {"login": actor},
        "performed_via_github_app": {"slug": slug},
    }
    assert (
        carrier.github_comment_has_app_provenance(
            comment, actor="royhsu-work", app_slug="chatgpt-codex-connector"
        )
        is expected
    )


def test_shared_github_pager_reads_all_pages_and_keeps_query_identity() -> None:
    observed: list[str] = []

    def reader(_repo: str, _token: str, path: str) -> object:
        observed.append(path)
        if path.endswith("page=1"):
            return [{"id": index} for index in range(100)]
        return [{"id": 100}]

    items = carrier.github_paginated_mappings(
        _REPOSITORY,
        "token",
        "issues/55/comments?sort=created",
        read=reader,
        incomplete_error="incomplete list",
        malformed_error="malformed item",
    )
    assert len(items) == 101
    assert items[-1] == {"id": 100}
    assert observed == [
        "issues/55/comments?sort=created&per_page=100&page=1",
        "issues/55/comments?sort=created&per_page=100&page=2",
    ]


@pytest.mark.parametrize("invalid_page", [None, {}, ["not-a-mapping"]])
def test_shared_github_pager_refuses_partial_evidence(invalid_page: object) -> None:
    def reader(_repo: str, _token: str, path: str) -> object:
        return [{"id": index} for index in range(100)] if path.endswith("page=1") else invalid_page

    with pytest.raises(RuntimeError, match="incomplete list|malformed item"):
        carrier.github_paginated_mappings(
            _REPOSITORY,
            "token",
            "issues/55/comments",
            read=reader,
            incomplete_error="incomplete list",
            malformed_error="malformed item",
        )


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (
            {
                "reason": "carrier_required",
                "unfinished_boundary": "carrier-required",
                "mutation_status": "not-complete",
                "carrier_plan_id": "carrier-identity",
                "completed_effect_indexes": [],
                "completed_effect_sha256": [],
            },
            "RECONCILE_EFFECTS",
        ),
        (
            {
                "reason": "effect precondition rejected",
                "unfinished_boundary": "effect-precondition",
                "mutation_status": "not-complete",
                "failed_effect_index": 0,
                "failed_effect_kind": "github-mutation",
                "failed_effect_sha256": "a" * 64,
                "completed_effect_indexes": [],
                "completed_effect_sha256": [],
                "rejection": {"classification": "effect-precondition-unsatisfied"},
            },
            "ZERO_WRITE_REJECTION",
        ),
        (
            {
                "reason": "effect precondition rejected",
                "unfinished_boundary": "effect-precondition",
                "mutation_status": "unknown",
                "failed_effect_index": 0,
                "failed_effect_sha256": "a" * 64,
                "completed_effect_indexes": [],
                "completed_effect_sha256": [],
                "rejection": {"classification": "effect-precondition-unsatisfied"},
            },
            "INDETERMINATE",
        ),
        (
            {
                "reason": "effect precondition rejected",
                "unfinished_boundary": "effect-precondition",
                "mutation_status": "not-complete",
                "failed_effect_index": 0,
                "failed_effect_sha256": "a" * 64,
                "completed_effect_indexes": [1],
                "completed_effect_sha256": ["b" * 64],
                "rejection": {"classification": "effect-precondition-unsatisfied"},
            },
            "INDETERMINATE",
        ),
    ],
)
def test_continuation_classifies_effect_boundary_before_correction(
    failure: dict[str, object], expected: str
) -> None:
    """Carrier-complete and zero-write rejection must not share a recovery branch."""
    predecessor = bridge.ApplicationRecoveryArtifact(
        run_id=1,
        run_attempt=1,
        job_id=2,
        artifact_id=3,
        artifact_digest="sha256:" + "d" * 64,
        request_comment_id=4,
        accepted_decision_sha256="e" * 64,
        failure_evidence_sha256="f" * 64,
        recovery_episode_sha256="c" * 64,
        recovery_attempt=1,
        continuation_eligible=True,
        document={"failure_evidence": failure},
    )
    assert bridge._accepted_predecessor_disposition(predecessor) == expected


@pytest.mark.parametrize("effect_complete", [False, True])
def test_post_effect_result_recovery_requires_exact_accepted_materialization_proof(
    monkeypatch: pytest.MonkeyPatch, effect_complete: bool
) -> None:
    source = WorkerRequest(138, "lead", "propose-change")
    materialization = {
        "issue_number": 138,
        "operation": "application-materialize",
        "expected_change": "unset",
        "change": "restore-example",
        "branch": "agent/restore-example",
        "base_sha": _REVISION,
        "message": "OpenSpec proposal",
        "files": [
            {
                "path": "openspec/changes/restore-example/proposal.md",
                "blob_sha": "b" * 40,
                "expected_sha": None,
            }
        ],
        "pr_number": None,
    }
    worker = _worker_result(
        action=source.action, role=source.role, result_kind="ready-for-openspec-review"
    )
    worker["requested_effects"] = [
        {"kind": "github-mutation", "payload_json": json.dumps(materialization)}
    ]
    raw = json.dumps(worker, sort_keys=True)
    accepted = _accepted_record(
        raw,
        _effect_request(worker),
        source=source,
        change="unset",
        result_kind="ready-for-openspec-review",
    )
    failure = {
        "reason": "applied",
        "mutation_status": "unknown",
        "unfinished_boundary": "application-result",
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
    }
    artifact = bridge.ApplicationRecoveryArtifact(
        run_id=1,
        run_attempt=1,
        job_id=2,
        artifact_id=3,
        artifact_digest="sha256:" + "a" * 64,
        request_comment_id=accepted.request_comment_id,
        accepted_decision_sha256="c" * 64,
        failure_evidence_sha256="d" * 64,
        recovery_episode_sha256="e" * 64,
        recovery_attempt=1,
        continuation_eligible=False,
        document={
            "failure_evidence": failure,
            "issue_number": source.issue_number,
            "role": source.role,
            "action": source.action,
            "authorization_revision": _REVISION,
        },
    )
    reads: list[str] = []

    def read(_repo: str, _token: str, path: str, **_kw: object) -> dict[str, object]:
        reads.append(path)
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": _REVISION}}
        pytest.fail(f"unexpected GitHub read: {path}")

    observations: list[dict[str, object]] = []

    def prove(payload: dict[str, object], *_args: object, **_kwargs: object) -> object:
        observations.append(payload)
        return SimpleNamespace(
            disposition="COMPLETE" if effect_complete else "INCOMPLETE",
            reason=None,
            application_request=None,
            carrier_plan=None,
        )

    monkeypatch.setattr(bridge, "_github_json", read)
    monkeypatch.setattr(
        bridge,
        "_accepted_worker_result_for_continuation",
        lambda **kwargs: (
            raw if kwargs["accepted_intent"] is accepted else pytest.fail("wrong intent")
        ),
    )
    monkeypatch.setattr(bridge, "prove_materialization", prove)
    assert bridge._accepted_recovery_boundary(failure) == "POST_EFFECT_RESULT"
    assert bridge._accepted_predecessor_disposition(artifact) == "INDETERMINATE"
    proof = bridge.classify_post_effect_result_recovery(
        record=accepted, artifact=artifact, repository=_REPOSITORY, token=_REPOSITORY
    )
    assert (proof.continuation == "CONTINUE") is effect_complete
    assert reads == ["", "git/ref/heads/main"]
    assert len(observations) == 1
    assert observations[0] == materialization
    assert artifact.continuation_eligible is False  # immutable historical evidence


@pytest.mark.parametrize(
    "invalid",
    [
        {"reason": "unknown"},
        {"unfinished_boundary": "effect-postcondition"},
        {"mutation_status": "not-complete"},
        {"completed_effect_indexes": [0]},
        {"unexpected": "an untrusted override"},
    ],
)
def test_post_effect_result_recovery_rejects_unqualified_shape(invalid: dict[str, object]) -> None:
    evidence: dict[str, object] = {
        "reason": "applied",
        "mutation_status": "unknown",
        "unfinished_boundary": "application-result",
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
    }
    evidence.update(invalid)
    assert bridge._accepted_recovery_boundary(evidence) == "NONE"


@pytest.mark.parametrize("post_effect_state", ["COMPLETE", "MISSING_PR"])
@pytest.mark.parametrize("artifact_kind", ["recovery", "exception"])
def test_post_effect_result_continuation_uses_original_435_effect_not_formal_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    post_effect_state: str,
    artifact_kind: str,
) -> None:
    """Production #435: one accepted Git write plus an Application-owned result.

    The exact run 42827477053 was rejected before reconciliation because its
    freshly projected batch had two effects.  No GitHub write is permitted by
    this test; the boundary must instead reach the original-effect observer.
    """
    source = WorkerRequest(435, "lead", "propose-change")
    change = "restore-t1-dispatch-artifact-consumption"
    accepted_revision = "8bf5007c4dc6fb8368473af3aba86dbe5136a627"
    current_revision = "2b57c5d4af488bdd583a66c1f72d65713a594928"
    materialization = {
        "issue_number": 435,
        "operation": "application-materialize",
        "expected_change": "unset",
        "change": change,
        "branch": f"agent/{change}",
        "base_sha": accepted_revision,
        "message": "OpenSpec: restore exact T1 dispatch Artifact consumption (Refs #435)",
        "files": [
            {
                "path": f"openspec/changes/{change}/proposal.md",
                "blob_sha": "1ab7b8c1fee8403b77c3c6010a8cd46fcb4e36c4",
                "expected_sha": None,
            },
            {
                "path": f"openspec/changes/{change}/design.md",
                "blob_sha": "6e0b33f9e939401ca1ce8f7983800279641182a7",
                "expected_sha": None,
            },
            {
                "path": f"openspec/changes/{change}/tasks.md",
                "blob_sha": "af25a5fd1f668e3e30b0119a2a1a62887db3f68e",
                "expected_sha": None,
            },
            {
                "path": f"openspec/changes/{change}/specs/scheduled-agent-workflow/spec.md",
                "blob_sha": "bfd977c5d29e7a294de6a5fd3ba040e174760b48",
                "expected_sha": None,
            },
        ],
        "pr_number": None,
    }
    raw_worker = _worker_result(
        action="propose-change", role="lead", result_kind="ready-for-openspec-review"
    )
    raw_worker["issue_number"] = 435
    raw_worker["requested_effects"] = [
        {"kind": "github-mutation", "payload_json": json.dumps(materialization)}
    ]
    original = json.dumps(raw_worker, sort_keys=True)
    projected = json.loads(original)
    projected["requested_effects"].append(
        {
            "kind": "issue-comment",
            "payload_json": json.dumps({"issue_number": 435, "body": "ACTION_RESULT\nformal"}),
        }
    )
    projected_raw = json.dumps(projected, sort_keys=True)
    assert len(bridge.parse_effect_batch(original, source, authorized_change="unset").effects) == 1
    assert (
        len(bridge.parse_effect_batch(projected_raw, source, authorized_change="unset").effects)
        == 2
    )

    accepted = bridge.replace(
        _accepted_record(
            original,
            _effect_request(raw_worker, revision=accepted_revision),
            source=source,
            change="unset",
            result_kind="ready-for-openspec-review",
        ),
        authorization_revision=accepted_revision,
    )
    decision_body = "exact accepted decision #435"
    decision_digest = hashlib.sha256(decision_body.encode()).hexdigest()
    failure = {
        "reason": "applied",
        "mutation_status": "unknown",
        "unfinished_boundary": "application-result",
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
    }
    artifact: bridge.ApplicationRecoveryArtifact | bridge.ApplicationExceptionArtifact
    if artifact_kind == "exception":
        artifact = bridge.ApplicationExceptionArtifact(
            run_id=42827477053,
            run_attempt=1,
            job_id=129868554969,
            artifact_id=13768983651,
            artifact_digest="sha256:" + "a" * 64,
            request_comment_id=accepted.request_comment_id,
            accepted_decision_sha256=decision_digest,
            failure_evidence_sha256="b" * 64,
            recovery_episode_sha256="c" * 64,
            document={"schema": "scheduled-agent-execution-exception/v1"},
        )
    else:
        artifact = bridge.ApplicationRecoveryArtifact(
            run_id=42803777801,
            run_attempt=1,
            job_id=1,
            artifact_id=2,
            artifact_digest="sha256:" + "a" * 64,
            request_comment_id=accepted.request_comment_id,
            accepted_decision_sha256=decision_digest,
            failure_evidence_sha256="b" * 64,
            recovery_episode_sha256="c" * 64,
            recovery_attempt=1,
            continuation_eligible=False,
            document={"failure_evidence": failure},
        )
    continuation_body = render_application_continuation_request(
        repository=_REPOSITORY,
        issue_number=435,
        original_request_comment_id=accepted.request_comment_id,
        accepted_decision_sha256=decision_digest,
        predecessor_run_id=artifact.run_id,
        predecessor_run_attempt=artifact.run_attempt,
        predecessor_job_id=artifact.job_id,
        predecessor_artifact_id=artifact.artifact_id,
        predecessor_artifact_digest=artifact.artifact_digest,
        failure_evidence_sha256=artifact.failure_evidence_sha256,
        recovery_episode_sha256=artifact.recovery_episode_sha256,
    )
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(_event(continuation_body, comment_id=203)), encoding="utf-8")
    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scheduled_agent_application_bridge",
            "--event-path",
            str(event_path),
            "--revision",
            current_revision,
            "--default-branch",
            "main",
        ],
    )
    monkeypatch.setattr(bridge, "_fresh_event_observation", lambda *_args: False)
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(action="propose-change", issue_number=435),
    )
    monkeypatch.setattr(
        bridge, "_find_application_decision_from_current_frontier", lambda **_kwargs: accepted
    )
    monkeypatch.setattr(
        bridge,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (accepted, decision_body),
    )
    monkeypatch.setattr(
        bridge, "qualify_application_continuation_predecessor", lambda *_args, **_kwargs: artifact
    )
    monkeypatch.setattr(
        bridge, "_accepted_worker_result_for_continuation", lambda **_kwargs: original
    )
    monkeypatch.setattr(
        bridge,
        "plan_application",
        lambda **_kwargs: SimpleNamespace(
            should_apply=True,
            source=source,
            raw_worker_result=original,
            request_comment_id=accepted.request_comment_id,
            change="unset",
            pending_application_correlation=None,
            pending_continuation=True,
        ),
    )
    monkeypatch.setattr(
        bridge, "_fresh_application_worker_result", lambda *_args, **_kwargs: projected_raw
    )
    monkeypatch.setattr(bridge, "_repair_partial_first_activation_route", lambda **_kwargs: False)

    class ReachedOriginalEffectReconciliation(Exception):
        pass

    def reconcile(*_args: object, **_kwargs: object) -> None:
        if post_effect_state == "MISSING_PR":
            pytest.fail("an already durable accepted branch may emit only the missing PR carrier")
        assert _kwargs["reconcile_only"] is True
        assert _kwargs["uncertain_effect_index"] == 0
        raise ReachedOriginalEffectReconciliation

    monkeypatch.setattr(bridge, "run_guarded_effect_application", reconcile)
    missing_pr_plan = make_carrier_plan(
        repository=_REPOSITORY,
        issue_number=435,
        change=change,
        action="propose-change",
        authorization_revision=current_revision,
        operation="pull-request-create",
        target={"repository": _REPOSITORY, "head_ref": f"agent/{change}", "base_ref": "main"},
        expected={"head_sha": "c" * 40, "base_sha": current_revision, "existing_pr_count": 0},
        requested={"head": f"agent/{change}", "base": "main", "head_sha": "c" * 40},
        expected_postcondition={"head_sha": "c" * 40, "base_sha": current_revision},
    )
    monkeypatch.setattr(
        bridge,
        "_observe_accepted_post_effect_result",
        lambda **_kwargs: (
            bridge.AcceptedPostEffectProof("MISSING_PR", "verified original", missing_pr_plan)
            if post_effect_state == "MISSING_PR"
            else bridge.AcceptedPostEffectProof("COMPLETE", "verified original")
        ),
    )
    if post_effect_state == "COMPLETE":
        with pytest.raises(ReachedOriginalEffectReconciliation):
            bridge._main_unprotected(bridge.ApplicationExceptionContext())
    else:
        outputs: list[bridge.ApplyResult] = []
        monkeypatch.setattr(bridge, "_write_carrier_outputs", outputs.append)
        monkeypatch.setattr(bridge, "_write_validation_outputs", lambda *_args: None)
        monkeypatch.setattr(bridge, "_write_application_recovery_evidence", lambda *_a, **_k: True)
        assert bridge._main_unprotected(bridge.ApplicationExceptionContext()) == 0
        assert len(outputs) == 1
        assert outputs[0].carrier_plan == missing_pr_plan
        assert outputs[0].reason == "carrier_required"


@pytest.mark.parametrize(
    ("original_extra", "projected_extra", "expected", "index"),
    [
        ("none", "formal", "EXACT", 0),
        ("none", "formal-first", "EXACT", 1),
        ("none", "none", "EXACT", 0),
        ("duplicate", "formal", "AMBIGUOUS", None),
        ("foreign-write", "formal", "UNSAFE", None),
        ("original-comment", "formal", "UNSAFE", None),
        ("missing", "formal", "MISSING", None),
        ("none", "missing", "MISSING", None),
        ("none", "duplicate", "AMBIGUOUS", None),
        ("none", "foreign-write", "UNSAFE", None),
    ],
)
def test_accepted_activation_identity_contract_table(
    original_extra: str, projected_extra: str, expected: str, index: int | None
) -> None:
    """One canonical decision table: identity comes from intent, never order."""
    source = WorkerRequest(435, "lead", "propose-change")
    change = "restore-t1-dispatch-artifact-consumption"
    original_effect = {
        "kind": "github-mutation",
        "payload_json": json.dumps(
            {
                "issue_number": 435,
                "operation": "application-materialize",
                "expected_change": "unset",
                "change": change,
                "branch": f"agent/{change}",
                "base_sha": _REVISION,
                "message": "OpenSpec: restore exact Artifact consumption (Refs #435)",
                "files": [
                    {
                        "path": f"openspec/changes/{change}/proposal.md",
                        "blob_sha": "b" * 40,
                        "expected_sha": None,
                    }
                ],
                "pr_number": None,
            },
            sort_keys=True,
        ),
    }
    foreign = {
        "kind": "github-mutation",
        "payload_json": json.dumps({"issue_number": 435, "operation": "issue-label-add"}),
    }
    comment = {
        "kind": "issue-comment",
        "payload_json": json.dumps({"issue_number": 435, "body": "ACTION_RESULT\nformal"}),
    }
    originals = [original_effect]
    if original_extra == "missing":
        originals = []
    elif original_extra == "duplicate":
        originals.append(original_effect)
    elif original_extra == "foreign-write":
        originals.append(foreign)
    elif original_extra == "original-comment":
        originals.append(comment)
    projection = [original_effect]
    if projected_extra == "formal":
        projection.append(comment)
    elif projected_extra == "formal-first":
        projection.insert(0, comment)
    elif projected_extra == "missing":
        projection = [comment]
    elif projected_extra == "duplicate":
        projection.append(original_effect)
    elif projected_extra == "foreign-write":
        projection.append(foreign)

    def render(effects: list[dict[str, str]]) -> str:
        worker = _worker_result(
            action="propose-change", role="lead", result_kind="ready-for-openspec-review"
        )
        worker["issue_number"] = 435
        worker["requested_effects"] = effects
        return json.dumps(worker)

    identity = bridge._accepted_activation_effect_identity(
        render(originals),
        source=source,
        change="unset",
        projected_raw=render(projection),
    )
    assert identity.disposition == expected
    assert identity.projected_index == index
    assert (identity.effect is not None) is (expected == "EXACT")


@pytest.mark.parametrize(
    ("materialization_status", "recovery_status", "admission"),
    [
        ("COMPLETE", "COMPLETE", "CONTINUE"),
        ("INCOMPLETE", "NOT_APPLIED", "REJECT"),
        ("UNKNOWN", "INDETERMINATE", "OBSERVE"),
        ("CONTRADICTORY", "UNSAFE", "REJECT"),
    ],
)
def test_post_effect_result_uses_existing_typed_materialization_proof(
    monkeypatch: pytest.MonkeyPatch,
    materialization_status: str,
    recovery_status: str,
    admission: str,
) -> None:
    """All four proof outcomes retain their distinct safety/liveness meaning."""
    source = WorkerRequest(435, "lead", "propose-change")
    materialization = {
        "issue_number": 435,
        "operation": "application-materialize",
        "expected_change": "unset",
        "change": "restore-t1-dispatch-artifact-consumption",
        "branch": "agent/restore-t1-dispatch-artifact-consumption",
        "base_sha": _REVISION,
        "message": "OpenSpec: restore exact Artifact consumption (Refs #435)",
        "files": [
            {
                "path": "openspec/changes/restore-t1-dispatch-artifact-consumption/proposal.md",
                "blob_sha": "b" * 40,
                "expected_sha": None,
            }
        ],
        "pr_number": None,
    }
    original = _worker_result(
        action="propose-change", role="lead", result_kind="ready-for-openspec-review"
    )
    original["issue_number"] = 435
    original["requested_effects"] = [
        {"kind": "github-mutation", "payload_json": json.dumps(materialization)}
    ]
    raw = json.dumps(original)
    accepted = _accepted_record(
        raw,
        _effect_request(original),
        source=source,
        change="unset",
        result_kind="ready-for-openspec-review",
    )
    calls: list[str] = []
    current = [materialization_status]

    def prove(*_args: object, **kwargs: object) -> object:
        calls.append(str(kwargs["accepted_authorization_revision"]))
        return SimpleNamespace(
            disposition=current[0], reason=None, application_request=None, carrier_plan=None
        )

    monkeypatch.setattr(bridge, "_accepted_worker_result_for_continuation", lambda **_kw: raw)
    monkeypatch.setattr(bridge, "prove_materialization", prove)

    def observe() -> bridge.AcceptedPostEffectProof:
        return bridge._observe_accepted_post_effect_result(
            record=accepted,
            source=source,
            repository=_REPOSITORY,
            token=_REVISION,
            current_revision=_REVISION,
            default_branch="main",
        )

    decision = observe()
    assert decision.disposition == recovery_status
    assert decision.continuation == admission
    # After a transient failure or an incomplete materialization, a later
    # fresh read can observe completion without replay or changing the intent.
    current[0] = "COMPLETE"
    assert observe().disposition == "COMPLETE"
    assert calls == [_REVISION, _REVISION]


@pytest.mark.parametrize("head_matches", [False, True])
def test_lead_retirement_rebinding_preserves_original_exact_head(
    monkeypatch: pytest.MonkeyPatch, head_matches: bool
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    current_head = "b" * 40
    proposed_head = current_head if head_matches else "c" * 40
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda _repo, _token, path: (
            {
                "number": 418,
                "head": {"sha": current_head},
            }
            if path == "pulls/418"
            else pytest.fail(f"unexpected GitHub request: {path}")
        ),
    )
    effect = {
        "kind": "github-mutation",
        "payload_json": json.dumps(
            {
                "issue_number": 138,
                "operation": "pull-request-update",
                "number": 418,
                "expected_head_sha": proposed_head,
                "fields": {"state": "closed"},
            }
        ),
    }

    def invocation() -> object:
        return bridge._fresh_control_effect(
            raw_effect=effect,
            source=source,
            change=_CHANGE,
            repository=_REPOSITORY,
            token="test-token",  # noqa: S106
            current_revision=_REVISION,
            default_branch="main",
        )

    if head_matches:
        assert invocation() == {
            "issue_number": 138,
            "operation": "pull-request-update",
            "number": 418,
            "expected_head_sha": current_head,
            "fields": {"state": "closed"},
        }
    else:
        with pytest.raises(RuntimeError, match="retirement expected HEAD is stale"):
            invocation()


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH"])
def test_application_read_retry_does_not_repeat_write_after_gateway_timeout(
    monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    attempts: list[str] = []
    delays: list[float] = []

    def urlopen(request: Request, *, timeout: int) -> BytesIO:
        assert timeout == 30
        attempts.append(request.get_method())
        if method == "GET" and len(attempts) == 3:
            return BytesIO(b'{"ok":true}')
        raise HTTPError(request.full_url, 504, "Gateway Timeout", Message(), None)

    monkeypatch.setattr(bridge, "urlopen", urlopen)
    monkeypatch.setattr(bridge.time, "sleep", delays.append)
    if method == "GET":
        assert bridge._github_json(_REPOSITORY, "test-token", "pulls/418") == {"ok": True}
        assert attempts == ["GET"] * 3
        assert delays == [0.25, 0.5]
    else:
        with pytest.raises(HTTPError, match="504"):
            bridge._github_json(
                _REPOSITORY,
                "test-token",
                "issues/322",
                method=method,
                payload={"example": True},
            )
        assert attempts == [method]
        assert delays == []


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_preflight_paged_issue_get_retries_gateway_failure_without_losing_page(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """A transient GET failure cannot strand first-activation preflight."""
    calls: list[str] = []
    delays: list[float] = []

    def urlopen(request: Request, *, timeout: int) -> BytesIO:
        assert timeout == 30
        calls.append(request.get_method())
        assert request.full_url.endswith("issues?state=all&per_page=100&page=1")
        if len(calls) < 3:
            raise HTTPError(request.full_url, status, "transient", Message(), None)
        return BytesIO(b'[{"number": 435, "state": "open"}]')

    monkeypatch.setattr(runtime, "urlopen", urlopen)
    monkeypatch.setattr(runtime.time, "sleep", delays.append)
    pages = runtime._github_issue_pages(_REPOSITORY, "test-token")
    assert len(pages) == 1
    assert pages[0][0]["number"] == 435
    assert calls == ["GET", "GET", "GET"]
    assert delays == [0.25, 0.5]


@pytest.mark.parametrize(("status", "expected_attempts"), [(502, 3), (401, 1), (404, 1)])
def test_preflight_get_failure_exhaustion_never_returns_partial_issue_state(
    monkeypatch: pytest.MonkeyPatch, status: int, expected_attempts: int
) -> None:
    calls: list[str] = []
    delays: list[float] = []

    def urlopen(request: Request, *, timeout: int) -> BytesIO:
        assert timeout == 30
        calls.append(request.get_method())
        raise HTTPError(request.full_url, status, "denied or unavailable", Message(), None)

    monkeypatch.setattr(runtime, "urlopen", urlopen)
    monkeypatch.setattr(runtime.time, "sleep", delays.append)
    with pytest.raises(HTTPError) as raised:
        runtime._github_issue_pages(_REPOSITORY, "test-token")
    assert raised.value.code == status
    assert calls == ["GET"] * expected_attempts
    assert delays == ([0.25, 0.5] if expected_attempts == 3 else [])


@pytest.mark.parametrize(
    ("variant", "expected_downloads"),
    [
        ("valid", 1),
        ("digest-mismatch", 1),
        ("wrong-run", 0),
        ("expired", 0),
        ("bad-artifact-id", 0),
        ("bad-json", 1),
        ("bad-utf8", 1),
        ("oversized", 1),
    ],
)
def test_application_artifact_shared_verified_bytes_contract(
    variant: str, expected_downloads: int
) -> None:
    """Recovery and execution-exception readers must use identical byte proof.

    Metadata never authorizes a download if run identity is contradictory;
    integrity/size/JSON checks use the same single source of truth.
    """
    raw = b'{"schema":"native-application-evidence"}'
    if variant == "bad-json":
        raw = b"not valid json"
    elif variant == "bad-utf8":
        raw = b"\xff"
    elif variant == "oversized":
        raw = b"x" * (bridge._MAX_APPLICATION_RECOVERY_BYTES + 1)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    metadata: dict[str, object] = {
        "id": 7401,
        "digest": digest,
        "expired": False,
        "workflow_run": {"id": 7001, "head_sha": _REVISION},
    }
    if variant == "wrong-run":
        metadata["workflow_run"] = {"id": 7002, "head_sha": _REVISION}
    elif variant == "expired":
        metadata["expired"] = True
    elif variant == "bad-artifact-id":
        metadata["id"] = False
    elif variant == "digest-mismatch":
        metadata["digest"] = "sha256:" + "0" * 64
    downloads: list[str] = []

    def download(repository: str, token: str, path: str) -> bytes:
        assert (repository, token) == (_REPOSITORY, "test-token")
        downloads.append(path)
        return raw

    proven = bridge._read_verified_application_artifact(
        _REPOSITORY,
        "test-token",
        metadata=metadata,
        run_id=7001,
        run_head_sha=_REVISION,
        download=download,
    )
    if variant == "valid":
        assert proven == (7401, digest, {"schema": "native-application-evidence"})
    else:
        assert proven is None
    assert downloads == ["actions/artifacts/7401/zip"] * expected_downloads


def test_application_artifact_reader_uses_github_api_media_type_for_raw_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub's artifact API rejects octet-stream before issuing its redirect."""
    signed = "https://results.actions.githubusercontent.com/raw-artifact"
    raw = b'{"schema":"application-recovery"}\n'
    observed: list[str] = []

    class ApiOpener:
        def open(self, request: Request, timeout: int) -> BytesIO:
            assert timeout == 30
            observed.append("api")
            assert request.get_header("Authorization") == "Bearer test-token"
            if request.get_header("Accept") != "application/vnd.github+json":
                raise HTTPError(request.full_url, 415, "Unsupported Media Type", Message(), None)
            headers = Message()
            headers["Location"] = signed
            raise HTTPError(request.full_url, 302, "Found", headers, None)

    class RedirectOpener:
        def open(self, request: Request, timeout: int) -> BytesIO:
            assert timeout == 30
            observed.append("redirect")
            assert request.full_url == signed
            assert request.get_header("Authorization") is None
            return BytesIO(raw)

    monkeypatch.setattr(
        carrier,
        "build_opener",
        lambda *handlers: ApiOpener() if handlers else RedirectOpener(),
    )
    assert (
        carrier.read_github_artifact_bytes(
            _REPOSITORY, "test-token", "actions/artifacts/13034637193/zip"
        )
        == raw
    )
    assert observed == ["api", "redirect"]


@pytest.mark.parametrize(
    ("api_path", "expected_url"),
    [
        ("", "https://api.github.com/repos/royhsu-work/investment-strategy"),
        ("/pulls/390", "https://api.github.com/repos/royhsu-work/investment-strategy/pulls/390"),
    ],
)
def test_application_github_url_has_exact_root_and_nonempty_path(
    monkeypatch: pytest.MonkeyPatch, api_path: str, expected_url: str
) -> None:
    visited: list[str] = []

    def github_get(request: Request, *, timeout: int) -> BytesIO:
        assert timeout == 30
        url = request.full_url
        visited.append(url)
        if url.endswith("/investment-strategy/"):
            raise HTTPError(url, 404, "repository root with trailing slash", Message(), None)
        return BytesIO(b'{"default_branch":"main"}')

    monkeypatch.setattr(bridge, "urlopen", github_get)
    assert bridge._github_json(_REPOSITORY, "token", api_path) == {"default_branch": "main"}
    assert visited == [expected_url]


def test_preaccept_404_keeps_exception_evidence_and_never_forges_accept(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = WorkerRequest(322, "executor", "merge-implementation-pr")
    worker = _worker_result(action=source.action, role=source.role, result_kind="merged")
    worker["issue_number"] = source.issue_number
    worker["change"] = "restore-no-work-idle-discovery"
    request_body = _effect_request(worker)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(_event(request_body)), encoding="utf-8")
    evidence_path = tmp_path / "execution-exception.json"
    output_path = tmp_path / "github-output.txt"
    github_comments: list[dict[str, object]] = []
    mutations: list[str] = []

    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "test-private-token")
    monkeypatch.setenv("GITHUB_RUN_ID", "41036535846")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
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
            "--exception-evidence-path",
            str(evidence_path),
        ],
    )
    monkeypatch.setattr(bridge, "_fresh_event_observation", lambda *_args: False)
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(
            issue_number=322, action=source.action, change="restore-no-work-idle-discovery"
        ),
    )
    monkeypatch.setattr(
        bridge,
        "plan_application",
        lambda **_kwargs: bridge.ApplicationPlan(
            should_apply=True,
            source=source,
            raw_worker_result=json.dumps(worker),
            change="restore-no-work-idle-discovery",
            request_comment_id=102,
        ),
    )

    def failed_qualification(*_args: object, **_kwargs: object) -> str:
        raise HTTPError(
            "https://api.github.com/repos/owner/repo/", 404, "Not Found", Message(), None
        )

    monkeypatch.setattr(bridge, "_fresh_application_worker_result", failed_qualification)
    monkeypatch.setattr(
        bridge,
        "run_guarded_effect_application",
        lambda *_args, **_kwargs: pytest.fail("pre-ACCEPT exception cannot apply effects"),
    )

    def github_io(
        _repository: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
    ) -> object:
        if path == "issues/322":
            return {
                "state": "open",
                "body": "Change: restore-no-work-idle-discovery\n",
                "labels": [{"name": "action:merge-implementation-pr"}],
            }
        if path == "issues/322/comments?per_page=100&page=1":
            return github_comments
        if path == "issues/322/comments" and method == "POST":
            assert payload is not None
            mutations.append(path)
            github_comments.append({"id": 123, "body": payload["body"]})
            return {"id": 123}
        raise AssertionError(f"unexpected API {method} {path}")

    monkeypatch.setattr(bridge, "_github_json", github_io)

    with pytest.raises(HTTPError, match="HTTP Error 404"):
        bridge.main()

    document = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert document["schema"] == "scheduled-agent-execution-exception/v1"
    assert (document["issue_number"], document["action"], document["request_comment_id"]) == (
        322,
        "merge-implementation-pr",
        102,
    )
    assert document["run_id"] == 41036535846
    assert document["raw_error"] == "HTTP Error 404: Not Found"
    assert document["mutation_status"] == "NO_APPLICATION_WRITE_ATTEMPTED"
    assert document["unfinished_boundary"] == "pre-accept-worker-result-qualification"
    assert "test-private-token" not in evidence_path.read_text(encoding="utf-8")
    assert output_path.read_text(encoding="utf-8") == (
        f"execution_exception_path={evidence_path}\n"
    )
    assert mutations == ["issues/322/comments"]
    assert len(github_comments) == 1
    assert str(github_comments[0]["body"]).startswith("EXECUTION_EXCEPTION\nWorkflow: #322")
    assert "Disposition: fresh-reconcile-or-bounded-Lead-repair" in str(github_comments[0]["body"])
    # Repeating the handler for the same run/attempt must not append a second
    # record, manufacture ACCEPT, or enter effect execution.
    with pytest.raises(HTTPError, match="HTTP Error 404"):
        bridge.main()
    assert mutations == ["issues/322/comments"]


def test_application_workflow_uploads_exception_even_when_apply_fails() -> None:
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")
    assert (
        workflow.count(
            '--exception-evidence-path "$RUNNER_TEMP/application-execution-exception.json"'
        )
        == 2
    )
    assert "if: always() && steps.apply.outputs.execution_exception_path != ''" in workflow
    assert (
        "if: always() && steps.post_validation_apply.outputs.execution_exception_path != ''"
        in workflow
    )
    assert workflow.count("name: application-execution-exception") == 2


def test_uncertain_effect_exception_does_not_claim_no_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    context = bridge.ApplicationExceptionContext(
        repository=_REPOSITORY,
        revision=_REVISION,
        source=WorkerRequest(322, "executor", "merge-implementation-pr"),
        change="restore-no-work-idle-discovery",
        request_comment_id=102,
        evidence_path=str(tmp_path / "execution-exception.json"),
        stage="application-effect-and-postcondition",
        mutation_attempted=True,
    )
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    bridge._record_application_exception(context, RuntimeError("lost write response"))
    document = json.loads((tmp_path / "execution-exception.json").read_text(encoding="utf-8"))
    assert document["mutation_status"] == "UNKNOWN_REQUIRES_FRESH_RECONCILIATION"
    assert document["raw_error"] == "lost write response"


def _worker_result(
    *,
    action: str = "explore-change",
    role: str = "lead",
    result_kind: str = "proposal-ready",
) -> dict[str, object]:
    return {
        "issue_number": 138,
        "role": role,
        "action": action,
        "change": "unset",
        "result_kind": result_kind,
        "evidence_ref": "issuecomment-typed-result",
        "result_content": "bounded semantic evidence",
        "requested_effects": [],
    }


def _effect_request(
    worker_result: dict[str, object] | None = None,
    *,
    revision: str = _REVISION,
) -> str:
    raw = json.dumps(worker_result or _worker_result(), sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return "\n".join(
        (
            APPLICATION_REQUEST_MARKER,
            f"{AUTHORIZATION_REVISION_PREFIX}{revision}",
            f"Worker-Result-B64: {encoded}",
        )
    )


def test_semantic_finalize_result_revision_uses_default_branch_without_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(234, "lead", "finalize-change")
    raw = json.dumps(
        {
            "result_kind": "archive-ready",
            "evidence_ref": "archive-ready-evidence",
            "result_content": "fresh archive evidence",
            "requested_effects": [
                {
                    "kind": "github-mutation",
                    "payload_json": json.dumps(
                        {
                            "issue_number": 234,
                            "operation": "workflow-dispatch",
                            "workflow_id": "openspec-archive.yml",
                            "ref": "main",
                            "inputs": {
                                "change": "source-decision-explore-materialization",
                                "issue": "234",
                                "revision": _REVISION,
                                "request_key": (
                                    "archive-234-4e3241d7d84a64012bf3b6218442128a4cb48d7a"
                                ),
                            },
                        },
                        sort_keys=True,
                    ),
                }
            ],
        },
        sort_keys=True,
    )
    monkeypatch.setattr(
        bridge,
        "_machine_carrier_head",
        lambda **_kwargs: pytest.fail("finalize-change must not resolve an implementation carrier"),
    )

    assert (
        bridge._machine_result_revision(
            raw,
            source,
            change="source-decision-explore-materialization",
            repository=_REPOSITORY,
            token=_REPOSITORY,
            current_revision=_REVISION,
            default_branch="main",
        )
        == _REVISION
    )


def test_review_discovers_only_the_last_freshly_qualified_merged_change_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late READY after merge must review the real Change, not a repair PR."""

    change = "restore-no-work-idle-discovery"
    historical = (
        (324, {"head": {"sha": "1" * 40}}),
        (347, {"head": {"sha": "2" * 40}}),
        (353, {"head": {"sha": "3" * 40}}),
    )
    calls: list[int] = []
    monkeypatch.setattr(bridge, "_review_predecessor_carrier", lambda *_args: (353, "9" * 40))
    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(bridge, "_historical_carriers", lambda *_args, **_kwargs: historical)

    def qualify(**kwargs: object) -> SimpleNamespace:
        number = cast(int, kwargs["pr_number"])
        calls.append(number)
        return SimpleNamespace(
            disposition="HISTORICAL_MERGED",
            default_branch="main",
            head_sha="3" * 40,
        )

    monkeypatch.setattr(bridge, "qualify_implementation_carrier", qualify)
    assert (
        bridge._machine_carrier_head(
            repository=_REPOSITORY,
            token=_REPOSITORY,
            source=WorkerRequest(322, "reviewer", "review-implementation"),
            change=change,
            default_branch="main",
            current_revision=_REVISION,
        )
        == "3" * 40
    )
    assert calls == [353]  # Repair PR #340 is not the accepted Change materialization.


@pytest.mark.parametrize(
    ("result_kind", "carrier_disposition", "ready_head_matches", "permitted"),
    [
        ("findings", "RECONCILIATION_REQUIRED", True, True),
        ("findings", "RECONCILIATION_REQUIRED", False, False),
        ("pass", "RECONCILIATION_REQUIRED", True, False),
        ("findings", "INDETERMINATE", True, False),
        ("pass", "QUALIFIED", True, True),
    ],
)
def test_review_findings_can_return_to_executor_without_qualifying_stale_head_for_pass(
    monkeypatch: pytest.MonkeyPatch,
    result_kind: str,
    carrier_disposition: str,
    ready_head_matches: bool,
    permitted: bool,
) -> None:
    """Only FINDINGS may consume an accepted PR needing base reconciliation."""

    change = "restore-no-work-idle-discovery"
    source = WorkerRequest(322, "reviewer", "review-implementation")
    head = "e" * 40
    calls: list[int] = []
    ready_head = head if ready_head_matches else "d" * 40
    monkeypatch.setattr(bridge, "_review_predecessor_carrier", lambda *_args: (398, ready_head))

    def qualify(**kwargs: object) -> SimpleNamespace:
        calls.append(cast(int, kwargs["pr_number"]))
        return SimpleNamespace(
            disposition=carrier_disposition,
            default_branch="main",
            head_sha=head,
        )

    monkeypatch.setattr(bridge, "qualify_implementation_carrier", qualify)
    raw = json.dumps(
        {
            "issue_number": 322,
            "role": source.role,
            "action": source.action,
            "change": change,
            "result_kind": result_kind,
            "evidence_ref": "https://github.com/royhsu-work/investment-strategy/pull/398",
            "result_content": "independent exact-head review",
            "requested_effects": [],
        }
    )

    def revision() -> str:
        return bridge._machine_result_revision(
            raw,
            source,
            change=change,
            repository=_REPOSITORY,
            token=_REPOSITORY,
            current_revision=_REVISION,
            default_branch="main",
        )

    if permitted:
        assert revision() == head
    else:
        with pytest.raises(RuntimeError, match="accepted implementation carrier"):
            revision()
    assert calls == [398]  # The earlier accepted PR identity is mandatory.


@pytest.mark.parametrize("scenario", ["no-history", "ambiguous", "unqualified", "new-slice"])
def test_merged_carrier_discovery_fails_closed_outside_exact_review(
    monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(bridge, "_review_predecessor_carrier", lambda *_args: (None, "3" * 40))
    historical = (
        None
        if scenario == "ambiguous"
        else ()
        if scenario == "no-history"
        else ((353, {"head": {"sha": "3" * 40}}),)
    )
    monkeypatch.setattr(bridge, "_historical_carriers", lambda *_args, **_kwargs: historical)
    monkeypatch.setattr(
        bridge,
        "qualify_implementation_carrier",
        lambda **_kwargs: SimpleNamespace(
            disposition="INDETERMINATE" if scenario == "unqualified" else "HISTORICAL_MERGED",
            default_branch="main",
            head_sha="3" * 40,
        ),
    )
    source = (
        WorkerRequest(322, "executor", "implement-change")
        if scenario == "new-slice"
        else WorkerRequest(322, "reviewer", "review-implementation")
    )
    with pytest.raises(RuntimeError, match="carrier is not freshly recognized"):
        bridge._machine_carrier_head(
            repository=_REPOSITORY,
            token=_REPOSITORY,
            source=source,
            change="restore-no-work-idle-discovery",
            default_branch="main",
            current_revision=_REVISION,
        )


def test_merge_consequence_selects_only_the_exact_review_pass_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    change = "restore-no-work-idle-discovery"
    head = "3" * 40
    calls: list[int] = []
    monkeypatch.setattr(
        bridge,
        "current_reviewed_implementation_head",
        lambda *_args, **_kwargs: SimpleNamespace(head_sha=head, merged_sha=None),
    )
    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda *_args, **_kwargs: (
            {"number": 324, "head": {"sha": "1" * 40}},
            {"number": 347, "head": {"sha": "2" * 40}},
            {"number": 353, "head": {"sha": head}},
        ),
    )

    detail_reads: list[int] = []

    def read(_repo: str, _token: str, path: str) -> dict[str, object]:
        number = int(path.split("/")[-1])
        detail_reads.append(number)
        if number != 353:
            # A transient failure on unrelated history must not interrupt
            # the already reviewed exact-head merge carrier.
            raise HTTPError(path, 503, "Service Unavailable", Message(), None)
        return {
            "number": number,
            "state": "closed",
            "merged": True,
            "body": "Refs #322",
            "head": {
                "sha": str({324: "1", 347: "2", 353: "3"}[number]) * 40,
                "ref": "agent/restore-no-work-idle-discovery-continuation-347",
                "repo": {"full_name": _REPOSITORY},
            },
            "base": {"ref": "main", "repo": {"full_name": _REPOSITORY}},
        }

    monkeypatch.setattr(bridge, "_github_json", read)

    def qualify(**kwargs: object) -> SimpleNamespace:
        calls.append(cast(int, kwargs["pr_number"]))
        return SimpleNamespace(disposition="HISTORICAL_MERGED")

    monkeypatch.setattr(bridge, "qualify_implementation_carrier", qualify)
    result = bridge._fresh_merge_carrier(
        repository=_REPOSITORY,
        token=_REPOSITORY,
        source=WorkerRequest(322, "executor", "merge-implementation-pr"),
        change=change,
        current_revision=_REVISION,
        default_branch="main",
    )
    assert result["number"] == 353
    assert detail_reads == [353]
    assert calls == [353]


@pytest.mark.parametrize(
    "summary",
    [
        {"number": 353},
        {"number": 353, "head": {}},
        {"number": 353, "head": {"sha": "invalid"}},
    ],
)
def test_merge_consequence_rejects_incomplete_historical_summary(
    monkeypatch: pytest.MonkeyPatch, summary: dict[str, object]
) -> None:
    monkeypatch.setattr(
        bridge,
        "current_reviewed_implementation_head",
        lambda *_args, **_kwargs: SimpleNamespace(head_sha="3" * 40, merged_sha=None),
    )
    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args, **_kwargs: (summary,))
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda *_args, **_kwargs: pytest.fail("unqualified summary cannot reach PR detail"),
    )
    with pytest.raises(RuntimeError, match="summary is incomplete"):
        bridge._fresh_merge_carrier(
            repository=_REPOSITORY,
            token=_REPOSITORY,
            source=WorkerRequest(322, "executor", "merge-implementation-pr"),
            change="restore-no-work-idle-discovery",
            current_revision=_REVISION,
            default_branch="main",
        )


@pytest.mark.parametrize(
    "scenario",
    ["accepted", "missing-decision", "wrong-identity", "ambiguous-effect", "missing-effect"],
)
def test_review_predecessor_uses_accepted_implementation_not_ready_projection(
    monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    """READY is a transition: its revision cannot replace accepted PR identity."""

    change = "restore-no-work-idle-discovery"
    issue = SimpleNamespace(
        authoritative=True,
        state="open",
        change=change,
        routing=("reviewer", "review-implementation"),
    )
    fake_event = SimpleNamespace(
        valid=True,
        issue_number=322,
        change=change,
        role="executor",
        action="implement-change",
        result_kind="ready",
        successor=("reviewer", "review-implementation"),
        revision="a" * 40,  # Maintenance PR HEAD mistakenly written by old Recovery.
        default_branch_revision=_REVISION,
        application_correlation=f"application:6019133874:322:{change}:executor:implement-change:ready:{_REVISION}",
    )
    monkeypatch.setattr(bridge, "_github_json", lambda *_args: {"number": 322})
    monkeypatch.setattr(bridge, "normalize_github_issue", lambda *_args: issue)
    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args: ({"id": 1},))
    monkeypatch.setattr(bridge, "parse_formal_result", lambda *_args, **_kwargs: fake_event)
    decision = SimpleNamespace(
        disposition="ACCEPTED" if scenario != "wrong-identity" else "REJECTED",
        issue_number=322,
        role="executor",
        action="implement-change",
        change=change,
        result_kind="ready",
        raw_worker_result="{}",
    )
    monkeypatch.setattr(
        bridge,
        "_application_decisions_for_request_id",
        lambda **_kwargs: () if scenario == "missing-decision" else (decision,),
    )
    monkeypatch.setattr(
        bridge,
        "_materialization_effects",
        lambda *_args, **_kwargs: (
            ()
            if scenario == "missing-effect"
            else ({"operation": "application-materialize"},)
            * (2 if scenario == "ambiguous-effect" else 1)
        ),
    )
    monkeypatch.setattr(
        bridge,
        "find_materialization_payload",
        lambda *_args: SimpleNamespace(change=change, pr_number=353),
    )
    if scenario in {"accepted", "missing-effect"}:
        assert bridge._review_predecessor_carrier(
            _REPOSITORY,
            _REPOSITORY,
            WorkerRequest(322, "reviewer", "review-implementation"),
            change,
            _REVISION,
        ) == ((None, "a" * 40) if scenario == "missing-effect" else (353, "a" * 40))
    else:
        with pytest.raises(RuntimeError, match="review predecessor"):
            bridge._review_predecessor_carrier(
                _REPOSITORY,
                _REPOSITORY,
                WorkerRequest(322, "reviewer", "review-implementation"),
                change,
                _REVISION,
            )


@pytest.mark.parametrize("disposition", ["QUALIFIED", "RECONCILIATION_REQUIRED", "INDETERMINATE"])
def test_review_predecessor_resolves_application_owned_supersession_without_borrowing_old_pr(
    monkeypatch: pytest.MonkeyPatch, disposition: str
) -> None:
    change = "restore-no-work-idle-discovery"
    branch = f"agent/{change}-supersedes-408"
    fresh_head = "a" * 40
    ready = SimpleNamespace(
        valid=True,
        issue_number=322,
        change=change,
        role="executor",
        action="implement-change",
        result_kind="ready",
        successor=("reviewer", "review-implementation"),
        revision=fresh_head,
        default_branch_revision=_REVISION,
        application_correlation=f"application:6019133874:322:{change}:executor:implement-change:ready:{_REVISION}",
    )
    monkeypatch.setattr(bridge, "_github_json", lambda *_args: {"number": 322})
    monkeypatch.setattr(
        bridge,
        "normalize_github_issue",
        lambda *_args: SimpleNamespace(
            authoritative=True,
            state="open",
            change=change,
            routing=("reviewer", "review-implementation"),
        ),
    )
    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args: ({"number": 519},))
    monkeypatch.setattr(bridge, "parse_formal_result", lambda *_args, **_kwargs: ready)
    monkeypatch.setattr(
        bridge,
        "_application_decisions_for_request_id",
        lambda **_kwargs: (
            SimpleNamespace(
                disposition="ACCEPTED",
                issue_number=322,
                role="executor",
                action="implement-change",
                change=change,
                result_kind="ready",
                raw_worker_result="{}",
            ),
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_materialization_effects",
        lambda *_args, **_kwargs: ({"operation": "application-materialize"},),
    )
    monkeypatch.setattr(
        bridge,
        "find_materialization_payload",
        lambda *_args: SimpleNamespace(change=change, branch=branch, pr_number=None),
    )
    monkeypatch.setattr(bridge, "qualify_supersession_branch", lambda **_kwargs: True)
    monkeypatch.setattr(
        bridge,
        "qualify_implementation_carrier",
        lambda **_kwargs: SimpleNamespace(
            disposition=disposition, branch=branch, head_sha=fresh_head
        ),
    )
    args = (
        _REPOSITORY,
        _REPOSITORY,
        WorkerRequest(322, "reviewer", "review-implementation"),
        change,
        _REVISION,
    )
    if disposition == "INDETERMINATE":
        with pytest.raises(RuntimeError, match="exact READY successor"):
            bridge._review_predecessor_carrier(*args)
    else:
        assert bridge._review_predecessor_carrier(*args) == (519, fresh_head)


@pytest.mark.parametrize("blocked_revision_matches_default", [True, False])
def test_review_blocked_self_loop_preserves_accepted_ready_work_product(
    monkeypatch: pytest.MonkeyPatch, blocked_revision_matches_default: bool
) -> None:
    change = "restore-no-work-idle-discovery"
    ready = SimpleNamespace(
        valid=True,
        issue_number=322,
        change=change,
        role="executor",
        action="implement-change",
        result_kind="ready",
        revision="a" * 40,
        default_branch_revision=_REVISION,
        successor=("reviewer", "review-implementation"),
        application_correlation=(
            f"application:6019133874:322:{change}:executor:implement-change:ready:{_REVISION}"
        ),
    )
    blocked = SimpleNamespace(
        valid=True,
        issue_number=322,
        change=change,
        role="reviewer",
        action="review-implementation",
        result_kind="blocked",
        revision=_REVISION if blocked_revision_matches_default else "b" * 40,
        default_branch_revision=_REVISION,
        successor=("reviewer", "review-implementation"),
    )
    monkeypatch.setattr(bridge, "_github_json", lambda *_args: {"number": 322})
    monkeypatch.setattr(
        bridge,
        "normalize_github_issue",
        lambda *_args: SimpleNamespace(
            authoritative=True,
            state="open",
            change=change,
            routing=("reviewer", "review-implementation"),
        ),
    )
    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args: ({"id": 1}, {"id": 2}))
    monkeypatch.setattr(
        bridge, "parse_formal_result", lambda raw, **_kwargs: ready if raw["id"] == 1 else blocked
    )
    monkeypatch.setattr(
        bridge,
        "_application_decisions_for_request_id",
        lambda **_kwargs: (
            SimpleNamespace(
                disposition="ACCEPTED",
                issue_number=322,
                role="executor",
                action="implement-change",
                change=change,
                result_kind="ready",
                raw_worker_result="{}",
            ),
        ),
    )
    monkeypatch.setattr(bridge, "_materialization_effects", lambda *_args, **_kwargs: ())
    args = (
        _REPOSITORY,
        _REPOSITORY,
        WorkerRequest(322, "reviewer", "review-implementation"),
        change,
        _REVISION,
    )
    if blocked_revision_matches_default:
        assert bridge._review_predecessor_carrier(*args) == (None, "a" * 40)
    else:
        with pytest.raises(RuntimeError, match="not a legal self-loop"):
            bridge._review_predecessor_carrier(*args)


def _preflight(
    *,
    action: str = "explore-change",
    issue_number: int = 138,
    change: str = "unset",
    human_authorized: bool = True,
    current_state_provenance: ObservationProvenance = ObservationProvenance.QUALIFIED,
) -> DispatchPreflight:
    role = (
        "reviewer"
        if action.startswith("review-")
        else "executor"
        if action.startswith(("implement", "merge"))
        else "lead"
    )
    return acquire_dispatch_preflight(
        observations=(
            GitHubIssueObservation(
                issue_number=issue_number,
                change=change,
                routing=cast(Routing, (role, action)),
                state="open",
                created_order=1,
                authoritative=True,
                current_state_provenance=current_state_provenance,
            ),
        ),
        source_total_count=1,
        incomplete_results=False,
        exhausted=True,
        human_authorized=human_authorized,
    )


def _connector_comment(comment_id: int, body: str, *, trusted: bool = True) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": ({"slug": "chatgpt-codex-connector"} if trusted else None),
    }


def _event(
    body: str,
    *,
    trusted: bool = True,
    comment_id: int = 102,
    issue_number: int = 142,
) -> dict[str, object]:
    return {
        "action": "created",
        "issue": {
            "number": issue_number,
            "title": checkin_title(date(2026, 9, 3)),
            "state": "open",
            "labels": [],
        },
        "comment": _connector_comment(comment_id, body, trusted=trusted),
    }


def _accepted_record(
    raw_worker_result: str,
    request_body: str,
    *,
    source: WorkerRequest,
    change: str,
    result_kind: str,
    request_comment_id: int = 102,
) -> ApplicationDecisionRecord:
    return ApplicationDecisionRecord(
        request_comment_id=request_comment_id,
        request_body_sha256=hashlib.sha256(request_body.encode("utf-8")).hexdigest(),
        authorization_revision=_REVISION,
        issue_number=source.issue_number,
        role=source.role,
        action=source.action,
        change=change,
        result_kind=result_kind,
        disposition="ACCEPTED",
        worker_result_sha256=hashlib.sha256(raw_worker_result.encode("utf-8")).hexdigest(),
        raw_worker_result=raw_worker_result,
        reason="accepted",
    )


@pytest.mark.parametrize("mismatch", ["disposition", "role"])
def test_s2_post_effect_original_proof_rejects_foreign_accepted_identity(
    monkeypatch: pytest.MonkeyPatch, mismatch: str
) -> None:
    """RED R0: a positive Effect does not certify a foreign ACCEPTED identity."""
    source = WorkerRequest(435, "executor", "implement-change")
    raw = '{"source":"accepted-original"}'
    record = _accepted_record(
        raw,
        "EFFECT_REQUEST",
        source=source,
        change="restore-t1-dispatch-artifact-consumption",
        result_kind="blocked",
        request_comment_id=6796616018,
    )
    record = (
        replace(record, disposition="REJECTED")
        if mismatch == "disposition"
        else replace(record, role="lead")
    )
    effect = StagedEffect("issue-comment", '{"issue_number":435,"body":"original"}')
    monkeypatch.setattr(bridge, "_accepted_worker_result_for_continuation", lambda **_k: raw)
    monkeypatch.setattr(
        bridge,
        "parse_effect_batch",
        lambda *_a, **_k: SimpleNamespace(
            typed_result=SimpleNamespace(
                result=SimpleNamespace(kind=SimpleNamespace(value="blocked"))
            ),
            effects=(effect,),
        ),
    )
    observed: list[StagedEffect] = []

    class Observer:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        def observe_postcondition(self, candidate: StagedEffect) -> bool:
            observed.append(candidate)
            return True

    monkeypatch.setattr(bridge, "GitHubEffectAdapter", Observer)
    proof = bridge._observe_accepted_post_effect_result(
        record=record,
        source=source,
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=_REVISION,
        default_branch="main",
    )
    assert proof.disposition == "UNSAFE"
    assert observed == []


@pytest.mark.parametrize(
    ("original_count", "observed", "zero_source_proven", "expected"),
    [
        (1, True, False, "COMPLETE"),
        (1, False, False, "INDETERMINATE"),
        (0, True, False, "INDETERMINATE"),
        (0, True, True, "COMPLETE"),
    ],
)
def test_nonactivation_exception_proof_reconciles_original_effects_without_replay(
    monkeypatch: pytest.MonkeyPatch,
    original_count: int,
    observed: bool,
    zero_source_proven: bool,
    expected: str,
) -> None:
    source = WorkerRequest(435, "executor", "implement-change")
    raw = json.dumps({"source": "immutable accepted intent"})
    record = _accepted_record(
        raw,
        "EFFECT_REQUEST",
        source=source,
        change="restore-t1-dispatch-artifact-consumption",
        result_kind="blocked",
        request_comment_id=6796616018,
    )
    effect = StagedEffect("github-mutation", "{}")
    batch = SimpleNamespace(
        typed_result=SimpleNamespace(result=SimpleNamespace(kind=SimpleNamespace(value="blocked"))),
        effects=(effect,) if original_count else (),
    )
    monkeypatch.setattr(bridge, "_accepted_worker_result_for_continuation", lambda **_kw: raw)
    monkeypatch.setattr(bridge, "parse_effect_batch", lambda *_a, **_kw: batch)
    monkeypatch.setattr(
        bridge, "_verified_zero_original_accepted_effects", lambda **_kw: zero_source_proven
    )
    original_observations: list[tuple[StagedEffect, ...]] = []
    original_observer = bridge._observe_accepted_effect_prefix

    def track_original_proof(
        effects: Sequence[StagedEffect],
        observe: Callable[[StagedEffect], bool],
        *,
        source: WorkerRequest,
    ) -> tuple[bridge.RecoveryEvidenceNode, ...] | None:
        original_observations.append(tuple(effects))
        return original_observer(effects, observe, source=source)

    monkeypatch.setattr(bridge, "_observe_accepted_effect_prefix", track_original_proof)
    seen: list[StagedEffect] = []

    class Observer:
        def __init__(self, *_args: object, **kwargs: object) -> None:
            assert kwargs["accepted_intent"] is True
            assert kwargs["request_comment_id"] == 6796616018

        def observe_postcondition(self, candidate: StagedEffect) -> bool:
            seen.append(candidate)
            return observed

    monkeypatch.setattr(bridge, "GitHubEffectAdapter", Observer)
    proof = bridge._observe_accepted_post_effect_result(
        record=record,
        source=source,
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=_REVISION,
        default_branch="main",
    )
    assert proof.disposition == expected
    assert seen == ([effect] if original_count else [])
    assert original_observations == (
        [tuple(batch.effects)] if original_count or zero_source_proven else []
    )


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (OSError, "INDETERMINATE"),
        (ValueError, "UNSAFE"),
        (RuntimeError, "RAISE"),
    ],
)
@pytest.mark.parametrize("empty_original", [False, True])
def test_accepted_original_source_captures_only_operational_failures(
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
    expected: str,
    empty_original: bool,
) -> None:
    """R9: a deterministic proof defect must reach the existing outer owner.

    A GitHub read fault remains observable; an invalid input is unsafe, while
    an unexpected programming/contract fault must never become endless UNKNOWN.
    """
    source = WorkerRequest(435, "executor", "implement-change")
    raw = json.dumps({"source": "immutable accepted intent"})
    record = _accepted_record(
        raw,
        "EFFECT_REQUEST",
        source=source,
        change="restore-t1-dispatch-artifact-consumption",
        result_kind="blocked",
        request_comment_id=6796616018,
    )

    def fail(**_kwargs: object) -> str:
        raise failure("proof boundary fault")

    if empty_original:
        monkeypatch.setattr(
            bridge, "_accepted_worker_result_for_continuation", lambda **_kwargs: raw
        )
        monkeypatch.setattr(
            bridge,
            "parse_effect_batch",
            lambda *_args, **_kwargs: SimpleNamespace(
                typed_result=SimpleNamespace(
                    result=SimpleNamespace(kind=SimpleNamespace(value="blocked"))
                ),
                effects=(),
            ),
        )
        monkeypatch.setattr(bridge, "_verified_zero_original_accepted_effects", fail)
    else:
        monkeypatch.setattr(bridge, "_accepted_worker_result_for_continuation", fail)

    def observe() -> bridge.AcceptedPostEffectProof:
        return bridge._observe_accepted_post_effect_result(
            record=record,
            source=source,
            repository=_REPOSITORY,
            token=_REVISION,
            current_revision=_REVISION,
            default_branch="main",
        )

    if expected == "RAISE":
        with pytest.raises(RuntimeError, match="proof boundary fault"):
            observe()
    else:
        assert observe().disposition == expected


@pytest.mark.parametrize(
    ("postcondition", "expected"),
    [(True, "SATISFIED"), (False, "UNKNOWN")],
)
def test_positive_accepted_effect_postcondition_outweighs_missing_attempt_history(
    monkeypatch: pytest.MonkeyPatch, postcondition: bool, expected: str
) -> None:
    """R2/R5: original-Effect completion is independent of past Run inventory.

    This concerns the immutable original Effect only; formal result and
    successor are distinct obligations, not permissions to replay writes.
    """
    source = WorkerRequest(435, "executor", "implement-change")
    raw = json.dumps({"source": "immutable accepted effect"})
    record = _accepted_record(
        raw,
        "EFFECT_REQUEST",
        source=source,
        change="restore-t1-dispatch-artifact-consumption",
        result_kind="blocked",
        request_comment_id=6796616018,
    )
    effect = StagedEffect("github-mutation", "{}")
    checkpoint: dict[str, object] = {
        "attempted_effects": [{"kind": effect.kind, "payload_json": effect.payload_json}],
        "attempt_revision": _REVISION,
        "failed_effect_index": 0,
        "write_call_entered": True,
    }
    artifact = SimpleNamespace(document={"failure_evidence": checkpoint})
    monkeypatch.setattr(bridge, "_accepted_recovery_boundary", lambda _e: "READ_ONLY")
    monkeypatch.setattr(
        bridge,
        "_verified_attempted_effect_checkpoint",
        lambda *_a, **_kw: (effect,),
    )
    monkeypatch.setattr(
        bridge,
        "_read_accepted_never_called_evidence",
        lambda **_kw: bridge.TypedEvidenceError(
            "UNKNOWN", "TEST_HISTORY", "unavailable", 6796616018
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_accepted_worker_result_for_continuation",
        lambda **_kw: raw,
    )
    monkeypatch.setattr(
        bridge,
        "parse_effect_batch",
        lambda *_a, **_kw: SimpleNamespace(
            typed_result=SimpleNamespace(
                result=SimpleNamespace(kind=SimpleNamespace(value="blocked"))
            ),
            effects=(effect,),
        ),
    )

    class Observer:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def observe_postcondition(self, _effect: StagedEffect) -> bool:
            return postcondition

    monkeypatch.setattr(bridge, "GitHubEffectAdapter", Observer)
    proof = bridge.classify_accepted_read_only_effects(
        record=record,
        source=source,
        recovery_evidence=checkpoint,
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=_REVISION,
        default_branch="main",
        recovery_artifact=artifact,  # type: ignore[arg-type]
    )
    # A positive original Effect proof is not the formal-result/successor gate.
    # Historical uncertainty may still block the *next write* independently.
    assert proof.original_effect_proof == expected
    assert proof.disposition == "INDETERMINATE"


def test_noncompletion_accepted_intent_has_no_synthetic_checkpoint_obligation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(435, "executor", "implement-change")
    monkeypatch.setattr(
        bridge,
        "parse_worker_result",
        lambda *_a, **_kw: SimpleNamespace(requested_effects=()),
    )
    assert not bridge._accepted_checkpoint_already_durable(
        "{}",
        source=source,
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=_REVISION,
        request_comment_id=6796616018,
    )


@pytest.mark.parametrize(
    ("projection", "allowed"),
    [
        ((), True),
        ((0, 1), True),
        ((1, 0), False),
        ((0, 2), False),
    ],
)
def test_accepted_projection_preserves_immutable_completed_effects(
    projection: tuple[int, ...], allowed: bool
) -> None:
    # Use the actual typed worker parser: a fresh planner may omit completed
    # effects, but cannot replace or reorder their immutable identities.
    source = WorkerRequest(138, "lead", "explore-change")
    original = _worker_result(action=source.action, role=source.role, result_kind="blocked")
    effects = [
        {
            "kind": "issue-comment",
            "payload_json": json.dumps({"issue_number": 138, "body": f"original-{n}"}),
        }
        for n in range(3)
    ]
    formal = {
        "kind": "issue-comment",
        "payload_json": json.dumps({"issue_number": 138, "body": "ACTION_RESULT\nformal"}),
    }
    original["requested_effects"] = effects[:2]
    projected = dict(
        original, requested_effects=[effects[index] for index in projection] + [formal]
    )
    raw = json.dumps(original, sort_keys=True)
    changed = json.dumps(projected, sort_keys=True)
    if not allowed:
        with pytest.raises(RuntimeError, match="accepted recovery"):
            bridge._accepted_reconciliation_effect_projection(
                accepted_raw=raw, projected_raw=changed, source=source, change="unset"
            )
        return
    reconciled, count = bridge._accepted_reconciliation_effect_projection(
        accepted_raw=raw, projected_raw=changed, source=source, change="unset"
    )
    assert count == 2
    assert json.loads(reconciled)["requested_effects"] == effects[:2] + [formal]


def test_empty_original_projection_preserves_application_formal_obligation() -> None:
    source = WorkerRequest(138, "lead", "explore-change")
    original = _worker_result(action=source.action, role=source.role, result_kind="blocked")
    formal = {
        "kind": "issue-comment",
        "payload_json": json.dumps({"issue_number": 138, "body": "ACTION_RESULT\nformal"}),
    }
    raw = json.dumps(original, sort_keys=True)
    projected = json.dumps(dict(original, requested_effects=[formal]), sort_keys=True)
    reconciled, count = bridge._accepted_reconciliation_effect_projection(
        accepted_raw=raw, projected_raw=projected, source=source, change="unset"
    )
    assert count == 0
    assert json.loads(reconciled)["requested_effects"] == [formal]


@pytest.mark.parametrize(
    ("has_physical_effect", "mutated", "verified"),
    [
        (False, False, True),
        (True, False, False),
        (False, True, False),
    ],
)
def test_accepted_zero_effect_source_requires_exact_original_request(
    has_physical_effect: bool, mutated: bool, verified: bool
) -> None:
    source = WorkerRequest(138, "lead", "explore-change")
    original = _worker_result(action=source.action, role=source.role, result_kind="blocked")
    if has_physical_effect:
        original["requested_effects"] = [
            {
                "kind": "issue-comment",
                "payload_json": json.dumps(
                    {"issue_number": 138, "body": "historical physical Effect"}
                ),
            }
        ]
    request_body = _effect_request(original)
    semantic = dict(original, _semantic_intent_version=2, requested_effects=[])
    record = _accepted_record(
        json.dumps(semantic),
        request_body,
        source=source,
        change="unset",
        result_kind="blocked",
        request_comment_id=102,
    )
    source_comment = {
        "id": record.request_comment_id,
        "body": request_body + (" " if mutated else ""),
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def read(_repo: str, _token: str, path: str) -> object:
        assert path == "issues/comments/102"
        return source_comment

    assert (
        bridge._verified_zero_original_accepted_effects(
            record=record,
            source=source,
            repository=_REPOSITORY,
            token=_REVISION,
            read=read,
        )
        is verified
    )


@pytest.mark.parametrize(
    ("observed", "expected"),
    [(True, "COMPLETE"), (False, "INDETERMINATE")],
)
def test_incident_435_accepted_blocked_materialization_is_read_only_proven(
    monkeypatch: pytest.MonkeyPatch, observed: bool, expected: str
) -> None:
    """Incident source shape: the one accepted Effect is seven exact PR blobs."""

    source = WorkerRequest(435, "executor", "implement-change")
    change = "restore-t1-dispatch-artifact-consumption"
    targets = [
        (
            "src/investment_strategy/scheduled_agent_carrier.py",
            "fa63766cc353d9f3c4a1e11b30ddd64ad53b0bda",
            "a6b802e2409fadf52fab3aee3c5f79e25ac96575",
        ),
        (
            "src/investment_strategy/scheduled_agent_dispatch_result.py",
            "e5c8de3b034f31b53dab76d56826249dc215e8e0",
            "b9188f580caf6dcad93bc1cbca111bea440713e2",
        ),
        (
            "src/investment_strategy/scheduled_agent_idle_admission.py",
            "bef6073228b46e07e89f828c5615b3e5518df95f",
            "b7e8a7f472dd992799eecb5233611b8b0410bd24",
        ),
        (
            "tests/test_scheduled_agent_dispatch_result.py",
            "5a781a964897e248626bd2d8e3fce3369693fa49",
            "cc7aecb0e65ed41c0a0be4619dfa1b07a90a8709",
        ),
        (
            "tests/test_scheduled_agent_idle_admission.py",
            "2c391fc3dd516259d06a64b3492a4e43dbbf83dc",
            "5111748a42de52b3f6d5e59c42bcf4a3a35c9ed2",
        ),
        (
            ".github/workflows/quality.yml",
            "ab7bb278bfc22fa3e9b2e6867ca2d0ea1d3c29f0",
            "b7028b01d10d967ee6339274ba6d45f43b9d7cab",
        ),
        (
            ".github/scripts/diagnose_dispatch_artifact.py",
            "37da19717c32b0ba323ffe50b511ab6ba5d2112b",
            None,
        ),
    ]
    materialization = {
        "issue_number": 435,
        "operation": "application-materialize",
        "change": change,
        "expected_change": change,
        "branch": "agent/restore-t1-dispatch-artifact-consumption",
        "base_sha": "6f97d0fc53742221f411ceee808938d701d6069f",
        "pr_number": 437,
        "message": (
            "test: qualify exact T1 Artifact reads [t1-native-artifact-diagnostic] (Refs #435)"
        ),
        "files": [
            {"path": path, "blob_sha": sha, "expected_sha": old} for path, sha, old in targets
        ],
    }
    raw = json.dumps(
        {
            "_semantic_intent_version": 2,
            "issue_number": source.issue_number,
            "role": source.role,
            "action": source.action,
            "change": change,
            "result_kind": "blocked",
            "evidence_ref": "https://github.com/royhsu-work/investment-strategy/pull/437",
            "result_content": "Bounded blocked implementation, no checkpoint obligation.",
            "requested_effects": [
                {"kind": "github-mutation", "payload_json": json.dumps(materialization)}
            ],
        },
        sort_keys=True,
    )
    record = _accepted_record(
        raw,
        "EFFECT_REQUEST",
        source=source,
        change=change,
        result_kind="blocked",
        request_comment_id=6796616018,
    )
    checked: list[StagedEffect] = []

    class Observer:
        def __init__(self, *_args: object, **kwargs: object) -> None:
            assert kwargs["accepted_intent"] is True
            assert kwargs["request_comment_id"] == record.request_comment_id

        def observe_postcondition(self, effect: StagedEffect) -> bool:
            checked.append(effect)
            payload = json.loads(effect.payload_json)
            assert payload == materialization
            return observed

    monkeypatch.setattr(bridge, "GitHubEffectAdapter", Observer)
    proof = bridge._observe_accepted_post_effect_result(
        record=record,
        source=source,
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=_REVISION,
        default_branch="main",
    )
    assert proof.disposition == expected
    assert len(checked) == 1


def test_accepted_intent_lookup_includes_indeterminate_current_issue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "explore-change")
    raw = json.dumps(_worker_result(), sort_keys=True, separators=(",", ":"))
    body = _effect_request()
    record = _accepted_record(
        raw,
        body,
        source=source,
        change="unset",
        result_kind="proposal-ready",
    )
    lookups: list[int] = []

    def fake_lookup(**kwargs: object) -> tuple[ApplicationDecisionRecord, ...]:
        issue_number = cast(int, kwargs["issue_number"])
        lookups.append(issue_number)
        return (record,) if issue_number == source.issue_number else ()

    monkeypatch.setattr(bridge, "_application_decisions_for_request_id", fake_lookup)

    found = bridge._find_application_decision_from_current_frontier(
        repository=_REPOSITORY,
        token=_REPOSITORY,
        request_comment_id=record.request_comment_id,
        preflight=_preflight(
            current_state_provenance=ObservationProvenance.INDETERMINATE,
        ),
    )

    assert found == record
    assert lookups == [source.issue_number]


def test_main_rehydrates_accepted_intent_before_transport_observation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = WorkerRequest(138, "lead", "finalize-change")
    worker = _worker_result(
        action=source.action,
        role=source.role,
        result_kind="archive-ready",
    )
    worker["change"] = _CHANGE
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    body = _effect_request(worker)
    record = _accepted_record(
        raw,
        body,
        source=source,
        change=_CHANGE,
        result_kind="archive-ready",
    )
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(_event(body)), encoding="utf-8")
    output_path = tmp_path / "github-output.txt"
    seen: dict[str, object] = {}

    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
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
            "--run-attempt",
            "2",
        ],
    )
    monkeypatch.setattr(
        bridge,
        "_application_decision_for_request",
        lambda **kwargs: (
            record
            if kwargs["issue_number"] == source.issue_number
            and kwargs["request_comment_id"] == record.request_comment_id
            else None
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_fresh_event_observation",
        lambda *_args: pytest.fail("accepted recovery must not consult mutable transport"),
    )
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(
            issue_number=source.issue_number,
            action="review-archive",
            change=_CHANGE,
        ),
    )

    def fake_apply(raw_result: str, **kwargs: object) -> tuple[EffectBatch, object]:
        seen["raw"] = raw_result
        seen["source"] = kwargs["source"]
        return (
            EffectBatch(
                source=cast(WorkerRequest, kwargs["source"]),
                effects=(),
                typed_result=None,
            ),
            bridge.ApplyResult(True, "reconciled"),
        )

    monkeypatch.setattr(bridge, "run_guarded_effect_application", fake_apply)

    assert bridge.main() == 0
    assert seen == {"raw": raw, "source": source}


def test_recovery_artifact_uses_chain_ordinal_after_a_workflow_rerun(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    worker = _worker_result(
        action=source.action,
        role=source.role,
        result_kind="more-implementation-required",
    )
    worker["change"] = _CHANGE
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    body = _effect_request(worker)
    record = _accepted_record(
        raw,
        body,
        source=source,
        change=_CHANGE,
        result_kind="more-implementation-required",
    )
    decision_body = "accepted decision"
    monkeypatch.setattr(
        bridge,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (record, decision_body),
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7001")
    carrier_plan = make_carrier_plan(
        repository=_REPOSITORY,
        issue_number=source.issue_number,
        change=_CHANGE,
        action=source.action,
        authorization_revision=_REVISION,
        operation="pull-request-ready",
        target={"pull_request_number": 236},
        expected={"head_sha": _REVISION},
        requested={"head_sha": _REVISION, "draft": False},
        expected_postcondition={"draft": False},
    )
    output = tmp_path / "recovery.json"
    bridge._write_application_recovery_evidence(
        str(output),
        result=bridge.ApplyResult(False, "carrier-required", carrier_plan=carrier_plan),
        repository=_REPOSITORY,
        token=_REVISION,
        source=source,
        request_comment_id=record.request_comment_id,
        trigger_comment_id=404,
        authorization_revision=_REVISION,
        current_revision=_REVISION,
        run_attempt=2,
        continuation=None,
        predecessor=None,
    )

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["run_attempt"] == 2
    assert document["recovery_attempt"] == 1
    assert document["predecessor"] is None
    assert document["continuation_eligible"] is True


def test_exception_predecessor_is_preserved_in_next_real_recovery_checkpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    worker = _worker_result(
        action=source.action, role=source.role, result_kind="more-implementation-required"
    )
    worker["change"] = _CHANGE
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    record = _accepted_record(
        raw,
        _effect_request(worker),
        source=source,
        change=_CHANGE,
        result_kind="more-implementation-required",
    )
    accepted_body = "accepted decision"
    accepted_hash = hashlib.sha256(accepted_body.encode()).hexdigest()
    exception = bridge.ApplicationExceptionArtifact(
        run_id=7000,
        run_attempt=1,
        job_id=7001,
        artifact_id=7002,
        artifact_digest="sha256:" + "a" * 64,
        request_comment_id=record.request_comment_id,
        accepted_decision_sha256=accepted_hash,
        failure_evidence_sha256="b" * 64,
        recovery_episode_sha256=bridge._canonical_sha256(
            {
                "schema": "scheduled-agent-recovery-episode/v1",
                "repository": _REPOSITORY,
                "issue_number": source.issue_number,
                "request_comment_id": record.request_comment_id,
                "accepted_decision_sha256": accepted_hash,
            }
        ),
        document={"schema": "scheduled-agent-execution-exception/v1"},
    )
    monkeypatch.setattr(
        bridge,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (record, accepted_body),
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7003")
    plan = make_carrier_plan(
        repository=_REPOSITORY,
        issue_number=source.issue_number,
        change=_CHANGE,
        action=source.action,
        authorization_revision=_REVISION,
        operation="pull-request-ready",
        target={"pull_request_number": 236},
        expected={"head_sha": _REVISION},
        requested={"head_sha": _REVISION, "draft": False},
        expected_postcondition={"draft": False},
    )
    output = tmp_path / "following-exception.json"
    bridge._write_application_recovery_evidence(
        str(output),
        result=bridge.ApplyResult(False, "carrier-required", carrier_plan=plan),
        repository=_REPOSITORY,
        token=_REVISION,
        source=source,
        request_comment_id=record.request_comment_id,
        trigger_comment_id=404,
        authorization_revision=_REVISION,
        current_revision=_REVISION,
        run_attempt=1,
        continuation=None,
        predecessor=exception,
    )
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["recovery_attempt"] == 2
    assert document["prior_failure_evidence_sha256"] == [exception.failure_evidence_sha256]
    assert document["predecessor"] == {
        "run_id": exception.run_id,
        "run_attempt": exception.run_attempt,
        "job_id": exception.job_id,
        "artifact_id": exception.artifact_id,
        "artifact_digest": exception.artifact_digest,
        "failure_evidence_sha256": exception.failure_evidence_sha256,
        "recovery_attempt": 1,
    }


def test_recovery_evidence_continues_only_for_unwritten_precondition_rejection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = WorkerRequest(138, "executor", "implement-change")
    worker = _worker_result(
        action=source.action,
        role=source.role,
        result_kind="more-implementation-required",
    )
    worker["change"] = _CHANGE
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    body = _effect_request(worker)
    record = _accepted_record(
        raw,
        body,
        source=source,
        change=_CHANGE,
        result_kind="more-implementation-required",
    )
    monkeypatch.setattr(
        bridge,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (record, "accepted decision"),
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7001")
    rejection = ApplicationRejection(
        ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED,
        "target is at the expected revision",
        "target revision changed",
    )

    def write_evidence(name: str, evidence: EffectRecoveryEvidence) -> dict[str, object]:
        output = tmp_path / f"{name}.json"
        bridge._write_application_recovery_evidence(
            str(output),
            result=bridge.ApplyResult(
                False,
                "effect precondition rejected",
                rejection=rejection,
                recovery_evidence=evidence,
            ),
            repository=_REPOSITORY,
            token=_REVISION,
            source=source,
            request_comment_id=record.request_comment_id,
            trigger_comment_id=404,
            authorization_revision=_REVISION,
            current_revision=_REVISION,
            run_attempt=1,
            continuation=None,
            predecessor=None,
        )
        return json.loads(output.read_text(encoding="utf-8"))

    safe = write_evidence(
        "safe",
        EffectRecoveryEvidence(
            failed_effect_index=0,
            failed_effect_kind="github-mutation",
            failed_effect_sha256="a" * 64,
            completed_effect_indexes=(),
            completed_effect_sha256=(),
            mutation_status="not-complete",
            unfinished_boundary="effect-precondition",
            rejection=rejection,
        ),
    )
    partial = write_evidence(
        "partial",
        EffectRecoveryEvidence(
            failed_effect_index=1,
            failed_effect_kind="github-mutation",
            failed_effect_sha256="b" * 64,
            completed_effect_indexes=(0,),
            completed_effect_sha256=("c" * 64,),
            mutation_status="not-complete",
            unfinished_boundary="effect-precondition",
            rejection=rejection,
        ),
    )
    unknown_postcondition = write_evidence(
        "unknown-postcondition",
        EffectRecoveryEvidence(
            failed_effect_index=0,
            failed_effect_kind="github-mutation",
            failed_effect_sha256="d" * 64,
            completed_effect_indexes=(),
            completed_effect_sha256=(),
            mutation_status="unknown",
            unfinished_boundary="effect-postcondition",
            rejection=rejection,
        ),
    )

    unknown_source = write_evidence(
        "unknown-source",
        EffectRecoveryEvidence(
            failed_effect_index=0,
            failed_effect_kind="github-mutation",
            failed_effect_sha256="e" * 64,
            completed_effect_indexes=(),
            completed_effect_sha256=(),
            mutation_status="not-complete",
            unfinished_boundary="effect-precondition",
            rejection=ApplicationRejection(
                ApplicationRejectionKind.OBSERVATION_UNQUALIFIED,
                '{"materialization_proof":["COMPLETE","INCOMPLETE"],"accepted_intent":true}',
                '{"disposition":"UNKNOWN","reason":"GitHub source unreadable"}',
            ),
        ),
    )

    assert safe["continuation_eligible"] is True
    assert partial["continuation_eligible"] is True  # read-only, never retry the failed write
    assert unknown_postcondition["continuation_eligible"] is True  # read-only reconciliation
    assert unknown_source["continuation_eligible"] is False
    failure = cast(dict[str, object], unknown_source["failure_evidence"])
    rejected = cast(dict[str, object], failure["rejection"])
    assert rejected["classification"] == "observation-unqualified"


@pytest.mark.parametrize(
    ("role", "action", "result_kind"),
    [
        ("lead", "finalize-change", "archive-ready"),
        ("executor", "merge-archive-pr", "merged"),
        ("executor", "merge-implementation-pr", "merged"),
    ],
)
@pytest.mark.parametrize("boundary", ["carrier", "unknown", "partial"])
def test_main_accepts_only_a_fresh_continuation_transport(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    role: str,
    action: str,
    result_kind: str,
    boundary: str,
) -> None:
    source = WorkerRequest(138, role, action)
    worker = _worker_result(
        action=source.action,
        role=source.role,
        result_kind=result_kind,
    )
    worker["change"] = _CHANGE
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    original_body = _effect_request(worker)
    record = _accepted_record(
        raw,
        original_body,
        source=source,
        change=_CHANGE,
        result_kind=result_kind,
        request_comment_id=102,
    )
    decision_body = "accepted-decision-body"
    continuation_body = render_application_continuation_request(
        repository=_REPOSITORY,
        issue_number=source.issue_number,
        original_request_comment_id=record.request_comment_id,
        accepted_decision_sha256=hashlib.sha256(decision_body.encode("utf-8")).hexdigest(),
        predecessor_run_id=_TEST_PREDECESSOR_RUN_ID,
        predecessor_run_attempt=_TEST_PREDECESSOR_RUN_ATTEMPT,
        predecessor_job_id=_TEST_PREDECESSOR_JOB_ID,
        predecessor_artifact_id=_TEST_PREDECESSOR_ARTIFACT_ID,
        predecessor_artifact_digest=_TEST_PREDECESSOR_ARTIFACT_DIGEST,
        failure_evidence_sha256=_TEST_FAILURE_EVIDENCE_SHA256,
        recovery_episode_sha256=_TEST_RECOVERY_EPISODE_SHA256,
    )
    continuation = parse_application_continuation_request(continuation_body)
    assert continuation is not None
    failure_evidence: dict[str, object] = {
        "reason": "carrier_required",
        "unfinished_boundary": "carrier-required",
        "mutation_status": "not-complete",
        "carrier_plan_id": "original-carrier",
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
    }
    if boundary in {"unknown", "partial"}:
        failure_evidence = {
            "reason": "durable postcondition not observed",
            "unfinished_boundary": "effect-postcondition"
            if boundary == "unknown"
            else "effect-precondition",
            "mutation_status": "unknown" if boundary == "unknown" else "not-complete",
            "failed_effect_index": 1 if boundary == "partial" else 0,
            "failed_effect_kind": "issue-comment",
            "failed_effect_sha256": "a" * 64,
            "completed_effect_indexes": [0] if boundary == "partial" else [],
            "completed_effect_sha256": ["b" * 64] if boundary == "partial" else [],
            "rejection": {"classification": "effect-precondition-unsatisfied"}
            if boundary == "partial"
            else None,
        }
    predecessor = bridge.ApplicationRecoveryArtifact(
        run_id=continuation.predecessor_run_id,
        run_attempt=continuation.predecessor_run_attempt,
        job_id=continuation.predecessor_job_id,
        artifact_id=continuation.predecessor_artifact_id,
        artifact_digest=continuation.predecessor_artifact_digest,
        request_comment_id=continuation.original_request_comment_id,
        accepted_decision_sha256=continuation.accepted_decision_sha256,
        failure_evidence_sha256=continuation.failure_evidence_sha256,
        recovery_episode_sha256=continuation.recovery_episode_sha256,
        recovery_attempt=1,
        continuation_eligible=True,
        document={
            "prior_failure_evidence_sha256": [],
            "failure_evidence": failure_evidence,
        },
    )
    event_path = tmp_path / "continuation-event.json"
    event_path.write_text(
        json.dumps(_event(continuation_body, comment_id=404)),
        encoding="utf-8",
    )
    output_path = tmp_path / "github-output.txt"
    seen: dict[str, object] = {}

    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", _REVISION)
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
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
            "--run-attempt",
            "1",
        ],
    )
    monkeypatch.setattr(
        bridge,
        "_fresh_event_observation",
        lambda event, body, *_args: (
            False
            if body == continuation_body and cast(dict[str, object], event["comment"])["id"] == 404
            else pytest.fail("continuation transport was not freshly observed")
        ),
    )
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(
            issue_number=source.issue_number,
            action=source.action,
            change=_CHANGE,
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_find_application_decision_from_current_frontier",
        lambda **_kwargs: record,
    )
    monkeypatch.setattr(
        bridge,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (record, decision_body),
    )
    monkeypatch.setattr(
        bridge,
        "_accepted_worker_result_for_continuation",
        lambda **_kwargs: raw,
    )
    monkeypatch.setattr(bridge, "_resume_pending_accepted_merge_recovery", lambda **_kwargs: False)
    # This test exercises the real continuation decision, not the separate
    # per-effect GitHub consequence planner (covered by its own tests).
    monkeypatch.setattr(
        bridge, "_fresh_application_worker_result", lambda original, **_kwargs: original
    )
    monkeypatch.setattr(
        bridge,
        "qualify_application_continuation_predecessor",
        lambda *_args, **_kwargs: predecessor,
    )

    def fake_apply(raw_result: str, **kwargs: object) -> tuple[EffectBatch, object]:
        seen["raw"] = raw_result
        seen["source"] = kwargs["source"]
        seen["request_comment_id"] = kwargs["request_comment_id"]
        seen["read_only"] = kwargs.get("reconcile_only", False)
        return (
            EffectBatch(
                source=cast(WorkerRequest, kwargs["source"]),
                effects=(),
                typed_result=None,
            ),
            bridge.ApplyResult(True, "continued"),
        )

    monkeypatch.setattr(bridge, "run_guarded_effect_application", fake_apply)

    assert bridge.main() == 0
    assert seen == {
        "raw": raw,
        "source": source,
        "request_comment_id": 102,
        "read_only": boundary != "carrier",
    }


def test_main_resumes_live_322_effect_through_the_same_application_owner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A fresh application run reuses #322's accepted intent without semantic replay."""

    fixture_path = Path(__file__).parent / "fixtures" / "issue322-application-recovery.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    request = cast(dict[str, object], fixture["request_comment"])
    body = cast(str, request["body"])
    issue_comments = cast(list[dict[str, object]], fixture["issue_comments"])
    acceptance = next(item for item in issue_comments if item.get("id") == 5810770514)
    record = bridge.parse_application_decision(cast(str, acceptance["body"]))
    assert record is not None
    source = WorkerRequest(322, "lead", "resolve-question")
    assert record.request_comment_id == 5810765007
    assert (record.issue_number, record.role, record.action, record.change) == (
        322,
        "lead",
        "resolve-question",
        "restore-no-work-idle-discovery",
    )
    raw_worker_result = record.raw_worker_result
    event = _event(body)
    event["issue"] = {
        "number": 330,
        "title": checkin_title(date(2026, 9, 24)),
        "state": "open",
        "labels": [],
    }
    event_comment = cast(dict[str, object], event["comment"])
    event_comment["id"] = 5810765007
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    output_path = tmp_path / "github-output.txt"
    seen: list[dict[str, object]] = []
    current_revision = cast(str, fixture["source_revision"])
    target = bridge.ValidationResourceTarget(
        repository=_REPOSITORY,
        revision="7af49c85ebcb1cc22435913a154e9895bf43cdd2",
        correlation=(
            "application:5810765007:322:restore-no-work-idle-discovery:lead:resolve-question:"
            "ready-for-openspec-review:d019fdc604e8a7fa40e2f3e6436a12b076658057"
        ),
        pr_number=324,
        change="restore-no-work-idle-discovery",
        branch="agent/restore-no-work-idle-discovery",
    )

    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "fixture")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scheduled_agent_application_bridge",
            "--event-path",
            str(event_path),
            "--revision",
            current_revision,
            "--default-branch",
            "main",
            "--run-attempt",
            "8",
        ],
    )
    monkeypatch.setattr(
        bridge,
        "_application_decision_for_request",
        lambda **kwargs: (
            record
            if kwargs["issue_number"] == 322
            and kwargs["request_comment_id"] == 5810765007
            and kwargs["request_body"] == body
            else None
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_accepted_worker_result_for_continuation",
        lambda **kwargs: (
            raw_worker_result
            if kwargs["request_comment_id"] == 5810765007
            else pytest.fail("accepted request identity changed")
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_fresh_application_worker_result",
        lambda raw, **_kwargs: raw,
    )
    monkeypatch.setattr(
        bridge,
        "_fresh_event_observation",
        lambda *_args: pytest.fail("accepted recovery must not consult mutable transport"),
    )
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(
            issue_number=322,
            action="resolve-question",
            change="restore-no-work-idle-discovery",
        ),
    )

    def capture_application(
        raw_result: str, **kwargs: object
    ) -> tuple[EffectBatch, bridge.ApplyResult]:
        seen.append({"raw": raw_result, **kwargs})
        return (
            EffectBatch(source=source, effects=(), typed_result=None),
            bridge.ApplyResult(True, "recovered from accepted intent"),
        )

    monkeypatch.setattr(bridge, "run_guarded_effect_application", capture_application)
    monkeypatch.setattr(bridge, "observe_materialization_target", lambda *_args, **_kwargs: target)

    assert bridge.main() == 0
    captured = capsys.readouterr()
    assert '"applied": true' in captured.out
    assert len(seen) == 1
    assert seen[0]["raw"] == raw_worker_result
    assert seen[0]["source"] == source
    assert seen[0]["request_comment_id"] == 5810765007
    assert seen[0]["authorization_revision"] == current_revision
    assert seen[0]["accepted_intent"] is True
    assert seen[0]["allow_pending_continuation"] is False


def test_accepted_first_activation_recovers_legacy_mechanical_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "propose-change")
    materialization = {
        "issue_number": source.issue_number,
        "operation": "application-materialize",
        "expected_change": "unset",
        "change": "restore-no-work-idle-discovery",
        "branch": "agent/restore-no-work-idle-discovery",
        "base_sha": _REVISION,
        "message": "OpenSpec proposal",
        "files": [
            {
                "path": "openspec/changes/restore-no-work-idle-discovery/proposal.md",
                "blob_sha": "b" * 40,
                "expected_sha": None,
            }
        ],
        "pr_number": None,
    }
    original = _worker_result(
        action=source.action,
        role=source.role,
        result_kind="ready-for-openspec-review",
    )
    original["issue_number"] = source.issue_number
    original["requested_effects"] = [
        {
            "kind": "github-mutation",
            "payload_json": json.dumps(materialization, sort_keys=True),
        }
    ]
    semantic = dict(original)
    semantic["requested_effects"] = []
    semantic["_semantic_intent_version"] = 2
    semantic_raw = json.dumps(semantic, sort_keys=True, separators=(",", ":"))
    body = _effect_request(original)
    accepted = _accepted_record(
        semantic_raw,
        body,
        source=source,
        change="unset",
        result_kind="ready-for-openspec-review",
    )
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda _repository, _token, api_path, **_kwargs: (
            _connector_comment(102, body)
            if api_path == "issues/comments/102"
            else pytest.fail(api_path)
        ),
    )

    recovered = bridge._accepted_worker_result_for_continuation(
        accepted_intent=accepted,
        source=source,
        repository=_REPOSITORY,
        token=_REVISION,
        request_comment_id=102,
    )

    recovered_decoded = json.loads(recovered)
    recovered_decoded["requested_effects"] = []
    assert recovered_decoded == semantic
    assert (
        json.loads(json.loads(recovered)["requested_effects"][0]["payload_json"]) == materialization
    )


def test_main_keeps_rehydrated_first_activation_manifest_after_acceptance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = WorkerRequest(322, "lead", "propose-change")
    authorization_revision = "2" * 40
    current_revision = "a" * 40
    materialization = {
        "issue_number": source.issue_number,
        "operation": "application-materialize",
        "expected_change": "unset",
        "change": "restore-no-work-idle-discovery",
        "branch": "agent/restore-no-work-idle-discovery",
        "base_sha": authorization_revision,
        "message": "OpenSpec proposal",
        "files": [
            {
                "path": "openspec/changes/restore-no-work-idle-discovery/proposal.md",
                "blob_sha": "b" * 40,
                "expected_sha": None,
            }
        ],
        "pr_number": None,
    }
    original = _worker_result(
        action=source.action,
        role=source.role,
        result_kind="ready-for-openspec-review",
    )
    original["issue_number"] = source.issue_number
    original["result_content"] = (
        "ACTION_RESULT\\n"
        "Workflow: #322\\n"
        "Change: unset\\n"
        "Action: propose-change\\n"
        "Role: lead\\n"
        "Result: READY_FOR_OPENSPEC_REVIEW\\n"
        f"Revision: {authorization_revision}\\n"
        f"Default-Branch-Revision: {authorization_revision}\\n"
    )
    original["requested_effects"] = [
        {
            "kind": "github-mutation",
            "payload_json": json.dumps(materialization, sort_keys=True),
        }
    ]
    semantic = dict(original)
    semantic["requested_effects"] = []
    semantic["_semantic_intent_version"] = 2
    semantic_raw = json.dumps(semantic, sort_keys=True, separators=(",", ":"))
    request_body = _effect_request(original, revision=authorization_revision)
    accepted = _accepted_record(
        semantic_raw,
        request_body,
        source=source,
        change="unset",
        result_kind="ready-for-openspec-review",
    )
    accepted = bridge.replace(accepted, authorization_revision=authorization_revision)
    request_comment = _connector_comment(102, request_body)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(_event(request_body)), encoding="utf-8")
    output_path = tmp_path / "github-output.txt"
    seen: dict[str, object] = {}
    target = bridge.ValidationResourceTarget(
        repository=_REPOSITORY,
        revision="c" * 40,
        correlation="accepted-rerun",
        pr_number=17,
        change="restore-no-work-idle-discovery",
        validation_required=True,
    )

    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scheduled_agent_application_bridge",
            "--event-path",
            str(event_path),
            "--revision",
            current_revision,
            "--default-branch",
            "main",
            "--run-attempt",
            "2",
        ],
    )
    monkeypatch.setattr(
        bridge,
        "_application_decision_for_request",
        lambda **kwargs: (
            accepted
            if kwargs["issue_number"] == source.issue_number
            and kwargs["request_comment_id"] == accepted.request_comment_id
            else None
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda _repository, _token, api_path, **_kwargs: (
            request_comment
            if api_path == f"issues/comments/{accepted.request_comment_id}"
            else pytest.fail(api_path)
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_authorization_revision_is_ancestor",
        lambda *_args: True,
    )
    monkeypatch.setattr(
        bridge,
        "_fresh_event_observation",
        lambda *_args: pytest.fail("accepted recovery must not consult mutable transport"),
    )
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(
            issue_number=source.issue_number,
            action="review-openspec",
            change="unset",
        ),
    )

    def capture_repair(**kwargs: object) -> bool:
        seen["repair_source"] = kwargs["source"]
        seen["repair_manifest"] = kwargs["materialization"]
        return False

    monkeypatch.setattr(bridge, "_repair_partial_first_activation_route", capture_repair)

    def capture_validation_target(
        observed_materialization: object,
        observed_source: object,
        **kwargs: object,
    ) -> bridge.ValidationResourceTarget:
        seen["validation_materialization"] = observed_materialization
        seen["validation_source"] = observed_source
        seen["validation_revision"] = kwargs["current_revision"]
        seen["validation_default_branch"] = kwargs["default_branch"]
        seen["validation_pending_continuation"] = kwargs["allow_pending_continuation"]
        return target

    monkeypatch.setattr(bridge, "observe_materialization_target", capture_validation_target)

    def capture_application(
        raw_result: str,
        **kwargs: object,
    ) -> tuple[EffectBatch, bridge.ApplyResult]:
        seen["application_manifest"] = bridge._materialization_effects(
            raw_result,
            source,
            change="unset",
        )
        seen["apply_derived"] = kwargs["apply_derived"]
        return (
            EffectBatch(source=source, effects=(), typed_result=None),
            bridge.ApplyResult(True, "test interception before validation output"),
        )

    monkeypatch.setattr(bridge, "run_guarded_effect_application", capture_application)

    # The intercepted actuator reports application success; target observation remains mocked.
    assert bridge.main() == 0

    assert seen["repair_source"] == source
    assert seen["repair_manifest"] == materialization
    assert seen["application_manifest"] == (materialization,)
    assert seen["apply_derived"] is False
    assert seen["validation_materialization"] == materialization
    assert seen["validation_source"] == source
    assert seen["validation_revision"] == current_revision
    assert seen["validation_default_branch"] == "main"
    assert seen["validation_pending_continuation"] is True
    assert '"validation_required": true' in capsys.readouterr().out
    validation_outputs = output_path.read_text(encoding="utf-8")
    assert "validation_required=true" in validation_outputs
    assert f"validation_target_repository={target.repository}" in validation_outputs
    assert f"validation_target_revision={target.revision}" in validation_outputs
    assert f"validation_correlation={target.correlation}" in validation_outputs
    assert f"validation_pr_number={target.pr_number}" in validation_outputs
    assert f"validation_change={target.change}" in validation_outputs


def test_unbound_first_activation_result_matches_accepted_revision_after_main_advances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(322, "lead", "propose-change")
    accepted_revision = "2" * 40
    current_revision = "a" * 40
    semantic_result = _worker_result(
        action=source.action,
        role=source.role,
        result_kind="ready-for-openspec-review",
    )
    semantic_result["issue_number"] = source.issue_number
    semantic_result["result_content"] = (
        "ACTION_RESULT\n"
        "Workflow: #322\n"
        "Change: unset\n"
        "Action: propose-change\n"
        "Role: lead\n"
        "Result: READY_FOR_OPENSPEC_REVIEW\n"
        f"Revision: {accepted_revision}\n"
        f"Default-Branch-Revision: {accepted_revision}\n"
    )
    raw_result = json.dumps(semantic_result, sort_keys=True, separators=(",", ":"))
    request_body = _effect_request(semantic_result, revision=accepted_revision)
    accepted = _accepted_record(
        raw_result,
        request_body,
        source=source,
        change="unset",
        result_kind="ready-for-openspec-review",
    )
    accepted = bridge.replace(accepted, authorization_revision=accepted_revision)

    materialization = {
        "issue_number": source.issue_number,
        "operation": "application-materialize",
        "expected_change": "unset",
        "change": "restore-no-work-idle-discovery",
        "branch": "agent/restore-no-work-idle-discovery",
        "base_sha": accepted_revision,
        "message": "OpenSpec proposal",
        "files": [
            {
                "path": "openspec/changes/restore-no-work-idle-discovery/proposal.md",
                "blob_sha": "b" * 40,
                "expected_sha": None,
            }
        ],
        "pr_number": None,
    }
    recovered_result = dict(semantic_result)
    recovered_result["requested_effects"] = [
        {
            "kind": "github-mutation",
            "payload_json": json.dumps(materialization, sort_keys=True),
        }
    ]
    recovered_raw = json.dumps(recovered_result, sort_keys=True, separators=(",", ":"))

    current_result = bridge._fresh_application_worker_result(
        recovered_raw,
        source=source,
        change="unset",
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=current_revision,
        default_branch="main",
        request_comment_id=accepted.request_comment_id,
    )
    persisted_result = bridge._application_owned_worker_result(
        raw_result,
        source=source,
        change="unset",
        current_revision=accepted_revision,
        result_revision=accepted_revision,
        request_comment_id=accepted.request_comment_id,
    )
    current_worker_result = bridge.parse_worker_result(
        current_result,
        source,
        authorized_change="unset",
    )
    assert current_worker_result.result_content == semantic_result["result_content"]
    persisted_worker_result = bridge.parse_worker_result(
        persisted_result,
        source,
        authorized_change="unset",
    )
    comment = {
        "body": persisted_worker_result.result_content,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args: (comment,))

    assert bridge._unbound_first_activation_result_matches(
        worker_result=current_worker_result,
        source=source,
        accepted_intent=accepted,
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=current_revision,
        request_comment_id=accepted.request_comment_id,
    )

    stale_projection = bridge._application_owned_worker_result(
        recovered_raw,
        source=source,
        change="unset",
        current_revision=current_revision,
        result_revision=accepted_revision,
        request_comment_id=accepted.request_comment_id,
    )
    assert not bridge._unbound_first_activation_result_matches(
        worker_result=bridge.parse_worker_result(
            stale_projection,
            source,
            authorized_change="unset",
        ),
        source=source,
        accepted_intent=accepted,
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=current_revision,
        request_comment_id=accepted.request_comment_id,
    )

    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args: (comment, comment))
    assert not bridge._unbound_first_activation_result_matches(
        worker_result=current_worker_result,
        source=source,
        accepted_intent=accepted,
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=current_revision,
        request_comment_id=accepted.request_comment_id,
    )


def test_parse_application_request_decodes_revision_bound_worker_result() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None
    assert request.authorization_revision == _REVISION
    assert json.loads(request.raw_worker_result) == _worker_result()


def test_raw_worker_result_transport_canonicalizes_from_current_machine_source() -> None:
    source = WorkerRequest(138, "lead", "explore-change")
    worker = _worker_result()
    worker["change"] = _CHANGE
    raw = json.dumps(worker, sort_keys=True)
    body = f"WORKER_RESULT\n{raw}\n"
    request = bridge.canonicalize_raw_worker_result(
        body=body,
        source=source,
        authorized_change=_CHANGE,
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )
    assert request is not None
    assert request.raw_worker_result == raw
    assert request.dispatch_correlation == bridge.dispatch_correlation_for(
        _REPOSITORY, source, _REVISION
    )
    assert (
        bridge.parse_application_request(
            bridge.render_application_request(request, source=source, authorized_change=_CHANGE)
        )
        == request
    )
    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(),
        repository=_REPOSITORY,
        current_revision=_REVISION,
        allow_raw_result_transport=True,
        raw_shard_qualified=True,
    )
    assert plan.should_apply
    assert plan.request_comment_id == 102


def test_raw_worker_result_cannot_enter_phase_a_without_creation_shard_proof() -> None:
    source = WorkerRequest(138, "lead", "explore-change")
    raw = json.dumps(_worker_result(), sort_keys=True)
    body = f"WORKER_RESULT\n{raw}\n"
    request = bridge.canonicalize_raw_worker_result(
        body=body,
        source=source,
        authorized_change="unset",
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )
    with pytest.raises(ValueError, match="no verified current-shard source"):
        plan_application(
            event=_event(body),
            request=request,
            preflight=_preflight(),
            repository=_REPOSITORY,
            current_revision=_REVISION,
            allow_raw_result_transport=True,
        )


@pytest.mark.parametrize(
    ("variant", "accepted"),
    [
        ("current", True),
        ("closed-after-comment", True),
        ("cross-midnight-rollover", True),
        ("closed-get-open-list", True),
        ("open-get-closed-list", True),
        ("closed-before-comment", False),
        ("closed-without-closure-time", False),
        ("event-closed-before-comment", False),
        ("historical-closed", False),
        ("historical-open", False),
        ("wrong-date", False),
        ("duplicate-current-day", False),
        ("duplicate-closed-current-day", False),
        ("closed-at-comment-then-reopened", False),
        ("changed-timestamp", False),
        ("missing-timestamp", False),
        ("future-shard", False),
    ],
)
def test_new_raw_transport_requires_unique_creation_day_shard(
    monkeypatch: pytest.MonkeyPatch, variant: str, accepted: bool
) -> None:
    body = "WORKER_RESULT\n" + json.dumps(_worker_result(), sort_keys=True) + "\n"
    event = _event(body)
    event_comment = cast(dict[str, object], event["comment"])
    event_comment["created_at"] = "2026-09-03T03:00:00Z"  # Asia/Taipei 11:00
    event_issue = cast(dict[str, object], event["issue"])
    event_issue["created_at"] = "2026-09-02T17:00:00Z"
    current = dict(event_issue)
    if variant.startswith("historical") or variant == "wrong-date":
        current["title"] = checkin_title(date(2026, 9, 2))
    if variant == "historical-closed":
        current["state"] = "closed"
    if variant in {"closed-after-comment", "closed-get-open-list"}:
        current["state"] = "closed"
        current["closed_at"] = "2026-09-03T03:05:00Z"
    if variant == "cross-midnight-rollover":
        event_comment["created_at"] = "2026-09-03T15:59:59Z"  # Taipei 23:59:59
        current["state"] = "closed"
        current["closed_at"] = "2026-09-03T16:05:00Z"  # Taipei next day 00:05
    if variant == "closed-before-comment":
        current["state"] = "closed"
        current["closed_at"] = "2026-09-03T02:59:59Z"
    if variant == "closed-without-closure-time":
        current["state"] = "closed"
    if variant == "event-closed-before-comment":
        event_issue["state"] = "closed"
        current["state"] = "closed"
        current["closed_at"] = "2026-09-03T02:59:59Z"
    if variant == "closed-at-comment-then-reopened":
        event_issue["state"] = "closed"
    if variant == "future-shard":
        current["created_at"] = "2026-09-03T04:00:00Z"
    observed_comment = dict(event_comment)
    if variant == "changed-timestamp":
        observed_comment["created_at"] = "2026-09-03T03:01:00Z"
    if variant == "missing-timestamp":
        observed_comment.pop("created_at")
        event_comment.pop("created_at")

    list_issue = dict(current)
    if variant == "closed-get-open-list":
        list_issue["state"] = "open"
        list_issue["closed_at"] = None
    if variant == "open-get-closed-list":
        list_issue["state"] = "closed"
        list_issue["closed_at"] = "2026-09-03T03:05:00Z"
    issues = [list_issue]
    if variant.startswith("duplicate"):
        duplicate = dict(current)
        duplicate["number"] = 200
        if variant == "duplicate-closed-current-day":
            duplicate["state"] = "closed"
        issues.append(duplicate)

    def read(_repository: str, _token: str, api_path: str) -> object:
        if api_path == "issues/comments/102":
            return observed_comment
        if api_path == "issues/142":
            return current
        if api_path == "issues?state=all&per_page=100&page=1":
            return issues
        pytest.fail(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(bridge, "_github_json", read)
    if accepted:
        assert bridge._fresh_event_observation(event, body, _REPOSITORY, "token") is False
    else:
        with pytest.raises(ValueError, match="WORKER_RESULT"):
            bridge._fresh_event_observation(event, body, _REPOSITORY, "token")


def test_new_raw_transport_survives_rollover_between_pre_accept_observations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Phase-A recheck must not reject an event accepted before rollover."""

    body = "WORKER_RESULT\n" + json.dumps(_worker_result(), sort_keys=True) + "\n"
    event = _event(body)
    event_comment = cast(dict[str, object], event["comment"])
    event_comment["created_at"] = "2026-09-03T15:59:59Z"  # Taipei 23:59:59
    event_issue = cast(dict[str, object], event["issue"])
    event_issue["created_at"] = "2026-09-02T17:00:00Z"
    before_rollover = dict(event_issue)
    after_rollover = {**before_rollover, "state": "closed", "closed_at": "2026-09-03T16:05:00Z"}
    current = [before_rollover]

    def read(_repository: str, _token: str, api_path: str) -> object:
        if api_path == "issues/comments/102":
            return event_comment
        if api_path == "issues/142":
            return current[0]
        if api_path == "issues?state=all&per_page=100&page=1":
            return [current[0]]
        pytest.fail(f"unexpected GitHub read: {api_path}")

    monkeypatch.setattr(bridge, "_github_json", read)
    assert bridge._fresh_event_observation(event, body, _REPOSITORY, "token") is False
    current[0] = after_rollover
    assert bridge._fresh_event_observation(event, body, _REPOSITORY, "token") is False


def test_accepted_raw_result_continues_after_midnight_on_retired_shard() -> None:
    source = WorkerRequest(138, "lead", "explore-change")
    raw = json.dumps(_worker_result(), sort_keys=True)
    body = f"WORKER_RESULT\n{raw}\n"
    event = _event(body)
    event_issue = cast(dict[str, object], event["issue"])
    event_issue["state"] = "closed"  # A previously accepted shard has since rolled over.
    request = bridge.ApplicationRequest(authorization_revision=_REVISION, raw_worker_result=raw)
    accepted = _accepted_record(
        raw, body, source=source, change="unset", result_kind="proposal-ready"
    )
    plan = plan_application(
        event=event,
        request=request,
        preflight=_preflight(),
        repository=_REPOSITORY,
        current_revision=_REVISION,
        accepted_intent=accepted,
        accepted_request_comment_id=102,
        allow_accepted_request_mutation=True,
    )
    assert plan.should_apply
    assert plan.request_comment_id == 102
    assert plan.source == source


@pytest.mark.parametrize(
    "payload",
    [
        "WORKER_RESULT\nnot-json",
        "WORKER_RESULT\n{}\n\n",
        "WORKER_RESULT\n{}\nunknown: extra",
        "WORKER_RESULT\n[]",
        "WORKER_RESULT\n{}{}",
        'WORKER_RESULT\n{"result_kind":"blocked","unexpected":1}',
        'WORKER_RESULT\n{"result_kind":"blocked","result_kind":"blocked"}',
    ],
)
def test_raw_worker_result_transport_rejects_malformed_framing(payload: str) -> None:
    with pytest.raises(ValueError):
        bridge.canonicalize_raw_worker_result(
            body=payload,
            source=WorkerRequest(138, "lead", "explore-change"),
            authorized_change=_CHANGE,
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


@pytest.mark.parametrize("invalid", [None, "evidence", "changed", "claimed-source"])
def test_main_raw_worker_result_enters_existing_phase_a_without_second_comment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    invalid: str | None,
) -> None:
    worker = _worker_result()
    if invalid == "evidence":
        worker["evidence_ref"] = "not a valid reference"
    if invalid == "claimed-source":
        worker["issue_number"] = 999
    body = "WORKER_RESULT\n" + json.dumps(worker, sort_keys=True) + "\n"
    event = _event(body)
    event_path = tmp_path / "raw-result-event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", _REVISION)
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
        ],
    )
    seen: list[tuple[object, object]] = []

    def observe_raw_event(observed_event: object, observed_body: object, *_args: object) -> bool:
        seen.append((observed_event, observed_body))
        return invalid == "changed"

    monkeypatch.setattr(
        bridge,
        "_fresh_event_observation",
        observe_raw_event,
    )
    monkeypatch.setattr(bridge, "acquire_current_github_preflight", lambda *_args: _preflight())
    monkeypatch.setattr(
        bridge, "_find_application_decision_from_current_frontier", lambda **_kwargs: None
    )

    def phase_a(**kwargs: object) -> object:
        request = cast(bridge.ApplicationRequest, kwargs["request"])
        assert kwargs["allow_raw_result_transport"] is True
        assert kwargs["event"] == event
        assert request.authorization_revision == _REVISION
        assert json.loads(request.raw_worker_result) == worker
        assert request.dispatch_correlation == bridge.dispatch_correlation_for(
            _REPOSITORY, WorkerRequest(138, "lead", "explore-change"), _REVISION
        )
        return bridge.ApplicationPlan(False)

    monkeypatch.setattr(bridge, "plan_application", phase_a)
    if invalid is None:
        assert bridge.main() == 0
    else:
        with pytest.raises(ValueError):
            bridge.main()
    assert seen == [(event, body)]


def test_application_actions_real_job_dispatches_raw_results_into_same_entrypoint() -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/scheduled-agent-application.yml"
    ).read_text(encoding="utf-8")
    assert "startsWith(github.event.comment.body, 'WORKER_RESULT')" in workflow
    assert "uv run python -m investment_strategy.scheduled_agent_application_bridge" in workflow


def test_application_wire_accepts_one_terminal_newline_but_not_extra_fields() -> None:
    body = _effect_request()
    parsed = parse_application_request(body)
    assert parsed is not None
    assert parse_application_request(body + "\n") == parsed
    with pytest.raises(ValueError):
        parse_application_request(body + "\n\n")
    with pytest.raises(ValueError):
        parse_application_request(body + "\nUnknown: extra")


def test_application_formatter_preflights_canonical_typed_worker_fields() -> None:
    raw = json.dumps(
        {
            "issue_number": 138,
            "role": "lead",
            "action": "explore-change",
            "change": _CHANGE,
            "result_kind": "proposal-ready",
            "evidence_ref": "not a valid reference",
            "result_content": "evidence",
            "requested_effects": [],
        }
    )
    with pytest.raises(ValueError, match="evidence reference is invalid"):
        bridge.render_application_request(ApplicationRequest(_REVISION, raw))


def test_parse_application_request_rejects_old_correlation_shape() -> None:
    with pytest.raises(ValueError, match="exactly three lines"):
        parse_application_request("\n".join((APPLICATION_REQUEST_MARKER, "old", "old", "old")))


def test_application_continuation_is_content_addressed_and_strict() -> None:
    decision_sha256 = "a" * 64
    rendered = render_application_continuation_request(
        repository=_REPOSITORY,
        issue_number=138,
        original_request_comment_id=102,
        accepted_decision_sha256=decision_sha256,
        predecessor_run_id=_TEST_PREDECESSOR_RUN_ID,
        predecessor_run_attempt=_TEST_PREDECESSOR_RUN_ATTEMPT,
        predecessor_job_id=_TEST_PREDECESSOR_JOB_ID,
        predecessor_artifact_id=_TEST_PREDECESSOR_ARTIFACT_ID,
        predecessor_artifact_digest=_TEST_PREDECESSOR_ARTIFACT_DIGEST,
        failure_evidence_sha256=_TEST_FAILURE_EVIDENCE_SHA256,
        recovery_episode_sha256=_TEST_RECOVERY_EPISODE_SHA256,
    )

    parsed = parse_application_continuation_request(rendered)

    assert parsed is not None
    assert parsed.issue_number == 138
    assert parsed.original_request_comment_id == 102
    assert parsed.accepted_decision_sha256 == decision_sha256
    assert parsed.continuation_correlation == application_continuation_correlation(
        _REPOSITORY,
        138,
        102,
        decision_sha256,
        _TEST_PREDECESSOR_RUN_ID,
        _TEST_PREDECESSOR_RUN_ATTEMPT,
        _TEST_PREDECESSOR_JOB_ID,
        _TEST_PREDECESSOR_ARTIFACT_ID,
        _TEST_PREDECESSOR_ARTIFACT_DIGEST,
        _TEST_FAILURE_EVIDENCE_SHA256,
        _TEST_RECOVERY_EPISODE_SHA256,
    )
    assert parse_application_continuation_request(rendered + "\nextra") is None
    assert (
        parse_application_continuation_request(rendered.replace("Issue: 138", "Issue: 0138"))
        is None
    )


@pytest.mark.parametrize("invalid", [None, "duplicate", "untrusted", "missing-accept"])
def test_continuation_predecessor_qualifies_runtime_shard_transport_separately_from_formal_issue(
    monkeypatch: pytest.MonkeyPatch,
    invalid: str | None,
) -> None:
    """Accepted decisions live on #322; continuation comments live on the daily shard."""
    decision_body = "accepted decision"
    digest = hashlib.sha256(decision_body.encode()).hexdigest()
    body = render_application_continuation_request(
        repository=_REPOSITORY,
        issue_number=322,
        original_request_comment_id=102,
        accepted_decision_sha256=digest,
        predecessor_run_id=_TEST_PREDECESSOR_RUN_ID,
        predecessor_run_attempt=_TEST_PREDECESSOR_RUN_ATTEMPT,
        predecessor_job_id=_TEST_PREDECESSOR_JOB_ID,
        predecessor_artifact_id=_TEST_PREDECESSOR_ARTIFACT_ID,
        predecessor_artifact_digest=_TEST_PREDECESSOR_ARTIFACT_DIGEST,
        failure_evidence_sha256=_TEST_FAILURE_EVIDENCE_SHA256,
        recovery_episode_sha256=_TEST_RECOVERY_EPISODE_SHA256,
    )
    continuation = parse_application_continuation_request(body)
    assert continuation is not None
    formal = [{"id": 105, "body": decision_body}]
    transport = [_connector_comment(404, body, trusted=invalid != "untrusted")]
    if invalid == "duplicate":
        transport.append(_connector_comment(405, body))
    if invalid == "missing-accept":
        formal.clear()

    def read_comments(_repo: str, _token: str, path: str) -> list[dict[str, object]]:
        if path == "issues/322/comments?sort=created&direction=asc":
            return formal
        if path == "issues/396/comments?sort=created&direction=asc":
            return transport
        pytest.fail(f"unexpected comment source: {path}")

    monkeypatch.setattr(bridge, "_paged_github_list", read_comments)
    monkeypatch.setattr(
        bridge,
        "parse_application_decision",
        lambda value: (
            SimpleNamespace(request_comment_id=102, disposition="ACCEPTED")
            if value == decision_body
            else None
        ),
    )
    monkeypatch.setattr(bridge, "is_github_actions_comment", lambda item: item in formal)
    evidence = SimpleNamespace(
        artifact_id=_TEST_PREDECESSOR_ARTIFACT_ID,
        artifact_digest=_TEST_PREDECESSOR_ARTIFACT_DIGEST,
        failure_evidence_sha256=_TEST_FAILURE_EVIDENCE_SHA256,
        recovery_episode_sha256=_TEST_RECOVERY_EPISODE_SHA256,
        continuation_eligible=True,
        document={"prior_failure_evidence_sha256": []},
    )
    monkeypatch.setattr(
        bridge, "read_application_recovery_artifact", lambda *_args, **_kwargs: evidence
    )
    observed = bridge.qualify_application_continuation_predecessor(
        _REPOSITORY,
        "token",
        continuation,
        current_comment_id=404,
        transport_issue_number=396,
    )
    assert (observed is evidence) == (invalid is None)


def test_accepted_continuation_binds_original_request_not_relay_comment() -> None:
    source = WorkerRequest(138, "lead", "finalize-change")
    worker = _worker_result(action=source.action, role=source.role, result_kind="archive-ready")
    worker["change"] = _CHANGE
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    original_body = _effect_request(worker)
    record = _accepted_record(
        raw,
        original_body,
        source=source,
        change=_CHANGE,
        result_kind="archive-ready",
        request_comment_id=102,
    )
    continuation_body = render_application_continuation_request(
        repository=_REPOSITORY,
        issue_number=source.issue_number,
        original_request_comment_id=record.request_comment_id,
        accepted_decision_sha256="b" * 64,
        predecessor_run_id=_TEST_PREDECESSOR_RUN_ID,
        predecessor_run_attempt=_TEST_PREDECESSOR_RUN_ATTEMPT,
        predecessor_job_id=_TEST_PREDECESSOR_JOB_ID,
        predecessor_artifact_id=_TEST_PREDECESSOR_ARTIFACT_ID,
        predecessor_artifact_digest=_TEST_PREDECESSOR_ARTIFACT_DIGEST,
        failure_evidence_sha256=_TEST_FAILURE_EVIDENCE_SHA256,
        recovery_episode_sha256=_TEST_RECOVERY_EPISODE_SHA256,
    )
    continuation_request = ApplicationRequest(_REVISION, raw)

    plan = plan_application(
        event=_event(continuation_body, comment_id=404),
        request=continuation_request,
        preflight=_preflight(
            issue_number=source.issue_number,
            action=source.action,
            change=_CHANGE,
        ),
        repository=_REPOSITORY,
        current_revision=_REVISION,
        token=_REVISION,
        allow_descendant_resume=True,
        allow_accepted_request_mutation=True,
        accepted_intent=record,
        accepted_request_comment_id=record.request_comment_id,
    )

    assert plan.should_apply
    assert plan.source == source
    assert plan.request_comment_id == record.request_comment_id
    with pytest.raises(ValueError, match="request identity"):
        plan_application(
            event=_event(continuation_body, comment_id=404),
            request=continuation_request,
            preflight=_preflight(
                issue_number=source.issue_number,
                action=source.action,
                change=_CHANGE,
            ),
            repository=_REPOSITORY,
            current_revision=_REVISION,
            token=_REVISION,
            allow_descendant_resume=True,
            allow_accepted_request_mutation=True,
            accepted_intent=record,
            accepted_request_comment_id=999,
        )


def test_plan_application_derives_source_from_fresh_repository_preflight() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(),
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source == WorkerRequest(138, "lead", "explore-change")
    assert plan.request_comment_id == 102
    assert json.loads(plan.raw_worker_result or "") == _worker_result()


def test_plan_application_accepts_semantic_only_ingress_and_derives_machine_envelope() -> None:
    semantic: dict[str, object] = {
        "result_kind": "blocked",
        "evidence_ref": None,
        "result_content": "runner capability evidence",
    }
    body = _effect_request(semantic)
    request = parse_application_request(body)
    assert request is not None

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(),
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source == WorkerRequest(138, "lead", "explore-change")
    assert plan.change == "unset"
    normalized = bridge._application_owned_worker_result(
        plan.raw_worker_result or "",
        source=plan.source,
        change=plan.change,
        current_revision=_REVISION,
        request_comment_id=plan.request_comment_id,
    )
    payload = json.loads(normalized)
    assert payload["issue_number"] == 138
    assert payload["role"] == "lead"
    assert payload["action"] == "explore-change"
    assert payload["change"] == "unset"
    assert payload["requested_effects"]
    assert payload["requested_effects"][-1]["kind"] == "issue-comment"


def test_application_request_round_trips_one_opaque_dispatch_correlation() -> None:
    source = WorkerRequest(138, "lead", "explore-change")
    correlation = bridge.dispatch_correlation_for(_REPOSITORY, source, _REVISION)
    raw = json.dumps({"result_kind": "blocked", "result_content": "evidence"})
    request = bridge.ApplicationRequest(_REVISION, raw, correlation)

    # An externally supplied opaque payload still parses as transport, but is
    # forbidden to pass the production emitter's typed-result preflight.
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    body = (
        f"{APPLICATION_REQUEST_MARKER}\n"
        f"{AUTHORIZATION_REVISION_PREFIX}{_REVISION}\n"
        f"{bridge.DISPATCH_CORRELATION_PREFIX}{correlation}\n"
        f"{bridge.WORKER_RESULT_B64_PREFIX}{encoded}"
    )
    parsed = parse_application_request(body)

    assert parsed == request
    with pytest.raises(ValueError, match="source is required"):
        bridge.render_application_request(request)


def test_plan_application_rejects_untrusted_or_stale_ingress() -> None:
    body = _effect_request()
    request = parse_application_request(body)
    assert request is not None

    with pytest.raises(ValueError, match="configured ChatGPT connector"):
        plan_application(
            event=_event(body, trusted=False),
            request=request,
            preflight=_preflight(),
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )

    stale_request = parse_application_request(_effect_request(revision="0" * 40))
    assert stale_request is not None
    with pytest.raises(ValueError, match="authorization revision is stale"):
        plan_application(
            event=_event(_effect_request(revision="0" * 40)),
            request=stale_request,
            preflight=_preflight(),
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_accepted_intent_recovery_keeps_original_source_across_successor_frontier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_source = WorkerRequest(142, "lead", "finalize-change")
    current_source = WorkerRequest(142, "reviewer", "review-archive")
    worker = _worker_result(
        action=old_source.action,
        role=old_source.role,
        result_kind="archive-ready",
    )
    worker["issue_number"] = old_source.issue_number
    worker["change"] = _CHANGE
    raw_worker_result = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    old_correlation = bridge.dispatch_correlation_for(_REPOSITORY, old_source, _REVISION)
    current_correlation = bridge.dispatch_correlation_for(_REPOSITORY, current_source, _REVISION)
    assert old_correlation != current_correlation
    request = bridge.ApplicationRequest(_REVISION, raw_worker_result, old_correlation)
    body = bridge.render_application_request(request)
    parsed = parse_application_request(body)
    assert parsed == request
    accepted_intent = ApplicationDecisionRecord(
        request_comment_id=102,
        request_body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
        authorization_revision=_REVISION,
        issue_number=old_source.issue_number,
        role=old_source.role,
        action=old_source.action,
        change=_CHANGE,
        result_kind="archive-ready",
        disposition="ACCEPTED",
        worker_result_sha256=hashlib.sha256(raw_worker_result.encode("utf-8")).hexdigest(),
        raw_worker_result=raw_worker_result,
        reason="test",
    )

    monkeypatch.setattr(bridge, "_authorization_revision_is_ancestor", lambda *_args: True)
    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(
            issue_number=current_source.issue_number,
            action=current_source.action,
            change=_CHANGE,
        ),
        repository=_REPOSITORY,
        current_revision=_REVISION,
        token=_CHANGE,
        allow_descendant_resume=True,
        allow_accepted_request_mutation=True,
        accepted_intent=accepted_intent,
    )

    assert plan.should_apply
    assert plan.source == old_source
    assert plan.change == _CHANGE
    assert plan.request_comment_id == 102
    assert plan.raw_worker_result == raw_worker_result


def test_plan_application_rejects_worker_claim_that_differs_from_fresh_selection() -> None:
    body = _effect_request(
        _worker_result(action="resolve-question", result_kind="human-decision-required")
    )
    request = parse_application_request(body)
    assert request is not None
    with pytest.raises(ValueError, match="does not match fresh repository Action"):
        plan_application(
            event=_event(body),
            request=request,
            preflight=_preflight(),
            repository=_REPOSITORY,
            current_revision=_REVISION,
        )


def test_main_validation_boundary_preserves_exact_binding_for_fresh_successor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected_source = WorkerRequest(138, "lead", "resolve-question")
    formal_body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: resolve-question\n"
        "Role: lead\n"
        "Result: READY\n"
        f"Revision: {_REVISION}\n"
        "Evidence-Ref: issuecomment-worker-evidence\n"
    )
    materialization = {
        "issue_number": 138,
        "operation": "application-materialize",
        "expected_change": _CHANGE,
        "change": _CHANGE,
        "branch": f"agent/{_CHANGE}",
        "base_sha": _REVISION,
        "message": "test validation boundary",
        "files": [],
        "pr_number": 178,
    }
    worker_result = _worker_result(
        action="resolve-question",
        role="lead",
        result_kind="ready",
    )
    worker_result["change"] = _CHANGE
    worker_result["requested_effects"] = [
        {
            "kind": "issue-comment",
            "payload_json": json.dumps({"issue_number": 138, "body": formal_body}),
        },
        {
            "kind": "github-mutation",
            "payload_json": json.dumps(materialization, sort_keys=True),
        },
    ]
    body = _effect_request(worker_result, revision=_REVISION)
    accepted_raw = json.dumps(worker_result, sort_keys=True, separators=(",", ":"))
    accepted_intent = ApplicationDecisionRecord(
        request_comment_id=102,
        request_body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
        authorization_revision=_REVISION,
        issue_number=138,
        role="lead",
        action="resolve-question",
        change=_CHANGE,
        result_kind="ready",
        disposition="ACCEPTED",
        worker_result_sha256=hashlib.sha256(accepted_raw.encode("utf-8")).hexdigest(),
        raw_worker_result=accepted_raw,
        reason="test",
    )
    event = _event(body)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    output_path = tmp_path / "github-output.txt"

    target = ValidationResourceTarget(
        repository=_REPOSITORY,
        revision="b" * 40,
        correlation="effect-request-138",
        pr_number=178,
        change=_CHANGE,
        validation_required=True,
    )
    applications: list[GitHubEffectAdapter] = []
    durable_evidence: list[str] = []
    calls: list[dict[str, object]] = []

    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setattr(bridge, "_fresh_event_observation", lambda *_args: None)
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(
            action="resolve-question",
            issue_number=138,
            change=_CHANGE,
        ),
    )
    monkeypatch.setattr(
        bridge,
        "observe_materialization_target",
        lambda *_args, **_kwargs: target,
    )

    def fake_run(
        _raw_worker_result: str,
        *,
        source: WorkerRequest,
        repository: str,
        token: str,
        current_revision: str,
        request_comment_id: int | None = None,
        apply_derived: bool = True,
        materialization_promote_change: bool = False,
        validated_materialization_revision: str | None = None,
        defer_issue_comments: bool = False,
        allow_pending_continuation: bool = False,
        pending_application_correlation: str | None = None,
        application_request_body: str | None = None,
        authorization_revision: str | None = None,
        authorized_change: str | None = None,
        accepted_intent: bool = False,
        uncertain_effect_index: int | None = None,
    ) -> tuple[EffectBatch, bridge.ApplyResult]:
        assert source == expected_source
        assert request_comment_id == 102
        assert allow_pending_continuation is False
        assert pending_application_correlation is None
        assert application_request_body == body
        assert authorization_revision == _REVISION
        assert authorized_change == _CHANGE
        assert accepted_intent is (len(calls) > 0)
        assert uncertain_effect_index is None
        adapter = GitHubEffectAdapter(
            repository,
            token,
            source,
            authorized_change=_CHANGE,
            current_revision=current_revision,
            expected_result_kind="ready",
            request_comment_id=request_comment_id,
        )
        applications.append(adapter)
        calls.append(
            {
                "request_comment_id": request_comment_id,
                "apply_derived": apply_derived,
                "materialization_promote_change": materialization_promote_change,
                "validated_materialization_revision": validated_materialization_revision,
                "defer_issue_comments": defer_issue_comments,
                "allow_pending_continuation": allow_pending_continuation,
                "pending_application_correlation": pending_application_correlation,
                "application_request_body": application_request_body,
                "authorization_revision": authorization_revision,
                "accepted_intent": accepted_intent,
            }
        )
        correlation = formal_application_correlation(
            source,
            change=_CHANGE,
            result_kind="ready",
            current_revision=current_revision,
            request_comment_id=102,
        )
        bound = formal_body.replace(
            "Evidence-Ref: issuecomment-worker-evidence\n",
            (
                f"Application-Correlation: {correlation}\n"
                "Evidence-Ref: issuecomment-worker-evidence\n"
            ),
        )
        if apply_derived:
            assert materialization_promote_change
            assert validated_materialization_revision == target.revision
            assert durable_evidence == [bound]
            assert source.action == "resolve-question"
        else:
            assert not materialization_promote_change
            assert validated_materialization_revision is None
            assert durable_evidence == []
            durable_evidence.append(bound)
        return EffectBatch(source=source, effects=()), bridge.ApplyResult(True, "applied")

    monkeypatch.setattr(bridge, "run_guarded_effect_application", fake_run)
    monkeypatch.setattr(
        bridge,
        "_application_decision_for_request",
        lambda **_kwargs: accepted_intent,
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
        ],
    )
    assert bridge.main() == 0

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
            target.revision,
        ],
    )
    assert bridge.main() == 0

    assert calls == [
        {
            "request_comment_id": 102,
            "apply_derived": False,
            "materialization_promote_change": False,
            "validated_materialization_revision": None,
            "defer_issue_comments": True,
            "allow_pending_continuation": False,
            "pending_application_correlation": None,
            "application_request_body": body,
            "authorization_revision": _REVISION,
            "accepted_intent": False,
        },
        {
            "request_comment_id": 102,
            "apply_derived": True,
            "materialization_promote_change": True,
            "validated_materialization_revision": target.revision,
            "defer_issue_comments": False,
            "allow_pending_continuation": False,
            "pending_application_correlation": None,
            "application_request_body": body,
            "authorization_revision": _REVISION,
            "accepted_intent": True,
        },
    ]
    assert len(applications) == 2
    assert applications[0] is not applications[1]
    assert all(not hasattr(adapter, "_formal_evidence_observed") for adapter in applications)
    correlation = formal_application_correlation(
        expected_source,
        change=_CHANGE,
        result_kind="ready",
        current_revision=_REVISION,
        request_comment_id=102,
    )
    assert durable_evidence == [
        formal_body.replace(
            "Evidence-Ref: issuecomment-worker-evidence\n",
            (
                f"Application-Correlation: {correlation}\n"
                "Evidence-Ref: issuecomment-worker-evidence\n"
            ),
        )
    ]
    output = capsys.readouterr().out
    assert '"validation_completed": false' in output
    assert '"validation_completed": true' in output


def test_plan_application_recovers_a_persisted_validation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    result_body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: resolve-question\n"
        "Role: lead\n"
        "Result: READY_FOR_OPENSPEC_REVIEW\n"
        f"Revision: {_REVISION}\n"
        f"Default-Branch-Revision: {_REVISION}\n"
        "Evidence-Ref: issuecomment-worker-evidence\n"
        "Repository-derived successor: Reviewer / review-openspec\n"
    )
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="ready-for-openspec-review",
        current_revision=_REVISION,
        request_comment_id=777,
    )
    bound_lines = result_body.splitlines()
    bound_lines.insert(
        next(
            index
            for index, line in enumerate(bound_lines)
            if line.startswith("Default-Branch-Revision:")
        )
        + 1,
        f"Application-Correlation: {correlation}",
    )
    bound_body = "\n".join(bound_lines)
    materialization = {
        "issue_number": 138,
        "operation": "application-materialize",
        "expected_change": _CHANGE,
        "change": _CHANGE,
        "branch": f"agent/{_CHANGE}",
        "base_sha": _REVISION,
        "message": "test validation boundary",
        "files": [],
        "pr_number": 178,
    }
    worker_result = {
        "issue_number": 138,
        "role": "lead",
        "action": "resolve-question",
        "change": _CHANGE,
        "result_kind": "ready-for-openspec-review",
        "evidence_ref": "issuecomment-worker-evidence",
        "result_content": result_body,
        "requested_effects": [
            {
                "kind": "github-mutation",
                "payload_json": json.dumps(materialization, sort_keys=True),
            },
            {
                "kind": "issue-comment",
                "payload_json": json.dumps({"issue_number": 138, "body": result_body}),
            },
        ],
    }
    body = _effect_request(worker_result)
    request = parse_application_request(body)
    assert request is not None
    comment = {
        "id": 900,
        "body": bound_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda *_args, **_kwargs: {
            "number": 138,
            "state": "open",
            "created_at": "2026-09-17T00:00:00Z",
            "closed_at": None,
            "labels": [{"name": "action:resolve-question"}],
            "body": f"Change: {_CHANGE}",
        },
    )
    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda _repository, _token, path: (
            (comment,)
            if "comments" in path
            else (
                {
                    "event": "commented",
                    "id": 900,
                    "created_at": "2026-09-17T00:00:00Z",
                },
            )
        ),
    )

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(
            action="resolve-question",
            issue_number=138,
            change=_CHANGE,
            current_state_provenance=ObservationProvenance.INDETERMINATE,
        ),
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source == source
    assert plan.pending_continuation
    assert plan.pending_application_correlation == correlation


def test_plan_application_recovers_persisted_result_after_main_advances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    historical_revision = "3" * 40
    current_revision = "4" * 40
    result_body = (
        "ACTION_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: resolve-question\n"
        "Role: lead\n"
        "Result: READY_FOR_OPENSPEC_REVIEW\n"
        f"Revision: {historical_revision}\n"
        f"Default-Branch-Revision: {historical_revision}\n"
        "Evidence-Ref: issuecomment-worker-evidence\n"
        "Repository-derived successor: Reviewer / review-openspec\n"
    )
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="ready-for-openspec-review",
        current_revision=historical_revision,
        request_comment_id=777,
    )
    bound_lines = result_body.splitlines()
    bound_lines.insert(
        next(
            index
            for index, line in enumerate(bound_lines)
            if line.startswith("Default-Branch-Revision:")
        )
        + 1,
        f"Application-Correlation: {correlation}",
    )
    bound_body = "\n".join(bound_lines)
    materialization = {
        "issue_number": 138,
        "operation": "application-materialize",
        "expected_change": _CHANGE,
        "change": _CHANGE,
        "branch": f"agent/{_CHANGE}",
        "base_sha": historical_revision,
        "message": "test validation boundary",
        "files": [],
        "pr_number": 178,
    }
    worker_result = {
        "issue_number": 138,
        "role": "lead",
        "action": "resolve-question",
        "change": _CHANGE,
        "result_kind": "ready-for-openspec-review",
        "evidence_ref": "issuecomment-worker-evidence",
        "result_content": result_body,
        "requested_effects": [
            {
                "kind": "github-mutation",
                "payload_json": json.dumps(materialization, sort_keys=True),
            },
            {
                "kind": "issue-comment",
                "payload_json": json.dumps({"issue_number": 138, "body": result_body}),
            },
        ],
    }
    body = _effect_request(worker_result, revision=current_revision)
    request = parse_application_request(body)
    assert request is not None
    comment = {
        "id": 900,
        "body": bound_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    recovery_revision = "2" * 40
    recovery_comment = {
        "id": 899,
        "body": (
            "APPLICATION_RECOVERY\n"
            "Workflow: #138\n"
            f"Change: {_CHANGE}\n"
            "Source: Lead / propose-change\n"
            "Target: Lead / resolve-question\n"
            f"Default-Branch-Revision: {recovery_revision}\n"
            f"Failed-Authorization-Revision: {'1' * 40}\n"
            "Request-Comment-ID: 901\n"
            "Reason: partial-first-activation"
        ),
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda *_args, **_kwargs: {
            "number": 138,
            "state": "open",
            "created_at": "2026-09-17T00:00:00Z",
            "closed_at": None,
            "labels": [{"name": "action:resolve-question"}],
            "body": f"Change: {_CHANGE}",
        },
    )
    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda _repository, _token, path: (
            (recovery_comment, comment)
            if "comments" in path
            else (
                {
                    "event": "commented",
                    "id": 899,
                    "created_at": "2026-09-17T00:00:00Z",
                },
                {
                    "event": "unlabeled",
                    "id": 901,
                    "created_at": "2026-09-17T00:00:01Z",
                    "label": {"name": "action:propose-change"},
                },
                {
                    "event": "labeled",
                    "id": 902,
                    "created_at": "2026-09-17T00:00:01Z",
                    "label": {"name": "action:resolve-question"},
                },
                {
                    "event": "commented",
                    "id": 900,
                    "created_at": "2026-09-17T00:00:02Z",
                },
            )
        ),
    )
    ancestry_calls: list[tuple[object, ...]] = []

    def fake_ancestor(*args: str) -> bool:
        ancestry_calls.append(args)
        return True

    monkeypatch.setattr(bridge, "_authorization_revision_is_ancestor", fake_ancestor)

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(
            action="resolve-question",
            issue_number=138,
            change=_CHANGE,
            current_state_provenance=ObservationProvenance.INDETERMINATE,
        ),
        repository=_REPOSITORY,
        current_revision=current_revision,
    )

    assert plan.should_apply
    assert plan.source == source
    assert plan.pending_continuation
    assert plan.pending_application_correlation == correlation
    assert {call[2] for call in ancestry_calls} == {historical_revision, recovery_revision}


def test_plan_application_recovers_persisted_formal_result_without_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(138, "reviewer", "review-openspec")
    result_body = (
        "REVIEW_RESULT\n"
        "Workflow: #138\n"
        f"Change: {_CHANGE}\n"
        "Action: Reviewer / review-openspec\n"
        "Role: reviewer\n"
        "Result: PASS\n"
        f"Revision: {_REVISION}\n"
        f"Default-Branch-Revision: {_REVISION}\n"
        "Evidence-Ref: issuecomment-worker-evidence\n"
        "Repository-derived successor: Executor / implement-change\n"
    )
    correlation = formal_application_correlation(
        source,
        change=_CHANGE,
        result_kind="pass",
        current_revision=_REVISION,
        request_comment_id=777,
    )
    bound_lines = result_body.splitlines()
    bound_lines.insert(
        next(
            index
            for index, line in enumerate(bound_lines)
            if line.startswith("Default-Branch-Revision:")
        )
        + 1,
        f"Application-Correlation: {correlation}",
    )
    bound_body = "\n".join(bound_lines)
    worker_result = {
        "issue_number": 138,
        "role": "reviewer",
        "action": "review-openspec",
        "change": _CHANGE,
        "result_kind": "pass",
        "evidence_ref": "issuecomment-worker-evidence",
        "result_content": (
            "worker summary; canonical formal body is in the requested issue-comment effect"
        ),
        "requested_effects": [
            {
                "kind": "issue-comment",
                "payload_json": json.dumps(
                    {"issue_number": 138, "body": result_body},
                    sort_keys=True,
                ),
            }
        ],
    }
    body = _effect_request(worker_result)
    request = parse_application_request(body)
    assert request is not None
    current_issue = {
        "number": 138,
        "title": checkin_title(date(2026, 9, 3)),
        "state": "open",
        "created_at": "2026-09-17T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "action:review-openspec"}],
        "body": f"Change: {_CHANGE}",
    }
    comment = {
        "id": 900,
        "body": bound_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    monkeypatch.setattr(
        bridge,
        "_github_json",
        lambda *_args, **_kwargs: current_issue,
    )
    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda _repository, _token, path: (
            (comment,)
            if "comments" in path
            else (
                {
                    "event": "commented",
                    "id": 900,
                    "created_at": "2026-09-17T00:00:00Z",
                },
            )
        ),
    )

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(
            action="review-openspec",
            issue_number=138,
            change=_CHANGE,
            current_state_provenance=ObservationProvenance.INDETERMINATE,
        ),
        repository=_REPOSITORY,
        current_revision=_REVISION,
    )

    assert plan.should_apply
    assert plan.source == source
    assert plan.pending_continuation
    assert plan.pending_application_correlation == correlation


def test_real_issue233_mixed_formal_history_recovers_persisted_review_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(233, "reviewer", "review-openspec")
    change = "operationalize-review-openspec-semantic-proof"
    historical_review_revision = "7f7a376bb052d6b45307ee04587719dcc430cd39"
    review_authorization_revision = "1991e31bf97b0286d5f4affb3dff5e9354b32c9a"
    current_revision = "b708129828e541227095ff801c2801907bae7d2e"
    result_body = (
        "REVIEW_RESULT\n"
        "Workflow: #233\n"
        f"Change: {change}\n"
        "Action: Reviewer / review-openspec\n"
        "Role: reviewer\n"
        "Result: PASS\n"
        f"Revision: {historical_review_revision}\n"
        f"Default-Branch-Revision: {review_authorization_revision}\n"
        "Evidence-Ref: https://github.com/royhsu-work/investment-strategy/pull/247\n"
        "Review-Mode: fresh exact-revision independent reverse-first and forward semantic review\n"
        "Traceability: tasks -> design -> specs -> proposal and "
        "proposal -> specs -> design -> tasks are complete for the "
        "same exact zero-delta target.\n"
        "Parent: Human-approved repository-wide semantic-consumption scope and the "
        "#229 regression boundary are preserved; the active-formal case remains a "
        "proof case, not a scope replacement.\n"
        "Boundary: DERIVE -> CHALLENGE -> REALIZE -> CLOSE operationalizes the "
        "existing review owner without adding an Action, Result, state, verifier, "
        "registry, second workflow graph, or semantic authority.\n"
        "Runtime-Evidence: The current-main closed-history and recovery-ancestry repairs "
        "are reused; the proposal keeps the pre-activation -> durable producer/"
        "application evidence -> descendant qualification -> typed continuation -> "
        "application postcondition chain explicit.\n"
        "Substrate: Strict OpenSpec validation passed 8/8 for the exact PR #247 head, "
        "and the remaining Skill/test changes are bounded implementation work on the "
        "existing repository Skill/test owners.\n"
        "Safety: Current/default evidence is distinguished from candidate, staged, future, "
        "or unavailable proof; application/carrier authority, fresh reauthorization, "
        "lifecycle/ABA qualification, and fail-closed behavior remain intact.\n"
        "Skill-Maintenance: The existing agents/skills/openspec-review/SKILL.md is the "
        "sole declared procedure owner; validator/wiring coverage is planned on the "
        "existing repository-Skill test surface.\n"
        "Findings: None.\n"
        "Repository-derived successor: Executor / implement-change"
    )
    application_correlation = formal_application_correlation(
        source,
        change=change,
        result_kind="pass",
        current_revision=review_authorization_revision,
        request_comment_id=5710940292,
    )
    persisted_body = result_body.replace(
        f"Default-Branch-Revision: {review_authorization_revision}\n",
        (
            f"Default-Branch-Revision: {review_authorization_revision}\n"
            f"Application-Correlation: {application_correlation}\n"
        ),
    )
    recovery_body = (
        "APPLICATION_RECOVERY\n"
        "Workflow: #233\n"
        f"Change: {change}\n"
        "Source: Lead / propose-change\n"
        "Target: Lead / resolve-question\n"
        "Default-Branch-Revision: cf953ef356bdbd05848cdaf74663f4281bbe8a25\n"
        "Failed-Authorization-Revision: 24308310d6d65064ddd3a3d76e43cd3c9dd87cdc\n"
        "Request-Comment-ID: 5693106011\n"
        "Reason: partial-first-activation"
    )
    old_formal_body = (
        "ACTION_RESULT\n"
        "Workflow: #233\n"
        f"Change: {change}\n"
        "Action: resolve-question\n"
        "Role: lead\n"
        "Result: READY_FOR_OPENSPEC_REVIEW\n"
        "Revision: 0923580f161408c2953700b7e07e1c34dd03b5b5\n"
        "Default-Branch-Revision: 0923580f161408c2953700b7e07e1c34dd03b5b5\n"
        "Application-Correlation: application:5709636345:233:"
        "operationalize-review-openspec-semantic-proof:lead:"
        "resolve-question:ready-for-openspec-review:"
        "0923580f161408c2953700b7e07e1c34dd03b5b5\n"
        "Evidence-Ref: https://github.com/royhsu-work/investment-strategy/pull/247\n"
        "Decision: The proposal now includes the review-consumption repair and the "
        "residual formal-activation/application closure.\n"
        "Decision: Existing runtime/application owners and the current descendant/"
        "recovery evidence remain authoritative; no new state, exception, or review "
        "layer is introduced.\n"
        "Verification: PR #247 is the exact carrier for fresh independent review after "
        "application-owned materialization and strict OpenSpec validation.\n"
        "Repository-derived successor: Reviewer / review-openspec\n"
    )

    def bot_comment(comment_id: int, body: str) -> dict[str, object]:
        return {
            "id": comment_id,
            "body": body,
            "user": {"login": "github-actions[bot]"},
            "performed_via_github_app": {"slug": "github-actions"},
        }

    recovery_comment = bot_comment(5707223672, recovery_body)
    old_formal_comment = bot_comment(5709649340, old_formal_body)
    persisted_formal_comment = bot_comment(5710947012, persisted_body)
    worker_result = {
        "issue_number": 233,
        "role": "reviewer",
        "action": "review-openspec",
        "change": change,
        "result_kind": "pass",
        "evidence_ref": "https://github.com/royhsu-work/investment-strategy/pull/247",
        "result_content": result_body,
        "requested_effects": [
            {
                "kind": "issue-comment",
                "payload_json": json.dumps(
                    {"issue_number": 233, "body": result_body},
                    sort_keys=True,
                ),
            }
        ],
    }
    request_body = _effect_request(worker_result, revision=current_revision)
    request = parse_application_request(request_body)
    assert request is not None
    event = {
        "action": "created",
        "issue": {
            "number": 252,
            "title": checkin_title(date(2026, 9, 17)),
            "state": "open",
            "labels": [],
        },
        "comment": _connector_comment(5711090028, request_body),
    }
    current_issue = {
        "number": 233,
        "title": "Explore review-openspec semantic gate consumption after #229 PASS",
        "state": "open",
        "created_at": "2026-09-09T07:28:08Z",
        "closed_at": None,
        "labels": [{"name": "action:review-openspec"}],
        "body": f"Change: {change}",
    }
    lifecycle = (
        {
            "id": 30822867782,
            "event": "labeled",
            "created_at": "2026-09-09T11:00:04Z",
            "label": {"name": "action:explore-change"},
        },
        {"id": 5707223672, "event": "commented", "created_at": "2026-09-17T01:52:20Z"},
        {
            "id": 31287353469,
            "event": "unlabeled",
            "created_at": "2026-09-17T01:52:22Z",
            "label": {"name": "action:propose-change"},
        },
        {
            "id": 31287353519,
            "event": "labeled",
            "created_at": "2026-09-17T01:52:22Z",
            "label": {"name": "action:resolve-question"},
        },
        {"id": 5709649340, "event": "commented", "created_at": "2026-09-17T05:56:39Z"},
        {
            "id": 31302117639,
            "event": "unlabeled",
            "created_at": "2026-09-17T07:40:31Z",
            "label": {"name": "action:resolve-question"},
        },
        {
            "id": 31302117669,
            "event": "labeled",
            "created_at": "2026-09-17T07:40:31Z",
            "label": {"name": "action:review-openspec"},
        },
        {"id": 5710947012, "event": "commented", "created_at": "2026-09-17T07:53:07Z"},
    )
    compare_calls: list[str] = []

    def fake_github_json(
        _repo: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == "issues/233":
            return current_issue
        if path.startswith("compare/"):
            compare_calls.append(path)
            failed_revision, _separator, _current = path.removeprefix("compare/").partition("...")
            return {
                "status": "ahead",
                "base_commit": {"sha": failed_revision},
            }
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_github_json", fake_github_json)
    monkeypatch.setattr(
        bridge,
        "_paged_github_list",
        lambda _repo, _token, path: (
            (recovery_comment, old_formal_comment, persisted_formal_comment)
            if "comments" in path
            else lifecycle
        ),
    )
    decisions: list[QualificationDecision] = []
    real_qualifier = bridge.qualify_current_formal_consequence

    def capture_qualification(qualification: QualificationInput) -> QualificationDecision:
        decision = real_qualifier(qualification)
        decisions.append(decision)
        return decision

    monkeypatch.setattr(bridge, "qualify_current_formal_consequence", capture_qualification)
    plan = plan_application(
        event=event,
        request=request,
        preflight=_preflight(
            action="review-openspec",
            issue_number=233,
            change=change,
            current_state_provenance=ObservationProvenance.INDETERMINATE,
        ),
        repository=_REPOSITORY,
        current_revision=current_revision,
    )
    assert plan.should_apply
    assert plan.source == source
    assert plan.pending_continuation
    assert plan.pending_application_correlation == application_correlation
    assert historical_review_revision != review_authorization_revision
    assert any(
        review_authorization_revision in path and current_revision in path for path in compare_calls
    )
    assert decisions
    assert getattr(decisions[-1], "qualified", False)


def test_application_boundary_does_not_replay_dispatch_artifacts() -> None:
    source = Path("src/investment_strategy/scheduled_agent_application_bridge.py").read_text(
        encoding="utf-8"
    )
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")

    assert "fetch_dispatch_result" not in source
    assert "scheduled_agent_dispatch_result" not in source
    assert "Dispatch-Request-Comment-ID" not in source
    assert "Dispatch-Run-ID" not in source
    assert workflow.count("startsWith(github.event.comment.body, 'EFFECT_REQUEST')") == 1
    assert "VALIDATION_RESOURCE_REQUEST" not in workflow
    assert "WORK_PRODUCT_REQUEST" not in workflow
    assert "FORMALIZE_CHANGE_REQUEST" not in workflow
    assert "End invocation at CarrierRequired boundary" in workflow
    assert workflow.count("steps.apply.outputs.carrier_required != 'true'") == 8
    recovery_name = "application-recovery-evidence"
    recovery_path = f"$RUNNER_TEMP/{recovery_name}"
    assert workflow.count(f'--recovery-evidence-path "{recovery_path}"') == 2
    initial_evidence_upload = workflow.index(
        "      - name: Upload exact application recovery evidence"
    )
    carrier_plan_upload = workflow.index("      - name: Persist exact external carrier plan")
    initial_evidence_step = workflow[initial_evidence_upload:carrier_plan_upload]
    assert f"name: {recovery_name}" in initial_evidence_step
    assert "path: ${{ steps.apply.outputs.recovery_evidence_path }}" in initial_evidence_step
    assert "archive: false" in initial_evidence_step
    assert "overwrite: true" in initial_evidence_step

    validation_apply_start = workflow.index(
        "      - name: Persist the derived successor after exact validation"
    )
    final_evidence_upload = workflow.index(
        "      - name: Upload final exact application recovery evidence"
    )
    final_evidence_step = workflow[final_evidence_upload:]
    assert final_evidence_upload > validation_apply_start
    assert "id: post_validation_apply" in workflow[validation_apply_start:final_evidence_upload]
    assert "if: always()" in final_evidence_step
    assert "steps.post_validation_apply.outputs.recovery_evidence_path" in final_evidence_step
    assert f"name: {recovery_name}" in final_evidence_step
    assert "archive: false" in final_evidence_step
    assert "overwrite: true" in final_evidence_step


def test_original_322_recovery_comment_is_bounded_to_the_existing_application_owner() -> None:
    """Transport must not invoke the normal effect path or mint a second Action."""
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")
    marker = "RECOVERY_EXIT_REQUEST 6019133874"
    assert workflow.count("  apply:\n") == 1
    assert workflow.count("startsWith(github.event.comment.body, 'EFFECT_REQUEST')") == 1
    assert workflow.count("github.event.comment.body == '" + marker + "'") == 2
    assert workflow.count("github.event.comment.user.login == 'royhsu-work'") == 2
    assert workflow.count("github.event.issue.number == 322") == 2
    assert "github.event.comment.body != '" + marker + "'" in workflow
    recovery_step = workflow.split(
        "      - name: Bounded original #322 recovery through existing application owner", 1
    )[1].split("      - name: Upload exact application recovery evidence", 1)[0]
    assert "inputs.recovery_exit_request_comment_id != ''" in recovery_step
    assert (
        "(github.event_name == 'pull_request_target' || github.event_name == 'issue_comment')"
        " && '6019133874' || inputs.recovery_exit_request_comment_id"
    ) in recovery_step
    assert '--recovery-exit-request-comment-id "$ORIGINAL_REQUEST"' in recovery_step
    assert 'if [[ "$ORIGINAL_REQUEST" != "6019133874" ]]' in recovery_step


def test_main_exits_at_carrier_boundary_before_formal_continuation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    worker_result = _worker_result(
        action="implement-change",
        role="executor",
        result_kind="spec-blocker",
    )
    worker_result["change"] = "carrier-exit-change"
    body = _effect_request(worker_result, revision=_REVISION)
    event = _event(body)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    output_path = tmp_path / "github-output.txt"
    source = WorkerRequest(138, "executor", "implement-change")
    carrier_plan = make_carrier_plan(
        repository=_REPOSITORY,
        issue_number=138,
        change="carrier-exit-change",
        action="implement-change",
        authorization_revision=_REVISION,
        operation="pull-request-ready",
        target={"pull_request_number": 226},
        expected={"head_sha": _REVISION},
        requested={"head_sha": _REVISION, "draft": False},
        expected_postcondition={"draft": False},
    )
    events: list[str] = []

    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
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
        ],
    )
    monkeypatch.setattr(bridge, "_fresh_event_observation", lambda *_args: None)
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(
            action="implement-change",
            issue_number=138,
            change="carrier-exit-change",
        ),
    )
    monkeypatch.setattr(
        bridge,
        "plan_application",
        lambda **_kwargs: bridge.ApplicationPlan(
            should_apply=True,
            source=source,
            raw_worker_result=json.dumps(worker_result),
            request_comment_id=102,
        ),
    )
    monkeypatch.setattr(bridge, "_machine_result_revision", lambda *_args, **_kwargs: _REVISION)

    def raise_carrier(*_args: object, **_kwargs: object) -> object:
        events.append("application")
        raise CarrierRequired(carrier_plan)

    monkeypatch.setattr(bridge, "run_guarded_effect_application", raise_carrier)
    monkeypatch.setattr(
        bridge,
        "_write_carrier_outputs",
        lambda result: events.append(f"carrier:{result.carrier_plan.plan_id}"),
    )
    monkeypatch.setattr(
        bridge,
        "_write_validation_outputs",
        lambda target: events.append(f"validation:{target}"),
    )

    assert bridge.main() == 0

    assert events == ["application", f"carrier:{carrier_plan.plan_id}", "validation:None"]
    output = capsys.readouterr().out
    assert '"carrier_required": true' in output
    assert '"effects": 0' in output
    assert "ACTION_RESULT" not in output
    assert "SLICE_CHECKPOINT" not in output


def test_application_owns_formal_result_after_other_worker_effects() -> None:
    source = WorkerRequest(138, "lead", "explore-change")
    worker = _worker_result()
    worker["result_content"] = "decision-complete explore"
    worker["requested_effects"] = [
        {
            "kind": "issue-comment",
            "payload_json": json.dumps(
                {"issue_number": 138, "body": "diagnostic note"},
                sort_keys=True,
            ),
        }
    ]
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))

    normalized = bridge._application_owned_worker_result(
        raw,
        source=source,
        current_revision=_REVISION,
    )
    payload = json.loads(normalized)
    effects = payload["requested_effects"]
    assert [effect["kind"] for effect in effects] == ["issue-comment", "issue-comment"]
    assert json.loads(effects[0]["payload_json"])["body"] == "diagnostic note"
    formal = json.loads(effects[1]["payload_json"])["body"]
    assert formal.startswith("ACTION_RESULT\n")
    assert "Result: PROPOSAL_READY" in formal
    assert f"Default-Branch-Revision: {_REVISION}" in formal


def test_rerun_reauthorizes_exact_request_on_descendant_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_revision = "1" * 40
    body = _effect_request(revision=old_revision)
    request = parse_application_request(body)
    assert request is not None
    monkeypatch.setattr(bridge, "_authorization_revision_is_ancestor", lambda *_args: True)

    plan = plan_application(
        event=_event(body),
        request=request,
        preflight=_preflight(),
        repository=_REPOSITORY,
        current_revision=_REVISION,
        token=_CHANGE,
        allow_descendant_resume=True,
    )

    assert plan.should_apply
    assert plan.source == WorkerRequest(138, "lead", "explore-change")
    assert plan.request_comment_id == 102


def test_application_failed_effect_is_not_lost_from_actions_log_contract() -> None:
    """The normal application failure summary must preserve bounded effect identity."""
    import inspect

    main_source = inspect.getsource(bridge._main_unprotected)
    assert '"failure_evidence": _public_failure_diagnostics(result)' in main_source


def test_public_failure_diagnostics_keeps_ordinal_and_redacts_raw_payload() -> None:
    """An artifact upload failure still leaves a nonauthoritative, safe log hint."""
    marker_value = "NEVER_PRINT_A_RAW_SECRET"
    rejection = ApplicationRejection(
        ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED,
        expected=json.dumps(
            {"materialization_proof": ["COMPLETE", "INCOMPLETE"], "accepted_intent": True}
        ),
        observed=json.dumps(
            {
                "disposition": "CONTRADICTORY",
                "reason": "materialization missing work preimage is stale",
            }
        ),
    )
    evidence = EffectRecoveryEvidence(
        failed_effect_index=1,
        failed_effect_kind="github-mutation",
        failed_effect_sha256="b" * 64,
        completed_effect_indexes=(0,),
        completed_effect_sha256=("a" * 64,),
        mutation_status="not-complete",
        unfinished_boundary="effect-precondition",
        rejection=rejection,
    )
    result = bridge.ApplyResult(
        False,
        f"effect precondition rejected {marker_value}",
        rejection=rejection,
        recovery_evidence=evidence,
    )
    logged = bridge._public_failure_diagnostics(result)
    assert logged is not None
    assert logged["failed_effect_index"] == 1
    assert logged["failed_effect_kind"] == "github-mutation"
    assert logged["failed_effect_sha256"] == "b" * 64
    assert logged["completed_effect_indexes"] == [0]
    assert logged["completed_effect_sha256"] == ["a" * 64]
    assert logged["mutation_status"] == "not-complete"
    assert logged["unfinished_boundary"] == "effect-precondition"
    assert logged["rejection_classification"] == "effect-precondition-unsatisfied"
    assert logged["guard_reason"] == "materialization missing work preimage is stale"
    assert logged["failure_evidence_sha256"] == bridge._canonical_sha256(
        bridge._recovery_failure_document(result)
    )
    assert marker_value not in json.dumps(logged)
    assert bridge._public_failure_diagnostics(bridge.ApplyResult(True, "applied")) is None


def test_public_failure_diagnostics_never_exposes_untrusted_guard_reason() -> None:
    """Review regression: effect payloads cannot spoof proof-classified log details."""
    untrusted_value = "NONPUBLIC_PAYLOAD_MARKER"
    rejection = ApplicationRejection(
        ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED,
        expected=json.dumps({"source": {"issue_number": 322}}),
        observed=json.dumps(
            {"disposition": "CONTRADICTORY", "reason": f"materialization {untrusted_value}"}
        ),
    )
    evidence = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind="github-mutation",
        failed_effect_sha256="a" * 64,
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="not-complete",
        unfinished_boundary="effect-precondition",
        rejection=rejection,
    )
    result = bridge.ApplyResult(False, "effect precondition rejected", recovery_evidence=evidence)
    diagnostics = bridge._public_failure_diagnostics(result)

    assert diagnostics is not None
    assert diagnostics["rejection_classification"] == "effect-precondition-unsatisfied"
    assert "guard_reason" not in diagnostics
    assert untrusted_value not in json.dumps(diagnostics)


def test_merge_precondition_failure_is_diagnosable_without_leaking_raw_evidence() -> None:
    rejection = ApplicationRejection(
        ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED,
        json.dumps(
            {"issue": 322, "change": _CHANGE, "pr": 418, "head": _REVISION, "failed_predicates": []}
        ),
        json.dumps(
            {
                "failed_predicates": ["current_carrier", "exact_review"],
                "snapshot": {"raw_private_field": "REDACT_ME"},
            }
        ),
    )
    evidence = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind="github-mutation",
        failed_effect_sha256="a" * 64,
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="not-complete",
        unfinished_boundary="effect-precondition",
        rejection=rejection,
    )
    diagnostic = bridge._public_failure_diagnostics(
        bridge.ApplyResult(False, "effect precondition rejected", recovery_evidence=evidence)
    )
    assert diagnostic is not None
    assert diagnostic["merge_failed_predicates"] == ["current_carrier", "exact_review"]
    assert "REDACT_ME" not in json.dumps(diagnostic)


def test_nonprogressing_merge_rejection_authorizes_recovery_only_continuation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = WorkerRequest(138, "executor", "merge-implementation-pr")
    worker = _worker_result(action=source.action, role=source.role, result_kind="merged")
    worker["change"] = _CHANGE
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    body = _effect_request(worker)
    record = _accepted_record(raw, body, source=source, change=_CHANGE, result_kind="merged")
    monkeypatch.setattr(
        bridge,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (record, "accepted decision"),
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "7001")
    rejection = ApplicationRejection(
        ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED,
        "expected exact head/current gate",
        "observed stale head/current gate",
    )
    evidence = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind="github-mutation",
        failed_effect_sha256="a" * 64,
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="not-complete",
        unfinished_boundary="effect-precondition",
        rejection=rejection,
    )
    output = tmp_path / "merge-rejection.json"
    bridge._write_application_recovery_evidence(
        str(output),
        result=bridge.ApplyResult(
            False, "effect precondition rejected", recovery_evidence=evidence
        ),
        repository=_REPOSITORY,
        token=_REVISION,
        source=source,
        request_comment_id=record.request_comment_id,
        trigger_comment_id=404,
        authorization_revision=_REVISION,
        current_revision=_REVISION,
        run_attempt=1,
        continuation=None,
        predecessor=None,
    )
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["continuation_eligible"] is True
    assert document["failure_evidence"]["mutation_status"] == "not-complete"
    assert document["failure_evidence"]["completed_effect_indexes"] == []


@pytest.mark.parametrize(
    ("mutation_status", "mergeable", "carrier_disposition", "expect_handoff"),
    [
        ("not-complete", False, "RECONCILIATION_REQUIRED", True),
        ("not-complete", None, "INDETERMINATE", False),
        ("not-complete", True, "QUALIFIED", False),
        ("unknown", False, "RECONCILIATION_REQUIRED", False),
    ],
)
def test_accepted_merge_recovery_routes_only_fresh_proven_zero_write_failure(
    monkeypatch: pytest.MonkeyPatch,
    mutation_status: str,
    mergeable: bool | None,
    carrier_disposition: str,
    expect_handoff: bool,
) -> None:
    """Original ACCEPTED MERGED stays immutable; only application recovery routes."""

    source = WorkerRequest(138, "executor", "merge-implementation-pr")
    merge_payload = {
        "operation": "pull-request-merge",
        "issue_number": 138,
        "number": 418,
        "expected_head_sha": _REVISION,
        "merge_method": "squash",
    }
    effect = StagedEffect("github-mutation", json.dumps(merge_payload, sort_keys=True))
    worker = _worker_result(action=source.action, role=source.role, result_kind="merged")
    worker["change"] = _CHANGE
    worker["requested_effects"] = [{"kind": effect.kind, "payload_json": effect.payload_json}]
    parsed = bridge.parse_worker_result(json.dumps(worker), source, authorized_change=_CHANGE)
    batch = EffectBatch(source, (effect,), typed_result=parsed.typed_result)
    record = _accepted_record(
        json.dumps(worker),
        _effect_request(worker),
        source=source,
        change=_CHANGE,
        result_kind="merged",
    )
    rejection = ApplicationRejection(
        ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED,
        "exact carrier integration",
        "current conflict",
    )
    evidence = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind="github-mutation",
        failed_effect_sha256=hashlib.sha256(effect.payload_json.encode()).hexdigest(),
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status=mutation_status,
        unfinished_boundary="effect-precondition",
        rejection=rejection,
    )
    result = bridge.ApplyResult(False, "effect precondition rejected", recovery_evidence=evidence)
    labels = ["human:approved", "action:merge-implementation-pr"]
    issue = {"number": 138, "state": "open", "body": f"Change: {_CHANGE}", "labels": []}
    pr = {
        "number": 418,
        "state": "open",
        "merged": False,
        "mergeable": mergeable,
        "head": {"sha": _REVISION},
        "base": {"ref": "main"},
    }
    reads: list[str] = []
    writes: list[tuple[str, object]] = []
    comments: list[str] = []

    def api(
        _repo: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        **_kwargs: object,
    ) -> object:
        if method != "GET":
            writes.append((path, payload))
            assert path == "issues/138" and method == "PATCH"
            assert payload is not None
            labels[:] = cast(list[str], payload["labels"])
            return issue
        reads.append(path)
        if path == "pulls/418":
            return pr
        if path == "issues/138":
            issue["labels"] = [{"name": label} for label in labels]
            return issue
        raise AssertionError(f"unexpected API path {path}")

    def normalize(_issue: object) -> SimpleNamespace:
        action = next(label[7:] for label in labels if label.startswith("action:"))
        return SimpleNamespace(
            authoritative=True,
            state="open",
            change=_CHANGE,
            routing=("lead" if action == "resolve-question" else "executor", action),
        )

    monkeypatch.setattr(bridge, "_github_json", api)
    monkeypatch.setattr(bridge, "normalize_github_issue", normalize)
    monkeypatch.setattr(bridge, "_fresh_branch_head", lambda *_args: _REVISION)
    monkeypatch.setattr(
        bridge,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (record, "original immutable ACCEPTED MERGED decision"),
    )
    monkeypatch.setattr(
        bridge,
        "qualify_implementation_carrier",
        lambda **_kwargs: SimpleNamespace(
            disposition=carrier_disposition,
            head_sha=_REVISION,
            reason="carrier-confirmed-git-merge-conflict",
        ),
    )
    monkeypatch.setattr(bridge, "acquire_current_github_preflight", lambda *_args: object())
    monkeypatch.setattr(
        bridge,
        "classify_dispatch",
        lambda _preflight: SimpleNamespace(
            disposition="AUTHORIZE",
            selected_issue_id=138,
            selected_routing=normalize(issue).routing,
        ),
    )
    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args: ())

    def persist_recovery(body: str, **_kwargs: object) -> int:
        comments.append(body)
        return 55

    monkeypatch.setattr(bridge, "_persist_recovery_comment", persist_recovery)

    assert (
        bridge._recover_deterministic_accepted_merge_failure(
            result=result,
            batch=batch,
            source=source,
            repository=_REPOSITORY,
            token=_REPOSITORY,
            current_revision=_REVISION,
            default_branch="main",
            request_comment_id=record.request_comment_id,
        )
        is expect_handoff
    )
    assert (labels[-1] == "action:resolve-question") is expect_handoff
    assert bool(writes) is expect_handoff
    assert bool(comments) is expect_handoff
    assert "human:approved" in labels
    assert all(path != "pulls/418/merge" for path, _ in writes)
    if expect_handoff:
        assert "Accepted-Decision-SHA256" in comments[0]
        assert "Failure-Evidence-SHA256" in comments[0]
        assert "Reason: accepted-merge-precondition-rejected" in comments[0]


@pytest.mark.parametrize("run_identity_available", [True, False])
def test_recovery_evidence_is_prepared_before_first_administrative_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, run_identity_available: bool
) -> None:
    """A crash after recovery POST retains the original run's continuation proof."""

    source = WorkerRequest(138, "executor", "merge-implementation-pr")
    effect = StagedEffect(
        "github-mutation",
        json.dumps(
            {
                "operation": "pull-request-merge",
                "issue_number": 138,
                "number": 418,
                "expected_head_sha": _REVISION,
                "merge_method": "squash",
            },
            sort_keys=True,
        ),
    )
    worker = _worker_result(action=source.action, role=source.role, result_kind="merged")
    worker["change"] = _CHANGE
    worker["requested_effects"] = [{"kind": effect.kind, "payload_json": effect.payload_json}]
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    request_body = _effect_request(worker)
    accepted = _accepted_record(
        raw, request_body, source=source, change=_CHANGE, result_kind="merged"
    )
    accepted_body = "qualified original ACCEPTED MERGED"
    rejection = ApplicationRejection(
        ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED,
        "merge current proof",
        "confirmed Git conflict",
    )
    evidence = EffectRecoveryEvidence(
        failed_effect_index=0,
        failed_effect_kind=effect.kind,
        failed_effect_sha256=hashlib.sha256(effect.payload_json.encode()).hexdigest(),
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="not-complete",
        unfinished_boundary="effect-precondition",
        rejection=rejection,
    )
    result = bridge.ApplyResult(False, "effect precondition rejected", recovery_evidence=evidence)
    batch = EffectBatch(source, (effect,), typed_result=None)
    event_path = tmp_path / "effect-event.json"
    event_path.write_text(json.dumps(_event(request_body)), encoding="utf-8")
    evidence_path = tmp_path / "application-recovery-evidence"
    github_output = tmp_path / "github-output"
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")
    assert "if: always() && steps.apply.outputs.recovery_evidence_path != ''" in workflow
    assert "name: application-recovery-evidence" in workflow
    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "test")
    if run_identity_available:
        monkeypatch.setenv("GITHUB_RUN_ID", "8001")
    else:
        monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "application-bridge",
            "--event-path",
            str(event_path),
            "--revision",
            _REVISION,
            "--default-branch",
            "main",
            "--recovery-evidence-path",
            str(evidence_path),
        ],
    )
    monkeypatch.setattr(bridge, "_fresh_event_observation", lambda *_args: False)
    monkeypatch.setattr(bridge, "acquire_current_github_preflight", lambda *_args: object())
    monkeypatch.setattr(
        bridge,
        "plan_application",
        lambda **_kwargs: bridge.ApplicationPlan(
            True, source=source, raw_worker_result=raw, change=_CHANGE, request_comment_id=102
        ),
    )
    monkeypatch.setattr(
        bridge, "_fresh_application_worker_result", lambda original, **_kw: original
    )
    monkeypatch.setattr(
        bridge, "run_guarded_effect_application", lambda *_args, **_kwargs: (batch, result)
    )
    monkeypatch.setattr(
        bridge,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (accepted, accepted_body),
    )

    def interrupted_after_comment(**_kwargs: object) -> bool:
        assert evidence_path.is_file(), "continuation evidence must precede recovery POST"
        checkpoint = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert checkpoint["continuation_eligible"] is True
        assert checkpoint["failure_evidence"]["completed_effect_indexes"] == []
        assert (
            checkpoint["accepted_decision_sha256"]
            == hashlib.sha256(accepted_body.encode()).hexdigest()
        )
        assert f"recovery_evidence_path={evidence_path}" in github_output.read_text(
            encoding="utf-8"
        )
        raise RuntimeError("interrupted after durable APPLICATION_RECOVERY comment")

    monkeypatch.setattr(
        bridge, "_recover_deterministic_accepted_merge_failure", interrupted_after_comment
    )
    if run_identity_available:
        with pytest.raises(RuntimeError, match="interrupted after durable"):
            bridge._main_unprotected(bridge.ApplicationExceptionContext())
    else:
        # An incomplete predecessor identity cannot authorize either the
        # administrative comment or the routing write.
        assert bridge._main_unprotected(bridge.ApplicationExceptionContext()) == 1
        assert not evidence_path.exists()


def test_interrupted_accepted_merge_recovery_completes_without_replaying_merge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = WorkerRequest(138, "executor", "merge-implementation-pr")
    worker = _worker_result(action=source.action, role=source.role, result_kind="merged")
    worker["change"] = _CHANGE
    record = _accepted_record(
        json.dumps(worker),
        _effect_request(worker),
        source=source,
        change=_CHANGE,
        result_kind="merged",
    )
    labels = ["human:approved", "action:merge-implementation-pr"]
    body = "\n".join(
        (
            "APPLICATION_RECOVERY",
            "Workflow: #138",
            f"Change: {_CHANGE}",
            "Source: Executor / merge-implementation-pr",
            "Target: Lead / resolve-question",
            f"Default-Branch-Revision: {_REVISION}",
            f"Failed-Authorization-Revision: {_REVISION}",
            f"Request-Comment-ID: {record.request_comment_id}",
            "Accepted-Decision-SHA256: " + "a" * 64,
            "Failure-Evidence-SHA256: " + "b" * 64,
            "PR-Number: 418",
            f"PR-Head-SHA: {_REVISION}",
            "Reason: accepted-merge-precondition-rejected",
        )
    )
    comment = {
        "id": 55,
        "body": body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    issue = {"state": "open", "number": 138, "body": f"Change: {_CHANGE}", "labels": []}
    writes: list[str] = []

    def api(
        _repo: str,
        _token: str,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
    ) -> object:
        if method == "PATCH":
            assert path == "issues/138"
            assert payload is not None
            labels[:] = cast(list[str], payload["labels"])
            writes.append(path)
            return issue
        if path == "issues/138":
            issue["labels"] = [{"name": label} for label in labels]
            return issue
        if path == "pulls/418":
            return {"state": "open", "merged": False, "head": {"sha": _REVISION}}
        raise AssertionError(f"unexpected GitHub path: {path}")

    def observation(_issue: object) -> SimpleNamespace:
        action = next(label[7:] for label in labels if label.startswith("action:"))
        return SimpleNamespace(
            authoritative=True,
            state="open",
            change=_CHANGE,
            routing=("lead" if action == "resolve-question" else "executor", action),
        )

    recovery_event = SimpleNamespace(
        valid=True,
        reason="accepted-merge-precondition-rejected",
        request_comment_id=record.request_comment_id,
        source=(source.role, source.action),
        change=_CHANGE,
        target=("lead", "resolve-question"),
        pr_number=418,
        pr_head_sha=_REVISION,
    )
    monkeypatch.setattr(bridge, "_github_json", api)
    monkeypatch.setattr(bridge, "normalize_github_issue", observation)
    monkeypatch.setattr(bridge, "_fresh_branch_head", lambda *_args: _REVISION)
    monkeypatch.setattr(bridge, "_paged_github_list", lambda *_args: (comment,))
    monkeypatch.setattr(
        bridge,
        "build_qualification_input",
        lambda **_kwargs: SimpleNamespace(recovery_events=(recovery_event,)),
    )
    monkeypatch.setattr(
        bridge,
        "qualify_current_formal_consequence",
        lambda *_args: SimpleNamespace(
            qualified=True, reason="current-administrative-recovery-route-qualified"
        ),
    )
    monkeypatch.setattr(bridge, "acquire_current_github_preflight", lambda *_args: object())
    monkeypatch.setattr(
        bridge,
        "classify_dispatch",
        lambda *_args: SimpleNamespace(
            disposition="AUTHORIZE",
            selected_issue_id=138,
            selected_routing=observation(issue).routing,
        ),
    )

    # An ordinary external dispatch wake transports the existing
    # APPLICATION_CONTINUATION body as an issue_comment event. GitHub's
    # original GITHUB_TOKEN-authored APPLICATION_RECOVERY comment does not
    # itself launch an application job. Test the admitted event-to-repair
    # entry point, not just a direct call to the private repair helper.
    accepted_body = "original immutable ACCEPTED MERGED decision"
    decision_digest = hashlib.sha256(accepted_body.encode()).hexdigest()
    continuation = bridge.render_application_continuation_request(
        repository=_REPOSITORY,
        issue_number=source.issue_number,
        original_request_comment_id=record.request_comment_id,
        accepted_decision_sha256=decision_digest,
        predecessor_run_id=8001,
        predecessor_run_attempt=1,
        predecessor_job_id=8002,
        predecessor_artifact_id=8003,
        predecessor_artifact_digest="sha256:" + "c" * 64,
        failure_evidence_sha256="b" * 64,
        recovery_episode_sha256="d" * 64,
    )
    event_path = tmp_path / "application-continuation-event.json"
    event_path.write_text(
        json.dumps(
            {
                "action": "created",
                "issue": {"number": 142},
                "comment": {"id": 8004, "body": continuation},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "test")
    monkeypatch.setattr(bridge, "_fresh_event_observation", lambda *_args: False)
    monkeypatch.setattr(
        bridge,
        "_find_application_decision_from_current_frontier",
        lambda **_kwargs: record,
    )
    monkeypatch.setattr(
        bridge,
        "_application_decision_comment_for_request",
        lambda **_kwargs: (record, accepted_body),
    )
    monkeypatch.setattr(
        bridge,
        "qualify_application_continuation_predecessor",
        lambda *_args, **_kwargs: SimpleNamespace(continuation_eligible=True),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "application-bridge",
            "--event-path",
            str(event_path),
            "--revision",
            _REVISION,
            "--default-branch",
            "main",
        ],
    )
    assert "startsWith(github.event.comment.body, 'APPLICATION_CONTINUATION')" in Path(
        ".github/workflows/scheduled-agent-application.yml"
    ).read_text(encoding="utf-8")
    assert bridge.main() == 0
    assert writes == ["issues/138"]

    for _ in range(2):
        assert bridge._resume_pending_accepted_merge_recovery(
            accepted=record,
            repository=_REPOSITORY,
            token=_REPOSITORY,
            current_revision=_REVISION,
            default_branch="main",
        )
    assert writes == ["issues/138"]
    assert labels == ["human:approved", "action:resolve-question"]


def test_checkpoint_can_only_rehydrate_known_zero_write_merge_rejection() -> None:
    failure = {
        "reason": "effect precondition rejected",
        "failed_effect_index": 0,
        "failed_effect_kind": "github-mutation",
        "failed_effect_sha256": "a" * 64,
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
        "mutation_status": "not-complete",
        "unfinished_boundary": "effect-precondition",
        "rejection": {
            "classification": "effect-precondition-unsatisfied",
            "expected": "exact original accepted head",
            "observed": "confirmed conflict",
        },
    }
    predecessor = bridge.ApplicationRecoveryArtifact(
        run_id=1,
        run_attempt=1,
        job_id=2,
        artifact_id=3,
        artifact_digest="sha256:" + "c" * 64,
        request_comment_id=4,
        accepted_decision_sha256="d" * 64,
        failure_evidence_sha256="e" * 64,
        recovery_episode_sha256="f" * 64,
        recovery_attempt=1,
        continuation_eligible=True,
        document={"failure_evidence": failure},
    )
    result = bridge._rejected_merge_result_from_checkpoint(predecessor)
    assert result is not None
    assert result.recovery_evidence is not None
    assert result.recovery_evidence.completed_effect_indexes == ()
    failure["mutation_status"] = "unknown"
    assert bridge._rejected_merge_result_from_checkpoint(predecessor) is None


def test_recovery_artifact_reader_propagates_transient_download_failure() -> None:
    """An observed upload followed by a failed download is unavailable, not absent."""
    run_id, job_id, artifact_id = 7001, 7002, 7003
    run_head = _REVISION
    digest = "sha256:" + "a" * 64

    def read(_repository: str, _token: str, path: str) -> object:
        if path == f"actions/runs/{run_id}":
            return {
                "id": run_id,
                "run_attempt": 1,
                "status": "completed",
                "head_sha": run_head,
                "display_title": "Scheduled Agent Application 90",
            }
        if path == f"actions/runs/{run_id}/attempts/1/jobs":
            return {
                "total_count": 1,
                "jobs": [
                    {
                        "id": job_id,
                        "name": "apply",
                        "run_attempt": 1,
                        "status": "completed",
                        "conclusion": "failure",
                        "steps": [
                            {
                                "name": "Upload exact application recovery evidence",
                                "conclusion": "success",
                            }
                        ],
                    }
                ],
            }
        if path == f"actions/runs/{run_id}/artifacts?per_page=100":
            return {
                "artifacts": [
                    {
                        "id": artifact_id,
                        "name": "application-recovery-evidence",
                        "digest": digest,
                        "expired": False,
                        "workflow_run": {"id": run_id, "head_sha": run_head},
                    }
                ]
            }
        raise AssertionError(f"unexpected read: {path}")

    def failed_download(_repository: str, _token: str, path: str) -> bytes:
        assert path == f"actions/artifacts/{artifact_id}/zip"
        raise OSError("transient artifact read refusal")

    with pytest.raises(OSError, match="transient artifact read refusal"):
        bridge.read_application_recovery_artifact(
            _REPOSITORY,
            "test-token",
            run_id=run_id,
            run_attempt=1,
            job_id=job_id,
            request_comment_id=90,
            accepted_decision_sha256="b" * 64,
            read=read,
            artifact_reader=failed_download,
        )


@pytest.mark.parametrize(
    "alteration",
    [
        "valid",
        "post-validation-valid",
        "post-validation-earlier-recovery",
        "post-validation-earlier-recovery-unqualified",
        "post-validation-final-recovery-conflict",
        "post-validation-conflicting-writers",
        "bad-digest",
        "duplicate",
        "write-after-failure",
        "missing-upload",
        "wrong-source",
        "wrong-run",
        "recovery-present",
        "truncated-inventory",
        "duplicate-job",
        "wrong-run-head",
        "truncated-jobs",
        "missing-job-total",
        "cross-page-duplicate-apply",
        "cross-page-unreadable",
    ],
)
def test_execution_exception_is_a_distinct_verified_predecessor(
    alteration: str,
) -> None:
    """An exception artifact is never silently recast as a recovery checkpoint."""

    source = WorkerRequest(435, "lead", "propose-change")
    record = _accepted_record(
        "{}",
        "EFFECT_REQUEST",
        source=source,
        change="unset",
        result_kind="proposal-ready",
        request_comment_id=6760870154,
    )
    run_id, job_id, artifact_id, trigger = 42827477053, 129868554969, 13768983651, 6768960211
    revision = "2b57c5d4af488bdd583a66c1f72d65713a594928"
    document = {
        "schema": "scheduled-agent-execution-exception/v1",
        "repository": _REPOSITORY,
        "issue_number": 435,
        "role": "lead",
        "action": "propose-change",
        "change": "unset",
        "revision": revision,
        "request_comment_id": record.request_comment_id,
        "trigger_comment_id": trigger,
        "run_id": run_id,
        "run_attempt": 1,
        "attempted_operation": "application-effect-preparation",
        "exception_type": "RuntimeError",
        "raw_error": "post-effect result recovery has no exact activation effect",
        "raw_traceback": "actual diagnostic, not an effect outcome",
        "mutation_status": "UNKNOWN_REQUIRES_FRESH_RECONCILIATION",
        "unfinished_boundary": "application-effect-preparation",
        "classification": "UNCLASSIFIED_EXECUTION_EXCEPTION",
    }
    if alteration == "wrong-source":
        document["issue_number"] = 436
    if alteration == "wrong-run":
        document["run_id"] = run_id + 1
    raw = json.dumps(document).encode()
    digest = f"sha256:{hashlib.sha256(raw).hexdigest()}"
    artifact = {
        "id": artifact_id,
        "name": "application-execution-exception.json",
        "expired": False,
        "digest": digest if alteration != "bad-digest" else "sha256:" + "f" * 64,
        "workflow_run": {"id": run_id, "head_sha": revision},
    }
    artifacts = [artifact]
    if alteration == "duplicate":
        artifacts.append(dict(artifact, id=artifact_id + 1))
    if alteration == "recovery-present":
        artifacts.append({"name": "application-recovery-evidence"})
    if alteration in {
        "post-validation-earlier-recovery",
        "post-validation-earlier-recovery-unqualified",
        "post-validation-final-recovery-conflict",
    }:
        artifacts.append(
            {
                "id": artifact_id + 1,
                "name": "application-recovery-evidence",
                "expired": alteration == "post-validation-earlier-recovery-unqualified",
                "digest": "sha256:" + "b" * 64,
                "workflow_run": {"id": run_id, "head_sha": revision},
            }
        )
    steps = [
        {"name": "Freshly authorize and apply repository-owned effects", "conclusion": "failure"},
        {"name": "Upload exact application recovery evidence", "conclusion": "skipped"},
        {
            "name": "Upload pre-ACCEPT or interrupted application exception evidence",
            "conclusion": "success",
        },
        {"name": "Persist exact external carrier plan", "conclusion": "skipped"},
        {"name": "Upload exact external carrier plan", "conclusion": "skipped"},
        {"name": "Persist the derived successor after exact validation", "conclusion": "skipped"},
        {"name": "Upload final exact application recovery evidence", "conclusion": "skipped"},
    ]
    if alteration.startswith("post-validation-"):
        steps[0]["conclusion"] = "success"
        steps[2]["conclusion"] = "skipped"
        steps[5]["conclusion"] = "failure"
        steps.append(
            {
                "name": "Upload post-validation application exception evidence",
                "conclusion": "success",
            }
        )
        if alteration in {
            "post-validation-earlier-recovery",
            "post-validation-earlier-recovery-unqualified",
            "post-validation-final-recovery-conflict",
        }:
            steps[1]["conclusion"] = "success"
        if alteration == "post-validation-final-recovery-conflict":
            steps[6]["conclusion"] = "success"
        if alteration == "post-validation-conflicting-writers":
            steps[2]["conclusion"] = "success"
    if alteration == "write-after-failure":
        steps[-2]["conclusion"] = "success"
    if alteration == "missing-upload":
        steps[2]["conclusion"] = "skipped"

    def read(_repo: str, _token: str, path: str) -> object:
        if path == f"actions/runs/{run_id}":
            return {
                "id": run_id,
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "failure",
                "head_sha": "f" * 40 if alteration == "wrong-run-head" else revision,
                "display_title": f"Scheduled Agent Application {trigger}",
            }
        if path in {
            f"actions/runs/{run_id}/attempts/1/jobs",
            f"actions/runs/{run_id}/attempts/1/jobs?per_page=100&page=1",
        }:
            jobs = [
                {
                    "id": job_id,
                    "name": "apply",
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "failure",
                    "steps": steps,
                }
            ]
            if alteration == "valid":
                # GitHub's documented job response does not promise run_attempt.
                # The attempt-specific URL, not this optional field, owns identity.
                jobs[0].pop("run_attempt")
            if alteration == "duplicate-job":
                jobs.append(dict(jobs[0], id=job_id + 1))
            if alteration.startswith("cross-page-"):
                jobs.extend(
                    {"id": job_id + index, "name": "idle-admission", "run_attempt": 1}
                    for index in range(1, 100)
                )
            inventory: dict[str, object] = {
                "total_count": len(jobs)
                + (
                    1
                    if alteration
                    in {"truncated-jobs", "cross-page-duplicate-apply", "cross-page-unreadable"}
                    else 0
                ),
                "jobs": jobs,
            }
            if alteration == "missing-job-total":
                del inventory["total_count"]
            return inventory
        if path == f"actions/runs/{run_id}/attempts/1/jobs?per_page=100&page=2":
            if alteration == "cross-page-duplicate-apply":
                return {
                    "total_count": 101,
                    "jobs": [{"id": job_id + 100, "name": "apply", "run_attempt": 1}],
                }
            raise OSError("unavailable second job page")
        if path == f"actions/runs/{run_id}/artifacts?per_page=100":
            return {
                "total_count": len(artifacts) + (1 if alteration == "truncated-inventory" else 0),
                "artifacts": artifacts,
            }
        raise AssertionError(path)

    evidence = bridge.read_application_exception_artifact(
        _REPOSITORY,
        "token",
        run_id=run_id,
        run_attempt=1,
        job_id=job_id,
        record=record,
        accepted_decision_sha256="a" * 64,
        read=read,
        artifact_reader=lambda *_: raw,
    )
    if alteration in {"valid", "post-validation-valid", "post-validation-earlier-recovery"}:
        assert evidence is not None
        assert type(evidence) is bridge.ApplicationExceptionArtifact
        assert evidence.artifact_id == artifact_id
        assert evidence.failure_evidence_sha256 == bridge._canonical_sha256(document)
    else:
        assert evidence is None


def test_native_application_artifact_stage_preserves_phase_order() -> None:
    def steps(*completed: str) -> tuple[tuple[str, str], ...]:
        return tuple((name, "success") for name in completed)

    early = "Upload exact application recovery evidence"
    final = "Upload final exact application recovery evidence"
    pre = "Upload pre-ACCEPT or interrupted application exception evidence"
    post = "Upload post-validation application exception evidence"
    assert bridge.application_artifact_stage(steps(early, post)) == "POST_EXCEPTION"
    assert bridge.application_artifact_stage(steps(early, final)) == "FINAL_RECOVERY"
    assert bridge.application_artifact_stage(steps(pre)) == "PRE_EXCEPTION"
    assert bridge.application_artifact_stage(steps(pre, early)) == "INVALID"
    assert bridge.application_artifact_stage(steps(pre, post)) == "INVALID"
    assert bridge.application_artifact_stage(steps(post, final)) == "INVALID"
    assert bridge.application_artifact_stage(steps(early, early)) == "INVALID"


@pytest.mark.parametrize(
    ("outcome", "duplicate", "admitted"),
    [
        ("COMPLETE", False, True),
        ("INDETERMINATE", False, False),
        ("UNSAFE", False, False),
        ("COMPLETE", True, False),
    ],
)
def test_application_exception_continuation_requalifies_at_native_ingress(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
    duplicate: bool,
    admitted: bool,
) -> None:
    source = WorkerRequest(435, "lead", "propose-change")
    record = _accepted_record(
        "{}",
        "EFFECT_REQUEST",
        source=source,
        change="unset",
        result_kind="proposal-ready",
        request_comment_id=6760870154,
    )
    accepted_body = "immutable accepted decision"
    decision_hash = hashlib.sha256(accepted_body.encode()).hexdigest()
    evidence = bridge.ApplicationExceptionArtifact(
        42827477053,
        1,
        129868554969,
        13768983651,
        "sha256:" + "a" * 64,
        record.request_comment_id,
        decision_hash,
        "b" * 64,
        "c" * 64,
        {"schema": "scheduled-agent-execution-exception/v1"},
    )
    body = bridge.render_application_continuation_request(
        repository=_REPOSITORY,
        issue_number=435,
        original_request_comment_id=record.request_comment_id,
        accepted_decision_sha256=decision_hash,
        predecessor_run_id=evidence.run_id,
        predecessor_run_attempt=evidence.run_attempt,
        predecessor_job_id=evidence.job_id,
        predecessor_artifact_id=evidence.artifact_id,
        predecessor_artifact_digest=evidence.artifact_digest,
        failure_evidence_sha256=evidence.failure_evidence_sha256,
        recovery_episode_sha256=evidence.recovery_episode_sha256,
    )
    continuation = bridge.parse_application_continuation_request(body)
    assert continuation is not None
    decision_comment = {
        "id": 100,
        "body": accepted_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    transport_comment = {
        "id": 200,
        "body": body,
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }

    def comments(_repo: str, _token: str, path: str) -> list[dict[str, object]]:
        if path.startswith("issues/435/comments?"):
            return [decision_comment]
        if path.startswith("issues/440/comments?"):
            return (
                [transport_comment, dict(transport_comment, id=201)]
                if duplicate
                else [transport_comment]
            )
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_paged_github_list", comments)
    monkeypatch.setattr(
        bridge,
        "parse_application_decision",
        lambda raw: record if raw == accepted_body else None,
    )
    monkeypatch.setattr(bridge, "read_application_recovery_artifact", lambda *_a, **_k: None)
    monkeypatch.setattr(bridge, "read_application_exception_artifact", lambda *_a, **_k: evidence)
    monkeypatch.setattr(
        bridge,
        "classify_application_exception_recovery",
        lambda **_k: bridge.AcceptedPostEffectProof(
            cast(
                Literal["COMPLETE", "INDETERMINATE", "UNSAFE"],
                outcome,
            ),
            "fresh observation",
        ),
    )
    actual = bridge.qualify_application_continuation_predecessor(
        _REPOSITORY,
        "token",
        continuation,
        current_comment_id=200,
        transport_issue_number=440,
    )
    assert (actual is evidence) is admitted


@pytest.mark.parametrize(
    "upload_stage",
    [
        "Upload exact application recovery evidence",
        "Upload final exact application recovery evidence",
    ],
)
@pytest.mark.parametrize(
    ("run_attempt", "comparison_status", "comparison_base", "expected_qualified"),
    [
        (3, "ahead", "4" * 40, True),
        (1, "ahead", "4" * 40, False),
        (3, "diverged", "4" * 40, False),
        (3, "ahead", "9" * 40, False),
        (3, None, "4" * 40, False),
    ],
)
def test_recovery_reader_binds_rerun_checkout_to_immutable_original_run_head(
    upload_stage: str,
    run_attempt: int,
    comparison_status: str | None,
    comparison_base: str,
    expected_qualified: bool,
) -> None:
    """An old run rerun from fresh main keeps its original GitHub head_sha.

    Its exact current checkout is independently attested by Application's
    uploaded artifact. Require a strict descendant of the immutable initial
    head for attempt >1; a divergent or unverified revision stays unavailable.
    """
    run_id, job_id, artifact_id, request_comment_id = 7001, 7002, 7003, 91
    original_head, checkout = "4" * 40, "5" * 40
    accepted_sha = "a" * 64
    failure = {
        "reason": "carrier_required",
        "mutation_status": "not-complete",
        "unfinished_boundary": "carrier-required",
        "carrier_plan_id": "qualified-plan",
        "completed_effect_indexes": [],
        "completed_effect_sha256": [],
    }
    document = {
        "schema": "scheduled-agent-application-recovery/v1",
        "repository": _REPOSITORY,
        "issue_number": 322,
        "role": "executor",
        "action": "implement-change",
        "request_comment_id": request_comment_id,
        "accepted_decision_sha256": accepted_sha,
        "trigger_comment_id": request_comment_id,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "current_revision": checkout,
        "authorization_revision": original_head,
        "recovery_attempt": 1,
        "recovery_episode_sha256": "b" * 64,
        "prior_failure_evidence_sha256": [],
        "predecessor": None,
        "failure_evidence": failure,
        "failure_evidence_sha256": bridge._canonical_sha256(failure),
        "continuation_eligible": True,
    }
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = f"sha256:{hashlib.sha256(raw).hexdigest()}"
    seen: list[str] = []

    def read(_repository: str, _token: str, path: str) -> object:
        seen.append(path)
        if path == f"actions/runs/{run_id}":
            return {
                "id": run_id,
                "run_attempt": run_attempt,
                "status": "completed",
                "head_sha": original_head,
                "display_title": f"Scheduled Agent Application {request_comment_id}",
            }
        if path == f"actions/runs/{run_id}/attempts/{run_attempt}/jobs":
            return {
                "total_count": 1,
                "jobs": [
                    {
                        "id": job_id,
                        "name": "apply",
                        "run_attempt": run_attempt,
                        "status": "completed",
                        "conclusion": "success",
                        "steps": [
                            {
                                "name": upload_stage,
                                "conclusion": "success",
                            }
                        ],
                    }
                ],
            }
        if path == f"actions/runs/{run_id}/artifacts?per_page=100":
            return {
                "artifacts": [
                    {
                        "id": artifact_id,
                        "name": "application-recovery-evidence",
                        "digest": digest,
                        "expired": False,
                        "workflow_run": {"id": run_id, "head_sha": original_head},
                    }
                ]
            }
        if path == f"compare/{original_head}...{checkout}":
            if comparison_status is None:
                raise OSError("comparison unavailable")
            return {
                "status": comparison_status,
                "base_commit": {"sha": comparison_base},
                "merge_base_commit": {"sha": comparison_base},
                "ahead_by": 2,
                "behind_by": 0 if comparison_status == "ahead" else 2,
            }
        raise AssertionError(f"unexpected read: {path}")

    try:
        observed = bridge.read_application_recovery_artifact(
            _REPOSITORY,
            "test-token",
            run_id=run_id,
            run_attempt=run_attempt,
            job_id=job_id,
            request_comment_id=request_comment_id,
            accepted_decision_sha256=accepted_sha,
            read=read,
            artifact_reader=lambda *_args: raw,
        )
    except OSError:
        if comparison_status is not None:
            raise
        observed = None
    assert (observed is not None) is expected_qualified
    if expected_qualified:
        assert observed is not None
        assert observed.document["current_revision"] == checkout
        assert f"compare/{original_head}...{checkout}" in seen
    if run_attempt == 1:
        assert f"compare/{original_head}...{checkout}" not in seen


@pytest.mark.parametrize("has_upload_step", [False, True])
def test_strict_recovery_reader_distinguishes_legacy_absence_from_missing_uploaded_artifact(
    has_upload_step: bool,
) -> None:
    """No upload is historical absence; a successful upload with missing listing is unknown."""
    run_id, job_id = 8101, 8102
    seen: list[str] = []

    def read(_repository: str, _token: str, path: str) -> object:
        seen.append(path)
        if path == f"actions/runs/{run_id}":
            return {
                "id": run_id,
                "run_attempt": 1,
                "status": "completed",
                "head_sha": _REVISION,
            }
        if path == f"actions/runs/{run_id}/attempts/1/jobs":
            steps = (
                [{"name": "Upload exact application recovery evidence", "conclusion": "success"}]
                if has_upload_step
                else [{"name": "Complete job", "conclusion": "success"}]
            )
            return {
                "total_count": 1,
                "jobs": [
                    {
                        "id": job_id,
                        "name": "apply",
                        "run_attempt": 1,
                        "status": "completed",
                        "conclusion": "failure",
                        "steps": steps,
                    }
                ],
            }
        if path == f"actions/runs/{run_id}/artifacts?per_page=100":
            return {"artifacts": []}
        raise AssertionError(f"unexpected read: {path}")

    def qualify() -> object:
        return bridge.read_application_recovery_artifact(
            _REPOSITORY,
            "test-token",
            run_id=run_id,
            run_attempt=1,
            job_id=job_id,
            request_comment_id=90,
            accepted_decision_sha256="b" * 64,
            read=read,
            strict_read=True,
        )

    if has_upload_step:
        with pytest.raises(RuntimeError, match="application recovery evidence unavailable"):
            qualify()
        assert f"actions/runs/{run_id}/artifacts?per_page=100" in seen
    else:
        assert qualify() is None
        assert f"actions/runs/{run_id}/artifacts?per_page=100" not in seen


def test_cli_checkpoint_revision_is_bound_to_fresh_proven_target_not_unverified_argument() -> None:
    """CLI echo is evidence transport, never the materialized checkpoint authority."""
    import inspect

    main_source = inspect.getsource(bridge._main_unprotected)
    assert "validated_materialization_revision=args.validated_revision" not in main_source
    assert (
        main_source.count(
            "validated_materialization_revision=(None if target is None else target.revision)"
        )
        == 1
    )
    assert (
        "None if target is None or checkpoint_already_durable else target.revision" in main_source
    )


def test_accepted_checkpoint_and_formal_projection_rebind_only_after_proven_target() -> None:
    checkpoint = "\n".join(
        (
            "SLICE_CHECKPOINT",
            "Workflow: #322",
            f"Change: {_CHANGE}",
            "Action: implement-change",
            "Role: executor",
            "Completed-Tasks: 5.1",
            f"Revision: {_REVISION}",
            "Application-Correlation: accepted-original",
            "Gate-Evidence: all gates passed",
            "Remaining-Approved-Boundary: review-implementation",
        )
    )
    formal = "\n".join(
        (
            "ACTION_RESULT",
            "Workflow: #322",
            f"Change: {_CHANGE}",
            "Action: implement-change",
            "Role: executor",
            "Result: READY",
            f"Revision: {_REVISION}",
            "Default-Branch-Revision: " + _REVISION,
            "Application-Correlation: accepted-original",
        )
    )
    result = _worker_result(action="implement-change", role="executor", result_kind="ready")
    result["change"] = _CHANGE
    result["requested_effects"] = [
        {"kind": "issue-comment", "payload_json": json.dumps({"body": body, "issue_number": 322})}
        for body in (checkpoint, formal)
    ]
    rebound = json.loads(bridge._rebind_application_result_revision(json.dumps(result), "b" * 40))
    rebound_bodies = [
        json.loads(effect["payload_json"])["body"] for effect in rebound["requested_effects"]
    ]
    assert f"Revision: {'b' * 40}" in rebound_bodies[0].splitlines()
    assert f"Revision: {'b' * 40}" in rebound_bodies[1].splitlines()
    assert "Completed-Tasks: 5.1" in rebound_bodies[0]
    assert "Gate-Evidence: all gates passed" in rebound_bodies[0]
    assert rebound["result_content"] == rebound_bodies[1]


@pytest.mark.parametrize("materialized", [False, True])
def test_accepted_implementation_stages_checkpoint_only_after_fresh_carrier_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    materialized: bool,
) -> None:
    """Phase B first creates its carrier, then binds a checkpoint on a fresh wake."""
    source = WorkerRequest(138, "executor", "implement-change")
    revision = "b" * 40
    materialization = {
        "issue_number": 138,
        "operation": "application-materialize",
        "expected_change": _CHANGE,
        "change": _CHANGE,
        "branch": f"agent/{_CHANGE}",
        "base_sha": _REVISION,
        "message": "Accepted implementation slice",
        "pr_number": 178,
        "files": [
            {
                "path": f"openspec/changes/{_CHANGE}/tasks.md",
                "blob_sha": "c" * 40,
                "expected_sha": "a" * 40,
            }
        ],
    }
    checkpoint = "\n".join(
        (
            "SLICE_CHECKPOINT",
            "Workflow: #138",
            f"Change: {_CHANGE}",
            "Action: implement-change",
            "Role: executor",
            "Completed-Tasks: 5.1",
            f"Revision: {_REVISION}",
            "Application-Correlation: original",
            "Gate-Evidence: verified gates",
            "Remaining-Approved-Boundary: implementation review",
        )
    )
    formal = "\n".join(
        (
            "ACTION_RESULT",
            "Workflow: #138",
            f"Change: {_CHANGE}",
            "Action: implement-change",
            "Role: executor",
            "Result: READY",
            f"Revision: {_REVISION}",
            f"Default-Branch-Revision: {_REVISION}",
            "Application-Correlation: original",
        )
    )
    worker = _worker_result(action=source.action, role=source.role, result_kind="ready")
    worker["change"] = _CHANGE
    worker["_semantic_intent_version"] = 2
    worker["requested_effects"] = [
        {"kind": "github-mutation", "payload_json": json.dumps(materialization)},
        {
            "kind": "issue-comment",
            "payload_json": json.dumps({"issue_number": 138, "body": checkpoint}),
        },
        {
            "kind": "issue-comment",
            "payload_json": json.dumps({"issue_number": 138, "body": formal}),
        },
    ]
    raw = json.dumps(worker, sort_keys=True, separators=(",", ":"))
    body = _effect_request(worker)
    accepted = _accepted_record(raw, body, source=source, change=_CHANGE, result_kind="ready")
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(_event(body)), encoding="utf-8")
    monkeypatch.setenv("GITHUB_REPOSITORY", _REPOSITORY)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
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
            "--run-attempt",
            "2",
        ],
    )
    monkeypatch.setattr(bridge, "_application_decision_for_request", lambda **_kw: accepted)
    monkeypatch.setattr(bridge, "_accepted_worker_result_for_continuation", lambda **_kw: raw)
    monkeypatch.setattr(
        bridge, "_fresh_event_observation", lambda *_args: pytest.fail("replayed transport")
    )
    monkeypatch.setattr(
        bridge,
        "acquire_current_github_preflight",
        lambda *_args: _preflight(action=source.action, issue_number=138, change=_CHANGE),
    )
    monkeypatch.setattr(bridge, "_fresh_application_worker_result", lambda *_args, **_kw: raw)
    monkeypatch.setattr(bridge, "_write_application_recovery_evidence", lambda *_args, **_kw: None)
    target = ValidationResourceTarget(
        repository=_REPOSITORY,
        revision=revision,
        correlation="effect-request-138",
        pr_number=178,
        change=_CHANGE,
        validation_required=False,
    )
    monkeypatch.setattr(
        bridge,
        "prove_materialization",
        lambda *_args, **_kw: type(
            "Proof",
            (),
            {
                "disposition": "COMPLETE" if materialized else "INCOMPLETE",
                "target": target if materialized else None,
                "reason": None,
            },
        )(),
    )
    monkeypatch.setattr(bridge, "_accepted_checkpoint_already_durable", lambda *_a, **_k: False)
    # This scenario is explicitly precommit; no authoritative formal result exists.
    monkeypatch.setattr(bridge, "_qualified_committed_implementation_result", lambda **_kw: None)
    calls: list[dict[str, object]] = []

    def fake_apply(raw_result: str, **kwargs: object) -> tuple[EffectBatch, bridge.ApplyResult]:
        calls.append({"raw": json.loads(raw_result), **kwargs})
        return EffectBatch(source=source, effects=()), bridge.ApplyResult(False, "controlled-stop")

    monkeypatch.setattr(bridge, "run_guarded_effect_application", fake_apply)
    assert bridge.main() == 1
    assert len(calls) == 1
    call = calls[0]
    assert call["accepted_intent"] is True
    assert call["apply_derived"] is materialized
    assert call["defer_issue_comments"] is (not materialized)
    assert call["validated_materialization_revision"] == (revision if materialized else None)
    projected = cast(dict[str, object], call["raw"])
    projected_effects = cast(list[dict[str, str]], projected["requested_effects"])
    bodies = [
        json.loads(effect["payload_json"])["body"]
        for effect in projected_effects
        if effect["kind"] == "issue-comment"
    ]
    assert (f"Revision: {revision}" in bodies[0].splitlines()) is materialized


def test_application_apply_job_uses_bounded_pending_queue() -> None:
    """Application serialization must not replace normal queued effect requests."""
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")
    assert workflow.count("  apply:\n") == 1
    apply_header = workflow.split("  apply:\n", 1)[1].split("    permissions:", 1)[0]
    assert "    concurrency:" in apply_header
    assert "group: scheduled-agent-effect-apply-${{ github.repository }}" in apply_header
    assert "cancel-in-progress: false" in apply_header
    assert "queue: max" in apply_header


def test_original_322_recovery_pr_merge_wake_is_exact_and_not_a_generic_effect_request() -> None:
    """One merged maintenance PR may wake the existing application owner, not generic effects."""
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")
    assert "  pull_request_target:\n    types: [closed]\n" in workflow
    assert workflow.count("  apply:\n") == 1
    assert workflow.count("github.event_name == 'pull_request_target'") == 4
    assert workflow.count("github.event.pull_request.merged == true") == 3
    assert workflow.count("github.event.pull_request.base.ref == 'main'") == 2
    assert workflow.count("github.event.pull_request.number == 388") == 3
    assert "steps.reviewed_merge.outputs.head == github.event.pull_request.head.sha" in workflow
    assert (
        workflow.count(
            "github.event.pull_request.head.repo.full_name == 'royhsu-work/investment-strategy'"
        )
        == 2
    )
    assert (
        workflow.count(
            "github.event.pull_request.head.ref == 'agent/issue322-pr-merge-recovery-trigger'"
        )
        == 2
    )
    normal_effect = workflow.split(
        "      - name: Freshly authorize and apply repository-owned effects", 1
    )[1].split(
        "      - name: Bounded original #322 recovery through existing application owner", 1
    )[0]
    assert "github.event_name == 'issue_comment'" in normal_effect
    assert "pull_request_target" not in normal_effect
    bounded = workflow.split(
        "      - name: Bounded original #322 recovery through existing application owner", 1
    )[1].split("      - name: Upload exact application recovery evidence", 1)[0]
    assert "github.event.pull_request.merged == true" in bounded
    assert '--recovery-exit-request-comment-id "$ORIGINAL_REQUEST"' in bounded
    assert 'if [[ "$ORIGINAL_REQUEST" != "6019133874" ]]' in bounded


@pytest.mark.parametrize(
    ("review_matches_head", "latest_is_pass"),
    [(True, True), (False, True), (True, False)],
)
def test_original_322_pr_merge_review_gate_rejects_unreviewed_or_findings_head(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    review_matches_head: bool,
    latest_is_pass: bool,
) -> None:
    """The actual GitHub-event gate checks a fresh review's immutable commit_id."""
    import io
    import textwrap

    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")
    section = workflow.split("      - name: Qualify #388 merged event", 1)[1].split(
        "      - name: Freshly authorize and apply repository-owned effects", 1
    )[0]
    script = textwrap.dedent(
        section.split("          python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
    )
    head = "e" * 40
    reviewed = head if review_matches_head else "f" * 40
    body = (
        "Independent technical review: PASS (scoped transport change)\n"
        if latest_is_pass
        else "Independent technical review — FINDINGS (P1)\n"
    ) + f"Revision: {reviewed}\n"
    pr = {
        "state": "closed",
        "merged": True,
        "base": {"ref": "main"},
        "head": {
            "sha": head,
            "repo": {"full_name": _REPOSITORY},
            "ref": "agent/issue322-pr-merge-recovery-trigger",
        },
    }
    reviews = [
        {
            "id": 10,
            "submitted_at": "2026-10-28T15:00:00Z",
            "state": "COMMENTED",
            "commit_id": reviewed,
            "user": {"login": "royhsu-work"},
            "body": body,
        }
    ]

    def stub_urlopen(request: Request, timeout: int = 20) -> io.BytesIO:
        payload: object
        if request.full_url.endswith("/pulls/388"):
            payload = pr
        elif "/pulls/388/reviews?" in request.full_url:
            payload = reviews
        else:
            raise AssertionError("unexpected GitHub read")
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", stub_urlopen)
    monkeypatch.setenv("EXPECTED_HEAD", head)
    monkeypatch.setenv("GITHUB_TOKEN", "test-only-token")
    output = tmp_path / "reviewed-head"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    if review_matches_head and latest_is_pass:
        exec(compile(script, "<recovery-review-gate>", "exec"), {})  # noqa: S102 - trusted checked-in workflow source
        assert output.read_text(encoding="utf-8") == f"head={head}\n"
    else:
        with pytest.raises(SystemExit, match="review"):
            exec(compile(script, "<recovery-review-gate>", "exec"), {})  # noqa: S102 - trusted checked-in workflow source
        assert not output.exists()


@pytest.mark.parametrize(
    ("zero_proven", "expected"),
    [(False, "INDETERMINATE"), (True, "COMPLETE")],
)
def test_s2b_read_only_zero_original_requires_physical_source_witness(
    monkeypatch: pytest.MonkeyPatch, zero_proven: bool, expected: str
) -> None:
    """R0/R2: an empty accepted semantic projection is not physical zero."""
    source = WorkerRequest(435, "executor", "implement-change")
    raw = '{"source":"accepted-empty-original"}'
    record = _accepted_record(
        raw,
        "EFFECT_REQUEST",
        source=source,
        change="restore-t1-dispatch-artifact-consumption",
        result_kind="blocked",
        request_comment_id=6796616018,
    )
    # Build the exact correlated Formal identity; this test isolates
    # the physical-zero original witness rather than invalid Formal metadata.
    formal_body = "\n".join(
        (
            bridge._expected_formal_marker(source),
            "Workflow: #435",
            "Change: restore-t1-dispatch-artifact-consumption",
            "Action: implement-change",
            "Role: executor",
            "Result: BLOCKED",
            f"Default-Branch-Revision: {_REVISION}",
            "Application-Correlation: "
            + bridge.formal_application_correlation(
                source,
                change="restore-t1-dispatch-artifact-consumption",
                result_kind="blocked",
                current_revision=_REVISION,
                request_comment_id=6796616018,
            ),
        )
    )
    formal = StagedEffect("issue-comment", json.dumps({"issue_number": 435, "body": formal_body}))
    checkpoint: dict[str, object] = {
        "attempted_effects": [
            {"kind": formal.kind, "payload_json": formal.payload_json, "derived": False}
        ],
        "attempt_revision": _REVISION,
        "failed_effect_index": 0,
        "write_call_entered": True,
    }
    artifact = SimpleNamespace(document={"failure_evidence": checkpoint})
    monkeypatch.setattr(bridge, "_accepted_recovery_boundary", lambda _e: "READ_ONLY")
    monkeypatch.setattr(
        bridge, "_verified_attempted_effect_checkpoint", lambda *_a, **_k: (formal,)
    )
    monkeypatch.setattr(
        bridge,
        "parse_effect_batch",
        lambda *_a, **_k: SimpleNamespace(
            typed_result=SimpleNamespace(
                result=SimpleNamespace(kind=SimpleNamespace(value="blocked"))
            ),
            effects=(),
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_read_accepted_never_called_evidence",
        lambda **_k: bridge.CompleteNeverCalledWitness(6796616018, 1, "a" * 64, ((7001, 1, 7003),)),
    )
    zero_reads: list[int] = []

    def verify_physical_zero(**_k: object) -> bool:
        zero_reads.append(record.request_comment_id)
        return zero_proven

    monkeypatch.setattr(bridge, "_verified_zero_original_accepted_effects", verify_physical_zero)

    class Observer:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        def observe_postcondition(self, _effect: StagedEffect) -> bool:
            return True

    monkeypatch.setattr(bridge, "GitHubEffectAdapter", Observer)
    proof = bridge.classify_accepted_read_only_effects(
        record=record,
        source=source,
        recovery_evidence=checkpoint,
        repository=_REPOSITORY,
        token=_REVISION,
        current_revision=_REVISION,
        default_branch="main",
        recovery_artifact=artifact,  # type: ignore[arg-type]
    )
    assert proof.disposition == expected
    assert zero_reads == [record.request_comment_id]
