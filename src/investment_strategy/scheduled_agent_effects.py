"""Fresh reauthorization and durable-effect boundary for Scheduled Agent work."""

from __future__ import annotations

import base64
import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_effect_contract import (
    GITHUB_MUTATION_KIND,
    allowed_github_mutation_operations,
)
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    acquire_current_github_preflight,
    normalize_github_issue,
)
from investment_strategy.scheduled_agent_worker import parse_worker_result
from investment_strategy.workflow_dispatch import DispatchPreflight, classify_dispatch


@dataclass(frozen=True)
class StagedEffect:
    """One invocation-local requested durable effect."""

    kind: str
    payload_json: str


@dataclass(frozen=True)
class EffectBatch:
    """Worker output bound to its original machine-authorized source."""

    source: WorkerRequest
    effects: tuple[StagedEffect, ...]


@dataclass(frozen=True)
class ApplyResult:
    """Application outcome plus optional newly dispatched continuation."""

    applied: bool
    reason: str
    continuation: WorkerRequest | None = None


FreshPreflight = Callable[[], DispatchPreflight]
EffectGuard = Callable[[StagedEffect], bool]
EffectApplier = Callable[[StagedEffect], None]
PostconditionObserver = Callable[[StagedEffect], bool]
TopologyValidator = Callable[[WorkerRequest, StagedEffect], bool]

_ROUTING_TOKEN = re.compile(r"`(Lead|Reviewer|Executor) / ([a-z-]+)`")
_ALLOWED_ISSUE_FIELDS = frozenset({"title", "body", "state"})
_ALLOWED_PR_FIELDS = frozenset({"title", "body", "state", "base"})
_ALLOWED_MERGE_METHODS = frozenset({"merge", "squash", "rebase"})


def _authorized_request(preflight: DispatchPreflight) -> WorkerRequest | None:
    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id is None
        or decision.selected_routing is None
    ):
        return None
    role, action = decision.selected_routing
    return WorkerRequest(decision.selected_issue_id, role, action)


def apply_effect_batch(
    batch: EffectBatch,
    *,
    fresh_preflight: FreshPreflight,
    effect_guard: EffectGuard,
    topology_validator: TopologyValidator,
    apply_effect: EffectApplier,
    observe_postcondition: PostconditionObserver,
) -> ApplyResult:
    """Apply one staged batch only after fresh same-source reauthorization."""

    current = _authorized_request(fresh_preflight())
    if current != batch.source:
        return ApplyResult(False, "source dispatch is stale")

    # Validate the complete normal batch before its first durable mutation.
    for effect in batch.effects:
        if not effect_guard(effect):
            return ApplyResult(False, "effect precondition rejected")
        if effect.kind == "routing-transition" and not topology_validator(batch.source, effect):
            return ApplyResult(False, "routing successor rejected")

    for effect in batch.effects:
        apply_effect(effect)
        if not observe_postcondition(effect):
            return ApplyResult(False, "durable postcondition not observed")

    continuation = _authorized_request(fresh_preflight())
    return ApplyResult(True, "applied", continuation)


def parse_effect_batch(raw: str, source: WorkerRequest) -> EffectBatch:
    """Parse same-invocation worker output and bind it to the authorized source."""

    result = parse_worker_result(raw, source)
    effects = tuple(
        StagedEffect(kind=effect.kind, payload_json=effect.payload_json)
        for effect in result.requested_effects
    )
    return EffectBatch(source=source, effects=effects)


def _effect_payload(effect: StagedEffect) -> dict[str, object] | None:
    try:
        decoded = json.loads(effect.payload_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict) or not all(isinstance(key, str) for key in decoded):
        return None
    return cast(dict[str, object], decoded)


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_repo_path(value: object) -> bool:
    if not _is_nonempty_string(value):
        return False
    path = PurePosixPath(cast(str, value))
    return not path.is_absolute() and ".." not in path.parts


def _valid_branch(value: object) -> bool:
    return _is_nonempty_string(value) and not cast(str, value).startswith("refs/")


def _valid_ref(value: object) -> bool:
    if not _is_nonempty_string(value):
        return False
    ref = cast(str, value)
    return ref.startswith("refs/heads/") and ".." not in ref and ref.count("//") == 0


