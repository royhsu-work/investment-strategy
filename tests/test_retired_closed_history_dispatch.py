"""Production-shaped regressions for administratively retired closed workflow history."""

from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_runtime as runtime
import investment_strategy.workflow_dispatch as workflow_dispatch


def _formal_140_payload() -> dict[str, object]:
    return {
        "number": 140,
        "state": "open",
        "body": "Change: validate-no-api-issue-comment-bridge",
        "labels": [{"name": "agent:lead"}, {"name": "action:finalize-change"}],
        "created_at": "2026-08-23T11:39:39Z",
        "closed_at": None,
    }


def _retired_133_payload() -> dict[str, object]:
    return {
        "number": 133,
        "state": "closed",
        "state_reason": "not_planned",
        "body": "Change: enforce-runtime-dispatch-preconditions\n",
        "labels": [{"name": "human:notified"}],
        "created_at": "2026-08-21T17:21:27Z",
        "closed_at": "2026-08-23T12:14:54Z",
        "comments": 84,
    }


def _retirement_comment(
    *,
    created_at: str = "2026-08-23T12:05:21Z",
    updated_at: str | None = None,
    performed_via_github_app: object = None,
) -> dict[str, object]:
    return {
        "id": 5385902831,
        "body": (
            "Human administrative retirement: abandon Change "
            "enforce-runtime-dispatch-preconditions. Do not recover or resume #133. "
            "Remaining runtime-enforcement work is superseded by #140."
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": created_at,
        "updated_at": updated_at or created_at,
        "performed_via_github_app": performed_via_github_app,
    }


def test_retired_133_clears_structurally_without_closed_change_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime,
        "_github_open_issue_pages",
        lambda repository, token: ((_formal_140_payload(),),),
    )
    monkeypatch.setattr(
        runtime,
        "_github_closed_issue_pages",
        lambda repository, token: ((_retired_133_payload(),),),
    )

    def structural_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        assert url.endswith("/issues/133/comments?per_page=100&page=1")
        return (_retirement_comment(),)

    monkeypatch.setattr(runtime, "_github_get_list_page", structural_page)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("retired history must not inspect closed Change state")

    monkeypatch.setattr(runtime, "_legacy_terminal_evidence_from_checkout", forbidden)
    monkeypatch.setattr(runtime, "_github_issue_comment_pages", forbidden)
    monkeypatch.setattr(runtime, "_github_issue", forbidden)

    preflight = runtime.acquire_current_github_preflight(
        "royhsu-work/investment-strategy",
        "token",
        repository_root=tmp_path,
    )
    decision = workflow_dispatch.classify_dispatch(preflight)

    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 140
    assert decision.selected_routing == ("lead", "finalize-change")
    assert all(item.state == "open" for item in preflight.issues)


@pytest.mark.parametrize(
    ("raw_patch", "comment"),
    [
        ({"state_reason": "completed"}, _retirement_comment()),
        (
            {},
            _retirement_comment(performed_via_github_app={"slug": "chatgpt-codex-connector"}),
        ),
        ({}, _retirement_comment(updated_at="2026-08-23T12:06:00Z")),
        ({}, _retirement_comment(created_at="2026-08-23T12:15:00Z")),
    ],
)
def test_retirement_structural_proof_rejects_unsafe_shapes(
    monkeypatch: pytest.MonkeyPatch,
    raw_patch: dict[str, object],
    comment: dict[str, object],
) -> None:
    raw = _retired_133_payload()
    raw.update(raw_patch)
    observation = runtime.normalize_github_issue(raw)
    assert observation is not None

    monkeypatch.setattr(
        runtime,
        "_github_last_visible_issue_comment",
        lambda *args, **kwargs: comment,
    )

    assert not runtime._structural_terminal_marker(
        "royhsu-work/investment-strategy",
        "token",
        raw_issue=raw,
        observation=observation,
    )


def test_retirement_comment_does_not_clear_routed_closed_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _retired_133_payload()
    raw["labels"] = [{"name": "agent:lead"}, {"name": "action:finalize-change"}]
    observation = runtime.normalize_github_issue(raw)
    assert observation is not None

    monkeypatch.setattr(
        runtime,
        "_github_last_visible_issue_comment",
        lambda *args, **kwargs: _retirement_comment(),
    )

    assert not runtime._structural_terminal_marker(
        "royhsu-work/investment-strategy",
        "token",
        raw_issue=raw,
        observation=observation,
    )
