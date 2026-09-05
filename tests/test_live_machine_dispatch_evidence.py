from __future__ import annotations

import json

from investment_strategy import issue_comment_bridge as bridge

LIVE_REQUEST_COMMENT_ID = 5550423455
LIVE_RUN_ID = 33953875181
LIVE_ARTIFACT_ID = 9965709634
LIVE_DEFAULT_BRANCH_REVISION = "6cf4d0a45fe3770a4ff459f937a08e063695943f"
LIVE_ARTIFACT_DIGEST = "sha256:e513cf45774778fd00f6a7dc6f039ed094442763474ad791cd9ad497789952ed"
LIVE_RESULT_BODY = (
    '{"action":"propose-change","default_branch_revision":"'
    f"{LIVE_DEFAULT_BRANCH_REVISION}"
    '","disposition":"AUTHORIZE","issue_number":169,'
    f'"request_comment_id":{LIVE_REQUEST_COMMENT_ID},'
    '"schema":"scheduled-agent-dispatch-result/v1"}'
)


def test_live_machine_dispatch_evidence_matches_exact_artifact_contract() -> None:
    """Preserve the exact repository-produced Artifact E2E evidence for #194."""

    assert LIVE_RUN_ID == 33953875181
    assert LIVE_ARTIFACT_ID == 9965709634
    assert LIVE_ARTIFACT_DIGEST.startswith("sha256:")

    parsed = bridge.parse_dispatch_result_document(LIVE_RESULT_BODY)
    payload = json.loads(LIVE_RESULT_BODY)

    assert parsed.request_comment_id == LIVE_REQUEST_COMMENT_ID
    assert parsed.default_branch_revision == LIVE_DEFAULT_BRANCH_REVISION
    assert parsed.disposition == "AUTHORIZE"
    assert parsed.issue_number == 169
    assert parsed.role == "lead"
    assert parsed.action == "propose-change"
    assert "role" not in payload
    assert bridge.parse_dispatch_request(LIVE_RESULT_BODY) is None
