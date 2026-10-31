from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

import investment_strategy.scheduled_agent_checkin as checkin
from investment_strategy.scheduled_agent_checkin import (
    CheckinDisposition,
    checkin_body,
    checkin_title,
    plan_rollover,
    select_current_shard,
)


def _issue(
    number: int,
    day: date,
    *,
    state: str = "open",
    labels: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "number": number,
        "title": checkin_title(day),
        "state": state,
        "labels": [] if labels is None else labels,
    }


def test_checkin_body_has_only_bounded_shard_identity() -> None:
    body = checkin_body(date(2026, 9, 3))
    assert "<!-- scheduled-agent-runtime-checkin -->" in body
    assert "Asia/Taipei" in body
    assert "2026-09-03" in body
    assert "Change:" not in body
    assert "Action:" not in body


def test_current_shard_selection_is_unique_and_fail_closed() -> None:
    day = date(2026, 9, 3)

    selected = select_current_shard([_issue(142, day)], day)
    assert selected.disposition is CheckinDisposition.SELECTED
    assert selected.issue_number == 142

    missing = select_current_shard([_issue(141, date(2026, 9, 2))], day)
    assert missing.disposition is CheckinDisposition.MISSING
    assert missing.issue_number is None

    duplicate = select_current_shard([_issue(142, day), _issue(143, day)], day)
    assert duplicate.disposition is CheckinDisposition.FAIL_CLOSED
    assert duplicate.reason == "duplicate-current-day"

    closed = select_current_shard([_issue(142, day, state="closed")], day)
    assert closed.disposition is CheckinDisposition.FAIL_CLOSED
    assert closed.reason == "current-day-not-open"


def test_rollover_establishes_today_before_retiring_yesterday() -> None:
    day = date(2026, 9, 3)
    yesterday = _issue(142, date(2026, 9, 2))
    plan = plan_rollover([yesterday], day)

    assert plan.disposition is CheckinDisposition.CREATE
    assert plan.current_issue_number is None
    assert plan.retire_issue_numbers == (142,)

    current = _issue(143, day)
    plan = plan_rollover([yesterday, current], day)
    assert plan.disposition is CheckinDisposition.RETIRE
    assert plan.current_issue_number == 143
    assert plan.retire_issue_numbers == (142,)


def test_rollover_preserves_closed_in_flight_shard_and_rejects_bad_identity() -> None:
    day = date(2026, 9, 3)
    current = _issue(143, day)
    closed_old = _issue(142, date(2026, 9, 2), state="closed")
    plan = plan_rollover([closed_old, current], day)
    assert plan.retire_issue_numbers == ()

    malformed = dict(current)
    malformed["labels"] = [{"name": "action:implement-change"}]
    rejected = plan_rollover([malformed], day)
    assert rejected.disposition is CheckinDisposition.FAIL_CLOSED
    assert rejected.reason == "invalid-shard-identity"


def test_created_shard_postcondition_observes_eventual_consistency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    day = date(2026, 9, 3)
    observations = iter(
        (
            checkin.RolloverPlan(
                CheckinDisposition.CREATE,
                day,
                None,
                (142,),
            ),
            checkin.RolloverPlan(
                CheckinDisposition.CREATE,
                day,
                None,
                (142,),
            ),
            checkin.RolloverPlan(
                CheckinDisposition.RETIRE,
                day,
                143,
                (142,),
            ),
        )
    )

    monkeypatch.setattr(
        checkin,
        "_fresh_rollover",
        lambda _repository, _token, _today: ((), next(observations)),
    )
    monkeypatch.setattr(checkin.time, "sleep", lambda _seconds: None)

    plan = checkin._observe_created_shard("owner/repo", "token", day, 143)

    assert plan.current_issue_number == 143
    assert plan.disposition is CheckinDisposition.RETIRE


