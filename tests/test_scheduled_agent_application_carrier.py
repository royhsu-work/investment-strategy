"""Production-shaped regression coverage for application carrier qualification."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from investment_strategy import scheduled_agent_application_carrier as carrier
from investment_strategy.scheduled_agent_runtime import WorkerRequest

REPOSITORY = "royhsu-work/investment-strategy"
CHANGE = "qualify-active-formal-consequences"
MAIN = "1" * 40
HEAD = "2" * 40
HISTORICAL_HEAD = "3" * 40
MERGE = "4" * 40


def _repo(name: str = REPOSITORY) -> dict[str, object]:
    return {"full_name": name}


def _pr(
    number: int,
    *,
    branch: str,
    head_sha: str,
    state: str = "open",
    merged: bool = False,
    merged_at: str | None = None,
    merge_commit_sha: str | None = None,
    issue_number: int = 229,
) -> dict[str, object]:
    return {
        "number": number,
        "state": state,
        "merged": merged,
        "merged_at": merged_at,
        "merge_commit_sha": merge_commit_sha,
        "body": f"Continue OpenSpec change `{CHANGE}` after the merged carrier.\n\nRefs #{issue_number}",
        "head": {
            "ref": branch,
            "sha": head_sha,
            "repo": _repo(),
        },
        "base": {
            "ref": "main",
            "sha": MAIN,
            "repo": _repo(),
        },
    }


def _historical_pr() -> dict[str, object]:
    payload = _pr(
        232,
        branch=f"agent/{CHANGE}",
        head_sha=HISTORICAL_HEAD,
        state="closed",
        merged=True,
        merged_at="2026-09-10T00:00:00Z",
        merge_commit_sha=MERGE,
    )
    payload["body"] = "Refs #229"
    return payload


def _continuation_pr(
    *,
    number: int = 236,
    branch: str | None = None,
    head_sha: str = HEAD,
    issue_number: int = 229,
) -> dict[str, object]:
    return _pr(
        number,
        branch=branch or f"agent/{CHANGE}-continuation-232",
        head_sha=head_sha,
        issue_number=issue_number,
    )


_DEFAULT_HISTORICAL = object()


def _fake_github(
    *,
    current_pr: dict[str, object] | None = None,
    historical_pr: dict[str, object] | None | object = _DEFAULT_HISTORICAL,
    open_prs: list[dict[str, object]] | None = None,
    pr_files: list[dict[str, object]] | None = None,
    default_is_ancestor: bool = True,
    historical_is_ancestor: bool = True,
    branch_ref_sha: str | None = HEAD,
    default_revision: str = MAIN,
    issue_body: str | None = None,
) -> Callable[..., object | None]:
    current = current_pr or _continuation_pr()
    historical = (
        _historical_pr()
        if historical_pr is _DEFAULT_HISTORICAL
        else historical_pr
    )
    opens = [current] if open_prs is None else open_prs
    files = [{"filename": "src/investment_strategy/example.py"}] if pr_files is None else pr_files
    body = issue_body or f"Change: {CHANGE}\n"

    def fake(
        repository: str,
        token: str,
        api_path: str,
        *,
        allow_not_found: bool = False,
    ) -> object | None:
        assert repository == REPOSITORY
        assert token == "token"
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main":
            return {"object": {"sha": default_revision}}
        if api_path == "issues/229":
            return {"number": 229, "state": "open", "body": body}
        if api_path == f"pulls/{current['number']}":
            return current
        if historical is not None and api_path == f"pulls/{historical['number']}":
            return historical
        if api_path.startswith("pulls?") and "state=closed" in api_path:
            return [] if historical is None else [{"number": historical["number"]}]
        if api_path.startswith("pulls?") and "state=open" in api_path:
            return opens
        if api_path.startswith(f"pulls/{current['number']}/files?"):
            return files
        if historical is not None and api_path == f"compare/{MERGE}...{default_revision}":
            return {
                "status": "ahead" if historical_is_ancestor else "diverged",
                "behind_by": 0 if historical_is_ancestor else 1,
            }
        if api_path == f"compare/{default_revision}...{current['head']['sha']}":
            return {
                "status": "ahead" if default_is_ancestor else "diverged",
                "behind_by": 0 if default_is_ancestor else 2,
            }
        branch = current["head"]["ref"]
        if api_path == f"git/ref/heads/{branch}":
            if branch_ref_sha is None and allow_not_found:
                return None
            return {"object": {"sha": branch_ref_sha}}
        raise AssertionError(f"unexpected GitHub path: {api_path}")

    return fake


def _source(action: str = "implement-change") -> WorkerRequest:
    return WorkerRequest(229, "executor", action)


def _qualify(monkeypatch: pytest.MonkeyPatch, fake: Callable[..., object | None]):
    monkeypatch.setattr(carrier, "_github_json", fake)
    return carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token="token",
        source=_source(),
        change=CHANGE,
        pr_number=236,
        current_revision=MAIN,
    )


def test_initial_carrier_remains_strict_and_qualified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial = _continuation_pr(branch=f"agent/{CHANGE}")
    fake = _fake_github(
        current_pr=initial,
        historical_pr=None,
        open_prs=[initial],
        pr_files=[{"filename": f"openspec/changes/{CHANGE}/proposal.md"}],
    )
    decision = _qualify(monkeypatch, fake)
    assert decision.disposition == "QUALIFIED"
    assert decision.branch == f"agent/{CHANGE}"
    assert decision.historical_pr_number is None


def test_code_only_continuation_is_qualified_from_historical_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(monkeypatch, _fake_github())
    assert decision.disposition == "QUALIFIED"
    assert decision.pr_number == 236
    assert decision.branch == f"agent/{CHANGE}-continuation-232"
    assert decision.historical_pr_number == 232


def test_diverged_continuation_is_recognized_only_for_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(monkeypatch, _fake_github(default_is_ancestor=False))
    assert decision.disposition == "RECONCILIATION_REQUIRED"
    assert decision.recognized
    assert not decision.qualified


@pytest.mark.parametrize(
    "branch",
    [
        f"agent/{CHANGE}-continuation-999",
        f"agent/{CHANGE}-continuation-232-copy",
        "agent/arbitrary",
    ],
)
def test_arbitrary_or_wrong_continuation_branch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    branch: str,
) -> None:
    current = _continuation_pr(branch=branch)
    decision = _qualify(
        monkeypatch,
        _fake_github(current_pr=current, open_prs=[current]),
    )
    assert decision.disposition == "INDETERMINATE"


def test_missing_historical_carrier_rejects_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(monkeypatch, _fake_github(historical_pr=None))
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "initial-carrier-branch-is-not-canonical"


def test_nonancestor_historical_merge_rejects_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(historical_is_ancestor=False),
    )
    assert decision.disposition == "INDETERMINATE"


def test_multiple_claimed_continuation_carriers_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _continuation_pr()
    competitor = _continuation_pr(
        number=237,
        branch=f"agent/{CHANGE}-continuation-233",
        head_sha="5" * 40,
    )
    decision = _qualify(
        monkeypatch,
        _fake_github(current_pr=current, open_prs=[current, competitor]),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-competing-open-carrier"


def test_pr_ref_head_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(branch_ref_sha="6" * 40),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-pr-ref-head-mismatch"


def test_competing_active_change_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(
            pr_files=[
                {"filename": "src/investment_strategy/example.py"},
                {"filename": "openspec/changes/other-change/tasks.md"},
            ]
        ),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-competing-active-change"


def test_stale_default_revision_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(default_revision="7" * 40),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-default-revision-stale"


def test_wrong_issue_link_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _continuation_pr(issue_number=230)
    decision = _qualify(
        monkeypatch,
        _fake_github(current_pr=current, open_prs=[current]),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-pr-identity-incoherent"


def test_competing_change_in_issue_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(issue_body="Change: another-change\n"),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-issue-change-incoherent"


def test_historical_carrier_is_recognized_from_current_default_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical = _historical_pr()
    monkeypatch.setattr(
        carrier,
        "_github_json",
        _fake_github(
            current_pr=historical,
            historical_pr=historical,
            open_prs=[],
            branch_ref_sha=HISTORICAL_HEAD,
        ),
    )
    decision = carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token="token",
        source=_source(),
        change=CHANGE,
        pr_number=232,
        current_revision=MAIN,
    )
    assert decision.disposition == "HISTORICAL_MERGED"
    assert decision.historical_pr_number == 232
