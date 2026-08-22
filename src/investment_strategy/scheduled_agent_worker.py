"""Fresh Responses API worker for one machine-authorized Scheduled Agent action."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.request import Request, urlopen

from investment_strategy.scheduled_agent_runtime import WorkerRequest

_SKILL_MAPPING = re.compile(r"- `([^`]+)` uses `([^`]+)`\.")
_RESPONSES_URL = "https://api.openai.com/v1/responses"
_GITHUB_API_URL = "https://api.github.com"
_BASE_WORKER_CAPABILITIES = frozenset({"github_read", "read_file", "list_dir", "run_command"})
_LOCAL_WRITE_ACTIONS = frozenset(
    {
        ("lead", "propose-change"),
        ("lead", "resolve-question"),
        ("executor", "implement-change"),
    }
)
_MAPPED_ACTIONS = frozenset(
    {
        ("lead", "explore-change"),
        ("lead", "propose-change"),
        ("lead", "resolve-question"),
        ("lead", "finalize-change"),
        ("lead", "finalize-archive"),
        ("reviewer", "review-openspec"),
        ("reviewer", "review-implementation"),
        ("reviewer", "review-archive"),
        ("executor", "implement-change"),
        ("executor", "merge-pr"),
    }
)
_SECRET_ENV_NAMES = frozenset(
    {
        "OPENAI_API_KEY",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "GITHUB_READ_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    }
)


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


def worker_capabilities_for(request: WorkerRequest) -> frozenset[str]:
    """Return the explicit local/read capability profile for one mapped action."""

    identity = (request.role, request.action)
    if identity not in _MAPPED_ACTIONS:
        raise ValueError(f"unsupported worker role/action: {request.role}/{request.action}")
    capabilities = set(_BASE_WORKER_CAPABILITIES)
    if identity in _LOCAL_WRITE_ACTIONS:
        capabilities.add("write_file")
    return frozenset(capabilities)


@dataclass(frozen=True)
class WorkerToolRuntime:
    """Bounded worker tools with no durable GitHub mutation authority."""

    checkout_root: Path
    repository: str
    github_read_token: str | None
    capabilities: frozenset[str]

    def _workspace_path(self, raw_path: object) -> Path:
        if not isinstance(raw_path, str):
            raise ValueError("workspace path must be a string")
        relative = Path(raw_path)
        if relative.is_absolute():
            raise ValueError("workspace path must be relative")
        root = self.checkout_root.resolve()
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("workspace path escapes checkout workspace")
        return candidate

    def _tool_parameters(self, name: str) -> dict[str, Any]:
        if name in {"read_file", "write_file"}:
            properties: dict[str, Any] = {"path": {"type": "string"}}
            required = ["path"]
            if name == "write_file":
                properties["content"] = {"type": "string"}
                required.append("content")
            return {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            }
        if name == "list_dir":
            return {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "additionalProperties": False,
            }
        if name == "run_command":
            return {
                "type": "object",
                "properties": {
                    "argv": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "cwd": {"type": "string"},
                },
                "required": ["argv"],
                "additionalProperties": False,
            }
        if name == "github_read":
            return {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            }
        raise ValueError(f"unsupported worker tool: {name}")

    def tool_specs(self) -> list[dict[str, Any]]:
        """Expose only the tools authorized for this selected action."""

        return [
            {
                "type": "function",
                "name": name,
                "description": f"Scheduled Agent bounded worker tool: {name}",
                "parameters": self._tool_parameters(name),
            }
            for name in sorted(self.capabilities)
        ]

    def _run_command(self, payload: Mapping[str, object]) -> dict[str, object]:
        argv = payload.get("argv")
        if (
            not isinstance(argv, Sequence)
            or isinstance(argv, (str, bytes))
            or not argv
            or not all(isinstance(value, str) for value in argv)
        ):
            raise ValueError("run_command argv must be a non-empty string array")
        cwd = self._workspace_path(payload.get("cwd", "."))
        if not cwd.is_dir():
            raise ValueError("run_command cwd must be a workspace directory")
        environment = {
            key: value for key, value in os.environ.items() if key not in _SECRET_ENV_NAMES
        }
        completed = subprocess.run(  # noqa: S603 - argv is explicit and shell is never used
            list(argv),
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def _github_read(self, payload: Mapping[str, object]) -> dict[str, object]:
        raw_path = payload.get("path")
        if (
            not isinstance(raw_path, str)
            or not raw_path
            or raw_path.startswith(("http://", "https://"))
        ):
            raise ValueError("github_read path must be a repository-relative API path")
        path = raw_path.lstrip("/")
        if path.startswith("..") or "/../" in f"/{path}/":
            raise ValueError("github_read path escapes repository API scope")
        url = f"{_GITHUB_API_URL}/repos/{self.repository}/{path}"
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_read_token:
            headers["Authorization"] = f"Bearer {self.github_read_token}"
        request = Request(url, headers=headers, method="GET")  # noqa: S310 - fixed GitHub API host
        with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed GitHub API host
            body = response.read().decode("utf-8")
        return {"ok": True, "content": body}

    def execute(self, name: str, payload: object) -> str:
        """Execute one selected capability and return a JSON tool result."""

        if name not in self.capabilities:
            raise ValueError(f"worker tool is not authorized: {name}")
        if not isinstance(payload, Mapping):
            raise ValueError("worker tool payload must be an object")

        if name == "read_file":
            path = self._workspace_path(payload.get("path"))
            result: dict[str, object] = {"ok": True, "content": path.read_text(encoding="utf-8")}
        elif name == "write_file":
            path = self._workspace_path(payload.get("path"))
            content = payload.get("content")
            if not isinstance(content, str):
                raise ValueError("write_file content must be a string")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            result = {"ok": True, "path": str(path.relative_to(self.checkout_root.resolve()))}
        elif name == "list_dir":
            path = self._workspace_path(payload.get("path", "."))
            if not path.is_dir():
                raise ValueError("list_dir path must be a workspace directory")
            result = {
                "ok": True,
                "entries": [
                    {"name": entry.name, "type": "dir" if entry.is_dir() else "file"}
                    for entry in sorted(path.iterdir(), key=lambda value: value.name)
                ],
            }
        elif name == "run_command":
            result = self._run_command(payload)
        elif name == "github_read":
            result = self._github_read(payload)
        else:  # pragma: no cover - guarded by capability/profile validation
            raise ValueError(f"unsupported worker tool: {name}")
        return json.dumps(result, sort_keys=True)


def _skill_path_for_action(role_text: str, action: str) -> Path:
    matches = [
        path for mapped_action, path in _SKILL_MAPPING.findall(role_text) if mapped_action == action
    ]
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


def _function_calls(response: Mapping[str, object]) -> list[tuple[str, str, str]]:
    output = response.get("output")
    if not isinstance(output, list):
        raise RuntimeError("Responses API returned no output list")
    calls: list[tuple[str, str, str]] = []
    for item in output:
        if not isinstance(item, Mapping) or item.get("type") != "function_call":
            continue
        name = item.get("name")
        arguments = item.get("arguments")
        call_id = item.get("call_id")
        if (
            not isinstance(name, str)
            or not isinstance(arguments, str)
            or not isinstance(call_id, str)
        ):
            raise RuntimeError("Responses API returned malformed function call")
        calls.append((name, arguments, call_id))
    return calls


@dataclass(frozen=True)
class OpenAIResponsesTransport:
    """Responses API transport with bounded same-worker local/read tool execution."""

    api_key: str
    model: str
    tool_runtime: WorkerToolRuntime | None = None

    def _post(self, payload: Mapping[str, object]) -> Mapping[str, object]:
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
        return cast(Mapping[str, object], decoded)

    def __call__(self, prompt: str) -> str:
        format_config = {
            "format": {
                "type": "json_schema",
                "name": "scheduled_agent_action_result",
                "strict": True,
                "schema": _response_schema(),
            }
        }
        tools = self.tool_runtime.tool_specs() if self.tool_runtime else []
        payload: dict[str, object] = {
            "model": self.model,
            "input": prompt,
            "text": format_config,
        }
        if tools:
            payload["tools"] = tools

        for _ in range(32):
            decoded = self._post(payload)
            calls = _function_calls(decoded)
            if not calls:
                return _extract_output_text(decoded)
            if self.tool_runtime is None:
                raise RuntimeError("Responses API requested tools without a worker tool runtime")
            response_id = decoded.get("id")
            if not isinstance(response_id, str):
                raise RuntimeError("Responses API tool response is missing response id")
            outputs: list[dict[str, str]] = []
            for name, raw_arguments, call_id in calls:
                arguments = json.loads(raw_arguments)
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": self.tool_runtime.execute(name, arguments),
                    }
                )
            payload = {
                "model": self.model,
                "previous_response_id": response_id,
                "input": outputs,
                "text": format_config,
            }
            if tools:
                payload["tools"] = tools
        raise RuntimeError("Responses API exceeded bounded worker tool-call rounds")


def _authorized_request_from_environment() -> WorkerRequest:
    issue = os.environ.get("AUTHORIZED_ISSUE")
    role = os.environ.get("AUTHORIZED_ROLE")
    action = os.environ.get("AUTHORIZED_ACTION")
    if not issue or not role or not action:
        raise RuntimeError("machine-authorized Issue/role/action environment is required")
    try:
        issue_number = int(issue)
    except ValueError as exc:
        raise RuntimeError("AUTHORIZED_ISSUE must be an integer") from exc
    return WorkerRequest(issue_number=issue_number, role=role, action=action)


def main() -> int:
    """Invoke one fresh Responses API worker for the exact same-run authorization."""

    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL")
    if not api_key or not model:
        raise RuntimeError("OPENAI_API_KEY and OPENAI_MODEL are required")

    request = _authorized_request_from_environment()
    checkout_root = Path.cwd()
    repository = os.environ.get("GITHUB_REPOSITORY", "royhsu-work/investment-strategy")
    tool_runtime = WorkerToolRuntime(
        checkout_root=checkout_root,
        repository=repository,
        github_read_token=None,
        capabilities=worker_capabilities_for(request),
    )
    result = run_authorized_worker(
        request,
        checkout_root,
        OpenAIResponsesTransport(api_key=api_key, model=model, tool_runtime=tool_runtime),
    )
    if result is None:
        raise RuntimeError("authorized worker unexpectedly produced no result")
    print(
        json.dumps(
            {
                "issue_number": result.issue_number,
                "role": result.role,
                "action": result.action,
                "result_content": result.result_content,
                "requested_effects": [
                    {"kind": effect.kind, "payload_json": effect.payload_json}
                    for effect in result.requested_effects
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
