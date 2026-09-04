"""Fresh reauthorization and durable-effect boundary for Scheduled Agent work."""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_action_model import Action as ModelAction
from investment_strategy.scheduled_agent_action_model import (
    ActionApplicationDecision,
    ActionObservation,
    ActionSource,
    ApplicationRejection,
    BoundedActionResult,
    plan_action_application,
)
from investment_strategy.scheduled_agent_action_model import (
    ObservationProvenance as ModelObservationProvenance,
)
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
from investment_strategy.workflow_dispatch import (
    DispatchPreflight,
    ObservationProvenance,
    classify_dispatch,
)


@dataclass(frozen=True)
class StagedEffect:
    """One invocation-local requested durable effect."""

    kind: str
    payload_json: str
    derived: bool = False


@dataclass(frozen=True)
class EffectBatch:
    """Worker output bound to its original machine-authorized source."""

    source: WorkerRequest
    effects: tuple[StagedEffect, ...]
    typed_result: BoundedActionResult | None = None


@dataclass(frozen=True)
class ApplyResult:
    """Application outcome for one wake; successors are persisted, never executed here."""

    applied: bool
    reason: str
    rejection: ApplicationRejection | None = None


FreshPreflight = Callable[[], DispatchPreflight]
EffectGuard = Callable[[StagedEffect], bool]
EffectApplier = Callable[[StagedEffect], None]
PostconditionObserver = Callable[[StagedEffect], bool]


def parse_effect_batch(raw: str, source: WorkerRequest) -> EffectBatch:
    """Parse one structured worker result and bind its requested effects."""

    result = parse_worker_result(raw, source)
    return EffectBatch(
        source=source,
        effects=tuple(
            StagedEffect(kind=effect.kind, payload_json=effect.payload_json)
            for effect in result.requested_effects
        ),
        typed_result=result.typed_result,
    )


def _effect_payload(effect: StagedEffect) -> dict[str, object] | None:
    try:
        decoded = json.loads(effect.payload_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict) or not all(isinstance(key, str) for key in decoded):
        return None
    return cast(dict[str, object], decoded)


def _typed_successor_effect_matches(
    effect: StagedEffect,
    decision: ActionApplicationDecision,
) -> bool:
    if not effect.derived or decision.successor is None:
        return False
    return _effect_payload(effect) == {
        "issue_number": decision.source.issue_number,
        "action": decision.successor.value,
    }


def _typed_terminal_effect_matches(
    effect: StagedEffect,
    decision: ActionApplicationDecision,
) -> bool:
    if not effect.derived or decision.successor is not None:
        return False
    return _effect_payload(effect) == {
        "issue_number": decision.source.issue_number,
        "expected_change": decision.source.change,
    }


