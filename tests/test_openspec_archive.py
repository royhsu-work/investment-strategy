"""Tests for the bounded OpenSpec archive request parser."""

from __future__ import annotations

from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

_CHANGE = "simplify-scheduled-agent-control-plane"
_REVISION = "f" * 40
_REPOSITORY = "royhsu-work/investment-strategy"


def _archive_script() -> dict[str, Any]:
    path = Path(__file__).parents[1] / ".github" / "scripts" / "openspec_archive.py"
    return run_path(str(path))


def _request_body() -> str:
    return (
        "ARCHIVE_REQUEST
"
        "Workflow: #138
"
        f"Change: {_CHANGE}
"
        "Action: finalize-change
"
        f"Revision: {_REVISION}"
    )


def _args(*, body: str, actor: str = "github-actions[bot]") -> Any:
    from argparse import Namespace

    return Namespace(
        event_name="issue_comment",
        comment_body=body,
        comment_actor=actor,
        comment_issue="138",
        comment_repository=_REPOSITORY,
        expected_repository=_REPOSITORY,
        manual_change=None,
        merged="false",
        head_ref="",
        head_repo="",
        base_repo="",
        recovery="false",
        changed_files="",
        changes_root="openspec/changes",
    )


def test_application_archive_request_is_exactly_classified(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _archive_script()

    module["_classify"](_args(body=_request_body()))

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "action=evaluate",
        f"change={_CHANGE}",
        "mode=request",
        "reason=application-archive-request",
        "request_issue=138",
        f"request_revision={_REVISION}",
    ]


def test_archive_request_rejects_non_application_actor() -> None:
    module = _archive_script()

    with pytest.raises(SystemExit):
        module["_classify"](_args(body=_request_body(), actor="royhsu-work"))


def test_archive_request_rejects_extra_lines() -> None:
    module = _archive_script()

    with pytest.raises(SystemExit):
        module["_classify"](_args(body=_request_body() + "
extra"))