def test_daily_rollover_workflow_is_repository_owned_and_not_a_mailbox() -> None:
    workflow = Path(".github/workflows/scheduled-agent-checkin.yml").read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert 'cron: "0 16 * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "investment_strategy.scheduled_agent_checkin" in workflow
    assert "issues: write" in workflow
    assert "AGENT_RUNTIME_CHECKIN_ISSUE" not in workflow
    assert "DISPATCH_DECISION" not in workflow


def test_missing_day_handoff_uses_latest_unique_older_shard_and_exact_comment() -> None:
    today = date(2026, 11, 2)
    older = _issue(301, date(2026, 10, 27))
    older["locked"] = False
    prior = _issue(300, date(2026, 10, 24))
    prior["locked"] = False
    evidence = {300: (), 301: ()}
    selected = checkin.plan_rollover_handoff(
        [prior, older],
        today,
        commentable_issue_numbers=frozenset({300, 301}),
        comments_by_issue=evidence,
        actor_login="royhsu-work",
    )
    assert selected.source_issue_number == 301
    assert selected.current_issue_number is None
    assert selected.reason is None
    assert checkin.rollover_request_body(today, 301) == (
        "ROLLOVER_REQUEST\nRequested-Day: 2026-11-02\nSource-Shard: 301\n"
    )
    assert checkin.parse_rollover_request(checkin.rollover_request_body(today, 301)) == (
        today,
        301,
    )
    for invalid in (
        "ROLLOVER_REQUEST\nRequested-Day: 2026-11-02\nSource-Shard: 301",
        "ROLLOVER_REQUEST\nSource-Shard: 301\nRequested-Day: 2026-11-02\n",
        "ROLLOVER_REQUEST\nRequested-Day: 2026-11-02\nSource-Shard: 0301\n",
        (
            "ROLLOVER_REQUEST\nRequested-Day: 2026-11-02\n"
            "Source-Shard: 301\nAction: implement-change\n"
        ),
    ):
        assert checkin.parse_rollover_request(invalid) is None


def test_handoff_current_duplicate_locked_closed_and_missing_evidence_fail_closed() -> None:
    today = date(2026, 11, 2)
    older = _issue(301, date(2026, 10, 27))
    older["locked"] = False
    today_issue = _issue(302, today)
    selected = checkin.plan_rollover_handoff(
        [older, today_issue],
        today,
        commentable_issue_numbers=frozenset({301}),
        comments_by_issue={301: ()},
        actor_login="royhsu-work",
    )
    assert selected.current_issue_number == 302
    assert selected.source_issue_number is None

    duplicated = _issue(303, date(2026, 10, 27))
    duplicated["locked"] = False
    locked = dict(older, locked=True)
    missing = dict(older)
    closed = dict(older, state="closed")
    future = _issue(304, date(2026, 11, 3))
    for issues, capability, comments in (
        ([older, duplicated], {301, 303}, {301: (), 303: ()}),
        ([locked], {301}, {301: ()}),
        ([missing], {301}, {}),
        ([closed], set(), {301: ()}),
        ([future], {304}, {304: ()}),
    ):
        plan = checkin.plan_rollover_handoff(
            issues,
            today,
            commentable_issue_numbers=frozenset(capability),
            comments_by_issue=comments,
            actor_login="royhsu-work",
        )
        assert plan.source_issue_number is None
        assert plan.reason is not None
    valid_closed = checkin.plan_rollover_handoff(
        [closed],
        today,
        commentable_issue_numbers=frozenset({301}),
        comments_by_issue={301: ()},
        actor_login="royhsu-work",
    )
    assert valid_closed.source_issue_number == 301


