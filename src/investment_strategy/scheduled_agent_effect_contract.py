"""Action-scoped durable-effect capabilities."""

from __future__ import annotations

from typing import Final

RoleAction = tuple[str, str]
GITHUB_MUTATION_KIND: Final = "github-mutation"

_ACTION_OPERATIONS: Final[dict[RoleAction, frozenset[str]]] = {
    ("lead", "explore-change"): frozenset({"issue-update", "issue-label-add"}),
    ("lead", "propose-change"): frozenset({"issue-update", "issue-label-add"}),
    ("lead", "resolve-question"): frozenset(
        {
            "issue-update",
            "issue-label-add",
            "pull-request-create",
            "pull-request-update",
        }
    ),
    ("lead", "finalize-change"): frozenset(
        {
            "issue-update",
            "issue-label-add",
            "pull-request-create",
            "pull-request-update",
        }
    ),
    ("lead", "finalize-archive"): frozenset({"issue-update", "issue-label-add"}),
    ("reviewer", "review-openspec"): frozenset(),
    ("reviewer", "review-implementation"): frozenset(),
    ("reviewer", "review-archive"): frozenset(),
    ("executor", "implement-change"): frozenset(
        {
            "ref-create",
            "ref-update",
            "pull-request-create",
            "pull-request-update",
            "pull-request-ready",
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
