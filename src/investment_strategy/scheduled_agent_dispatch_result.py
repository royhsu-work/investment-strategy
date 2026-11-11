"""Read-only adapter for exact run-scoped Scheduled-Agent dispatch results."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Literal, TypeVar, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from investment_strategy.issue_comment_bridge import (
    MachineDispatchDecision,
    parse_dispatch_result_document,
    parse_dispatch_run_name,
)
from investment_strategy.scheduled_agent_carrier import (
    MAX_GITHUB_ARTIFACT_BYTES,
    GitHubArtifactBytes,
    GitHubArtifactReadError,
    github_read_bytes_with_retry,
    github_repository_api_url,
    read_github_artifact,
)

_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ARTIFACT_NAME = "dispatch-result.json"
_BRIDGE_PATH = ".github/workflows/scheduled-agent-bridge.yml"
_MAX_DISPATCH_ARTIFACT_BYTES = MAX_GITHUB_ARTIFACT_BYTES

FailureClassification = Literal[
    "READ_UNAVAILABLE",
    "REDIRECT_UNTRUSTED",
    "PAYLOAD_FORMAT_INVALID",
    "INTEGRITY_MISMATCH",
    "IDENTITY_STALE",
    "PERMANENT_INVALID",
    "RECOVERABLE_INCOMPLETE",
    "UNKNOWN",
]
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class DispatchArtifactFailure:
    """Safe machine-readable failure and exact correlation for one read stage."""

    stage: str
    classification: FailureClassification
    request_comment_id: int | None
    run_id: int | None
    run_attempt: int | None
    artifact_id: int | None
    revision: str | None
    http_status: int | None = None
    exception_category: str | None = None
    redirect_host_class: str | None = None
    expected_correlation: tuple[tuple[str, int | str], ...] = ()
    observed_correlation: tuple[tuple[str, int | str], ...] = ()
    mutation_attempted: bool = False

    def diagnostic(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "classification": self.classification,
            "request_comment_id": self.request_comment_id,
            "run_id": self.run_id,
            "run_attempt": self.run_attempt,
            "artifact_id": self.artifact_id,
            "revision": self.revision,
            "http_status": self.http_status,
            "exception_category": self.exception_category,
            "redirect_host_class": self.redirect_host_class,
            "expected_correlation": dict(self.expected_correlation),
            "observed_correlation": dict(self.observed_correlation),
            "mutation_attempted": self.mutation_attempted,
        }


class DispatchArtifactReadError(RuntimeError):
    """A failed artifact stage with a safe typed diagnostic."""

    def __init__(self, failure: DispatchArtifactFailure) -> None:
        super().__init__(f"dispatch artifact {failure.stage}: {failure.classification}")
        self.failure = failure

    def diagnostic(self) -> dict[str, object]:
        return self.failure.diagnostic()


@dataclass(frozen=True, slots=True)
class StageResult(Generic[T]):
    """Exactly one successful stage value or one typed failure."""

    value: T | None = None
    failure: DispatchArtifactFailure | None = None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.failure is None):
            raise ValueError("stage result must contain one value or one failure")

    def require(self) -> T:
        if self.failure is not None:
            raise DispatchArtifactReadError(self.failure)
        return cast(T, self.value)


@dataclass(frozen=True, slots=True)
class VerifiedDispatchArtifact:
    """Canonical parsed decision plus evidence for its exact source bytes."""

    decision: MachineDispatchDecision
    run_attempt: int
    artifact_id: int
    artifact_size_in_bytes: int
    artifact_sha256: str
    content_length: int
    content_sha256: str
    initial_status: int
    redirect_host_class: str | None

    def diagnostic(self, *, run_id: int) -> dict[str, object]:
        return {
            "stage": "complete",
            "classification": "VERIFIED",
            "request_comment_id": self.decision.request_comment_id,
            "run_id": run_id,
            "run_attempt": self.run_attempt,
            "artifact_id": self.artifact_id,
            "revision": self.decision.default_branch_revision,
            "artifact_size_in_bytes": self.artifact_size_in_bytes,
            "content_length": self.content_length,
            "artifact_sha256": self.artifact_sha256,
            "content_sha256": self.content_sha256,
            "initial_status": self.initial_status,
            "redirect_host_class": self.redirect_host_class,
            "disposition": self.decision.disposition,
            "mutation_attempted": False,
        }


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _expected_correlation(
    request_comment_id: int | None,
    run_id: int | None,
    revision: str | None,
    run_attempt: int | None = None,
    artifact_id: int | None = None,
) -> tuple[tuple[str, int | str], ...]:
    pairs: list[tuple[str, int | str]] = []
    for key, value in (
        ("request_comment_id", request_comment_id),
        ("run_id", run_id),
        ("run_attempt", run_attempt),
        ("artifact_id", artifact_id),
        ("revision", revision),
    ):
        if value is not None:
            pairs.append((key, value))
    return tuple(pairs)


def _observed_pairs(
    value: Mapping[str, object], keys: tuple[str, ...]
) -> tuple[tuple[str, int | str], ...]:
    pairs: list[tuple[str, int | str]] = []
    for key in keys:
        item = value.get(key)
        if isinstance(item, bool):
            continue
        if isinstance(item, (int, str)):
            pairs.append((key, item))
    return tuple(pairs)


def _failure(
    *,
    stage: str,
    classification: FailureClassification,
    request_comment_id: int | None,
    run_id: int | None,
    revision: str | None,
    run_attempt: int | None = None,
    artifact_id: int | None = None,
    http_status: int | None = None,
    exception_category: str | None = None,
    redirect_host_class: str | None = None,
    observed: Mapping[str, object] | None = None,
) -> DispatchArtifactFailure:
    return DispatchArtifactFailure(
        stage=stage,
        classification=classification,
        request_comment_id=request_comment_id,
        run_id=run_id,
        run_attempt=run_attempt,
        artifact_id=artifact_id,
        revision=revision,
        http_status=http_status,
        exception_category=exception_category,
        redirect_host_class=redirect_host_class,
        expected_correlation=_expected_correlation(
            request_comment_id, run_id, revision, run_attempt, artifact_id
        ),
        observed_correlation=(
            ()
            if observed is None
            else _observed_pairs(
                observed,
                ("id", "run_attempt", "request_comment_id", "artifact_id", "head_sha"),
            )
        ),
    )


def _github_json(
    repository: str,
    token: str,
    api_path: str,
    *,
    stage: str,
    request_comment_id: int,
    run_id: int,
    revision: str,
) -> object:
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        github_repository_api_url(repository, api_path),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        raw = github_read_bytes_with_retry(request, open_request=urlopen, wait=time.sleep)
    except HTTPError as error:
        classification: FailureClassification = (
            "READ_UNAVAILABLE" if error.code in {429, 500, 502, 503, 504} else "PERMANENT_INVALID"
        )
        raise DispatchArtifactReadError(
            _failure(
                stage=stage,
                classification=classification,
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                http_status=error.code,
                exception_category=type(error).__name__,
            )
        ) from None
    except OSError as error:
        raise DispatchArtifactReadError(
            _failure(
                stage=stage,
                classification="READ_UNAVAILABLE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                exception_category=type(error).__name__,
            )
        ) from None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise DispatchArtifactReadError(
            _failure(
                stage=stage,
                classification="PAYLOAD_FORMAT_INVALID",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                exception_category=type(error).__name__,
            )
        ) from None


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _validate_request_identity(
    repository: str,
    token: str,
    request_comment_id: int,
    run_id: int,
    current_revision: str,
) -> StageResult[tuple[str, str, int, int, str]]:
    valid = (
        isinstance(repository, str)
        and _REPOSITORY.fullmatch(repository) is not None
        and isinstance(token, str)
        and bool(token)
        and _positive_int(request_comment_id) is not None
        and _positive_int(run_id) is not None
        and isinstance(current_revision, str)
        and _SHA.fullmatch(current_revision) is not None
    )
    if not valid:
        failure = _failure(
            stage="request-identity",
            classification="PERMANENT_INVALID",
            request_comment_id=request_comment_id if _positive_int(request_comment_id) else None,
            run_id=run_id if _positive_int(run_id) else None,
            revision=current_revision if isinstance(current_revision, str) else None,
            exception_category="InvalidRequestIdentity",
        )
        return StageResult(failure=failure)
    return StageResult(value=(repository, token, request_comment_id, run_id, current_revision))


def _validate_run(
    value: object,
    *,
    request_comment_id: int,
    run_id: int,
    revision: str,
) -> StageResult[tuple[Mapping[str, object], int, datetime, datetime]]:
    run = _as_mapping(value)
    if run is None:
        return StageResult(
            failure=_failure(
                stage="run-identity",
                classification="RECOVERABLE_INCOMPLETE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                exception_category="RunResponseIncomplete",
            )
        )
    observed_names = tuple(
        item for item in (run.get("name"), run.get("display_title")) if isinstance(item, str)
    )
    path = run.get("path")
    path_matches = path == _BRIDGE_PATH or (
        isinstance(path, str) and path.startswith(f"{_BRIDGE_PATH}@")
    )
    attempt = _positive_int(run.get("run_attempt"))
    started = _timestamp(run.get("run_started_at"))
    updated = _timestamp(run.get("updated_at"))
    missing = (
        _positive_int(run.get("id")) is None
        or not observed_names
        or not isinstance(path, str)
        or attempt is None
        or started is None
        or updated is None
        or not isinstance(run.get("head_sha"), str)
        or not isinstance(run.get("status"), str)
        or not isinstance(run.get("conclusion"), str)
    )
    if missing:
        return StageResult(
            failure=_failure(
                stage="run-identity",
                classification="RECOVERABLE_INCOMPLETE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=attempt,
                exception_category="RunIdentityIncomplete",
                observed=run,
            )
        )
    identity_matches = (
        run.get("id") == run_id
        and any(parse_dispatch_run_name(name) == request_comment_id for name in observed_names)
        and path_matches
        and run.get("event") == "issue_comment"
        and run.get("head_sha") == revision
    )
    if not identity_matches:
        return StageResult(
            failure=_failure(
                stage="run-identity",
                classification="IDENTITY_STALE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=attempt,
                exception_category="RunCorrelationMismatch",
                observed=run,
            )
        )
    if run.get("status") != "completed":
        return StageResult(
            failure=_failure(
                stage="run-completion",
                classification="RECOVERABLE_INCOMPLETE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=attempt,
                exception_category="RunNotCompleted",
                observed=run,
            )
        )
    if run.get("conclusion") != "success":
        return StageResult(
            failure=_failure(
                stage="run-completion",
                classification="PERMANENT_INVALID",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=attempt,
                exception_category="RunNotSuccessful",
                observed=run,
            )
        )
    return StageResult(
        value=(run, cast(int, attempt), cast(datetime, started), cast(datetime, updated))
    )


def _validate_artifact_listing(
    value: object,
    *,
    request_comment_id: int,
    run_id: int,
    run_attempt: int,
    revision: str,
    started: datetime,
    updated: datetime,
    expected_artifact_id: int | None,
    expected_artifact_sha256: str | None,
) -> StageResult[Mapping[str, object]]:
    payload = _as_mapping(value)
    if payload is None:
        return StageResult(
            failure=_failure(
                stage="artifact-list",
                classification="RECOVERABLE_INCOMPLETE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                exception_category="ArtifactListingIncomplete",
            )
        )
    artifacts = payload.get("artifacts")
    total_count = payload.get("total_count")
    if (
        not isinstance(artifacts, list)
        or isinstance(total_count, bool)
        or not isinstance(total_count, int)
        or total_count != len(artifacts)
    ):
        return StageResult(
            failure=_failure(
                stage="artifact-list",
                classification="RECOVERABLE_INCOMPLETE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                exception_category="ArtifactListingIncomplete",
            )
        )
    mapped = tuple(_as_mapping(item) for item in artifacts)
    if any(item is None for item in mapped):
        return StageResult(
            failure=_failure(
                stage="artifact-list",
                classification="PAYLOAD_FORMAT_INVALID",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                exception_category="ArtifactEntryInvalid",
            )
        )
    matches = tuple(
        item for item in mapped if item is not None and item.get("name") == _ARTIFACT_NAME
    )
    if len(matches) != 1:
        return StageResult(
            failure=_failure(
                stage="artifact-identity",
                classification="PERMANENT_INVALID",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                exception_category="ArtifactMissingOrAmbiguous",
            )
        )
    artifact = matches[0]
    artifact_id = _positive_int(artifact.get("id"))
    size = artifact.get("size_in_bytes")
    digest = artifact.get("digest")
    workflow_run = _as_mapping(artifact.get("workflow_run"))
    created = _timestamp(artifact.get("created_at"))
    expired = artifact.get("expired")
    workflow_id = None if workflow_run is None else _positive_int(workflow_run.get("id"))
    workflow_sha = None if workflow_run is None else workflow_run.get("head_sha")
    metadata_missing = (
        artifact_id is None
        or not isinstance(expired, bool)
        or isinstance(size, bool)
        or not isinstance(size, int)
        or not isinstance(digest, str)
        or workflow_run is None
        or workflow_id is None
        or not isinstance(workflow_sha, str)
        or created is None
    )
    if metadata_missing:
        return StageResult(
            failure=_failure(
                stage="artifact-metadata",
                classification="RECOVERABLE_INCOMPLETE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                exception_category="ArtifactMetadataIncomplete",
            )
        )
    if artifact.get("expired") is not False:
        return StageResult(
            failure=_failure(
                stage="artifact-metadata",
                classification="PERMANENT_INVALID",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                exception_category="ArtifactExpired",
            )
        )
    if re.fullmatch(r"sha256:[0-9a-f]{64}", cast(str, digest)) is None:
        return StageResult(
            failure=_failure(
                stage="artifact-metadata",
                classification="PERMANENT_INVALID",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                exception_category="ArtifactDigestInvalid",
            )
        )
    artifact_id = cast(int, artifact_id)
    artifact_run = cast(Mapping[str, object], workflow_run)
    artifact_created = cast(datetime, created)
    size = cast(int, size)
    digest = cast(str, digest)
    if size <= 0 or size > _MAX_DISPATCH_ARTIFACT_BYTES:
        return StageResult(
            failure=_failure(
                stage="artifact-metadata",
                classification="PERMANENT_INVALID",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                exception_category="ArtifactSizeOutOfBounds",
            )
        )
    identity_matches = (
        _positive_int(artifact_run.get("id")) == run_id
        and artifact_run.get("head_sha") == revision
        and artifact_created > started
        and artifact_created <= updated
        and (expected_artifact_id is None or artifact_id == expected_artifact_id)
        and (
            expected_artifact_sha256 is None
            or digest.removeprefix("sha256:") == expected_artifact_sha256
        )
    )
    if not identity_matches:
        return StageResult(
            failure=_failure(
                stage="artifact-identity",
                classification="IDENTITY_STALE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                exception_category="ArtifactCorrelationMismatch",
                observed={
                    "artifact_id": artifact_id,
                    "head_sha": artifact_run.get("head_sha"),
                },
            )
        )
    return StageResult(value=artifact)


def _github_artifact(
    repository: str,
    token: str,
    api_path: str,
    *,
    request_comment_id: int,
    run_id: int,
    run_attempt: int,
    artifact_id: int,
    revision: str,
) -> GitHubArtifactBytes:
    try:
        return read_github_artifact(
            repository,
            token,
            api_path,
            accept="application/octet-stream",
            max_bytes=_MAX_DISPATCH_ARTIFACT_BYTES,
        )
    except GitHubArtifactReadError as error:
        observed_failure = error.diagnostic()
        classification = cast(FailureClassification, observed_failure["classification"])
        raise DispatchArtifactReadError(
            _failure(
                stage=cast(str, observed_failure["stage"]),
                classification=classification,
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                http_status=cast(int | None, observed_failure["http_status"]),
                exception_category=cast(str | None, observed_failure["exception_category"]),
                redirect_host_class=cast(str | None, observed_failure["redirect_host_class"]),
            )
        ) from None
    except (OSError, ValueError) as error:
        raise DispatchArtifactReadError(
            _failure(
                stage="artifact-read",
                classification="UNKNOWN",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                exception_category=type(error).__name__,
            )
        ) from None


def _github_bytes(repository: str, token: str, api_path: str) -> bytes:
    """Compatibility wrapper around the shared credential-safe artifact adapter."""

    response = read_github_artifact(
        repository,
        token,
        api_path,
        accept="application/octet-stream",
        max_bytes=_MAX_DISPATCH_ARTIFACT_BYTES,
    )
    return response.content


def fetch_dispatch_artifact(
    repository: str,
    token: str,
    *,
    request_comment_id: int,
    run_id: int,
    current_revision: str,
    expected_run_attempt: int | None = None,
    expected_artifact_id: int | None = None,
    expected_artifact_sha256: str | None = None,
) -> VerifiedDispatchArtifact:
    """Read and qualify exactly one successful run, attempt and raw Artifact."""

    identity = _validate_request_identity(
        repository, token, request_comment_id, run_id, current_revision
    ).require()
    repository, token, request_comment_id, run_id, current_revision = identity
    expected_identity_valid = (
        (expected_run_attempt is None or _positive_int(expected_run_attempt) is not None)
        and (expected_artifact_id is None or _positive_int(expected_artifact_id) is not None)
        and (
            expected_artifact_sha256 is None
            or (
                isinstance(expected_artifact_sha256, str)
                and _SHA256.fullmatch(expected_artifact_sha256) is not None
            )
        )
    )
    if not expected_identity_valid:
        raise DispatchArtifactReadError(
            _failure(
                stage="request-identity",
                classification="PERMANENT_INVALID",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=current_revision,
                exception_category="InvalidExpectedCorrelation",
            )
        )

    run_value = _github_json(
        repository,
        token,
        f"actions/runs/{run_id}",
        stage="run-read",
        request_comment_id=request_comment_id,
        run_id=run_id,
        revision=current_revision,
    )
    run, run_attempt, started, updated = _validate_run(
        run_value,
        request_comment_id=request_comment_id,
        run_id=run_id,
        revision=current_revision,
    ).require()
    if expected_run_attempt is not None and expected_run_attempt != run_attempt:
        raise DispatchArtifactReadError(
            _failure(
                stage="run-attempt",
                classification="IDENTITY_STALE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=current_revision,
                run_attempt=run_attempt,
                exception_category="RunAttemptChanged",
                observed={"id": run_id, "run_attempt": run_attempt},
            )
        )

    artifacts_value = _github_json(
        repository,
        token,
        f"actions/runs/{run_id}/artifacts?per_page=100",
        stage="artifact-list-read",
        request_comment_id=request_comment_id,
        run_id=run_id,
        revision=current_revision,
    )
    artifact = _validate_artifact_listing(
        artifacts_value,
        request_comment_id=request_comment_id,
        run_id=run_id,
        run_attempt=run_attempt,
        revision=current_revision,
        started=started,
        updated=updated,
        expected_artifact_id=expected_artifact_id,
        expected_artifact_sha256=expected_artifact_sha256,
    ).require()
    artifact_id = cast(int, artifact["id"])
    artifact_size = cast(int, artifact["size_in_bytes"])
    artifact_sha256 = cast(str, artifact["digest"]).removeprefix("sha256:")

    response = _github_artifact(
        repository,
        token,
        f"actions/artifacts/{artifact_id}/zip",
        request_comment_id=request_comment_id,
        run_id=run_id,
        run_attempt=run_attempt,
        artifact_id=artifact_id,
        revision=current_revision,
    )
    raw = response.content
    observed_size = len(raw)
    observed_sha256 = hashlib.sha256(raw).hexdigest()
    if observed_size != artifact_size or observed_sha256 != artifact_sha256:
        raise DispatchArtifactReadError(
            _failure(
                stage="artifact-integrity",
                classification="INTEGRITY_MISMATCH",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=current_revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                exception_category="ArtifactSizeOrDigestMismatch",
                redirect_host_class=response.redirect_host_class,
                observed={"artifact_id": artifact_id},
            )
        )
    try:
        decision = parse_dispatch_result_document(raw)
    except (RuntimeError, ValueError) as error:
        raise DispatchArtifactReadError(
            _failure(
                stage="canonical-payload",
                classification="PAYLOAD_FORMAT_INVALID",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=current_revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                exception_category=type(error).__name__,
                redirect_host_class=response.redirect_host_class,
            )
        ) from None
    if (
        decision.request_comment_id != request_comment_id
        or decision.default_branch_revision != current_revision
    ):
        raise DispatchArtifactReadError(
            _failure(
                stage="canonical-identity",
                classification="IDENTITY_STALE",
                request_comment_id=request_comment_id,
                run_id=run_id,
                revision=current_revision,
                run_attempt=run_attempt,
                artifact_id=artifact_id,
                exception_category="PayloadCorrelationMismatch",
                redirect_host_class=response.redirect_host_class,
                observed={
                    "request_comment_id": decision.request_comment_id,
                    "head_sha": decision.default_branch_revision,
                },
            )
        )
    return VerifiedDispatchArtifact(
        decision=decision,
        run_attempt=run_attempt,
        artifact_id=artifact_id,
        artifact_size_in_bytes=artifact_size,
        artifact_sha256=artifact_sha256,
        content_length=observed_size,
        content_sha256=observed_sha256,
        initial_status=response.initial_status,
        redirect_host_class=response.redirect_host_class,
    )


def fetch_dispatch_result(
    repository: str,
    token: str,
    *,
    request_comment_id: int,
    run_id: int,
    current_revision: str,
) -> MachineDispatchDecision:
    """Compatibility API returning the canonical decision after exact verification."""

    return fetch_dispatch_artifact(
        repository,
        token,
        request_comment_id=request_comment_id,
        run_id=run_id,
        current_revision=current_revision,
    ).decision


__all__ = [
    "FailureClassification",
    "DispatchArtifactFailure",
    "DispatchArtifactReadError",
    "StageResult",
    "VerifiedDispatchArtifact",
    "fetch_dispatch_artifact",
    "fetch_dispatch_result",
]
