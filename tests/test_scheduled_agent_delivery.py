"""Delivery regressions through production acquisition and carrier entry points."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import cast

import pytest

import investment_strategy.native_closing_merge_application as native
import investment_strategy.scheduled_agent_application_carrier as carrier
import investment_strategy.scheduled_agent_application_materialization as materialization
import investment_strategy.scheduled_agent_effects as effects
import investment_strategy.scheduled_agent_merge_acceptance as acceptance
import investment_strategy.scheduled_agent_runtime as runtime
import investment_strategy.scheduled_agent_validation_resource as resources
from investment_strategy.native_closing_preflight import MergeStrategy
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.workflow_dispatch import classify_dispatch
from tests.test_scheduled_agent_application_carrier import (
    CHANGE,
    CONTINUATION_MERGE,
    HEAD,
    MAIN,
    REPOSITORY,
    TEST_VALUE,
    _continuation_pr,
    _fake_github,
)


def _raw_history() -> list[dict[str, object]]:
    return cast(
        list[dict[str, object]],
        json.loads((Path(__file__).parent / "fixtures/issue229-comments.json").read_text()),
    )


def test_complete_real_timeline_reconstructs_same_action_blocked_result() -> None:
    from investment_strategy.scheduled_agent_formal_qualification import (
        build_qualification_input,
        qualify_current_formal_consequence,
    )

    timeline = json.loads((Path(__file__).parent / "fixtures/issue229-timeline.json").read_text())
    decision = qualify_current_formal_consequence(
        build_qualification_input(
            issue_number=229,
            change=CHANGE,
            state="open",
            current_routing=("executor", "merge-implementation-pr"),
            comments=_raw_history(),
            current_revision="4422c8b8661cdc8af3ce699d4dbffdd61b86d7b4",
            lifecycle_events=timeline,
        )
    )
    assert decision.qualified, decision


def _review_snapshot(
    monkeypatch: pytest.MonkeyPatch, full_history: bool, corruption: str | None = None
) -> acceptance.MergeAcceptanceSnapshot:
    comments = _raw_history()
    exact = next(item for item in comments if item["id"] == 5667862037)
    if not full_history:
        comments = [exact]
    if corruption is not None and corruption != "incomplete-page":
        forged = dict(exact)
        body = str(forged["body"])
        changes = {
            "wrong-issue": ("Workflow: #229", "Workflow: #999"),
            "wrong-change": (f"Change: {CHANGE}", "Change: other"),
            "missing-binding": ("Application-Correlation:", "Unbound-Correlation:"),
            "wrong-marker": ("REVIEW_RESULT", "ACTION_RESULT"),
            "wrong-role": ("Role: reviewer", "Role: executor"),
            "duplicate-action": (
                "Action: review-implementation",
                "Action: review-implementation\nAction: review-archive",
            ),
        }
        if corruption in changes:
            body = body.replace(*changes[corruption])
        elif corruption == "findings":
            body = body.replace("Result: PASS", "Result: FINDINGS").replace(":pass:", ":findings:")
            body = body.replace("Executor / merge-implementation-pr", "Executor / implement-change")
        elif corruption == "connector":
            forged["performed_via_github_app"] = {"slug": "chatgpt-codex-connector"}
        elif corruption == "human":
            forged["performed_via_github_app"] = None
            forged["user"] = {"login": "royhsu-work"}
            body = "Please correct the implementation before merging."
        forged.update(
            id=9999999999,
            body=body,
            created_at="2026-09-15T23:00:00Z",
            updated_at="2026-09-15T23:00:00Z",
        )
        comments.append(forged)
    # Exercise page exhaustion, including a second page, without replacing acquisition.
    comments = [
        {"id": 100 + i, "body": "observation", "created_at": "2026-01-01T00:00:00Z"}
        for i in range(100)
    ] + comments
    head = "2ea915da35926bbcc155ebca30ae1305d7a2bc5a"
    main = "4422c8b8661cdc8af3ce699d4dbffdd61b86d7b4"
    pr = {
        "number": 236,
        "state": "open",
        "title": "Continuation",
        "body": "Refs #229",
        "head": {"sha": head},
        "commits": 1,
    }
    reads: list[str] = []

    def read(_repository: str, _token: str, path: str = "") -> object:
        reads.append(path)
        if path == "":
            return {
                "allow_merge_commit": True,
                "merge_commit_title": "PR_TITLE",
                "merge_commit_message": "PR_BODY",
            }
        if path == "pulls/236":
            return pr
        if path == "issues/229":
            return {"number": 229, "body": f"Change: {CHANGE}"}
        if path.startswith("issues/229/comments?"):
            page = int(path.rsplit("page=", 1)[1])
            if corruption == "incomplete-page" and page == 2:
                raise RuntimeError("page unavailable")
            return comments[(page - 1) * 100 : page * 100]
        if path.startswith("pulls/236/commits?"):
            return [{"commit": {"message": "Implement approved continuation"}}]
        if path.startswith(f"commits/{head}/check-runs?"):
            return {
                "total_count": 1,
                "check_runs": [{"status": "completed", "conclusion": "success"}],
            }
        raise AssertionError(path)

    monkeypatch.setattr(acceptance, "_github_json", read)
    monkeypatch.setattr(native, "_github_json", read)
    snapshot = acceptance.acquire_merge_acceptance_snapshot(
        repository=REPOSITORY,
        token=TEST_VALUE,
        issue_number=229,
        pr_number=236,
        expected_head_sha=head,
        merge_strategy=MergeStrategy.MERGE,
        required_review_action="review-implementation",
        current_revision=main,
    )
    assert any(path.endswith("page=2") for path in reads)
    return snapshot


@pytest.mark.parametrize("full_history", [False, True])
def test_merge_acquisition_accepts_bound_review_with_irrelevant_history(
    monkeypatch: pytest.MonkeyPatch, full_history: bool
) -> None:
    snapshot = _review_snapshot(monkeypatch, full_history)
    assert acceptance.merge_acceptance_allows(snapshot), snapshot


@pytest.mark.parametrize(
    "corruption",
    [
        "wrong-issue",
        "wrong-change",
        "missing-binding",
        "wrong-marker",
        "wrong-role",
        "duplicate-action",
        "findings",
        "connector",
        "human",
        "incomplete-page",
    ],
)
def test_merge_acquisition_rejects_applicable_adverse_evidence(
    monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    snapshot = _review_snapshot(monkeypatch, True, corruption)
    assert not acceptance.merge_acceptance_allows(snapshot), snapshot


def test_historical_source_enters_read_only_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pr = _continuation_pr()
    pr.update(
        state="closed",
        merged=True,
        merged_at="2026-09-13T00:00:00Z",
        merge_commit_sha=CONTINUATION_MERGE,
    )
    upstream = _fake_github(current_pr=pr, open_prs=[], branch_ref_sha=None)

    def read(repository: str, token: str, path: str, **kwargs: object) -> object:
        value = upstream(repository, token, path, **kwargs)
        if path == "issues/229":
            return {
                **cast(dict[str, object], value),
                "labels": [{"name": "action:merge-implementation-pr"}],
                "created_at": "2026-09-08T18:15:57Z",
                "closed_at": None,
            }
        return value

    monkeypatch.setattr(effects, "_github_json", read)
    adapter = effects.GitHubEffectAdapter(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=WorkerRequest(229, "executor", "merge-implementation-pr"),
        authorized_change=CHANGE,
        current_revision=MAIN,
    )
    observed = adapter._source_pull_request(236, require_open=False)
    assert observed is not None
    assert cast(dict[str, object], observed["head"])["sha"] == HEAD
    assert adapter._source_pull_request(236, require_open=True) is None


def test_old_review_cannot_replace_historical_head_current_default_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pr = _continuation_pr()
    pr.update(
        state="closed",
        merged=True,
        merged_at="2026-09-13T00:00:00Z",
        merge_commit_sha=CONTINUATION_MERGE,
    )

    def read(_repository: str, _token: str, path: str) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path == "git/ref/heads/main":
            return {"object": {"sha": MAIN}}
        if path.startswith("compare/"):
            return {"status": "ahead", "behind_by": 0}
        if path.startswith("commits/"):
            return {"parents": [{"sha": "a" * 40}]}
        raise AssertionError(path)

    monkeypatch.setattr(acceptance, "_github_json", read)
    assert not acceptance._historical_merged_carrier_allowed(
        pr,
        repository=REPOSITORY,
        token=TEST_VALUE,
        expected_head_sha=HEAD,
        current_revision=MAIN,
        expected_branch=f"agent/{CHANGE}-continuation-232",
        reviewer_pass_default_branch_revision="a" * 40,
    )


def test_completed_historical_checkpoint_is_read_only_for_rereview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pr = _continuation_pr()
    pr.update(
        state="closed",
        merged=True,
        merged_at="2026-09-13T00:00:00Z",
        merge_commit_sha=CONTINUATION_MERGE,
    )
    upstream = _fake_github(current_pr=pr, open_prs=[], branch_ref_sha=None)
    blob = "f" * 40
    content = "## Slice 2\n- [x] 2.1 Verified implementation\n"

    def read(repository: str, token: str, path: str, **kwargs: object) -> object:
        assert kwargs.get("method", "GET") == "GET", "historical checkpoint must not write"
        if path.startswith("contents/") or path.startswith("git/blobs/"):
            return {
                "sha": blob,
                "encoding": "base64",
                "content": base64.b64encode(content.encode()).decode(),
            }
        return upstream(repository, token, path, **kwargs)

    for module in (carrier, materialization, resources):
        monkeypatch.setattr(module, "_github_json", read)
    source = WorkerRequest(229, "executor", "implement-change")
    payload = {
        "operation": "application-materialize",
        "issue_number": 229,
        "expected_change": CHANGE,
        "change": CHANGE,
        "pr_number": 236,
        "branch": f"agent/{CHANGE}-continuation-232",
        "base_sha": HEAD,
        "message": "Observe completed implementation for current-default review",
        "files": [
            {"path": f"openspec/changes/{CHANGE}/tasks.md", "blob_sha": blob, "expected_sha": blob}
        ],
    }
    request = materialization.parse_materialization_payload(payload, source)
    target = materialization._materialize_implementation_target(
        request,
        source,
        repository=REPOSITORY,
        token=TEST_VALUE,
        default_branch="main",
        current_revision=MAIN,
    )
    assert target.revision == HEAD and target.pr_number == 236
    assert (
        materialization._observe_implementation_target(
            request,
            source,
            repository=REPOSITORY,
            token=TEST_VALUE,
            current_revision=MAIN,
        )
        == target
    )


def test_fresh_dispatch_survives_default_advance_with_bound_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.test_scheduled_agent_formal_qualification import _comment, _lifecycle_events

    old, new = "a" * 40, "b" * 40
    comment = _comment(
        1,
        action="review-implementation",
        role="reviewer",
        result="pass",
        successor="Executor / merge-implementation-pr",
        request_id=10,
        default_revision=old,
    )
    timeline = _lifecycle_events([comment])
    issue = {
        "number": 229,
        "state": "open",
        "body": f"Change: {CHANGE}",
        "labels": [{"name": "action:merge-implementation-pr"}],
        "created_at": "2026-09-08T18:15:57Z",
        "closed_at": None,
    }

    def read_list(url: str, _token: str) -> tuple[dict[str, object], ...]:
        if "/comments?" in url:
            return (comment,)
        if "/timeline?" in url:
            return tuple(timeline)
        if "/issues?" in url:
            return (issue,)
        raise AssertionError(url)

    def read_object(url: str, _token: str) -> dict[str, object]:
        if "/git/ref/heads/main" in url:
            return {"object": {"sha": new}}
        if "/compare/" in url:
            return {"status": "ahead", "behind_by": 0}
        return {"default_branch": "main"}

    monkeypatch.setattr(runtime, "_github_get_list_page", read_list)
    monkeypatch.setattr(runtime, "_github_get_object", read_object)
    decision = classify_dispatch(runtime.acquire_current_github_preflight(REPOSITORY, TEST_VALUE))
    assert decision.disposition == "AUTHORIZE", decision
    assert decision.selected_issue_id == 229
