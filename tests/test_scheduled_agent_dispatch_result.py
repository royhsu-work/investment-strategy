"""Regression coverage for exact run-scoped dispatch result transport."""

from __future__ import annotations

import hashlib
import json
from email.message import Message
from io import BytesIO
from typing import cast
from urllib.error import HTTPError
from urllib.request import Request

import pytest

import investment_strategy.scheduled_agent_carrier as carrier
import investment_strategy.scheduled_agent_dispatch_result as transport
from investment_strategy.issue_comment_bridge import (
    MachineDispatchDecision,
    parse_dispatch_result_document,
)

_REVISION = "cb8f9ec12d826e0d71897a4c73ece961d00df59e"
_REQUEST_ID = 100
_RUN_ID = 200
_ARTIFACT_ID = 300
_NO_WORK_REVISION = "8bf5007c4dc6fb8368473af3aba86dbe5136a627"
_NO_WORK_FIXTURES = (
    {
        "request_comment_id": 6757650907,
        "run_id": 42746001986,
        "run_attempt": 1,
        "job_id": 129600128294,
        "artifact_id": 13731193002,
        "created_at": "2026-11-10T02:55:29Z",
        "run_started_at": "2026-11-10T02:55:16Z",
        "run_updated_at": "2026-11-10T02:55:33Z",
        "workflow_path": ".github/workflows/scheduled-agent-bridge.yml",
        "event": "issue_comment",
        "head_sha": "8bf5007c4dc6fb8368473af3aba86dbe5136a627",
        "size_in_bytes": 199,
        "digest": "6cf122171ef4a82d09ed3f34e50fe65bb39a04c179beef6afce8dcc1cd6a14cd",
        "raw": (
            b'{"default_branch_revision":"8bf5007c4dc6fb8368473af3aba86dbe5136a627",'
            b'"disposition":"NO_WORK","reason":"no-routed-work",'
            b'"request_comment_id":6757650907,'
            b'"schema":"scheduled-agent-dispatch-result/v1"}\n'
        ),
    },
    {
        "request_comment_id": 6758397830,
        "run_id": 42751607415,
        "run_attempt": 1,
        "job_id": 129617686177,
        "artifact_id": 13733163299,
        "created_at": "2026-11-10T03:46:49Z",
        "run_started_at": "2026-11-10T03:46:36Z",
        "run_updated_at": "2026-11-10T03:46:52Z",
        "workflow_path": ".github/workflows/scheduled-agent-bridge.yml",
        "event": "issue_comment",
        "head_sha": "8bf5007c4dc6fb8368473af3aba86dbe5136a627",
        "size_in_bytes": 199,
        "digest": "7a9da20934c78dd4f03d62432a37901ea853e53d4e88f7f3ba0f3b84e6015625",
        "raw": (
            b'{"default_branch_revision":"8bf5007c4dc6fb8368473af3aba86dbe5136a627",'
            b'"disposition":"NO_WORK","reason":"no-routed-work",'
            b'"request_comment_id":6758397830,'
            b'"schema":"scheduled-agent-dispatch-result/v1"}\n'
        ),
    },
)


def _run(
    *,
    name: str | None = None,
    run_id: int = _RUN_ID,
    request_id: int = _REQUEST_ID,
    attempt: int = 1,
    revision: str = _REVISION,
    started: str = "2026-11-11T00:00:00Z",
    updated: str = "2026-11-11T00:00:20Z",
    status: str = "completed",
    conclusion: str = "success",
) -> dict[str, object]:
    return {
        "id": run_id,
        "name": name or f"Scheduled Agent Dispatch {request_id}",
        "path": ".github/workflows/scheduled-agent-bridge.yml",
        "event": "issue_comment",
        "head_sha": revision,
        "status": status,
        "conclusion": conclusion,
        "run_attempt": attempt,
        "run_started_at": started,
        "updated_at": updated,
    }


def _authorize_document(**overrides: object) -> bytes:
    payload: dict[str, object] = {
        "schema": "scheduled-agent-dispatch-result/v1",
        "request_comment_id": _REQUEST_ID,
        "default_branch_revision": _REVISION,
        "disposition": "AUTHORIZE",
        "issue_number": 138,
        "action": "implement-change",
    }
    payload.update(overrides)
    return (json.dumps(payload, sort_keys=True) + "\n").encode()


