"""One evolving REST observation sequence across merge and fresh application."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

import investment_strategy.native_closing_merge_application as native
import investment_strategy.scheduled_agent_application_bridge as bridge
import investment_strategy.scheduled_agent_application_carrier as carrier
import investment_strategy.scheduled_agent_application_materialization as materialization
import investment_strategy.scheduled_agent_effects as effects
import investment_strategy.scheduled_agent_merge_acceptance as acceptance
import investment_strategy.scheduled_agent_runtime as runtime
import investment_strategy.scheduled_agent_validation_resource as resources
from investment_strategy.scheduled_agent_action_model import (
    Action,
    ResultKind,
    TypedResult,
    next_action,
    role_for,
)
from investment_strategy.scheduled_agent_carrier import CarrierPlan
from investment_strategy.workflow_dispatch import classify_dispatch

REPO = "royhsu-work/investment-strategy"
CHANGE = "qualify-active-formal-consequences"
MAIN = "4422c8b8661cdc8af3ce699d4dbffdd61b86d7b4"
HEAD = "2ea915da35926bbcc155ebca30ae1305d7a2bc5a"
NEW = "e" * 40
BRANCH = f"agent/{CHANGE}-continuation-232"
TASK_BLOB = "f" * 40


class SequenceInterruption(RuntimeError):
    """Fixture process exits after the remote mutation becomes durable."""


class GitHubSequence:
    def __init__(self) -> None:
        fixtures = Path(__file__).parent / "fixtures"
        self.comments = json.loads((fixtures / "issue229-comments.json").read_text())
        self.timeline = json.loads((fixtures / "issue229-timeline.json").read_text())
        self.main = MAIN
        self.action = "merge-implementation-pr"
        self.merged = False
        self.writes: list[tuple[str, str]] = []
        self.clock = 0
        self.requests: dict[int, dict[str, object]] = {}
        self.interrupt_after: str | None = None

    def stamp(self) -> str:
        self.clock += 1
        return f"2026-09-16T00:{self.clock // 60:02d}:{self.clock % 60:02d}Z"

    def issue(self) -> dict[str, object]:
        return {
            "number": 229,
            "state": "open",
            "body": f"Change: {CHANGE}",
            "labels": [{"name": f"action:{self.action}"}] if self.action else [],
            "created_at": "2026-09-08T18:15:57Z",
            "closed_at": None,
        }

    def pr(self, historical: bool = False) -> dict[str, object]:
        repo = {"full_name": REPO, "owner": {"login": "royhsu-work"}}
        return {
            "number": 232 if historical else 236,
            "state": "closed" if historical or self.merged else "open",
            "merged": historical or self.merged,
            "merged_at": "2026-09-15T00:00:00Z" if historical or self.merged else None,
            "merge_commit_sha": "c" * 40 if historical else NEW if self.merged else None,
            "title": "Implement qualification",
            "body": "Refs #229",
            "draft": False,
            "commits": 1,
            "head": {
                "ref": f"agent/{CHANGE}" if historical else BRANCH,
                "sha": "d" * 40 if historical else HEAD,
                "repo": repo,
            },
            "base": {"ref": "main", "sha": MAIN, "repo": repo},
        }

    def read(
        self,
        _repository: str,
        _token: str,
        path: str = "",
        *,
        method: str = "GET",
        payload: Mapping[str, object] | None = None,
        allow_not_found: bool = False,
    ) -> object:
        parsed = urlsplit(path)
        route = unquote(parsed.path)
        query = parse_qs(parsed.query)
        page = int(query.get("page", ["1"])[0])

        def paged(items: list[object]) -> list[object]:
            return items[(page - 1) * 100 : page * 100]

        if method != "GET":
            self.writes.append((method, route))
            assert payload is not None or method == "DELETE"
            if route == "issues/229/comments" and payload is not None:
                stamp = self.stamp()
                comment = {
                    "id": 10000000000 + self.clock,
                    "body": payload["body"],
                    "created_at": stamp,
                    "updated_at": stamp,
                    "user": {"login": "github-actions[bot]"},
                    "performed_via_github_app": {"slug": "github-actions"},
                }
                self.comments.append(comment)
                self.timeline.append(
                    {"id": comment["id"], "event": "commented", "created_at": stamp}
                )
                if self.interrupt_after == "formal-result" and str(payload["body"]).startswith(
                    "ACTION_RESULT"
                ):
                    self.interrupt_after = None
                    raise SequenceInterruption("after durable formal result")
                return comment
            if route == "issues/229" and method == "PATCH" and payload is not None:
                labels = cast(list[str], payload["labels"])
                target = next(label for label in labels if label.startswith("action:"))
                for event, label in (("unlabeled", f"action:{self.action}"), ("labeled", target)):
                    stamp = self.stamp()
                    self.timeline.append(
                        {
                            "id": 20000000000 + self.clock,
                            "event": event,
                            "created_at": stamp,
                            "label": {"name": label},
                        }
                    )
                self.action = target.removeprefix("action:")
                if self.interrupt_after == "routing":
                    self.interrupt_after = None
                    raise SequenceInterruption("after durable successor routing")
                return self.issue()
            if "/labels" in route:
                stamp = self.stamp()
                if method == "DELETE":
                    label = route.split("/labels/")[1]
                    self.action = ""
                    event = "unlabeled"
                else:
                    assert payload is not None
                    label = cast(list[str], payload["labels"])[0]
                    self.action = label.removeprefix("action:")
                    event = "labeled"
                self.timeline.append(
                    {
                        "id": 20000000000 + self.clock,
                        "event": event,
                        "created_at": stamp,
                        "label": {"name": label},
                    }
                )
                return self.issue()["labels"]
            raise AssertionError(f"unexpected mutation {method} {route}")
        if route == "":
            return {
                "default_branch": "main",
                "allow_merge_commit": True,
                "merge_commit_title": "PR_TITLE",
                "merge_commit_message": "PR_BODY",
            }
        if route == "issues":
            return paged([self.issue()])
        if route == "issues/243":
            return {
                "number": 243,
                "title": "[Agent Runtime] 2026-09-16",
                "labels": [],
                "state": "open",
            }
        if route == "issues/229":
            return self.issue()
        if route == "issues/229/comments":
            return paged(self.comments)
        if route == "issues/229/timeline":
            return paged(self.timeline)
        if route.startswith("issues/comments/"):
            number = int(route.rsplit("/", 1)[1])
            if number in self.requests:
                return self.requests[number]
            return next(c for c in self.comments if c["id"] == int(route.rsplit("/", 1)[1]))
        if route == "pulls/236":
            return self.pr()
        if route == "pulls/232":
            return self.pr(True)
        if route == "pulls":
            if query.get("state") == ["open"]:
                return [] if self.merged else [self.pr()]
            candidates = [self.pr(True)]
            if self.merged:
                candidates.append(self.pr())
            requested_heads = query.get("head")
            if requested_heads:
                _owner, _separator, requested_branch = requested_heads[0].partition(":")
                candidates = [
                    candidate
                    for candidate in candidates
                    if cast(dict[str, object], candidate["head"]).get("ref") == requested_branch
                ]
            return candidates
        if route == "pulls/232/files":
            return [{"filename": f"openspec/changes/{CHANGE}/proposal.md"}]
        if route == "pulls/236/files":
            return [{"filename": "src/investment_strategy/scheduled_agent_formal_qualification.py"}]
        if route == "pulls/236/commits":
            return [{"commit": {"message": "Implement qualification"}}]
        if route.endswith("/check-runs"):
            return {
                "total_count": 1,
                "check_runs": [{"status": "completed", "conclusion": "success"}],
            }
        if route.startswith("commits/"):
            return {"parents": [{"sha": MAIN}]}
        if route.startswith("git/ref/heads/"):
            branch = route.removeprefix("git/ref/heads/")
            if branch == "main":
                return {"object": {"sha": self.main}}
            if branch == BRANCH and not self.merged:
                return {"object": {"sha": HEAD}}
            assert allow_not_found
            return None
        graph = {
            "a" * 40: (),
            "d" * 40: ("a" * 40,),
            "c" * 40: ("a" * 40, "d" * 40),
            MAIN: ("c" * 40,),
            HEAD: (MAIN,),
            NEW: (MAIN, HEAD),
        }

        def lineage(revision: str) -> list[str]:
            ordered: list[str] = []

            def visit(sha: str) -> None:
                for parent in graph[sha]:
                    visit(parent)
                if sha not in ordered:
                    ordered.append(sha)

            visit(revision)
            return ordered

        if route.startswith("compare/"):
            old, new = route.removeprefix("compare/").split("...")
            historical_baseline = old not in graph
            if historical_baseline:
                # Historical formal fixture authorizations precede this sequence's main.
                graph[old] = ("a" * 40,)
                graph[MAIN] = (*graph[MAIN], old)
            before, after = lineage(old), lineage(new)
            commits = [sha for sha in after if sha not in before]
            behind = len([sha for sha in before if sha not in after])
            return {
                "base_commit": {"sha": old},
                "merge_base_commit": {"sha": next(sha for sha in reversed(after) if sha in before)},
                "ahead_by": len(commits),
                "behind_by": behind,
                "total_commits": len(commits),
                "status": "diverged"
                if commits and behind
                else "ahead"
                if commits
                else "behind"
                if behind
                else "identical",
                "commits": [
                    {"sha": sha, "parents": [{"sha": p} for p in graph[sha]]} for sha in commits
                ],
                "files": [
                    {
                        "filename": (
                            "src/investment_strategy/scheduled_agent_formal_qualification.py"
                        ),
                        "status": "modified",
                    }
                ]
                if historical_baseline
                else [],
            }
        if route.startswith("git/commits/"):
            sha = route.removeprefix("git/commits/")
            return {
                "sha": sha,
                "message": "Observed fixture commit",
                "tree": {"sha": "9" * 40},
                "parents": [{"sha": p} for p in graph[sha]],
            }
        if route.startswith("git/trees/"):
            return {
                "sha": "9" * 40,
                "truncated": False,
                "tree": [
                    {
                        "path": f"openspec/changes/{CHANGE}/tasks.md",
                        "mode": "100644",
                        "type": "blob",
                        "sha": TASK_BLOB,
                    }
                ],
            }
        if route.startswith("contents/") or route.startswith("git/blobs/"):
            return {
                "sha": TASK_BLOB,
                "type": "file",
                "encoding": "base64",
                "content": base64.b64encode(
                    b"## Slice 2\n- [x] 2.1 Verified implementation\n"
                ).decode(),
            }
        raise AssertionError(f"unexpected read {path}")

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for module in (bridge, native, carrier, materialization, effects, acceptance, resources):
            monkeypatch.setattr(module, "_github_json", self.read)
        prefix = f"https://api.github.com/repos/{REPO}"
        monkeypatch.setattr(
            runtime,
            "_github_get_list_page",
            lambda url, token: tuple(
                cast(
                    list[Mapping[str, object]],
                    self.read(REPO, token, url.removeprefix(prefix).lstrip("/")),
                )
            ),
        )
        monkeypatch.setattr(
            runtime,
            "_github_get_object",
            lambda url, token: self.read(REPO, token, url.removeprefix(prefix).lstrip("/")),
        )

    def apply_local(
        self,
        kind: str,
        request_id: int,
        extra: list[dict[str, str]] | None = None,
        validation_passed: bool = False,
    ) -> effects.ApplyResult:
        if kind == "continue-accepted":
            decisions = [
                c
                for c in self.comments
                if (record := effects.parse_application_decision(c["body"])) is not None
                and record.request_comment_id == request_id
                and record.disposition == "ACCEPTED"
            ]
            assert len(decisions) == 1
            body = bridge.render_application_continuation_request(
                repository=REPO,
                issue_number=229,
                original_request_comment_id=request_id,
                accepted_decision_sha256=hashlib.sha256(decisions[0]["body"].encode()).hexdigest(),
                predecessor_run_id=8001,
                predecessor_run_attempt=1,
                predecessor_job_id=8002,
                predecessor_artifact_id=8003,
                predecessor_artifact_digest="sha256:" + "1" * 64,
                failure_evidence_sha256="2" * 64,
                recovery_episode_sha256="3" * 64,
            )
            event_comment_id = request_id + 1000000
            self.requests[event_comment_id] = {
                "id": event_comment_id,
                "body": body,
                "user": {"login": "royhsu-work"},
                "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
            }
        else:
            decision = classify_dispatch(runtime.acquire_current_github_preflight(REPO, "test"))
            assert decision.disposition == "AUTHORIZE", decision
            assert decision.selected_routing is not None
            role, action = decision.selected_routing
            model_action = Action(action)
            successor = next_action(model_action, TypedResult(ResultKind(kind)))
            marker = (
                "REVIEW_RESULT"
                if action.startswith("review-")
                else "MERGE_RESULT"
                if action.startswith("merge-")
                else "ACTION_RESULT"
            )
            body = (
                f"{marker}\nWorkflow: #229\nChange: {CHANGE}\nAction: {action}\nRole: {role}"
                f"\nResult: {kind.upper().replace('-', '_')}\nRevision: {HEAD}"
                f"\nDefault-Branch-Revision: {self.main}"
            )
            body += "\nApplication-Correlation: pending"
            if successor is not None:
                body += (
                    f"\nRepository-derived successor: {role_for(successor).value.title()}"
                    f" / {successor.value}"
                )
            requested = [] if extra is None else list(extra)
            requested.append(
                {
                    "kind": "issue-comment",
                    "payload_json": json.dumps({"issue_number": 229, "body": body}),
                }
            )
            raw = json.dumps(
                {
                    "issue_number": 229,
                    "role": role,
                    "action": action,
                    "change": CHANGE,
                    "result_kind": kind,
                    "result_content": body,
                    "evidence_ref": "sequence-test",
                    "requested_effects": requested,
                }
            )
            request_body = (
                f"EFFECT_REQUEST\nAuthorization-Revision: {self.main}\nWorker-Result-B64: "
                + base64.b64encode(raw.encode()).decode()
            )
            self.requests[request_id] = {
                "id": request_id,
                "body": request_body,
                "user": {"login": "royhsu-work"},
                "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
            }
            event_comment_id = request_id
        event = {
            "action": "created",
            "issue": self.read(REPO, "test", "issues/243"),
            "comment": self.requests[event_comment_id],
        }
        with tempfile.TemporaryDirectory() as directory, pytest.MonkeyPatch.context() as patch:
            self.install(patch)
            event_path = Path(directory) / "event.json"
            output_path = Path(directory) / "outputs"
            event_path.write_text(json.dumps(event))
            patch.setenv("GITHUB_REPOSITORY", REPO)
            patch.setenv("GITHUB_TOKEN", "test")
            patch.setenv("GITHUB_OUTPUT", str(output_path))
            patch.setattr(
                sys,
                "argv",
                [
                    "bridge",
                    "--event-path",
                    str(event_path),
                    "--revision",
                    self.main,
                    "--default-branch",
                    "main",
                ]
                + (
                    ["--validation-passed", "--validated-revision", HEAD]
                    if validation_passed
                    else []
                ),
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                bridge.main()
            observed = json.loads(output.getvalue().splitlines()[-1])
            plan = None
            if observed.get("carrier_required"):
                fields = dict(line.split("=", 1) for line in output_path.read_text().splitlines())
                plan = json.loads(base64.b64decode(fields["carrier_plan_b64"]))
                # Serialization includes schema, while the runtime value is typed.
                plan.pop("schema", None)
                plan = CarrierPlan(**plan)
            return effects.ApplyResult(
                observed["applied"], observed.get("reason"), carrier_plan=plan
            )

    def apply(
        self,
        kind: str,
        request_id: int,
        extra: list[dict[str, str]] | None = None,
        validation_passed: bool = False,
    ) -> effects.ApplyResult:
        # Each wake is a fresh Python process. Only the emulated remote REST state
        # survives; no adapter cache, imported module state or local receipt does.
        command = [sys.executable, "-m", "tests.test_scheduled_agent_delivery_sequence"]
        result = subprocess.run(  # noqa: S603 - fixed local test module, no shell
            command,
            input=json.dumps(
                {
                    "state": self.__dict__,
                    "kind": kind,
                    "request_id": request_id,
                    "extra": extra,
                    "validation_passed": validation_passed,
                }
            ),
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONPATH": str(Path.cwd() / "src")},
        )
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        self.__dict__.update(output["state"])
        self.requests = {int(key): value for key, value in self.requests.items()}
        value = output["result"]
        plan = None if value["carrier_plan"] is None else CarrierPlan(**value["carrier_plan"])
        return effects.ApplyResult(value["applied"], value["reason"], carrier_plan=plan)


@pytest.mark.parametrize("interruption", [None, "formal-result", "routing"])
def test_merge_delivery_and_rereview_use_one_evolving_rest_sequence(
    monkeypatch: pytest.MonkeyPatch,
    interruption: str | None,
) -> None:
    github = GitHubSequence()
    github.install(monkeypatch)
    merge_effect = {
        "kind": "github-mutation",
        "payload_json": json.dumps(
            {
                "issue_number": 229,
                "operation": "pull-request-merge",
                "number": 236,
                "expected_head_sha": HEAD,
                "merge_method": "merge",
            }
        ),
    }
    before = len(github.comments)
    first = github.apply("merged", 100, [merge_effect])
    assert first.carrier_plan is not None, first
    assert len(github.comments) == before + 1
    assert github.writes == [["POST", "issues/229/comments"]]
    assert github.comments[-1]["body"].splitlines()[0] == "APPLICATION_DECISION"
    assert github.action == "merge-implementation-pr"
    # The external actuator observes this exact authorized identity before merge.
    assert first.carrier_plan.requested["expected_head_sha"] == HEAD
    github.merged = True
    github.main = NEW
    # Complete current graph evidence proves the exact already-accepted merge;
    # the fresh process persists only its missing formal result and successor.
    completed_merge = github.apply("merged", 101, [merge_effect])
    assert completed_merge.applied and completed_merge.carrier_plan is None
    assert github.action == "finalize-change"
    assert not any(method == "PUT" for method, _path in github.writes)
    assert github.apply("more-implementation-required", 102).applied
    assert github.action == "implement-change"
    manifest = {
        "operation": "application-materialize",
        "issue_number": 229,
        "expected_change": CHANGE,
        "change": CHANGE,
        "pr_number": 236,
        "branch": BRANCH,
        "base_sha": HEAD,
        "message": "Observe completed task checkpoint",
        "files": [
            {
                "path": f"openspec/changes/{CHANGE}/tasks.md",
                "blob_sha": TASK_BLOB,
                "expected_sha": TASK_BLOB,
            }
        ],
    }
    checkpoint = (
        f"SLICE_CHECKPOINT\nWorkflow: #229\nChange: {CHANGE}\nAction: implement-change"
        f"\nRole: executor\nCompleted-Tasks: 2.1\nRevision: {HEAD}"
        "\nApplication-Correlation: pending\nGate-Evidence: sequence-test"
        "\nRemaining-Approved-Boundary: current-default independent review"
    )
    checkpoint_effects = [
        {"kind": "github-mutation", "payload_json": json.dumps(manifest)},
        {
            "kind": "issue-comment",
            "payload_json": json.dumps({"issue_number": 229, "body": checkpoint}),
        },
    ]
    github.interrupt_after = interruption
    result = github.apply("ready", 104, checkpoint_effects)
    if interruption is not None:
        assert not result.applied and "after durable" in str(result.reason)
        if interruption == "formal-result":
            assert github.action == "implement-change"
            result = github.apply("continue-accepted", 104)
            assert result.applied, result
        formal_results = [
            c
            for c in github.comments
            if c["id"] >= 10000000000
            and c["body"].startswith("ACTION_RESULT")
            and "Action: implement-change" in c["body"]
        ]
        assert len(formal_results) == 1
    else:
        assert result.applied, result
    assert github.action == "review-implementation"
    checkpoints = [
        comment
        for comment in github.comments
        if comment["id"] >= 10000000000 and comment["body"].startswith("SLICE_CHECKPOINT")
    ]
    assert len(checkpoints) == 1
    assert github.apply("pass", 105).applied
    assert github.action == "merge-implementation-pr"
    result = github.apply("merged", 106, [merge_effect])
    assert result.applied and result.carrier_plan is None, result
    assert github.action == "finalize-change"
    assert not any(method == "PUT" or path.startswith("git/") for method, path in github.writes)


if __name__ == "__main__":
    from dataclasses import asdict

    request = json.loads(sys.stdin.read())
    remote = GitHubSequence()
    remote.__dict__.update(request["state"])
    remote.requests = {int(key): value for key, value in remote.requests.items()}
    with pytest.MonkeyPatch.context() as patch:
        remote.install(patch)
        try:
            result = remote.apply_local(
                request["kind"],
                request["request_id"],
                request["extra"],
                request.get("validation_passed", False),
            )
        except SequenceInterruption as error:
            result = effects.ApplyResult(False, str(error))
    print(json.dumps({"state": remote.__dict__, "result": asdict(result)}))
