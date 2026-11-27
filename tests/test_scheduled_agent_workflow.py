"""Repository governance points to one Action-only execution contract."""

import os
import subprocess
from pathlib import Path
from typing import cast

import pytest
import yaml

from investment_strategy.scheduled_agent_action_model import render_workflow_presentation


def test_workflow_document_is_a_human_projection_of_the_action_model() -> None:
    path = Path("agents/workflow.md")
    workflow = path.read_text(encoding="utf-8")
    assert "Scheduled-Dispatch-Mode: workflow-dynamic" in workflow
    assert "one Action per Scheduled Task wake" in workflow
    assert "Role = role_for(Action)" in workflow
    assert "next_action(current_action, result)" in workflow

    start_marker = "<!-- BEGIN GENERATED ACTION MODEL -->"
    end_marker = "<!-- END GENERATED ACTION MODEL -->"
    start = workflow.index(start_marker)
    end = workflow.index(end_marker, start) + len(end_marker)
    assert workflow[start : end + 1] == render_workflow_presentation()

    for forbidden in (
        "HANDOFF",
        "HANDOFF_COMPLETION_REQUEST",
        "same-role immediate continuation",
        "cross-role wake barrier",
        "response mailbox",
        "Markdown topology parsing",
    ):
        assert forbidden not in workflow


def test_quality_workflow_checks_the_exact_pull_request_head() -> None:
    workflow = Path(".github/workflows/quality.yml").read_text(encoding="utf-8")

    assert "github.event.pull_request.head.sha || github.sha }}" in workflow


