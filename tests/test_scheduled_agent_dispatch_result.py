"""Regression coverage for exact run-scoped dispatch result transport."""

from __future__ import annotations

import json
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request

import pytest

import investment_strategy.scheduled_agent_dispatch_result as transport
from investment_strategy.issue_comment_bridge import (
    MachineDispatchDecision,
    parse_dispatch_result_document,
)

_REVISION = "cb8f9ec12d826e0d71897a4c73ece961d00df59e"
_REQUEST_ID = 100
_RUN_ID = 200
_ARTIFACT_ID = 300


def _run(*, name: str | None = None) -> dict[str, object]:
    return {
        "id": _RUN_ID,
        "name": name or f"Scheduled Agent Dispatch {_REQUEST_ID}",
        "path": ".github/workflows/scheduled-agent-bridge.yml",
        "event": "issue_comment",
        "head_sha": _REVISION,
        "status": "completed",
        "conclusion": "success",
    }


def _artifact_listing(*, expired: bool = False) -> dict[str, object]:
    return {
        "total_count": 1,
        "artifacts": [
            {
                "id": _ARTIFACT_ID,
                "name": "dispatch-result.json",
                "expired": expired,
            }
        ],
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


def test_fetch_dispatch_result_reads_only_exact_successful_run_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_json(repository: str, token: str, path: str) -> object:
        del repository, token
        if path == f"actions/runs/{_RUN_ID}":
            return _run()
        if path == f"actions/runs/{_RUN_ID}/artifacts?per_page=100":
            return _artifact_listing()
        raise AssertionError(f"unexpected JSON read: {path}")

    def fake_bytes(repository: str, token: str, path: str) -> bytes:
        del repository, token
        assert path == f"actions/artifacts/{_ARTIFACT_ID}/zip"
        return _authorize_document()

    monkeypatch.setattr(transport, "_github_json", fake_json)
    monkeypatch.setattr(transport, "_github_bytes", fake_bytes)

    result = transport.fetch_dispatch_result(
        "owner/repo",
        "token",
        request_comment_id=_REQUEST_ID,
        run_id=_RUN_ID,
        current_revision=_REVISION,
    )

    assert result == MachineDispatchDecision(
        request_comment_id=_REQUEST_ID,
        default_branch_revision=_REVISION,
        disposition="AUTHORIZE",
        issue_number=138,
        role="executor",
        action="implement-change",
    )


def test_fetch_dispatch_result_rejects_wrong_run_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        transport,
        "_github_json",
        lambda repository, token, path: _run(name="Scheduled Agent Dispatch 999"),
    )
    with pytest.raises(RuntimeError, match="identity or completion"):
        transport.fetch_dispatch_result(
            "owner/repo",
            "token",
            request_comment_id=_REQUEST_ID,
            run_id=_RUN_ID,
            current_revision=_REVISION,
        )


def test_fetch_dispatch_result_rejects_zero_or_multiple_matching_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listings = (
        {"total_count": 0, "artifacts": []},
        {
            "total_count": 2,
            "artifacts": [
                {"id": 300, "name": "dispatch-result.json", "expired": False},
                {"id": 301, "name": "dispatch-result.json", "expired": False},
            ],
        },
    )
    for listing in listings:

        def fake_json(repository: str, token: str, path: str, *, value: object = listing) -> object:
            del repository, token
            return _run() if path == f"actions/runs/{_RUN_ID}" else value

        monkeypatch.setattr(transport, "_github_json", fake_json)
        with pytest.raises(RuntimeError, match="one dispatch-result.json Artifact"):
            transport.fetch_dispatch_result(
                "owner/repo",
                "token",
                request_comment_id=_REQUEST_ID,
                run_id=_RUN_ID,
                current_revision=_REVISION,
            )


def test_fetch_dispatch_result_rejects_expired_or_stale_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_json(repository: str, token: str, path: str) -> object:
        del repository, token
        return _run() if path == f"actions/runs/{_RUN_ID}" else _artifact_listing(expired=True)

    monkeypatch.setattr(transport, "_github_json", fake_json)
    with pytest.raises(RuntimeError, match="expired or invalid"):
        transport.fetch_dispatch_result(
            "owner/repo",
            "token",
            request_comment_id=_REQUEST_ID,
            run_id=_RUN_ID,
            current_revision=_REVISION,
        )


def test_artifact_document_omits_role_and_derives_it_from_action() -> None:
    result = parse_dispatch_result_document(_authorize_document())
    assert result.role == "executor"
    assert result.action == "implement-change"

    with pytest.raises(RuntimeError, match="schema is invalid"):
        parse_dispatch_result_document(_authorize_document(role="executor"))


def test_artifact_document_rejects_malformed_and_revision_mismatch() -> None:
    with pytest.raises(RuntimeError, match="UTF-8 JSON"):
        parse_dispatch_result_document(b"not-json")

    with pytest.raises(RuntimeError, match="identity is invalid"):
        parse_dispatch_result_document(_authorize_document(default_branch_revision="wrong"))


def test_github_bytes_reads_signed_redirect_without_forwarding_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirect = "https://pipelines.actions.githubusercontent.com/signed-artifact"

    class _Response:
        def __init__(self, value: bytes) -> None:
            self.value = value

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return self.value

    class _Opener:
        def open(self, request: Request, timeout: int) -> _Response:
            del timeout
            assert request.full_url == (
                "https://api.github.com/repos/owner/repo/actions/artifacts/300/zip"
            )
            assert request.get_header("Authorization") == "Bearer token"
            headers = Message()
            headers["Location"] = redirect
            raise HTTPError(request.full_url, 302, "Found", headers, BytesIO())

    def fake_build_opener(handler: object) -> _Opener:
        assert handler is transport._NoRedirect
        return _Opener()

    def fake_urlopen(request: Request, timeout: int) -> _Response:
        del timeout
        assert request.full_url == redirect
        assert request.get_header("Authorization") is None
        return _Response(b"raw artifact")

    monkeypatch.setattr(transport, "build_opener", fake_build_opener)
    monkeypatch.setattr(transport, "urlopen", fake_urlopen)

    assert (
        transport._github_bytes("owner/repo", "token", "actions/artifacts/300/zip")
        == b"raw artifact"
    )
