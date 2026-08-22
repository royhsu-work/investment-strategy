"""Fresh reauthorization and durable-effect boundary for Scheduled Agent work."""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import quote
from urllib.request import Request, urlopen

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


def supported_effect_guard(source: WorkerRequest, effect: StagedEffect) -> bool:
    """Validate the bounded structural effect surface implemented by Slice 4C."""

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
    """Return whether a newly selected action should get a fresh machine wake."""

    return continuation is not None and continuation != source


def _github_json(
    repository: str,
    token: str,
    api_path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
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
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        raw = response.read()
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


class GitHubEffectAdapter:
    """Small production adapter for the initial bounded durable-effect surface."""

    def __init__(self, repository: str, token: str, source: WorkerRequest) -> None:
        self.repository = repository
        self.token = token
        self.source = source
        self._comment_ids: dict[StagedEffect, int] = {}
        self._routing_targets: dict[StagedEffect, tuple[str, str]] = {}

    def _current_issue(self) -> Mapping[str, object] | None:
        payload = _github_json(
            self.repository,
            self.token,
            f"issues/{self.source.issue_number}",
        )
        return payload if isinstance(payload, Mapping) else None

    def guard(self, effect: StagedEffect) -> bool:
        if not supported_effect_guard(self.source, effect):
            return False
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
                _github_json(
                    self.repository,
                    self.token,
                    f"issues/{self.source.issue_number}/labels/{quote(source_action_label, safe='')}",
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

        raise RuntimeError(f"unsupported effect kind: {effect.kind}")

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
