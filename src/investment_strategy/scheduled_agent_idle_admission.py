"""Typed NO_WORK handoff and repository-owned idle admission boundary.

The normal dispatcher remains Action-only.  This module is deliberately a
small non-Action boundary: a bootstrap can bind one successful, exact
``NO_WORK`` dispatch artifact to one bounded Lead result, and the repository
application can then admit at most one canonical Explore candidate.  The
request is transport evidence, not workflow state; all durable truth is
reconstructed from the current Issue and default branch.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_checkin import is_runtime_checkin_issue
from investment_strategy.scheduled_agent_dispatch_result import fetch_dispatch_result
from investment_strategy.scheduled_agent_runtime import acquire_current_github_preflight
from investment_strategy.workflow_dispatch import (
    DispatchDecision,
    ObservationProvenance,
    classify_dispatch,
)

IDLE_ENVELOPE_MARKER = "NO_WORK_IDLE_ENVELOPE"
IDLE_REQUEST_MARKER = "IDLE_ADMISSION_REQUEST"
IDLE_SCHEMA = "scheduled-agent-idle-admission/v1"
ACTION_EXPLORE_CHANGE = "action:explore-change"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_CORRELATION_LINE = re.compile(r"(?m)^Idle-Admission-Correlation:\s*(\S+)\s*$")
_SOURCE_REVISION_LINE = re.compile(r"(?m)^Idle-Source-Revision:\s*(\S+)\s*$")
_SOURCE_LINE = re.compile(r"(?m)^Idle-Source:\s*(\S+)\s*$")
_DISPATCH_RUN_PREFIX = "Scheduled Agent Dispatch "
_DISPATCH_ARTIFACT_NAME = "dispatch-result.json"
_DISPATCH_WORKFLOW_PATH = ".github/workflows/scheduled-agent-bridge.yml"
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"

IdleCandidateKind = Literal["no-finding", "existing", "new"]
IdleAdmissionState = Literal[
    "NO_FINDING",
    "ADMITTED",
    "ALREADY_ADMITTED",
    "STALE",
    "FAIL_CLOSED",
    "AMBIGUOUS",
    "INVALID",
]
GitHubReader = Callable[[str, str, str], object | None]
GitHubWriter = Callable[[str, str, str, Mapping[str, object]], object | None]
FreshDispatch = Callable[[], DispatchDecision]
ArtifactResultReader = Callable[[], Mapping[str, object] | None]


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _valid_text(value: object, *, maximum: int = 512) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value == value.strip()
        and "\x00" not in value
        and len(value) <= maximum
    )


def _valid_branch(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not value.startswith(("refs/", "/"))
        and ".." not in value
        and "//" not in value
        and _BRANCH.fullmatch(value) is not None
    )


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _encode_payload(value: Mapping[str, object]) -> str:
    return base64.b64encode(_canonical_json(value).encode("utf-8")).decode("ascii")


def _decode_payload(value: str) -> Mapping[str, object] | None:
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
        parsed = json.loads(decoded)
    except (ValueError, UnicodeError, binascii.Error, json.JSONDecodeError):
        return None
    return cast(Mapping[str, object], parsed) if isinstance(parsed, Mapping) else None


@dataclass(frozen=True, slots=True)
class IdleDispatchEnvelope:
    """Immutable evidence that one exact bridge wake ended in NO_WORK."""

    repository: str
    default_branch: str
    request_comment_id: int
    dispatch_run_id: int
    dispatch_artifact_id: int
    dispatch_artifact_sha256: str
    default_branch_revision: str
    source_evidence: str = "dispatch-result.json"
    schema: str = IDLE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != IDLE_SCHEMA:
            raise ValueError("idle envelope schema is invalid")
        if _REPOSITORY.fullmatch(self.repository) is None:
            raise ValueError("idle envelope repository is invalid")
        if not _valid_branch(self.default_branch):
            raise ValueError("idle envelope default branch is invalid")
        for field in (
            self.request_comment_id,
            self.dispatch_run_id,
            self.dispatch_artifact_id,
        ):
            if _positive_int(field) is None:
                raise ValueError("idle envelope identity is invalid")
        if not _valid_sha256(self.dispatch_artifact_sha256):
            raise ValueError("idle envelope artifact digest is invalid")
        if not _valid_sha(self.default_branch_revision):
            raise ValueError("idle envelope revision is invalid")
        if self.source_evidence != _DISPATCH_ARTIFACT_NAME:
            raise ValueError("idle envelope source evidence is invalid")

    @property
    def wake_correlation(self) -> str:
        material = (
            f"{self.repository}:{self.default_branch}:{self.request_comment_id}:"
            f"{self.dispatch_run_id}:{self.dispatch_artifact_id}:{self.default_branch_revision}:"
            f"{self.dispatch_artifact_sha256}"
        )
        return f"idle-wake-v1:{hashlib.sha256(material.encode('utf-8')).hexdigest()}"

    def payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "repository": self.repository,
            "default_branch": self.default_branch,
            "request_comment_id": self.request_comment_id,
            "dispatch_run_id": self.dispatch_run_id,
            "dispatch_artifact_id": self.dispatch_artifact_id,
            "dispatch_artifact_sha256": self.dispatch_artifact_sha256,
            "default_branch_revision": self.default_branch_revision,
            "disposition": "NO_WORK",
            "reason": "no-routed-work",
            "source_evidence": self.source_evidence,
            "wake_correlation": self.wake_correlation,
        }


def render_idle_envelope(envelope: IdleDispatchEnvelope) -> str:
    """Render a strict transport envelope for the external bootstrap."""

    return f"{IDLE_ENVELOPE_MARKER}\nEnvelope-B64: {_encode_payload(envelope.payload())}"


def parse_idle_envelope(body: str) -> IdleDispatchEnvelope | None:
    lines = body.splitlines()
    if len(lines) != 2 or lines[0] != IDLE_ENVELOPE_MARKER:
        return None
    prefix = "Envelope-B64: "
    if not lines[1].startswith(prefix):
        return None
    payload = _decode_payload(lines[1][len(prefix) :])
    if payload is None:
        return None
    expected = {
        "schema",
        "repository",
        "default_branch",
        "request_comment_id",
        "dispatch_run_id",
        "dispatch_artifact_id",
        "dispatch_artifact_sha256",
        "default_branch_revision",
        "disposition",
        "reason",
        "source_evidence",
        "wake_correlation",
    }
    if set(payload) != expected:
        return None
    if payload.get("disposition") != "NO_WORK" or payload.get("reason") != "no-routed-work":
        return None
    try:
        envelope = IdleDispatchEnvelope(
            repository=cast(str, payload["repository"]),
            default_branch=cast(str, payload["default_branch"]),
            request_comment_id=cast(int, payload["request_comment_id"]),
            dispatch_run_id=cast(int, payload["dispatch_run_id"]),
            dispatch_artifact_id=cast(int, payload["dispatch_artifact_id"]),
            dispatch_artifact_sha256=cast(str, payload["dispatch_artifact_sha256"]),
            default_branch_revision=cast(str, payload["default_branch_revision"]),
            source_evidence=cast(str, payload["source_evidence"]),
            schema=cast(str, payload["schema"]),
        )
    except (TypeError, ValueError):
        return None
    return envelope if payload.get("wake_correlation") == envelope.wake_correlation else None


@dataclass(frozen=True, slots=True)
class IdleCandidate:
    """One bounded Lead finding, or an explicit no-finding result."""

    kind: IdleCandidateKind
    source_kind: str = ""
    source_ref: str = ""
    source_revision: str = ""
    evidence: str = ""
    issue_number: int | None = None
    title: str | None = None
    body: str | None = None
    labels: tuple[str, ...] = ()
    observed_issue_sha256: str | None = None

    def validate(self, envelope: IdleDispatchEnvelope) -> None:
        if self.kind == "no-finding":
            if (
                any(
                    value is not None and value != ""
                    for value in (
                        self.issue_number,
                        self.title,
                        self.body,
                        self.source_kind,
                        self.source_ref,
                        self.source_revision,
                        self.evidence,
                        self.observed_issue_sha256,
                    )
                )
                or self.labels
            ):
                raise ValueError("no-finding candidate contains mutation data")
            return
        if self.source_revision != envelope.default_branch_revision or not _valid_sha(
            self.source_revision
        ):
            raise ValueError("idle candidate source revision is stale or invalid")
        if not _valid_text(self.source_kind, maximum=128) or not _valid_text(
            self.source_ref, maximum=512
        ):
            raise ValueError("idle candidate source evidence identity is invalid")
        if not _valid_text(self.evidence, maximum=8_192):
            raise ValueError("idle candidate evidence is invalid")
        if self.observed_issue_sha256 is not None and not _valid_sha256(self.observed_issue_sha256):
            raise ValueError("idle candidate observation digest is invalid")
        if self.kind == "existing":
            if _positive_int(self.issue_number) is None:
                raise ValueError("existing idle candidate Issue is invalid")
            if self.title is not None or self.body is not None or self.labels:
                raise ValueError("existing candidate must not carry replacement Issue fields")
            return
        if self.kind != "new":
            raise ValueError("idle candidate kind is invalid")
        if self.issue_number is not None:
            raise ValueError("new idle candidate unexpectedly carries an Issue")
        if not _valid_text(self.title, maximum=256) or not _valid_text(self.body, maximum=60_000):
            raise ValueError("new idle candidate content is invalid")
        if len(self.labels) != len(set(self.labels)) or not all(
            _valid_text(label, maximum=100) for label in self.labels
        ):
            raise ValueError("new idle candidate labels are invalid")
        action_labels = tuple(label for label in self.labels if label.startswith("action:"))
        if action_labels != (ACTION_EXPLORE_CHANGE,):
            raise ValueError("new idle candidate must have exactly one explore routing label")
        change_values = _CHANGE_LINE.findall(cast(str, self.body))
        if change_values != ["unset"]:
            raise ValueError("new idle candidate must contain exactly Change: unset")

    def payload(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "source_kind": self.source_kind,
            "source_ref": self.source_ref,
            "source_revision": self.source_revision,
            "evidence": self.evidence,
            "issue_number": self.issue_number,
            "title": self.title,
            "body": self.body,
            "labels": list(self.labels),
            "observed_issue_sha256": self.observed_issue_sha256,
        }


@dataclass(frozen=True, slots=True)
class IdleAdmissionRequest:
    envelope: IdleDispatchEnvelope
    candidate: IdleCandidate
    correlation: str
    schema: str = IDLE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != IDLE_SCHEMA:
            raise ValueError("idle request schema is invalid")
        self.candidate.validate(self.envelope)
        if self.correlation != idle_admission_correlation(self.envelope, self.candidate):
            raise ValueError("idle request correlation is invalid")

    def payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "envelope": self.envelope.payload(),
            "candidate": self.candidate.payload(),
            "correlation": self.correlation,
        }


def idle_admission_correlation(
    envelope: IdleDispatchEnvelope,
    candidate: IdleCandidate,
) -> str:
    material = _canonical_json({"envelope": envelope.payload(), "candidate": candidate.payload()})
    return f"idle-admission-v1:{hashlib.sha256(material.encode('utf-8')).hexdigest()}"


def make_idle_admission_request(
    envelope: IdleDispatchEnvelope,
    candidate: IdleCandidate,
) -> IdleAdmissionRequest:
    return IdleAdmissionRequest(
        envelope=envelope,
        candidate=candidate,
        correlation=idle_admission_correlation(envelope, candidate),
    )


def render_idle_admission_request(request: IdleAdmissionRequest) -> str:
    return f"{IDLE_REQUEST_MARKER}\nRequest-B64: {_encode_payload(request.payload())}"


def parse_idle_admission_request(body: str) -> IdleAdmissionRequest | None:
    lines = body.splitlines()
    if len(lines) != 2 or lines[0] != IDLE_REQUEST_MARKER:
        return None
    prefix = "Request-B64: "
    if not lines[1].startswith(prefix):
        return None
    payload = _decode_payload(lines[1][len(prefix) :])
    if payload is None or set(payload) != {"schema", "envelope", "candidate", "correlation"}:
        return None
    envelope_payload = payload.get("envelope")
    candidate_payload = payload.get("candidate")
    if not isinstance(envelope_payload, Mapping) or not isinstance(candidate_payload, Mapping):
        return None
    if set(candidate_payload) != {
        "kind",
        "source_kind",
        "source_ref",
        "source_revision",
        "evidence",
        "issue_number",
        "title",
        "body",
        "labels",
        "observed_issue_sha256",
    }:
        return None
    envelope_body = f"{IDLE_ENVELOPE_MARKER}\nEnvelope-B64: {_encode_payload(envelope_payload)}"
    envelope = parse_idle_envelope(envelope_body)
    if envelope is None:
        return None
    labels = candidate_payload.get("labels")
    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        return None
    try:
        candidate = IdleCandidate(
            kind=cast(IdleCandidateKind, candidate_payload.get("kind")),
            source_kind=cast(str, candidate_payload.get("source_kind", "")),
            source_ref=cast(str, candidate_payload.get("source_ref", "")),
            source_revision=cast(str, candidate_payload.get("source_revision", "")),
            evidence=cast(str, candidate_payload.get("evidence", "")),
            issue_number=cast(int | None, candidate_payload.get("issue_number")),
            title=cast(str | None, candidate_payload.get("title")),
            body=cast(str | None, candidate_payload.get("body")),
            labels=tuple(cast(list[str], labels)),
            observed_issue_sha256=cast(str | None, candidate_payload.get("observed_issue_sha256")),
        )
        return IdleAdmissionRequest(
            envelope=envelope,
            candidate=candidate,
            correlation=cast(str, payload["correlation"]),
            schema=cast(str, payload["schema"]),
        )
    except (TypeError, ValueError):
        return None


def _trusted_connector_comment(comment: Mapping[str, object], owner: str) -> bool:
    user = comment.get("user")
    app = comment.get("performed_via_github_app")
    return (
        isinstance(user, Mapping)
        and user.get("login") == owner
        and isinstance(app, Mapping)
        and app.get("slug") == _CHATGPT_CONNECTOR_APP_SLUG
    )


def parse_idle_admission_event(
    event: Mapping[str, object],
    *,
    repository: str,
) -> IdleAdmissionRequest | None:
    """Parse the production issue-comment ingress for one idle request.

    The comment is only a trigger.  The request remains bound to the original
    successful ``NO_WORK`` artifact and is re-authorized by ``admit_idle_request``.
    Requiring the configured connector identity here prevents an arbitrary Issue
    comment from becoming an application carrier.
    """

    if event.get("action") != "created":
        return None
    issue = event.get("issue")
    comment = event.get("comment")
    if not isinstance(issue, Mapping) or not isinstance(comment, Mapping):
        return None
    if not is_runtime_checkin_issue(issue) or not _trusted_connector_comment(
        comment, repository.split("/", 1)[0]
    ):
        return None
    body = comment.get("body")
    if not isinstance(body, str):
        return None
    request = parse_idle_admission_request(body)
    if request is None or request.envelope.repository != repository:
        return None
    return request


@dataclass(frozen=True, slots=True)
class IdleAdmissionResult:
    state: IdleAdmissionState
    reason: str
    issue_number: int | None = None
    mutation_attempted: bool = False


def is_exact_no_work(decision: DispatchDecision) -> bool:
    """Return true only for a complete, qualified machine NO_WORK result."""

    return (
        decision.disposition == "NO_WORK"
        and decision.reason == "no-routed-work"
        and decision.completeness == "COMPLETE"
        and decision.observation_provenance is ObservationProvenance.QUALIFIED
        and decision.selected_issue_id is None
        and decision.selected_routing is None
    )


def qualify_idle_handoff(decision: DispatchDecision) -> bool:
    """Qualify the bootstrap boundary without creating an Action or state."""

    return is_exact_no_work(decision)


def _github_json(
    repository: str,
    token: str,
    api_path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
) -> object | None:
    request = Request(
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method=method,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub host
            raw = response.read()
    except HTTPError as exc:
        if method == "GET" and exc.code == 404:
            return None
        raise
    return None if not raw else json.loads(raw.decode("utf-8"))


def _labels(payload: Mapping[str, object]) -> tuple[str, ...] | None:
    raw = payload.get("labels")
    if not isinstance(raw, list):
        return None
    names: list[str] = []
    for item in raw:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str):
            return None
        names.append(cast(str, item["name"]))
    return tuple(names)


def _change_values(body: object) -> tuple[str, ...] | None:
    if not isinstance(body, str):
        return None
    return tuple(_CHANGE_LINE.findall(body))


def _issue_digest(issue: Mapping[str, object]) -> str:
    relevant = {
        "number": issue.get("number"),
        "state": issue.get("state"),
        "title": issue.get("title"),
        "body": issue.get("body"),
        "labels": _labels(issue),
    }
    return hashlib.sha256(_canonical_json(relevant).encode("utf-8")).hexdigest()


def _routing_complete(issue: Mapping[str, object]) -> bool:
    if issue.get("state") != "open" or "pull_request" in issue:
        return False
    values = _change_values(issue.get("body"))
    names = _labels(issue)
    if values != ("unset",) or names is None:
        return False
    return sum(name.startswith("action:") for name in names) == 1 and ACTION_EXPLORE_CHANGE in names


def _existing_update(
    issue: Mapping[str, object],
) -> tuple[dict[str, object], tuple[str, ...]] | None:
    if issue.get("state") != "open":
        return None
    values = _change_values(issue.get("body"))
    names = _labels(issue)
    if (
        values is None
        or names is None
        or len(values) > 1
        or any(value != "unset" for value in values)
    ):
        return None
    body = issue.get("body")
    if not isinstance(body, str):
        return None
    new_body = body if values == ("unset",) else f"Change: unset\n{body}"
    unrelated = tuple(name for name in names if not name.startswith("action:"))
    new_labels = unrelated + (ACTION_EXPLORE_CHANGE,)
    return {"body": new_body, "labels": list(new_labels)}, unrelated


def _fresh_gate(
    request: IdleAdmissionRequest,
    *,
    read: GitHubReader,
    fresh_dispatch: FreshDispatch,
    artifact_result: ArtifactResultReader,
) -> IdleAdmissionResult | None:
    run = read(
        request.envelope.repository,
        "",
        f"actions/runs/{request.envelope.dispatch_run_id}",
    )
    if not isinstance(run, Mapping):
        return IdleAdmissionResult("FAIL_CLOSED", "idle-dispatch-run-unavailable")
    run_title = f"{_DISPATCH_RUN_PREFIX}{request.envelope.request_comment_id}"
    run_path = run.get("path")
    path_matches = run_path in {
        _DISPATCH_WORKFLOW_PATH,
        f"{_DISPATCH_WORKFLOW_PATH}@{request.envelope.default_branch}",
        f"{_DISPATCH_WORKFLOW_PATH}@refs/heads/{request.envelope.default_branch}",
    }
    title_matches = run.get("name") == run_title or run.get("display_title") == run_title
    if (
        run.get("id") != request.envelope.dispatch_run_id
        or not title_matches
        or not path_matches
        or run.get("event") != "issue_comment"
        or run.get("head_sha") != request.envelope.default_branch_revision
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
    ):
        return IdleAdmissionResult("STALE", "idle-dispatch-run-stale")
    artifacts_payload = read(
        request.envelope.repository,
        "",
        f"actions/runs/{request.envelope.dispatch_run_id}/artifacts?per_page=100",
    )
    artifacts = (
        artifacts_payload.get("artifacts") if isinstance(artifacts_payload, Mapping) else None
    )
    total_count = (
        artifacts_payload.get("total_count") if isinstance(artifacts_payload, Mapping) else None
    )
    if (
        not isinstance(artifacts, list)
        or isinstance(total_count, bool)
        or not isinstance(total_count, int)
        or total_count != len(artifacts)
    ):
        return IdleAdmissionResult("FAIL_CLOSED", "idle-dispatch-artifact-list-incomplete")
    matches = tuple(
        item
        for item in artifacts
        if isinstance(item, Mapping) and item.get("name") == _DISPATCH_ARTIFACT_NAME
    )
    if len(matches) != 1:
        return IdleAdmissionResult("FAIL_CLOSED", "idle-dispatch-artifact-ambiguous")
    artifact = matches[0]
    digest = artifact.get("digest")
    normalized_digest = digest.removeprefix("sha256:") if isinstance(digest, str) else None
    if (
        artifact.get("id") != request.envelope.dispatch_artifact_id
        or artifact.get("expired") is not False
        or normalized_digest != request.envelope.dispatch_artifact_sha256
    ):
        return IdleAdmissionResult("STALE", "idle-dispatch-artifact-stale")
    try:
        result = artifact_result()
    except (HTTPError, OSError, RuntimeError, TimeoutError, ValueError):
        return IdleAdmissionResult("FAIL_CLOSED", "idle-dispatch-artifact-content-unavailable")
    if (
        not isinstance(result, Mapping)
        or result.get("request_comment_id") != request.envelope.request_comment_id
        or result.get("default_branch_revision") != request.envelope.default_branch_revision
        or result.get("disposition") != "NO_WORK"
        or result.get("reason") != "no-routed-work"
    ):
        return IdleAdmissionResult("STALE", "idle-dispatch-artifact-content-stale")
    root = read(request.envelope.repository, "", "")
    if (
        not isinstance(root, Mapping)
        or root.get("default_branch") != request.envelope.default_branch
    ):
        return IdleAdmissionResult("STALE", "idle-default-branch-identity-stale")
    ref = read(
        request.envelope.repository,
        "",
        f"git/ref/heads/{quote(request.envelope.default_branch, safe='/')}",
    )
    ref_object = ref.get("object") if isinstance(ref, Mapping) else None
    if (
        not isinstance(ref_object, Mapping)
        or ref_object.get("sha") != request.envelope.default_branch_revision
    ):
        return IdleAdmissionResult("STALE", "idle-source-revision-stale")
    decision = fresh_dispatch()
    if not is_exact_no_work(decision):
        return IdleAdmissionResult("FAIL_CLOSED", "idle-normal-dispatch-no-longer-no-work")
    return None


def _paged_open_issues(
    repository: str,
    token: str,
    *,
    read: GitHubReader,
) -> tuple[Mapping[str, object], ...] | None:
    issues: list[Mapping[str, object]] = []
    page = 1
    while True:
        payload = read(repository, token, f"issues?state=all&per_page=100&page={page}")
        if not isinstance(payload, list):
            return None
        for item in payload:
            if not isinstance(item, Mapping):
                return None
            issues.append(cast(Mapping[str, object], item))
        if len(payload) < 100:
            return tuple(issues)
        page += 1


def _new_body(request: IdleAdmissionRequest) -> str:
    candidate = request.candidate
    body = candidate.body
    if body is None:
        raise ValueError("new idle candidate body is missing")
    additions = (
        f"Idle-Admission-Correlation: {request.correlation}",
        f"Idle-Source-Revision: {request.envelope.default_branch_revision}",
        f"Idle-Source: {candidate.source_kind}:{candidate.source_ref}",
    )
    for marker, pattern in zip(
        additions, (_CORRELATION_LINE, _SOURCE_REVISION_LINE, _SOURCE_LINE), strict=True
    ):
        matches = pattern.findall(body)
        if matches and matches != [marker.split(": ", 1)[1]]:
            raise ValueError("idle candidate source marker contradicts request")
    missing = tuple(
        marker
        for marker, pattern in zip(
            additions, (_CORRELATION_LINE, _SOURCE_REVISION_LINE, _SOURCE_LINE), strict=True
        )
        if not pattern.search(body)
    )
    return body if not missing else body.rstrip() + "\n\n" + "\n".join(missing) + "\n"


def _matching_new_candidates(
    request: IdleAdmissionRequest,
    issues: tuple[Mapping[str, object], ...],
) -> tuple[Mapping[str, object], ...]:
    marker = request.correlation
    return tuple(
        issue
        for issue in issues
        if "pull_request" not in issue
        and isinstance(issue.get("body"), str)
        and _CORRELATION_LINE.findall(cast(str, issue["body"])) == [marker]
    )


def _new_postcondition(request: IdleAdmissionRequest, issue: Mapping[str, object]) -> bool:
    if not _routing_complete(issue):
        return False
    if issue.get("title") != request.candidate.title:
        return False
    body = issue.get("body")
    if not isinstance(body, str):
        return False
    try:
        expected_body = _new_body(request)
    except ValueError:
        return False
    return (
        body == expected_body
        and _CORRELATION_LINE.findall(body) == [request.correlation]
        and _SOURCE_REVISION_LINE.findall(body) == [request.envelope.default_branch_revision]
        and _SOURCE_LINE.findall(body)
        == [f"{request.candidate.source_kind}:{request.candidate.source_ref}"]
    )


def _existing_postcondition(
    issue: Mapping[str, object],
    *,
    unrelated: tuple[str, ...],
    expected_body: str,
) -> bool:
    if not _routing_complete(issue):
        return False
    names = _labels(issue)
    return (
        issue.get("body") == expected_body
        and names is not None
        and names == unrelated + (ACTION_EXPLORE_CHANGE,)
    )


def admit_idle_request(
    request: IdleAdmissionRequest,
    *,
    read: GitHubReader,
    write: GitHubWriter,
    fresh_dispatch: FreshDispatch,
    artifact_result: ArtifactResultReader,
) -> IdleAdmissionResult:
    """Freshly authorize and apply one bounded idle candidate.

    A failed or ambiguous write is reconciled by exact target/correlation
    reads.  This function never retries a mutation after an unknown response.
    """

    try:
        request.candidate.validate(request.envelope)
    except ValueError as exc:
        return IdleAdmissionResult("INVALID", str(exc))
    if request.candidate.kind == "no-finding":
        return IdleAdmissionResult("NO_FINDING", "idle-no-finding")

    candidate = request.candidate
    if candidate.kind == "existing":
        if candidate.issue_number is None:
            return IdleAdmissionResult("INVALID", "idle-existing-target-identity-incomplete")
        current = read(request.envelope.repository, "", f"issues/{candidate.issue_number}")
        if not isinstance(current, Mapping) or "pull_request" in current:
            return IdleAdmissionResult(
                "STALE", "idle-existing-target-unavailable", candidate.issue_number
            )
        if (
            candidate.observed_issue_sha256 is not None
            and _issue_digest(current) != candidate.observed_issue_sha256
        ):
            return IdleAdmissionResult(
                "STALE", "idle-existing-target-changed", candidate.issue_number
            )
        prepared = _existing_update(current)
        if prepared is None:
            return IdleAdmissionResult(
                "FAIL_CLOSED", "idle-existing-target-invalid", candidate.issue_number
            )
        fields, unrelated = prepared
        expected_body = cast(str, fields["body"])
        if _existing_postcondition(
            current,
            unrelated=unrelated,
            expected_body=expected_body,
        ):
            return IdleAdmissionResult(
                "ALREADY_ADMITTED", "idle-existing-target-already-complete", candidate.issue_number
            )
        gate = _fresh_gate(
            request,
            read=read,
            fresh_dispatch=fresh_dispatch,
            artifact_result=artifact_result,
        )
        if gate is not None:
            return IdleAdmissionResult(gate.state, gate.reason, candidate.issue_number)
        latest = read(request.envelope.repository, "", f"issues/{candidate.issue_number}")
        if not isinstance(latest, Mapping) or _issue_digest(latest) != _issue_digest(current):
            return IdleAdmissionResult(
                "STALE", "idle-existing-target-changed-before-write", candidate.issue_number
            )
        gate = _fresh_gate(
            request,
            read=read,
            fresh_dispatch=fresh_dispatch,
            artifact_result=artifact_result,
        )
        if gate is not None:
            return IdleAdmissionResult(gate.state, gate.reason, candidate.issue_number)
        try:
            write(
                request.envelope.repository,
                "",
                f"issues/{candidate.issue_number}",
                fields,
            )
        except (HTTPError, OSError, RuntimeError, TimeoutError):
            reconciled = read(request.envelope.repository, "", f"issues/{candidate.issue_number}")
            if isinstance(reconciled, Mapping) and _existing_postcondition(
                reconciled,
                unrelated=unrelated,
                expected_body=expected_body,
            ):
                return IdleAdmissionResult(
                    "ADMITTED", "idle-existing-write-reconciled", candidate.issue_number, True
                )
            return IdleAdmissionResult(
                "AMBIGUOUS", "idle-existing-write-ambiguous", candidate.issue_number, True
            )
        observed = read(request.envelope.repository, "", f"issues/{candidate.issue_number}")
        if isinstance(observed, Mapping) and _existing_postcondition(
            observed,
            unrelated=unrelated,
            expected_body=expected_body,
        ):
            return IdleAdmissionResult(
                "ADMITTED", "idle-existing-admitted", candidate.issue_number, True
            )
        return IdleAdmissionResult(
            "AMBIGUOUS", "idle-existing-postcondition-unproven", candidate.issue_number, True
        )

    try:
        body = _new_body(request)
    except ValueError as exc:
        return IdleAdmissionResult("INVALID", str(exc))
    labels = tuple(candidate.labels)
    issues = _paged_open_issues(request.envelope.repository, "", read=read)
    if issues is None:
        return IdleAdmissionResult("AMBIGUOUS", "idle-new-target-enumeration-incomplete")
    matches = _matching_new_candidates(request, issues)
    if len(matches) > 1:
        return IdleAdmissionResult("AMBIGUOUS", "idle-new-target-correlation-ambiguous")
    if matches:
        number = _positive_int(matches[0].get("number"))
        if number is None or not _new_postcondition(request, matches[0]):
            return IdleAdmissionResult("AMBIGUOUS", "idle-new-target-postcondition-invalid")
        return IdleAdmissionResult("ALREADY_ADMITTED", "idle-new-target-already-complete", number)
    gate = _fresh_gate(
        request,
        read=read,
        fresh_dispatch=fresh_dispatch,
        artifact_result=artifact_result,
    )
    if gate is not None:
        return gate
    issues_again = _paged_open_issues(request.envelope.repository, "", read=read)
    if issues_again is None:
        return IdleAdmissionResult("AMBIGUOUS", "idle-new-target-enumeration-incomplete")
    matches_again = _matching_new_candidates(request, issues_again)
    if matches_again:
        if len(matches_again) != 1 or not _new_postcondition(request, matches_again[0]):
            return IdleAdmissionResult("AMBIGUOUS", "idle-new-target-correlation-ambiguous")
        number = _positive_int(matches_again[0].get("number"))
        return IdleAdmissionResult("ALREADY_ADMITTED", "idle-new-target-already-complete", number)
    gate = _fresh_gate(
        request,
        read=read,
        fresh_dispatch=fresh_dispatch,
        artifact_result=artifact_result,
    )
    if gate is not None:
        return gate
    payload = {"title": candidate.title, "body": body, "labels": list(labels)}
    try:
        response = write(request.envelope.repository, "", "issues", payload)
    except (HTTPError, OSError, RuntimeError, TimeoutError):
        reconciled = _paged_open_issues(request.envelope.repository, "", read=read)
        if reconciled is None:
            return IdleAdmissionResult(
                "AMBIGUOUS", "idle-new-write-reconciliation-incomplete", None, True
            )
        matches_after = _matching_new_candidates(request, reconciled)
        if len(matches_after) == 1 and _new_postcondition(request, matches_after[0]):
            number = _positive_int(matches_after[0].get("number"))
            return IdleAdmissionResult("ADMITTED", "idle-new-write-reconciled", number, True)
        return IdleAdmissionResult("AMBIGUOUS", "idle-new-write-ambiguous", None, True)
    number = _positive_int(response.get("number")) if isinstance(response, Mapping) else None
    observed = None if number is None else read(request.envelope.repository, "", f"issues/{number}")
    if (
        number is not None
        and isinstance(observed, Mapping)
        and _new_postcondition(request, observed)
    ):
        return IdleAdmissionResult("ADMITTED", "idle-new-admitted", number, True)
    reconciled = _paged_open_issues(request.envelope.repository, "", read=read)
    if reconciled is not None:
        matches_after = _matching_new_candidates(request, reconciled)
        if len(matches_after) == 1 and _new_postcondition(request, matches_after[0]):
            return IdleAdmissionResult(
                "ADMITTED",
                "idle-new-postcondition-reconciled",
                _positive_int(matches_after[0].get("number")),
                True,
            )
    return IdleAdmissionResult("AMBIGUOUS", "idle-new-postcondition-unproven", number, True)


def _default_dispatch(repository: str, token: str) -> DispatchDecision:
    return classify_dispatch(acquire_current_github_preflight(repository, token))


def _verified_artifact_result(
    repository: str,
    token: str,
    envelope: IdleDispatchEnvelope,
) -> Mapping[str, object]:
    result = fetch_dispatch_result(
        repository,
        token,
        request_comment_id=envelope.request_comment_id,
        run_id=envelope.dispatch_run_id,
        current_revision=envelope.default_branch_revision,
    )
    return {
        "request_comment_id": result.request_comment_id,
        "default_branch_revision": result.default_branch_revision,
        "disposition": result.disposition,
        "reason": result.reason,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description="Apply one typed NO_WORK idle admission request")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--request-b64")
    source.add_argument("--event-path", type=Path)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if args.event_path is not None:
        try:
            event = json.loads(args.event_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SystemExit("invalid idle admission event") from exc
        request = (
            parse_idle_admission_event(event, repository=repository)
            if isinstance(event, Mapping)
            else None
        )
    else:
        try:
            body = base64.b64decode(args.request_b64, validate=True).decode("utf-8")
        except (UnicodeDecodeError, binascii.Error, ValueError) as exc:
            raise SystemExit("invalid idle admission request") from exc
        request = parse_idle_admission_request(body)
    if request is None:
        raise SystemExit("invalid idle admission request")
    if (
        repository != request.envelope.repository
        or args.revision != request.envelope.default_branch_revision
    ):
        raise SystemExit("idle admission request is stale")
    result = admit_idle_request(
        request,
        read=lambda repo, _unused, path: _github_json(repo, token, path),
        write=lambda repo, _unused, path, payload: _github_json(
            repo, token, path, method="POST" if path == "issues" else "PATCH", payload=payload
        ),
        fresh_dispatch=lambda: _default_dispatch(repository, token),
        artifact_result=lambda: _verified_artifact_result(repository, token, request.envelope),
    )
    print(
        json.dumps(
            {
                "state": result.state,
                "reason": result.reason,
                "issue_number": result.issue_number,
                "mutation_attempted": result.mutation_attempted,
            },
            sort_keys=True,
        )
    )
    return 0 if result.state in {"NO_FINDING", "ADMITTED", "ALREADY_ADMITTED"} else 1


if __name__ == "__main__":
    raise SystemExit(_main())
