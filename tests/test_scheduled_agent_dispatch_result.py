"""Regression coverage for exact run-scoped dispatch result transport."""

from __future__ import annotations

import pytest

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
        recovery_candidate_ids=(),
        preactivation_candidate_ids=(),
        selected_issue_id=138,
        selected_routing=("executor", "implement-change"),
        disposition="AUTHORIZE",
        reason="unused",
    )


def test_fetch_dispatch_result_reads_only_exact_successful_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _decision()
    run = {
        "id": _RUN_ID,
        "name": f"Scheduled Agent Dispatch {_REQUEST_ID}",
        "path": ".github/workflows/scheduled-agent-bridge.yml",
        "event": "issue_comment",
        "head_sha": _REVISION,
        "status": "completed",
        "conclusion": "success",
    }
    jobs = {
        "jobs": [
            {"id": 300, "name": "bridge", "status": "completed", "conclusion": "success"}
        ]
    }
    log = render_run_scoped_dispatch_result(
        request_comment_id=_REQUEST_ID,
        default_branch_revision=_REVISION,
        decision=decision,
    )
    observed: list[str] = []

    def fake_json(repository: str, token: str, path: str) -> object:
        del repository, token
        observed.append(path)
        if path == f"actions/runs/{_RUN_ID}":
            return run
        if path == f"actions/runs/{_RUN_ID}/jobs?per_page=100":
            return jobs
        raise AssertionError(f"unexpected JSON read: {path}")

    def fake_text(repository: str, token: str, path: str) -> str:
        del repository, token
        observed.append(path)
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
    assert observed == [
        f"actions/runs/{_RUN_ID}",
        f"actions/runs/{_RUN_ID}/jobs?per_page=100",
        "actions/jobs/300/logs",
    ]


def test_fetch_dispatch_result_rejects_wrong_request_run_name(
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
