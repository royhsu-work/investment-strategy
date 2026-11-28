"""Run-scoped machine dispatch transport."""

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
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.human_authority import (
    decision_comment_from_raw,
    is_human_decision_approved,
    label_event_from_raw,
    parse_decision_ref,
)
from investment_strategy.scheduled_agent_action_model import Action as ModelAction
from investment_strategy.scheduled_agent_action_model import next_action, role_for
from investment_strategy.scheduled_agent_application_bridge import (
    AcceptedPostEffectProof,
    ApplicationContinuationRequest,
    ApplicationExceptionArtifact,
    ApplicationRecoveryArtifact,
    ApplicationRequest,
    CompleteNeverCalledWitness,
    RecoveryEvidenceNode,
    RecoveryProofResult,
    TypedEvidenceError,
    _accepted_correction_observer_for_batch,
    _accepted_recovery_boundary,
    _application_owned_worker_result,
    _claimed_source,
    _materialization_effects,
    _qualified_accepted_original_effects,
    _qualified_physical_original_accepted_effects,
    application_artifact_stage,
    application_continuation_correlation,
    classify_accepted_read_only_effects,
    classify_application_exception_recovery,
    classify_post_effect_result_recovery,
    dispatch_correlation_for,
    parse_application_continuation_request,
    parse_application_request,
    read_application_exception_artifact,
    read_application_recovery_artifact,
    render_application_continuation_request,
)
from investment_strategy.scheduled_agent_application_bridge import (
    _github_json as _application_github_json,
)
from investment_strategy.scheduled_agent_application_carrier import qualify_implementation_carrier
from investment_strategy.scheduled_agent_application_materialization import (
    MaterializationProof,
    MaterializationRequest,
    _proof_witness,
    find_materialization_payload,
    prove_materialization,
)
from investment_strategy.scheduled_agent_carrier import (
    CarrierOutcomeReport,
    CarrierPlan,
    QualifiedApplicationJob,
    QualifiedCarrierPlan,
    github_comment_has_app_provenance,
    github_complete_job_inventory,
    github_complete_run_jobs,
    github_original_request_matches,
    github_paginated_mappings,
    github_read_bytes_with_retry,
    github_repository_api_url,
    github_run_artifact_identity,
    github_run_artifact_inventory,
    parse_carrier_outcome_report,
    parse_carrier_plan_document,
    parse_qualified_carrier_document,
    qualified_carrier_document,
    read_github_artifact_bytes,
)
from investment_strategy.scheduled_agent_checkin import is_runtime_checkin_issue
from investment_strategy.scheduled_agent_effects import (
    ApplicationDecisionRecord,
    ApplyResult,
    EffectBatch,
    StagedEffect,
    _implementation_development_save,
    _slice_checkpoint_completed_task_ids,
    consequence_postconditions_complete,
    merged_pr_readiness_complete,
    parse_application_decision,
    parse_effect_batch,
)
from investment_strategy.scheduled_agent_formal_qualification import (
    CurrentFrontier,
    QualificationInput,
    bind_initial_source_admission,
    build_qualification_input,
    derive_current_frontier,
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
from investment_strategy.scheduled_agent_validation_resource import (
    NativeQualityAttempt,
    _content_sha_at,
    _content_text_at,
    _task_slices,
    native_quality_setup_failure_index,
    native_quality_witness_matches,
    openspec_review_revision_applies,
    qualify_native_quality_job,
    read_native_quality_attempt,
    reduce_native_quality_attempts,
    task_checkpoint_is_exact,
)
from investment_strategy.scheduled_agent_wire import RUNTIME_REPAIR_REQUEST_WIRE
from investment_strategy.scheduled_agent_worker import (
    WorkerActionResult,
    parse_worker_result,
)
from investment_strategy.workflow_dispatch import (
    DispatchDecision,
    DispatchPreflight,
    classify_dispatch,
    pending_continuation_candidate,
)

REQUEST_MARKER = "DISPATCH_REQUEST"
REQUESTED_AT_PREFIX = "Requested-At: "
RUN_NAME_PREFIX = "Scheduled Agent Dispatch "
APPLICATION_RUN_NAME_PREFIX = "Scheduled Agent Application "
DISPATCH_RESULT_SCHEMA = "scheduled-agent-dispatch-result/v1"
_APPLICATION_WORKFLOW = "scheduled-agent-application.yml"
_DISPATCH_WORKFLOW = "scheduled-agent-bridge.yml"
_QUALITY_WORKFLOW = "quality.yml"
_APPLICATION_DECISION_PROTOCOL_REVISION = "e874b4bdfc866649c0e7e61c151991d124d5c0c6"
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"
_FORMAL_RESULT_MARKERS = frozenset({"ACTION_RESULT", "REVIEW_RESULT", "MERGE_RESULT"})
_DECISION_DISPOSITIONS = {"AUTHORIZE", "NO_WORK", "FAIL_CLOSED"}
_TERMINAL_NO_ACCEPT_CONCLUSIONS = frozenset(
    {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale", "skipped"}
)
_MAX_REASON_LENGTH = 240
_MAX_RESULT_BYTES = 16_384
_LEGACY_SOURCE_B64_PREFIX_CHARS = 8_192
_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class DispatchRequest:
    requested_at: str


@dataclass(frozen=True)
class MachineDispatchDecision:
    request_comment_id: int
    default_branch_revision: str
    disposition: str
    issue_number: int | None = None
    role: str | None = None
    action: str | None = None
    reason: str | None = None
    application_continuation: str | None = None
    qualified_carrier: QualifiedCarrierPlan | None = None


@dataclass(frozen=True)
class BridgePlan:
    should_emit: bool
    issue_number: int | None = None
    request_comment_id: int | None = None
    result_body: str | None = None
    quality_call: dict[str, str] | None = None


@dataclass(frozen=True)
class DevelopmentDispatchSource:
    """One native authorization bound to its actual ingress boundary."""

    dispatch_request_comment_id: int
    run_id: int
    run_attempt: int
    job_id: int
    artifact_id: int
    artifact_digest: str
    authorization_revision: str


@dataclass(frozen=True)
class NativeQualityObligation:
    """Exact saved-work gate; never a new durable lifecycle state."""

    revision: str
    branch: str
    workflow_blob: str
    obligation_id: str
    accepted_at: str
    default_branch: str
    carrier_revision: str
    carrier_base: str


@dataclass(frozen=True)
class ApplicationCompletion:
    state: Literal["NONE", "REJECTED", "RESUMABLE", "COMPLETE", "ABORTED", "INVALID", "AMBIGUOUS"]
    reason: str
    request_comment_id: int | None = None
    job_id: int | None = None
    qualified_carrier: QualifiedCarrierPlan | None = None
    recovery_artifact: ApplicationRecoveryArtifact | ApplicationExceptionArtifact | None = None
    # Only the Application's actual accepted proof can propose an R9 intake.
    accepted_proof: AcceptedPostEffectProof | None = None
    # Application-owned exact accepted-source proof, not Bridge-local history.
    accepted_record: ApplicationDecisionRecord | None = None
    accepted_decision_sha256: str | None = None
    quality_obligation: NativeQualityObligation | None = None
    quality_observation: NativeQualityObservation | None = None
    settled_quality_obligation: NativeQualityObligation | None = None
    settled_development_records: tuple[ApplicationDecisionRecord, ...] = ()


# The canonical proof owns permission. This Bridge-only table preserves the
# existing reason vocabulary without inventing a second recovery decision.
_ACCEPTED_PROOF_FAILURE_REASONS = {
    "EXCEPTION": {
        "INDETERMINATE": "application-completion-exception-observing",
        "NOT_APPLIED": "application-completion-exception-unsafe",
        "UNSAFE": "application-completion-exception-unsafe",
    },
    "POST_EFFECT": {
        "INDETERMINATE": "application-completion-post-effect-observing",
        "NOT_APPLIED": "application-completion-original-effect-incomplete",
        "UNSAFE": "application-completion-original-effect-unsafe",
    },
    "READ_ONLY": {
        "INDETERMINATE": "application-completion-read-only-observing",
        "NOT_APPLIED": "application-completion-read-only-proof-conflict",
        "UNSAFE": "application-completion-read-only-proof-conflict",
    },
}


def _unresolved_accepted_proof_completion(
    proof: AcceptedPostEffectProof,
    *,
    origin: Literal["EXCEPTION", "POST_EFFECT", "READ_ONLY"],
    request_comment_id: int,
    recovery_artifact: ApplicationRecoveryArtifact | ApplicationExceptionArtifact | None,
    accepted_record: ApplicationDecisionRecord | None = None,
    accepted_decision_sha256: str | None = None,
) -> ApplicationCompletion | None:
    """Project one accepted-source Application proof into non-authorizing evidence."""

    if proof.continuation == "CONTINUE":
        return None
    return ApplicationCompletion(
        "RESUMABLE" if proof.continuation == "OBSERVE" else "INVALID",
        _ACCEPTED_PROOF_FAILURE_REASONS[origin][proof.disposition],
        request_comment_id=request_comment_id,
        recovery_artifact=recovery_artifact,
        accepted_proof=proof,
        accepted_record=accepted_record,
        accepted_decision_sha256=accepted_decision_sha256,
    )


RecoveryPredicate = Literal["COMPLETE", "INCOMPLETE", "UNKNOWN", "CONFLICT"]


@dataclass(frozen=True)
class RecoveryReviewAdoption:
    """A source-qualified semantic review; never a synthetic REVIEW_RESULT."""

    disposition: RecoveryPredicate
    reason: str
    review_id: str | None = None
    revision: str | None = None


@dataclass(frozen=True)
class RecoveryPreFormalQualification:
    """Fixed predicate results for an accepted #322 READY, before formal persistence."""

    disposition: RecoveryPredicate
    predicates: tuple[tuple[str, RecoveryPredicate], ...]

    @property
    def blocking_predicates(self) -> tuple[str, ...]:
        return tuple(name for name, status in self.predicates if status != "COMPLETE")


def _recovery_predicate_result(
    predicates: Mapping[str, RecoveryPredicate],
) -> RecoveryPreFormalQualification:
    """Qualify only evidence relevant to the pending formal-result effect."""

    if set(predicates) != {"I", "R", "M", "S", "F"}:
        raise ValueError("recovery predicate set is incomplete")
    ordered = tuple((name, predicates[name]) for name in ("I", "R", "M", "S", "F"))
    for disposition in ("CONFLICT", "UNKNOWN", "INCOMPLETE", "COMPLETE"):
        if disposition in predicates.values():
            return RecoveryPreFormalQualification(cast(RecoveryPredicate, disposition), ordered)
    raise ValueError("recovery predicate state is invalid")


def _recovery_task_disposition(raw_tasks: object) -> RecoveryPredicate:
    """Classify task progress only; a checked marker is never effect proof."""

    if not isinstance(raw_tasks, str):
        return "UNKNOWN"
    if "## 0G. Forward Recovery" not in raw_tasks or "0.42 **RED:**" not in raw_tasks:
        return "CONFLICT"
    if re.search(r"(?m)^\s*- \[ \] \d+(?:\.\d+)?\s", raw_tasks):
        return "INCOMPLETE"
    if not all(f"- [x] {task}" in raw_tasks for task in ("0.42", "0.43", "0.44")):
        return "INCOMPLETE"
    return "COMPLETE"


_RECOVERY_NECESSARY_EXECUTABLE_FILES = frozenset(
    {
        "src/investment_strategy/issue_comment_bridge.py",
        "src/investment_strategy/scheduled_agent_effects.py",
        "tests/test_issue_comment_bridge.py",
        "tests/test_scheduled_agent_effects.py",
    }
)


_RECOVERY_REVIEW_MARKER = "RECOVERY_OPENSPEC_REVIEW"
_RECOVERY_REVIEW_FIELDS = (
    "Repository",
    "Issue",
    "Change",
    "PR",
    "Revision",
    "Baseline",
    "Human-Decision-Comment",
    "Validator-Run",
    "Disposition",
)
_RECOVERY_NORMATIVE_PREFIXES = (
    "openspec/config.yaml",
    "openspec/specs/",
    "openspec/changes/restore-no-work-idle-discovery/proposal.md",
    "openspec/changes/restore-no-work-idle-discovery/design.md",
    "openspec/changes/restore-no-work-idle-discovery/specs/",
    "agents/AGENTS.md",
    "agents/workflow.md",
    "agents/roles/",
    "agents/skills/",
)


def _recovery_review_receipt(body: object) -> dict[str, str] | None:
    """Parse only the spec's ordered receipt, never prose semantic equivalence."""

    if not isinstance(body, str):
        return None
    lines = body.splitlines()
    if len(lines) < 10 or lines[0] != _RECOVERY_REVIEW_MARKER:
        return None
    fields: dict[str, str] = {}
    for field, line in zip(_RECOVERY_REVIEW_FIELDS, lines[1:10], strict=True):
        prefix = f"{field}: "
        if not line.startswith(prefix):
            return None
        value = line[len(prefix) :]
        if not value or value != value.strip():
            return None
        fields[field] = value
    if len(lines) > 10 and lines[10] not in {"", "---"}:
        return None
    if (
        _SHA.fullmatch(fields["Revision"]) is None
        or _SHA.fullmatch(fields["Baseline"]) is None
        or _positive_int_string(fields["Issue"]) is None
        or _positive_int_string(fields["PR"]) is None
        or _positive_int_string(fields["Human-Decision-Comment"]) is None
        or _positive_int_string(fields["Validator-Run"]) is None
        or fields["Disposition"] not in {"PASS", "FINDINGS"}
    ):
        return None
    return fields


def _recovery_review_log_proves_checkout(log: str, repository: str, revision: str) -> bool:
    """Require executed checkout identity and successful strict validation output."""

    def exact_output(field: str, value: str) -> bool:
        found = re.findall(
            rf"(?m)^(?:\d{{4}}-\d\d-\d\dT\S+Z )?{re.escape(field)}=([^\s\r\n]+)$",
            log,
        )
        return bool(found) and all(item == value for item in found)

    return (
        exact_output("validation_target_repository", repository)
        and exact_output("validation_target_sha", revision)
        and exact_output("validator_checkout_head", revision)
        and "Run openspec validate --all --strict --json --no-interactive" in log
        and re.search(r'"totals"\s*:\s*\{', log) is not None
        and re.search(r'"passed"\s*:\s*[1-9]\d*', log) is not None
        and re.search(r'"failed"\s*:\s*0\b', log) is not None
    )


def _latest_recovery_review(
    reviews: object,
    *,
    repository: str,
    issue_number: int,
    change: str,
    pr_number: int,
) -> tuple[Mapping[str, object], dict[str, str]] | RecoveryReviewAdoption:
    """Select the latest exact-R receipt without erasing earlier review history.

    Corrected FINDINGS on a *different earlier revision* remain historical.
    Same-R duplicate or contradictory verdicts never become a unique PASS.
    """
    unknown = RecoveryReviewAdoption("UNKNOWN", "recovery-review-source-incomplete")
    conflict = RecoveryReviewAdoption("CONFLICT", "recovery-review-source-conflict")
    if not isinstance(reviews, (list, tuple)):
        return unknown
    candidates: list[tuple[datetime, Mapping[str, object], dict[str, str]]] = []
    seen_revisions: set[str] = set()
    for review in reviews:
        if not isinstance(review, Mapping) or not isinstance(review.get("body"), str):
            return unknown
        body = cast(str, review["body"])
        if not body.startswith(_RECOVERY_REVIEW_MARKER):
            continue
        receipt = _recovery_review_receipt(body)
        if receipt is None:
            return conflict
        if (
            receipt["Repository"] != repository
            or receipt["Issue"] != str(issue_number)
            or receipt["Change"] != change
            or receipt["PR"] != str(pr_number)
            or review.get("commit_id") != receipt["Revision"]
        ):
            return conflict
        if receipt["Revision"] in seen_revisions:
            return conflict
        seen_revisions.add(receipt["Revision"])
        submitted_at = review.get("submitted_at")
        if not isinstance(submitted_at, str):
            return unknown
        try:
            stamp = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        except ValueError:
            return unknown
        if stamp.utcoffset() is None:
            return unknown
        candidates.append((stamp, review, receipt))
    if not candidates:
        return unknown
    candidates.sort(key=lambda item: item[0])
    if len(candidates) > 1 and candidates[-1][0] == candidates[-2][0]:
        return conflict
    _stamp, review, receipt = candidates[-1]
    if receipt["Disposition"] != "PASS":
        return conflict
    return review, receipt


def qualify_recovery_openspec_review(
    *,
    repository: str,
    issue_number: int,
    change: str,
    pr_number: int,
    head_sha: str,
    approval_label_present: bool,
    reviews: object,
    commit: object,
    original_human_comment: object,
    issue_comments: object,
    events: object,
    validator: object,
    validator_job: object,
    validator_log: object,
    comparison: object,
    baseline_comparison: object,
    reviewed_blobs: object,
    current_blobs: object,
    threads: object,
) -> RecoveryReviewAdoption:
    """Adopt one independent exact-R semantic PR review as evidence for V only.

    Callers must supply complete freshly paginated GitHub source collections and
    the actual validator job log. No model decision or formal result is consumed.
    """

    unknown = RecoveryReviewAdoption("UNKNOWN", "recovery-review-source-incomplete")
    conflict = RecoveryReviewAdoption("CONFLICT", "recovery-review-source-conflict")
    if (
        repository != "royhsu-work/investment-strategy"
        or issue_number != 322
        or change != "restore-no-work-idle-discovery"
        or pr_number != 340
        or _SHA.fullmatch(head_sha) is None
    ):
        return conflict
    if (
        not isinstance(reviews, (list, tuple))
        or not isinstance(commit, Mapping)
        or not isinstance(original_human_comment, Mapping)
        or not isinstance(issue_comments, (list, tuple))
        or not isinstance(events, (list, tuple))
        or not isinstance(validator, Mapping)
        or not isinstance(validator_job, Mapping)
        or not isinstance(validator_log, str)
        or not isinstance(comparison, Mapping)
        or not isinstance(baseline_comparison, Mapping)
        or not isinstance(reviewed_blobs, Mapping)
        or not isinstance(current_blobs, Mapping)
        or not isinstance(threads, (list, tuple))
    ):
        return unknown
    selected = _latest_recovery_review(
        reviews,
        repository=repository,
        issue_number=issue_number,
        change=change,
        pr_number=pr_number,
    )
    if isinstance(selected, RecoveryReviewAdoption):
        return selected
    review, receipt = selected
    revision = receipt["Revision"]
    review_id = review.get("node_id")
    user = review.get("user")
    author = commit.get("author")
    submitted_at = review.get("submitted_at")
    if (
        not isinstance(review_id, str)
        or not review_id.startswith("PRR_")
        or not isinstance(user, Mapping)
        or not isinstance(author, Mapping)
        or not isinstance(user.get("login"), str)
        or not isinstance(author.get("login"), str)
        or not isinstance(submitted_at, str)
    ):
        return unknown
    if (
        receipt["Disposition"] != "PASS"
        or review.get("commit_id") != revision
        or review.get("state") not in {"COMMENTED", "APPROVED"}
        or receipt["Human-Decision-Comment"] != "6313995887"
        or validator.get("id") != int(receipt["Validator-Run"])
        or validator.get("conclusion") != "success"
        or validator_job.get("name") != "validate"
        or validator_job.get("conclusion") != "success"
        or not _recovery_review_log_proves_checkout(validator_log, repository, revision)
    ):
        return conflict
    if (
        baseline_comparison.get("status") != "ahead"
        or not isinstance(baseline_comparison.get("base_commit"), Mapping)
        or baseline_comparison["base_commit"].get("sha") != receipt["Baseline"]
    ):
        return conflict
    try:
        original_human = decision_comment_from_raw(original_human_comment)
        reviewed_time = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return unknown
    if (
        original_human.id != 6313995887
        or original_human.author != "royhsu-work"
        or not original_human.provenance_available
        or original_human.updated_at != original_human.created_at
        or original_human.created_at >= reviewed_time
        or "Marker: HUMAN_APPROVED_FORWARD_RECOVERY_CONVERGENCE_20261021"
        not in original_human.body.splitlines()
    ):
        return unknown
    # The pinned original decision is a scope/reference witness, not the
    # reserved Human approval. Its historical connector provenance is real;
    # only the separately bound independence attestation and approval event
    # must be Human-only (checked below).
    if revision == head_sha:
        if comparison.get("status") != "identical":
            return conflict
    elif (
        comparison.get("status") != "ahead"
        or not isinstance(comparison.get("base_commit"), Mapping)
        or comparison["base_commit"].get("sha") != revision
    ):
        return conflict

    # Compare the complete normative tree, not only files named in the PR diff.
    # Checked task markers are execution bookkeeping, not normative semantics;
    # this exact subset excludes tasks.md while preserving reviewed design/specs.
    def normative(path: object) -> bool:
        return isinstance(path, str) and path.startswith(_RECOVERY_NORMATIVE_PREFIXES)

    old = {key: value for key, value in reviewed_blobs.items() if normative(key)}
    current = {key: value for key, value in current_blobs.items() if normative(key)}
    if not old or not current:
        return unknown
    if any(
        not isinstance(value, str) or _SHA.fullmatch(value) is None
        for value in (*old.values(), *current.values())
    ):
        return unknown
    if old != current:
        return conflict
    for thread in threads:
        if not isinstance(thread, Mapping) or not isinstance(thread.get("comments"), list):
            return unknown
        for comment in cast(list[object], thread["comments"]):
            if not isinstance(comment, Mapping) or not isinstance(comment.get("body"), str):
                return unknown
            if (
                "RECOVERY_OPENSPEC_FINDING" in cast(str, comment["body"])
                and not thread.get("is_resolved")
                and not thread.get("is_outdated")
            ):
                return conflict
    if user["login"] == author["login"]:
        expected_ref = f"issue:322:recovery-openspec-review:{revision}:{review_id}"
        try:
            comments = tuple(
                decision_comment_from_raw(cast(Mapping[str, object], item))
                for item in issue_comments
            )
            label_events = tuple(
                label_event_from_raw(cast(Mapping[str, object], item))
                for item in events
                if isinstance(item, Mapping) and item.get("event") == "labeled"
            )
        except (TypeError, ValueError):
            return unknown
        bound = tuple(c for c in comments if parse_decision_ref(c.body) == expected_ref)
        if len(bound) > 1:
            return conflict
        if len(bound) != 1:
            return unknown
        attestation = bound[0]
        if (
            attestation.created_at <= reviewed_time
            or attestation.updated_at != attestation.created_at
            or attestation.body.splitlines().count(
                "Recovery-Review-Independence: separately-reviewed"
            )
            != 1
            or not is_human_decision_approved(
                expected_ref=expected_ref,
                approval_label_present=approval_label_present,
                comments=comments,
                label_events=label_events,
            )
        ):
            return unknown
        bound_events = tuple(
            event
            for event in label_events
            if event.actor == "royhsu-work"
            and event.label == "human:approved"
            and event.provenance_available
            and event.performed_via_github_app is None
            and event.created_at > attestation.created_at
        )
        if len(bound_events) != 1:
            return conflict if len(bound_events) > 1 else unknown
    return RecoveryReviewAdoption("COMPLETE", "recovery-review-adopted", review_id, revision)


def _github_job_log(repository: str, token: str, job_id: int) -> str:
    """Read the executed validator log; its run HEAD alone is not checkout proof."""

    request = Request(  # noqa: S310 - fixed GitHub REST host
        f"https://api.github.com/repos/{repository}/actions/jobs/{job_id}/logs",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub API redirect
        return response.read().decode("utf-8")


def _github_review_threads(repository: str, token: str, pr_number: int) -> list[dict[str, object]]:
    """Exhaustive GraphQL review threads, including resolution and comment pagination."""

    owner, name = repository.split("/", 1)
    query = """
    query($owner: String!, $name: String!, $number: Int!, $after: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          reviewThreads(first: 100, after: $after) {
            nodes {
              isResolved
              isOutdated
              comments(first: 100) {
                nodes { body }
                pageInfo { hasNextPage }
              }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
      }
    }
    """
    cursor: str | None = None
    threads: list[dict[str, object]] = []
    while True:
        payload = json.dumps(
            {
                "query": query,
                "variables": {"owner": owner, "name": name, "number": pr_number, "after": cursor},
            }
        ).encode("utf-8")
        request = Request(  # noqa: S310 - fixed GitHub GraphQL host
            "https://api.github.com/graphql",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed host
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, Mapping) or result.get("errors"):
            raise RuntimeError("review thread observation incomplete")
        data = result.get("data")
        repo = data.get("repository") if isinstance(data, Mapping) else None
        pr = repo.get("pullRequest") if isinstance(repo, Mapping) else None
        connection = pr.get("reviewThreads") if isinstance(pr, Mapping) else None
        nodes = connection.get("nodes") if isinstance(connection, Mapping) else None
        page = connection.get("pageInfo") if isinstance(connection, Mapping) else None
        if not isinstance(nodes, list) or not isinstance(page, Mapping):
            raise RuntimeError("review thread pagination incomplete")
        for node in nodes:
            if not isinstance(node, Mapping):
                raise RuntimeError("review thread identity incomplete")
            comment_connection = node.get("comments")
            if not isinstance(comment_connection, Mapping):
                raise RuntimeError("review thread comments incomplete")
            comment_page = comment_connection.get("pageInfo")
            comments = comment_connection.get("nodes")
            if (
                not isinstance(comment_page, Mapping)
                or comment_page.get("hasNextPage") is not False
                or not isinstance(comments, list)
            ):
                raise RuntimeError("review thread comment pagination incomplete")
            threads.append(
                {
                    "is_resolved": node.get("isResolved"),
                    "is_outdated": node.get("isOutdated"),
                    "comments": comments,
                }
            )
        if page.get("hasNextPage") is False:
            return threads
        cursor = page.get("endCursor") if isinstance(page.get("endCursor"), str) else None
        if not cursor:
            raise RuntimeError("review thread cursor missing")


def _recovery_normative_blobs(
    repository: str,
    token: str,
    revision: str,
    *,
    read: GitHubReader,
) -> dict[str, str]:
    commit = read(repository, token, f"git/commits/{revision}")
    tree = commit.get("tree") if isinstance(commit, Mapping) else None
    tree_sha = tree.get("sha") if isinstance(tree, Mapping) else None
    if not isinstance(tree_sha, str) or _SHA.fullmatch(tree_sha) is None:
        raise RuntimeError("normative commit tree identity unavailable")
    listing = read(repository, token, f"git/trees/{tree_sha}?recursive=1")
    if (
        not isinstance(listing, Mapping)
        or listing.get("truncated") is not False
        or not isinstance(listing.get("tree"), list)
    ):
        raise RuntimeError("normative tree enumeration incomplete")
    blobs: dict[str, str] = {}
    for item in cast(list[object], listing["tree"]):
        if not isinstance(item, Mapping):
            raise RuntimeError("normative tree entry malformed")
        path = item.get("path")
        sha = item.get("sha")
        if not isinstance(path, str) or not isinstance(sha, str):
            raise RuntimeError("normative tree entry unavailable")
        if item.get("type") == "blob" and path.startswith(_RECOVERY_NORMATIVE_PREFIXES):
            if path in blobs or _SHA.fullmatch(sha) is None:
                raise RuntimeError("normative tree identity ambiguous")
            blobs[path] = sha
    return blobs


def read_recovery_openspec_review(
    repository: str,
    token: str,
    *,
    head_sha: str,
    approval_label_present: bool,
    issue_comments: tuple[Mapping[str, object], ...],
    read: GitHubReader | None = None,
    log_read: Callable[[str, str, int], str] = _github_job_log,
    thread_read: Callable[[str, str, int], list[dict[str, object]]] = _github_review_threads,
) -> RecoveryReviewAdoption:
    """Existing bridge's fresh source-reader for the bounded #322 review gate."""

    unknown = RecoveryReviewAdoption("UNKNOWN", "recovery-review-source-unavailable")
    source_read = _github_json if read is None else read
    try:
        reviews = _paged_list(repository, token, "pulls/340/reviews", read=source_read)
        selected = _latest_recovery_review(
            reviews,
            repository=repository,
            issue_number=322,
            change="restore-no-work-idle-discovery",
            pr_number=340,
        )
        if isinstance(selected, RecoveryReviewAdoption):
            return selected
        _, receipt = selected
        revision = receipt["Revision"]
        run_id = int(receipt["Validator-Run"])
        commit = source_read(repository, token, f"commits/{revision}")
        human = source_read(repository, token, "issues/comments/6313995887")
        events = _paged_list(repository, token, "issues/322/timeline", read=source_read)
        validator = source_read(repository, token, f"actions/runs/{run_id}")
        jobs = source_read(repository, token, f"actions/runs/{run_id}/jobs?per_page=100")
        if (
            not isinstance(jobs, Mapping)
            or not isinstance(jobs.get("jobs"), list)
            or jobs.get("total_count") != len(jobs["jobs"])
        ):
            return unknown
        validate_jobs = [
            item
            for item in jobs["jobs"]
            if isinstance(item, Mapping) and item.get("name") == "validate"
        ]
        if len(validate_jobs) != 1:
            return unknown
        job = validate_jobs[0]
        job_id = _positive_int(job.get("id"))
        if job_id is None:
            return unknown
        log = log_read(repository, token, job_id)
        comparison = (
            {"status": "identical"}
            if revision == head_sha
            else source_read(repository, token, f"compare/{revision}...{head_sha}")
        )
        baseline_comparison = source_read(
            repository, token, f"compare/{receipt['Baseline']}...{revision}"
        )
        reviewed_blobs = _recovery_normative_blobs(repository, token, revision, read=source_read)
        current_blobs = (
            reviewed_blobs
            if revision == head_sha
            else _recovery_normative_blobs(repository, token, head_sha, read=source_read)
        )
        threads = thread_read(repository, token, 340)
    except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return unknown
    return qualify_recovery_openspec_review(
        repository=repository,
        issue_number=322,
        change="restore-no-work-idle-discovery",
        pr_number=340,
        head_sha=head_sha,
        approval_label_present=approval_label_present,
        reviews=reviews,
        commit=commit,
        original_human_comment=human,
        issue_comments=issue_comments,
        events=events,
        validator=validator,
        validator_job=job,
        validator_log=log,
        comparison=comparison,
        baseline_comparison=baseline_comparison,
        reviewed_blobs=reviewed_blobs,
        current_blobs=current_blobs,
        threads=threads,
    )


_ORIGINAL_322_REQUEST = 6019133874
_ORIGINAL_322_DECISION_DIGEST = "9c545558249285ec6d4fa632970dfa7157774d75bf2b6e46889e240a175cbd54"
_EXCEPTION_322_REQUEST = 6568245475
_EXCEPTION_322_DECISION_DIGEST = "2422cfdd6724d29db124b3e9770912c0d1ad3a3a1a6493f2f07ddd9c87f4fb50"
_EXCEPTION_322_HEAD = "ddd6b3f5a19b879e427aee313334aeab6a43a241"
_EXCEPTION_322_BRANCH = "agent/restore-no-work-idle-discovery-continuation-398"


def qualify_original_322_pre_formal(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    record: ApplicationDecisionRecord,
    issue_comments: tuple[Mapping[str, object], ...],
    current_issue: Mapping[str, object],
    current_revision: str,
    read: GitHubReader,
    expected_request_id: int = _ORIGINAL_322_REQUEST,
    expected_decision_digest: str = _ORIGINAL_322_DECISION_DIGEST,
    expected_pr_number: int = 340,
    expected_pr_branch: str = "agent/report-materialization-postcondition-failure",
) -> RecoveryPreFormalQualification:
    """Qualify one formal-result-only correction from current GitHub facts.

    This is a read-only source gate, not a write authorization by itself.
    GitHubEffectAdapter still owns fresh CAS, deduplication and postconditions
    for each eventual effect. Historical checkpoint/materialization uncertainty
    and prior semantic-review-to-correction comparisons do not enter the
    predicate set of a *new*, formal-result-only operation. They remain
    historical facts; the current implementation review remains a separate
    successor Action and is not preemptively marked PASS here.
    """

    predicates: dict[str, RecoveryPredicate] = dict.fromkeys(("I", "R", "M", "S", "F"), "UNKNOWN")
    if (
        repository != "royhsu-work/investment-strategy"
        or source != WorkerRequest(322, "executor", "implement-change")
        or record.request_comment_id != expected_request_id
        or record.issue_number != 322
        or record.change != "restore-no-work-idle-discovery"
        or record.disposition != "ACCEPTED"
        or record.result_kind != "ready"
    ):
        predicates["I"] = "CONFLICT"
        return _recovery_predicate_result(predicates)
    matched = [
        item
        for item in issue_comments
        if is_github_actions_comment(item)
        and parse_application_decision(item.get("body")) == record
    ]
    # Past completed Action occurrences are history, not competing owners.
    # Only a new accepted write *after* this original acceptance would be a
    # competing unresolved application at its current frontier.
    original_time = _comment_time(matched[0]) if len(matched) == 1 else None
    other_accepted = [
        item
        for item in issue_comments
        if (decision := parse_application_decision(item.get("body"))) is not None
        and decision.disposition == "ACCEPTED"
        and decision.issue_number == 322
        and decision.request_comment_id != expected_request_id
        and original_time is not None
        and ((later_time := _comment_time(item)) is None or later_time >= original_time)
    ]
    if (
        len(matched) != 1
        or other_accepted
        or (
            _accepted_decision_sha256(record, issue_comments) != expected_decision_digest
            or _application_worker_for_record(record, source) is None
        )
    ):
        predicates["I"] = "CONFLICT"
    else:
        predicates["I"] = "COMPLETE"

    observation = normalize_github_issue(current_issue)
    labels = current_issue.get("labels")
    approval_present = isinstance(labels, list) and any(
        isinstance(item, Mapping) and item.get("name") == "human:approved" for item in labels
    )
    if observation is None or not observation.authoritative:
        predicates["R"] = "UNKNOWN"
    elif (
        observation.issue_number != 322
        or observation.change != record.change
        or observation.state != "open"
        or not approval_present
        or observation.routing
        not in {("executor", "implement-change"), ("reviewer", "review-implementation")}
    ):
        predicates["R"] = "CONFLICT"
    else:
        try:
            worker = _application_worker_for_record(record, source)
            successor = (
                None
                if worker is None
                else next_action(worker.typed_result.action, worker.typed_result.result)
            )
            predicates["R"] = (
                "COMPLETE" if successor == ModelAction.REVIEW_IMPLEMENTATION else "CONFLICT"
            )
        except (TypeError, ValueError):
            predicates["R"] = "CONFLICT"

    pr = read(repository, token, f"pulls/{expected_pr_number}")
    head_sha: str | None = None
    if not isinstance(pr, Mapping):
        predicates["M"] = "UNKNOWN"
    else:
        head = pr.get("head")
        base = pr.get("base")
        head_repo = head.get("repo") if isinstance(head, Mapping) else None
        base_repo = base.get("repo") if isinstance(base, Mapping) else None
        head_sha = head.get("sha") if isinstance(head, Mapping) else None
        head_ref = head.get("ref") if isinstance(head, Mapping) else None
        open_carrier = pr.get("state") == "open" and pr.get("merged") is not True
        merged_carrier = pr.get("state") == "closed" and pr.get("merged") is True
        if (
            pr.get("number") != expected_pr_number
            or not (open_carrier or merged_carrier)
            or pr.get("draft") is not False
            or not isinstance(head_sha, str)
            or _SHA.fullmatch(head_sha) is None
            or head_ref != expected_pr_branch
            or not isinstance(head_repo, Mapping)
            or head_repo.get("full_name") != repository
            or not isinstance(base_repo, Mapping)
            or base_repo.get("full_name") != repository
            or (base.get("ref") if isinstance(base, Mapping) else None) != "main"
        ):
            predicates["M"] = "CONFLICT"
        else:
            carrier_qualified = False
            if open_carrier:
                live_ref = read(repository, token, f"git/ref/heads/{head_ref}")
                ref_object = live_ref.get("object") if isinstance(live_ref, Mapping) else None
                if not isinstance(ref_object, Mapping):
                    predicates["M"] = "UNKNOWN"
                elif ref_object.get("sha") != head_sha:
                    predicates["M"] = "CONFLICT"
                else:
                    carrier_qualified = True
            else:
                merge_sha = pr.get("merge_commit_sha")
                merged_at = pr.get("merged_at")
                if (
                    not isinstance(merge_sha, str)
                    or _SHA.fullmatch(merge_sha) is None
                    or not isinstance(merged_at, str)
                    or not merged_at.strip()
                ):
                    predicates["M"] = "UNKNOWN"
                else:
                    merged_commit = read(repository, token, f"git/commits/{merge_sha}")
                    lineage = read(repository, token, f"compare/{merge_sha}...{current_revision}")
                    parents = (
                        merged_commit.get("parents") if isinstance(merged_commit, Mapping) else None
                    )
                    comparison_base = (
                        lineage.get("base_commit") if isinstance(lineage, Mapping) else None
                    )
                    if (
                        not isinstance(merged_commit, Mapping)
                        or not isinstance(parents, list)
                        or not isinstance(lineage, Mapping)
                    ):
                        predicates["M"] = "UNKNOWN"
                    elif (
                        merged_commit.get("sha") != merge_sha
                        or len(parents) != 2
                        or not all(isinstance(parent, Mapping) for parent in parents)
                        or not isinstance(parents[0].get("sha"), str)
                        or _SHA.fullmatch(parents[0]["sha"]) is None
                        or parents[0]["sha"] == head_sha
                        or parents[1].get("sha") != head_sha
                        or lineage.get("status") not in {"identical", "ahead"}
                        or lineage.get("behind_by") != 0
                        or not isinstance(comparison_base, Mapping)
                        or comparison_base.get("sha") != merge_sha
                    ):
                        predicates["M"] = "CONFLICT"
                    else:
                        carrier_qualified = True
            task_path = f"openspec/changes/{record.change}/tasks.md"
            task_content = (
                read(repository, token, f"contents/{task_path}?ref={head_sha}")
                if carrier_qualified
                else None
            )
            if (
                not isinstance(task_content, Mapping)
                or task_content.get("encoding") != "base64"
                or not isinstance(task_content.get("content"), str)
                or not isinstance(task_content.get("sha"), str)
                or _SHA.fullmatch(task_content["sha"]) is None
            ):
                if predicates["M"] != "CONFLICT":
                    predicates["M"] = "UNKNOWN"
            else:
                try:
                    tasks = base64.b64decode(
                        task_content["content"].encode("ascii"), validate=False
                    ).decode("utf-8")
                except (UnicodeError, binascii.Error, ValueError):
                    predicates["M"] = "UNKNOWN"
                else:
                    predicates["M"] = _recovery_task_disposition(tasks)
                    if predicates["M"] == "COMPLETE":
                        # Current PR-head content is relevant to READY. The
                        # historical reviewed-R -> H diff is not: this new
                        # operation writes only a formal result and routing.
                        head_commit = read(repository, token, f"git/commits/{head_sha}")
                        head_tree = (
                            head_commit.get("tree") if isinstance(head_commit, Mapping) else None
                        )
                        tree_sha = head_tree.get("sha") if isinstance(head_tree, Mapping) else None
                        if not isinstance(tree_sha, str) or _SHA.fullmatch(tree_sha) is None:
                            predicates["M"] = "UNKNOWN"
                        else:
                            listing = read(repository, token, f"git/trees/{tree_sha}?recursive=1")
                            if (
                                not isinstance(listing, Mapping)
                                or listing.get("truncated") is not False
                                or not isinstance(listing.get("tree"), list)
                            ):
                                predicates["M"] = "UNKNOWN"
                            else:
                                blobs: dict[str, str] = {}
                                for item in listing["tree"]:
                                    if not isinstance(item, Mapping):
                                        predicates["M"] = "UNKNOWN"
                                        break
                                    path, sha = item.get("path"), item.get("sha")
                                    if item.get("type") == "blob" and isinstance(path, str):
                                        if (
                                            path in blobs
                                            or not isinstance(sha, str)
                                            or _SHA.fullmatch(sha) is None
                                        ):
                                            predicates["M"] = "CONFLICT"
                                            break
                                        blobs[path] = sha
                                if predicates["M"] == "COMPLETE":
                                    if blobs.get(task_path) != task_content["sha"]:
                                        predicates["M"] = "CONFLICT"
                                    elif not _RECOVERY_NECESSARY_EXECUTABLE_FILES.issubset(blobs):
                                        predicates["M"] = "INCOMPLETE"

    # The original two-effect envelope is never replayed by this entry. Its
    # unobserved historical checkpoint does not classify a proposed new
    # *formal-result-only* write. A competing accepted owner remains unsafe.
    predicates["S"] = "CONFLICT" if other_accepted else "COMPLETE"

    formal = [
        item
        for item in issue_comments
        if is_github_actions_comment(item)
        and isinstance(item.get("body"), str)
        and cast(str, item["body"]).splitlines()[:1] == ["ACTION_RESULT"]
        and ((f"application:{expected_request_id}:322:") in cast(str, item["body"]))
    ]
    # Zero is the lawful pre-write state. A previously persisted record must
    # be qualified through the ordinary _formal_consequence owner, not
    # blindly counted as a successful recovery write.
    if len(formal) > 1:
        predicates["F"] = "CONFLICT"
    elif not formal:
        predicates["F"] = "COMPLETE"
    else:
        event = parse_formal_result(formal[0], current_revision=current_revision)
        predicates["F"] = (
            "COMPLETE"
            if event is not None
            and event.valid
            and event.issue_number == 322
            and event.role == "executor"
            and event.action == "implement-change"
            and event.change == record.change
            and event.result_kind == "ready"
            and isinstance(event.application_correlation, str)
            and event.application_correlation.startswith(
                f"application:{expected_request_id}:322:{record.change}:"
                "executor:implement-change:ready:"
            )
            else "CONFLICT"
        )
    if (
        observation is not None
        and observation.routing == ("reviewer", "review-implementation")
        and (len(formal) != 1 or predicates["F"] != "COMPLETE")
    ):
        predicates["R"] = "CONFLICT"
    return _recovery_predicate_result(predicates)


def apply_original_322_recovery_exit(
    repository: str,
    token: str,
    *,
    current_revision: str,
    read: GitHubReader | None = None,
    effect_apply: Callable[..., tuple[object, ApplyResult]] = run_guarded_effect_application,
    request_id: int = _ORIGINAL_322_REQUEST,
    decision_digest: str = _ORIGINAL_322_DECISION_DIGEST,
    carrier_pr: int = 340,
    carrier_branch: str = "agent/report-materialization-postcondition-failure",
    prequalified_accepted_head: str | None = None,
) -> ApplicationCompletion:
    """One existing application-owned correction, never a second semantic Action.

    The only new effects are the canonical formal projection and the
    Action-model-derived successor. The obsolete six-file materialization and
    checkpoint are retained as historical UNKNOWN and are never replayed.
    """

    source_read = _github_json if read is None else read
    source = WorkerRequest(322, "executor", "implement-change")
    try:
        first = _paged_list(
            repository, token, "issues/322/comments?sort=created&direction=asc", read=source_read
        )
        second = _paged_list(
            repository, token, "issues/322/comments?sort=created&direction=asc", read=source_read
        )
        if first != second:
            raise RuntimeError("recovery comment enumeration changed")
        issue = source_read(repository, token, "issues/322")
        if not isinstance(issue, Mapping):
            raise RuntimeError("recovery current Issue unavailable")
        decisions = [
            record
            for item in second
            if is_github_actions_comment(item)
            and (record := parse_application_decision(item.get("body"))) is not None
            and record.request_comment_id == request_id
            and record.disposition == "ACCEPTED"
        ]
        if len(decisions) != 1:
            raise RuntimeError("original accepted application identity is not unique")
        record = decisions[0]
        if (
            _authorization_ancestry(
                repository,
                token,
                authorization_revision=record.authorization_revision,
                current_revision=current_revision,
                read=source_read,
            )
            is None
        ):
            raise RuntimeError("original authorization ancestry unavailable")
        evidence = qualify_original_322_pre_formal(
            repository=repository,
            token=token,
            source=source,
            record=record,
            issue_comments=second,
            current_issue=issue,
            current_revision=current_revision,
            read=source_read,
            expected_request_id=request_id,
            expected_decision_digest=decision_digest,
            expected_pr_number=carrier_pr,
            expected_pr_branch=carrier_branch,
        )
    except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return ApplicationCompletion(
            "INVALID", "recovery-exit-authoritative-source-unavailable", request_id
        )
    if evidence.disposition != "COMPLETE":
        return ApplicationCompletion(
            "INVALID",
            f"recovery-exit-{evidence.disposition.lower()}-"
            + ",".join(evidence.blocking_predicates),
            request_id,
        )
    current_observation = normalize_github_issue(issue)
    if current_observation is None:
        return ApplicationCompletion("INVALID", "recovery-exit-frontier-unknown")
    if current_observation.routing == ("reviewer", "review-implementation"):
        # Only the already-proven formal result and successor may be observed;
        # this path performs zero writes after an ambiguous/lost response.
        return ApplicationCompletion(
            "COMPLETE", "recovery-exit-existing-formal-successor", request_id
        )
    if current_observation.routing != ("executor", "implement-change"):
        return ApplicationCompletion("INVALID", "recovery-exit-frontier-conflict")

    already_formal = any(
        isinstance(item.get("body"), str)
        and cast(str, item["body"]).splitlines()[:1] == ["ACTION_RESULT"]
        and f"application:{request_id}:322:" in cast(str, item["body"])
        for item in second
    )
    prior_formal_correlation = None
    if already_formal:
        events = [
            event
            for item in second
            if (event := parse_formal_result(item, current_revision=current_revision)) is not None
            and event.valid
            and isinstance(event.application_correlation, str)
            and event.application_correlation.startswith(
                f"application:{request_id}:322:{record.change}:executor:implement-change:ready:"
            )
        ]
        if len(events) != 1:
            return ApplicationCompletion("INVALID", "recovery-exit-formal-correlation-conflict")
        prior_formal_correlation = events[0].application_correlation

    # The review gate for the maintenance repair is distinct from the
    # immutable implementation materialization of the accepted request.
    # Its PR HEAD must never become the READY work-product revision.
    try:
        materializations = _materialization_effects(
            record.raw_worker_result, source, change=record.change
        )
        if len(materializations) != 1:
            raise RuntimeError("accepted implementation materialization is not unique")
        materialization = find_materialization_payload(materializations[0], source)
        if (
            materialization is None
            or materialization.change != record.change
            or materialization.pr_number is None
        ):
            raise RuntimeError("accepted implementation PR is incomplete")
        if prequalified_accepted_head is not None:
            # #322's immutable accepted commit is proven by the caller's
            # seven-file Git witness. A later unrelated main advance is NOT
            # a reason to rewrite PR #408 before emitting READY: freshness
            # reconciliation belongs to the subsequent review/merge Action.
            if (
                request_id != _EXCEPTION_322_REQUEST
                or carrier_pr != 408
                or carrier_branch != _EXCEPTION_322_BRANCH
                or prequalified_accepted_head != _EXCEPTION_322_HEAD
                or materialization.pr_number != 408
                or materialization.branch != _EXCEPTION_322_BRANCH
            ):
                raise RuntimeError("accepted exception identity mismatch")
            pr = source_read(repository, token, "pulls/408")
            head = pr.get("head") if isinstance(pr, Mapping) else None
            ref = source_read(repository, token, f"git/ref/heads/{_EXCEPTION_322_BRANCH}")
            ref_obj = ref.get("object") if isinstance(ref, Mapping) else None
            if (
                not isinstance(pr, Mapping)
                or pr.get("state") != "open"
                or pr.get("merged") is True
                or not isinstance(head, Mapping)
                or head.get("sha") != _EXCEPTION_322_HEAD
                or not isinstance(ref_obj, Mapping)
                or ref_obj.get("sha") != _EXCEPTION_322_HEAD
            ):
                raise RuntimeError("accepted exception carrier changed")
            head_sha = _EXCEPTION_322_HEAD
        else:
            carrier = qualify_implementation_carrier(
                repository=repository,
                token=token,
                source=source,
                change=record.change,
                pr_number=materialization.pr_number,
                current_revision=current_revision,
                read=source_read,
            )
            if carrier.disposition not in {"QUALIFIED", "HISTORICAL_MERGED"} or not isinstance(
                carrier.head_sha, str
            ):
                raise RuntimeError("accepted implementation PR is not qualified")
            head_sha = carrier.head_sha
    except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return ApplicationCompletion("INVALID", "recovery-exit-accepted-implementation-unavailable")
    try:
        worker = _application_worker_for_record(record, source)
        decoded = json.loads(record.raw_worker_result)
        if worker is None or not isinstance(decoded, dict):
            raise RuntimeError("original accepted worker unavailable")
        # Strip only obsolete physical effects from the application-owned
        # projection; the immutable accepted result and decision remain intact.
        decoded["requested_effects"] = []
        bounded_raw = json.dumps(decoded, sort_keys=True, separators=(",", ":"))
        application_raw = _application_owned_worker_result(
            bounded_raw,
            source=source,
            change=record.change,
            current_revision=current_revision,
            result_revision=head_sha,
            request_comment_id=record.request_comment_id,
        )
        if already_formal:
            # Formal POST may have succeeded before the route PATCH failed or
            # its response was lost. Reuse the already-qualified record and
            # ask the existing effect owner to apply *only* derived routing.
            # Never construct another comment with a new observation SHA.
            projected_formal = json.loads(application_raw)
            if not isinstance(projected_formal, dict):
                raise RuntimeError("formal-only recovery payload malformed")
            projected_formal["requested_effects"] = []
            application_raw = json.dumps(projected_formal, sort_keys=True, separators=(",", ":"))
        projected = parse_worker_result(application_raw, source, authorized_change=record.change)
        if (
            projected.typed_result.result.kind.value != "ready"
            or len(projected.requested_effects) != (0 if already_formal else 1)
            or (not already_formal and projected.requested_effects[0].kind != "issue-comment")
        ):
            raise RuntimeError("recovery correction projected non-formal effects")
        _, result = effect_apply(
            application_raw,
            source=source,
            repository=repository,
            token=token,
            current_revision=current_revision,
            request_comment_id=record.request_comment_id,
            authorization_revision=record.authorization_revision,
            authorized_change=record.change,
            accepted_intent=True,
            original_322_recovery=True,
            pending_application_correlation=prior_formal_correlation,
        )
    except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        # The GitHub effect adapter's idempotent read-before-write semantics
        # are still required on the next fresh recovery invocation.
        return ApplicationCompletion("INVALID", "recovery-exit-effect-unverified")
    if not result.applied:
        return ApplicationCompletion("INVALID", "recovery-exit-effect-not-applied")
    try:
        final_issue = source_read(repository, token, "issues/322")
        final_comments = _paged_list(
            repository, token, "issues/322/comments?sort=created&direction=asc", read=source_read
        )
        if not isinstance(final_issue, Mapping):
            raise RuntimeError("recovery exit Issue postcondition unavailable")
        post = qualify_original_322_pre_formal(
            repository=repository,
            token=token,
            source=source,
            record=record,
            issue_comments=final_comments,
            current_issue=final_issue,
            current_revision=current_revision,
            read=source_read,
            expected_request_id=request_id,
            expected_decision_digest=decision_digest,
            expected_pr_number=carrier_pr,
            expected_pr_branch=carrier_branch,
        )
    except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return ApplicationCompletion("INVALID", "recovery-exit-postcondition-unavailable")
    if post.disposition != "COMPLETE":
        return ApplicationCompletion("INVALID", "recovery-exit-postcondition-unqualified")
    observation = normalize_github_issue(final_issue)
    if observation is None or observation.routing != ("reviewer", "review-implementation"):
        return ApplicationCompletion("INVALID", "recovery-exit-successor-not-observed")
    return ApplicationCompletion("COMPLETE", "recovery-exit-formal-successor-observed")


def apply_one_time_322_exception(
    repository: str,
    token: str,
    *,
    current_revision: str,
    read: GitHubReader | None = None,
    write: Callable[..., object] | None = None,
    effect_apply: Callable[..., tuple[object, ApplyResult]] = run_guarded_effect_application,
) -> ApplicationCompletion:
    """Repair the exact Human-handoff interval, then reuse the shipped owner.

    The only permitted mutations are a fresh, bounded label correction and
    the original Application's real formal result plus derived successor.
    The accepted PR, materialization and task checkpoint are read-only.
    """

    source_read = _github_json if read is None else read
    source_write = _application_github_json if write is None else write

    def fail(reason: str) -> ApplicationCompletion:
        return ApplicationCompletion("INVALID", f"exception-322-{reason}", _EXCEPTION_322_REQUEST)

    source = WorkerRequest(322, "executor", "implement-change")
    try:
        comments = _paged_list(
            repository, token, "issues/322/comments?sort=created&direction=asc", read=source_read
        )
        if comments != _paged_list(
            repository, token, "issues/322/comments?sort=created&direction=asc", read=source_read
        ):
            return fail("comment-snapshot-changed")
        issue = source_read(repository, token, "issues/322")
        observation = normalize_github_issue(issue) if isinstance(issue, Mapping) else None
        labels = issue.get("labels") if isinstance(issue, Mapping) else None
        names = (
            [item.get("name") for item in labels if isinstance(item, Mapping)]
            if isinstance(labels, list)
            else []
        )
        if (
            repository != "royhsu-work/investment-strategy"
            or observation is None
            or not observation.authoritative
            or observation.issue_number != 322
            or observation.change != "restore-no-work-idle-discovery"
            or observation.state != "open"
            or observation.routing
            not in {
                ("lead", "resolve-question"),
                ("executor", "implement-change"),
                ("reviewer", "review-implementation"),
            }
            or "human:approved" not in names
        ):
            return fail("source-not-qualified")
        accepted = [
            (index, record)
            for index, item in enumerate(comments)
            if is_github_actions_comment(item)
            and (record := parse_application_decision(item.get("body"))) is not None
            and record.disposition == "ACCEPTED"
            and record.issue_number == 322
        ]
        exact = [
            (index, record)
            for index, record in accepted
            if record.request_comment_id == _EXCEPTION_322_REQUEST
        ]
        if len(exact) != 1 or any(index > exact[0][0] for index, _ in accepted):
            return fail("accepted-owner-not-unique")
        record = exact[0][1]
        if (
            _accepted_decision_sha256(record, comments) != _EXCEPTION_322_DECISION_DIGEST
            or _application_worker_for_record(record, source) is None
            or _authorization_ancestry(
                repository,
                token,
                authorization_revision=record.authorization_revision,
                current_revision=current_revision,
                read=source_read,
            )
            is None
        ):
            return fail("accepted-intent-unqualified")
        handoff = [item for item in comments if item.get("id") == 6569195457]
        if (
            len(handoff) != 1
            or not isinstance(handoff[0].get("user"), Mapping)
            or cast(Mapping[str, object], handoff[0]["user"]).get("login") != "royhsu-work"
            or not isinstance(handoff[0].get("body"), str)
            or "一次性 Lead 接管紀錄" not in cast(str, handoff[0]["body"])
        ):
            return fail("human-handoff-unqualified")
        predecessor = [item for item in comments if item.get("id") == 6567424875]
        predecessor_event = (
            parse_formal_result(predecessor[0], current_revision=current_revision)
            if len(predecessor) == 1 and is_github_actions_comment(predecessor[0])
            else None
        )
        if (
            predecessor_event is None
            or not predecessor_event.valid
            or (predecessor_event.role, predecessor_event.action, predecessor_event.result_kind)
            != ("reviewer", "review-implementation", "findings")
            or predecessor_event.successor != ("executor", "implement-change")
            or any(
                item.get("id") != 6567424875
                and isinstance(item.get("id"), int)
                and cast(int, item["id"]) > 6567424875
                and is_github_actions_comment(item)
                and (event := parse_formal_result(item, current_revision=current_revision))
                is not None
                and event.valid
                and not (
                    event.application_correlation is not None
                    and event.application_correlation.startswith(
                        f"application:{_EXCEPTION_322_REQUEST}:322:{record.change}:executor:implement-change:ready:"
                    )
                )
                for item in comments
            )
        ):
            return fail("formal-predecessor-conflict")
        effects = _materialization_effects(record.raw_worker_result, source, change=record.change)
        materialization = (
            find_materialization_payload(effects[0], source) if len(effects) == 1 else None
        )
        if (
            materialization is None
            or materialization.pr_number != 408
            or materialization.branch != _EXCEPTION_322_BRANCH
            or len(materialization.files) != 7
        ):
            return fail("accepted-manifest-unqualified")
        pr = source_read(repository, token, "pulls/408")
        head = pr.get("head") if isinstance(pr, Mapping) else None
        base = pr.get("base") if isinstance(pr, Mapping) else None
        ref = source_read(repository, token, f"git/ref/heads/{_EXCEPTION_322_BRANCH}")
        obj = ref.get("object") if isinstance(ref, Mapping) else None
        if (
            not isinstance(pr, Mapping)
            or pr.get("number") != 408
            or pr.get("state") != "open"
            or pr.get("draft") is not False
            or pr.get("merged") is True
            or not isinstance(head, Mapping)
            or head.get("sha") != _EXCEPTION_322_HEAD
            or head.get("ref") != _EXCEPTION_322_BRANCH
            or not isinstance(head.get("repo"), Mapping)
            or head["repo"].get("full_name") != repository
            or not isinstance(base, Mapping)
            or base.get("ref") != "main"
            or not isinstance(obj, Mapping)
            or obj.get("sha") != _EXCEPTION_322_HEAD
            or _proof_witness(
                materialization,
                repository=repository,
                token=token,
                revision=_EXCEPTION_322_HEAD,
                current_revision=current_revision,
            )
            != _EXCEPTION_322_HEAD
        ):
            return fail("accepted-git-witness-unqualified")
        if observation.routing == ("lead", "resolve-question"):
            if source_read(repository, token, "issues/322") != issue:
                return fail("source-changed-before-label")
            corrected = [
                name for name in names if isinstance(name, str) and not name.startswith("action:")
            ]
            source_write(
                repository,
                token,
                "issues/322",
                method="PATCH",
                payload={"labels": [*corrected, "action:implement-change"]},
            )
    except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return fail("authoritative-proof-unavailable")

    result = apply_original_322_recovery_exit(
        repository,
        token,
        current_revision=current_revision,
        read=source_read,
        effect_apply=effect_apply,
        request_id=_EXCEPTION_322_REQUEST,
        decision_digest=_EXCEPTION_322_DECISION_DIGEST,
        carrier_pr=408,
        carrier_branch=_EXCEPTION_322_BRANCH,
        prequalified_accepted_head=_EXCEPTION_322_HEAD,
    )
    if result.state != "COMPLETE":
        return result
    try:
        final_issue = source_read(repository, token, "issues/322")
        final_comments = _paged_list(
            repository, token, "issues/322/comments?sort=created&direction=asc", read=source_read
        )
        timeline = _paged_list(repository, token, "issues/322/timeline", read=source_read)
        frontier, qualified = _derive_frontier(
            repository=repository,
            token=token,
            source=WorkerRequest(322, "reviewer", "review-implementation"),
            current_issue=cast(Mapping[str, object], final_issue),
            issue_comments=final_comments,
            lifecycle_events=timeline,
            current_revision=current_revision,
            read=source_read,
        )
    except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return fail("frontier-proof-unavailable")
    if (
        not qualified
        or frontier is None
        or not isinstance(frontier.event, FormalLifecycleEvent)
        or not isinstance(frontier.event.application_correlation, str)
        or not frontier.event.application_correlation.startswith(
            f"application:{_EXCEPTION_322_REQUEST}:322:restore-no-work-idle-discovery:executor:implement-change:ready:"
        )
    ):
        return fail("reviewer-frontier-not-qualified")
    return ApplicationCompletion(
        "COMPLETE", "exception-322-formal-reviewer-qualified", _EXCEPTION_322_REQUEST
    )


PreacceptClassification = Literal[
    "ACCEPTED",
    "LIVE_PREACCEPT",
    "TERMINAL_NO_ACCEPT",
    "NEEDS_REPAIR",
    "REJECTED",
    "INVALID",
    "UNKNOWN",
]


@dataclass(frozen=True)
class _IngressCandidate:
    request_comment_id: int
    body: str | None
    created_at: str | None
    authorization_revision: str | None
    request: ApplicationRequest | None


GitHubReader = Callable[[str, str, str], object | None]


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _positive_int_string(value: str) -> int | None:
    if not value.isdigit() or value.startswith("0"):
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _valid_reason(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and "\n" not in value
        and len(value) <= _MAX_REASON_LENGTH
    )


def parse_dispatch_request(body: str) -> DispatchRequest | None:
    from investment_strategy.scheduled_agent_wire import DISPATCH_REQUEST_WIRE

    fields = DISPATCH_REQUEST_WIRE.parse(body)
    return None if fields is None else DispatchRequest(requested_at=fields["Requested-At"])


def render_dispatch_request(request: DispatchRequest) -> str:
    """Emit the two-field dispatch wire accepted by its production parser."""

    from investment_strategy.scheduled_agent_wire import DISPATCH_REQUEST_WIRE

    body = DISPATCH_REQUEST_WIRE.render({"Requested-At": request.requested_at})
    if parse_dispatch_request(body) != request:
        raise ValueError("dispatch request renderer/parser contract mismatch")
    return body


def render_dispatch_run_name(request_comment_id: int) -> str:
    if request_comment_id <= 0:
        raise ValueError("request_comment_id must be positive")
    return f"{RUN_NAME_PREFIX}{request_comment_id}"


def parse_dispatch_run_name(run_name: str) -> int | None:
    if not run_name.startswith(RUN_NAME_PREFIX):
        return None
    raw = run_name[len(RUN_NAME_PREFIX) :]
    try:
        parsed = int(raw)
    except ValueError:
        return None
    return parsed if parsed > 0 and str(parsed) == raw else None


def render_application_run_name(request_comment_id: int) -> str:
    if request_comment_id <= 0:
        raise ValueError("request_comment_id must be positive")
    return f"{APPLICATION_RUN_NAME_PREFIX}{request_comment_id}"


def parse_application_run_name(run_name: str) -> int | None:
    if not run_name.startswith(APPLICATION_RUN_NAME_PREFIX):
        return None
    raw = run_name[len(APPLICATION_RUN_NAME_PREFIX) :]
    try:
        parsed = int(raw)
    except ValueError:
        return None
    return parsed if parsed > 0 and str(parsed) == raw else None


def _github_json(repository: str, token: str, api_path: str) -> object | None:
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        github_repository_api_url(repository, api_path),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    raw = github_read_bytes_with_retry(
        request,
        open_request=urlopen,  # noqa: S310 - trusted GitHub API host
        wait=time.sleep,
    )
    return None if not raw else json.loads(raw.decode("utf-8"))


def _paged_list(
    repository: str,
    token: str,
    api_path: str,
    *,
    read: GitHubReader,
) -> tuple[Mapping[str, object], ...]:
    return github_paginated_mappings(
        repository,
        token,
        api_path,
        read=read,
        incomplete_error="application completion evidence list is incomplete",
        malformed_error="application completion evidence list is malformed",
    )


def _runtime_shard_comments(
    repository: str,
    token: str,
    *,
    runtime_shard_issue_number: int,
    source_issue_number: int,
    source_issue_comments: tuple[Mapping[str, object], ...],
    read: GitHubReader,
) -> tuple[Mapping[str, object], ...]:
    """Read complete dispatch evidence from the current runtime shard."""

    if _positive_int(runtime_shard_issue_number) is None:
        raise ValueError("runtime shard issue number is invalid")
    if runtime_shard_issue_number == source_issue_number:
        return source_issue_comments
    return _paged_list(
        repository,
        token,
        f"issues/{runtime_shard_issue_number}/comments?sort=created&direction=asc",
        read=read,
    )


def _comment_time(comment: Mapping[str, object]) -> str | None:
    value = comment.get("created_at")
    return value if isinstance(value, str) and value else None


def _trusted_connector_comment(comment: Mapping[str, object], owner: str) -> bool:
    return github_comment_has_app_provenance(
        comment, actor=owner, app_slug=_CHATGPT_CONNECTOR_APP_SLUG
    )


def _completion_source(
    preflight: DispatchPreflight,
    decision: DispatchDecision,
) -> WorkerRequest | None:
    if (
        decision.disposition == "AUTHORIZE"
        and decision.selected_issue_id is not None
        and decision.selected_routing is not None
    ):
        role, action = decision.selected_routing
        return WorkerRequest(decision.selected_issue_id, role, action)
    candidate = pending_continuation_candidate(preflight)
    if candidate is None or candidate.routing is None:
        return None
    role, action = candidate.routing
    return WorkerRequest(candidate.issue_number, role, action)


def _formal_result_records(
    comments: tuple[Mapping[str, object], ...],
) -> tuple[tuple[str, str], ...]:
    records: list[tuple[str, str]] = []
    for comment in comments:
        if not is_github_actions_comment(comment):
            continue
        body = comment.get("body")
        created_at = _comment_time(comment)
        if not isinstance(body, str) or created_at is None:
            continue
        marker = body.splitlines()[:1]
        if not marker or marker[0].removeprefix("## ").strip() not in _FORMAL_RESULT_MARKERS:
            continue
        records.append((created_at, body))
    return tuple(records)


def _carrier_change_matches_accepted_intent(
    record: ApplicationDecisionRecord, plan: CarrierPlan
) -> bool:
    """Bind a first Change carrier to the immutable materialization, not source `unset`."""

    if record.change != "unset":
        return plan.change == record.change
    if (
        record.role != "lead"
        or record.action != "propose-change"
        or plan.operation != "pull-request-create"
    ):
        return False

    source = WorkerRequest(record.issue_number, record.role, record.action)
    try:
        effects = _materialization_effects(record.raw_worker_result, source, change=record.change)
        if len(effects) != 1:
            return False
        materialization = find_materialization_payload(effects[0], source)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        materialization is not None
        and materialization.expected_change == record.change
        and materialization.change == plan.change
        and plan.target.get("head_ref") == materialization.branch
        and plan.expected.get("head_ref") == materialization.branch
        and plan.requested.get("head") == materialization.branch
        and plan.expected_postcondition.get("head_ref") == materialization.branch
    )


def _single_run_artifact(payload: object, *, name: str) -> Mapping[str, object] | None:
    """Qualify a complete run inventory and at most one named Artifact."""

    inventory = github_run_artifact_inventory(payload)
    if inventory is None:
        raise ValueError("incomplete")
    matches = [item for item in inventory if item.get("name") == name]
    if len(matches) > 1:
        raise LookupError("multiple matching run artifacts")
    return matches[0] if matches else None


def _qualified_carrier_for_application_run(
    repository: str,
    token: str,
    request_comment_id: int,
    *,
    run: Mapping[str, object],
    run_id: int,
    run_attempt: int,
    job: QualifiedApplicationJob,
    record: ApplicationDecisionRecord,
    read: GitHubReader,
) -> QualifiedCarrierPlan | None:
    """Recover one current-attempt carrier Artifact without replaying its producer."""

    artifacts_payload = read(repository, token, f"actions/runs/{run_id}/artifacts?per_page=100")
    try:
        artifact = _single_run_artifact(artifacts_payload, name="carrier-plan.json")
    except LookupError as exc:
        raise RuntimeError("application carrier artifact identity is ambiguous") from exc
    except ValueError as exc:
        raise RuntimeError("application carrier artifact listing is incomplete") from exc
    if artifact is None:
        return None

    steps = job.steps
    if steps is None:
        raise RuntimeError("application carrier job steps are incomplete")
    upload_steps = [
        conclusion for name, conclusion in steps if name == "Upload exact external carrier plan"
    ]
    if len(upload_steps) != 1:
        raise RuntimeError("application carrier upload step identity is ambiguous")
    upload_conclusion = upload_steps[0]
    if upload_conclusion == "skipped" and run_attempt > 1:
        return None
    if upload_conclusion != "success":
        raise RuntimeError("application carrier Artifact is not current-attempt evidence")

    identity = github_run_artifact_identity(
        artifact, run_id=run_id, run_head_sha=run.get("head_sha")
    )
    if identity is None:
        raise RuntimeError("application carrier Artifact identity is invalid")
    artifact_id, digest = identity

    raw = read_github_artifact_bytes(repository, token, f"actions/artifacts/{artifact_id}/zip")
    if f"sha256:{hashlib.sha256(raw).hexdigest()}" != digest:
        raise RuntimeError("application carrier Artifact digest is invalid")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("application carrier Artifact content is invalid") from exc
    try:
        plan = parse_carrier_plan_document(document)
    except ValueError as exc:
        raise RuntimeError("application carrier plan is invalid") from exc
    if (
        plan.repository != repository
        or plan.issue_number != record.issue_number
        or not _carrier_change_matches_accepted_intent(record, plan)
        or plan.action != record.action
        or _authorization_ancestry(
            repository,
            token,
            authorization_revision=record.authorization_revision,
            current_revision=plan.authorization_revision,
            read=read,
        )
        is None
    ):
        raise RuntimeError("application carrier plan does not match accepted intent")
    return QualifiedCarrierPlan(
        request_comment_id=request_comment_id,
        run_id=run_id,
        run_attempt=run_attempt,
        artifact_id=artifact_id,
        artifact_digest=digest,
        plan=plan,
    )


def _carrier_outcome_field(body: str, field: str) -> str | None:
    prefix = f"{field}: "
    for line in body.split("\n")[1:]:
        if line.startswith(prefix):
            return line[len(prefix) :]
    return None


def _carrier_precondition_shape_matches(expected: object, observed: object) -> bool:
    """Require the observation to carry exactly the plan's precondition fields."""

    if isinstance(expected, Mapping):
        if not isinstance(observed, Mapping) or set(expected) != set(observed):
            return False
        return all(
            _carrier_precondition_shape_matches(expected[key], observed[key]) for key in expected
        )
    if isinstance(expected, list):
        return (
            isinstance(observed, list)
            and len(expected) == len(observed)
            and all(
                _carrier_precondition_shape_matches(left, right)
                for left, right in zip(expected, observed, strict=True)
            )
        )
    return type(expected) is type(observed)


def _carrier_outcome_status(
    *,
    recent_comments: tuple[Mapping[str, object], ...],
    owner: str,
    repository: str,
    source: WorkerRequest,
    record: ApplicationDecisionRecord,
    accepted_decision_sha256: str,
    recovery_artifact: ApplicationRecoveryArtifact,
    qualified_carrier: QualifiedCarrierPlan,
) -> tuple[Literal["NONE", "COMPLETE", "BLOCKED"], str | None]:
    """Bind trusted carrier reports to the exact accepted and artifact lineage."""

    if (
        qualified_carrier.run_id != recovery_artifact.run_id
        or qualified_carrier.run_attempt != recovery_artifact.run_attempt
        or recovery_artifact.request_comment_id != record.request_comment_id
        or recovery_artifact.accepted_decision_sha256 != accepted_decision_sha256
    ):
        return "BLOCKED", "application-completion-carrier-outcome-invalid"
    try:
        expected_correlation = application_continuation_correlation(
            repository,
            source.issue_number,
            record.request_comment_id,
            accepted_decision_sha256,
            recovery_artifact.run_id,
            recovery_artifact.run_attempt,
            recovery_artifact.job_id,
            recovery_artifact.artifact_id,
            recovery_artifact.artifact_digest,
            recovery_artifact.failure_evidence_sha256,
            recovery_artifact.recovery_episode_sha256,
        )
    except ValueError:
        return "BLOCKED", "application-completion-carrier-outcome-invalid"

    expected_lineage_fields = {
        "Repository": repository,
        "Issue": str(source.issue_number),
        "Request-Comment": str(record.request_comment_id),
        "Accepted-Decision-SHA256": accepted_decision_sha256,
        "Continuation-Correlation": expected_correlation,
        "Predecessor-Run-ID": str(recovery_artifact.run_id),
        "Predecessor-Run-Attempt": str(recovery_artifact.run_attempt),
        "Predecessor-Job-ID": str(recovery_artifact.job_id),
        "Recovery-Artifact-ID": str(recovery_artifact.artifact_id),
        "Recovery-Artifact-Digest": recovery_artifact.artifact_digest,
        "Failure-Evidence-SHA256": recovery_artifact.failure_evidence_sha256,
        "Recovery-Episode-SHA256": recovery_artifact.recovery_episode_sha256,
        "Carrier-Artifact-ID": str(qualified_carrier.artifact_id),
        "Carrier-Artifact-Digest": qualified_carrier.artifact_digest,
    }
    matching: list[CarrierOutcomeReport] = []
    for comment in recent_comments:
        if not _trusted_connector_comment(comment, owner):
            continue
        body = comment.get("body")
        if not isinstance(body, str) or body.split("\n", 1)[0] != "APPLICATION_CARRIER_OUTCOME":
            continue
        report = parse_carrier_outcome_report(body)
        raw_lineage_matches = all(
            _carrier_outcome_field(body, field) == expected
            for field, expected in expected_lineage_fields.items()
        )
        if report is None:
            if raw_lineage_matches:
                return "BLOCKED", "application-completion-carrier-outcome-invalid"
            continue
        exact_lineage = (
            report.repository == repository
            and report.issue_number == source.issue_number
            and report.request_comment_id == record.request_comment_id
            and report.accepted_decision_sha256 == accepted_decision_sha256
            and report.continuation_correlation == expected_correlation
            and report.predecessor_run_id == recovery_artifact.run_id
            and report.predecessor_run_attempt == recovery_artifact.run_attempt
            and report.predecessor_job_id == recovery_artifact.job_id
            and report.recovery_artifact_id == recovery_artifact.artifact_id
            and report.recovery_artifact_digest == recovery_artifact.artifact_digest
            and report.failure_evidence_sha256 == recovery_artifact.failure_evidence_sha256
            and report.recovery_episode_sha256 == recovery_artifact.recovery_episode_sha256
            and report.carrier_artifact_id == qualified_carrier.artifact_id
            and report.carrier_artifact_digest == qualified_carrier.artifact_digest
        )
        if not exact_lineage:
            continue
        if (
            report.plan_id != qualified_carrier.plan.plan_id
            or report.operation != qualified_carrier.plan.operation
        ):
            return "BLOCKED", "application-completion-carrier-outcome-plan-reused"
        expected_precondition_json = json.dumps(
            dict(qualified_carrier.plan.expected), sort_keys=True, separators=(",", ":")
        )
        observed_precondition = (
            None
            if report.observed_precondition_json is None
            else json.loads(report.observed_precondition_json)
        )
        observation_matches_status = (
            (
                report.precondition == "MATCH"
                and report.observed_precondition_json == expected_precondition_json
                and _carrier_precondition_shape_matches(
                    dict(qualified_carrier.plan.expected), observed_precondition
                )
            )
            or (
                report.precondition == "MISMATCH"
                and report.observed_precondition_json != expected_precondition_json
                and _carrier_precondition_shape_matches(
                    dict(qualified_carrier.plan.expected), observed_precondition
                )
            )
            or (
                report.precondition in {"UNKNOWN", "NOT_REQUIRED"}
                and report.observed_precondition_json is None
            )
        )
        if not observation_matches_status:
            return "BLOCKED", "application-completion-carrier-outcome-invalid"
        matching.append(report)
    if not matching:
        return "NONE", None
    if len(matching) != 1:
        return "BLOCKED", "application-completion-carrier-outcome-ambiguous"
    report = matching[0]
    if report.outcome != "COMPLETE" or report.postcondition != "COMPLETE":
        return "BLOCKED", "application-completion-carrier-outcome-incomplete"
    return "COMPLETE", None


def _dispatch_runs_for_request(
    repository: str,
    token: str,
    request_comment_id: int,
    *,
    read: GitHubReader,
) -> tuple[Mapping[str, object], ...] | None:
    """Read all bridge runs for one earlier transport comment."""

    runs = _complete_workflow_runs(repository, token, _DISPATCH_WORKFLOW, read=read)
    if runs is None:
        return None
    title = render_dispatch_run_name(request_comment_id)
    return tuple(run for run in runs if run.get("display_title") == title)


def _complete_workflow_runs(
    repository: str,
    token: str,
    workflow: str,
    *,
    read: GitHubReader,
    event: str = "issue_comment",
    head_sha: str | None = None,
    require_count: bool = False,
) -> tuple[Mapping[str, object], ...] | None:
    """Read one complete workflow-run history with a single counted-page proof.

    Exact-head searches require counted pages and confirmed event and head
    metadata. At the search cap, use the unfiltered history (which is not
    capped) and reapply the filters. Preserve the legacy issue-comment reader
    contract when no exact head is requested.
    """

    path = f"actions/workflows/{quote(workflow, safe='')}/runs"

    def page(number: int, *, filtered: bool) -> Mapping[str, object] | None:
        params: dict[str, str | int] = {"per_page": 100, "page": number}
        if filtered:
            params = {"event": event, **params}
            if head_sha is not None:
                params["head_sha"] = head_sha
        payload = read(repository, token, f"{path}?{urlencode(params)}")
        if not isinstance(payload, Mapping) or not isinstance(payload.get("workflow_runs"), list):
            return None
        return payload

    first = page(1, filtered=True)
    if first is None:
        return None
    total_count = first.get("total_count")
    if total_count is not None and (type(total_count) is not int or total_count < 0):
        return None

    if type(total_count) is int:
        reported_count = total_count
        filtered = total_count < 1000 or (
            head_sha is None and not require_count and total_count == 1000
        )
        if not filtered:
            unfiltered_first = page(1, filtered=False)
            if unfiltered_first is None:
                return None
            unfiltered_count = unfiltered_first.get("total_count")
            if type(unfiltered_count) is not int or unfiltered_count < total_count:
                return None
            first = unfiltered_first
            total_count = unfiltered_count

        # Both counted modes use the same complete-page, stable-count and
        # unique-run-ID qualification. The event proof differs only when the
        # GitHub search cap forces an unfiltered history.
        pages = max(1, (total_count + 99) // 100)
        with ThreadPoolExecutor(max_workers=min(8, pages)) as pool:
            remaining = tuple(pool.map(lambda n: page(n, filtered=filtered), range(2, pages + 1)))
        runs: list[Mapping[str, object]] = []
        for index, payload in enumerate((first, *remaining)):
            if payload is None or payload.get("total_count") != total_count:
                return None
            rows = payload.get("workflow_runs")
            if not isinstance(rows, list) or len(rows) != min(100, total_count - index * 100):
                return None
            for run in rows:
                if (
                    not isinstance(run, Mapping)
                    or type(run.get("id")) is not int
                    or (not filtered and not isinstance(run.get("event"), str))
                ):
                    return None
                if head_sha is not None:
                    revision = run.get("head_sha")
                    if (
                        not isinstance(revision, str)
                        or _SHA.fullmatch(revision) is None
                        or (filtered and (revision != head_sha or run.get("event") != event))
                    ):
                        return None
                runs.append(cast(Mapping[str, object], run))
        ids = [cast(int, run["id"]) for run in runs]
        if len(ids) != len(set(ids)):
            return None
        if filtered:
            return tuple(runs)
        matching = tuple(
            run
            for run in runs
            if run.get("event") == event and (head_sha is None or run.get("head_sha") == head_sha)
        )
        if head_sha is not None and (
            len(matching) < reported_count
            or (reported_count > 1000 and len(matching) != reported_count)
        ):
            return None
        return matching

    if head_sha is not None or require_count:
        return None
    # Historical injected readers without total_count retain a bounded
    # short-page terminator; do not trust a filtered 1,000-result cap.
    legacy_runs: list[Mapping[str, object]] = []
    current = first
    number = 1
    while True:
        raw_runs = current["workflow_runs"]
        if not isinstance(raw_runs, list) or current.get("total_count") is not None:
            return None
        if any(not isinstance(run, Mapping) for run in raw_runs):
            return None
        legacy_runs.extend(cast(list[Mapping[str, object]], raw_runs))
        if len(raw_runs) < 100:
            return tuple(legacy_runs)
        if len(legacy_runs) >= 1000:
            return None
        number += 1
        next_page = page(number, filtered=True)
        if next_page is None:
            return None
        current = next_page


def read_native_quality_runs(
    repository: str,
    token: str,
    revision: str,
    *,
    read: GitHubReader = _github_json,
) -> tuple[Mapping[str, object], ...] | None:
    """Read push/PR candidates for one exact head before qualifying their jobs."""
    if _SHA.fullmatch(revision) is None:
        return None

    eligible: list[Mapping[str, object]] = []
    seen: set[int] = set()
    for event in ("push", "pull_request"):
        try:
            runs = _complete_workflow_runs(
                repository, token, _QUALITY_WORKFLOW, read=read, event=event, head_sha=revision
            )
        except (OSError, RuntimeError, ValueError):
            return None
        if runs is None:
            return None
        for run in runs:
            run_id = _positive_int(run.get("id"))
            run_repo = run.get("repository")
            head_repo = run.get("head_repository")
            origin = head_repo.get("full_name") if isinstance(head_repo, Mapping) else None
            if (
                run_id is None
                or run_id in seen
                or _positive_int(run.get("run_attempt")) is None
                or run.get("path") != f".github/workflows/{_QUALITY_WORKFLOW}"
                or not isinstance(run_repo, Mapping)
                or run_repo.get("full_name") != repository
                or not isinstance(origin, str)
                or not origin
            ):
                return None
            seen.add(run_id)
            if origin == repository:
                eligible.append(run)
    return tuple(eligible)


def read_native_quality_history(
    repository: str,
    token: str,
    revision: str,
    *,
    branch: str,
    workflow_blob: str,
    read: GitHubReader = _github_json,
    log_read: Callable[[str, str, int], str] = _github_job_log,
) -> tuple[NativeQualityAttempt, ...] | None:
    """Reconstruct all ordinary quality attempts for one qualified gate.

    Reruns cannot erase historical verdicts. Compare two complete inventories
    around the exact attempt reads; an intervening run or rerun requires fresh
    observation. An empty ordinary history alone does not authorize a call,
    since the existing bridge-call history must also be qualified.
    """
    if (
        not branch
        or branch != branch.strip()
        or _SHA.fullmatch(revision) is None
        or _SHA.fullmatch(workflow_blob) is None
    ):
        return None

    def snapshot() -> tuple[tuple[int, int, str, str, str | None], ...] | None:
        runs = read_native_quality_runs(repository, token, revision, read=read)
        if runs is None:
            return None
        rows: list[tuple[int, int, str, str, str | None]] = []
        for run in runs:
            observed_branch = run.get("head_branch")
            if not isinstance(observed_branch, str) or not observed_branch:
                return None
            if observed_branch != branch:
                continue
            run_id = _positive_int(run.get("id"))
            latest = _positive_int(run.get("run_attempt"))
            event = run.get("event")
            status, conclusion = run.get("status"), run.get("conclusion")
            if (
                run_id is None
                or latest is None
                or not isinstance(event, str)
                or event not in ("push", "pull_request")
                or not isinstance(status, str)
                or (conclusion is not None and not isinstance(conclusion, str))
            ):
                return None
            rows.append((run_id, latest, event, status, conclusion))
        return tuple(sorted(rows, key=lambda row: row[0]))

    def qualify(
        row: tuple[int, int, str, str, str | None], number: int
    ) -> NativeQualityAttempt | None:
        run_id, latest, event, status, conclusion = row
        endpoint = f"actions/runs/{run_id}/attempts/{number}"
        try:
            observed = read(repository, token, endpoint)
        except (OSError, RuntimeError, TypeError, ValueError):
            observed = None
        if (
            number == latest
            and isinstance(observed, Mapping)
            and (observed.get("status"), observed.get("conclusion")) != (status, conclusion)
        ):
            return None

        def exact_read(repo: str, credential: str, path: str) -> object:
            # Bind the classifier to the same exact source used for comparison,
            # not a second potentially different read of that attempt.
            if path == endpoint:
                return observed
            return read(repo, credential, path)

        attempt = read_native_quality_attempt(
            repository,
            token,
            revision=revision,
            branch=branch,
            workflow_blob=workflow_blob,
            run_id=run_id,
            run_attempt=number,
            event=event,
            read=exact_read,
            log_read=log_read,
        )
        if number < latest and attempt.outcome == "PENDING":
            return None
        return attempt

    first = snapshot()
    if first is None:
        return None
    attempts: list[NativeQualityAttempt] = []
    for row in first:
        for number in range(1, row[1] + 1):
            attempt = qualify(row, number)
            if attempt is None:
                return None
            attempts.append(attempt)
    return tuple(attempts) if snapshot() == first else None


_QualityOutcome = Literal["PASS", "FAIL", "CONFLICT", "NO_VERDICT", "PENDING", "INDETERMINATE"]


@dataclass(frozen=True)
class NativeQualityObservation:
    """Invocation-local verification evidence; never semantic dispatch authority."""

    outcome: _QualityOutcome
    attempts: tuple[NativeQualityAttempt, ...] | None = None
    call: dict[str, str] | None = None


def _quality_call_fields(
    repository: str,
    revision: str,
    definition: str,
    obligation: str,
    source_id: int,
    run_id: int,
    attempt: int,
) -> dict[str, str]:
    correlation = hashlib.sha256(
        f"{obligation}:{definition}:{source_id}:{run_id}:{attempt}".encode()
    ).hexdigest()
    return {
        "quality_obligation": obligation,
        "quality_target_repository": repository,
        "quality_target_revision": revision,
        "quality_definition_revision": definition,
        "quality_verification_correlation": correlation,
        "quality_source_comment_id": str(source_id),
        "quality_run_id": str(run_id),
        "quality_run_attempt": str(attempt),
        "quality_call": "true",
        "quality_result": "verification-obligation-pending",
    }


def _quality_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _quality_workflow_blob(
    repository: str, token: str, revision: str, *, read: GitHubReader
) -> str | None:
    path = f".github/workflows/{_QUALITY_WORKFLOW}"
    file = read(repository, token, f"contents/{path}?{urlencode({'ref': revision})}")
    if not isinstance(file, Mapping) or file.get("type") != "file" or file.get("path") != path:
        return None
    sha = file.get("sha")
    return sha if isinstance(sha, str) and _SHA.fullmatch(sha) is not None else None


def _quality_dispatch_requests(
    repository: str, token: str, accepted_at: str, *, read: GitHubReader
) -> dict[int, str] | None:
    boundary = _quality_time(accepted_at)
    if boundary is None:
        return None
    query = urlencode({"sort": "created", "direction": "asc", "since": accepted_at})
    rows = _paged_list(repository, token, f"issues/comments?{query}", read=read)
    requests: dict[int, str] = {}
    for comment in rows:
        body = comment.get("body")
        if (
            not isinstance(body, str)
            or body.splitlines()[:1] != [REQUEST_MARKER]
            or not _trusted_connector_comment(comment, repository.split("/", 1)[0])
        ):
            continue
        stamp = _quality_time(comment.get("created_at"))
        if stamp is None or stamp == boundary:
            return None
        if stamp < boundary:
            continue
        source_id = _positive_int(comment.get("id"))
        issue_url = comment.get("issue_url")
        prefix = github_repository_api_url(repository, "issues/")
        if (
            source_id is None
            or source_id in requests
            or not isinstance(issue_url, str)
            or not issue_url.startswith(prefix)
            or comment.get("updated_at") != comment.get("created_at")
            or parse_dispatch_request(body) is None
        ):
            return None
        issue_id = _positive_int_string(issue_url.removeprefix(prefix))
        if issue_id is None:
            return None
        observed = read(repository, token, f"issues/comments/{source_id}")
        if (
            not isinstance(observed, Mapping)
            or not _trusted_connector_comment(observed, repository.split("/", 1)[0])
            or any(
                observed.get(key) != comment.get(key)
                for key in ("id", "body", "issue_url", "created_at", "updated_at")
            )
        ):
            return None
        issue = read(repository, token, f"issues/{issue_id}")
        if (
            not isinstance(issue, Mapping)
            or issue.get("number") != issue_id
            or not is_runtime_checkin_issue(issue)
        ):
            return None
        requests[source_id] = cast(str, comment["created_at"])
    return requests


def _quality_bridge_run(
    run: Mapping[str, object], repository: str, default_branch: str, source: int
) -> tuple[int, int, str, str, str | None] | None:
    run_id, attempt = _positive_int(run.get("id")), _positive_int(run.get("run_attempt"))
    repo, head = run.get("repository"), run.get("head_repository")
    definition, status, conclusion = run.get("head_sha"), run.get("status"), run.get("conclusion")
    if (
        run_id is None
        or attempt is None
        or not isinstance(repo, Mapping)
        or repo.get("full_name") != repository
        or not isinstance(head, Mapping)
        or head.get("full_name") != repository
        or run.get("event") != "issue_comment"
        or run.get("path") != f".github/workflows/{_DISPATCH_WORKFLOW}"
        or run.get("head_branch") != default_branch
        or run.get("display_title") != render_dispatch_run_name(source)
        or not isinstance(definition, str)
        or _SHA.fullmatch(definition) is None
        or not isinstance(status, str)
        or (conclusion is not None and not isinstance(conclusion, str))
    ):
        return None
    return run_id, attempt, definition, status, conclusion


_QUALITY_ACTIVE = ("queued", "in_progress", "requested", "waiting", "pending")
_QUALITY_NO_VERDICT = (
    "cancelled",
    "skipped",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
    "neutral",
)


def _quality_bridge_attempt(
    repository: str,
    token: str,
    *,
    source: int,
    row: tuple[int, int, str, str, str | None],
    obligation_id: str | None,
    revision: str | None,
    workflow_blob: str,
    read: GitHubReader,
    log_read: Callable[[str, str, int], str],
    audit_result_sha256: str | None = None,
) -> NativeQualityAttempt:
    run_id, attempt, definition, status, conclusion = row
    unknown = NativeQualityAttempt(run_id, attempt, "INDETERMINATE")
    absent = NativeQualityAttempt(run_id, attempt, "NO_VERDICT")
    if obligation_id is None:
        if (
            revision is not None
            or audit_result_sha256 is None
            or re.fullmatch(r"[0-9a-f]{64}", audit_result_sha256) is None
        ):
            return unknown
    elif revision is None or audit_result_sha256 is not None:
        return unknown
    if status in _QUALITY_ACTIVE:
        return NativeQualityAttempt(run_id, attempt, "PENDING") if conclusion is None else unknown
    if status != "completed" or conclusion not in ("success", "failure", *_QUALITY_NO_VERDICT):
        return unknown
    jobs = github_complete_job_inventory(
        repository, token, run_id=run_id, run_attempt=attempt, read=read
    )
    if jobs is None:
        return unknown
    by_name: dict[str, Mapping[str, object]] = {}
    for job in jobs:
        name = job.get("name")
        if (
            not isinstance(name, str)
            or name not in ("bridge", "verify_quality / quality", "verify_quality")
            or name in by_name
            or job.get("run_id") != run_id
            or job.get("run_attempt") != attempt
            or job.get("head_sha") != definition
            or job.get("status") != "completed"
            or _positive_int(job.get("id")) is None
        ):
            return unknown
        by_name[name] = job
    planner = by_name.pop("bridge", None)
    if len(by_name) > 1:
        return unknown
    quality = next(iter(by_name.values()), None)
    not_called = quality is None or quality.get("conclusion") == "skipped"
    if planner is None or planner.get("conclusion") != "success":
        # An unsuccessful/missing planner cannot authorize a dependent job.
        return absent if not_called and conclusion != "success" else unknown
    planner_steps = planner.get("steps")
    if not isinstance(planner_steps, list):
        return unknown
    required = (
        "Check out authoritative default branch",
        "Record exact checked-out default-branch revision",
        "Plan exact correlated machine dispatch decision",
        "Upload exact run-scoped machine dispatch result",
    )
    observed = [
        step for step in planner_steps if isinstance(step, Mapping) and step.get("name") in required
    ]
    if tuple(step.get("name") for step in observed) != required or any(
        step.get("status") != "completed" or step.get("conclusion") != "success"
        for step in observed
    ):
        return unknown
    lines = [
        re.sub(r"^\d{4}-\d\d-\d\dT\S+Z ", "", raw)
        for raw in log_read(repository, token, cast(int, planner["id"])).splitlines()
    ]
    if audit_result_sha256 is not None:
        result_prefix = "native_quality_result_sha256="
        result_receipts = [
            line.removeprefix(result_prefix) for line in lines if line.startswith(result_prefix)
        ]
        if result_receipts != [audit_result_sha256]:
            return unknown
    prefix = "native_quality_plan="
    receipts = [line.removeprefix(prefix) for line in lines if line.startswith(prefix)]
    if len(receipts) != 1:
        return unknown
    if receipts[0] == "none":
        return absent if not_called and conclusion in ("success", *_QUALITY_NO_VERDICT) else unknown
    plan = json.loads(receipts[0])
    if not isinstance(plan, dict):
        return unknown
    gate, target = plan.get("quality_obligation"), plan.get("quality_target_revision")
    if (
        not isinstance(gate, str)
        or re.fullmatch(r"[0-9a-f]{64}", gate) is None
        or not isinstance(target, str)
        or _SHA.fullmatch(target) is None
        or plan
        != _quality_call_fields(repository, target, definition, gate, source, run_id, attempt)
        or (gate == obligation_id and target != revision)
    ):
        return unknown
    blob = _quality_workflow_blob(repository, token, definition, read=read)
    if blob is None or ((obligation_id is None or gate == obligation_id) and blob != workflow_blob):
        return unknown
    if quality is None or quality.get("conclusion") == "skipped":
        # A recorded plan may be skipped by the native dependency/identity guard.
        return absent if conclusion in ("success", *_QUALITY_NO_VERDICT) else unknown
    job_conclusion = quality.get("conclusion")
    if job_conclusion in _QUALITY_NO_VERDICT:
        return absent if conclusion == job_conclusion else unknown
    if job_conclusion not in ("success", "failure") or conclusion != job_conclusion:
        return unknown
    if quality.get("name") != "verify_quality / quality":
        return unknown
    failed = native_quality_setup_failure_index(quality)
    if failed is not None and failed < 2:
        return absent
    log = log_read(repository, token, cast(int, quality["id"]))
    if failed is not None:
        if failed > 2 and native_quality_witness_matches(
            log,
            repository=repository,
            revision=target,
            definition_sha=definition,
            run_id=run_id,
            run_attempt=attempt,
            source_comment_id=source,
            verification_correlation=plan["quality_verification_correlation"],
        ):
            return absent
        return unknown
    verdict = qualify_native_quality_job(
        quality,
        log,
        repository=repository,
        revision=target,
        definition_sha=definition,
        run_id=run_id,
        run_attempt=attempt,
        job_id=cast(int, quality["id"]),
        job_name="verify_quality / quality",
        source_comment_id=source,
        verification_correlation=plan["quality_verification_correlation"],
    )
    if verdict is None:
        return unknown
    if obligation_id is None or gate == obligation_id:
        return NativeQualityAttempt(
            run_id,
            attempt,
            verdict,
            job_id=cast(int, quality["id"]),
            checkout_revision=target,
            definition_revision=definition,
            source_comment_id=source,
        )
    return absent


def qualify_failed_native_quality_audit(
    repository: str,
    token: str,
    *,
    run: Mapping[str, object],
    request_comment_id: int,
    current_revision: str,
    artifact_sha256: str,
    read: GitHubReader,
    log_read: Callable[[str, str, int], str],
) -> bool:
    """Read-only failed-caller audit; never establish an accepted work gate."""
    try:
        repo = read(repository, token, "")
        default_branch = repo.get("default_branch") if isinstance(repo, Mapping) else None
        if (
            not isinstance(repo, Mapping)
            or repo.get("full_name") != repository
            or not isinstance(default_branch, str)
            or not default_branch
        ):
            return False

        def main_is_current() -> bool:
            ref = read(repository, token, f"git/ref/heads/{quote(default_branch, safe='/')}")
            obj = ref.get("object") if isinstance(ref, Mapping) else None
            return isinstance(obj, Mapping) and obj.get("sha") == current_revision

        row = _quality_bridge_run(run, repository, default_branch, request_comment_id)
        if row is None or row[2:] != (current_revision, "completed", "failure"):
            return False
        if not main_is_current():
            return False
        run_id, attempt = row[:2]
        source_path = f"issues/comments/{request_comment_id}"
        comment = read(repository, token, source_path)
        if not isinstance(comment, Mapping):
            return False
        body, issue_url = comment.get("body"), comment.get("issue_url")
        prefix = github_repository_api_url(repository, "issues/")
        created = _quality_time(comment.get("created_at"))
        started = _quality_time(run.get("created_at"))
        if (
            _positive_int(comment.get("id")) != request_comment_id
            or not _trusted_connector_comment(comment, repository.split("/", 1)[0])
            or not isinstance(body, str)
            or parse_dispatch_request(body) is None
            or not isinstance(issue_url, str)
            or not issue_url.startswith(prefix)
            or comment.get("updated_at") != comment.get("created_at")
            or created is None
            or started is None
            or started < created
        ):
            return False
        issue_id = _positive_int_string(issue_url.removeprefix(prefix))
        if issue_id is None:
            return False
        issue = read(repository, token, f"issues/{issue_id}")
        if (
            not isinstance(issue, Mapping)
            or issue.get("number") != issue_id
            or not is_runtime_checkin_issue(issue)
        ):
            return False
        raw_attempt = read(repository, token, f"actions/runs/{run_id}/attempts/{attempt}")
        if (
            not isinstance(raw_attempt, Mapping)
            or _quality_bridge_run(raw_attempt, repository, default_branch, request_comment_id)
            != row
        ):
            return False
        blob = _quality_workflow_blob(repository, token, current_revision, read=read)
        if blob is None:
            return False
        evidence = _quality_bridge_attempt(
            repository,
            token,
            source=request_comment_id,
            row=row,
            obligation_id=None,
            revision=None,
            workflow_blob=blob,
            read=read,
            log_read=log_read,
            audit_result_sha256=artifact_sha256,
        )
        latest = read(repository, token, f"actions/runs/{run_id}")
        return (
            evidence.outcome in ("STATIC_STEP_FAILURE", "PYTEST_STEP_FAILURE")
            and isinstance(latest, Mapping)
            and _quality_bridge_run(latest, repository, default_branch, request_comment_id) == row
            and read(repository, token, source_path) == comment
            and main_is_current()
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return False


def _quality_verdicts_precede(
    repository: str,
    token: str,
    *,
    attempts: tuple[NativeQualityAttempt, ...],
    boundary: datetime,
    accepted_at: str,
    read: GitHubReader,
) -> bool:
    """Qualify the actual job event, not a later observation of its verdict."""
    accepted = _quality_time(accepted_at)
    if accepted is None or accepted >= boundary:
        return False
    for attempt in attempts:
        if attempt.outcome not in ("PASS", "STATIC_STEP_FAILURE", "PYTEST_STEP_FAILURE"):
            continue
        if attempt.job_id is None:
            return False
        job = read(repository, token, f"actions/jobs/{attempt.job_id}")
        if not isinstance(job, Mapping):
            return False
        started = _quality_time(job.get("started_at"))
        completed = _quality_time(job.get("completed_at"))
        expected_head = (
            attempt.checkout_revision
            if attempt.source_comment_id is None
            else attempt.definition_revision
        )
        if (
            job.get("id") != attempt.job_id
            or job.get("run_id") != attempt.run_id
            or job.get("run_attempt") != attempt.run_attempt
            or job.get("head_sha") != expected_head
            or job.get("status") != "completed"
            or job.get("conclusion") != ("success" if attempt.outcome == "PASS" else "failure")
            or started is None
            or completed is None
            or not accepted < started <= completed < boundary
        ):
            return False
    return True


def plan_native_quality_verification(
    repository: str,
    token: str,
    *,
    revision: str,
    branch: str,
    workflow_blob: str,
    obligation_id: str,
    accepted_at: str,
    current_revision: str,
    default_branch: str,
    request_comment_id: int,
    run_id: int,
    run_attempt: int,
    read: GitHubReader = _github_json,
    log_read: Callable[[str, str, int], str] = _github_job_log,
    observe_only: bool = False,
    verdict_before: datetime | None = None,
) -> NativeQualityObservation:
    """Observe both native producers before admitting one read-only local call.

    The Application supplies the exact outstanding gate and its immutable
    acceptance boundary. A fresh dispatch is not an execution retry token.
    Observe-only mode requires the exact successful completed dispatcher and
    cannot issue a verification call; its consumer still qualifies authority.
    """
    unknown = NativeQualityObservation("INDETERMINATE")
    if (
        _SHA.fullmatch(revision) is None
        or _SHA.fullmatch(current_revision) is None
        or _SHA.fullmatch(workflow_blob) is None
        or re.fullmatch(r"[0-9a-f]{64}", obligation_id) is None
        or any(_positive_int(n) is None for n in (request_comment_id, run_id, run_attempt))
        or not default_branch
        or not branch
    ):
        return unknown

    def main_is_current() -> bool:
        repo = read(repository, token, "")
        ref = read(repository, token, f"git/ref/heads/{quote(default_branch, safe='/')}")
        obj = ref.get("object") if isinstance(ref, Mapping) else None
        return (
            isinstance(repo, Mapping)
            and repo.get("full_name") == repository
            and repo.get("default_branch") == default_branch
            and isinstance(obj, Mapping)
            and obj.get("sha") == current_revision
        )

    def snapshot() -> dict[int, tuple[int, int, str, str, str | None]] | None:
        boundary = _quality_time(accepted_at)
        requests = _quality_dispatch_requests(repository, token, accepted_at, read=read)
        if boundary is None or requests is None or request_comment_id not in requests:
            return None
        runs = _complete_workflow_runs(
            repository, token, _DISPATCH_WORKFLOW, read=read, require_count=True
        )
        if runs is None:
            return None
        found: dict[int, tuple[int, int, str, str, str | None]] = {}
        for run in runs:
            title = run.get("display_title")
            source = parse_dispatch_run_name(title) if isinstance(title, str) else None
            if source is None:
                continue
            row = _quality_bridge_run(run, repository, default_branch, source)
            created = _quality_time(run.get("created_at"))
            if source not in requests:
                if row is None or created is None:
                    return None
                if created < boundary:
                    continue
                # A run that outlived its source must not disappear from the
                # inventory merely because the current request list omits it.
                comment = read(repository, token, f"issues/comments/{source}")
                if not isinstance(comment, Mapping):
                    return None
                requested = _quality_time(comment.get("created_at"))
                body, issue_url = comment.get("body"), comment.get("issue_url")
                prefix = github_repository_api_url(repository, "issues/")
                if (
                    _positive_int(comment.get("id")) != source
                    or requested is None
                    or requested > created
                    or comment.get("updated_at") != comment.get("created_at")
                    or not isinstance(issue_url, str)
                    or not issue_url.startswith(prefix)
                    or _positive_int_string(issue_url.removeprefix(prefix)) is None
                    or not isinstance(body, str)
                ):
                    return None
                if requested < boundary:
                    continue
                if requested == boundary or body.splitlines()[:1] == [REQUEST_MARKER]:
                    return None
                continue
            requested = _quality_time(requests[source])
            if row is None or source in found or created is None or requested is None:
                return None
            if created < requested:
                return None
            found[source] = row
        return found if set(found) == set(requests) else None

    def ordinary_history(blob: str) -> tuple[NativeQualityAttempt, ...] | None:
        return read_native_quality_history(
            repository,
            token,
            revision,
            branch=branch,
            workflow_blob=blob,
            read=read,
            log_read=log_read,
        )

    try:
        if not main_is_current():
            return unknown
        if _quality_workflow_blob(repository, token, current_revision, read=read) != workflow_blob:
            return unknown
        target_blob = _quality_workflow_blob(repository, token, revision, read=read)
        if target_blob is None:
            return unknown
        ordinary = ordinary_history(target_blob)
        first = snapshot()
        if ordinary is None or first is None:
            return unknown
        own = first[request_comment_id]
        own_state_qualified = (
            own[3:] == ("completed", "success")
            if observe_only
            else own[3] in _QUALITY_ACTIVE and own[4] is None
        )
        if own[:3] != (run_id, run_attempt, current_revision) or not own_state_qualified:
            return unknown
        called: list[NativeQualityAttempt] = []
        for source, latest in first.items():
            observed_run, last, definition, _, _ = latest
            ancestry = _authorization_ancestry(
                repository,
                token,
                authorization_revision=definition,
                current_revision=current_revision,
                read=read,
            )
            if ancestry is None:
                return unknown
            for attempt in range(1, last + 1):
                raw = read(repository, token, f"actions/runs/{observed_run}/attempts/{attempt}")
                if not isinstance(raw, Mapping):
                    return unknown
                row = _quality_bridge_run(raw, repository, default_branch, source)
                if (
                    row is None
                    or row[:3] != (observed_run, attempt, definition)
                    or (attempt == last and row != latest)
                ):
                    return unknown
                if source == request_comment_id and attempt == run_attempt:
                    continue
                result = _quality_bridge_attempt(
                    repository,
                    token,
                    source=source,
                    row=row,
                    obligation_id=obligation_id,
                    revision=revision,
                    workflow_blob=workflow_blob,
                    read=read,
                    log_read=log_read,
                )
                if attempt < last and result.outcome == "PENDING":
                    return unknown
                called.append(result)
        if (
            snapshot() != first
            or ordinary_history(target_blob) != ordinary
            or not main_is_current()
        ):
            return unknown
        if verdict_before is not None and not _quality_verdicts_precede(
            repository,
            token,
            attempts=(*ordinary, *called),
            boundary=verdict_before,
            accepted_at=accepted_at,
            read=read,
        ):
            return unknown
        if target_blob == workflow_blob:
            history = (*ordinary, *called)
            outcome = reduce_native_quality_attempts(history)
        else:
            # A B-owned call cannot establish candidate-producer correctness.
            candidate = reduce_native_quality_attempts(ordinary)
            history = (*ordinary, *called)
            outcome = reduce_native_quality_attempts(tuple(called))
            if candidate in ("FAIL", "CONFLICT", "PENDING", "INDETERMINATE"):
                return NativeQualityObservation(candidate, ordinary)
            if outcome == "PASS" and candidate != "PASS":
                return unknown
        call = (
            _quality_call_fields(
                repository,
                revision,
                current_revision,
                obligation_id,
                request_comment_id,
                run_id,
                run_attempt,
            )
            if outcome == "NO_VERDICT" and not observe_only
            else None
        )
        return NativeQualityObservation(outcome, history, call)
    except (OSError, RuntimeError, TypeError, ValueError):
        return unknown


def qualify_development_dispatch_source(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    request_comment_id: int,
    current_revision: str,
    default_branch: str,
    read: GitHubReader = _github_json,
    expected_source: Mapping[str, object] | None = None,
) -> DevelopmentDispatchSource | None:
    """Qualify the original native dispatch for one physical development ingress.

    Comment IDs are identities, not timestamps. A second ingress cannot reuse
    the same dispatch. The original shard can be closed after its ingress.
    """
    owner = repository.split("/", 1)[0]
    prefix = github_repository_api_url(repository, "issues/")
    if (
        _positive_int(request_comment_id) is None
        or _SHA.fullmatch(current_revision) is None
        or not default_branch
        or (source.role, source.action) != ("executor", "implement-change")
    ):
        return None

    def same_comment(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
        return _trusted_connector_comment(right, owner) and all(
            left.get(key) == right.get(key)
            for key in ("id", "body", "issue_url", "created_at", "updated_at")
        )

    try:
        ingress = read(repository, token, f"issues/comments/{request_comment_id}")
        if (
            not isinstance(ingress, Mapping)
            or ingress.get("id") != request_comment_id
            or not _trusted_connector_comment(ingress, owner)
            or ingress.get("updated_at") != ingress.get("created_at")
        ):
            return None
        body, issue_url = ingress.get("body"), ingress.get("issue_url")
        ingress_at = _quality_time(ingress.get("created_at"))
        if (
            ingress_at is None
            or not isinstance(body, str)
            or body.splitlines()[:1] not in (["WORKER_RESULT"], ["EFFECT_REQUEST"])
            or not isinstance(issue_url, str)
            or not issue_url.startswith(prefix)
        ):
            return None
        shard = _positive_int_string(issue_url.removeprefix(prefix))
        if shard is None:
            return None
        issue = read(repository, token, f"issues/{shard}")
        if (
            not isinstance(issue, Mapping)
            or issue.get("number") != shard
            or not is_runtime_checkin_issue(issue)
        ):
            return None
        comments = _paged_list(
            repository,
            token,
            f"issues/{shard}/comments?sort=created&direction=asc",
            read=read,
        )
        own = [item for item in comments if item.get("id") == request_comment_id]
        if len(own) != 1 or not same_comment(ingress, own[0]):
            return None
        prior: list[tuple[datetime, Mapping[str, object]]] = []
        for item in comments:
            candidate_body = item.get("body")
            if (
                item.get("id") == request_comment_id
                or not _trusted_connector_comment(item, owner)
                or not isinstance(candidate_body, str)
                or candidate_body.splitlines()[:1]
                not in ([REQUEST_MARKER], ["WORKER_RESULT"], ["EFFECT_REQUEST"])
            ):
                continue
            stamp = _quality_time(item.get("created_at"))
            if stamp is None or stamp == ingress_at:
                return None
            if stamp < ingress_at:
                prior.append((stamp, item))
        if not prior:
            return None
        requested_at = max(stamp for stamp, _ in prior)
        latest = [item for stamp, item in prior if stamp == requested_at]
        if len(latest) != 1:
            return None
        dispatch = latest[0]
        dispatch_id = _positive_int(dispatch.get("id"))
        dispatch_body = dispatch.get("body")
        if (
            dispatch_id is None
            or dispatch.get("issue_url") != issue_url
            or dispatch.get("updated_at") != dispatch.get("created_at")
            or not isinstance(dispatch_body, str)
            or parse_dispatch_request(dispatch_body) is None
        ):
            return None
        observed = read(repository, token, f"issues/comments/{dispatch_id}")
        if not isinstance(observed, Mapping) or not same_comment(dispatch, observed):
            return None
        runs = _complete_workflow_runs(
            repository, token, _DISPATCH_WORKFLOW, read=read, require_count=True
        )
        if runs is None:
            return None
        matching = [
            item
            for item in runs
            if item.get("display_title") == render_dispatch_run_name(dispatch_id)
        ]
        if len(matching) != 1:
            return None
        run = matching[0]
        latest_row = _quality_bridge_run(run, repository, default_branch, dispatch_id)
        if latest_row is None or latest_row[2] != current_revision:
            return None
        run_id, latest_attempt = latest_row[:2]
        attempt = latest_attempt
        if expected_source is not None:
            expected_attempt = _positive_int(expected_source.get("run_attempt"))
            if (
                expected_source.get("run_id") != run_id
                or expected_attempt is None
                or expected_attempt > latest_attempt
            ):
                return None
            attempt = expected_attempt
        row = (run_id, attempt, current_revision, "completed", "success")
        attempt_run = read(repository, token, f"actions/runs/{run_id}/attempts/{attempt}")
        if (
            not isinstance(attempt_run, Mapping)
            or _quality_bridge_run(attempt_run, repository, default_branch, dispatch_id) != row
            or (
                attempt == latest_attempt
                and (
                    latest_row != row
                    or any(
                        attempt_run.get(key) != run.get(key) for key in ("created_at", "updated_at")
                    )
                )
            )
        ):
            return None
        created = _quality_time(attempt_run.get("created_at"))
        completed = _quality_time(attempt_run.get("updated_at"))
        if (
            created is None
            or completed is None
            or not requested_at <= created < completed < ingress_at
        ):
            return None
        jobs = github_complete_job_inventory(
            repository, token, run_id=run_id, run_attempt=attempt, read=read
        )
        if jobs is None:
            return None
        planners = [item for item in jobs if item.get("name") == "bridge"]
        if len(planners) != 1:
            return None
        job = planners[0]
        job_id = _positive_int(job.get("id"))
        started = _quality_time(job.get("started_at"))
        finished = _quality_time(job.get("completed_at"))
        if (
            job_id is None
            or job.get("run_id") != run_id
            or job.get("run_attempt") != attempt
            or job.get("head_sha") != current_revision
            or job.get("status") != "completed"
            or job.get("conclusion") != "success"
            or started is None
            or finished is None
            or not created <= started <= finished <= completed
        ):
            return None
        steps = job.get("steps")
        required = (
            "Check out authoritative default branch",
            "Record exact checked-out default-branch revision",
            "Plan exact correlated machine dispatch decision",
            "Upload exact run-scoped machine dispatch result",
        )
        if not isinstance(steps, list):
            return None
        witnessed = [
            step for step in steps if isinstance(step, Mapping) and step.get("name") in required
        ]
        if tuple(step.get("name") for step in witnessed) != required or any(
            step.get("status") != "completed" or step.get("conclusion") != "success"
            for step in witnessed
        ):
            return None
        if expected_source is None:
            artifact = _single_run_artifact(
                read(repository, token, f"actions/runs/{run_id}/artifacts?per_page=100"),
                name="dispatch-result.json",
            )
        else:
            expected_artifact = _positive_int(expected_source.get("artifact_id"))
            if expected_artifact is None:
                return None
            observed_artifact = read(repository, token, f"actions/artifacts/{expected_artifact}")
            artifact = (
                observed_artifact
                if isinstance(observed_artifact, Mapping)
                and observed_artifact.get("name") == "dispatch-result.json"
                else None
            )
        if artifact is None:
            return None
        identity = github_run_artifact_identity(
            artifact, run_id=run_id, run_head_sha=current_revision
        )
        uploaded = _quality_time(artifact.get("created_at"))
        if identity is None or uploaded is None or not started <= uploaded <= finished:
            return None
        artifact_id, digest = identity
        raw = read_github_artifact_bytes(repository, token, f"actions/artifacts/{artifact_id}/zip")
        if "sha256:" + hashlib.sha256(raw).hexdigest() != digest:
            return None
        result = parse_dispatch_result_document(raw)
        if (
            result.request_comment_id != dispatch_id
            or result.default_branch_revision != current_revision
            or result.disposition != "AUTHORIZE"
            or (result.issue_number, result.role, result.action)
            != (source.issue_number, source.role, source.action)
        ):
            return None
        current_run = read(repository, token, f"actions/runs/{run_id}")
        if (
            not isinstance(current_run, Mapping)
            or _quality_bridge_run(current_run, repository, default_branch, dispatch_id)
            != latest_row
            or current_run.get("updated_at") != run.get("updated_at")
        ):
            return None
        qualified = DevelopmentDispatchSource(
            dispatch_id, run_id, attempt, job_id, artifact_id, digest, current_revision
        )
        if expected_source is not None and asdict(qualified) != expected_source:
            return None
        return qualified
    except (OSError, RuntimeError, TypeError, ValueError, LookupError):
        return None


def _prior_dispatch_handoff_reason(
    repository: str,
    token: str,
    *,
    recent_comments: tuple[Mapping[str, object], ...],
    owner: str,
    current_dispatch_request_comment_id: int | None,
    plan_id: str,
    read: GitHubReader,
) -> str | None:
    """Do not repeat any earlier plan handoff without its exact durable outcome."""

    if current_dispatch_request_comment_id is None:
        return None
    prior_ids = []
    for comment in recent_comments:
        comment_id = _positive_int(comment.get("id"))
        body = comment.get("body")
        if (
            comment_id is not None
            and comment_id < current_dispatch_request_comment_id
            and _trusted_connector_comment(comment, owner)
            and isinstance(body, str)
            and body.split("\n", 1)[0] == "DISPATCH_REQUEST"
        ):
            # A malformed transport request is an orphaned historical
            # boundary, not evidence that no earlier plan was handed off.
            # Do not let a later valid or FAIL_CLOSED dispatch mask it.
            if parse_dispatch_request(body) is None:
                return "application-completion-carrier-prior-dispatch-incomplete"
            prior_ids.append(comment_id)
    if not prior_ids:
        return None
    # One read-only history observation for this handoff classification.
    # Never re-fetch the same full workflow history once per prior request;
    # the indexed snapshot is not shared across a later mutation boundary.
    all_runs = _complete_workflow_runs(repository, token, _DISPATCH_WORKFLOW, read=read)
    if all_runs is None:
        return "application-completion-carrier-prior-dispatch-unavailable"
    by_title: dict[str, list[Mapping[str, object]]] = {}
    for run in all_runs:
        title = run.get("display_title")
        if isinstance(title, str):
            by_title.setdefault(title, []).append(run)
    for prior_comment_id in sorted(prior_ids, reverse=True):
        runs = by_title.get(render_dispatch_run_name(prior_comment_id), [])
        if not runs:
            return "application-completion-carrier-prior-dispatch-incomplete"
        if len(runs) != 1:
            return "application-completion-carrier-prior-dispatch-ambiguous"
        run = runs[0]
        run_id = _positive_int(run.get("id"))
        if run_id is None or run.get("status") != "completed":
            return "application-completion-carrier-prior-dispatch-incomplete"
        artifacts_payload = read(
            repository,
            token,
            f"actions/runs/{run_id}/artifacts?per_page=100",
        )
        try:
            artifact = _single_run_artifact(artifacts_payload, name="dispatch-result.json")
        except (ValueError, LookupError):
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        if artifact is None:
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        identity = github_run_artifact_identity(
            artifact, run_id=run_id, run_head_sha=run.get("head_sha")
        )
        if identity is None:
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        artifact_id, digest = identity
        try:
            raw = read_github_artifact_bytes(
                repository,
                token,
                f"actions/artifacts/{artifact_id}/zip",
            )
        except (HTTPError, OSError, RuntimeError, ValueError):
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        if f"sha256:{hashlib.sha256(raw).hexdigest()}" != digest:
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        try:
            prior_result = parse_dispatch_result_document(raw)
        except (RuntimeError, ValueError, json.JSONDecodeError):
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        if prior_result.request_comment_id != prior_comment_id:
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        prior_carrier = prior_result.qualified_carrier
        if prior_carrier is not None and prior_carrier.plan.plan_id == plan_id:
            return "application-completion-carrier-outcome-missing"
    return None


def _qualified_unapplied_terminal_carrier_effect(
    repository: str,
    token: str,
    *,
    record: ApplicationDecisionRecord,
    run: Mapping[str, object],
    job: QualifiedApplicationJob,
    run_id: int,
    run_attempt: int,
    read: GitHubReader,
) -> bool:
    """Reconcile a terminal Application against immutable effects, not errors.

    Carrier-only PR mutations are *never* written by the Application job.  A
    complete, current-attempt artifact inventory and skipped carrier/successor
    steps prove that this invocation handed no writer an executable plan.
    ABORTED additionally needs a *monotonic* negative postcondition: an
    already-created PR cannot disappear and a merged PR cannot reopen. For
    mutable update/ready effects the current mismatch does not prove an
    earlier idempotent success never reached the formal/derived writers;
    these cases remain UNKNOWN. HTTP status, exception content and traceback
    are deliberately irrelevant.
    """

    steps = job.steps
    if (
        record.disposition != "ACCEPTED"
        or record.role != "executor"
        or run_attempt != 1
        or run.get("status") != "completed"
        or run.get("conclusion") not in {"failure", "cancelled", "timed_out"}
        or job.status != "completed"
        or job.conclusion not in {"failure", "cancelled", "timed_out"}
        or steps is None
    ):
        return False
    conclusions: dict[str, str] = {}
    for name, conclusion in steps:
        if name is None or conclusion is None or name in conclusions:
            return False
        conclusions[name] = conclusion
    if (
        conclusions.get("Freshly authorize and apply repository-owned effects")
        not in {"failure", "cancelled", "timed_out"}
        or conclusions.get("Upload exact application recovery evidence") != "skipped"
        or any(
            conclusions.get(name) != "skipped"
            for name in (
                "Persist exact external carrier plan",
                "Upload exact external carrier plan",
                "Persist the derived successor after exact validation",
                "Upload final exact application recovery evidence",
            )
        )
    ):
        return False

    # The failed *first* apply step can itself write ACTION_RESULT and derived
    # routing after an idempotently satisfied PR effect. Re-read *after* the
    # terminal run/job and skipped-writer proof: a comment tuple captured by
    # the outer completion classifier before the writer terminated is stale
    # evidence for absence. Both reads must succeed and be authoritative.
    terminal_comments = _paged_list(
        repository,
        token,
        f"issues/{record.issue_number}/comments?sort=created&direction=asc",
        read=read,
    )
    terminal_issue = read(repository, token, f"issues/{record.issue_number}")
    observation = (
        normalize_github_issue(terminal_issue) if isinstance(terminal_issue, Mapping) else None
    )
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != record.issue_number
        or observation.state != "open"
        or observation.routing != (record.role, record.action)
        or observation.change not in {record.change, "unset"}
    ):
        return False
    correlation_prefix = (
        f"Application-Correlation: application:{record.request_comment_id}:{record.issue_number}:"
    )
    if any(
        not isinstance(comment.get("body"), str) or correlation_prefix in cast(str, comment["body"])
        for comment in terminal_comments
    ):
        return False

    # Terminal writes keep the stricter original dispatch correlation
    # requirement, but use the same immutable-source proof as read-only
    # Application recovery. This is evidence, never Effect permission.
    try:
        original = _qualified_physical_original_accepted_effects(
            record=record,
            source=WorkerRequest(record.issue_number, record.role, record.action),
            repository=repository,
            token=token,
            read=read,
            require_dispatch_correlation=True,
        )
    except (ValueError, TypeError, RuntimeError, json.JSONDecodeError):
        return False
    if original is None or len(original.effects) != 1:
        return False
    effect = original.effects[0]
    if effect.kind != "github-mutation":
        return False
    try:
        payload = json.loads(effect.payload_json)
    except ValueError:
        return False
    if not isinstance(payload, Mapping):
        return False
    operation = payload.get("operation")
    if (
        operation not in {"pull-request-create", "pull-request-merge"}
        or payload.get("issue_number") != record.issue_number
        or (operation == "pull-request-merge" and record.result_kind != "merged")
    ):
        return False

    artifacts = github_run_artifact_inventory(
        read(repository, token, f"actions/runs/{run_id}/artifacts?per_page=100")
    )
    if artifacts is None:
        return False
    if any(_positive_int(artifact.get("id")) is None for artifact in artifacts):
        return False
    if any(
        artifact["name"] in {"carrier-plan.json", "application-recovery-evidence"}
        for artifact in artifacts
    ):
        return False

    # Only immutable creation/merge consequences have a monotonic negative
    # witness. A mutable PR field/draft state can change *after* the first
    # apply step has already persisted a formal result. Neither the missing
    # carrier plan nor a now-different field proves no prior partial write.
    # Nothing is replayed: a new dispatch must requalify the full source.
    if operation == "pull-request-create":
        branch = payload.get("head")
        base_ref = payload.get("base")
        if (
            not isinstance(branch, str)
            or not branch
            or not isinstance(base_ref, str)
            or not base_ref
        ):
            return False
        owner = repository.split("/", 1)[0]
        query = f"pulls?state=all&head={quote(f'{owner}:{branch}', safe='')}&per_page=100"
        candidates = read(repository, token, query)
        # PR base is mutable: a successful creation can later be retargeted.
        # Search every PR on this head, regardless of current base, matching
        # the real PR-create writer's identity boundary. A full first page
        # is not proven complete and never supplies a negative witness.
        return isinstance(candidates, list) and len(candidates) == 0

    number = _positive_int(payload.get("number"))
    expected_head = payload.get("expected_head_sha")
    if (
        number is None
        or not isinstance(expected_head, str)
        or _SHA.fullmatch(expected_head) is None
    ):
        return False
    pr = read(repository, token, f"pulls/{number}")
    if not isinstance(pr, Mapping):
        return False
    head = pr.get("head")
    base = pr.get("base")
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        return False
    head_repo = head.get("repo")
    base_repo = base.get("repo")
    identity_matches = (
        pr.get("number") == number
        and pr.get("state") == "open"
        and pr.get("merged") is False
        and isinstance(head_repo, Mapping)
        and head_repo.get("full_name") == repository
        and isinstance(base_repo, Mapping)
        and base_repo.get("full_name") == repository
        and isinstance(base.get("ref"), str)
    )
    if not identity_matches:
        return False
    # This final observation is monotonic; historical merges cannot hide.
    return identity_matches


def _saved_development_quality_obligation(
    repository: str,
    token: str,
    *,
    record: ApplicationDecisionRecord,
    accepted_decision_sha256: str,
    issue_comments: tuple[Mapping[str, object], ...],
    current_revision: str,
    run: Mapping[str, object],
    job: QualifiedApplicationJob,
    read: GitHubReader,
) -> NativeQualityObligation | None:
    """Use the existing physical Original and canonical materialization witness."""
    source = WorkerRequest(record.issue_number, record.role, record.action)
    if (
        job.status != "completed"
        or job.conclusion not in ("success", "failure", *_QUALITY_NO_VERDICT)
        or run.get("status") != "completed"
        or run.get("conclusion") != job.conclusion
        or run.get("path") != f".github/workflows/{_APPLICATION_WORKFLOW}"
        or run.get("event") != "issue_comment"
        or run.get("head_sha") != record.authorization_revision
    ):
        return None
    repo = read(repository, token, "")
    origin, head = run.get("repository"), run.get("head_repository")
    default_branch = repo.get("default_branch") if isinstance(repo, Mapping) else None
    if (
        not isinstance(repo, Mapping)
        or repo.get("full_name") != repository
        or not isinstance(default_branch, str)
        or not default_branch
        or run.get("head_branch") != default_branch
        or not isinstance(origin, Mapping)
        or origin.get("full_name") != repository
        or not isinstance(head, Mapping)
        or head.get("full_name") != repository
    ):
        return None
    matches = [
        comment
        for comment in issue_comments
        if is_github_actions_comment(comment)
        and isinstance(comment.get("body"), str)
        and parse_application_decision(cast(str, comment["body"])) == record
    ]
    if len(matches) != 1:
        return None
    comment = matches[0]
    accepted_at = comment.get("created_at")
    comment_id = _positive_int(comment.get("id"))
    if (
        not isinstance(accepted_at, str)
        or _quality_time(accepted_at) is None
        or comment.get("updated_at") != accepted_at
        or comment_id is None
        or comment.get("issue_url")
        != github_repository_api_url(repository, f"issues/{record.issue_number}")
    ):
        return None
    observed = read(repository, token, f"issues/comments/{comment_id}")
    if (
        not isinstance(observed, Mapping)
        or not is_github_actions_comment(observed)
        or any(
            observed.get(key) != comment.get(key)
            for key in ("id", "body", "issue_url", "created_at", "updated_at")
        )
        or hashlib.sha256(cast(str, comment["body"]).encode()).hexdigest()
        != accepted_decision_sha256
    ):
        return None
    original = _qualified_physical_original_accepted_effects(
        record=record, source=source, repository=repository, token=token, read=read
    )
    if original is None or not _implementation_development_save(original):
        return None
    payload = json.loads(original.effects[0].payload_json)
    proof = prove_materialization(
        payload,
        source,
        repository=repository,
        token=token,
        current_revision=current_revision,
        default_branch=default_branch,
        accepted_authorization_revision=record.authorization_revision,
        accepted_intent=True,
    )
    target, witness = proof.target, proof.witness
    if (
        proof.disposition != "COMPLETE"
        or target is None
        or witness is None
        or target.repository != repository
        or target.change != record.change
        or target.branch is None
    ):
        return None
    blob = _quality_workflow_blob(repository, token, current_revision, read=read)
    if blob is None:
        return None
    identity = json.dumps(
        [
            repository,
            record.issue_number,
            record.change,
            record.request_comment_id,
            accepted_decision_sha256,
            witness.revision,
            target.branch,
            blob,
        ],
        separators=(",", ":"),
    )
    return NativeQualityObligation(
        witness.revision,
        target.branch,
        blob,
        hashlib.sha256(identity.encode()).hexdigest(),
        accepted_at,
        default_branch,
        target.revision,
        witness.revisions.carrier_base,
    )


def _application_job(
    repository: str,
    token: str,
    request_comment_id: int,
    *,
    read: GitHubReader,
    record: ApplicationDecisionRecord | None = None,
    transport_comment_ids: tuple[int, ...] = (),
    accepted_decision_sha256: str | None = None,
    recent_comments: tuple[Mapping[str, object], ...] = (),
    current_dispatch_request_comment_id: int | None = None,
    current_revision: str | None = None,
    issue_comments: tuple[Mapping[str, object], ...] = (),
) -> ApplicationCompletion:
    """Locate one exact application run and prefer its durable carrier handoff."""

    runs = _application_runs(
        repository,
        token,
        request_comment_id,
        read=read,
        transport_comment_ids=transport_comment_ids,
    )
    if runs is None or not runs:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-run-unavailable",
            request_comment_id=request_comment_id,
        )
    if len(runs) > 1:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-run-identity-ambiguous",
            request_comment_id=request_comment_id,
        )
    run = runs[0]

    run_id = _positive_int(run.get("id"))
    run_attempt = _positive_int(run.get("run_attempt"))
    if run_id is None or run_attempt is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-run-identity-incomplete",
            request_comment_id=request_comment_id,
        )
    if run.get("status") != "completed":
        return ApplicationCompletion(
            "RESUMABLE",
            "application-completion-in-progress",
            request_comment_id=request_comment_id,
        )
    inventory = github_complete_run_jobs(
        repository, token, run_id=run_id, run_attempt=run_attempt, read=read
    )
    if inventory is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-job-list-incomplete",
            request_comment_id=request_comment_id,
        )
    job = inventory.single_apply
    if job is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-job-identity-ambiguous",
            request_comment_id=request_comment_id,
        )
    job_id = job.id

    # A physical-only accepted save has no formal consequence to replay.
    # Only a terminal native Application plus the canonical write witness can
    # expose its outstanding verification gate; unknown writes stay in the
    # existing recovery path.
    if record is not None and accepted_decision_sha256 is not None and current_revision:
        try:
            source = WorkerRequest(record.issue_number, record.role, record.action)
            batch = parse_effect_batch(
                record.raw_worker_result, source, authorized_change=record.change
            )
            if _implementation_development_save(batch):
                obligation = _saved_development_quality_obligation(
                    repository,
                    token,
                    record=record,
                    accepted_decision_sha256=accepted_decision_sha256,
                    issue_comments=issue_comments,
                    current_revision=current_revision,
                    run=run,
                    job=job,
                    read=read,
                )
                if obligation is not None:
                    return ApplicationCompletion(
                        "RESUMABLE",
                        (
                            "verification-obligation-pending"
                            if obligation.carrier_revision == obligation.revision
                            else "application-completion-historical-save-unsettled"
                        ),
                        request_comment_id=request_comment_id,
                        job_id=job_id,
                        quality_obligation=obligation,
                    )
        except (HTTPError, OSError, RuntimeError, TypeError, ValueError):
            # Failure to prove the saved work is never a verification target.
            pass

    # Reconcile the final durable Effect for a terminal no-carrier run before
    # considering optional recovery/diagnostic artifacts. Error text is not a
    # completion predicate: only immutable intent, exhausted writer paths and
    # a monotonic negative postcondition can prove ABORTED.
    if record is not None and accepted_decision_sha256 is not None:
        try:
            if _qualified_unapplied_terminal_carrier_effect(
                repository,
                token,
                record=record,
                run=run,
                job=job,
                run_id=run_id,
                run_attempt=run_attempt,
                read=read,
            ):
                return ApplicationCompletion(
                    "ABORTED",
                    "application-completion-terminal-effect-not-applied",
                    request_comment_id=request_comment_id,
                )
        except (HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
            return ApplicationCompletion(
                "INVALID",
                "application-completion-effect-evidence-unavailable",
                request_comment_id=request_comment_id,
            )

    recovery_artifact: ApplicationRecoveryArtifact | ApplicationExceptionArtifact | None = None
    if (
        record is not None
        and accepted_decision_sha256 is not None
        and isinstance(run.get("head_sha"), str)
    ):
        try:
            steps = job.steps
            # Both native Application stages can fail after ACCEPT. The
            # complete attempt-scoped job inventory selects the evidence type,
            # not the Role, error message or the historical request shape.
            stage = application_artifact_stage(steps)
            if stage == "INVALID":
                return ApplicationCompletion(
                    "INVALID",
                    "application-completion-artifact-writers-ambiguous",
                    request_comment_id=request_comment_id,
                )
            has_exception = stage in {"PRE_EXCEPTION", "POST_EXCEPTION"}
            accepted_effects: object = None
            try:
                accepted_document = json.loads(record.raw_worker_result)
                if isinstance(accepted_document, Mapping):
                    accepted_effects = accepted_document.get("requested_effects")
            except json.JSONDecodeError:
                pass
            # A v2 semantic projection may elide the physical Original.
            # Only the shared Application source qualifier can establish it.
            # Carrier-owned PR writes retain the distinct terminal negative
            # postcondition path above; the native upload step alone cannot
            # reclassify a merge as an Application-owned Effect.
            has_original_effect = isinstance(accepted_effects, list) and bool(accepted_effects)
            legacy_activation = (record.role, record.action, record.change) == (
                "lead",
                "propose-change",
                "unset",
            )
            physical_exception_source = False
            if has_exception and accepted_effects == [] and not legacy_activation:
                try:
                    original = _qualified_physical_original_accepted_effects(
                        record=record,
                        source=WorkerRequest(record.issue_number, record.role, record.action),
                        repository=repository,
                        token=token,
                        read=read,
                    )
                    if original is not None:
                        physical_exception_source = not original.effects
                        if (
                            len(original.effects) == 1
                            and original.effects[0].kind == "github-mutation"
                        ):
                            payload = json.loads(original.effects[0].payload_json)
                            physical_exception_source = (
                                isinstance(payload, Mapping)
                                and payload.get("operation") == "application-materialize"
                            )
                except (HTTPError, OSError, RuntimeError, TypeError, ValueError):
                    # Unqualified source never licenses a different artifact
                    # or converts uncertainty into absence/no-write proof.
                    physical_exception_source = False
            if has_exception and (
                has_original_effect or legacy_activation or physical_exception_source
            ):
                recovery_artifact = read_application_exception_artifact(
                    repository,
                    token,
                    run_id=run_id,
                    run_attempt=run_attempt,
                    job_id=job_id,
                    record=record,
                    accepted_decision_sha256=accepted_decision_sha256,
                    read=read,
                    artifact_reader=read_github_artifact_bytes,
                    strict_read=True,
                )
            else:
                recovery_artifact = read_application_recovery_artifact(
                    repository,
                    token,
                    run_id=run_id,
                    run_attempt=run_attempt,
                    job_id=job_id,
                    request_comment_id=record.request_comment_id,
                    accepted_decision_sha256=accepted_decision_sha256,
                    read=read,
                    artifact_reader=read_github_artifact_bytes,
                    strict_read=True,
                )
        except (HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
            # A failed/incomplete evidence read is not an observed absent
            # legacy artifact. Never reclassify source failure as NO_WRITE.
            return ApplicationCompletion(
                "INVALID",
                "application-completion-recovery-evidence-unavailable",
                request_comment_id=request_comment_id,
            )

    if recovery_artifact is None or accepted_decision_sha256 is None:
        # The pre-recovery-protocol job can be identified from its *actual*
        # completed Actions step list.  This is missing historical evidence,
        # never a proof of zero writes or permission to rerun the old job.
        steps = job.steps
        legacy_no_upload_step = (
            record is not None
            and accepted_decision_sha256 is not None
            and job.status == "completed"
            and job.conclusion == "failure"
            and steps is not None
            and ("Freshly authorize and apply repository-owned effects", "failure") in steps
            and not any(
                name
                in {
                    "Upload exact application recovery evidence",
                    "Upload final exact application recovery evidence",
                }
                for name, _conclusion in steps
            )
            and any(name == "Complete job" for name, _conclusion in steps)
        )
        return ApplicationCompletion(
            "INVALID",
            (
                "application-completion-legacy-recovery-upload-unavailable"
                if legacy_no_upload_step
                else "application-completion-recovery-evidence-missing"
            ),
            request_comment_id=request_comment_id,
            job_id=job_id if legacy_no_upload_step else None,
        )
    if isinstance(recovery_artifact, ApplicationExceptionArtifact):
        if record is None:
            return ApplicationCompletion("INVALID", "application-exception-acceptance-missing")
        proof = classify_application_exception_recovery(
            record=record, artifact=recovery_artifact, repository=repository, token=token
        )
        unresolved = _unresolved_accepted_proof_completion(
            proof,
            origin="EXCEPTION",
            request_comment_id=request_comment_id,
            recovery_artifact=recovery_artifact,
            accepted_record=record,
            accepted_decision_sha256=accepted_decision_sha256,
        )
        if unresolved is not None:
            return unresolved
        return ApplicationCompletion(
            "RESUMABLE",
            "application-completion-continuation-required",
            request_comment_id=request_comment_id,
            recovery_artifact=recovery_artifact,
        )

    prior_failures = cast(
        list[str],
        recovery_artifact.document["prior_failure_evidence_sha256"],
    )
    if recovery_artifact.failure_evidence_sha256 in prior_failures:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-recovery-evidence-repeated",
            request_comment_id=request_comment_id,
            recovery_artifact=recovery_artifact,
        )

    recovery_failure = recovery_artifact.document.get("failure_evidence")
    post_effect_candidate = bool(
        not recovery_artifact.continuation_eligible
        and isinstance(recovery_failure, Mapping)
        and _accepted_recovery_boundary(recovery_failure) == "POST_EFFECT_RESULT"
    )
    post_effect_proof = (
        classify_post_effect_result_recovery(
            record=record,
            artifact=recovery_artifact,
            repository=repository,
            token=token,
        )
        if post_effect_candidate and record is not None
        else None
    )
    post_effect_proven = bool(
        post_effect_proof is not None and post_effect_proof.continuation == "CONTINUE"
    )
    if post_effect_candidate:
        if post_effect_proof is None:
            return ApplicationCompletion(
                "INVALID",
                "application-completion-recovery-proof-missing",
                request_comment_id=request_comment_id,
                recovery_artifact=recovery_artifact,
            )
        unresolved = _unresolved_accepted_proof_completion(
            post_effect_proof,
            origin="POST_EFFECT",
            request_comment_id=request_comment_id,
            recovery_artifact=recovery_artifact,
            accepted_record=record,
            accepted_decision_sha256=accepted_decision_sha256,
        )
        if unresolved is not None:
            return unresolved

    if record is not None:
        try:
            qualified_carrier = _qualified_carrier_for_application_run(
                repository,
                token,
                request_comment_id,
                run=run,
                run_id=run_id,
                run_attempt=run_attempt,
                job=job,
                record=record,
                read=read,
            )
        except (OSError, RuntimeError, ValueError):
            return ApplicationCompletion(
                "INVALID",
                "application-completion-carrier-evidence-invalid",
                request_comment_id=request_comment_id,
                recovery_artifact=recovery_artifact,
            )
        if qualified_carrier is not None:
            if not recovery_artifact.continuation_eligible and not post_effect_proven:
                return ApplicationCompletion(
                    "INVALID",
                    "application-completion-carrier-recovery-evidence-incomplete",
                    request_comment_id=request_comment_id,
                    qualified_carrier=qualified_carrier,
                    recovery_artifact=recovery_artifact,
                )
            outcome_source = WorkerRequest(
                record.issue_number,
                record.role,
                record.action,
            )
            outcome_state, outcome_reason = _carrier_outcome_status(
                recent_comments=recent_comments,
                owner=repository.split("/", 1)[0],
                repository=repository,
                source=outcome_source,
                record=record,
                accepted_decision_sha256=accepted_decision_sha256,
                recovery_artifact=recovery_artifact,
                qualified_carrier=qualified_carrier,
            )
            if outcome_state == "BLOCKED":
                return ApplicationCompletion(
                    "INVALID",
                    outcome_reason or "application-completion-carrier-outcome-invalid",
                    request_comment_id=request_comment_id,
                    recovery_artifact=recovery_artifact,
                )
            if outcome_state == "COMPLETE":
                return ApplicationCompletion(
                    "RESUMABLE",
                    "application-completion-continuation-required",
                    request_comment_id=request_comment_id,
                    recovery_artifact=recovery_artifact,
                )
            prior_handoff_reason = _prior_dispatch_handoff_reason(
                repository,
                token,
                recent_comments=recent_comments,
                owner=repository.split("/", 1)[0],
                current_dispatch_request_comment_id=current_dispatch_request_comment_id,
                plan_id=qualified_carrier.plan.plan_id,
                read=read,
            )
            if prior_handoff_reason is not None:
                return ApplicationCompletion(
                    "INVALID",
                    prior_handoff_reason,
                    request_comment_id=request_comment_id,
                    recovery_artifact=recovery_artifact,
                )
            return ApplicationCompletion(
                "RESUMABLE",
                "application-completion-carrier-required",
                request_comment_id=request_comment_id,
                qualified_carrier=qualified_carrier,
                recovery_artifact=recovery_artifact,
            )

    if not recovery_artifact.continuation_eligible and not post_effect_proven:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-recovery-boundary-unsafe",
            request_comment_id=request_comment_id,
            recovery_artifact=recovery_artifact,
        )
    failure_evidence = recovery_artifact.document.get("failure_evidence")
    if (
        isinstance(failure_evidence, Mapping)
        and _accepted_recovery_boundary(failure_evidence) == "READ_ONLY"
        and failure_evidence.get("unfinished_boundary")
        in {
            "effect-reconciliation",
            "effect-precondition",
            "effect-precondition-exception",
        }
    ):
        # The previous read-only invocation obtained no sufficient proof.
        # Re-observe the *same* immutable accepted effects in each fresh
        # dispatcher wake, but issue no additional Application continuation
        # while they remain unproven. This is observation, never a write retry.
        if record is None or current_revision is None:
            return ApplicationCompletion(
                "INVALID",
                "application-completion-read-only-observation-context-missing",
                request_comment_id=request_comment_id,
                recovery_artifact=recovery_artifact,
            )
        try:
            repo = read(repository, token, "")
        except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            repo = None
        branch = repo.get("default_branch") if isinstance(repo, Mapping) else None
        if not isinstance(branch, str) or not branch:
            return ApplicationCompletion(
                "INVALID",
                "application-completion-read-only-default-branch-unavailable",
                request_comment_id=request_comment_id,
                recovery_artifact=recovery_artifact,
            )
        source = WorkerRequest(record.issue_number, record.role, record.action)
        proof = classify_accepted_read_only_effects(
            record=record,
            source=source,
            recovery_evidence=failure_evidence,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=branch,
            recovery_artifact=(
                recovery_artifact
                if isinstance(recovery_artifact, ApplicationRecoveryArtifact)
                else None
            ),
        )
        unresolved = _unresolved_accepted_proof_completion(
            proof,
            origin="READ_ONLY",
            request_comment_id=request_comment_id,
            recovery_artifact=recovery_artifact,
            accepted_record=record,
            accepted_decision_sha256=accepted_decision_sha256,
        )
        if unresolved is not None:
            return unresolved
        if proof.pending_frontier_proof is not None:
            return ApplicationCompletion(
                "RESUMABLE",
                "application-completion-continuation-required",
                request_comment_id=request_comment_id,
                recovery_artifact=recovery_artifact,
                accepted_proof=proof,
                accepted_record=record,
                accepted_decision_sha256=accepted_decision_sha256,
            )
    return ApplicationCompletion(
        "RESUMABLE",
        "application-completion-continuation-required",
        request_comment_id=request_comment_id,
        recovery_artifact=recovery_artifact,
    )


def _application_runs(
    repository: str,
    token: str,
    request_comment_id: int,
    *,
    read: GitHubReader,
    transport_comment_ids: tuple[int, ...] = (),
) -> tuple[Mapping[str, object], ...] | None:
    """Read every transport run bound to an exact request, if observable."""

    transport_ids = transport_comment_ids or (request_comment_id,)
    titles = {render_application_run_name(comment_id) for comment_id in transport_ids}
    runs = _complete_workflow_runs(repository, token, _APPLICATION_WORKFLOW, read=read)
    if runs is None:
        return None
    return tuple(run for run in runs if run.get("display_title") in titles)


def _preaccept_application_state(
    repository: str,
    token: str,
    request_comment_id: int,
    *,
    read: GitHubReader,
) -> ApplicationCompletion | None:
    """Classify one ingress from fresh run/job terminal evidence.

    A request comment without an observable application run is not a terminal
    rejection: GitHub event and workflow-run visibility are asynchronous.  A
    completed run is terminal-no-accept only when its exact ``apply`` job also
    has a known non-success terminal conclusion, which is the repository-owned
    pre-ACCEPT non-mutation boundary.
    """

    runs = _application_runs(repository, token, request_comment_id, read=read)
    if runs is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-run-observation-incomplete",
            request_comment_id=request_comment_id,
        )
    if len(runs) > 1:
        return ApplicationCompletion(
            "AMBIGUOUS",
            "application-completion-run-identity-ambiguous",
            request_comment_id=request_comment_id,
        )
    if not runs:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-run-not-yet-observable",
            request_comment_id=request_comment_id,
        )
    run = runs[0]
    status = run.get("status")
    if status != "completed":
        return ApplicationCompletion(
            "RESUMABLE",
            "application-completion-preaccept-in-progress",
            request_comment_id=request_comment_id,
        )
    conclusion = run.get("conclusion")
    if conclusion not in _TERMINAL_NO_ACCEPT_CONCLUSIONS:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-terminal-evidence-unknown",
            request_comment_id=request_comment_id,
        )
    run_id = _positive_int(run.get("id"))
    if run_id is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-run-identity-incomplete",
            request_comment_id=request_comment_id,
        )
    run_attempt = _positive_int(run.get("run_attempt"))
    inventory = (
        github_complete_run_jobs(
            repository, token, run_id=run_id, run_attempt=run_attempt, read=read
        )
        if run_attempt is not None
        else None
    )
    if inventory is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-terminal-job-evidence-incomplete",
            request_comment_id=request_comment_id,
        )
    # Capacity cancellation can finish before GitHub creates an apply job.
    # Only a complete first-attempt inventory proves zero apply executions.
    if (
        not inventory.apply_jobs
        and conclusion in {"cancelled", "timed_out", "skipped"}
        and run_attempt == 1
    ):
        return ApplicationCompletion(
            "REJECTED",
            "application-completion-preaccept-terminal-no-accept",
            request_comment_id=request_comment_id,
        )
    apply_job = inventory.single_apply
    if apply_job is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-terminal-job-identity-ambiguous",
            request_comment_id=request_comment_id,
        )
    if (
        apply_job.status != "completed"
        or apply_job.conclusion not in _TERMINAL_NO_ACCEPT_CONCLUSIONS
    ):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-terminal-job-evidence-contradictory",
            request_comment_id=request_comment_id,
        )
    return ApplicationCompletion(
        "REJECTED",
        "application-completion-preaccept-terminal-no-accept",
        request_comment_id=request_comment_id,
    )


def _accepted_decision_sha256(
    record: ApplicationDecisionRecord,
    comments: tuple[Mapping[str, object], ...],
) -> str | None:
    """Return the digest of the one exact accepted decision already observed."""

    bodies = [
        cast(str, comment.get("body"))
        for comment in comments
        if is_github_actions_comment(comment)
        and isinstance(comment.get("body"), str)
        and parse_application_decision(comment.get("body")) == record
    ]
    if len(bodies) != 1:
        return None
    return hashlib.sha256(bodies[0].encode("utf-8")).hexdigest()


def _application_decisions(
    comments: tuple[Mapping[str, object], ...],
) -> tuple[ApplicationDecisionRecord, ...]:
    return tuple(
        record
        for comment in comments
        if is_github_actions_comment(comment)
        for record in (parse_application_decision(comment.get("body")),)
        if record is not None
    )


def _proven_aborted_predecessors(
    repository: str,
    token: str,
    *,
    records: list[ApplicationDecisionRecord],
    ingress_times: Mapping[int, str | None],
    decision_times: Mapping[int, str | None],
    issue_comments: tuple[Mapping[str, object], ...],
    read: GitHubReader,
) -> set[int]:
    """Retire only an earlier, provably no-write ACCEPTED merge occurrence.

    A new EFFECT_REQUEST cannot compete indefinitely with the earlier failed
    ACCEPT. An independently qualified ingress after the old ACCEPTED decision
    (not a later decision or higher numeric ID), plus a fresh exact abort proof,
    is mandatory before the old occurrence becomes history.
    """

    def source_timestamp(value: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(UTC) if parsed.tzinfo is not None else None

    # A contradictory or missing Actions decision timestamp for any competing
    # ACCEPTED occurrence makes ordering indeterminate for the whole set.
    if any(
        record.disposition == "ACCEPTED"
        and source_timestamp(decision_times.get(record.request_comment_id)) is None
        for record in records
    ):
        return set()

    retired: set[int] = set()
    for record in records:
        if record.disposition != "ACCEPTED":
            continue
        old_time = source_timestamp(decision_times.get(record.request_comment_id))
        if old_time is None or not any(
            request_id != record.request_comment_id
            and (ingress_time := source_timestamp(created_at)) is not None
            and ingress_time > old_time
            for request_id, created_at in ingress_times.items()
        ):
            continue
        digest = _accepted_decision_sha256(record, issue_comments)
        if digest is None:
            continue
        try:
            consequence = _application_job(
                repository,
                token,
                record.request_comment_id,
                read=read,
                record=record,
                accepted_decision_sha256=digest,
            )
        except (HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
            continue
        if consequence.state == "ABORTED":
            retired.add(record.request_comment_id)
    return retired


def _application_worker_for_record(
    record: ApplicationDecisionRecord,
    source: WorkerRequest,
) -> WorkerActionResult | None:
    """Validate the immutable intent payload against its decision metadata."""

    if (
        record.issue_number != source.issue_number
        or record.role != source.role
        or record.action != source.action
        or record.disposition not in {"ACCEPTED", "REJECTED"}
    ):
        return None
    try:
        worker = parse_worker_result(
            record.raw_worker_result,
            source,
            authorized_change=record.change,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.worker_result_sha256
        != hashlib.sha256(record.raw_worker_result.encode("utf-8")).hexdigest()
        or worker.change != record.change
        or worker.typed_result.result.kind.value != record.result_kind
        or worker.typed_result.action.value != source.action
    ):
        return None
    return worker


def _authorization_ancestry(
    repository: str,
    token: str,
    *,
    authorization_revision: str,
    current_revision: str,
    read: GitHubReader,
) -> tuple[tuple[str, str], ...] | None:
    if authorization_revision == current_revision:
        return ()
    comparison = read(
        repository,
        token,
        f"compare/{authorization_revision}...{current_revision}",
    )
    base_commit = comparison.get("base_commit") if isinstance(comparison, Mapping) else None
    if (
        not isinstance(comparison, Mapping)
        or comparison.get("status") != "ahead"
        or not isinstance(base_commit, Mapping)
        or base_commit.get("sha") != authorization_revision
    ):
        return None
    return ((authorization_revision, current_revision),)


def _observe_initial_source_admission(
    qualification: QualificationInput,
    comments: tuple[Mapping[str, object], ...],
    *,
    repository: str,
    token: str,
    read: GitHubReader,
) -> QualificationInput:
    """Acquire only evidence required by the initial-occurrence predicate."""

    if (
        qualification.change != "unset"
        or not qualification.events
        or qualification.initial_source_admission is not None
        or qualification.current_revision is None
    ):
        return qualification
    correlation = _application_correlation_fields(
        qualification.events[0].application_correlation or ""
    )
    if correlation is None:
        return qualification
    records = [
        record
        for record in _application_decisions(comments)
        if record.request_comment_id == _positive_int_string(correlation[1])
        and record.disposition == "ACCEPTED"
    ]
    if len(records) != 1:
        return qualification
    record = records[0]
    ancestry = qualification.authorization_ancestry
    for before, after in (
        (record.authorization_revision, correlation[7]),
        (correlation[7], qualification.current_revision),
    ):
        if before == after or (before, after) in ancestry:
            continue
        observed = _authorization_ancestry(
            repository, token, authorization_revision=before, current_revision=after, read=read
        )
        if observed is None:
            return qualification
        ancestry = (*ancestry, *observed)
    qualification = replace(qualification, authorization_ancestry=ancestry)
    qualification = bind_initial_source_admission(
        qualification, comments, original_request=None, repository=repository
    )
    if qualification.initial_source_admission is not None:
        return qualification
    try:
        original = read(repository, token, f"issues/comments/{record.request_comment_id}")
    except (HTTPError, OSError, ValueError):
        return qualification
    return bind_initial_source_admission(
        qualification,
        comments,
        original_request=original if isinstance(original, Mapping) else None,
        repository=repository,
    )


def _fresh_completion_postconditions(
    raw_worker_result: str,
    *,
    source: WorkerRequest,
    repository: str,
    token: str,
    current_revision: str,
    accepted_authorization_revision: str,
    authorized_change: str,
    request_comment_id: int,
    observed_application_correlation: str | None = None,
    accepted_record: ApplicationDecisionRecord | None = None,
    read: GitHubReader = _github_json,
) -> bool:
    """Reobserve the existing consequence first, before correction admission."""

    def qualified(
        correction_observer: (
            Callable[[StagedEffect], tuple[int, MaterializationProof] | None] | None
        ) = None,
    ) -> bool:
        return consequence_postconditions_complete(
            raw_worker_result,
            source=source,
            repository=repository,
            token=token,
            current_revision=current_revision,
            accepted_authorization_revision=accepted_authorization_revision,
            authorized_change=authorized_change,
            request_comment_id=request_comment_id,
            allow_pending_continuation=True,
            allow_accepted_successor=True,
            accepted_intent=True,
            observed_application_correlation=observed_application_correlation,
            formal_result_observed=True,
            **(
                {"accepted_correction_observer": correction_observer}
                if correction_observer is not None
                else {}
            ),
        )

    # A previously completed original result needs no R9 lookup, extra GET,
    # or new callback; unchanged recovery paths retain their original owner.
    if qualified():
        return True
    if (
        accepted_record is None
        or accepted_record.disposition != "ACCEPTED"
        or "application-materialize" not in accepted_record.raw_worker_result
    ):
        return False
    original = _qualified_accepted_original_effects(
        record=accepted_record,
        source=source,
        raw_worker_result=accepted_record.raw_worker_result,
        repository=repository,
        token=token,
    )
    # A correction qualifies only the materialization it witnesses. Each
    # remaining accepted Effect must still pass its own postcondition via the
    # shared consequence owner; partial completion is not batch completion.
    if not isinstance(original, EffectBatch) or original.typed_result is None:
        return False
    repository_info = read(repository, token, "")
    default_branch = (
        repository_info.get("default_branch") if isinstance(repository_info, Mapping) else None
    )
    if not isinstance(default_branch, str) or not default_branch:
        return False
    successor = next_action(original.typed_result.action, original.typed_result.result)
    successor_routing = None if successor is None else (role_for(successor).value, successor.value)
    correction_observer = _accepted_correction_observer_for_batch(
        record=accepted_record,
        source=source,
        batch=original,
        repository=repository,
        token=token,
        current_revision=current_revision,
        default_branch=default_branch,
        accepted_successor_routing=successor_routing,
    )
    return correction_observer is not None and qualified(correction_observer)


def _formal_consequence(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    record: ApplicationDecisionRecord,
    worker: WorkerActionResult,
    issue_comments: tuple[Mapping[str, object], ...],
    lifecycle_events: tuple[Mapping[str, object], ...],
    current_issue: Mapping[str, object],
    current_revision: str,
    read: GitHubReader,
    mode: Literal["current", "pending"],
    authorization_ancestry: tuple[tuple[str, str], ...],
    original_322_recovery_qualified: bool = False,
) -> bool:
    observation = normalize_github_issue(current_issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != source.issue_number
        or observation.state not in {"open", "closed"}
        or observation.change == ""
    ):
        return False
    try:
        successor = next_action(worker.typed_result.action, worker.typed_result.result)
    except (TypeError, ValueError):
        return False
    expected_terminal = successor is None
    expected_routing = None if successor is None else (role_for(successor).value, successor.value)
    effective_change: str | None = record.change
    if effective_change == "unset" and observation.change != "unset":
        effective_change = observation.change
    prefix = f"application:{record.request_comment_id}:{source.issue_number}:"
    matching_comments: list[Mapping[str, object]] = []
    matching_events = []
    for comment in issue_comments:
        event = parse_formal_result(comment, current_revision=current_revision)
        if (
            event is not None
            and event.valid
            and event.issue_number == source.issue_number
            and event.role == source.role
            and event.action == source.action
            and event.result_kind == record.result_kind
            and (
                (effective_change is None or effective_change == "unset")
                and event.change not in {"", "unset"}
                or event.change == effective_change
            )
            and event.application_correlation is not None
            and event.application_correlation.startswith(prefix)
        ):
            matching_comments.append(comment)
            matching_events.append(event)
    if not matching_comments:
        return False
    # One accepted request is one immutable intent.  A recovery run may
    # re-emit the same canonical consequence after the default branch moves;
    # those transport-level duplicates are not competing application owners.
    canonical_event = max(
        matching_events,
        key=lambda event: -1 if event.comment_id is None else event.comment_id,
    )
    if effective_change in {None, "unset"}:
        effective_change = canonical_event.change
    if effective_change is None:
        return False
    # The formal result carries two different revisions:
    # Default-Branch-Revision is the worker/formal evidence revision, while
    # the final correlation field is the exact application observation
    # revision used to bind repository effects.  Both must be safe ancestors
    # of this fresh wake, but postcondition observation must use the latter.
    formal_evidence_revision = canonical_event.default_branch_revision
    correlation_fields = _application_correlation_fields(
        canonical_event.application_correlation or ""
    )
    if (
        formal_evidence_revision is None
        or correlation_fields is None
        or _SHA.fullmatch(correlation_fields[7]) is None
    ):
        return False
    application_observation_revision = correlation_fields[7]
    formal_authorization_ancestry = authorization_ancestry
    for evidence_revision in (
        formal_evidence_revision,
        application_observation_revision,
    ):
        if evidence_revision == current_revision:
            continue
        descendant_ancestry = _authorization_ancestry(
            repository,
            token,
            authorization_revision=evidence_revision,
            current_revision=current_revision,
            read=read,
        )
        if descendant_ancestry is None:
            return False
        formal_authorization_ancestry = (
            *formal_authorization_ancestry,
            *descendant_ancestry,
        )

    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=effective_change,
        state=observation.state,
        current_routing=observation.routing,
        # The formal qualifier owns the complete causal suffix.  Supplying
        # only the candidate result makes a historical same-Action occurrence
        # look like the current frontier and breaks A -> A / A -> B -> A.
        comments=issue_comments,
        current_revision=current_revision,
        mode=mode,
        expected_routing=expected_routing,
        expected_terminal=expected_terminal,
        source_routing=(source.role, source.action),
        expected_result_kind=record.result_kind,
        expected_application_correlation=(
            canonical_event.application_correlation if mode == "pending" else None
        ),
        lifecycle_events=lifecycle_events,
        authorization_ancestry=formal_authorization_ancestry,
    )
    qualification = _observe_initial_source_admission(
        qualification, issue_comments, repository=repository, token=token, read=read
    )
    decision = qualify_current_formal_consequence(qualification)
    if not decision.qualified or decision.event is None:
        return False
    candidate = canonical_event
    if (
        mode == "current"
        and not original_322_recovery_qualified
        and not _fresh_completion_postconditions(
            record.raw_worker_result,
            source=source,
            repository=repository,
            token=token,
            # Formal correlation remains bound to the accepted observation, but
            # successor-readiness is a fresh repository predicate.  In
            # particular an Archive PR must target the current default branch,
            # not merely the historical application revision.
            current_revision=current_revision,
            authorized_change=record.change,
            request_comment_id=record.request_comment_id,
            accepted_authorization_revision=record.authorization_revision,
            observed_application_correlation=canonical_event.application_correlation,
            accepted_record=record,
            read=read,
        )
    ):
        return False
    return (
        getattr(decision.event, "comment_id", None) == candidate.comment_id
        and getattr(decision.event, "application_correlation", None)
        == candidate.application_correlation
    )


def _successor_consequence_supersedes(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    worker: WorkerActionResult,
    current_issue: Mapping[str, object],
    change: str,
    current_revision: str,
) -> bool:
    """Recognize a committed predecessor consumed by a merged successor."""

    try:
        successor = next_action(worker.typed_result.action, worker.typed_result.result)
    except (TypeError, ValueError):
        return False
    observation = normalize_github_issue(current_issue)
    if (
        successor not in {ModelAction.MERGE_ARCHIVE_PR, ModelAction.MERGE_IMPLEMENTATION_PR}
        or observation is None
        or observation.routing != (role_for(successor).value, successor.value)
    ):
        return False
    return merged_pr_readiness_complete(
        repository=repository,
        token=token,
        issue_number=source.issue_number,
        action=successor.value,
        change=change,
        current_revision=current_revision,
    )


def _accepted_application_state(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    record: ApplicationDecisionRecord,
    issue_comments: tuple[Mapping[str, object], ...],
    lifecycle_events: tuple[Mapping[str, object], ...],
    current_issue: Mapping[str, object],
    current_revision: str,
    read: GitHubReader,
    continuation_transport_comment_ids: tuple[int, ...] | None = (),
    recent_comments: tuple[Mapping[str, object], ...] = (),
    current_dispatch_request_comment_id: int | None = None,
) -> ApplicationCompletion:
    worker = _application_worker_for_record(record, source)
    if worker is None or record.disposition != "ACCEPTED":
        return ApplicationCompletion(
            "INVALID",
            "application-completion-accepted-intent-invalid",
            request_comment_id=record.request_comment_id,
        )
    accepted_decision_sha256 = _accepted_decision_sha256(record, issue_comments)
    ancestry = _authorization_ancestry(
        repository,
        token,
        authorization_revision=record.authorization_revision,
        current_revision=current_revision,
        read=read,
    )
    if ancestry is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-stale",
            request_comment_id=record.request_comment_id,
        )
    try:
        decoded_intent = json.loads(record.raw_worker_result)
    except json.JSONDecodeError:
        decoded_intent = None
    semantic_intent = (
        isinstance(decoded_intent, Mapping) and decoded_intent.get("_semantic_intent_version") == 2
    )
    # Only the original, Human-authorized #322 correction can substitute a
    # freshly qualified I/R/M/V/S/F proof for its obsolete six-file envelope.
    # This is deliberately *after* a formal event is observed, so the normal
    # absence-of-result path never calls a result-dependent predicate.
    original_322_formal_seen = (
        source == WorkerRequest(322, "executor", "implement-change")
        and record.request_comment_id == _ORIGINAL_322_REQUEST
        and any(
            isinstance(item.get("body"), str)
            and cast(str, item["body"]).startswith("ACTION_RESULT\n")
            and f"application:{_ORIGINAL_322_REQUEST}:322:" in cast(str, item["body"])
            for item in issue_comments
        )
    )
    if original_322_formal_seen:
        try:
            recovery = qualify_original_322_pre_formal(
                repository=repository,
                token=token,
                source=source,
                record=record,
                issue_comments=issue_comments,
                current_issue=current_issue,
                current_revision=current_revision,
                read=read,
            )
        except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            recovery = None
        if (
            recovery is not None
            and recovery.disposition == "COMPLETE"
            and _formal_consequence(
                repository=repository,
                token=token,
                source=source,
                record=record,
                worker=worker,
                issue_comments=issue_comments,
                lifecycle_events=lifecycle_events,
                current_issue=current_issue,
                current_revision=current_revision,
                read=read,
                mode="current",
                authorization_ancestry=ancestry,
                original_322_recovery_qualified=True,
            )
        ):
            return ApplicationCompletion(
                "COMPLETE",
                "application-completion-original-322-recovered",
                record.request_comment_id,
            )
    if _formal_consequence(
        repository=repository,
        token=token,
        source=source,
        record=record,
        worker=worker,
        issue_comments=issue_comments,
        lifecycle_events=lifecycle_events,
        current_issue=current_issue,
        current_revision=current_revision,
        read=read,
        mode="current",
        authorization_ancestry=ancestry,
    ):
        return ApplicationCompletion(
            "COMPLETE",
            "application-completion-complete",
            request_comment_id=record.request_comment_id,
        )
    # A predecessor's open-carrier predicate is intentionally monotonic at
    # the causal boundary: once its successor merge consequence is observed
    # in the current default branch, the predecessor must not be resumed as
    # though its former open carrier were still missing.  This is derived
    # from the same successor consequence owner; it does not accept a formal
    # result without a prior commit-time readiness proof, and it does not
    # apply to a missing archive carrier on the review route.
    if _successor_consequence_supersedes(
        repository=repository,
        token=token,
        source=source,
        worker=worker,
        current_issue=current_issue,
        change=record.change,
        current_revision=current_revision,
    ):
        return ApplicationCompletion(
            "COMPLETE",
            "application-completion-successor-advanced",
            request_comment_id=record.request_comment_id,
        )
    if continuation_transport_comment_ids is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-continuation-chain-incomplete",
            request_comment_id=record.request_comment_id,
        )
    if len(continuation_transport_comment_ids) > 1:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-continuation-chain-ambiguous",
            request_comment_id=record.request_comment_id,
        )

    # One native Application observation per accepted frontier. Later
    # formal/successor proof checks must not replace its read-only witness.
    def observe_application_job() -> ApplicationCompletion:
        return _application_job(
            repository,
            token,
            record.request_comment_id,
            read=read,
            record=record,
            transport_comment_ids=continuation_transport_comment_ids,
            accepted_decision_sha256=accepted_decision_sha256,
            recent_comments=recent_comments,
            current_dispatch_request_comment_id=current_dispatch_request_comment_id,
            current_revision=current_revision,
            issue_comments=issue_comments,
        )

    # New semantic envelopes resume Phase B even with zero worker Effects.
    # Historical raw envelopes retain their existing formal-only path.
    resumed: ApplicationCompletion | None = None
    if worker.requested_effects or semantic_intent:
        resumed = observe_application_job()
        if resumed.state == "RESUMABLE":
            return resumed
    if (
        not worker.requested_effects
        and not semantic_intent
        and source.action == "finalize-change"
        and record.result_kind == "archive-ready"
    ):
        return ApplicationCompletion(
            "NONE",
            "application-completion-none",
        )
    if _formal_consequence(
        repository=repository,
        token=token,
        source=source,
        record=record,
        worker=worker,
        issue_comments=issue_comments,
        lifecycle_events=lifecycle_events,
        current_issue=current_issue,
        current_revision=current_revision,
        read=read,
        mode="pending",
        authorization_ancestry=ancestry,
    ):
        return ApplicationCompletion(
            "RESUMABLE",
            "application-completion-formal-result-pending",
            request_comment_id=record.request_comment_id,
        )
    observation = normalize_github_issue(current_issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != source.issue_number
        or observation.change not in {record.change, "unset"}
        or observation.state not in {"open", "closed"}
    ):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-current-issue-invalid",
            request_comment_id=record.request_comment_id,
        )
    try:
        successor = next_action(worker.typed_result.action, worker.typed_result.result)
    except (TypeError, ValueError):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-result-transition-invalid",
            request_comment_id=record.request_comment_id,
        )
    expected_routing = None if successor is None else (role_for(successor).value, successor.value)
    if observation.state == "closed":
        return ApplicationCompletion(
            "INVALID",
            "application-completion-routing-without-formal",
            request_comment_id=record.request_comment_id,
        )
    if observation.routing == (source.role, source.action):
        return resumed if resumed is not None else observe_application_job()
    if successor is not None and observation.routing == expected_routing:
        return ApplicationCompletion(
            "RESUMABLE",
            "application-completion-successor-pending",
            request_comment_id=record.request_comment_id,
        )
    return ApplicationCompletion(
        "INVALID",
        "application-completion-current-routing-invalid",
        request_comment_id=record.request_comment_id,
    )


def _effect_request_source_hint(body: str) -> WorkerRequest | None:
    """Recover only source identity from current or legacy EFFECT_REQUEST shapes."""

    lines = body.splitlines()
    if lines[:1] != ["EFFECT_REQUEST"]:
        return None
    encoded = [
        line.removeprefix("Worker-Result-B64: ")
        for line in lines[1:]
        if line.startswith("Worker-Result-B64: ")
    ]
    if len(encoded) != 1 or not encoded[0] or encoded[0] != encoded[0].strip():
        return None
    try:
        raw = base64.b64decode(encoded[0].encode("ascii"), validate=True).decode("utf-8")
        decoded = json.loads(raw)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError):
        return None
    if not isinstance(decoded, Mapping):
        return None
    issue_number = decoded.get("issue_number")
    role = decoded.get("role")
    action = decoded.get("action")
    if (
        isinstance(issue_number, bool)
        or not isinstance(issue_number, int)
        or issue_number <= 0
        or not isinstance(role, str)
        or not isinstance(action, str)
    ):
        return None
    try:
        return WorkerRequest(issue_number, role, action)
    except (TypeError, ValueError):
        return None


def _legacy_encoded_source_identity(body: str) -> tuple[int, str] | None:
    """Recover bounded source identity from an older encoded worker envelope.

    Some pre-protocol envelopes contain a valid source prefix but an invalid
    or obsolete worker payload later in the JSON document.  They cannot be
    accepted as application requests, but their explicit encoded Issue and
    Action are still sufficient to prove that they belong to another source
    and must not poison the current one.  Role is deliberately ignored and
    remains derived from Action everywhere it is executable.
    """

    lines = body.splitlines()
    if lines[:1] != ["EFFECT_REQUEST"]:
        return None
    encoded = [
        line.removeprefix("Worker-Result-B64: ")
        for line in lines[1:]
        if line.startswith("Worker-Result-B64: ")
    ]
    if len(encoded) != 1 or not encoded[0]:
        return None
    # Older connector transports can be truncated after the source prefix,
    # and a rendered copy may contain whitespace or a non-base64 ellipsis at
    # the cut.  Only recover a bounded valid base64 prefix; this helper is a
    # source filter for historical transport, never an application parser.
    normalized = "".join(encoded[0].split())[:_LEGACY_SOURCE_B64_PREFIX_CHARS]
    match = re.match(r"[A-Za-z0-9+/=]+", normalized)
    if match is None:
        return None
    usable = match.group(0)
    usable = usable[: len(usable) - (len(usable) % 4)]
    if not usable:
        return None
    try:
        raw = base64.b64decode(usable.encode("ascii"), validate=True).decode("utf-8", "ignore")
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error):
        return None

    # Legacy worker results put their source fields before requested effects.
    # Restrict extraction to that prefix so nested effect payloads cannot
    # become a second source of authority.  Duplicate or absent fields fail
    # closed instead of being guessed.
    boundaries = [
        index
        for marker in ('"result_content"', '"requested_effects"')
        if (index := raw.find(marker)) >= 0
    ]
    prefix = raw[: min(boundaries)] if boundaries else raw

    def unique_match(pattern: str) -> str | None:
        matches = re.findall(pattern, prefix)
        return matches[0] if len(matches) == 1 else None

    issue_text = unique_match(r'(?:^|[,{])\s*"issue_n(?:umber|uber)"\s*:\s*([1-9][0-9]*)')
    action = unique_match(r'(?:^|[,{])\s*"action"\s*:\s*"([^"\\]+)"')
    if issue_text is None or action is None:
        return None
    return int(issue_text), action


def _legacy_raw_source_hint(body: str) -> WorkerRequest | None:
    """Recover source identity from the explicit legacy raw envelope.

    Older EFFECT_REQUEST comments may not contain a parseable modern worker
    envelope, but an explicit ``Workflow: #N`` plus ``Action: X`` still binds
    the transport to one source.  Role is derived from the executable Action
    model; it is never accepted from untrusted prose.
    """

    lines = body.splitlines()
    if lines[:1] != ["EFFECT_REQUEST"]:
        return None
    workflow = next(
        (line.removeprefix("Workflow: #") for line in lines if line.startswith("Workflow: #")),
        None,
    )
    action = next(
        (line.removeprefix("Action: ") for line in lines if line.startswith("Action: ")),
        None,
    )
    if workflow is None or action is None or not workflow.isdigit() or workflow.startswith("0"):
        return None
    try:
        parsed_action = ModelAction(action)
        role = role_for(parsed_action).value
        return WorkerRequest(int(workflow), role, parsed_action.value)
    except (TypeError, ValueError):
        return None


def _effect_request_matches_source(
    *,
    repository: str,
    source: WorkerRequest,
    body: str,
    request: ApplicationRequest | None,
) -> bool:
    """Resolve legacy identity or the one opaque machine correlation."""

    claimed = _effect_request_source_hint(body)
    if claimed is not None:
        return claimed == source
    if request is None or request.dispatch_correlation is None:
        return False
    return request.dispatch_correlation == dispatch_correlation_for(
        repository,
        source,
        request.authorization_revision,
    )


def _preaccept_exception_repair_status(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    request_comment_id: int,
    issue_comments: tuple[Mapping[str, object], ...],
    current_revision: str,
    read: GitHubReader,
    candidate: _IngressCandidate | None = None,
    current_issue: Mapping[str, object] | None = None,
) -> Literal["NONE", "BLOCKED", "REPAIRED", "TERMINAL_INVALID_INPUT", "INVALID"]:
    """Bound an observed execution defect to a material application-code advance.

    This consumes the existing EXECUTION_EXCEPTION evidence surface, not a
    retry counter or routing state. A source change permits fresh normal
    reauthorization, but never accepts an old pre-ACCEPT request or replays a
    write. Missing/contradictory provenance cannot release a failed effect.
    """

    def one(body: str, field: str) -> str | None:
        matches = [line[len(field) :] for line in body.splitlines() if line.startswith(field)]
        return matches[0] if len(matches) == 1 and matches[0] else None

    matches: list[Mapping[str, object]] = []
    for comment in issue_comments:
        if not is_github_actions_comment(comment):
            continue
        body = comment.get("body")
        if not isinstance(body, str) or not body.startswith("EXECUTION_EXCEPTION\n"):
            continue
        if one(body, "Request-Comment-ID: ") == str(request_comment_id):
            matches.append(comment)
    if not matches:
        return "NONE"
    # One GitHub run can have several completed attempts. Every attempt has
    # its own immutable exception correlation. Older attempts are historical,
    # not competing current-frontier ingresses or an application retry count.
    attempts: dict[int, tuple[int, str]] = {}
    for comment in matches:
        body = cast(str, comment["body"])
        run_id = one(body, "Run-ID: ")
        run_attempt = one(body, "Run-Attempt: ")
        original_revision = one(body, "Revision: ")
        if (
            one(body, "Workflow: ") != f"#{source.issue_number}"
            or one(body, "Role: ") != source.role
            or one(body, "Action: ") != source.action
            or one(body, "Mutation-Outcome: ") != "NO_APPLICATION_WRITE_ATTEMPTED"
            or one(body, "Classification: ") != "UNCLASSIFIED_EXECUTION_EXCEPTION"
            or not isinstance(original_revision, str)
            or _SHA.fullmatch(original_revision) is None
            or not isinstance(run_id, str)
            or not run_id.isdecimal()
            or int(run_id) <= 0
            or not isinstance(run_attempt, str)
            or not run_attempt.isdecimal()
            or int(run_attempt) <= 0
            or one(body, "Exception-Correlation: ")
            != f"application:{run_id}:{run_attempt}:{request_comment_id}"
        ):
            return "INVALID"
        attempt_number = int(run_attempt)
        if attempt_number in attempts:
            # A duplicate in the same attempt cannot be dismissed as a rerun.
            return "INVALID"
        attempts[attempt_number] = (int(run_id), original_revision)
    runs = _application_runs(repository, token, request_comment_id, read=read)
    if runs is None or len(runs) != 1:
        return "INVALID"
    run = runs[0]
    latest_attempt = _positive_int(run.get("run_attempt"))
    if (
        latest_attempt is None
        or max(attempts) > latest_attempt
        or any(run.get("id") != recorded_run_id for recorded_run_id, _ in attempts.values())
        or run.get("status") != "completed"
        or run.get("conclusion") not in _TERMINAL_NO_ACCEPT_CONCLUSIONS
    ):
        return "INVALID"
    _recorded_run_id, original_revision = attempts[max(attempts)]

    # A deterministic typed-input rejection is terminal even on unchanged
    # application code.  This is narrower than repairing a valid worker result:
    # it needs the original immutable request, the current authoritative source,
    # every native attempt's pre-ACCEPT/zero-write evidence and the same parser
    # that rejected the payload.  The caller has already ruled out ACCEPTED.
    if candidate is not None and current_issue is not None:
        request = candidate.request
        body = candidate.body
        observed = normalize_github_issue(current_issue)
        if (
            request is not None
            and body is not None
            and candidate.request_comment_id == request_comment_id
            and request.authorization_revision == original_revision
            and run.get("head_sha") == original_revision
            and observed is not None
            and observed.authoritative
            and observed.state == "open"
            and observed.issue_number == source.issue_number
            and observed.routing == (source.role, source.action)
            and isinstance(observed.change, str)
            and observed.change not in {"", "unset"}
            and request.dispatch_correlation
            == dispatch_correlation_for(repository, source, original_revision)
            and set(attempts) == set(range(1, latest_attempt + 1))
        ):
            try:
                original_request = parse_application_request(body)
            except ValueError:
                original_request = None
            if original_request == request and all(
                one(cast(str, comment["body"]), "Revision: ") == original_revision
                and one(cast(str, comment["body"]), "Result: ") == "execution-exception"
                and one(cast(str, comment["body"]), "Change: ") == observed.change
                and one(cast(str, comment["body"]), "Attempted-Operation: ")
                == "pre-accept-worker-result-qualification"
                and one(cast(str, comment["body"]), "Unfinished-Work: ")
                == "pre-accept-worker-result-qualification"
                for comment in matches
            ):
                try:
                    parse_worker_result(
                        request.raw_worker_result,
                        source,
                        authorized_change=observed.change,
                    )
                except ValueError as exc:
                    if all(
                        one(cast(str, comment["body"]), "Raw-Error: ") == str(exc)
                        for comment in matches
                    ):
                        return "TERMINAL_INVALID_INPUT"

    if original_revision == current_revision:
        return "BLOCKED"
    try:
        comparison = read(repository, token, f"compare/{original_revision}...{current_revision}")
    except (HTTPError, OSError, ValueError, json.JSONDecodeError):
        return "INVALID"
    if not isinstance(comparison, Mapping):
        return "INVALID"
    base = comparison.get("base_commit")
    files = comparison.get("files")
    if (
        comparison.get("status") != "ahead"
        or not isinstance(base, Mapping)
        or base.get("sha") != original_revision
        or not isinstance(files, list)
        or len(files) >= 300
        or any(not isinstance(item, Mapping) for item in files)
    ):
        return "INVALID"
    relevant = any(
        isinstance(item.get("filename"), str)
        and (
            cast(str, item["filename"]).startswith("src/investment_strategy/scheduled_agent_")
            or item["filename"]
            in {
                "src/investment_strategy/issue_comment_bridge.py",
                "src/investment_strategy/workflow_dispatch.py",
                ".github/workflows/scheduled-agent-application.yml",
            }
        )
        for item in files
        if isinstance(item, Mapping)
    )
    return "REPAIRED" if relevant else "BLOCKED"


def _classify_ingress_candidate(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    candidate: _IngressCandidate,
    decisions_by_request: Mapping[int, tuple[ApplicationDecisionRecord, ...]],
    issue_comments: tuple[Mapping[str, object], ...],
    current_revision: str,
    read: GitHubReader,
    current_issue: Mapping[str, object] | None = None,
) -> PreacceptClassification:
    """Classify one current-frontier ingress before reducing the set."""

    decisions = decisions_by_request.get(candidate.request_comment_id, ())
    if len(decisions) > 1:
        return "INVALID"
    if decisions:
        disposition = decisions[0].disposition
        if disposition == "ACCEPTED":
            return "ACCEPTED"
        if disposition == "REJECTED":
            return "REJECTED"
        return "INVALID"

    state = _preaccept_application_state(
        repository,
        token,
        candidate.request_comment_id,
        read=read,
    )
    if state is None:
        return "UNKNOWN"
    if state.state == "RESUMABLE":
        return "LIVE_PREACCEPT"
    if state.state != "REJECTED":
        return "UNKNOWN" if "not-yet-observable" in state.reason else "INVALID"

    exception_status = _preaccept_exception_repair_status(
        repository=repository,
        token=token,
        source=source,
        request_comment_id=candidate.request_comment_id,
        issue_comments=issue_comments,
        current_revision=current_revision,
        read=read,
        candidate=candidate,
        current_issue=current_issue,
    )
    if exception_status == "INVALID":
        return "INVALID"
    if exception_status == "BLOCKED":
        return "NEEDS_REPAIR"
    if exception_status == "TERMINAL_INVALID_INPUT":
        return "TERMINAL_NO_ACCEPT"

    # Historical pre-protocol requests require an independent inertness proof;
    # current protocol terminal failures already carry the application-owned
    # no-mutation boundary from the failed apply job.
    request = candidate.request
    if request is not None:
        relation = _application_protocol_relation(
            repository,
            token,
            authorization_revision=request.authorization_revision,
            read=read,
        )
        if relation == "PRE_PROTOCOL":
            if candidate.body is None or not _legacy_unaccepted_request_is_inert(
                repository,
                token,
                source=source,
                request_comment_id=candidate.request_comment_id,
                request_body=candidate.body,
                issue_comments=issue_comments,
                current_revision=current_revision,
                read=read,
            ):
                return "INVALID"
            return "REJECTED"
        if relation == "INDETERMINATE":
            # The exact completed application run already supplies the
            # authoritative terminal/no-accept boundary.  Historical
            # protocol lineage is compatibility evidence only; an old
            # authorization SHA may legitimately have disappeared from the
            # current commit graph and must not crash dispatch or become a
            # second competing classifier.
            return "TERMINAL_NO_ACCEPT"
    return "TERMINAL_NO_ACCEPT"


def _application_protocol_relation(
    repository: str,
    token: str,
    *,
    authorization_revision: str,
    read: GitHubReader,
) -> Literal["PRE_PROTOCOL", "PROTOCOL", "INDETERMINATE"]:
    """Classify an exact request revision against the durable protocol activation."""

    if authorization_revision == _APPLICATION_DECISION_PROTOCOL_REVISION:
        return "PROTOCOL"
    try:
        before = read(
            repository,
            token,
            f"compare/{authorization_revision}...{_APPLICATION_DECISION_PROTOCOL_REVISION}",
        )
    except (HTTPError, OSError, ValueError, json.JSONDecodeError):
        return "INDETERMINATE"
    if isinstance(before, Mapping):
        base = before.get("base_commit")
        if (
            before.get("status") == "ahead"
            and isinstance(base, Mapping)
            and base.get("sha") == authorization_revision
        ):
            return "PRE_PROTOCOL"
    try:
        after = read(
            repository,
            token,
            f"compare/{_APPLICATION_DECISION_PROTOCOL_REVISION}...{authorization_revision}",
        )
    except (HTTPError, OSError, ValueError, json.JSONDecodeError):
        return "INDETERMINATE"
    if isinstance(after, Mapping):
        base = after.get("base_commit")
        if (
            after.get("status") in {"ahead", "identical"}
            and isinstance(base, Mapping)
            and base.get("sha") == _APPLICATION_DECISION_PROTOCOL_REVISION
        ):
            return "PROTOCOL"
    return "INDETERMINATE"


def _legacy_unaccepted_request_is_inert(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    request_comment_id: int,
    request_body: str,
    issue_comments: tuple[Mapping[str, object], ...],
    current_revision: str,
    read: GitHubReader,
) -> bool:
    """Prove a pre-protocol request left no request-owned durable consequence."""

    try:
        request = parse_application_request(request_body)
        if request is None:
            return False
        worker = parse_worker_result(request.raw_worker_result, source)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    if worker.requested_effects:
        return False

    issue = read(repository, token, f"issues/{source.issue_number}")
    observation = normalize_github_issue(issue) if isinstance(issue, Mapping) else None
    if (
        observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.routing != (source.role, source.action)
        or observation.change != worker.change
    ):
        return False

    expected_kind = worker.typed_result.result.kind.value
    for comment in issue_comments:
        event = parse_formal_result(comment, current_revision=current_revision)
        correlation_fields = (
            None
            if event is None or not isinstance(event.application_correlation, str)
            else _application_correlation_fields(event.application_correlation)
        )
        if (
            event is not None
            and event.issue_number == source.issue_number
            and event.change == worker.change
            and event.role == source.role
            and event.action == source.action
            and event.result_kind == expected_kind
            and correlation_fields is not None
            and correlation_fields[1] == str(request_comment_id)
        ):
            return False

    # The request id is part of the proof boundary even though a pre-protocol
    # request has no APPLICATION_DECISION record to bind it.
    return request_comment_id > 0


def _derive_frontier(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    current_issue: Mapping[str, object],
    issue_comments: tuple[Mapping[str, object], ...],
    lifecycle_events: tuple[Mapping[str, object], ...],
    current_revision: str,
    read: GitHubReader,
) -> tuple[CurrentFrontier | None, bool]:
    """Read the current frontier through the canonical formal qualifier."""

    observation = normalize_github_issue(current_issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != source.issue_number
        or observation.state not in {"open", "closed"}
        or observation.routing != (source.role, source.action)
        or observation.change == ""
    ):
        return None, False
    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=observation.change,
        state=observation.state,
        current_routing=observation.routing,
        comments=issue_comments,
        current_revision=current_revision,
        lifecycle_events=lifecycle_events,
    )
    if qualification.events:
        latest_revision = qualification.events[-1].default_branch_revision
        if latest_revision is None:
            return None, False
        ancestry = _authorization_ancestry(
            repository,
            token,
            authorization_revision=latest_revision,
            current_revision=current_revision,
            read=read,
        )
        if ancestry is None:
            return None, False
        qualification = replace(qualification, authorization_ancestry=ancestry)
    qualification = _observe_initial_source_admission(
        qualification, issue_comments, repository=repository, token=token, read=read
    )
    frontier = derive_current_frontier(qualification)
    return frontier, frontier is not None


def _frontier_comment_id(frontier: CurrentFrontier | None) -> int | None:
    if frontier is None or frontier.event is None:
        return None
    comment_id = getattr(frontier.event, "comment_id", None)
    return _positive_int(comment_id)


def derive_unanswered_human_wait(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    current_revision: str,
    read: GitHubReader = _github_json,
) -> bool:
    """Prove an unchanged same-action Human question from current GitHub truth.

    This is deliberately a narrow no-op qualification, not a cached BLOCKED
    result. Any fresh Issue event, comment, or changed main revision resumes
    ordinary semantics; missing evidence never qualifies a suppressing wait.
    """

    if (source.role, source.action) != ("lead", "resolve-question"):
        return False
    try:
        issue = read(repository, token, f"issues/{source.issue_number}")
        if not isinstance(issue, Mapping):
            return False
        comments = _paged_list(
            repository,
            token,
            f"issues/{source.issue_number}/comments?sort=created&direction=asc",
            read=read,
        )
        lifecycle = _paged_list(
            repository, token, f"issues/{source.issue_number}/timeline", read=read
        )
        frontier, qualified = _derive_frontier(
            repository=repository,
            token=token,
            source=source,
            current_issue=cast(Mapping[str, object], issue),
            issue_comments=comments,
            lifecycle_events=lifecycle,
            current_revision=current_revision,
            read=read,
        )
    except (HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return False
    if not qualified or frontier is None or not isinstance(frontier.event, FormalLifecycleEvent):
        return False
    event = frontier.event
    if (
        not event.valid
        or event.comment_id is None
        or event.action != "resolve-question"
        or event.result_kind != "human-decision-required"
        or event.successor != ("lead", "resolve-question")
        or event.default_branch_revision != current_revision
        or frontier.current_routing != ("lead", "resolve-question")
    ):
        return False
    anchor = [item for item in comments if item.get("id") == event.comment_id]
    if len(anchor) != 1:
        return False
    since = _comment_time(anchor[0])
    if (
        since is None
        or anchor[0].get("updated_at") != since
        or not isinstance(issue.get("updated_at"), str)
        or cast(str, issue["updated_at"]) > since
    ):
        return False
    # A newer comment may be a qualifying Human answer, or new material
    # source evidence. Neither may be silenced merely by unchanged routing.
    if any(
        item.get("id") != event.comment_id
        and (not isinstance(item.get("created_at"), str) or cast(str, item["created_at"]) >= since)
        for item in comments
    ):
        return False
    # Issue mutations are also source evidence. Same-second event order is
    # not inferred; in doubt, resume rather than suppress.
    return not any(
        item.get("event") != "commented"
        or item.get("id") != event.comment_id
        or item.get("created_at") != since
        for item in lifecycle
        if not isinstance(item.get("created_at"), str) or cast(str, item["created_at"]) >= since
    )


def apply_derived_human_wait(
    decision: DispatchDecision,
    *,
    repository: str,
    token: str,
    current_revision: str,
    read: GitHubReader = _github_json,
) -> DispatchDecision:
    """Keep the Action-only selector intact and prevent repeated ingress."""

    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_routing != ("lead", "resolve-question")
        or decision.selected_issue_id is None
    ):
        return decision
    if not derive_unanswered_human_wait(
        repository,
        token,
        source=WorkerRequest(decision.selected_issue_id, "lead", "resolve-question"),
        current_revision=current_revision,
        read=read,
    ):
        return decision
    return replace(
        decision,
        selected_issue_id=None,
        selected_routing=None,
        disposition="FAIL_CLOSED",
        reason="human-question-awaiting-new-evidence",
    )


def _belongs_to_current_frontier(
    request_comment_id: int,
    frontier: CurrentFrontier | None,
    *,
    occurrence_created_at: str | None = None,
) -> bool:
    """Retain evidence not proven historical relative to the current frontier.

    Formal routes use the latest qualified consequence comment as their causal
    boundary.  A first pre-activation route has no such consequence, so it
    uses the active Issue-timeline routing admission.  This is a candidate
    filter, not proof of current-occurrence authority.
    """

    boundary = _frontier_comment_id(frontier)
    if boundary is not None:
        return request_comment_id > boundary
    if frontier is None or frontier.occurrence_anchor is None:
        return False
    anchor_time = frontier.occurrence_anchor.created_at
    if anchor_time is None:
        return False
    # Cross-Issue timestamps have second precision. Only strictly earlier
    # evidence is historical here. Retain ties and missing timestamps for
    # the existing ingress/decision classifier, without inferring causality.
    return occurrence_created_at is None or occurrence_created_at >= anchor_time


def _accepted_intent_owns_frontier(
    record: ApplicationDecisionRecord,
    frontier: CurrentFrontier | None,
    *,
    source: WorkerRequest,
) -> bool:
    """Allow a same-Action result to bind its own recurrence frontier.

    For ``A -> A`` the accepted request necessarily precedes its formal result,
    while the repository route remains ``A``.  The existing
    ``Application-Correlation`` is the causal binding that distinguishes this
    current occurrence from an earlier accepted request; it is not a new
    persisted generation or epoch.
    """

    if frontier is None or frontier.event is None:
        return False
    correlation = getattr(frontier.event, "application_correlation", None)
    if not isinstance(correlation, str):
        return False
    fields = _application_correlation_fields(correlation)
    if fields is None:
        return False
    return (
        fields[1] == str(record.request_comment_id)
        and fields[2] == str(source.issue_number)
        and fields[4] == source.role
        and fields[5] == source.action
        and fields[6] == record.result_kind.lower().replace("_", "-")
    )


def _frontier_application_decisions(
    decisions: tuple[ApplicationDecisionRecord, ...],
    frontier: CurrentFrontier | None,
) -> tuple[ApplicationDecisionRecord, ...]:
    """Resolve the ACCEPTED intent that owns the qualified formal frontier."""

    if frontier is None or frontier.event is None:
        return ()
    correlation = getattr(frontier.event, "application_correlation", None)
    if not isinstance(correlation, str):
        return ()
    fields = _application_correlation_fields(correlation)
    if fields is None:
        return ()
    request_comment_id = _positive_int_string(fields[1])
    if request_comment_id is None:
        return ()
    return tuple(
        record
        for record in decisions
        if record.request_comment_id == request_comment_id
        and record.issue_number == frontier.issue_number
        and record.change == frontier.change
        and record.role == fields[4]
        and record.action == fields[5]
        and record.result_kind == fields[6]
    )


def _continuation_transport_comment_ids(
    *,
    repository: str,
    owner: str,
    source: WorkerRequest,
    record: ApplicationDecisionRecord,
    issue_comments: tuple[Mapping[str, object], ...],
    recent_comments: tuple[Mapping[str, object], ...],
    token: str,
    read: GitHubReader,
) -> tuple[int, ...] | None:
    """Find fresh transport comments for one immutable accepted intent.

    A continuation comment is deliberately not an application intent.  It is
    only a new issue-comment workflow boundary, content-addressed to the one
    accepted decision body.  Runs started by that boundary have a different
    GitHub comment id in their run name, so the recovery reducer must bind
    exactly those runs while ignoring the exhausted predecessor run.
    """

    decision_bodies = []
    for comment in issue_comments:
        if not is_github_actions_comment(comment):
            continue
        body = comment.get("body")
        if not isinstance(body, str):
            continue
        parsed = parse_application_decision(body)
        if (
            parsed is not None
            and parsed.request_comment_id == record.request_comment_id
            and parsed.disposition == "ACCEPTED"
            and parsed.issue_number == source.issue_number
            and parsed.role == source.role
            and parsed.action == source.action
        ):
            decision_bodies.append(body)
    if len(decision_bodies) != 1:
        return ()
    decision_sha256 = hashlib.sha256(decision_bodies[0].encode("utf-8")).hexdigest()
    matches: dict[int, ApplicationContinuationRequest] = {}
    for comment in recent_comments:
        if not _trusted_connector_comment(comment, owner):
            continue
        body = comment.get("body")
        comment_id = _positive_int(comment.get("id"))
        if not isinstance(body, str) or comment_id is None:
            continue
        continuation = parse_application_continuation_request(body)
        if continuation is None:
            continue
        try:
            expected_correlation = application_continuation_correlation(
                repository,
                source.issue_number,
                record.request_comment_id,
                decision_sha256,
                continuation.predecessor_run_id,
                continuation.predecessor_run_attempt,
                continuation.predecessor_job_id,
                continuation.predecessor_artifact_id,
                continuation.predecessor_artifact_digest,
                continuation.failure_evidence_sha256,
                continuation.recovery_episode_sha256,
            )
        except ValueError:
            continue
        if (
            continuation.issue_number == source.issue_number
            and continuation.original_request_comment_id == record.request_comment_id
            and continuation.accepted_decision_sha256 == decision_sha256
            and continuation.continuation_correlation == expected_correlation
        ):
            matches[comment_id] = continuation
    if not matches:
        return ()
    workflow_runs = _application_runs(
        repository,
        token,
        record.request_comment_id,
        read=read,
        transport_comment_ids=(record.request_comment_id, *sorted(matches)),
    )
    return _continuation_leaf_comment_ids(
        request_comment_id=record.request_comment_id,
        continuation_predecessors={
            comment_id: (
                continuation.predecessor_run_id,
                continuation.predecessor_run_attempt,
            )
            for comment_id, continuation in matches.items()
        },
        workflow_runs=workflow_runs,
    )


def _continuation_leaf_comment_ids(
    *,
    request_comment_id: int,
    continuation_predecessors: Mapping[int, tuple[int, int]],
    workflow_runs: tuple[Mapping[str, object], ...] | None,
) -> tuple[int, ...] | None:
    """Reduce trusted continuation comments to the leaf of their observed run chain.

    None means the Actions run lineage is incomplete or ambiguous, so the
    caller must fail closed. Multiple leaf ids preserve a real branch for an
    explicit ambiguity result.
    """

    if not continuation_predecessors:
        return ()
    if workflow_runs is None:
        return None
    transport_ids = set(continuation_predecessors)
    if request_comment_id in transport_ids:
        return None
    transport_ids.add(request_comment_id)
    run_by_comment: dict[int, tuple[int, int]] = {}
    for run in workflow_runs:
        title = run.get("display_title")
        if not isinstance(title, str):
            continue
        comment_id = parse_application_run_name(title)
        if comment_id is None or comment_id not in transport_ids:
            continue
        run_id = _positive_int(run.get("id"))
        run_attempt = _positive_int(run.get("run_attempt"))
        if run_id is None or run_attempt is None:
            return None
        identity = (run_id, run_attempt)
        previous = run_by_comment.get(comment_id)
        if previous is not None and previous != identity:
            return None
        run_by_comment[comment_id] = identity
    if set(run_by_comment) != transport_ids:
        return None

    comment_by_run: dict[int, int] = {}
    for comment_id, (run_id, _latest_attempt) in run_by_comment.items():
        if run_id in comment_by_run:
            return None
        comment_by_run[run_id] = comment_id

    children: dict[int, list[int]] = {comment_id: [] for comment_id in transport_ids}
    for child_id, predecessor_identity in continuation_predecessors.items():
        predecessor_run_id, predecessor_run_attempt = predecessor_identity
        parent_id = comment_by_run.get(predecessor_run_id)
        if parent_id is None:
            return None
        latest_attempt = run_by_comment[parent_id][1]
        if predecessor_run_attempt > latest_attempt:
            return None
        children[parent_id].append(child_id)

    leaves: set[int] = set()
    visited: set[int] = set()
    active: set[int] = set()

    def visit(comment_id: int) -> bool:
        if comment_id in active or comment_id in visited:
            return False
        active.add(comment_id)
        visited.add(comment_id)
        descendants = children[comment_id]
        if not descendants and comment_id != request_comment_id:
            leaves.add(comment_id)
        for child_id in descendants:
            if not visit(child_id):
                return False
        active.remove(comment_id)
        return True

    if not visit(request_comment_id) or visited != transport_ids:
        return None
    return tuple(sorted(leaves))


def _application_continuation_body(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    request_comment_id: int,
    predecessor_evidence: ApplicationRecoveryArtifact | ApplicationExceptionArtifact | None = None,
    read: GitHubReader = _github_json,
) -> str | None:
    """Render one exact continuation transport for a qualified predecessor."""

    if predecessor_evidence is None:
        return None
    if isinstance(predecessor_evidence, ApplicationRecoveryArtifact) and (
        predecessor_evidence.failure_evidence_sha256
        in cast(list[str], predecessor_evidence.document["prior_failure_evidence_sha256"])
    ):
        return None
    issue_comments = _paged_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created&direction=asc",
        read=read,
    )
    matches: list[tuple[str, str]] = []
    for comment in issue_comments:
        if not is_github_actions_comment(comment):
            continue
        body = comment.get("body")
        if not isinstance(body, str):
            continue
        record = parse_application_decision(body)
        if (
            record is not None
            and record.request_comment_id == request_comment_id
            and record.disposition == "ACCEPTED"
            and record.issue_number == source.issue_number
            and record.role == source.role
            and record.action == source.action
        ):
            created_at = _comment_time(comment)
            if created_at is None:
                return None
            matches.append((body, created_at))
    if len(matches) != 1:
        return None
    decision_sha256 = hashlib.sha256(matches[0][0].encode("utf-8")).hexdigest()
    if predecessor_evidence.accepted_decision_sha256 != decision_sha256:
        return None
    if isinstance(predecessor_evidence, ApplicationExceptionArtifact):
        accepted_record = parse_application_decision(matches[0][0])
        if (
            accepted_record is None
            or classify_application_exception_recovery(
                record=accepted_record,
                artifact=predecessor_evidence,
                repository=repository,
                token=token,
            ).continuation
            != "CONTINUE"
        ):
            return None
    elif not predecessor_evidence.continuation_eligible:
        accepted_record = parse_application_decision(matches[0][0])
        if (
            accepted_record is None
            or classify_post_effect_result_recovery(
                record=accepted_record,
                artifact=predecessor_evidence,
                repository=repository,
                token=token,
            ).continuation
            != "CONTINUE"
        ):
            return None
    body = render_application_continuation_request(
        repository=repository,
        issue_number=source.issue_number,
        original_request_comment_id=request_comment_id,
        accepted_decision_sha256=decision_sha256,
        predecessor_run_id=predecessor_evidence.run_id,
        predecessor_run_attempt=predecessor_evidence.run_attempt,
        predecessor_job_id=predecessor_evidence.job_id,
        predecessor_artifact_id=predecessor_evidence.artifact_id,
        predecessor_artifact_digest=predecessor_evidence.artifact_digest,
        failure_evidence_sha256=predecessor_evidence.failure_evidence_sha256,
        recovery_episode_sha256=predecessor_evidence.recovery_episode_sha256,
    )
    parsed_body = parse_application_continuation_request(body)
    if parsed_body is None:
        raise RuntimeError("rendered application continuation is not parseable")
    # Continuations are carried on Runtime shards, never on the source Issue.
    # Observe the complete repository-wide lineage since the immutable ACCEPT;
    # the current-day shard alone cannot prove that a predecessor is unused.
    history_query = urlencode({"sort": "created", "direction": "asc", "since": matches[0][1]})
    comments = _paged_list(
        repository,
        token,
        f"issues/comments?{history_query}",
        read=read,
    )
    existing_correlations = {
        comment_id
        for item in comments
        if isinstance(item, Mapping)
        and isinstance(item.get("body"), str)
        and (comment_id := _positive_int(item.get("id"))) is not None
        and (existing := parse_application_continuation_request(cast(str, item.get("body"))))
        is not None
        and _trusted_connector_comment(item, repository.split("/", 1)[0])
        and existing.continuation_correlation == parsed_body.continuation_correlation
    }
    if existing_correlations:
        return None
    return body


def _development_acceptance_source(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    record: ApplicationDecisionRecord,
    default_branch: str,
    read: GitHubReader,
) -> DevelopmentDispatchSource | None:
    document = json.loads(record.raw_worker_result)
    stored = document.get("_native_development_dispatch") if isinstance(document, dict) else None
    if stored is None and isinstance(document, Mapping):
        delivery = document.get("_native_implementation_delivery")
        if isinstance(delivery, Mapping):
            stored = delivery.get("dispatch")
    if not isinstance(stored, Mapping):
        return None
    qualified = qualify_development_dispatch_source(
        repository,
        token,
        source=source,
        request_comment_id=record.request_comment_id,
        current_revision=record.authorization_revision,
        default_branch=default_branch,
        read=read,
        expected_source=stored,
    )
    return qualified if qualified is not None and asdict(qualified) == stored else None


def _development_planning_boundary(
    repository: str,
    token: str,
    *,
    receipt: DevelopmentDispatchSource,
    read: GitHubReader,
) -> datetime | None:
    jobs = github_complete_job_inventory(
        repository, token, run_id=receipt.run_id, run_attempt=receipt.run_attempt, read=read
    )
    if jobs is None:
        return None
    planners = [job for job in jobs if job.get("name") == "bridge"]
    if len(planners) != 1:
        return None
    planner = planners[0]
    steps = planner.get("steps")
    if (
        planner.get("id") != receipt.job_id
        or planner.get("run_id") != receipt.run_id
        or planner.get("run_attempt") != receipt.run_attempt
        or planner.get("head_sha") != receipt.authorization_revision
        or planner.get("status") != "completed"
        or planner.get("conclusion") != "success"
        or not isinstance(steps, list)
    ):
        return None
    planning = [
        step
        for step in steps
        if isinstance(step, Mapping)
        and step.get("name") == "Plan exact correlated machine dispatch decision"
    ]
    if len(planning) != 1:
        return None
    started = _quality_time(planner.get("started_at"))
    boundary = _quality_time(planning[0].get("started_at"))
    completed = _quality_time(planner.get("completed_at"))
    if (
        started is None
        or boundary is None
        or completed is None
        or not started <= boundary <= completed
    ):
        return None
    return boundary


def development_predecessor_evidence(
    completion: ApplicationCompletion, authorization_revision: str
) -> dict[str, object] | None:
    """Project the shared settled proof into the existing immutable ACCEPT intent."""
    obligation = completion.settled_quality_obligation
    observation = completion.quality_observation
    record = completion.accepted_record
    digest = completion.accepted_decision_sha256
    if (
        completion.state != "COMPLETE"
        or obligation is None
        or observation is None
        or record is None
        or digest is None
        or observation.outcome not in ("PASS", "FAIL", "CONFLICT")
        or observation.attempts is None
    ):
        return None
    attempts = [
        asdict(attempt)
        for attempt in observation.attempts
        if attempt.outcome in ("PASS", "STATIC_STEP_FAILURE", "PYTEST_STEP_FAILURE")
    ]
    if not attempts:
        return None
    return {
        "request_comment_id": record.request_comment_id,
        "accepted_decision_sha256": digest,
        "revision": obligation.revision,
        "branch": obligation.branch,
        "workflow_blob": obligation.workflow_blob,
        "obligation_id": obligation.obligation_id,
        "authorization_revision": authorization_revision,
        "attempts": attempts,
    }


def _native_strict_marker_evidence(
    repository: str,
    token: str,
    *,
    revision: str,
    branch: str,
    current_revision: str,
    read: GitHubReader,
) -> tuple[tuple[int, int, int], ...]:
    """Qualify an ordinary native strict PASS, including the executed checkout."""
    path = ".github/workflows/openspec-validate.yml"
    definitions = [
        read(repository, token, f"contents/{path}?{urlencode({'ref': ref})}")
        for ref in (current_revision, revision)
    ]
    if any(
        not isinstance(item, Mapping)
        or item.get("type") != "file"
        or item.get("path") != path
        or not isinstance(item.get("sha"), str)
        or _SHA.fullmatch(item["sha"]) is None
        for item in definitions
    ):
        return ()
    if (
        cast(Mapping[str, object], definitions[0])["sha"]
        != cast(Mapping[str, object], definitions[1])["sha"]
    ):
        return ()
    required_steps = (
        "Checkout validation target",
        "Verify exact checkout revision",
        "Run actions/setup-node@v4",
        "Install qualified OpenSpec baseline",
        "Show OpenSpec version",
        "Qualify executable compatibility",
        "Show active changes",
        "Validate all OpenSpec artifacts",
    )
    observed: list[tuple[int, int, int]] = []
    for event in ("push", "pull_request"):
        runs = _complete_workflow_runs(
            repository,
            token,
            "openspec-validate.yml",
            read=read,
            event=event,
            head_sha=revision,
            require_count=True,
        )
        if runs is None:
            return ()
        for run in runs:
            if run.get("head_branch") != branch:
                continue
            run_id = _positive_int(run.get("id"))
            attempt = _positive_int(run.get("run_attempt"))
            if run_id is None or attempt is None:
                return ()
            for number in range(1, attempt + 1):
                row = read(repository, token, f"actions/runs/{run_id}/attempts/{number}")
                if not isinstance(row, Mapping):
                    return ()
                repo = row.get("repository")
                head_repo = row.get("head_repository")
                if (
                    row.get("id") != run_id
                    or row.get("run_attempt") != number
                    or row.get("path") != path
                    or row.get("event") != event
                    or row.get("head_sha") != revision
                    or row.get("head_branch") != branch
                    or not isinstance(repo, Mapping)
                    or repo.get("full_name") != repository
                    or not isinstance(head_repo, Mapping)
                    or head_repo.get("full_name") != repository
                    or row.get("status") != "completed"
                    or row.get("conclusion") != "success"
                ):
                    return ()
                jobs = github_complete_job_inventory(
                    repository, token, run_id=run_id, run_attempt=number, read=read
                )
                if jobs is None or len(jobs) != 1:
                    return ()
                job = jobs[0]
                job_id = _positive_int(job.get("id"))
                steps = job.get("steps")
                if (
                    job_id is None
                    or job.get("name") != "validate"
                    or job.get("run_id") != run_id
                    or job.get("run_attempt") != number
                    or job.get("head_sha") != revision
                    or job.get("status") != "completed"
                    or job.get("conclusion") != "success"
                    or not isinstance(steps, list)
                ):
                    return ()
                executed = tuple(
                    step.get("name")
                    for step in steps
                    if isinstance(step, Mapping)
                    and step.get("name") in required_steps
                    and step.get("status") == "completed"
                    and step.get("conclusion") == "success"
                )
                if executed != required_steps or not _recovery_review_log_proves_checkout(
                    _github_job_log(repository, token, job_id), repository, revision
                ):
                    return ()
                observed.append((run_id, number, job_id))
    return tuple(observed)


def _bound_legacy_delivery_scope(
    repository: str,
    token: str,
    *,
    original: EffectBatch,
    record: ApplicationDecisionRecord,
    event: FormalLifecycleEvent,
    review: FormalLifecycleEvent,
    formal_comment: Mapping[str, object],
    scope: tuple[str, ...],
    comments: tuple[Mapping[str, object], ...],
    branch: str,
    pr_number: int,
) -> bool:
    """Read a completed legacy bundle; never authorize or replay its effects."""
    if (
        event.revision is None
        or event.application_correlation is None
        or review.revision is None
        or len(original.effects) != 2
        or original.effects[0].kind != "github-mutation"
        or original.effects[1].kind != "issue-comment"
    ):
        return False
    request = find_materialization_payload(
        json.loads(original.effects[0].payload_json), original.source
    )
    checkpoint = json.loads(original.effects[1].payload_json)
    if (
        request is None
        or request.expected_change != record.change
        or request.change != record.change
        or request.branch != branch
        or request.pr_number != pr_number
        or not isinstance(checkpoint, dict)
        or checkpoint.get("issue_number") != record.issue_number
        or not isinstance(checkpoint.get("body"), str)
    ):
        return False
    body = cast(str, checkpoint["body"])
    if (
        _slice_checkpoint_completed_task_ids(
            body, source=original.source, change=record.change, request=request
        )
        != scope
    ):
        return False
    lines = body.splitlines()
    correlation_line = next(line for line in lines if line.startswith("Application-Correlation: "))
    if correlation_line not in (
        "Application-Correlation: pending-application-binding",
        f"Application-Correlation: {event.application_correlation}",
    ):
        return False
    expected = "\n".join(
        f"Revision: {event.revision}"
        if line.startswith("Revision: ")
        else f"Application-Correlation: {event.application_correlation}"
        if line == correlation_line
        else line
        for line in lines
    ) + ("\n" if body.endswith("\n") else "")
    checkpoint_comments = [
        comment
        for comment in comments
        if is_github_actions_comment(comment)
        and isinstance(comment.get("body"), str)
        and cast(str, comment["body"]).startswith("SLICE_CHECKPOINT\n")
        and f"Application-Correlation: {event.application_correlation}"
        in cast(str, comment["body"]).splitlines()
    ]
    accepted_comments = [
        comment
        for comment in comments
        if is_github_actions_comment(comment)
        and parse_application_decision(comment.get("body")) == record
    ]
    if (
        len(checkpoint_comments) != 1
        or checkpoint_comments[0].get("body") != expected
        or len(accepted_comments) != 1
    ):
        return False
    ordered = (accepted_comments[0], checkpoint_comments[0], formal_comment)
    stamps = tuple(_quality_time(comment.get("created_at")) for comment in ordered)
    if (
        any(
            comment.get("created_at") != comment.get("updated_at")
            or _positive_int(comment.get("id")) is None
            for comment in ordered
        )
        or stamps[0] is None
        or stamps[1] is None
        or stamps[2] is None
        or not stamps[0] < stamps[1] < stamps[2]
    ):
        return False
    files = tuple(
        file for file in request.files if file.path == f"openspec/changes/{record.change}/tasks.md"
    )
    return (
        len(files) == 1
        and all(
            _content_sha_at(repository, token, path=file.path, revision=event.revision)
            == file.blob_sha
            for file in request.files
        )
        and openspec_review_revision_applies(
            repository,
            token,
            change=record.change,
            reviewed_revision=review.revision,
            head_revision=event.revision,
        )
        and task_checkpoint_is_exact(
            repository,
            token,
            expected_change=record.change,
            base_sha=request.base_sha,
            file=files[0],
            completed_task_ids=scope,
        )
    )


def _bound_native_delivery_scope(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    frontier: CurrentFrontier,
    event: FormalLifecycleEvent,
    review: FormalLifecycleEvent,
    scope: tuple[str, ...],
    comments: tuple[Mapping[str, object], ...],
    branch: str,
    pr_number: int,
    revision: str,
    current_revision: str,
    read: GitHubReader,
) -> bool:
    """Bind one historical formal delivery to its immutable accepted evidence."""
    decisions = _application_decisions(comments)
    owners = _frontier_application_decisions(decisions, replace(frontier, event=event))
    if len(owners) != 1 or owners[0].disposition != "ACCEPTED":
        return False
    record = owners[0]
    if (
        sum(item.request_comment_id == record.request_comment_id for item in decisions) != 1
        or _accepted_decision_sha256(record, comments) is None
        or event.revision is None
        or _authorization_ancestry(
            repository,
            token,
            authorization_revision=record.authorization_revision,
            current_revision=current_revision,
            read=read,
        )
        is None
        or _authorization_ancestry(
            repository,
            token,
            authorization_revision=event.revision,
            current_revision=revision,
            read=read,
        )
        is None
    ):
        return False
    original = _qualified_physical_original_accepted_effects(
        record=record, source=source, repository=repository, token=token, read=read
    )
    raw = json.loads(record.raw_worker_result)
    evidence = raw.get("_native_implementation_delivery") if isinstance(raw, dict) else None
    formal = [
        comment
        for comment in comments
        if comment.get("id") == event.comment_id
        and parse_formal_result(comment, current_revision=current_revision) == event
    ]
    if original is None or len(formal) != 1 or not isinstance(formal[0].get("body"), str):
        return False
    if evidence is None and original.effects:
        return _bound_legacy_delivery_scope(
            repository,
            token,
            original=original,
            record=record,
            event=event,
            review=review,
            formal_comment=formal[0],
            scope=scope,
            comments=comments,
            branch=branch,
            pr_number=pr_number,
        )
    if (
        original.effects
        or not isinstance(evidence, Mapping)
        or evidence.get("scope_task_ids") != list(scope)
        or evidence.get("revision") != event.revision
        or evidence.get("result_kind") != event.result_kind
        or evidence.get("branch") != branch
        or evidence.get("pr_number") != pr_number
        or evidence.get("reviewed_revision") != review.revision
        or evidence.get("review_comment_id") != review.comment_id
    ):
        return False
    digest = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    body = cast(str, formal[0]["body"])
    if [line for line in body.splitlines() if line.startswith("Evidence:")] != [
        f"Evidence: native-delivery:{digest}"
    ]:
        return False
    marker_id = _positive_int(evidence.get("marker_request_comment_id"))
    marker_records = [item for item in decisions if item.request_comment_id == marker_id]
    marker_revision = evidence.get("marker_revision")
    marker_blob = evidence.get("marker_blob")
    current_task_blob = evidence.get("current_task_blob", marker_blob)
    if (
        marker_id is None
        or len(marker_records) != 1
        or not isinstance(marker_revision, str)
        or _SHA.fullmatch(marker_revision) is None
        or not isinstance(marker_blob, str)
        or _SHA.fullmatch(marker_blob) is None
        or not isinstance(current_task_blob, str)
        or _SHA.fullmatch(current_task_blob) is None
    ):
        return False
    marker = marker_records[0]
    if (
        marker.disposition != "ACCEPTED"
        or marker.change != record.change
        or _accepted_decision_sha256(marker, comments)
        != evidence.get("marker_accepted_decision_sha256")
        or _authorization_ancestry(
            repository,
            token,
            authorization_revision=marker_revision,
            current_revision=event.revision,
            read=read,
        )
        is None
    ):
        return False
    physical = _qualified_physical_original_accepted_effects(
        record=marker, source=source, repository=repository, token=token, read=read
    )
    if physical is None or not _implementation_development_save(physical):
        return False
    if _implementation_development_save(physical, include_task_markers=False):
        return False
    request = find_materialization_payload(json.loads(physical.effects[0].payload_json), source)
    if request is None or request.branch != branch or request.pr_number != pr_number:
        return False
    file = request.files[0]
    quality = evidence.get("quality")
    strict = evidence.get("strict")
    if (
        not isinstance(quality, Mapping)
        or quality.get("revision") != event.revision
        or quality.get("branch") != branch
        or not isinstance(strict, list)
        or not strict
    ):
        return False
    attempts = quality.get("attempts")
    if (
        not isinstance(attempts, list)
        or not attempts
        or any(
            not isinstance(attempt, Mapping)
            or attempt.get("outcome") != "PASS"
            or attempt.get("checkout_revision") != event.revision
            for attempt in attempts
        )
        or any(
            not isinstance(reference, list)
            or len(reference) != 3
            or any(_positive_int(value) is None for value in reference)
            for reference in strict
        )
    ):
        return False
    quality_id = _positive_int(quality.get("request_comment_id"))
    quality_records = [item for item in decisions if item.request_comment_id == quality_id]
    if (
        quality_id is None
        or len(quality_records) != 1
        or quality_records[0].disposition != "ACCEPTED"
        or (quality_records[0].issue_number, quality_records[0].role, quality_records[0].action)
        != (source.issue_number, source.role, source.action)
        or quality_records[0].change != record.change
        or _accepted_decision_sha256(quality_records[0], comments)
        != quality.get("accepted_decision_sha256")
    ):
        return False
    return (
        file.blob_sha == marker_blob
        and _content_sha_at(repository, token, path=file.path, revision=marker_revision)
        == marker_blob
        and _content_sha_at(repository, token, path=file.path, revision=event.revision)
        == current_task_blob
        and task_checkpoint_is_exact(
            repository,
            token,
            expected_change=record.change,
            base_sha=request.base_sha,
            file=file,
            completed_task_ids=scope,
        )
    )


def _ordinary_implementation_scope(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    frontier: CurrentFrontier,
    comments: tuple[Mapping[str, object], ...],
    lifecycle: tuple[Mapping[str, object], ...],
    slices: tuple[tuple[tuple[str, bool], ...], ...],
    branch: str,
    pr_number: int,
    revision: str,
    current_revision: str,
    read: GitHubReader,
) -> tuple[FormalLifecycleEvent, int] | None:
    """Derive the first undelivered slice from the qualified formal history."""
    event = frontier.event
    if not isinstance(event, FormalLifecycleEvent) or not event.valid:
        return None
    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=frontier.change,
        state="open",
        current_routing=frontier.current_routing,
        comments=comments,
        current_revision=current_revision,
        lifecycle_events=lifecycle,
    )
    if not qualification.events or qualification.events[-1] != event:
        return None
    deliveries: list[FormalLifecycleEvent] = []
    review = None
    for item in reversed(qualification.events):
        if (
            not item.valid
            or item.issue_number != source.issue_number
            or item.change != frontier.change
        ):
            return None
        identity = (item.role, item.action, item.result_kind)
        if identity == ("reviewer", "review-openspec", "pass"):
            review = item
            break
        if identity == ("executor", "implement-change", "more-implementation-required"):
            deliveries.append(item)
            continue
        # The canonical frontier has already qualified these transitions.
        # A question, its resolution, or a blocked iteration can return to
        # implementation without delivering another slice. Preserve the
        # earlier scope and still require the reviewed plan to apply at HEAD.
        iteration_routes = {("executor", "implement-change"), ("lead", "resolve-question")}
        if (item.role, item.action) in iteration_routes and item.successor in iteration_routes:
            continue
        return None
    if (
        review is None
        or review.revision is None
        or len(deliveries) >= len(slices)
        or not openspec_review_revision_applies(
            repository,
            token,
            change=frontier.change,
            reviewed_revision=review.revision,
            head_revision=revision,
        )
    ):
        return None
    for group, delivery in zip(slices, reversed(deliveries), strict=False):
        if not all(checked for _, checked in group) or not _bound_native_delivery_scope(
            repository,
            token,
            source=source,
            frontier=frontier,
            event=delivery,
            review=review,
            scope=tuple(task_id for task_id, _ in group),
            comments=comments,
            branch=branch,
            pr_number=pr_number,
            revision=revision,
            current_revision=current_revision,
            read=read,
        ):
            return None
    return review, len(deliveries)


def _reviewed_correction_marker(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    frontier: CurrentFrontier,
    comments: tuple[Mapping[str, object], ...],
    lifecycle: tuple[Mapping[str, object], ...],
    slices: tuple[tuple[tuple[str, bool], ...], ...],
    branch: str | None,
    revision: str,
    current_revision: str,
    read: GitHubReader,
) -> (
    tuple[
        FormalLifecycleEvent,
        ApplicationDecisionRecord,
        MaterializationRequest,
        dict[str, object],
        Mapping[str, object],
        Mapping[str, object],
        str,
        Mapping[str, object],
    ]
    | None
):
    """Reuse the first affected approved group's delivered marker."""
    finding = frontier.event
    if (
        not slices
        or not all(checked for group in slices for _, checked in group)
        or not isinstance(finding, FormalLifecycleEvent)
        or not finding.valid
        or (finding.role, finding.action, finding.result_kind)
        != ("reviewer", "review-implementation", "findings")
        or finding.revision is None
        or finding.default_branch_revision is None
    ):
        return None
    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=frontier.change,
        state="open",
        current_routing=frontier.current_routing,
        comments=comments,
        current_revision=current_revision,
        lifecycle_events=lifecycle,
    )
    events = qualification.events
    if len(events) < 3 or events[-1] != finding:
        return None
    delivered = events[-2]
    if (
        not delivered.valid
        or (delivered.role, delivered.action, delivered.result_kind)
        != ("executor", "implement-change", "ready")
        or delivered.revision != finding.revision
    ):
        return None
    review = next(
        (
            event
            for event in reversed(events[:-2])
            if (event.role, event.action, event.result_kind)
            == ("reviewer", "review-openspec", "pass")
        ),
        None,
    )
    if (
        review is None
        or not review.valid
        or review.revision is None
        or not openspec_review_revision_applies(
            repository,
            token,
            change=frontier.change,
            reviewed_revision=review.revision,
            head_revision=revision,
        )
    ):
        return None
    decisions = _application_decisions(comments)
    finding_owners = _frontier_application_decisions(decisions, frontier)
    if len(finding_owners) != 1:
        return None
    finding_record = finding_owners[0]
    reviewer = WorkerRequest(source.issue_number, "reviewer", "review-implementation")
    finding_digest = _accepted_decision_sha256(finding_record, comments)
    if (
        finding_record.disposition != "ACCEPTED"
        or sum(item.request_comment_id == finding_record.request_comment_id for item in decisions)
        != 1
        or finding_digest is None
        or finding.application_correlation is None
        or _authorization_ancestry(
            repository,
            token,
            authorization_revision=finding_record.authorization_revision,
            current_revision=current_revision,
            read=read,
        )
        is None
    ):
        return None
    original = _qualified_physical_original_accepted_effects(
        record=finding_record, source=reviewer, repository=repository, token=token, read=read
    )
    if original is None or original.effects:
        return None
    projection = json.loads(
        _application_owned_worker_result(
            finding_record.raw_worker_result,
            source=reviewer,
            change=frontier.change,
            current_revision=finding.default_branch_revision,
            result_revision=finding.revision,
            request_comment_id=finding_record.request_comment_id,
        )
    )
    formal = [
        comment
        for comment in comments
        if comment.get("id") == finding.comment_id
        and parse_formal_result(comment, current_revision=current_revision) == finding
    ]
    if len(formal) != 1 or not isinstance(formal[0].get("body"), str):
        return None
    expected_body = projection.get("result_content")
    if not isinstance(expected_body, str):
        return None
    expected_evidence = [
        line for line in expected_body.splitlines() if line.startswith("Evidence:")
    ]
    observed_evidence = [
        line for line in cast(str, formal[0]["body"]).splitlines() if line.startswith("Evidence:")
    ]
    if len(expected_evidence) != 1 or observed_evidence != expected_evidence:
        return None
    # The immutable accepted finding, already matched to its original
    # request, owns the structured scope. Prose is evidence, never selection.
    finding_worker = _application_worker_for_record(finding_record, reviewer)
    if finding_worker is None or finding_worker.reviewed_task_ids is None:
        return None
    affected_indices: set[int] = set()
    for affected_task in finding_worker.reviewed_task_ids:
        matches = [
            index
            for index, group in enumerate(slices)
            if any(task_id == affected_task for task_id, _ in group)
        ]
        if len(matches) != 1:
            return None
        affected_indices.add(matches[0])
    if not affected_indices:
        return None
    selected_index = min(affected_indices)
    expected_kind = "more-implementation-required" if len(affected_indices) > 1 else "ready"
    finding_binding = {
        "finding_application_correlation": finding.application_correlation,
        "finding_accepted_decision_sha256": finding_digest,
        "finding_revision": finding.revision,
    }
    # The reviewed task plan and all later markers must survive correction.
    path = f"openspec/changes/{frontier.change}/tasks.md"
    current_blob = _content_sha_at(repository, token, path=path, revision=revision)
    if current_blob is None or current_blob != _content_sha_at(
        repository, token, path=path, revision=finding.revision
    ):
        return None
    owners = _frontier_application_decisions(decisions, replace(frontier, event=delivered))
    if len(owners) != 1:
        return None
    document = json.loads(owners[0].raw_worker_result)
    evidence = (
        document.get("_native_implementation_delivery") if isinstance(document, dict) else None
    )
    if not isinstance(evidence, Mapping):
        return None
    latest_delivery = evidence
    pr_number = _positive_int(evidence.get("pr_number"))
    delivery_branch = evidence.get("branch")
    if not isinstance(delivery_branch, str) or (branch is not None and branch != delivery_branch):
        return None
    branch = delivery_branch
    if pr_number is None:
        return None
    deliveries = [
        event
        for event in events[events.index(review) + 1 : -1]
        if (event.role, event.action) == ("executor", "implement-change")
        and event.result_kind in ("ready", "more-implementation-required")
    ]
    if len(deliveries) < len(slices) or deliveries[-1] != delivered:
        return None
    original_evidence: list[Mapping[str, object] | None] = []
    for occurrence, delivery_event in enumerate(deliveries):
        owners = _frontier_application_decisions(decisions, replace(frontier, event=delivery_event))
        if len(owners) != 1:
            return None
        raw = json.loads(owners[0].raw_worker_result)
        occurrence_evidence = (
            raw.get("_native_implementation_delivery") if isinstance(raw, dict) else None
        )
        if occurrence < len(slices):
            scope_index = occurrence
            expected_kind = (
                "ready" if occurrence == len(slices) - 1 else "more-implementation-required"
            )
        else:
            # Subsequent READY occurrences are reviewed corrections, not new
            # positions in the original delivery sequence.
            if not isinstance(occurrence_evidence, Mapping):
                return None
            matching = [
                index
                for index, group in enumerate(slices)
                if [task_id for task_id, _ in group] == occurrence_evidence.get("scope_task_ids")
            ]
            if len(matching) != 1:
                return None
            scope_index = matching[0]
            original_scope = original_evidence[scope_index]
            if original_scope is None or any(
                occurrence_evidence.get(key) != original_scope.get(key)
                for key in (
                    "marker_request_comment_id",
                    "marker_accepted_decision_sha256",
                    "marker_revision",
                    "marker_blob",
                )
            ):
                return None
            expected_kind = "ready"
        if delivery_event.result_kind != expected_kind or not _bound_native_delivery_scope(
            repository,
            token,
            source=source,
            frontier=frontier,
            event=delivery_event,
            review=review,
            scope=tuple(task_id for task_id, _ in slices[scope_index]),
            comments=comments,
            branch=branch,
            pr_number=pr_number,
            revision=revision,
            current_revision=current_revision,
            read=read,
        ):
            return None
        if occurrence < len(slices):
            original_evidence.append(
                occurrence_evidence if isinstance(occurrence_evidence, Mapping) else None
            )
    if any(original_evidence[index] is None for index in affected_indices):
        return None
    evidence = original_evidence[selected_index]
    if evidence is None:
        return None
    marker_id = _positive_int(evidence.get("marker_request_comment_id"))
    markers = [item for item in decisions if item.request_comment_id == marker_id]
    if len(markers) != 1:
        return None
    marker = markers[0]
    physical = _qualified_physical_original_accepted_effects(
        record=marker, source=source, repository=repository, token=token, read=read
    )
    if physical is None or not _implementation_development_save(physical):
        return None
    payload = json.loads(physical.effects[0].payload_json)
    request = find_materialization_payload(payload, source)
    if request is None:
        return None
    return (
        review,
        marker,
        request,
        payload,
        evidence,
        latest_delivery,
        expected_kind,
        finding_binding,
    )


def qualify_initial_marker_save(
    repository: str,
    token: str,
    *,
    request: MaterializationRequest,
    source: WorkerRequest,
    request_comment_id: int,
    current_revision: str,
    default_branch: str,
    read: GitHubReader = _github_json,
) -> bool:
    """Qualify the first undelivered scope without a checkpoint publication."""
    if (
        request.pr_number is None
        or len(request.files) != 1
        or request.files[0].path != f"openspec/changes/{request.change}/tasks.md"
        or request.files[0].expected_sha is None
        or request.files[0].expected_sha == request.files[0].blob_sha
    ):
        return False
    try:
        receipt = qualify_development_dispatch_source(
            repository,
            token,
            source=source,
            request_comment_id=request_comment_id,
            current_revision=current_revision,
            default_branch=default_branch,
            read=read,
        )
        ingress = read(repository, token, f"issues/comments/{request_comment_id}")
        prefix = github_repository_api_url(repository, "issues/")
        url = ingress.get("issue_url") if isinstance(ingress, Mapping) else None
        if receipt is None or not isinstance(url, str) or not url.startswith(prefix):
            return False
        shard = _positive_int_string(url.removeprefix(prefix))
        if shard is None:
            return False
        completion = qualify_application_completion(
            repository,
            token,
            source=source,
            current_revision=current_revision,
            read=read,
            current_dispatch_request_comment_id=receipt.dispatch_request_comment_id,
            current_dispatch_issue_number=shard,
            phase_a_request_comment_id=request_comment_id,
        )
        obligation = completion.settled_quality_obligation
        if (
            obligation is None
            or obligation.revision != request.base_sha
            or obligation.carrier_revision != request.base_sha
            or obligation.branch != request.branch
            or obligation.default_branch != default_branch
            or completion.quality_observation is None
            or completion.quality_observation.outcome != "PASS"
            or development_predecessor_evidence(completion, current_revision) is None
        ):
            return False
        carrier = qualify_implementation_carrier(
            repository=repository,
            token=token,
            source=source,
            change=request.change,
            pr_number=request.pr_number,
            current_revision=current_revision,
            read=read,
        )
        if (
            carrier.disposition != "QUALIFIED"
            or carrier.branch != request.branch
            or carrier.head_sha != request.base_sha
        ):
            return False
        issue = read(repository, token, f"issues/{source.issue_number}")
        if not isinstance(issue, Mapping):
            return False
        comments = _paged_list(
            repository, token, f"issues/{source.issue_number}/comments", read=read
        )
        lifecycle = _paged_list(
            repository, token, f"issues/{source.issue_number}/timeline", read=read
        )
        frontier, qualified = _derive_frontier(
            repository=repository,
            token=token,
            source=source,
            current_issue=issue,
            issue_comments=comments,
            lifecycle_events=lifecycle,
            current_revision=current_revision,
            read=read,
        )
        if not qualified or frontier is None or frontier.change != request.change:
            return False
        file = request.files[0]
        content = _content_text_at(repository, token, path=file.path, revision=request.base_sha)
        slices = _task_slices(content)
        if slices is None:
            return False
        scoped = _ordinary_implementation_scope(
            repository,
            token,
            source=source,
            frontier=frontier,
            comments=comments,
            lifecycle=lifecycle,
            slices=slices,
            branch=request.branch,
            pr_number=request.pr_number,
            revision=request.base_sha,
            current_revision=current_revision,
            read=read,
        )
        if scoped is None:
            return False
        _, index = scoped
        if any(checked for group in slices[index:] for _, checked in group):
            return False
        return task_checkpoint_is_exact(
            repository,
            token,
            expected_change=request.change,
            base_sha=request.base_sha,
            file=file,
            completed_task_ids=tuple(task_id for task_id, _ in slices[index]),
        ) and bool(
            _native_strict_marker_evidence(
                repository,
                token,
                revision=request.base_sha,
                branch=request.branch,
                current_revision=current_revision,
                read=read,
            )
        )
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _observe_same_head_correction_quality(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    frontier: CurrentFrontier,
    comments: tuple[Mapping[str, object], ...],
    historical_delivery: Mapping[str, object],
    marker: MaterializationRequest,
    revision: str,
    current_revision: str,
    default_branch: str,
    receipt: DevelopmentDispatchSource,
    read: GitHubReader,
) -> ApplicationCompletion | None:
    """Reobserve the original physical witness, not a new current-occurrence write."""
    finding = frontier.event
    if (
        not isinstance(finding, FormalLifecycleEvent)
        or finding.revision != revision
        or historical_delivery.get("revision") != revision
        or marker.pr_number is None
    ):
        return None
    carrier = qualify_implementation_carrier(
        repository=repository,
        token=token,
        source=source,
        change=frontier.change,
        pr_number=marker.pr_number,
        current_revision=current_revision,
        read=read,
    )
    if (
        carrier.disposition != "QUALIFIED"
        or carrier.branch != marker.branch
        or carrier.head_sha != revision
    ):
        return None
    historical_quality = historical_delivery.get("quality")
    if not isinstance(historical_quality, Mapping):
        return None
    quality_id = _positive_int(historical_quality.get("request_comment_id"))
    records = [
        record
        for record in _application_decisions(comments)
        if record.request_comment_id == quality_id
    ]
    if len(records) != 1:
        return None
    record = records[0]
    digest = _accepted_decision_sha256(record, comments)
    if digest is None or digest != historical_quality.get("accepted_decision_sha256"):
        return None
    observed = _application_job(
        repository,
        token,
        record.request_comment_id,
        read=read,
        record=record,
        accepted_decision_sha256=digest,
        current_revision=current_revision,
        issue_comments=comments,
    )
    obligation = observed.quality_obligation
    if (
        observed.state != "RESUMABLE"
        or obligation is None
        or obligation.revision != revision
        or obligation.carrier_revision != revision
        or obligation.branch != marker.branch
        or obligation.default_branch != default_branch
    ):
        return None
    return _current_development_completion(
        repository,
        token,
        source=source,
        record=record,
        completion=observed,
        current_revision=current_revision,
        dispatch_request_id=receipt.dispatch_request_comment_id,
        phase_a=True,
        accepted_decision_sha256=digest,
        read=read,
    )


def qualify_initial_implementation_delivery(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    change: str,
    revision: str,
    result_kind: str,
    request_comment_id: int,
    current_revision: str,
    default_branch: str,
    read: GitHubReader = _github_json,
) -> dict[str, object] | None:
    """Derive ordinary delivery from the qualified scope and exact native gates."""
    try:
        receipt = qualify_development_dispatch_source(
            repository,
            token,
            source=source,
            request_comment_id=request_comment_id,
            current_revision=current_revision,
            default_branch=default_branch,
            read=read,
        )
        ingress = read(repository, token, f"issues/comments/{request_comment_id}")
        prefix = github_repository_api_url(repository, "issues/")
        url = ingress.get("issue_url") if isinstance(ingress, Mapping) else None
        if receipt is None or not isinstance(url, str) or not url.startswith(prefix):
            return None
        shard = _positive_int_string(url.removeprefix(prefix))
        if shard is None:
            return None
        completion = qualify_application_completion(
            repository,
            token,
            source=source,
            current_revision=current_revision,
            read=read,
            current_dispatch_request_comment_id=receipt.dispatch_request_comment_id,
            current_dispatch_issue_number=shard,
            phase_a_request_comment_id=request_comment_id,
        )
        evidence_only = completion.state in ("NONE", "REJECTED")
        obligation = completion.settled_quality_obligation
        if evidence_only:
            if (
                completion.accepted_record is not None
                or completion.quality_obligation is not None
                or obligation is not None
                or completion.settled_development_records
            ):
                return None
        elif obligation is None or not completion.settled_development_records:
            return None
        issue = read(repository, token, f"issues/{source.issue_number}")
        if not isinstance(issue, Mapping):
            return None
        comments = _paged_list(
            repository, token, f"issues/{source.issue_number}/comments", read=read
        )
        lifecycle = _paged_list(
            repository, token, f"issues/{source.issue_number}/timeline", read=read
        )
        frontier, qualified = _derive_frontier(
            repository=repository,
            token=token,
            source=source,
            current_issue=issue,
            issue_comments=comments,
            lifecycle_events=lifecycle,
            current_revision=current_revision,
            read=read,
        )
        if not qualified or frontier is None or frontier.change != change:
            return None
        path = f"openspec/changes/{change}/tasks.md"
        content = _content_text_at(repository, token, path=path, revision=revision)
        slices = _task_slices(content)
        if slices is None:
            return None
        markers: list[tuple[ApplicationDecisionRecord, MaterializationRequest, dict[str, object]]]
        markers = []
        for record in completion.settled_development_records:
            if record.change != change:
                return None
            batch = parse_effect_batch(record.raw_worker_result, source, authorized_change=change)
            if not _implementation_development_save(batch):
                return None
            if _implementation_development_save(batch, include_task_markers=False):
                continue
            payload = json.loads(batch.effects[0].payload_json)
            request = find_materialization_payload(payload, source)
            if request is None:
                return None
            markers.append((record, request, payload))
        reviewed_correction = not markers
        expected_kind = "ready"
        finding_binding: Mapping[str, object] = {}
        if not markers:
            correction = _reviewed_correction_marker(
                repository,
                token,
                source=source,
                frontier=frontier,
                comments=comments,
                lifecycle=lifecycle,
                slices=slices,
                branch=obligation.branch if obligation is not None else None,
                revision=revision,
                current_revision=current_revision,
                read=read,
            )
            if correction is None:
                return None
            (
                event,
                record,
                marker,
                payload,
                historical,
                latest_delivery,
                expected_kind,
                finding_binding,
            ) = correction
            if evidence_only:
                observed = _observe_same_head_correction_quality(
                    repository,
                    token,
                    source=source,
                    frontier=frontier,
                    comments=comments,
                    historical_delivery=latest_delivery,
                    marker=marker,
                    revision=revision,
                    current_revision=current_revision,
                    default_branch=default_branch,
                    receipt=receipt,
                    read=read,
                )
                if observed is None:
                    return None
                completion = observed
                obligation = completion.settled_quality_obligation
            matching_indices = [
                i
                for i, group in enumerate(slices)
                if [task_id for task_id, _ in group] == historical.get("scope_task_ids")
            ]
            if len(matching_indices) != 1:
                return None
            index = matching_indices[0]
        elif len(markers) == 1:
            record, marker, payload = markers[0]
            if marker.pr_number is None:
                return None
            scoped = _ordinary_implementation_scope(
                repository,
                token,
                source=source,
                frontier=frontier,
                comments=comments,
                lifecycle=lifecycle,
                slices=slices,
                branch=marker.branch,
                pr_number=marker.pr_number,
                revision=revision,
                current_revision=current_revision,
                read=read,
            )
            if scoped is None:
                return None
            event, index = scoped
            expected_kind = "ready" if index == len(slices) - 1 else "more-implementation-required"
        else:
            return None
        quality = development_predecessor_evidence(completion, current_revision)
        if (
            obligation is None
            or obligation.revision != revision
            or obligation.carrier_revision != revision
            or obligation.default_branch != default_branch
            or completion.quality_observation is None
            or completion.quality_observation.outcome != "PASS"
            or quality is None
            or marker.pr_number is None
            or marker.branch != obligation.branch
        ):
            return None
        if (
            not all(checked for _, checked in slices[index])
            or (
                not reviewed_correction
                and any(checked for group in slices[index + 1 :] for _, checked in group)
            )
            or result_kind != expected_kind
        ):
            return None
        scope = tuple(task_id for task_id, _ in slices[index])
        file = marker.files[0]
        digest = _accepted_decision_sha256(record, comments)
        current_task_blob = _content_sha_at(repository, token, path=path, revision=revision)
        if (
            digest is None
            or file.expected_sha == file.blob_sha
            or current_task_blob is None
            or (not reviewed_correction and current_task_blob != file.blob_sha)
            or not task_checkpoint_is_exact(
                repository,
                token,
                expected_change=change,
                base_sha=marker.base_sha,
                file=file,
                completed_task_ids=scope,
            )
        ):
            return None
        proof = prove_materialization(
            payload,
            source,
            repository=repository,
            token=token,
            current_revision=current_revision,
            default_branch=default_branch,
            accepted_authorization_revision=record.authorization_revision,
            accepted_intent=True,
        )
        if (
            proof.disposition != "COMPLETE"
            or proof.target is None
            or proof.witness is None
            or proof.target.revision != revision
            or proof.target.branch != marker.branch
            or proof.witness.desired_blobs != ((path, file.blob_sha),)
        ):
            return None
        strict = _native_strict_marker_evidence(
            repository,
            token,
            revision=revision,
            branch=marker.branch,
            current_revision=current_revision,
            read=read,
        )
        if not strict:
            return None
        return {
            **finding_binding,
            "scope_task_ids": list(scope),
            "revision": revision,
            "pr_number": marker.pr_number,
            "branch": marker.branch,
            "reviewed_revision": event.revision,
            "review_comment_id": event.comment_id,
            "marker_request_comment_id": record.request_comment_id,
            "marker_accepted_decision_sha256": digest,
            "marker_revision": proof.witness.revision,
            "marker_blob": file.blob_sha,
            **(
                {"current_task_blob": current_task_blob}
                if current_task_blob != file.blob_sha
                else {}
            ),
            "quality": quality,
            "strict": [list(attempt) for attempt in strict],
            "dispatch": asdict(receipt),
            "result_kind": result_kind,
        }
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _historical_development_verdict(
    repository: str,
    token: str,
    *,
    obligation: NativeQualityObligation,
    evidence: Mapping[str, object],
    boundary: datetime,
    read: GitHubReader,
) -> bool:
    """Requalify the exact terminal attempts actually used, not the latest verdict."""
    references = evidence.get("attempts")
    blob = evidence.get("workflow_blob")
    gate = evidence.get("obligation_id")
    authorization = evidence.get("authorization_revision")
    if (
        not isinstance(references, list)
        or not references
        or not isinstance(blob, str)
        or not isinstance(gate, str)
        or not isinstance(authorization, str)
    ):
        return False
    target_blob = _quality_workflow_blob(repository, token, obligation.revision, read=read)
    if target_blob is None:
        return False
    attempts: list[NativeQualityAttempt] = []
    ordinary: list[NativeQualityAttempt] = []
    called: list[NativeQualityAttempt] = []
    for reference in references:
        if not isinstance(reference, Mapping):
            return False
        run_id = _positive_int(reference.get("run_id"))
        number = _positive_int(reference.get("run_attempt"))
        if (
            run_id is None
            or number is None
            or reference.get("checkout_revision") != obligation.revision
        ):
            return False
        run = read(repository, token, f"actions/runs/{run_id}/attempts/{number}")
        if not isinstance(run, Mapping):
            return False
        source_id = reference.get("source_comment_id")
        if source_id is None:
            event = run.get("event")
            if not isinstance(event, str) or event not in ("push", "pull_request"):
                return False
            attempt = read_native_quality_attempt(
                repository,
                token,
                revision=obligation.revision,
                branch=obligation.branch,
                workflow_blob=target_blob,
                run_id=run_id,
                run_attempt=number,
                event=event,
                read=read,
                log_read=_github_job_log,
            )
            ordinary.append(attempt)
        else:
            source_number = _positive_int(source_id)
            if source_number is None:
                return False
            row = _quality_bridge_run(run, repository, obligation.default_branch, source_number)
            comment = read(repository, token, f"issues/comments/{source_number}")
            requested = _quality_time(
                comment.get("created_at") if isinstance(comment, Mapping) else None
            )
            created = _quality_time(run.get("created_at"))
            accepted = _quality_time(obligation.accepted_at)
            if (
                row is None
                or row[:2] != (run_id, number)
                or not isinstance(comment, Mapping)
                or comment.get("id") != source_number
                or not _trusted_connector_comment(comment, repository.split("/", 1)[0])
                or comment.get("updated_at") != comment.get("created_at")
                or not isinstance(comment.get("body"), str)
                or parse_dispatch_request(cast(str, comment["body"])) is None
                or requested is None
                or created is None
                or accepted is None
                or not accepted < requested <= created
                or _authorization_ancestry(
                    repository,
                    token,
                    authorization_revision=row[2],
                    current_revision=authorization,
                    read=read,
                )
                is None
            ):
                return False
            attempt = _quality_bridge_attempt(
                repository,
                token,
                source=source_number,
                row=row,
                obligation_id=gate,
                revision=obligation.revision,
                workflow_blob=blob,
                read=read,
                log_read=_github_job_log,
            )
            called.append(attempt)
        if asdict(attempt) != reference or attempt.outcome not in (
            "PASS",
            "STATIC_STEP_FAILURE",
            "PYTEST_STEP_FAILURE",
        ):
            return False
        attempts.append(attempt)
    combined = tuple(attempts)
    outcome = reduce_native_quality_attempts(combined)
    if outcome not in ("PASS", "FAIL", "CONFLICT"):
        return False
    if outcome == "PASS" and target_blob != blob and (not ordinary or not called):
        return False
    return _quality_verdicts_precede(
        repository,
        token,
        attempts=combined,
        boundary=boundary,
        accepted_at=obligation.accepted_at,
        read=read,
    )


def _native_delivery_never_called(
    record: ApplicationDecisionRecord,
    completion: ApplicationCompletion,
    digest: str,
) -> bool:
    """Qualify the existing first-Formal no-call proof, not a gate verdict."""
    proof = completion.accepted_proof
    artifact = completion.recovery_artifact
    if (
        completion.state != "RESUMABLE"
        or completion.accepted_record != record
        or completion.accepted_decision_sha256 != digest
        or proof is None
        or proof.disposition != "COMPLETE"
        or not isinstance(artifact, ApplicationRecoveryArtifact)
        or artifact.request_comment_id != record.request_comment_id
        or artifact.accepted_decision_sha256 != digest
    ):
        return False
    frontier = proof.pending_frontier_proof
    failure = artifact.document.get("failure_evidence")
    rejection = failure.get("rejection") if isinstance(failure, Mapping) else None
    if (
        frontier is None
        or frontier.disposition != "NOT_APPLIED"
        or frontier.obligation != "FORMAL_RESULT"
        or frontier.remaining_obligation != "FORMAL_RESULT"
        or frontier.frontier_index != 0
        or not isinstance(frontier.witness, CompleteNeverCalledWitness)
        or not isinstance(failure, Mapping)
        or _accepted_recovery_boundary(failure) != "READ_ONLY"
        or failure.get("unfinished_boundary") != "effect-precondition"
        or failure.get("failed_effect_index") != 0
        or not isinstance(rejection, Mapping)
        or rejection.get("expected") != "fresh native implementation delivery gates"
    ):
        return False
    witness = frontier.witness
    return (
        witness.request_comment_id == record.request_comment_id
        and witness.target_index == 0
        and witness.accepted_decision_sha256 == digest
        and bool(witness.artifact_chain)
        and witness.artifact_chain[0]
        == (artifact.run_id, artifact.run_attempt, artifact.artifact_id)
    )


def _settled_development_prefix(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    accepted: list[ApplicationDecisionRecord],
    decision_times: Mapping[int, str | None],
    ingress_times: Mapping[int, str | None],
    issue_comments: tuple[Mapping[str, object], ...],
    accepted_state: Callable[[ApplicationDecisionRecord, WorkerRequest], ApplicationCompletion],
    current_revision: str,
    dispatch_request_id: int | None,
    phase_a: bool,
    current_issue: Mapping[str, object],
    lifecycle_events: tuple[Mapping[str, object], ...],
    read: GitHubReader,
) -> tuple[ApplicationDecisionRecord, ApplicationCompletion] | None:
    """Retire only a fully proven causal prefix of physical saves."""
    if (source.role, source.action) != ("executor", "implement-change"):
        return None
    ordered: list[tuple[datetime, ApplicationDecisionRecord]] = []
    for record in accepted:
        stamp = _quality_time(decision_times.get(record.request_comment_id))
        if stamp is None:
            return None
        ordered.append((stamp, record))
    if len({stamp for stamp, _ in ordered}) != len(ordered):
        return None
    ordered.sort(key=lambda item: item[0])
    prior: tuple[ApplicationDecisionRecord, NativeQualityObligation, str, datetime] | None = None
    prior_completion: ApplicationCompletion | None = None
    settled_records: list[ApplicationDecisionRecord] = []
    retired_publication: tuple[datetime, ApplicationRecoveryArtifact, str] | None = None
    seen_dispatch: set[int] = set()
    seen_revisions: set[str] = set()
    try:
        for index, (stamp, record) in enumerate(ordered):
            completion = accepted_state(record, source)
            obligation = completion.quality_obligation
            publication: Mapping[str, object] | None = None
            digest = _accepted_decision_sha256(record, issue_comments)
            if digest is None or completion.request_comment_id != record.request_comment_id:
                return None
            if obligation is None:
                # The final accepted owner may still have an incomplete or
                # unknown effect. Qualify its exact Original and intended
                # carrier preimage, not an invented completed write.
                if prior is None or completion.state not in ("RESUMABLE", "INVALID"):
                    return None
                original = _qualified_physical_original_accepted_effects(
                    record=record, source=source, repository=repository, token=token, read=read
                )
                if original is None:
                    return None
                default_branch = prior[1].default_branch
                if not original.effects:
                    # A publication-only ACCEPT owns its formal Effect even
                    # while pending or unknown; this is not write permission.
                    document = json.loads(record.raw_worker_result)
                    delivery = document.get("_native_implementation_delivery")
                    if (
                        not isinstance(delivery, Mapping)
                        or delivery.get("revision") != prior[1].revision
                        or delivery.get("branch") != prior[1].branch
                        or delivery.get("result_kind") != record.result_kind
                        or record.result_kind not in ("ready", "more-implementation-required")
                    ):
                        return None
                    marker_id = _positive_int(delivery.get("marker_request_comment_id"))
                    markers = [
                        item for item in settled_records if item.request_comment_id == marker_id
                    ]
                    if not markers:
                        # A reviewed correction may bind a previously delivered
                        # marker without writing it again in this occurrence.
                        frontier, qualified = _derive_frontier(
                            repository=repository,
                            token=token,
                            source=source,
                            current_issue=current_issue,
                            issue_comments=issue_comments,
                            lifecycle_events=lifecycle_events,
                            current_revision=current_revision,
                            read=read,
                        )
                        if not qualified or frontier is None or frontier.change != record.change:
                            return None
                        path = f"openspec/changes/{record.change}/tasks.md"
                        content = _content_text_at(
                            repository, token, path=path, revision=prior[1].revision
                        )
                        slices = _task_slices(content)
                        if slices is None:
                            return None
                        correction = _reviewed_correction_marker(
                            repository,
                            token,
                            source=source,
                            frontier=frontier,
                            comments=issue_comments,
                            lifecycle=lifecycle_events,
                            slices=slices,
                            branch=prior[1].branch,
                            revision=prior[1].revision,
                            current_revision=current_revision,
                            read=read,
                        )
                        if correction is None:
                            return None
                        (
                            _,
                            historical_marker,
                            _,
                            _,
                            historical,
                            _,
                            expected_kind,
                            finding_binding,
                        ) = correction
                        if record.result_kind != expected_kind:
                            return None
                        # A historical single-group READY may predate the binding.
                        # A partial correction always belongs to the original finding.
                        has_binding = any(key in delivery for key in finding_binding)
                        if (has_binding or expected_kind != "ready") and any(
                            delivery.get(key) != value for key, value in finding_binding.items()
                        ):
                            return None
                        if any(
                            delivery.get(key) != historical.get(key)
                            for key in (
                                "scope_task_ids",
                                "pr_number",
                                "branch",
                                "reviewed_revision",
                                "review_comment_id",
                                "marker_request_comment_id",
                                "marker_accepted_decision_sha256",
                                "marker_revision",
                                "marker_blob",
                            )
                        ):
                            return None
                        if delivery.get("current_task_blob", delivery.get("marker_blob")) != (
                            _content_sha_at(
                                repository, token, path=path, revision=prior[1].revision
                            )
                        ):
                            return None
                        markers = [historical_marker]
                    if len(markers) != 1 or _accepted_decision_sha256(
                        markers[0], issue_comments
                    ) != delivery.get("marker_accepted_decision_sha256"):
                        return None
                    publication = delivery
                    carrier_branch = prior[1].branch
                    carrier_base = prior[1].revision
                else:
                    if index != len(ordered) - 1 or not _implementation_development_save(original):
                        return None
                    materialization = find_materialization_payload(
                        json.loads(original.effects[0].payload_json), source
                    )
                    if materialization is None:
                        return None
                    carrier_branch = materialization.branch
                    carrier_base = materialization.base_sha
            else:
                if (
                    completion.state != "RESUMABLE"
                    or _quality_time(obligation.accepted_at) != stamp
                    or obligation.revision in seen_revisions
                ):
                    return None
                carrier_branch = obligation.branch
                carrier_base = obligation.carrier_base
                default_branch = obligation.default_branch
            receipt = _development_acceptance_source(
                repository,
                token,
                source=source,
                record=record,
                default_branch=default_branch,
                read=read,
            )
            ingress = _quality_time(ingress_times.get(record.request_comment_id))
            if receipt is None or receipt.dispatch_request_comment_id in seen_dispatch:
                return None
            if ingress is None or ingress >= stamp:
                return None
            if prior is not None:
                previous, old, previous_digest, previous_stamp = prior
                if (
                    previous.change != record.change
                    or old.branch != carrier_branch
                    or old.default_branch != default_branch
                    or (
                        obligation is not None
                        and old.carrier_revision != obligation.carrier_revision
                    )
                    or carrier_base != old.revision
                ):
                    return None
                boundary = _development_planning_boundary(
                    repository, token, receipt=receipt, read=read
                )
                if boundary is None or not previous_stamp < boundary < ingress:
                    return None
                document = json.loads(record.raw_worker_result)
                evidence = (
                    publication.get("quality")
                    if publication is not None
                    else document.get("_native_development_predecessor")
                )
                if not isinstance(evidence, Mapping):
                    return None
                if publication is not None:
                    attempts = evidence.get("attempts")
                    if (
                        not isinstance(attempts, list)
                        or not attempts
                        or any(
                            not isinstance(attempt, Mapping) or attempt.get("outcome") != "PASS"
                            for attempt in attempts
                        )
                    ):
                        return None
                blob = _quality_workflow_blob(
                    repository, token, record.authorization_revision, read=read
                )
                if (
                    blob is None
                    or _authorization_ancestry(
                        repository,
                        token,
                        authorization_revision=record.authorization_revision,
                        current_revision=current_revision,
                        read=read,
                    )
                    is None
                ):
                    return None
                # The historical producer, not a later main's producer,
                # determines the gate actually used for successor admission.
                gate = old.obligation_id
                if blob != old.workflow_blob:
                    identity = json.dumps(
                        [
                            repository,
                            previous.issue_number,
                            previous.change,
                            previous.request_comment_id,
                            previous_digest,
                            old.revision,
                            old.branch,
                            blob,
                        ],
                        separators=(",", ":"),
                    )
                    gate = hashlib.sha256(identity.encode()).hexdigest()
                expected = {
                    "request_comment_id": previous.request_comment_id,
                    "accepted_decision_sha256": previous_digest,
                    "revision": old.revision,
                    "branch": old.branch,
                    "workflow_blob": blob,
                    "obligation_id": gate,
                    "authorization_revision": record.authorization_revision,
                    "attempts": evidence.get("attempts"),
                }
                if evidence != expected or not _historical_development_verdict(
                    repository,
                    token,
                    obligation=old,
                    evidence=evidence,
                    boundary=boundary,
                    read=read,
                ):
                    return None
                if retired_publication is not None:
                    # A later accepted correction must independently prove the
                    # negative verdict at its own planning boundary. A fresh
                    # verdict today cannot authorize an old successor.
                    retired_at, artifact, retired_authority = retired_publication
                    attempts = evidence.get("attempts")
                    stale_successor = (
                        retired_authority != record.authorization_revision
                        and _authorization_ancestry(
                            repository,
                            token,
                            authorization_revision=retired_authority,
                            current_revision=record.authorization_revision,
                            read=read,
                        )
                        is not None
                    )
                    job = read(repository, token, f"actions/jobs/{artifact.job_id}")
                    completed = (
                        _quality_time(job.get("completed_at")) if isinstance(job, Mapping) else None
                    )
                    if (
                        not isinstance(attempts, list)
                        or (publication is not None and not stale_successor)
                        or (
                            not stale_successor
                            and not any(
                                isinstance(attempt, Mapping)
                                and attempt.get("outcome")
                                in ("STATIC_STEP_FAILURE", "PYTEST_STEP_FAILURE")
                                for attempt in attempts
                            )
                        )
                        or not isinstance(job, Mapping)
                        or job.get("id") != artifact.job_id
                        or job.get("run_id") != artifact.run_id
                        or job.get("run_attempt") != artifact.run_attempt
                        or job.get("status") != "completed"
                        or job.get("conclusion") != "failure"
                        or completed is None
                        or not retired_at < completed < boundary
                    ):
                        return None
                    retired_publication = None
                if publication is not None and index != len(ordered) - 1:
                    candidate_artifact = completion.recovery_artifact
                    if not (
                        isinstance(candidate_artifact, ApplicationRecoveryArtifact)
                        and _native_delivery_never_called(record, completion, digest)
                    ):
                        return None
                    # Preserve the immutable ACCEPT as history, without
                    # attributing either a save or a formal consequence to it.
                    retired_publication = stamp, candidate_artifact, record.authorization_revision
                    seen_dispatch.add(receipt.dispatch_request_comment_id)
                    continue
                if (
                    publication is not None
                    and prior_completion is not None
                    and _native_delivery_never_called(record, completion, digest)
                ):
                    settled = _current_development_completion(
                        repository,
                        token,
                        source=source,
                        record=previous,
                        completion=replace(
                            prior_completion,
                            settled_development_records=tuple(settled_records),
                        ),
                        current_revision=current_revision,
                        dispatch_request_id=dispatch_request_id,
                        phase_a=phase_a,
                        accepted_decision_sha256=previous_digest,
                        read=read,
                    )
                    observation = settled.quality_observation
                    stale_authority = record.authorization_revision != current_revision
                    if (
                        settled.state == "COMPLETE"
                        and observation is not None
                        and (
                            observation.outcome in ("FAIL", "CONFLICT")
                            or (stale_authority and observation.outcome == "PASS")
                        )
                    ):
                        pr_number = _positive_int(publication.get("pr_number"))
                        if pr_number is None:
                            return None
                        carrier = qualify_implementation_carrier(
                            repository=repository,
                            token=token,
                            source=source,
                            change=record.change,
                            pr_number=pr_number,
                            current_revision=current_revision,
                            read=read,
                        )
                        ref = read(
                            repository, token, f"git/ref/heads/{quote(default_branch, safe='/')}"
                        )
                        obj = ref.get("object") if isinstance(ref, Mapping) else None
                        if (
                            isinstance(obj, Mapping)
                            and obj.get("sha") == current_revision
                            and carrier.disposition == "QUALIFIED"
                            and carrier.branch == old.branch
                            and carrier.head_sha == old.revision
                            and read(repository, token, f"issues/{source.issue_number}")
                            == current_issue
                            and _paged_list(
                                repository,
                                token,
                                f"issues/{source.issue_number}/comments?sort=created&direction=asc",
                                read=read,
                            )
                            == issue_comments
                            and _paged_list(
                                repository,
                                token,
                                f"issues/{source.issue_number}/timeline",
                                read=read,
                            )
                            == lifecycle_events
                        ):
                            return previous, settled
                    if (
                        settled.state != "COMPLETE"
                        or observation is None
                        or observation.outcome != "PASS"
                        or stale_authority
                    ):
                        return record, replace(
                            completion, reason="application-completion-read-only-observing"
                        )
            if obligation is None:
                return record, completion
            seen_dispatch.add(receipt.dispatch_request_comment_id)
            seen_revisions.add(obligation.revision)
            prior = record, obligation, digest, stamp
            prior_completion = completion
            settled_records.append(record)
        if (
            retired_publication is not None
            or prior is None
            or prior[1].revision != prior[1].carrier_revision
        ):
            return None
        return record, replace(
            completion,
            settled_development_records=tuple(settled_records),
        )
    except (OSError, RuntimeError, TypeError, ValueError, LookupError):
        return None


def _current_development_completion(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    record: ApplicationDecisionRecord,
    completion: ApplicationCompletion,
    current_revision: str,
    dispatch_request_id: int | None,
    phase_a: bool,
    accepted_decision_sha256: str | None,
    read: GitHubReader,
) -> ApplicationCompletion:
    """Re-observe a saved W's own verdict at the shared authorization boundary."""
    obligation = completion.quality_obligation
    if (
        obligation is None
        or obligation.carrier_revision != obligation.revision
        or dispatch_request_id is None
    ):
        return completion
    unknown = replace(completion, quality_observation=NativeQualityObservation("INDETERMINATE"))
    try:
        original_source = _development_acceptance_source(
            repository,
            token,
            source=source,
            record=record,
            default_branch=obligation.default_branch,
            read=read,
        )
        if (
            original_source is None
            or original_source.dispatch_request_comment_id == dispatch_request_id
            or accepted_decision_sha256 is None
        ):
            return replace(
                unknown,
                state="INVALID",
                reason="application-completion-development-source-invalid",
            )
        runs = _complete_workflow_runs(
            repository, token, _DISPATCH_WORKFLOW, read=read, require_count=True
        )
        if runs is None:
            return unknown
        matching = [
            run
            for run in runs
            if run.get("display_title") == render_dispatch_run_name(dispatch_request_id)
        ]
        if len(matching) != 1:
            return unknown
        run = matching[0]
        row = _quality_bridge_run(run, repository, obligation.default_branch, dispatch_request_id)
        if row is None or row[2] != current_revision:
            return unknown
        run_id, attempt, _, status, conclusion = row
        if phase_a:
            if (status, conclusion) != ("completed", "success"):
                return unknown
        elif status not in _QUALITY_ACTIVE or conclusion is not None:
            return unknown
        jobs = github_complete_job_inventory(
            repository, token, run_id=run_id, run_attempt=attempt, read=read
        )
        if jobs is None:
            return unknown
        planners = [job for job in jobs if job.get("name") == "bridge"]
        if len(planners) != 1:
            return unknown
        planner = planners[0]
        steps = planner.get("steps")
        if (
            planner.get("run_id") != run_id
            or planner.get("run_attempt") != attempt
            or planner.get("head_sha") != current_revision
            or not isinstance(steps, list)
        ):
            return unknown
        planning = [
            step
            for step in steps
            if isinstance(step, Mapping)
            and step.get("name") == "Plan exact correlated machine dispatch decision"
        ]
        if len(planning) != 1:
            return unknown
        boundary = _quality_time(planning[0].get("started_at"))
        started = _quality_time(planner.get("started_at"))
        if boundary is None or started is None or boundary < started:
            return unknown
        observation = plan_native_quality_verification(
            repository,
            token,
            revision=obligation.revision,
            branch=obligation.branch,
            workflow_blob=obligation.workflow_blob,
            obligation_id=obligation.obligation_id,
            accepted_at=obligation.accepted_at,
            current_revision=current_revision,
            default_branch=obligation.default_branch,
            request_comment_id=dispatch_request_id,
            run_id=run_id,
            run_attempt=attempt,
            read=read,
            observe_only=phase_a,
            verdict_before=boundary,
        )
        if observation.outcome not in ("PASS", "FAIL", "CONFLICT"):
            return replace(completion, quality_observation=observation)
        if (
            observation.attempts is None
            or not any(
                item.checkout_revision == obligation.revision
                and item.outcome in ("PASS", "STATIC_STEP_FAILURE", "PYTEST_STEP_FAILURE")
                for item in observation.attempts
            )
            or not _quality_verdicts_precede(
                repository,
                token,
                attempts=observation.attempts,
                boundary=boundary,
                accepted_at=obligation.accepted_at,
                read=read,
            )
        ):
            return unknown
        return replace(
            completion,
            state="COMPLETE",
            reason="application-completion-development-verdict-settled",
            quality_obligation=None,
            quality_observation=observation,
            settled_quality_obligation=obligation,
            settled_development_records=completion.settled_development_records or (record,),
            accepted_record=record,
            accepted_decision_sha256=accepted_decision_sha256,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return unknown


def _application_correlation_fields(correlation: str) -> tuple[str, ...] | None:
    fields = tuple(correlation.split(":"))
    return fields if len(fields) == 8 and fields[0] == "application" else None


def qualify_application_completion(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    current_revision: str,
    read: GitHubReader = _github_json,
    current_dispatch_request_comment_id: int | None = None,
    current_dispatch_issue_number: int | None = None,
    phase_a_request_comment_id: int | None = None,
    now: datetime | None = None,
) -> ApplicationCompletion:
    """Return one exhaustive consequence disposition from durable evidence."""

    current_time = datetime.now(UTC) if now is None else now.astimezone(UTC)
    owner = repository.split("/", 1)[0]
    since = (current_time - timedelta(days=30)).isoformat(timespec="seconds").replace("+00:00", "Z")
    issue_comments = _paged_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created&direction=asc",
        read=read,
    )
    # Recovery lineage can cross midnight and Runtime shards. Keep the global
    # observation window open from the current ACCEPTED intent, even when the
    # intent is older than the ordinary 30-day ingress lookback.
    for comment in issue_comments:
        if not is_github_actions_comment(comment):
            continue
        record = parse_application_decision(comment.get("body"))
        if (
            record is not None
            and record.disposition == "ACCEPTED"
            and (record.issue_number, record.role, record.action)
            == (source.issue_number, source.role, source.action)
        ):
            observed_at = _comment_time(comment)
            if observed_at is not None:
                since = min(since, observed_at)
    recent = _paged_list(
        repository,
        token,
        f"issues/comments?{urlencode({'sort': 'created', 'direction': 'asc', 'since': since})}",
        read=read,
    )
    runtime_comments = recent
    if current_dispatch_request_comment_id is not None:
        runtime_issue_number = _positive_int(current_dispatch_issue_number)
        current_request_id = _positive_int(current_dispatch_request_comment_id)
        if runtime_issue_number is None or current_request_id is None:
            return ApplicationCompletion(
                "INVALID",
                "application-completion-carrier-history-unavailable",
            )
        try:
            runtime_comments = _runtime_shard_comments(
                repository,
                token,
                runtime_shard_issue_number=runtime_issue_number,
                source_issue_number=source.issue_number,
                source_issue_comments=issue_comments,
                read=read,
            )
        except (HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
            return ApplicationCompletion(
                "INVALID",
                "application-completion-carrier-history-unavailable",
            )
        current_request_comments = []
        for comment in runtime_comments:
            body = comment.get("body")
            if (
                _positive_int(comment.get("id")) == current_request_id
                and isinstance(body, str)
                and parse_dispatch_request(body) is not None
            ):
                current_request_comments.append(comment)
        if len(current_request_comments) != 1:
            return ApplicationCompletion(
                "INVALID",
                "application-completion-carrier-history-incomplete",
            )
    decisions = _application_decisions(issue_comments)
    relevant_decisions = [
        record
        for record in decisions
        if record.issue_number == source.issue_number
        and record.role == source.role
        and record.action == source.action
    ]
    candidates: dict[int, _IngressCandidate] = {}
    invalid_request_ids: set[int] = set()
    ingress_created_at: dict[int, str | None] = {}
    unbound_request_ids: set[int] = set()
    # The raw wire deliberately permits omission of the source identity.
    # A machine decision on its actual Issue can identify such a transport as
    # historical/foreign, but only the complete local decision read owns
    # current-source acceptance. Do not recreate an authorization envelope.
    observed_decisions: dict[int, list[tuple[ApplicationDecisionRecord, bool]]] = {}
    conflicting_decision_ids: set[int] = set()
    for comment in recent:
        if not is_github_actions_comment(comment):
            continue
        record = parse_application_decision(comment.get("body"))
        if record is not None:
            observed_decisions.setdefault(record.request_comment_id, []).append(
                (
                    record,
                    _positive_int(comment.get("id")) is not None
                    and comment.get("issue_url")
                    == github_repository_api_url(repository, f"issues/{record.issue_number}"),
                )
            )
    # Phase A has independently qualified its native dispatch source. Exclude
    # only that in-flight ingress, not other live or unqualified transports.
    if phase_a_request_comment_id is not None:
        own_id = _positive_int(phase_a_request_comment_id)
        shard_id = _positive_int(current_dispatch_issue_number)
        own_shard = [item for item in runtime_comments if item.get("id") == own_id]
        own_global = [item for item in recent if item.get("id") == own_id]
        if (
            own_id is None
            or shard_id is None
            or current_dispatch_request_comment_id is None
            or own_id == current_dispatch_request_comment_id
            or len(own_shard) != 1
            or len(own_global) != 1
            or own_id in observed_decisions
            or any(record.request_comment_id == own_id for record in decisions)
        ):
            return ApplicationCompletion("INVALID", "application-completion-phase-a-source-invalid")
        own = read(repository, token, f"issues/comments/{own_id}")
        if (
            not isinstance(own, Mapping)
            or own.get("id") != own_id
            or own.get("issue_url") != github_repository_api_url(repository, f"issues/{shard_id}")
            or own.get("updated_at") != own.get("created_at")
            or _quality_time(own.get("created_at")) is None
            or not isinstance(own.get("body"), str)
            or cast(str, own["body"]).splitlines()[:1]
            not in (["WORKER_RESULT"], ["EFFECT_REQUEST"])
            or not _trusted_connector_comment(own, owner)
            or any(
                not _trusted_connector_comment(item, owner)
                or any(
                    item.get(key) != own.get(key)
                    for key in ("id", "body", "issue_url", "created_at", "updated_at")
                )
                for item in (*own_shard, *own_global)
            )
        ):
            return ApplicationCompletion("INVALID", "application-completion-phase-a-source-invalid")

    for comment in (*recent, *issue_comments):
        if (
            phase_a_request_comment_id is not None
            and comment.get("id") == phase_a_request_comment_id
        ):
            continue
        if not _trusted_connector_comment(comment, owner):
            continue
        body = comment.get("body")
        if not isinstance(body, str):
            continue
        marker = body.splitlines()[:1]
        if marker not in (["EFFECT_REQUEST"], ["WORKER_RESULT"]):
            continue
        comment_id = _positive_int(comment.get("id"))
        if comment_id is None:
            invalid_request_ids.add(-1)
            continue
        ingress_created_at[comment_id] = _comment_time(comment)

        # Normalize physical ingress into the same source filter and reducer.
        # Native raw claims are hints only; the persisted decision (if any)
        # owns source authority. An unbound live transport cannot prove NONE.
        if marker == ["WORKER_RESULT"]:
            request = None
            legacy_source_hint = None
            encoded_source_identity = None
            observed = observed_decisions.get(comment_id, [])
            local = [record for record in decisions if record.request_comment_id == comment_id]
            if observed and (
                len(observed) != 1
                or not observed[0][1]
                or (
                    (local or observed[0][0].issue_number == source.issue_number)
                    and local != [observed[0][0]]
                )
            ):
                invalid_request_ids.add(comment_id)
                if local:
                    conflicting_decision_ids.add(comment_id)
                continue
            if len(local) > 1:
                invalid_request_ids.add(comment_id)
                conflicting_decision_ids.add(comment_id)
                continue
            record = local[0] if local else observed[0][0] if observed else None
            try:
                source_hint = (
                    WorkerRequest(record.issue_number, record.role, record.action)
                    if record is not None
                    else _claimed_source(body.partition("\n")[2])
                )
            except ValueError:
                source_hint = None
            if source_hint != source:
                if record is None:
                    # A worker's claimed foreign source cannot exclude a live
                    # or not-yet-visible Application from observation.
                    source_hint = None
                elif not github_original_request_matches(comment, record, repository):
                    invalid_request_ids.add(comment_id)
                    continue
        else:
            source_hint = _effect_request_source_hint(body)
            legacy_source_hint = _legacy_raw_source_hint(body)
            encoded_source_identity = _legacy_encoded_source_identity(body)
            try:
                request = parse_application_request(body)
            except ValueError:
                request = None
        source_bound = False
        if source_hint is not None:
            if source_hint != source:
                continue
            source_bound = True
        elif legacy_source_hint is not None:
            if legacy_source_hint != source:
                continue
            source_bound = True
        elif request is not None and request.dispatch_correlation is not None:
            if not _effect_request_matches_source(
                repository=repository,
                source=source,
                body=body,
                request=request,
            ):
                continue
            source_bound = True
        elif request is not None:
            # A semantic-only payload is safe only when the machine-owned
            # envelope carries the one opaque dispatch correlation.  Without
            # that binding, the application cannot prove which exact ingress
            # selected the current frontier and must not guess.
            invalid_request_ids.add(comment_id)
            continue
        elif encoded_source_identity is not None:
            # This is only a historical source filter.  It never authorizes
            # an effect: an exact current-source identity remains subject to
            # the normal application-run/ACCEPT classifier below.
            if encoded_source_identity != (source.issue_number, source.action):
                continue
            source_bound = True
        elif not source_bound:
            # No source identity is established.  Keep the transport separate
            # from current-source evidence so terminal historical noise can
            # retire naturally, while a live/unknown exact Application run
            # still prevents semantic redispatch below.
            unbound_request_ids.add(comment_id)
            continue
        try:
            authorization_revision = None if request is None else request.authorization_revision
        except AttributeError:
            authorization_revision = None
        previous = candidates.get(comment_id)
        candidate = _IngressCandidate(
            request_comment_id=comment_id,
            body=body,
            created_at=_comment_time(comment),
            authorization_revision=authorization_revision,
            request=request,
        )
        if previous is not None and previous != candidate:
            invalid_request_ids.add(comment_id)
            candidates.pop(comment_id, None)
        elif comment_id not in invalid_request_ids:
            candidates[comment_id] = candidate

    # Absence of ingress is meaningful only relative to a qualified current
    # occurrence. All candidates, including the empty set, share that proof.
    issue = read(repository, token, f"issues/{source.issue_number}")
    if not isinstance(issue, Mapping):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-current-issue-unavailable",
        )
    lifecycle = _paged_list(
        repository,
        token,
        f"issues/{source.issue_number}/timeline",
        read=read,
    )

    # One accepted-source proof owner for unqualified, predecessor and
    # current frontiers. Reconstruct the continuation transport from this
    # invocation's fresh sources; never memoize an earlier wake's proof.
    def accepted_state(
        accepted_record: ApplicationDecisionRecord, accepted_source: WorkerRequest
    ) -> ApplicationCompletion:
        return _accepted_application_state(
            repository=repository,
            token=token,
            source=accepted_source,
            record=accepted_record,
            issue_comments=issue_comments,
            lifecycle_events=lifecycle,
            current_issue=cast(Mapping[str, object], issue),
            current_revision=current_revision,
            read=read,
            recent_comments=runtime_comments,
            current_dispatch_request_comment_id=current_dispatch_request_comment_id,
            continuation_transport_comment_ids=_continuation_transport_comment_ids(
                repository=repository,
                owner=owner,
                token=token,
                read=read,
                source=accepted_source,
                record=accepted_record,
                issue_comments=issue_comments,
                recent_comments=recent,
            ),
        )

    frontier, frontier_qualified = _derive_frontier(
        repository=repository,
        token=token,
        source=source,
        current_issue=cast(Mapping[str, object], issue),
        issue_comments=issue_comments,
        lifecycle_events=lifecycle,
        current_revision=current_revision,
        read=read,
    )
    if not frontier_qualified:
        # A durable ACCEPTED intent is the source of truth for its immutable
        # application job.  A legacy/unqualified ACTION_RESULT may leave the
        # current Issue route unchanged while making the formal frontier
        # temporarily unqualifiable.  In that narrow case, resume only one
        # accepted intent whose exact source and Change still match the fresh
        # open Issue.  The existing accepted-intent owner performs ancestry,
        # durable consequence, and exact application-run checks; ambiguity or
        # missing evidence still fails closed.
        observation = normalize_github_issue(cast(Mapping[str, object], issue))
        current_accepted = tuple(
            record
            for record in _application_decisions(issue_comments)
            if record.disposition == "ACCEPTED"
            and observation is not None
            and (record.issue_number, record.role, record.action, record.change)
            == (source.issue_number, source.role, source.action, observation.change)
        )
        if (
            observation is not None
            and observation.authoritative
            and observation.state == "open"
            and observation.issue_number == source.issue_number
            and observation.routing == (source.role, source.action)
            and len(current_accepted) == 1
            and current_accepted[0].request_comment_id not in conflicting_decision_ids
        ):
            resumed = accepted_state(current_accepted[0], source)
            if resumed.state != "NONE":
                return resumed
        elif len(current_accepted) > 1:
            return ApplicationCompletion(
                "AMBIGUOUS",
                "application-completion-invalid-frontier-accepted-intents-ambiguous",
            )
        return ApplicationCompletion("INVALID", "application-completion-current-frontier-invalid")

    qualified_decision_events: dict[int, list[tuple[ApplicationDecisionRecord, str | None]]] = {}
    for comment in issue_comments:
        if not is_github_actions_comment(comment):
            continue
        record = parse_application_decision(comment.get("body"))
        if record is None:
            continue
        qualified_decision_events.setdefault(record.request_comment_id, []).append(
            (record, _comment_time(comment))
        )
    decisions_by_request = {
        request_id: tuple(record for record, _ in events)
        for request_id, events in qualified_decision_events.items()
    }
    # An ordering timestamp belongs to exactly one provenance-qualified Actions
    # decision event. Copies from other actors, duplicate/contradictory Actions
    # decisions, and missing timestamps cannot authorize predecessor retirement.
    decision_created_at = {
        request_id: events[0][1] if len(events) == 1 else None
        for request_id, events in qualified_decision_events.items()
    }

    # An unbound transport cannot own this source, but it is not safe to erase
    # it from observation.  A terminal exact application run with no ACCEPT is
    # inert history; a live, missing, or contradictory run remains unresolved
    # and blocks redispatch without becoming current-source authority.
    accepted_request_ids = {
        request_id
        for request_id, records in decisions_by_request.items()
        if any(record.disposition == "ACCEPTED" for record in records)
    }
    for request_id in unbound_request_ids - accepted_request_ids:
        state = _preaccept_application_state(
            repository,
            token,
            request_id,
            read=read,
        )
        if state is None or state.state != "REJECTED":
            return ApplicationCompletion(
                "INVALID",
                "application-completion-unbound-transport-unresolved",
            )

    # A successor wake observes the frontier's canonical correlation, not the
    # predecessor's old Role/Action labels.  Reconcile that exact accepted
    # intent before allowing the successor ingress to compete.
    frontier_owner_decisions = _frontier_application_decisions(decisions, frontier)
    if len(frontier_owner_decisions) > 1:
        return ApplicationCompletion(
            "AMBIGUOUS",
            "application-completion-frontier-owner-ambiguous",
        )
    if frontier_owner_decisions:
        frontier_owner = frontier_owner_decisions[0]
        if frontier_owner.request_comment_id in conflicting_decision_ids:
            return ApplicationCompletion(
                "INVALID", "application-completion-preaccept-evidence-unknown"
            )
        if frontier_owner.disposition != "ACCEPTED":
            return ApplicationCompletion(
                "INVALID",
                "application-completion-consequence-without-acceptance",
                request_comment_id=frontier_owner.request_comment_id,
            )
        try:
            frontier_source = WorkerRequest(
                frontier_owner.issue_number,
                frontier_owner.role,
                frontier_owner.action,
            )
        except (TypeError, ValueError):
            return ApplicationCompletion(
                "INVALID",
                "application-completion-frontier-owner-invalid",
                request_comment_id=frontier_owner.request_comment_id,
            )
        frontier_completion = accepted_state(frontier_owner, frontier_source)
        if frontier_completion.state != "COMPLETE":
            return frontier_completion

    # The formal qualifier owns the current frontier.  Decisions before its
    # latest qualified predecessor are historical, even when they have the
    # same Role/Action as the current route.  This is the recurrence boundary
    # for both A -> A and A -> B -> A.
    current_request_ids = {
        request_id
        for request_id in candidates
        if _belongs_to_current_frontier(
            request_id,
            frontier,
            occurrence_created_at=candidates[request_id].created_at,
        )
    }
    current_invalid_request_ids = {
        request_id
        for request_id in invalid_request_ids
        if request_id < 0
        or _belongs_to_current_frontier(
            request_id,
            frontier,
            occurrence_created_at=ingress_created_at.get(request_id),
        )
    }
    current_frontier_decisions = [
        record
        for record in relevant_decisions
        if _belongs_to_current_frontier(
            record.request_comment_id,
            frontier,
            occurrence_created_at=decision_created_at.get(record.request_comment_id),
        )
    ]
    predecessor_decisions = [
        record
        for record in relevant_decisions
        if _accepted_intent_owns_frontier(record, frontier, source=source)
    ]
    # A predecessor accepted intent is a recovery fallback only while there is
    # no later ingress or decision for this frontier.  Once a new occurrence
    # is observable, the completed predecessor is historical and must not
    # compete with the new current-frontier reducer input.  This is the
    # causal boundary for A -> A as well as A -> B -> A; it is not a request
    # count, retry, or generation mechanism.
    relevant_decisions = (
        current_frontier_decisions
        if current_request_ids or current_invalid_request_ids or current_frontier_decisions
        else predecessor_decisions
    )
    # Proven pre-write failures can be terminal without a formal ACTION_RESULT:
    # no repository effect occurred to warrant a semantic successor. When a
    # genuinely newer ingress is observed, retire that one no-effect ACCEPT
    # instead of allowing two immutable accepts to create a permanent loop.
    if relevant_decisions and (current_request_ids or len(relevant_decisions) > 1):
        aborted_ids = _proven_aborted_predecessors(
            repository,
            token,
            records=relevant_decisions,
            ingress_times={
                request_id: ingress_created_at.get(request_id) for request_id in current_request_ids
            },
            decision_times={
                record.request_comment_id: decision_created_at.get(record.request_comment_id)
                for record in relevant_decisions
            },
            issue_comments=issue_comments,
            read=read,
        )
        relevant_decisions = [
            record for record in relevant_decisions if record.request_comment_id not in aborted_ids
        ]
        current_request_ids.difference_update(aborted_ids)
    accepted = [record for record in relevant_decisions if record.disposition == "ACCEPTED"]
    accepted_request_ids = {record.request_comment_id for record in accepted}
    if conflicting_decision_ids.intersection(
        record.request_comment_id for record in relevant_decisions
    ):
        return ApplicationCompletion("INVALID", "application-completion-preaccept-evidence-unknown")
    frontier_correlation = (
        None
        if frontier is None or frontier.event is None
        else getattr(frontier.event, "application_correlation", None)
    )
    frontier_correlation_fields = (
        None
        if not isinstance(frontier_correlation, str)
        else _application_correlation_fields(frontier_correlation)
    )
    frontier_request_id = (
        None
        if frontier_correlation_fields is None
        else _positive_int_string(frontier_correlation_fields[1])
    )
    current_ingress_ids = set(candidates) | {
        request_id for request_id in invalid_request_ids if request_id > 0
    }
    if (
        not accepted
        and not frontier_owner_decisions
        and frontier_request_id is not None
        and frontier_request_id in current_ingress_ids
    ):
        # A formal consequence tied to this ingress without Phase-A ACCEPT is
        # contradictory evidence, not proof that source ownership is free.
        # The exact frontier owner above has already been reconciled COMPLETE;
        # retiring it from this occurrence does not erase its acceptance.
        return ApplicationCompletion(
            "INVALID",
            "application-completion-consequence-without-acceptance",
            request_comment_id=frontier_request_id,
        )
    settled_prefix: tuple[ApplicationDecisionRecord, ApplicationCompletion] | None = None
    if len(accepted) > 1:
        settled_prefix = _settled_development_prefix(
            repository,
            token,
            source=source,
            accepted=accepted,
            decision_times=decision_created_at,
            ingress_times=ingress_created_at,
            issue_comments=issue_comments,
            accepted_state=accepted_state,
            current_revision=current_revision,
            dispatch_request_id=current_dispatch_request_comment_id,
            phase_a=phase_a_request_comment_id is not None,
            current_issue=cast(Mapping[str, object], issue),
            lifecycle_events=lifecycle,
            read=read,
        )
        if settled_prefix is None:
            return ApplicationCompletion("AMBIGUOUS", "application-completion-accepted-ambiguous")
        accepted = [settled_prefix[0]]
    classifications: dict[int, PreacceptClassification] = {}
    for request_id in current_request_ids - accepted_request_ids:
        candidate = candidates[request_id]
        classifications[request_id] = _classify_ingress_candidate(
            repository=repository,
            token=token,
            source=source,
            candidate=candidate,
            decisions_by_request=decisions_by_request,
            issue_comments=issue_comments,
            current_revision=current_revision,
            read=read,
            current_issue=cast(Mapping[str, object], issue),
        )
    for request_id in current_invalid_request_ids:
        if request_id > 0 and request_id not in accepted_request_ids:
            classifications[request_id] = "INVALID"

    if (
        any(state in {"INVALID", "UNKNOWN"} for state in classifications.values())
        or -1 in current_invalid_request_ids
    ):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-preaccept-evidence-unknown",
        )

    needs_repair = [
        request_id for request_id, state in classifications.items() if state == "NEEDS_REPAIR"
    ]
    if needs_repair:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-execution-exception-requires-lead",
            request_comment_id=needs_repair[0] if len(needs_repair) == 1 else None,
        )

    live_request_ids = {
        request_id for request_id, state in classifications.items() if state == "LIVE_PREACCEPT"
    }
    terminal_request_ids = {
        request_id for request_id, state in classifications.items() if state == "TERMINAL_NO_ACCEPT"
    }
    rejected_request_ids = {
        request_id for request_id, state in classifications.items() if state == "REJECTED"
    }
    rejected_request_ids.update(
        record.request_comment_id
        for record in relevant_decisions
        if record.disposition == "REJECTED"
    )

    if not accepted:
        if len(live_request_ids) > 1:
            return ApplicationCompletion(
                "AMBIGUOUS",
                "application-completion-live-preaccept-ambiguous",
            )
        if len(live_request_ids) == 1:
            request_comment_id = next(iter(live_request_ids))
            return ApplicationCompletion(
                "RESUMABLE",
                "application-completion-preaccept-in-progress",
                request_comment_id=request_comment_id,
            )
        if terminal_request_ids or rejected_request_ids:
            terminal_comment_id = (
                next(iter(terminal_request_ids or rejected_request_ids))
                if len(terminal_request_ids) + len(rejected_request_ids) == 1
                else None
            )
            return ApplicationCompletion(
                "REJECTED",
                "application-completion-terminal-no-accept"
                if terminal_request_ids
                else "application-completion-rejected",
                request_comment_id=terminal_comment_id,
            )
        return ApplicationCompletion("NONE", "application-completion-none")

    record = accepted[0]
    competing_live = any(request_id != record.request_comment_id for request_id in live_request_ids)
    competing_unknown = any(
        request_id != record.request_comment_id
        and classifications.get(request_id) in {"INVALID", "UNKNOWN"}
        for request_id in classifications
    )
    if competing_live or competing_unknown:
        return ApplicationCompletion(
            "AMBIGUOUS",
            "application-completion-request-binding-ambiguous",
        )
    # An accepted decision is immutable intent.  If the ingress comment was
    # edited or deleted after ACCEPT, do not parse its new text and do not
    # replay worker semantics; the exact accepted record remains the only
    # resumable payload.
    completion = accepted_state(record, source) if settled_prefix is None else settled_prefix[1]
    return _current_development_completion(
        repository,
        token,
        source=source,
        record=record,
        completion=completion,
        current_revision=current_revision,
        dispatch_request_id=current_dispatch_request_comment_id,
        phase_a=phase_a_request_comment_id is not None,
        accepted_decision_sha256=_accepted_decision_sha256(record, issue_comments),
        read=read,
    )


def render_dispatch_result_document(
    *,
    request_comment_id: int,
    default_branch_revision: str,
    decision: DispatchDecision,
    application_continuation: str | None = None,
    qualified_carrier: QualifiedCarrierPlan | None = None,
) -> str:
    """Render the one canonical plaintext JSON result owned by an exact bridge run."""

    if request_comment_id <= 0 or _SHA.fullmatch(default_branch_revision) is None:
        raise ValueError("dispatch result identity is invalid")
    if decision.disposition not in _DECISION_DISPOSITIONS:
        raise ValueError("unsupported dispatch disposition")

    payload: dict[str, object] = {
        "schema": DISPATCH_RESULT_SCHEMA,
        "request_comment_id": request_comment_id,
        "default_branch_revision": default_branch_revision,
        "disposition": decision.disposition,
    }
    if decision.disposition == "AUTHORIZE":
        if application_continuation is not None or qualified_carrier is not None:
            raise ValueError("AUTHORIZE cannot carry application completion transport")
        issue_number = decision.selected_issue_id
        if (
            isinstance(issue_number, bool)
            or not isinstance(issue_number, int)
            or issue_number <= 0
            or decision.selected_routing is None
        ):
            raise ValueError("AUTHORIZE requires one Issue and Action")
        role, action = decision.selected_routing
        try:
            parsed_action = ModelAction(action)
        except ValueError as exc:
            raise ValueError("dispatch Action is invalid") from exc
        if role_for(parsed_action).value != role:
            raise ValueError("dispatch role is not derived from Action")
        payload.update({"issue_number": issue_number, "action": action})
    else:
        if decision.selected_issue_id is not None or decision.selected_routing is not None:
            raise ValueError("non-authorizing result carries selected work")
        if not _valid_reason(decision.reason):
            raise ValueError("dispatch reason is invalid")
        payload["reason"] = decision.reason
        if qualified_carrier is not None:
            if (
                decision.disposition != "FAIL_CLOSED"
                or decision.reason != "application-completion-carrier-required"
            ):
                raise ValueError("qualified carrier is only valid for carrier-required")
            payload["qualified_carrier"] = qualified_carrier_document(qualified_carrier)
        if application_continuation is not None:
            if decision.disposition != "FAIL_CLOSED" or decision.reason not in {
                "application-completion-rerun-limit",
                "application-completion-continuation-required",
                "application-completion-carrier-required",
            }:
                raise ValueError(
                    "application continuation is only valid for application completion"
                )
            if parse_application_continuation_request(application_continuation) is None:
                raise ValueError("application continuation is invalid")
            payload["application_continuation"] = application_continuation
        if decision.reason == "application-completion-carrier-required" and (
            qualified_carrier is None or application_continuation is None
        ):
            raise ValueError("carrier-required result is missing exact handoff evidence")

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def parse_dispatch_result_document(raw: bytes | str) -> MachineDispatchDecision:
    """Strictly parse the canonical plaintext JSON dispatch-result contract."""

    if isinstance(raw, bytes):
        if not raw or len(raw) > _MAX_RESULT_BYTES:
            raise RuntimeError("exact dispatch result artifact size is invalid")
        try:
            document = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("exact dispatch result artifact is not UTF-8 JSON") from exc
    else:
        encoded = raw.encode("utf-8")
        if not encoded or len(encoded) > _MAX_RESULT_BYTES:
            raise RuntimeError("exact dispatch result artifact size is invalid")
        document = raw

    try:
        decoded = json.loads(document)
    except json.JSONDecodeError as exc:
        raise RuntimeError("exact dispatch result artifact is not UTF-8 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise RuntimeError("exact dispatch result artifact must be a JSON object")
    payload = cast(Mapping[str, object], decoded)

    disposition = payload.get("disposition")
    if disposition not in _DECISION_DISPOSITIONS:
        raise RuntimeError("exact dispatch result disposition is invalid")
    common_keys = {
        "schema",
        "request_comment_id",
        "default_branch_revision",
        "disposition",
    }
    if disposition == "AUTHORIZE":
        expected_keys = common_keys | {"issue_number", "action"}
        valid_keys = set(expected_keys)
        payload_keys_valid = set(payload) == valid_keys
    else:
        expected_keys = common_keys | {"reason"}
        valid_keys = set(expected_keys)
        payload_keys_valid = set(payload) == valid_keys
        if disposition == "FAIL_CLOSED":
            optional_keys = set(payload) - valid_keys
            payload_keys_valid = optional_keys in (
                set(),
                {"application_continuation"},
                {"application_continuation", "qualified_carrier"},
            )
    if not payload_keys_valid or payload.get("schema") != DISPATCH_RESULT_SCHEMA:
        raise RuntimeError("exact dispatch result schema is invalid")

    request_comment_id = _positive_int(payload.get("request_comment_id"))
    revision = payload.get("default_branch_revision")
    if (
        request_comment_id is None
        or not isinstance(revision, str)
        or _SHA.fullmatch(revision) is None
    ):
        raise RuntimeError("exact dispatch result identity is invalid")

    if disposition == "AUTHORIZE":
        issue_number = _positive_int(payload.get("issue_number"))
        action = payload.get("action")
        if issue_number is None or not isinstance(action, str):
            raise RuntimeError("AUTHORIZE dispatch result is incomplete")
        try:
            parsed_action = ModelAction(action)
        except ValueError as exc:
            raise RuntimeError("AUTHORIZE dispatch Action is invalid") from exc
        return MachineDispatchDecision(
            request_comment_id=request_comment_id,
            default_branch_revision=revision,
            disposition=disposition,
            issue_number=issue_number,
            role=role_for(parsed_action).value,
            action=action,
        )

    reason = payload.get("reason")
    if not _valid_reason(reason):
        raise RuntimeError("non-authorizing dispatch reason is invalid")
    application_continuation = payload.get("application_continuation")
    if application_continuation is not None:
        if disposition != "FAIL_CLOSED" or not isinstance(application_continuation, str):
            raise RuntimeError("exact application continuation is invalid")
        if parse_application_continuation_request(application_continuation) is None:
            raise RuntimeError("exact application continuation is invalid")
    qualified_carrier_raw = payload.get("qualified_carrier")
    qualified_carrier = None
    if qualified_carrier_raw is not None:
        if (
            disposition != "FAIL_CLOSED"
            or reason != "application-completion-carrier-required"
            or application_continuation is None
        ):
            raise RuntimeError("exact qualified carrier is invalid")
        try:
            qualified_carrier = parse_qualified_carrier_document(qualified_carrier_raw)
        except ValueError as exc:
            raise RuntimeError("exact qualified carrier is invalid") from exc
    if reason == "application-completion-carrier-required" and (
        application_continuation is None or qualified_carrier is None
    ):
        raise RuntimeError("carrier-required dispatch result is incomplete")
    return MachineDispatchDecision(
        request_comment_id=request_comment_id,
        default_branch_revision=revision,
        disposition=disposition,
        reason=cast(str, reason),
        application_continuation=application_continuation,
        qualified_carrier=qualified_carrier,
    )


def _request_identity(event: Mapping[str, object]) -> tuple[int, int] | None:
    if event.get("action") != "created":
        return None
    issue = event.get("issue")
    comment = event.get("comment")
    if not isinstance(issue, Mapping) or not isinstance(comment, Mapping):
        return None
    if "pull_request" in issue or not is_runtime_checkin_issue(cast(Mapping[str, object], issue)):
        return None
    issue_number = issue.get("number")
    comment_id = comment.get("id")
    body = comment.get("body")
    if (
        not isinstance(issue_number, int)
        or isinstance(issue_number, bool)
        or issue_number <= 0
        or not isinstance(comment_id, int)
        or isinstance(comment_id, bool)
        or comment_id <= 0
        or not isinstance(body, str)
        or parse_dispatch_request(body) is None
    ):
        return None
    return issue_number, comment_id


def plan_dispatch_decision(
    *,
    event: Mapping[str, object],
    default_branch_revision: str,
    decision: DispatchDecision,
    application_continuation: str | None = None,
    qualified_carrier: QualifiedCarrierPlan | None = None,
    quality_call: dict[str, str] | None = None,
) -> BridgePlan:
    identity = _request_identity(event)
    if identity is None:
        return BridgePlan(False)
    issue_number, request_comment_id = identity
    if quality_call is not None and (
        decision.disposition != "NO_WORK"
        or decision.reason != "verification-obligation-pending"
        or quality_call.get("quality_source_comment_id") != str(request_comment_id)
        or quality_call.get("quality_definition_revision") != default_branch_revision
        or application_continuation is not None
        or qualified_carrier is not None
    ):
        raise ValueError("quality call is not bound to the non-authorizing dispatch")
    return BridgePlan(
        should_emit=True,
        issue_number=issue_number,
        request_comment_id=request_comment_id,
        result_body=render_dispatch_result_document(
            request_comment_id=request_comment_id,
            default_branch_revision=default_branch_revision,
            decision=decision,
            application_continuation=application_continuation,
            qualified_carrier=qualified_carrier,
        ),
        quality_call=quality_call,
    )


def acquire_production_dispatch_decision(repository: str, token: str) -> DispatchDecision:
    return classify_dispatch(acquire_current_github_preflight(repository, token))


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a JSON object")
    return cast(Mapping[str, object], value)


def _write_outputs(path: Path, plan: BridgePlan, *, repair_admission: bool = False) -> None:
    lines = [f"should_emit={'true' if plan.should_emit else 'false'}"]
    if repair_admission:
        lines.append("repair_admission=true")
    if plan.issue_number is not None:
        lines.append(f"issue_number={plan.issue_number}")
    if plan.request_comment_id is not None:
        lines.append(f"request_comment_id={plan.request_comment_id}")
    if plan.quality_call is not None:
        lines.extend(
            f"{key}={value}"
            for key, value in plan.quality_call.items()
            if key != "quality_obligation"
        )
        print("native_quality_plan=" + json.dumps(plan.quality_call, sort_keys=True))
    else:
        print("native_quality_plan=none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_result_payload(path: Path, plan: BridgePlan) -> None:
    if plan.should_emit and plan.result_body is not None:
        payload = (plan.result_body + "\n").encode("utf-8")
        path.write_bytes(payload)
        if plan.quality_call is not None:
            print("native_quality_result_sha256=" + hashlib.sha256(payload).hexdigest())


@dataclass(frozen=True)
class RuntimeRepairAdmission:
    """A native-Human-qualified, non-writing maintenance handoff only."""

    source: WorkerRequest
    change: str
    authorization_revision: str
    trigger_comment_id: int
    accepted_request_comment_id: int
    accepted_decision_sha256: str
    accepted_worker_sha256: str
    repair_pr: int
    repair_head: str
    result_state: str
    reason: str
    frontier_proof: RecoveryProofResult
    # Existing Application-validated native Run/Job/Artifact identity; this
    # handoff cannot be upgraded from a bare status or a synthetic DAG proof.
    source_artifact: ApplicationRecoveryArtifact | ApplicationExceptionArtifact


def qualify_runtime_repair_admission(
    event: Mapping[str, object],
    *,
    repository: str,
    token: str,
    current_revision: str,
    read: GitHubReader = _github_json,
    qualify: Callable[..., ApplicationCompletion] = qualify_application_completion,
) -> RuntimeRepairAdmission | None:
    """Consume a native Human issue_comment without emitting any repository Effect.

    The existing Application remains the one accepted-intent/evidence owner.
    This qualified intake is not approval to patch a PR or replay an Effect.
    The external Human maintenance interaction must fresh-reauthorize writes.
    """

    comment = event.get("comment")
    event_issue = event.get("issue")
    sender = event.get("sender")
    event_repo = event.get("repository")
    if (
        repository != "royhsu-work/investment-strategy"
        or _SHA.fullmatch(current_revision) is None
        or event.get("action") != "created"
        or not isinstance(comment, Mapping)
        or not isinstance(event_issue, Mapping)
        or "pull_request" in event_issue
        or not isinstance(sender, Mapping)
        or not isinstance(event_repo, Mapping)
        or event_repo.get("full_name") != repository
        or event_repo.get("default_branch") != "main"
    ):
        return None
    raw_body = comment.get("body")
    if not isinstance(raw_body, str):
        return None
    fields = RUNTIME_REPAIR_REQUEST_WIRE.parse(raw_body)
    if fields is None:
        return None
    issue_number = _positive_int_string(fields["Issue"])
    request_comment_id = _positive_int_string(fields["Accepted-Request-Comment"])
    repair_pr = _positive_int_string(fields["Repair-PR"])
    trigger_comment_id = _positive_int(comment.get("id"))
    actor = comment.get("user")
    native_actor = actor.get("login") if isinstance(actor, Mapping) else None
    owner = repository.split("/", 1)[0]
    if (
        issue_number is None
        or request_comment_id is None
        or repair_pr is None
        or trigger_comment_id is None
        or issue_number != event_issue.get("number")
        or not isinstance(actor, Mapping)
        or native_actor != owner
        or actor.get("type") != "User"
        or sender.get("login") != owner
        or sender.get("id") != actor.get("id")
        or _positive_int(actor.get("id")) is None
        or comment.get("performed_via_github_app") is not None
        or _SHA.fullmatch(fields["Repair-HEAD"]) is None
        or re.fullmatch(r"[0-9a-f]{64}", fields["Accepted-Decision-SHA256"]) is None
    ):
        return None
    try:
        role = role_for(ModelAction(fields["Action"])).value
    except ValueError:
        return None
    source = WorkerRequest(issue_number, role, fields["Action"])
    native = read(repository, token, f"issues/comments/{trigger_comment_id}")
    main_ref = read(repository, token, "git/ref/heads/main")
    current_issue = read(repository, token, f"issues/{issue_number}")
    pr = read(repository, token, f"pulls/{repair_pr}")
    if not all(isinstance(value, Mapping) for value in (native, main_ref, current_issue, pr)):
        return None
    native = cast(Mapping[str, object], native)
    main_ref = cast(Mapping[str, object], main_ref)
    current_issue = cast(Mapping[str, object], current_issue)
    pr = cast(Mapping[str, object], pr)
    native_user = native.get("user")
    main_object = main_ref.get("object")
    pr_head = pr.get("head")
    pr_base = pr.get("base")
    head_repo = pr_head.get("repo") if isinstance(pr_head, Mapping) else None
    base_repo = pr_base.get("repo") if isinstance(pr_base, Mapping) else None
    if (
        native.get("id") != trigger_comment_id
        or native.get("body") != comment.get("body")
        or native.get("issue_url")
        != f"https://api.github.com/repos/{repository}/issues/{issue_number}"
        or not isinstance(native_user, Mapping)
        or native_user.get("login") != owner
        or native_user.get("id") != actor.get("id")
        or native.get("performed_via_github_app") is not None
        or not isinstance(main_object, Mapping)
        or main_object.get("sha") != current_revision
        or pr.get("number") != repair_pr
        or pr.get("state") != "open"
        or pr.get("merged") is not False
        or not isinstance(pr_head, Mapping)
        or pr_head.get("sha") != fields["Repair-HEAD"]
        or not isinstance(head_repo, Mapping)
        or head_repo.get("full_name") != repository
        or not isinstance(pr_base, Mapping)
        or pr_base.get("ref") != "main"
        or not isinstance(base_repo, Mapping)
        or base_repo.get("full_name") != repository
    ):
        return None
    observation = normalize_github_issue(current_issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.change != fields["Change"]
        or observation.routing != (source.role, source.action)
    ):
        return None
    # Application owns the unique native accepted-decision inventory and SHA.
    # Bridge consumes that result; a second GET is neither atomic nor authority.
    completion = qualify(
        repository,
        token,
        source=source,
        current_revision=current_revision,
        read=read,
    )
    accepted = completion.accepted_record
    if (
        accepted is None
        or completion.accepted_decision_sha256 != fields["Accepted-Decision-SHA256"]
        or accepted.disposition != "ACCEPTED"
        or accepted.request_comment_id != request_comment_id
        or (accepted.issue_number, accepted.change, accepted.role, accepted.action)
        != (issue_number, fields["Change"], source.role, source.action)
    ):
        return None
    # Eligibility comes from the Application-owned typed proof, not a
    # Bridge status/reason allowlist. A missing or mismatched accepted source
    # cannot become a positive repair admission just because it is INVALID.
    proof = completion.accepted_proof
    if proof is None:
        return None
    repair_frontier = proof.runtime_repair_frontier
    artifact = completion.recovery_artifact
    # Both Application artifact readers independently qualify the native
    # Run/Job/Artifact, but their documents use distinct stage schemas:
    # recovery carries authorization_revision; exception carries change.
    # Compare the common accepted identity once, then its typed schema field.
    if repair_frontier is None or not isinstance(
        artifact, (ApplicationRecoveryArtifact, ApplicationExceptionArtifact)
    ):
        return None
    if (
        artifact.request_comment_id != request_comment_id
        or artifact.accepted_decision_sha256 != fields["Accepted-Decision-SHA256"]
        or (
            artifact.document.get("issue_number"),
            artifact.document.get("role"),
            artifact.document.get("action"),
        )
        != (accepted.issue_number, accepted.role, accepted.action)
        or (
            artifact.document.get("authorization_revision")
            if isinstance(artifact, ApplicationRecoveryArtifact)
            else artifact.document.get("change")
        )
        != (
            accepted.authorization_revision
            if isinstance(artifact, ApplicationRecoveryArtifact)
            else accepted.change
        )
        or completion.request_comment_id != request_comment_id
        or completion.state != ("RESUMABLE" if proof.continuation == "OBSERVE" else "INVALID")
    ):
        return None
    return RuntimeRepairAdmission(
        source=source,
        change=accepted.change,
        authorization_revision=accepted.authorization_revision,
        trigger_comment_id=trigger_comment_id,
        accepted_request_comment_id=request_comment_id,
        accepted_decision_sha256=fields["Accepted-Decision-SHA256"],
        accepted_worker_sha256=accepted.worker_result_sha256,
        repair_pr=repair_pr,
        repair_head=fields["Repair-HEAD"],
        result_state=completion.state,
        reason=completion.reason,
        frontier_proof=repair_frontier,
        source_artifact=artifact,
    )


def _runtime_repair_admission_document(
    admission: RuntimeRepairAdmission, *, repository: str
) -> dict[str, object]:
    """One canonical snapshot for emission and fresh Human/Runtime consumption.

    This is a description of evidence, not an Effect or repair authorization.
    """
    evidence_kind = (
        "recovery"
        if isinstance(admission.source_artifact, ApplicationRecoveryArtifact)
        else "exception"
    )
    proof = admission.frontier_proof
    witness = proof.witness
    stage = witness.stage if isinstance(witness, TypedEvidenceError) else None
    if (
        isinstance(witness, RecoveryEvidenceNode)
        and witness.materialization_observation is not None
    ):
        stage = f"MATERIALIZATION_{witness.materialization_observation.disposition}"
    document: dict[str, object] = {
        "schema": "scheduled-agent-runtime-repair-admission/v1",
        "source": {
            "repository": repository,
            "issue_number": admission.source.issue_number,
            "role": admission.source.role,
            "action": admission.source.action,
            "change": admission.change,
            "authorization_revision": admission.authorization_revision,
            "human_comment_id": admission.trigger_comment_id,
            "accepted_request_comment_id": admission.accepted_request_comment_id,
            "accepted_decision_sha256": admission.accepted_decision_sha256,
            "accepted_worker_sha256": admission.accepted_worker_sha256,
        },
        "repair_target": {"pr_number": admission.repair_pr, "head_sha": admission.repair_head},
        "native_application": {
            "run_id": admission.source_artifact.run_id,
            "run_attempt": admission.source_artifact.run_attempt,
            "job_id": admission.source_artifact.job_id,
            "artifact_id": admission.source_artifact.artifact_id,
            "artifact_digest": admission.source_artifact.artifact_digest,
            "recovery_episode_sha256": admission.source_artifact.recovery_episode_sha256,
            "kind": evidence_kind,
        },
        "frontier": {
            "obligation": proof.remaining_obligation,
            "disposition": proof.disposition,
            "ordinal": proof.frontier_index,
            "witness_kind": type(witness).__name__,
            "evidence_stage": stage,
        },
        "completion": {"state": admission.result_state, "reason": admission.reason},
        "effect_authority": "NONE",
    }
    return document


def _present_runtime_repair_admission(
    admission: RuntimeRepairAdmission, *, repository: str, evidence_path: Path | None = None
) -> None:
    """Present the canonical non-writing Artifact without a second evidence projection."""

    document = _runtime_repair_admission_document(admission, repository=repository)
    source = cast(Mapping[str, object], document["source"])
    repair = cast(Mapping[str, object], document["repair_target"])
    native = cast(Mapping[str, object], document["native_application"])
    frontier = cast(Mapping[str, object], document["frontier"])
    completion = cast(Mapping[str, object], document["completion"])
    evidence_stage = frontier["evidence_stage"]
    body = "\n".join(
        (
            "## Non-writing R9 Human/Runtime repair intake",
            "",
            f"- Exact source: {repository} Issue #{source['issue_number']}",
            f"- Original Action: {source['role']}/{source['action']}",
            f"- Immutable Change: {source['change']}",
            f"- Accepted authorization revision: {source['authorization_revision']}",
            f"- Native Human trigger: issuecomment-{source['human_comment_id']}",
            f"- Immutable accepted request: issuecomment-{source['accepted_request_comment_id']}",
            f"- Accepted decision SHA256: {source['accepted_decision_sha256']}",
            f"- Accepted worker SHA256: {source['accepted_worker_sha256']}",
            f"- Existing maintenance PR: #{repair['pr_number']}",
            f"- Exact PR HEAD: {repair['head_sha']}",
            f"- Native Application run: {native['run_id']} / attempt {native['run_attempt']}",
            f"- Native Application job: {native['job_id']}",
            f"- Native evidence kind: {native['kind']}",
            f"- Evidence Artifact ID: {native['artifact_id']}",
            f"- Evidence Artifact digest: {native['artifact_digest']}",
            f"- Recovery episode SHA256: {native['recovery_episode_sha256']}",
            f"- Read-only proof: {completion['state']}/{completion['reason']}",
            f"- Pending original/formal/successor frontier: "
            f"{frontier['obligation']}:{frontier['disposition']}",
            f"- Verified Effect ordinal: {frontier['ordinal']}",
            f"- Typed witness: {frontier['witness_kind']}",
            f"- Evidence error stage: "
            f"{evidence_stage if evidence_stage is not None else 'not-an-operational-error'}",
            "",
            "This native event was consumed by the existing Bridge. It authorizes NO "
            "Effect, Action, routing, merge, direct workflow run, or PR mutation. "
            "A separately authorized Human/Runtime maintainer must fresh-qualify "
            "the exact source, target and gates before any repair; only a later "
            "ordinary fresh wake may re-observe the accepted obligation.",
            "",
        )
    )
    # One document owns both machine Artifact and Human summary field values.
    if evidence_path is not None:
        evidence_path.write_text(
            json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    print(body)
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if destination:
        with Path(destination).open("a", encoding="utf-8") as output:
            output.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan one run-scoped dispatch result")
    parser.add_argument("--event-path", type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--result-payload", type=Path)
    parser.add_argument("--repair-admission-payload", type=Path)
    parser.add_argument("--recovery-exit-request-comment-id", type=int)
    args = parser.parse_args()

    if args.recovery_exit_request_comment_id is not None:
        if (
            args.recovery_exit_request_comment_id
            not in {_ORIGINAL_322_REQUEST, _EXCEPTION_322_REQUEST}
            or args.event_path is not None
            or args.github_output is not None
            or args.result_payload is not None
            or _SHA.fullmatch(args.revision) is None
        ):
            parser.error("only the exact historical #322 recovery request is permitted")
        repository = os.environ.get("GITHUB_REPOSITORY")
        token = os.environ.get("GITHUB_TOKEN")
        if repository != "royhsu-work/investment-strategy" or not token:
            raise RuntimeError("recovery requires the exact repository and GitHub token")
        if args.recovery_exit_request_comment_id == _EXCEPTION_322_REQUEST:
            if os.environ.get("GITHUB_EVENT_NAME") != "issue_comment":
                raise RuntimeError("one-time exception requires native issue_comment ingress")
            event_path = os.environ.get("GITHUB_EVENT_PATH")
            if not event_path:
                raise RuntimeError("exception event unavailable")
            event = _require_mapping(_load_json(Path(event_path)), "exception event")
            issue = event.get("issue")
            comment = event.get("comment")
            actor = comment.get("user") if isinstance(comment, Mapping) else None
            event_repository = event.get("repository")
            if not (
                event.get("action") == "created"
                and isinstance(issue, Mapping)
                and issue.get("number") == 322
                and isinstance(comment, Mapping)
                and comment.get("body") == f"RECOVERY_EXIT_REQUEST {_EXCEPTION_322_REQUEST}"
                and isinstance(actor, Mapping)
                and actor.get("login") == "royhsu-work"
                and isinstance(event_repository, Mapping)
                and event_repository.get("full_name") == repository
            ):
                raise RuntimeError("one-time exception event is not Human-authorized")
            completion = apply_one_time_322_exception(
                repository, token, current_revision=args.revision
            )
        else:
            completion = apply_original_322_recovery_exit(
                repository, token, current_revision=args.revision
            )
        print(f"recovery_exit={completion.state}; reason={completion.reason}")
        return 0 if completion.state == "COMPLETE" else 1

    if args.event_path is None or args.github_output is None or args.result_payload is None:
        parser.error("dispatch requires --event-path, --github-output and --result-payload")

    event = _require_mapping(json.loads(args.event_path.read_text(encoding="utf-8")), "event")
    event_comment = event.get("comment")
    event_body = event_comment.get("body") if isinstance(event_comment, Mapping) else None
    if isinstance(event_body, str) and event_body.splitlines()[:1] == [
        RUNTIME_REPAIR_REQUEST_WIRE.marker
    ]:
        repository = os.environ.get("GITHUB_REPOSITORY")
        token = os.environ.get("GITHUB_TOKEN")
        if not repository or not token or os.environ.get("GITHUB_EVENT_NAME") != "issue_comment":
            return 1
        try:
            admission = qualify_runtime_repair_admission(
                event,
                repository=repository,
                token=token,
                current_revision=args.revision,
            )
        except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            admission = None
        if admission is None:
            print(
                "Native R9 repair intake is not source-qualified; no work emitted.",
                file=sys.stderr,
            )
            return 1
        if args.repair_admission_payload is None:
            print("Native R9 repair intake has no evidence Artifact destination.", file=sys.stderr)
            return 1
        _present_runtime_repair_admission(
            admission, repository=repository, evidence_path=args.repair_admission_payload
        )
        _write_outputs(args.github_output, BridgePlan(False), repair_admission=True)
        return 0
    identity = _request_identity(event)
    if identity is None:
        plan = BridgePlan(False)
    else:
        repository = os.environ.get("GITHUB_REPOSITORY")
        token = os.environ.get("GITHUB_TOKEN")
        if not repository or not token:
            raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
        preflight = acquire_current_github_preflight(repository, token)
        decision = classify_dispatch(preflight)
        source = _completion_source(preflight, decision)
        if source is None:
            completion = ApplicationCompletion("NONE", "application-completion-none")
        else:
            try:
                completion = qualify_application_completion(
                    repository,
                    token,
                    source=source,
                    current_revision=args.revision,
                    current_dispatch_request_comment_id=identity[1],
                    current_dispatch_issue_number=identity[0],
                )
            except Exception as exc:
                # The run-scoped dispatch result is the existing durable
                # pre-dispatch repair entry. Preserve exact source identity
                # without exposing exception text, replaying accepted effects,
                # or manufacturing a repository-dispatched successor Action.
                print(
                    "Pre-dispatch accepted-completion proof exception: "
                    f"issue={source.issue_number} action={source.action} "
                    f"type={type(exc).__qualname__}",
                    file=sys.stderr,
                )
                completion = ApplicationCompletion(
                    "INVALID",
                    "application-completion-proof-exception:"
                    f"issue-{source.issue_number}:{source.action}",
                )
        continuation_body = None
        quality_call = None
        if (
            completion.state == "RESUMABLE"
            and completion.quality_obligation is not None
            and completion.quality_obligation.carrier_revision
            == completion.quality_obligation.revision
        ):
            obligation = completion.quality_obligation
            decision = replace(
                decision,
                selected_issue_id=None,
                selected_routing=None,
                disposition="NO_WORK",
                reason="verification-obligation-pending",
            )
            run_id = _positive_int_string(os.environ.get("GITHUB_RUN_ID", ""))
            run_attempt = _positive_int_string(os.environ.get("GITHUB_RUN_ATTEMPT", ""))
            if (
                os.environ.get("GITHUB_EVENT_NAME") == "issue_comment"
                and os.environ.get("GITHUB_WORKFLOW_SHA") == args.revision
                and run_id is not None
                and run_attempt is not None
            ):
                observation = completion.quality_observation
                if observation is None:
                    observation = plan_native_quality_verification(
                        repository,
                        token,
                        revision=obligation.revision,
                        branch=obligation.branch,
                        workflow_blob=obligation.workflow_blob,
                        obligation_id=obligation.obligation_id,
                        accepted_at=obligation.accepted_at,
                        current_revision=args.revision,
                        default_branch=obligation.default_branch,
                        request_comment_id=identity[1],
                        run_id=run_id,
                        run_attempt=run_attempt,
                        read=_github_json,
                        log_read=_github_job_log,
                    )
                if (
                    observation.outcome == "NO_VERDICT"
                    and observation.call is not None
                    and observation.call.get("quality_run_id") == str(run_id)
                    and observation.call.get("quality_run_attempt") == str(run_attempt)
                ):
                    quality_call = observation.call
        elif completion.state in {"RESUMABLE", "INVALID", "AMBIGUOUS"}:
            if (
                completion.reason
                in {
                    "application-completion-rerun-limit",
                    "application-completion-continuation-required",
                    "application-completion-carrier-required",
                }
                and source is not None
                and completion.request_comment_id is not None
            ):
                try:
                    continuation_body = _application_continuation_body(
                        repository=repository,
                        token=token,
                        source=source,
                        request_comment_id=completion.request_comment_id,
                        predecessor_evidence=completion.recovery_artifact,
                    )
                except (HTTPError, OSError, RuntimeError, ValueError, json.JSONDecodeError):
                    # The accepted-decision evidence is not uniquely readable;
                    # retain the fail-closed result and emit no transport.
                    continuation_body = None
            decision = replace(
                decision,
                selected_issue_id=None,
                selected_routing=None,
                disposition="FAIL_CLOSED",
                reason=completion.reason,
            )
        decision = apply_derived_human_wait(
            decision,
            repository=repository,
            token=token,
            current_revision=args.revision,
        )
        plan = plan_dispatch_decision(
            event=event,
            default_branch_revision=args.revision,
            decision=decision,
            application_continuation=continuation_body,
            qualified_carrier=completion.qualified_carrier,
            quality_call=quality_call,
        )
    _write_outputs(args.github_output, plan)
    _write_result_payload(args.result_payload, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
