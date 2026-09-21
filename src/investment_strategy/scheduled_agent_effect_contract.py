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


def _evidence_target(action: Action, result: ResultKind) -> EvidenceTarget:
    """Map every legal transition to a positive evidence target."""

    if result in {
        ResultKind.BLOCKED,
        ResultKind.HUMAN_DECISION_REQUIRED,
        ResultKind.NO_GO,
        ResultKind.RESEARCH_REQUIRED,
        ResultKind.SPEC_BLOCKER,
    }:
        return EvidenceTarget.DEFAULT_BRANCH
    if action is Action.FINALIZE_CHANGE and result is ResultKind.ARCHIVE_READY:
        return EvidenceTarget.ARCHIVE_PR_HEAD
    if action is Action.REVIEW_ARCHIVE and result is ResultKind.PASS:
        return EvidenceTarget.ARCHIVE_PR_HEAD
    if action is Action.MERGE_ARCHIVE_PR and result is ResultKind.MERGED:
        return EvidenceTarget.MERGED_PR_HEAD
    if action is Action.MERGE_IMPLEMENTATION_PR and result is ResultKind.MERGED:
        return EvidenceTarget.MERGED_PR_HEAD
    if action in {Action.IMPLEMENT_CHANGE, Action.REVIEW_IMPLEMENTATION}:
        return EvidenceTarget.IMPLEMENTATION_PR_HEAD
    if action is Action.MERGE_IMPLEMENTATION_PR:
        return EvidenceTarget.DEFAULT_BRANCH
    return EvidenceTarget.DEFAULT_BRANCH


def _missing_effect(action: Action, result: ResultKind) -> str:
    """Name the next repository consequence derived from fresh state."""

    if action is Action.FINALIZE_CHANGE and result is ResultKind.ARCHIVE_READY:
        return "archive-pr-create-or-reuse"
    if action in {Action.IMPLEMENT_CHANGE, Action.RESOLVE_QUESTION}:
        return "application-materialize-or-formal-result"
    if action in {
        Action.MERGE_IMPLEMENTATION_PR,
        Action.MERGE_ARCHIVE_PR,
    }:
        return "merge-carrier-or-formal-result"
    return "formal-result"


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
                    else "formal-result-and-evidence"
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
