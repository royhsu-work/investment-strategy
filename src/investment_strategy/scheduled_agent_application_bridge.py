"""Fresh repository-authorized ingress for Scheduled Agent effect application."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_action_model import next_action, role_for
from investment_strategy.scheduled_agent_application_materialization import (
    find_materialization_payload,
    materialization_requires_validation,
    observe_materialization_target,
)
from investment_strategy.scheduled_agent_carrier import CarrierRequired, carrier_plan_document
from investment_strategy.scheduled_agent_checkin import is_runtime_checkin_issue
from investment_strategy.scheduled_agent_effects import (
    ApplyResult,
    formal_application_correlation,
)
from investment_strategy.scheduled_agent_formal_qualification import (
    build_qualification_input,
    qualify_current_formal_consequence,
)
from investment_strategy.scheduled_agent_formal_result import parse_formal_result
from investment_strategy.scheduled_agent_merge_acceptance import run_guarded_effect_application
from investment_strategy.scheduled_agent_runtime import (
    WorkerRequest,
    acquire_current_github_preflight,
    is_github_actions_comment,
    normalize_github_issue,
)
from investment_strategy.scheduled_agent_validation_resource import ValidationResourceTarget
from investment_strategy.scheduled_agent_worker import WorkerActionResult, parse_worker_result
from investment_strategy.workflow_dispatch import DispatchPreflight, classify_dispatch

APPLICATION_REQUEST_MARKER = "EFFECT_REQUEST"
AUTHORIZATION_REVISION_PREFIX = "Authorization-Revision: "
WORKER_RESULT_B64_PREFIX = "Worker-Result-B64: "
_CHATGPT_CONNECTOR_APP_SLUG = "chatgpt-codex-connector"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_CHANGE_LINE = re.compile(r"(?m)^Change:\s*([^\s]+)\s*$")
_ROUTING_LABEL_PREFIXES = ("agent:", "action:")
_FIRST_ACTIVATION_RESULT = "ready-for-openspec-review"
_ACTIVATION_OBSERVATION_ATTEMPTS = 5
_ACTIVATION_OBSERVATION_DELAY_SECONDS = 1.0


@dataclass(frozen=True)
class ApplicationRequest:
    """One worker result bound only to the default-branch revision it observed."""

    authorization_revision: str
    raw_worker_result: str


@dataclass(frozen=True)
class ApplicationPlan:
    """Validated application input or an unrelated-comment no-op."""

    should_apply: bool
    source: WorkerRequest | None = None
    raw_worker_result: str | None = None
    request_comment_id: int | None = None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _app_slug(payload: Mapping[str, object]) -> str | None:
    app = _as_mapping(payload.get("performed_via_github_app"))
    slug = None if app is None else app.get("slug")
    return slug if isinstance(slug, str) else None


def _actor_login(payload: Mapping[str, object]) -> str | None:
    user = _as_mapping(payload.get("user"))
    login = None if user is None else user.get("login")
    return login if isinstance(login, str) else None


def _trusted_connector_comment(comment: Mapping[str, object], repository_owner: str) -> bool:
    return (
        _actor_login(comment) == repository_owner
        and _app_slug(comment) == _CHATGPT_CONNECTOR_APP_SLUG
    )


def parse_application_request(body: str) -> ApplicationRequest | None:
    """Parse the bounded effect ingress without any dispatch Artifact identity."""

    lines = body.split("\n")
    if not lines or lines[0] != APPLICATION_REQUEST_MARKER:
        return None
    if len(lines) != 3:
        raise ValueError("EFFECT_REQUEST must contain exactly three lines")
    if not lines[1].startswith(AUTHORIZATION_REVISION_PREFIX) or not lines[2].startswith(
        WORKER_RESULT_B64_PREFIX
    ):
        raise ValueError("EFFECT_REQUEST field order is invalid")

    authorization_revision = lines[1][len(AUTHORIZATION_REVISION_PREFIX) :]
    encoded_result = lines[2][len(WORKER_RESULT_B64_PREFIX) :]
    if _SHA.fullmatch(authorization_revision) is None or not encoded_result:
        raise ValueError("EFFECT_REQUEST authorization identity is invalid")
    if encoded_result != encoded_result.strip():
        raise ValueError("EFFECT_REQUEST worker result must be trimmed")
    try:
        raw_worker_result = base64.b64decode(encoded_result.encode("ascii"), validate=True).decode(
            "utf-8"
        )
        decoded = json.loads(raw_worker_result)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise ValueError("EFFECT_REQUEST worker result is not valid base64 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("EFFECT_REQUEST worker result must decode to a JSON object")
    return ApplicationRequest(
        authorization_revision=authorization_revision,
        raw_worker_result=raw_worker_result,
    )


def _claimed_source(raw_worker_result: str) -> WorkerRequest:
    try:
        decoded = json.loads(raw_worker_result)
    except json.JSONDecodeError as exc:
        raise ValueError("EFFECT_REQUEST worker result is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("EFFECT_REQUEST worker result must be a JSON object")
    issue_number = decoded.get("issue_number")
    role = decoded.get("role")
    action = decoded.get("action")
    if (
        _positive_int(issue_number) is None
        or not isinstance(role, str)
        or not isinstance(action, str)
    ):
        raise ValueError("EFFECT_REQUEST worker source identity is invalid")
    return WorkerRequest(cast(int, issue_number), role, action)


def plan_application(
    *,
    event: Mapping[str, object],
    request: ApplicationRequest,
    preflight: DispatchPreflight,
    repository: str,
    current_revision: str,
) -> ApplicationPlan:
    """Freshly derive the only legal source Issue/Action/Role from the repository."""

    if "/" not in repository or _SHA.fullmatch(current_revision) is None:
        raise ValueError("repository and current revision are required")
    if request.authorization_revision != current_revision:
        raise ValueError("EFFECT_REQUEST authorization revision is stale")

    issue = _as_mapping(event.get("issue"))
    event_comment = _as_mapping(event.get("comment"))
    if event.get("action") != "created" or issue is None or event_comment is None:
        return ApplicationPlan(False)
    if "pull_request" in issue or not is_runtime_checkin_issue(issue):
        return ApplicationPlan(False)

    body = event_comment.get("body")
    if not isinstance(body, str) or parse_application_request(body) != request:
        raise ValueError("EFFECT_REQUEST event body does not match parsed request")
    repository_owner = repository.split("/", 1)[0]
    if not _trusted_connector_comment(event_comment, repository_owner):
        raise ValueError("EFFECT_REQUEST must originate from the configured ChatGPT connector")
    request_comment_id = _positive_int(event_comment.get("id"))
    if request_comment_id is None:
        raise ValueError("EFFECT_REQUEST event comment id is invalid")

    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id is None
        or decision.selected_routing is None
    ):
        raise ValueError("EFFECT_REQUEST has no current AUTHORIZE dispatch")
    selected_role, selected_action = decision.selected_routing
    source = WorkerRequest(decision.selected_issue_id, selected_role, selected_action)
    claimed = _claimed_source(request.raw_worker_result)
    if claimed != source:
        raise ValueError("EFFECT_REQUEST worker source does not match fresh repository Action")
    return ApplicationPlan(
        should_apply=True,
        source=source,
        raw_worker_result=request.raw_worker_result,
        request_comment_id=request_comment_id,
    )


def _github_json(
    repository: str,
    token: str,
    api_path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
) -> object:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"https://api.github.com/repos/{repository}/{api_path.lstrip('/')}",
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted GitHub API host
        raw = response.read()
    return None if not raw else json.loads(raw.decode("utf-8"))


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
            f"{api_path}{separator}per_page=100&page={page}",
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


def _fresh_event_observation(
    event: Mapping[str, object],
    body: str,
    repository: str,
    token: str,
) -> None:
    issue = _as_mapping(event.get("issue"))
    comment = _as_mapping(event.get("comment"))
    if event.get("action") != "created" or issue is None or comment is None:
        raise ValueError("application request event is invalid")
    if "pull_request" in issue or not is_runtime_checkin_issue(issue):
        raise ValueError("application request event is not a control shard comment")

    comment_id = _positive_int(comment.get("id"))
    issue_number = _positive_int(issue.get("number"))
    owner = repository.split("/", 1)[0] if "/" in repository else ""
    if (
        comment_id is None
        or issue_number is None
        or comment.get("body") != body
        or not _trusted_connector_comment(comment, owner)
    ):
        raise ValueError("application request event identity is invalid")

    observed_comment = _as_mapping(_github_json(repository, token, f"issues/comments/{comment_id}"))
    if (
        observed_comment is None
        or observed_comment.get("id") != comment_id
        or observed_comment.get("body") != body
        or not _trusted_connector_comment(observed_comment, owner)
    ):
        raise ValueError("application request current comment observation is incomplete")
    observed_issue = _as_mapping(_github_json(repository, token, f"issues/{issue_number}"))
    if (
        observed_issue is None
        or observed_issue.get("number") != issue_number
        or not is_runtime_checkin_issue(observed_issue)
    ):
        raise ValueError("application request current shard observation is invalid")


def _load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _materialization_effects(
    raw_worker_result: str,
    source: WorkerRequest,
) -> tuple[Mapping[str, object], ...]:
    result = parse_worker_result(raw_worker_result, source)
    effects: list[Mapping[str, object]] = []
    for requested in result.requested_effects:
        if requested.kind != "github-mutation":
            continue
        try:
            payload = json.loads(requested.payload_json)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping) and payload.get("operation") == "application-materialize":
            effects.append(cast(Mapping[str, object], payload))
    return tuple(effects)


def _field_values(body: str, key: str) -> tuple[str, ...]:
    return tuple(
        value.strip().strip(chr(96))
        for value in re.findall(rf"(?m)^{re.escape(key)}:[ \t]*(.*)$", body)
    )


def _field(body: str, key: str) -> str | None:
    values = _field_values(body, key)
    if len(values) != 1 or not values[0]:
        return None
    return values[0]


def _marker(body: str) -> str | None:
    first = body.splitlines()[:1]
    if not first:
        return None
    marker = first[0].strip()
    return marker[3:].strip() if marker.startswith("## ") else marker


def _activation_result_body(
    worker_result: WorkerActionResult,
    *,
    source: WorkerRequest,
    change: str,
    result_revision: str,
    current_revision: str,
    request_comment_id: int,
) -> tuple[str, str, tuple[str, str]]:
    """Bind preactivation semantic output to application-owned formal identity."""

    if source != WorkerRequest(source.issue_number, "lead", "propose-change"):
        raise RuntimeError("first activation requires Lead / propose-change")
    if worker_result.change != "unset" or worker_result.typed_result.result.kind.value != _FIRST_ACTIVATION_RESULT:
        raise RuntimeError("first activation worker result is not activation-ready")
    successor = next_action(worker_result.typed_result.action, worker_result.typed_result.result)
    if successor is None:
        raise RuntimeError("first activation result has no formal successor")
    successor_routing = (role_for(successor).value, successor.value)
    if successor_routing != ("reviewer", "review-openspec"):
        raise RuntimeError("first activation successor is not review-openspec")

    body = worker_result.result_content
    expected_result = worker_result.typed_result.result.kind.value.upper().replace("-", "_")
    if (
        _marker(body) != "ACTION_RESULT"
        or _field(body, "Workflow") != f"#{source.issue_number}"
        or _field(body, "Change") != "unset"
        or _field(body, "Action") != source.action
        or _field(body, "Role") != source.role
        or _field(body, "Result") != expected_result
        or _field(body, "Default-Branch-Revision") != current_revision
        or _SHA.fullmatch(_field(body, "Revision") or "") is None
        or len(_field_values(body, "Application-Correlation")) > 0
        or len(_field_values(body, "Repository-derived successor")) > 0
    ):
        raise RuntimeError("first activation result_content is not a bounded canonical result")

    updated, count = _CHANGE_LINE.subn(f"Change: {change}", body, count=1)
    if count != 1:
        raise RuntimeError("first activation result Change binding is ambiguous")
    if _SHA.fullmatch(result_revision) is None:
        raise RuntimeError("first activation result revision is invalid")
    updated, count = re.subn(
        r"(?m)^Revision:\s*[0-9a-f]{40}\s*$",
        f"Revision: {result_revision}",
        updated,
        count=1,
    )
    if count != 1:
        raise RuntimeError("first activation result revision binding is ambiguous")
    correlation = formal_application_correlation(
        source,
        change=change,
        result_kind=worker_result.typed_result.result.kind.value,
        current_revision=current_revision,
        request_comment_id=request_comment_id,
    )
    lines = updated.splitlines()
    anchors = [
        index
        for index, line in enumerate(lines)
        if line.startswith(("Revision:", "Default-Branch-Revision:"))
    ]
    if not anchors:
        raise RuntimeError("first activation result has no revision anchor")
    insert_at = max(anchors) + 1
    lines[insert_at:insert_at] = [
        f"Application-Correlation: {correlation}",
        "Repository-derived successor: Reviewer / review-openspec",
    ]
    suffix = "\n" if body.endswith("\n") else ""
    return "\n".join(lines) + suffix, correlation, successor_routing


def _fresh_preactivation_source(
    repository: str,
    token: str,
    source: WorkerRequest,
) -> None:
    preflight = acquire_current_github_preflight(repository, token)
    decision = classify_dispatch(preflight)
    if (
        decision.disposition != "AUTHORIZE"
        or decision.selected_issue_id != source.issue_number
        or decision.selected_routing != (source.role, source.action)
    ):
        raise RuntimeError("first activation source is no longer current")
    matching = tuple(
        item for item in preflight.issues if item.issue_number == source.issue_number
    )
    if (
        len(matching) != 1
        or matching[0].state != "open"
        or matching[0].change != "unset"
        or matching[0].routing != (source.role, source.action)
    ):
        raise RuntimeError("first activation source identity is no longer preactivation")


def _persist_activation_result(
    body: str,
    *,
    repository: str,
    token: str,
    issue_number: int,
) -> int:
    comments = _paged_github_list(repository, token, f"issues/{issue_number}/comments?sort=created")
    matches = tuple(
        comment
        for comment in comments
        if comment.get("body") == body and is_github_actions_comment(comment)
    )
    if len(matches) > 1:
        raise RuntimeError("first activation has duplicate application result evidence")
    if len(matches) == 1:
        comment_id = _positive_int(matches[0].get("id"))
        if comment_id is None:
            raise RuntimeError("first activation result comment id is invalid")
        return comment_id

    response = _as_mapping(
        _github_json(
            repository,
            token,
            f"issues/{issue_number}/comments",
            method="POST",
            payload={"body": body},
        )
    )
    comment_id = None if response is None else _positive_int(response.get("id"))
    if (
        response is None
        or comment_id is None
        or response.get("body") != body
        or not is_github_actions_comment(response)
    ):
        raise RuntimeError("first activation result postcondition was not observed")
    observed = _as_mapping(
        _github_json(repository, token, f"issues/comments/{comment_id}")
    )
    if (
        observed is None
        or observed.get("id") != comment_id
        or observed.get("body") != body
        or not is_github_actions_comment(observed)
    ):
        raise RuntimeError("first activation result fresh postcondition was not observed")
    return comment_id


def _formal_qualification(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    current_revision: str,
    expected_result_kind: str,
    expected_application_correlation: str,
    current_routing: tuple[str, str],
    expected_routing: tuple[str, str] | None,
    mode: Literal["current", "pending"],
) -> bool:
    issue = _as_mapping(
        _github_json(repository, token, f"issues/{source.issue_number}")
    )
    observation = None if issue is None else normalize_github_issue(issue)
    if (
        observation is None
        or not observation.authoritative
        or observation.issue_number != source.issue_number
        or observation.state != "open"
        or observation.routing != current_routing
    ):
        return False
    comments = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created",
    )
    lifecycle = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/timeline",
    )
    qualification = build_qualification_input(
        issue_number=source.issue_number,
        change=change,
        state=observation.state,
        current_routing=observation.routing,
        comments=comments,
        current_revision=current_revision,
        mode=mode,
        expected_routing=expected_routing,
        expected_terminal=False,
        source_routing=(source.role, source.action) if mode == "pending" else None,
        expected_result_kind=expected_result_kind if mode == "pending" else None,
        expected_application_correlation=(
            expected_application_correlation if mode == "pending" else None
        ),
        lifecycle_events=lifecycle,
    )
    return qualify_current_formal_consequence(qualification).qualified


def _issue_label_names(issue: Mapping[str, object]) -> list[str]:
    raw_labels = issue.get("labels")
    if not isinstance(raw_labels, list):
        raise RuntimeError("first activation Issue labels are incomplete")
    names: list[str] = []
    for item in raw_labels:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str):
            raise RuntimeError("first activation Issue label identity is incomplete")
        names.append(cast(str, item["name"]))
    return names


def _existing_activation_correlation(
    *,
    repository: str,
    token: str,
    source: WorkerRequest,
    change: str,
    result_revision: str,
    current_revision: str,
    result_kind: str,
    successor_routing: tuple[str, str],
) -> str | None:
    """Reuse one exact pending result instead of replaying semantic work."""

    comments = _paged_github_list(
        repository,
        token,
        f"issues/{source.issue_number}/comments?sort=created",
    )
    matching: list[str] = []
    for comment in comments:
        event = parse_formal_result(comment, current_revision=current_revision)
        if (
            event is None
            or not event.valid
            or event.issue_number != source.issue_number
            or event.change != change
            or (event.role, event.action) != (source.role, source.action)
            or event.result_kind != result_kind
            or event.revision != result_revision
            or event.default_branch_revision != current_revision
            or event.successor != successor_routing
            or event.terminal
            or event.application_correlation is None
        ):
            continue
        matching.append(event.application_correlation)
    if len(matching) > 1:
        raise RuntimeError("first activation has ambiguous exact pending result evidence")
    if not matching:
        return None
    correlation = matching[0]
    if not _formal_qualification(
        repository=repository,
        token=token,
        source=source,
        change=change,
        current_revision=current_revision,
        expected_result_kind=result_kind,
        expected_application_correlation=correlation,
        current_routing=(source.role, source.action),
        expected_routing=successor_routing,
        mode="pending",
    ):
        raise RuntimeError("existing first activation result is no longer a valid pending consequence")
    return correlation


def _complete_first_activation(
    *,
    raw_worker_result: str,
    materialization: Mapping[str, object],
    target: ValidationResourceTarget,
    source: WorkerRequest,
    repository: str,
    token: str,
    current_revision: str,
    default_branch: str,
    request_comment_id: int,
) -> None:
    """Persist result first, then atomically promote Change and successor routing."""

    worker_result = parse_worker_result(raw_worker_result, source)
    body, proposed_correlation, successor_routing = _activation_result_body(
        worker_result,
        source=source,
        change=target.change,
        result_revision=target.revision,
        current_revision=current_revision,
        request_comment_id=request_comment_id,
    )
    _fresh_preactivation_source(repository, token, source)
    correlation = _existing_activation_correlation(
        repository=repository,
        token=token,
        source=source,
        change=target.change,
        result_revision=target.revision,
        current_revision=current_revision,
        result_kind=worker_result.typed_result.result.kind.value,
        successor_routing=successor_routing,
    )
    if correlation is None:
        _persist_activation_result(
            body,
            repository=repository,
            token=token,
            issue_number=source.issue_number,
        )
        correlation = proposed_correlation
    _fresh_preactivation_source(repository, token, source)

    if not _formal_qualification(
        repository=repository,
        token=token,
        source=source,
        change=target.change,
        current_revision=current_revision,
        expected_result_kind=worker_result.typed_result.result.kind.value,
        expected_application_correlation=correlation,
        current_routing=(source.role, source.action),
        expected_routing=successor_routing,
        mode="pending",
    ):
        raise RuntimeError("first activation pending formal consequence is not qualified")

    fresh_target = observe_materialization_target(
        materialization,
        source,
        repository=repository,
        token=token,
        current_revision=current_revision,
        default_branch=default_branch,
    )
    if fresh_target != target:
        raise RuntimeError("first activation validation target changed before promotion")

    issue = _as_mapping(
        _github_json(repository, token, f"issues/{source.issue_number}")
    )
    observation = None if issue is None else normalize_github_issue(issue)
    issue_body = None if issue is None else issue.get("body")
    if (
        issue is None
        or observation is None
        or not observation.authoritative
        or observation.state != "open"
        or observation.change != "unset"
        or observation.routing != (source.role, source.action)
        or not isinstance(issue_body, str)
        or _CHANGE_LINE.findall(issue_body) != ["unset"]
    ):
        raise RuntimeError("first activation source changed before atomic promotion")

    updated_body, count = _CHANGE_LINE.subn(
        f"Change: {target.change}",
        issue_body,
        count=1,
    )
    if count != 1:
        raise RuntimeError("first activation Change update is ambiguous")
    labels = [
        name
        for name in _issue_label_names(issue)
        if not name.startswith(_ROUTING_LABEL_PREFIXES)
    ]
    labels.append(f"action:{successor_routing[1]}")
    _github_json(
        repository,
        token,
        f"issues/{source.issue_number}",
        method="PATCH",
        payload={"body": updated_body, "labels": labels},
    )

    for attempt in range(_ACTIVATION_OBSERVATION_ATTEMPTS):
        final = _as_mapping(
            _github_json(repository, token, f"issues/{source.issue_number}")
        )
        final_observation = None if final is None else normalize_github_issue(final)
        state_matches = bool(
            final_observation is not None
            and final_observation.authoritative
            and final_observation.state == "open"
            and final_observation.change == target.change
            and final_observation.routing == successor_routing
            and not final_observation.routing_debt
        )
        if state_matches and _formal_qualification(
            repository=repository,
            token=token,
            source=source,
            change=target.change,
            current_revision=current_revision,
            expected_result_kind=worker_result.typed_result.result.kind.value,
            expected_application_correlation=correlation,
            current_routing=successor_routing,
            expected_routing=None,
            mode="current",
        ):
            return
        if attempt + 1 < _ACTIVATION_OBSERVATION_ATTEMPTS:
            time.sleep(_ACTIVATION_OBSERVATION_DELAY_SECONDS)
    raise RuntimeError("first activation current formal postcondition was not qualified")


def _write_validation_outputs(target: ValidationResourceTarget | None) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    lines = [f"validation_required={'true' if target is not None else 'false'}"]
    if target is not None:
        lines.extend(
            (
                f"validation_target_repository={target.repository}",
                f"validation_target_revision={target.revision}",
                f"validation_correlation={target.correlation}",
                f"validation_pr_number={target.pr_number}",
                f"validation_change={target.change}",
            )
        )
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def _write_carrier_outputs(result: ApplyResult) -> None:
    """Expose an immutable carrier plan as run-scoped application evidence."""

    output_path = os.environ.get("GITHUB_OUTPUT")
    plan = result.carrier_plan
    if output_path is None:
        return
    lines = [f"carrier_required={'true' if plan is not None else 'false'}"]
    if plan is not None:
        document = carrier_plan_document(plan)
        encoded = base64.b64encode(
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        lines.extend((f"carrier_plan_id={plan.plan_id}", f"carrier_plan_b64={encoded}"))
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def main() -> int:
    """Apply one worker result after fresh repository authorization."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--default-branch", required=True)
    parser.add_argument("--validation-passed", action="store_true")
    parser.add_argument("--validated-revision")
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    event = _as_mapping(_load_json(args.event_path))
    if event is None:
        raise RuntimeError("GitHub event payload must be an object")
    event_comment = _as_mapping(event.get("comment"))
    body = None if event_comment is None else event_comment.get("body")
    if not isinstance(body, str):
        return 0
    request = parse_application_request(body)
    if request is None:
        return 0

    _fresh_event_observation(event, body, repository, token)
    preflight = acquire_current_github_preflight(repository, token)
    plan = plan_application(
        event=event,
        request=request,
        preflight=preflight,
        repository=repository,
        current_revision=args.revision,
    )
    if not plan.should_apply:
        _write_validation_outputs(None)
        return 0
    if plan.source is None or plan.raw_worker_result is None or plan.request_comment_id is None:
        raise RuntimeError("application plan is missing validated source/result/request identity")

    worker_result = parse_worker_result(plan.raw_worker_result, plan.source)
    materializations = _materialization_effects(plan.raw_worker_result, plan.source)
    if len(materializations) > 1:
        raise RuntimeError("EFFECT_REQUEST contains ambiguous materialization effects")
    materialization = None if not materializations else materializations[0]
    parsed_materialization = None
    first_activation = False
    target = None
    requires_validation = False
    if materialization is not None:
        parsed_materialization = find_materialization_payload(materialization, plan.source)
        if parsed_materialization is None:
            raise RuntimeError("EFFECT_REQUEST materialization payload is invalid")
        first_activation = parsed_materialization.expected_change == "unset"
        if first_activation and (
            plan.source != WorkerRequest(plan.source.issue_number, "lead", "propose-change")
            or worker_result.change != "unset"
            or worker_result.typed_result.result.kind.value != _FIRST_ACTIVATION_RESULT
        ):
            raise RuntimeError("EFFECT_REQUEST first materialization is not activation-ready")
        requires_validation = materialization_requires_validation(
            parsed_materialization, plan.source
        )
        if requires_validation and args.validation_passed:
            target = observe_materialization_target(
                materialization,
                plan.source,
                repository=repository,
                token=token,
                current_revision=args.revision,
                default_branch=args.default_branch,
            )
            if args.validated_revision is None or target.revision != args.validated_revision:
                raise RuntimeError("EFFECT_REQUEST validation proof is stale")
        elif not requires_validation and args.validation_passed:
            raise RuntimeError("EFFECT_REQUEST has no validation gate to complete")
    elif args.validation_passed:
        raise RuntimeError("EFFECT_REQUEST validation completion has no materialization")

    try:
        if first_activation and args.validation_passed:
            batch, result = run_guarded_effect_application(
                plan.raw_worker_result,
                source=plan.source,
                repository=repository,
                token=token,
                current_revision=args.revision,
                apply_derived=False,
                materialization_promote_change=False,
                validated_materialization_revision=args.validated_revision,
                request_comment_id=plan.request_comment_id,
            )
            if result.applied:
                if materialization is None or target is None:
                    raise RuntimeError("first activation validation target is unavailable")
                _complete_first_activation(
                    raw_worker_result=plan.raw_worker_result,
                    materialization=materialization,
                    target=target,
                    source=plan.source,
                    repository=repository,
                    token=token,
                    current_revision=args.revision,
                    default_branch=args.default_branch,
                    request_comment_id=plan.request_comment_id,
                )
        else:
            batch, result = run_guarded_effect_application(
                plan.raw_worker_result,
                source=plan.source,
                repository=repository,
                token=token,
                current_revision=args.revision,
                apply_derived=not requires_validation or args.validation_passed,
                materialization_promote_change=args.validation_passed,
                validated_materialization_revision=args.validated_revision,
                request_comment_id=plan.request_comment_id,
            )
    except CarrierRequired as exc:
        # CarrierRequired is the hard invocation-exit boundary. Persist only
        # the exact application-authorized plan; a later fresh wake must
        # reconstruct repository truth before any missing effect or successor.
        carrier_result = ApplyResult(False, "carrier_required", carrier_plan=exc.plan)
        _write_carrier_outputs(carrier_result)
        _write_validation_outputs(None)
        print(
            json.dumps(
                {
                    "applied": False,
                    "reason": carrier_result.reason,
                    "effects": 0,
                    "validation_required": requires_validation,
                    "validation_completed": args.validation_passed,
                    "carrier_required": True,
                    "carrier_plan_id": exc.plan.plan_id,
                },
                sort_keys=True,
            )
        )
        return 0

    if result.carrier_plan is not None:
        # Keep compatibility with an adapter that returns the existing carrier
        # result surface while enforcing the same invocation boundary.
        _write_carrier_outputs(result)
        _write_validation_outputs(None)
        print(
            json.dumps(
                {
                    "applied": False,
                    "reason": result.reason,
                    "effects": len(batch.effects),
                    "validation_required": requires_validation,
                    "validation_completed": args.validation_passed,
                    "carrier_required": True,
                    "carrier_plan_id": result.carrier_plan.plan_id,
                },
                sort_keys=True,
            )
        )
        return 0
    if result.applied and requires_validation and not args.validation_passed:
        if materialization is None:
            raise RuntimeError("validation gate has no materialization target")
        target = observe_materialization_target(
            materialization,
            plan.source,
            repository=repository,
            token=token,
            current_revision=args.revision,
            default_branch=args.default_branch,
        )
    else:
        target = None
    _write_carrier_outputs(result)
    _write_validation_outputs(target)
    print(
        json.dumps(
            {
                "applied": result.applied,
                "reason": result.reason,
                "effects": len(batch.effects),
                "validation_required": requires_validation,
                "validation_completed": args.validation_passed,
                "carrier_required": result.carrier_plan is not None,
                "carrier_plan_id": None
                if result.carrier_plan is None
                else result.carrier_plan.plan_id,
            },
            sort_keys=True,
        )
    )
    return 0 if result.applied or result.carrier_plan is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