def _typed_application_plan(
    batch: EffectBatch,
    preflight: DispatchPreflight,
    current_revision: str | None,
) -> tuple[ActionApplicationDecision | None, StagedEffect | None, ApplyResult | None]:
    typed_result = batch.typed_result
    if typed_result is None:
        return None, None, ApplyResult(False, "typed application rejected:result-missing")
    transition_kinds = {"routing-transition", "terminal-transition"}
    if any(effect.kind in transition_kinds for effect in batch.effects):
        return None, None, ApplyResult(False, "typed application rejected:worker-transition-effect")
    if current_revision is None or not re.fullmatch(r"[0-9a-f]{40}", current_revision):
        return None, None, ApplyResult(False, "typed application rejected:revision-unavailable")

    try:
        action = ModelAction(batch.source.action)
        source = ActionSource(
            issue_number=batch.source.issue_number,
            change=typed_result.change,
            action=action,
            authorization_revision=current_revision,
        )
    except ValueError:
        return None, None, ApplyResult(False, "typed application rejected:source-action-invalid")

    selected = classify_dispatch(preflight)
    if (
        selected.disposition != "AUTHORIZE"
        or selected.selected_issue_id != source.issue_number
        or selected.selected_routing is None
        or selected.selected_routing[1] != source.action.value
    ):
        return None, None, ApplyResult(False, "typed application rejected:model-selection")

    matching_issues = tuple(
        issue for issue in preflight.issues if issue.issue_number == source.issue_number
    )
    if len(matching_issues) != 1:
        return None, None, ApplyResult(False, "typed application rejected:current-issue")
    issue = matching_issues[0]
    current_action = None if issue.routing is None else issue.routing[1]
    current = ActionObservation(
        issue_number=issue.issue_number,
        change=issue.change,
        action=current_action,
        revision=current_revision,
        provenance=(
            ModelObservationProvenance.QUALIFIED
            if issue.current_state_provenance is ObservationProvenance.QUALIFIED
            else ModelObservationProvenance.INDETERMINATE
        ),
        human_authorized=preflight.human_authorized,
        state=issue.state,
    )
    decision = plan_action_application(source, typed_result, current)
    if not decision.accepted:
        rejection = decision.rejection
        classification = "unknown"
        if rejection is not None:
            classification = rejection.classification.value
        return (
            decision,
            None,
            ApplyResult(
                False,
                f"typed application rejected:{classification}",
                rejection=rejection,
            ),
        )

    if decision.successor is not None:
        successor_effect = StagedEffect(
            kind="routing-transition",
            payload_json=json.dumps(
                {
                    "issue_number": source.issue_number,
                    "action": decision.successor.value,
                },
                sort_keys=True,
            ),
            derived=True,
        )
        return decision, successor_effect, None

    terminal_effect = StagedEffect(
        kind="terminal-transition",
        payload_json=json.dumps(
            {
                "issue_number": source.issue_number,
                "expected_change": source.change,
            },
            sort_keys=True,
        ),
        derived=True,
    )
    return decision, terminal_effect, None


_ALLOWED_ISSUE_FIELDS = frozenset({"title", "body"})
_ALLOWED_PR_FIELDS = frozenset({"title", "body", "base"})
_ALLOWED_MERGE_METHODS = frozenset({"merge", "squash", "rebase"})
_SHA = re.compile(r"^[0-9a-f]{40}$")


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _valid_repo_path(value: object) -> bool:
    if not _is_nonempty_string(value):
        return False
    path = PurePosixPath(cast(str, value))
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def _valid_branch(value: object) -> bool:
    return (
        _is_nonempty_string(value)
        and not cast(str, value).startswith("refs/")
        and ".." not in cast(str, value)
        and "//" not in cast(str, value)
    )


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


_ROUTING_LABEL_PREFIXES = tuple(f"{name}:" for name in ("agent", "action"))


def _routing_label(value: object) -> bool:
    return isinstance(value, str) and not value.startswith(_ROUTING_LABEL_PREFIXES)


def _github_mutation_structurally_valid(
    source: WorkerRequest,
    payload: Mapping[str, object],
) -> bool:
    if payload.get("issue_number") != source.issue_number:
        return False
    operation = payload.get("operation")
    if not isinstance(operation, str):
        return False
    if operation not in allowed_github_mutation_operations(source.role, source.action):
        return False

    if operation == "issue-create":
        labels = payload.get("labels", [])
        return (
            _is_nonempty_string(payload.get("title"))
            and isinstance(payload.get("body", ""), str)
            and isinstance(labels, list)
            and all(_routing_label(label) for label in labels)
        )
    if operation == "issue-update":
        fields = payload.get("fields")
        expected = payload.get("expected")
        return _valid_fields(fields, _ALLOWED_ISSUE_FIELDS) and (
            expected is None or _valid_fields(expected, _ALLOWED_ISSUE_FIELDS)
        )
    if operation == "issue-label-add":
        return _is_nonempty_string(payload.get("label")) and _routing_label(payload.get("label"))
    if operation == "ref-create":
        return _valid_ref(payload.get("ref")) and _valid_sha(payload.get("sha"))
    if operation in {"ref-update", "ref-delete"}:
        return (
            _valid_ref(payload.get("ref"))
            and _valid_sha(payload.get("expected_sha"))
            and (operation == "ref-delete" or _valid_sha(payload.get("sha")))
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
            and not isinstance(payload.get("number"), bool)
            and payload.get("number") > 0
            and _valid_sha(payload.get("expected_head_sha"))
            and _valid_fields(payload.get("fields"), _ALLOWED_PR_FIELDS)
        )
    if operation == "pull-request-ready":
        return (
            isinstance(payload.get("number"), int)
            and not isinstance(payload.get("number"), bool)
            and payload.get("number") > 0
            and _valid_sha(payload.get("expected_head_sha"))
        )
    if operation == "pull-request-merge":
        method = payload.get("merge_method", "merge")
        return (
            isinstance(payload.get("number"), int)
            and not isinstance(payload.get("number"), bool)
            and payload.get("number") > 0
            and _valid_sha(payload.get("expected_head_sha"))
            and isinstance(method, str)
            and method in _ALLOWED_MERGE_METHODS
        )
    return False


