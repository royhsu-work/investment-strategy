"""Production-shaped regression coverage for application carrier qualification."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest

from investment_strategy import scheduled_agent_application_carrier as carrier
from investment_strategy import scheduled_agent_effects as effects
from investment_strategy.scheduled_agent_runtime import WorkerRequest

REPOSITORY = "royhsu-work/investment-strategy"
CHANGE = "qualify-active-formal-consequences"
MAIN = "1" * 40
HEAD = "2" * 40
HISTORICAL_HEAD = "3" * 40
MERGE = "4" * 40
CONTINUATION_MERGE = "8" * 40
TEST_VALUE = "opaque-test-value"


def _repo(name: str = REPOSITORY) -> dict[str, object]:
    return {"full_name": name}


@pytest.mark.parametrize("result_kind", ["pass", "findings", "absent"])
def test_merge_target_is_exact_current_review_pass_predecessor(
    monkeypatch: pytest.MonkeyPatch, result_kind: str
) -> None:
    monkeypatch.setattr(
        carrier,
        "normalize_github_issue",
        lambda *_args: SimpleNamespace(
            authoritative=True,
            state="open",
            change=CHANGE,
            routing=("executor", "merge-implementation-pr"),
        ),
    )
    monkeypatch.setattr(carrier, "_paged_list", lambda *_args, **_kwargs: ({"id": 1},))
    monkeypatch.setattr(
        carrier,
        "parse_formal_result",
        lambda *_args, **_kwargs: (
            None
            if result_kind == "absent"
            else SimpleNamespace(
                valid=True,
                issue_number=229,
                change=CHANGE,
                role="reviewer",
                action="review-implementation",
                result_kind=result_kind,
                successor=("executor", "merge-implementation-pr"),
                revision=HISTORICAL_HEAD,
                default_branch_revision=MAIN,
            )
        ),
    )
    head = carrier.current_reviewed_implementation_head(
        REPOSITORY,
        TEST_VALUE,
        source=WorkerRequest(229, "executor", "merge-implementation-pr"),
        change=CHANGE,
        current_revision=MAIN,
        read=lambda *_args: {"number": 229},
    )
    assert head == (
        carrier.ReviewedImplementationConsequence(HISTORICAL_HEAD, None)
        if result_kind == "pass"
        else None
    )


@pytest.mark.parametrize("blocked_revision", ["default", "historical-head", "unrelated"])
def test_merge_blocked_self_loop_keeps_review_pass_head(
    monkeypatch: pytest.MonkeyPatch, blocked_revision: str
) -> None:
    monkeypatch.setattr(
        carrier,
        "normalize_github_issue",
        lambda *_args: SimpleNamespace(
            authoritative=True,
            state="open",
            change=CHANGE,
            routing=("executor", "merge-implementation-pr"),
        ),
    )
    monkeypatch.setattr(carrier, "_paged_list", lambda *_args, **_kwargs: ({"id": 1}, {"id": 2}))
    reviewed = SimpleNamespace(
        valid=True,
        issue_number=229,
        change=CHANGE,
        role="reviewer",
        action="review-implementation",
        result_kind="pass",
        successor=("executor", "merge-implementation-pr"),
        revision=HISTORICAL_HEAD,
        default_branch_revision=MAIN,
    )
    blocked = SimpleNamespace(
        valid=True,
        issue_number=229,
        change=CHANGE,
        role="executor",
        action="merge-implementation-pr",
        result_kind="blocked",
        successor=("executor", "merge-implementation-pr"),
        revision={"default": MAIN, "historical-head": HISTORICAL_HEAD, "unrelated": HEAD}[
            blocked_revision
        ],
        default_branch_revision=MAIN,
    )
    monkeypatch.setattr(
        carrier,
        "parse_formal_result",
        lambda item, **_kwargs: reviewed if item["id"] == 1 else blocked,
    )
    actual = carrier.current_reviewed_implementation_head(
        REPOSITORY,
        TEST_VALUE,
        source=WorkerRequest(229, "executor", "merge-implementation-pr"),
        change=CHANGE,
        current_revision=MAIN,
        read=lambda *_args: {"number": 229},
    )
    assert actual == (
        carrier.ReviewedImplementationConsequence(HISTORICAL_HEAD, None)
        if blocked_revision != "unrelated"
        else None
    )


@pytest.mark.parametrize("successor_routed", [False, True])
def test_durable_merged_formal_keeps_exact_reviewed_head_across_routing(
    monkeypatch: pytest.MonkeyPatch, successor_routed: bool
) -> None:
    monkeypatch.setattr(
        carrier,
        "normalize_github_issue",
        lambda *_args: SimpleNamespace(
            authoritative=True,
            state="open",
            change=CHANGE,
            routing=("lead", "finalize-change")
            if successor_routed
            else ("executor", "merge-implementation-pr"),
        ),
    )
    monkeypatch.setattr(carrier, "_paged_list", lambda *_args, **_kwargs: ({"id": 1}, {"id": 2}))
    pass_event = SimpleNamespace(
        valid=True,
        issue_number=229,
        change=CHANGE,
        role="reviewer",
        action="review-implementation",
        result_kind="pass",
        successor=("executor", "merge-implementation-pr"),
        revision=HISTORICAL_HEAD,
        default_branch_revision=MAIN,
    )
    merge_event = SimpleNamespace(
        valid=True,
        issue_number=229,
        change=CHANGE,
        role="executor",
        action="merge-implementation-pr",
        result_kind="merged",
        successor=("lead", "finalize-change"),
        revision=CONTINUATION_MERGE,
        default_branch_revision=MAIN,
    )
    monkeypatch.setattr(
        carrier,
        "parse_formal_result",
        lambda comment, **_kwargs: pass_event if comment["id"] == 1 else merge_event,
    )
    result = carrier.current_reviewed_implementation_head(
        REPOSITORY,
        TEST_VALUE,
        source=WorkerRequest(229, "executor", "merge-implementation-pr"),
        change=CHANGE,
        current_revision=MAIN,
        read=lambda *_args: {"number": 229},
    )
    assert result == carrier.ReviewedImplementationConsequence(HISTORICAL_HEAD, CONTINUATION_MERGE)


def _pr(
    number: int,
    *,
    branch: str,
    head_sha: str,
    state: str = "open",
    merged: bool = False,
    merged_at: str | None = None,
    merge_commit_sha: str | None = None,
    issue_number: int = 229,
    base_sha: str = MAIN,
) -> dict[str, object]:
    return {
        "number": number,
        "state": state,
        "draft": False,
        "merged": merged,
        "merged_at": merged_at,
        "merge_commit_sha": merge_commit_sha,
        "body": (
            f"Continue OpenSpec change `{CHANGE}` after the merged carrier.\n\nRefs #{issue_number}"
        ),
        "head": {
            "ref": branch,
            "sha": head_sha,
            "repo": _repo(),
        },
        "base": {
            "ref": "main",
            "sha": base_sha,
            "repo": _repo(),
        },
    }


def _historical_pr() -> dict[str, object]:
    payload = _pr(
        232,
        branch=f"agent/{CHANGE}",
        head_sha=HISTORICAL_HEAD,
        state="closed",
        merged=True,
        merged_at="2026-09-10T00:00:00Z",
        merge_commit_sha=MERGE,
    )
    payload["body"] = "Refs #229"
    return payload


def _continuation_pr(
    *,
    number: int = 236,
    branch: str | None = None,
    head_sha: str = HEAD,
    issue_number: int = 229,
) -> dict[str, object]:
    return _pr(
        number,
        branch=branch or f"agent/{CHANGE}-continuation-232",
        head_sha=head_sha,
        issue_number=issue_number,
    )


_DEFAULT_HISTORICAL = object()


def _fake_github(
    *,
    current_pr: dict[str, object] | None = None,
    historical_pr: dict[str, object] | None | object = _DEFAULT_HISTORICAL,
    merged_continuations: list[dict[str, object]] | None = None,
    open_prs: list[dict[str, object]] | None = None,
    pr_files: list[dict[str, object]] | None = None,
    historical_files: list[dict[str, object]] | None = None,
    default_is_ancestor: bool = True,
    historical_is_ancestor: bool = True,
    default_advance_files: list[dict[str, object]] | None = None,
    current_merge_is_ancestor: bool = True,
    branch_ref_sha: str | None = HEAD,
    default_revision: str = MAIN,
    issue_body: str | None = None,
    formal_comments: list[dict[str, object]] | None = None,
    routing_timeline: list[dict[str, object]] | None = None,
    request_comments: dict[int, dict[str, object]] | None = None,
) -> Callable[..., object | None]:
    current = current_pr or _continuation_pr()
    historical = (
        _historical_pr()
        if historical_pr is _DEFAULT_HISTORICAL
        else cast(dict[str, object] | None, historical_pr)
    )
    continuations = [] if merged_continuations is None else merged_continuations
    opens = [current] if open_prs is None else open_prs
    files = [{"filename": "src/investment_strategy/example.py"}] if pr_files is None else pr_files
    history_files = (
        [{"filename": f"openspec/changes/{CHANGE}/proposal.md"}]
        if historical_files is None
        else historical_files
    )
    body = issue_body or f"Change: {CHANGE}\n"
    current_head = cast(dict[str, object], current["head"])

    def fake(
        repository: str,
        token: str,
        api_path: str,
        *,
        allow_not_found: bool = False,
    ) -> object | None:
        assert repository == REPOSITORY
        assert token == TEST_VALUE
        if api_path == "":
            return {"default_branch": "main"}
        if api_path == "git/ref/heads/main":
            return {"object": {"sha": default_revision}}
        if api_path == "issues/229":
            return {"number": 229, "state": "open", "body": body}
        if api_path.startswith("issues/229/comments?"):
            return [] if formal_comments is None else formal_comments
        if api_path.startswith("issues/comments/"):
            identifier = int(api_path.rsplit("/", 1)[1])
            return (request_comments or {}).get(identifier)
        if api_path.startswith("issues/229/timeline?"):
            return [] if routing_timeline is None else routing_timeline
        if api_path == f"pulls/{current['number']}":
            return current
        if historical is not None and api_path == f"pulls/{historical['number']}":
            return historical
        for continuation in continuations:
            if api_path == f"pulls/{continuation['number']}":
                return continuation
        if api_path.startswith("pulls?") and "state=closed" in api_path:
            requested_head = parse_qs(urlsplit(api_path).query).get("head", [None])[0]
            closed_candidates = [
                candidate
                for candidate in ([historical] if historical is not None else [])
                + continuations
                + ([current] if current.get("merged") is True else [])
                if isinstance(candidate, dict)
                and isinstance(candidate.get("head"), dict)
                and requested_head
                == f"royhsu-work:{cast(dict[str, object], candidate['head']).get('ref', '')}"
            ]
            deduplicated = {
                cast(int, candidate["number"]): candidate for candidate in closed_candidates
            }
            return [{"number": number} for number in deduplicated]
        if api_path.startswith("pulls?") and "state=open" in api_path:
            return opens
        if historical is not None and api_path.startswith(f"pulls/{historical['number']}/files?"):
            return history_files
        for continuation in continuations:
            if api_path.startswith(f"pulls/{continuation['number']}/files?"):
                return files
        if api_path.startswith(f"pulls/{current['number']}/files?"):
            return files
        if historical is not None and api_path == f"compare/{MERGE}...{default_revision}":
            return {
                "status": "ahead" if historical_is_ancestor else "diverged",
                "behind_by": 0 if historical_is_ancestor else 1,
            }
        for continuation in continuations:
            continuation_merge = continuation.get("merge_commit_sha")
            if continuation_merge is not None and api_path == (
                f"compare/{continuation_merge}...{default_revision}"
            ):
                return {"status": "ahead", "behind_by": 0}
        current_merge = current.get("merge_commit_sha")
        if current_merge is not None and api_path == (
            f"compare/{current_merge}...{default_revision}"
        ):
            return {
                "status": "ahead" if current_merge_is_ancestor else "diverged",
                "behind_by": 0 if current_merge_is_ancestor else 1,
            }
        if api_path == f"compare/{default_revision}...{current_head['sha']}":
            return {
                "status": "ahead" if default_is_ancestor else "diverged",
                "behind_by": 0 if default_is_ancestor else 2,
            }
        base = cast(dict[str, object], current["base"])
        base_sha = base.get("sha")
        if (
            default_advance_files is not None
            and isinstance(base_sha, str)
            and api_path == f"compare/{base_sha}...{default_revision}"
        ):
            return {
                "status": "ahead",
                "behind_by": 0,
                "files": default_advance_files,
            }
        if api_path.startswith("compare/"):
            return None
        branch = cast(str, current_head["ref"])
        if api_path == f"git/ref/heads/{branch}":
            if branch_ref_sha is None and allow_not_found:
                return None
            return {"object": {"sha": branch_ref_sha}}
        raise AssertionError(f"unexpected GitHub path: {api_path}")

    return fake


def _source(action: str = "implement-change") -> WorkerRequest:
    return WorkerRequest(229, "executor", action)


def _qualify(
    monkeypatch: pytest.MonkeyPatch,
    fake: Callable[..., object | None],
    *,
    current_revision: str = MAIN,
) -> carrier.ImplementationCarrierQualification:
    monkeypatch.setattr(carrier, "_github_json", fake)
    return carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=_source(),
        change=CHANGE,
        pr_number=236,
        current_revision=current_revision,
    )


def test_initial_carrier_remains_strict_and_qualified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial = _continuation_pr(branch=f"agent/{CHANGE}")
    fake = _fake_github(
        current_pr=initial,
        historical_pr=None,
        open_prs=[initial],
        pr_files=[{"filename": f"openspec/changes/{CHANGE}/proposal.md"}],
    )
    decision = _qualify(monkeypatch, fake)
    assert decision.disposition == "QUALIFIED"
    assert decision.branch == f"agent/{CHANGE}"
    assert decision.historical_pr_number is None


def test_code_only_continuation_is_qualified_from_historical_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(monkeypatch, _fake_github())
    assert decision.disposition == "QUALIFIED"
    assert decision.pr_number == 236
    assert decision.branch == f"agent/{CHANGE}-continuation-232"
    assert decision.historical_pr_number == 232


def test_lead_retirement_guard_uses_real_code_only_implementation_qualification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not mock the shared carrier qualifier: Lead is retiring code, not OpenSpec."""

    fake = _fake_github(pr_files=[{"filename": "src/investment_strategy/example.py"}])
    monkeypatch.setattr(effects, "_github_json", fake)
    adapter = effects.GitHubEffectAdapter(
        REPOSITORY,
        TEST_VALUE,
        WorkerRequest(229, "lead", "resolve-question"),
        authorized_change=CHANGE,
        current_revision=MAIN,
        expected_result_kind="ready",
        accepted_intent=True,
    )
    monkeypatch.setattr(
        adapter, "_authorized_issue_observation", lambda: SimpleNamespace(change=CHANGE)
    )
    monkeypatch.setattr(adapter, "_default_branch", lambda: "main")
    monkeypatch.setattr(adapter, "_default_branch_revision", lambda _branch: MAIN)
    target = adapter._lead_retirement_target(236, HEAD, require_open=True)
    assert target is not None and target["number"] == 236
    # Lead OpenSpec materialization still has the narrower active-Change gate.
    openspec = carrier.qualify_change_carrier(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=WorkerRequest(229, "lead", "resolve-question"),
        change=CHANGE,
        pr_number=236,
        current_revision=MAIN,
        read=fake,
    )
    assert openspec.reason == "carrier-openspec-change-missing-or-competing"


