"""Shared durable-effect contract for machine-gated Scheduled Agent workers."""

from __future__ import annotations

from typing import Final

RoleAction = tuple[str, str]

GITHUB_MUTATION_KIND: Final = "github-mutation"

# Operations are repository-application capabilities, not model-side write tools.
# The selected action may request only the operations listed for its exact role/action.
_ACTION_OPERATIONS: Final[dict[RoleAction, frozenset[str]]] = {
    ("lead", "explore-change"): frozenset(
        {
            "issue-update",
            "issue-label-add",
        }
    ),
    ("lead", "propose-change"): frozenset(
        {
            "issue-update",
            "issue-label-add",
            "contents-upsert",
            "contents-delete",
            "ref-create",
            "ref-update",
            "pull-request-create",
            "pull-request-update",
        }
    ),
    ("lead", "resolve-question"): frozenset(
        {
            "issue-create",
            "issue-update",
            "issue-label-add",
            "contents-upsert",
            "contents-delete",
            "ref-create",
            "ref-update",
            "pull-request-create",
            "pull-request-update",
        }
    ),
    ("lead", "finalize-change"): frozenset(
        {
            "issue-create",
            "issue-update",
            "issue-label-add",
            "pull-request-create",
            "pull-request-update",
        }
    ),
    ("lead", "finalize-archive"): frozenset(
        {
            "issue-update",
            "issue-label-add",
        }
    ),
    ("reviewer", "review-openspec"): frozenset(),
    ("reviewer", "review-implementation"): frozenset(),
    ("reviewer", "review-archive"): frozenset(),
    ("executor", "implement-change"): frozenset(
        {
            "contents-upsert",
            "contents-delete",
            "ref-create",
            "ref-update",
            "ref-delete",
            "pull-request-create",
            "pull-request-update",
            "pull-request-ready",
        }
    ),
    ("executor", "merge-pr"): frozenset(
        {
            "pull-request-merge",
            "ref-delete",
        }
    ),
}


def allowed_github_mutation_operations(role: str, action: str) -> frozenset[str]:
    """Return repository-application operations allowed for one exact mapped action."""

    try:
        return _ACTION_OPERATIONS[(role, action)]
    except KeyError as exc:
        raise ValueError(f"unsupported worker role/action: {role}/{action}") from exc


def mapped_role_actions() -> frozenset[RoleAction]:
    """Return every role/action covered by the shared durable-effect contract."""

    return frozenset(_ACTION_OPERATIONS)