def _valid_fields(value: object, allowed: frozenset[str]) -> bool:
    return (
        isinstance(value, Mapping)
        and bool(value)
        and all(isinstance(key, str) and key in allowed for key in value)
    )


def _github_mutation_structurally_valid(source: WorkerRequest, payload: Mapping[str, object]) -> bool:
    if payload.get("issue_number") != source.issue_number:
        return False
    operation = payload.get("operation")
    if not isinstance(operation, str):
        return False
    if operation not in allowed_github_mutation_operations(source.role, source.action):
        return False

    if operation == "issue-create":
        return (
            _is_nonempty_string(payload.get("title"))
            and isinstance(payload.get("body", ""), str)
            and isinstance(payload.get("labels", []), list)
            and all(isinstance(label, str) and label for label in cast(list[object], payload.get("labels", [])))
        )
    if operation == "issue-update":
        fields = payload.get("fields")
        expected = payload.get("expected")
        return _valid_fields(fields, _ALLOWED_ISSUE_FIELDS) and (
            expected is None or _valid_fields(expected, _ALLOWED_ISSUE_FIELDS)
        )
    if operation == "issue-label-add":
        return _is_nonempty_string(payload.get("label"))
    if operation in {"contents-upsert", "contents-delete"}:
        expected_sha = payload.get("expected_sha")
        base_valid = (
            _valid_repo_path(payload.get("path"))
            and _valid_branch(payload.get("branch"))
            and _is_nonempty_string(payload.get("message"))
            and (expected_sha is None or _is_nonempty_string(expected_sha))
        )
        if not base_valid:
            return False
        if operation == "contents-upsert":
            return isinstance(payload.get("content"), str)
        return _is_nonempty_string(expected_sha)
    if operation == "ref-create":
        return _valid_ref(payload.get("ref")) and _is_nonempty_string(payload.get("sha"))
    if operation in {"ref-update", "ref-delete"}:
        return (
            _valid_ref(payload.get("ref"))
            and _is_nonempty_string(payload.get("expected_sha"))
            and (
                operation == "ref-delete" or _is_nonempty_string(payload.get("sha"))
            )
        )
    if operation == "pull-request-create":
        return (
            _is_nonempty_string(payload.get("title"))
            and isinstance(payload.get("body", ""), str)
            and _valid_branch(payload.get("head"))
            and _valid_branch(payload.get("base"))
            and isinstance(payload.get("draft", False), bool)
        )
    if operation == "pull-request-update":
        return (
            isinstance(payload.get("number"), int)
            and _is_nonempty_string(payload.get("expected_head_sha"))
            and _valid_fields(payload.get("fields"), _ALLOWED_PR_FIELDS)
        )
    if operation == "pull-request-ready":
        return isinstance(payload.get("number"), int) and _is_nonempty_string(
            payload.get("expected_head_sha")
        )
    if operation == "pull-request-merge":
        method = payload.get("merge_method", "merge")
        return (
            isinstance(payload.get("number"), int)
            and _is_nonempty_string(payload.get("expected_head_sha"))
            and isinstance(method, str)
            and method in _ALLOWED_MERGE_METHODS
        )
    return False


def supported_effect_guard(source: WorkerRequest, effect: StagedEffect) -> bool:
    """Validate the bounded structural effect surface used by mapped Skills."""

    payload = _effect_payload(effect)
    if payload is None or payload.get("issue_number") != source.issue_number:
        return False

    if effect.kind == "issue-comment":
        return (
            set(payload) == {"issue_number", "body"}
            and isinstance(payload.get("body"), str)
            and bool(cast(str, payload["body"]).strip())
        )

    if effect.kind == "routing-transition":
        return (
            set(payload) == {"issue_number", "role", "action"}
            and isinstance(payload.get("role"), str)
            and isinstance(payload.get("action"), str)
            and bool(cast(str, payload["role"]).strip())
            and bool(cast(str, payload["action"]).strip())
        )

    if effect.kind == GITHUB_MUTATION_KIND:
        return _github_mutation_structurally_valid(source, payload)

    return False


def _routing_identity(request: WorkerRequest) -> tuple[str, str]:
    return request.role, request.action


