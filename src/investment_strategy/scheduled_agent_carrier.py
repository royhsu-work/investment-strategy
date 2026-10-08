"""Bounded immutable plans for identity-sensitive external GitHub carriers."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_REDIRECT_HOST = re.compile(
    r"^(?:[a-z0-9-]+\.actions\.githubusercontent\.com|productionresultssa[0-9]+\.blob\.core\.windows\.net)$"
)
_MAX_CARRIER_ARTIFACT_BYTES = 65_536


class _NoRedirect(HTTPRedirectHandler):
    """Expose a signed GitHub artifact redirect without forwarding the API bearer token."""

    def http_error_302(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
    ) -> None:
        raise HTTPError(req.full_url, code, msg, headers, fp)


def read_github_artifact_bytes(repository: str, token: str, api_path: str) -> bytes:
    """Read one GitHub Actions artifact without leaking the API bearer across redirects."""

    if _REPOSITORY.fullmatch(repository) is None or not token:
        raise RuntimeError("repository/token identity is invalid")
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        headers={
            "Accept": "application/octet-stream",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with build_opener(_NoRedirect).open(request, timeout=30) as response:
            raw = response.read(_MAX_CARRIER_ARTIFACT_BYTES + 1)
    except HTTPError as exc:
        if exc.code != 302:
            raise RuntimeError("exact GitHub artifact read failed") from exc
        location = exc.headers.get("Location")
        if not isinstance(location, str):
            raise RuntimeError("exact GitHub artifact redirect is not trusted") from exc
        parsed = urlsplit(location)
        host = parsed.hostname.lower() if parsed.hostname is not None else None
        if (
            parsed.scheme != "https"
            or host is None
            or _ARTIFACT_REDIRECT_HOST.fullmatch(host) is None
        ):
            raise RuntimeError("exact GitHub artifact redirect is not trusted") from exc
        redirected = Request(  # noqa: S310 - validated GitHub Actions host
            location,
            headers={"Accept": "application/octet-stream"},
        )
        try:
            with build_opener().open(redirected, timeout=30) as response:
                raw = response.read(_MAX_CARRIER_ARTIFACT_BYTES + 1)
        except (HTTPError, URLError, TimeoutError) as redirect_exc:
            raise RuntimeError("exact GitHub artifact response is invalid") from redirect_exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("exact GitHub artifact response is invalid") from exc
    if not raw or len(raw) > _MAX_CARRIER_ARTIFACT_BYTES:
        raise RuntimeError("exact GitHub artifact size is invalid")
    return raw


@dataclass(frozen=True)
class CarrierPlan:
    """Exact application-authorized mutation plan for one replaceable carrier."""

    plan_id: str
    correlation: str
    repository: str
    issue_number: int
    change: str
    action: str
    authorization_revision: str
    operation: str
    target: Mapping[str, object]
    expected: Mapping[str, object]
    requested: Mapping[str, object]
    force: bool
    expected_postcondition: Mapping[str, object]


@dataclass(frozen=True)
class QualifiedCarrierPlan:
    """Run-bound proof that one immutable carrier plan is the pending application effect."""

    request_comment_id: int
    run_id: int
    run_attempt: int
    artifact_id: int
    artifact_digest: str
    plan: CarrierPlan



CarrierOutcomeKind = Literal["COMPLETE", "REFUSED", "ERROR", "UNKNOWN"]
CarrierMutationStatus = Literal["NO_WRITE", "COMPLETED", "UNKNOWN"]
CarrierPrecondition = Literal["MATCH", "MISMATCH", "UNKNOWN", "NOT_REQUIRED"]
CarrierPostcondition = Literal["COMPLETE", "INCOMPLETE", "UNKNOWN"]
CarrierUnfinishedBoundary = Literal["none", "precondition-read", "carrier-operation", "postcondition-read"]

_CARRIER_OUTCOME_SCHEMA = "application-carrier-outcome/v1"
_CARRIER_OUTCOME_MARKER = "APPLICATION_CARRIER_OUTCOME"
_CARRIER_OUTCOME_OPERATIONS = frozenset(
    {
        "pull-request-create",
        "pull-request-update",
        "pull-request-ready",
        "pull-request-merge",
        "pull-request-head-update",
    }
)
_CARRIER_OUTCOME_FAILURE_CODES = frozenset(
    {
        "none",
        "precondition-mismatch",
        "connector-unavailable",
        "connector-refused",
        "write-outcome-unknown",
        "postcondition-mismatch",
        "postcondition-unavailable",
    }
)
_CARRIER_OUTCOME_FIELDS = (
    ("Schema", "schema"),
    ("Repository", "repository"),
    ("Issue", "issue_number"),
    ("Request-Comment", "request_comment_id"),
    ("Accepted-Decision-SHA256", "accepted_decision_sha256"),
    ("Continuation-Correlation", "continuation_correlation"),
    ("Predecessor-Run-ID", "predecessor_run_id"),
    ("Predecessor-Run-Attempt", "predecessor_run_attempt"),
    ("Predecessor-Job-ID", "predecessor_job_id"),
    ("Recovery-Artifact-ID", "recovery_artifact_id"),
    ("Recovery-Artifact-Digest", "recovery_artifact_digest"),
    ("Failure-Evidence-SHA256", "failure_evidence_sha256"),
    ("Recovery-Episode-SHA256", "recovery_episode_sha256"),
    ("Carrier-Artifact-ID", "carrier_artifact_id"),
    ("Carrier-Artifact-Digest", "carrier_artifact_digest"),
    ("Plan-ID", "plan_id"),
    ("Operation", "operation"),
    ("Outcome", "outcome"),
    ("Mutation-Status", "mutation_status"),
    ("Precondition", "precondition"),
    ("Observed-Precondition-JSON-B64", "observed_precondition_json_b64"),
    ("Postcondition", "postcondition"),
    ("Unfinished-Boundary", "unfinished_boundary"),
    ("Failure-Code", "failure_code"),
    ("Failure-Summary", "failure_summary"),
)


@dataclass(frozen=True)
class CarrierOutcomeReport:
    """Durable, non-authorizing result of one exact external carrier handoff."""

    repository: str
    issue_number: int
    request_comment_id: int
    accepted_decision_sha256: str
    continuation_correlation: str
    predecessor_run_id: int
    predecessor_run_attempt: int
    predecessor_job_id: int
    recovery_artifact_id: int
    recovery_artifact_digest: str
    failure_evidence_sha256: str
    recovery_episode_sha256: str
    carrier_artifact_id: int
    carrier_artifact_digest: str
    plan_id: str
    operation: str
    outcome: CarrierOutcomeKind
    mutation_status: CarrierMutationStatus
    precondition: CarrierPrecondition
    observed_precondition_json: str | None
    postcondition: CarrierPostcondition
    unfinished_boundary: CarrierUnfinishedBoundary
    failure_code: str
    failure_summary: str


def render_carrier_outcome_report(report: CarrierOutcomeReport) -> str:
    """Render the exact transport evidence schema consumed by the dispatcher."""

    observed_precondition_b64 = (
        "none"
        if report.observed_precondition_json is None
        else base64.urlsafe_b64encode(
            report.observed_precondition_json.encode("utf-8")
        ).decode("ascii").rstrip("=")
    )
    body = "\n".join(
        (
            _CARRIER_OUTCOME_MARKER,
            f"Schema: {_CARRIER_OUTCOME_SCHEMA}",
            f"Repository: {report.repository}",
            f"Issue: {report.issue_number}",
            f"Request-Comment: {report.request_comment_id}",
            f"Accepted-Decision-SHA256: {report.accepted_decision_sha256}",
            f"Continuation-Correlation: {report.continuation_correlation}",
            f"Predecessor-Run-ID: {report.predecessor_run_id}",
            f"Predecessor-Run-Attempt: {report.predecessor_run_attempt}",
            f"Predecessor-Job-ID: {report.predecessor_job_id}",
            f"Recovery-Artifact-ID: {report.recovery_artifact_id}",
            f"Recovery-Artifact-Digest: {report.recovery_artifact_digest}",
            f"Failure-Evidence-SHA256: {report.failure_evidence_sha256}",
            f"Recovery-Episode-SHA256: {report.recovery_episode_sha256}",
            f"Carrier-Artifact-ID: {report.carrier_artifact_id}",
            f"Carrier-Artifact-Digest: {report.carrier_artifact_digest}",
            f"Plan-ID: {report.plan_id}",
            f"Operation: {report.operation}",
            f"Outcome: {report.outcome}",
            f"Mutation-Status: {report.mutation_status}",
            f"Precondition: {report.precondition}",
            f"Observed-Precondition-JSON-B64: {observed_precondition_b64}",
            f"Postcondition: {report.postcondition}",
            f"Unfinished-Boundary: {report.unfinished_boundary}",
            f"Failure-Code: {report.failure_code}",
            f"Failure-Summary: {report.failure_summary}",
        )
    )
    if parse_carrier_outcome_report(body) != report:
        raise ValueError("carrier outcome report identity or status is invalid")
    return body


def parse_carrier_outcome_report(body: object) -> CarrierOutcomeReport | None:
    """Parse one exact, bounded carrier result without granting it authority."""

    if not isinstance(body, str) or "\r" in body:
        return None
    lines = body.split("\n")
    if len(lines) != len(_CARRIER_OUTCOME_FIELDS) + 1 or lines[0] != _CARRIER_OUTCOME_MARKER:
        return None
    values: dict[str, str] = {}
    for line, (header, field) in zip(lines[1:], _CARRIER_OUTCOME_FIELDS, strict=True):
        prefix = f"{header}: "
        if not line.startswith(prefix):
            return None
        value = line[len(prefix) :]
        if not value or value.strip() != value:
            return None
        values[field] = value
    if values.get("schema") != _CARRIER_OUTCOME_SCHEMA:
        return None
    repository = values["repository"]
    if _REPOSITORY.fullmatch(repository) is None:
        return None
    decimal_fields = (
        "issue_number",
        "request_comment_id",
        "predecessor_run_id",
        "predecessor_run_attempt",
        "predecessor_job_id",
        "recovery_artifact_id",
        "carrier_artifact_id",
    )
    parsed_ids: dict[str, int] = {}
    for field in decimal_fields:
        raw = values[field]
        if re.fullmatch(r"[1-9][0-9]*", raw) is None:
            return None
        parsed_ids[field] = int(raw)
    for field in (
        "accepted_decision_sha256",
        "continuation_correlation",
        "failure_evidence_sha256",
        "recovery_episode_sha256",
    ):
        if _SHA256.fullmatch(values[field]) is None:
            return None
    for field in ("recovery_artifact_digest", "carrier_artifact_digest"):
        if re.fullmatch(r"sha256:[0-9a-f]{64}", values[field]) is None:
            return None
    plan_id = values["plan_id"]
    if not plan_id.startswith("carrier-plan-") or _SHA256.fullmatch(
        plan_id.removeprefix("carrier-plan-")
    ) is None:
        return None
    operation = values["operation"]
    if operation not in _CARRIER_OUTCOME_OPERATIONS:
        return None
    outcome = values["outcome"]
    mutation_status = values["mutation_status"]
    precondition = values["precondition"]
    observed_encoded = values["observed_precondition_json_b64"]
    postcondition = values["postcondition"]
    unfinished_boundary = values["unfinished_boundary"]
    failure_code = values["failure_code"]
    failure_summary = values["failure_summary"]
    if precondition not in {"MATCH", "MISMATCH", "UNKNOWN", "NOT_REQUIRED"}:
        return None
    if unfinished_boundary not in {
        "none",
        "precondition-read",
        "carrier-operation",
        "postcondition-read",
    }:
        return None
    observed_precondition_json = None
    if observed_encoded != "none":
        if (
            len(observed_encoded) > 21846
            or re.fullmatch(r"[A-Za-z0-9_-]+", observed_encoded) is None
        ):
            return None
        try:
            observed_raw = base64.urlsafe_b64decode(
                observed_encoded + "=" * (-len(observed_encoded) % 4)
            )
            observed_value = json.loads(observed_raw)
        except (UnicodeError, ValueError, json.JSONDecodeError):
            return None
        if (
            len(observed_raw) > 16_384
            or not isinstance(observed_value, dict)
            or any(not isinstance(key, str) for key in observed_value)
        ):
            return None
        observed_precondition_json = json.dumps(
            observed_value, sort_keys=True, separators=(",", ":")
        )
        if observed_raw.decode("utf-8") != observed_precondition_json:
            return None
    if (precondition in {"MATCH", "MISMATCH"}) != (
        observed_precondition_json is not None
    ) or (outcome != "COMPLETE" and unfinished_boundary == "none"):
        return None
    if (
        outcome not in {"COMPLETE", "REFUSED", "ERROR", "UNKNOWN"}
        or mutation_status not in {"NO_WRITE", "COMPLETED", "UNKNOWN"}
        or postcondition not in {"COMPLETE", "INCOMPLETE", "UNKNOWN"}
        or failure_code not in _CARRIER_OUTCOME_FAILURE_CODES
        or re.fullmatch(r"(?:none|[A-Za-z0-9][A-Za-z0-9 .,;:/_-]{0,159})", failure_summary)
        is None
        or re.search(r"(?i)(?:bearer\s|token[:=]|authorization[:=]|https?://)", failure_summary)
        is not None
    ):
        return None
    if outcome == "COMPLETE":
        if (
            mutation_status not in {"NO_WRITE", "COMPLETED"}
            or postcondition != "COMPLETE"
            or failure_code != "none"
            or failure_summary != "none"
            or unfinished_boundary != "none"
            or precondition not in {"MATCH", "NOT_REQUIRED"}
            or (mutation_status == "COMPLETED" and precondition != "MATCH")
        ):
            return None
    elif failure_code == "none" or failure_summary == "none" or postcondition == "COMPLETE":
        return None
    elif outcome == "REFUSED" and (
        mutation_status != "NO_WRITE" or postcondition not in {"INCOMPLETE", "UNKNOWN"}
    ):
        return None
    elif precondition in {"MISMATCH", "UNKNOWN"} and mutation_status != "NO_WRITE":
        return None
    elif precondition == "NOT_REQUIRED" and (
        outcome != "COMPLETE" or mutation_status != "NO_WRITE" or postcondition != "COMPLETE"
    ):
        return None
    elif outcome == "ERROR" and mutation_status == "COMPLETED":
        return None
    elif outcome == "UNKNOWN" and (
        mutation_status != "UNKNOWN" or postcondition != "UNKNOWN"
    ):
        return None
    return CarrierOutcomeReport(
        repository=repository,
        issue_number=parsed_ids["issue_number"],
        request_comment_id=parsed_ids["request_comment_id"],
        accepted_decision_sha256=values["accepted_decision_sha256"],
        continuation_correlation=values["continuation_correlation"],
        predecessor_run_id=parsed_ids["predecessor_run_id"],
        predecessor_run_attempt=parsed_ids["predecessor_run_attempt"],
        predecessor_job_id=parsed_ids["predecessor_job_id"],
        recovery_artifact_id=parsed_ids["recovery_artifact_id"],
        recovery_artifact_digest=values["recovery_artifact_digest"],
        failure_evidence_sha256=values["failure_evidence_sha256"],
        recovery_episode_sha256=values["recovery_episode_sha256"],
        carrier_artifact_id=parsed_ids["carrier_artifact_id"],
        carrier_artifact_digest=values["carrier_artifact_digest"],
        plan_id=plan_id,
        operation=operation,
        outcome=cast(CarrierOutcomeKind, outcome),
        mutation_status=cast(CarrierMutationStatus, mutation_status),
        precondition=cast(CarrierPrecondition, precondition),
        observed_precondition_json=observed_precondition_json,
        postcondition=cast(CarrierPostcondition, postcondition),
        unfinished_boundary=cast(CarrierUnfinishedBoundary, unfinished_boundary),
        failure_code=failure_code,
        failure_summary=failure_summary,
    )



CarrierQualification = Literal["COMPLETE", "ELIGIBLE", "BLOCKED", "UNKNOWN"]
CarrierConsumeResult = Literal["already-complete", "executed-complete", "reconciled-complete"]


class CarrierRequired(RuntimeError):
    """The application authorized a mutation but an external carrier must execute it."""

    def __init__(self, plan: CarrierPlan) -> None:
        super().__init__(f"carrier required: {plan.plan_id}")
        self.plan = plan


def make_carrier_plan(
    *,
    repository: str,
    issue_number: int,
    change: str,
    action: str,
    authorization_revision: str,
    operation: str,
    target: Mapping[str, object],
    expected: Mapping[str, object],
    requested: Mapping[str, object],
    expected_postcondition: Mapping[str, object],
) -> CarrierPlan:
    """Construct a content-addressed plan with no carrier or successor authority."""

    if len(authorization_revision) != 40 or any(
        character not in "0123456789abcdef" for character in authorization_revision
    ):
        raise ValueError("carrier plan authorization revision is invalid")
    material = {
        "repository": repository,
        "issue_number": issue_number,
        "change": change,
        "action": action,
        "authorization_revision": authorization_revision,
        "operation": operation,
        "target": dict(target),
        "expected": dict(expected),
        "requested": dict(requested),
        "force": False,
        "expected_postcondition": dict(expected_postcondition),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    plan_id = f"carrier-plan-{hashlib.sha256(encoded).hexdigest()}"
    return CarrierPlan(
        plan_id=plan_id,
        correlation=f"{plan_id}:effect-request-{issue_number}",
        repository=repository,
        issue_number=issue_number,
        change=change,
        action=action,
        authorization_revision=authorization_revision,
        operation=operation,
        target=dict(target),
        expected=dict(expected),
        requested=dict(requested),
        force=False,
        expected_postcondition=dict(expected_postcondition),
    )


def carrier_plan_document(plan: CarrierPlan) -> dict[str, object]:
    """Return the serialized plan surface used by workflow artifacts and carriers."""

    return {
        "plan_id": plan.plan_id,
        "correlation": plan.correlation,
        "repository": plan.repository,
        "issue_number": plan.issue_number,
        "change": plan.change,
        "action": plan.action,
        "authorization_revision": plan.authorization_revision,
        "operation": plan.operation,
        "target": dict(plan.target),
        "expected": dict(plan.expected),
        "requested": dict(plan.requested),
        "force": plan.force,
        "expected_postcondition": dict(plan.expected_postcondition),
    }


def parse_carrier_plan_document(document: object) -> CarrierPlan:
    """Strictly recover a content-addressed plan from durable JSON evidence."""

    if not isinstance(document, Mapping):
        raise ValueError("carrier plan document must be a JSON object")
    payload = cast(Mapping[str, object], document)
    expected_keys = {
        "plan_id",
        "correlation",
        "repository",
        "issue_number",
        "change",
        "action",
        "authorization_revision",
        "operation",
        "target",
        "expected",
        "requested",
        "force",
        "expected_postcondition",
    }
    if set(payload) != expected_keys:
        raise ValueError("carrier plan document schema is invalid")

    issue_number = payload.get("issue_number")
    if isinstance(issue_number, bool) or not isinstance(issue_number, int) or issue_number <= 0:
        raise ValueError("carrier plan Issue identity is invalid")
    repository = payload.get("repository")
    plan_id = payload.get("plan_id")
    correlation = payload.get("correlation")
    change = payload.get("change")
    action = payload.get("action")
    authorization_revision = payload.get("authorization_revision")
    operation = payload.get("operation")
    if (
        not isinstance(repository, str)
        or _REPOSITORY.fullmatch(repository) is None
        or not isinstance(plan_id, str)
        or not plan_id.startswith("carrier-plan-")
        or _SHA256.fullmatch(plan_id.removeprefix("carrier-plan-")) is None
        or not isinstance(correlation, str)
        or not isinstance(change, str)
        or not change
        or not isinstance(action, str)
        or not action
        or not isinstance(authorization_revision, str)
        or not isinstance(operation, str)
        or not operation
        or payload.get("force") is not False
    ):
        raise ValueError("carrier plan identity is invalid")
    mappings: dict[str, Mapping[str, object]] = {}
    for key in ("target", "expected", "requested", "expected_postcondition"):
        value = payload.get(key)
        if not isinstance(value, Mapping):
            raise ValueError(f"carrier plan {key} is invalid")
        mappings[key] = cast(Mapping[str, object], value)

    rebuilt = make_carrier_plan(
        repository=repository,
        issue_number=issue_number,
        change=change,
        action=action,
        authorization_revision=authorization_revision,
        operation=operation,
        target=mappings["target"],
        expected=mappings["expected"],
        requested=mappings["requested"],
        expected_postcondition=mappings["expected_postcondition"],
    )
    if (
        plan_id != rebuilt.plan_id
        or correlation != rebuilt.correlation
        or dict(payload) != carrier_plan_document(rebuilt)
    ):
        raise ValueError("carrier plan content address is invalid")
    return rebuilt


def qualified_carrier_document(qualified: QualifiedCarrierPlan) -> dict[str, object]:
    """Serialize exact run/attempt/artifact identity with its immutable plan."""

    return {
        "request_comment_id": qualified.request_comment_id,
        "run_id": qualified.run_id,
        "run_attempt": qualified.run_attempt,
        "artifact_id": qualified.artifact_id,
        "artifact_digest": qualified.artifact_digest,
        "plan": carrier_plan_document(qualified.plan),
    }


def parse_qualified_carrier_document(document: object) -> QualifiedCarrierPlan:
    """Strictly parse one run-bound carrier descriptor from a dispatch Artifact."""

    if not isinstance(document, Mapping):
        raise ValueError("qualified carrier descriptor must be a JSON object")
    payload = cast(Mapping[str, object], document)
    if set(payload) != {
        "request_comment_id",
        "run_id",
        "run_attempt",
        "artifact_id",
        "artifact_digest",
        "plan",
    }:
        raise ValueError("qualified carrier descriptor schema is invalid")
    values = tuple(
        payload.get(key) for key in ("request_comment_id", "run_id", "run_attempt", "artifact_id")
    )
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values):
        raise ValueError("qualified carrier descriptor identity is invalid")
    digest = payload.get("artifact_digest")
    if (
        not isinstance(digest, str)
        or not digest.startswith("sha256:")
        or _SHA256.fullmatch(digest.removeprefix("sha256:")) is None
    ):
        raise ValueError("qualified carrier artifact digest is invalid")
    return QualifiedCarrierPlan(
        request_comment_id=cast(int, values[0]),
        run_id=cast(int, values[1]),
        run_attempt=cast(int, values[2]),
        artifact_id=cast(int, values[3]),
        artifact_digest=digest,
        plan=parse_carrier_plan_document(payload.get("plan")),
    )


def consume_qualified_carrier(
    qualified: QualifiedCarrierPlan,
    *,
    qualify: Callable[[QualifiedCarrierPlan], CarrierQualification],
    connector: Callable[[CarrierPlan], None],
) -> CarrierConsumeResult:
    """Execute once after a fresh guard, reconciling an unknown write outcome read-only."""

    before = qualify(qualified)
    if before == "COMPLETE":
        return "already-complete"
    if before != "ELIGIBLE":
        raise RuntimeError(f"qualified carrier is not executable: {before}")
    try:
        connector(qualified.plan)
    except Exception:
        if qualify(qualified) == "COMPLETE":
            return "reconciled-complete"
        raise
    if qualify(qualified) != "COMPLETE":
        raise RuntimeError("carrier connector result is not durably complete")
    return "executed-complete"


def carrier_pr_identity(payload: Mapping[str, object]) -> dict[str, object]:
    """Capture only the immutable PR/ref identity relevant to a carrier plan."""

    head = payload.get("head")
    base = payload.get("base")
    head_mapping = head if isinstance(head, Mapping) else {}
    base_mapping = base if isinstance(base, Mapping) else {}
    head_repo = head_mapping.get("repo")
    base_repo = base_mapping.get("repo")
    head_repo_mapping = head_repo if isinstance(head_repo, Mapping) else {}
    base_repo_mapping = base_repo if isinstance(base_repo, Mapping) else {}
    return {
        "number": payload.get("number"),
        "state": payload.get("state"),
        "merged": payload.get("merged"),
        "draft": payload.get("draft"),
        "title": payload.get("title"),
        "body": payload.get("body"),
        "head": {
            "ref": head_mapping.get("ref"),
            "sha": head_mapping.get("sha"),
            "repo": head_repo_mapping.get("full_name"),
        },
        "base": {
            "ref": base_mapping.get("ref"),
            "sha": base_mapping.get("sha"),
            "repo": base_repo_mapping.get("full_name"),
        },
    }


__all__ = [
    "CarrierConsumeResult",
    "CarrierOutcomeKind",
    "CarrierOutcomeReport",
    "CarrierPrecondition",
    "CarrierUnfinishedBoundary",
    "CarrierMutationStatus",
    "CarrierPostcondition",
    "CarrierPlan",
    "CarrierQualification",
    "CarrierRequired",
    "QualifiedCarrierPlan",
    "carrier_plan_document",
    "carrier_pr_identity",
    "consume_qualified_carrier",
    "make_carrier_plan",
    "parse_carrier_plan_document",
    "parse_qualified_carrier_document",
    "qualified_carrier_document",
    "read_github_artifact_bytes",
]
