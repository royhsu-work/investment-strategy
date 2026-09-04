"""Fresh merge-application consumption of the shared native-closing preflight."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from investment_strategy.native_closing_preflight import (
    MergePresentationInput,
    MergeStrategy,
    NativeClosingDisposition,
    NativeClosingPreflightResult,
    evaluate_native_closing_preflight,
)


@dataclass(frozen=True)
class MergeApplicationEvidence:
    """Exact merge evidence acquired immediately before a merge mutation."""

    repository_full_name: str
    coordination_issue: int
    pr_number: int
    expected_head_sha: str
    observed_head_sha: str
    lifecycle_context: str
    merge_strategy: MergeStrategy
    pr_body: str | None
    commit_messages: tuple[str, ...]
    commit_enumeration_complete: bool
    presentation_complete: bool
    generated_message: str | None


def native_closing_merge_result(
    evidence: MergeApplicationEvidence,
) -> NativeClosingPreflightResult:
    """Evaluate application evidence with the repository-owned deterministic preflight."""

    return evaluate_native_closing_preflight(
        MergePresentationInput(
            repository_full_name=evidence.repository_full_name,
            coordination_issue=evidence.coordination_issue,
            pr_number=evidence.pr_number,
            head_sha=evidence.expected_head_sha,
            observed_head_sha=evidence.observed_head_sha,
            lifecycle_context=evidence.lifecycle_context,
            merge_strategy=evidence.merge_strategy,
            pr_body=evidence.pr_body,
            commit_messages=evidence.commit_messages,
            commit_enumeration_complete=evidence.commit_enumeration_complete,
            presentation_complete=evidence.presentation_complete,
            generated_message=evidence.generated_message,
        )
    )


def native_closing_merge_allows(evidence: MergeApplicationEvidence) -> bool:
    """Return whether fresh application evidence permits the merge mutation."""

    return native_closing_merge_result(evidence).allowed


def _fail_closed() -> NativeClosingPreflightResult:
    return NativeClosingPreflightResult(NativeClosingDisposition.FAIL_CLOSED)


def _github_json(repository: str, token: str, api_path: str = "") -> object:
    suffix = api_path.lstrip("/")
    url = f"https://api.github.com/repos/{repository}"
    if suffix:
        url = f"{url}/{suffix}"
    request = Request(  # noqa: S310 - fixed trusted GitHub API host
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        return json.loads(response.read().decode("utf-8"))


def _paged_github_list(
    repository: str,
    token: str,
    api_path: str,
) -> tuple[Mapping[str, object], ...]:
    items: list[Mapping[str, object]] = []
    page = 1
    while True:
        separator = "&" if "?" in api_path else "?"
        decoded = _github_json(
            repository,
            token,
            f"{api_path}{separator}{urlencode({'per_page': 100, 'page': page})}",
        )
        if not isinstance(decoded, list):
            raise RuntimeError("GitHub paginated evidence endpoint returned a non-list response")
        current: list[Mapping[str, object]] = []
        for item in decoded:
            if not isinstance(item, Mapping):
                raise RuntimeError("GitHub paginated evidence endpoint returned a malformed item")
            current.append(cast(Mapping[str, object], item))
        items.extend(current)
        if len(current) < 100:
            return tuple(items)
        page += 1


def _pull_request_head_sha(payload: Mapping[str, object]) -> str | None:
    head = payload.get("head")
    if not isinstance(head, Mapping):
        return None
    sha = head.get("sha")
    return sha if isinstance(sha, str) else None


def _pull_request_head_merge_source(payload: Mapping[str, object]) -> str | None:
    """Return GitHub's effective MERGE_MESSAGE source in ``owner/ref`` form."""

    head = payload.get("head")
    if not isinstance(head, Mapping):
        return None
    ref = head.get("ref")
    repo = head.get("repo")
    if not isinstance(ref, str) or not ref or not isinstance(repo, Mapping):
        return None
    owner = repo.get("owner")
    if not isinstance(owner, Mapping):
        return None
    login = owner.get("login")
    if not isinstance(login, str) or not login:
        return None
    return f"{login}/{ref}"