def _routing_tokens(line: str) -> tuple[tuple[str, str], ...]:
    return tuple((role.lower(), action) for role, action in _ROUTING_TOKEN.findall(line))


def topology_allows_successor(
    workflow_text: str,
    source: WorkerRequest,
    effect: StagedEffect,
) -> bool:
    """Validate a requested successor by consuming the canonical workflow document."""

    if effect.kind != "routing-transition" or not supported_effect_guard(source, effect):
        return False
    payload = _effect_payload(effect)
    if payload is None:
        return False
    target = (cast(str, payload["role"]), cast(str, payload["action"]))
    source_identity = _routing_identity(source)

    legal_pairs: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    for line in workflow_text.splitlines():
        tokens = _routing_tokens(line)
        if len(tokens) >= 2:
            legal_pairs.update(zip(tokens, tokens[1:], strict=False))
        if "`PROPOSAL_READY`" in line and ("lead", "propose-change") in tokens:
            legal_pairs.add((("lead", "explore-change"), ("lead", "propose-change")))

    return (source_identity, target) in legal_pairs


def continuation_requires_fresh_wake(
    source: WorkerRequest,
    continuation: WorkerRequest | None,
) -> bool:
    """Return whether any authorized post-apply work needs a fresh mapped worker."""

    del source
    return continuation is not None


def _github_json(
    repository: str,
    token: str,
    api_path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
    allow_not_found: bool = False,
) -> object | None:
    url = f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
            raw = response.read()
    except HTTPError as exc:
        if allow_not_found and exc.code == 404:
            return None
        raise
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def _github_graphql(token: str, query: str, variables: Mapping[str, object]) -> object:
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        raw = response.read()
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, Mapping) or decoded.get("errors"):
        raise RuntimeError("GitHub GraphQL mutation failed")
    return decoded


