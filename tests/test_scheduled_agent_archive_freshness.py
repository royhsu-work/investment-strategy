"""Archive freshness is an independent source predicate, even before a PR."""

from __future__ import annotations

from typing import cast

import pytest

import investment_strategy.scheduled_agent_application_bridge as bridge
import investment_strategy.scheduled_agent_effects as effects
import investment_strategy.scheduled_agent_validation_resource as validation
from investment_strategy.scheduled_agent_archive_freshness import archive_tree_matches_change

_CHANGE = "restore-no-work-idle-discovery"
_SOURCE = "a" * 40
_BRANCH = "b" * 40
_SOURCE_TREE_SHA = "c" * 40
_ARCHIVE_TREE_SHA = "d" * 40


def _tree(*, archived: bool, tasks_sha: str = "1" * 40) -> dict[str, object]:
    prefix = (
        f"openspec/changes/archive/2026-11-08-{_CHANGE}"
        if archived
        else f"openspec/changes/{_CHANGE}"
    )
    return {
        "truncated": False,
        "tree": [
            {"path": f"{prefix}/tasks.md", "type": "blob", "sha": tasks_sha},
            {"path": f"{prefix}/proposal.md", "type": "blob", "sha": "2" * 40},
            {"path": "README.md", "type": "blob", "sha": "3" * 40},
        ],
    }


@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        ("exact", True),
        ("stale-tasks", False),
        ("incomplete-tree", False),
        ("extra-archived-file", False),
        ("two-archive-dirs", False),
        ("active-still-present", False),
        ("unrelated-branch-write", False),
        ("unapproved-canonical-write", False),
    ],
)
def test_archive_tree_requires_byte_identical_current_change(variant: str, expected: bool) -> None:
    source = _tree(archived=False)
    archive = _tree(archived=True, tasks_sha="0" * 40 if variant == "stale-tasks" else "1" * 40)
    entries = cast(list[dict[str, object]], archive["tree"])
    if variant == "incomplete-tree":
        archive["truncated"] = True
    elif variant == "extra-archived-file":
        entries.append(
            {
                "path": f"openspec/changes/archive/2026-11-08-{_CHANGE}/extra.md",
                "type": "blob",
                "sha": "4" * 40,
            }
        )
    elif variant == "two-archive-dirs":
        entries.append(
            {
                "path": f"openspec/changes/archive/2026-11-07-{_CHANGE}/tasks.md",
                "type": "blob",
                "sha": "1" * 40,
            }
        )
    elif variant == "active-still-present":
        entries.append(
            {
                "path": f"openspec/changes/{_CHANGE}/tasks.md",
                "type": "blob",
                "sha": "1" * 40,
            }
        )
    elif variant == "unrelated-branch-write":
        entries[-1]["sha"] = "5" * 40
    elif variant == "unapproved-canonical-write":
        entries.append(
            {
                "path": "openspec/specs/unapproved/spec.md",
                "type": "blob",
                "sha": "6" * 40,
            }
        )
    assert archive_tree_matches_change(source, archive, _CHANGE) is expected


def test_archive_tree_allows_only_canonicalized_change_capabilities() -> None:
    source, archive = _tree(archived=False), _tree(archived=True)
    cast(list[dict[str, object]], source["tree"]).append(
        {
            "path": f"openspec/changes/{_CHANGE}/specs/approved/spec.md",
            "type": "blob",
            "sha": "4" * 40,
        }
    )
    cast(list[dict[str, object]], archive["tree"]).append(
        {
            "path": f"openspec/changes/archive/2026-11-08-{_CHANGE}/specs/approved/spec.md",
            "type": "blob",
            "sha": "4" * 40,
        }
    )
    cast(list[dict[str, object]], archive["tree"]).append(
        {"path": "openspec/specs/approved/spec.md", "type": "blob", "sha": "7" * 40}
    )
    assert archive_tree_matches_change(source, archive, _CHANGE)


@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        ("exact", True),
        ("diverged", False),
        ("stale-tasks", False),
        ("truncated", False),
    ],
)
def test_archive_source_proof_is_required_before_pr_lookup(
    monkeypatch: pytest.MonkeyPatch, variant: str, expected: bool
) -> None:
    calls: list[str] = []

    def read(_repo: str, _token: str, path: str, **_kwargs: object) -> object:
        calls.append(path)
        if path == f"compare/{_SOURCE}...{_BRANCH}":
            return {
                "status": "diverged" if variant == "diverged" else "ahead",
                "behind_by": 0,
                "ahead_by": 1,
                "base_commit": {"sha": _SOURCE},
            }
        if path == f"git/commits/{_SOURCE}":
            return {"tree": {"sha": _SOURCE_TREE_SHA}}
        if path == f"git/commits/{_BRANCH}":
            return {"tree": {"sha": _ARCHIVE_TREE_SHA}}
        if path == f"git/trees/{_SOURCE_TREE_SHA}?recursive=1":
            return _tree(archived=False)
        if path == f"git/trees/{_ARCHIVE_TREE_SHA}?recursive=1":
            tree = _tree(
                archived=True,
                tasks_sha="0" * 40 if variant == "stale-tasks" else "1" * 40,
            )
            if variant == "truncated":
                tree["truncated"] = True
            return tree
        raise AssertionError(f"unexpected API path: {path}")

    monkeypatch.setattr(effects, "_github_json", read)
    assert (
        effects.archive_branch_matches_current_source(
            repository="owner/repo",
            token="fixture",  # noqa: S106
            change=_CHANGE,
            source_sha=_SOURCE,
            branch_sha=_BRANCH,
        )
        is expected
    )
    assert not any("pulls" in path for path in calls)


def test_stale_branch_does_not_become_missing_archive_pr_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch = f"agent/archive-{_CHANGE}"
    monkeypatch.setattr(bridge, "_fresh_branch_head", lambda *_args: _BRANCH)
    monkeypatch.setattr(
        bridge,
        "archive_branch_matches_current_source",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        bridge,
        "_fresh_pull_requests",
        lambda *_args, **_kwargs: pytest.fail("stale source cannot reach Archive PR lookup"),
    )
    assert bridge._fresh_archive_state(
        "owner/repo",
        "fixture",
        issue_number=322,
        change=_CHANGE,
        current_revision=_SOURCE,
        default_branch="main",
    ) == ("stale-branch", branch, _BRANCH)


def test_historical_task_checkpoint_does_not_authorize_new_source_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = validation.WorkProductFile(f"openspec/changes/{_CHANGE}/tasks.md", "1" * 40, "1" * 40)
    new_source = validation.WorkProductFile("src/investment_strategy/runtime.py", "2" * 40, None)
    monkeypatch.setattr(validation, "_content_sha_at", lambda *_args, **_kwargs: "1" * 40)
    monkeypatch.setattr(
        validation,
        "_content_text_at",
        lambda *_args, **_kwargs: "## 6. Verified slice\n- [x] 6.1 Completed\n",
    )

    def predicate(files: tuple[validation.WorkProductFile, ...]) -> bool:
        return validation.completed_task_bookkeeping_is_current(
            "owner/repo",
            "fixture",
            change=_CHANGE,
            revision=_SOURCE,
            files=files,
        )

    assert predicate((task,))
    assert not predicate((task, new_source))