def _supersession_formal_comments(
    old_head: str,
    *,
    first_id: int = 900,
    ready_at: str = "2026-11-03T01:00:00Z",
    findings_at: str = "2026-11-03T02:00:00Z",
) -> list[dict[str, object]]:
    def result(
        *,
        comment_id: int,
        role: str,
        action: str,
        result_kind: str,
        successor: str,
        timestamp: str,
    ) -> dict[str, object]:
        marker = "REVIEW_RESULT" if role == "reviewer" else "ACTION_RESULT"
        return {
            "id": comment_id,
            "user": {"login": "github-actions[bot]"},
            "performed_via_github_app": {"slug": "github-actions"},
            "created_at": timestamp,
            "body": "\n".join(
                (
                    marker,
                    "Workflow: #229",
                    f"Change: {CHANGE}",
                    f"Role: {role}",
                    f"Action: {action}",
                    f"Result: {result_kind.upper()}",
                    f"Revision: {old_head}",
                    f"Default-Branch-Revision: {MAIN}",
                    "Application-Correlation: "
                    f"application:{comment_id + 100}:229:{CHANGE}:"
                    f"{role}:{action}:{result_kind}:{MAIN}",
                    f"Repository-derived successor: {successor}",
                )
            ),
        }

    return [
        result(
            comment_id=first_id,
            role="executor",
            action="implement-change",
            result_kind="ready",
            successor="Reviewer / review-implementation",
            timestamp=ready_at,
        ),
        result(
            comment_id=first_id + 1,
            role="reviewer",
            action="review-implementation",
            result_kind="findings",
            successor="Executor / implement-change",
            timestamp=findings_at,
        ),
    ]