def _shallow_matches(actual: Mapping[str, object], expected: Mapping[str, object]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def _pull_request_head_sha(payload: Mapping[str, object]) -> str | None:
    head = payload.get("head")
    if not isinstance(head, Mapping):
        return None
    sha = head.get("sha")
    return sha if isinstance(sha, str) else None


def _ref_api_path(ref: str) -> str:
    return f"git/ref/{quote(ref.removeprefix('refs/'), safe='/')}"


def _ref_mutation_path(ref: str) -> str:
    return f"git/refs/{quote(ref.removeprefix('refs/'), safe='/')}"


class GitHubEffectAdapter:
    """Production adapter for bounded durable effects requested by mapped workers."""

    def __init__(self, repository: str, token: str, source: WorkerRequest) -> None:
        self.repository = repository
        self.token = token
        self.source = source
        self._comment_ids: dict[StagedEffect, int] = {}
        self._routing_targets: dict[StagedEffect, tuple[str, str]] = {}
        self._created_issue_numbers: dict[StagedEffect, int] = {}
        self._created_pr_numbers: dict[StagedEffect, int] = {}
        self._content_shas: dict[StagedEffect, str] = {}

    def _current_issue(self) -> Mapping[str, object] | None:
        payload = _github_json(
            self.repository,
            self.token,
            f"issues/{self.source.issue_number}",
        )
        return payload if isinstance(payload, Mapping) else None

    def _source_still_current(self) -> bool:
        current = self._current_issue()
        if current is None:
            return False
        observation = normalize_github_issue(current)
        return (
            observation is not None
            and observation.authoritative
            and observation.issue_number == self.source.issue_number
            and observation.routing == _routing_identity(self.source)
        )

    def _guard_github_mutation(self, payload: Mapping[str, object]) -> bool:
        operation = cast(str, payload["operation"])
        if operation == "issue-create" or operation == "issue-label-add":
            return True
        if operation == "issue-update":
            current = self._current_issue()
            if current is None:
                return False
            expected = payload.get("expected")
            return expected is None or (
                isinstance(expected, Mapping) and _shallow_matches(current, expected)
            )
        if operation in {"contents-upsert", "contents-delete"}:
            path = cast(str, payload["path"])
            branch = cast(str, payload["branch"])
            expected_sha = payload.get("expected_sha")
            current = _github_json(
                self.repository,
                self.token,
                f"contents/{quote(path, safe='/')}?{urlencode({'ref': branch})}",
                allow_not_found=True,
            )
            if current is None:
                return expected_sha is None
            return isinstance(current, Mapping) and current.get("sha") == expected_sha
        if operation in {"ref-update", "ref-delete"}:
            ref = cast(str, payload["ref"])
            current = _github_json(self.repository, self.token, _ref_api_path(ref), allow_not_found=True)
            if not isinstance(current, Mapping):
                return False
            obj = current.get("object")
            return isinstance(obj, Mapping) and obj.get("sha") == payload.get("expected_sha")
        if operation == "ref-create":
            ref = cast(str, payload["ref"])
            return (
                _github_json(
                    self.repository,
                    self.token,
                    _ref_api_path(ref),
                    allow_not_found=True,
                )
                is None
            )
        if operation == "pull-request-create":
            head = cast(str, payload["head"])
            base = cast(str, payload["base"])
            head_ref = _github_json(
                self.repository,
                self.token,
                _ref_api_path(f"refs/heads/{head}"),
                allow_not_found=True,
            )
            base_ref = _github_json(
                self.repository,
                self.token,
                _ref_api_path(f"refs/heads/{base}"),
                allow_not_found=True,
            )
            return isinstance(head_ref, Mapping) and isinstance(base_ref, Mapping)
        if operation in {"pull-request-update", "pull-request-ready", "pull-request-merge"}:
            number = cast(int, payload["number"])
            current = _github_json(self.repository, self.token, f"pulls/{number}")
            return (
                isinstance(current, Mapping)
                and _pull_request_head_sha(current) == payload.get("expected_head_sha")
                and current.get("state") == "open"
            )
        return False

    def guard(self, effect: StagedEffect) -> bool:
        if not supported_effect_guard(self.source, effect) or not self._source_still_current():
            return False
        if effect.kind != GITHUB_MUTATION_KIND:
            return True
        payload = _effect_payload(effect)
        return payload is not None and self._guard_github_mutation(payload)

    def _apply_github_mutation(self, effect: StagedEffect, payload: Mapping[str, object]) -> None:
        operation = cast(str, payload["operation"])
        if operation == "issue-create":
            response = _github_json(
                self.repository,
                self.token,
                "issues",
                method="POST",
                payload={
                    "title": cast(str, payload["title"]),
                    "body": cast(str, payload.get("body", "")),
                    "labels": cast(list[object], payload.get("labels", [])),
                },
            )
            if not isinstance(response, Mapping) or not isinstance(response.get("number"), int):
                raise RuntimeError("GitHub issue creation returned no issue number")
            self._created_issue_numbers[effect] = cast(int, response["number"])
            return
        if operation == "issue-update":
            _github_json(
                self.repository,
                self.token,
                f"issues/{self.source.issue_number}",
                method="PATCH",
                payload=cast(Mapping[str, object], payload["fields"]),
            )
            return
        if operation == "issue-label-add":
            _github_json(
                self.repository,
                self.token,
                f"issues/{self.source.issue_number}/labels",
                method="POST",
                payload={"labels": [cast(str, payload["label"])]},
            )
            return
        if operation == "contents-upsert":
            path = cast(str, payload["path"])
            mutation: dict[str, object] = {
                "message": cast(str, payload["message"]),
                "content": base64.b64encode(cast(str, payload["content"]).encode()).decode(),
                "branch": cast(str, payload["branch"]),
            }
            expected_sha = payload.get("expected_sha")
            if isinstance(expected_sha, str):
                mutation["sha"] = expected_sha
            response = _github_json(
                self.repository,
                self.token,
                f"contents/{quote(path, safe='/')}",
                method="PUT",
                payload=mutation,
            )
            if not isinstance(response, Mapping):
                raise RuntimeError("GitHub contents update returned no response")
            content = response.get("content")
            if not isinstance(content, Mapping) or not isinstance(content.get("sha"), str):
                raise RuntimeError("GitHub contents update returned no content sha")
            self._content_shas[effect] = cast(str, content["sha"])
            return
        if operation == "contents-delete":
            path = cast(str, payload["path"])
            _github_json(
                self.repository,
                self.token,
                f"contents/{quote(path, safe='/')}",
                method="DELETE",
                payload={
                    "message": cast(str, payload["message"]),
                    "sha": cast(str, payload["expected_sha"]),
                    "branch": cast(str, payload["branch"]),
                },
            )
            return
        if operation == "ref-create":
            _github_json(
                self.repository,
                self.token,
                "git/refs",
                method="POST",
                payload={"ref": cast(str, payload["ref"]), "sha": cast(str, payload["sha"])},
            )
            return
        if operation == "ref-update":
            _github_json(
                self.repository,
                self.token,
                _ref_mutation_path(cast(str, payload["ref"])),
                method="PATCH",
                payload={"sha": cast(str, payload["sha"]), "force": False},
            )
            return
        if operation == "ref-delete":
            _github_json(
                self.repository,
                self.token,
                _ref_mutation_path(cast(str, payload["ref"])),
                method="DELETE",
            )
            return
        if operation == "pull-request-create":
            response = _github_json(
                self.repository,
                self.token,
                "pulls",
                method="POST",
                payload={
                    "title": cast(str, payload["title"]),
                    "body": cast(str, payload.get("body", "")),
                    "head": cast(str, payload["head"]),
                    "base": cast(str, payload["base"]),
                    "draft": cast(bool, payload.get("draft", False)),
                },
            )
            if not isinstance(response, Mapping) or not isinstance(response.get("number"), int):
                raise RuntimeError("GitHub pull request creation returned no number")
            self._created_pr_numbers[effect] = cast(int, response["number"])
            return
        if operation == "pull-request-update":
            _github_json(
                self.repository,
                self.token,
                f"pulls/{cast(int, payload['number'])}",
                method="PATCH",
                payload=cast(Mapping[str, object], payload["fields"]),
            )
            return
        if operation == "pull-request-ready":
            number = cast(int, payload["number"])
            current = _github_json(self.repository, self.token, f"pulls/{number}")
            if not isinstance(current, Mapping) or not isinstance(current.get("node_id"), str):
                raise RuntimeError("GitHub pull request has no node id for ready transition")
            _github_graphql(
                self.token,
                "mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id})"
                "{pullRequest{isDraft}}}",
                {"id": cast(str, current["node_id"])},
            )
            return
        if operation == "pull-request-merge":
            _github_json(
                self.repository,
                self.token,
                f"pulls/{cast(int, payload['number'])}/merge",
                method="PUT",
                payload={
                    "sha": cast(str, payload["expected_head_sha"]),
                    "merge_method": cast(str, payload.get("merge_method", "merge")),
                },
            )
            return
        raise RuntimeError(f"unsupported GitHub mutation operation: {operation}")

    def apply(self, effect: StagedEffect) -> None:
        payload = _effect_payload(effect)
        if payload is None:
            raise RuntimeError("validated effect payload became unavailable")

        if effect.kind == "issue-comment":
            response = _github_json(
                self.repository,
                self.token,
                f"issues/{self.source.issue_number}/comments",
                method="POST",
                payload={"body": cast(str, payload["body"])},
            )
            if not isinstance(response, Mapping) or not isinstance(response.get("id"), int):
                raise RuntimeError("GitHub comment mutation returned no comment id")
            self._comment_ids[effect] = cast(int, response["id"])
            return

        if effect.kind == "routing-transition":
            target_role = cast(str, payload["role"])
            target_action = cast(str, payload["action"])
            source_role_label = f"agent:{self.source.role}"
            source_action_label = f"action:{self.source.action}"
            target_role_label = f"agent:{target_role}"
            target_action_label = f"action:{target_action}"

            if source_action_label != target_action_label:
                encoded_action_label = quote(source_action_label, safe="")
                _github_json(
                    self.repository,
                    self.token,
                    f"issues/{self.source.issue_number}/labels/{encoded_action_label}",
                    method="DELETE",
                )
            if source_role_label != target_role_label:
                _github_json(
                    self.repository,
                    self.token,
                    f"issues/{self.source.issue_number}/labels/{quote(source_role_label, safe='')}",
                    method="DELETE",
                )

            additions = []
            if source_role_label != target_role_label:
                additions.append(target_role_label)
            if source_action_label != target_action_label:
                additions.append(target_action_label)
            if additions:
                _github_json(
                    self.repository,
                    self.token,
                    f"issues/{self.source.issue_number}/labels",
                    method="POST",
                    payload={"labels": additions},
                )
            self._routing_targets[effect] = (target_role, target_action)
            return

        if effect.kind == GITHUB_MUTATION_KIND:
            self._apply_github_mutation(effect, payload)
            return

        raise RuntimeError(f"unsupported effect kind: {effect.kind}")

    def _observe_github_mutation(self, effect: StagedEffect, payload: Mapping[str, object]) -> bool:
        operation = cast(str, payload["operation"])
        if operation == "issue-create":
            number = self._created_issue_numbers.get(effect)
            if number is None:
                return False
            current = _github_json(self.repository, self.token, f"issues/{number}")
            return (
                isinstance(current, Mapping)
                and current.get("title") == payload.get("title")
                and current.get("body", "") == payload.get("body", "")
            )
        if operation == "issue-update":
            current = self._current_issue()
            fields = payload.get("fields")
            return (
                current is not None
                and isinstance(fields, Mapping)
                and _shallow_matches(current, fields)
            )
        if operation == "issue-label-add":
            current = self._current_issue()
            if current is None:
                return False
            labels = current.get("labels")
            if not isinstance(labels, list):
                return False
            names = {
                item.get("name")
                for item in labels
                if isinstance(item, Mapping) and isinstance(item.get("name"), str)
            }
            return payload.get("label") in names
        if operation == "contents-upsert":
            path = cast(str, payload["path"])
            branch = cast(str, payload["branch"])
            expected_new_sha = self._content_shas.get(effect)
            current = _github_json(
                self.repository,
                self.token,
                f"contents/{quote(path, safe='/')}?{urlencode({'ref': branch})}",
            )
            return (
                expected_new_sha is not None
                and isinstance(current, Mapping)
                and current.get("sha") == expected_new_sha
            )
        if operation == "contents-delete":
            path = cast(str, payload["path"])
            branch = cast(str, payload["branch"])
            return (
                _github_json(
                    self.repository,
                    self.token,
                    f"contents/{quote(path, safe='/')}?{urlencode({'ref': branch})}",
                    allow_not_found=True,
                )
                is None
            )
        if operation in {"ref-create", "ref-update"}:
            ref = cast(str, payload["ref"])
            current = _github_json(self.repository, self.token, _ref_api_path(ref))
            obj = current.get("object") if isinstance(current, Mapping) else None
            return isinstance(obj, Mapping) and obj.get("sha") == payload.get("sha")
        if operation == "ref-delete":
            return (
                _github_json(
                    self.repository,
                    self.token,
                    _ref_api_path(cast(str, payload["ref"])),
                    allow_not_found=True,
                )
                is None
            )
        if operation == "pull-request-create":
            number = self._created_pr_numbers.get(effect)
            if number is None:
                return False
            current = _github_json(self.repository, self.token, f"pulls/{number}")
            if not isinstance(current, Mapping):
                return False
            head = current.get("head")
            base = current.get("base")
            return (
                current.get("title") == payload.get("title")
                and current.get("body", "") == payload.get("body", "")
                and current.get("draft") == payload.get("draft", False)
                and isinstance(head, Mapping)
                and head.get("ref") == payload.get("head")
                and isinstance(base, Mapping)
                and base.get("ref") == payload.get("base")
            )
        if operation == "pull-request-update":
            current = _github_json(
                self.repository,
                self.token,
                f"pulls/{cast(int, payload['number'])}",
            )
            fields = payload.get("fields")
            if not isinstance(current, Mapping) or not isinstance(fields, Mapping):
                return False
            for key, value in fields.items():
                if key == "base":
                    base = current.get("base")
                    if not isinstance(base, Mapping) or base.get("ref") != value:
                        return False
                elif current.get(key) != value:
                    return False
            return _pull_request_head_sha(current) == payload.get("expected_head_sha")
        if operation == "pull-request-ready":
            current = _github_json(
                self.repository,
                self.token,
                f"pulls/{cast(int, payload['number'])}",
            )
            return (
                isinstance(current, Mapping)
                and current.get("draft") is False
                and _pull_request_head_sha(current) == payload.get("expected_head_sha")
            )
        if operation == "pull-request-merge":
            current = _github_json(
                self.repository,
                self.token,
                f"pulls/{cast(int, payload['number'])}",
            )
            return isinstance(current, Mapping) and current.get("merged") is True
        return False

    def observe_postcondition(self, effect: StagedEffect) -> bool:
        if effect.kind == "issue-comment":
            comment_id = self._comment_ids.get(effect)
            payload = _effect_payload(effect)
            if comment_id is None or payload is None:
                return False
            response = _github_json(
                self.repository,
                self.token,
                f"issues/comments/{comment_id}",
            )
            return (
                isinstance(response, Mapping)
                and response.get("body") == payload.get("body")
                and response.get("id") == comment_id
            )

        if effect.kind == "routing-transition":
            target = self._routing_targets.get(effect)
            if target is None:
                return False
            current = self._current_issue()
            if current is None:
                return False
            observation = normalize_github_issue(current)
            return (
                observation is not None
                and observation.authoritative
                and observation.routing == target
            )

        if effect.kind == GITHUB_MUTATION_KIND:
            payload = _effect_payload(effect)
            return payload is not None and self._observe_github_mutation(effect, payload)

        return False


def run_effect_application(
    raw_worker_result: str,
    *,
    source: WorkerRequest,
    repository: str,
    token: str,
    workflow_text: str,
) -> tuple[EffectBatch, ApplyResult]:
    """Freshly reauthorize and apply one invocation-local staged effect batch."""

    batch = parse_effect_batch(raw_worker_result, source)
    adapter = GitHubEffectAdapter(repository, token, source)
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: acquire_current_github_preflight(repository, token),
        effect_guard=adapter.guard,
        topology_validator=lambda request, effect: topology_allows_successor(
            workflow_text,
            request,
            effect,
        ),
        apply_effect=adapter.apply,
        observe_postcondition=adapter.observe_postcondition,
    )
    return batch, result


