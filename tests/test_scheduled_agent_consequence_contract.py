"""Executable consequence topology and interruption-boundary regressions."""

from __future__ import annotations

import json

import pytest

import investment_strategy.scheduled_agent_application_bridge as bridge
import investment_strategy.scheduled_agent_effects as effects
from investment_strategy.scheduled_agent_action_model import TRANSITIONS, Action, ResultKind
from investment_strategy.scheduled_agent_effect_contract import (
    EvidenceTarget,
    consequence_spec_for,
    legal_transition_keys,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest

_REPOSITORY = "royhsu-work/investment-strategy"
_MAIN = "a" * 40
_ARCHIVE_HEAD = "b" * 40
_CHANGE = "source-decision-explore-materialization"
_TOKEN = "test"  # noqa: S105


def _archive_ready_worker() -> str:
    return json.dumps(
        {
            "issue_number": 234,
            "role": "lead",
            "action": "finalize-change",
            "change": _CHANGE,
            "result_kind": "archive-ready",
            "evidence_ref": "issuecomment-archive",
            "result_content": "archive branch and workflow evidence",
            "requested_effects": [
                {
                    "kind": "github-mutation",
                    "payload_json": json.dumps(
                        {
                            "issue_number": 234,
                            "operation": "workflow-dispatch",
                            "workflow_id": "openspec-archive.yml",
                            "ref": "main",
                            "inputs": {
                                "change": _CHANGE,
                                "issue": "234",
                                "revision": _MAIN,
                                "request_key": f"archive-234-{_MAIN}",
                            },
                        },
                        sort_keys=True,
                    ),
                },
                {
                    "kind": "issue-comment",
                    "payload_json": json.dumps(
                        {
                            "issue_number": 234,
                            "body": (
                                "ACTION_RESULT\nWorkflow: #234\n"
                                f"Change: {_CHANGE}\nRole: lead\n"
                                "Action: finalize-change\nResult: ARCHIVE_READY\n"
                                f"Revision: {_MAIN}\nDefault-Branch-Revision: {_MAIN}"
                            ),
                        },
                        sort_keys=True,
                    ),
                },
            ],
        },
        sort_keys=True,
    )


def _merge_archive_worker() -> str:
    return json.dumps(
        {
            "issue_number": 234,
            "role": "executor",
            "action": "merge-archive-pr",
            "change": _CHANGE,
            "result_kind": "merged",
            "evidence_ref": "pr#301@archive-head",
            "result_content": "exact reviewed Archive PR merge evidence",
            "requested_effects": [],
        },
        sort_keys=True,
    )


def test_every_legal_transition_has_exactly_one_consequence_spec() -> None:
    expected = {(action, result) for action, results in TRANSITIONS.items() for result in results}
    assert legal_transition_keys() == expected
    assert {
        (spec.action, spec.result)
        for spec in (consequence_spec_for(action, result) for action, result in expected)
    } == expected


def test_archive_snapshot_derives_only_missing_archive_pr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch = f"agent/archive-{_CHANGE}"

    def fake_read(
        _repository: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path == f"git/ref/heads/{branch}":
            return {"object": {"sha": _ARCHIVE_HEAD}}
        if path.startswith("pulls?state=all"):
            return []
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_github_json", fake_read)
    raw = bridge._fresh_application_worker_result(
        _archive_ready_worker(),
        source=WorkerRequest(234, "lead", "finalize-change"),
        change=_CHANGE,
        repository=_REPOSITORY,
        token=_TOKEN,
        current_revision=_MAIN,
        default_branch="main",
        request_comment_id=9001,
    )
    payload = json.loads(raw)
    effects = payload["requested_effects"]
    assert len(effects) == 1
    assert effects[0]["kind"] == "github-mutation"
    create = json.loads(effects[0]["payload_json"])
    assert create == {
        "base": "main",
        "body": bridge._archive_pr_body(_CHANGE, 234),
        "draft": False,
        "expected_head_sha": _ARCHIVE_HEAD,
        "head": branch,
        "issue_number": 234,
        "operation": "pull-request-create",
        "title": f"Archive OpenSpec change {_CHANGE}",
    }


def test_recovered_semantic_intent_rebuilds_formal_after_pr_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch = f"agent/archive-{_CHANGE}"
    full_pr = {
        "number": 301,
        "state": "open",
        "merged": False,
        "draft": False,
        "title": f"Archive OpenSpec change {_CHANGE}",
        "body": "Archive\n\nRefs #234\n",
        "head": {
            "ref": branch,
            "sha": _ARCHIVE_HEAD,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": _MAIN,
            "repo": {"full_name": _REPOSITORY},
        },
    }
    ready = False

    def fake_read(
        _repository: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path == f"git/ref/heads/{branch}":
            return {"object": {"sha": _ARCHIVE_HEAD}}
        if path.startswith("pulls?state=all"):
            return [full_pr] if ready else []
        if path == "pulls/301":
            return full_pr
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_github_json", fake_read)
    source = WorkerRequest(234, "lead", "finalize-change")
    first = bridge._fresh_application_worker_result(
        _archive_ready_worker(),
        source=source,
        change=_CHANGE,
        repository=_REPOSITORY,
        token=_TOKEN,
        current_revision=_MAIN,
        default_branch="main",
        request_comment_id=9001,
    )
    accepted_intent = effects.semantic_intent_payload(first)
    assert json.loads(accepted_intent)["requested_effects"] == []

    ready = True
    recovered = json.loads(
        bridge._fresh_application_worker_result(
            accepted_intent,
            source=source,
            change=_CHANGE,
            repository=_REPOSITORY,
            token=_TOKEN,
            current_revision=_MAIN,
            default_branch="main",
            request_comment_id=9001,
        )
    )
    requested = recovered["requested_effects"]
    assert len(requested) == 1
    assert requested[0]["kind"] == "issue-comment"
    assert json.loads(requested[0]["payload_json"])["body"].startswith("ACTION_RESULT\n")


def test_archive_ready_requires_current_non_draft_exact_pr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch = f"agent/archive-{_CHANGE}"
    full_pr = {
        "number": 301,
        "state": "open",
        "merged": False,
        "draft": False,
        "title": f"Archive OpenSpec change {_CHANGE}",
        "body": "Archive\n\nRefs #234\n",
        "head": {
            "ref": branch,
            "sha": _ARCHIVE_HEAD,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": _MAIN,
            "repo": {"full_name": _REPOSITORY},
        },
    }

    def fake_read(
        _repository: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path == f"git/ref/heads/{branch}":
            return {"object": {"sha": _ARCHIVE_HEAD}}
        if path.startswith("pulls?state=all"):
            return [full_pr]
        if path == "pulls/301":
            return full_pr
        raise AssertionError(path)

    monkeypatch.setattr(effects, "_github_json", fake_read)
    assert effects.archive_pr_readiness_complete(
        repository=_REPOSITORY,
        token=_TOKEN,
        issue_number=234,
        change=_CHANGE,
        current_revision=_MAIN,
    )
    full_pr["draft"] = True
    assert not effects.archive_pr_readiness_complete(
        repository=_REPOSITORY,
        token=_TOKEN,
        issue_number=234,
        change=_CHANGE,
        current_revision=_MAIN,
    )


def test_merge_intent_derives_exact_merge_carrier_before_formal_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch = f"agent/archive-{_CHANGE}"
    full_pr = {
        "number": 301,
        "state": "open",
        "merged": False,
        "draft": False,
        "title": f"Archive OpenSpec change {_CHANGE}",
        "body": "Archive\n\nRefs #234\n",
        "head": {
            "ref": branch,
            "sha": _ARCHIVE_HEAD,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": _MAIN,
            "repo": {"full_name": _REPOSITORY},
        },
    }

    def fake_read(
        _repository: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path.startswith("pulls?state=all"):
            return [full_pr]
        if path == "pulls/301":
            return full_pr
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_github_json", fake_read)
    payload = json.loads(
        bridge._fresh_application_worker_result(
            _merge_archive_worker(),
            source=WorkerRequest(234, "executor", "merge-archive-pr"),
            change=_CHANGE,
            repository=_REPOSITORY,
            token=_TOKEN,
            current_revision=_MAIN,
            default_branch="main",
            request_comment_id=9002,
        )
    )
    requested = payload["requested_effects"]
    assert len(requested) == 1
    effect = json.loads(requested[0]["payload_json"])
    assert effect == {
        "expected_head_sha": _ARCHIVE_HEAD,
        "issue_number": 234,
        "merge_method": "merge",
        "number": 301,
        "operation": "pull-request-merge",
    }


def test_merge_intent_reconstructs_formal_result_only_after_merged_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch = f"agent/archive-{_CHANGE}"
    merge_commit = "c" * 40
    full_pr = {
        "number": 301,
        "state": "closed",
        "merged": True,
        "merged_at": "2026-09-21T12:00:00Z",
        "merge_commit_sha": merge_commit,
        "draft": False,
        "title": f"Archive OpenSpec change {_CHANGE}",
        "body": "Archive\n\nRefs #234\n",
        "head": {
            "ref": branch,
            "sha": _ARCHIVE_HEAD,
            "repo": {"full_name": _REPOSITORY},
        },
        "base": {
            "ref": "main",
            "sha": _MAIN,
            "repo": {"full_name": _REPOSITORY},
        },
    }

    def fake_read(
        _repository: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == "":
            return {"default_branch": "main"}
        if path.startswith("pulls?state=all"):
            return [full_pr]
        if path == "pulls/301":
            return full_pr
        if path == f"compare/{merge_commit}...{_MAIN}":
            return {
                "status": "identical",
                "behind_by": 0,
                "base_commit": {"sha": merge_commit},
            }
        if path == f"git/ref/heads/{branch}":
            return None
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_github_json", fake_read)
    payload = json.loads(
        bridge._fresh_application_worker_result(
            _merge_archive_worker(),
            source=WorkerRequest(234, "executor", "merge-archive-pr"),
            change=_CHANGE,
            repository=_REPOSITORY,
            token=_TOKEN,
            current_revision=_MAIN,
            default_branch="main",
            request_comment_id=9003,
        )
    )
    requested = payload["requested_effects"]
    assert len(requested) == 1
    formal = json.loads(requested[0]["payload_json"])["body"]
    assert formal.startswith("MERGE_RESULT\n")
    assert f"Revision: {merge_commit}" in formal


def test_review_archive_blocked_uses_default_branch_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorkerRequest(234, "reviewer", "review-archive")
    raw = json.dumps(
        {
            "issue_number": 234,
            "role": "reviewer",
            "action": "review-archive",
            "change": _CHANGE,
            "result_kind": "blocked",
            "result_content": "Archive PR is absent",
            "requested_effects": [],
        },
        sort_keys=True,
    )
    monkeypatch.setattr(
        bridge,
        "_machine_carrier_head",
        lambda **_kwargs: pytest.fail("BLOCKED review must not resolve an implementation carrier"),
    )
    assert (
        bridge._machine_result_revision(
            raw,
            source,
            change=_CHANGE,
            repository=_REPOSITORY,
            token=_TOKEN,
            current_revision=_MAIN,
            default_branch="main",
        )
        == _MAIN
    )


def test_archive_ready_spec_names_successor_readiness() -> None:
    spec = consequence_spec_for(Action.FINALIZE_CHANGE, ResultKind.ARCHIVE_READY)
    assert spec.evidence_target is EvidenceTarget.ARCHIVE_PR_HEAD
    assert spec.completion_predicate == "archive-pr-successor-ready"
    assert spec.successor_required


def test_archive_terminal_spec_names_merged_successor_evidence() -> None:
    spec = consequence_spec_for(Action.FINALIZE_ARCHIVE, ResultKind.LIFECYCLE_COMPLETE)
    assert spec.evidence_target is EvidenceTarget.MERGED_PR_HEAD
    assert spec.successor_required is False
