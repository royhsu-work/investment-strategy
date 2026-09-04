"""Regression coverage for exact run-scoped dispatch result transport."""

from __future__ import annotations

import pytest
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request

import investment_strategy.scheduled_agent_dispatch_result as transport
from investment_strategy.issue_comment_bridge import (
    MachineDispatchDecision,
    render_run_scoped_dispatch_result,
)
from investment_strategy.workflow_dispatch import DispatchDecision, ObservationProvenance

_REVISION = "cb8f9ec12d826e0d71897a4c73ece961d00df59e"
_REQUEST_ID = 100
_RUN_ID = 200


def _decision() -> DispatchDecision:
    return DispatchDecision(
        completeness="COMPLETE",
        observation_provenance=ObservationProvenance.QUALIFIED,
        formal_issue_ids=(138,),
        preactivation_candidate_ids=(),
        selected_issue_id=138,
        selected_routing=("executor", "implement-change"),
        disposition="AUTHORIZE",
        reason="unused",
    )


def test_fetch_dispatch_result_reads_only_exact_successful_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = {
        "id": _RUN_ID,
        "name": f"Scheduled Agent Dispatch {_REQUEST_ID}",
        "path": ".github/workflows/scheduled-agent-bridge.yml",
        "event": "issue_comment",
        "head_sha": _REVISION,
        "status": "completed",
        "conclusion": "success",
    }
    jobs = {"jobs": [{"id": 300, "name": "bridge", "status": "completed", "conclusion": "success"}]}
    log = render_run_scoped_dispatch_result(
        request_comment_id=_REQUEST_ID,
        default_branch_revision=_REVISION,
        decision=_decision(),
    )

    def fake_json(repository: str, token: str, path: str) -> object:
        del repository, token
        if path == f"actions/runs/{_RUN_ID}":
            return run
        if path == f"actions/runs/{_RUN_ID}/jobs?per_page=100":
            return jobs
        raise AssertionError(f"unexpected JSON read: {path}")

    def fake_text(repository: str, token: str, path: str) -> str:
        del repository, token
        assert path == "actions/jobs/300/logs"
        return log

    monkeypatch.setattr(transport, "_github_json", fake_json)
    monkeypatch.setattr(transport, "_github_text", fake_text)

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
        lambda repository, token, path: {
            "id": _RUN_ID,
            "name": "Scheduled Agent Dispatch 999",
            "path": ".github/workflows/scheduled-agent-bridge.yml",
            "event": "issue_comment",
            "head_sha": _REVISION,
            "status": "completed",
            "conclusion": "success",
        },
    )
    with pytest.raises(RuntimeError, match="identity or completion"):
        transport.fetch_dispatch_result(
            "owner/repo",
            "token",
            request_comment_id=_REQUEST_ID,
            run_id=_RUN_ID,
            current_revision=_REVISION,
        )


def test_fetch_dispatch_result_rejects_ambiguous_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        transport,
        "_github_json",
        lambda repository, token, path: (
            {
                "id": _RUN_ID,
                "name": f"Scheduled Agent Dispatch {_REQUEST_ID}",
                "path": ".github/workflows/scheduled-agent-bridge.yml",
                "event": "issue_comment",
                "head_sha": _REVISION,
                "status": "completed",
                "conclusion": "success",
            }
            if path == f"actions/runs/{_RUN_ID}"
            else {"jobs": [{"id": 300}, {"id": 301}]}
        ),
    )
    with pytest.raises(RuntimeError, match="one bridge job"):
        transport.fetch_dispatch_result(
            "owner/repo",
            "token",
            request_comment_id=_REQUEST_ID,
            run_id=_RUN_ID,
            current_revision=_REVISION,
        )


def test_github_text_reads_signed_redirect_without_forwarding_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirect = "https://pipelines.actions.githubusercontent.com/signed-log"

    class _Response:
        def __init__(self, value: bytes) -> None:
            self.value = value

        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return self.value

    class _Opener:
        def open(self, request: Request, timeout: int) -> _Response:
            del timeout
            assert request.full_url == (
                "https://api.github.com/repos/owner/repo/actions/jobs/300/logs"
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
        return _Response(b"signed log")

    monkeypatch.setattr(transport, "build_opener", fake_build_opener)
    monkeypatch.setattr(transport, "urlopen", fake_urlopen)

    assert (
        transport._github_text("owner/repo", "token", "actions/jobs/300/logs")
        == "signed log"
    )
