"""Action-scoped durable-effect and consequence capabilities.

The Action/Result graph is the executable topology.  This module is the one
repository-owned table that describes what a legal transition must leave
behind.  It intentionally describes affirmative evidence targets and the
next missing effect, rather than inferring ownership from a list of special
cases.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch
from types import MappingProxyType
from typing import Final

from investment_strategy.scheduled_agent_action_model import (
    TRANSITIONS,
    Action,
    ResultKind,
    Role,
    TypedResult,
    next_action,
    role_for,
)

RoleAction = tuple[str, str]
GITHUB_MUTATION_KIND: Final = "github-mutation"
_CANDIDATE_ACTIONS: Final = frozenset(
    {Action.EXPLORE_CHANGE, Action.PROPOSE_CHANGE, Action.RESOLVE_QUESTION}
)


class EvidenceTarget(StrEnum):
    """Fresh repository evidence used to qualify a formal result."""

    DEFAULT_BRANCH = "DEFAULT_BRANCH"
    IMPLEMENTATION_PR_HEAD = "IMPLEMENTATION_PR_HEAD"
    ARCHIVE_PR_HEAD = "ARCHIVE_PR_HEAD"
    MERGED_PR_HEAD = "MERGED_PR_HEAD"
    MATERIALIZED_REVISION = "MATERIALIZED_REVISION"


class DurablePrefix(StrEnum):
    """Repository-visible interruption boundaries used by verification."""

    BEFORE_ACCEPT = "before-accept"
    AFTER_ACCEPT = "after-accept"
    CONTENT = "content-blob-tree-commit"
    BRANCH_REF = "branch-ref"
    PR_CARRIER = "pr-carrier"
    CARRIER_RETURN = "carrier-return"
    ASYNC_WORKFLOW = "async-workflow"
    VALIDATION = "validation"
    FORMAL_RESULT = "canonical-formal-result"
    ROUTING = "routing-projection"
    TERMINAL = "terminal-close"


DURABLE_PREFIXES: Final[tuple[DurablePrefix, ...]] = tuple(DurablePrefix)


@dataclass(frozen=True, slots=True)
class ConsequenceSpec:
    """Executable contract for one legal Action/Result transition.

    ``missing_effect`` is a bounded operation name understood by the current
    application/effect owner.  It is descriptive for transitions that are
    already complete in repository state, and is never a permission to let a
    worker select a target or a successor.
    """

    action: Action
    result: ResultKind
    evidence_target: EvidenceTarget
    completion_predicate: str
    missing_effect: str
    successor_required: bool


# Every legal transition declares its evidence subject. Coordination outcomes
# use the governance revision; work-product outcomes use their own carrier.
# The Change PR is also the OpenSpec carrier before implementation starts.
_EVIDENCE_TARGET_GROUPS: Final[dict[Action, dict[EvidenceTarget, tuple[ResultKind, ...]]]] = {
    Action.EXPLORE_CHANGE: {
        EvidenceTarget.DEFAULT_BRANCH: (
            ResultKind.PROPOSAL_READY,
            ResultKind.RESEARCH_REQUIRED,
            ResultKind.HUMAN_DECISION_REQUIRED,
            ResultKind.NO_CHANGE_REQUIRED,
            ResultKind.NO_GO,
            ResultKind.BLOCKED,
        ),
    },
    Action.PROPOSE_CHANGE: {
        EvidenceTarget.DEFAULT_BRANCH: (
            ResultKind.RESEARCH_REQUIRED,
            ResultKind.HUMAN_DECISION_REQUIRED,
            ResultKind.NO_GO,
            ResultKind.BLOCKED,
        ),
        EvidenceTarget.MATERIALIZED_REVISION: (ResultKind.READY_FOR_OPENSPEC_REVIEW,),
    },
    Action.RESOLVE_QUESTION: {
        EvidenceTarget.DEFAULT_BRANCH: (
            ResultKind.LIFECYCLE_READY,
            ResultKind.READY,
            ResultKind.RESEARCH_REQUIRED,
            ResultKind.HUMAN_DECISION_REQUIRED,
            ResultKind.NO_GO,
            ResultKind.BLOCKED,
        ),
        EvidenceTarget.MATERIALIZED_REVISION: (ResultKind.READY_FOR_OPENSPEC_REVIEW,),
    },
    Action.FINALIZE_CHANGE: {
        EvidenceTarget.DEFAULT_BRANCH: (
            ResultKind.SPEC_BLOCKER,
            ResultKind.MORE_IMPLEMENTATION_REQUIRED,
            ResultKind.HUMAN_DECISION_REQUIRED,
            ResultKind.NO_GO,
            ResultKind.BLOCKED,
        ),
        EvidenceTarget.ARCHIVE_PR_HEAD: (ResultKind.ARCHIVE_READY,),
    },
    Action.FINALIZE_ARCHIVE: {
        EvidenceTarget.DEFAULT_BRANCH: (ResultKind.HUMAN_DECISION_REQUIRED, ResultKind.BLOCKED),
        EvidenceTarget.MERGED_PR_HEAD: (ResultKind.LIFECYCLE_COMPLETE,),
    },
    Action.REVIEW_OPENSPEC: {
        EvidenceTarget.DEFAULT_BRANCH: (
            ResultKind.HUMAN_DECISION_REQUIRED,
            ResultKind.NO_GO,
            ResultKind.BLOCKED,
        ),
        EvidenceTarget.IMPLEMENTATION_PR_HEAD: (ResultKind.PASS, ResultKind.FINDINGS),
    },
    Action.REVIEW_IMPLEMENTATION: {
        EvidenceTarget.DEFAULT_BRANCH: (
            ResultKind.SPEC_BLOCKER,
            ResultKind.HUMAN_DECISION_REQUIRED,
            ResultKind.BLOCKED,
        ),
        EvidenceTarget.IMPLEMENTATION_PR_HEAD: (ResultKind.PASS, ResultKind.FINDINGS),
    },
    Action.REVIEW_ARCHIVE: {
        EvidenceTarget.DEFAULT_BRANCH: (
            ResultKind.HUMAN_DECISION_REQUIRED,
            ResultKind.NO_GO,
            ResultKind.BLOCKED,
        ),
        EvidenceTarget.ARCHIVE_PR_HEAD: (ResultKind.PASS, ResultKind.FINDINGS),
    },
    Action.IMPLEMENT_CHANGE: {
        EvidenceTarget.DEFAULT_BRANCH: (
            ResultKind.SPEC_BLOCKER,
            ResultKind.HUMAN_DECISION_REQUIRED,
            ResultKind.BLOCKED,
        ),
        EvidenceTarget.IMPLEMENTATION_PR_HEAD: (
            ResultKind.READY,
            ResultKind.MORE_IMPLEMENTATION_REQUIRED,
        ),
    },
    Action.MERGE_IMPLEMENTATION_PR: {
        EvidenceTarget.DEFAULT_BRANCH: (ResultKind.LIFECYCLE_VIOLATION, ResultKind.BLOCKED),
        EvidenceTarget.MERGED_PR_HEAD: (ResultKind.MERGED,),
    },
    Action.MERGE_ARCHIVE_PR: {
        EvidenceTarget.DEFAULT_BRANCH: (ResultKind.LIFECYCLE_VIOLATION, ResultKind.BLOCKED),
        EvidenceTarget.MERGED_PR_HEAD: (ResultKind.MERGED,),
    },
}

_MISSING_EFFECT_OVERRIDES: Final[dict[tuple[Action, ResultKind], str]] = {
    (
        Action.PROPOSE_CHANGE,
        ResultKind.READY_FOR_OPENSPEC_REVIEW,
    ): "application-materialize-or-formal-result",
    (Action.FINALIZE_CHANGE, ResultKind.ARCHIVE_READY): "archive-pr-create-or-reuse",
}


def _build_evidence_targets() -> dict[tuple[Action, ResultKind], EvidenceTarget]:
    targets: dict[tuple[Action, ResultKind], EvidenceTarget] = {}
    for action, groups in _EVIDENCE_TARGET_GROUPS.items():
        for target, results in groups.items():
            for result in results:
                key = (action, result)
                if key in targets:
                    raise AssertionError(f"duplicate evidence target: {key}")
                targets[key] = target
    legal = {(action, result) for action, results in TRANSITIONS.items() for result in results}
    if targets.keys() != legal:
        raise AssertionError("evidence targets must cover exactly the legal transitions")
    return targets


def _build_missing_effects() -> dict[tuple[Action, ResultKind], str]:
    effects = {
        (action, result): "formal-result"
        for action, results in TRANSITIONS.items()
        for result in results
    }
    for action in {Action.IMPLEMENT_CHANGE, Action.RESOLVE_QUESTION}:
        for result in TRANSITIONS[action]:
            effects[(action, result)] = "application-materialize-or-formal-result"
    for action in {Action.MERGE_IMPLEMENTATION_PR, Action.MERGE_ARCHIVE_PR}:
        for result in TRANSITIONS[action]:
            effects[(action, result)] = "merge-carrier-or-formal-result"
    effects.update(_MISSING_EFFECT_OVERRIDES)
    return effects


_EVIDENCE_TARGETS: Final = _build_evidence_targets()
_MISSING_EFFECTS: Final = _build_missing_effects()


def _evidence_target(action: Action, result: ResultKind) -> EvidenceTarget:
    """Return the positive evidence target for one legal transition."""

    try:
        return _EVIDENCE_TARGETS[(action, result)]
    except KeyError as exc:
        raise AssertionError("legal transition has no evidence target") from exc


def _missing_effect(action: Action, result: ResultKind) -> str:
    """Return the fresh-state missing-effect owner for one legal transition."""

    try:
        return _MISSING_EFFECTS[(action, result)]
    except KeyError as exc:
        raise AssertionError("legal transition has no consequence planner") from exc


def _build_consequence_specs() -> Mapping[tuple[Action, ResultKind], ConsequenceSpec]:
    specs: dict[tuple[Action, ResultKind], ConsequenceSpec] = {}
    for action, results in TRANSITIONS.items():
        for result in results:
            target = _evidence_target(action, result)
            specs[(action, result)] = ConsequenceSpec(
                action=action,
                result=result,
                evidence_target=target,
                completion_predicate=(
                    "archive-pr-successor-ready"
                    if target is EvidenceTarget.ARCHIVE_PR_HEAD
                    and result in {ResultKind.ARCHIVE_READY, ResultKind.PASS}
                    else "materialized-revision-and-successor-ready"
                    if target is EvidenceTarget.MATERIALIZED_REVISION
                    else "formal-result-and-successor-ready"
                    if results[result] is not None
                    else "formal-result-and-terminal-ready"
                ),
                missing_effect=_missing_effect(action, result),
                successor_required=results[result] is not None,
            )
    return MappingProxyType(specs)


CONSEQUENCE_SPECS: Final = _build_consequence_specs()


def legal_transition_keys() -> frozenset[tuple[Action, ResultKind]]:
    """Return the executable Action/Result topology as stable test data."""

    return frozenset(
        (action, result) for action, results in TRANSITIONS.items() for result in results
    )


def verification_matrix() -> tuple[tuple[Action, ResultKind, DurablePrefix], ...]:
    """Generate the topology × durable-prefix fresh-process matrix."""

    return tuple(
        (action, result, prefix)
        for action, result in sorted(
            legal_transition_keys(), key=lambda item: (item[0].value, item[1].value)
        )
        for prefix in DURABLE_PREFIXES
    )


def consequence_spec_for(
    action: Action | str,
    result: ResultKind | str,
) -> ConsequenceSpec:
    """Return the one affirmative consequence contract for a legal result."""

    try:
        key = (Action(action), ResultKind(result))
    except ValueError as exc:
        raise ValueError("unknown Action/Result consequence") from exc
    try:
        return CONSEQUENCE_SPECS[key]
    except KeyError as exc:
        raise ValueError(
            f"illegal Action/Result consequence: {key[0].value}/{key[1].value}"
        ) from exc


def candidate_withdrawal_permitted(
    role: str,
    action: Action | str,
    result: ResultKind | str | None,
) -> bool:
    """Derive the bounded candidate withdrawal capability from the topology."""

    if result is None:
        return False
    try:
        spec = consequence_spec_for(action, result)
    except ValueError:
        return False
    if (
        spec.action not in _CANDIDATE_ACTIONS
        or role != Role.LEAD.value
        or role_for(spec.action) is not Role.LEAD
        or spec.evidence_target is not EvidenceTarget.DEFAULT_BRANCH
    ):
        return False
    return (
        spec.action is Action.RESOLVE_QUESTION and spec.result is ResultKind.READY
    ) or next_action(spec.action, TypedResult(spec.result)) in _CANDIDATE_ACTIONS


def is_exact_pull_request_close(
    kind: object,
    payload: Mapping[str, object],
    *,
    issue_number: object,
) -> bool:
    """Recognize an exact close shape without granting carrier authority."""

    payload_issue = payload.get("issue_number")
    number = payload.get("number")
    head_sha = payload.get("expected_head_sha")
    return (
        kind == GITHUB_MUTATION_KIND
        and isinstance(issue_number, int)
        and not isinstance(issue_number, bool)
        and issue_number > 0
        and isinstance(payload_issue, int)
        and not isinstance(payload_issue, bool)
        and payload_issue == issue_number
        and payload.get("operation") == "pull-request-update"
        and isinstance(number, int)
        and not isinstance(number, bool)
        and number > 0
        and isinstance(head_sha, str)
        and fullmatch(r"[0-9a-f]{40}", head_sha) is not None
        and payload.get("fields") == {"state": "closed"}
    )


def assert_consequence_specs_complete() -> None:
    """Mechanically enforce one spec for every, and only every, transition."""

    legal = legal_transition_keys()
    actual = frozenset(CONSEQUENCE_SPECS)
    if actual != legal:
        missing = sorted((a.value, r.value) for a, r in legal - actual)
        extra = sorted((a.value, r.value) for a, r in actual - legal)
        raise AssertionError(f"consequence topology mismatch: missing={missing}, extra={extra}")
    if any(
        not spec.evidence_target.value or not spec.completion_predicate or not spec.missing_effect
        for spec in CONSEQUENCE_SPECS.values()
    ):
        raise AssertionError("consequence specification contains an empty executable field")


assert_consequence_specs_complete()

_ACTION_OPERATIONS: Final[dict[RoleAction, frozenset[str]]] = {
    ("lead", "explore-change"): frozenset({"issue-update", "issue-label-add"}),
    ("lead", "propose-change"): frozenset(
        {"issue-update", "issue-label-add", "application-materialize"}
    ),
    ("lead", "resolve-question"): frozenset(
        {
            "issue-update",
            "issue-label-add",
            "pull-request-create",
            "pull-request-update",
            "application-materialize",
        }
    ),
    ("lead", "finalize-change"): frozenset(
        {
            "issue-update",
            "issue-label-add",
            "pull-request-create",
            "pull-request-update",
            "workflow-dispatch",
        }
    ),
    ("lead", "finalize-archive"): frozenset({"issue-update", "issue-label-add"}),
    ("reviewer", "review-openspec"): frozenset(),
    ("reviewer", "review-implementation"): frozenset(),
    ("reviewer", "review-archive"): frozenset(),
    ("executor", "implement-change"): frozenset(
        {
            "pull-request-create",
            "pull-request-update",
            "pull-request-ready",
            "application-materialize",
        }
    ),
    ("executor", "merge-implementation-pr"): frozenset({"pull-request-merge", "ref-delete"}),
    ("executor", "merge-archive-pr"): frozenset({"pull-request-merge", "ref-delete"}),
}


def allowed_github_mutation_operations(role: str, action: str) -> frozenset[str]:
    try:
        return _ACTION_OPERATIONS[(role, action)]
    except KeyError as exc:
        raise ValueError(f"unsupported worker role/action: {role}/{action}") from exc


def mapped_role_actions() -> frozenset[RoleAction]:
    return frozenset(_ACTION_OPERATIONS)