def _source_from_environment() -> WorkerRequest:
    issue = os.environ.get("AUTHORIZED_ISSUE")
    role = os.environ.get("AUTHORIZED_ROLE")
    action = os.environ.get("AUTHORIZED_ACTION")
    if not issue or not role or not action:
        raise RuntimeError("machine-authorized Issue/role/action environment is required")
    try:
        issue_number = int(issue)
    except ValueError as exc:
        raise RuntimeError("AUTHORIZED_ISSUE must be an integer") from exc
    return WorkerRequest(issue_number=issue_number, role=role, action=action)


def _write_github_outputs(batch: EffectBatch, result: ApplyResult) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    fresh_wake = continuation_requires_fresh_wake(batch.source, result.continuation)
    lines = [
        f"applied={'true' if result.applied else 'false'}",
        f"continuation_required={'true' if fresh_wake else 'false'}",
    ]
    if result.continuation is not None:
        lines.extend(
            (
                f"continuation_issue={result.continuation.issue_number}",
                f"continuation_role={result.continuation.role}",
                f"continuation_action={result.continuation.action}",
            )
        )
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def main() -> int:
    """Apply one same-run worker result through the write-authorized boundary."""

    if len(sys.argv) != 2:
        raise RuntimeError("worker result path argument is required")
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    source = _source_from_environment()
    raw_worker_result = Path(sys.argv[1]).read_text(encoding="utf-8")
    workflow_text = Path("agents/workflow.md").read_text(encoding="utf-8")
    batch, result = run_effect_application(
        raw_worker_result,
        source=source,
        repository=repository,
        token=token,
        workflow_text=workflow_text,
    )
    _write_github_outputs(batch, result)
    print(
        json.dumps(
            {
                "applied": result.applied,
                "reason": result.reason,
                "continuation": (
                    None
                    if result.continuation is None
                    else {
                        "issue_number": result.continuation.issue_number,
                        "role": result.continuation.role,
                        "action": result.continuation.action,
                    }
                ),
            },
            sort_keys=True,
        )
    )
    return 0 if result.applied else 1


if __name__ == "__main__":
    raise SystemExit(main())
