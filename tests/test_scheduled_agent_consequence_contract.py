"""Executable consequence topology and interruption-boundary regressions."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Literal, cast

import pytest

import investment_strategy.scheduled_agent_application_bridge as bridge
import investment_strategy.scheduled_agent_effects as effects
import investment_strategy.scheduled_agent_validation_resource as resource
from investment_strategy.scheduled_agent_action_model import TRANSITIONS, Action, ResultKind
from investment_strategy.scheduled_agent_application_carrier import (
    ImplementationCarrierQualification,
)
from investment_strategy.scheduled_agent_application_materialization import (
    MaterializationRequest,
)
from investment_strategy.scheduled_agent_archive_freshness import (
    archive_branch_matches_current_change,
)
from investment_strategy.scheduled_agent_effect_contract import (
    DURABLE_PREFIXES,
    DurablePrefix,
    EvidenceTarget,
    consequence_spec_for,
    legal_transition_keys,
    verification_matrix,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_validation_resource import WorkProductFile

_REPOSITORY = "royhsu-work/investment-strategy"
_MAIN = "a" * 40
_ARCHIVE_HEAD = "b" * 40
_CHANGE = "source-decision-explore-materialization"
_TOKEN = "test"  # noqa: S105


def _current_archive_evidence(path: str) -> object | None:
    """Complete, source-ancestral archive fixture for unrelated PR tests."""
    if path == f"compare/{_MAIN}...{_ARCHIVE_HEAD}":
        return {
            "status": "ahead",
            "behind_by": 0,
            "base_commit": {"sha": _MAIN},
        }
    prefix = f"openspec/changes/{_CHANGE}"
    if path == f"git/trees/{_MAIN}?recursive=1":
        return {
            "truncated": False,
            "tree": [
                {"type": "blob", "path": f"{prefix}/tasks.md", "sha": "1" * 40},
                {
                    "type": "blob",
                    "path": f"{prefix}/specs/agent-workflow/spec.md",
                    "sha": "2" * 40,
                },
            ],
        }
    if path == f"git/trees/{_ARCHIVE_HEAD}?recursive=1":
        prefix = f"openspec/changes/archive/2026-11-01-{_CHANGE}"
        return {
            "truncated": False,
            "tree": [
                {"type": "blob", "path": f"{prefix}/tasks.md", "sha": "1" * 40},
                {
                    "type": "blob",
                    "path": f"{prefix}/specs/agent-workflow/spec.md",
                    "sha": "2" * 40,
                },
                {
                    "type": "blob",
                    "path": "openspec/specs/agent-workflow/spec.md",
                    "sha": "3" * 40,
                },
            ],
        }
    return None


@pytest.mark.parametrize(
    "failure",
    (
        "diverged",
        "stale-tasks",
        "truncated",
        "duplicate-archive",
        "missing-canonical",
        "active-remains",
    ),
)
def test_archive_provenance_rejects_all_stale_or_ambiguous_evidence(failure: str) -> None:
    def fake_read(_repository: str, _token: str, path: str) -> object:
        result = deepcopy(_current_archive_evidence(path))
        assert isinstance(result, dict)
        if failure == "diverged" and path.startswith("compare/"):
            result["status"] = "diverged"
            result["behind_by"] = 77
        if path == f"git/trees/{_ARCHIVE_HEAD}?recursive=1":
            archive_tree = result["tree"]
            assert isinstance(archive_tree, list)
            if failure == "stale-tasks":
                cast(dict[str, str], archive_tree[0])["sha"] = "9" * 40
            elif failure == "truncated":
                result["truncated"] = True
            elif failure == "duplicate-archive":
                duplicate = deepcopy(archive_tree[0])
                duplicate["path"] = duplicate["path"].replace("2026-11-01", "2026-10-23")
                archive_tree.append(duplicate)
            elif failure == "missing-canonical":
                archive_tree.pop()
            elif failure == "active-remains":
                archive_tree.append(
                    {
                        "type": "blob",
                        "path": f"openspec/changes/{_CHANGE}/tasks.md",
                        "sha": "1" * 40,
                    }
                )
        return result

    assert not archive_branch_matches_current_change(
        fake_read,
        repository=_REPOSITORY,
        token=_TOKEN,
        change=_CHANGE,
        source_revision=_MAIN,
        archive_revision=_ARCHIVE_HEAD,
    )


def test_archive_provenance_accepts_exact_current_archive_snapshot() -> None:
    def fake_read(_repository: str, _token: str, path: str) -> object:
        result = _current_archive_evidence(path)
        assert result is not None
        return result

    assert archive_branch_matches_current_change(
        fake_read,
        repository=_REPOSITORY,
        token=_TOKEN,
        change=_CHANGE,
        source_revision=_MAIN,
        archive_revision=_ARCHIVE_HEAD,
    )


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


@pytest.mark.parametrize(
    "action",
    (Action.PROPOSE_CHANGE, Action.RESOLVE_QUESTION),
)
def test_openspec_ready_consequence_requires_fresh_materialized_revision(
    action: Action,
) -> None:
    spec = consequence_spec_for(action, ResultKind.READY_FOR_OPENSPEC_REVIEW)

    assert spec.evidence_target is EvidenceTarget.MATERIALIZED_REVISION
    assert spec.completion_predicate == "materialized-revision-and-successor-ready"
    assert spec.missing_effect == "application-materialize-or-formal-result"


def _matrix_intent(action: Action, result: ResultKind) -> str:
    role = (
        "reviewer"
        if action.value.startswith("review-")
        else ("executor" if action.value.startswith(("implement-", "merge-")) else "lead")
    )
    return json.dumps(
        {
            "_semantic_intent_version": 2,
            "issue_number": 272,
            "role": role,
            "action": action.value,
            "change": "matrix-change",
            "result_kind": result.value,
            "evidence_ref": f"matrix-{action.value}-{result.value}",
            "result_content": "immutable semantic evidence",
            "requested_effects": [
                {
                    "kind": "github-mutation",
                    "payload_json": json.dumps(
                        {
                            "operation": "workflow-dispatch",
                            "issue_number": 272,
                            "ref": "main",
                        },
                        sort_keys=True,
                    ),
                }
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _projection(action: Action, result: ResultKind) -> tuple[str, str, str, str]:
    spec = consequence_spec_for(action, result)
    successor = TRANSITIONS[action][result]
    return (
        spec.evidence_target.value,
        spec.completion_predicate,
        spec.missing_effect,
        "terminal" if successor is None else successor.value,
    )


def test_verification_matrix_covers_every_prefix_without_duplicate_owner() -> None:
    matrix = verification_matrix()
    expected_count = len(legal_transition_keys()) * len(DURABLE_PREFIXES)
    assert len(matrix) == expected_count
    assert len(set(matrix)) == expected_count
    assert {prefix for _, _, prefix in matrix} == set(DurablePrefix)
    assert {(action, result) for action, result, _ in matrix} == legal_transition_keys()
    for action, result, _prefix in matrix:
        spec = consequence_spec_for(action, result)
        assert spec.action is action
        assert spec.result is result
        assert spec.evidence_target.value
        assert spec.completion_predicate
        assert spec.missing_effect


def test_fresh_process_matrix_preserves_intent_and_commit_projection() -> None:
    """Every durable prefix re-enters the same intent and consequence owner."""

    matrix = verification_matrix()
    expected_by_prefix: dict[DurablePrefix, dict[str, tuple[str, str, str, str]]] = {}
    for prefix in DURABLE_PREFIXES:
        payload = [
            {
                "prefix": prefix.value,
                "action": action.value,
                "result": result.value,
                "raw": _matrix_intent(action, result),
            }
            for action, result, _matrix_prefix in matrix
            if _matrix_prefix is prefix
        ]
        script = """