def _supersession_routing_timeline() -> list[dict[str, object]]:
    return [
        {
            "id": 9010,
            "event": "unlabeled",
            "label": {"name": "action:review-implementation"},
            "actor": {"login": "github-actions[bot]"},
            "created_at": "2026-11-03T02:01:00Z",
        },
        {
            "id": 9011,
            "event": "labeled",
            "label": {"name": "action:implement-change"},
            "actor": {"login": "github-actions[bot]"},
            "created_at": "2026-11-03T02:01:00Z",
        },
    ]


def _accepted_supersession_comments(
    old_head: str,
    *,
    carrier_number: int = 236,
    reformat_accepted_effects: bool = False,
    tamper_accepted_effect: bool = False,
    first_id: int = 900,
    ready_at: str = "2026-11-03T01:00:00Z",
    findings_at: str = "2026-11-03T02:00:00Z",
    branch: str | None = None,
) -> tuple[list[dict[str, object]], dict[int, dict[str, object]]]:
    """Use real ingress/decision parsers to bind both formal results to requests."""

    from investment_strategy.scheduled_agent_application_bridge import (
        ApplicationRequest,
        _render_accepted_application_wire,
        dispatch_correlation_for,
    )

    formal = _supersession_formal_comments(
        old_head, first_id=first_id, ready_at=ready_at, findings_at=findings_at
    )
    requests: dict[int, dict[str, object]] = {}
    for entry in tuple(formal):
        body = cast(str, entry["body"])
        fields = dict(line.split(": ", 1) for line in body.splitlines()[1:])
        role = fields["Role"]
        action = fields["Action"]
        result_kind = fields["Result"].lower()
        request_id = cast(int, entry["id"]) + 100
        effects = []
        if result_kind == "ready":
            effects.append(
                {
                    "kind": "github-mutation",
                    "payload_json": json.dumps(
                        {
                            "operation": "application-materialize",
                            "pr_number": carrier_number,
                            "branch": branch or f"agent/{CHANGE}-continuation-232",
                        }
                    ),
                }
            )
        raw_result = json.dumps(
            {
                "_semantic_intent_version": 2,
                "issue_number": 229,
                "role": role,
                "action": action,
                "change": CHANGE,
                "result_kind": result_kind,
                "requested_effects": effects,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        request_body = _render_accepted_application_wire(
            ApplicationRequest(
                authorization_revision=MAIN,
                raw_worker_result=raw_result,
                dispatch_correlation=dispatch_correlation_for(
                    REPOSITORY, WorkerRequest(229, role, action), MAIN
                ),
            )
        )
        requests[request_id] = {
            "id": request_id,
            "body": request_body,
            "user": {"login": "royhsu-work"},
            "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
        }

        def sha(value: str) -> str:
            return hashlib.sha256(value.encode("utf-8")).hexdigest()

        accepted_result = raw_result
        if reformat_accepted_effects or tamper_accepted_effect:
            accepted = json.loads(raw_result)
            for effect in accepted["requested_effects"]:
                nested = json.loads(effect["payload_json"])
                if tamper_accepted_effect:
                    nested["unapproved_field"] = "mutated"
                effect["payload_json"] = json.dumps(nested, sort_keys=True)
            accepted_result = json.dumps(accepted, sort_keys=True, separators=(",", ":"))
        decision_body = "\n".join(
            (
                "APPLICATION_DECISION",
                f"Request-Comment: {request_id}",
                f"Request-Body-SHA256: {sha(request_body)}",
                f"Authorization-Revision: {MAIN}",
                "Issue: 229",
                f"Role: {role}",
                f"Action: {action}",
                f"Change: {CHANGE}",
                f"Result-Kind: {result_kind}",
                "Disposition: ACCEPTED",
                f"Worker-Result-SHA256: {sha(accepted_result)}",
                f"Application-Intent-B64: {base64.b64encode(accepted_result.encode()).decode()}",
                "Reason: accepted",
            )
        )
        formal.append(
            {
                "id": request_id + 100,
                "body": decision_body,
                "user": {"login": "github-actions[bot]"},
                "performed_via_github_app": {"slug": "github-actions"},
                "created_at": "2026-11-03T01:00:00Z",
            }
        )
    return formal, requests


def _accepted_lead_retirement_comments(
    old_head: str,
    *,
    retired_number: int = 236,
    request_id: int = 1060,
    close_fields: dict[str, str] | None = None,
    decision_at: str = "2026-11-03T02:59:00Z",
    versionless_ingress: bool = False,
    extra_invocation_effect: bool = False,
    accepted_content_override: str | None = None,
) -> tuple[list[dict[str, object]], dict[int, dict[str, object]]]:
    """One exact accepted Lead READY close, without inventing Reviewer FINDINGS."""

    from investment_strategy.scheduled_agent_application_bridge import (
        ApplicationRequest,
        dispatch_correlation_for,
        render_application_request,
    )

    result = {
        "_semantic_intent_version": 2,
        "issue_number": 229,
        "role": "lead",
        "action": "resolve-question",
        "change": CHANGE,
        "result_kind": "ready",
        "result_content": "Human-resolved implementation readiness",
        "requested_effects": [
            {
                "kind": "github-mutation",
                "payload_json": json.dumps(
                    {
                        "issue_number": 229,
                        "operation": "pull-request-update",
                        "number": retired_number,
                        "expected_head_sha": old_head,
                        "fields": {"state": "closed"} if close_fields is None else close_fields,
                    }
                ),
            }
        ],
    }
    if extra_invocation_effect:
        cast(list[dict[str, str]], result["requested_effects"]).append(
            {
                "kind": "issue-comment",
                "payload_json": json.dumps({"issue_number": 229, "body": "ACTION_RESULT\n..."}),
            }
        )
    accepted_result = {**result}
    if accepted_content_override is not None:
        accepted_result["result_content"] = accepted_content_override
    accepted = effects.semantic_intent_payload(
        json.dumps(accepted_result, sort_keys=True, separators=(",", ":"))
    )
    if versionless_ingress:
        del result["_semantic_intent_version"]
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"))
    request_body = render_application_request(
        ApplicationRequest(
            authorization_revision=MAIN,
            raw_worker_result=raw,
            dispatch_correlation=dispatch_correlation_for(
                REPOSITORY, WorkerRequest(229, "lead", "resolve-question"), MAIN
            ),
        )
    )

    def digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    decision = {
        "id": request_id + 100,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
        "created_at": decision_at,
        "body": "\n".join(
            (
                "APPLICATION_DECISION",
                f"Request-Comment: {request_id}",
                f"Request-Body-SHA256: {digest(request_body)}",
                f"Authorization-Revision: {MAIN}",
                "Issue: 229",
                "Role: lead",
                "Action: resolve-question",
                f"Change: {CHANGE}",
                "Result-Kind: ready",
                "Disposition: ACCEPTED",
                f"Worker-Result-SHA256: {digest(accepted)}",
                f"Application-Intent-B64: {base64.b64encode(accepted.encode()).decode()}",
                "Reason: accepted",
            )
        ),
    }
    formal = {
        "id": request_id + 200,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
        "created_at": "2026-11-03T04:00:00Z",
        "body": "\n".join(
            (
                "ACTION_RESULT",
                "Workflow: #229",
                f"Change: {CHANGE}",
                "Role: lead",
                "Action: resolve-question",
                "Result: READY",
                f"Revision: {MAIN}",
                f"Default-Branch-Revision: {MAIN}",
                "Application-Correlation: "
                f"application:{request_id}:229:{CHANGE}:lead:resolve-question:ready:{MAIN}",
                "Repository-derived successor: Executor / implement-change",
            )
        ),
    }
    return [decision, formal], {
        request_id: {
            "id": request_id,
            "body": request_body,
            "user": {"login": "royhsu-work"},
            "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
        }
    }


@pytest.mark.parametrize("wrong_fields", [False, True])
def test_lead_accepted_retirement_can_supersede_pass_carrier(
    monkeypatch: pytest.MonkeyPatch, wrong_fields: bool
) -> None:
    retired = _continuation_pr(head_sha="5" * 40)
    retired.update(state="closed", closed_at="2026-11-03T03:00:00Z")
    replacement = _continuation_pr(number=237, branch=f"agent/{CHANGE}-supersedes-236")
    formal, requests = _accepted_lead_retirement_comments(
        "5" * 40, close_fields={"state": "open"} if wrong_fields else None
    )
    github = _fake_github(
        current_pr=replacement,
        merged_continuations=[retired],
        open_prs=[replacement],
        formal_comments=formal,
        request_comments=requests,
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    assert (
        carrier.qualify_supersession_branch(
            repository=REPOSITORY,
            token=TEST_VALUE,
            issue_number=229,
            change=CHANGE,
            branch=f"agent/{CHANGE}-supersedes-236",
            current_revision=MAIN,
        )
        is not wrong_fields
    )


@pytest.mark.parametrize("extra_invocation_effect", [False, True])
@pytest.mark.parametrize("accepted_content_override", [None, "Changed semantic evidence"])
def test_versionless_ingress_proves_accepted_lead_retirement(
    monkeypatch: pytest.MonkeyPatch,
    extra_invocation_effect: bool,
    accepted_content_override: str | None,
) -> None:
    """The real ingress lacks the Application-owned semantic-intent version."""

    retired = _continuation_pr(head_sha="5" * 40)
    retired.update(state="closed", closed_at="2026-11-03T03:00:00Z")
    replacement = _continuation_pr(number=237, branch=f"agent/{CHANGE}-supersedes-236")
    formal, requests = _accepted_lead_retirement_comments(
        "5" * 40,
        versionless_ingress=True,
        extra_invocation_effect=extra_invocation_effect,
        accepted_content_override=accepted_content_override,
    )
    github = _fake_github(
        current_pr=replacement,
        merged_continuations=[retired],
        open_prs=[replacement],
        formal_comments=formal,
        request_comments=requests,
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    assert carrier.qualify_supersession_branch(
        repository=REPOSITORY,
        token=TEST_VALUE,
        issue_number=229,
        change=CHANGE,
        branch=f"agent/{CHANGE}-supersedes-236",
        current_revision=MAIN,
    ) is (accepted_content_override is None)


def test_lead_retirement_preserves_second_generation_supersession(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A PASS-reviewed supersession can itself be retired without false FINDINGS."""

    first_retired = _continuation_pr(head_sha="5" * 40)
    first_retired.update(state="closed", merged=False, closed_at="2026-11-03T03:00:00Z")
    second_retired = _continuation_pr(
        number=237, branch=f"agent/{CHANGE}-supersedes-236", head_sha="6" * 40
    )
    second_retired.update(state="closed", merged=False, closed_at="2026-11-03T03:45:00Z")
    replacement = _continuation_pr(number=238, branch=f"agent/{CHANGE}-supersedes-237")
    first_formal, first_requests = _accepted_supersession_comments("5" * 40)
    second_formal, second_requests = _accepted_lead_retirement_comments(
        "6" * 40,
        retired_number=237,
        request_id=1090,
        decision_at="2026-11-03T03:40:00Z",
        versionless_ingress=True,
    )
    github = _fake_github(
        current_pr=replacement,
        merged_continuations=[first_retired, second_retired],
        open_prs=[replacement],
        formal_comments=first_formal + second_formal,
        routing_timeline=_supersession_routing_timeline(),
        request_comments=first_requests | second_requests,
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    decision = carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=_source(),
        change=CHANGE,
        pr_number=238,
        current_revision=MAIN,
    )
    assert decision.disposition == "QUALIFIED", decision.reason


@pytest.mark.parametrize("replacement_merged", [False, True])
def test_supersession_can_retire_an_already_superseding_carrier(
    monkeypatch: pytest.MonkeyPatch,
    replacement_merged: bool,
) -> None:
    first_retired = _continuation_pr(head_sha="5" * 40)
    first_retired.update(state="closed", merged=False, closed_at="2026-11-03T03:00:00Z")
    second_retired = _continuation_pr(
        number=237, branch=f"agent/{CHANGE}-supersedes-236", head_sha="6" * 40
    )
    second_retired.update(state="closed", merged=False, closed_at="2026-11-03T05:00:00Z")
    replacement = _continuation_pr(number=238, branch=f"agent/{CHANGE}-supersedes-237")
    if replacement_merged:
        replacement.update(
            state="closed",
            merged=True,
            merged_at="2026-11-04T02:00:00Z",
            merge_commit_sha=CONTINUATION_MERGE,
        )
    first_formal, first_requests = _accepted_supersession_comments("5" * 40)
    second_formal, second_requests = _accepted_supersession_comments(
        "6" * 40,
        carrier_number=237,
        first_id=920,
        ready_at="2026-11-03T03:30:00Z",
        findings_at="2026-11-03T04:00:00Z",
        branch=f"agent/{CHANGE}-supersedes-236",
    )
    timeline = _supersession_routing_timeline() + [
        {
            "event": event,
            "label": {"name": label},
            "actor": {"login": "github-actions[bot]"},
            "created_at": "2026-11-03T04:01:00Z",
        }
        for event, label in [
            ("unlabeled", "action:review-implementation"),
            ("labeled", "action:implement-change"),
        ]
    ]
    github = _fake_github(
        current_pr=replacement,
        merged_continuations=[first_retired, second_retired],
        open_prs=[] if replacement_merged else [replacement],
        formal_comments=first_formal + second_formal,
        routing_timeline=timeline,
        request_comments=first_requests | second_requests,
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    assert carrier.qualify_supersession_branch(
        repository=REPOSITORY,
        token=TEST_VALUE,
        issue_number=229,
        change=CHANGE,
        branch=f"agent/{CHANGE}-supersedes-237",
        current_revision=MAIN,
    )
    decision = carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=_source(),
        change=CHANGE,
        pr_number=238,
        current_revision=MAIN,
    )
    assert decision.disposition == ("HISTORICAL_MERGED" if replacement_merged else "QUALIFIED")


@pytest.mark.parametrize(
    ("retired", "findings", "expected"),
    [
        (True, True, "QUALIFIED"),
        (True, False, "INDETERMINATE"),
        (False, True, "INDETERMINATE"),
    ],
)
def test_superseded_unmerged_carrier_requires_formal_findings_before_fresh_main_replacement(
    monkeypatch: pytest.MonkeyPatch,
    retired: bool,
    findings: bool,
    expected: str,
) -> None:
    """Closed-unmerged history is replaceable only after an exact legal handoff."""

    old_head = "5" * 40
    retired_pr = _continuation_pr(head_sha=old_head)
    retired_pr.update(
        state="closed" if retired else "open",
        merged=False,
        closed_at="2026-11-03T03:00:00Z" if retired else None,
    )
    replacement_pr = _continuation_pr(
        number=237,
        branch=f"agent/{CHANGE}-supersedes-236",
    )
    accepted_comments, requests = _accepted_supersession_comments(old_head)
    github = _fake_github(
        current_pr=replacement_pr,
        merged_continuations=[retired_pr],
        open_prs=[replacement_pr],
        formal_comments=accepted_comments if findings else [],
        routing_timeline=_supersession_routing_timeline(),
        request_comments=requests,
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    decision = carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=_source(),
        change=CHANGE,
        pr_number=237,
        current_revision=MAIN,
    )
    assert decision.disposition == expected, decision.reason
    if expected == "QUALIFIED":
        assert decision.head_sha == HEAD
        assert decision.branch == f"agent/{CHANGE}-supersedes-236"


def test_supersession_rejects_bot_shaped_results_without_accepted_application_decisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_head = "5" * 40
    retired = _continuation_pr(head_sha=old_head)
    retired.update(state="closed", merged=False, closed_at="2026-11-03T03:00:00Z")
    replacement = _continuation_pr(number=237, branch=f"agent/{CHANGE}-supersedes-236")
    fake = _fake_github(
        current_pr=replacement,
        merged_continuations=[retired],
        open_prs=[replacement],
        formal_comments=_supersession_formal_comments(old_head),
        routing_timeline=_supersession_routing_timeline(),
    )
    monkeypatch.setattr(carrier, "_github_json", fake)
    assert not carrier.qualify_supersession_branch(
        repository=REPOSITORY,
        token=TEST_VALUE,
        issue_number=229,
        change=CHANGE,
        branch=f"agent/{CHANGE}-supersedes-236",
        current_revision=MAIN,
    )


@pytest.mark.parametrize("same_retired_head", (False, True))
def test_supersession_qualifies_only_retired_head_formal_results(
    monkeypatch: pytest.MonkeyPatch,
    same_retired_head: bool,
) -> None:
    """#322: early Change: unset and old malformed results are not retirement gates."""

    old_head = "5" * 40
    old = _continuation_pr(head_sha=old_head)
    old.update(state="closed", merged=False, closed_at="2026-11-03T03:00:00Z")
    replacement = _continuation_pr(number=237, branch=f"agent/{CHANGE}-supersedes-236")
    formal, requests = _accepted_supersession_comments(old_head)
    earlier_head = old_head if same_retired_head else "4" * 40
    historical = {
        "id": 700,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
        "created_at": "2026-09-22T16:52:31Z",
        "body": "\n".join(
            (
                "ACTION_RESULT",
                "Workflow: #229",
                "Change: unset",
                "Role: lead",
                "Action: explore-change",
                "Result: PROPOSAL_READY",
                f"Revision: {earlier_head}",
                f"Default-Branch-Revision: {earlier_head}",
                "Application-Correlation: "
                f"application:699:229:unset:lead:explore-change:proposal-ready:{earlier_head}",
                "Repository-derived successor: Lead / propose-change",
            )
        ),
    }
    legacy = {
        "id": 701,
        "user": {"login": "github-actions[bot]"},
        "performed_via_github_app": {"slug": "github-actions"},
        "created_at": "2026-09-22T17:52:19Z",
        "body": "\n".join(
            (
                "ACTION_RESULT",
                "Workflow: #229",
                "Change: unset",
                "Role: lead",
                "Action: propose-change",
                "Result: READY_FOR_OPENSPEC_REVIEW",
                f"Revision: {'3' * 40}",
                f"Default-Branch-Revision: {'3' * 40}",
                "Evidence: Legacy formal record without Application-Correlation",
            )
        ),
    }
    github = _fake_github(
        current_pr=replacement,
        merged_continuations=[old],
        open_prs=[replacement],
        formal_comments=[historical, legacy, *formal],
        request_comments=requests,
        routing_timeline=_supersession_routing_timeline(),
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    assert (
        carrier.qualify_supersession_branch(
            repository=REPOSITORY,
            token=TEST_VALUE,
            issue_number=229,
            change=CHANGE,
            branch=f"agent/{CHANGE}-supersedes-236",
            current_revision=MAIN,
        )
        is not same_retired_head
    )


@pytest.mark.parametrize(
    ("malformation", "expected"),
    [
        ("duplicate-retired-head", False),
        ("malformed-retired-head", False),
        ("duplicate-unrelated-heads", True),
    ],
)
def test_supersession_rejects_ambiguous_formal_revision_claiming_retired_head(
    monkeypatch: pytest.MonkeyPatch,
    malformation: str,
    expected: bool,
) -> None:
    """Malformed claims naming retired HEAD fail closed; unrelated history remains isolated."""

    old_head = "5" * 40
    retired = _continuation_pr(head_sha=old_head)
    retired.update(state="closed", merged=False, closed_at="2026-11-03T03:00:00Z")
    replacement = _continuation_pr(number=237, branch=f"agent/{CHANGE}-supersedes-236")
    formal, requests = _accepted_supersession_comments(old_head)

    malformed = dict(formal[1])
    malformed["id"] = 902
    malformed["created_at"] = "2026-11-03T02:30:00Z"
    revision_lines = {
        "duplicate-retired-head": f"Revision: {old_head}\nRevision: {'4' * 40}",
        "malformed-retired-head": f"Revision: `{old_head}` (ambiguous)",
        "duplicate-unrelated-heads": f"Revision: {'4' * 40}\nRevision: {'3' * 40}",
    }[malformation]
    malformed["body"] = cast(str, malformed["body"]).replace(
        f"Revision: {old_head}", revision_lines, 1
    )

    github = _fake_github(
        current_pr=replacement,
        merged_continuations=[retired],
        open_prs=[replacement],
        formal_comments=[*formal, malformed],
        request_comments=requests,
        routing_timeline=_supersession_routing_timeline(),
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    assert (
        carrier.qualify_supersession_branch(
            repository=REPOSITORY,
            token=TEST_VALUE,
            issue_number=229,
            change=CHANGE,
            branch=f"agent/{CHANGE}-supersedes-236",
            current_revision=MAIN,
        )
        is expected
    )


@pytest.mark.parametrize("tamper_accepted_effect", (False, True))
def test_supersession_preserves_accepted_intent_semantics_across_nested_json_serialization(
    monkeypatch: pytest.MonkeyPatch,
    tamper_accepted_effect: bool,
) -> None:
    """#322 regression: real ACCEPTED intent reformatted inner payload_json strings."""

    old_head = "5" * 40
    old = _continuation_pr(head_sha=old_head)
    old.update(state="closed", merged=False, closed_at="2026-11-03T03:00:00Z")
    replacement = _continuation_pr(number=237, branch=f"agent/{CHANGE}-supersedes-236")
    formal, requests = _accepted_supersession_comments(
        old_head,
        reformat_accepted_effects=True,
        tamper_accepted_effect=tamper_accepted_effect,
    )
    github = _fake_github(
        current_pr=replacement,
        merged_continuations=[old],
        open_prs=[replacement],
        formal_comments=formal,
        request_comments=requests,
        routing_timeline=_supersession_routing_timeline(),
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    assert (
        carrier.qualify_supersession_branch(
            repository=REPOSITORY,
            token=TEST_VALUE,
            issue_number=229,
            change=CHANGE,
            branch=f"agent/{CHANGE}-supersedes-236",
            current_revision=MAIN,
        )
        is not tamper_accepted_effect
    )


@pytest.mark.parametrize(
    "invalid_provenance",
    ("unaccepted", "tampered-request", "foreign-actor", "wrong-retired-pr", "missing-decision"),
)
def test_supersession_rejects_decision_or_ingress_without_exact_causal_binding(
    monkeypatch: pytest.MonkeyPatch, invalid_provenance: str
) -> None:
    old_head = "5" * 40
    old = _continuation_pr(head_sha=old_head)
    old.update(state="closed", merged=False, closed_at="2026-11-03T03:00:00Z")
    replacement = _continuation_pr(number=237, branch=f"agent/{CHANGE}-supersedes-236")
    formal, requests = _accepted_supersession_comments(
        old_head, carrier_number=999 if invalid_provenance == "wrong-retired-pr" else 236
    )
    if invalid_provenance == "unaccepted":
        formal[2]["body"] = cast(str, formal[2]["body"]).replace(
            "Disposition: ACCEPTED", "Disposition: REJECTED"
        )
    elif invalid_provenance == "tampered-request":
        requests[1000]["body"] = f"{requests[1000]['body']}\n"
    elif invalid_provenance == "foreign-actor":
        requests[1000]["user"] = {"login": "untrusted-user"}
    elif invalid_provenance == "missing-decision":
        formal.pop(2)
    github = _fake_github(
        current_pr=replacement,
        merged_continuations=[old],
        open_prs=[replacement],
        formal_comments=formal,
        request_comments=requests,
        routing_timeline=_supersession_routing_timeline(),
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    assert not carrier.qualify_supersession_branch(
        repository=REPOSITORY,
        token=TEST_VALUE,
        issue_number=229,
        change=CHANGE,
        branch=f"agent/{CHANGE}-supersedes-236",
        current_revision=MAIN,
    )


def test_merged_supersession_becomes_immutable_historical_lineage_for_finalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_head = "5" * 40
    retired = _continuation_pr(head_sha=old_head)
    retired.update(state="closed", merged=False, closed_at="2026-11-03T03:00:00Z")
    replacement = _continuation_pr(number=237, branch=f"agent/{CHANGE}-supersedes-236")
    replacement.update(
        state="closed",
        merged=True,
        merged_at="2026-11-03T04:00:00Z",
        merge_commit_sha="7" * 40,
    )
    accepted_comments, requests = _accepted_supersession_comments(old_head)
    github = _fake_github(
        current_pr=replacement,
        merged_continuations=[retired],
        open_prs=[],
        formal_comments=accepted_comments,
        routing_timeline=_supersession_routing_timeline(),
        request_comments=requests,
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    historical = carrier._historical_carriers(
        REPOSITORY,
        TEST_VALUE,
        issue_number=229,
        change=CHANGE,
        default_branch="main",
        default_revision=MAIN,
        read=github,
    )
    assert historical is not None
    assert [number for number, _pr in historical] == [232, 237]
    decision = carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=WorkerRequest(229, "executor", "merge-implementation-pr"),
        change=CHANGE,
        pr_number=237,
        current_revision=MAIN,
    )
    assert decision.disposition == "HISTORICAL_MERGED", decision.reason


@pytest.mark.parametrize(
    "invalid_evidence",
    [
        "missing-routing",
        "manual-routing",
        "closed-before-findings",
        "wrong-ready-head",
        "wrong-issue",
        "draft-retired",
        "duplicate-retired",
        "competing-open",
    ],
)
def test_supersession_fails_closed_for_unqualified_review_or_retirement(
    monkeypatch: pytest.MonkeyPatch, invalid_evidence: str
) -> None:
    old_head = "5" * 40
    old_pr = _continuation_pr(head_sha=old_head)
    old_pr.update(
        state="closed",
        merged=False,
        closed_at="2026-11-03T03:00:00Z",
    )
    new_pr = _continuation_pr(number=237, branch=f"agent/{CHANGE}-supersedes-236")
    formal, requests = _accepted_supersession_comments(old_head)
    timeline = _supersession_routing_timeline()
    continuations = [old_pr]
    opens = [new_pr]
    if invalid_evidence == "missing-routing":
        timeline.clear()
    elif invalid_evidence == "manual-routing":
        timeline[1]["actor"] = {"login": "royhsu-work"}
    elif invalid_evidence == "closed-before-findings":
        old_pr["closed_at"] = "2026-11-03T01:30:00Z"
    elif invalid_evidence == "wrong-ready-head":
        formal, requests = _accepted_supersession_comments("6" * 40)
    elif invalid_evidence == "wrong-issue":
        old_pr["body"] = "Refs #888"
    elif invalid_evidence == "draft-retired":
        old_pr["draft"] = True
    elif invalid_evidence == "duplicate-retired":
        duplicate = _continuation_pr(number=238, head_sha="6" * 40)
        duplicate.update(state="closed", merged=False, closed_at=old_pr["closed_at"])
        continuations.append(duplicate)
    else:
        competitor = _continuation_pr(number=239, head_sha="6" * 40)
        opens.append(competitor)
    github = _fake_github(
        current_pr=new_pr,
        merged_continuations=continuations,
        open_prs=opens,
        formal_comments=formal,
        routing_timeline=timeline,
        request_comments=requests,
    )
    monkeypatch.setattr(carrier, "_github_json", github)
    result = carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=_source(),
        change=CHANGE,
        pr_number=237,
        current_revision=MAIN,
    )
    assert result.disposition == "INDETERMINATE", invalid_evidence


def test_diverged_continuation_is_recognized_only_for_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(monkeypatch, _fake_github(default_is_ancestor=False))
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-current-integration-evidence-unavailable"
    assert not decision.recognized
    assert not decision.qualified


def test_confirmed_git_conflict_is_not_confused_with_plain_divergence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _continuation_pr()
    current["mergeable"] = False
    decision = _qualify(
        monkeypatch,
        _fake_github(current_pr=current, open_prs=[current], default_is_ancestor=False),
    )
    assert decision.disposition == "RECONCILIATION_REQUIRED"
    assert decision.reason == "carrier-confirmed-git-merge-conflict"


@pytest.mark.parametrize(
    ("head_paths", "main_paths", "mergeable", "expected"),
    [
        (["src/work.py"], ["docs/readme.md"], True, True),
        (["src/work.py"], ["src/work.py"], True, False),
        (["src/work.py"], ["docs/readme.md"], False, False),
        (["src/work.py"], ["docs/readme.md"], None, False),
    ],
)
def test_diverged_mergeability_requires_complete_disjoint_git_proof(
    head_paths: list[str], main_paths: list[str], mergeable: bool | None, expected: bool
) -> None:
    """Same-file changes are not *assumed* to conflict; they require reconciliation."""

    base = "a" * 40
    responses: dict[str, object] = {
        f"compare/{HEAD}...{MAIN}": {"status": "diverged", "merge_base_commit": {"sha": base}},
        f"compare/{base}...{HEAD}": {
            "status": "ahead",
            "behind_by": 0,
            "files": [{"filename": path} for path in head_paths],
        },
        f"compare/{base}...{MAIN}": {
            "status": "ahead",
            "behind_by": 0,
            "files": [{"filename": path} for path in main_paths],
        },
    }

    def read(_repo: str, _token: str, path: str) -> object | None:
        return responses.get(path)

    assert (
        carrier._disjoint_divergence_is_mergeable(
            REPOSITORY,
            TEST_VALUE,
            pr={"mergeable": mergeable},
            head_sha=HEAD,
            default_revision=MAIN,
            read=read,
        )
        is expected
    )


def test_divergence_does_not_treat_truncated_or_unavailable_evidence_as_safe() -> None:
    base = "a" * 40

    def read(_repo: str, _token: str, path: str) -> object | None:
        if path == f"compare/{HEAD}...{MAIN}":
            return {"status": "diverged", "merge_base_commit": {"sha": base}}
        if path == f"compare/{base}...{MAIN}":
            return {"status": "ahead", "behind_by": 0, "files": [{"filename": "a"}] * 300}
        if path == f"compare/{base}...{HEAD}":
            return {"status": "ahead", "behind_by": 0, "files": [{"filename": "b"}]}
        return None

    assert not carrier._disjoint_divergence_is_mergeable(
        REPOSITORY,
        TEST_VALUE,
        pr={"mergeable": True},
        head_sha=HEAD,
        default_revision=MAIN,
        read=read,
    )


@pytest.mark.parametrize(
    ("mergeable", "drop_compare", "expected"),
    [
        (None, None, "INDETERMINATE"),
        (True, "merge-base", "INDETERMINATE"),
        (True, "main-paths", "INDETERMINATE"),
        (True, None, "RECONCILIATION_REQUIRED"),
        (False, None, "RECONCILIATION_REQUIRED"),
    ],
)
def test_diverged_carrier_final_classification_preserves_unknown_git_evidence(
    monkeypatch: pytest.MonkeyPatch,
    mergeable: bool | None,
    drop_compare: str | None,
    expected: str,
) -> None:
    current = _continuation_pr(branch=f"agent/{CHANGE}")
    current["mergeable"] = mergeable
    base = "a" * 40
    fake = _fake_github(
        current_pr=current,
        historical_pr=None,
        open_prs=[current],
        default_is_ancestor=False,
        pr_files=[{"filename": f"openspec/changes/{CHANGE}/proposal.md"}],
    )

    def read(repo: str, token: str, path: str, **kwargs: object) -> object | None:
        if path == f"compare/{HEAD}...{MAIN}":
            if drop_compare == "merge-base":
                return None
            return {"status": "diverged", "merge_base_commit": {"sha": base}}
        if path == f"compare/{base}...{HEAD}":
            return {"status": "ahead", "behind_by": 0, "files": [{"filename": "a.py"}]}
        if path == f"compare/{base}...{MAIN}":
            if drop_compare == "main-paths":
                return {"status": "ahead", "behind_by": 0, "files": [{"filename": "x"}] * 300}
            return {"status": "ahead", "behind_by": 0, "files": [{"filename": "a.py"}]}
        return fake(repo, token, path, **kwargs)

    decision = _qualify(monkeypatch, read)
    assert decision.disposition == expected, decision.reason
    assert decision.recovery_classification == (
        "INDETERMINATE" if expected == "INDETERMINATE" else "RECOVERABLE"
    )


@pytest.mark.parametrize(
    ("disposition", "reason", "classification"),
    [
        ("QUALIFIED", "carrier-qualified", "RECOVERABLE"),
        ("RECONCILIATION_REQUIRED", "carrier-confirmed-git-merge-conflict", "RECOVERABLE"),
        ("INDETERMINATE", "carrier-default-revision-stale", "INDETERMINATE"),
        ("INDETERMINATE", "carrier-competing-open-carrier", "UNSAFE"),
    ],
)
def test_carrier_diagnostics_have_three_non_authorizing_recovery_classes(
    disposition: carrier.CarrierDisposition, reason: str, classification: str
) -> None:
    decision = carrier.ImplementationCarrierQualification(
        disposition=disposition,
        reason=reason,
        repository=REPOSITORY,
        issue_number=229,
        change=CHANGE,
        action="merge-implementation-pr",
        pr_number=236,
    )
    assert decision.recovery_classification == classification
    assert not decision.qualified or disposition == "QUALIFIED"


@pytest.mark.parametrize("initial", [False, True])
def test_qualified_carrier_survives_disjoint_mergeable_main_advance(
    monkeypatch: pytest.MonkeyPatch, initial: bool
) -> None:
    current = _continuation_pr(branch=f"agent/{CHANGE}" if initial else None)
    current["mergeable"] = True
    base = "a" * 40
    default_fake = _fake_github(
        current_pr=current,
        historical_pr=None if initial else _DEFAULT_HISTORICAL,
        open_prs=[current],
        default_is_ancestor=False,
        pr_files=[{"filename": f"openspec/changes/{CHANGE}/tasks.md"}],
    )

    def read(repo: str, token: str, path: str, **kwargs: object) -> object | None:
        if path == f"compare/{HEAD}...{MAIN}":
            return {"status": "diverged", "merge_base_commit": {"sha": base}}
        if path == f"compare/{base}...{HEAD}":
            return {
                "status": "ahead",
                "behind_by": 0,
                "files": [{"filename": f"openspec/changes/{CHANGE}/tasks.md"}],
            }
        if path == f"compare/{base}...{MAIN}":
            return {"status": "ahead", "behind_by": 0, "files": [{"filename": "docs/a.md"}]}
        return default_fake(repo, token, path, **kwargs)

    monkeypatch.setattr(carrier, "_github_json", read)
    decision = carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=_source("merge-implementation-pr"),
        change=CHANGE,
        pr_number=236,
        current_revision=MAIN,
    )
    assert decision.qualified
    assert decision.head_sha == HEAD
    assert decision.reason == "carrier-qualified-after-disjoint-mergeable-default-advance"


@pytest.mark.parametrize(
    "branch",
    [
        f"agent/{CHANGE}-continuation-999",
        f"agent/{CHANGE}-continuation-232-copy",
        "agent/arbitrary",
    ],
)
def test_arbitrary_or_wrong_continuation_branch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    branch: str,
) -> None:
    current = _continuation_pr(branch=branch)
    decision = _qualify(
        monkeypatch,
        _fake_github(current_pr=current, open_prs=[current]),
    )
    assert decision.disposition == "INDETERMINATE"


def test_missing_historical_carrier_rejects_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(monkeypatch, _fake_github(historical_pr=None))
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "initial-carrier-branch-is-not-canonical"


def test_nonancestor_historical_merge_rejects_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(historical_is_ancestor=False),
    )
    assert decision.disposition == "INDETERMINATE"


def test_multiple_claimed_continuation_carriers_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _continuation_pr()
    competitor = _continuation_pr(
        number=237,
        branch=f"agent/{CHANGE}-continuation-233",
        head_sha="5" * 40,
    )
    decision = _qualify(
        monkeypatch,
        _fake_github(current_pr=current, open_prs=[current, competitor]),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-competing-open-carrier"


def test_pr_ref_head_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(branch_ref_sha="6" * 40),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-pr-ref-head-mismatch"


def test_competing_active_change_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(
            pr_files=[
                {"filename": "src/investment_strategy/example.py"},
                {"filename": "openspec/changes/other-change/tasks.md"},
            ]
        ),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-competing-active-change"


def test_stale_default_revision_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(default_revision="7" * 40),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-default-revision-stale"


def test_stale_open_continuation_carrier_is_reconcilable_but_not_qualified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _continuation_pr()
    current["base"] = {"ref": "main", "sha": "7" * 40, "repo": _repo()}
    decision = _qualify(
        monkeypatch,
        _fake_github(current_pr=current, open_prs=[current], default_is_ancestor=False),
    )
    assert decision.disposition == "INDETERMINATE"
    assert not decision.recognized
    assert not decision.qualified
    assert decision.reason == "carrier-current-integration-evidence-unavailable"


def test_reconciled_continuation_branch_qualifies_even_if_pr_base_sha_is_old(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _continuation_pr()
    current["base"] = {"ref": "main", "sha": "7" * 40, "repo": _repo()}
    decision = _qualify(
        monkeypatch,
        _fake_github(current_pr=current, open_prs=[current], default_is_ancestor=True),
    )
    assert decision.disposition == "QUALIFIED"
    assert decision.recognized
    assert decision.reason == "continuation-carrier-qualified-after-reconciliation"


def test_stale_open_initial_carrier_enters_reconciliation_only_with_ancestral_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _continuation_pr(branch=f"agent/{CHANGE}")
    current["base"] = {"ref": "main", "sha": "7" * 40, "repo": _repo()}
    decision = _qualify(
        monkeypatch,
        _fake_github(
            current_pr=current,
            historical_pr=None,
            open_prs=[current],
            pr_files=[{"filename": f"openspec/changes/{CHANGE}/proposal.md"}],
            default_advance_files=[
                {"filename": f"openspec/changes/{CHANGE}/proposal.md"},
            ],
        ),
    )
    assert decision.disposition == "RECONCILIATION_REQUIRED"
    assert decision.reason == "initial-carrier-requires-default-reconciliation"


def test_wrong_issue_link_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _continuation_pr(issue_number=230)
    decision = _qualify(
        monkeypatch,
        _fake_github(current_pr=current, open_prs=[current]),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-pr-identity-incoherent"


def test_competing_change_in_issue_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(issue_body="Change: another-change\n"),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-issue-change-incoherent"


def test_historical_carrier_is_recognized_from_current_default_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical = _historical_pr()
    monkeypatch.setattr(
        carrier,
        "_github_json",
        _fake_github(
            current_pr=historical,
            historical_pr=historical,
            open_prs=[],
            branch_ref_sha=HISTORICAL_HEAD,
        ),
    )
    decision = carrier.qualify_implementation_carrier(
        repository=REPOSITORY,
        token=TEST_VALUE,
        source=_source(),
        change=CHANGE,
        pr_number=232,
        current_revision=MAIN,
    )
    assert decision.disposition == "HISTORICAL_MERGED"
    assert decision.historical_pr_number == 232


def test_merged_deterministic_continuation_is_recognized_from_default_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    continuation = _continuation_pr()
    continuation.update(
        {
            "state": "closed",
            "merged": True,
            "merged_at": "2026-09-13T00:00:00Z",
            "merge_commit_sha": CONTINUATION_MERGE,
        }
    )
    decision = _qualify(
        monkeypatch,
        _fake_github(
            current_pr=continuation,
            open_prs=[],
            branch_ref_sha=None,
        ),
    )
    assert decision.disposition == "HISTORICAL_MERGED"
    assert decision.reason == "merged-continuation-carrier-qualified"
    assert decision.branch == f"agent/{CHANGE}-continuation-232"
    assert decision.historical_pr_number == 232


def test_historical_carrier_with_competing_active_change_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _qualify(
        monkeypatch,
        _fake_github(
            historical_files=[
                {"filename": f"openspec/changes/{CHANGE}/proposal.md"},
                {"filename": "openspec/changes/other-change/tasks.md"},
            ]
        ),
    )
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "initial-carrier-branch-is-not-canonical"


@pytest.mark.parametrize(
    ("default_advance_files", "qualified"),
    [
        ([{"filename": "src/investment_strategy/bootstrap.py"}], False),
        ([{"filename": "src/investment_strategy/example.py"}], False),
    ],
)
def test_initial_carrier_does_not_treat_missing_git_proof_as_recoverable(
    monkeypatch: pytest.MonkeyPatch,
    default_advance_files: list[dict[str, object]],
    qualified: bool,
) -> None:
    old_base = "7" * 40
    new_default = "9" * 40
    current = _continuation_pr(branch=f"agent/{CHANGE}")
    current["base"] = {"ref": "main", "sha": old_base, "repo": _repo()}
    decision = _qualify(
        monkeypatch,
        _fake_github(
            current_pr=current,
            historical_pr=None,
            open_prs=[current],
            pr_files=[
                {"filename": f"openspec/changes/{CHANGE}/proposal.md"},
                {"filename": "src/investment_strategy/example.py"},
            ],
            default_is_ancestor=False,
            default_revision=new_default,
            default_advance_files=default_advance_files,
        ),
        current_revision=new_default,
    )
    assert decision.qualified is qualified
    assert decision.disposition == "INDETERMINATE"
    assert decision.reason == "carrier-current-integration-evidence-unavailable"


def test_second_generation_openspec_continuation_uses_latest_merged_predecessor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_continuation = _continuation_pr()
    first_continuation.update(
        {
            "state": "closed",
            "merged": True,
            "merged_at": "2026-09-13T00:00:00Z",
            "merge_commit_sha": CONTINUATION_MERGE,
        }
    )
    next_head = "5" * 40
    current = _continuation_pr(
        number=240,
        branch=carrier.deterministic_continuation_branch(CHANGE, 236),
        head_sha=next_head,
    )
    fake = _fake_github(
        current_pr=current,
        merged_continuations=[first_continuation],
        open_prs=[current],
        pr_files=[{"filename": f"openspec/changes/{CHANGE}/proposal.md"}],
        branch_ref_sha=next_head,
    )
    monkeypatch.setattr(carrier, "_github_json", fake)

    for source in (
        WorkerRequest(229, "lead", "resolve-question"),
        WorkerRequest(229, "reviewer", "review-openspec"),
    ):
        decision = carrier.qualify_change_carrier(
            repository=REPOSITORY,
            token=TEST_VALUE,
            source=source,
            change=CHANGE,
            pr_number=240,
            current_revision=MAIN,
        )
        assert decision.disposition == "QUALIFIED"
        assert decision.branch == carrier.deterministic_continuation_branch(CHANGE, 236)
        assert decision.historical_pr_number == 236