def _terminal_transition_structurally_valid(
    source: WorkerRequest,
    payload: Mapping[str, object],
    *,
    derived: bool,
) -> bool:
    return (
        derived
        and set(payload) == {"issue_number", "expected_change"}
        and payload.get("issue_number") == source.issue_number
        and _is_nonempty_string(payload.get("expected_change"))
    )


def _routing_transition_structurally_valid(
    source: WorkerRequest,
    payload: Mapping[str, object],
    *,
    derived: bool,
) -> bool:
    if not derived or set(payload) != {"issue_number", "action"}:
        return False
    if payload.get("issue_number") != source.issue_number:
        return False
    action = payload.get("action")
    if not isinstance(action, str):
        return False
    try:
        ModelAction(action)
    except ValueError:
        return False
    return True


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
        return _routing_transition_structurally_valid(
            source,
            payload,
            derived=effect.derived,
        )
    if effect.kind == "terminal-transition":
        return _terminal_transition_structurally_valid(
            source,
            payload,
            derived=effect.derived,
        )
    if effect.kind == GITHUB_MUTATION_KIND:
        return _github_mutation_structurally_valid(source, payload)
    return False


def _routing_identity(request: WorkerRequest) -> tuple[str, str]:
    return request.role, request.action


def apply_effect_batch(
    batch: EffectBatch,
    *,
    fresh_preflight: FreshPreflight,
    effect_guard: EffectGuard,
    apply_effect: EffectApplier,
    observe_postcondition: PostconditionObserver,
    current_revision: str | None = None,
) -> ApplyResult:
    """Apply one typed batch after fresh source reauthorization."""

    current_preflight = fresh_preflight()
    typed_decision, derived_effect, typed_rejection = _typed_application_plan(
        batch,
        current_preflight,
        current_revision,
    )
    if typed_rejection is not None:
        return typed_rejection
    if typed_decision is None or derived_effect is None:
        return ApplyResult(False, "typed application rejected:plan-missing")

    effects = [*batch.effects, derived_effect]
    for effect in effects:
        if not effect_guard(effect):
            return ApplyResult(False, "effect precondition rejected")
        if effect.kind == "routing-transition" and not _typed_successor_effect_matches(
            effect,
            typed_decision,
        ):
            return ApplyResult(False, "typed application rejected:successor-effect")
        if effect.kind == "terminal-transition" and not _typed_terminal_effect_matches(
            effect,
            typed_decision,
        ):
            return ApplyResult(False, "typed application rejected:terminal-effect")

    for effect in effects:
        apply_effect(effect)
        if not observe_postcondition(effect):
            return ApplyResult(False, "durable postcondition not observed")

    return ApplyResult(True, "applied")


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
    request = Request(
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
    request = Request(
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
        self._routing_targets: dict[StagedEffect, str] = {}
        self._created_issue_numbers: dict[StagedEffect, int] = {}
        self._created_pr_numbers: dict[StagedEffect, int] = {}
        self._terminal_transitions: set[StagedEffect] = set()

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
        return bool(
            observation is not None
            and observation.authoritative
            and observation.issue_number == self.source.issue_number
            and observation.state == "open"
            and observation.routing == _routing_identity(self.source)
        )

    def _guard_github_mutation(self, payload: Mapping[str, object]) -> bool:
        operation = cast(str, payload["operation"])
        if operation in {"issue-create", "issue-label-add"}:
            return True
        if operation == "issue-update":
            current_issue = self._current_issue()
            if current_issue is None:
                return False
            expected = payload.get("expected")
            return expected is None or (
                isinstance(expected, Mapping) and _shallow_matches(current_issue, expected)
            )
        if operation in {"ref-update", "ref-delete"}:
            ref_state = _github_json(
                self.repository,
                self.token,
                _ref_api_path(cast(str, payload["ref"])),
                allow_not_found=True,
            )
            if not isinstance(ref_state, Mapping):
                return False
            obj = ref_state.get("object")
            return isinstance(obj, Mapping) and obj.get("sha") == payload.get("expected_sha")
        if operation == "ref-create":
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
            head_ref = _github_json(
                self.repository,
                self.token,
                _ref_api_path(f"refs/heads/{payload['head']}"),
                allow_not_found=True,
            )
            base_ref = _github_json(
                self.repository,
                self.token,
                _ref_api_path(f"refs/heads/{payload['base']}"),
                allow_not_found=True,
            )
            return isinstance(head_ref, Mapping) and isinstance(base_ref, Mapping)
        if operation in {"pull-request-update", "pull-request-ready", "pull-request-merge"}:
            number = cast(int, payload["number"])
            pr_state = _github_json(self.repository, self.token, f"pulls/{number}")
            return (
                isinstance(pr_state, Mapping)
                and _pull_request_head_sha(pr_state) == payload.get("expected_head_sha")
                and pr_state.get("state") == "open"
                and pr_state.get("merged") is not True
            )
        return False

    def guard(self, effect: StagedEffect) -> bool:
        if not supported_effect_guard(self.source, effect) or not self._source_still_current():
            return False
        if effect.kind in {"issue-comment", "routing-transition", "terminal-transition"}:
            return True
        payload = _effect_payload(effect)
        return payload is not None and self._guard_github_mutation(payload)

    def _apply_terminal_transition(
        self,
        effect: StagedEffect,
        payload: Mapping[str, object],
    ) -> None:
        if not _terminal_transition_structurally_valid(
            self.source,
            payload,
            derived=effect.derived,
        ):
            raise RuntimeError("terminal transition identity is invalid")
        current = self._current_issue()
        observation = None if current is None else normalize_github_issue(current)
        if (
            observation is None
            or not observation.authoritative
            or observation.state != "open"
            or observation.routing != _routing_identity(self.source)
            or observation.change != payload.get("expected_change")
        ):
            raise RuntimeError("terminal transition source is stale")
        _github_json(
            self.repository,
            self.token,
            f"issues/{self.source.issue_number}",
            method="PATCH",
            payload={"state": "closed"},
        )
        closed = self._current_issue()
        if closed is None or closed.get("state") != "closed":
            raise RuntimeError("terminal transition close postcondition not observed")
        label = f"action:{self.source.action}"
        _github_json(
            self.repository,
            self.token,
            f"issues/{self.source.issue_number}/labels/{quote(label, safe='')}",
            method="DELETE",
        )
        final = self._current_issue()
        final_observation = None if final is None else normalize_github_issue(final)
        if (
            final_observation is None
            or not final_observation.authoritative
            or final_observation.state != "closed"
            or final_observation.change != payload.get("expected_change")
            or final_observation.routing is not None
        ):
            raise RuntimeError("terminal transition postcondition not observed")
        self._terminal_transitions.add(effect)

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
            target_action = cast(str, payload["action"])
            source_label = f"action:{self.source.action}"
            target_label = f"action:{target_action}"
            current = self._current_issue()
            observation = None if current is None else normalize_github_issue(current)
            if (
                observation is None
                or not observation.authoritative
                or observation.state != "open"
                or observation.routing != _routing_identity(self.source)
            ):
                raise RuntimeError("routing transition source is stale")
            if source_label != target_label:
                _github_json(
                    self.repository,
                    self.token,
                    f"issues/{self.source.issue_number}/labels/{quote(source_label, safe='')}",
                    method="DELETE",
                )
                _github_json(
                    self.repository,
                    self.token,
                    f"issues/{self.source.issue_number}/labels",
                    method="POST",
                    payload={"labels": [target_label]},
                )
            self._routing_targets[effect] = target_action
            return

        if effect.kind == "terminal-transition":
            self._apply_terminal_transition(effect, payload)
            return

        if effect.kind == GITHUB_MUTATION_KIND:
            self._apply_github_mutation(effect, payload)
            return

        raise RuntimeError(f"unsupported effect kind: {effect.kind}")

    def _observe_github_mutation(
        self,
        effect: StagedEffect,
        payload: Mapping[str, object],
    ) -> bool:
        operation = cast(str, payload["operation"])
        if operation == "issue-create":
            number = self._created_issue_numbers.get(effect)
            if number is None:
                return False
            current = _github_json(self.repository, self.token, f"issues/{number}")
            if not isinstance(current, Mapping):
                return False
            labels = current.get("labels")
            names = (
                {
                    item.get("name")
                    for item in labels
                    if isinstance(item, Mapping) and isinstance(item.get("name"), str)
                }
                if isinstance(labels, list)
                else set()
            )
            return (
                current.get("title") == payload.get("title")
                and current.get("body", "") == payload.get("body", "")
                and all(label in names for label in cast(list[object], payload.get("labels", [])))
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
        if operation in {"ref-create", "ref-update"}:
            current = _github_json(
                self.repository,
                self.token,
                _ref_api_path(cast(str, payload["ref"])),
            )
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
            target_action = self._routing_targets.get(effect)
            current = self._current_issue()
            observation = None if current is None else normalize_github_issue(current)
            return bool(
                target_action is not None
                and observation is not None
                and observation.authoritative
                and observation.state == "open"
                and observation.routing
                == (
                    self.source.role,
                    target_action,
                )
            )

        if effect.kind == "terminal-transition":
            payload = _effect_payload(effect)
            current = self._current_issue()
            observation = None if current is None else normalize_github_issue(current)
            return bool(
                effect in self._terminal_transitions
                and payload is not None
                and observation is not None
                and observation.authoritative
                and observation.state == "closed"
                and observation.change == payload.get("expected_change")
                and observation.routing is None
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
    current_revision: str | None = None,
) -> tuple[EffectBatch, ApplyResult]:
    """Freshly reauthorize and apply one typed invocation-local effect batch."""

    batch = parse_effect_batch(raw_worker_result, source)
    adapter = GitHubEffectAdapter(repository, token, source)
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: acquire_current_github_preflight(repository, token),
        effect_guard=adapter.guard,
        apply_effect=adapter.apply,
        observe_postcondition=adapter.observe_postcondition,
        current_revision=current_revision,
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
    return WorkerRequest(
        issue_number=issue_number,
        role=role,
        action=action,
    )


def _write_github_outputs(result: ApplyResult) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write(f"applied={'true' if result.applied else 'false'}\n")


def main() -> int:
    """Apply one typed result through the write-authorized boundary."""

    if len(sys.argv) != 2:
        raise RuntimeError("worker result path argument is required")
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    source = _source_from_environment()
    raw_worker_result = Path(sys.argv[1]).read_text(encoding="utf-8")
    batch, result = run_effect_application(
        raw_worker_result,
        source=source,
        repository=repository,
        token=token,
    )
    _write_github_outputs(result)
    print(
        json.dumps(
            {
                "applied": result.applied,
                "reason": result.reason,
                "effects": len(batch.effects),
            },
            sort_keys=True,
        )
    )
    return 0 if result.applied else 1


if __name__ == "__main__":
    raise SystemExit(main())
