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
    role_for,
)
from investment_strategy.scheduled_agent_action_model import (
    ObservationProvenance as ModelObservationProvenance,
)
from investment_strategy.scheduled_agent_application_materialization import (
    apply_materialization,
    find_materialization_payload,
    materialization_postcondition,
)
from investment_strategy.scheduled_agent_carrier import (
    CarrierPlan,
    CarrierRequired,
    carrier_pr_identity,
    make_carrier_plan,
)
from investment_strategy.scheduled_agent_effect_contract import (
    GITHUB_MUTATION_KIND,
    allowed_github_mutation_operations,
)
from investment_strategy.scheduled_agent_runtime import (
    GitHubIssueObservation,
    WorkerRequest,
    acquire_current_github_preflight,
    normalize_github_issue,
)
from investment_strategy.scheduled_agent_validation_resource import ValidationResourceTarget
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
    carrier_plan: CarrierPlan | None = None


FreshPreflight = Callable[[], DispatchPreflight]
EffectGuard = Callable[[StagedEffect], bool]
EffectApplier = Callable[[StagedEffect], None]
PostconditionObserver = Callable[[StagedEffect], bool]
CarrierPlanProvider = Callable[[StagedEffect], CarrierPlan | None]


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
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_ARCHIVE_WORKFLOW_ID = "openspec-archive.yml"
_ARCHIVE_WORKFLOW_PATH = ".github/workflows/openspec-archive.yml"
_WORKFLOW_DISPATCH_INPUTS = frozenset({"change", "issue", "revision", "request_key"})


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _valid_positive_decimal(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[1-9][0-9]*", value) is not None


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


def _body_change(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    matches = _CHANGE_LINE.findall(value)
    if len(matches) > 1:
        return None
    return matches[0] if matches else "unset"


def _source_branch(change: object) -> str | None:
    if not isinstance(change, str) or change in {"", "unset"}:
        return None
    branch = f"agent/{change}"
    return branch if _valid_branch(branch) else None


def _archive_branch(change: object) -> str | None:
    if not isinstance(change, str) or change in {"", "unset"}:
        return None
    branch = f"agent/archive-{change}"
    return branch if _valid_branch(branch) else None


def _source_ref(change: object) -> str | None:
    branch = _source_branch(change)
    return None if branch is None else f"refs/heads/{branch}"


def _archive_ref(change: object) -> str | None:
    branch = _archive_branch(change)
    return None if branch is None else f"refs/heads/{branch}"


def _references_issue(body: object, issue_number: int) -> bool:
    return (
        isinstance(body, str)
        and re.search(rf"(?mi)^\s*Refs\s+#{issue_number}\s*$", body) is not None
    )


def _repository_full_name(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    full_name = value.get("full_name")
    return full_name if isinstance(full_name, str) else None


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
_RESERVED_ISSUE_LABEL_PREFIXES = _ROUTING_LABEL_PREFIXES + ("human:", "intake:")


def _routing_label(value: object) -> bool:
    return isinstance(value, str) and not value.startswith(_RESERVED_ISSUE_LABEL_PREFIXES)


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

    if operation == "application-materialize":
        try:
            find_materialization_payload(payload, source)
        except ValueError:
            return False
        return True

    if operation == "issue-update":
        fields = payload.get("fields")
        expected = payload.get("expected")
        return (
            _valid_fields(fields, _ALLOWED_ISSUE_FIELDS)
            and isinstance(expected, Mapping)
            and _valid_fields(expected, _ALLOWED_ISSUE_FIELDS)
        )
    if operation == "issue-label-add":
        return _is_nonempty_string(payload.get("label")) and _routing_label(payload.get("label"))
    if operation == "workflow-dispatch":
        inputs = payload.get("inputs")
        if (
            payload.get("workflow_id") != _ARCHIVE_WORKFLOW_ID
            or not _valid_branch(payload.get("ref"))
            or not isinstance(inputs, Mapping)
            or set(inputs) != _WORKFLOW_DISPATCH_INPUTS
            or not _is_nonempty_string(inputs.get("change"))
            or not _valid_positive_decimal(inputs.get("issue"))
            or not _valid_sha(inputs.get("revision"))
            or not isinstance(inputs.get("request_key"), str)
        ):
            return False
        issue = cast(str, inputs["issue"])
        revision = cast(str, inputs["revision"])
        return inputs["request_key"] == f"archive-{issue}-{revision}"
    if operation == "ref-delete":
        return _valid_ref(payload.get("ref")) and _valid_sha(payload.get("expected_sha"))
    if operation == "pull-request-create":
        head = payload.get("head")
        if (
            not _is_nonempty_string(payload.get("title"))
            or not isinstance(payload.get("body", ""), str)
            or not _valid_branch(head)
            or not _valid_branch(payload.get("base"))
            or not isinstance(payload.get("draft", False), bool)
        ):
            return False
        if isinstance(head, str) and head.startswith("agent/archive-"):
            return _valid_sha(payload.get("expected_head_sha"))
        return "expected_head_sha" not in payload
    if operation == "pull-request-update":
        number = payload.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            return False
        return _valid_sha(payload.get("expected_head_sha")) and _valid_fields(
            payload.get("fields"), _ALLOWED_PR_FIELDS
        )
    if operation == "pull-request-ready":
        number = payload.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            return False
        return _valid_sha(payload.get("expected_head_sha"))
    if operation == "pull-request-merge":
        number = payload.get("number")
        method = payload.get("merge_method", "merge")
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            return False
        return (
            _valid_sha(payload.get("expected_head_sha"))
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


def _issue_label_names(payload: Mapping[str, object]) -> tuple[str, ...] | None:
    raw = payload.get("labels")
    if not isinstance(raw, list):
        return None
    names: list[str] = []
    for item in raw:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str):
            return None
        names.append(cast(str, item["name"]))
    return tuple(names)


def _transition_labels(
    payload: Mapping[str, object],
    target_action: str | None,
) -> list[str] | None:
    names = _issue_label_names(payload)
    if names is None:
        return None
    labels = [name for name in names if not name.startswith(_ROUTING_LABEL_PREFIXES)]
    if target_action is not None:
        labels.append(f"action:{target_action}")
    return labels


def apply_effect_batch(
    batch: EffectBatch,
    *,
    fresh_preflight: FreshPreflight,
    effect_guard: EffectGuard,
    apply_effect: EffectApplier,
    observe_postcondition: PostconditionObserver,
    current_revision: str | None = None,
    apply_derived: bool = True,
    carrier_plan_for_effect: CarrierPlanProvider | None = None,
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

    effects = [*batch.effects, derived_effect] if apply_derived else list(batch.effects)
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
        if not effect_guard(effect):
            return ApplyResult(False, "effect precondition rejected")
        try:
            apply_effect(effect)
        except CarrierRequired as exc:
            return ApplyResult(False, "carrier_required", carrier_plan=exc.plan)
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
    repository_url = f"https://api.github.com/repos/{repository}"
    url = repository_url if not api_path else f"{repository_url}/{api_path.lstrip('/')}"
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

    def __init__(
        self,
        repository: str,
        token: str,
        source: WorkerRequest,
        *,
        authorized_change: str,
        current_revision: str | None = None,
        materialization_promote_change: bool = False,
        validated_materialization_revision: str | None = None,
    ) -> None:
        self.repository = repository
        self.token = token
        self.source = source
        self.authorized_change = authorized_change
        self.current_revision = current_revision
        self.materialization_promote_change = materialization_promote_change
        self.validated_materialization_revision = validated_materialization_revision
        self._comment_ids: dict[StagedEffect, int] = {}
        self._routing_targets: dict[StagedEffect, str] = {}
        self._created_pr_numbers: dict[StagedEffect, int] = {}
        self._terminal_transitions: set[StagedEffect] = set()
        self._idempotent_merges: set[StagedEffect] = set()
        self._merge_metadata: dict[str, tuple[str, str]] = {}
        self._materialization_targets: dict[StagedEffect, ValidationResourceTarget] = {}

    def _current_issue(self) -> Mapping[str, object] | None:
        payload = _github_json(
            self.repository,
            self.token,
            f"issues/{self.source.issue_number}",
        )
        return payload if isinstance(payload, Mapping) else None

    def _authorized_issue_observation(
        self,
        current: Mapping[str, object] | None = None,
    ) -> GitHubIssueObservation | None:
        payload = self._current_issue() if current is None else current
        if payload is None:
            return None
        observation = normalize_github_issue(payload)
        if (
            observation is None
            or not observation.authoritative
            or observation.issue_number != self.source.issue_number
            or observation.state != "open"
            or observation.routing != _routing_identity(self.source)
            or observation.change != self.authorized_change
        ):
            return None
        return observation

    def _source_still_current(self) -> bool:
        return self._authorized_issue_observation() is not None

    def _default_branch_still_current(self) -> bool:
        if self.current_revision is None:
            return True
        branch = self._default_branch()
        return branch is not None and self._default_branch_revision(branch) == self.current_revision

    def _default_branch(self) -> str | None:
        payload = _github_json(self.repository, self.token, "")
        if not isinstance(payload, Mapping):
            return None
        branch = payload.get("default_branch")
        return branch if _valid_branch(branch) else None

    def _default_branch_revision(self, branch: str) -> str | None:
        payload = _github_json(
            self.repository,
            self.token,
            _ref_api_path(f"refs/heads/{branch}"),
            allow_not_found=True,
        )
        if not isinstance(payload, Mapping):
            return None
        obj = payload.get("object")
        if not isinstance(obj, Mapping):
            return None
        sha = obj.get("sha")
        return sha if _valid_sha(sha) else None

    def _pull_request_matches_source(
        self,
        payload: Mapping[str, object],
        number: int,
        observation: GitHubIssueObservation,
        default_branch: str,
    ) -> bool:
        head = payload.get("head")
        base = payload.get("base")
        if not isinstance(head, Mapping) or not isinstance(base, Mapping):
            return False
        expected_branch = (
            _archive_branch(observation.change)
            if self.source.action == "merge-archive-pr"
            else _source_branch(observation.change)
        )
        return (
            payload.get("number") == number
            and _references_issue(payload.get("body"), self.source.issue_number)
            and expected_branch is not None
            and head.get("ref") == expected_branch
            and base.get("ref") == default_branch
            and _repository_full_name(head.get("repo")) == self.repository
            and _repository_full_name(base.get("repo")) == self.repository
        )

    def _pull_request_matches_create(
        self,
        current: Mapping[str, object],
        number: int,
        request: Mapping[str, object],
    ) -> bool:
        default_branch = self._default_branch()
        head = current.get("head")
        base = current.get("base")
        if (
            default_branch is None
            or not isinstance(head, Mapping)
            or not isinstance(base, Mapping)
            or current.get("number") != number
            or current.get("state") != "open"
            or current.get("merged") is True
            or current.get("title") != request.get("title")
            or current.get("body", "") != request.get("body", "")
            or current.get("draft") != request.get("draft", False)
            or request.get("base") != default_branch
            or head.get("ref") != request.get("head")
            or base.get("ref") != request.get("base")
            or _repository_full_name(head.get("repo")) != self.repository
            or _repository_full_name(base.get("repo")) != self.repository
        ):
            return False
        expected_head_sha = request.get("expected_head_sha")
        if expected_head_sha is not None and head.get("sha") != expected_head_sha:
            return False
        if request.get("head") == _archive_branch(self.authorized_change):
            return _valid_sha(self.current_revision) and base.get("sha") == self.current_revision
        return _valid_sha(self.current_revision) and base.get("sha") == self.current_revision

    def _source_pull_request(
        self,
        number: int,
        *,
        require_open: bool,
    ) -> Mapping[str, object] | None:
        observation = self._authorized_issue_observation()
        default_branch = self._default_branch()
        if observation is None or default_branch is None:
            return None
        payload = _github_json(self.repository, self.token, f"pulls/{number}")
        if not isinstance(payload, Mapping) or not self._pull_request_matches_source(
            payload, number, observation, default_branch
        ):
            return None
        if require_open and (payload.get("state") != "open" or payload.get("merged") is True):
            return None
        return payload

    def _no_existing_source_pull_request(self, branch: str, base: str) -> bool:
        owner = self.repository.split("/", 1)[0]
        head = f"{owner}:{branch}"
        query = "pulls?state=all"
        query += f"&head={quote(head, safe='')}"
        query += f"&base={quote(base, safe='')}"
        query += "&per_page=100"
        payload = _github_json(self.repository, self.token, query)
        return isinstance(payload, list) and not payload

    def _existing_pull_request_for_create(
        self,
        payload: Mapping[str, object],
    ) -> Mapping[str, object] | None:
        branch = payload.get("head")
        base = payload.get("base")
        if not isinstance(branch, str) or not isinstance(base, str):
            return None
        owner = self.repository.split("/", 1)[0]
        head = f"{owner}:{branch}"
        query = "pulls?state=all"
        query += f"&head={quote(head, safe='')}"
        query += f"&base={quote(base, safe='')}"
        query += "&per_page=100"
        response = _github_json(self.repository, self.token, query)
        if not isinstance(response, list):
            return None
        matches: list[Mapping[str, object]] = []
        for item in response:
            if not isinstance(item, Mapping):
                continue
            number = item.get("number")
            if (
                isinstance(number, int)
                and not isinstance(number, bool)
                and number > 0
                and self._pull_request_matches_create(item, number, payload)
            ):
                matches.append(item)
        if len(matches) > 1:
            raise RuntimeError("carrier PR target is ambiguous: duplicate matching PRs")
        return None if not matches else matches[0]

    def _existing_workflow_dispatch(
        self,
        payload: Mapping[str, object],
    ) -> Mapping[str, object] | None:
        workflow_id = cast(str, payload["workflow_id"])
        ref = cast(str, payload["ref"])
        inputs = cast(Mapping[str, object], payload["inputs"])
        revision = cast(str, inputs["revision"])
        request_key = cast(str, inputs["request_key"])
        query = (
            f"actions/workflows/{quote(workflow_id, safe='')}/runs"
            f"?event=workflow_dispatch&branch={quote(ref, safe='')}&per_page=100"
        )
        response = _github_json(self.repository, self.token, query)
        runs = response.get("workflow_runs") if isinstance(response, Mapping) else None
        if not isinstance(runs, list):
            return None
        expected_title = f"OpenSpec Archive {request_key}"
        for run in runs:
            if not isinstance(run, Mapping):
                continue
            run_id = run.get("id")
            if (
                isinstance(run_id, int)
                and not isinstance(run_id, bool)
                and run_id > 0
                and run.get("display_title") == expected_title
                and run.get("event") == "workflow_dispatch"
                and run.get("path") == _ARCHIVE_WORKFLOW_PATH
                and run.get("head_branch") == ref
                and run.get("head_sha") == revision
            ):
                return run
        return None

    def _historical_merged_pr(
        self,
        payload: Mapping[str, object],
        expected_head_sha: str,
    ) -> bool:
        merged_at = payload.get("merged_at")
        return (
            payload.get("state") == "closed"
            and payload.get("merged") is True
            and _valid_sha(payload.get("merge_commit_sha"))
            and isinstance(merged_at, str)
            and bool(merged_at.strip())
            and _pull_request_head_sha(payload) == expected_head_sha
        )

    def _carrier_plan(
        self,
        *,
        operation: str,
        target: Mapping[str, object],
        expected: Mapping[str, object],
        requested: Mapping[str, object],
        expected_postcondition: Mapping[str, object],
    ) -> CarrierPlan:
        """Bind one carrier-only operation to the current application authorization."""

        if not _valid_sha(self.current_revision):
            raise RuntimeError("carrier plan authorization revision is unavailable")
        return make_carrier_plan(
            repository=self.repository,
            issue_number=self.source.issue_number,
            change=self.authorized_change,
            action=self.source.action,
            authorization_revision=cast(str, self.current_revision),
            operation=operation,
            target=target,
            expected=expected,
            requested=requested,
            expected_postcondition=expected_postcondition,
        )

    def _carrier_plan_for_github_mutation(
        self,
        payload: Mapping[str, object],
    ) -> CarrierPlan:
        """Create a plan only after the fresh operation guard has passed."""

        operation = cast(str, payload["operation"])
        number = payload.get("number")
        if operation == "pull-request-create":
            default_branch = self._default_branch()
            branch = payload.get("head")
            if default_branch is None or not isinstance(branch, str):
                raise RuntimeError("carrier create plan target is unavailable")
            head_ref = _github_json(
                self.repository,
                self.token,
                _ref_api_path(f"refs/heads/{branch}"),
                allow_not_found=True,
            )
            base_ref = _github_json(
                self.repository,
                self.token,
                _ref_api_path(f"refs/heads/{default_branch}"),
                allow_not_found=True,
            )
            head_object = head_ref.get("object") if isinstance(head_ref, Mapping) else None
            base_object = base_ref.get("object") if isinstance(base_ref, Mapping) else None
            head_sha = head_object.get("sha") if isinstance(head_object, Mapping) else None
            base_sha = base_object.get("sha") if isinstance(base_object, Mapping) else None
            if not _valid_sha(head_sha) or not _valid_sha(base_sha):
                raise RuntimeError("carrier create plan ref identity is unavailable")
            create_requested = {
                "title": payload.get("title"),
                "body": payload.get("body", ""),
                "head": branch,
                "base": default_branch,
                "draft": payload.get("draft", False),
                "head_sha": head_sha,
            }
            create_expected = {
                "head_ref": branch,
                "head_sha": head_sha,
                "base_ref": default_branch,
                "base_sha": base_sha,
                "existing_pr_count": 0,
            }
            return self._carrier_plan(
                operation=operation,
                target={"head_ref": branch, "base_ref": default_branch},
                expected=create_expected,
                requested=create_requested,
                expected_postcondition={
                    "state": "open",
                    "merged": False,
                    "title": payload.get("title"),
                    "body": payload.get("body", ""),
                    "draft": payload.get("draft", False),
                    "head_ref": branch,
                    "head_sha": head_sha,
                    "base_ref": default_branch,
                    "base_sha": base_sha,
                    "repository": self.repository,
                },
            )

        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            raise RuntimeError("carrier plan PR identity is invalid")
        current = self._source_pull_request(number, require_open=operation != "pull-request-merge")
        if current is None:
            raise RuntimeError("carrier plan PR observation is unavailable")
        identity = carrier_pr_identity(current)
        requested: dict[str, object]
        expected_postcondition: dict[str, object]
        if operation == "pull-request-update":
            fields = payload.get("fields")
            if not isinstance(fields, Mapping):
                raise RuntimeError("carrier update plan fields are invalid")
            requested = {
                "fields": dict(fields),
                "expected_head_sha": payload.get("expected_head_sha"),
            }
            expected_postcondition = {
                "pr": number,
                "head_sha": payload.get("expected_head_sha"),
                "fields": dict(fields),
            }
        elif operation == "pull-request-ready":
            requested = {"expected_head_sha": payload.get("expected_head_sha"), "draft": False}
            expected_postcondition = {
                "pr": number,
                "state": "open",
                "merged": False,
                "draft": False,
                "head_sha": payload.get("expected_head_sha"),
            }
        elif operation == "pull-request-merge":
            requested = {
                "expected_head_sha": payload.get("expected_head_sha"),
                "merge_method": payload.get("merge_method", "merge"),
            }
            expected_postcondition = {
                "pr": number,
                "state": "closed",
                "merged": True,
                "head_sha": payload.get("expected_head_sha"),
            }
        else:
            raise RuntimeError(f"unsupported carrier plan operation: {operation}")
        return self._carrier_plan(
            operation=operation,
            target={"pull_request_number": number},
            expected={"pull_request": identity},
            requested=requested,
            expected_postcondition=expected_postcondition,
        )

    def carrier_plan_if_required(self, effect: StagedEffect) -> CarrierPlan | None:
        """Return a carrier plan only when a fresh PR postcondition is not current."""

        if effect.kind != GITHUB_MUTATION_KIND:
            return None
        payload = _effect_payload(effect)
        if payload is None:
            return None
        operation = payload.get("operation")
        if operation not in {
            "pull-request-create",
            "pull-request-update",
            "pull-request-ready",
            "pull-request-merge",
        }:
            return None
        if not self._guard_github_mutation(payload):
            return None
        if operation == "pull-request-create":
            return (
                None
                if self._existing_pull_request_for_create(payload) is not None
                else self._carrier_plan_for_github_mutation(payload)
            )
        number = payload.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            return None
        current = self._source_pull_request(
            number,
            require_open=operation != "pull-request-merge",
        )
        if current is None:
            return None
        if operation == "pull-request-update":
            fields = payload.get("fields")
            if (
                isinstance(fields, Mapping)
                and all(
                    (
                        (
                            key == "base"
                            and isinstance(current_base := current.get("base"), Mapping)
                            and current_base.get("ref") == value
                        )
                        or (key != "base" and current.get(key) == value)
                    )
                    for key, value in fields.items()
                )
                and _pull_request_head_sha(current) == payload.get("expected_head_sha")
            ):
                return None
        elif operation == "pull-request-ready":
            if current.get("draft") is False and _pull_request_head_sha(current) == payload.get(
                "expected_head_sha"
            ):
                return None
        elif operation == "pull-request-merge":
            if self._historical_merged_pr(current, cast(str, payload["expected_head_sha"])):
                return None
        return self._carrier_plan_for_github_mutation(payload)

    def _guard_github_mutation(self, payload: Mapping[str, object]) -> bool:
        observation = self._authorized_issue_observation()
        if observation is None:
            return False
        operation = cast(str, payload["operation"])
        if operation == "application-materialize":
            request = find_materialization_payload(payload, self.source)
            if request is None:
                return False
            default_branch = self._default_branch()
            return (
                request.expected_change == self.authorized_change
                and default_branch is not None
                and self.current_revision is not None
                and _valid_sha(self.current_revision)
                and self._default_branch_revision(default_branch) == self.current_revision
            )
        if operation == "issue-label-add":
            return True
        if operation == "workflow-dispatch":
            default_branch = self._default_branch()
            inputs = cast(Mapping[str, object], payload["inputs"])
            issue = cast(str, inputs["issue"])
            revision = cast(str, inputs["revision"])
            request_key = cast(str, inputs["request_key"])
            return (
                default_branch is not None
                and payload.get("ref") == default_branch
                and self.current_revision is not None
                and _valid_sha(self.current_revision)
                and self._default_branch_revision(default_branch) == self.current_revision
                and inputs.get("change") == self.authorized_change
                and issue == str(self.source.issue_number)
                and revision == self.current_revision
                and request_key == f"archive-{issue}-{revision}"
            )
        if operation == "issue-update":
            current_issue = self._current_issue()
            current_observation = self._authorized_issue_observation(current_issue)
            expected = payload.get("expected")
            fields = payload.get("fields")
            return (
                current_issue is not None
                and current_observation is not None
                and isinstance(expected, Mapping)
                and isinstance(fields, Mapping)
                and _shallow_matches(current_issue, expected)
                and ("body" not in fields or _body_change(fields["body"]) == self.authorized_change)
            )
        expected_ref = (
            _archive_ref(observation.change)
            if self.source.action == "merge-archive-pr"
            else _source_ref(observation.change)
        )
        if operation == "ref-delete":
            if expected_ref is None or payload.get("ref") != expected_ref:
                return False
            ref_state = _github_json(
                self.repository,
                self.token,
                _ref_api_path(expected_ref),
                allow_not_found=True,
            )
            if not isinstance(ref_state, Mapping):
                return False
            obj = ref_state.get("object")
            return isinstance(obj, Mapping) and obj.get("sha") == payload.get("expected_sha")
        if operation == "pull-request-create":
            default_branch = self._default_branch()
            source_branch = _source_branch(observation.change)
            archive_branch = _archive_branch(observation.change)
            requested_branch = payload.get("head")
            if (
                default_branch is None
                or not isinstance(requested_branch, str)
                or payload.get("base") != default_branch
                or not _references_issue(payload.get("body"), self.source.issue_number)
            ):
                return False
            if requested_branch == archive_branch:
                if self.source.action != "finalize-change":
                    return False
                expected_head_sha = payload.get("expected_head_sha")
                if not _valid_sha(expected_head_sha):
                    return False
                expected_branch = archive_branch
            elif requested_branch == source_branch:
                if "expected_head_sha" in payload:
                    return False
                expected_branch = source_branch
            else:
                return False
            if expected_branch is None:
                return False
            head_ref = _github_json(
                self.repository,
                self.token,
                _ref_api_path(f"refs/heads/{expected_branch}"),
                allow_not_found=True,
            )
            base_ref = _github_json(
                self.repository,
                self.token,
                _ref_api_path(f"refs/heads/{default_branch}"),
                allow_not_found=True,
            )
            if not isinstance(head_ref, Mapping) or not isinstance(base_ref, Mapping):
                return False
            head_object = head_ref.get("object")
            base_object = base_ref.get("object")
            if not isinstance(head_object, Mapping) or not isinstance(base_object, Mapping):
                return False
            if requested_branch == archive_branch and not (
                head_object.get("sha") == payload.get("expected_head_sha")
                and _valid_sha(self.current_revision)
                and base_object.get("sha") == self.current_revision
            ):
                return False
            if self._existing_pull_request_for_create(payload) is not None:
                return True
            return self._no_existing_source_pull_request(expected_branch, default_branch)
        if operation == "pull-request-merge":
            number = cast(int, payload["number"])
            expected_head_sha = cast(str, payload["expected_head_sha"])
            pr_state = self._source_pull_request(number, require_open=False)
            if pr_state is None or _pull_request_head_sha(pr_state) != expected_head_sha:
                return False
            if self._historical_merged_pr(pr_state, expected_head_sha):
                metadata = (
                    cast(str, pr_state["merge_commit_sha"]),
                    cast(str, pr_state["merged_at"]),
                )
                key = json.dumps(payload, sort_keys=True)
                previous = self._merge_metadata.get(key)
                if previous is not None and previous != metadata:
                    return False
                self._merge_metadata[key] = metadata
                return True
            return pr_state.get("state") == "open" and pr_state.get("merged") is not True
        if operation in {"pull-request-update", "pull-request-ready"}:
            number = cast(int, payload["number"])
            pr_state = self._source_pull_request(number, require_open=True)
            if pr_state is None or _pull_request_head_sha(pr_state) != payload.get(
                "expected_head_sha"
            ):
                return False
            if operation == "pull-request-update":
                fields = payload.get("fields")
                default_branch = self._default_branch()
                if not isinstance(fields, Mapping) or default_branch is None:
                    return False
                if "base" in fields and fields["base"] != default_branch:
                    return False
                if "body" in fields and not _references_issue(
                    fields["body"], self.source.issue_number
                ):
                    return False
            return True
        return False

    def guard(self, effect: StagedEffect) -> bool:
        if (
            not supported_effect_guard(self.source, effect)
            or not self._source_still_current()
            or not self._default_branch_still_current()
        ):
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
        observation = self._authorized_issue_observation(current)
        labels = None if current is None else _transition_labels(current, None)
        if (
            observation is None
            or labels is None
            or observation.change != payload.get("expected_change")
        ):
            raise RuntimeError("terminal transition source is stale")
        _github_json(
            self.repository,
            self.token,
            f"issues/{self.source.issue_number}",
            method="PATCH",
            payload={"state": "closed", "labels": labels},
        )
        final = self._current_issue()
        final_observation = None if final is None else normalize_github_issue(final)
        if (
            final_observation is None
            or not final_observation.authoritative
            or final_observation.state != "closed"
            or final_observation.change != payload.get("expected_change")
            or final_observation.routing is not None
            or final_observation.routing_debt
        ):
            raise RuntimeError("terminal transition postcondition not observed")
        self._terminal_transitions.add(effect)

    def _apply_github_mutation(self, effect: StagedEffect, payload: Mapping[str, object]) -> None:
        operation = cast(str, payload["operation"])
        if operation == "application-materialize":
            default_branch = self._default_branch()
            if default_branch is None or self.current_revision is None:
                raise RuntimeError("application materialization default branch is unavailable")
            target = apply_materialization(
                payload,
                self.source,
                repository=self.repository,
                token=self.token,
                current_revision=self.current_revision,
                default_branch=default_branch,
                promote_change=self.materialization_promote_change,
                validated_revision=self.validated_materialization_revision,
            )
            self._materialization_targets[effect] = target
            if self.materialization_promote_change:
                self.authorized_change = target.change
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
        if operation == "ref-delete":
            _github_json(
                self.repository,
                self.token,
                _ref_mutation_path(cast(str, payload["ref"])),
                method="DELETE",
            )
            return
        if operation == "workflow-dispatch":
            if self._existing_workflow_dispatch(payload) is not None:
                return
            inputs = cast(Mapping[str, object], payload["inputs"])
            _github_json(
                self.repository,
                self.token,
                f"actions/workflows/{quote(cast(str, payload['workflow_id']), safe='')}/dispatches",
                method="POST",
                payload={
                    "ref": cast(str, payload["ref"]),
                    "inputs": {key: cast(str, value) for key, value in inputs.items()},
                },
            )
            return
        if operation == "pull-request-create":
            existing = self._existing_pull_request_for_create(payload)
            if existing is not None:
                number = existing.get("number")
                if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                    raise RuntimeError("existing pull request number is invalid")
                self._created_pr_numbers[effect] = number
                return
            raise CarrierRequired(self._carrier_plan_for_github_mutation(payload))
            return
        if operation == "pull-request-update":
            current = self._source_pull_request(cast(int, payload["number"]), require_open=True)
            fields = payload.get("fields")
            if current is None or not isinstance(fields, Mapping):
                raise RuntimeError("pull request update source became stale")
            if all(
                (
                    (
                        key == "base"
                        and isinstance(current_base := current.get("base"), Mapping)
                        and current_base.get("ref") == value
                    )
                    or (key != "base" and current.get(key) == value)
                )
                for key, value in fields.items()
            ) and _pull_request_head_sha(current) == payload.get("expected_head_sha"):
                return
            raise CarrierRequired(self._carrier_plan_for_github_mutation(payload))
            return
        if operation == "pull-request-ready":
            number = cast(int, payload["number"])
            ready_current = self._source_pull_request(number, require_open=True)
            if ready_current is None:
                raise RuntimeError("pull request ready source became stale")
            if ready_current.get("draft") is False and _pull_request_head_sha(
                ready_current
            ) == payload.get("expected_head_sha"):
                return
            raise CarrierRequired(self._carrier_plan_for_github_mutation(payload))
            return
        if operation == "pull-request-merge":
            number = cast(int, payload["number"])
            expected_head_sha = cast(str, payload["expected_head_sha"])
            current = self._source_pull_request(number, require_open=False)
            if current is None or _pull_request_head_sha(current) != expected_head_sha:
                raise RuntimeError("pull request merge source became stale")
            if self._historical_merged_pr(current, expected_head_sha):
                key = json.dumps(payload, sort_keys=True)
                self._merge_metadata.setdefault(
                    key,
                    (cast(str, current["merge_commit_sha"]), cast(str, current["merged_at"])),
                )
                self._idempotent_merges.add(effect)
                return
            if current.get("state") != "open" or current.get("merged") is True:
                raise RuntimeError("pull request merge source is not open")
            raise CarrierRequired(self._carrier_plan_for_github_mutation(payload))
            return
        raise RuntimeError(f"unsupported GitHub mutation operation: {operation}")

    def _existing_issue_comment(self, body: str) -> int | None:
        page = 1
        while True:
            page_suffix = "" if page == 1 else f"&page={page}"
            payload = _github_json(
                self.repository,
                self.token,
                "issues/"
                f"{self.source.issue_number}/comments?per_page=100&sort=created"
                f"&direction=desc{page_suffix}",
            )
            if not isinstance(payload, list):
                return None
            for item in payload:
                if not isinstance(item, Mapping) or item.get("body") != body:
                    continue
                comment_id = item.get("id")
                user = item.get("user")
                if not isinstance(comment_id, int) or not isinstance(user, Mapping):
                    continue
                if user.get("login") == "github-actions[bot]":
                    return comment_id
            if len(payload) < 100:
                return None
            page += 1

    def apply(self, effect: StagedEffect) -> None:
        payload = _effect_payload(effect)
        if payload is None:
            raise RuntimeError("validated effect payload became unavailable")

        if effect.kind == "issue-comment":
            body = cast(str, payload["body"])
            existing = self._existing_issue_comment(body)
            if existing is not None:
                self._comment_ids[effect] = existing
                return
            response = _github_json(
                self.repository,
                self.token,
                f"issues/{self.source.issue_number}/comments",
                method="POST",
                payload={"body": body},
            )
            if not isinstance(response, Mapping) or not isinstance(response.get("id"), int):
                raise RuntimeError("GitHub comment mutation returned no comment id")
            self._comment_ids[effect] = cast(int, response["id"])
            return

        if effect.kind == "routing-transition":
            if not _routing_transition_structurally_valid(
                self.source,
                payload,
                derived=effect.derived,
            ):
                raise RuntimeError("routing transition identity is invalid")
            target_action = cast(str, payload["action"])
            current = self._current_issue()
            observation = self._authorized_issue_observation(current)
            labels = None if current is None else _transition_labels(current, target_action)
            if observation is None or labels is None:
                raise RuntimeError("routing transition source is stale")
            _github_json(
                self.repository,
                self.token,
                f"issues/{self.source.issue_number}",
                method="PATCH",
                payload={"labels": labels},
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
        if operation == "application-materialize":
            default_branch = self._default_branch()
            return (
                default_branch is not None
                and self.current_revision is not None
                and materialization_postcondition(
                    payload,
                    self.source,
                    repository=self.repository,
                    token=self.token,
                    current_revision=self.current_revision,
                    default_branch=default_branch,
                    target=self._materialization_targets.get(effect),
                )
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
        if operation == "workflow-dispatch":
            return self._existing_workflow_dispatch(payload) is not None
        if operation == "pull-request-create":
            number = self._created_pr_numbers.get(effect)
            if number is None:
                existing = self._existing_pull_request_for_create(payload)
                if existing is None:
                    return False
                candidate_number = existing.get("number")
                if (
                    not isinstance(candidate_number, int)
                    or isinstance(candidate_number, bool)
                    or candidate_number <= 0
                ):
                    return False
                number = candidate_number
            current_pr = _github_json(self.repository, self.token, f"pulls/{number}")
            return isinstance(current_pr, Mapping) and self._pull_request_matches_create(
                current_pr, number, payload
            )
        if operation == "pull-request-update":
            current = self._source_pull_request(cast(int, payload["number"]), require_open=True)
            fields = payload.get("fields")
            if current is None or not isinstance(fields, Mapping):
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
            current = self._source_pull_request(cast(int, payload["number"]), require_open=True)
            return (
                current is not None
                and current.get("draft") is False
                and _pull_request_head_sha(current) == payload.get("expected_head_sha")
            )
        if operation == "pull-request-merge":
            current = self._source_pull_request(cast(int, payload["number"]), require_open=False)
            if current is None or not self._historical_merged_pr(
                current,
                cast(str, payload["expected_head_sha"]),
            ):
                return False
            metadata = (
                cast(str, current["merge_commit_sha"]),
                cast(str, current["merged_at"]),
            )
            expected_metadata = self._merge_metadata.get(json.dumps(payload, sort_keys=True))
            return expected_metadata is None or expected_metadata == metadata
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
            try:
                target_role = (
                    None if target_action is None else role_for(ModelAction(target_action)).value
                )
            except ValueError:
                target_role = None
            return bool(
                target_action is not None
                and target_role is not None
                and observation is not None
                and observation.authoritative
                and observation.state == "open"
                and not observation.routing_debt
                and observation.routing == (target_role, target_action)
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
                and not observation.routing_debt
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
    apply_derived: bool = True,
    materialization_promote_change: bool = False,
    validated_materialization_revision: str | None = None,
) -> tuple[EffectBatch, ApplyResult]:
    """Freshly reauthorize and apply one typed invocation-local effect batch."""

    batch = parse_effect_batch(raw_worker_result, source)
    if batch.typed_result is None:
        return batch, ApplyResult(False, "typed application rejected:result-missing")
    adapter = GitHubEffectAdapter(
        repository,
        token,
        source,
        authorized_change=batch.typed_result.change,
        current_revision=current_revision,
        materialization_promote_change=materialization_promote_change,
        validated_materialization_revision=validated_materialization_revision,
    )
    result = apply_effect_batch(
        batch,
        fresh_preflight=lambda: acquire_current_github_preflight(repository, token),
        effect_guard=adapter.guard,
        apply_effect=adapter.apply,
        observe_postcondition=adapter.observe_postcondition,
        current_revision=current_revision,
        apply_derived=apply_derived,
        carrier_plan_for_effect=adapter.carrier_plan_if_required,
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
