"""Regression coverage for the executable Action dispatch boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_runtime as runtime
from investment_strategy.scheduled_agent_action_model import Action, WorkflowDependencies
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
    dependencies: WorkflowDependencies | None = (),
) -> DispatchPreflight:
    return acquire_dispatch_preflight(
        observations=observations,
        source_total_count=(
            len(observations) if source_total_count is None else source_total_count
        ),
        incomplete_results=incomplete_results,
        exhausted=exhausted,
        human_authorized=human_authorized,
        dependencies=dependencies,
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


def test_multiple_formal_workflows_and_incomplete_observations() -> None:
    two = _preflight((_issue(138, "implement-change"), _issue(139, "review-implementation")))
    assert classify_dispatch(two).selected_issue_id == 138

    incomplete = _preflight(
        (_issue(138, "implement-change"),),
        source_total_count=None,
        incomplete_results=True,
        exhausted=False,
    )
    assert classify_dispatch(incomplete).disposition == "FAIL_CLOSED"
    assert classify_dispatch(incomplete).completeness == "INDETERMINATE"


@pytest.mark.parametrize("pair", [(435, 468), (900, 850)])
def test_dependency_selection_preserves_activation_proof(pair: tuple[int, int]) -> None:
    blocked, repair = pair
    before = _preflight(
        (
            _issue(blocked, "implement-change", change="restore-t1", order=1),
            _issue(repair, "propose-change", change="unset", order=2),
        ),
        dependencies=((blocked, (repair,)),),
    )
    assert classify_dispatch(before).selected_issue_id == repair
    assert action_entry_authorized(before, repair, ("lead", "propose-change"))

    issues = (
        _issue(blocked, "implement-change", change="restore-t1", order=1),
        _issue(repair, "propose-change", change="repair-scope", order=2),
    )
    after = _preflight(issues, dependencies=((blocked, (repair,)),))
    assert classify_dispatch(after).formal_issue_ids == tuple(sorted(pair))
    assert activation_postwrite_accepted(after, issue_number=repair, expected_change="repair-scope")
    assert not activation_postwrite_accepted(
        after, issue_number=blocked, expected_change="restore-t1"
    )
    assert not activation_postwrite_accepted(
        _preflight(issues), issue_number=repair, expected_change="repair-scope"
    )


def test_dependency_selection_does_not_bypass_closed_debt() -> None:
    before = _preflight(
        (
            _issue(435, "implement-change", change="restore-t1"),
            _issue(468, "explore-change", change="unset"),
            _issue(411, "resolve-question", state="closed", routing_debt=True),
        ),
        dependencies=((435, (468,)),),
    )
    assert classify_dispatch(before).disposition == "FAIL_CLOSED"


def _dependency_fixture(
    monkeypatch: pytest.MonkeyPatch,
    pair: tuple[int, int],
    *,
    phase: str = "explore",
    fault: str = "",
) -> list[str]:
    """Actual acquisition/qualification, with only GitHub GETs substituted."""
    blocked, repair = pair
    revision = "a" * 40
    repo_url = "https://api.github.com/repos/owner/repo"
    state = "closed" if phase in {"completed", "no-go", "bare-close"} else "open"
    repair_change = "unset" if phase == "explore" else "repair-scope"
    repair_labels = (
        []
        if state == "closed"
        else [
            {"name": "action:explore-change" if phase == "explore" else "action:implement-change"}
        ]
    )
    blocked_issue = {
        "number": blocked,
        "id": blocked + 10000,
        "repository_url": repo_url,
        "state": "open",
        "body": "Change: restore-t1\n",
        "created_at": "2026-09-12T00:00:00Z",
        "closed_at": None,
        "labels": [{"name": "action:implement-change"}],
    }
    repair_issue = {
        "number": repair,
        "id": repair + 10000,
        "repository_url": repo_url,
        "state": state,
        "body": f"Change: {repair_change}\n",
        "created_at": "2026-09-12T00:00:00Z",
        "closed_at": "2026-09-12T00:00:10Z" if state == "closed" else None,
        "labels": repair_labels,
    }

    def formal_comment(
        number: int, change: str, action: str, role: str, result: str, successor: str
    ) -> dict[str, object]:
        marker = "REVIEW_RESULT" if action.startswith("review-") else "ACTION_RESULT"
        return {
            "id": 10 if number == blocked else 20,
            "user": {"login": "github-actions[bot]"},
            "performed_via_github_app": {"slug": "github-actions"},
            "body": "\n".join(
                (
                    marker,
                    f"Workflow: #{number}",
                    f"Change: {change}",
                    f"Action: {action}",
                    f"Role: {role}",
                    f"Result: {result.upper().replace('-', '_')}",
                    "Revision: " + "b" * 40,
                    "Default-Branch-Revision: " + revision,
                    f"Application-Correlation: application:1:{number}:{change}:"
                    f"{role}:{action}:{result}:{revision}",
                    f"Repository-derived successor: {successor}",
                )
            ),
        }

    blocked_formal = formal_comment(
        blocked,
        "restore-t1",
        "finalize-change",
        "lead",
        "more-implementation-required",
        "Executor / implement-change",
    )
    declaration: dict[str, object] = {
        "id": 12,
        "body": f"Blocked by: #{repair}",
        "user": {"login": "owner"},
        "author_association": "OWNER",
        "performed_via_github_app": {"id": 1144995, "slug": "chatgpt-codex-connector"},
        "issue_url": f"{repo_url}/issues/{blocked}",
        "created_at": "2026-09-12T00:00:03Z",
        "updated_at": "2026-09-12T00:00:03Z",
    }
    if fault == "wrong-ref":
        declaration["body"] = f"Blocked by: #{repair + 1}"
    elif fault == "self":
        declaration["body"] = f"Blocked by: #{blocked}"
    elif fault == "malformed":
        declaration["body"] = f"Blocked by: #{repair},, #999"
    elif fault == "cross-issue":
        declaration["issue_url"] = f"{repo_url}/issues/{repair}"
    elif fault == "edited":
        declaration["updated_at"] = "2026-09-12T00:00:04Z"
    elif fault == "missing-provenance":
        del declaration["performed_via_github_app"]
    elif fault == "other-app":
        declaration["performed_via_github_app"] = {"slug": "other-app"}
    elif fault == "outsider":
        declaration["user"] = {"login": "outsider"}
        declaration["author_association"] = "NONE"
    elif fault == "ordinary-prose":
        declaration["body"] = f"This workflow is blocked by #{repair}"
    elif fault == "direct-owner":
        declaration["performed_via_github_app"] = None
    earlier = {
        **declaration,
        "id": 9,
        "body": f"Blocked by: #{repair + 1}",
        "created_at": "2026-09-12T00:00:00Z",
        "updated_at": "2026-09-12T00:00:00Z",
    }
    withdrawal = {
        **declaration,
        "id": 14,
        "body": "Blocked by: none",
        "created_at": "2026-09-12T00:00:04Z",
        "updated_at": "2026-09-12T00:00:04Z",
    }
    blocked_timeline = (
        {"id": 10, "event": "commented", "created_at": "2026-09-12T00:00:01Z"},
        {
            "id": 11,
            "event": "labeled",
            "created_at": "2026-09-12T00:00:02Z",
            "label": {"name": "action:implement-change"},
        },
        {"id": 12, "event": "commented", "created_at": "2026-09-12T00:00:03Z"},
    )
    if phase == "formal":
        repair_formal = formal_comment(
            repair,
            repair_change,
            "review-openspec",
            "reviewer",
            "pass",
            "Executor / implement-change",
        )
        repair_timeline = (
            {"id": 20, "event": "commented", "created_at": "2026-09-12T00:00:05Z"},
            {
                "id": 21,
                "event": "labeled",
                "created_at": "2026-09-12T00:00:06Z",
                "label": {"name": "action:implement-change"},
            },
        )
    else:
        repair_formal = formal_comment(
            repair,
            repair_change,
            "finalize-archive" if phase == "completed" else "finalize-change",
            "lead",
            "lifecycle-complete" if phase == "completed" else "no-go",
            "terminal",
        )
        repair_timeline = (
            {"id": 20, "event": "commented", "created_at": "2026-09-12T00:00:05Z"},
            {"id": 21, "event": "closed", "created_at": "2026-09-12T00:00:10Z"},
        )
    urls: list[str] = []

    def fake_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        urls.append(url)
        if "/issues?" in url:
            return (blocked_issue, repair_issue)
        if f"/issues/{blocked}/comments?" in url:
            if fault == "no-declaration":
                return (blocked_formal,)
            if fault == "corrected":
                return (earlier, blocked_formal, declaration)
            if fault == "withdrawn":
                return (declaration, withdrawal, blocked_formal)
            if fault == "duplicate":
                return (declaration, declaration, blocked_formal)
            return (declaration, blocked_formal)
        if f"/issues/{blocked}/timeline?" in url:
            return blocked_timeline
        if f"/issues/{repair}/comments?" in url:
            if fault == "cycle":
                return (
                    {
                        **declaration,
                        "id": 22,
                        "body": f"Blocked by: #{blocked}",
                        "issue_url": f"{repo_url}/issues/{repair}",
                    },
                )
            return () if phase in {"explore", "bare-close"} else (repair_formal,)
        if f"/issues/{repair}/timeline?" in url:
            return repair_timeline
        raise AssertionError(url)

    monkeypatch.setattr(runtime, "_github_get_list_page", fake_page)
    monkeypatch.setattr(runtime, "_current_default_branch_revision", lambda *_args: revision)
    return urls


@pytest.mark.parametrize("pair", [(435, 468), (900, 850)])
@pytest.mark.parametrize("phase", ["explore", "formal", "completed"])
def test_comment_dependency_drives_fresh_selection_and_completion(
    monkeypatch: pytest.MonkeyPatch, pair: tuple[int, int], phase: str
) -> None:
    blocked, repair = pair
    urls = _dependency_fixture(monkeypatch, pair, phase=phase)
    preflight = runtime.acquire_current_github_preflight("owner/repo", "token")
    decision = classify_dispatch(preflight)
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == (blocked if phase == "completed" else repair)
    assert not any("pyproject.toml" in url for url in urls)
    assert not any("/dependencies/" in url for url in urls)
    assert sum(f"/issues/{blocked}/comments?" in url for url in urls) == 1


@pytest.mark.parametrize("phase", ["no-go", "bare-close"])
def test_dependency_closure_without_delivery_cannot_resume(
    monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    _dependency_fixture(monkeypatch, (435, 468), phase=phase)
    preflight = runtime.acquire_current_github_preflight("owner/repo", "token")
    decision = classify_dispatch(preflight)
    assert decision.disposition == "NO_WORK"
    assert decision.reason == "dependencies-unsatisfied"


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-ref",
        "self",
        "malformed",
        "cross-issue",
        "edited",
        "missing-provenance",
        "duplicate",
        "cycle",
    ],
)
def test_comment_dependency_rejects_incoherent_qualified_declarations(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    _dependency_fixture(monkeypatch, (435, 468), fault=fault)
    decision = classify_dispatch(runtime.acquire_current_github_preflight("owner/repo", "token"))
    assert decision.disposition == "FAIL_CLOSED"
    assert decision.selected_issue_id is None


@pytest.mark.parametrize(
    "fault", ["other-app", "outsider", "ordinary-prose", "no-declaration", "withdrawn"]
)
def test_comment_dependency_absent_or_untrusted_keeps_ordinary_selection(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    _dependency_fixture(monkeypatch, (435, 468), fault=fault)
    decision = classify_dispatch(runtime.acquire_current_github_preflight("owner/repo", "token"))
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 435


@pytest.mark.parametrize("fault", ["direct-owner", "corrected"])
def test_comment_dependency_accepts_maintainer_correction_without_human_approval(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    _dependency_fixture(monkeypatch, (435, 468), fault=fault)
    decision = classify_dispatch(runtime.acquire_current_github_preflight("owner/repo", "token"))
    assert decision.disposition == "AUTHORIZE"
    assert decision.selected_issue_id == 468


def _graph_fixture(
    monkeypatch: pytest.MonkeyPatch,
    graph: dict[int, tuple[int | None, ...]],
    formal: set[int],
    completed: set[int],
    *,
    failed: set[int] | None = None,
    missing_formal_evidence: set[int] | None = None,
) -> list[str]:
    """Use the real paginated acquisition and formal qualifier for a whole graph."""
    revision = "a" * 40
    repo_url = "https://api.github.com/repos/owner/repo"
    failed = failed or set()
    missing_formal_evidence = missing_formal_evidence or set()
    numbers = set(graph) | {
        target for blockers in graph.values() for target in blockers if target is not None
    }
    issues: list[dict[str, object]] = []
    comments: dict[int, tuple[dict[str, object], ...]] = {}
    timelines: dict[int, tuple[dict[str, object], ...]] = {}
    urls: list[str] = []
    for number in sorted(numbers, reverse=True):
        closed = number in completed | failed
        change = f"change-{number}" if closed or number in formal else "unset"
        action = "implement-change" if number in formal else "explore-change"
        issues.append(
            {
                "number": number,
                "state": "closed" if closed else "open",
                "body": f"Change: {change}",
                "created_at": "2026-09-12T00:00:00Z",
                "closed_at": "2026-09-12T00:00:10Z" if closed else None,
                "labels": [] if closed else [{"name": f"action:{action}"}],
            }
        )
        entries: list[dict[str, object]] = []
        blockers = graph.get(number, ())
        if blockers and not closed:
            targets = ", ".join("external" if item is None else f"#{item}" for item in blockers)
            entries.append(
                {
                    "id": number * 10 + 2,
                    "body": f"Blocked by: {targets}",
                    "user": {"login": "owner"},
                    "author_association": "OWNER",
                    "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
                    "issue_url": f"{repo_url}/issues/{number}",
                    "created_at": "2026-09-12T00:00:03Z",
                    "updated_at": "2026-09-12T00:00:03Z",
                }
            )
        formal_id = number * 10
        if (closed or number in formal) and number not in missing_formal_evidence:
            result = (
                "LIFECYCLE_COMPLETE"
                if number in completed
                else "NO_GO"
                if closed
                else "MORE_IMPLEMENTATION_REQUIRED"
            )
            current_action = "finalize-archive" if number in completed else "finalize-change"
            successor = "terminal" if closed else "Executor / implement-change"
            entries.append(
                {
                    "id": formal_id,
                    "body": "\n".join(
                        (
                            "ACTION_RESULT",
                            f"Workflow: #{number}",
                            f"Change: {change}",
                            f"Action: {current_action}",
                            "Role: lead",
                            f"Result: {result}",
                            "Revision: " + "b" * 40,
                            "Default-Branch-Revision: " + revision,
                            f"Application-Correlation: application:1:{number}:{change}:"
                            f"lead:{current_action}:{result.lower().replace('_', '-')}:{revision}",
                            f"Repository-derived successor: {successor}",
                        )
                    ),
                    "user": {"login": "github-actions[bot]"},
                    "performed_via_github_app": {"slug": "github-actions"},
                }
            )
            event: dict[str, object] = {
                "id": formal_id + 1,
                "event": "closed" if closed else "labeled",
                "created_at": "2026-09-12T00:00:10Z" if closed else "2026-09-12T00:00:02Z",
            }
            if not closed:
                event["label"] = {"name": "action:implement-change"}
            timelines[number] = (
                {
                    "id": formal_id,
                    "event": "commented",
                    "created_at": "2026-09-12T00:00:01Z",
                },
                event,
            )
        comments[number] = tuple(entries)

    def read_page(url: str, token: str) -> tuple[dict[str, object], ...]:
        del token
        urls.append(url)
        if "/issues?" in url:
            return tuple(issues)
        for number in numbers:
            if f"/issues/{number}/comments?" in url:
                return comments[number]
            if f"/issues/{number}/timeline?" in url:
                return timelines.get(number, ())
        raise AssertionError(url)

    monkeypatch.setattr(runtime, "_github_get_list_page", read_page)
    monkeypatch.setattr(runtime, "_current_default_branch_revision", lambda *_args: revision)
    return urls


@pytest.mark.parametrize("offset", [0, 800])
def test_diamond_dependency_graph_advances_and_resumes_without_rewind(
    monkeypatch: pytest.MonkeyPatch, offset: int
) -> None:
    a, b, c, d = (offset + number for number in (10, 20, 30, 40))
    graph = {a: (b, c), b: (d,), c: (d,), d: ()}
    phases = (
        (set(), d),
        ({d}, b),
        ({d, b}, c),
        ({d, b, c}, a),
    )
    for completed, expected in phases:
        urls = _graph_fixture(monkeypatch, graph, {a, b, c, d}, completed)
        preflight = runtime.acquire_current_github_preflight("owner/repo", "token")
        decision = classify_dispatch(preflight)
        assert decision.disposition == "AUTHORIZE"
        assert decision.selected_issue_id == expected
        assert decision.selected_routing == ("executor", "implement-change")
        assert all(
            not action_entry_authorized(preflight, number, ("executor", "implement-change"))
            for number in (a, b, c, d)
            if number != expected
        )
        assert sum(f"/issues/{d}/comments?" in url for url in urls) == (0 if expected == a else 1)


def test_suspension_does_not_require_blocked_formal_frontier_or_stop_unrelated_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = {10: (20, None), 20: (), 30: ()}
    urls = _graph_fixture(monkeypatch, graph, {10, 20, 30}, set(), missing_formal_evidence={10})
    decision = classify_dispatch(runtime.acquire_current_github_preflight("owner/repo", "token"))
    assert decision.selected_issue_id == 20
    assert all("/issues/10/timeline?" not in url for url in urls)
    # Completing 20 is insufficient while the external condition remains.
    _graph_fixture(monkeypatch, graph, {10, 20, 30}, {20}, missing_formal_evidence={10})
    decision = classify_dispatch(runtime.acquire_current_github_preflight("owner/repo", "token"))
    assert decision.selected_issue_id == 30
    # The fresh corrected declaration makes the original Action runnable again.
    _graph_fixture(monkeypatch, {10: (20,), 20: (), 30: ()}, {10, 20, 30}, {20})
    decision = classify_dispatch(runtime.acquire_current_github_preflight("owner/repo", "token"))
    assert decision.selected_issue_id == 10


def test_failed_prerequisite_suspends_only_its_dependent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _graph_fixture(monkeypatch, {10: (20,), 20: (), 30: ()}, {10, 20}, set(), failed={20})
    decision = classify_dispatch(runtime.acquire_current_github_preflight("owner/repo", "token"))
    assert decision.selected_issue_id == 30
    _graph_fixture(monkeypatch, {10: (20,), 20: ()}, {10, 20}, set(), failed={20})
    waiting = classify_dispatch(runtime.acquire_current_github_preflight("owner/repo", "token"))
    assert waiting.disposition == "NO_WORK"
    assert waiting.reason == "dependencies-unsatisfied"


def test_formal_priority_reaches_transitive_preactivation_prerequisite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _graph_fixture(monkeypatch, {10: (), 20: (30,), 30: (40,), 40: ()}, {20}, set())
    decision = classify_dispatch(runtime.acquire_current_github_preflight("owner/repo", "token"))
    assert decision.selected_issue_id == 40
    assert decision.selected_routing == ("lead", "explore-change")


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
