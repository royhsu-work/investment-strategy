"""Regression for canonical ACTION_RESULT fields rendered as Markdown bullets."""

import investment_strategy.scheduled_agent_runtime as runtime


def _bulleted_lifecycle_complete_105_comment() -> dict[str, object]:
    return {
        "id": 5348437664,
        "body": (
            "## ACTION_RESULT\n\n"
            "- Workflow: #105\n"
            "- Change: `enforce-dispatch-cardinality-preflight`\n"
            "- Action: `Lead / finalize-archive`\n"
            "- Result: `LIFECYCLE_COMPLETE`\n"
            "- Revision: Archive PR #108 exact reviewed head "
            "`38d2e9c90bf72e710d9e43cc55a7b6d18c36f845`; merge commit "
            "`77ba3d9b746dc05f562626d13937f9c672996ba9`\n"
        ),
        "user": {"login": "royhsu-work"},
        "author_association": "OWNER",
        "created_at": "2026-08-19T21:31:00Z",
        "updated_at": "2026-08-19T21:31:00Z",
    }


def test_bulleted_completion_is_terminal_when_exceptional_classifier_consumes_it() -> None:
    evidence = runtime._terminal_evidence_from_comments(
        (_bulleted_lifecycle_complete_105_comment(),),
        issue_number=105,
        change="enforce-dispatch-cardinality-preflight",
        repository_owner="royhsu-work",
    )

    assert evidence == "terminal-history"


def test_bulleted_fields_do_not_allow_duplicate_terminal_identity() -> None:
    comment = _bulleted_lifecycle_complete_105_comment()
    comment["body"] = f"{comment['body']}\nWorkflow: #105\n"

    assert not runtime._valid_lifecycle_complete_comment(
        comment,
        issue_number=105,
        change="enforce-dispatch-cardinality-preflight",
        repository_owner="royhsu-work",
    )
