"""Application-owned qualification for implementation continuation carriers.

This module is a read-only evidence/decision boundary. It owns no persisted
workflow state and performs no mutation. All implementation-carrier consumers
reuse the same fresh qualification instead of reconstructing branch identity.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, cast
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_runtime import WorkerRequest

_SHA = re.compile(r"^[0-9a-f]{40}$")
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")

CarrierDisposition = Literal[
    "QUALIFIED",
    "RECONCILIATION_REQUIRED",
    "HISTORICAL_MERGED",
    "INDETERMINATE",
]
GitHubReader = Callable[..., object | None]


@dataclass(frozen=True, slots=True)
class ImplementationCarrierQualification:
    """One fresh application-owned decision for an implementation carrier."""

    disposition: CarrierDisposition
    reason: str
    repository: str
    issue_number: int
    change: str
    action: str
    pr_number: int
    branch: str | None = None
    head_sha: str | None = None
    default_branch: str | None = None
    default_revision: str | None = None
    historical_pr_number: int | None = None

    @property
    def qualified(self) -> bool:
        return self.disposition == "QUALIFIED"

    @property
    def recognized(self) -> bool:
        return self.disposition in {
            "QUALIFIED",
            "RECONCILIATION_REQUIRED",
            "HISTORICAL_MERGED",
        }


def canonical_implementation_branch(change: str) -> str | None:
    """Return the strict initial implementation carrier branch."""

    if (
        not isinstance(change, str)
        or not change
        or change == "unset"
        or change != change.strip()
        or any(character.isspace() for character in change)
    ):
        return None
    branch = f"agent/{change}"
    if branch.startswith("refs/") or ".." in branch or "//" in branch:
        return None
    return branch


def deterministic_continuation_branch(change: str, historical_pr_number: int) -> str:
    """Derive the one allowed continuation branch from the verified history carrier."""

    return f"agent/{change}-continuation-{historical_pr_number}"


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _github_json(
    repository: str,
    token: str,
    api_path: str,
    *,
    allow_not_found: bool = False,
) -> object | None:
    """Perform one GET-only GitHub observation."""

    normalized_path = api_path.lstrip("/")
    api_url = f"https://api.github.com/repos/{repository}"
    if normalized_path:
        api_url = f"{api_url}/{normalized_path}"
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
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


def _paged_list(
    repository: str,
    token: str,
    api_path: str,
    *,
    read: GitHubReader,
) -> tuple[Mapping[str, object], ...]:
    """Exhaust one list endpoint; incomplete/malformed evidence fails closed."""

    items: list[Mapping[str, object]] = []
    page = 1
    separator = "&" if "?" in api_path else "?"
    while True:
        payload = read(
            repository,
            token,
            f"{api_path}{separator}per_page=100&page={page}",
        )
        if not isinstance(payload, list):
            raise RuntimeError("implementation carrier evidence list is incomplete")
        for raw in payload:
            item = _as_mapping(raw)
            if item is None:
                raise RuntimeError("implementation carrier evidence list is malformed")
            items.append(item)
        if len(payload) < 100:
            return tuple(items)
        page += 1


def _change_from_issue(payload: Mapping[str, object]) -> str | None:
    body = payload.get("body")
    if not isinstance(body, str):
        return None
    matches = _CHANGE_LINE.findall(body)
    return matches[0] if len(matches) == 1 else None


def _pr_has_nonclosing_issue_link(body: object, issue_number: int) -> bool:
    if not isinstance(body, str):
        return False
    return re.search(rf"(?mi)^\s*Refs\s+#{issue_number}\s*$", body) is not None


def _repository_default(
    repository: str,
    token: str,
    *,
    read: GitHubReader,
) -> tuple[str | None, str | None]:
    root = _as_mapping(cast(object, read(repository, token, "")))
    branch = None if root is None else root.get("default_branch")
    if not isinstance(branch, str) or not branch or branch.startswith("refs/"):
        return None, None
    ref = _as_mapping(
        cast(
            object,
            read(
                repository,
                token,
                f"git/ref/heads/{quote(branch, safe='/')}",
            ),
        )
    )
    obj = None if ref is None else _as_mapping(ref.get("object"))
    sha = None if obj is None else obj.get("sha")
    return branch, cast(str, sha) if _valid_sha(sha) else None


def _ref_head_sha(
    repository: str,
    token: str,
    branch: str,
    *,
    read: GitHubReader,
) -> str | None:
    ref = _as_mapping(
        cast(
            object,
            read(
                repository,
                token,
                f"git/ref/heads/{quote(branch, safe='/')}",
                allow_not_found=True,
            ),
        )
    )
    obj = None if ref is None else _as_mapping(ref.get("object"))
    sha = None if obj is None else obj.get("sha")
    return cast(str, sha) if _valid_sha(sha) else None


def _compare_is_ancestor(
    repository: str,
    token: str,
    *,
    ancestor: str,
    descendant: str,
    read: GitHubReader,
) -> bool:
    comparison = _as_mapping(
        cast(
            object,
            read(
                repository,
                token,
                f"compare/{ancestor}...{descendant}",
            ),
        )
    )
    if comparison is None:
        return False
    status = comparison.get("status")
    behind_by = comparison.get("behind_by")
    return status in {"ahead", "identical"} and behind_by == 0


def _pr_identity_is_coherent(
    pr: Mapping[str, object],
    *,
    repository: str,
    issue_number: int,
    default_branch: str,
) -> tuple[str, str] | None:
    head = _as_mapping(pr.get("head"))
    base = _as_mapping(pr.get("base"))
    head_repo = None if head is None else _as_mapping(head.get("repo"))
    base_repo = None if base is None else _as_mapping(base.get("repo"))
    branch = None if head is None else head.get("ref")
    head_sha = None if head is None else head.get("sha")
    if (
        head is None
        or base is None
        or head_repo is None
        or base_repo is None
        or head_repo.get("full_name") != repository
        or base_repo.get("full_name") != repository
        or not isinstance(branch, str)
        or not branch
        or not _valid_sha(head_sha)
        or base.get("ref") != default_branch
        or not _pr_has_nonclosing_issue_link(pr.get("body"), issue_number)
    ):
        return None
    return branch, cast(str, head_sha)


def _is_merged_pr(pr: Mapping[str, object]) -> bool:
    merged_at = pr.get("merged_at")
    return (
        pr.get("state") == "closed"
        and pr.get("merged") is True
        and _valid_sha(pr.get("merge_commit_sha"))
        and isinstance(merged_at, str)
        and bool(merged_at.strip())
    )


def _pr_active_changes(
    repository: str,
    token: str,
    pr_number: int,
    *,
    read: GitHubReader,
) -> tuple[set[str], bool]:
    files = _paged_list(
        repository,
        token,
        f"pulls/{pr_number}/files?",
        read=read,
    )
    if not files:
        return set(), False
    names: set[str] = set()
    has_non_openspec_file = False
    for file in files:
        filename = file.get("filename")
        if not isinstance(filename, str) or not filename:
            raise RuntimeError("implementation carrier file evidence is malformed")
        if filename.startswith("openspec/changes/"):
            remainder = filename.removeprefix("openspec/changes/")
            change = remainder.split("/", 1)[0]
            if change and change != "archive":
                names.add(change)
        else:
            has_non_openspec_file = True
    return names, has_non_openspec_file


def _historical_carriers(
    repository: str,
    token: str,
    *,
    issue_number: int,
    change: str,
    default_branch: str,
    default_revision: str,
    read: GitHubReader,
) -> tuple[tuple[int, Mapping[str, object]], ...]:
    canonical = canonical_implementation_branch(change)
    if canonical is None:
        return ()
    owner = repository.split("/", 1)[0]
    query = urlencode(
        {
            "state": "closed",
            "head": f"{owner}:{canonical}",
            "base": default_branch,
        }
    )
    candidates = _paged_list(repository, token, f"pulls?{query}&", read=read)
    result: list[tuple[int, Mapping[str, object]]] = []
    for summary in candidates:
        number = summary.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            continue
        pr = _as_mapping(cast(object, read(repository, token, f"pulls/{number}")))
        if pr is None:
            raise RuntimeError("historical implementation carrier evidence is incomplete")
        identity = _pr_identity_is_coherent(
            pr,
            repository=repository,
            issue_number=issue_number,
            default_branch=default_branch,
        )
        merge_sha = pr.get("merge_commit_sha")
        active_changes, _has_code = _pr_active_changes(
            repository,
            token,
            number,
            read=read,
        )
        if (
            identity is not None
            and identity[0] == canonical
            and _is_merged_pr(pr)
            and _valid_sha(merge_sha)
            and active_changes == {change}
            and _compare_is_ancestor(
                repository,
                token,
                ancestor=cast(str, merge_sha),
                descendant=default_revision,
                read=read,
            )
        ):
            result.append((number, pr))
    return tuple(result)


def _claimed_open_carriers(
    repository: str,
    token: str,
    *,
    issue_number: int,
    change: str,
    default_branch: str,
    read: GitHubReader,
) -> tuple[Mapping[str, object], ...]:
    prs = _paged_list(
        repository,
        token,
        f"pulls?{urlencode({'state': 'open', 'base': default_branch})}&",
        read=read,
    )
    canonical = canonical_implementation_branch(change)
    if canonical is None:
        return ()
    continuation = re.compile(rf"^{re.escape(canonical)}-continuation-([1-9][0-9]*)$")
    result: list[Mapping[str, object]] = []
    for pr in prs:
        identity = _pr_identity_is_coherent(
            pr,
            repository=repository,
            issue_number=issue_number,
            default_branch=default_branch,
        )
        if identity is None:
            continue
        branch, _head_sha = identity
        if branch == canonical or continuation.fullmatch(branch) is not None:
            result.append(pr)
    return tuple(result)


def _indeterminate(
    *,
    repository: str,
    source: WorkerRequest,
    change: str,
    pr_number: int,
    reason: str,
    branch: str | None = None,
    head_sha: str | None = None,
    default_branch: str | None = None,
    default_revision: str | None = None,
    historical_pr_number: int | None = None,
) -> ImplementationCarrierQualification:
    return ImplementationCarrierQualification(
        disposition="INDETERMINATE",
        reason=reason,
        repository=repository,
        issue_number=source.issue_number,
        change=change,
        action=source.action,
        pr_number=pr_number,
        branch=branch,
        head_sha=head_sha,
        default_branch=default_branch,
        default_revision=default_revision,
        historical_pr_number=historical_pr_number,
    )


def qualify_implementation_carrier(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    pr_number: int,
    current_revision: str,
    read: GitHubReader | None = None,
) -> ImplementationCarrierQualification:
    """Freshly qualify one exact implementation carrier.

    `RECONCILIATION_REQUIRED` means identity is repository-approved but the
    current default branch is not yet an ancestor of the carrier head. Only
    application/materialization may use that disposition to construct a
    reconciliation. Validation/checkpoint/merge consumers require `QUALIFIED`.

    `read` replaces transport only. The qualifier still acquires every piece
    of evidence and owns the complete semantic decision.
    """

    reader = _github_json if read is None else read
    if (
        source.issue_number <= 0
        or source.action
        not in {"implement-change", "review-implementation", "merge-implementation-pr"}
        or not isinstance(pr_number, int)
        or isinstance(pr_number, bool)
        or pr_number <= 0
        or not _valid_sha(current_revision)
    ):
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-input-incomplete",
        )
    canonical = canonical_implementation_branch(change)
    if canonical is None:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-change-invalid",
        )

    default_branch, default_revision = _repository_default(
        repository,
        token,
        read=reader,
    )
    if default_branch is None or default_revision is None or default_revision != current_revision:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-default-revision-stale",
            default_branch=default_branch,
            default_revision=default_revision,
        )

    issue = _as_mapping(
        cast(
            object,
            reader(
                repository,
                token,
                f"issues/{source.issue_number}",
            ),
        )
    )
    if issue is None or issue.get("state") != "open" or _change_from_issue(issue) != change:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-issue-change-incoherent",
            default_branch=default_branch,
            default_revision=default_revision,
        )

    pr = _as_mapping(
        cast(
            object,
            reader(
                repository,
                token,
                f"pulls/{pr_number}",
            ),
        )
    )
    if pr is None or pr.get("number") != pr_number:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-pr-missing",
            default_branch=default_branch,
            default_revision=default_revision,
        )
    identity = _pr_identity_is_coherent(
        pr,
        repository=repository,
        issue_number=source.issue_number,
        default_branch=default_branch,
    )
    if identity is None:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-pr-identity-incoherent",
            default_branch=default_branch,
            default_revision=default_revision,
        )
    branch, head_sha = identity

    historical = _historical_carriers(
        repository,
        token,
        issue_number=source.issue_number,
        change=change,
        default_branch=default_branch,
        default_revision=default_revision,
        read=reader,
    )
    if len(historical) > 1:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-historical-identity-ambiguous",
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            default_revision=default_revision,
        )
    historical_pr_number = historical[0][0] if historical else None

    active_changes, _has_code = _pr_active_changes(
        repository,
        token,
        pr_number,
        read=reader,
    )
    if _is_merged_pr(pr):
        merge_sha = pr.get("merge_commit_sha")
        if not _valid_sha(merge_sha) or not _compare_is_ancestor(
            repository,
            token,
            ancestor=cast(str, merge_sha),
            descendant=default_revision,
            read=reader,
        ):
            return _indeterminate(
                repository=repository,
                source=source,
                change=change,
                pr_number=pr_number,
                reason="carrier-merged-pr-is-not-in-current-default-history",
                branch=branch,
                head_sha=head_sha,
                default_branch=default_branch,
                default_revision=default_revision,
                historical_pr_number=historical_pr_number,
            )
        canonical_merged = historical_pr_number == pr_number and branch == canonical
        continuation_merged = (
            historical_pr_number is not None
            and pr_number != historical_pr_number
            and branch == deterministic_continuation_branch(change, historical_pr_number)
            and not any(active_change != change for active_change in active_changes)
        )
        if not canonical_merged and not continuation_merged:
            return _indeterminate(
                repository=repository,
                source=source,
                change=change,
                pr_number=pr_number,
                reason="carrier-merged-pr-is-not-approved-history",
                branch=branch,
                head_sha=head_sha,
                default_branch=default_branch,
                default_revision=default_revision,
                historical_pr_number=historical_pr_number,
            )
        return ImplementationCarrierQualification(
            disposition="HISTORICAL_MERGED",
            reason=(
                "historical-merged-carrier-qualified"
                if canonical_merged
                else "merged-continuation-carrier-qualified"
            ),
            repository=repository,
            issue_number=source.issue_number,
            change=change,
            action=source.action,
            pr_number=pr_number,
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            default_revision=default_revision,
            historical_pr_number=historical_pr_number,
        )

    if pr.get("state") != "open" or pr.get("merged") is True:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-pr-is-not-open",
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            default_revision=default_revision,
            historical_pr_number=historical_pr_number,
        )

    if historical_pr_number is None:
        if branch != canonical:
            return _indeterminate(
                repository=repository,
                source=source,
                change=change,
                pr_number=pr_number,
                reason="initial-carrier-branch-is-not-canonical",
                branch=branch,
                head_sha=head_sha,
                default_branch=default_branch,
                default_revision=default_revision,
            )
    else:
        expected_continuation = deterministic_continuation_branch(change, historical_pr_number)
        if branch != expected_continuation:
            return _indeterminate(
                repository=repository,
                source=source,
                change=change,
                pr_number=pr_number,
                reason="carrier-branch-is-not-deterministic-continuation",
                branch=branch,
                head_sha=head_sha,
                default_branch=default_branch,
                default_revision=default_revision,
                historical_pr_number=historical_pr_number,
            )

    claimed = _claimed_open_carriers(
        repository,
        token,
        issue_number=source.issue_number,
        change=change,
        default_branch=default_branch,
        read=reader,
    )
    claimed_numbers = {
        cast(int, candidate["number"])
        for candidate in claimed
        if isinstance(candidate.get("number"), int)
        and not isinstance(candidate.get("number"), bool)
    }
    if claimed_numbers != {pr_number}:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-competing-open-carrier",
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            default_revision=default_revision,
            historical_pr_number=historical_pr_number,
        )

    if _ref_head_sha(repository, token, branch, read=reader) != head_sha:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-pr-ref-head-mismatch",
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            default_revision=default_revision,
            historical_pr_number=historical_pr_number,
        )

    if (historical_pr_number is None and active_changes != {change}) or any(
        active_change != change for active_change in active_changes
    ):
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason=(
                "initial-carrier-does-not-uniquely-represent-change"
                if historical_pr_number is None
                else "carrier-competing-active-change"
            ),
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            default_revision=default_revision,
            historical_pr_number=historical_pr_number,
        )

    if _compare_is_ancestor(
        repository,
        token,
        ancestor=default_revision,
        descendant=head_sha,
        read=reader,
    ):
        disposition: CarrierDisposition = "QUALIFIED"
        reason = (
            "initial-carrier-qualified"
            if historical_pr_number is None
            else "continuation-carrier-qualified"
        )
    else:
        disposition = "RECONCILIATION_REQUIRED"
        reason = "continuation-carrier-requires-default-reconciliation"

    return ImplementationCarrierQualification(
        disposition=disposition,
        reason=reason,
        repository=repository,
        issue_number=source.issue_number,
        change=change,
        action=source.action,
        pr_number=pr_number,
        branch=branch,
        head_sha=head_sha,
        default_branch=default_branch,
        default_revision=default_revision,
        historical_pr_number=historical_pr_number,
    )


__all__ = [
    "CarrierDisposition",
    "GitHubReader",
    "ImplementationCarrierQualification",
    "canonical_implementation_branch",
    "deterministic_continuation_branch",
    "qualify_implementation_carrier",
]
