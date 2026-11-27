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

    assert "ref: ${{ github.event.pull_request.head.sha || github.sha }}" in workflow


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