def test_handoff_dedupes_valid_request_and_rejects_conflicting_history() -> None:
    today = date(2026, 11, 2)
    older = dict(_issue(301, date(2026, 10, 27)), locked=False)
    request = checkin.rollover_request_body(today, 301)
    trusted = {
        "id": 9001,
        "body": request,
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }
    dedup = checkin.plan_rollover_handoff(
        [older],
        today,
        commentable_issue_numbers=frozenset({301}),
        comments_by_issue={301: (trusted,)},
        actor_login="royhsu-work",
    )
    assert dedup.already_requested is True
    assert dedup.source_issue_number is None
    invalid = dict(trusted, body=request + "other")
    ambiguous = checkin.plan_rollover_handoff(
        [older],
        today,
        commentable_issue_numbers=frozenset({301}),
        comments_by_issue={301: (invalid,)},
        actor_login="royhsu-work",
    )
    assert ambiguous.reason is not None
    assert ambiguous.source_issue_number is None


def test_event_checkin_requires_real_created_connector_comment_and_rechecks_github(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    today = date(2026, 11, 2)
    old = dict(_issue(301, date(2026, 10, 27)), locked=False)
    request = checkin.rollover_request_body(today, 301)
    comment = {
        "id": 9001,
        "body": request,
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }
    event: dict[str, object] = {
        "action": "created",
        "repository": {"full_name": "royhsu-work/investment-strategy"},
        "sender": {"login": "royhsu-work"},
        "issue": old,
        "comment": comment,
    }

    def github(_repository: str, _token: str, path: str, **_kw: object) -> object:
        if path == "/issues/301":
            return old
        if path == "/issues/comments/9001":
            return comment
        if path == "/issues/301/comments?per_page=100&page=1":
            return [comment]
        raise AssertionError(path)

    monkeypatch.setattr(checkin, "_github_json", github)
    monkeypatch.setattr(checkin, "_github_issues", lambda *_args: (old,))
    assert (
        checkin.qualify_rollover_comment_event(
            "royhsu-work/investment-strategy",
            "token",
            event,
            today=today,
            actor_login="royhsu-work",
        )
        == 301
    )
    for bad in (
        dict(event, action="edited"),
        dict(event, sender={"login": "attacker"}),
        dict(event, comment=dict(comment, body=request + "malformed")),
        dict(event, repository={"full_name": "other/repo"}),
    ):
        assert (
            checkin.qualify_rollover_comment_event(
                "royhsu-work/investment-strategy",
                "token",
                bad,
                today=today,
                actor_login="royhsu-work",
            )
            is None
        )


def test_unknown_create_result_never_blindly_creates_a_second_shard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    today = date(2026, 11, 2)
    old = dict(_issue(301, date(2026, 10, 27)), locked=False)
    current = _issue(302, today)
    calls = {"create": 0}

    def create(*_args: object) -> int:
        calls["create"] += 1
        raise RuntimeError("GitHub response unknown after POST")

    monkeypatch.setattr(checkin, "_create_shard", create)
    monkeypatch.setattr(
        checkin,
        "_fresh_rollover",
        lambda *_args: ((old, current), checkin.plan_rollover([old, current], today)),
    )
    assert checkin._create_or_reconcile_shard("owner/repo", "token", today) == 302
    assert calls["create"] == 1


def test_comment_trigger_is_serialized_with_cron() -> None:
    workflow = Path(".github/workflows/scheduled-agent-checkin.yml").read_text(encoding="utf-8")
    assert "issue_comment:" in workflow
    assert "types: [created]" in workflow
    assert "scheduled-agent-checkin-${{ github.repository }}" in workflow
    assert "cancel-in-progress: false" in workflow


def test_pre_dispatch_duplicate_valid_requests_and_untrusted_comment_are_fail_closed() -> None:
    today = date(2026, 11, 2)
    older = dict(_issue(301, date(2026, 10, 27)), locked=False)
    body = checkin.rollover_request_body(today, 301)
    trusted = {
        "id": 9001,
        "body": body,
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }
    for comments in (
        (trusted, dict(trusted, id=9002)),
        (dict(trusted, user={"login": "attacker"}),),
        (dict(trusted, performed_via_github_app=None),),
    ):
        plan = checkin.plan_rollover_handoff(
            [older],
            today,
            commentable_issue_numbers=frozenset({301}),
            comments_by_issue={301: comments},
            actor_login="royhsu-work",
        )
        assert plan.reason is not None
        assert plan.source_issue_number is None


def test_untrusted_token_comment_and_stale_local_date_cannot_trigger_checkin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    today = date(2026, 11, 2)
    source = dict(_issue(301, date(2026, 10, 27)), locked=False)
    body = checkin.rollover_request_body(today, 301)
    comment = {
        "id": 9001,
        "body": body,
        "user": {"login": "royhsu-work"},
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }
    event = {
        "action": "created",
        "repository": {"full_name": "royhsu-work/investment-strategy"},
        "sender": {"login": "royhsu-work"},
        "issue": source,
        "comment": comment,
    }
    monkeypatch.setattr(
        checkin,
        "_github_json",
        lambda *_args, **_kwargs: dict(comment, performed_via_github_app=None),
    )
    assert (
        checkin.qualify_rollover_comment_event(
            "royhsu-work/investment-strategy",
            "token",
            event,
            today=today,
            actor_login="royhsu-work",
        )
        is None
    )
    assert (
        checkin.qualify_rollover_comment_event(
            "royhsu-work/investment-strategy",
            "token",
            event,
            today=date(2026, 11, 3),
            actor_login="royhsu-work",
        )
        is None
    )


def test_issue_comment_pagination_fails_closed_on_incomplete_api_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(checkin, "_github_json", lambda *_args, **_kwargs: {"missing": "page"})
    with pytest.raises(RuntimeError, match="incomplete"):
        checkin._github_comments("owner/repo", "token", 301)


def test_create_unknown_and_no_unique_readback_does_not_retry_post(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    today = date(2026, 11, 2)
    calls = {"post": 0}

    def create(*_args: object) -> int:
        calls["post"] += 1
        raise RuntimeError("transport failed after create")

    monkeypatch.setattr(checkin, "_create_shard", create)
    monkeypatch.setattr(
        checkin,
        "_fresh_rollover",
        lambda *_args: ((), checkin.RolloverPlan(CheckinDisposition.CREATE, today, None, ())),
    )
    with pytest.raises(RuntimeError, match="transport failed"):
        checkin._create_or_reconcile_shard("owner/repo", "token", today)
    assert calls["post"] == 1


def test_native_comment_handoff_and_cron_share_one_idempotent_checkin_owner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    today = date(2026, 11, 2)
    older = dict(_issue(301, date(2026, 10, 27)), locked=False)
    current = _issue(302, today)
    snapshots = iter(((older,), (older, current), (older, current)))
    creations = {"count": 0}
    retired: list[int] = []

    def issues(*_args: object) -> tuple[dict[str, object], ...]:
        return next(snapshots)

    def create(*_args: object) -> int:
        creations["count"] += 1
        return 302

    def retire(*_args: object, **_kwargs: object) -> list[int]:
        older["state"] = "closed"
        retired.append(301)
        return [301]

    event_file = tmp_path / "created.json"
    event_file.write_text(json.dumps({"action": "created"}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issue_comment")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))
    monkeypatch.setenv("GITHUB_ACTOR", "royhsu-work")
    monkeypatch.setenv("GITHUB_REPOSITORY", "royhsu-work/investment-strategy")
    monkeypatch.setenv("GITHUB_TOKEN", "unused")
    monkeypatch.setattr(checkin, "taipei_day", lambda: today)
    monkeypatch.setattr(checkin, "qualify_rollover_comment_event", lambda *_args, **_kw: 301)
    monkeypatch.setattr(checkin, "_github_issues", issues)
    monkeypatch.setattr(checkin, "_create_shard", create)
    monkeypatch.setattr(checkin, "_retire_exact_targets", retire)
    assert checkin.main() == 0
    assert creations["count"] == 1
    assert retired == [301]
