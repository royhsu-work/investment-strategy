"""Regressions for canonical Issue Change identity outside Markdown examples."""

import investment_strategy.scheduled_agent_runtime as runtime


def _closed_93_payload() -> dict[str, object]:
    return {
        "number": 93,
        "state": "closed",
        "state_reason": "completed",
        "body": (
            "Change: remove-generic-human-explore-admission\n\n"
            "## Normal workflow example\n\n"
            "```text\n"
            "Change: unset\n"
            "```\n"
        ),
        "labels": [
            {"name": "agent:lead"},
            {"name": "action:finalize-archive"},
            {"name": "human:approved"},
        ],
        "comments": 29,
        "created_at": "2026-08-18T17:28:23Z",
        "closed_at": "2026-08-19T12:51:55Z",
    }


def test_fenced_change_example_preserves_canonical_closed_debt_identity() -> None:
    observation = runtime.normalize_github_issue(_closed_93_payload())

    assert observation is not None
    assert observation.change == "remove-generic-human-explore-admission"
    assert observation.routing == ("lead", "finalize-archive")
    assert observation.routing_debt is True
    assert observation.authoritative is True


def test_multiple_top_level_change_fields_remain_indeterminate() -> None:
    payload = _closed_93_payload()
    payload["body"] = (
        "Change: remove-generic-human-explore-admission\nChange: attacker-controlled-second-value\n"
    )

    observation = runtime.normalize_github_issue(payload)
    assert observation is not None
    assert observation.change == "unset"
    assert not observation.authoritative