def _artifact_listing(
    raw: bytes | None = None,
    *,
    expired: bool = False,
    artifact_id: int = _ARTIFACT_ID,
    request_id: int = _REQUEST_ID,
    run_id: int = _RUN_ID,
    revision: str = _REVISION,
    run_attempt: int = 1,
    created_at: str = "2026-11-11T00:00:10Z",
) -> dict[str, object]:
    content = _authorize_document() if raw is None else raw
    return {
        "total_count": 1,
        "artifacts": [
            {
                "id": artifact_id,
                "name": "dispatch-result.json",
                "expired": expired,
                "size_in_bytes": len(content),
                "digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
                "created_at": created_at,
                "workflow_run": {"id": run_id, "head_sha": revision},
                "run_attempt": run_attempt,
            }
        ],
    }


def _install_observations(
    monkeypatch: pytest.MonkeyPatch,
    raw: bytes,
    *,
    run: dict[str, object] | None = None,
    listing: dict[str, object] | None = None,
    response: carrier.GitHubArtifactBytes | None = None,
    request_id: int = _REQUEST_ID,
    run_id: int = _RUN_ID,
    revision: str = _REVISION,
) -> None:
    def fake_json(
        repository: str,
        token: str,
        path: str,
        *,
        stage: str,
        request_comment_id: int,
        run_id: int,
        revision: str,
    ) -> object:
        del repository, token, stage, request_comment_id
        if path == f"actions/runs/{run_id}":
            return (
                _run(run_id=run_id, request_id=request_id, revision=revision)
                if run is None
                else run
            )
        if path == f"actions/runs/{run_id}/artifacts?per_page=100":
            return (
                _artifact_listing(
                    raw,
                    request_id=request_id,
                    run_id=run_id,
                    revision=revision,
                )
                if listing is None
                else listing
            )
        raise AssertionError(f"unexpected JSON read: {path}")

    def fake_artifact(*_args: object, **_kwargs: object) -> carrier.GitHubArtifactBytes:
        return response or carrier.GitHubArtifactBytes(raw, 200, None)

    monkeypatch.setattr(transport, "_github_json", fake_json)
    monkeypatch.setattr(transport, "_github_artifact", fake_artifact)


def _fetch(
    *,
    request_id: int = _REQUEST_ID,
    run_id: int = _RUN_ID,
    revision: str = _REVISION,
    expected_run_attempt: int | None = None,
    expected_artifact_id: int | None = None,
    expected_artifact_sha256: str | None = None,
) -> transport.VerifiedDispatchArtifact:
    return transport.fetch_dispatch_artifact(
        "owner/repo",
        "token",
        request_comment_id=request_id,
        run_id=run_id,
        current_revision=revision,
        expected_run_attempt=expected_run_attempt,
        expected_artifact_id=expected_artifact_id,
        expected_artifact_sha256=expected_artifact_sha256,
    )


@pytest.mark.parametrize("fixture", _NO_WORK_FIXTURES)
def test_native_no_work_source_fixtures_pin_exact_bytes_and_artifact_metadata(
    monkeypatch: pytest.MonkeyPatch,
    fixture: dict[str, object],
) -> None:
    raw = fixture["raw"]
    assert isinstance(raw, bytes)
    assert len(raw) == fixture["size_in_bytes"] == 199
    assert hashlib.sha256(raw).hexdigest() == fixture["digest"]
    decision = parse_dispatch_result_document(raw)
    assert decision.request_comment_id == fixture["request_comment_id"]
    assert decision.default_branch_revision == _NO_WORK_REVISION
    assert decision.disposition == "NO_WORK"
    assert decision.reason == "no-routed-work"
    assert fixture["run_attempt"] == 1
    assert fixture["event"] == "issue_comment"
    assert fixture["workflow_path"] == ".github/workflows/scheduled-agent-bridge.yml"
    assert fixture["head_sha"] == _NO_WORK_REVISION
    assert cast(str, fixture["created_at"]) >= cast(str, fixture["run_started_at"])
    assert cast(str, fixture["created_at"]) <= cast(str, fixture["run_updated_at"])
    assert cast(int, fixture["job_id"]) > 0
    assert cast(int, fixture["run_id"]) > 0
    assert cast(int, fixture["artifact_id"]) > 0
    request_id = cast(int, fixture["request_comment_id"])
    run_id = cast(int, fixture["run_id"])
    artifact_id = cast(int, fixture["artifact_id"])
    digest = cast(str, fixture["digest"])
    revision = cast(str, fixture["head_sha"])
    run = _run(
        request_id=request_id,
        run_id=run_id,
        revision=revision,
        started=cast(str, fixture["run_started_at"]),
        updated=cast(str, fixture["run_updated_at"]),
    )
    listing = _artifact_listing(
        raw,
        artifact_id=artifact_id,
        request_id=request_id,
        run_id=run_id,
        revision=revision,
        created_at=cast(str, fixture["created_at"]),
    )
    _install_observations(
        monkeypatch,
        raw,
        run=run,
        listing=listing,
        request_id=request_id,
        run_id=run_id,
        revision=revision,
    )
    verified = _fetch(
        request_id=request_id,
        run_id=run_id,
        revision=revision,
        expected_run_attempt=cast(int, fixture["run_attempt"]),
        expected_artifact_id=artifact_id,
        expected_artifact_sha256=digest,
    )
    assert verified.decision.disposition == "NO_WORK"
    assert verified.run_attempt == fixture["run_attempt"]
    assert verified.artifact_id == artifact_id
    assert verified.artifact_size_in_bytes == fixture["size_in_bytes"]
    assert verified.artifact_sha256 == digest


