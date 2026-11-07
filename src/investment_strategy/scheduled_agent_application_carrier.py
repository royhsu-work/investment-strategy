"""Application-owned qualification for deterministic same-Change carriers.

This module is a read-only evidence/decision boundary. It owns no persisted
workflow state and performs no mutation. OpenSpec and implementation consumers
reuse the same fresh canonical / merged-history / continuation qualification
instead of reconstructing branch identity independently.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_formal_result import parse_formal_result
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    normalize_github_issue,
)

_SHA = re.compile(r"^[0-9a-f]{40}$")
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")

CarrierDisposition = Literal[
    "QUALIFIED",
    "RECONCILIATION_REQUIRED",
    "HISTORICAL_MERGED",
    "INDETERMINATE",
]
RecoveryClassification = Literal["RECOVERABLE", "INDETERMINATE", "UNSAFE"]
DivergenceEvidence = Literal["SAFE", "NEEDS_RECONCILIATION", "INDETERMINATE"]
GitHubReader = Callable[..., object | None]

_CHANGE_CARRIER_SOURCES = frozenset(
    {
        ("lead", "propose-change"),
        ("lead", "resolve-question"),
        ("reviewer", "review-openspec"),
        ("executor", "implement-change"),
        ("reviewer", "review-implementation"),
        ("executor", "merge-implementation-pr"),
    }
)
_IMPLEMENTATION_CARRIER_SOURCES = frozenset(
    {
        ("executor", "implement-change"),
        ("reviewer", "review-implementation"),
        ("executor", "merge-implementation-pr"),
    }
)
_OPENSPEC_CARRIER_SOURCES = frozenset(
    {
        ("lead", "propose-change"),
        ("lead", "resolve-question"),
        ("reviewer", "review-openspec"),
    }
)


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

    @property
    def recovery_classification(self) -> RecoveryClassification:
        """Diagnostic only; never a new routing or acceptance authority."""

        if self.recognized:
            return "RECOVERABLE"
        if self.reason in {
            "carrier-competing-open-carrier",
            "carrier-pr-ref-head-mismatch",
            "carrier-merged-pr-is-not-approved-history",
            "carrier-pr-identity-incoherent",
            "carrier-competing-active-change",
        }:
            return "UNSAFE"
        return "INDETERMINATE"


@dataclass(frozen=True, slots=True)
class ReviewedImplementationConsequence:
    """Exact review PASS head and optional already-posted MERGED consequence."""

    head_sha: str
    merged_sha: str | None


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


def deterministic_supersession_branch(change: str, retired_pr_number: int) -> str:
    """Distinct successor to a formally rejected and closed-unmerged carrier."""

    return f"agent/{change}-supersedes-{retired_pr_number}"


def current_reviewed_implementation_head(
    repository: str,
    token: str,
    *,
    source: WorkerRequest,
    change: str,
    current_revision: str,
    read: GitHubReader,
) -> ReviewedImplementationConsequence | None:
    """Find the exact reviewed work-product SHA for a pending merge Action.

    A Change may have multiple already-merged continuation PRs.  The current
    PASS predecessor, not branch order or an arbitrary merged candidate, owns
    the next merge consequence.  The caller still qualifies the PR and gates.
    """

    if source.action != "merge-implementation-pr" or not _valid_sha(current_revision):
        return None
    issue = _as_mapping(cast(object, read(repository, token, f"issues/{source.issue_number}")))
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.change != change
        or observation.routing
        not in {("executor", "merge-implementation-pr"), ("lead", "finalize-change")}
    ):
        return None
    comments = _paged_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created&direction=asc&",
        read=read,
    )
    events = tuple(
        event
        for comment in comments
        if (event := parse_formal_result(comment, current_revision=current_revision)) is not None
    )
    if not events:
        return None
    reviewed = None
    merged_revision = None
    blocked_revisions: list[tuple[str, str]] = []
    for offset, event in enumerate(reversed(events)):
        if (
            not event.valid
            or event.issue_number != source.issue_number
            or event.change != change
            or not _valid_sha(event.revision)
        ):
            return None
        if (event.role, event.action, event.result_kind) == (
            "reviewer",
            "review-implementation",
            "pass",
        ):
            if event.successor != ("executor", "merge-implementation-pr"):
                return None
            reviewed = event
            break
        if (event.role, event.action, event.result_kind) == (
            "executor",
            "merge-implementation-pr",
            "merged",
        ):
            # Formal MERGED precedes the derived route patch and remains the
            # current postcondition after it.  This is not a second merge.
            if (
                offset != 0
                or merged_revision is not None
                or event.successor != ("lead", "finalize-change")
            ):
                return None
            merged_revision = event.revision
            continue
        # A blocked merge is a legal self-loop, not a new review.  New
        # semantic intents carry DEFAULT_BRANCH; historical formal envelopes
        # may carry the exact reviewed PR HEAD.  Neither creates a new PASS.
        if (event.role, event.action) != (
            "executor",
            "merge-implementation-pr",
        ) or (
            event.result_kind != "blocked"
            or event.successor != ("executor", "merge-implementation-pr")
            or not _valid_sha(event.default_branch_revision)
        ):
            return None
        if event.default_branch_revision != current_revision and not _compare_is_ancestor(
            repository,
            token,
            ancestor=cast(str, event.default_branch_revision),
            descendant=current_revision,
            read=read,
        ):
            return None
        blocked_revisions.append(
            (cast(str, event.revision), cast(str, event.default_branch_revision))
        )
    if (
        reviewed is None
        or not _valid_sha(reviewed.default_branch_revision)
        or any(
            revision not in {reviewed.revision, default} for revision, default in blocked_revisions
        )
        or (observation.routing == ("lead", "finalize-change") and merged_revision is None)
    ):
        return None
    if reviewed.default_branch_revision != current_revision and not _compare_is_ancestor(
        repository,
        token,
        ancestor=cast(str, reviewed.default_branch_revision),
        descendant=current_revision,
        read=read,
    ):
        return None
    return ReviewedImplementationConsequence(cast(str, reviewed.revision), merged_revision)


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


def _changed_paths(
    repository: str,
    token: str,
    *,
    ancestor: str,
    descendant: str,
    read: GitHubReader,
) -> frozenset[str] | None:
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
        return None
    if (
        comparison.get("status") not in {"ahead", "identical"}
        or comparison.get("behind_by") != 0
        or comparison.get("too_large") is True
    ):
        return None
    files = comparison.get("files")
    if not isinstance(files, list) or len(files) >= 300:
        return None
    paths: set[str] = set()
    for raw_file in files:
        file = _as_mapping(raw_file)
        filename = None if file is None else file.get("filename")
        if not isinstance(filename, str) or not filename:
            return None
        paths.add(filename)
        if file is not None and "previous_filename" in file:
            previous = file["previous_filename"]
            if not isinstance(previous, str) or not previous:
                return None
            paths.add(previous)
    return frozenset(paths)


def _divergence_evidence(
    repository: str,
    token: str,
    *,
    pr: Mapping[str, object],
    head_sha: str,
    default_revision: str,
    read: GitHubReader,
) -> DivergenceEvidence:
    """Prove an open PR can integrate an advanced main without moving its HEAD.

    GitHub's current mergeability is necessary but not sufficient: the exact
    merge base and both complete changed-path sets must also be established.
    Overlap, conflict, unknown mergeability, or truncated comparison evidence
    never silently acquires the existing exact-head review's authority.
    """

    # A PR head already contained in main is an observed integration relation,
    # not an unknown GitHub mergeability calculation. The branch can be
    # reconciled by its owner without treating this as a current merge PASS.
    if _compare_is_ancestor(
        repository, token, ancestor=head_sha, descendant=default_revision, read=read
    ):
        return "NEEDS_RECONCILIATION"
    if pr.get("mergeable") is False:
        return "NEEDS_RECONCILIATION"
    if pr.get("mergeable") is not True:
        return "INDETERMINATE"
    comparison = _as_mapping(read(repository, token, f"compare/{head_sha}...{default_revision}"))
    merge_base = None if comparison is None else _as_mapping(comparison.get("merge_base_commit"))
    ancestor = None if merge_base is None else merge_base.get("sha")
    if (
        comparison is None
        or comparison.get("status") != "diverged"
        or not _valid_sha(ancestor)
        or not _compare_is_ancestor(
            repository, token, ancestor=cast(str, ancestor), descendant=head_sha, read=read
        )
        or not _compare_is_ancestor(
            repository,
            token,
            ancestor=cast(str, ancestor),
            descendant=default_revision,
            read=read,
        )
    ):
        return "INDETERMINATE"
    main_paths = _changed_paths(
        repository, token, ancestor=cast(str, ancestor), descendant=default_revision, read=read
    )
    carrier_paths = _changed_paths(
        repository, token, ancestor=cast(str, ancestor), descendant=head_sha, read=read
    )
    if main_paths is None or carrier_paths is None or not carrier_paths:
        return "INDETERMINATE"
    return "SAFE" if main_paths.isdisjoint(carrier_paths) else "NEEDS_RECONCILIATION"


def _disjoint_divergence_is_mergeable(
    repository: str,
    token: str,
    *,
    pr: Mapping[str, object],
    head_sha: str,
    default_revision: str,
    read: GitHubReader,
) -> bool:
    """Compatibility predicate; application qualification retains unknown evidence."""

    return (
        _divergence_evidence(
            repository,
            token,
            pr=pr,
            head_sha=head_sha,
            default_revision=default_revision,
            read=read,
        )
        == "SAFE"
    )


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


def _pr_base_is_current(
    pr: Mapping[str, object],
    *,
    default_revision: str,
) -> bool:
    """Require an open carrier to target the freshly observed default head."""

    base = _as_mapping(pr.get("base"))
    return base is not None and base.get("sha") == default_revision


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
    stop_before_branch: str | None = None,
) -> tuple[tuple[int, Mapping[str, object]], ...] | None:
    """Return the unique merged carrier lineage, or None when history is ambiguous."""

    canonical = canonical_implementation_branch(change)
    if canonical is None:
        return ()

    owner = repository.split("/", 1)[0]
    expected_branch = canonical
    result: list[tuple[int, Mapping[str, object]]] = []
    seen_numbers: set[int] = set()

    while True:
        if expected_branch == stop_before_branch:
            return tuple(result)
        query = urlencode(
            {
                "state": "closed",
                "head": f"{owner}:{expected_branch}",
                "base": default_branch,
            }
        )
        candidates = _paged_list(repository, token, f"pulls?{query}&", read=read)
        matches: list[tuple[int, Mapping[str, object]]] = []
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
            change_identity_ok = (
                active_changes == {change}
                if expected_branch == canonical
                else not any(active_change != change for active_change in active_changes)
            )
            if (
                identity is not None
                and identity[0] == expected_branch
                and _is_merged_pr(pr)
                and _valid_sha(merge_sha)
                and change_identity_ok
                and _compare_is_ancestor(
                    repository,
                    token,
                    ancestor=cast(str, merge_sha),
                    descendant=default_revision,
                    read=read,
                )
            ):
                matches.append((number, pr))

        if len(matches) > 1:
            return None
        if not matches:
            # An unmerged retired carrier is not a merged ancestor. It may,
            # however, identify exactly one later merged supersession when
            # application-accepted retirement evidence is independently proven.
            # This is historical lineage discovery,
            # never permission to use the retired HEAD as an implementation.
            retired_numbers = []
            for summary in candidates:
                number = summary.get("number")
                if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                    continue
                detail = _as_mapping(read(repository, token, f"pulls/{number}"))
                if (
                    detail is not None
                    and detail.get("state") == "closed"
                    and detail.get("merged") is False
                    and detail.get("merged_at") is None
                    and _pr_identity_is_coherent(
                        detail,
                        repository=repository,
                        issue_number=issue_number,
                        default_branch=default_branch,
                    )
                    is not None
                ):
                    retired_numbers.append(number)
            if len(retired_numbers) > 1:
                return None
            if not retired_numbers:
                return tuple(result)
            retired_number = retired_numbers[0]
            retired_seen: set[int] = set()
            while True:
                if retired_number in retired_seen:
                    return None
                retired_seen.add(retired_number)
                if not _formally_superseded_closed_carrier(
                    repository,
                    token,
                    issue_number=issue_number,
                    change=change,
                    default_branch=default_branch,
                    historical_pr_number=result[-1][0] if result else None,
                    retired_number=retired_number,
                    read=read,
                ):
                    return tuple(result)
                supersession_branch = deterministic_supersession_branch(change, retired_number)
                replacement_query = urlencode(
                    {
                        "state": "closed",
                        "head": f"{owner}:{supersession_branch}",
                        "base": default_branch,
                    }
                )
                replacements = _paged_list(
                    repository, token, f"pulls?{replacement_query}&", read=read
                )
                if len(replacements) > 1:
                    return None
                if not replacements:
                    return tuple(result)
                number = replacements[0].get("number")
                if (
                    not isinstance(number, int)
                    or isinstance(number, bool)
                    or number <= retired_number
                    or number in seen_numbers
                ):
                    return None
                pr = _as_mapping(read(repository, token, f"pulls/{number}"))
                if pr is None:
                    raise RuntimeError("supersession historical PR evidence is incomplete")
                identity = _pr_identity_is_coherent(
                    pr,
                    repository=repository,
                    issue_number=issue_number,
                    default_branch=default_branch,
                )
                if identity is None or identity[0] != supersession_branch:
                    return None
                if pr.get("state") == "closed" and pr.get("merged") is False:
                    if pr.get("merged_at") is not None:
                        return None
                    retired_number = number
                    continue
                merge_sha = pr.get("merge_commit_sha")
                active_changes, _has_code = _pr_active_changes(repository, token, number, read=read)
                if (
                    not _is_merged_pr(pr)
                    or any(active != change for active in active_changes)
                    or not _valid_sha(merge_sha)
                    or not _compare_is_ancestor(
                        repository,
                        token,
                        ancestor=cast(str, merge_sha),
                        descendant=default_revision,
                        read=read,
                    )
                ):
                    return None
                break
            if number in seen_numbers:
                return None
            seen_numbers.add(number)
            result.append((number, pr))
            expected_branch = deterministic_continuation_branch(change, number)
            continue

        number, pr = matches[0]
        if number in seen_numbers:
            return None
        seen_numbers.add(number)
        result.append((number, pr))
        expected_branch = deterministic_continuation_branch(change, number)


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
    supersession = re.compile(rf"^{re.escape(canonical)}-supersedes-([1-9][0-9]*)$")
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
        if (
            branch == canonical
            or continuation.fullmatch(branch) is not None
            or supersession.fullmatch(branch) is not None
        ):
            result.append(pr)
    return tuple(result)


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result if result.utcoffset() is not None else None


def _canonical_intent_effect_json(raw_intent: str) -> str | None:
    """Compare accepted effect values, not incidental inner JSON serialization.

    The immutable request body and accepted decision retain their own exact
    hashes. Only the schema-defined nested `payload_json` field is decoded for
    semantic equality; all other intent fields remain in the comparison.
    """

    try:
        intent = json.loads(raw_intent)
        if not isinstance(intent, dict) or not isinstance(intent.get("requested_effects"), list):
            return None
        normalized_effects = []
        for effect in intent["requested_effects"]:
            if not isinstance(effect, dict) or not isinstance(effect.get("payload_json"), str):
                return None
            payload = json.loads(effect["payload_json"])
            if not isinstance(payload, dict):
                return None
            normalized_effects.append(
                {
                    **effect,
                    "payload_json": json.dumps(payload, sort_keys=True, separators=(",", ":")),
                }
            )
    except (TypeError, ValueError):
        return None
    intent["requested_effects"] = normalized_effects
    return json.dumps(intent, sort_keys=True, separators=(",", ":"))


def _accepted_formal_result_is_proven(
    repository: str,
    token: str,
    *,
    issue_number: int,
    change: str,
    retired_number: int,
    retired_branch: str,
    retired_head: str | None = None,
    event: object,
    comments: tuple[Mapping[str, object], ...],
    read: GitHubReader,
) -> bool:
    """Bind a formal transition to one immutable accepted Application intent.

    A bot-authored formal comment alone is not proof of Application acceptance.
    This reuses the existing decision/ingress parsers and checks their source
    objects, including the exact request body hash, without creating state.
    """

    # Import at call time because the Application effects/bridge modules use
    # this carrier qualifier. No competing parser or new authority is added.
    from investment_strategy.scheduled_agent_application_bridge import (
        dispatch_correlation_for,
        parse_application_request,
    )
    from investment_strategy.scheduled_agent_effects import (
        parse_application_decision,
        semantic_intent_payload,
    )

    correlation = getattr(event, "application_correlation", None)
    parts = correlation.split(":") if isinstance(correlation, str) else []
    role = getattr(event, "role", None)
    action = getattr(event, "action", None)
    result = getattr(event, "result_kind", None)
    default_revision = getattr(event, "default_branch_revision", None)
    if (
        len(parts) != 8
        or parts[0] != "application"
        or not parts[1].isdigit()
        or parts[2:7] != [str(issue_number), change, role, action, result]
        or parts[7] != default_revision
        or not _valid_sha(default_revision)
    ):
        return False
    request_id = int(parts[1])
    decisions = []
    for comment in comments:
        user = _as_mapping(comment.get("user"))
        app = _as_mapping(comment.get("performed_via_github_app"))
        if (
            user is None
            or user.get("login") != "github-actions[bot]"
            or app is None
            or app.get("slug") != "github-actions"
        ):
            continue
        decision = parse_application_decision(comment.get("body"))
        if decision is not None and decision.request_comment_id == request_id:
            decisions.append(decision)
    if len(decisions) != 1:
        return False
    decision = decisions[0]
    if (
        decision.disposition != "ACCEPTED"
        or (decision.issue_number, decision.change) != (issue_number, change)
        or (decision.role, decision.action, decision.result_kind) != (role, action, result)
        or (
            decision.authorization_revision != default_revision
            and not _compare_is_ancestor(
                repository,
                token,
                ancestor=decision.authorization_revision,
                descendant=cast(str, default_revision),
                read=read,
            )
        )
    ):
        return False
    request = _as_mapping(read(repository, token, f"issues/comments/{request_id}"))
    if request is None or request.get("id") != request_id:
        return False
    user = _as_mapping(request.get("user"))
    app = _as_mapping(request.get("performed_via_github_app"))
    body = request.get("body")
    if (
        user is None
        or user.get("login") != repository.split("/", 1)[0]
        or app is None
        or app.get("slug") != "chatgpt-codex-connector"
        or not isinstance(body, str)
        or hashlib.sha256(body.encode("utf-8")).hexdigest() != decision.request_body_sha256
    ):
        return False
    try:
        ingress = parse_application_request(body)
        if ingress is None:
            return False
        source = WorkerRequest(issue_number, cast(str, role), cast(str, action))
        ingress_result = json.loads(ingress.raw_worker_result)
        if not isinstance(ingress_result, dict):
            return False
        # The worker's real EFFECT_REQUEST is versionless. The Application
        # adds this owned projection marker when accepting the same semantic
        # result; the raw request body/hash above remains untouched.
        ingress_result.setdefault("_semantic_intent_version", 2)
        ingress_intent = _canonical_intent_effect_json(
            semantic_intent_payload(json.dumps(ingress_result))
        )
        accepted_intent = _canonical_intent_effect_json(decision.raw_worker_result)
        if (
            ingress.authorization_revision != decision.authorization_revision
            or ingress.dispatch_correlation
            != dispatch_correlation_for(repository, source, decision.authorization_revision)
            or ingress_intent is None
            or ingress_intent != accepted_intent
        ):
            return False
        intent = json.loads(decision.raw_worker_result)
    except (TypeError, ValueError):
        return False
    if (
        not isinstance(intent, Mapping)
        or (intent.get("issue_number"), intent.get("role"), intent.get("action"))
        != (issue_number, role, action)
        or (intent.get("change"), intent.get("result_kind")) != (change, result)
    ):
        return False
    if (role, action, result) == ("executor", "implement-change", "ready"):
        effects = intent.get("requested_effects")
        if not isinstance(effects, list):
            return False
        carriers = []
        for effect in effects:
            if not isinstance(effect, Mapping) or effect.get("kind") != "github-mutation":
                continue
            raw = effect.get("payload_json")
            try:
                payload = json.loads(raw) if isinstance(raw, str) else None
            except ValueError:
                return False
            if (
                isinstance(payload, Mapping)
                and payload.get("operation") == "application-materialize"
            ):
                carriers.append(payload)
        if len(carriers) != 1 or (carriers[0].get("pr_number"), carriers[0].get("branch")) != (
            retired_number,
            retired_branch,
        ):
            return False
    if (role, action, result) == ("lead", "resolve-question", "ready"):
        # A Lead resolution can retire an already-reviewed carrier without
        # manufacturing a Reviewer FINDINGS.  The intent, not PR closure alone,
        # must name one exact existing PR/head and request only its closure.
        effects = intent.get("requested_effects")
        if not isinstance(effects, list) or len(effects) != 1 or retired_head is None:
            return False
        effect = effects[0]
        if not isinstance(effect, Mapping) or effect.get("kind") != "github-mutation":
            return False
        raw = effect.get("payload_json")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else None
        except ValueError:
            return False
        if not isinstance(payload, Mapping) or (
            payload.get("issue_number"),
            payload.get("operation"),
            payload.get("number"),
            payload.get("expected_head_sha"),
            payload.get("fields"),
        ) != (
            issue_number,
            "pull-request-update",
            retired_number,
            retired_head,
            {"state": "closed"},
        ):
            return False
    return True


def _accepted_lead_retirement(
    repository: str,
    token: str,
    *,
    issue_number: int,
    change: str,
    retired_number: int,
    retired_branch: str,
    retired_head: str,
    closed_at: datetime,
    comments: tuple[Mapping[str, object], ...],
    read: GitHubReader,
) -> bool:
    """Prove one application-owned closure, independent of older review outcome.

    Exact PR/head, typed Lead READY, accepted close intent, and observed
    closed-unmerged state establish retirement.  No old PASS or FINDINGS is
    transferred to the successor; its fresh gates remain mandatory.
    """

    matching = []
    for comment in comments:
        event = parse_formal_result(comment, current_revision=None)
        if (
            event is None
            or not event.valid
            or (event.issue_number, event.change, event.role, event.action)
            != (issue_number, change, "lead", "resolve-question")
            or event.result_kind != "ready"
            or event.successor != ("executor", "implement-change")
        ):
            continue
        occurred = _timestamp(comment.get("created_at"))
        if occurred is None or occurred < closed_at:
            continue
        if _accepted_formal_result_is_proven(
            repository,
            token,
            issue_number=issue_number,
            change=change,
            retired_number=retired_number,
            retired_branch=retired_branch,
            retired_head=retired_head,
            event=event,
            comments=comments,
            read=read,
        ):
            matching.append(event)
    return len(matching) == 1


def _formally_superseded_closed_carrier(
    repository: str,
    token: str,
    *,
    issue_number: int,
    change: str,
    default_branch: str,
    historical_pr_number: int | None,
    retired_number: int,
    read: GitHubReader,
    visited: frozenset[int] = frozenset(),
) -> bool:
    """Prove retirement without giving a closed PR or prose any routing authority.

    Either the existing accepted READY -> Reviewer FINDINGS transition or one
    accepted Lead READY exact-head closure effect must justify retirement.
    No past READY, PASS, CI, or old branch head is transferred to replacement.
    """

    # Every generation is independently retired. A newer supersession is not
    # authorized merely because its own predecessor had once been retired.
    if retired_number in visited:
        return False
    visited = visited | {retired_number}
    retired = _as_mapping(read(repository, token, f"pulls/{retired_number}"))
    if retired is None or retired.get("number") != retired_number:
        return False
    identity = _pr_identity_is_coherent(
        retired,
        repository=repository,
        issue_number=issue_number,
        default_branch=default_branch,
    )
    expected_branch = (
        canonical_implementation_branch(change)
        if historical_pr_number is None
        else deterministic_continuation_branch(change, historical_pr_number)
    )
    if identity is not None and identity[0] != expected_branch:
        canonical = canonical_implementation_branch(change)
        replacement = (
            None
            if canonical is None
            else re.fullmatch(rf"{re.escape(canonical)}-supersedes-([1-9][0-9]*)", identity[0])
        )
        predecessor = None if replacement is None else int(replacement.group(1))
        if (
            predecessor is None
            or predecessor >= retired_number
            or not _formally_superseded_closed_carrier(
                repository,
                token,
                issue_number=issue_number,
                change=change,
                default_branch=default_branch,
                historical_pr_number=historical_pr_number,
                retired_number=predecessor,
                read=read,
                visited=visited,
            )
        ):
            return False
        expected_branch = identity[0]
    closed_at = _timestamp(retired.get("closed_at"))
    if (
        identity is None
        or identity[0] != expected_branch
        or retired.get("state") != "closed"
        or retired.get("merged") is not False
        or retired.get("merged_at") is not None
        or retired.get("draft") is not False
        or closed_at is None
    ):
        return False
    owner = repository.split("/", 1)[0]
    matching = _paged_list(
        repository,
        token,
        f"pulls?{urlencode({'state': 'closed', 'head': f'{owner}:{expected_branch}'})}",
        read=read,
    )
    if len(matching) != 1 or matching[0].get("number") != retired_number:
        return False
    active_changes, _has_code = _pr_active_changes(repository, token, retired_number, read=read)
    if any(active_change != change for active_change in active_changes):
        return False
    comments = _paged_list(
        repository,
        token,
        f"issues/{issue_number}/comments?sort=created&direction=asc",
        read=read,
    )
    if _accepted_lead_retirement(
        repository,
        token,
        issue_number=issue_number,
        change=change,
        retired_number=retired_number,
        retired_branch=expected_branch,
        retired_head=identity[1],
        closed_at=closed_at,
        comments=comments,
        read=read,
    ):
        return True
    relevant: list[tuple[object, datetime]] = []
    for comment in comments:
        formal = parse_formal_result(comment, current_revision=None)
        # Retirement is an exact-head consequence. Historical formal results
        # for other revisions (including pre-activation Change: unset) cannot
        # qualify or invalidate this one retired carrier.
        if formal is None:
            continue
        if formal.revision != identity[1]:
            # A malformed/duplicated Revision becomes None in the formal
            # parser. Do not silently discard a record that explicitly claims
            # this retired HEAD among its conflicting revision values.
            body = comment.get("body")
            if (
                formal.revision is None
                and isinstance(body, str)
                and re.search(
                    rf"(?m)^Revision:[ \t]*.*(?<![0-9a-f]){re.escape(identity[1])}(?![0-9a-f])",
                    body,
                    flags=re.IGNORECASE,
                )
            ):
                return False
            continue
        if not formal.valid or (formal.issue_number, formal.change) != (issue_number, change):
            return False
        at = _timestamp(comment.get("created_at"))
        if at is None:
            return False
        relevant.append((formal, at))
    if len(relevant) < 2:
        return False
    ready, _ready_at = relevant[-2]
    findings, findings_at = relevant[-1]
    formal_transition = bool(
        getattr(ready, "role", None) == "executor"
        and getattr(ready, "action", None) == "implement-change"
        and getattr(ready, "result_kind", None) == "ready"
        and getattr(ready, "successor", None) == ("reviewer", "review-implementation")
        and getattr(findings, "role", None) == "reviewer"
        and getattr(findings, "action", None) == "review-implementation"
        and getattr(findings, "result_kind", None) == "findings"
        and getattr(findings, "successor", None) == ("executor", "implement-change")
        and _ready_at < findings_at <= closed_at
    )
    if not formal_transition:
        return False
    if not all(
        _accepted_formal_result_is_proven(
            repository,
            token,
            issue_number=issue_number,
            change=change,
            retired_number=retired_number,
            retired_branch=expected_branch,
            event=event,
            comments=comments,
            read=read,
        )
        for event in (ready, findings)
    ):
        return False
    timeline = _paged_list(
        repository,
        token,
        f"issues/{issue_number}/timeline",
        read=read,
    )
    routed: list[tuple[str, str]] = []
    for entry in timeline:
        event = entry.get("event")
        label = _as_mapping(entry.get("label"))
        name = None if label is None else label.get("name")
        if event not in {"labeled", "unlabeled"} or not isinstance(name, str):
            continue
        at = _timestamp(entry.get("created_at"))
        if at is None:
            return False
        if not (findings_at <= at <= closed_at) or not name.startswith("action:"):
            continue
        actor = _as_mapping(entry.get("actor"))
        if actor is None or actor.get("login") != "github-actions[bot]":
            return False
        routed.append((cast(str, event), name))
    return sorted(routed) == [
        ("labeled", "action:implement-change"),
        ("unlabeled", "action:review-implementation"),
    ]


def qualify_supersession_branch(
    *,
    repository: str,
    token: str,
    issue_number: int,
    change: str,
    branch: str,
    current_revision: str,
    read: GitHubReader | None = None,
) -> bool:
    """Read-only permission for the sole branch derived from retired GitHub truth.

    This cannot close a PR, move a ref, select an Action, or create a result.
    A real application-owned FINDINGS transition or exact-head Lead retirement
    effect plus observed closure supplies the supersession evidence. The new
    work product must independently qualify.
    """

    reader = _github_json if read is None else read
    canonical = canonical_implementation_branch(change)
    if canonical is None or not _valid_sha(current_revision):
        return False
    match = re.fullmatch(rf"{re.escape(canonical)}-supersedes-([1-9][0-9]*)", branch)
    if match is None:
        return False
    default_branch, default_revision = _repository_default(repository, token, read=reader)
    if default_branch is None or default_revision != current_revision:
        return False
    issue = _as_mapping(reader(repository, token, f"issues/{issue_number}"))
    if issue is None or issue.get("state") != "open" or _change_from_issue(issue) != change:
        return False
    historical = _historical_carriers(
        repository,
        token,
        issue_number=issue_number,
        change=change,
        default_branch=default_branch,
        default_revision=current_revision,
        read=reader,
    )
    if historical is None:
        return False
    competing = _claimed_open_carriers(
        repository,
        token,
        issue_number=issue_number,
        change=change,
        default_branch=default_branch,
        read=reader,
    )
    if any(
        not isinstance(pr.get("head"), Mapping)
        or cast(Mapping[str, object], pr["head"]).get("ref") != branch
        for pr in competing
    ):
        return False
    historical_index = next(
        (
            index
            for index, (_number, pr) in enumerate(historical)
            if isinstance(pr.get("head"), Mapping)
            and cast(Mapping[str, object], pr["head"]).get("ref") == branch
        ),
        None,
    )
    predecessor_number = (
        historical[historical_index - 1][0]
        if historical_index is not None and historical_index > 0
        else historical[-1][0]
        if historical_index is None and historical
        else None
    )
    return _formally_superseded_closed_carrier(
        repository,
        token,
        issue_number=issue_number,
        change=change,
        default_branch=default_branch,
        historical_pr_number=predecessor_number,
        retired_number=int(match.group(1)),
        read=reader,
    )


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


def qualify_change_carrier(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    pr_number: int,
    current_revision: str,
    read: GitHubReader | None = None,
    implementation_retirement: bool = False,
) -> ImplementationCarrierQualification:
    """Freshly qualify one exact canonical or deterministic same-Change carrier.

    `RECONCILIATION_REQUIRED` means identity is repository-approved but safe
    integration has not been proven. A diverged PR can remain `QUALIFIED` when
    current mergeability and complete, disjoint Git changes prove integration
    without rewriting the reviewed HEAD. Otherwise only application-owned
    implementation reconciliation can advance the branch; merge consumers
    require `QUALIFIED` and their separate exact review/CI/Human gates.

    `read` replaces transport only. The qualifier still acquires every piece
    of evidence and owns the complete semantic decision.
    """

    reader = _github_json if read is None else read
    if (
        source.issue_number <= 0
        or (source.role, source.action) not in _CHANGE_CARRIER_SOURCES
        or not isinstance(pr_number, int)
        or isinstance(pr_number, bool)
        or pr_number <= 0
        or not _valid_sha(current_revision)
        or (
            implementation_retirement
            and (source.role, source.action) != ("lead", "resolve-question")
        )
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

    # An open carrier with an old PR base remains recognizable.  The
    # application owner may construct a reconciliation when the old base is a
    # proven ancestor of current default; unresolved ancestry or content
    # conflicts still fail closed at the application-owned reconciliation
    # boundary.
    base_is_current = _pr_base_is_current(
        pr,
        default_revision=default_revision,
    )

    historical = _historical_carriers(
        repository,
        token,
        issue_number=source.issue_number,
        change=change,
        default_branch=default_branch,
        default_revision=default_revision,
        read=reader,
        stop_before_branch=branch if not _is_merged_pr(pr) else None,
    )
    if historical is None:
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
    historical_pr_number = historical[-1][0] if historical else None

    active_changes, _has_code = _pr_active_changes(
        repository,
        token,
        pr_number,
        read=reader,
    )
    if (
        (source.role, source.action) in _OPENSPEC_CARRIER_SOURCES
        and not implementation_retirement
        and active_changes != {change}
    ):
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-openspec-change-missing-or-competing",
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            default_revision=default_revision,
            historical_pr_number=historical_pr_number,
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

        lineage_index = next(
            (index for index, (number, _carrier) in enumerate(historical) if number == pr_number),
            None,
        )
        if lineage_index is None:
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
        if lineage_index == 0:
            predecessor_number = pr_number
            expected_historical_branch = canonical
            historical_reason = "historical-merged-carrier-qualified"
        else:
            predecessor_number = historical[lineage_index - 1][0]
            expected_historical_branch = deterministic_continuation_branch(
                change, predecessor_number
            )
            historical_reason = "merged-continuation-carrier-qualified"
        approved_historical_branch = branch == expected_historical_branch or (
            branch.startswith(f"{canonical}-supersedes-")
            and qualify_supersession_branch(
                repository=repository,
                token=token,
                issue_number=source.issue_number,
                change=change,
                branch=branch,
                current_revision=current_revision,
                read=reader,
            )
        )
        if not approved_historical_branch or any(
            active_change != change for active_change in active_changes
        ):
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
            reason=historical_reason,
            repository=repository,
            issue_number=source.issue_number,
            change=change,
            action=source.action,
            pr_number=pr_number,
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            default_revision=default_revision,
            historical_pr_number=predecessor_number,
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
        expected_continuation = canonical
    else:
        expected_continuation = deterministic_continuation_branch(change, historical_pr_number)
    if branch != expected_continuation:
        replacement = re.fullmatch(rf"{re.escape(canonical)}-supersedes-([1-9][0-9]*)", branch)
        if replacement is None or not qualify_supersession_branch(
            repository=repository,
            token=token,
            issue_number=source.issue_number,
            change=change,
            branch=branch,
            current_revision=current_revision,
            read=reader,
        ):
            return _indeterminate(
                repository=repository,
                source=source,
                change=change,
                pr_number=pr_number,
                reason=(
                    "initial-carrier-branch-is-not-canonical"
                    if historical_pr_number is None
                    else "carrier-branch-is-not-deterministic-continuation"
                ),
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

    default_is_ancestor = _compare_is_ancestor(
        repository,
        token,
        ancestor=default_revision,
        descendant=head_sha,
        read=reader,
    )
    divergence_evidence: DivergenceEvidence = "NEEDS_RECONCILIATION"
    if not default_is_ancestor:
        divergence_evidence = _divergence_evidence(
            repository,
            token,
            pr=pr,
            head_sha=head_sha,
            default_revision=default_revision,
            read=reader,
        )

    disposition: CarrierDisposition
    reason: str
    if divergence_evidence == "INDETERMINATE":
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-current-integration-evidence-unavailable",
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            default_revision=default_revision,
            historical_pr_number=historical_pr_number,
        )
    if divergence_evidence == "SAFE":
        disposition = "QUALIFIED"
        reason = "carrier-qualified-after-disjoint-mergeable-default-advance"
    elif not base_is_current:
        if historical_pr_number is None:
            base = _as_mapping(pr.get("base"))
            base_sha = None if base is None else base.get("sha")
            if not _valid_sha(base_sha) or not _compare_is_ancestor(
                repository,
                token,
                ancestor=cast(str, base_sha),
                descendant=default_revision,
                read=reader,
            ):
                return _indeterminate(
                    repository=repository,
                    source=source,
                    change=change,
                    pr_number=pr_number,
                    reason="carrier-pr-base-is-stale",
                    branch=branch,
                    head_sha=head_sha,
                    default_branch=default_branch,
                    default_revision=default_revision,
                    historical_pr_number=historical_pr_number,
                )
            disposition = "RECONCILIATION_REQUIRED"
            reason = "initial-carrier-requires-default-reconciliation"
        else:
            if not default_is_ancestor:
                disposition = "RECONCILIATION_REQUIRED"
                reason = "carrier-pr-base-is-stale"
            else:
                # GitHub may retain a recorded old base even after reconciliation.
                # Proven ancestry is the postcondition, not the incidental SHA.
                disposition = "QUALIFIED"
                reason = "continuation-carrier-qualified-after-reconciliation"
    elif default_is_ancestor:
        disposition = "QUALIFIED"
        reason = (
            "initial-carrier-qualified"
            if historical_pr_number is None
            else "continuation-carrier-qualified"
        )
    else:
        disposition = "RECONCILIATION_REQUIRED"
        reason = "continuation-carrier-requires-default-reconciliation"

    if disposition == "RECONCILIATION_REQUIRED" and pr.get("mergeable") is False:
        reason = "carrier-confirmed-git-merge-conflict"

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
    """Compatibility entry point restricted to implementation-owned Actions."""

    if (source.role, source.action) not in _IMPLEMENTATION_CARRIER_SOURCES:
        return _indeterminate(
            repository=repository,
            source=source,
            change=change,
            pr_number=pr_number,
            reason="carrier-input-incomplete",
        )
    return qualify_change_carrier(
        repository=repository,
        token=token,
        source=source,
        change=change,
        pr_number=pr_number,
        current_revision=current_revision,
        read=read,
    )


__all__ = [
    "CarrierDisposition",
    "GitHubReader",
    "ImplementationCarrierQualification",
    "canonical_implementation_branch",
    "deterministic_continuation_branch",
    "deterministic_supersession_branch",
    "qualify_supersession_branch",
    "qualify_change_carrier",
    "qualify_implementation_carrier",
]