@pytest.mark.parametrize("matching", [False, True])
def test_quality_proves_checkout_before_running_quality_commands(matching: bool) -> None:
    workflow = yaml.safe_load(Path(".github/workflows/quality.yml").read_text(encoding="utf-8"))
    steps = cast(list[dict[str, object]], workflow["jobs"]["quality"]["steps"])
    proof = next((step for step in steps if step.get("id") == "quality_checkout"), None)
    assert proof is not None, "Python Quality must prove its actual checkout before testing"
    checkout = next(step for step in steps if step.get("uses") == "actions/checkout@v4")
    required_steps = ["Ruff lint", "Ruff format check", "Mypy", "Run tests"]
    checks = [step for step in steps if step.get("name") in required_steps]
    assert [step.get("name") for step in checks] == required_steps
    assert steps.index(checkout) < steps.index(proof) < steps.index(checks[0])

    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()  # noqa: S603, S607
    target = actual if matching else ("0" if actual[0] != "0" else "1") + actual[1:]
    witness = subprocess.run(  # noqa: S603 - execute the checked-in workflow step locally
        ["bash", "-e", "-o", "pipefail", "-c", cast(str, proof["run"])],  # noqa: S607
        env={
            **os.environ,
            "EXPECTED_QUALITY_SHA": target,
            "GITHUB_REPOSITORY": "owner/repository",
            "GITHUB_WORKFLOW_SHA": "a" * 40,
            "GITHUB_RUN_ID": "12345",
            "GITHUB_RUN_ATTEMPT": "2",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    if matching:
        assert witness.returncode == 0, witness.stderr
        assert witness.stdout.splitlines() == [
            "quality_repository=owner/repository",
            f"quality_target_sha={target}",
            f"quality_checkout_sha={actual}",
            f"quality_definition_sha={'a' * 40}",
            "quality_run_id=12345",
            "quality_run_attempt=2",
        ]
    else:
        assert witness.returncode != 0
        assert "quality_checkout_sha=" not in witness.stdout


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "wrong-repository",
        "wrong-target",
        "wrong-definition",
        "wrong-source",
        "wrong-run",
        "wrong-attempt",
        "empty-target",
        "missing-correlation",
        "malformed-correlation",
        "wrong-event",
    ],
)
def test_reusable_quality_proves_exact_caller_before_candidate_execution(case: str) -> None:
    workflow = yaml.safe_load(Path(".github/workflows/quality.yml").read_text(encoding="utf-8"))
    triggers = workflow[True]
    assert "workflow_call" in triggers, "Python Quality must expose the same job for native calls"
    inputs = triggers["workflow_call"]["inputs"]
    assert set(inputs) == {
        "target_repository",
        "target_revision",
        "definition_revision",
        "verification_correlation",
        "source_comment_id",
        "run_id",
        "run_attempt",
    }
    assert all(value == {"required": True, "type": "string"} for value in inputs.values())
    assert set(workflow["jobs"]) == {"quality"}
    job = workflow["jobs"]["quality"]
    assert job["permissions"] == {"contents": "read"}
    steps = cast(list[dict[str, object]], job["steps"])
    proof = next(step for step in steps if step.get("id") == "quality_checkout")
    checkout = next(step for step in steps if step.get("uses") == "actions/checkout@v4")
    setup = next(step for step in steps if step.get("uses") == "astral-sh/setup-uv@v6")
    options = cast(dict[str, object], checkout["with"])
    assert options["persist-credentials"] is False
    assert options["repository"] == "${{ github.repository }}"
    assert options["ref"] == (
        "${{ inputs.target_revision || github.event.pull_request.head.sha || github.sha }}"
    )
    assert cast(dict[str, object], setup["with"])["enable-cache"] == (
        "${{ github.event_name != 'issue_comment' }}"
    )
    assert steps.index(checkout) < steps.index(proof) < steps.index(setup)
    expected_env = {
        "EXPECTED_QUALITY_SHA": options["ref"],
        "QUALITY_CALL_REPOSITORY": "${{ inputs.target_repository }}",
        "QUALITY_CALL_TARGET": "${{ inputs.target_revision }}",
        "QUALITY_CALL_DEFINITION": "${{ inputs.definition_revision }}",
        "QUALITY_CALL_CORRELATION": "${{ inputs.verification_correlation }}",
        "QUALITY_CALL_SOURCE": "${{ inputs.source_comment_id }}",
        "QUALITY_EVENT_SOURCE": "${{ github.event.comment.id }}",
        "QUALITY_CALL_RUN_ID": "${{ inputs.run_id }}",
        "QUALITY_CALL_RUN_ATTEMPT": "${{ inputs.run_attempt }}",
    }
    assert proof["env"] == expected_env

    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()  # noqa: S603, S607
    env = {
        **os.environ,
        "EXPECTED_QUALITY_SHA": actual,
        "GITHUB_REPOSITORY": "owner/repository",
        "GITHUB_WORKFLOW_SHA": "a" * 40,
        "GITHUB_EVENT_NAME": "issue_comment",
        "GITHUB_RUN_ID": "12345",
        "GITHUB_RUN_ATTEMPT": "2",
        "QUALITY_CALL_REPOSITORY": "owner/repository",
        "QUALITY_CALL_TARGET": actual,
        "QUALITY_CALL_DEFINITION": "a" * 40,
        "QUALITY_CALL_CORRELATION": "b" * 64,
        "QUALITY_CALL_SOURCE": "901",
        "QUALITY_EVENT_SOURCE": "901",
        "QUALITY_CALL_RUN_ID": "12345",
        "QUALITY_CALL_RUN_ATTEMPT": "2",
    }
    if case != "valid":
        field, value = {
            "wrong-repository": ("QUALITY_CALL_REPOSITORY", "other/repository"),
            "wrong-target": ("QUALITY_CALL_TARGET", "c" * 40),
            "wrong-definition": ("QUALITY_CALL_DEFINITION", "d" * 40),
            "wrong-source": ("QUALITY_CALL_SOURCE", "902"),
            "wrong-run": ("QUALITY_CALL_RUN_ID", "12346"),
            "wrong-attempt": ("QUALITY_CALL_RUN_ATTEMPT", "1"),
            "empty-target": ("QUALITY_CALL_TARGET", ""),
            "missing-correlation": ("QUALITY_CALL_CORRELATION", ""),
            "malformed-correlation": ("QUALITY_CALL_CORRELATION", "untrusted"),
            "wrong-event": ("GITHUB_EVENT_NAME", "push"),
        }[case]
        env[field] = value
    witness = subprocess.run(  # noqa: S603 - execute the checked-in workflow step locally
        ["bash", "-e", "-o", "pipefail", "-c", cast(str, proof["run"])],  # noqa: S607
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if case == "valid":
        assert witness.returncode == 0, witness.stderr
        assert witness.stdout.splitlines() == [
            "quality_repository=owner/repository",
            f"quality_target_sha={actual}",
            f"quality_checkout_sha={actual}",
            f"quality_definition_sha={'a' * 40}",
            "quality_run_id=12345",
            "quality_run_attempt=2",
            "quality_source_comment_id=901",
            f"quality_verification_correlation={'b' * 64}",
        ]
    else:
        assert witness.returncode != 0
        assert "quality_checkout_sha=" not in witness.stdout