def test_fetch_dispatch_result_reads_exact_completed_attempt_and_matching_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _authorize_document()
    _install_observations(monkeypatch, raw)

    result = _fetch(expected_artifact_id=_ARTIFACT_ID)
    assert result.decision == MachineDispatchDecision(
        request_comment_id=_REQUEST_ID,
        default_branch_revision=_REVISION,
        disposition="AUTHORIZE",
        issue_number=138,
        role="executor",
        action="implement-change",
    )
    assert result.run_attempt == 1
    assert result.artifact_id == _ARTIFACT_ID
    assert result.artifact_size_in_bytes == result.content_length == len(raw)
    assert result.artifact_sha256 == result.content_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.initial_status == 200
    assert result.redirect_host_class is None


def test_fetch_dispatch_result_accepts_actions_display_title_and_ref_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _run(name="Scheduled Agent Issue Comment Bridge")
    run.update(
        {
            "display_title": f"Scheduled Agent Dispatch {_REQUEST_ID}",
            "path": ".github/workflows/scheduled-agent-bridge.yml@main",
        }
    )
    _install_observations(monkeypatch, _authorize_document(), run=run)

    result = _fetch()
    assert result.decision.request_comment_id == _REQUEST_ID


@pytest.mark.parametrize(
    ("run", "classification"),
    [
        (_run(name="Scheduled Agent Dispatch 999"), "IDENTITY_STALE"),
        (_run(attempt=0), "RECOVERABLE_INCOMPLETE"),
        (_run(status="in_progress", conclusion=""), "RECOVERABLE_INCOMPLETE"),
        (_run(conclusion="failure"), "PERMANENT_INVALID"),
    ],
)
def test_run_stage_has_distinct_identity_completion_results(
    monkeypatch: pytest.MonkeyPatch,
    run: dict[str, object],
    classification: str,
) -> None:
    _install_observations(monkeypatch, _authorize_document(), run=run)
    with pytest.raises(transport.DispatchArtifactReadError) as caught:
        _fetch()
    assert caught.value.failure.classification == classification
    assert caught.value.failure.stage in {"run-identity", "run-completion"}
    assert caught.value.failure.mutation_attempted is False


def test_exact_run_attempt_is_checked_against_expected_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_observations(monkeypatch, _authorize_document())
    with pytest.raises(transport.DispatchArtifactReadError) as caught:
        _fetch(expected_run_attempt=2)
    assert caught.value.failure.classification == "IDENTITY_STALE"
    assert caught.value.failure.stage == "run-attempt"


@pytest.mark.parametrize(
    ("listing", "classification"),
    [
        ({"total_count": 1, "artifacts": []}, "RECOVERABLE_INCOMPLETE"),
        (
            {
                "total_count": 2,
                "artifacts": [
                    cast(list[dict[str, object]], _artifact_listing()["artifacts"])[0],
                    cast(list[dict[str, object]], _artifact_listing()["artifacts"])[0],
                ],
            },
            "PERMANENT_INVALID",
        ),
        (_artifact_listing(expired=True), "PERMANENT_INVALID"),
        (_artifact_listing(created_at="2026-10-31T00:00:10Z"), "IDENTITY_STALE"),
        (_artifact_listing(run_id=999), "IDENTITY_STALE"),
        (_artifact_listing(revision="d" * 40), "IDENTITY_STALE"),
    ],
)
def test_artifact_listing_guards_fail_closed_by_stage(
    monkeypatch: pytest.MonkeyPatch,
    listing: dict[str, object],
    classification: str,
) -> None:
    _install_observations(monkeypatch, _authorize_document(), listing=listing)
    with pytest.raises(transport.DispatchArtifactReadError) as caught:
        _fetch()
    assert caught.value.failure.classification == classification
    assert caught.value.failure.mutation_attempted is False


