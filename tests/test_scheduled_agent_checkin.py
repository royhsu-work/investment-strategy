from __future__ import annotations

from datetime import date
from pathlib import Path

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


def test_daily_rollover_workflow_is_repository_owned_and_not_a_mailbox() -> None:
    workflow = Path(".github/workflows/scheduled-agent-checkin.yml").read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert 'cron: "0 16 * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "investment_strategy.scheduled_agent_checkin" in workflow
    assert "issues: write" in workflow
    assert "AGENT_RUNTIME_CHECKIN_ISSUE" not in workflow
    assert "DISPATCH_DECISION" not in workflow
