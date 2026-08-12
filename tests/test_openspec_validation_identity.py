from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/openspec-validate.yml"
AGENTS = ROOT / "agents/AGENTS.md"
README = ROOT / "README.md"


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_openspec_validation_proves_exact_checkout_identity() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "VALIDATION_TARGET_SHA:" in workflow
    assert "github.event.pull_request.head.sha" in workflow
    assert "github.sha" in workflow
    assert "VALIDATION_TARGET_REPOSITORY:" in workflow
    assert "github.event.pull_request.head.repo.full_name" in workflow
    assert "repository: ${{ env.VALIDATION_TARGET_REPOSITORY }}" in workflow
    assert "ref: ${{ env.VALIDATION_TARGET_SHA }}" in workflow
    assert "git rev-parse HEAD" in workflow
    assert '"$actual_sha" != "$VALIDATION_TARGET_SHA"' in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow


def test_governance_does_not_treat_run_head_sha_as_checkout_proof() -> None:
    shared = _normalized(AGENTS)
    readme = _normalized(README)

    for text in (shared, readme):
        assert "head_sha" in text
        assert "association metadata" in text
        assert "insufficient" in text
        assert "validator checkout `HEAD`" in text
        assert "synthetic merge" in text
