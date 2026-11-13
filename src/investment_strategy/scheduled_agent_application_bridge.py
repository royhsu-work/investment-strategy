"""Fresh repository-authorized ingress for Scheduled Agent effect application."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import sys
import time
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Literal, cast
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_action_model import (
    Action as ModelAction,
)
from investment_strategy.scheduled_agent_action_model import (
    ApplicationRejection,
    ApplicationRejectionKind,
    ResultKind,
    TypedResult,
    next_action,
    role_for,
)
from investment_strategy.scheduled_agent_application_carrier import (
    _historical_carriers,
    canonical_implementation_branch,
    current_reviewed_implementation_head,
    qualify_implementation_carrier,
    qualify_supersession_branch,
)
from investment_strategy.scheduled_agent_application_materialization import (
    find_materialization_payload,
    materialization_requires_validation,
    observe_materialization_target,
    prove_materialization,
)
from investment_strategy.scheduled_agent_carrier import (
    CarrierPlan,
    CarrierRequired,
    carrier_plan_document,
    github_comment_has_app_provenance,
    github_complete_run_jobs,
    github_paginated_mappings,
    github_read_bytes_with_retry,
    github_repository_api_url,
    read_github_artifact_bytes,
)
from investment_strategy.scheduled_agent_checkin import (
    checkin_title,
    is_runtime_checkin_issue,
    parse_checkin_day,
    taipei_day,
)
from investment_strategy.scheduled_agent_effect_contract import (
    EvidenceTarget,
    consequence_spec_for,
)
from investment_strategy.scheduled_agent_effects import (
    GITHUB_MUTATION_KIND,
    ApplicationDecisionRecord,
    ApplyResult,
    EffectBatch,
    EffectRecoveryEvidence,
    GitHubEffectAdapter,
    StagedEffect,
    _archive_branch,
    _archive_ref,
    _references_issue,
    _source_branch,
    archive_branch_matches_current_source,
    archive_branch_source_status,
    consequence_postconditions_complete,
    derived_transition_effect,
    formal_application_correlation,
    merged_pr_readiness_complete,
    parse_application_decision,
    parse_effect_batch,
)
from investment_strategy.scheduled_agent_formal_qualification import (
    build_qualification_input,
    qualify_current_formal_consequence,
)
from investment_strategy.scheduled_agent_formal_result import (
    FormalLifecycleEvent,
    parse_formal_result,
)
from investment_strategy.scheduled_agent_merge_acceptance import run_guarded_effect_application
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    acquire_current_github_preflight,
    is_github_actions_comment,
    normalize_github_issue,
)
from investment_strategy.scheduled_agent_validation_resource import ValidationResourceTarget
from investment_strategy.scheduled_agent_wire import (
    APPLICATION_CONTINUATION_WIRE,
    EFFECT_REQUEST_WIRE,
    MACHINE_EFFECT_REQUEST_WIRE,
)
from investment_strategy.scheduled_agent_worker import WorkerActionResult, parse_worker_result
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    ObservationProvenance,
    classify_dispatch,
)

APPLICATION_REQUEST_MARKER = "EFFECT_REQUEST"
APPLICATION_CONTINUATION_MARKER = "APPLICATION_CONTINUATION"
AUTHORIZATION_REVISION_PREFIX = "Authorization-Revision: "
DISPATCH_CORRELATION_PREFIX = "Dispatch-Correlation: "
WORKER_RESULT_B64_PREFIX = "Worker-Result-B64: "
ORIGINAL_REQUEST_COMMENT_PREFIX = "Original-Request-Comment: "
ACCEPTED_DECISION_SHA256_PREFIX = "Accepted-Decision-SHA256: "
PREDECESSOR_RUN_ID_PREFIX = "Predecessor-Run-ID: "
PREDECESSOR_RUN_ATTEMPT_PREFIX = "Predecessor-Run-Attempt: "
PREDECESSOR_JOB_ID_PREFIX = "Predecessor-Job-ID: "
PREDECESSOR_ARTIFACT_ID_PREFIX = "Predecessor-Artifact-ID: "
PREDECESSOR_ARTIFACT_DIGEST_PREFIX = "Predecessor-Artifact-Digest: "
FAILURE_EVIDENCE_SHA256_PREFIX = "Failure-Evidence-SHA256: "
RECOVERY_EPISODE_SHA256_PREFIX = "Recovery-Episode-SHA256: "
CONTINUATION_CORRELATION_PREFIX = "Continuation-Correlation: "
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_FORMAL_RESULT_MARKERS = frozenset({"ACTION_RESULT", "REVIEW_RESULT", "MERGE_RESULT"})
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_ROUTING_LABEL_PREFIXES = ("agent:", "action:")
_FIRST_ACTIVATION_RESULT = "ready-for-openspec-review"
_ACTIVATION_OBSERVATION_ATTEMPTS = 5
_ACTIVATION_OBSERVATION_DELAY_SECONDS = 1.0
_RECOVERY_MARKER = "APPLICATION_RECOVERY"
_RECOVERY_REASON = "partial-first-activation"
_RECOVERY_SOURCE = ("lead", "propose-change")
_RECOVERY_TARGET = ("lead", "resolve-question")


@dataclass(frozen=True)
class ApplicationRequest:
    """One worker result bound only to the default-branch revision it observed."""

    authorization_revision: str
    raw_worker_result: str
    dispatch_correlation: str | None = None


@dataclass(frozen=True)
class ApplicationContinuationRequest:
    """A fresh transport trigger bound to one exact recovery transition."""

    issue_number: int
    original_request_comment_id: int
    accepted_decision_sha256: str
    predecessor_run_id: int
    predecessor_run_attempt: int
    predecessor_job_id: int
    predecessor_artifact_id: int
    predecessor_artifact_digest: str
    failure_evidence_sha256: str
    recovery_episode_sha256: str
    continuation_correlation: str


@dataclass(frozen=True)
class ApplicationRecoveryArtifact:
    """One exact run/job/artifact transition eligible for fresh continuation."""

    run_id: int
    run_attempt: int
    job_id: int
    artifact_id: int
    artifact_digest: str
    request_comment_id: int
    accepted_decision_sha256: str
    failure_evidence_sha256: str
    recovery_episode_sha256: str
    recovery_attempt: int
    continuation_eligible: bool
    document: Mapping[str, object]


@dataclass(frozen=True)
class ApplicationExceptionArtifact:
    """An actual failed-run exception, never a fabricated recovery checkpoint.

    This identity permits *only* a fresh, read-only accepted-intent proof to
    authorize a continuation. The exception message is not an effect outcome.
    """

    run_id: int
    run_attempt: int
    job_id: int
    artifact_id: int
    artifact_digest: str
    request_comment_id: int
    accepted_decision_sha256: str
    failure_evidence_sha256: str
    recovery_episode_sha256: str
    document: Mapping[str, object]


@dataclass
class ApplicationExceptionContext:
    """Invocation-local observations, never routing or continuation authority."""

    repository: str | None = None
    token: str | None = None
    revision: str | None = None
    source: WorkerRequest | None = None
    change: str | None = None
    request_comment_id: int | None = None
    trigger_comment_id: int | None = None
    run_attempt: int = 1
    evidence_path: str | None = None
    stage: str = "application-bootstrap"
    mutation_attempted: bool = False


_APPLICATION_RECOVERY_ARTIFACT = "application-recovery-evidence"
_APPLICATION_RECOVERY_SCHEMA = "scheduled-agent-application-recovery/v1"
_MAX_APPLICATION_RECOVERY_BYTES = 65_536
_APPLICATION_EXCEPTION_ARTIFACTS = frozenset(
    {"application-execution-exception", "application-execution-exception.json"}
)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strict_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def application_continuation_correlation(
    repository: str,
    issue_number: int,
    original_request_comment_id: int,
    accepted_decision_sha256: str,
    predecessor_run_id: int,
    predecessor_run_attempt: int,
    predecessor_job_id: int,
    predecessor_artifact_id: int,
    predecessor_artifact_digest: str,
    failure_evidence_sha256: str,
    recovery_episode_sha256: str,
) -> str:
    """Content-address one qualified predecessor-to-recovery transition."""

    if (
        "/" not in repository
        or _positive_int(issue_number) is None
        or _positive_int(original_request_comment_id) is None
        or _positive_int(predecessor_run_id) is None
        or _positive_int(predecessor_run_attempt) is None
        or _positive_int(predecessor_job_id) is None
        or _positive_int(predecessor_artifact_id) is None
        or re.fullmatch(r"[0-9a-f]{64}", accepted_decision_sha256) is None
        or re.fullmatch(r"sha256:[0-9a-f]{64}", predecessor_artifact_digest) is None
        or re.fullmatch(r"[0-9a-f]{64}", failure_evidence_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", recovery_episode_sha256) is None
    ):
        raise ValueError("application continuation identity is invalid")
    material = "\n".join(
        (
            repository,
            str(issue_number),
            str(original_request_comment_id),
            accepted_decision_sha256,
            str(predecessor_run_id),
            str(predecessor_run_attempt),
            str(predecessor_job_id),
            str(predecessor_artifact_id),
            predecessor_artifact_digest,
            failure_evidence_sha256,
            recovery_episode_sha256,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def render_application_continuation_request(
    *,
    repository: str,
    issue_number: int,
    original_request_comment_id: int,
    accepted_decision_sha256: str,
    predecessor_run_id: int,
    predecessor_run_attempt: int,
    predecessor_job_id: int,
    predecessor_artifact_id: int,
    predecessor_artifact_digest: str,
    failure_evidence_sha256: str,
    recovery_episode_sha256: str,
) -> str:
    correlation = application_continuation_correlation(
        repository,
        issue_number,
        original_request_comment_id,
        accepted_decision_sha256,
        predecessor_run_id,
        predecessor_run_attempt,
        predecessor_job_id,
        predecessor_artifact_id,
        predecessor_artifact_digest,
        failure_evidence_sha256,
        recovery_episode_sha256,
    )
    return APPLICATION_CONTINUATION_WIRE.render(
        {
            "Issue": str(issue_number),
            "Original-Request-Comment": str(original_request_comment_id),
            "Accepted-Decision-SHA256": accepted_decision_sha256,
            "Predecessor-Run-ID": str(predecessor_run_id),
            "Predecessor-Run-Attempt": str(predecessor_run_attempt),
            "Predecessor-Job-ID": str(predecessor_job_id),
            "Predecessor-Artifact-ID": str(predecessor_artifact_id),
            "Predecessor-Artifact-Digest": predecessor_artifact_digest,
            "Failure-Evidence-SHA256": failure_evidence_sha256,
            "Recovery-Episode-SHA256": recovery_episode_sha256,
            "Continuation-Correlation": correlation,
        }
    )


def parse_application_continuation_request(
    body: str,
) -> ApplicationContinuationRequest | None:
    """Parse a strict transport bound to one exact recovery evidence transition."""

    fields = APPLICATION_CONTINUATION_WIRE.parse(body)
    if fields is None:
        return None
    try:
        issue_number = int(fields["Issue"])
        original_request_comment_id = int(fields["Original-Request-Comment"])
        predecessor_run_id = int(fields["Predecessor-Run-ID"])
        predecessor_run_attempt = int(fields["Predecessor-Run-Attempt"])
        predecessor_job_id = int(fields["Predecessor-Job-ID"])
        predecessor_artifact_id = int(fields["Predecessor-Artifact-ID"])
    except ValueError:
        return None
    accepted_decision_sha256 = fields["Accepted-Decision-SHA256"]
    predecessor_artifact_digest = fields["Predecessor-Artifact-Digest"]
    failure_evidence_sha256 = fields["Failure-Evidence-SHA256"]
    recovery_episode_sha256 = fields["Recovery-Episode-SHA256"]
    continuation_correlation = fields["Continuation-Correlation"]
    integer_pairs = (
        (fields["Issue"], issue_number),
        (fields["Original-Request-Comment"], original_request_comment_id),
        (fields["Predecessor-Run-ID"], predecessor_run_id),
        (fields["Predecessor-Run-Attempt"], predecessor_run_attempt),
        (fields["Predecessor-Job-ID"], predecessor_job_id),
        (fields["Predecessor-Artifact-ID"], predecessor_artifact_id),
    )
    if any(_positive_int(value) is None or raw != str(value) for raw, value in integer_pairs):
        return None
    if (
        re.fullmatch(r"[0-9a-f]{64}", accepted_decision_sha256) is None
        or re.fullmatch(r"sha256:[0-9a-f]{64}", predecessor_artifact_digest) is None
        or re.fullmatch(r"[0-9a-f]{64}", failure_evidence_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", recovery_episode_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", continuation_correlation) is None
    ):
        return None
    return ApplicationContinuationRequest(
        issue_number=issue_number,
        original_request_comment_id=original_request_comment_id,
        accepted_decision_sha256=accepted_decision_sha256,
        predecessor_run_id=predecessor_run_id,
        predecessor_run_attempt=predecessor_run_attempt,
        predecessor_job_id=predecessor_job_id,
        predecessor_artifact_id=predecessor_artifact_id,
        predecessor_artifact_digest=predecessor_artifact_digest,
        failure_evidence_sha256=failure_evidence_sha256,
        recovery_episode_sha256=recovery_episode_sha256,
        continuation_correlation=continuation_correlation,
    )


@dataclass(frozen=True)
class ApplicationPlan:
    """Validated application input or an unrelated-comment no-op."""

    should_apply: bool
    source: WorkerRequest | None = None
    raw_worker_result: str | None = None
    change: str | None = None
    request_comment_id: int | None = None
    pending_continuation: bool = False
    pending_application_correlation: str | None = None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _trusted_connector_comment(comment: Mapping[str, object], repository_owner: str) -> bool:
    return github_comment_has_app_provenance(
        comment, actor=repository_owner, app_slug=_CHATGPT_CONNECTOR_APP_SLUG
    )


def parse_application_request(body: str) -> ApplicationRequest | None:
    """Parse the bounded effect ingress and optional machine correlation."""

    if body.split("\n", 1)[0] != APPLICATION_REQUEST_MARKER:
        return None
    fields = MACHINE_EFFECT_REQUEST_WIRE.parse(body)
    if fields is None:
        fields = EFFECT_REQUEST_WIRE.parse(body)
    if fields is None:
        raise ValueError(
            "EFFECT_REQUEST must contain exactly three lines or the four-line machine form; "
            "fields, order, or framing are invalid"
        )
    authorization_revision = fields["Authorization-Revision"]
    dispatch_correlation = fields.get("Dispatch-Correlation")
    if dispatch_correlation is not None and not re.fullmatch(r"[0-9a-f]{64}", dispatch_correlation):
        raise ValueError("EFFECT_REQUEST dispatch correlation is invalid")
    encoded_result = fields["Worker-Result-B64"]
    if _SHA.fullmatch(authorization_revision) is None or not encoded_result:
        raise ValueError("EFFECT_REQUEST authorization identity is invalid")
    if encoded_result != encoded_result.strip():
        raise ValueError("EFFECT_REQUEST worker result must be trimmed")
    try:
        raw_worker_result = base64.b64decode(encoded_result.encode("ascii"), validate=True).decode(
            "utf-8"
        )
        decoded = json.loads(raw_worker_result)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise ValueError("EFFECT_REQUEST worker result is not valid base64 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("EFFECT_REQUEST worker result must decode to a JSON object")
    return ApplicationRequest(
        authorization_revision=authorization_revision,
        raw_worker_result=raw_worker_result,
        dispatch_correlation=dispatch_correlation,
    )


def render_application_request(
    request: ApplicationRequest,
    *,
    source: WorkerRequest | None = None,
    authorized_change: str | None = None,
) -> str:
    """Preflight typed worker input and round-trip the canonical request wire.

    Production callers provide the machine-owned source/Change.  Legacy fully
    identified results can supply a syntactic fallback to validate the wire,
    never to grant repository authorization or accepted-intent authority.
    """

    if source is None:
        source = _claimed_source(request.raw_worker_result)
    if source is None:
        raise ValueError("application request source is required for typed preflight")
    if authorized_change is None:
        try:
            decoded = json.loads(request.raw_worker_result)
        except json.JSONDecodeError as exc:
            raise ValueError("application request worker result is invalid JSON") from exc
        if not isinstance(decoded, Mapping) or not isinstance(decoded.get("change"), str):
            raise ValueError("application request authorized Change is required")
        authorized_change = cast(str, decoded["change"])
    parse_worker_result(request.raw_worker_result, source, authorized_change=authorized_change)

    return _render_accepted_application_wire(request)


def canonicalize_raw_worker_result(
    *,
    body: str,
    source: WorkerRequest,
    authorized_change: str,
    repository: str,
    current_revision: str,
) -> ApplicationRequest:
    """Construct a typed internal envelope from one external raw comment.

    Caller must separately qualify the original immutable GitHub event, its
    actor and the complete current machine dispatch. The generated wire is
    never a second GitHub comment or an independently authorized request.
    """

    marker = "WORKER_RESULT\n"
    if not body.startswith(marker):
        raise ValueError("WORKER_RESULT marker or newline is invalid")
    raw = body[len(marker) :]
    if not raw.strip():
        raise ValueError("WORKER_RESULT JSON body is empty")

    def unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
        fields: dict[str, object] = {}
        for key, value in pairs:
            if key in fields:
                raise ValueError("WORKER_RESULT contains duplicate JSON fields")
            fields[key] = value
        return fields

    try:
        decoder = json.JSONDecoder(object_pairs_hook=unique_fields)
        stripped = raw.lstrip()
        parsed, end = decoder.raw_decode(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("WORKER_RESULT body is invalid JSON") from exc
    suffix = stripped[end:]
    if (
        not isinstance(parsed, Mapping)
        or any(character not in " \t\r\n" for character in suffix)
        or suffix.count("\n") > 1
    ):
        raise ValueError("WORKER_RESULT must contain exactly one JSON object")
    allowed_fields = {
        "issue_number",
        "role",
        "action",
        "change",
        "result_kind",
        "evidence_ref",
        "result_content",
        "requested_effects",
    }
    if set(parsed) - allowed_fields:
        raise ValueError("WORKER_RESULT contains unknown JSON fields")
    raw = raw[:-1] if raw.endswith("\n") else raw
    request = ApplicationRequest(
        authorization_revision=current_revision,
        raw_worker_result=raw,
        dispatch_correlation=dispatch_correlation_for(repository, source, current_revision),
    )
    envelope = render_application_request(
        request,
        source=source,
        authorized_change=authorized_change,
    )
    parsed_request = parse_application_request(envelope)
    if parsed_request != request:
        raise ValueError("WORKER_RESULT application envelope round-trip failed")
    return parsed_request


def _render_accepted_application_wire(request: ApplicationRequest) -> str:
    """Only reconstruct already ACCEPTED immutable intent transport without preflight.

    Accepted semantic intent is not itself a fresh untrusted typed worker
    result; it is covered by its earlier qualified application decision. The
    initial emitter must always call the strict public renderer instead.
    """

    encoded = base64.b64encode(request.raw_worker_result.encode("utf-8")).decode("ascii")
    fields = {
        "Authorization-Revision": request.authorization_revision,
        "Worker-Result-B64": encoded,
    }
    if request.dispatch_correlation is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", request.dispatch_correlation):
            raise ValueError("application request dispatch correlation is invalid")
        fields["Dispatch-Correlation"] = request.dispatch_correlation
        contract = MACHINE_EFFECT_REQUEST_WIRE
    else:
        contract = EFFECT_REQUEST_WIRE
    body = contract.render(fields)
    if parse_application_request(body) != request:
        raise ValueError("application request renderer/parser contract mismatch")
    return body


def dispatch_correlation_for(
    repository: str,
    source: WorkerRequest,
    authorization_revision: str,
) -> str:
    """Derive the opaque carry-forward for one exact machine dispatch."""

    if "/" not in repository or _SHA.fullmatch(authorization_revision) is None:
        raise ValueError("dispatch correlation identity is invalid")
    canonical = "\x00".join(
        (
            repository,
            authorization_revision,
            str(source.issue_number),
            source.role,
            source.action,
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _claimed_source(raw_worker_result: str) -> WorkerRequest | None:
    try:
        decoded = json.loads(raw_worker_result)
    except json.JSONDecodeError as exc:
        raise ValueError("EFFECT_REQUEST worker result is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("EFFECT_REQUEST worker result must be a JSON object")
    identity = (decoded.get("issue_number"), decoded.get("role"), decoded.get("action"))
    if all(value is None for value in identity):
        return None
    issue_number, role, action = identity
    if (
        _positive_int(issue_number) is None
        or not isinstance(role, str)
        or not isinstance(action, str)
    ):
        raise ValueError("EFFECT_REQUEST worker source identity is invalid")
    return WorkerRequest(cast(int, issue_number), role, action)


def _preflight_change(preflight: DispatchPreflight, source: WorkerRequest) -> str | None:
    matching = tuple(
        issue for issue in preflight.issues if issue.issue_number == source.issue_number
    )
    if len(matching) != 1 or matching[0].routing != (source.role, source.action):
        return None
    return matching[0].change


def _without_application_correlation(body: str) -> str:
    """Normalize worker/formal bodies for exact replay identity."""

    return "\n".join(
        line for line in body.splitlines() if not line.startswith("Application-Correlation:")
    )


def _pending_application_correlation(
    *,
    raw_worker_result: str,
    source: WorkerRequest | None,
    preflight: DispatchPreflight,
    repository: str,
    token: str,
    current_revision: str,
) -> str | None:
    """Find one already-persisted formal result that can finish this application."""

    if source is None:
        return None

    enumeration = preflight.enumeration
    matching = tuple(
        issue for issue in preflight.issues if issue.issue_number == source.issue_number
    )
    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "FAIL_CLOSED"
        or decision.reason != "observations-unqualified"
        or preflight.human_authorized is not True
        or enumeration.incomplete_results
        or not enumeration.exhausted
        or enumeration.source_total_count is None
        or enumeration.observed_count != enumeration.source_total_count
        or len({issue.issue_number for issue in preflight.issues}) != len(preflight.issues)
        or len(matching) != 1
        or matching[0].current_state_provenance is not ObservationProvenance.INDETERMINATE
        or matching[0].state != "open"
        or matching[0].routing != (source.role, source.action)
    ):
        return None
    if any(
        issue.current_state_provenance is not ObservationProvenance.QUALIFIED
        for issue in preflight.issues
        if issue.issue_number != source.issue_number
    ):
        return None

    issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != source.issue_number
        or observation.state != "open"
        or observation.routing != (source.role, source.action)
    ):
        return None

    try:
        worker_result = parse_worker_result(
            raw_worker_result,
            source,
            authorized_change=matching[0].change,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if worker_result.change in {"", "unset"}:
        return None
    formal_body = _formal_result_body(worker_result, source=source)
    if formal_body is None:
        return None
    worker_revision = _field(formal_body, "Revision")
    worker_default_revision = _field(formal_body, "Default-Branch-Revision")
    if (
        worker_revision is None
        or worker_default_revision is None
        or _SHA.fullmatch(worker_revision) is None
        or _SHA.fullmatch(worker_default_revision) is None
        # Result revision identifies the reviewed work product; the default-branch
        # revision identifies the authorization snapshot. They are independent
        # identities and must not be collapsed into one SHA.
    ):
        return None
    authorization_ancestry: tuple[tuple[str, str], ...] = ()
    if worker_default_revision != current_revision:
        if not _authorization_revision_is_ancestor(
            repository,
            token,
            worker_default_revision,
            current_revision,
        ):
            return None
        authorization_ancestry = ((worker_default_revision, current_revision),)
    # A formal result may already be durable while its derived successor
    # was not.  First-activation recovery still requires its exact validation
    # materialization; ordinary formal results can resume from the persisted
    # result itself and re-run the existing application-owned successor guard.
    materializations = _materialization_effects(
        raw_worker_result,
        source,
        change=matching[0].change,
    )
    if len(materializations) > 1:
        return None
    if materializations:
        materialization = find_materialization_payload(materializations[0], source)
        if (
            materialization is None
            or materialization.expected_change != worker_result.change
            or not materialization_requires_validation(materialization, source)
        ):
            return None

    typed = worker_result.typed_result
    expected_result_kind = typed.result.kind.value
    try:
        successor = next_action(typed.action, typed.result)
    except (TypeError, ValueError):
        return None
    expected_terminal = successor is None
    expected_routing = None if successor is None else (role_for(successor).value, successor.value)
    comments = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created",
    )
    lifecycle = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/timeline",
    )
    worker_body = _without_application_correlation(formal_body)
    candidates: list[tuple[Mapping[str, object], FormalLifecycleEvent]] = []
    for comment in comments:
        event = parse_formal_result(comment, current_revision=current_revision)
        if (
            event is None
            or not event.valid
            or event.issue_number != source.issue_number
            or event.change != worker_result.change
            or event.role != source.role
            or event.action != source.action
            or event.result_kind != expected_result_kind
            or event.revision != worker_revision
            or event.default_branch_revision != worker_default_revision
            or event.successor != expected_routing
            or event.terminal != expected_terminal
            or event.application_correlation is None
            or _without_application_correlation(cast(str, comment.get("body", ""))) != worker_body
        ):
            continue
        candidates.append((comment, event))
    if len(candidates) != 1:
        return None
    _comment, candidate = candidates[0]
    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=worker_result.change,
        state=observation.state,
        current_routing=observation.routing,
        comments=comments,
        current_revision=current_revision,
        mode="pending",
        expected_routing=expected_routing,
        expected_terminal=expected_terminal,
        source_routing=(source.role, source.action),
        expected_result_kind=expected_result_kind,
        expected_application_correlation=candidate.application_correlation,
        lifecycle_events=lifecycle,
        authorization_ancestry=authorization_ancestry,
    )
    if current_revision is not None:
        ancestry = list(authorization_ancestry)
        for recovery in qualification.recovery_events:
            historical_revision = recovery.default_branch_revision
            if (
                not recovery.valid
                or historical_revision is None
                or historical_revision == current_revision
                or (historical_revision, current_revision) in ancestry
            ):
                continue
            if _authorization_revision_is_ancestor(
                repository,
                token,
                historical_revision,
                current_revision,
            ):
                ancestry.append((historical_revision, current_revision))
        if tuple(ancestry) != authorization_ancestry:
            qualification = replace(
                qualification,
                authorization_ancestry=tuple(ancestry),
            )
    if not qualify_current_formal_consequence(qualification).qualified:
        return None
    return candidate.application_correlation


def plan_application(
    *,
    event: Mapping[str, object],
    request: ApplicationRequest,
    preflight: DispatchPreflight,
    repository: str,
    current_revision: str,
    token: str | None = None,
    allow_descendant_resume: bool = False,
    allow_accepted_request_mutation: bool = False,
    accepted_intent: ApplicationDecisionRecord | None = None,
    accepted_request_comment_id: int | None = None,
    allow_raw_result_transport: bool = False,
    raw_shard_qualified: bool = False,
) -> ApplicationPlan:
    """Freshly derive the only legal source Issue/Action/Role from the repository."""

    if "/" not in repository or _SHA.fullmatch(current_revision) is None:
        raise ValueError("repository and current revision are required")
    if request.authorization_revision != current_revision and (
        not allow_descendant_resume
        or not _authorization_revision_is_ancestor(
            repository,
            os.environ.get("GITHUB_TOKEN", "") if token is None else token,
            request.authorization_revision,
            current_revision,
        )
    ):
        raise ValueError("EFFECT_REQUEST authorization revision is stale")

    issue = _as_mapping(event.get("issue"))
    event_comment = _as_mapping(event.get("comment"))
    if event.get("action") != "created" or issue is None or event_comment is None:
        return ApplicationPlan(False)
    if "pull_request" in issue or not is_runtime_checkin_issue(issue):
        return ApplicationPlan(False)

    body = event_comment.get("body")
    raw_matches = (
        allow_raw_result_transport
        and isinstance(body, str)
        and body.startswith("WORKER_RESULT\n")
        and body[len("WORKER_RESULT\n") :].removesuffix("\n") == request.raw_worker_result
    )
    if raw_matches and not raw_shard_qualified:
        raise ValueError("new WORKER_RESULT has no verified current-shard source")
    if not isinstance(body, str) or (
        not allow_accepted_request_mutation
        and not raw_matches
        and parse_application_request(body) != request
    ):
        raise ValueError("EFFECT_REQUEST event body does not match parsed request")
    repository_owner = repository.split("/", 1)[0]
    if not _trusted_connector_comment(event_comment, repository_owner):
        raise ValueError("EFFECT_REQUEST must originate from the configured ChatGPT connector")
    event_comment_id = _positive_int(event_comment.get("id"))
    if event_comment_id is None:
        raise ValueError("EFFECT_REQUEST event comment id is invalid")
    request_comment_id = event_comment_id

    if accepted_intent is not None and accepted_intent.disposition == "ACCEPTED":
        # After ACCEPT, the immutable intent—not the current semantic
        # frontier—owns continuation.  The current frontier may already be
        # the derived successor and therefore has a different correlation.
        if accepted_request_comment_id is not None:
            if accepted_request_comment_id != accepted_intent.request_comment_id:
                raise ValueError("accepted application intent request identity is invalid")
            request_comment_id = accepted_request_comment_id
        if accepted_intent.request_comment_id != request_comment_id:
            raise ValueError("accepted application intent request identity is invalid")
        accepted_source = WorkerRequest(
            accepted_intent.issue_number,
            accepted_intent.role,
            accepted_intent.action,
        )
        claimed = _claimed_source(accepted_intent.raw_worker_result)
        if claimed is not None and claimed != accepted_source:
            raise ValueError("accepted application intent worker source is invalid")
        current_dispatch = classify_dispatch(preflight)
        return ApplicationPlan(
            should_apply=True,
            source=accepted_source,
            raw_worker_result=accepted_intent.raw_worker_result,
            change=accepted_intent.change,
            request_comment_id=request_comment_id,
            pending_continuation=(
                current_dispatch.disposition == "FAIL_CLOSED"
                and current_dispatch.reason == "observations-unqualified"
            ),
        )

    claimed = _claimed_source(request.raw_worker_result)
    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id is None
        or decision.selected_routing is None
    ):
        continuation_source = claimed
        if continuation_source is None and accepted_intent is not None:
            continuation_source = WorkerRequest(
                accepted_intent.issue_number,
                accepted_intent.role,
                accepted_intent.action,
            )
        continuation_change = (
            accepted_intent.change
            if accepted_intent is not None and continuation_source is not None
            else None
        )
        pending_correlation = _pending_application_correlation(
            raw_worker_result=request.raw_worker_result,
            source=continuation_source,
            preflight=preflight,
            repository=repository,
            token=os.environ.get("GITHUB_TOKEN", "") if token is None else token,
            current_revision=current_revision,
        )
        if pending_correlation is None:
            raise ValueError("EFFECT_REQUEST has no current AUTHORIZE dispatch")
        if continuation_source is None:
            raise ValueError("EFFECT_REQUEST machine source is unavailable")
        if continuation_change is None:
            continuation_change = _preflight_change(preflight, continuation_source)
        if continuation_change is None:
            raise ValueError("EFFECT_REQUEST current Change is unavailable")
        return ApplicationPlan(
            should_apply=True,
            source=continuation_source,
            raw_worker_result=request.raw_worker_result,
            change=continuation_change,
            request_comment_id=request_comment_id,
            pending_continuation=True,
            pending_application_correlation=pending_correlation,
        )
    selected_role, selected_action = decision.selected_routing
    source = WorkerRequest(decision.selected_issue_id, selected_role, selected_action)
    if claimed is not None and claimed != source:
        raise ValueError("EFFECT_REQUEST worker source does not match fresh repository Action")
    change = _preflight_change(preflight, source)
    if change is None:
        raise ValueError("EFFECT_REQUEST current Change is unavailable")
    if request.dispatch_correlation is not None:
        expected_correlation = dispatch_correlation_for(
            repository,
            source,
            request.authorization_revision,
        )
        if request.dispatch_correlation != expected_correlation:
            raise ValueError(
                "EFFECT_REQUEST dispatch correlation does not match fresh repository Action"
            )
    if accepted_intent is not None and (
        accepted_intent.issue_number != source.issue_number
        or accepted_intent.role != source.role
        or accepted_intent.action != source.action
    ):
        raise ValueError("accepted application intent does not match fresh repository Action")
    return ApplicationPlan(
        should_apply=True,
        source=source,
        raw_worker_result=request.raw_worker_result,
        change=change,
        request_comment_id=request_comment_id,
    )


def _github_json(
    repository: str,
    token: str,
    api_path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
    allow_not_found: bool = False,
) -> object:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        github_repository_api_url(repository, api_path),
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    # GET retries share one transport contract with the source Issue reader;
    # writes remain one-shot because a lost response makes outcome unknown.
    if method == "GET":
        try:
            raw = github_read_bytes_with_retry(
                request,
                open_request=urlopen,  # noqa: S310 - trusted GitHub API host
                wait=time.sleep,
            )
        except HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return None
            raise
    else:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - trusted API host
            raw = response.read()
    return None if not raw else json.loads(raw.decode("utf-8"))


def _paged_github_list(
    repository: str,
    token: str,
    api_path: str,
) -> tuple[Mapping[str, object], ...]:
    return github_paginated_mappings(
        repository,
        token,
        api_path,
        read=_github_json,
        incomplete_error="GitHub paginated evidence endpoint returned a non-list response",
        malformed_error="GitHub paginated evidence endpoint returned a malformed item",
    )


def _application_decision_for_request(
    *,
    repository: str,
    token: str,
    issue_number: int,
    request_comment_id: int,
    request_body: str,
) -> ApplicationDecisionRecord | None:
    """Return the one durable decision for an exact request identity.

    The request comment is mutable transport.  Its body hash is useful for
    diagnosing an edit, but it cannot be required to resume an already
    accepted intent: doing so would turn an interruption/edit boundary into a
    semantic replay opportunity.  The source Issue and request comment id are
    the durable lookup key; the accepted record's immutable worker payload is
    the only payload used for continuation.
    """

    matches = _application_decisions_for_request_id(
        repository=repository,
        token=token,
        issue_number=issue_number,
        request_comment_id=request_comment_id,
    )
    if len(matches) != 1:
        return None
    record = matches[0]
    if record.disposition not in {"ACCEPTED", "REJECTED"}:
        return None
    return record


def _find_application_decision_from_current_frontier(
    *,
    repository: str,
    token: str,
    request_comment_id: int,
    preflight: DispatchPreflight,
) -> ApplicationDecisionRecord | None:
    """Find one exact decision on the complete fresh workflow-Issue surface.

    The source Issue may be temporarily ``INDETERMINATE`` while an accepted
    formal result is already durable but its derived routing projection is not.
    That observation cannot authorize new semantic work, but it must not hide
    the immutable accepted owner from Phase-B recovery.  The preflight must
    still be a complete, duplicate-free enumeration; every source candidate is
    read by the exact request comment id and multiple matches fail closed.
    """

    enumeration = preflight.enumeration
    if (
        enumeration.incomplete_results
        or not enumeration.exhausted
        or enumeration.source_total_count is None
        or enumeration.observed_count != enumeration.source_total_count
    ):
        raise ValueError("application decision source enumeration is incomplete")
    if preflight.human_authorized is not True:
        raise ValueError("application decision source lacks Human authority")
    issue_numbers = tuple(issue.issue_number for issue in preflight.issues)
    if len(issue_numbers) != len(set(issue_numbers)):
        raise ValueError("application decision source enumeration is ambiguous")

    matches: list[ApplicationDecisionRecord] = []
    for issue_number in issue_numbers:
        matches.extend(
            _application_decisions_for_request_id(
                repository=repository,
                token=token,
                issue_number=issue_number,
                request_comment_id=request_comment_id,
            )
        )
    if len(matches) > 1:
        raise ValueError("application decision identity is ambiguous")
    return None if not matches else matches[0]


def _application_decisions_for_request_id(
    *,
    repository: str,
    token: str,
    issue_number: int,
    request_comment_id: int,
) -> tuple[ApplicationDecisionRecord, ...]:
    """Read immutable decisions by request id without trusting mutable ingress text."""

    comments = _paged_github_list(
        repository,
        token,
        f"issues/{issue_number}/comments?sort=created&direction=asc",
    )
    matches: list[ApplicationDecisionRecord] = []
    for comment in comments:
        if not is_github_actions_comment(comment):
            continue
        record = parse_application_decision(comment.get("body"))
        if record is not None and record.request_comment_id == request_comment_id:
            matches.append(record)
    if len(matches) > 1:
        raise ValueError("application decision identity is ambiguous")
    return () if not matches else (matches[0],)


def _application_decision_comment_for_request(
    *,
    repository: str,
    token: str,
    issue_number: int,
    request_comment_id: int,
) -> tuple[ApplicationDecisionRecord, str] | None:
    """Return one exact decision record together with its immutable body."""

    comments = _paged_github_list(
        repository,
        token,
        f"issues/{issue_number}/comments?sort=created&direction=asc",
    )
    matches: list[tuple[ApplicationDecisionRecord, str]] = []
    for comment in comments:
        if not is_github_actions_comment(comment):
            continue
        body = comment.get("body")
        if not isinstance(body, str):
            continue
        record = parse_application_decision(body)
        if record is not None and record.request_comment_id == request_comment_id:
            matches.append((record, body))
    if len(matches) > 1:
        raise ValueError("application decision identity is ambiguous")
    return None if not matches else matches[0]


def _worker_semantic_projection(raw_worker_result: str) -> str:
    try:
        decoded = json.loads(raw_worker_result)
    except json.JSONDecodeError as exc:
        raise RuntimeError("accepted worker result is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("accepted worker result is not an object")
    decoded.pop("requested_effects", None)
    decoded.pop("_semantic_intent_version", None)
    return json.dumps(decoded, sort_keys=True, separators=(",", ":"))


def _accepted_worker_result_for_continuation(
    *,
    accepted_intent: ApplicationDecisionRecord,
    source: WorkerRequest,
    repository: str,
    token: str,
    request_comment_id: int,
) -> str:
    """Recover one old mechanical manifest when an older decision stripped it."""

    try:
        existing = _materialization_effects(
            accepted_intent.raw_worker_result,
            source,
            change=accepted_intent.change,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("accepted application intent is not parseable") from exc
    if existing:
        return accepted_intent.raw_worker_result
    if (
        source != WorkerRequest(source.issue_number, "lead", "propose-change")
        or accepted_intent.change != "unset"
        or accepted_intent.result_kind != _FIRST_ACTIVATION_RESULT
    ):
        return accepted_intent.raw_worker_result

    comment = _as_mapping(_github_json(repository, token, f"issues/comments/{request_comment_id}"))
    owner = repository.split("/", 1)[0]
    body = None if comment is None else comment.get("body")
    if (
        comment is None
        or comment.get("id") != request_comment_id
        or not isinstance(body, str)
        or not _trusted_connector_comment(comment, owner)
        or hashlib.sha256(body.encode("utf-8")).hexdigest() != accepted_intent.request_body_sha256
    ):
        raise RuntimeError("accepted first activation mechanical request is unavailable")

    original = parse_application_request(body)
    if (
        original is None
        or original.authorization_revision != accepted_intent.authorization_revision
    ):
        raise RuntimeError("accepted first activation mechanical request identity is invalid")
    if original.dispatch_correlation is not None and original.dispatch_correlation != (
        dispatch_correlation_for(repository, source, original.authorization_revision)
    ):
        raise RuntimeError("accepted first activation dispatch correlation is invalid")
    if _claimed_source(original.raw_worker_result) != source:
        raise RuntimeError("accepted first activation worker source changed")
    try:
        original_worker = parse_worker_result(
            original.raw_worker_result,
            source,
            authorized_change="unset",
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("accepted first activation worker result is invalid") from exc
    if (
        original_worker.change != "unset"
        or original_worker.typed_result.result.kind.value != _FIRST_ACTIVATION_RESULT
        or _worker_semantic_projection(original.raw_worker_result)
        != _worker_semantic_projection(accepted_intent.raw_worker_result)
    ):
        raise RuntimeError("accepted first activation semantic intent does not match")
    materializations = _materialization_effects(
        original.raw_worker_result,
        source,
        change="unset",
    )
    if len(materializations) != 1:
        raise RuntimeError("accepted first activation mechanical manifest is unavailable")
    parsed = find_materialization_payload(materializations[0], source)
    if parsed is None or parsed.expected_change != "unset" or parsed.change in {"", "unset"}:
        raise RuntimeError("accepted first activation mechanical manifest is invalid")
    recovered = json.loads(accepted_intent.raw_worker_result)
    if not isinstance(recovered, dict):
        raise RuntimeError("accepted first activation semantic intent is invalid")
    recovered["requested_effects"] = [
        {
            "kind": GITHUB_MUTATION_KIND,
            "payload_json": json.dumps(dict(materializations[0]), sort_keys=True),
        }
    ]
    return json.dumps(recovered, sort_keys=True, separators=(",", ":"))


def _verified_zero_original_accepted_effects(
    *,
    record: ApplicationDecisionRecord,
    source: WorkerRequest,
    repository: str,
    token: str,
    read: Callable[[str, str, str], object] | None = None,
) -> bool:
    """Prove zero *physical* original Effects, not an empty semantic projection.

    This additional proof is required only at exception reconciliation; normal
    accepted continuations remain independent of mutable ingress transport.
    """

    if record.disposition != "ACCEPTED" or (record.issue_number, record.role, record.action) != (
        source.issue_number,
        source.role,
        source.action,
    ):
        return False
    decoded = json.loads(record.raw_worker_result)
    if not isinstance(decoded, dict) or decoded.get("requested_effects") != []:
        return False
    reader = _github_json if read is None else read
    source_comment = _as_mapping(
        reader(repository, token, f"issues/comments/{record.request_comment_id}")
    )
    body = None if source_comment is None else source_comment.get("body")
    if (
        source_comment is None
        or source_comment.get("id") != record.request_comment_id
        or not isinstance(body, str)
        or not _trusted_connector_comment(source_comment, repository.split("/", 1)[0])
        or hashlib.sha256(body.encode()).hexdigest() != record.request_body_sha256
    ):
        return False
    original = parse_application_request(body)
    if (
        original is None
        or original.authorization_revision != record.authorization_revision
        or (
            original.dispatch_correlation is not None
            and original.dispatch_correlation
            != dispatch_correlation_for(repository, source, original.authorization_revision)
        )
        or _claimed_source(original.raw_worker_result) != source
    ):
        return False
    parsed = parse_worker_result(
        original.raw_worker_result, source, authorized_change=record.change
    )
    original_decoded = json.loads(original.raw_worker_result)
    return bool(
        isinstance(original_decoded, dict)
        and original_decoded.get("requested_effects") == []
        and parsed.change == record.change
        and parsed.typed_result.result.kind.value == record.result_kind
        and _worker_semantic_projection(original.raw_worker_result)
        == _worker_semantic_projection(record.raw_worker_result)
    )


def _github_timestamp(value: object) -> datetime:
    """Require a complete, timezone-aware GitHub creation timestamp."""

    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("new WORKER_RESULT source timestamp is unavailable")
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("new WORKER_RESULT source timestamp is malformed") from exc
    if observed.tzinfo is None:
        raise ValueError("new WORKER_RESULT source timestamp has no timezone")
    return observed


def _shard_was_open_at_comment_creation(
    observed_issue: Mapping[str, object], created: datetime
) -> bool:
    """Permit rollover only when fresh closure evidence follows the source comment.

    The immutable issue_comment.created event proves the shard was OPEN when
    the comment was posted. A later GET/list can see CLOSED after rollover;
    requiring it to remain OPEN would strand a legitimate in-flight request.
    """

    state = observed_issue.get("state")
    if state == "open":
        return True
    if state != "closed":
        return False
    try:
        return _github_timestamp(observed_issue.get("closed_at")) > created
    except ValueError:
        return False


def _qualify_new_raw_result_shard(
    *,
    event_issue: Mapping[str, object],
    event_comment: Mapping[str, object],
    observed_comment: Mapping[str, object],
    observed_issue: Mapping[str, object],
    repository: str,
    token: str,
) -> None:
    """Authorize a *new* raw result only on its unique creation-day shard.

    Historical closed/open transport remains valid for an already ACCEPTED
    intent, which never calls this new-ingress qualifier on continuation.
    """

    created_at = observed_comment.get("created_at")
    if created_at != event_comment.get("created_at"):
        raise ValueError("new WORKER_RESULT creation timestamp changed")
    created = _github_timestamp(created_at)
    shard_created = _github_timestamp(observed_issue.get("created_at"))
    day = taipei_day(created)
    issue_number = _positive_int(observed_issue.get("number"))
    if (
        issue_number is None
        or shard_created > created
        or event_issue.get("state") != "open"
        or event_issue.get("number") != issue_number
        or event_issue.get("created_at") != observed_issue.get("created_at")
        or event_issue.get("title") != observed_issue.get("title")
        or not _shard_was_open_at_comment_creation(observed_issue, created)
        or observed_issue.get("title") != checkin_title(day)
    ):
        raise ValueError("new WORKER_RESULT was not created on its current-day shard")

    # This must be an all-state list. Open-only discovery would miss a duplicate
    # closed shard and could turn an ambiguous date into source authorization.
    issues = _paged_github_list(repository, token, "issues?state=all")
    day_shards = [issue for issue in issues if issue.get("title") == checkin_title(day)]
    matches = [issue for issue in issues if issue.get("number") == issue_number]
    if (
        len(day_shards) != 1
        or parse_checkin_day(day_shards[0]) != day
        or day_shards[0].get("number") != issue_number
        or len(matches) != 1
        or not _shard_was_open_at_comment_creation(matches[0], created)
        or matches[0].get("title") != observed_issue.get("title")
        or matches[0].get("created_at") != observed_issue.get("created_at")
    ):
        raise ValueError("new WORKER_RESULT creation-day shard is not uniquely qualified")


def _fresh_event_observation(
    event: Mapping[str, object],
    body: str,
    repository: str,
    token: str,
) -> bool:
    issue = _as_mapping(event.get("issue"))
    comment = _as_mapping(event.get("comment"))
    if event.get("action") != "created" or issue is None or comment is None:
        raise ValueError("application request event is invalid")
    if "pull_request" in issue or not is_runtime_checkin_issue(issue):
        raise ValueError("application request event is not a control shard comment")

    comment_id = _positive_int(comment.get("id"))
    issue_number = _positive_int(issue.get("number"))
    owner = repository.split("/", 1)[0] if "/" in repository else ""
    if (
        comment_id is None
        or issue_number is None
        or comment.get("body") != body
        or not _trusted_connector_comment(comment, owner)
    ):
        raise ValueError("application request event identity is invalid")

    observed_comment = _as_mapping(_github_json(repository, token, f"issues/comments/{comment_id}"))
    if (
        observed_comment is None
        or observed_comment.get("id") != comment_id
        or not _trusted_connector_comment(observed_comment, owner)
    ):
        raise ValueError("application request current comment observation is incomplete")
    body_mutated = observed_comment.get("body") != body
    observed_issue = _as_mapping(_github_json(repository, token, f"issues/{issue_number}"))
    if (
        observed_issue is None
        or observed_issue.get("number") != issue_number
        or not is_runtime_checkin_issue(observed_issue)
    ):
        raise ValueError("application request current shard observation is invalid")
    if body.startswith("WORKER_RESULT\n"):
        _qualify_new_raw_result_shard(
            event_issue=issue,
            event_comment=comment,
            observed_comment=observed_comment,
            observed_issue=observed_issue,
            repository=repository,
            token=token,
        )
    return body_mutated


def _load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _materialization_effects(
    raw_worker_result: str,
    source: WorkerRequest,
    *,
    change: str | None = None,
) -> tuple[Mapping[str, object], ...]:
    result = parse_worker_result(raw_worker_result, source, authorized_change=change)
    effects: list[Mapping[str, object]] = []
    for requested in result.requested_effects:
        if requested.kind != "github-mutation":
            continue
        try:
            payload = json.loads(requested.payload_json)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping) and payload.get("operation") == "application-materialize":
            effects.append(cast(Mapping[str, object], payload))
    return tuple(effects)


def _fresh_branch_head(
    repository: str,
    token: str,
    branch: str,
) -> str | None:
    """Read one branch head as current evidence, never as worker authority."""

    try:
        payload = _github_json(
            repository,
            token,
            f"git/ref/heads/{quote(branch, safe='/')}",
            allow_not_found=True,
        )
    except (HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return None
    obj = payload.get("object") if isinstance(payload, Mapping) else None
    sha = obj.get("sha") if isinstance(obj, Mapping) else None
    return sha if _SHA.fullmatch(sha or "") is not None else None


def _machine_result_revision(
    raw_worker_result: str,
    source: WorkerRequest,
    *,
    change: str,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
) -> str:
    """Derive a work-product revision from fresh carrier evidence.

    A semantic worker may still carry a legacy ``Revision`` line in narrative
    evidence, but normal application never needs it.  For a materialization
    request the current PR head is the only acceptable pre-commit machine
    observation; the post-materialization validation target is rebound later.
    """

    try:
        worker = parse_worker_result(raw_worker_result, source, authorized_change=change)
    except (TypeError, ValueError, json.JSONDecodeError):
        worker = None
    try:
        decoded = json.loads(raw_worker_result)
    except json.JSONDecodeError:
        decoded = None
    if (
        worker is not None
        and isinstance(decoded, Mapping)
        and decoded.get("_semantic_intent_version") != 2
    ):
        # Historical envelopes carried a formal work-product revision.  It is
        # retained as migration evidence only; all repository controls still
        # pass through the fresh planner below.  New semantic intents never
        # enter this compatibility branch.
        legacy_body = _formal_result_body(worker, source=source)
        legacy_revision = None if legacy_body is None else _field(legacy_body, "Revision")
        if _SHA.fullmatch(legacy_revision or "") is not None:
            return cast(str, legacy_revision)

    materializations = _materialization_effects(raw_worker_result, source, change=change)
    if len(materializations) > 1:
        raise RuntimeError("EFFECT_REQUEST contains ambiguous materialization effects")
    if not materializations:
        if worker is None:
            return current_revision
        spec = consequence_spec_for(source.action, worker.typed_result.result.kind)
        if spec.evidence_target is EvidenceTarget.DEFAULT_BRANCH:
            return current_revision
        if spec.evidence_target is EvidenceTarget.ARCHIVE_PR_HEAD:
            branch = _archive_branch(change)
            return (
                current_revision
                if branch is None
                else (_fresh_branch_head(repository, token, branch) or current_revision)
            )
        if spec.evidence_target is EvidenceTarget.MERGED_PR_HEAD:
            merged_revision = _fresh_merged_carrier_revision(
                repository=repository,
                token=token,
                source=source,
                change=change,
                current_revision=current_revision,
                default_branch=default_branch,
            )
            return merged_revision or current_revision
        return _machine_carrier_head(
            repository=repository,
            token=token,
            source=source,
            change=change,
            default_branch=default_branch,
            current_revision=current_revision,
            allow_reconciliation_findings=(
                source.action == "review-implementation"
                and worker.typed_result.result.kind.value == "findings"
            ),
        )
    parsed = find_materialization_payload(materializations[0], source)
    if parsed is None or parsed.change != change:
        raise RuntimeError("application materialization carrier identity is incomplete")
    if parsed.pr_number is None:
        if (
            parsed.base_sha == current_revision
            and source.role == "executor"
            and source.action == "implement-change"
            and qualify_supersession_branch(
                repository=repository,
                token=token,
                issue_number=source.issue_number,
                change=change,
                branch=parsed.branch,
                current_revision=current_revision,
            )
        ):
            return current_revision
        raise RuntimeError("application supersession materialization is unqualified")
    qualification = qualify_implementation_carrier(
        repository=repository,
        token=token,
        source=source,
        change=change,
        pr_number=parsed.pr_number,
        current_revision=current_revision,
    )
    if (
        not qualification.recognized
        or qualification.default_branch != default_branch
        or not isinstance(qualification.head_sha, str)
    ):
        raise RuntimeError(
            f"application work-product carrier is not freshly recognized: {qualification.reason}"
        )
    return qualification.head_sha


def _machine_carrier_head(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    default_branch: str,
    current_revision: str,
    allow_reconciliation_findings: bool = False,
) -> str:
    """Resolve the current implementation carrier using its governed lineage.

    Review follows the exact accepted READY occurrence, including when its
    implementation PR was merged before the delayed formal consequence.
    """

    if canonical_implementation_branch(change) is None:
        return current_revision
    review_predecessor = (
        _review_predecessor_carrier(repository, token, source, change, current_revision)
        if source.action == "review-implementation"
        else None
    )
    if review_predecessor is not None and review_predecessor[0] is not None:
        # An accepted materialization carries its own immutable PR identity.
        # A later maintenance PR or unrelated newer Change carrier cannot
        # silently replace the reviewed work product, even if its HEAD SHA
        # was mistakenly copied into a delayed formal READY projection.
        accepted_number = review_predecessor[0]
        qualification = qualify_implementation_carrier(
            repository=repository,
            token=token,
            source=source,
            change=change,
            pr_number=accepted_number,
            current_revision=current_revision,
        )
        if (
            (
                qualification.disposition in {"QUALIFIED", "HISTORICAL_MERGED"}
                or (
                    allow_reconciliation_findings
                    and qualification.disposition == "RECONCILIATION_REQUIRED"
                    and qualification.head_sha == review_predecessor[1]
                )
            )
            and qualification.default_branch == default_branch
            and isinstance(qualification.head_sha, str)
        ):
            # A rejected implementation head can still be reviewed exactly
            # after unrelated default-branch maintenance advanced.  Returning
            # FINDINGS to Executor permits its existing carrier-reconciliation
            # owner to fix that head.  PASS (and every merge transition) must
            # retain strict QUALIFIED/HISTORICAL_MERGED ancestry.
            return qualification.head_sha
        raise RuntimeError("application accepted implementation carrier is not qualified")
    candidates = _paged_github_list(
        repository,
        token,
        f"pulls?{urlencode({'state': 'open', 'base': default_branch})}",
    )
    heads: list[str] = []
    for summary in candidates:
        number = _positive_int(summary.get("number"))
        if number is None:
            continue
        qualification = qualify_implementation_carrier(
            repository=repository,
            token=token,
            source=source,
            change=change,
            pr_number=number,
            current_revision=current_revision,
        )
        if (
            not qualification.recognized
            or qualification.default_branch != default_branch
            or not isinstance(qualification.head_sha, str)
        ):
            continue
        if review_predecessor is None or qualification.head_sha == review_predecessor[1]:
            heads.append(qualification.head_sha)
    if len(heads) > 1:
        raise RuntimeError("application carrier head is ambiguous")
    if heads:
        return heads[0]

    # The same qualification owner already admits immutable merged carriers
    # for exact-head review.  An open-only discovery query must not make that
    # legal review state unreachable after a default-branch merge.  This is
    # review-only: a new implementation must never reuse an old merged head.
    if source.action == "review-implementation":
        history = _historical_carriers(
            repository,
            token,
            issue_number=source.issue_number,
            change=change,
            default_branch=default_branch,
            default_revision=current_revision,
            read=_github_json,
        )
        if history:
            number, _ = history[-1]
            qualification = qualify_implementation_carrier(
                repository=repository,
                token=token,
                source=source,
                change=change,
                pr_number=number,
                current_revision=current_revision,
            )
            if (
                qualification.disposition == "HISTORICAL_MERGED"
                and qualification.default_branch == default_branch
                and isinstance(qualification.head_sha, str)
                and review_predecessor is not None
                and qualification.head_sha == review_predecessor[1]
            ):
                return qualification.head_sha
    raise RuntimeError("application implementation carrier is not freshly recognized")


def _review_predecessor_carrier(
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    current_revision: str,
) -> tuple[int | None, str]:
    """Bind review to its immediately preceding accepted READY work product.

    A formal result is a state transition, not a new implementation event.
    When accepted materialization exists, its immutable PR identity is the
    stronger work-product evidence; a READY ``Revision`` is only its recorded
    projection and cannot authorize selecting a maintenance PR.  Without an
    accepted materialization, exact READY revision remains mandatory.
    """

    issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.change != change
        or observation.routing != ("reviewer", "review-implementation")
    ):
        raise RuntimeError("application review predecessor current route is not qualified")
    comments = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created&direction=asc",
    )
    events = tuple(
        event
        for comment in comments
        if (event := parse_formal_result(comment, current_revision=current_revision)) is not None
    )
    if not events:
        raise RuntimeError("application review predecessor formal result is absent")
    latest = None
    for event in reversed(events):
        if (
            not event.valid
            or event.issue_number != source.issue_number
            or event.change != change
            or not isinstance(event.revision, str)
        ):
            raise RuntimeError("application review predecessor formal identity is invalid")
        if (event.role, event.action, event.result_kind) == (
            "executor",
            "implement-change",
            "ready",
        ):
            latest = event
            break
        if (
            (event.role, event.action, event.result_kind)
            != ("reviewer", "review-implementation", "blocked")
            or event.successor != ("reviewer", "review-implementation")
            or event.revision != event.default_branch_revision
        ):
            raise RuntimeError("application review predecessor chain is not a legal self-loop")
        if (
            event.default_branch_revision != current_revision
            and not _authorization_revision_is_ancestor(
                repository,
                token,
                cast(str, event.default_branch_revision),
                current_revision,
            )
        ):
            raise RuntimeError("application review predecessor blocked evidence is stale")
    if latest is None or latest.successor != ("reviewer", "review-implementation"):
        raise RuntimeError("application review predecessor is not an accepted READY")
    correlation = latest.application_correlation
    parts = correlation.split(":") if isinstance(correlation, str) else []
    if (
        len(parts) != 8
        or parts[0] != "application"
        or not parts[1].isdigit()
        or parts[2:]
        != [
            str(source.issue_number),
            change,
            "executor",
            "implement-change",
            "ready",
            latest.default_branch_revision,
        ]
    ):
        raise RuntimeError("application review predecessor correlation is invalid")
    decisions = _application_decisions_for_request_id(
        repository=repository,
        token=token,
        issue_number=source.issue_number,
        request_comment_id=int(parts[1]),
    )
    if len(decisions) != 1:
        raise RuntimeError("application review predecessor accepted intent is unavailable")
    accepted = decisions[0]
    if (
        accepted.disposition != "ACCEPTED"
        or accepted.issue_number != source.issue_number
        or (accepted.role, accepted.action, accepted.change, accepted.result_kind)
        != ("executor", "implement-change", change, "ready")
    ):
        raise RuntimeError("application review predecessor accepted identity is invalid")
    ready_source = WorkerRequest(source.issue_number, "executor", "implement-change")
    materializations = _materialization_effects(
        accepted.raw_worker_result,
        ready_source,
        change=change,
    )
    if len(materializations) > 1:
        raise RuntimeError("application review predecessor materialization is ambiguous")
    if not materializations:
        return None, cast(str, latest.revision)
    materialization = find_materialization_payload(materializations[0], ready_source)
    if materialization is None or materialization.change != change:
        raise RuntimeError("application review predecessor PR identity is incomplete")
    if materialization.pr_number is None:
        if not qualify_supersession_branch(
            repository=repository,
            token=token,
            issue_number=source.issue_number,
            change=change,
            branch=materialization.branch,
            current_revision=current_revision,
        ):
            raise RuntimeError("accepted supersession lost formal retirement authority")
        owner = repository.split("/", 1)[0]
        candidates = _paged_github_list(
            repository,
            token,
            f"pulls?{urlencode({'state': 'all', 'head': f'{owner}:{materialization.branch}'})}",
        )
        if len(candidates) != 1:
            raise RuntimeError("accepted supersession PR identity is missing or ambiguous")
        candidate_number = _positive_int(candidates[0].get("number"))
        if candidate_number is None:
            raise RuntimeError("accepted supersession PR number is unavailable")
        qualification = qualify_implementation_carrier(
            repository=repository,
            token=token,
            source=source,
            change=change,
            pr_number=candidate_number,
            current_revision=current_revision,
        )
        if (
            qualification.disposition not in {"QUALIFIED", "RECONCILIATION_REQUIRED"}
            or qualification.branch != materialization.branch
            or qualification.head_sha != latest.revision
        ):
            raise RuntimeError("accepted supersession PR is not an exact READY successor")
        return candidate_number, cast(str, latest.revision)
    return materialization.pr_number, cast(str, latest.revision)


def _field_values(body: str, key: str) -> tuple[str, ...]:
    return tuple(
        value.strip().strip(chr(96))
        for value in re.findall(rf"(?m)^{re.escape(key)}:[ \t]*(.*)$", body)
    )


def _field(body: str, key: str) -> str | None:
    values = _field_values(body, key)
    if len(values) != 1 or not values[0]:
        return None
    return values[0]


def _marker(body: str) -> str | None:
    first = body.splitlines()[:1]
    if not first:
        return None
    marker = first[0].strip()
    return marker[3:].strip() if marker.startswith("## ") else marker


def _formal_result_body(
    worker_result: WorkerActionResult,
    *,
    source: WorkerRequest,
) -> str | None:
    """Extract the one canonical formal body requested by this worker result."""

    bodies: list[str] = []
    for requested in worker_result.requested_effects:
        if requested.kind != "issue-comment":
            continue
        try:
            payload = json.loads(requested.payload_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping) or payload.get("issue_number") != source.issue_number:
            continue
        body = payload.get("body")
        if not isinstance(body, str) or _marker(body) not in _FORMAL_RESULT_MARKERS:
            continue
        bodies.append(body)
    return bodies[0] if len(bodies) == 1 else None


def _formal_body_for_worker(
    worker_result: WorkerActionResult,
    *,
    source: WorkerRequest,
) -> str | None:
    """Read a formal projection from effects or the rebuilt intent envelope."""

    body = _formal_result_body(worker_result, source=source)
    if body is not None:
        return body
    return (
        worker_result.result_content
        if _marker(worker_result.result_content) in _FORMAL_RESULT_MARKERS
        else None
    )


def _expected_formal_marker(source: WorkerRequest) -> str:
    if source.role == "reviewer":
        return "REVIEW_RESULT"
    if source.action.startswith("merge-"):
        return "MERGE_RESULT"
    return "ACTION_RESULT"


def _application_owned_worker_result(
    raw_worker_result: str,
    *,
    source: WorkerRequest,
    change: str | None = None,
    current_revision: str,
    result_revision: str | None = None,
    request_comment_id: int | None = None,
) -> str:
    """Require one application-owned formal result after worker effects."""

    if change is None:
        # Compatibility-only path for callers that predate the machine-owned
        # envelope.  Production application planning always supplies a fresh
        # Change from the repository preflight.
        change = parse_worker_result(raw_worker_result, source).change
    worker_result = parse_worker_result(
        raw_worker_result,
        source,
        authorized_change=change,
    )
    # Formal headers, routing, revisions, and successor text are application
    # protocol, not semantic-worker output.  Preserve only bounded semantic
    # evidence and rebuild the canonical result from fresh machine identity.
    semantic_content = worker_result.result_content
    if result_revision is None:
        candidate_revision = _field(semantic_content, "Revision")
        # Compatibility-only callers that predate machine-owned result
        # revision derivation may still supply a legacy formal body. Normal
        # application passes an explicitly fresh-derived revision below.
        result_revision = (
            candidate_revision
            if _SHA.fullmatch(candidate_revision or "") is not None
            else current_revision
        )
    elif _SHA.fullmatch(result_revision) is None:
        raise ValueError("application result revision is invalid")
    candidate_evidence = _field(semantic_content, "Evidence")
    evidence = " ".join((candidate_evidence or semantic_content).split())
    if not evidence:
        evidence = worker_result.typed_result.result.evidence_ref or "bounded typed result"
    expected_result = worker_result.typed_result.result.kind.value.upper().replace("-", "_")
    body_lines = [
        _expected_formal_marker(source),
        f"Workflow: #{source.issue_number}",
        f"Change: {change}",
        f"Role: {source.role}",
        f"Action: {source.action}",
        f"Result: {expected_result}",
        f"Revision: {result_revision}",
        f"Default-Branch-Revision: {current_revision}",
    ]
    first_activation = (
        source.role == "lead" and source.action == "propose-change" and change == "unset"
    )
    if request_comment_id is not None and not first_activation:
        body_lines.append(
            "Application-Correlation: "
            + formal_application_correlation(
                source,
                change=change,
                result_kind=worker_result.typed_result.result.kind.value,
                current_revision=current_revision,
                request_comment_id=request_comment_id,
            )
        )
    if not first_activation:
        try:
            successor = next_action(
                worker_result.typed_result.action,
                worker_result.typed_result.result,
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeError("worker result transition is invalid") from exc
        successor_text = "terminal"
        if successor is not None:
            successor_text = f"{role_for(successor).value.capitalize()} / {successor.value}"
        body_lines.append(f"Repository-derived successor: {successor_text}")
    body_lines.append(f"Evidence: {evidence}")
    body = "\n".join(body_lines)

    decoded = json.loads(raw_worker_result)
    if not isinstance(decoded, dict):
        raise RuntimeError("worker result must be a JSON object")
    requested = decoded.get("requested_effects", [])
    if not isinstance(requested, list):
        raise RuntimeError("worker result requested effects are invalid")

    ordered: list[object] = []
    for raw_effect in requested:
        if not isinstance(raw_effect, Mapping) or raw_effect.get("kind") != "issue-comment":
            ordered.append(raw_effect)
            continue
        payload_json = raw_effect.get("payload_json")
        if not isinstance(payload_json, str):
            ordered.append(raw_effect)
            continue
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            ordered.append(raw_effect)
            continue
        effect_body = payload.get("body") if isinstance(payload, Mapping) else None
        if isinstance(effect_body, str) and _marker(effect_body) in _FORMAL_RESULT_MARKERS:
            continue
        ordered.append(raw_effect)

    ordered.append(
        {
            "kind": "issue-comment",
            "payload_json": json.dumps(
                {"issue_number": source.issue_number, "body": body},
                sort_keys=True,
            ),
        }
    )
    # Carry the exact machine envelope forward once, after fresh application
    # authorization.  These fields are never sourced from the semantic worker.
    decoded["issue_number"] = source.issue_number
    decoded["role"] = source.role
    decoded["action"] = source.action
    decoded["change"] = change
    decoded["result_content"] = body
    decoded["requested_effects"] = ordered
    return json.dumps(decoded, sort_keys=True, separators=(",", ":"))


def _effect_payload(effect: Mapping[str, object]) -> Mapping[str, object] | None:
    payload = effect.get("payload_json")
    if not isinstance(payload, str):
        return None
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return cast(Mapping[str, object], decoded) if isinstance(decoded, Mapping) else None


def _effect_document(kind: str, payload: Mapping[str, object]) -> dict[str, str]:
    return {
        "kind": kind,
        "payload_json": json.dumps(dict(payload), sort_keys=True),
    }


def _fresh_issue(repository: str, token: str, issue_number: int) -> Mapping[str, object]:
    issue = _github_json(repository, token, f"issues/{issue_number}")
    if not isinstance(issue, Mapping):
        raise RuntimeError("fresh application Issue observation is unavailable")
    return issue


def _fresh_default_branch(repository: str, token: str) -> str:
    payload = _github_json(repository, token, "")
    branch = payload.get("default_branch") if isinstance(payload, Mapping) else None
    if not isinstance(branch, str) or not branch:
        raise RuntimeError("fresh application default branch is unavailable")
    return branch


def _fresh_pull_requests(
    repository: str,
    token: str,
    *,
    branch: str,
    default_branch: str,
) -> tuple[Mapping[str, object], ...]:
    owner = repository.split("/", 1)[0]
    query = (
        "pulls?state=all&head="
        + quote(f"{owner}:{branch}", safe="")
        + "&base="
        + quote(default_branch, safe="")
        + "&per_page=100"
    )
    payload = _github_json(repository, token, query)
    if not isinstance(payload, list):
        raise RuntimeError("fresh application pull-request enumeration is unavailable")
    candidates: list[Mapping[str, object]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            raise RuntimeError("fresh application pull-request enumeration is malformed")
        number = item.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            continue
        detail = _github_json(repository, token, f"pulls/{number}")
        if not isinstance(detail, Mapping):
            raise RuntimeError("fresh application pull-request observation is unavailable")
        candidates.append(detail)
    if len(candidates) > 1:
        raise RuntimeError("fresh application pull-request carrier is ambiguous")
    return tuple(candidates)


def _merge_carrier_action(source: WorkerRequest) -> str:
    """Map a consequence owner to the exact carrier lifecycle it observes."""

    if source.action == "finalize-archive":
        return "merge-archive-pr"
    if source.action in {"merge-implementation-pr", "merge-archive-pr"}:
        return source.action
    raise RuntimeError("fresh merge consequence has no legal carrier action")


def _merge_carrier_branch(source: WorkerRequest, change: str) -> str:
    action = _merge_carrier_action(source)
    branch = _archive_branch(change) if action == "merge-archive-pr" else _source_branch(change)
    if branch is None:
        raise RuntimeError("fresh merge consequence branch identity is invalid")
    return branch


def _fresh_merge_carrier(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    current_revision: str,
    default_branch: str,
    requested_number: int | None = None,
) -> Mapping[str, object]:
    """Read the one exact merge carrier from current repository state."""

    branch = _merge_carrier_branch(source, change)
    reviewed = None
    if source.action == "merge-implementation-pr":
        reviewed = current_reviewed_implementation_head(
            repository,
            token,
            source=source,
            change=change,
            current_revision=current_revision,
            read=_github_json,
        )
        if reviewed is None:
            raise RuntimeError("fresh merge consequence has no qualified review predecessor")
    candidates: tuple[Mapping[str, object], ...]
    if source.action == "merge-implementation-pr" and requested_number is not None:
        detail = _github_json(repository, token, f"pulls/{requested_number}")
        detail_head = detail.get("head") if isinstance(detail, Mapping) else None
        candidates = (
            (cast(Mapping[str, object], detail),)
            if isinstance(detail_head, Mapping)
            and reviewed is not None
            and detail_head.get("sha") == reviewed.head_sha
            else ()
        )
    elif source.action == "merge-implementation-pr":
        # Continuation carriers use a deterministic branch derived from the
        # already merged implementation history.  That branch is repository
        # state, not an immutable worker plan, so qualify every current
        # implementation carrier and retain exactly one open candidate (or
        # one historical merged candidate during recovery).
        summaries = _paged_github_list(
            repository,
            token,
            "pulls?state=all&base=" + quote(default_branch, safe=""),
        )
        qualified_open: list[Mapping[str, object]] = []
        qualified_merged: list[Mapping[str, object]] = []
        carrier_source = WorkerRequest(source.issue_number, "executor", source.action)
        for summary in summaries:
            number = summary.get("number")
            if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                continue
            # The independent PASS pins one immutable PR head.  List summaries
            # already expose that head; do not detail-fetch unrelated history.
            # A missing summary identity is indeterminate, never a reason to
            # skip a potentially relevant carrier.
            summary_head = summary.get("head")
            if (
                not isinstance(summary_head, Mapping)
                or not isinstance(summary_head.get("sha"), str)
                or _SHA.fullmatch(cast(str, summary_head["sha"])) is None
            ):
                raise RuntimeError("fresh implementation merge carrier summary is incomplete")
            if reviewed is None or summary_head["sha"] != reviewed.head_sha:
                continue
            detail = _github_json(repository, token, f"pulls/{number}")
            if not isinstance(detail, Mapping):
                raise RuntimeError("fresh implementation merge carrier is incomplete")
            detail_head = detail.get("head")
            if (
                not isinstance(detail_head, Mapping)
                or reviewed is None
                or detail_head.get("sha") != reviewed.head_sha
            ):
                continue
            decision = qualify_implementation_carrier(
                repository=repository,
                token=token,
                source=carrier_source,
                change=change,
                pr_number=number,
                current_revision=current_revision,
                read=_github_json,
            )
            if detail.get("state") == "open" and detail.get("merged") is not True:
                if decision.disposition == "QUALIFIED":
                    qualified_open.append(detail)
            elif decision.disposition == "HISTORICAL_MERGED":
                qualified_merged.append(detail)
        if len(qualified_open) > 1 or (qualified_open and qualified_merged):
            raise RuntimeError("fresh implementation merge carrier is ambiguous")
        candidates = tuple(qualified_open or qualified_merged)
    else:
        candidates = _fresh_pull_requests(
            repository,
            token,
            branch=branch,
            default_branch=default_branch,
        )
    if len(candidates) != 1:
        raise RuntimeError("fresh merge consequence carrier is missing or ambiguous")
    current = candidates[0]
    if (
        reviewed is not None
        and reviewed.merged_sha is not None
        and current.get("merge_commit_sha") != reviewed.merged_sha
    ):
        raise RuntimeError("fresh MERGED result is not bound to reviewed carrier merge commit")
    number = current.get("number")
    head = current.get("head")
    base = current.get("base")
    head_repo = head.get("repo") if isinstance(head, Mapping) else None
    base_repo = base.get("repo") if isinstance(base, Mapping) else None
    actual_branch = head.get("ref") if isinstance(head, Mapping) else None
    if (
        not isinstance(number, int)
        or isinstance(number, bool)
        or number <= 0
        or not isinstance(head, Mapping)
        or not isinstance(base, Mapping)
        or not isinstance(actual_branch, str)
        or (_merge_carrier_action(source) == "merge-archive-pr" and actual_branch != branch)
        or base.get("ref") != default_branch
        or not isinstance(head_repo, Mapping)
        or not isinstance(base_repo, Mapping)
        or head_repo.get("full_name") != repository
        or base_repo.get("full_name") != repository
        or not _references_issue(current.get("body"), source.issue_number)
    ):
        raise RuntimeError("fresh merge consequence carrier identity is invalid")
    if (
        _merge_carrier_action(source) == "merge-archive-pr"
        and current.get("title") != f"Archive OpenSpec change {change}"
    ):
        raise RuntimeError("fresh archive merge carrier title is invalid")
    return current


def _merged_carrier_is_in_current_default(
    repository: str,
    token: str,
    pull_request: Mapping[str, object],
    current_revision: str,
) -> bool:
    merge_commit = pull_request.get("merge_commit_sha")
    if not isinstance(merge_commit, str) or _SHA.fullmatch(merge_commit) is None:
        return False
    comparison = _github_json(
        repository,
        token,
        f"compare/{merge_commit}...{current_revision}",
    )
    base_commit = comparison.get("base_commit") if isinstance(comparison, Mapping) else None
    return bool(
        isinstance(comparison, Mapping)
        and comparison.get("status") in {"ahead", "identical"}
        and comparison.get("behind_by") == 0
        and isinstance(base_commit, Mapping)
        and base_commit.get("sha") == merge_commit
    )


def _fresh_merged_carrier_revision(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    current_revision: str,
    default_branch: str,
) -> str | None:
    """Return the fresh merge commit when the carrier has already merged."""

    try:
        current = _fresh_merge_carrier(
            repository=repository,
            token=token,
            source=source,
            change=change,
            current_revision=current_revision,
            default_branch=default_branch,
        )
    except RuntimeError:
        return None
    if current.get("merged") is not True or current.get("state") != "closed":
        return None
    merged_at = current.get("merged_at")
    merge_commit = current.get("merge_commit_sha")
    if (
        not isinstance(merged_at, str)
        or not merged_at.strip()
        or not isinstance(merge_commit, str)
        or _SHA.fullmatch(merge_commit) is None
    ):
        return None
    return merge_commit


def _fresh_archive_state(
    repository: str,
    token: str,
    *,
    issue_number: int,
    change: str,
    current_revision: str,
    default_branch: str,
) -> tuple[str, str | None, str | None]:
    """Return the current Archive consequence, including stale-source evidence."""

    branch = _archive_branch(change)
    if branch is None:
        raise RuntimeError("archive consequence branch identity is invalid")
    branch_sha = _fresh_branch_head(repository, token, branch)
    if branch_sha is None:
        return "missing-branch", branch, None
    provenance = archive_branch_source_status(
        repository=repository,
        token=token,
        change=change,
        source_sha=current_revision,
        branch_sha=branch_sha,
    )
    if provenance == "INDETERMINATE":
        return "indeterminate-branch", branch, branch_sha
    if provenance == "STALE":
        return "stale-branch", branch, branch_sha
    candidates = _fresh_pull_requests(
        repository,
        token,
        branch=branch,
        default_branch=default_branch,
    )
    if not candidates:
        return "missing-pr", branch, branch_sha
    pull_request = candidates[0]
    head = pull_request.get("head")
    base = pull_request.get("base")
    head_repo = head.get("repo") if isinstance(head, Mapping) else None
    base_repo = base.get("repo") if isinstance(base, Mapping) else None
    ready = (
        pull_request.get("state") == "open"
        and pull_request.get("merged") is not True
        and pull_request.get("draft") is False
        and isinstance(head, Mapping)
        and isinstance(base, Mapping)
        and head.get("ref") == branch
        and head.get("sha") == branch_sha
        and base.get("ref") == default_branch
        and isinstance(base.get("sha"), str)
        and _SHA.fullmatch(cast(str, base.get("sha"))) is not None
        and isinstance(head_repo, Mapping)
        and head_repo.get("full_name") == repository
    )
    if ready:
        ready = (
            isinstance(base, Mapping)
            and isinstance(base_repo, Mapping)
            and base_repo.get("full_name") == repository
            and pull_request.get("title") == f"Archive OpenSpec change {change}"
            and isinstance(pull_request.get("body"), str)
            and re.search(
                rf"(?mi)^\s*Refs\s+#{issue_number}\s*$",
                cast(str, pull_request["body"]),
            )
            is not None
        )
    return ("ready" if ready else "conflict"), branch, branch_sha


def _archive_pr_body(change: str, issue_number: int) -> str:
    return (
        f"Archive OpenSpec change `{change}`.\n\n"
        "This pull request is the repository-owned final archive snapshot. "
        "Its non-closing linkage preserves traceability while the coordination Issue remains open; "
        "independent Reviewer PASS, unchanged-head verification, current gates, and Lead terminal "
        "finalization remain required.\n\n"
        f"Refs #{issue_number}\n"
    )


def _archive_pr_create_payload(
    *,
    issue_number: int,
    change: str,
    branch: str,
    branch_sha: str,
    default_branch: str,
) -> dict[str, object]:
    return {
        "issue_number": issue_number,
        "operation": "pull-request-create",
        "title": f"Archive OpenSpec change {change}",
        "body": _archive_pr_body(change, issue_number),
        "head": branch,
        "base": default_branch,
        "draft": False,
        "expected_head_sha": branch_sha,
    }


def _fresh_workflow_dispatch_payload(
    *,
    issue_number: int,
    change: str,
    current_revision: str,
    default_branch: str,
) -> dict[str, object]:
    return {
        "issue_number": issue_number,
        "operation": "workflow-dispatch",
        "workflow_id": "openspec-archive.yml",
        "ref": default_branch,
        "inputs": {
            "change": change,
            "issue": str(issue_number),
            "revision": current_revision,
            "request_key": f"archive-{issue_number}-{current_revision}",
        },
    }


def _fresh_control_effect(
    *,
    raw_effect: Mapping[str, object],
    source: WorkerRequest,
    change: str,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
) -> Mapping[str, object] | None:
    """Rebind one control operation to current repository identity/state."""

    payload = _effect_payload(raw_effect)
    if payload is None or payload.get("issue_number") != source.issue_number:
        raise RuntimeError("application control effect payload is invalid")
    operation = payload.get("operation")
    if not isinstance(operation, str):
        raise RuntimeError("application control effect operation is invalid")
    if operation == "workflow-dispatch":
        derived = _fresh_workflow_dispatch_payload(
            issue_number=source.issue_number,
            change=change,
            current_revision=current_revision,
            default_branch=default_branch,
        )
        adapter = GitHubEffectAdapter(
            repository,
            token,
            source,
            authorized_change=change,
            current_revision=current_revision,
            expected_result_kind=None,
        )
        return None if adapter._existing_workflow_dispatch(derived) is not None else derived
    if operation == "application-materialize":
        # Materialization content/files are immutable semantic inputs.  The
        # current effect guard still rechecks repository identity and base
        # revision before the mutation.
        return payload
    if operation == "issue-label-add":
        issue = _fresh_issue(repository, token, source.issue_number)
        labels = issue.get("labels")
        names = (
            {
                item.get("name")
                for item in labels
                if isinstance(item, Mapping) and isinstance(item.get("name"), str)
            }
            if isinstance(labels, list)
            else set()
        )
        return (
            None
            if payload.get("label") in names
            else {
                "issue_number": source.issue_number,
                "operation": operation,
                "label": payload.get("label"),
            }
        )
    if operation == "issue-update":
        issue = _fresh_issue(repository, token, source.issue_number)
        fields = payload.get("fields")
        if not isinstance(fields, Mapping):
            raise RuntimeError("application issue-update fields are invalid")
        if all(issue.get(key) == value for key, value in fields.items()):
            return None
        return {
            "issue_number": source.issue_number,
            "operation": operation,
            "expected": {key: issue.get(key) for key in fields},
            "fields": dict(fields),
        }
    if operation == "pull-request-create":
        requested_head = payload.get("head")
        archive = source.action == "finalize-change" and (
            requested_head == _archive_branch(change) or requested_head is None
        )
        branch = _archive_branch(change) if archive else _source_branch(change)
        if branch is None:
            raise RuntimeError("application pull-request branch identity is invalid")
        branch_sha = _fresh_branch_head(repository, token, branch)
        if branch_sha is None:
            return None
        existing = _fresh_pull_requests(
            repository,
            token,
            branch=branch,
            default_branch=default_branch,
        )
        if existing:
            current = existing[0]
            current_head = current.get("head")
            current_base = current.get("base")
            if (
                current.get("state") == "open"
                and current.get("merged") is not True
                and current.get("draft") is False
                and isinstance(current_head, Mapping)
                and isinstance(current_base, Mapping)
                and current_head.get("sha") == branch_sha
                and current_base.get("sha") == current_revision
            ):
                return None
            raise RuntimeError("existing pull-request carrier is a material conflict")
        if archive:
            if not archive_branch_matches_current_source(
                repository=repository,
                token=token,
                change=change,
                source_sha=current_revision,
                branch_sha=branch_sha,
            ):
                raise RuntimeError("archive branch is not derived from current Change")
            return _archive_pr_create_payload(
                issue_number=source.issue_number,
                change=change,
                branch=branch,
                branch_sha=branch_sha,
                default_branch=default_branch,
            )
        title = payload.get("title")
        body = payload.get("body", f"Refs #{source.issue_number}")
        if not isinstance(title, str) or not title.strip() or not isinstance(body, str):
            raise RuntimeError("application pull-request content is invalid")
        return {
            "issue_number": source.issue_number,
            "operation": operation,
            "title": title,
            "body": body,
            "head": branch,
            "base": default_branch,
            "draft": payload.get("draft", False),
        }
    if operation in {
        "pull-request-update",
        "pull-request-ready",
        "pull-request-merge",
        "ref-delete",
    }:
        branch = (
            _archive_branch(change)
            if source.action in {"review-archive", "merge-archive-pr"}
            else _source_branch(change)
        )
        if branch is None:
            raise RuntimeError("application carrier branch identity is invalid")
        candidates: tuple[Mapping[str, object], ...]
        requested_number = payload.get("number")
        if (
            operation != "ref-delete"
            and isinstance(requested_number, int)
            and not isinstance(requested_number, bool)
            and requested_number > 0
        ):
            detail = _github_json(repository, token, f"pulls/{requested_number}")
            candidates = (detail,) if isinstance(detail, Mapping) else ()
        else:
            candidates = _fresh_pull_requests(
                repository,
                token,
                branch=branch,
                default_branch=default_branch,
            )
        if operation == "ref-delete":
            ref = (
                _archive_ref(change)
                if source.action == "merge-archive-pr"
                else f"refs/heads/{branch}"
            )
            head_sha = _fresh_branch_head(repository, token, branch)
            return (
                None
                if head_sha is None
                else {
                    "issue_number": source.issue_number,
                    "operation": operation,
                    "ref": ref,
                    "expected_sha": head_sha,
                }
            )
        if len(candidates) != 1:
            raise RuntimeError("application carrier is missing or ambiguous")
        current = candidates[0]
        number = current.get("number")
        head = current.get("head")
        if not isinstance(number, int) or not isinstance(head, Mapping):
            raise RuntimeError("application carrier identity is incomplete")
        head_sha = head.get("sha")
        if not isinstance(head_sha, str) or _SHA.fullmatch(head_sha) is None:
            raise RuntimeError("application carrier head is incomplete")
        if operation == "pull-request-update":
            fields = payload.get("fields")
            if not isinstance(fields, Mapping):
                raise RuntimeError("application pull-request-update fields are invalid")
            if fields == {"state": "closed"} and payload.get("expected_head_sha") != head_sha:
                # A retirement is an irreversible effect, not a rebinding of
                # a stale request to whichever HEAD happens to exist now.
                raise RuntimeError("application retirement expected HEAD is stale")
            return {
                "issue_number": source.issue_number,
                "operation": operation,
                "number": number,
                "expected_head_sha": head_sha,
                "fields": dict(fields),
            }
        if operation == "pull-request-ready":
            if current.get("draft") is False:
                return None
            return {
                "issue_number": source.issue_number,
                "operation": operation,
                "number": number,
                "expected_head_sha": head_sha,
            }
        return {
            "issue_number": source.issue_number,
            "operation": operation,
            "number": number,
            "expected_head_sha": head_sha,
            "merge_method": payload.get("merge_method", "merge"),
            **(
                {
                    "commit_title": payload["commit_title"],
                    "commit_message": payload["commit_message"],
                }
                if "commit_title" in payload and "commit_message" in payload
                else {}
            ),
        }
    raise RuntimeError(f"unsupported application control operation: {operation}")


def _fresh_merge_consequence_effect(
    *,
    source: WorkerRequest,
    change: str,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    requested_number: int | None = None,
) -> dict[str, str] | None:
    """Derive the next missing merge consequence from fresh carrier state."""

    current = _fresh_merge_carrier(
        repository=repository,
        token=token,
        source=source,
        change=change,
        current_revision=current_revision,
        default_branch=default_branch,
        requested_number=requested_number,
    )
    head = current.get("head")
    expected_head_sha = head.get("sha") if isinstance(head, Mapping) else None
    if not isinstance(expected_head_sha, str) or _SHA.fullmatch(expected_head_sha) is None:
        raise RuntimeError("fresh merge consequence carrier head is invalid")

    if current.get("state") == "open" and current.get("merged") is not True:
        candidate = _effect_document(
            GITHUB_MUTATION_KIND,
            {
                "issue_number": source.issue_number,
                "operation": "pull-request-merge",
                "number": current["number"],
                "merge_method": "merge",
            },
        )
        fresh = _fresh_control_effect(
            raw_effect=candidate,
            source=source,
            change=change,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
        )
        return None if fresh is None else _effect_document(GITHUB_MUTATION_KIND, fresh)

    if current.get("state") != "closed" or current.get("merged") is not True:
        raise RuntimeError("fresh merge consequence carrier is closed without a merge")
    merged_at = current.get("merged_at")
    merge_commit = current.get("merge_commit_sha")
    merged_in_default = _merged_carrier_is_in_current_default(
        repository,
        token,
        current,
        current_revision,
    )
    if (
        not isinstance(merged_at, str)
        or not merged_at.strip()
        or not isinstance(merge_commit, str)
        or _SHA.fullmatch(merge_commit) is None
        or not merged_in_default
    ):
        if requested_number is not None:
            # A legacy envelope may still carry the old carrier identity as
            # migration evidence.  Let the existing merge-acceptance gate
            # reject a stale historical proof; never turn that evidence into
            # a formal result here.
            candidate = _effect_document(
                GITHUB_MUTATION_KIND,
                {
                    "issue_number": source.issue_number,
                    "operation": "pull-request-merge",
                    "number": current["number"],
                    "merge_method": "merge",
                },
            )
            fresh = _fresh_control_effect(
                raw_effect=candidate,
                source=source,
                change=change,
                repository=repository,
                token=token,
                current_revision=current_revision,
                default_branch=default_branch,
            )
            return None if fresh is None else _effect_document(GITHUB_MUTATION_KIND, fresh)
        raise RuntimeError("merged carrier is not yet in the current default branch")

    # A merged carrier's ref is a separate repository consequence.  Derive
    # only that cleanup when it is still present, after proving the merge
    # itself.  The carrier guard re-proves the same historical merge before
    # deleting the exact ref.
    actual_head = current.get("head")
    actual_branch = actual_head.get("ref") if isinstance(actual_head, Mapping) else None
    if not isinstance(actual_branch, str) or not actual_branch:
        raise RuntimeError("merged carrier branch identity is incomplete")
    branch = actual_branch
    branch_sha = _fresh_branch_head(repository, token, branch)
    if branch_sha is not None:
        if branch_sha != expected_head_sha:
            raise RuntimeError("merged carrier ref changed after merge")
        candidate = _effect_document(
            GITHUB_MUTATION_KIND,
            {
                "issue_number": source.issue_number,
                "operation": "ref-delete",
                "ref": f"refs/heads/{branch}",
            },
        )
        if source.action == "merge-implementation-pr" and branch != _source_branch(change):
            fresh = {
                "issue_number": source.issue_number,
                "operation": "ref-delete",
                "ref": f"refs/heads/{branch}",
                "expected_sha": branch_sha,
            }
        else:
            fresh = _fresh_control_effect(
                raw_effect=candidate,
                source=source,
                change=change,
                repository=repository,
                token=token,
                current_revision=current_revision,
                default_branch=default_branch,
            )
        return None if fresh is None else _effect_document(GITHUB_MUTATION_KIND, fresh)
    return None


def _fresh_application_worker_result(
    raw_worker_result: str,
    *,
    source: WorkerRequest,
    change: str,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    request_comment_id: int,
) -> str:
    """Reconcile fresh repository consequences from immutable semantic input."""

    try:
        result_revision = _machine_result_revision(
            raw_worker_result,
            source,
            change=change,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
        )
    except RuntimeError:
        # Materialization is an interruptible repository consequence.  Before
        # its exact validation target is observed, the formal result remains
        # pending and is not eligible for commit; keep the fresh default
        # revision as a temporary envelope binding.
        if not _materialization_effects(raw_worker_result, source, change=change):
            raise
        result_revision = current_revision
    semantic_worker = parse_worker_result(
        raw_worker_result,
        source,
        authorized_change=change,
    )
    application_raw = _application_owned_worker_result(
        raw_worker_result,
        source=source,
        change=change,
        current_revision=current_revision,
        result_revision=result_revision,
        request_comment_id=request_comment_id,
    )
    decoded = json.loads(application_raw)
    if not isinstance(decoded, dict):
        raise RuntimeError("application worker result is not an object")
    worker = parse_worker_result(application_raw, source, authorized_change=change)
    semantic_effects: list[dict[str, str]] = []
    control_candidates = [
        {
            "kind": requested.kind,
            "payload_json": requested.payload_json,
        }
        for requested in worker.requested_effects
    ]
    legacy_merge_number: int | None = None
    for candidate in control_candidates:
        payload = _effect_payload(candidate)
        candidate_number = None if payload is None else payload.get("number")
        if (
            payload is not None
            and payload.get("operation") == "pull-request-merge"
            and isinstance(candidate_number, int)
            and not isinstance(candidate_number, bool)
            and candidate_number > 0
        ):
            legacy_merge_number = candidate_number
            break
    is_archive_completion = (
        source.action == "finalize-change"
        and worker.typed_result.result.kind.value == "archive-ready"
    )
    if is_archive_completion:
        state, branch, branch_sha = _fresh_archive_state(
            repository,
            token,
            issue_number=source.issue_number,
            change=change,
            current_revision=current_revision,
            default_branch=default_branch,
        )
        if state in {"missing-branch", "stale-branch"}:
            semantic_effects.append(
                _effect_document(
                    GITHUB_MUTATION_KIND,
                    _fresh_workflow_dispatch_payload(
                        issue_number=source.issue_number,
                        change=change,
                        current_revision=current_revision,
                        default_branch=default_branch,
                    ),
                )
            )
        elif state == "missing-pr":
            if branch is None or branch_sha is None:
                raise RuntimeError("archive consequence branch observation is incomplete")
            semantic_effects.append(
                _effect_document(
                    GITHUB_MUTATION_KIND,
                    _archive_pr_create_payload(
                        issue_number=source.issue_number,
                        change=change,
                        branch=branch,
                        branch_sha=branch_sha,
                        default_branch=default_branch,
                    ),
                )
            )
        elif state in {"conflict", "indeterminate-branch"}:
            raise RuntimeError("archive pull-request/source consequence is indeterminate")
        else:
            semantic_effects.extend(
                _fresh_non_control_effects(
                    control_candidates,
                    source=source,
                    change=change,
                    repository=repository,
                    token=token,
                    current_revision=current_revision,
                    default_branch=default_branch,
                    skip_operations={"workflow-dispatch", "pull-request-create"},
                )
            )
            formal = _formal_body_for_worker(
                worker,
                source=source,
            )
            if formal is None:
                raise RuntimeError("application formal result evidence is missing")
            semantic_effects.append(
                _effect_document(
                    "issue-comment",
                    {"issue_number": source.issue_number, "body": formal},
                )
            )
    elif (
        source.action in {"merge-implementation-pr", "merge-archive-pr"}
        and worker.typed_result.result.kind.value == "merged"
    ):
        semantic_effects.extend(
            _fresh_non_control_effects(
                control_candidates,
                source=source,
                change=change,
                repository=repository,
                token=token,
                current_revision=current_revision,
                default_branch=default_branch,
                skip_operations={"pull-request-merge", "ref-delete"},
            )
        )
        merge_effect = _fresh_merge_consequence_effect(
            source=source,
            change=change,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
            requested_number=cast(int | None, legacy_merge_number),
        )
        if merge_effect is not None:
            semantic_effects.append(merge_effect)
            # During cutover, a legacy envelope may still carry the old PR
            # number.  Keep its idempotent merge effect in the batch so the
            # existing mutation-adjacent merge gate decides whether the
            # historical carrier is currently acceptable.  Only after that
            # gate can its legacy formal projection be applied.
            if legacy_merge_number is not None:
                legacy_carrier = _github_json(
                    repository,
                    token,
                    f"pulls/{legacy_merge_number}",
                )
                if (
                    isinstance(legacy_carrier, Mapping)
                    and legacy_carrier.get("state") == "closed"
                    and legacy_carrier.get("merged") is True
                ):
                    formal = _formal_body_for_worker(worker, source=source)
                    if formal is None:
                        raise RuntimeError("application formal result evidence is missing")
                    semantic_effects.append(
                        _effect_document(
                            "issue-comment",
                            {"issue_number": source.issue_number, "body": formal},
                        )
                    )
        else:
            formal = _formal_body_for_worker(worker, source=source)
            if formal is None:
                raise RuntimeError("application formal result evidence is missing")
            semantic_effects.append(
                _effect_document(
                    "issue-comment",
                    {"issue_number": source.issue_number, "body": formal},
                )
            )
    else:
        semantic_effects.extend(
            _fresh_non_control_effects(
                control_candidates,
                source=source,
                change=change,
                repository=repository,
                token=token,
                current_revision=current_revision,
                default_branch=default_branch,
                skip_operations=set(),
            )
        )
        if (
            source.action == "finalize-archive"
            and worker.typed_result.result.kind.value == "lifecycle-complete"
            and not merged_pr_readiness_complete(
                repository=repository,
                token=token,
                issue_number=source.issue_number,
                action=source.action,
                change=change,
                current_revision=current_revision,
            )
        ):
            raise RuntimeError("final archive consequence is not successor-ready")
        formal = _formal_body_for_worker(worker, source=source)
        if formal is None:
            raise RuntimeError("application formal result evidence is missing")
        semantic_effects.append(
            _effect_document("issue-comment", {"issue_number": source.issue_number, "body": formal})
        )
    decoded["requested_effects"] = semantic_effects
    # The accepted intent retains semantic evidence.  The formal body built
    # above is an invocation-local projection and is rebuilt on every wake.
    decoded["result_content"] = semantic_worker.result_content
    decoded["_semantic_intent_version"] = 2
    return json.dumps(decoded, sort_keys=True, separators=(",", ":"))


def _fresh_non_control_effects(
    candidates: Sequence[Mapping[str, object]],
    *,
    source: WorkerRequest,
    change: str,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    skip_operations: set[str],
) -> list[dict[str, str]]:
    effects: list[dict[str, str]] = []
    for candidate in candidates:
        kind = candidate.get("kind")
        if kind == "issue-comment":
            payload = _effect_payload(candidate)
            if payload is None:
                raise RuntimeError("application evidence comment payload is invalid")
            body = payload.get("body")
            if not isinstance(body, str):
                raise RuntimeError("application evidence comment body is invalid")
            marker = _marker(body)
            if marker in _FORMAL_RESULT_MARKERS:
                continue
            effects.append(_effect_document("issue-comment", payload))
            continue
        if kind != GITHUB_MUTATION_KIND:
            raise RuntimeError("application consequence effect kind is invalid")
        payload = _effect_payload(candidate)
        if payload is None:
            raise RuntimeError("application consequence control payload is invalid")
        operation = payload.get("operation")
        if operation in skip_operations:
            continue
        fresh = _fresh_control_effect(
            raw_effect=candidate,
            source=source,
            change=change,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
        )
        if fresh is not None:
            effects.append(_effect_document(GITHUB_MUTATION_KIND, fresh))
    return effects


def _rebind_application_result_revision(
    raw_worker_result: str, revision: str, *, rebind_checkpoint: bool = True
) -> str:
    """Bind deferred checkpoint/formal evidence to a proven materialized head."""

    if _SHA.fullmatch(revision) is None:
        raise ValueError("application result revision is invalid")
    decoded = json.loads(raw_worker_result)
    if not isinstance(decoded, dict):
        raise ValueError("application worker result must be a JSON object")
    requested = decoded.get("requested_effects", [])
    if not isinstance(requested, list):
        raise ValueError("application worker result requested effects are invalid")
    rebound = False
    updated_requested: list[object] = []
    for raw_effect in requested:
        if not isinstance(raw_effect, Mapping) or raw_effect.get("kind") != "issue-comment":
            updated_requested.append(raw_effect)
            continue
        payload_json = raw_effect.get("payload_json")
        if not isinstance(payload_json, str):
            updated_requested.append(raw_effect)
            continue
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            updated_requested.append(raw_effect)
            continue
        body = payload.get("body") if isinstance(payload, Mapping) else None
        if not isinstance(body, str) or _marker(body) not in (
            _FORMAL_RESULT_MARKERS | {"SLICE_CHECKPOINT"}
        ):
            updated_requested.append(raw_effect)
            continue
        if _marker(body) == "SLICE_CHECKPOINT" and not rebind_checkpoint:
            updated_requested.append(raw_effect)
            continue
        lines = body.splitlines()
        revision_indexes = [
            index for index, line in enumerate(lines) if line.startswith("Revision:")
        ]
        if len(revision_indexes) != 1:
            raise ValueError("application formal result revision is ambiguous")
        lines[revision_indexes[0]] = f"Revision: {revision}"
        updated_body = "\n".join(lines) + ("\n" if body.endswith("\n") else "")
        updated_payload = dict(payload)
        updated_payload["body"] = updated_body
        updated_effect = dict(raw_effect)
        updated_effect["payload_json"] = json.dumps(updated_payload, sort_keys=True)
        updated_requested.append(updated_effect)
        if _marker(body) in _FORMAL_RESULT_MARKERS:
            decoded["result_content"] = updated_body
        rebound = True
    if rebound:
        decoded["requested_effects"] = updated_requested
    return json.dumps(decoded, sort_keys=True, separators=(",", ":"))


def _qualified_committed_implementation_result(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    worker_result: WorkerActionResult,
    change: str,
    current_revision: str,
    request_comment_id: int,
) -> tuple[str, str, tuple[str, str]] | None:
    """Reuse the canonical formal frontier before treating ACCEPT as committed.

    ACCEPT alone cannot settle an implementation. Only its exact Actions
    ACTION_RESULT, still qualified as the current successor, ends the
    historical materialization write boundary. Return revision, correlation,
    and successor for the already committed consequence.
    """
    if source.role != "executor" or source.action != "implement-change":
        return None
    successor = next_action(worker_result.typed_result.action, worker_result.typed_result.result)
    if successor is None:
        return None
    successor_routing = (role_for(successor).value, successor.value)
    issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != source.issue_number
        or observation.state != "open"
        or observation.change != change
        or observation.routing != successor_routing
    ):
        return None
    comments = _paged_github_list(
        repository, token, f"issues/{source.issue_number}/comments?sort=created"
    )
    lifecycle = _paged_github_list(repository, token, f"issues/{source.issue_number}/timeline")
    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=change,
        state=observation.state,
        current_routing=observation.routing,
        comments=comments,
        lifecycle_events=lifecycle,
        current_revision=current_revision,
        mode="current",
        expected_routing=successor_routing,
    )
    if not qualification.events:
        return None
    latest = qualification.events[-1]
    if latest.default_branch_revision is None:
        return None
    if latest.default_branch_revision != current_revision:
        if not _authorization_revision_is_ancestor(
            repository, token, latest.default_branch_revision, current_revision
        ):
            return None
        qualification = replace(
            qualification,
            authorization_ancestry=((latest.default_branch_revision, current_revision),),
        )
    decision = qualify_current_formal_consequence(qualification)
    event = decision.event
    if (
        not decision.qualified
        or not isinstance(event, FormalLifecycleEvent)
        or not event.valid
        or event.issue_number != source.issue_number
        or event.change != change
        or (event.role, event.action) != (source.role, source.action)
        or event.result_kind != worker_result.typed_result.result.kind.value
        or event.successor != successor_routing
        or event.revision is None
        or event.application_correlation is None
    ):
        return None
    original = [
        comment
        for comment in comments
        if comment.get("id") == event.comment_id
        and parse_formal_result(comment, current_revision=current_revision) == event
    ]
    if len(original) != 1:
        # A synthetic checkpoint frontier is not a committed ACTION_RESULT.
        return None
    expected_correlation = formal_application_correlation(
        source,
        change=change,
        result_kind=event.result_kind,
        current_revision=event.application_correlation.rsplit(":", 1)[-1],
        request_comment_id=request_comment_id,
    )
    if event.application_correlation != expected_correlation:
        return None
    return event.revision, event.application_correlation, successor_routing


def _accepted_checkpoint_already_durable(
    raw_worker_result: str,
    *,
    source: WorkerRequest,
    repository: str,
    token: str,
    current_revision: str,
    request_comment_id: int,
) -> bool:
    """Use the canonical trusted comment observer before altering a checkpoint.

    A partial accepted invocation may have written its old, exact checkpoint
    but lost the formal-result response. Rebinding that durable comment to a
    later carrier head would create a duplicate. The existing trusted comment
    is reconciled read-only; only a genuinely absent checkpoint may be bound
    to the newly proven head.
    """
    parsed = parse_worker_result(raw_worker_result, source)
    checkpoints = [
        StagedEffect(effect.kind, effect.payload_json)
        for effect in parsed.requested_effects
        if effect.kind == "issue-comment"
        and isinstance((payload := _effect_payload({"payload_json": effect.payload_json})), Mapping)
        and isinstance(payload.get("body"), str)
        and _marker(cast(str, payload["body"])) == "SLICE_CHECKPOINT"
    ]
    if not checkpoints:
        # A non-completion ACCEPTED result has no checkpoint obligation.
        # Its original Effect remains separately qualified and read-only.
        return False
    if len(checkpoints) != 1:
        raise RuntimeError("accepted implementation checkpoint identity is incomplete")
    adapter = GitHubEffectAdapter(
        repository,
        token,
        source,
        authorized_change=parsed.change,
        current_revision=current_revision,
        expected_result_kind=parsed.typed_result.result.kind.value,
        request_comment_id=request_comment_id,
        accepted_intent=True,
    )
    return adapter.observe_postcondition(checkpoints[0])


def _activation_result_body(
    worker_result: WorkerActionResult,
    *,
    source: WorkerRequest,
    change: str,
    result_revision: str,
    current_revision: str,
    request_comment_id: int,
) -> tuple[str, str, tuple[str, str]]:
    """Bind preactivation semantic output to application-owned formal identity."""

    if source != WorkerRequest(source.issue_number, "lead", "propose-change"):
        raise RuntimeError("first activation requires Lead / propose-change")
    if (
        worker_result.change != "unset"
        or worker_result.typed_result.result.kind.value != _FIRST_ACTIVATION_RESULT
    ):
        raise RuntimeError("first activation worker result is not activation-ready")
    successor = next_action(worker_result.typed_result.action, worker_result.typed_result.result)
    if successor is None:
        raise RuntimeError("first activation result has no formal successor")
    successor_routing = (role_for(successor).value, successor.value)
    if successor_routing != ("reviewer", "review-openspec"):
        raise RuntimeError("first activation successor is not review-openspec")

    body = worker_result.result_content
    expected_result = worker_result.typed_result.result.kind.value.upper().replace("-", "_")
    if (
        _marker(body) != "ACTION_RESULT"
        or _field(body, "Workflow") != f"#{source.issue_number}"
        or _field(body, "Change") != "unset"
        or _field(body, "Action") != source.action
        or _field(body, "Role") != source.role
        or _field(body, "Result") != expected_result
        or _field(body, "Default-Branch-Revision") != current_revision
        or _SHA.fullmatch(_field(body, "Revision") or "") is None
        or len(_field_values(body, "Application-Correlation")) > 0
        or len(_field_values(body, "Repository-derived successor")) > 0
    ):
        raise RuntimeError("first activation result_content is not a bounded canonical result")

    updated, count = _CHANGE_LINE.subn(f"Change: {change}", body, count=1)
    if count != 1:
        raise RuntimeError("first activation result Change binding is ambiguous")
    if _SHA.fullmatch(result_revision) is None:
        raise RuntimeError("first activation result revision is invalid")
    updated, count = re.subn(
        r"(?m)^Revision:\s*[0-9a-f]{40}\s*$",
        f"Revision: {result_revision}",
        updated,
        count=1,
    )
    if count != 1:
        raise RuntimeError("first activation result revision binding is ambiguous")
    correlation = formal_application_correlation(
        source,
        change=change,
        result_kind=worker_result.typed_result.result.kind.value,
        current_revision=current_revision,
        request_comment_id=request_comment_id,
    )
    lines = updated.splitlines()
    anchors = [
        index
        for index, line in enumerate(lines)
        if line.startswith(("Revision:", "Default-Branch-Revision:"))
    ]
    if not anchors:
        raise RuntimeError("first activation result has no revision anchor")
    insert_at = max(anchors) + 1
    lines[insert_at:insert_at] = [
        f"Application-Correlation: {correlation}",
        "Repository-derived successor: Reviewer / review-openspec",
    ]
    suffix = "\n" if body.endswith("\n") else ""
    return "\n".join(lines) + suffix, correlation, successor_routing


def _fresh_preactivation_source(
    repository: str,
    token: str,
    source: WorkerRequest,
) -> None:
    preflight = acquire_current_github_preflight(repository, token)
    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id != source.issue_number
        or decision.selected_routing != (source.role, source.action)
    ):
        raise RuntimeError("first activation source is no longer current")
    matching = tuple(item for item in preflight.issues if item.issue_number == source.issue_number)
    if (
        len(matching) != 1
        or matching[0].state != "open"
        or matching[0].change != "unset"
        or matching[0].routing != (source.role, source.action)
    ):
        raise RuntimeError("first activation source identity is no longer preactivation")


def _persist_activation_result(
    body: str,
    *,
    repository: str,
    token: str,
    issue_number: int,
) -> int:
    comments = _paged_github_list(repository, token, f"issues/{issue_number}/comments?sort=created")
    matches = tuple(
        comment
        for comment in comments
        if comment.get("body") == body and is_github_actions_comment(comment)
    )
    if len(matches) > 1:
        raise RuntimeError("first activation has duplicate application result evidence")
    if len(matches) == 1:
        comment_id = _positive_int(matches[0].get("id"))
        if comment_id is None:
            raise RuntimeError("first activation result comment id is invalid")
        return comment_id

    response = _as_mapping(
        _github_json(
            repository,
            token,
            f"issues/{issue_number}/comments",
            method="POST",
            payload={"body": body},
        )
    )
    comment_id = None if response is None else _positive_int(response.get("id"))
    if (
        response is None
        or comment_id is None
        or response.get("body") != body
        or not is_github_actions_comment(response)
    ):
        raise RuntimeError("first activation result postcondition was not observed")
    observed = _as_mapping(_github_json(repository, token, f"issues/comments/{comment_id}"))
    if (
        observed is None
        or observed.get("id") != comment_id
        or observed.get("body") != body
        or not is_github_actions_comment(observed)
    ):
        raise RuntimeError("first activation result fresh postcondition was not observed")
    return comment_id


def _formal_qualification(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    current_revision: str,
    expected_result_kind: str,
    expected_application_correlation: str,
    current_routing: tuple[str, str],
    expected_routing: tuple[str, str] | None,
    mode: Literal["current", "pending"],
) -> bool:
    issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != source.issue_number
        or observation.state != "open"
        or observation.routing != current_routing
    ):
        return False
    comments = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created",
    )
    lifecycle = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/timeline",
    )
    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=change,
        state=observation.state,
        current_routing=observation.routing,
        comments=comments,
        current_revision=current_revision,
        mode=mode,
        expected_routing=expected_routing,
        expected_terminal=False,
        source_routing=(source.role, source.action) if mode == "pending" else None,
        expected_result_kind=expected_result_kind if mode == "pending" else None,
        expected_application_correlation=(
            expected_application_correlation if mode == "pending" else None
        ),
        lifecycle_events=lifecycle,
    )
    return qualify_current_formal_consequence(qualification).qualified


def _issue_label_names(issue: Mapping[str, object]) -> list[str]:
    raw_labels = issue.get("labels")
    if not isinstance(raw_labels, list):
        raise RuntimeError("first activation Issue labels are incomplete")
    names: list[str] = []
    for item in raw_labels:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str):
            raise RuntimeError("first activation Issue label identity is incomplete")
        names.append(cast(str, item["name"]))
    return names


def _existing_activation_correlation(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    result_revision: str,
    current_revision: str,
    result_kind: str,
    successor_routing: tuple[str, str],
) -> str | None:
    """Reuse one exact pending result instead of replaying semantic work."""

    comments = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created",
    )
    matching: list[str] = []
    for comment in comments:
        event = parse_formal_result(comment, current_revision=current_revision)
        if (
            event is None
            or not event.valid
            or event.issue_number != source.issue_number
            or event.change != change
            or (event.role, event.action) != (source.role, source.action)
            or event.result_kind != result_kind
            or event.revision != result_revision
            or event.default_branch_revision != current_revision
            or event.successor != successor_routing
            or event.terminal
            or event.application_correlation is None
        ):
            continue
        matching.append(event.application_correlation)
    if len(matching) > 1:
        raise RuntimeError("first activation has ambiguous exact pending result evidence")
    if not matching:
        return None
    correlation = matching[0]
    if not _formal_qualification(
        repository=repository,
        token=token,
        source=source,
        change=change,
        current_revision=current_revision,
        expected_result_kind=result_kind,
        expected_application_correlation=correlation,
        current_routing=(source.role, source.action),
        expected_routing=successor_routing,
        mode="pending",
    ):
        raise RuntimeError(
            "existing first activation result is no longer a valid pending consequence"
        )
    return correlation


def _complete_first_activation(
    *,
    raw_worker_result: str,
    materialization: Mapping[str, object],
    target: ValidationResourceTarget,
    source: WorkerRequest,
    repository: str,
    token: str,
    current_revision: str,
    accepted_authorization_revision: str,
    default_branch: str,
    request_comment_id: int,
    allow_pending_continuation: bool = False,
) -> None:
    """Persist result first, then atomically promote Change and successor routing."""

    worker_result = parse_worker_result(raw_worker_result, source)
    body, proposed_correlation, successor_routing = _activation_result_body(
        worker_result,
        source=source,
        change=target.change,
        result_revision=target.revision,
        current_revision=current_revision,
        request_comment_id=request_comment_id,
    )
    _fresh_preactivation_source(repository, token, source)
    correlation = _existing_activation_correlation(
        repository=repository,
        token=token,
        source=source,
        change=target.change,
        result_revision=target.revision,
        current_revision=current_revision,
        result_kind=worker_result.typed_result.result.kind.value,
        successor_routing=successor_routing,
    )
    if correlation is None:
        _persist_activation_result(
            body,
            repository=repository,
            token=token,
            issue_number=source.issue_number,
        )
        correlation = proposed_correlation
    _fresh_preactivation_source(repository, token, source)

    if not _formal_qualification(
        repository=repository,
        token=token,
        source=source,
        change=target.change,
        current_revision=current_revision,
        expected_result_kind=worker_result.typed_result.result.kind.value,
        expected_application_correlation=correlation,
        current_routing=(source.role, source.action),
        expected_routing=successor_routing,
        mode="pending",
    ):
        raise RuntimeError("first activation pending formal consequence is not qualified")

    fresh_target = observe_materialization_target(
        materialization,
        source,
        repository=repository,
        token=token,
        current_revision=current_revision,
        default_branch=default_branch,
        accepted_authorization_revision=accepted_authorization_revision,
        allow_pending_continuation=allow_pending_continuation,
    )
    if fresh_target != target:
        raise RuntimeError("first activation validation target changed before promotion")
    issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    observation = None if issue is None else normalize_github_issue(issue)
    issue_body = None if issue is None else issue.get("body")
    if (
        issue is None
        or observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.change != "unset"
        or observation.routing != (source.role, source.action)
        or not isinstance(issue_body, str)
        or _CHANGE_LINE.findall(issue_body) != ["unset"]
    ):
        raise RuntimeError("first activation source changed before atomic promotion")

    updated_body, count = _CHANGE_LINE.subn(
        f"Change: {target.change}",
        issue_body,
        count=1,
    )
    if count != 1:
        raise RuntimeError("first activation Change update is ambiguous")
    labels = [
        name for name in _issue_label_names(issue) if not name.startswith(_ROUTING_LABEL_PREFIXES)
    ]
    labels.append(f"action:{successor_routing[1]}")
    _github_json(
        repository,
        token,
        f"issues/{source.issue_number}",
        method="PATCH",
        payload={"body": updated_body, "labels": labels},
    )

    for attempt in range(_ACTIVATION_OBSERVATION_ATTEMPTS):
        final = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
        final_observation = None if final is None else normalize_github_issue(final)
        state_matches = bool(
            final_observation is not None
            and final_observation.authoritative
            and final_observation.state == "open"
            and final_observation.change == target.change
            and final_observation.routing == successor_routing
            and not final_observation.routing_debt
        )
        if state_matches and _formal_qualification(
            repository=repository,
            token=token,
            source=source,
            change=target.change,
            current_revision=current_revision,
            expected_result_kind=worker_result.typed_result.result.kind.value,
            expected_application_correlation=correlation,
            current_routing=successor_routing,
            expected_routing=None,
            mode="current",
        ):
            return
        if attempt + 1 < _ACTIVATION_OBSERVATION_ATTEMPTS:
            time.sleep(_ACTIVATION_OBSERVATION_DELAY_SECONDS)
    raise RuntimeError("first activation current formal postcondition was not qualified")


def _recovery_body(
    *,
    source: WorkerRequest,
    change: str,
    current_revision: str,
    failed_authorization_revision: str,
    request_comment_id: int,
) -> str:
    return "\n".join(
        (
            _RECOVERY_MARKER,
            f"Workflow: #{source.issue_number}",
            f"Change: {change}",
            "Source: Lead / propose-change",
            "Target: Lead / resolve-question",
            f"Default-Branch-Revision: {current_revision}",
            f"Failed-Authorization-Revision: {failed_authorization_revision}",
            f"Request-Comment-ID: {request_comment_id}",
            f"Reason: {_RECOVERY_REASON}",
        )
    )


def _authorization_revision_is_ancestor(
    repository: str,
    token: str,
    failed_revision: str,
    current_revision: str,
) -> bool:
    if failed_revision == current_revision:
        return False
    comparison = _as_mapping(
        _github_json(repository, token, f"compare/{failed_revision}...{current_revision}")
    )
    base_commit = None if comparison is None else _as_mapping(comparison.get("base_commit"))
    return bool(
        comparison is not None
        and comparison.get("status") == "ahead"
        and base_commit is not None
        and base_commit.get("sha") == failed_revision
    )


def _partial_activation_carrier_matches(
    materialization: Mapping[str, object],
    source: WorkerRequest,
    *,
    repository: str,
    token: str,
    failed_revision: str,
    default_branch: str,
) -> bool:
    request = find_materialization_payload(materialization, source)
    if (
        request is None
        or request.expected_change != "unset"
        or request.base_sha != failed_revision
        or request.change in {"", "unset"}
        or any(file.expected_sha is not None for file in request.files)
    ):
        return False
    ref = _as_mapping(
        _github_json(
            repository,
            token,
            f"git/ref/heads/{request.branch}",
        )
    )
    ref_object = None if ref is None else _as_mapping(ref.get("object"))
    head_sha = None if ref_object is None else ref_object.get("sha")
    if not isinstance(head_sha, str) or _SHA.fullmatch(head_sha) is None:
        return False

    commit = _as_mapping(_github_json(repository, token, f"git/commits/{head_sha}"))
    raw_parents = None if commit is None else commit.get("parents")
    if (
        commit is None
        or commit.get("message") != request.message
        or not isinstance(raw_parents, list)
        or len(raw_parents) != 1
    ):
        return False
    parent = _as_mapping(raw_parents[0])
    tree = _as_mapping(commit.get("tree"))
    tree_sha = None if tree is None else tree.get("sha")
    if parent is None or parent.get("sha") != failed_revision or not isinstance(tree_sha, str):
        return False

    tree_payload = _as_mapping(_github_json(repository, token, f"git/trees/{tree_sha}?recursive=1"))
    raw_entries = None if tree_payload is None else tree_payload.get("tree")
    if not isinstance(raw_entries, list):
        return False
    entries: dict[str, str] = {}
    for raw_entry in raw_entries:
        entry = _as_mapping(raw_entry)
        if entry is None:
            continue
        path = entry.get("path")
        sha = entry.get("sha")
        if isinstance(path, str) and isinstance(sha, str):
            entries[path] = sha
    if any(entries.get(file.path) != file.blob_sha for file in request.files):
        return False

    owner = repository.split("/", 1)[0]
    head_query = quote(f"{owner}:{request.branch}", safe="")
    base_query = quote(default_branch, safe="")
    pulls = _github_json(
        repository,
        token,
        f"pulls?state=all&head={head_query}&base={base_query}&per_page=100",
    )
    if not isinstance(pulls, list) or len(pulls) != 1:
        return False
    pr = _as_mapping(pulls[0])
    pr_head = None if pr is None else _as_mapping(pr.get("head"))
    pr_base = None if pr is None else _as_mapping(pr.get("base"))
    head_repo = None if pr_head is None else _as_mapping(pr_head.get("repo"))
    base_repo = None if pr_base is None else _as_mapping(pr_base.get("repo"))
    body = None if pr is None else pr.get("body")
    return bool(
        pr is not None
        and pr.get("state") == "open"
        and pr_head is not None
        and pr_head.get("ref") == request.branch
        and pr_head.get("sha") == head_sha
        and pr_base is not None
        and pr_base.get("ref") == default_branch
        and head_repo is not None
        and head_repo.get("full_name") == repository
        and base_repo is not None
        and base_repo.get("full_name") == repository
        and isinstance(body, str)
        and re.search(rf"(?mi)^\s*Refs\s+#{source.issue_number}\s*$", body) is not None
    )


def _persist_recovery_comment(
    body: str,
    *,
    repository: str,
    token: str,
    issue_number: int,
) -> int:
    comments = _paged_github_list(repository, token, f"issues/{issue_number}/comments?sort=created")
    matches = tuple(
        comment
        for comment in comments
        if comment.get("body") == body and is_github_actions_comment(comment)
    )
    if len(matches) > 1:
        raise RuntimeError("partial activation recovery evidence is duplicated")
    if len(matches) == 1:
        comment_id = _positive_int(matches[0].get("id"))
        if comment_id is None:
            raise RuntimeError("partial activation recovery comment id is invalid")
        return comment_id
    response = _as_mapping(
        _github_json(
            repository,
            token,
            f"issues/{issue_number}/comments",
            method="POST",
            payload={"body": body},
        )
    )
    comment_id = None if response is None else _positive_int(response.get("id"))
    if (
        response is None
        or comment_id is None
        or response.get("body") != body
        or not is_github_actions_comment(response)
    ):
        raise RuntimeError("partial activation recovery comment postcondition was not observed")
    observed = _as_mapping(_github_json(repository, token, f"issues/comments/{comment_id}"))
    if (
        observed is None
        or observed.get("body") != body
        or observed.get("id") != comment_id
        or not is_github_actions_comment(observed)
    ):
        raise RuntimeError("partial activation recovery fresh comment was not observed")
    return comment_id


def _unbound_first_activation_result_matches(
    *,
    worker_result: WorkerActionResult,
    source: WorkerRequest,
    accepted_intent: ApplicationDecisionRecord,
    repository: str,
    token: str,
    current_revision: str,
    request_comment_id: int,
) -> bool:
    if (
        accepted_intent.disposition != "ACCEPTED"
        or accepted_intent.issue_number != source.issue_number
        or accepted_intent.role != source.role
        or accepted_intent.action != source.action
        or accepted_intent.change != "unset"
        or accepted_intent.result_kind != _FIRST_ACTIVATION_RESULT
        or accepted_intent.request_comment_id != request_comment_id
        or accepted_intent.worker_result_sha256
        != hashlib.sha256(accepted_intent.raw_worker_result.encode("utf-8")).hexdigest()
        or source != WorkerRequest(source.issue_number, "lead", "propose-change")
        or _SHA.fullmatch(accepted_intent.authorization_revision) is None
        or _SHA.fullmatch(current_revision) is None
    ):
        return False

    try:
        current_projection = _application_owned_worker_result(
            accepted_intent.raw_worker_result,
            source=source,
            change="unset",
            current_revision=current_revision,
            # Before the OpenSpec target has passed exact-head validation,
            # first-activation projection binds its temporary result revision
            # to the current default branch.  The durable malformed result is
            # checked independently below against the original authorization.
            result_revision=current_revision,
            request_comment_id=request_comment_id,
        )
        expected_current = parse_worker_result(
            current_projection,
            source,
            authorized_change="unset",
        )
        accepted_projection = _application_owned_worker_result(
            accepted_intent.raw_worker_result,
            source=source,
            change="unset",
            current_revision=accepted_intent.authorization_revision,
            result_revision=accepted_intent.authorization_revision,
            request_comment_id=request_comment_id,
        )
        accepted_result = parse_worker_result(
            accepted_projection,
            source,
            authorized_change="unset",
        )
    except (TypeError, ValueError, RuntimeError, json.JSONDecodeError):
        return False

    body = _formal_result_body(worker_result, source=source)
    if body is None:
        return False
    if (
        worker_result.issue_number != source.issue_number
        or worker_result.role != source.role
        or worker_result.action != source.action
        or worker_result.change != "unset"
        or worker_result.typed_result.result.kind.value != _FIRST_ACTIVATION_RESULT
        or body != expected_current.result_content
        or _marker(body) != "ACTION_RESULT"
        or _field(body, "Workflow") != f"#{source.issue_number}"
        or _field(body, "Change") != "unset"
        or _field(body, "Action") != source.action
        or _field(body, "Role") != source.role
        or _field(body, "Result") != _FIRST_ACTIVATION_RESULT.upper().replace("-", "_")
        or _field(body, "Revision") != current_revision
        or _field(body, "Default-Branch-Revision") != current_revision
        or _field(body, "Application-Correlation") is not None
        or _field(body, "Repository-derived successor") is not None
    ):
        return False
    comments = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created",
    )
    matches = tuple(
        comment
        for comment in comments
        if is_github_actions_comment(comment)
        and comment.get("body") == accepted_result.result_content
    )
    return len(matches) == 1


def _repair_partial_first_activation_route(
    *,
    raw_worker_result: str,
    materialization: Mapping[str, object],
    accepted_intent: ApplicationDecisionRecord,
    source: WorkerRequest,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    request_comment_id: int,
) -> bool:
    """Restore only the source route after an invalid pre-validation projection."""

    if (
        request_comment_id != accepted_intent.request_comment_id
        or source != WorkerRequest(source.issue_number, "lead", "propose-change")
        or accepted_intent.change != "unset"
    ):
        return False
    try:
        worker_result = parse_worker_result(
            raw_worker_result,
            source,
            authorized_change="unset",
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    if (
        worker_result.change != "unset"
        or worker_result.typed_result.result.kind.value != _FIRST_ACTIVATION_RESULT
    ):
        return False
    parsed = find_materialization_payload(materialization, source)
    if (
        parsed is None
        or parsed.expected_change != "unset"
        or parsed.base_sha != accepted_intent.authorization_revision
        or parsed.change in {"", "unset"}
    ):
        return False
    if current_revision != accepted_intent.authorization_revision:
        if not _authorization_revision_is_ancestor(
            repository,
            token,
            accepted_intent.authorization_revision,
            current_revision,
        ):
            return False
        comparison = _as_mapping(
            _github_json(
                repository,
                token,
                f"compare/{accepted_intent.authorization_revision}...{current_revision}",
            )
        )
        raw_files = None if comparison is None else comparison.get("files")
        base_commit = None if comparison is None else _as_mapping(comparison.get("base_commit"))
        if (
            comparison is None
            or comparison.get("status") != "ahead"
            or base_commit is None
            or base_commit.get("sha") != accepted_intent.authorization_revision
            or not isinstance(raw_files, list)
        ):
            return False
        changed_paths = {
            filename
            for raw_file in raw_files
            for filename in ((raw_file.get("filename") if isinstance(raw_file, Mapping) else None),)
            if isinstance(filename, str)
        }
        if changed_paths.intersection(file.path for file in parsed.files):
            return False
    if _fresh_branch_head(repository, token, default_branch) != current_revision:
        return False
    if not _partial_activation_carrier_matches(
        materialization,
        source,
        repository=repository,
        token=token,
        failed_revision=accepted_intent.authorization_revision,
        default_branch=default_branch,
    ):
        return False
    if not _unbound_first_activation_result_matches(
        worker_result=worker_result,
        source=source,
        accepted_intent=accepted_intent,
        repository=repository,
        token=token,
        current_revision=current_revision,
        request_comment_id=request_comment_id,
    ):
        return False

    issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        issue is None
        or observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.change != "unset"
        or observation.routing != ("reviewer", "review-openspec")
        or not isinstance(issue.get("body"), str)
        or _CHANGE_LINE.findall(cast(str, issue["body"])) != ["unset"]
    ):
        return False
    unrelated_labels = [
        name for name in _issue_label_names(issue) if not name.startswith(_ROUTING_LABEL_PREFIXES)
    ]
    repaired_labels = [*unrelated_labels, f"action:{source.action}"]

    # Re-read the exact target immediately before this sole repair mutation.
    fresh_issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    fresh_observation = None if fresh_issue is None else normalize_github_issue(fresh_issue)
    if (
        fresh_issue is None
        or fresh_observation is None
        or not fresh_observation.authoritative
        or fresh_observation.state != "open"
        or fresh_observation.change != "unset"
        or fresh_observation.routing != ("reviewer", "review-openspec")
        or fresh_issue.get("body") != issue.get("body")
    ):
        raise RuntimeError("partial first activation repair target changed before mutation")
    _github_json(
        repository,
        token,
        f"issues/{source.issue_number}",
        method="PATCH",
        payload={"labels": repaired_labels},
    )
    final = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    final_observation = None if final is None else normalize_github_issue(final)
    final_labels = [] if final is None else _issue_label_names(final)
    if (
        final is None
        or final_observation is None
        or not final_observation.authoritative
        or final_observation.state != "open"
        or final_observation.change != "unset"
        or final_observation.routing != (source.role, source.action)
        or final.get("body") != issue.get("body")
        or sorted(name for name in final_labels if not name.startswith(_ROUTING_LABEL_PREFIXES))
        != sorted(unrelated_labels)
    ):
        raise RuntimeError("partial first activation repair postcondition was not observed")
    return True


def _recover_partial_first_activation(
    *,
    request: ApplicationRequest,
    event: Mapping[str, object],
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
) -> bool:
    if request.authorization_revision == current_revision:
        return False
    source = _claimed_source(request.raw_worker_result)
    if source is None:
        return False
    if (source.role, source.action) != _RECOVERY_SOURCE:
        return False
    worker_result = parse_worker_result(request.raw_worker_result, source)
    if (
        worker_result.change != "unset"
        or worker_result.typed_result.result.kind.value != _FIRST_ACTIVATION_RESULT
    ):
        return False
    materializations = _materialization_effects(request.raw_worker_result, source)
    if len(materializations) != 1:
        return False
    materialization = materializations[0]
    parsed = find_materialization_payload(materialization, source)
    if parsed is None or parsed.expected_change != "unset" or parsed.change in {"", "unset"}:
        return False
    event_comment = _as_mapping(event.get("comment"))
    request_comment_id = None if event_comment is None else _positive_int(event_comment.get("id"))
    if request_comment_id is None:
        return False
    if not _authorization_revision_is_ancestor(
        repository,
        token,
        request.authorization_revision,
        current_revision,
    ):
        return False
    if not _partial_activation_carrier_matches(
        materialization,
        source,
        repository=repository,
        token=token,
        failed_revision=request.authorization_revision,
        default_branch=default_branch,
    ):
        return False

    issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        issue is None
        or observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.change != parsed.change
    ):
        return False
    comments = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created",
    )
    lifecycle = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/timeline",
    )
    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=parsed.change,
        state=observation.state,
        current_routing=observation.routing,
        comments=comments,
        current_revision=current_revision,
        lifecycle_events=lifecycle,
    )
    decision = qualify_current_formal_consequence(qualification)
    matching_recoveries = tuple(
        recovery
        for recovery in qualification.recovery_events
        if recovery.valid
        and recovery.request_comment_id == request_comment_id
        and recovery.failed_authorization_revision == request.authorization_revision
        and recovery.default_branch_revision == current_revision
        and recovery.change == parsed.change
    )
    recovery_matches_request = (
        len(qualification.recovery_events) == 1 and len(matching_recoveries) == 1
    )
    if (
        observation.routing == _RECOVERY_TARGET
        and decision.qualified
        and decision.reason == "current-administrative-recovery-route-qualified"
        and recovery_matches_request
    ):
        return True
    if (
        observation.routing != _RECOVERY_SOURCE
        or decision.qualified
        or (qualification.recovery_events and not recovery_matches_request)
        or any(event.change == parsed.change for event in qualification.events)
    ):
        return False

    if not recovery_matches_request:
        body = _recovery_body(
            source=source,
            change=parsed.change,
            current_revision=current_revision,
            failed_authorization_revision=request.authorization_revision,
            request_comment_id=request_comment_id,
        )
        _persist_recovery_comment(
            body,
            repository=repository,
            token=token,
            issue_number=source.issue_number,
        )

    fresh_issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    fresh_observation = None if fresh_issue is None else normalize_github_issue(fresh_issue)
    if (
        fresh_issue is None
        or fresh_observation is None
        or not fresh_observation.authoritative
        or fresh_observation.state != "open"
        or fresh_observation.change != parsed.change
        or fresh_observation.routing != _RECOVERY_SOURCE
    ):
        raise RuntimeError("partial activation changed before recovery routing repair")
    labels = [
        name
        for name in _issue_label_names(fresh_issue)
        if not name.startswith(_ROUTING_LABEL_PREFIXES)
    ]
    labels.append(f"action:{_RECOVERY_TARGET[1]}")
    _github_json(
        repository,
        token,
        f"issues/{source.issue_number}",
        method="PATCH",
        payload={"labels": labels},
    )

    recovery_source = WorkerRequest(source.issue_number, *_RECOVERY_TARGET)
    for attempt in range(_ACTIVATION_OBSERVATION_ATTEMPTS):
        if _formal_qualification(
            repository=repository,
            token=token,
            source=recovery_source,
            change=parsed.change,
            current_revision=current_revision,
            expected_result_kind="",
            expected_application_correlation="",
            current_routing=_RECOVERY_TARGET,
            expected_routing=None,
            mode="current",
        ):
            return True
        if attempt + 1 < _ACTIVATION_OBSERVATION_ATTEMPTS:
            time.sleep(_ACTIVATION_OBSERVATION_DELAY_SECONDS)
    raise RuntimeError("partial activation administrative recovery did not qualify")


def _resume_pending_accepted_merge_recovery(
    *,
    accepted: ApplicationDecisionRecord,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
) -> bool:
    """Finish an interrupted recovery comment -> routing handoff, never MERGED."""

    if (
        accepted.disposition != "ACCEPTED"
        or accepted.result_kind != "merged"
        or accepted.role != "executor"
        or accepted.action not in {"merge-implementation-pr", "merge-archive-pr"}
    ):
        return False
    comments = _paged_github_list(
        repository, token, f"issues/{accepted.issue_number}/comments?sort=created"
    )
    recovery_candidates = [
        comment
        for comment in comments
        if is_github_actions_comment(comment)
        and isinstance(comment.get("body"), str)
        and cast(str, comment["body"]).startswith(_RECOVERY_MARKER + "\n")
        and _field(cast(str, comment["body"]), "Reason") == "accepted-merge-precondition-rejected"
        and _field(cast(str, comment["body"]), "Request-Comment-ID")
        == str(accepted.request_comment_id)
    ]
    if not recovery_candidates:
        return False
    if len(recovery_candidates) != 1:
        raise RuntimeError("accepted merge recovery evidence is duplicated")
    issue = _as_mapping(_github_json(repository, token, f"issues/{accepted.issue_number}"))
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        issue is None
        or observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.change != accepted.change
    ):
        raise RuntimeError("accepted merge recovery current Issue is unavailable")
    timeline = _paged_github_list(repository, token, f"issues/{accepted.issue_number}/timeline")
    recovery_body = cast(str, recovery_candidates[0]["body"])
    recovery_revision = _field(recovery_body, "Default-Branch-Revision")
    revisions = {accepted.authorization_revision, recovery_revision}
    ancestry: list[tuple[str, str]] = []
    for revision in revisions:
        if revision == current_revision:
            continue
        if (
            revision is None
            or _SHA.fullmatch(revision) is None
            or not _authorization_revision_is_ancestor(
                repository, token, revision, current_revision
            )
        ):
            raise RuntimeError("accepted merge recovery ancestry is unqualified")
        ancestry.append((revision, current_revision))
    qualified = build_qualification_input(
        issue_number=accepted.issue_number,
        change=accepted.change,
        state=observation.state,
        current_routing=observation.routing,
        comments=comments,
        current_revision=current_revision,
        lifecycle_events=timeline,
        authorization_ancestry=tuple(ancestry),
    )
    matching = [
        event
        for event in qualified.recovery_events
        if event.valid
        and event.reason == "accepted-merge-precondition-rejected"
        and event.request_comment_id == accepted.request_comment_id
        and event.source == (accepted.role, accepted.action)
        and event.change == accepted.change
    ]
    if len(matching) != 1 or matching[0] != qualified.recovery_events[-1]:
        raise RuntimeError("accepted merge recovery provenance is not qualified")
    event = matching[0]
    target = event.target
    if target is None or event.pr_number is None or event.pr_head_sha is None:
        raise RuntimeError("accepted merge recovery target identity is incomplete")
    pr = _as_mapping(_github_json(repository, token, f"pulls/{event.pr_number}"))
    pr_head = None if pr is None else _as_mapping(pr.get("head"))
    if (
        pr is None
        or pr.get("state") != "open"
        or pr.get("merged") is not False
        or pr_head is None
        or pr_head.get("sha") != event.pr_head_sha
        or _fresh_branch_head(repository, token, default_branch) != current_revision
    ):
        raise RuntimeError("accepted merge recovery PR or main changed")

    if observation.routing == target:
        outcome = qualify_current_formal_consequence(qualified)
        if (
            not outcome.qualified
            or outcome.reason != "current-administrative-recovery-route-qualified"
        ):
            raise RuntimeError("accepted merge recovery current route is not qualified")
        fresh_dispatch = classify_dispatch(acquire_current_github_preflight(repository, token))
        if (
            fresh_dispatch.disposition != "AUTHORIZE"
            or fresh_dispatch.selected_issue_id != accepted.issue_number
            or fresh_dispatch.selected_routing != target
        ):
            raise RuntimeError("accepted merge recovery has no freshly dispatchable successor")
        return True
    if observation.routing != (accepted.role, accepted.action):
        raise RuntimeError("accepted merge recovery source routing changed")
    fresh = _as_mapping(_github_json(repository, token, f"issues/{accepted.issue_number}"))
    fresh_observation = None if fresh is None else normalize_github_issue(fresh)
    if (
        fresh is None
        or fresh_observation is None
        or not fresh_observation.authoritative
        or fresh_observation.routing != observation.routing
        or fresh.get("body") != issue.get("body")
        or _fresh_branch_head(repository, token, default_branch) != current_revision
    ):
        raise RuntimeError("accepted merge recovery route changed before write")
    fresh_pr = _as_mapping(_github_json(repository, token, f"pulls/{event.pr_number}"))
    fresh_pr_head = None if fresh_pr is None else _as_mapping(fresh_pr.get("head"))
    if (
        fresh_pr is None
        or fresh_pr.get("state") != "open"
        or fresh_pr.get("merged") is not False
        or fresh_pr_head is None
        or fresh_pr_head.get("sha") != event.pr_head_sha
    ):
        raise RuntimeError("accepted merge recovery PR changed before write")
    labels = [
        name for name in _issue_label_names(fresh) if not name.startswith(_ROUTING_LABEL_PREFIXES)
    ]
    labels.append(f"action:{target[1]}")
    _github_json(
        repository,
        token,
        f"issues/{accepted.issue_number}",
        method="PATCH",
        payload={"labels": labels},
    )
    after = _as_mapping(_github_json(repository, token, f"issues/{accepted.issue_number}"))
    after_observation = None if after is None else normalize_github_issue(after)
    if (
        after is None
        or after_observation is None
        or after_observation.routing != target
        or after_observation.change != accepted.change
        or after.get("body") != issue.get("body")
        or sorted(
            name
            for name in _issue_label_names(after)
            if not name.startswith(_ROUTING_LABEL_PREFIXES)
        )
        != sorted(
            name
            for name in _issue_label_names(issue)
            if not name.startswith(_ROUTING_LABEL_PREFIXES)
        )
    ):
        raise RuntimeError("accepted merge recovery routing postcondition is absent")
    fresh_dispatch = classify_dispatch(acquire_current_github_preflight(repository, token))
    if (
        fresh_dispatch.disposition != "AUTHORIZE"
        or fresh_dispatch.selected_issue_id != accepted.issue_number
        or fresh_dispatch.selected_routing != target
    ):
        raise RuntimeError("accepted merge recovery has no freshly dispatchable successor")
    return True


def _recover_deterministic_accepted_merge_failure(
    *,
    result: ApplyResult,
    batch: object,
    source: WorkerRequest,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    request_comment_id: int,
) -> bool:
    """Dispose of a rejected accepted merge without replacing or replaying MERGED.

    This is an application-owned administrative recovery, not a semantic
    ACTION_RESULT or a second merge attempt. Only a proven zero-write,
    deterministic integration prerequisite may activate the existing model's
    lifecycle-violation successor. An unknown write or incomplete Git proof
    never qualifies.
    """

    from investment_strategy.scheduled_agent_effects import EffectBatch

    if (
        source.role != "executor"
        or source.action not in {"merge-implementation-pr", "merge-archive-pr"}
        or not isinstance(batch, EffectBatch)
        or batch.typed_result is None
        or batch.typed_result.result.kind.value != "merged"
    ):
        return False
    recovery = result.recovery_evidence
    rejection = None if recovery is None else recovery.rejection
    if (
        result.applied
        or recovery is None
        or recovery.mutation_status != "not-complete"
        or recovery.unfinished_boundary != "effect-precondition"
        or recovery.completed_effect_indexes
        or recovery.completed_effect_sha256
        or rejection is None
        or getattr(rejection.classification, "value", rejection.classification)
        != "effect-precondition-unsatisfied"
        or recovery.failed_effect_kind != GITHUB_MUTATION_KIND
        or recovery.failed_effect_index < 0
        or recovery.failed_effect_index >= len(batch.effects)
    ):
        return False
    effect = batch.effects[recovery.failed_effect_index]
    payload = _effect_payload({"payload_json": effect.payload_json})
    if (
        effect.kind != GITHUB_MUTATION_KIND
        or hashlib.sha256(effect.payload_json.encode("utf-8")).hexdigest()
        != recovery.failed_effect_sha256
        or payload is None
        or payload.get("operation") != "pull-request-merge"
        or not isinstance(payload.get("number"), int)
        or isinstance(payload.get("number"), bool)
        or _SHA.fullmatch(str(payload.get("expected_head_sha"))) is None
    ):
        return False

    decision = _application_decision_comment_for_request(
        repository=repository,
        token=token,
        issue_number=source.issue_number,
        request_comment_id=request_comment_id,
    )
    if decision is None:
        return False
    accepted, accepted_body = decision
    if (
        accepted.disposition != "ACCEPTED"
        or accepted.issue_number != source.issue_number
        or (accepted.role, accepted.action) != (source.role, source.action)
        or accepted.result_kind != "merged"
        or not isinstance(accepted.change, str)
        or accepted.change == "unset"
    ):
        return False

    # A newly observed PR conflict or fully qualified implementation-owned
    # reconciliation is actionable. Missing evidence, a pending mergeability
    # computation, or an unexplained mismatch is not deterministic.
    number = cast(int, payload["number"])
    head = cast(str, payload["expected_head_sha"])
    pr = _as_mapping(_github_json(repository, token, f"pulls/{number}"))
    pr_head = None if pr is None else _as_mapping(pr.get("head"))
    pr_base = None if pr is None else _as_mapping(pr.get("base"))
    if (
        pr is None
        or pr.get("state") != "open"
        or pr.get("merged") is not False
        or pr_head is None
        or pr_head.get("sha") != head
        or pr_base is None
        or pr_base.get("ref") != default_branch
        or _fresh_branch_head(repository, token, default_branch) != current_revision
    ):
        return False
    deterministic = pr.get("mergeable") is False
    if source.action == "merge-implementation-pr":
        carrier = qualify_implementation_carrier(
            repository=repository,
            token=token,
            source=source,
            change=accepted.change,
            pr_number=number,
            current_revision=current_revision,
        )
        deterministic = (
            carrier.disposition == "RECONCILIATION_REQUIRED"
            and carrier.head_sha == head
            and carrier.reason
            in {
                "carrier-confirmed-git-merge-conflict",
                "initial-carrier-requires-default-reconciliation",
                "carrier-pr-base-is-stale",
                "continuation-carrier-requires-default-reconciliation",
            }
        )
    if not deterministic:
        return False

    successor = next_action(ModelAction(source.action), TypedResult(ResultKind.LIFECYCLE_VIOLATION))
    if successor is None:
        return False
    target = (role_for(successor).value, successor.value)
    issue = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        issue is None
        or observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.change != accepted.change
        or observation.routing != (source.role, source.action)
    ):
        return False
    preflight = acquire_current_github_preflight(repository, token)
    dispatch = classify_dispatch(preflight)
    if (
        dispatch.disposition != "AUTHORIZE"
        or dispatch.selected_issue_id != source.issue_number
        or dispatch.selected_routing != (source.role, source.action)
    ):
        return False

    decision_sha = hashlib.sha256(accepted_body.encode("utf-8")).hexdigest()
    failure_sha = _canonical_sha256(_recovery_failure_document(result))
    body = "\n".join(
        (
            _RECOVERY_MARKER,
            f"Workflow: #{source.issue_number}",
            f"Change: {accepted.change}",
            f"Source: {source.role.capitalize()} / {source.action}",
            f"Target: {target[0].capitalize()} / {target[1]}",
            f"Default-Branch-Revision: {current_revision}",
            f"Failed-Authorization-Revision: {accepted.authorization_revision}",
            f"Request-Comment-ID: {request_comment_id}",
            f"Accepted-Decision-SHA256: {decision_sha}",
            f"Failure-Evidence-SHA256: {failure_sha}",
            f"PR-Number: {number}",
            f"PR-Head-SHA: {head}",
            "Reason: accepted-merge-precondition-rejected",
        )
    )
    existing_comments = _paged_github_list(
        repository, token, f"issues/{source.issue_number}/comments?sort=created"
    )
    if any(
        is_github_actions_comment(comment)
        and isinstance(comment.get("body"), str)
        and cast(str, comment["body"]).startswith(_RECOVERY_MARKER + "\n")
        and _field(cast(str, comment["body"]), "Request-Comment-ID") == str(request_comment_id)
        and comment.get("body") != body
        for comment in existing_comments
    ):
        return False
    _persist_recovery_comment(
        body, repository=repository, token=token, issue_number=source.issue_number
    )

    # Reconstruct an exact, still-current route and PR before the only label
    # write. Retain unrelated labels and inspect the postcondition and the
    # machine dispatch independently, as with partial-activation recovery.
    fresh = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    fresh_observation = None if fresh is None else normalize_github_issue(fresh)
    if (
        fresh is None
        or fresh_observation is None
        or not fresh_observation.authoritative
        or fresh_observation.state != "open"
        or fresh_observation.change != accepted.change
        or fresh_observation.routing != (source.role, source.action)
        or fresh.get("body") != issue.get("body")
        or _fresh_branch_head(repository, token, default_branch) != current_revision
    ):
        raise RuntimeError("accepted merge recovery target changed before routing")
    fresh_pr = _as_mapping(_github_json(repository, token, f"pulls/{number}"))
    fresh_pr_head = None if fresh_pr is None else _as_mapping(fresh_pr.get("head"))
    if (
        fresh_pr is None
        or fresh_pr.get("state") != "open"
        or fresh_pr.get("merged") is not False
        or fresh_pr_head is None
        or fresh_pr_head.get("sha") != head
    ):
        raise RuntimeError("accepted merge recovery PR changed before routing")
    labels = [
        name for name in _issue_label_names(fresh) if not name.startswith(_ROUTING_LABEL_PREFIXES)
    ]
    labels.append(f"action:{successor.value}")
    _github_json(
        repository,
        token,
        f"issues/{source.issue_number}",
        method="PATCH",
        payload={"labels": labels},
    )
    after = _as_mapping(_github_json(repository, token, f"issues/{source.issue_number}"))
    after_observation = None if after is None else normalize_github_issue(after)
    if (
        after is None
        or after_observation is None
        or not after_observation.authoritative
        or after_observation.state != "open"
        or after_observation.change != accepted.change
        or after_observation.routing != target
        or after.get("body") != issue.get("body")
        or sorted(
            name
            for name in _issue_label_names(after)
            if not name.startswith(_ROUTING_LABEL_PREFIXES)
        )
        != sorted(
            name
            for name in _issue_label_names(issue)
            if not name.startswith(_ROUTING_LABEL_PREFIXES)
        )
    ):
        raise RuntimeError("accepted merge recovery routing postcondition not observed")
    dispatched = classify_dispatch(acquire_current_github_preflight(repository, token))
    if (
        dispatched.disposition != "AUTHORIZE"
        or dispatched.selected_issue_id != source.issue_number
        or dispatched.selected_routing != target
    ):
        raise RuntimeError("accepted merge recovery fresh dispatch not qualified")
    return True


def _write_validation_outputs(target: ValidationResourceTarget | None) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    lines = [f"validation_required={'true' if target is not None else 'false'}"]
    if target is not None:
        lines.extend(
            (
                f"validation_target_repository={target.repository}",
                f"validation_target_revision={target.revision}",
                f"validation_correlation={target.correlation}",
                f"validation_pr_number={target.pr_number}",
                f"validation_change={target.change}",
            )
        )
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def _rejected_merge_result_from_checkpoint(
    predecessor: ApplicationRecoveryArtifact,
) -> ApplyResult | None:
    """Rehydrate only a verified zero-write failure; never reconstruct a merge write."""

    failure = predecessor.document.get("failure_evidence")
    if not isinstance(failure, Mapping):
        return None
    rejection_doc = failure.get("rejection")
    if not isinstance(rejection_doc, Mapping):
        return None
    try:
        kind = ApplicationRejectionKind(cast(str, rejection_doc["classification"]))
    except (KeyError, TypeError, ValueError):
        return None
    if (
        kind is not ApplicationRejectionKind.EFFECT_PRECONDITION_UNSATISFIED
        or failure.get("mutation_status") != "not-complete"
        or failure.get("unfinished_boundary") != "effect-precondition"
        or failure.get("completed_effect_indexes") != []
        or failure.get("completed_effect_sha256") != []
        or type(failure.get("failed_effect_index")) is not int
        or not isinstance(failure.get("failed_effect_kind"), str)
        or not isinstance(failure.get("failed_effect_sha256"), str)
        or not isinstance(rejection_doc.get("expected"), str)
        or not isinstance(rejection_doc.get("observed"), str)
    ):
        return None
    recovery = EffectRecoveryEvidence(
        failed_effect_index=cast(int, failure["failed_effect_index"]),
        failed_effect_kind=cast(str, failure["failed_effect_kind"]),
        failed_effect_sha256=cast(str, failure["failed_effect_sha256"]),
        completed_effect_indexes=(),
        completed_effect_sha256=(),
        mutation_status="not-complete",
        unfinished_boundary="effect-precondition",
        rejection=ApplicationRejection(
            kind,
            cast(str, rejection_doc["expected"]),
            cast(str, rejection_doc["observed"]),
        ),
    )
    return ApplyResult(False, "effect precondition rejected", recovery_evidence=recovery)


def _write_carrier_outputs(result: ApplyResult) -> None:
    """Expose an immutable carrier plan as run-scoped application evidence."""

    output_path = os.environ.get("GITHUB_OUTPUT")
    plan = result.carrier_plan
    if output_path is None:
        return
    lines = [f"carrier_required={'true' if plan is not None else 'false'}"]
    if plan is not None:
        document = carrier_plan_document(plan)
        encoded = base64.b64encode(
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        lines.extend((f"carrier_plan_id={plan.plan_id}", f"carrier_plan_b64={encoded}"))
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def _read_verified_application_artifact(
    repository: str,
    token: str,
    *,
    metadata: Mapping[str, object],
    run_id: int,
    run_head_sha: str,
    download: Callable[[str, str, str], bytes],
) -> tuple[int, str, Mapping[str, object]] | None:
    """One exact metadata, bytes, digest and JSON reader for both native artifacts.

    The recovery and exception readers retain their separate run/stage/lineage
    contracts. This reader cannot admit a continuation or authorize a write.
    """

    artifact_id = _strict_positive_int(metadata.get("id"))
    digest = metadata.get("digest")
    artifact_run = metadata.get("workflow_run")
    if (
        artifact_id is None
        or metadata.get("expired") is not False
        or not isinstance(digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None
        or not isinstance(artifact_run, Mapping)
        or artifact_run.get("id") != run_id
        or artifact_run.get("head_sha") != run_head_sha
    ):
        return None
    raw = download(repository, token, f"actions/artifacts/{artifact_id}/zip")
    if (
        not raw
        or len(raw) > _MAX_APPLICATION_RECOVERY_BYTES
        or f"sha256:{hashlib.sha256(raw).hexdigest()}" != digest
    ):
        return None
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(decoded, Mapping):
        return None
    return artifact_id, digest, cast(Mapping[str, object], decoded)


def read_application_recovery_artifact(
    repository: str,
    token: str,
    *,
    run_id: int,
    run_attempt: int,
    job_id: int,
    request_comment_id: int,
    accepted_decision_sha256: str,
    read: Callable[[str, str, str], object] | None = None,
    artifact_reader: Callable[[str, str, str], bytes] | None = None,
    strict_read: bool = False,
) -> ApplicationRecoveryArtifact | None:
    """Qualify structured recovery evidence against one completed Actions job."""

    def unavailable() -> ApplicationRecoveryArtifact | None:
        # A missing, contradictory, expired or unreadable current-protocol
        # artifact is NOT observed legacy absence.
        if strict_read:
            raise RuntimeError("application recovery evidence unavailable")
        return None

    api_read = _github_json if read is None else read
    download = read_github_artifact_bytes if artifact_reader is None else artifact_reader
    if (
        _strict_positive_int(run_id) is None
        or _strict_positive_int(run_attempt) is None
        or _strict_positive_int(job_id) is None
        or _strict_positive_int(request_comment_id) is None
        or re.fullmatch(r"[0-9a-f]{64}", accepted_decision_sha256) is None
    ):
        return unavailable()
    run = api_read(repository, token, f"actions/runs/{run_id}")
    if (
        not isinstance(run, Mapping)
        or run.get("id") != run_id
        or run.get("run_attempt") != run_attempt
        or run.get("status") != "completed"
        or not isinstance(run.get("head_sha"), str)
    ):
        return unavailable()
    inventory = github_complete_run_jobs(
        repository, token, run_id=run_id, run_attempt=run_attempt, read=api_read
    )
    if inventory is None:
        return unavailable()
    job = inventory.single_apply
    if job is None or job.id != job_id:
        return unavailable()
    if job.status != "completed" or job.conclusion not in {"success", "failure"}:
        return unavailable()
    steps = job.steps
    if steps is None:
        return unavailable()
    upload_stage = application_artifact_stage(steps)
    if upload_stage not in {"PRE_RECOVERY", "FINAL_RECOVERY"}:
        if upload_stage == "NONE" and not any(
            name
            in {
                "Upload exact application recovery evidence",
                "Upload final exact application recovery evidence",
            }
            for name, _ in steps
        ):
            # A completed legacy job with no writer step is distinct from a
            # missing artifact after a successful native upload.
            return None
        return unavailable()
    artifacts_payload = api_read(
        repository,
        token,
        f"actions/runs/{run_id}/artifacts?per_page=100",
    )
    if not isinstance(artifacts_payload, Mapping) or not isinstance(
        artifacts_payload.get("artifacts"), list
    ):
        return unavailable()
    artifacts = [
        item
        for item in cast(list[object], artifacts_payload["artifacts"])
        if isinstance(item, Mapping) and item.get("name") == _APPLICATION_RECOVERY_ARTIFACT
    ]
    if len(artifacts) != 1:
        return unavailable()
    artifact = cast(Mapping[str, object], artifacts[0])
    verified = _read_verified_application_artifact(
        repository,
        token,
        metadata=artifact,
        run_id=run_id,
        run_head_sha=cast(str, run["head_sha"]),
        download=download,
    )
    if verified is None:
        return unavailable()
    artifact_id, artifact_digest, document = verified
    expected_keys = {
        "schema",
        "repository",
        "issue_number",
        "role",
        "action",
        "request_comment_id",
        "accepted_decision_sha256",
        "trigger_comment_id",
        "run_id",
        "run_attempt",
        "current_revision",
        "authorization_revision",
        "recovery_attempt",
        "recovery_episode_sha256",
        "prior_failure_evidence_sha256",
        "predecessor",
        "failure_evidence",
        "failure_evidence_sha256",
        "continuation_eligible",
    }
    failure_evidence = document.get("failure_evidence")
    prior_failures = document.get("prior_failure_evidence_sha256")
    trigger_comment_id = _strict_positive_int(document.get("trigger_comment_id"))
    recovery_attempt = _strict_positive_int(document.get("recovery_attempt"))
    episode_sha256 = document.get("recovery_episode_sha256")
    evidence_sha256 = document.get("failure_evidence_sha256")
    issue_number = document.get("issue_number")
    authorization_revision = document.get("authorization_revision")
    if (
        set(document) != expected_keys
        or document.get("schema") != _APPLICATION_RECOVERY_SCHEMA
        or document.get("repository") != repository
        or isinstance(issue_number, bool)
        or not isinstance(issue_number, int)
        or issue_number <= 0
        or document.get("request_comment_id") != request_comment_id
        or document.get("accepted_decision_sha256") != accepted_decision_sha256
        or document.get("run_id") != run_id
        or document.get("run_attempt") != run_attempt
        or not isinstance(document.get("current_revision"), str)
        or _SHA.fullmatch(cast(str, document["current_revision"])) is None
        or not isinstance(document.get("role"), str)
        or not isinstance(document.get("action"), str)
        or not isinstance(authorization_revision, str)
        or _SHA.fullmatch(authorization_revision) is None
        or recovery_attempt is None
        or not isinstance(episode_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", episode_sha256) is None
        or not isinstance(evidence_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", evidence_sha256) is None
        or not isinstance(prior_failures, list)
        or len(prior_failures) != recovery_attempt - 1
        or any(
            not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in prior_failures
        )
        or len(set(prior_failures)) != len(prior_failures)
        or not isinstance(failure_evidence, Mapping)
        or evidence_sha256 != _canonical_sha256(failure_evidence)
        or not isinstance(document.get("continuation_eligible"), bool)
        or trigger_comment_id is None
        or run.get("display_title") != f"Scheduled Agent Application {trigger_comment_id}"
    ):
        return unavailable()
    if cast(bool, document["continuation_eligible"]) and (
        _accepted_recovery_boundary(cast(Mapping[str, object], failure_evidence)) == "NONE"
    ):
        return unavailable()
    predecessor = document.get("predecessor")
    if recovery_attempt == 1:
        if predecessor is not None or prior_failures:
            return unavailable()
    elif predecessor is None:
        if cast(bool, document.get("continuation_eligible")) or prior_failures:
            return unavailable()
    elif (
        not isinstance(predecessor, Mapping)
        or predecessor.get("recovery_attempt") != recovery_attempt - 1
        or predecessor.get("run_id") is None
        or predecessor.get("artifact_id") is None
        or predecessor.get("failure_evidence_sha256") not in prior_failures
    ):
        return unavailable()
    # A rerun retains the original workflow run's immutable head_sha even
    # though its explicit default-branch checkout is fresh. The uploaded
    # evidence records that checked-out revision, so accept a different SHA
    # only for an actual rerun with independently verified ancestry. Keep the
    # original exact equality for first attempts and fail closed on divergence.
    checked_out_revision = cast(str, document["current_revision"])
    original_run_head = cast(str, run["head_sha"])
    if checked_out_revision != original_run_head:
        if run_attempt <= 1 or _SHA.fullmatch(original_run_head) is None:
            return unavailable()
        comparison = _as_mapping(
            api_read(repository, token, f"compare/{original_run_head}...{checked_out_revision}")
        )
        base_commit = None if comparison is None else _as_mapping(comparison.get("base_commit"))
        merge_base = (
            None if comparison is None else _as_mapping(comparison.get("merge_base_commit"))
        )
        if (
            comparison is None
            or comparison.get("status") != "ahead"
            or comparison.get("behind_by") != 0
            or type(comparison.get("ahead_by")) is not int
            or cast(int, comparison["ahead_by"]) <= 0
            or base_commit is None
            or base_commit.get("sha") != original_run_head
            or merge_base is None
            or merge_base.get("sha") != original_run_head
        ):
            return unavailable()
    return ApplicationRecoveryArtifact(
        run_id=run_id,
        run_attempt=run_attempt,
        job_id=job_id,
        artifact_id=artifact_id,
        artifact_digest=artifact_digest,
        request_comment_id=request_comment_id,
        accepted_decision_sha256=accepted_decision_sha256,
        failure_evidence_sha256=evidence_sha256,
        recovery_episode_sha256=episode_sha256,
        recovery_attempt=recovery_attempt,
        continuation_eligible=cast(bool, document.get("continuation_eligible")),
        document=document,
    )


_EXCEPTION_APPLY_STEP_CONTRACT: dict[str, str] = {
    "Freshly authorize and apply repository-owned effects": "failure",
    "Upload exact application recovery evidence": "skipped",
    "Upload pre-ACCEPT or interrupted application exception evidence": "success",
    "Persist exact external carrier plan": "skipped",
    "Upload exact external carrier plan": "skipped",
    "Persist the derived successor after exact validation": "skipped",
    "Upload final exact application recovery evidence": "skipped",
}

_POST_VALIDATION_EXCEPTION_STEP_CONTRACT: dict[str, str] = {
    "Freshly authorize and apply repository-owned effects": "success",
    "Upload pre-ACCEPT or interrupted application exception evidence": "skipped",
    "Persist exact external carrier plan": "skipped",
    "Upload exact external carrier plan": "skipped",
    "Persist the derived successor after exact validation": "failure",
    "Upload final exact application recovery evidence": "skipped",
    "Upload post-validation application exception evidence": "success",
}


def application_artifact_stage(
    steps: Sequence[tuple[str | None, str | None]] | None,
) -> Literal[
    "PRE_EXCEPTION", "POST_EXCEPTION", "PRE_RECOVERY", "FINAL_RECOVERY", "INVALID", "NONE"
]:
    """Select one native output phase; a prior checkpoint is not a same-stage conflict."""

    if steps is None:
        return "NONE"
    names = [name for name, _ in steps]
    if any(not isinstance(name, str) for name in names) or len(names) != len(set(names)):
        return "INVALID"
    completed = {name for name, conclusion in steps if conclusion == "success"}
    pre_exception = "Upload pre-ACCEPT or interrupted application exception evidence" in completed
    post_exception = "Upload post-validation application exception evidence" in completed
    early_recovery = "Upload exact application recovery evidence" in completed
    final_recovery = "Upload final exact application recovery evidence" in completed
    if (pre_exception and (post_exception or early_recovery or final_recovery)) or (
        post_exception and final_recovery
    ):
        return "INVALID"
    if post_exception:
        return "POST_EXCEPTION"
    if pre_exception:
        return "PRE_EXCEPTION"
    if final_recovery:
        return "FINAL_RECOVERY"
    if early_recovery:
        return "PRE_RECOVERY"
    return "NONE"


_EXCEPTION_DOCUMENT_KEYS = frozenset(
    {
        "schema",
        "repository",
        "issue_number",
        "role",
        "action",
        "change",
        "revision",
        "request_comment_id",
        "trigger_comment_id",
        "run_id",
        "run_attempt",
        "attempted_operation",
        "exception_type",
        "raw_error",
        "raw_traceback",
        "mutation_status",
        "unfinished_boundary",
        "classification",
    }
)


def _matches_required_fields(
    observed: Mapping[str, object], required: Mapping[str, object]
) -> bool:
    """Check a named-field contract without an independently maintained guard tree."""

    return all(observed.get(key) == value for key, value in required.items())


def _qualified_exception_apply_run(
    repository: str,
    token: str,
    *,
    run_id: int,
    run_attempt: int,
    job_id: int,
    read: Callable[[str, str, str], object],
) -> tuple[Mapping[str, object], bool] | None:
    """Prove one failed native stage and its earlier-phase recovery writer."""

    run = _as_mapping(read(repository, token, f"actions/runs/{run_id}"))
    required_run = {
        "id": run_id,
        "run_attempt": run_attempt,
        "status": "completed",
        "conclusion": "failure",
    }
    if run is None or not _matches_required_fields(run, required_run):
        return None
    if (
        not isinstance(run.get("head_sha"), str)
        or _SHA.fullmatch(cast(str, run["head_sha"])) is None
    ):
        return None
    inventory = github_complete_run_jobs(
        repository, token, run_id=run_id, run_attempt=run_attempt, read=read
    )
    if inventory is None:
        return None
    job = inventory.single_apply
    if job is None:
        return None
    if job.id != job_id or job.status != "completed" or job.conclusion != "failure":
        return None
    steps = job.steps
    if steps is None:
        return None
    conclusions: dict[str, str] = {}
    for name, result in steps:
        if name is None or result is None or name in conclusions:
            return None
        conclusions[name] = result
    stage = application_artifact_stage(steps)
    pre_exception = stage == "PRE_EXCEPTION" and _matches_required_fields(
        conclusions, _EXCEPTION_APPLY_STEP_CONTRACT
    )
    post_exception = stage == "POST_EXCEPTION" and _matches_required_fields(
        conclusions, _POST_VALIDATION_EXCEPTION_STEP_CONTRACT
    )
    if post_exception and conclusions.get("Upload exact application recovery evidence") not in {
        "success",
        "skipped",
    }:
        return None
    if pre_exception == post_exception:
        return None
    return run, bool(
        post_exception
        and conclusions.get("Upload exact application recovery evidence") == "success"
    )


def _qualified_exception_artifact_metadata(
    inventory: object, *, run_id: int, run_head_sha: str, predecessor_recovery: bool
) -> Mapping[str, object] | None:
    """Qualify a later exception without discarding a prior-phase checkpoint."""

    payload = _as_mapping(inventory)
    artifacts = None if payload is None else payload.get("artifacts")
    if not isinstance(artifacts, list) or payload is None:
        return None
    if type(payload.get("total_count")) is not int or payload["total_count"] != len(artifacts):
        return None
    if any(not isinstance(item, Mapping) for item in artifacts):
        return None
    if any(item.get("name") == "carrier-plan.json" for item in artifacts):
        return None
    prior = [item for item in artifacts if item.get("name") == _APPLICATION_RECOVERY_ARTIFACT]
    if len(prior) != (1 if predecessor_recovery else 0):
        return None
    if prior:
        prior_run = _as_mapping(prior[0].get("workflow_run"))
        if (
            prior_run is None
            or not _matches_required_fields(prior_run, {"id": run_id, "head_sha": run_head_sha})
            or prior[0].get("expired") is not False
            or not isinstance(prior[0].get("digest"), str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", cast(str, prior[0]["digest"])) is None
        ):
            return None
    candidates = [
        item
        for item in artifacts
        if isinstance(item, Mapping) and item.get("name") in _APPLICATION_EXCEPTION_ARTIFACTS
    ]
    if len(candidates) != 1:
        return None
    # The shared verified-bytes reader owns exact Artifact run/head identity.
    return candidates[0]


def _qualified_exception_document(
    document: object,
    *,
    repository: str,
    record: ApplicationDecisionRecord,
    run: Mapping[str, object],
    run_id: int,
    run_attempt: int,
) -> Mapping[str, object] | None:
    """Canonical typed identity; diagnostic strings never determine admission."""

    if not isinstance(document, Mapping) or set(document) != _EXCEPTION_DOCUMENT_KEYS:
        return None
    expected = {
        "schema": "scheduled-agent-execution-exception/v1",
        "repository": repository,
        "issue_number": record.issue_number,
        "role": record.role,
        "action": record.action,
        "change": record.change,
        "revision": run.get("head_sha"),
        "request_comment_id": record.request_comment_id,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "classification": "UNCLASSIFIED_EXECUTION_EXCEPTION",
    }
    if not _matches_required_fields(document, expected):
        return None
    trigger = _strict_positive_int(document.get("trigger_comment_id"))
    if trigger is None or run.get("display_title") != f"Scheduled Agent Application {trigger}":
        return None
    if document.get("mutation_status") not in {
        "UNKNOWN_REQUIRES_FRESH_RECONCILIATION",
        "NO_APPLICATION_WRITE_ATTEMPTED",
    }:
        return None
    if document.get("attempted_operation") != document.get("unfinished_boundary"):
        return None
    if any(
        not isinstance(document.get(key), str)
        for key in ("exception_type", "raw_error", "raw_traceback", "attempted_operation")
    ):
        return None
    return document


def read_application_exception_artifact(
    repository: str,
    token: str,
    *,
    run_id: int,
    run_attempt: int,
    job_id: int,
    record: ApplicationDecisionRecord,
    accepted_decision_sha256: str,
    read: Callable[[str, str, str], object] | None = None,
    artifact_reader: Callable[[str, str, str], bytes] | None = None,
    strict_read: bool = False,
) -> ApplicationExceptionArtifact | None:
    """Qualify *actual* exception evidence without inferring an unwritten Effect.

    Only a terminal failed apply step with no downstream writer qualifies.
    This reader never turns an exception string into a recovery predicate.
    """

    def unavailable() -> ApplicationExceptionArtifact | None:
        if strict_read:
            raise RuntimeError("application exception evidence unavailable")
        return None

    api_read = _github_json if read is None else read
    download = read_github_artifact_bytes if artifact_reader is None else artifact_reader
    if (
        not all(_strict_positive_int(v) is not None for v in (run_id, run_attempt, job_id))
        or record.disposition != "ACCEPTED"
        or re.fullmatch(r"[0-9a-f]{64}", accepted_decision_sha256) is None
    ):
        return unavailable()
    qualified = _qualified_exception_apply_run(
        repository,
        token,
        run_id=run_id,
        run_attempt=run_attempt,
        job_id=job_id,
        read=api_read,
    )
    if qualified is None:
        return unavailable()
    run, predecessor_recovery = qualified
    artifact = _qualified_exception_artifact_metadata(
        api_read(repository, token, f"actions/runs/{run_id}/artifacts?per_page=100"),
        run_id=run_id,
        run_head_sha=cast(str, run["head_sha"]),
        predecessor_recovery=predecessor_recovery,
    )
    if artifact is None:
        return unavailable()
    verified = _read_verified_application_artifact(
        repository,
        token,
        metadata=artifact,
        run_id=run_id,
        run_head_sha=cast(str, run["head_sha"]),
        download=download,
    )
    if verified is None:
        return unavailable()
    artifact_id, digest, raw_document = verified
    document = _qualified_exception_document(
        raw_document,
        repository=repository,
        record=record,
        run=run,
        run_id=run_id,
        run_attempt=run_attempt,
    )
    if document is None:
        return unavailable()
    episode = _canonical_sha256(
        {
            "schema": "scheduled-agent-recovery-episode/v1",
            "repository": repository,
            "issue_number": record.issue_number,
            "request_comment_id": record.request_comment_id,
            "accepted_decision_sha256": accepted_decision_sha256,
        }
    )
    return ApplicationExceptionArtifact(
        run_id,
        run_attempt,
        job_id,
        artifact_id,
        digest,
        record.request_comment_id,
        accepted_decision_sha256,
        _canonical_sha256(document),
        episode,
        document,
    )


def qualify_application_continuation_predecessor(
    repository: str,
    token: str,
    continuation: ApplicationContinuationRequest,
    *,
    current_comment_id: int,
    transport_issue_number: int,
    read: Callable[[str, str, str], object] | None = None,
    artifact_reader: Callable[[str, str, str], bytes] | None = None,
) -> ApplicationRecoveryArtifact | ApplicationExceptionArtifact | None:
    """Verify the exact prior artifact and reject duplicate continuation branches."""

    api_read = _github_json if read is None else read
    if _strict_positive_int(transport_issue_number) is None:
        return None
    # The accepted decision belongs to the formal Issue.  The continuation is
    # a bounded runtime-shard transport, never a formal Issue comment.
    decision_comments = _paged_github_list(
        repository,
        token,
        f"issues/{continuation.issue_number}/comments?sort=created&direction=asc",
    )
    transport_comments = _paged_github_list(
        repository,
        token,
        f"issues/{transport_issue_number}/comments?sort=created&direction=asc",
    )
    copies = []
    accepted_bodies = []
    for comment in decision_comments:
        if not isinstance(comment, Mapping):
            continue
        body = comment.get("body")
        if is_github_actions_comment(comment) and isinstance(body, str):
            record = parse_application_decision(body)
            if (
                record is not None
                and record.request_comment_id == continuation.original_request_comment_id
                and record.disposition == "ACCEPTED"
            ):
                accepted_bodies.append(body)
    trusted_current = False
    for comment in transport_comments:
        if not isinstance(comment, Mapping):
            continue
        body = comment.get("body")
        comment_id = _positive_int(comment.get("id"))
        parsed = parse_application_continuation_request(body) if isinstance(body, str) else None
        if (
            parsed is not None
            and parsed.continuation_correlation == continuation.continuation_correlation
            and comment_id is not None
        ):
            copies.append(comment_id)
            if comment_id == current_comment_id:
                trusted_current = (
                    _trusted_connector_comment(comment, repository.split("/", 1)[0])
                    and parsed == continuation
                )
    if (
        len(copies) != 1
        or copies[0] != current_comment_id
        or not trusted_current
        or len(accepted_bodies) != 1
    ):
        return None
    decision_sha256 = hashlib.sha256(accepted_bodies[0].encode("utf-8")).hexdigest()
    if decision_sha256 != continuation.accepted_decision_sha256:
        return None
    accepted_record = parse_application_decision(accepted_bodies[0])
    if accepted_record is None:
        return None
    evidence: ApplicationRecoveryArtifact | ApplicationExceptionArtifact | None = (
        read_application_recovery_artifact(
            repository,
            token,
            run_id=continuation.predecessor_run_id,
            run_attempt=continuation.predecessor_run_attempt,
            job_id=continuation.predecessor_job_id,
            request_comment_id=continuation.original_request_comment_id,
            accepted_decision_sha256=decision_sha256,
            read=api_read,
            artifact_reader=artifact_reader,
        )
    )
    if evidence is None:
        evidence = read_application_exception_artifact(
            repository,
            token,
            run_id=continuation.predecessor_run_id,
            run_attempt=continuation.predecessor_run_attempt,
            job_id=continuation.predecessor_job_id,
            record=accepted_record,
            accepted_decision_sha256=decision_sha256,
            read=api_read,
            artifact_reader=artifact_reader,
        )
    if (
        evidence is None
        or evidence.artifact_id != continuation.predecessor_artifact_id
        or evidence.artifact_digest != continuation.predecessor_artifact_digest
        or evidence.failure_evidence_sha256 != continuation.failure_evidence_sha256
        or evidence.recovery_episode_sha256 != continuation.recovery_episode_sha256
        or (
            isinstance(evidence, ApplicationRecoveryArtifact)
            and evidence.failure_evidence_sha256
            in cast(list[str], evidence.document["prior_failure_evidence_sha256"])
        )
    ):
        return None
    proof = (
        classify_application_exception_recovery(
            record=accepted_record, artifact=evidence, repository=repository, token=token
        )
        if isinstance(evidence, ApplicationExceptionArtifact)
        else (
            classify_post_effect_result_recovery(
                record=accepted_record, artifact=evidence, repository=repository, token=token
            )
            if not evidence.continuation_eligible
            else None
        )
    )
    if proof is not None and proof.continuation != "CONTINUE":
        return None
    return evidence


def _public_failure_diagnostics(result: ApplyResult) -> dict[str, object] | None:
    """Expose bounded effect failure identity in run logs, without raw payloads.

    Logs aid diagnosis if artifact persistence fails, but cannot serve as a
    qualified recovery artifact or authorize replay of a completed job.
    """
    evidence = result.recovery_evidence
    if result.applied or evidence is None:
        return None
    summary: dict[str, object] = {
        "failed_effect_index": evidence.failed_effect_index,
        "failed_effect_kind": evidence.failed_effect_kind,
        "failed_effect_sha256": evidence.failed_effect_sha256,
        "completed_effect_indexes": list(evidence.completed_effect_indexes),
        "completed_effect_sha256": list(evidence.completed_effect_sha256),
        "mutation_status": evidence.mutation_status,
        "unfinished_boundary": evidence.unfinished_boundary,
        "failure_evidence_sha256": _canonical_sha256(_recovery_failure_document(result)),
    }
    rejection = evidence.rejection
    if rejection is not None:
        summary["rejection_classification"] = str(
            getattr(rejection.classification, "value", rejection.classification)
        )
        try:
            expected = json.loads(rejection.expected)
            observed = json.loads(rejection.observed)
        except (TypeError, ValueError, json.JSONDecodeError):
            expected = observed = None
        # Both the exact internal proof envelope and a known reason must match:
        # a generic guard rejection carries untrusted effect.payload_json in
        # observed and must never be promoted to public diagnostic text.
        if (
            isinstance(expected, Mapping)
            and set(expected) == {"materialization_proof", "accepted_intent"}
            and expected.get("materialization_proof") == ["COMPLETE", "INCOMPLETE"]
            and isinstance(expected.get("accepted_intent"), bool)
            and isinstance(observed, Mapping)
            and set(observed) == {"disposition", "reason"}
            and observed.get("disposition") == "CONTRADICTORY"
            and observed.get("reason")
            in {
                "materialization missing work preimage is stale",
                "materialization missing work overlaps default advance",
            }
        ):
            summary["guard_reason"] = observed["reason"]
        # Merge acceptance itself constructs this bounded envelope. Expose only
        # known predicate names, never the PR/comment/payload or raw transport
        # response. It distinguishes a durable gate failure from API failure.
        merge_predicates = frozenset(
            {
                "complete",
                "current_carrier",
                "exact_head",
                "exact_review",
                "required_checks",
                "non_closing_linkage",
                "native_closing_preflight",
                "no_contradiction",
                "human_freshness",
            }
        )
        if (
            isinstance(expected, Mapping)
            and set(expected) == {"issue", "change", "pr", "head", "failed_predicates"}
            and expected.get("failed_predicates") == []
            and isinstance(observed, Mapping)
            and set(observed) == {"failed_predicates", "snapshot"}
            and isinstance(observed.get("failed_predicates"), list)
            and bool(observed["failed_predicates"])
            and all(
                isinstance(item, str) and item in merge_predicates
                for item in observed["failed_predicates"]
            )
        ):
            summary["merge_failed_predicates"] = sorted(set(observed["failed_predicates"]))
    return summary


def _recovery_failure_document(result: ApplyResult) -> dict[str, object]:
    recovery = result.recovery_evidence
    if recovery is None:
        if result.carrier_plan is not None:
            return {
                "reason": result.reason,
                "mutation_status": "not-complete",
                "unfinished_boundary": "carrier-required",
                "carrier_plan_id": result.carrier_plan.plan_id,
                "completed_effect_indexes": [],
                "completed_effect_sha256": [],
            }
        return {
            "reason": result.reason,
            "mutation_status": "unknown",
            "unfinished_boundary": "application-result",
            "completed_effect_indexes": [],
            "completed_effect_sha256": [],
        }
    rejection_document = None
    if recovery.rejection is not None:
        classification = getattr(
            recovery.rejection.classification,
            "value",
            recovery.rejection.classification,
        )
        rejection_document = {
            "classification": str(classification),
            "expected": recovery.rejection.expected,
            "observed": recovery.rejection.observed,
        }
    failure: dict[str, object] = {
        "reason": result.reason,
        "failed_effect_index": recovery.failed_effect_index,
        "failed_effect_kind": recovery.failed_effect_kind,
        "failed_effect_sha256": recovery.failed_effect_sha256,
        "completed_effect_indexes": list(recovery.completed_effect_indexes),
        "completed_effect_sha256": list(recovery.completed_effect_sha256),
        "mutation_status": recovery.mutation_status,
        "unfinished_boundary": recovery.unfinished_boundary,
        "rejection": rejection_document,
    }
    # Capture only observed operational failure facts. This does not decide
    # whether the same accepted Effect was called in an earlier native run.
    if recovery.operation_stage is not None:
        failure["operation_stage"] = recovery.operation_stage
        failure["write_call_entered"] = recovery.write_call_entered
    if recovery.raw_error is not None:
        failure["raw_error"] = recovery.raw_error
    return failure


def _attempted_effect_checkpoint(
    batch: EffectBatch,
    recovery: EffectRecoveryEvidence,
) -> list[dict[str, object]] | None:
    """Snapshot the exact attempted prefix, never a later state-dependent projection.

    This is part of the existing content-addressed recovery artifact, not a
    separate registry. The hashes already emitted by the Effect engine must
    match the snapshot before it can qualify a read-only observation.
    """

    index = recovery.failed_effect_index
    if index < 0 or index > len(batch.effects) or batch.typed_result is None:
        return None
    attempted = list(batch.effects[: min(index + 1, len(batch.effects))])
    if index == len(batch.effects):
        attempted.append(
            derived_transition_effect(
                issue_number=batch.source.issue_number,
                change=batch.typed_result.change,
                successor=next_action(batch.typed_result.action, batch.typed_result.result),
            )
        )
    if (
        not attempted
        or attempted[-1].kind != recovery.failed_effect_kind
        or hashlib.sha256(attempted[-1].payload_json.encode()).hexdigest()
        != recovery.failed_effect_sha256
        or any(
            position >= len(batch.effects)
            or hashlib.sha256(batch.effects[position].payload_json.encode()).hexdigest() != digest
            for position, digest in zip(
                recovery.completed_effect_indexes,
                recovery.completed_effect_sha256,
                strict=True,
            )
        )
    ):
        return None
    return [
        {"kind": effect.kind, "payload_json": effect.payload_json, "derived": effect.derived}
        for effect in attempted
    ]


def _verified_attempted_effect_checkpoint(
    failure: Mapping[str, object],
    *,
    source: WorkerRequest,
) -> tuple[StagedEffect, ...] | None:
    """Validate stored write identity before invoking the shared observer."""

    snapshot = failure.get("attempted_effects")
    index = failure.get("failed_effect_index")
    completed = failure.get("completed_effect_indexes")
    hashes = failure.get("completed_effect_sha256")
    if (
        not isinstance(snapshot, list)
        or type(index) is not int
        or index < 0
        or len(snapshot) != index + 1
        or not isinstance(completed, list)
        or not isinstance(hashes, list)
        or len(completed) != len(hashes)
        or len(snapshot) > 256
    ):
        return None
    attempted: list[StagedEffect] = []
    for position, entry in enumerate(snapshot):
        if (
            not isinstance(entry, Mapping)
            or set(entry) != {"kind", "payload_json", "derived"}
            or not isinstance(entry.get("kind"), str)
            or not isinstance(entry.get("payload_json"), str)
            or not isinstance(entry.get("derived"), bool)
            or (position < index and entry["derived"])
        ):
            return None
        effect = StagedEffect(
            kind=cast(str, entry["kind"]),
            payload_json=cast(str, entry["payload_json"]),
            derived=cast(bool, entry["derived"]),
        )
        payload = _effect_payload({"kind": effect.kind, "payload_json": effect.payload_json})
        if payload is None or payload.get("issue_number") != source.issue_number:
            return None
        attempted.append(effect)
    if (
        attempted[-1].kind != failure.get("failed_effect_kind")
        or hashlib.sha256(attempted[-1].payload_json.encode()).hexdigest()
        != failure.get("failed_effect_sha256")
        or any(
            type(position) is not int
            or position < 0
            or position >= index
            or hashlib.sha256(attempted[position].payload_json.encode()).hexdigest() != digest
            for position, digest in zip(completed, hashes, strict=True)
        )
    ):
        return None
    return tuple(attempted)


def _attempted_formal_identity(
    attempted: Sequence[StagedEffect],
    *,
    source: WorkerRequest,
    change: str,
    result_kind: str,
    request_comment_id: int,
) -> tuple[StagedEffect, str, str] | None:
    """Read one exact original formal Effect, revision and body from its checkpoint.

    A later continuation's default-branch HEAD is not the revision of an
    already-committed formal comment. This identity must survive *subsequent*
    interrupted or zero-write-rejected successor attempts as well.
    """

    formals: list[tuple[StagedEffect, str]] = []
    for effect in attempted:
        if effect.kind != "issue-comment":
            continue
        payload = _effect_payload({"kind": effect.kind, "payload_json": effect.payload_json})
        body = None if payload is None else payload.get("body")
        if isinstance(body, str) and _marker(body) in _FORMAL_RESULT_MARKERS:
            formals.append((effect, body))
    if not formals:
        return None
    if len(formals) != 1:
        raise RuntimeError("accepted attempted prefix has ambiguous formal result")
    formal_effect, body = formals[0]
    revision = _field(body, "Default-Branch-Revision")
    if (
        not isinstance(revision, str)
        or _SHA.fullmatch(revision) is None
        or _marker(body) != _expected_formal_marker(source)
        or _field(body, "Workflow") != f"#{source.issue_number}"
        or _field(body, "Change") != change
        or _field(body, "Action") != source.action
        or _field(body, "Role") != source.role
        or _field(body, "Result") != result_kind.upper().replace("-", "_")
        or _field(body, "Application-Correlation")
        != formal_application_correlation(
            source,
            change=change,
            result_kind=result_kind,
            current_revision=revision,
            request_comment_id=request_comment_id,
        )
    ):
        raise RuntimeError("accepted attempted formal identity is invalid")
    return formal_effect, revision, body


def _retain_completed_accepted_formal_effect(
    raw_projection: str,
    *,
    failure: Mapping[str, object],
    source: WorkerRequest,
    change: str,
    result_kind: str,
    request_comment_id: int,
) -> tuple[str, str] | None:
    """Reuse the *original* durable formal Effect, never synthesize a R2 copy.

    The fresh worker projection remains the source for new unattempted Effects
    and the Action model remains the sole successor authority. Only an exact
    formal comment from the verified attempted prefix may replace its newly
    rendered counterpart; other current consequences are not rewritten.
    """

    attempted = _verified_attempted_effect_checkpoint(failure, source=source)
    if attempted is None:
        return None
    formal_identity = _attempted_formal_identity(
        attempted,
        source=source,
        change=change,
        result_kind=result_kind,
        request_comment_id=request_comment_id,
    )
    if formal_identity is None:
        return None
    original, original_revision, original_body = formal_identity
    if failure.get("attempt_revision") != original_revision:
        raise RuntimeError("accepted attempted formal revision is inconsistent")
    original_correlation = formal_application_correlation(
        source,
        change=change,
        result_kind=result_kind,
        current_revision=original_revision,
        request_comment_id=request_comment_id,
    )
    decoded = json.loads(raw_projection)
    if not isinstance(decoded, dict):
        raise RuntimeError("current formal projection is unavailable")
    requested = decoded.get("requested_effects")
    if not isinstance(requested, list):
        raise RuntimeError("current requested effects are unavailable")
    formal_indexes: list[int] = []
    for index, raw_effect in enumerate(requested):
        if not isinstance(raw_effect, Mapping):
            raise RuntimeError("current projected effect is invalid")
        payload = _effect_payload(raw_effect)
        body = None if payload is None else payload.get("body")
        if (
            raw_effect.get("kind") == "issue-comment"
            and isinstance(body, str)
            and _marker(body) in _FORMAL_RESULT_MARKERS
        ):
            formal_indexes.append(index)
    if len(formal_indexes) != 1:
        # A previously committed formal result cannot authorize an unrelated
        # phase to be reopened or a new control write inserted ahead of it.
        raise RuntimeError("completed formal result has no unique current projection")
    if any(
        isinstance(effect, Mapping) and effect.get("kind") == GITHUB_MUTATION_KIND
        for effect in requested
    ):
        raise RuntimeError("completed formal result conflicts with a new control phase")
    updated = list(requested)
    updated[formal_indexes[0]] = {
        "kind": original.kind,
        "payload_json": original.payload_json,
    }
    decoded["requested_effects"] = updated
    decoded["result_content"] = original_body
    return json.dumps(decoded, sort_keys=True, separators=(",", ":")), original_correlation


def _accepted_recovery_boundary(
    evidence: Mapping[str, object],
) -> Literal["CARRIER", "ZERO_WRITE_REJECTION", "READ_ONLY", "POST_EFFECT_RESULT", "NONE"]:
    """One structural eligibility contract for producer and artifact reader.

    Eligibility starts a *read*, not a retry permission. Unknown attempted
    effects and known zero-write-rejected suffixes both require a proven
    original prefix before normal current guards may authorize later writes.
    Artifact prose never upgrades an unsupported boundary into permission.
    """

    if (
        evidence.get("unfinished_boundary") == "application-result"
        and evidence.get("mutation_status") == "unknown"
        and evidence.get("reason") == "applied"
        and evidence.get("completed_effect_indexes") == []
        and evidence.get("completed_effect_sha256") == []
        and set(evidence)
        == {
            "unfinished_boundary",
            "mutation_status",
            "reason",
            "completed_effect_indexes",
            "completed_effect_sha256",
        }
    ):
        # Legacy post-effect, pre-consequence interruption. This is only a
        # candidate for a fresh read-only proof of a single first-activation
        # materialization, never permission to replay its GitHub mutation.
        return "POST_EFFECT_RESULT"
    if (
        evidence.get("unfinished_boundary") == "carrier-required"
        and evidence.get("mutation_status") == "not-complete"
        and evidence.get("reason") in {"carrier_required", "carrier-required"}
        and isinstance(evidence.get("carrier_plan_id"), str)
        and bool(evidence["carrier_plan_id"])
        and evidence.get("completed_effect_indexes") == []
        and evidence.get("completed_effect_sha256") == []
    ):
        return "CARRIER"
    rejection = evidence.get("rejection")
    known_rejection = (
        evidence.get("unfinished_boundary") == "effect-precondition"
        and evidence.get("mutation_status") == "not-complete"
        and isinstance(rejection, Mapping)
        and rejection.get("classification") == "effect-precondition-unsatisfied"
    )
    indexes = evidence.get("completed_effect_indexes")
    hashes = evidence.get("completed_effect_sha256")
    exact_frontier = (
        isinstance(indexes, list)
        and isinstance(hashes, list)
        and len(indexes) == len(hashes)
        and all(type(index) is int and index >= 0 for index in indexes)
        and indexes == sorted(set(indexes))
        and all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes)
    )
    exact_failure = (
        type(evidence.get("failed_effect_index")) is int
        and cast(int, evidence["failed_effect_index"]) >= 0
        and isinstance(evidence.get("failed_effect_kind"), str)
        and bool(evidence["failed_effect_kind"])
        and isinstance(evidence.get("failed_effect_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", cast(str, evidence["failed_effect_sha256"])) is not None
    )
    # A catchable guard/read exception proves this Effect was *not called*
    # by the sequential engine. It does not prove the preceding writes;
    # those still require fresh exact postconditions on every continuation.
    unattempted_exception = (
        evidence.get("unfinished_boundary") == "effect-precondition-exception"
        and evidence.get("mutation_status") == "not-complete"
        and evidence.get("rejection") is None
    )
    if known_rejection and exact_frontier and exact_failure and not indexes:
        return "ZERO_WRITE_REJECTION"
    if exact_frontier and exact_failure:
        if unattempted_exception or (known_rejection and indexes):
            return "READ_ONLY"
        if evidence.get("mutation_status") == "unknown" and evidence.get("unfinished_boundary") in {
            "effect-postcondition",
            "derived-effect-postcondition",
            "effect-reconciliation",
        }:
            return "READ_ONLY"
    return "NONE"


def _accepted_predecessor_disposition(
    predecessor: ApplicationRecoveryArtifact | ApplicationExceptionArtifact,
) -> Literal["RECONCILE_EFFECTS", "ZERO_WRITE_REJECTION", "INDETERMINATE"]:
    """Preserve the original accepted intent and select only lawful next work."""

    if isinstance(predecessor, ApplicationExceptionArtifact):
        return "INDETERMINATE"
    evidence = predecessor.document.get("failure_evidence")
    if not isinstance(evidence, Mapping):
        return "INDETERMINATE"
    boundary = _accepted_recovery_boundary(evidence)
    if not predecessor.continuation_eligible and boundary != "POST_EFFECT_RESULT":
        return "INDETERMINATE"
    if boundary == "CARRIER":
        return "RECONCILE_EFFECTS"
    if boundary == "ZERO_WRITE_REJECTION":
        return "ZERO_WRITE_REJECTION"
    return "INDETERMINATE"


@dataclass(frozen=True)
class AcceptedActivationEffectIdentity:
    """Qualification of the *accepted* write, not a fresh Effect-array shape.

    The index is only an address in the current projection for the existing
    Effect engine.  It never identifies or authorizes the original write.
    """

    disposition: Literal["EXACT", "MISSING", "AMBIGUOUS", "UNSAFE"]
    effect: StagedEffect | None = None
    projected_index: int | None = None


# The one domain decision table; downstream owners may map a typed rejection
# to their own output protocol but must never change its recovery admission.
_POST_EFFECT_ADMISSION: dict[
    Literal["COMPLETE", "MISSING_PR", "NOT_APPLIED", "INDETERMINATE", "UNSAFE"],
    Literal["CONTINUE", "OBSERVE", "REJECT"],
] = {
    "COMPLETE": "CONTINUE",
    "MISSING_PR": "CONTINUE",
    "NOT_APPLIED": "REJECT",
    "INDETERMINATE": "OBSERVE",
    "UNSAFE": "REJECT",
}


RecoveryProofDisposition = Literal["SATISFIED", "NOT_APPLIED", "UNKNOWN", "CONFLICT"]


@dataclass(frozen=True)
class CompleteNeverCalledWitness:
    """Exact accepted-intent-wide no-call chain, never a write authorization."""

    request_comment_id: int
    target_index: int
    accepted_decision_sha256: str
    artifact_chain: tuple[tuple[int, int, int], ...]


@dataclass(frozen=True)
class TypedEvidenceError:
    """Operational evidence Result.Err, not domain proof of non-application."""

    category: Literal["UNKNOWN", "CONFLICT"]
    stage: str
    detail: str
    request_comment_id: int
    artifact_id: int | None = None


AcceptedNeverCalledEvidence = CompleteNeverCalledWitness | TypedEvidenceError


@dataclass(frozen=True)
class RecoveryEvidenceNode:
    """Typed per-obligation IR fact, never an Action or write authorization.

    A later formal-result node can depend on shared original-Effect nodes,
    and a successor on formal-result proof. Evidence remains invocation-local.
    """

    obligation: Literal["ORIGINAL_EFFECT", "FORMAL_RESULT", "SUCCESSOR"]
    effect: StagedEffect | None
    final_postcondition: bool | None
    never_called_evidence: AcceptedNeverCalledEvidence | None = None
    source_conflict: bool = False
    depends_on: tuple[RecoveryEvidenceNode, ...] = ()


def evaluate_recovery_evidence(node: RecoveryEvidenceNode) -> RecoveryProofDisposition:
    """Pure DAG proof: shared facts once; conflicts dominate; no write permission.

    A positive exact final state does not require historical attempt inventory,
    but a provenance contradiction cannot be ignored. A *missing* descendant
    is NOT_APPLIED only when all prerequisites are SATISFIED and the descendant
    has its own positive never-called witness. Cycles are invalid evidence.
    """

    memo: dict[int, RecoveryProofDisposition] = {}
    visiting: set[int] = set()

    def evaluate(fact: RecoveryEvidenceNode) -> RecoveryProofDisposition:
        identity = id(fact)
        if identity in visiting:
            return "CONFLICT"
        if identity in memo:
            return memo[identity]
        visiting.add(identity)
        dependencies = tuple(evaluate(parent) for parent in fact.depends_on)
        visiting.remove(identity)
        if (
            fact.source_conflict
            or "CONFLICT" in dependencies
            or (
                isinstance(fact.never_called_evidence, TypedEvidenceError)
                and fact.never_called_evidence.category == "CONFLICT"
            )
        ):
            disposition: RecoveryProofDisposition = "CONFLICT"
        elif any(result != "SATISFIED" for result in dependencies):
            disposition = "UNKNOWN"
        elif fact.final_postcondition is True:
            disposition = "SATISFIED"
        elif fact.final_postcondition is False and isinstance(
            fact.never_called_evidence, CompleteNeverCalledWitness
        ):
            disposition = "NOT_APPLIED"
        else:
            disposition = "UNKNOWN"
        memo[identity] = disposition
        return disposition

    return evaluate(node)


def _recovery_obligation(
    effect: StagedEffect, source: WorkerRequest
) -> Literal["ORIGINAL_EFFECT", "FORMAL_RESULT", "SUCCESSOR"]:
    """Project an existing Effect identity into one typed DAG obligation."""

    if effect.derived:
        return "SUCCESSOR"
    if effect.kind == "issue-comment":
        payload = _effect_payload({"kind": effect.kind, "payload_json": effect.payload_json})
        body = None if payload is None else payload.get("body")
        if isinstance(body, str) and _marker(body) == _expected_formal_marker(source):
            return "FORMAL_RESULT"
    return "ORIGINAL_EFFECT"


def _observe_accepted_effect_prefix(
    effects: Sequence[StagedEffect],
    observe_postcondition: Callable[[StagedEffect], bool],
    *,
    source: WorkerRequest,
) -> tuple[RecoveryEvidenceNode, ...] | None:
    """One positive proof reader for original and Application-owned obligations."""

    nodes: list[RecoveryEvidenceNode] = []
    for effect in effects:
        fact = RecoveryEvidenceNode(
            _recovery_obligation(effect, source),
            effect,
            final_postcondition=observe_postcondition(effect),
        )
        if evaluate_recovery_evidence(fact) != "SATISFIED":
            return None
        nodes.append(fact)
    return tuple(nodes)


@dataclass(frozen=True)
class AcceptedPostEffectProof:
    """Read-only recovery outcome from the canonical materialization owner."""

    disposition: Literal["COMPLETE", "MISSING_PR", "NOT_APPLIED", "INDETERMINATE", "UNSAFE"]
    reason: str
    carrier_plan: CarrierPlan | None = None
    # Independent leaf proof. It never grants continuation or replay authority.
    original_effect_proof: RecoveryProofDisposition | None = None

    def __post_init__(self) -> None:
        if (self.disposition == "MISSING_PR") != (self.carrier_plan is not None):
            raise ValueError("only an exact missing-PR recovery may carry a CarrierPlan")

    @property
    def continuation(self) -> Literal["CONTINUE", "OBSERVE", "REJECT"]:
        """One contract decision table for dispatch and continuation admission."""

        return _POST_EFFECT_ADMISSION[self.disposition]


def _accepted_activation_effect_identity(
    accepted_raw: str,
    *,
    source: WorkerRequest,
    change: str,
    projected_raw: str | None = None,
) -> AcceptedActivationEffectIdentity:
    """Bind the one uncertain materialization to immutable accepted intent.

    Every original Effect must be accounted for: an unknown historical write
    cannot be silently ignored.  The Application-owned formal comment is not
    in that immutable set and does not change its identity or cardinality.
    """

    accepted = parse_effect_batch(accepted_raw, source, authorized_change=change)
    originals: list[StagedEffect] = []
    for effect in accepted.effects:
        if effect.kind != GITHUB_MUTATION_KIND:
            return AcceptedActivationEffectIdentity("UNSAFE")
        payload = _effect_payload({"kind": effect.kind, "payload_json": effect.payload_json})
        if payload is None or payload.get("operation") != "application-materialize":
            return AcceptedActivationEffectIdentity("UNSAFE")
        if find_materialization_payload(payload, source) is None:
            return AcceptedActivationEffectIdentity("UNSAFE")
        originals.append(effect)

    if not originals:
        return AcceptedActivationEffectIdentity("MISSING")
    if len(originals) != 1:
        return AcceptedActivationEffectIdentity("AMBIGUOUS")
    original = originals[0]
    if projected_raw is None:
        return AcceptedActivationEffectIdentity("EXACT", original)

    projected = parse_effect_batch(projected_raw, source, authorized_change=change)
    original_payload = _effect_payload(
        {"kind": original.kind, "payload_json": original.payload_json}
    )
    matches: list[int] = []
    for index, effect in enumerate(projected.effects):
        if effect.kind != GITHUB_MUTATION_KIND:
            continue  # Application-derived formal result has its own owner.
        payload = _effect_payload({"kind": effect.kind, "payload_json": effect.payload_json})
        if payload != original_payload:
            return AcceptedActivationEffectIdentity("UNSAFE")
        matches.append(index)
    if not matches:
        return AcceptedActivationEffectIdentity("MISSING")
    if len(matches) != 1:
        return AcceptedActivationEffectIdentity("AMBIGUOUS")
    return AcceptedActivationEffectIdentity("EXACT", original, matches[0])


def _accepted_original_source_identity_error(
    record: ApplicationDecisionRecord,
    source: WorkerRequest,
) -> TypedEvidenceError | None:
    """Exact immutable ACCEPTED identity fact, shared before any source read."""
    if record.disposition == "ACCEPTED" and (record.issue_number, record.role, record.action) == (
        source.issue_number,
        source.role,
        source.action,
    ):
        return None
    return TypedEvidenceError(
        "CONFLICT",
        "ORIGINAL_SOURCE",
        "accepted original source identity conflicts",
        record.request_comment_id,
    )


def _qualified_accepted_original_effects(
    *,
    record: ApplicationDecisionRecord,
    source: WorkerRequest,
    raw_worker_result: str,
) -> EffectBatch | TypedEvidenceError:
    """One source-identity reader shared by accepted original proof stages.

    Source qualification is evidence, not a mutation or Action decision.
    The caller preserves the native read-only or post-effect stage boundary.
    """
    source_error = _accepted_original_source_identity_error(record, source)
    if source_error is not None:
        return source_error
    try:
        batch = parse_effect_batch(raw_worker_result, source, authorized_change=record.change)
    except (TypeError, ValueError, json.JSONDecodeError):
        return TypedEvidenceError(
            "CONFLICT",
            "ORIGINAL_PARSE",
            "accepted original Effect identity invalid",
            record.request_comment_id,
        )
    if batch.typed_result is None or batch.typed_result.result.kind.value != record.result_kind:
        return TypedEvidenceError(
            "CONFLICT",
            "ORIGINAL_RESULT",
            "accepted original result identity invalid",
            record.request_comment_id,
        )
    return batch


def _observe_accepted_post_effect_result(
    *,
    record: ApplicationDecisionRecord,
    source: WorkerRequest,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
) -> AcceptedPostEffectProof:
    """Reconcile original intent; do not treat an absent write as replayable.

    The existing materialization proof distinguishes COMPLETE, INCOMPLETE,
    UNKNOWN and CONTRADICTORY using fresh GitHub reads.  This adapter only
    translates those established outcomes into the recovery contract; it
    owns no independent state, effect registry or GitHub transport.
    """

    if (source, record.change, record.result_kind) != (
        WorkerRequest(record.issue_number, "lead", "propose-change"),
        "unset",
        _FIRST_ACTIVATION_RESULT,
    ):
        # Reuse the existing original Effect postcondition owner for every
        # other accepted Action, without classifying by the exception string.
        try:
            raw = _accepted_worker_result_for_continuation(
                accepted_intent=record,
                source=source,
                repository=repository,
                token=token,
                request_comment_id=record.request_comment_id,
            )
        except OSError:
            return AcceptedPostEffectProof(
                "INDETERMINATE", "accepted original Effect source proof unavailable"
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            return AcceptedPostEffectProof("UNSAFE", "accepted original Effect identity invalid")
        batch = _qualified_accepted_original_effects(
            record=record, source=source, raw_worker_result=raw
        )
        if isinstance(batch, TypedEvidenceError):
            return AcceptedPostEffectProof(
                "UNSAFE" if batch.category == "CONFLICT" else "INDETERMINATE",
                batch.detail,
            )
        if not batch.effects:
            # The signed accepted semantic projection may have omitted a
            # physical Effect. Verify its original request specifically at
            # this recovery gate, not during normal accepted continuation.
            try:
                verified_empty = _verified_zero_original_accepted_effects(
                    record=record, source=source, repository=repository, token=token
                )
            except OSError:
                verified_empty = False
            except (TypeError, ValueError):
                return AcceptedPostEffectProof(
                    "UNSAFE", "accepted zero-Effect source identity invalid"
                )
            return (
                AcceptedPostEffectProof("COMPLETE", "original empty Effect set proven")
                if verified_empty
                else AcceptedPostEffectProof(
                    "INDETERMINATE", "accepted zero-Effect source not proven"
                )
            )
        adapter = GitHubEffectAdapter(
            repository,
            token,
            source,
            authorized_change=record.change,
            current_revision=current_revision,
            expected_result_kind=record.result_kind,
            request_comment_id=record.request_comment_id,
            authorization_revision=record.authorization_revision,
            allow_pending_continuation=True,
            accepted_intent=True,
        )
        observed_originals = _observe_accepted_effect_prefix(
            batch.effects, adapter.observe_postcondition, source=source
        )
        if observed_originals is None:
            return AcceptedPostEffectProof(
                "INDETERMINATE", "accepted original Effect postconditions unproven"
            )
        return AcceptedPostEffectProof("COMPLETE", "accepted original Effects observed")
    accepted_raw = _accepted_worker_result_for_continuation(
        accepted_intent=record,
        source=source,
        repository=repository,
        token=token,
        request_comment_id=record.request_comment_id,
    )
    identity = _accepted_activation_effect_identity(
        accepted_raw, source=source, change=record.change
    )
    if identity.disposition != "EXACT" or identity.effect is None:
        return AcceptedPostEffectProof("UNSAFE", f"original identity: {identity.disposition}")
    payload = _effect_payload(
        {"kind": identity.effect.kind, "payload_json": identity.effect.payload_json}
    )
    if payload is None:
        return AcceptedPostEffectProof("UNSAFE", "original payload unavailable")
    materialization = find_materialization_payload(payload, source)
    if materialization is None:
        return AcceptedPostEffectProof("UNSAFE", "original materialization invalid")
    if (materialization.expected_change, materialization.base_sha) != (
        "unset",
        record.authorization_revision,
    ):
        return AcceptedPostEffectProof("UNSAFE", "accepted materialization contract mismatch")

    proof = prove_materialization(
        payload,
        source,
        repository=repository,
        token=token,
        current_revision=current_revision,
        default_branch=default_branch,
        accepted_authorization_revision=record.authorization_revision,
        allow_pending_continuation=True,
        accepted_intent=True,
    )
    if proof.carrier_plan is not None:
        return AcceptedPostEffectProof(
            "MISSING_PR", "accepted branch and content proven; only PR absent", proof.carrier_plan
        )
    # Canonical decision table. NOT_APPLIED is evidence of missing work, not
    # permission to replay an uncertain non-idempotent GitHub request.
    outcomes: dict[str, AcceptedPostEffectProof] = {
        "COMPLETE": AcceptedPostEffectProof("COMPLETE", "exact original effect observed"),
        "INCOMPLETE": AcceptedPostEffectProof("NOT_APPLIED", "original effect incomplete"),
        "UNKNOWN": AcceptedPostEffectProof(
            "INDETERMINATE", proof.reason or "GitHub proof unavailable"
        ),
        "CONTRADICTORY": AcceptedPostEffectProof(
            "UNSAFE", proof.reason or "original effect contradictory"
        ),
    }
    return outcomes[proof.disposition]


def _accepted_reconciliation_effect_projection(
    *,
    accepted_raw: str,
    projected_raw: str,
    source: WorkerRequest,
    change: str,
) -> tuple[str, int]:
    """Keep proven immutable originals ahead of fresh Application-owned formal work.

    The ordinary fresh planner may drop already-applied labels/updates. Its
    mutable list is not an immutable original Effect identity. This pure
    projection retains the original order; unexpected or reordered effects
    are never inferred to be a lawful successor.
    """

    original = parse_effect_batch(accepted_raw, source, authorized_change=change)
    projected = parse_effect_batch(projected_raw, source, authorized_change=change)
    if (
        original.typed_result is None
        or projected.typed_result is None
        or original.typed_result != projected.typed_result
    ):
        raise RuntimeError("accepted recovery semantic result has changed")
    originals = original.effects
    expected_index = 0
    suffix: list[StagedEffect] = []
    for candidate in projected.effects:
        if candidate in originals:
            index = originals.index(candidate)
            if index < expected_index:
                raise RuntimeError("accepted recovery original Effect order has changed")
            expected_index = index + 1
            if suffix:
                raise RuntimeError("accepted recovery Effect appears after a new suffix")
            continue
        payload = _effect_payload({"kind": candidate.kind, "payload_json": candidate.payload_json})
        body = None if payload is None else payload.get("body")
        if (
            candidate.kind != "issue-comment"
            or not isinstance(body, str)
            or _marker(body) not in _FORMAL_RESULT_MARKERS
            or suffix
        ):
            raise RuntimeError("accepted recovery has unqualified new Effect")
        suffix.append(candidate)
    if len(suffix) != 1:
        raise RuntimeError("accepted recovery formal consequence is not unique")
    # A semantic worker never owns a formal result. Its immutable Effects
    # are distinct from the single Application-derived consequence.
    if any(
        effect.kind == "issue-comment"
        and isinstance(
            (
                payload := _effect_payload(
                    {"kind": effect.kind, "payload_json": effect.payload_json}
                )
            ),
            Mapping,
        )
        and isinstance(payload.get("body"), str)
        and _marker(cast(str, payload["body"])) in _FORMAL_RESULT_MARKERS
        for effect in originals
    ):
        raise RuntimeError("accepted recovery includes a worker-owned formal result")

    decoded = json.loads(projected_raw)
    if not isinstance(decoded, dict):
        raise RuntimeError("accepted recovery projected result is not an object")
    decoded["requested_effects"] = [
        {"kind": effect.kind, "payload_json": effect.payload_json}
        for effect in (*originals, *suffix)
    ]
    return json.dumps(decoded, sort_keys=True, separators=(",", ":")), len(originals)


def _read_accepted_never_called_evidence(
    *,
    record: ApplicationDecisionRecord,
    source: WorkerRequest,
    artifact: ApplicationRecoveryArtifact | None,
    failed_index: int,
    repository: str,
    token: str,
) -> AcceptedNeverCalledEvidence:
    """Qualify historical facts; only the shared DAG decides NOT_APPLIED.

    Each predecessor is independently content-addressed and re-read. A
    run-local pre-call flag is never an accepted-intent-wide witness.
    This is a read adapter, not a policy, mutation guard, or retry permit.
    """

    def error(stage: str, detail: str, *, conflict: bool = False) -> TypedEvidenceError:
        return TypedEvidenceError(
            "CONFLICT" if conflict else "UNKNOWN",
            stage,
            detail,
            record.request_comment_id,
            None if artifact is None else artifact.artifact_id,
        )

    if artifact is None:
        return error("ARTIFACT", "qualified recovery artifact unavailable")
    if failed_index < 0:
        return error("FRONTIER", "invalid negative target index", conflict=True)
    try:
        original_raw = _accepted_worker_result_for_continuation(
            accepted_intent=record,
            source=source,
            repository=repository,
            token=token,
            request_comment_id=record.request_comment_id,
        )
        original = parse_effect_batch(original_raw, source, authorized_change=record.change)
    except (HTTPError, OSError):
        return error("SOURCE_GET", "original accepted source read unavailable")
    except (RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return error("SOURCE", "original accepted source unqualified")
    if original.typed_result is None or failed_index > len(original.effects) + 2:
        return error("SOURCE_IDENTITY", "immutable original result/frontier invalid", conflict=True)
    if not original.effects:
        try:
            verified_zero = _verified_zero_original_accepted_effects(
                record=record, source=source, repository=repository, token=token
            )
        except (HTTPError, OSError, RuntimeError, TypeError, ValueError):
            return error("ZERO_ORIGINAL_GET", "original physical Effect count unavailable")
        if not verified_zero:
            return error("ZERO_ORIGINAL", "zero physical original Effects not proven")

    current = artifact
    seen: set[tuple[int, int, int]] = set()
    chain: list[tuple[int, int, int]] = []
    while True:
        identity = (current.run_id, current.run_attempt, current.artifact_id)
        document = current.document
        failure = document.get("failure_evidence")
        if identity in seen:
            return error("CHAIN", "repeated native attempt identity", conflict=True)
        if (
            current.request_comment_id != record.request_comment_id
            or document.get("issue_number") != record.issue_number
            or document.get("role") != record.role
            or document.get("action") != record.action
            or document.get("authorization_revision") != record.authorization_revision
            or not isinstance(failure, Mapping)
            or _accepted_recovery_boundary(failure) != "READ_ONLY"
        ):
            return error("CHAIN_IDENTITY", "accepted source/stage contradicts chain", conflict=True)
        seen.add(identity)
        chain.append(identity)
        attempted = _verified_attempted_effect_checkpoint(failure, source=source)
        index = failure.get("failed_effect_index")
        if attempted is None or type(index) is not int:
            return error("CHECKPOINT", "attempted Effect checkpoint invalid", conflict=True)
        if index > failed_index:
            return error("ATTEMPTED", "a prior attempt crossed the claimed uncalled frontier")
        if any(
            effect != original.effects[position]
            for position, effect in enumerate(attempted)
            if position < len(original.effects)
        ):
            return error("ORIGINAL_IDENTITY", "immutable original Effect mismatch", conflict=True)
        derived_tail = attempted[len(original.effects) :]
        if derived_tail:
            try:
                formal_identity = _attempted_formal_identity(
                    attempted,
                    source=source,
                    change=record.change,
                    result_kind=record.result_kind,
                    request_comment_id=record.request_comment_id,
                )
                expected_derived = derived_transition_effect(
                    issue_number=source.issue_number,
                    change=record.change,
                    successor=next_action(
                        original.typed_result.action, original.typed_result.result
                    ),
                )
            except (RuntimeError, TypeError, ValueError):
                return error(
                    "FORMAL_IDENTITY",
                    "formal or successor identity invalid",
                    conflict=True,
                )
            if (
                formal_identity is None
                or failure.get("attempt_revision") != formal_identity[1]
                or len(derived_tail) > 2
                or (len(derived_tail) == 2 and derived_tail[1] != expected_derived)
            ):
                return error(
                    "FORMAL_IDENTITY",
                    "Application-derived Effect mismatch",
                    conflict=True,
                )
        if index == failed_index and not (
            failure.get("mutation_status") == "not-complete"
            and failure.get("unfinished_boundary")
            in {"effect-precondition", "effect-precondition-exception"}
            and failure.get("write_call_entered") is False
        ):
            return error("CALL_ENTRY", "target Effect may already have been called")

        if current.recovery_attempt == 1:
            if (
                current.run_attempt != 1
                or document.get("predecessor") is not None
                or document.get("trigger_comment_id") != record.request_comment_id
                or document.get("prior_failure_evidence_sha256") != []
            ):
                return error("ROOT", "first native attempt identity invalid", conflict=True)
            from investment_strategy.issue_comment_bridge import _application_runs

            try:
                runs = _application_runs(
                    repository, token, record.request_comment_id, read=_github_json
                )
            except (HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
                return error("RUN_INVENTORY", "complete original run inventory unavailable")
            if not (
                runs is not None
                and len(runs) == 1
                and runs[0].get("id") == current.run_id
                and runs[0].get("run_attempt") == 1
            ):
                return error("RUN_INVENTORY", "other or incomplete native attempt history")
            return CompleteNeverCalledWitness(
                record.request_comment_id,
                failed_index,
                artifact.accepted_decision_sha256,
                tuple(chain),
            )

        predecessor = document.get("predecessor")
        previous_hashes = document.get("prior_failure_evidence_sha256")
        if not isinstance(predecessor, Mapping) or not isinstance(previous_hashes, list):
            return error("PREDECESSOR", "prior chain pointers are missing")
        try:
            previous = read_application_recovery_artifact(
                repository,
                token,
                run_id=cast(int, predecessor["run_id"]),
                run_attempt=cast(int, predecessor["run_attempt"]),
                job_id=cast(int, predecessor["job_id"]),
                request_comment_id=record.request_comment_id,
                accepted_decision_sha256=current.accepted_decision_sha256,
                strict_read=True,
            )
        except (HTTPError, OSError, RuntimeError, KeyError, TypeError, ValueError):
            return error("PREDECESSOR_GET", "prior native Artifact unavailable")
        if previous is None:
            return error("PREDECESSOR_GET", "prior native Artifact missing")
        if (
            previous.recovery_attempt != current.recovery_attempt - 1
            or previous.artifact_id != predecessor.get("artifact_id")
            or previous.artifact_digest != predecessor.get("artifact_digest")
            or previous.failure_evidence_sha256 != predecessor.get("failure_evidence_sha256")
            or previous.recovery_episode_sha256 != current.recovery_episode_sha256
            or previous.accepted_decision_sha256 != current.accepted_decision_sha256
            or previous_hashes
            != [
                *cast(list[str], previous.document["prior_failure_evidence_sha256"]),
                previous.failure_evidence_sha256,
            ]
        ):
            return error("PREDECESSOR_IDENTITY", "prior hash/correlation mismatch", conflict=True)
        current = previous


def classify_accepted_read_only_effects(
    *,
    record: ApplicationDecisionRecord,
    source: WorkerRequest,
    recovery_evidence: Mapping[str, object],
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    recovery_artifact: ApplicationRecoveryArtifact | None = None,
) -> AcceptedPostEffectProof:
    """Classify accepted read-only evidence at the existing proof owner.

    A missing history read may be observed later. A contradictory immutable
    Effect identity is not an observation delay and must not be requeued as
    one. Neither outcome licenses a GitHub write or a synthetic Action.
    """

    source_error = _accepted_original_source_identity_error(record, source)
    if source_error is not None:
        return AcceptedPostEffectProof("UNSAFE", source_error.detail)
    boundary = _accepted_recovery_boundary(recovery_evidence)
    if boundary not in {"READ_ONLY", "POST_EFFECT_RESULT"}:
        return AcceptedPostEffectProof("UNSAFE", "read-only failure boundary is invalid")
    if _SHA.fullmatch(current_revision) is None or not default_branch:
        return AcceptedPostEffectProof("INDETERMINATE", "fresh revision evidence unavailable")
    try:
        if boundary == "POST_EFFECT_RESULT":
            return _observe_accepted_post_effect_result(
                record=record,
                source=source,
                repository=repository,
                token=token,
                current_revision=current_revision,
                default_branch=default_branch,
            )
        if "attempted_effects" not in recovery_evidence:
            return AcceptedPostEffectProof(
                "INDETERMINATE", "immutable attempted Effect checkpoint unavailable"
            )
        attempted = _verified_attempted_effect_checkpoint(recovery_evidence, source=source)
        attempted_revision = recovery_evidence.get("attempt_revision")
        if (
            attempted is None
            or not isinstance(attempted_revision, str)
            or _SHA.fullmatch(attempted_revision) is None
        ):
            return AcceptedPostEffectProof(
                "UNSAFE", "immutable attempted Effect identity contradicts checkpoint"
            )
        if recovery_artifact is None:
            return AcceptedPostEffectProof(
                "INDETERMINATE", "qualified recovery artifact unavailable"
            )
        if recovery_artifact.document.get("failure_evidence") != recovery_evidence:
            return AcceptedPostEffectProof(
                "UNSAFE", "recovery artifact and attempted Effect checkpoint disagree"
            )
        index = recovery_evidence.get("failed_effect_index")
        if type(index) is not int:
            return AcceptedPostEffectProof("UNSAFE", "read-only Effect index is invalid")
        non_entry = recovery_evidence.get("write_call_entered") is False
        original = _qualified_accepted_original_effects(
            record=record, source=source, raw_worker_result=record.raw_worker_result
        )
        if isinstance(original, TypedEvidenceError):
            return AcceptedPostEffectProof(
                "UNSAFE" if original.category == "CONFLICT" else "INDETERMINATE",
                original.detail,
            )
        # A witnessed postcondition cannot rehabilitate an immutable Effect
        # identity contradiction, even if the current GitHub state is positive.
        if original.effects:
            prefix_length = min(len(original.effects), len(attempted))
            if attempted[:prefix_length] != original.effects[:prefix_length]:
                conflict = RecoveryEvidenceNode(
                    "ORIGINAL_EFFECT",
                    attempted[0],
                    final_postcondition=None,
                    source_conflict=True,
                )
                return AcceptedPostEffectProof(
                    "UNSAFE",
                    "immutable accepted original Effect prefix contradicts checkpoint",
                    original_effect_proof=evaluate_recovery_evidence(conflict),
                )
        adapter = GitHubEffectAdapter(
            repository,
            token,
            source,
            authorized_change=record.change,
            current_revision=current_revision,
            expected_result_kind=record.result_kind,
            request_comment_id=record.request_comment_id,
            authorization_revision=record.authorization_revision,
            allow_pending_continuation=True,
            accepted_intent=True,
            pending_application_correlation=formal_application_correlation(
                source,
                change=record.change,
                result_kind=record.result_kind,
                current_revision=attempted_revision,
                request_comment_id=record.request_comment_id,
            ),
        )
        # One proof table: a positively SATISFIED Effect does not have to
        # prove it was never called. Only an absent, invocation-local
        # never-called Effect requires the full historical NOT_APPLIED proof.
        proven_prefix = _observe_accepted_effect_prefix(
            attempted[:-1], adapter.observe_postcondition, source=source
        )
        if proven_prefix is None:
            return AcceptedPostEffectProof(
                "INDETERMINATE", "accepted historical prefix is not yet satisfied"
            )
        # A never-called derived Effect is not independently observed here:
        # its final state has a canonical consequence owner below. This
        # preserves the producer's no-write checkpoint observation boundary.
        failed_satisfied = (
            adapter.observe_postcondition(attempted[-1])
            if not non_entry or not attempted[-1].derived
            else False
        )
        attempted_fact = RecoveryEvidenceNode(
            _recovery_obligation(attempted[-1], source),
            attempted[-1],
            final_postcondition=failed_satisfied,
            depends_on=tuple(proven_prefix),
        )
        attempted_proof = evaluate_recovery_evidence(attempted_fact)
        historical_frontier = index + 1 if attempted_proof == "SATISFIED" else index
        # Original Effect proof is separate from *authorization of the next*
        # formal/result/successor write. Bind its leaf to the immutable
        # accepted source before attributing a positive postcondition.
        # This uses the already-accepted source, not optional historic Runs.
        original_effect_proof: RecoveryProofDisposition | None = None
        if (
            0 <= index < len(original.effects)
            and attempted[: index + 1] == original.effects[: index + 1]
        ):
            original_effect_proof = attempted_proof
        if attempted_proof != "SATISFIED" and not non_entry:
            return AcceptedPostEffectProof(
                "INDETERMINATE",
                "attempted accepted Effect is not yet proven complete",
                original_effect_proof=original_effect_proof,
            )
        # R9: after positive original/formal witnesses, the canonical
        # consequence owner can read-only prove an already durable successor.
        # No history-of-nonentry gate is needed when no write remains.
        # A missing result/route still requires the no-replay gate below.
        if (
            attempted[-1].derived
            and original.typed_result is not None
            and original.typed_result.result.kind.value == record.result_kind
            and (
                bool(original.effects)
                or (
                    not non_entry
                    and _verified_zero_original_accepted_effects(
                        record=record, source=source, repository=repository, token=token
                    )
                )
            )
            and len(attempted) == len(original.effects) + 2
            and attempted[:-2] == original.effects
        ):
            formal_identity = _attempted_formal_identity(
                attempted,
                source=source,
                change=record.change,
                result_kind=record.result_kind,
                request_comment_id=record.request_comment_id,
            )
            expected_successor = derived_transition_effect(
                issue_number=source.issue_number,
                change=record.change,
                successor=next_action(original.typed_result.action, original.typed_result.result),
            )
            if (
                formal_identity is not None
                and formal_identity[0] == attempted[-2]
                and formal_identity[1] == attempted_revision
                and attempted[-1] == expected_successor
                # Commit of the formal result does not prove the final
                # routing/terminal projection. Only the existing authoritative
                # Effect adapter can observe that later durable consequence.
                and adapter.observe_postcondition(expected_successor)
                and consequence_postconditions_complete(
                    record.raw_worker_result,
                    source=source,
                    repository=repository,
                    token=token,
                    current_revision=current_revision,
                    authorized_change=record.change,
                    request_comment_id=record.request_comment_id,
                    accepted_intent=True,
                    allow_accepted_successor=True,
                    observed_application_correlation=formal_application_correlation(
                        source,
                        change=record.change,
                        result_kind=record.result_kind,
                        current_revision=formal_identity[1],
                        request_comment_id=record.request_comment_id,
                    ),
                    formal_result_observed=True,
                )
            ):
                return AcceptedPostEffectProof(
                    "COMPLETE", "exact accepted formal and successor already observed"
                )
        history = _read_accepted_never_called_evidence(
            record=record,
            source=source,
            artifact=recovery_artifact,
            failed_index=historical_frontier,
            repository=repository,
            token=token,
        )
        # Evidence Result is a leaf fact, never a caller-side Boolean decision.
        # No physical Effect object is invented for the future formal/successor
        # frontier; only the existing Application may reauthorize consequences.
        historical_proof = evaluate_recovery_evidence(
            RecoveryEvidenceNode(
                "ORIGINAL_EFFECT",
                None,
                final_postcondition=False,
                never_called_evidence=history,
                depends_on=tuple(proven_prefix),
            )
        )
        if historical_proof != "NOT_APPLIED":
            return AcceptedPostEffectProof(
                "UNSAFE" if historical_proof == "CONFLICT" else "INDETERMINATE",
                (
                    "accepted historical write frontier contradicts source"
                    if historical_proof == "CONFLICT"
                    else "accepted historical write frontier is not proven"
                ),
                original_effect_proof=original_effect_proof,
            )
        return AcceptedPostEffectProof(
            "COMPLETE",
            "accepted historical Effect satisfied"
            if failed_satisfied
            else "accepted unattempted suffix qualified",
            original_effect_proof=original_effect_proof,
        )
    except OSError:
        # Only an expected transport/read failure is re-observable. Invalid
        # proof data has explicit UNSAFE returns above; unexpected program
        # errors belong to the existing outer execution-exception capture.
        return AcceptedPostEffectProof("INDETERMINATE", "accepted GitHub observation unavailable")


def accepted_read_only_effects_complete(
    *,
    record: ApplicationDecisionRecord,
    source: WorkerRequest,
    recovery_evidence: Mapping[str, object],
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    recovery_artifact: ApplicationRecoveryArtifact | None = None,
) -> bool:
    """Boolean compatibility projection; typed proof is the sole owner."""

    return (
        classify_accepted_read_only_effects(
            record=record,
            source=source,
            recovery_evidence=recovery_evidence,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
            recovery_artifact=recovery_artifact,
        ).disposition
        == "COMPLETE"
    )


def classify_post_effect_result_recovery(
    *,
    record: ApplicationDecisionRecord,
    artifact: ApplicationRecoveryArtifact,
    repository: str,
    token: str,
) -> AcceptedPostEffectProof:
    """Preserve the canonical proof taxonomy through the dispatch boundary.

    The artifact's signed `continuation_eligible=false` remains immutable.
    Each consumer must fresh-observe the original accepted effect, and the
    Application must independently prove it again before any formal write.
    """

    failure = artifact.document.get("failure_evidence")
    if not isinstance(failure, Mapping):
        return AcceptedPostEffectProof("UNSAFE", "recovery boundary is not structured")
    # Exact correlation is one named-field contract, not eight independently
    # maintained Boolean gates. Both sides must agree on the same immutable
    # source identity; no observation failure can be promoted to permission.
    observed = {
        "boundary": _accepted_recovery_boundary(failure),
        "continuation_eligible": artifact.continuation_eligible,
        "request_comment_id": artifact.request_comment_id,
        "issue_number": artifact.document.get("issue_number"),
        "role": artifact.document.get("role"),
        "action": artifact.document.get("action"),
        "authorization_revision": artifact.document.get("authorization_revision"),
        "decision": record.disposition,
    }
    required = {
        "boundary": "POST_EFFECT_RESULT",
        "continuation_eligible": False,
        "request_comment_id": record.request_comment_id,
        "issue_number": record.issue_number,
        "role": record.role,
        "action": record.action,
        "authorization_revision": record.authorization_revision,
        "decision": "ACCEPTED",
    }
    if observed != required:
        return AcceptedPostEffectProof("UNSAFE", "invalid immutable recovery correlation")
    return _fresh_accepted_activation_proof(record, repository=repository, token=token)


def classify_application_exception_recovery(
    *,
    record: ApplicationDecisionRecord,
    artifact: ApplicationExceptionArtifact,
    repository: str,
    token: str,
) -> AcceptedPostEffectProof:
    """An exception is admissible only after independently proving the original.

    This is not an exception-string classifier: no `raw_error`, traceback or
    claimed mutation status authorizes a second Effect invocation.
    """

    identity = (
        artifact.request_comment_id,
        artifact.document.get("issue_number"),
        artifact.document.get("role"),
        artifact.document.get("action"),
        artifact.document.get("change"),
    )
    if (
        identity
        != (
            record.request_comment_id,
            record.issue_number,
            record.role,
            record.action,
            record.change,
        )
        or record.disposition != "ACCEPTED"
    ):
        return AcceptedPostEffectProof("UNSAFE", "exception accepted identity mismatch")
    return _fresh_accepted_activation_proof(record, repository=repository, token=token)


def _fresh_accepted_activation_proof(
    record: ApplicationDecisionRecord, *, repository: str, token: str
) -> AcceptedPostEffectProof:
    """One read-only owner for both standard and exception recovery admission."""

    try:
        repo = _as_mapping(_github_json(repository, token, ""))
        branch = None if repo is None else repo.get("default_branch")
        if not isinstance(branch, str) or not branch:
            return AcceptedPostEffectProof("INDETERMINATE", "default branch unavailable")
        revision = _fresh_branch_head(repository, token, branch)
        if revision is None or _SHA.fullmatch(revision) is None:
            return AcceptedPostEffectProof("INDETERMINATE", "default revision unavailable")
        return _observe_accepted_post_effect_result(
            record=record,
            source=WorkerRequest(record.issue_number, record.role, record.action),
            repository=repository,
            token=token,
            current_revision=revision,
            default_branch=branch,
        )
    except OSError:
        # The shared I/O boundary admits read failures only. A contract or
        # programming error must reach the existing outer exception owner,
        # not become an indefinite read-only observation.
        return AcceptedPostEffectProof("INDETERMINATE", "accepted GitHub proof unavailable")


def _write_application_recovery_evidence(
    path: str | None,
    *,
    result: ApplyResult,
    repository: str,
    token: str,
    source: WorkerRequest,
    request_comment_id: int,
    trigger_comment_id: int,
    authorization_revision: str,
    current_revision: str,
    run_attempt: int,
    continuation: ApplicationContinuationRequest | None,
    predecessor: ApplicationRecoveryArtifact | ApplicationExceptionArtifact | None,
    effect_batch: EffectBatch | None = None,
    preserve_predecessor_failure: bool = False,
) -> bool:
    """Persist a bounded, content-addressed application boundary for later reads."""

    if path is None:
        return False
    try:
        decision = _application_decision_comment_for_request(
            repository=repository,
            token=token,
            issue_number=source.issue_number,
            request_comment_id=request_comment_id,
        )
    except (HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return False
    if decision is None:
        return False
    accepted_record, accepted_body = decision
    if (
        accepted_record.disposition != "ACCEPTED"
        or accepted_record.issue_number != source.issue_number
        or accepted_record.role != source.role
        or accepted_record.action != source.action
    ):
        return False
    accepted_sha256 = hashlib.sha256(accepted_body.encode("utf-8")).hexdigest()
    if continuation is not None and continuation.accepted_decision_sha256 != accepted_sha256:
        return False
    try:
        run_id = int(os.environ.get("GITHUB_RUN_ID", ""))
    except ValueError:
        return False
    if _strict_positive_int(run_id) is None or _strict_positive_int(run_attempt) is None:
        return False

    if preserve_predecessor_failure:
        # This invocation only re-observed a fully qualified predecessor:
        # its write-call facts are immutable, not a new Effect attempt.
        if (
            result.applied
            or result.recovery_evidence is not None
            or result.carrier_plan is not None
            or not isinstance(predecessor, ApplicationRecoveryArtifact)
            or predecessor.request_comment_id != request_comment_id
            or predecessor.accepted_decision_sha256 != accepted_sha256
            or predecessor.document.get("issue_number") != source.issue_number
            or predecessor.document.get("role") != source.role
            or predecessor.document.get("action") != source.action
            or predecessor.document.get("authorization_revision") != authorization_revision
        ):
            return False
        original_failure = predecessor.document.get("failure_evidence")
        if (
            not isinstance(original_failure, Mapping)
            or _accepted_recovery_boundary(original_failure) != "READ_ONLY"
            or _canonical_sha256(original_failure) != predecessor.failure_evidence_sha256
        ):
            return False
        failure_evidence = dict(original_failure)
        failure_evidence["reason"] = result.reason
    else:
        failure_evidence = _recovery_failure_document(result)
    # Redact the raw cause once at the existing evidence producer, before
    # computing its content digest. Neither reader nor proof table uses the
    # error string to infer write eligibility.
    raw_error = failure_evidence.get("raw_error")
    if isinstance(raw_error, str):
        safe_error = raw_error.replace(token, "***") if token else raw_error
        safe_error = re.sub(r"https?://\S+", "[redacted-url]", safe_error)
        failure_evidence["raw_error"] = safe_error[:2048]
    recovery = result.recovery_evidence
    if recovery is not None and _accepted_recovery_boundary(failure_evidence) == "READ_ONLY":
        # Structural qualification already belongs to _accepted_recovery_boundary.
        # Capture incomplete prefixes; do not reimplement its admissibility
        # predicate or silently lose evidence when an earlier GET was absent.
        predecessor_failure = (
            predecessor.document.get("failure_evidence")
            if isinstance(predecessor, ApplicationRecoveryArtifact)
            else None
        )
        inherited = (
            _verified_attempted_effect_checkpoint(predecessor_failure, source=source)
            if isinstance(predecessor_failure, Mapping)
            and predecessor_failure.get("failed_effect_sha256") == recovery.failed_effect_sha256
            and predecessor_failure.get("failed_effect_kind") == recovery.failed_effect_kind
            and predecessor_failure.get("failed_effect_index") == recovery.failed_effect_index
            and "attempted_effects" in predecessor_failure
            else None
        )
        attempted = (
            [
                {
                    "kind": effect.kind,
                    "payload_json": effect.payload_json,
                    "derived": effect.derived,
                }
                for effect in inherited
            ]
            if inherited is not None
            else (
                None
                if effect_batch is None
                else _attempted_effect_checkpoint(effect_batch, recovery)
            )
        )
        if attempted is None:
            if effect_batch is not None or (
                isinstance(predecessor_failure, Mapping)
                and "attempted_effects" in predecessor_failure
            ):
                return False
        else:
            failure_evidence["attempted_effects"] = attempted
            try:
                formal_identity = _attempted_formal_identity(
                    tuple(
                        StagedEffect(
                            kind=cast(str, entry["kind"]),
                            payload_json=cast(str, entry["payload_json"]),
                            derived=cast(bool, entry["derived"]),
                        )
                        for entry in attempted
                    ),
                    source=source,
                    change=accepted_record.change,
                    result_kind=accepted_record.result_kind,
                    request_comment_id=request_comment_id,
                )
            except (KeyError, TypeError, RuntimeError):
                return False
            formal_revision = None if formal_identity is None else formal_identity[1]
            attempt_revision = (
                predecessor_failure.get("attempt_revision")
                if inherited is not None and isinstance(predecessor_failure, Mapping)
                else formal_revision or current_revision
            )
            if not isinstance(attempt_revision, str) or _SHA.fullmatch(attempt_revision) is None:
                return False
            if formal_revision is not None and attempt_revision != formal_revision:
                return False
            failure_evidence["attempt_revision"] = attempt_revision
    failure_evidence_sha256 = _canonical_sha256(failure_evidence)
    if predecessor is None:
        episode_sha256 = _canonical_sha256(
            {
                "schema": "scheduled-agent-recovery-episode/v1",
                "repository": repository,
                "issue_number": source.issue_number,
                "request_comment_id": request_comment_id,
                "accepted_decision_sha256": accepted_sha256,
            }
        )
        recovery_attempt = 1
        prior_failures: list[str] = []
        predecessor_document = None
    else:
        episode_sha256 = predecessor.recovery_episode_sha256
        recovery_attempt = (
            2
            if isinstance(predecessor, ApplicationExceptionArtifact)
            else predecessor.recovery_attempt + 1
        )
        prior_failures = (
            [predecessor.failure_evidence_sha256]
            if isinstance(predecessor, ApplicationExceptionArtifact)
            else list(cast(list[str], predecessor.document["prior_failure_evidence_sha256"]))
        )
        if isinstance(predecessor, ApplicationRecoveryArtifact):
            prior_failures.append(predecessor.failure_evidence_sha256)
        predecessor_document = {
            "run_id": predecessor.run_id,
            "run_attempt": predecessor.run_attempt,
            "job_id": predecessor.job_id,
            "artifact_id": predecessor.artifact_id,
            "artifact_digest": predecessor.artifact_digest,
            "failure_evidence_sha256": predecessor.failure_evidence_sha256,
            "recovery_attempt": (
                1
                if isinstance(predecessor, ApplicationExceptionArtifact)
                else predecessor.recovery_attempt
            ),
        }
    # The structural boundary is shared with the independent reader. READ_ONLY
    # means prove the immutable attempted/completed prefix before any new
    # mutation: UNKNOWN must prove its failed effect too, whereas a confirmed
    # zero-write rejection must *not* require its unattempted suffix to exist.
    # A post-effect application-result checkpoint is *always* recorded as
    # ineligible. Its immutable false flag can only be overcome by a fresh,
    # read-only proof of the exact accepted first-activation materialization
    # at every consumer; the producer cannot grant itself this proof.
    continuation_eligible = _accepted_recovery_boundary(failure_evidence) not in {
        "NONE",
        "POST_EFFECT_RESULT",
    }
    # An inconclusive read-only observation must not erase the legal ability
    # to observe later external truth. The dispatcher gates a *new* continuation
    # on a freshly proved COMPLETE result, rather than treating a repeated
    # observed index frontier as a permanent terminal failure.
    document = {
        "schema": _APPLICATION_RECOVERY_SCHEMA,
        "repository": repository,
        "issue_number": source.issue_number,
        "role": source.role,
        "action": source.action,
        "request_comment_id": request_comment_id,
        "accepted_decision_sha256": accepted_sha256,
        "trigger_comment_id": trigger_comment_id,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "current_revision": current_revision,
        "authorization_revision": authorization_revision,
        "recovery_attempt": recovery_attempt,
        "recovery_episode_sha256": episode_sha256,
        "prior_failure_evidence_sha256": prior_failures,
        "predecessor": predecessor_document,
        "failure_evidence": failure_evidence,
        "failure_evidence_sha256": failure_evidence_sha256,
        "continuation_eligible": continuation_eligible,
    }
    try:
        Path(path).write_text(
            json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return False
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as output:
            output.write(f"recovery_evidence_path={path}\n")
    return bool(output_path)


def _record_application_exception(context: ApplicationExceptionContext, exc: Exception) -> None:
    """Retain a catchable failure without manufacturing ACCEPT or a route.

    A run-scoped artifact survives even when a separate GitHub comment write
    cannot be freshly qualified. The comment is audit evidence only, not a
    substitute decision, an Action result, or permission to replay an effect.
    """

    token = context.token or ""

    def redacted(value: str) -> str:
        return value.replace(token, "***") if token else value

    raw_run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_id = _positive_int(int(raw_run_id)) if raw_run_id.isdecimal() else None
    source = context.source
    raw_error = redacted(str(exc))
    correlation = (
        f"application:{run_id}:{context.run_attempt}:{context.request_comment_id}"
        if run_id is not None and context.request_comment_id is not None
        else None
    )
    mutation_status = (
        "UNKNOWN_REQUIRES_FRESH_RECONCILIATION"
        if context.mutation_attempted
        else "NO_APPLICATION_WRITE_ATTEMPTED"
    )
    document: dict[str, object] = {
        "schema": "scheduled-agent-execution-exception/v1",
        "repository": context.repository,
        "issue_number": None if source is None else source.issue_number,
        "role": None if source is None else source.role,
        "action": None if source is None else source.action,
        "change": context.change,
        "revision": context.revision,
        "request_comment_id": context.request_comment_id,
        "trigger_comment_id": context.trigger_comment_id,
        "run_id": run_id,
        "run_attempt": context.run_attempt,
        "attempted_operation": context.stage,
        "exception_type": type(exc).__qualname__,
        "raw_error": raw_error,
        "raw_traceback": redacted("".join(traceback.format_exception(exc))),
        "mutation_status": mutation_status,
        "unfinished_boundary": context.stage,
        "classification": "UNCLASSIFIED_EXECUTION_EXCEPTION",
    }
    if context.evidence_path:
        try:
            Path(context.evidence_path).write_text(
                json.dumps(document, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            output_path = os.environ.get("GITHUB_OUTPUT")
            if output_path:
                with Path(output_path).open("a", encoding="utf-8") as output:
                    output.write(f"execution_exception_path={context.evidence_path}\n")
        except OSError as persistence_error:
            print(f"Execution exception artifact unavailable: {persistence_error}", file=sys.stderr)

    if (
        source is None
        or context.repository is None
        or not token
        or context.change is None
        or context.revision is None
        or context.request_comment_id is None
        or correlation is None
    ):
        return
    # Freshly qualify the exact issue before writing an audit comment. A
    # changed route or unreadable issue prohibits this optional write; the
    # independently emitted run artifact still captures the actual failure.
    current = _github_json(context.repository, token, f"issues/{source.issue_number}")
    current_issue = _as_mapping(current)
    if current_issue is None or current_issue.get("state") != "open":
        return
    current_labels = current_issue.get("labels")
    if not isinstance(current_labels, list) or not any(
        isinstance(label, Mapping) and label.get("name") == f"action:{source.action}"
        for label in current_labels
    ):
        return
    current_body = current_issue.get("body")
    if not isinstance(current_body, str) or _CHANGE_LINE.findall(current_body) != [context.change]:
        return
    lines = [
        "EXECUTION_EXCEPTION",
        f"Workflow: #{source.issue_number}",
        f"Change: {context.change}",
        f"Action: {source.action}",
        f"Role: {source.role}",
        "Result: execution-exception",
        f"Revision: {context.revision}",
        f"Request-Comment-ID: {context.request_comment_id}",
        f"Run-ID: {run_id}",
        f"Run-Attempt: {context.run_attempt}",
        f"Exception-Correlation: {correlation}",
        f"Attempted-Operation: {context.stage}",
        f"Raw-Error: {raw_error}",
        f"Mutation-Outcome: {mutation_status}",
        f"Unfinished-Work: {context.stage}",
        "Classification: UNCLASSIFIED_EXECUTION_EXCEPTION",
        "Disposition: fresh-reconcile-or-bounded-Lead-repair; no automatic routing",
    ]
    message = "\n".join(lines)
    endpoint = f"issues/{source.issue_number}/comments"

    def matching_comments() -> tuple[Mapping[str, object], ...]:
        return tuple(
            comment
            for comment in _paged_github_list(context.repository or "", token, endpoint)
            if isinstance(comment.get("body"), str)
            and f"Exception-Correlation: {correlation}" in cast(str, comment["body"]).splitlines()
        )

    existing = matching_comments()
    if len(existing) > 1 or (existing and existing[0].get("body") != message):
        return
    if not existing:
        _github_json(context.repository, token, endpoint, method="POST", payload={"body": message})
    verified = matching_comments()
    if len(verified) != 1 or verified[0].get("body") != message:
        raise RuntimeError("EXECUTION_EXCEPTION postcondition is not uniquely observable")


def main() -> int:
    """Apply an exact worker result and capture exceptions at its outer boundary."""

    context = ApplicationExceptionContext()
    try:
        return _main_unprotected(context)
    except Exception as exc:
        try:
            _record_application_exception(context, exc)
        except Exception as capture_error:
            # The original exception remains primary; an uncertain audit write
            # must never be retried blindly or obscure the failed boundary.
            print(
                f"Execution exception evidence persistence failed: {capture_error}",
                file=sys.stderr,
            )
        raise


def _main_unprotected(context: ApplicationExceptionContext) -> int:
    """Apply one worker result after fresh repository authorization."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--default-branch", required=True)
    parser.add_argument("--validation-passed", action="store_true")
    parser.add_argument("--validated-revision")
    parser.add_argument("--run-attempt", type=int, default=1)
    parser.add_argument("--recovery-evidence-path")
    parser.add_argument("--exception-evidence-path")
    args = parser.parse_args()
    context.revision = args.revision
    context.run_attempt = args.run_attempt
    context.evidence_path = args.exception_evidence_path
    if args.run_attempt <= 0:
        raise ValueError("run attempt must be positive")

    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
    context.repository = repository
    context.token = token

    event = _as_mapping(_load_json(args.event_path))
    if event is None:
        raise RuntimeError("GitHub event payload must be an object")
    event_comment = _as_mapping(event.get("comment"))
    body = None if event_comment is None else event_comment.get("body")
    if not isinstance(body, str):
        return 0
    event_comment_id = _positive_int(None if event_comment is None else event_comment.get("id"))
    context.trigger_comment_id = event_comment_id
    accepted_intent: ApplicationDecisionRecord | None = None
    accepted_raw_worker_result: str | None = None
    continuation: ApplicationContinuationRequest | None = None
    predecessor_evidence: ApplicationRecoveryArtifact | ApplicationExceptionArtifact | None = None
    if isinstance(body, str):
        continuation = parse_application_continuation_request(body)
        if body.startswith(APPLICATION_CONTINUATION_MARKER) and continuation is None:
            raise ValueError("application continuation request is invalid")
    try:
        request = parse_application_request(body)
    except ValueError:
        request = None

    # A request can be re-entered as a fresh process even when its current
    # formal frontier is temporarily indeterminate.  If the parsed worker
    # payload carries a source identity, use that exact source Issue plus the
    # immutable request comment id before consulting frontier qualification.
    # Semantic-only payloads, edited envelopes, and deleted envelopes use the
    # complete fresh-Issue fallback below.
    preflight: DispatchPreflight | None = None
    if continuation is not None:
        if event_comment_id is None:
            raise ValueError("application continuation event comment id is invalid")
        if _fresh_event_observation(event, body, repository, token):
            raise ValueError("application continuation current comment was mutated")
        preflight = acquire_current_github_preflight(repository, token)
        accepted_intent = _find_application_decision_from_current_frontier(
            repository=repository,
            token=token,
            request_comment_id=continuation.original_request_comment_id,
            preflight=preflight,
        )
        if (
            accepted_intent is None
            or accepted_intent.disposition != "ACCEPTED"
            or accepted_intent.issue_number != continuation.issue_number
        ):
            raise ValueError("application continuation accepted intent is unavailable")
        decision_comments = _application_decision_comment_for_request(
            repository=repository,
            token=token,
            issue_number=accepted_intent.issue_number,
            request_comment_id=accepted_intent.request_comment_id,
        )
        if decision_comments is None:
            raise ValueError("application continuation decision evidence is unavailable")
        _decision_record, decision_body = decision_comments
        decision_sha256 = hashlib.sha256(decision_body.encode("utf-8")).hexdigest()
        expected_correlation = application_continuation_correlation(
            repository,
            accepted_intent.issue_number,
            accepted_intent.request_comment_id,
            decision_sha256,
            continuation.predecessor_run_id,
            continuation.predecessor_run_attempt,
            continuation.predecessor_job_id,
            continuation.predecessor_artifact_id,
            continuation.predecessor_artifact_digest,
            continuation.failure_evidence_sha256,
            continuation.recovery_episode_sha256,
        )
        if (
            decision_sha256 != continuation.accepted_decision_sha256
            or expected_correlation != continuation.continuation_correlation
        ):
            raise ValueError("application continuation correlation is invalid")
        event_issue = _as_mapping(event.get("issue"))
        transport_issue_number = (
            None if event_issue is None else _positive_int(event_issue.get("number"))
        )
        if transport_issue_number is None:
            raise ValueError("application continuation transport Issue is invalid")
        predecessor_evidence = qualify_application_continuation_predecessor(
            repository,
            token,
            continuation,
            current_comment_id=event_comment_id,
            transport_issue_number=transport_issue_number,
        )
        if predecessor_evidence is None:
            raise ValueError("application continuation predecessor evidence is invalid")

    if (
        continuation is None
        and event_comment_id is not None
        and request is not None
        and args.run_attempt > 1
    ):
        claimed_source = _claimed_source(request.raw_worker_result)
        if claimed_source is not None:
            accepted_intent = _application_decision_for_request(
                repository=repository,
                token=token,
                issue_number=claimed_source.issue_number,
                request_comment_id=event_comment_id,
                request_body=body,
            )
    if (
        event_comment_id is not None
        and accepted_intent is None
        and (request is None or args.run_attempt > 1)
    ):
        # A rerun is a Phase-B continuation boundary.  Resolve the immutable
        # decision before planning so a successor frontier cannot rebind the
        # old request to a new semantic Action/correlation.
        preflight = acquire_current_github_preflight(repository, token)
        accepted_intent = _find_application_decision_from_current_frontier(
            repository=repository,
            token=token,
            request_comment_id=event_comment_id,
            preflight=preflight,
        )
    if accepted_intent is not None and accepted_intent.disposition == "ACCEPTED":
        accepted_source = WorkerRequest(
            accepted_intent.issue_number,
            accepted_intent.role,
            accepted_intent.action,
        )
        accepted_raw_worker_result = _accepted_worker_result_for_continuation(
            accepted_intent=accepted_intent,
            source=accepted_source,
            repository=repository,
            token=token,
            request_comment_id=accepted_intent.request_comment_id,
        )
        request = ApplicationRequest(
            authorization_revision=accepted_intent.authorization_revision,
            raw_worker_result=accepted_raw_worker_result,
        )
        if _resume_pending_accepted_merge_recovery(
            accepted=accepted_intent,
            repository=repository,
            token=token,
            current_revision=args.revision,
            default_branch=args.default_branch,
        ):
            _write_carrier_outputs(ApplyResult(True, "accepted-merge-recovery-already-durable"))
            _write_validation_outputs(None)
            print(
                json.dumps(
                    {
                        "applied": True,
                        "reason": "accepted-merge-recovery-already-durable",
                        "effects": 0,
                    },
                    sort_keys=True,
                )
            )
            return 0
    if accepted_intent is not None and accepted_intent.disposition == "REJECTED":
        _write_carrier_outputs(ApplyResult(False, "application-rejected"))
        _write_validation_outputs(None)
        return 0
    raw_transport = False
    fresh_raw_mutated = False
    if accepted_intent is None and body.startswith("WORKER_RESULT"):
        # The real issue_comment.created Actions entrypoint owns this
        # canonicalization, before Phase A. Its original event is retained as
        # the only durable request/comment identity.
        fresh_raw_mutated = _fresh_event_observation(event, body, repository, token)
        if fresh_raw_mutated:
            raise ValueError("WORKER_RESULT current comment was mutated before ACCEPT")
        if preflight is None:
            preflight = acquire_current_github_preflight(repository, token)
        decision = classify_dispatch(preflight)
        if (
            decision.disposition != "AUTHORIZE"
            or decision.selected_issue_id is None
            or decision.selected_routing is None
        ):
            raise ValueError("WORKER_RESULT has no qualified current AUTHORIZE dispatch")
        selected_role, selected_action = decision.selected_routing
        source = WorkerRequest(decision.selected_issue_id, selected_role, selected_action)
        change = _preflight_change(preflight, source)
        if change is None:
            raise ValueError("WORKER_RESULT authoritative Change is unavailable")
        request = canonicalize_raw_worker_result(
            body=body,
            source=source,
            authorized_change=change,
            repository=repository,
            current_revision=args.revision,
        )
        raw_transport = True
    if request is None:
        if accepted_intent is None:
            return 0
        raise RuntimeError("accepted application intent could not reconstruct its request")

    # After ACCEPT the current comment is transport only.  Its fresh
    # observation is required for Phase A, but an immutable accepted intent
    # must survive an edit/delete boundary without consulting that transport.
    body_mutated = (
        False
        if accepted_intent is not None
        else fresh_raw_mutated
        if raw_transport
        else _fresh_event_observation(event, body, repository, token)
    )
    if preflight is None:
        preflight = acquire_current_github_preflight(repository, token)
    plan = plan_application(
        event=event,
        request=request,
        preflight=preflight,
        repository=repository,
        current_revision=args.revision,
        token=token,
        allow_descendant_resume=args.run_attempt > 1 or accepted_intent is not None,
        allow_accepted_request_mutation=accepted_intent is not None,
        accepted_intent=accepted_intent,
        accepted_request_comment_id=(
            None if continuation is None else continuation.original_request_comment_id
        ),
        allow_raw_result_transport=raw_transport,
        raw_shard_qualified=raw_transport and not fresh_raw_mutated,
    )
    if not plan.should_apply:
        _write_validation_outputs(None)
        return 0
    if plan.source is None or plan.raw_worker_result is None or plan.request_comment_id is None:
        raise RuntimeError("application plan is missing validated source/result/request identity")
    context.source = plan.source
    context.request_comment_id = plan.request_comment_id

    if accepted_intent is None and (body_mutated or args.run_attempt > 1 or args.validation_passed):
        accepted_intent = _application_decision_for_request(
            repository=repository,
            token=token,
            issue_number=plan.source.issue_number,
            request_comment_id=plan.request_comment_id,
            request_body=body,
        )
    if body_mutated and accepted_intent is None:
        raise ValueError("application request current comment was mutated before ACCEPT")
    effective_change = plan.change or (
        accepted_intent.change
        if accepted_intent is not None
        else _preflight_change(preflight, plan.source)
    )
    if effective_change is None:
        raise RuntimeError("application plan has no fresh machine-owned Change")
    context.change = effective_change
    context.stage = "pre-accept-worker-result-qualification"
    if accepted_intent is not None:
        if accepted_intent.disposition == "REJECTED":
            _write_carrier_outputs(ApplyResult(False, "application-rejected"))
            _write_validation_outputs(None)
            return 0
        if (
            accepted_intent.issue_number != plan.source.issue_number
            or accepted_intent.role != plan.source.role
            or accepted_intent.action != plan.source.action
            or accepted_intent.worker_result_sha256
            != hashlib.sha256(accepted_intent.raw_worker_result.encode("utf-8")).hexdigest()
        ):
            raise RuntimeError("accepted application intent identity is invalid")
        # Keep the validated continuation projection, including an exact manifest
        # rehydrated from the immutable original request after acceptance.
        semantic_worker_result = (
            accepted_raw_worker_result
            if accepted_raw_worker_result is not None
            else accepted_intent.raw_worker_result
        )
    else:
        semantic_worker_result = plan.raw_worker_result
    try:
        semantic_decoded = json.loads(semantic_worker_result)
    except json.JSONDecodeError:
        semantic_decoded = None
    legacy_empty_intent = (
        accepted_intent is not None
        and isinstance(semantic_decoded, Mapping)
        and semantic_decoded.get("_semantic_intent_version") != 2
        and semantic_decoded.get("requested_effects") == []
    )
    application_worker_result = (
        semantic_worker_result
        if legacy_empty_intent
        else _fresh_application_worker_result(
            semantic_worker_result,
            source=plan.source,
            change=effective_change,
            repository=repository,
            token=token,
            current_revision=args.revision,
            default_branch=args.default_branch,
            request_comment_id=plan.request_comment_id,
        )
    )
    application_request_body = (
        body
        if accepted_intent is None
        else _render_accepted_application_wire(
            ApplicationRequest(
                authorization_revision=accepted_intent.authorization_revision,
                raw_worker_result=accepted_intent.raw_worker_result,
            ),
        )
    )
    worker_result = parse_worker_result(
        application_worker_result,
        plan.source,
        authorized_change=plan.change,
    )
    materializations = _materialization_effects(
        application_worker_result,
        plan.source,
        change=plan.change,
    )
    if len(materializations) > 1:
        raise RuntimeError("EFFECT_REQUEST contains ambiguous materialization effects")
    materialization = None if not materializations else materializations[0]
    parsed_materialization = None
    first_activation = False
    target = None
    requires_validation = False
    if materialization is not None:
        parsed_materialization = find_materialization_payload(materialization, plan.source)
        if parsed_materialization is None:
            raise RuntimeError("EFFECT_REQUEST materialization payload is invalid")
        first_activation = parsed_materialization.expected_change == "unset"
        if first_activation and (
            plan.source != WorkerRequest(plan.source.issue_number, "lead", "propose-change")
            or worker_result.change != "unset"
            or worker_result.typed_result.result.kind.value != _FIRST_ACTIVATION_RESULT
        ):
            raise RuntimeError("EFFECT_REQUEST first materialization is not activation-ready")
        requires_validation = materialization_requires_validation(
            parsed_materialization, plan.source
        )

    # Post-ACCEPT Executor slices have already passed candidate verification,
    # but their checkpoint is a distinct non-idempotent, revision-bound effect.
    # First construct the exact carrier without comments or routing; only a
    # later fresh proof of its actual head may bind and persist the checkpoint.
    defer_accepted_checkpoint = False
    if (
        accepted_intent is not None
        and plan.source.role == "executor"
        and plan.source.action == "implement-change"
        and materialization is not None
        and not requires_validation
    ):
        committed_result = _qualified_committed_implementation_result(
            repository=repository,
            token=token,
            source=plan.source,
            worker_result=worker_result,
            change=effective_change,
            current_revision=args.revision,
            request_comment_id=plan.request_comment_id,
        )
        checkpoint_proof = prove_materialization(
            materialization,
            plan.source,
            repository=repository,
            token=token,
            current_revision=args.revision,
            default_branch=args.default_branch,
            accepted_authorization_revision=request.authorization_revision,
            allow_pending_continuation=plan.pending_continuation,
            accepted_intent=True,
            accepted_successor_routing=(None if committed_result is None else committed_result[2]),
            committed_formal_result=committed_result is not None,
        )
        if checkpoint_proof.disposition == "COMPLETE":
            target = checkpoint_proof.target
            if committed_result is not None:
                if (
                    checkpoint_proof.witness is None
                    or checkpoint_proof.witness.revision != committed_result[0]
                    or target is None
                    or target.revision != committed_result[0]
                ):
                    raise RuntimeError(
                        "committed implementation witness differs from formal result"
                    )
                if not consequence_postconditions_complete(
                    semantic_worker_result,
                    source=plan.source,
                    repository=repository,
                    token=token,
                    current_revision=args.revision,
                    authorized_change=effective_change,
                    request_comment_id=plan.request_comment_id,
                    allow_pending_continuation=plan.pending_continuation,
                    accepted_authorization_revision=request.authorization_revision,
                    allow_accepted_successor=True,
                    accepted_intent=True,
                    observed_application_correlation=committed_result[1],
                    formal_result_observed=True,
                ):
                    raise RuntimeError("committed implementation consequence is not complete")
                # The formal result and its derived successor are already
                # durable. No checkpoint, carrier, formal comment, or routing
                # effect may be reapplied by this historical accepted request.
                _write_carrier_outputs(ApplyResult(True, "already-formally-committed"))
                _write_validation_outputs(None)
                return 0
        elif checkpoint_proof.disposition == "INCOMPLETE" and committed_result is None:
            defer_accepted_checkpoint = True
        else:
            raise RuntimeError(
                checkpoint_proof.reason
                or "accepted implementation materialization proof is unavailable"
            )

    pending_continuation = plan.pending_continuation
    context.stage = "application-effect-preparation"
    if (
        first_activation
        and accepted_intent is not None
        and request.authorization_revision != args.revision
    ):
        pending_continuation = True
    if first_activation and materialization is not None and accepted_intent is not None:
        context.mutation_attempted = True
    if (
        first_activation
        and materialization is not None
        and accepted_intent is not None
        and _repair_partial_first_activation_route(
            raw_worker_result=application_worker_result,
            materialization=materialization,
            accepted_intent=accepted_intent,
            source=plan.source,
            repository=repository,
            token=token,
            current_revision=args.revision,
            default_branch=args.default_branch,
            request_comment_id=plan.request_comment_id,
        )
    ):
        preflight = acquire_current_github_preflight(repository, token)
        dispatch = classify_dispatch(preflight)
        if (
            dispatch.disposition != "AUTHORIZE"
            or dispatch.selected_issue_id != plan.source.issue_number
            or dispatch.selected_routing != (plan.source.role, plan.source.action)
        ):
            raise RuntimeError("partial first activation source route was not reauthorized")
        pending_continuation = True

    if requires_validation and args.validation_passed:
        if materialization is None:
            raise RuntimeError("validation target is missing materialization")
        target = observe_materialization_target(
            materialization,
            plan.source,
            repository=repository,
            token=token,
            current_revision=args.revision,
            default_branch=args.default_branch,
            accepted_authorization_revision=request.authorization_revision,
            allow_pending_continuation=pending_continuation,
            accepted_intent=accepted_intent is not None,
        )
        if args.validated_revision is None or target.revision != args.validated_revision:
            raise RuntimeError("EFFECT_REQUEST validation proof is stale")
    elif not requires_validation and args.validation_passed:
        raise RuntimeError("EFFECT_REQUEST has no validation gate to complete")
    elif args.validation_passed:
        raise RuntimeError("EFFECT_REQUEST validation completion has no materialization")

    checkpoint_already_durable = False
    if target is not None:
        if (
            accepted_intent is not None
            and plan.source.role == "executor"
            and plan.source.action == "implement-change"
            and not requires_validation
        ):
            checkpoint_already_durable = _accepted_checkpoint_already_durable(
                application_worker_result,
                source=plan.source,
                repository=repository,
                token=token,
                current_revision=args.revision,
                request_comment_id=plan.request_comment_id,
            )
        application_worker_result = _rebind_application_result_revision(
            application_worker_result,
            target.revision,
            rebind_checkpoint=not checkpoint_already_durable,
        )
        worker_result = parse_worker_result(
            application_worker_result,
            plan.source,
            authorized_change=plan.change,
        )

    retained_formal_correlation = plan.pending_application_correlation
    predecessor_disposition = (
        None
        if predecessor_evidence is None
        else _accepted_predecessor_disposition(predecessor_evidence)
    )
    uncertain_effect_index = None
    original_effect_count: int | None = None
    missing_pr_only_plan: CarrierPlan | None = None
    if predecessor_disposition == "INDETERMINATE" and predecessor_evidence is not None:
        failure = (
            predecessor_evidence.document.get("failure_evidence")
            if isinstance(predecessor_evidence, ApplicationRecoveryArtifact)
            else None
        )
        if isinstance(predecessor_evidence, ApplicationExceptionArtifact) or (
            isinstance(failure, Mapping)
            and _accepted_recovery_boundary(failure) == "POST_EFFECT_RESULT"
        ):
            # Each contract stage has a distinct failure cause; a compound
            # boolean cannot diagnose which proof was missing.
            accepted_original = semantic_worker_result
            if accepted_intent is None:
                raise RuntimeError("post-effect recovery lost its immutable accepted intent")
            if requires_validation:
                # Keep the existing exact first-activation proof/validation gate.
                original_identity = _accepted_activation_effect_identity(
                    accepted_original,
                    source=plan.source,
                    change=effective_change,
                    projected_raw=application_worker_result,
                )
                if (
                    original_identity.disposition != "EXACT"
                    or original_identity.projected_index is None
                ):
                    raise RuntimeError(
                        "post-effect original activation identity is "
                        + original_identity.disposition.lower()
                    )
                uncertain_effect_index = original_identity.projected_index
            else:
                # Derive the old attempted prefix from immutable accepted
                # effects, not a Role, error class or new arbitrary cursor.
                application_worker_result, original_effect_count = (
                    _accepted_reconciliation_effect_projection(
                        accepted_raw=accepted_original,
                        projected_raw=application_worker_result,
                        source=plan.source,
                        change=effective_change,
                    )
                )
                uncertain_effect_index = original_effect_count - 1
            recovery_proof = _observe_accepted_post_effect_result(
                record=accepted_intent,
                source=plan.source,
                repository=repository,
                token=token,
                current_revision=args.revision,
                default_branch=args.default_branch,
            )
            if recovery_proof.continuation == "REJECT":
                raise RuntimeError(
                    "accepted post-effect recovery is unsafe: " + recovery_proof.reason
                )
            if recovery_proof.continuation == "OBSERVE":
                # A temporary read failure cannot grant a write. The failed
                # native invocation will retain its own exact exception
                # artifact; the next fresh Dispatch may re-observe it.
                raise RuntimeError("accepted post-effect recovery observation unavailable")
            missing_pr_only_plan = recovery_proof.carrier_plan
        if isinstance(failure, Mapping) and _accepted_recovery_boundary(failure) == "READ_ONLY":
            candidate_index = failure.get("failed_effect_index")
            if type(candidate_index) is int:
                uncertain_effect_index = candidate_index
            if "attempted_effects" in failure:
                if accepted_intent is None:
                    raise RuntimeError("read-only continuation lost its accepted intent")
                exact_source = WorkerRequest(
                    accepted_intent.issue_number, accepted_intent.role, accepted_intent.action
                )
                proof = classify_accepted_read_only_effects(
                    record=accepted_intent,
                    source=exact_source,
                    recovery_evidence=failure,
                    repository=repository,
                    token=token,
                    current_revision=args.revision,
                    default_branch=args.default_branch,
                    recovery_artifact=(
                        predecessor_evidence
                        if isinstance(predecessor_evidence, ApplicationRecoveryArtifact)
                        else None
                    ),
                )
                if proof.continuation == "REJECT":
                    # Preserve the immutable accepted intent, but do not turn
                    # a contradiction into yet another observable UNKNOWN.
                    raise RuntimeError("accepted read-only recovery evidence conflict")
                if proof.continuation == "OBSERVE":
                    # A dispatch-time proof may disappear before Application
                    # reauthorization. Persist only a read-only boundary with
                    # the SAME attempted identity, and never apply a newly
                    # projected Effect on this invocation.
                    deferred = ApplyResult(
                        False, "accepted original effect not currently proven complete"
                    )
                    if not _write_application_recovery_evidence(
                        args.recovery_evidence_path,
                        result=deferred,
                        repository=repository,
                        token=token,
                        source=plan.source,
                        request_comment_id=plan.request_comment_id,
                        trigger_comment_id=event_comment_id or plan.request_comment_id,
                        authorization_revision=request.authorization_revision,
                        current_revision=args.revision,
                        run_attempt=args.run_attempt,
                        continuation=continuation,
                        predecessor=predecessor_evidence,
                        preserve_predecessor_failure=True,
                    ):
                        raise RuntimeError("read-only attempted-effect checkpoint was not durable")
                    _write_carrier_outputs(deferred)
                    _write_validation_outputs(None)
                    return 0
                # The exact historical write has been independently proven
                # complete. The next fresh projection is *new*, not the
                # originally uncertain Effect at its former array index.
                predecessor_disposition = "RECONCILE_EFFECTS"
                uncertain_effect_index = None
                restored_formal = _retain_completed_accepted_formal_effect(
                    application_worker_result,
                    failure=failure,
                    source=plan.source,
                    change=accepted_intent.change,
                    result_kind=accepted_intent.result_kind,
                    request_comment_id=plan.request_comment_id,
                )
                if restored_formal is not None:
                    application_worker_result, retained_formal_correlation = restored_formal
                    worker_result = parse_worker_result(
                        application_worker_result,
                        plan.source,
                        authorized_change=plan.change,
                    )
    if continuation is not None and predecessor_disposition == "ZERO_WRITE_REJECTION":
        # Only a *proven* deterministic zero-write rejection takes the
        # administrative correction route. CarrierRequired (even for merge)
        # instead resumes normal fresh effect/postcondition reconciliation.
        # Neither path changes the original ACCEPTED result.
        if plan.source.action not in {"merge-implementation-pr", "merge-archive-pr"}:
            raise RuntimeError("accepted effect rejection has no governed correction handoff")
        if not isinstance(predecessor_evidence, ApplicationRecoveryArtifact):
            raise RuntimeError("accepted merge recovery predecessor is missing")
        reconstructed = _rejected_merge_result_from_checkpoint(predecessor_evidence)
        batch = parse_effect_batch(
            application_worker_result,
            plan.source,
            authorized_change=plan.change,
        )
        if reconstructed is None or not _recover_deterministic_accepted_merge_failure(
            result=reconstructed,
            batch=batch,
            source=plan.source,
            repository=repository,
            token=token,
            current_revision=args.revision,
            default_branch=args.default_branch,
            request_comment_id=plan.request_comment_id,
        ):
            raise RuntimeError("accepted merge recovery cannot establish a safe durable handoff")
        _write_carrier_outputs(ApplyResult(True, "accepted-merge-recovery-handoff"))
        _write_validation_outputs(None)
        print(
            json.dumps(
                {"applied": True, "reason": "accepted-merge-recovery-handoff", "effects": 0},
                sort_keys=True,
            )
        )
        return 0

    context.stage = "application-effect-and-postcondition"
    # A new raw comment cannot become an accepted intent from a source
    # that lost qualification while Phase A prepared its effects.
    if (
        raw_transport
        and accepted_intent is None
        and _fresh_event_observation(event, body, repository, token)
    ):
        raise ValueError("WORKER_RESULT comment changed before Phase-A ACCEPT")
    context.mutation_attempted = True
    try:
        if missing_pr_only_plan is not None:
            # Native carrier actuator is the mutation boundary and rechecks
            # the accepted PR-only plan against fresh GitHub postconditions.
            raise CarrierRequired(missing_pr_only_plan)
        if first_activation and args.validation_passed:
            batch, result = run_guarded_effect_application(
                application_worker_result,
                source=plan.source,
                repository=repository,
                token=token,
                current_revision=args.revision,
                apply_derived=False,
                materialization_promote_change=False,
                validated_materialization_revision=(None if target is None else target.revision),
                request_comment_id=plan.request_comment_id,
                defer_issue_comments=first_activation,
                allow_pending_continuation=pending_continuation,
                pending_application_correlation=retained_formal_correlation,
                application_request_body=application_request_body,
                authorization_revision=request.authorization_revision,
                authorized_change=plan.change,
                **({"accepted_intent": True} if accepted_intent is not None else {}),
                **({"reconcile_only": True} if predecessor_disposition == "INDETERMINATE" else {}),
                uncertain_effect_index=uncertain_effect_index,
                **(
                    {"proven_empty_original_effects": True}
                    if original_effect_count == 0 and predecessor_disposition == "INDETERMINATE"
                    else {}
                ),
            )
            if result.applied:
                if materialization is None or target is None:
                    raise RuntimeError("first activation validation target is unavailable")
                if accepted_intent is None:
                    raise RuntimeError("first activation accepted application decision is missing")
                _complete_first_activation(
                    raw_worker_result=application_worker_result,
                    materialization=materialization,
                    target=target,
                    source=plan.source,
                    repository=repository,
                    token=token,
                    current_revision=args.revision,
                    default_branch=args.default_branch,
                    request_comment_id=plan.request_comment_id,
                    accepted_authorization_revision=accepted_intent.authorization_revision,
                    allow_pending_continuation=pending_continuation,
                )
        else:
            batch, result = run_guarded_effect_application(
                application_worker_result,
                source=plan.source,
                repository=repository,
                token=token,
                current_revision=args.revision,
                apply_derived=(
                    (not requires_validation or args.validation_passed)
                    and not defer_accepted_checkpoint
                ),
                materialization_promote_change=args.validation_passed,
                validated_materialization_revision=(
                    None if target is None or checkpoint_already_durable else target.revision
                ),
                request_comment_id=plan.request_comment_id,
                defer_issue_comments=(requires_validation and not args.validation_passed)
                or defer_accepted_checkpoint,
                allow_pending_continuation=pending_continuation,
                pending_application_correlation=retained_formal_correlation,
                application_request_body=application_request_body,
                authorization_revision=request.authorization_revision,
                authorized_change=plan.change,
                **({"accepted_intent": True} if accepted_intent is not None else {}),
                **({"reconcile_only": True} if predecessor_disposition == "INDETERMINATE" else {}),
                uncertain_effect_index=uncertain_effect_index,
                **(
                    {"proven_empty_original_effects": True}
                    if original_effect_count == 0 and predecessor_disposition == "INDETERMINATE"
                    else {}
                ),
            )
    except CarrierRequired as exc:
        # CarrierRequired is the hard invocation-exit boundary. Persist only
        # the exact application-authorized plan; a later fresh wake must
        # reconstruct repository truth before any missing effect or successor.
        carrier_result = ApplyResult(False, "carrier_required", carrier_plan=exc.plan)
        _write_carrier_outputs(carrier_result)
        _write_validation_outputs(None)
        if plan.source is not None and plan.request_comment_id is not None:
            _write_application_recovery_evidence(
                args.recovery_evidence_path,
                result=carrier_result,
                repository=repository,
                token=token,
                source=plan.source,
                request_comment_id=plan.request_comment_id,
                trigger_comment_id=event_comment_id or plan.request_comment_id,
                authorization_revision=request.authorization_revision,
                current_revision=args.revision,
                run_attempt=args.run_attempt,
                continuation=continuation,
                predecessor=predecessor_evidence,
            )
        print(
            json.dumps(
                {
                    "applied": False,
                    "reason": carrier_result.reason,
                    "effects": 0,
                    "validation_required": requires_validation,
                    "validation_completed": args.validation_passed,
                    "carrier_required": True,
                    "carrier_plan_id": exc.plan.plan_id,
                },
                sort_keys=True,
            )
        )
        return 0

    # A zero-write rejection may need an administrative comment and routing
    # write. Its recoverable predecessor artifact must be available to the
    # existing normal-dispatch APPLICATION_CONTINUATION channel *before*
    # either GitHub write, including if the process fails after the comment.
    recovery_evidence_written = False
    if (
        not result.applied
        and result.carrier_plan is None
        and plan.source.action in {"merge-implementation-pr", "merge-archive-pr"}
    ):
        recovery_evidence_written = _write_application_recovery_evidence(
            args.recovery_evidence_path,
            result=result,
            repository=repository,
            token=token,
            source=plan.source,
            request_comment_id=plan.request_comment_id,
            trigger_comment_id=event_comment_id or plan.request_comment_id,
            authorization_revision=request.authorization_revision,
            current_revision=args.revision,
            run_attempt=args.run_attempt,
            continuation=continuation,
            predecessor=predecessor_evidence,
            effect_batch=batch,
        )
    if recovery_evidence_written and _recover_deterministic_accepted_merge_failure(
        result=result,
        batch=batch,
        source=plan.source,
        repository=repository,
        token=token,
        current_revision=args.revision,
        default_branch=args.default_branch,
        request_comment_id=plan.request_comment_id,
    ):
        _write_carrier_outputs(ApplyResult(True, "accepted-merge-recovery-handoff"))
        _write_validation_outputs(None)
        print(
            json.dumps(
                {
                    "applied": True,
                    "reason": "accepted-merge-recovery-handoff",
                    "effects": 0,
                    "replayed_merge": False,
                },
                sort_keys=True,
            )
        )
        return 0

    if result.carrier_plan is not None:
        # Keep compatibility with an adapter that returns the existing carrier
        # result surface while enforcing the same invocation boundary.
        _write_carrier_outputs(result)
        _write_validation_outputs(None)
        _write_application_recovery_evidence(
            args.recovery_evidence_path,
            result=result,
            repository=repository,
            token=token,
            source=plan.source,
            request_comment_id=plan.request_comment_id,
            trigger_comment_id=event_comment_id or plan.request_comment_id,
            authorization_revision=request.authorization_revision,
            current_revision=args.revision,
            run_attempt=args.run_attempt,
            continuation=continuation,
            predecessor=predecessor_evidence,
            effect_batch=batch,
        )
        print(
            json.dumps(
                {
                    "applied": False,
                    "reason": result.reason,
                    "effects": len(batch.effects),
                    "validation_required": requires_validation,
                    "validation_completed": args.validation_passed,
                    "carrier_required": True,
                    "carrier_plan_id": result.carrier_plan.plan_id,
                },
                sort_keys=True,
            )
        )
        return 0
    if result.applied and requires_validation and not args.validation_passed:
        if materialization is None:
            raise RuntimeError("validation gate has no materialization target")
        target = observe_materialization_target(
            materialization,
            plan.source,
            repository=repository,
            token=token,
            current_revision=args.revision,
            default_branch=args.default_branch,
            accepted_authorization_revision=request.authorization_revision,
            allow_pending_continuation=pending_continuation,
            accepted_intent=accepted_intent is not None,
        )
    else:
        target = None
    _write_carrier_outputs(result)
    _write_validation_outputs(target)
    if not recovery_evidence_written:
        _write_application_recovery_evidence(
            args.recovery_evidence_path,
            result=result,
            repository=repository,
            token=token,
            source=plan.source,
            request_comment_id=plan.request_comment_id,
            trigger_comment_id=event_comment_id or plan.request_comment_id,
            authorization_revision=request.authorization_revision,
            current_revision=args.revision,
            run_attempt=args.run_attempt,
            continuation=continuation,
            predecessor=predecessor_evidence,
            effect_batch=batch,
        )
    print(
        json.dumps(
            {
                "applied": result.applied,
                "reason": result.reason,
                "effects": len(batch.effects),
                "validation_required": requires_validation,
                "validation_completed": args.validation_passed,
                "carrier_required": result.carrier_plan is not None,
                "carrier_plan_id": None
                if result.carrier_plan is None
                else result.carrier_plan.plan_id,
                "failure_evidence": _public_failure_diagnostics(result),
            },
            sort_keys=True,
        )
    )
    return 0 if result.applied or result.carrier_plan is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
