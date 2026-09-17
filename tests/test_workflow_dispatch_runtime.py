"""Regression coverage for the executable Action dispatch boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_runtime as runtime
from investment_strategy.scheduled_agent_action_model import Action
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    acquire_dispatch_preflight,
)
from investment_strategy.workflow_dispatch import (
    Action as WorkflowAction,
)
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    Role,
    action_entry_authorized,
    action_model_shadow,
    activation_postwrite_accepted,
    classify_dispatch,
)


def _preflight(
    observations: tuple[GitHubIssueObservation, ...],
    *,
    source_total_count: int | None = None,
    incomplete_results: bool = False,
    exhausted: bool = True,
    human_authorized: bool = True,
) -> DispatchPreflight:
    return acquire_dispatch_preflight(
        observations=observations,
        source_total_count=(
            len(observations) if source_total_count is None else source_total_count
        ),
        incomplete_results=incomplete_results,
        exhausted=exhausted,
        human_authorized=human_authorized,
    )


def _issue(
    number: int,
    action: WorkflowAction | None,
    *,
    change: str = "simplify-scheduled-agent-control-plane",
    order: int = 1,
    state: str = "open",
    routing_debt: bool = False,
) -> GitHubIssueObservation:
    routing: tuple[Role, WorkflowAction] | None
    if action is None:
        routing = None
    else:
        role: Role = (
            "reviewer"
            if action.startswith("review-")
            else ("executor" if action.startswith(("implement", "merge")) else "lead")
        )
        routing = (role, action)
    return GitHubIssueObservation(
        issue_number=number,
        change=change,
        routing=routing,
        state=state,
        created_order=order,
        authoritative=True,
        routing_debt=routing_debt,
    )


def test_action_only_dispatch_selects_exactly_one_formal_work_item() -> None:
    preflight = _preflight((_issue(138, "implement-change"),))
    decision = classify_dispatch(preflight)
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 138
    assert decision.selected_routing == ("executor", "implement-change")
    assert decision.formal_issue_ids == (138,)
    assert action_entry_authorized(preflight, 138, ("executor", "implement-change"))


def test_wip_and_incomplete_observations_fail_closed() -> None:
    two = _preflight((_issue(138, "implement-change"), _issue(139, "review-implementation")))
    assert classify_dispatch(two).reason == "wip-more-than-one"

    incomplete = _preflight(
        (_issue(138, "implement-change"),),
        source_total_count=None,
        incomplete_results=True,
        exhausted=False,
    )
    assert classify_dispatch(incomplete).disposition == "FAIL_CLOSED"
    assert classify_dispatch(incomplete).completeness == "INDETERMINATE"


def test_closed_routing_debt_fails_closed_before_selection() -> None:
    preflight = _preflight((_issue(138, "implement-change", state="closed", routing_debt=True),))

    decision = classify_dispatch(preflight)

    assert decision.disposition == "FAIL_CLOSED"
    assert decision.reason == "closed-routing-debt"


def test_production_preflight_enumerates_closed_routing_debt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_urls: list[str] = []

    def fake_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        requested_urls.append(url)
        if "/comments?" in url or "/timeline?" in url:
            return ()
        return (
            {
                "number": 138,
                "state": "closed",
                "body": "Change: simplify-scheduled-agent-control-plane\n",
                "created_at": "2026-09-03T00:00:00Z",
                "closed_at": "2026-09-03T01:00:00Z",
                "labels": [{"name": "action:implement-change"}],
            },
        )

    monkeypatch.setattr(runtime, "_github_get_list_page", fake_page)

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"default_branch":"main"}'

    def fake_urlopen(_request: object, timeout: int) -> FakeResponse:
        assert timeout == 30
        return FakeResponse()

    monkeypatch.setattr(runtime, "urlopen", fake_urlopen)
    preflight = runtime.acquire_current_github_preflight("owner/repo", "token")

    assert requested_urls == [
        "https://api.github.com/repos/owner/repo/issues?state=all&per_page=100&page=1",
        (
            "https://api.github.com/repos/owner/repo/issues/138/comments?per_page=100"
            "&sort=created&direction=desc"
        ),
        ("https://api.github.com/repos/owner/repo/issues/138/timeline?per_page=100&page=1"),
    ]
    assert classify_dispatch(preflight).reason == "closed-routing-debt"


def test_production_preflight_qualifies_from_issue_timeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = "a" * 40
    requested_urls: list[str] = []
    comment_body = "\n".join(
        (
            "ACTION_RESULT",
            "Workflow: #229",
            "Change: qualify-active-formal-consequences",
            "Action: finalize-change",
            "Role: lead",
            "Result: MORE_IMPLEMENTATION_REQUIRED",
            "Revision: " + "b" * 40,
            "Default-Branch-Revision: " + revision,
            (
                "Application-Correlation: "
                "application:10:229:qualify-active-formal-consequences:lead:"
                "finalize-change:more-implementation-required:" + revision
            ),
            "Repository-derived successor: Executor / implement-change",
        )
    )
    issue = {
        "number": 229,
        "state": "open",
        "body": "Change: qualify-active-formal-consequences\n",
        "created_at": "2026-09-12T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "action:implement-change"}],
    }
    comment = {
        "id": 10,
        "body": comment_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    timeline = (
        {
            "id": 10,
            "event": "commented",
            "created_at": "2026-09-12T00:00:01Z",
        },
        {
            "id": 11,
            "event": "labeled",
            "created_at": "2026-09-12T00:00:02Z",
            "label": {"name": "action:implement-change"},
        },
    )

    def fake_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        requested_urls.append(url)
        if "/issues?" in url:
            return (issue,)
        if "/comments?" in url:
            return (comment,)
        if "/timeline?" in url:
            return timeline
        raise AssertionError(url)

    monkeypatch.setattr(runtime, "_github_get_list_page", fake_page)
    monkeypatch.setattr(runtime, "_current_default_branch_revision", lambda *_args: revision)

    preflight = runtime.acquire_current_github_preflight("owner/repo", "token")

    assert requested_urls == [
        "https://api.github.com/repos/owner/repo/issues?state=all&per_page=100&page=1",
        (
            "https://api.github.com/repos/owner/repo/issues/229/comments?per_page=100"
            "&sort=created&direction=desc"
        ),
        ("https://api.github.com/repos/owner/repo/issues/229/timeline?per_page=100&page=1"),
    ]
    assert classify_dispatch(preflight).disposition == "AUTHORIZE"
    assert classify_dispatch(preflight).selected_issue_id == 229
    assert classify_dispatch(preflight).selected_routing == ("executor", "implement-change")



def test_production_preflight_qualifies_recovery_after_default_branch_advances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A durable recovery remains qualified on a descendant main revision."""
    previous_revision = "b" * 40
    current_revision = "a" * 40
    requested_urls: list[str] = []
    recovery_body = "\n".join(
        (
            "APPLICATION_RECOVERY",
            "Workflow: #233",
            "Change: operationalize-review-openspec-semantic-proof",
            "Source: Lead / propose-change",
            "Target: Lead / resolve-question",
            "Default-Branch-Revision: " + previous_revision,
            "Failed-Authorization-Revision: " + ("c" * 40),
            "Request-Comment-ID: 901",
            "Reason: partial-first-activation",
        )
    )
    issue = {
        "number": 233,
        "state": "open",
        "body": "Change: operationalize-review-openspec-semantic-proof\n",
        "created_at": "2026-09-09T07:28:08Z",
        "closed_at": None,
        "labels": [{"name": "action:resolve-question"}],
    }
    recovery = {
        "id": 50,
        "body": recovery_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    lifecycle = (
        {"id": 50, "event": "commented", "created_at": "2026-09-17T01:52:20Z"},
        {
            "id": 51,
            "event": "unlabeled",
            "created_at": "2026-09-17T01:52:22Z",
            "label": {"name": "action:propose-change"},
        },
        {
            "id": 52,
            "event": "labeled",
            "created_at": "2026-09-17T01:52:22Z",
            "label": {"name": "action:resolve-question"},
        },
    )

    def fake_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        requested_urls.append(url)
        if "/issues?" in url:
            return (issue,)
        if "/comments?" in url:
            return (recovery,)
        if "/timeline?" in url:
            return lifecycle
        raise AssertionError(url)

    def fake_object(url: str, token: str) -> dict[str, object]:
        del token
        expected = (
            "https://api.github.com/repos/owner/repo/compare/"
            + previous_revision
            + "..."
            + current_revision
        )
        assert url == expected
        return {"status": "ahead", "behind_by": 0}

    monkeypatch.setattr(runtime, "_github_get_list_page", fake_page)
    monkeypatch.setattr(runtime, "_github_get_object", fake_object)
    monkeypatch.setattr(
        runtime, "_current_default_branch_revision", lambda *_args: current_revision
    )

    preflight = runtime.acquire_current_github_preflight("owner/repo", "token")
    decision = classify_dispatch(preflight)

    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 233
    assert decision.selected_routing == ("lead", "resolve-question")
    assert any("compare/" in url for url in requested_urls) is False


def test_production_preflight_ignores_closed_inert_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = "a" * 40
    requested_urls: list[str] = []
    active_comment_body = "\n".join(
        (
            "ACTION_RESULT",
            "Workflow: #229",
            "Change: qualify-active-formal-consequences",
            "Action: finalize-change",
            "Role: lead",
            "Result: MORE_IMPLEMENTATION_REQUIRED",
            "Revision: " + "b" * 40,
            "Default-Branch-Revision: " + revision,
            (
                "Application-Correlation: "
                "application:10:229:qualify-active-formal-consequences:lead:"
                "finalize-change:more-implementation-required:" + revision
            ),
            "Repository-derived successor: Executor / implement-change",
        )
    )
    historical = {
        "number": 227,
        "state": "closed",
        "body": "Change: historical-change\n",
        "created_at": "2026-09-03T00:00:00Z",
        "closed_at": "2026-09-03T01:00:00Z",
        "labels": [],
    }
    active = {
        "number": 229,
        "state": "open",
        "body": "Change: qualify-active-formal-consequences\n",
        "created_at": "2026-09-12T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "action:implement-change"}],
    }
    active_comment = {
        "id": 10,
        "body": active_comment_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    active_timeline = (
        {
            "id": 10,
            "event": "commented",
            "created_at": "2026-09-12T00:00:01Z",
        },
        {
            "id": 11,
            "event": "labeled",
            "created_at": "2026-09-12T00:00:02Z",
            "label": {"name": "action:implement-change"},
        },
    )

    def fake_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        requested_urls.append(url)
        if "/issues?" in url:
            return (historical, active)
        if "/issues/229/comments?" in url:
            return (active_comment,)
        if "/issues/229/timeline?" in url:
            return active_timeline
        if "/issues/227/" in url:
            raise AssertionError("inert closed history should not be qualified")
        raise AssertionError(url)

    monkeypatch.setattr(runtime, "_github_get_list_page", fake_page)
    monkeypatch.setattr(runtime, "_current_default_branch_revision", lambda *_args: revision)

    preflight = runtime.acquire_current_github_preflight("owner/repo", "token")

    assert classify_dispatch(preflight).disposition == "AUTHORIZE"
    assert classify_dispatch(preflight).selected_issue_id == 229
    assert classify_dispatch(preflight).selected_routing == ("executor", "implement-change")
    assert all("/issues/227/" not in url for url in requested_urls)


def test_production_preflight_ignores_closed_inert_history_with_null_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub's null body on inert history cannot poison a live formal route."""

    revision = "a" * 40
    requested_urls: list[str] = []
    active_comment_body = "\n".join(
        (
            "ACTION_RESULT",
            "Workflow: #229",
            "Change: qualify-active-formal-consequences",
            "Action: finalize-change",
            "Role: lead",
            "Result: MORE_IMPLEMENTATION_REQUIRED",
            "Revision: " + "b" * 40,
            "Default-Branch-Revision: " + revision,
            (
                "Application-Correlation: "
                "application:10:229:qualify-active-formal-consequences:lead:"
                "finalize-change:more-implementation-required:" + revision
            ),
            "Repository-derived successor: Executor / implement-change",
        )
    )
    historical = {
        "number": 248,
        "state": "closed",
        "body": None,
        "created_at": None,
        "closed_at": None,
        "labels": [],
    }
    active = {
        "number": 229,
        "state": "open",
        "body": "Change: qualify-active-formal-consequences\n",
        "created_at": "2026-09-12T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "action:implement-change"}],
    }
    active_comment = {
        "id": 10,
        "body": active_comment_body,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
    }
    active_timeline = (
        {
            "id": 10,
            "event": "commented",
            "created_at": "2026-09-12T00:00:01Z",
        },
        {
            "id": 11,
            "event": "labeled",
            "created_at": "2026-09-12T00:00:02Z",
            "label": {"name": "action:implement-change"},
        },
    )

    def fake_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        requested_urls.append(url)
        if "/issues?" in url:
            return (historical, active)
        if "/issues/229/comments?" in url:
            return (active_comment,)
        if "/issues/229/timeline?" in url:
            return active_timeline
        if "/issues/248/" in url:
            raise AssertionError("inert null-body history should not be qualified")
        raise AssertionError(url)

    monkeypatch.setattr(runtime, "_github_get_list_page", fake_page)
    monkeypatch.setattr(runtime, "_current_default_branch_revision", lambda *_args: revision)

    preflight = runtime.acquire_current_github_preflight("owner/repo", "token")
    decision = classify_dispatch(preflight)

    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 229
    assert decision.selected_routing == ("executor", "implement-change")
    assert all("/issues/248/" not in url for url in requested_urls)


@pytest.mark.parametrize(
    ("state", "body", "labels"),
    (
        ("open", None, [{"name": "action:explore-change"}]),
        ("closed", None, [{"name": "action:implement-change"}]),
        ("closed", None, [{"name": "action:not-a-real-action"}]),
        ("closed", None, None),
    ),
)
def test_missing_body_stays_fail_closed_for_non_inert_observations(
    state: str,
    body: object,
    labels: object,
) -> None:
    payload = {
        "number": 248,
        "state": state,
        "body": body,
        "created_at": "2026-09-16T10:40:51Z",
        "closed_at": None if state == "open" else "2026-09-16T10:41:07Z",
        "labels": labels,
    }

    preflight = runtime.acquire_from_issue_pages(((payload,),), exhausted=True)
    decision = classify_dispatch(preflight)

    assert decision.disposition == "FAIL_CLOSED"
    assert decision.reason == "observations-unqualified"


def test_shadow_is_a_pure_comparison_of_the_same_executable_model() -> None:
    preflight = _preflight((_issue(138, "review-openspec"),))
    comparison = action_model_shadow(preflight)
    assert comparison.matches
    assert comparison.expected.action is Action.REVIEW_OPENSPEC


def test_activation_postcondition_requires_exact_change_and_action() -> None:
    preflight = _preflight(
        (
            _issue(
                138,
                "propose-change",
                change="simplify-scheduled-agent-control-plane",
            ),
        )
    )
    assert activation_postwrite_accepted(
        preflight,
        issue_number=138,
        expected_change="simplify-scheduled-agent-control-plane",
    )
    assert not activation_postwrite_accepted(
        preflight,
        issue_number=138,
        expected_change="other-change",
    )


def test_generated_governance_projection_has_no_second_runtime_dag() -> None:
    workflow = Path("agents/workflow.md").read_text(encoding="utf-8")
    assert "Scheduled-Dispatch-Mode: workflow-dynamic" in workflow
    start_marker = "<!-- BEGIN GENERATED ACTION MODEL -->"
    end_marker = "<!-- END GENERATED ACTION MODEL -->"
    start = workflow.index(start_marker)
    end = workflow.index(end_marker, start) + len(end_marker)
    assert workflow[start : end + 1].endswith("\n")
    assert (
        "parse"
        not in Path("src/investment_strategy/workflow_dispatch.py")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "HANDOFF" not in workflow


def test_preflight_excludes_daily_shards_and_unrouted_prose() -> None:
    """Only current routed workflow Issues can make Change prose authoritative."""

    checkin = {
        "number": 142,
        "title": "[Agent Runtime] 2026-08-24",
        "state": "open",
        "body": None,
        "labels": [],
        "created_at": "2026-08-24T04:51:39Z",
        "closed_at": None,
    }
    historical_unrouted = {
        "number": 93,
        "title": "Historical Issue",
        "state": "closed",
        "body": (
            "Change: historical-change\n\nExamples:\nChange: unset\nChange: another-prose-example\n"
        ),
        "labels": [{"name": "human:approved"}],
        "created_at": "2026-08-18T17:28:23Z",
        "closed_at": "2026-08-19T12:51:55Z",
    }
    active = {
        "number": 138,
        "title": "Active Change",
        "state": "open",
        "body": "Change: simplify-scheduled-agent-control-plane\n",
        "labels": [{"name": "action:finalize-change"}],
        "created_at": "2026-08-30T18:16:07Z",
        "closed_at": None,
    }

    preflight = runtime.acquire_from_issue_pages(
        ((checkin, historical_unrouted, active),),
        exhausted=True,
    )

    assert len(preflight.issues) == 2
    assert all(issue.issue_number != 142 for issue in preflight.issues)
    assert classify_dispatch(preflight).selected_issue_id == 138
    assert classify_dispatch(preflight).selected_routing == ("lead", "finalize-change")


def test_canonical_change_ignores_markdown_prose_examples() -> None:
    payload = {
        "number": 138,
        "title": "Active Change",
        "state": "open",
        "body": (
            "Change: simplify-scheduled-agent-control-plane\n\n"
            "Example:\n"
            "Change: another-prose-example\n"
        ),
        "labels": [{"name": "action:finalize-change"}],
        "created_at": "2026-08-30T18:16:07Z",
        "closed_at": None,
    }

    observation = runtime.normalize_github_issue(payload)

    assert observation is not None
    assert observation.authoritative is True
    assert observation.change == "simplify-scheduled-agent-control-plane"