import json
import sys
from investment_strategy.scheduled_agent_action_model import Action, ResultKind, TRANSITIONS
from investment_strategy.scheduled_agent_effect_contract import consequence_spec_for
from investment_strategy.scheduled_agent_effects import semantic_intent_payload

items = json.load(sys.stdin)
out = []
for item in items:
    action = Action(item["action"])
    result = ResultKind(item["result"])
    accepted = semantic_intent_payload(item["raw"])
    decoded = json.loads(accepted)
    spec = consequence_spec_for(action, result)
    successor = TRANSITIONS[action][result]
    out.append({
        "prefix": item["prefix"],
        "action": item["action"],
        "result": item["result"],
        "accepted": accepted,
        "requested_effects": decoded["requested_effects"],
        "projection": [
            spec.evidence_target.value,
            spec.completion_predicate,
            spec.missing_effect,
            "terminal" if successor is None else successor.value,
        ],
    })
json.dump(out, sys.stdout, sort_keys=True)
"""
        result = subprocess.run(  # noqa: S603 - fixed interpreter and inline verification script
            [sys.executable, "-c", script],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONPATH": str(Path.cwd() / "src")},
        )
        assert result.returncode == 0, result.stderr
        recovered = json.loads(result.stdout)
        for item in recovered:
            assert tuple(item["projection"]) == _projection(
                Action(item["action"]),
                ResultKind(item["result"]),
            )
        expected_by_prefix[prefix] = {
            item["accepted"]: tuple(item["projection"]) for item in recovered
        }
        assert all(item["requested_effects"] == [] for item in recovered)

    baseline = expected_by_prefix[DURABLE_PREFIXES[0]]
    for prefix, projections in expected_by_prefix.items():
        assert projections == baseline, prefix


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
        evidence = _current_archive_evidence(path)
        if evidence is not None:
            return evidence
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


def test_archive_snapshot_rejects_observed_322_stale_archive_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The actual #322 old ref must never authorize a new Archive PR."""
    change = "restore-no-work-idle-discovery"
    source = "328843882a2aaae51b6bbe3274d70882e94d5569"
    stale = "eb15b4c2362cd0910fc2601be69f679b18d54bd1"
    branch = f"agent/archive-{change}"

    def fake_read(
        _repository: str,
        _token: str,
        path: str,
        **_kwargs: object,
    ) -> object:
        if path == f"git/ref/heads/{branch}":
            return {"object": {"sha": stale}}
        if path.startswith("pulls?state=all"):
            return []
        if path == f"compare/{source}...{stale}":
            return {"status": "diverged", "behind_by": 77, "ahead_by": 1}
        raise AssertionError(path)

    monkeypatch.setattr(bridge, "_github_json", fake_read)
    state, actual_branch, actual_sha = bridge._fresh_archive_state(
        _REPOSITORY,
        _TOKEN,
        issue_number=322,
        change=change,
        current_revision=source,
        default_branch="main",
    )
    assert (state, actual_branch, actual_sha) == ("conflict", branch, stale)


