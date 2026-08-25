from __future__ import annotations

from investment_strategy import issue_comment_bridge as bridge

LIVE_REQUEST_COMMENT_ID = 5398504508
LIVE_DECISION_COMMENT_ID = 5398509738
LIVE_DEFAULT_BRANCH_REVISION = "a4ad197552fd062b6c46b547aa61a0a7edc768d8"
LIVE_DECISION_BODY = (
    "DISPATCH_DECISION\n"
    f"Request-Comment-ID: {LIVE_REQUEST_COMMENT_ID}\n"
    f"Default-Branch-Revision: {LIVE_DEFAULT_BRANCH_REVISION}\n"
    "Disposition: AUTHORIZE\n"
    "Issue: 140\n"
    "Role: lead\n"
    "Action: finalize-change"
)


def test_live_machine_dispatch_evidence_matches_exact_correlated_authorize_contract() -> None:
    """Preserve the bounded Slice 5 runtime evidence observed by the ChatGPT invocation."""

    # The decision comment itself is durable audit evidence. Correlation is still
    # exclusively the request-comment id carried inside the production payload.
    assert LIVE_DECISION_COMMENT_ID == 5398509738

    parsed = bridge.parse_dispatch_decision(LIVE_DECISION_BODY)

    assert parsed is not None
    assert parsed.request_comment_id == LIVE_REQUEST_COMMENT_ID
    assert parsed.default_branch_revision == LIVE_DEFAULT_BRANCH_REVISION
    assert parsed.disposition == "AUTHORIZE"
    assert parsed.issue_number == 140
    assert parsed.role == "lead"
    assert parsed.action == "finalize-change"

    for forbidden in ("Skill:", "Effect:"):
        assert forbidden not in LIVE_DECISION_BODY
    assert bridge.parse_dispatch_request(LIVE_DECISION_BODY) is None
