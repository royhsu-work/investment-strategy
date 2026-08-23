"""Exact revision identity regressions for the #133 live Scheduled Agent canary."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scheduled-agent-runtime.yml"
LIVE_EVIDENCE = ROOT / "src" / "investment_strategy" / "scheduled_agent_live_evidence.py"


def test_scheduled_runtime_pins_worker_apply_and_evidence_to_dispatch_checkout_revision() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    evidence = LIVE_EVIDENCE.read_text(encoding="utf-8")

    assert "revision: ${{ steps.checkout_revision.outputs.revision }}" in workflow
    assert "id: checkout_revision" in workflow
    assert 'echo "revision=$(git rev-parse HEAD)" >> "$GITHUB_OUTPUT"' in workflow
    assert workflow.count("ref: ${{ needs.dispatch.outputs.revision }}") == 2
    assert "RUNTIME_REVISION: ${{ needs.dispatch.outputs.revision }}" in workflow
    assert '_required_environment("RUNTIME_REVISION")' in evidence
    assert '_required_environment("GITHUB_SHA")' not in evidence
