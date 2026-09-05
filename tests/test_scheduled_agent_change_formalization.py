import base64
import json
from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_change_formalization as formalization
from investment_strategy.issue_comment_bridge import MachineDispatchDecision
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_validation_resource import (
    WorkProductFile,
    WorkProductManifest,
)

_BASE = "a" * 40
_BLOB = "b" * 40
_REVISION = "c" * 40
_CHANGE = "restore-lifecycle-correction-routing"


def _manifest(*, expected_sha: str | None = None) -> WorkProductManifest:
    return WorkProductManifest(
        branch=f"agent/{_CHANGE}",
        base_sha=_BASE,
        message="OpenSpec: restore lifecycle correction routing",
        files=(
            WorkProductFile(
                path=f"openspec/changes/{_CHANGE}/proposal.md",
                blob_sha=_BLOB,
                expected_sha=expected_sha,
            ),
        ),
    )


def _request(*, expected_sha: str | None = None) -> formalization.FormalizeChangeRequest:
    return formalization.FormalizeChangeRequest(
        dispatch_request_comment_id=10,
        dispatch_run_id=20,
        proposed_change=_CHANGE,
        manifest=_manifest(expected_sha=expected_sha),
    )


def test_parse_formalize_change_request_is_exact_and_content_addressed() -> None:
    encoded = base64.b64encode(
        json.dumps(
            {
                "branch": f"agent/{_CHANGE}",
                "base_sha": _BASE,
                "message": "OpenSpec: restore lifecycle correction routing",
                "files": [
                    {
                        "path": f"openspec/changes/{_CHANGE}/proposal.md",
                        "blob_sha": _BLOB,
                        "expected_sha": None,
                    }
                ],
            }
        ).encode()
    ).decode()
    request = formalization.parse_formalize_change_request(
        "\n".join(
            (
                "FORMALIZE_CHANGE_REQUEST",
                "Dispatch-Request-Comment-ID: 10",
                "Dispatch-Run-ID: 20",
                f"Proposed-Change: {_CHANGE}",
                f"Manifest-B64: {encoded}",
            )
        )
    )
    assert request == _request()
    with pytest.raises(ValueError):
        formalization.parse_formalize_change_request(
            "\n".join(
                (
                    "FORMALIZE_CHANGE_REQUEST",
                    "Dispatch-Request-Comment-ID: 10",
                    "Dispatch-Run-ID: 20",
                    "Proposed-Change: unset",
                    f"Manifest-B64: {encoded}",
                )
            )
        )


def test_source_from_dispatch_binds_exact_request_and_revision() -> None:
    dispatch = MachineDispatchDecision(
        request_comment_id=10,
        default_branch_revision=_BASE,
        disposition="AUTHORIZE",
        issue_number=169,
        role="lead",
        action="propose-change",
        reason=None,
    )
    assert formalization.source_from_dispatch(_request(), dispatch, _BASE) == WorkerRequest(
        169, "lead", "propose-change"
    )
    with pytest.raises(ValueError, match="stale"):
        formalization.source_from_dispatch(_request(), dispatch, "d" * 40)


def test_apply_formalization_uses_application_owned_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(169, "lead", "propose-change")
    persisted: list[tuple[int, str]] = []
    monkeypatch.setattr(formalization, "_current_authorized_request", lambda *_: source)
    monkeypatch.setattr(formalization, "_current_default_branch", lambda *_: "main")
    monkeypatch.setattr(formalization, "_ref_head_sha", lambda *args: _BASE)
    monkeypatch.setattr(formalization, "_review_openspec_required", lambda *_: True)
    monkeypatch.setattr(formalization, "_content_sha_at", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        formalization,
        "_issue",
        lambda *args: {"number": 169, "state": "open", "body": "Change: unset\n"},
    )
    monkeypatch.setattr(formalization, "_ensure_revision", lambda *args: _REVISION)
    monkeypatch.setattr(formalization, "_ensure_pr", lambda *args: 201)
    monkeypatch.setattr(
        formalization,
        "_persist_change",
        lambda repository, token, observed_source, change: persisted.append(
            (observed_source.issue_number, change)
        ),
    )
    monkeypatch.setattr(
        formalization,
        "_open_pr_payload",
        lambda **kwargs: {"head": {"sha": _REVISION}},
    )

    target = formalization.apply_change_formalization(
        _request(),
        source,
        30,
        repository="royhsu-work/investment-strategy",
        token="token",
        default_branch="main",
    )

    assert target.revision == _REVISION
    assert target.pr_number == 201
    assert target.change == _CHANGE
    assert target.correlation == "formalize-change-request-30"
    assert persisted == [(169, _CHANGE)]


def test_formalization_rejects_worker_authority_and_existing_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="Lead / propose-change"):
        formalization.apply_change_formalization(
            _request(),
            WorkerRequest(169, "executor", "implement-change"),
            30,
            repository="royhsu-work/investment-strategy",
            token="token",
            default_branch="main",
        )

    source = WorkerRequest(169, "lead", "propose-change")
    monkeypatch.setattr(formalization, "_current_authorized_request", lambda *_: source)
    monkeypatch.setattr(formalization, "_current_default_branch", lambda *_: "main")
    monkeypatch.setattr(formalization, "_ref_head_sha", lambda *args: _BASE)
    monkeypatch.setattr(formalization, "_review_openspec_required", lambda *_: True)
    with pytest.raises(RuntimeError, match="only new Change paths"):
        formalization.apply_change_formalization(
            _request(expected_sha="d" * 40),
            source,
            30,
            repository="royhsu-work/investment-strategy",
            token="token",
            default_branch="main",
        )


def test_application_workflow_exposes_formalization_as_validation_resource() -> None:
    workflow = Path(".github/workflows/scheduled-agent-application.yml").read_text(encoding="utf-8")
    assert "startsWith(github.event.comment.body, 'FORMALIZE_CHANGE_REQUEST')" in workflow
    assert "investment_strategy.scheduled_agent_change_formalization" in workflow
    assert "FORMALIZATION_REQUIRED" in workflow
    assert "FORMALIZATION_REVISION" in workflow
