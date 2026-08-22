"""Fresh Responses API worker for one machine-authorized Scheduled Agent action."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_runtime import WorkerRequest

_SKILL_MAPPING = re.compile(r"- `([^`]+)` uses `([^`]+)`\.")
_RESPONSES_URL = "https://api.openai.com/v1/responses"


@dataclass(frozen=True)
class WorkerRequestedEffect:
    """Invocation-local requested durable effect; never authorization itself."""

    kind: str
    payload_json: str


@dataclass(frozen=True)
class WorkerActionResult:
    """Structured worker result bound to the exact machine-authorized source."""

    issue_number: int
    role: str
    action: str
    result_content: str
    requested_effects: tuple[WorkerRequestedEffect, ...]


WorkerTransport = Callable[[str], str]


def _skill_path_for_action(role_text: str, action: str) -> Path:
    matches = [path for mapped_action, path in _SKILL_MAPPING.findall(role_text) if mapped_action == action]
    if len(matches) != 1:
        raise ValueError(f"role definition does not map action exactly once: {action}")
    return Path(matches[0])


def build_worker_prompt(request: WorkerRequest, checkout_root: Path) -> str:
    """Load the exact role and mapped Skill from the checked-out default branch."""

    role_path = checkout_root / "agents" / "roles" / f"{request.role}.md"
    role_text = role_path.read_text(encoding="utf-8")
    skill_path = checkout_root / _skill_path_for_action(role_text, request.action)
    skill_text = skill_path.read_text(encoding="utf-8")

    return (
        "You are a fresh Scheduled Agent worker invocation.\n"
        "The machine runtime has already authorized exactly this identity:\n"
        f"Issue: #{request.issue_number}\n"
        f"Role: {request.role}\n"
        f"Action: {request.action}\n\n"
        "You must not select or override the Issue, role, or action. "
        "Execute only the mapped role/Skill procedure below. "
        "You have no authority to make durable GitHub writes directly. "
        "Return only the structured action result requested by the runtime; "
        "requested effects are proposals for later fresh reauthorization.\n\n"
        "## Role definition\n"
        f"{role_text}\n\n"
        "## Mapped Skill\n"
        f"{skill_text}\n"
    )


def _effect_from_payload(payload: object) -> WorkerRequestedEffect:
    if not isinstance(payload, Mapping):
        raise ValueError("requested effect must be an object")
    kind = payload.get("kind")
    payload_json = payload.get("payload_json")
    if not isinstance(kind, str) or not isinstance(payload_json, str):
        raise ValueError("requested effect requires string kind and payload_json")
    return WorkerRequestedEffect(kind=kind, payload_json=payload_json)


def parse_worker_result(raw: str, request: WorkerRequest) -> WorkerActionResult:
    """Validate structured output and reject any model attempt to change identity."""

    decoded = json.loads(raw)
    if not isinstance(decoded, Mapping):
        raise ValueError("worker result must be a JSON object")

    issue_number = decoded.get("issue_number")
    role = decoded.get("role")
    action = decoded.get("action")
    result_content = decoded.get("result_content")
    requested_effects = decoded.get("requested_effects")
    if (
        not isinstance(issue_number, int)
        or not isinstance(role, str)
        or not isinstance(action, str)
        or not isinstance(result_content, str)
        or not isinstance(requested_effects, list)
    ):
        raise ValueError("worker result has invalid structured fields")

    if (issue_number, role, action) != (request.issue_number, request.role, request.action):
        raise ValueError("worker result does not match authorized Issue/role/action")

    return WorkerActionResult(
        issue_number=issue_number,
        role=role,
        action=action,
        result_content=result_content,
        requested_effects=tuple(_effect_from_payload(effect) for effect in requested_effects),
    )


def run_authorized_worker(
    request: WorkerRequest | None,
    checkout_root: Path,
    transport: WorkerTransport,
) -> WorkerActionResult | None:
    """Invoke a fresh worker only when the same execution supplied authorization."""

    if request is None:
        return None
    prompt = build_worker_prompt(request, checkout_root)
    return parse_worker_result(transport(prompt), request)


def _response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "issue_number": {"type": "integer"},
            "role": {"type": "string"},
            "action": {"type": "string"},
            "result_content": {"type": "string"},
            "requested_effects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string"},
                        "payload_json": {"type": "string"},
                    },
                    "required": ["kind", "payload_json"],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "issue_number",
            "role",
            "action",
            "result_content",
            "requested_effects",
        ],
        "additionalProperties": False,
    }


def _extract_output_text(response: Mapping[str, object]) -> str:
    output = response.get("output")
    if not isinstance(output, list):
        raise RuntimeError("Responses API returned no output list")
    for item in output:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, Mapping) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    return text
    raise RuntimeError("Responses API returned no output_text")


@dataclass(frozen=True)
class OpenAIResponsesTransport:
    """Minimal direct Responses API transport; API/model config is deployment-only."""

    api_key: str
    model: str

    def __call__(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "input": prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "scheduled_agent_action_result",
                    "strict": True,
                    "schema": _response_schema(),
                }
            },
        }
        request = Request(  # noqa: S310 - fixed trusted OpenAI API host
            _RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=120) as response:  # noqa: S310 - fixed trusted OpenAI host
            decoded = json.loads(response.read().decode("utf-8"))
        if not isinstance(decoded, Mapping):
            raise RuntimeError("Responses API returned a malformed response")
        return _extract_output_text(cast(Mapping[str, object], decoded))
