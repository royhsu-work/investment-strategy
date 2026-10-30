"""Run-scoped machine dispatch transport."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
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
    ApplicationContinuationRequest,
    ApplicationRecoveryArtifact,
    ApplicationRequest,
    _application_owned_worker_result,
    _materialization_effects,
    application_continuation_correlation,
    dispatch_correlation_for,
    parse_application_continuation_request,
    parse_application_request,
    read_application_recovery_artifact,
    render_application_continuation_request,
)
from investment_strategy.scheduled_agent_application_carrier import qualify_implementation_carrier
from investment_strategy.scheduled_agent_application_materialization import (
    find_materialization_payload,
)
from investment_strategy.scheduled_agent_carrier import (
    CarrierOutcomeReport,
    QualifiedCarrierPlan,
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
    consequence_postconditions_complete,
    merged_pr_readiness_complete,
    parse_application_decision,
)
from investment_strategy.scheduled_agent_formal_qualification import (
    CurrentFrontier,
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
from investment_strategy.scheduled_agent_worker import (
    WorkerActionResult,
    parse_worker_result,
)
from investment_strategy.workflow_dispatch import (
    DispatchDecision,
    DispatchPreflight,
    classify_dispatch,
)

REQUEST_MARKER = "DISPATCH_REQUEST"
REQUESTED_AT_PREFIX = "Requested-At: "
RUN_NAME_PREFIX = "Scheduled Agent Dispatch "
APPLICATION_RUN_NAME_PREFIX = "Scheduled Agent Application "
DISPATCH_RESULT_SCHEMA = "scheduled-agent-dispatch-result/v1"
_APPLICATION_WORKFLOW = "scheduled-agent-application.yml"
_DISPATCH_WORKFLOW = "scheduled-agent-bridge.yml"
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


@dataclass(frozen=True)
class ApplicationCompletion:
    state: Literal["NONE", "REJECTED", "RESUMABLE", "COMPLETE", "ABORTED", "INVALID", "AMBIGUOUS"]
    reason: str
    request_comment_id: int | None = None
    job_id: int | None = None
    qualified_carrier: QualifiedCarrierPlan | None = None
    recovery_artifact: ApplicationRecoveryArtifact | None = None


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


def _strictest_recovery_status(*statuses: RecoveryPredicate) -> RecoveryPredicate:
    for status in ("CONFLICT", "UNKNOWN", "INCOMPLETE", "COMPLETE"):
        if status in statuses:
            return cast(RecoveryPredicate, status)
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


_RECOVERY_CORRECTION_FILES = frozenset(
    {
        ".github/workflows/scheduled-agent-application.yml",
        "openspec/changes/restore-no-work-idle-discovery/tasks.md",
        "src/investment_strategy/issue_comment_bridge.py",
        "src/investment_strategy/scheduled_agent_effects.py",
        "src/investment_strategy/scheduled_agent_formal_qualification.py",
        "src/investment_strategy/scheduled_agent_idle_admission.py",
        "src/investment_strategy/scheduled_agent_merge_acceptance.py",
        "tests/fixtures/issue322-application-recovery.json",
        "tests/test_issue_comment_bridge.py",
        "tests/test_scheduled_agent_effects.py",
        "tests/test_scheduled_agent_formal_qualification.py",
        "tests/test_scheduled_agent_idle_admission.py",
    }
)
_RECOVERY_NECESSARY_EXECUTABLE_FILES = frozenset(
    {
        "src/investment_strategy/issue_comment_bridge.py",
        "src/investment_strategy/scheduled_agent_effects.py",
        "tests/test_issue_comment_bridge.py",
        "tests/test_scheduled_agent_effects.py",
    }
)


def _recovery_correction_disposition(
    repository: str,
    token: str,
    *,
    reviewed_revision: str | None,
    head_sha: str,
    task_blob_sha: str,
    read: GitHubReader,
) -> RecoveryPredicate:
    """Observe the actual corrective Git consequence, not its task checkbox.

    The separately Human-authorized, content-addressed corrections have no
    new normal Action/worker manifest. The immutable reviewed revision is the
    source preimage, the PR head/tree is T_new, and the complete Git compare
    plus exact tree blob identities is W_new. This does not certify old effects.
    """
    if reviewed_revision is None or _SHA.fullmatch(reviewed_revision) is None:
        return "UNKNOWN"
    if reviewed_revision == head_sha:
        return "INCOMPLETE"
    comparison = read(repository, token, f"compare/{reviewed_revision}...{head_sha}")
    commit = read(repository, token, f"git/commits/{head_sha}")
    if not isinstance(comparison, Mapping) or not isinstance(commit, Mapping):
        return "UNKNOWN"
    parents = commit.get("parents")
    tree_ref = commit.get("tree")
    tree_sha = tree_ref.get("sha") if isinstance(tree_ref, Mapping) else None
    if (
        commit.get("sha") != head_sha
        or not isinstance(parents, list)
        or not parents
        or not all(
            isinstance(parent, Mapping)
            and isinstance(parent.get("sha"), str)
            and _SHA.fullmatch(parent["sha"]) is not None
            for parent in parents
        )
        or not isinstance(tree_sha, str)
        or _SHA.fullmatch(tree_sha) is None
    ):
        return "CONFLICT"
    listing = read(repository, token, f"git/trees/{tree_sha}?recursive=1")
    if (
        not isinstance(listing, Mapping)
        or listing.get("truncated") is not False
        or not isinstance(listing.get("tree"), list)
    ):
        return "UNKNOWN"
    blobs: dict[str, str] = {}
    for item in listing["tree"]:
        if not isinstance(item, Mapping):
            return "UNKNOWN"
        path, sha = item.get("path"), item.get("sha")
        if item.get("type") == "blob" and isinstance(path, str):
            if path in blobs or not isinstance(sha, str) or _SHA.fullmatch(sha) is None:
                return "CONFLICT"
            blobs[path] = sha
    if blobs.get("openspec/changes/restore-no-work-idle-discovery/tasks.md") != task_blob_sha:
        return "CONFLICT"
    files = comparison.get("files")
    commits = comparison.get("commits")
    ahead = comparison.get("ahead_by")
    base = comparison.get("base_commit")
    if (
        comparison.get("status") != "ahead"
        or not isinstance(base, Mapping)
        or base.get("sha") != reviewed_revision
    ):
        return "CONFLICT"
    if (
        not isinstance(files, list)
        or not isinstance(commits, list)
        or not isinstance(ahead, int)
        or ahead < 1
        or ahead > 250
        or len(commits) != ahead
        or len(files) >= 300  # GitHub compare truncates changed files at 300.
    ):
        return "UNKNOWN"
    changed: set[str] = set()
    for file in files:
        if not isinstance(file, Mapping):
            return "UNKNOWN"
        path, sha = file.get("filename"), file.get("sha")
        if not isinstance(path, str) or not isinstance(sha, str) or _SHA.fullmatch(sha) is None:
            return "UNKNOWN"
        if path in changed or file.get("status") != "modified":
            return "CONFLICT"
        if blobs.get(path) != sha:
            return "CONFLICT"
        changed.add(path)
    # Verified disjoint descendant changes are not obsolete-SHA blockers.
    # Only the bounded correction paths count as its materialization witness;
    # this recovery writes no repository files and cannot overwrite others.
    correction_changes = changed & _RECOVERY_CORRECTION_FILES
    if not _RECOVERY_NECESSARY_EXECUTABLE_FILES.issubset(correction_changes):
        return "INCOMPLETE"
    return "COMPLETE"


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

    pr = read(repository, token, "pulls/340")
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
            pr.get("number") != 340
            or not (open_carrier or merged_carrier)
            or pr.get("draft") is not False
            or not isinstance(head_sha, str)
            or _SHA.fullmatch(head_sha) is None
            or head_ref != "agent/report-materialization-postcondition-failure"
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
            and record.request_comment_id == _ORIGINAL_322_REQUEST
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
        )
    except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return ApplicationCompletion(
            "INVALID", "recovery-exit-authoritative-source-unavailable", _ORIGINAL_322_REQUEST
        )
    if evidence.disposition != "COMPLETE":
        return ApplicationCompletion(
            "INVALID",
            f"recovery-exit-{evidence.disposition.lower()}-"
            + ",".join(evidence.blocking_predicates),
            _ORIGINAL_322_REQUEST,
        )
    current_observation = normalize_github_issue(issue)
    if current_observation is None:
        return ApplicationCompletion("INVALID", "recovery-exit-frontier-unknown")
    if current_observation.routing == ("reviewer", "review-implementation"):
        # Only the already-proven formal result and successor may be observed;
        # this path performs zero writes after an ambiguous/lost response.
        return ApplicationCompletion(
            "COMPLETE", "recovery-exit-existing-formal-successor", _ORIGINAL_322_REQUEST
        )
    if current_observation.routing != ("executor", "implement-change"):
        return ApplicationCompletion("INVALID", "recovery-exit-frontier-conflict")

    already_formal = any(
        isinstance(item.get("body"), str)
        and cast(str, item["body"]).splitlines()[:1] == ["ACTION_RESULT"]
        and f"application:{_ORIGINAL_322_REQUEST}:322:" in cast(str, item["body"])
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
                f"application:{_ORIGINAL_322_REQUEST}:322:{record.change}:"
                "executor:implement-change:ready:"
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
        )
    except (HTTPError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return ApplicationCompletion("INVALID", "recovery-exit-postcondition-unavailable")
    if post.disposition != "COMPLETE":
        return ApplicationCompletion("INVALID", "recovery-exit-postcondition-unqualified")
    observation = normalize_github_issue(final_issue)
    if observation is None or observation.routing != ("reviewer", "review-implementation"):
        return ApplicationCompletion("INVALID", "recovery-exit-successor-not-observed")
    return ApplicationCompletion("COMPLETE", "recovery-exit-formal-successor-observed")


PreacceptClassification = Literal[
    "ACCEPTED",
    "LIVE_PREACCEPT",
    "TERMINAL_NO_ACCEPT",
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
    lines = body.split("\n")
    if len(lines) != 2 or lines[0] != REQUEST_MARKER:
        return None
    if not lines[1].startswith(REQUESTED_AT_PREFIX):
        return None
    requested_at = lines[1][len(REQUESTED_AT_PREFIX) :]
    if not requested_at or requested_at != requested_at.strip():
        return None
    if body != f"{REQUEST_MARKER}\n{REQUESTED_AT_PREFIX}{requested_at}":
        return None
    return DispatchRequest(requested_at=requested_at)


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
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        raw = response.read()
    return None if not raw else json.loads(raw.decode("utf-8"))


def _paged_list(
    repository: str,
    token: str,
    api_path: str,
    *,
    read: GitHubReader,
) -> tuple[Mapping[str, object], ...]:
    items: list[Mapping[str, object]] = []
    page = 1
    separator = "&" if "?" in api_path else "?"
    while True:
        payload = read(repository, token, f"{api_path}{separator}per_page=100&page={page}")
        if not isinstance(payload, list):
            raise RuntimeError("application completion evidence list is incomplete")
        for raw in payload:
            if not isinstance(raw, Mapping):
                raise RuntimeError("application completion evidence list is malformed")
            items.append(cast(Mapping[str, object], raw))
        if len(payload) < 100:
            return tuple(items)
        page += 1


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
    user = comment.get("user")
    app = comment.get("performed_via_github_app")
    return (
        isinstance(user, Mapping)
        and user.get("login") == owner
        and isinstance(app, Mapping)
        and app.get("slug") == _CHATGPT_CONNECTOR_APP_SLUG
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
    if (
        decision.disposition != "FAIL_CLOSED"
        or decision.reason != "observations-unqualified"
        or preflight.human_authorized is not True
        or preflight.enumeration.incomplete_results
        or not preflight.enumeration.exhausted
        or preflight.enumeration.source_total_count is None
        or preflight.enumeration.observed_count != preflight.enumeration.source_total_count
    ):
        return None

    routed = tuple(
        issue for issue in preflight.issues if issue.state == "open" and issue.routing is not None
    )
    formal = tuple(issue for issue in routed if issue.change not in {"", "unset"})
    if len(formal) > 1:
        return None
    if formal:
        issue = formal[0]
    elif routed:
        issue = min(routed, key=lambda item: (item.created_order, item.issue_number))
    else:
        return None
    routing = issue.routing
    if routing is None:
        return None
    role, action = routing
    return WorkerRequest(issue.issue_number, role, action)


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


def _qualified_carrier_for_application_run(
    repository: str,
    token: str,
    request_comment_id: int,
    *,
    run: Mapping[str, object],
    run_id: int,
    run_attempt: int,
    job: Mapping[str, object],
    record: ApplicationDecisionRecord,
    read: GitHubReader,
) -> QualifiedCarrierPlan | None:
    """Recover one current-attempt carrier Artifact without replaying its producer."""

    artifacts_payload = read(repository, token, f"actions/runs/{run_id}/artifacts?per_page=100")
    if not isinstance(artifacts_payload, Mapping):
        raise RuntimeError("application carrier artifact listing is incomplete")
    raw_artifacts = artifacts_payload.get("artifacts")
    total_count = artifacts_payload.get("total_count")
    if (
        not isinstance(raw_artifacts, list)
        or isinstance(total_count, bool)
        or not isinstance(total_count, int)
        or total_count != len(raw_artifacts)
    ):
        raise RuntimeError("application carrier artifact listing is incomplete")
    artifacts = [
        cast(Mapping[str, object], item)
        for item in raw_artifacts
        if isinstance(item, Mapping) and item.get("name") == "carrier-plan.json"
    ]
    if not artifacts:
        return None
    if len(artifacts) != 1:
        raise RuntimeError("application carrier artifact identity is ambiguous")

    steps = job.get("steps")
    if not isinstance(steps, list):
        raise RuntimeError("application carrier job steps are incomplete")
    upload_steps = [
        cast(Mapping[str, object], step)
        for step in steps
        if isinstance(step, Mapping) and step.get("name") == "Upload exact external carrier plan"
    ]
    if len(upload_steps) != 1:
        raise RuntimeError("application carrier upload step identity is ambiguous")
    upload_conclusion = upload_steps[0].get("conclusion")
    if upload_conclusion == "skipped" and run_attempt > 1:
        return None
    if upload_conclusion != "success":
        raise RuntimeError("application carrier Artifact is not current-attempt evidence")

    artifact = artifacts[0]
    artifact_id = _positive_int(artifact.get("id"))
    digest = artifact.get("digest")
    workflow_run = artifact.get("workflow_run")
    if (
        artifact_id is None
        or artifact.get("expired") is not False
        or not isinstance(digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None
        or not isinstance(workflow_run, Mapping)
        or workflow_run.get("id") != run_id
        or workflow_run.get("head_sha") != run.get("head_sha")
    ):
        raise RuntimeError("application carrier Artifact identity is invalid")

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
        or plan.change != record.change
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
) -> tuple[Mapping[str, object], ...] | None:
    """Read complete issue-comment runs without GitHub's filtered 1,000-run cap.

    GitHub caps event-filtered workflow-run searches at 1,000 results even when
    ``total_count`` reports more.  The unfiltered endpoint is paginated without
    that search cap.  Fetch its independent pages concurrently and fail closed
    if the run count changes while constructing the observation.
    """

    path = f"actions/workflows/{quote(workflow, safe='')}/runs"

    def page(number: int, *, filtered: bool) -> Mapping[str, object] | None:
        params: dict[str, str | int] = {"per_page": 100, "page": number}
        if filtered:
            params = {"event": "issue_comment", **params}
        payload = read(repository, token, f"{path}?{urlencode(params)}")
        if not isinstance(payload, Mapping) or not isinstance(payload.get("workflow_runs"), list):
            return None
        return payload

    first = page(1, filtered=True)
    if first is None:
        return None
    total_count = first.get("total_count")
    if type(total_count) is int and total_count > 1000:
        first = page(1, filtered=False)
        if first is None:
            return None
        unfiltered_count = first.get("total_count")
        if type(unfiltered_count) is not int or unfiltered_count < total_count:
            return None
        pages = (unfiltered_count + 99) // 100
        if pages == 0:
            return None
        with ThreadPoolExecutor(max_workers=min(8, pages)) as pool:
            remaining = tuple(pool.map(lambda n: page(n, filtered=False), range(2, pages + 1)))
        payloads = (first, *remaining)
        if any(
            payload is None
            or payload.get("total_count") != unfiltered_count
            or len(cast(list[object], payload["workflow_runs"]))
            != min(100, unfiltered_count - index * 100)
            for index, payload in enumerate(payloads)
        ):
            return None
        complete_runs: list[Mapping[str, object]] = []
        for payload in payloads:
            if payload is None:
                return None
            raw_runs = payload["workflow_runs"]
            if not isinstance(raw_runs, list):
                return None
            for run in raw_runs:
                if (
                    not isinstance(run, Mapping)
                    or type(run.get("id")) is not int
                    or not isinstance(run.get("event"), str)
                ):
                    return None
                complete_runs.append(cast(Mapping[str, object], run))
        ids = [cast(int, run["id"]) for run in complete_runs]
        if len(ids) != len(set(ids)):
            return None
        return tuple(run for run in complete_runs if run.get("event") == "issue_comment")

    if total_count is not None and (type(total_count) is not int or total_count < 0):
        return None
    if isinstance(total_count, int):
        count_pages = max(1, (total_count + 99) // 100)
        with ThreadPoolExecutor(max_workers=min(8, count_pages)) as pool:
            remaining = tuple(pool.map(lambda n: page(n, filtered=True), range(2, count_pages + 1)))
        payloads = (first, *remaining)
        filtered_runs: list[Mapping[str, object]] = []
        for index, payload in enumerate(payloads):
            if payload is None or payload.get("total_count") != total_count:
                return None
            raw_runs = payload["workflow_runs"]
            if not isinstance(raw_runs, list) or len(raw_runs) != min(
                100, total_count - index * 100
            ):
                return None
            for run in raw_runs:
                if not isinstance(run, Mapping) or type(run.get("id")) is not int:
                    return None
                filtered_runs.append(cast(Mapping[str, object], run))
        ids = [cast(int, run["id"]) for run in filtered_runs]
        if len(ids) != len(set(ids)):
            return None
        return tuple(filtered_runs)

    # Legacy injected readers may omit the GitHub total_count field. A short
    # final page is still an explicit pagination terminator, but the search
    # cannot prove completeness at GitHub's 1,000-result filtered cap.
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
        if not isinstance(artifacts_payload, Mapping):
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        raw_artifacts = artifacts_payload.get("artifacts")
        total_count = artifacts_payload.get("total_count")
        if (
            not isinstance(raw_artifacts, list)
            or isinstance(total_count, bool)
            or not isinstance(total_count, int)
            or total_count != len(raw_artifacts)
        ):
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        artifacts = [
            cast(Mapping[str, object], item)
            for item in raw_artifacts
            if isinstance(item, Mapping) and item.get("name") == "dispatch-result.json"
        ]
        if len(artifacts) != 1:
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
        artifact = artifacts[0]
        artifact_id = _positive_int(artifact.get("id"))
        digest = artifact.get("digest")
        workflow_run = artifact.get("workflow_run")
        if (
            artifact_id is None
            or artifact.get("expired") is not False
            or not isinstance(digest, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None
            or not isinstance(workflow_run, Mapping)
            or workflow_run.get("id") != run_id
            or workflow_run.get("head_sha") != run.get("head_sha")
        ):
            return "application-completion-carrier-prior-dispatch-artifact-unavailable"
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
    jobs_payload = read(repository, token, f"actions/runs/{run_id}/jobs")
    if not isinstance(jobs_payload, Mapping) or not isinstance(jobs_payload.get("jobs"), list):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-job-list-incomplete",
            request_comment_id=request_comment_id,
        )
    jobs = [
        item
        for item in cast(list[object], jobs_payload["jobs"])
        if isinstance(item, Mapping) and item.get("name") == "apply"
    ]
    if len(jobs) != 1:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-job-identity-ambiguous",
            request_comment_id=request_comment_id,
        )
    job = cast(Mapping[str, object], jobs[0])
    job_id = _positive_int(job.get("id"))
    if job_id is None:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-job-identity-incomplete",
            request_comment_id=request_comment_id,
        )

    recovery_artifact = None
    if (
        record is not None
        and accepted_decision_sha256 is not None
        and isinstance(run.get("head_sha"), str)
    ):
        try:
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
        steps = job.get("steps")
        legacy_no_upload_step = (
            record is not None
            and accepted_decision_sha256 is not None
            and job.get("status") == "completed"
            and job.get("conclusion") == "failure"
            and isinstance(steps, list)
            and any(
                isinstance(step, Mapping)
                and step.get("name") == "Freshly authorize and apply repository-owned effects"
                and step.get("conclusion") == "failure"
                for step in steps
            )
            and not any(
                isinstance(step, Mapping)
                and step.get("name")
                in {
                    "Upload exact application recovery evidence",
                    "Upload final exact application recovery evidence",
                }
                for step in steps
            )
            and any(
                isinstance(step, Mapping) and step.get("name") == "Complete job" for step in steps
            )
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
            if not recovery_artifact.continuation_eligible:
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

    if not recovery_artifact.continuation_eligible:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-recovery-boundary-unsafe",
            request_comment_id=request_comment_id,
            recovery_artifact=recovery_artifact,
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
    jobs_payload = read(repository, token, f"actions/runs/{run_id}/jobs")
    if not isinstance(jobs_payload, Mapping) or not isinstance(jobs_payload.get("jobs"), list):
        return ApplicationCompletion(
            "INVALID",
            "application-completion-terminal-job-evidence-incomplete",
            request_comment_id=request_comment_id,
        )
    raw_jobs = cast(list[object], jobs_payload["jobs"])
    jobs = [item for item in raw_jobs if isinstance(item, Mapping) and item.get("name") == "apply"]
    if not jobs:
        # Capacity cancellation can finish before GitHub creates an apply job.
        # Only a complete first-attempt inventory proves zero apply executions.
        total_count = jobs_payload.get("total_count")
        job_ids = [
            _positive_int(item.get("id")) if isinstance(item, Mapping) else None
            for item in raw_jobs
        ]
        if (
            conclusion in {"cancelled", "timed_out", "skipped"}
            and _positive_int(run.get("run_attempt")) == 1
            and type(total_count) is int
            and total_count == len(raw_jobs)
            and all(job_id is not None for job_id in job_ids)
            and len(set(job_ids)) == len(raw_jobs)
            and all(
                isinstance(item, Mapping) and isinstance(item.get("name"), str) for item in raw_jobs
            )
        ):
            return ApplicationCompletion(
                "REJECTED",
                "application-completion-preaccept-terminal-no-accept",
                request_comment_id=request_comment_id,
            )
    if len(jobs) != 1:
        return ApplicationCompletion(
            "INVALID",
            "application-completion-terminal-job-identity-ambiguous",
            request_comment_id=request_comment_id,
        )
    apply_job = jobs[0]
    if (
        apply_job.get("status") != "completed"
        or apply_job.get("conclusion") not in _TERMINAL_NO_ACCEPT_CONCLUSIONS
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
) -> bool:
    """Use the single positive consequence owner for logical commit."""

    return consequence_postconditions_complete(
        raw_worker_result,
        source=source,
        repository=repository,
        token=token,
        current_revision=current_revision,
        accepted_authorization_revision=accepted_authorization_revision,
        authorized_change=authorized_change,
        request_comment_id=request_comment_id,
        # This read follows accepted-intent and formal-correlation qualification.
        # The canonical materialization observer may therefore reconstruct an
        # exact disjoint pending continuation from its original accepted base.
        allow_pending_continuation=True,
        # The formal result has already qualified the exact successor frontier.
        # Let the postcondition observer bind that same immutable intent after
        # the normal routing transition, without widening source authority.
        allow_accepted_successor=True,
        accepted_intent=True,
    )


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
    # An accepted semantic intent may intentionally have no worker-owned
    # requested effects.  New application-owned envelopes carry an explicit
    # semantic-intent marker so Phase B still resumes their job; historical
    # raw envelopes remain compatible with the old formal-only fixtures.
    if worker.requested_effects or semantic_intent:
        resumed = _application_job(
            repository,
            token,
            record.request_comment_id,
            read=read,
            record=record,
            transport_comment_ids=continuation_transport_comment_ids,
            accepted_decision_sha256=accepted_decision_sha256,
            recent_comments=recent_comments,
            current_dispatch_request_comment_id=current_dispatch_request_comment_id,
        )
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
        )
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
    """Bind one ingress to the derived current occurrence.

    Formal routes use the latest qualified consequence comment as their causal
    boundary.  A first pre-activation route has no such consequence, so it
    uses the active Issue-timeline routing admission.  Missing admission or
    ambiguous timing never widens the occurrence to repository history.
    """

    boundary = _frontier_comment_id(frontier)
    if boundary is not None:
        return request_comment_id > boundary
    if frontier is None or frontier.occurrence_anchor is None:
        return False
    anchor_time = frontier.occurrence_anchor.created_at
    if anchor_time is None:
        return False
    # A missing ingress timestamp is an incomplete current-source observation;
    # retain it for fail-closed classification rather than treating it as old.
    return occurrence_created_at is None or occurrence_created_at > anchor_time


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
    predecessor_evidence: ApplicationRecoveryArtifact | None = None,
    read: GitHubReader = _github_json,
) -> str | None:
    """Render one exact continuation transport for a qualified predecessor."""

    if predecessor_evidence is None or not predecessor_evidence.continuation_eligible:
        return None
    if predecessor_evidence.failure_evidence_sha256 in cast(
        list[str], predecessor_evidence.document["prior_failure_evidence_sha256"]
    ):
        return None
    comments = _paged_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created&direction=asc",
        read=read,
    )
    matches: list[str] = []
    for comment in comments:
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
            matches.append(body)
    if len(matches) != 1:
        return None
    decision_sha256 = hashlib.sha256(matches[0].encode("utf-8")).hexdigest()
    if predecessor_evidence.accepted_decision_sha256 != decision_sha256:
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
    existing_correlations = {
        comment_id
        for item in comments
        if isinstance(item, Mapping)
        and isinstance(item.get("body"), str)
        and (comment_id := _positive_int(item.get("id"))) is not None
        and (existing := parse_application_continuation_request(cast(str, item.get("body"))))
        is not None
        and existing.continuation_correlation == parsed_body.continuation_correlation
    }
    if existing_correlations:
        return None
    if parse_application_continuation_request(body) is None:
        raise RuntimeError("rendered application continuation is not parseable")
    return body


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
    now: datetime | None = None,
) -> ApplicationCompletion:
    """Return one exhaustive consequence disposition from durable evidence."""

    current_time = datetime.now(UTC) if now is None else now.astimezone(UTC)
    owner = repository.split("/", 1)[0]
    since = (current_time - timedelta(days=30)).isoformat(timespec="seconds").replace("+00:00", "Z")
    recent = _paged_list(
        repository,
        token,
        f"issues/comments?{urlencode({'sort': 'created', 'direction': 'asc', 'since': since})}",
        read=read,
    )
    issue_comments = _paged_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created&direction=asc",
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
    for comment in (*recent, *issue_comments):
        if not _trusted_connector_comment(comment, owner):
            continue
        body = comment.get("body")
        if not isinstance(body, str) or body.splitlines()[:1] != ["EFFECT_REQUEST"]:
            continue

        # Transport history is repository-wide, but application completion is
        # exact-source-local.  Legacy envelopes use their carried source; the
        # post-protocol semantic envelope uses one opaque dispatch correlation.
        # A semantic envelope with neither is unresolved evidence and therefore
        # fails closed instead of being guessed into the current Action.
        source_hint = _effect_request_source_hint(body)
        legacy_source_hint = _legacy_raw_source_hint(body)
        encoded_source_identity = _legacy_encoded_source_identity(body)
        comment_id = _positive_int(comment.get("id"))
        if comment_id is None:
            invalid_request_ids.add(-1)
            continue
        ingress_created_at[comment_id] = _comment_time(comment)
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

    if (
        not relevant_decisions
        and not candidates
        and not invalid_request_ids
        and not unbound_request_ids
        and not any(
            parse_formal_result(comment, current_revision=current_revision) is not None
            for comment in issue_comments
        )
    ):
        return ApplicationCompletion("NONE", "application-completion-none")

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
        ):
            resumed = _accepted_application_state(
                repository=repository,
                token=token,
                source=source,
                record=current_accepted[0],
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
                    source=source,
                    record=current_accepted[0],
                    issue_comments=issue_comments,
                    recent_comments=runtime_comments,
                ),
            )
            if resumed.state != "NONE":
                return resumed
        elif len(current_accepted) > 1:
            return ApplicationCompletion(
                "AMBIGUOUS",
                "application-completion-invalid-frontier-accepted-intents-ambiguous",
            )
        return ApplicationCompletion("INVALID", "application-completion-current-frontier-invalid")

    decisions_by_request: dict[int, tuple[ApplicationDecisionRecord, ...]] = {}
    decision_created_at: dict[int, str | None] = {}
    for comment in issue_comments:
        record = parse_application_decision(comment.get("body"))
        if record is None:
            continue
        decisions_by_request.setdefault(record.request_comment_id, ())
        decisions_by_request[record.request_comment_id] = (
            *decisions_by_request[record.request_comment_id],
            record,
        )
        decision_created_at[record.request_comment_id] = _comment_time(comment)

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
        frontier_completion = _accepted_application_state(
            repository=repository,
            token=token,
            source=frontier_source,
            record=frontier_owner,
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
                source=frontier_source,
                record=frontier_owner,
                issue_comments=issue_comments,
                recent_comments=runtime_comments,
            ),
        )
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
    accepted = [record for record in relevant_decisions if record.disposition == "ACCEPTED"]
    accepted_request_ids = {record.request_comment_id for record in accepted}
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
    if len(accepted) > 1:
        return ApplicationCompletion("AMBIGUOUS", "application-completion-accepted-ambiguous")
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
    return _accepted_application_state(
        repository=repository,
        token=token,
        source=source,
        record=record,
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
            source=source,
            record=record,
            issue_comments=issue_comments,
            recent_comments=runtime_comments,
        ),
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
) -> BridgePlan:
    identity = _request_identity(event)
    if identity is None:
        return BridgePlan(False)
    issue_number, request_comment_id = identity
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
    )


def acquire_production_dispatch_decision(repository: str, token: str) -> DispatchDecision:
    return classify_dispatch(acquire_current_github_preflight(repository, token))


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a JSON object")
    return cast(Mapping[str, object], value)


def _write_outputs(path: Path, plan: BridgePlan) -> None:
    lines = [f"should_emit={'true' if plan.should_emit else 'false'}"]
    if plan.issue_number is not None:
        lines.append(f"issue_number={plan.issue_number}")
    if plan.request_comment_id is not None:
        lines.append(f"request_comment_id={plan.request_comment_id}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_result_payload(path: Path, plan: BridgePlan) -> None:
    if plan.should_emit and plan.result_body is not None:
        path.write_text(plan.result_body + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan one run-scoped dispatch result")
    parser.add_argument("--event-path", type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--result-payload", type=Path)
    parser.add_argument("--recovery-exit-request-comment-id", type=int)
    args = parser.parse_args()

    if args.recovery_exit_request_comment_id is not None:
        if (
            args.recovery_exit_request_comment_id != _ORIGINAL_322_REQUEST
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
        completion = apply_original_322_recovery_exit(
            repository, token, current_revision=args.revision
        )
        print(f"recovery_exit={completion.state}; reason={completion.reason}")
        return 0 if completion.state == "COMPLETE" else 1

    if args.event_path is None or args.github_output is None or args.result_payload is None:
        parser.error("dispatch requires --event-path, --github-output and --result-payload")

    event = _require_mapping(json.loads(args.event_path.read_text(encoding="utf-8")), "event")
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
        completion = (
            ApplicationCompletion("NONE", "application-completion-none")
            if source is None
            else qualify_application_completion(
                repository,
                token,
                source=source,
                current_revision=args.revision,
                current_dispatch_request_comment_id=identity[1],
                current_dispatch_issue_number=identity[0],
            )
        )
        continuation_body = None
        if completion.state in {"RESUMABLE", "INVALID", "AMBIGUOUS"}:
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
        )
    _write_outputs(args.github_output, plan)
    _write_result_payload(args.result_payload, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