def _complete_commit_messages(
    repository: str,
    token: str,
    pr_number: int,
    pr: Mapping[str, object],
) -> tuple[tuple[str, ...], bool]:
    expected_count = pr.get("commits")
    commits = _paged_github_list(repository, token, f"pulls/{pr_number}/commits")
    if not isinstance(expected_count, int) or expected_count != len(commits):
        return (), False

    messages: list[str] = []
    for item in commits:
        commit = item.get("commit")
        if not isinstance(commit, Mapping) or not isinstance(commit.get("message"), str):
            return (), False
        messages.append(cast(str, commit["message"]))
    return tuple(messages), True


def _first_line(message: str) -> str:
    return message.splitlines()[0] if message.splitlines() else ""


def _merge_strategy_enabled(repository: Mapping[str, object], strategy: MergeStrategy) -> bool:
    setting = {
        MergeStrategy.MERGE: "allow_merge_commit",
        MergeStrategy.SQUASH: "allow_squash_merge",
        MergeStrategy.REBASE: "allow_rebase_merge",
    }[strategy]
    return repository.get(setting) is True


def _generated_merge_message(
    *,
    repository: Mapping[str, object],
    pr: Mapping[str, object],
    pr_number: int,
    strategy: MergeStrategy,
    commit_messages: tuple[str, ...],
) -> tuple[str | None, bool]:
    if not _merge_strategy_enabled(repository, strategy):
        return None, False
    if strategy is MergeStrategy.REBASE:
        return None, True

    title = pr.get("title")
    body = pr.get("body")
    if not isinstance(title, str) or body is not None and not isinstance(body, str):
        return None, False
    body_text = "" if body is None else cast(str, body)

    if strategy is MergeStrategy.MERGE:
        title_mode = repository.get("merge_commit_title")
        message_mode = repository.get("merge_commit_message")
        if title_mode == "PR_TITLE":
            generated_title = title
        elif title_mode == "MERGE_MESSAGE":
            merge_source = _pull_request_head_merge_source(pr)
            if merge_source is None:
                return None, False
            generated_title = f"Merge pull request #{pr_number} from {merge_source}"
        else:
            return None, False

        if message_mode == "PR_TITLE":
            generated_body = title
        elif message_mode == "PR_BODY":
            generated_body = body_text
        elif message_mode == "BLANK":
            generated_body = ""
        else:
            return None, False
        return f"{generated_title}\n\n{generated_body}".rstrip(), True

    title_mode = repository.get("squash_merge_commit_title")
    message_mode = repository.get("squash_merge_commit_message")
    if title_mode == "PR_TITLE":
        generated_title = title
    elif title_mode == "COMMIT_OR_PR_TITLE":
        generated_title = _first_line(commit_messages[0]) if len(commit_messages) == 1 else title
    else:
        return None, False

    if message_mode == "PR_BODY":
        generated_body = body_text
    elif message_mode == "COMMIT_MESSAGES":
        generated_body = "\n\n".join(commit_messages)
    elif message_mode == "BLANK":
        generated_body = ""
    else:
        return None, False
    return f"{generated_title}\n\n{generated_body}".rstrip(), True


def acquire_native_closing_merge_result(
    *,
    repository: str,
    token: str,
    coordination_issue: int,
    pr_number: int,
    expected_head_sha: str,
    lifecycle_context: str,
    merge_strategy: MergeStrategy,
) -> NativeClosingPreflightResult:
    """Acquire complete current GitHub presentation and evaluate one exact-head preflight."""

    try:
        pr = _github_json(repository, token, f"pulls/{pr_number}")
        repository_state = _github_json(repository, token)
        if not isinstance(pr, Mapping) or not isinstance(repository_state, Mapping):
            return _fail_closed()
        commit_messages, commits_complete = _complete_commit_messages(
            repository,
            token,
            pr_number,
            pr,
        )
        generated_message, presentation_complete = _generated_merge_message(
            repository=repository_state,
            pr=pr,
            pr_number=pr_number,
            strategy=merge_strategy,
            commit_messages=commit_messages,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return _fail_closed()

    body = pr.get("body")
    pr_body = body if isinstance(body, str) else None
    return native_closing_merge_result(
        MergeApplicationEvidence(
            repository_full_name=repository,
            coordination_issue=coordination_issue,
            pr_number=pr_number,
            expected_head_sha=expected_head_sha,
            observed_head_sha=_pull_request_head_sha(pr) or "",
            lifecycle_context=lifecycle_context,
            merge_strategy=merge_strategy,
            pr_body=pr_body,
            commit_messages=commit_messages,
            commit_enumeration_complete=commits_complete,
            presentation_complete=presentation_complete,
            generated_message=generated_message,
        )
    )