def test_artifact_listing_incomplete_metadata_is_recoverable_not_authorizing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listing = _artifact_listing()
    artifact = cast(list[dict[str, object]], listing["artifacts"])[0]
    del artifact["digest"]
    _install_observations(monkeypatch, _authorize_document(), listing=listing)
    with pytest.raises(transport.DispatchArtifactReadError) as caught:
        _fetch()
    assert caught.value.failure.classification == "RECOVERABLE_INCOMPLETE"
    assert caught.value.failure.stage == "artifact-metadata"


@pytest.mark.parametrize("tamper", ["size", "digest", "truncated", "empty"])
def test_raw_bytes_must_match_both_artifact_integrity_fields(
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    raw = _authorize_document()
    if tamper == "truncated":
        delivered = raw[:-1]
    elif tamper == "empty":
        delivered = b""
    else:
        delivered = raw
    listing = _artifact_listing(raw)
    artifact = cast(list[dict[str, object]], listing["artifacts"])[0]
    if tamper == "size":
        artifact["size_in_bytes"] = len(raw) + 1
    if tamper == "digest":
        artifact["digest"] = f"sha256:{'f' * 64}"
    _install_observations(
        monkeypatch,
        delivered,
        listing=listing,
    )
    with pytest.raises(transport.DispatchArtifactReadError) as caught:
        _fetch()
    assert caught.value.failure.classification == "INTEGRITY_MISMATCH"
    assert caught.value.failure.stage == "artifact-integrity"


@pytest.mark.parametrize("raw", [b"", b"PK\x03\x04unsupported zip", b"{not-json"])
def test_matching_bytes_still_require_the_single_canonical_json_parser(
    monkeypatch: pytest.MonkeyPatch,
    raw: bytes,
) -> None:
    _install_observations(monkeypatch, raw)
    with pytest.raises(transport.DispatchArtifactReadError) as caught:
        _fetch()
    assert caught.value.failure.classification in {
        "PAYLOAD_FORMAT_INVALID",
        "PERMANENT_INVALID",
    }
    assert caught.value.failure.stage in {"artifact-metadata", "canonical-payload"}


@pytest.mark.parametrize(
    "raw",
    [
        _authorize_document(request_comment_id=999),
        _authorize_document(default_branch_revision="e" * 40),
    ],
)
def test_valid_canonical_payload_must_still_match_request_and_revision(
    monkeypatch: pytest.MonkeyPatch,
    raw: bytes,
) -> None:
    _install_observations(monkeypatch, raw)
    with pytest.raises(transport.DispatchArtifactReadError) as caught:
        _fetch()
    assert caught.value.failure.classification == "IDENTITY_STALE"
    assert caught.value.failure.stage == "canonical-identity"


@pytest.mark.parametrize("status", [401, 403, 404])
def test_http_status_classification_preserves_known_status_and_sanitizes_error(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> bytes:
        raise HTTPError(
            "https://api.github.com/private?token=secret",
            status,
            "denied",
            Message(),
            None,
        )

    monkeypatch.setattr(transport, "github_read_bytes_with_retry", fail)
    with pytest.raises(transport.DispatchArtifactReadError) as caught:
        transport._github_json(
            "owner/repo",
            "token-value",
            "actions/runs/200",
            stage="run-read",
            request_comment_id=_REQUEST_ID,
            run_id=_RUN_ID,
            revision=_REVISION,
        )
    diagnostic = caught.value.diagnostic()
    assert diagnostic["classification"] == "PERMANENT_INVALID"
    assert diagnostic["http_status"] == status
    assert diagnostic["mutation_attempted"] is False
    assert "token" not in json.dumps(diagnostic).lower()
    assert "api.github.com" not in json.dumps(diagnostic)


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_exhausted_transient_github_status_remains_read_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> bytes:
        raise HTTPError("https://api.github.com/", status, "transient", Message(), None)

    monkeypatch.setattr(transport, "github_read_bytes_with_retry", fail)
    with pytest.raises(transport.DispatchArtifactReadError) as caught:
        transport._github_json(
            "owner/repo",
            "token",
            "actions/runs/200",
            stage="run-read",
            request_comment_id=_REQUEST_ID,
            run_id=_RUN_ID,
            revision=_REVISION,
        )
    assert caught.value.failure.classification == "READ_UNAVAILABLE"
    assert caught.value.failure.http_status == status
    assert caught.value.failure.mutation_attempted is False


def test_metamorphically_equivalent_direct_redirect_and_connector_bytes_share_one_parser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _NO_WORK_FIXTURES[0]
    raw = fixture["raw"]
    assert isinstance(raw, bytes)
    request_id = cast(int, fixture["request_comment_id"])
    run_id = cast(int, fixture["run_id"])
    artifact_id = cast(int, fixture["artifact_id"])
    digest = cast(str, fixture["digest"])
    _install_observations(
        monkeypatch,
        raw,
        response=carrier.GitHubArtifactBytes(raw, 200, None),
        request_id=request_id,
        run_id=run_id,
        revision=_NO_WORK_REVISION,
        listing=_artifact_listing(
            raw,
            artifact_id=artifact_id,
            request_id=request_id,
            run_id=run_id,
            revision=_NO_WORK_REVISION,
        ),
    )
    native_direct = _fetch(
        request_id=request_id,
        run_id=run_id,
        revision=_NO_WORK_REVISION,
        expected_run_attempt=1,
        expected_artifact_id=artifact_id,
        expected_artifact_sha256=digest,
    )
    monkeypatch.setattr(
        transport,
        "_github_artifact",
        lambda *_args, **_kwargs: carrier.GitHubArtifactBytes(raw, 302, "actions"),
    )
    native_redirect = _fetch(
        request_id=request_id,
        run_id=run_id,
        revision=_NO_WORK_REVISION,
        expected_run_attempt=1,
        expected_artifact_id=artifact_id,
        expected_artifact_sha256=digest,
    )
    connector_bytes = parse_dispatch_result_document(raw)
    assert native_direct.decision == native_redirect.decision == connector_bytes
    assert native_direct.decision.disposition == "NO_WORK"
    assert (native_direct.initial_status, native_direct.redirect_host_class) == (200, None)
    assert (native_redirect.initial_status, native_redirect.redirect_host_class) == (302, "actions")
    for observed in (native_direct, native_redirect):
        assert observed.content_length == fixture["size_in_bytes"]
        assert observed.content_sha256 == digest


def test_github_artifact_reader_accepts_exact_direct_200_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = b"direct artifact bytes"

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            assert size == carrier.MAX_GITHUB_ARTIFACT_BYTES + 1
            return raw

        def getcode(self) -> int:
            return 200

    class Opener:
        def open(self, request: Request, timeout: int) -> Response:
            assert timeout == 30
            assert request.get_method() == "GET"
            assert request.get_header("Accept") == "application/octet-stream"
            assert request.get_header("Authorization") == "Bearer token"
            return Response()

    def build(*handlers: object) -> Opener:
        assert handlers == (carrier._NoRedirect,)
        return Opener()

    monkeypatch.setattr(carrier, "build_opener", build)
    result = carrier.read_github_artifact(
        "owner/repo",
        "token",
        "actions/artifacts/300/zip",
        accept="application/octet-stream",
    )
    assert result.content == raw
    assert result.initial_status == 200
    assert result.redirect_host_class is None


def test_github_artifact_reader_rejects_unexpected_direct_success_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            return b"partial content"

        def getcode(self) -> int:
            return 206

    class Opener:
        def open(self, _request: Request, *, timeout: int) -> Response:
            assert timeout == 30
            return Response()

    monkeypatch.setattr(carrier, "build_opener", lambda *_handlers: Opener())
    with pytest.raises(carrier.GitHubArtifactReadError) as caught:
        carrier.read_github_artifact(
            "owner/repo",
            "token",
            "actions/artifacts/300/zip",
            accept="application/octet-stream",
        )

    assert caught.value.stage == "artifact-api-read"
    assert caught.value.classification == "PERMANENT_INVALID"
    assert caught.value.http_status == 206
    assert caught.value.exception_category == "UnexpectedSuccessStatus"


def test_github_artifact_reader_uses_trusted_redirect_without_forwarding_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirect = "https://pipelines.actions.githubusercontent.com/signed-artifact"
    raw = b"raw artifact"

    class Response:
        def __init__(self, value: bytes) -> None:
            self.value = value

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int = -1) -> bytes:
            return self.value

        def getcode(self) -> int:
            return 200

    class Opener:
        def open(self, request: Request, timeout: int) -> Response:
            del timeout
            if request.full_url.startswith("https://api.github.com/"):
                assert request.full_url == (
                    "https://api.github.com/repos/owner/repo/actions/artifacts/300/zip"
                )
                assert request.get_header("Authorization") == "Bearer token"
                headers = Message()
                headers["Location"] = redirect
                raise HTTPError(request.full_url, 302, "Found", headers, BytesIO())
            assert request.full_url == redirect
            assert request.get_header("Authorization") is None
            return Response(raw)

    openers: list[Opener] = []

    def build(*handlers: object) -> Opener:
        if handlers:
            assert len(handlers) == 1
            assert handlers[0] is carrier._NoRedirect
        opener = Opener()
        openers.append(opener)
        return opener

    monkeypatch.setattr(carrier, "build_opener", build)
    result = carrier.read_github_artifact(
        "owner/repo",
        "token",
        "actions/artifacts/300/zip",
        accept="application/octet-stream",
    )
    assert result.content == raw
    assert result.initial_status == 302
    assert result.redirect_host_class == "actions"
    assert len(openers) == 2


@pytest.mark.parametrize(
    ("location", "expected_category"),
    [
        (None, "MissingLocation"),
        ("http://pipelines.actions.githubusercontent.com/signed", "UntrustedLocation"),
        ("https://attacker.invalid/signed", "UntrustedLocation"),
    ],
)
def test_unsafe_redirect_fails_with_redacted_typed_error(
    monkeypatch: pytest.MonkeyPatch,
    location: str | None,
    expected_category: str,
) -> None:
    class Opener:
        def open(self, request: Request, timeout: int) -> object:
            del timeout
            headers = Message()
            if location is not None:
                headers["Location"] = location
            raise HTTPError(request.full_url, 302, "Found", headers, BytesIO())

    monkeypatch.setattr(carrier, "build_opener", lambda *_args: Opener())
    with pytest.raises(carrier.GitHubArtifactReadError) as caught:
        carrier.read_github_artifact("owner/repo", "token", "actions/artifacts/300/zip")
    assert caught.value.classification == "REDIRECT_UNTRUSTED"
    assert caught.value.exception_category == expected_category
    assert "attacker.invalid" not in str(caught.value)


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_github_get_retries_only_bounded_transient_statuses(status: int) -> None:
    calls = 0
    waits: list[float] = []

    def open_request(_request: Request, *, timeout: int) -> object:
        nonlocal calls
        del timeout
        calls += 1
        raise HTTPError("https://api.github.com/", status, "transient", Message(), None)

    with pytest.raises(HTTPError):
        carrier.github_read_bytes_with_retry(
            Request("https://api.github.com/"),
            open_request=open_request,
            wait=waits.append,
        )
    assert calls == 3
    assert waits == [0.25, 0.5]


@pytest.mark.parametrize("status", [401, 403, 404])
def test_github_get_does_not_retry_authorization_or_identity_status(status: int) -> None:
    calls = 0

    def open_request(_request: Request, *, timeout: int) -> object:
        nonlocal calls
        del timeout
        calls += 1
        raise HTTPError("https://api.github.com/", status, "denied", Message(), None)

    with pytest.raises(HTTPError):
        carrier.github_read_bytes_with_retry(
            Request("https://api.github.com/"),
            open_request=open_request,
            wait=lambda _delay: None,
        )
    assert calls == 1


@pytest.mark.parametrize("error", [TimeoutError("socket timeout")])
def test_github_get_retries_bounded_timeouts_only(error: BaseException) -> None:
    calls = 0
    waits: list[float] = []

    def open_request(_request: Request, *, timeout: int) -> object:
        nonlocal calls
        del timeout
        calls += 1
        raise error

    with pytest.raises(TimeoutError):
        carrier.github_read_bytes_with_retry(
            Request("https://api.github.com/"),
            open_request=open_request,
            wait=waits.append,
        )
    assert calls == 3
    assert waits == [0.25, 0.5]


def test_github_retry_helper_rejects_non_get_without_attempting_io() -> None:
    calls = 0

    def open_request(_request: Request, *, timeout: int) -> object:
        nonlocal calls
        del timeout
        calls += 1
        return object()

    with pytest.raises(ValueError, match="only supports GET"):
        carrier.github_read_bytes_with_retry(
            Request("https://api.github.com/", data=b"{}"),
            open_request=open_request,
            wait=lambda _delay: None,
        )
    assert calls == 0