def test_322_post_merge_checkpoint_rejects_new_code_until_open_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A merged task ledger cannot authorize new source; an open carrier can."""
    change = "restore-no-work-idle-discovery"
    source = WorkerRequest(322, "executor", "implement-change")
    task = WorkProductFile(f"openspec/changes/{change}/tasks.md", "1" * 40, "2" * 40)
    implementation = WorkProductFile(".github/scripts/openspec_archive.py", "3" * 40, "4" * 40)
    adapter = effects.GitHubEffectAdapter(
        _REPOSITORY, _TOKEN, source, authorized_change=change, current_revision=_MAIN
    )

    def materialization(pr: int, branch: str, base: str) -> MaterializationRequest:
        return MaterializationRequest(
            issue_number=322,
            expected_change=change,
            change=change,
            branch=branch,
            base_sha=base,
            message="fix(#322): current archive source",
            files=(task, implementation),
            pr_number=pr,
        )

    def qualification(
        pr: int, branch: str, head: str, disposition: Literal["HISTORICAL_MERGED", "QUALIFIED"]
    ) -> ImplementationCarrierQualification:
        return ImplementationCarrierQualification(
            disposition=disposition,
            reason="fixture lineage",
            repository=_REPOSITORY,
            issue_number=322,
            change=change,
            action="implement-change",
            pr_number=pr,
            branch=branch,
            head_sha=head,
            default_branch="main",
            default_revision=_MAIN,
            historical_pr_number=398,
        )

    merged_branch = f"agent/{change}-continuation-353"
    merged_head = "b" * 40
    monkeypatch.setattr(
        effects,
        "qualify_implementation_carrier",
        lambda **_kwargs: qualification(398, merged_branch, merged_head, "HISTORICAL_MERGED"),
    )
    assert not adapter.validate_implementation_checkpoint(
        materialization(398, merged_branch, merged_head), ("6.1", "6.2", "6.3", "6.4")
    )

    open_branch = f"agent/{change}-continuation-398"
    open_head = "c" * 40
    monkeypatch.setattr(
        effects,
        "qualify_implementation_carrier",
        lambda **_kwargs: qualification(408, open_branch, open_head, "QUALIFIED"),
    )
    monkeypatch.setattr(effects, "task_checkpoint_is_exact", lambda *_a, **_kw: True)
    monkeypatch.setattr(effects, "verify_implementation_candidate", lambda *_a, **_kw: True)
    assert adapter.validate_implementation_checkpoint(
        materialization(408, open_branch, open_head), ("6.1", "6.2", "6.3", "6.4")
    )


def test_322_unchanged_historical_task_only_reconciliation_remains_legal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    change = "restore-no-work-idle-discovery"
    unchanged = "5" * 40
    task = WorkProductFile(f"openspec/changes/{change}/tasks.md", unchanged, unchanged)
    monkeypatch.setattr(resource, "_content_sha_at", lambda *_a, **_kw: unchanged)
    monkeypatch.setattr(
        resource,
        "_content_text_at",
        lambda *_a, **_kw: "## 5. Previous completed slice\n- [x] 5.1 Verified\n",
    )
    assert resource.completed_task_bookkeeping_is_current(
        _REPOSITORY, _TOKEN, change=change, revision="b" * 40, files=(task,)
    )
    assert not resource.completed_task_bookkeeping_is_current(
        _REPOSITORY,
        _TOKEN,
        change=change,
        revision="b" * 40,
        files=(task, WorkProductFile(".github/scripts/openspec_archive.py", "7" * 40, "8" * 40)),
    )


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
        evidence = _current_archive_evidence(path)
        if evidence is not None:
            return evidence
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
        evidence = _current_archive_evidence(path)
        if evidence is not None:
            return evidence
        raise AssertionError(path)

    monkeypatch.setattr(effects, "_github_json", fake_read)
    assert effects.archive_pr_readiness_complete(
        repository=_REPOSITORY,
        token=_TOKEN,
        issue_number=234,
        change=_CHANGE,
        current_revision=_MAIN,
    )
    # A main-branch repair may land after the archive carrier is created. The
    # exact current PR/base identity remains a complete predecessor
    # consequence; mutation-time guards still capture the observed base SHA.
    cast(dict[str, object], full_pr["base"])["sha"] = "f" * 40
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
