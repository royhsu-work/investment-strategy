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
from types import MappingProxyType
from typing import Final

from investment_strategy.scheduled_agent_action_model import (
    TRANSITIONS,
    Action,
    ResultKind,
)

RoleAction = tuple[str, str]
GITHUB_MUTATION_KIND: Final = "github-mutation"


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


_EVIDENCE_TARGET_OVERRIDES: Final[dict[tuple[Action, ResultKind], EvidenceTarget]] = {
    (
        Action.PROPOSE_CHANGE,
        ResultKind.READY_FOR_OPENSPEC_REVIEW,
    ): EvidenceTarget.MATERIALIZED_REVISION,
    (
        Action.RESOLVE_QUESTION,
        ResultKind.READY_FOR_OPENSPEC_REVIEW,
    ): EvidenceTarget.MATERIALIZED_REVISION,
    (Action.FINALIZE_CHANGE, ResultKind.ARCHIVE_READY): EvidenceTarget.ARCHIVE_PR_HEAD,
    (Action.REVIEW_ARCHIVE, ResultKind.PASS): EvidenceTarget.ARCHIVE_PR_HEAD,
    (Action.MERGE_ARCHIVE_PR, ResultKind.MERGED): EvidenceTarget.MERGED_PR_HEAD,
    (Action.MERGE_IMPLEMENTATION_PR, ResultKind.MERGED): EvidenceTarget.MERGED_PR_HEAD,
    (Action.FINALIZE_ARCHIVE, ResultKind.LIFECYCLE_COMPLETE): EvidenceTarget.MERGED_PR_HEAD,
    (Action.IMPLEMENT_CHANGE, ResultKind.READY): EvidenceTarget.IMPLEMENTATION_PR_HEAD,
    (
        Action.IMPLEMENT_CHANGE,
        ResultKind.MORE_IMPLEMENTATION_REQUIRED,
    ): EvidenceTarget.IMPLEMENTATION_PR_HEAD,
    (Action.REVIEW_IMPLEMENTATION, ResultKind.PASS): EvidenceTarget.IMPLEMENTATION_PR_HEAD,
    (Action.REVIEW_IMPLEMENTATION, ResultKind.FINDINGS): EvidenceTarget.IMPLEMENTATION_PR_HEAD,
}


_MISSING_EFFECT_OVERRIDES: Final[dict[tuple[Action, ResultKind], str]] = {
    (
        Action.PROPOSE_CHANGE,
        ResultKind.READY_FOR_OPENSPEC_REVIEW,
    ): "application-materialize-or-formal-result",
    (Action.FINALIZE_CHANGE, ResultKind.ARCHIVE_READY): "archive-pr-create-or-reuse",
}


def _build_evidence_targets() -> dict[tuple[Action, ResultKind], EvidenceTarget]:
    targets = {
        (action, result): EvidenceTarget.DEFAULT_BRANCH
        for action, results in TRANSITIONS.items()
        for result in results
    }
    targets.update(_EVIDENCE_TARGET_OVERRIDES)
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
