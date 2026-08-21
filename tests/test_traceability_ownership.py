"""Contract coverage for OpenSpec traceability responsibility ownership."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
REVIEWER = ROOT / "agents" / "roles" / "reviewer.md"
CHANGE_SKILL = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
REVIEW_SKILL = ROOT / "agents" / "skills" / "openspec-review" / "SKILL.md"
IMPLEMENTATION = ROOT / "agents" / "skills" / "implementation" / "SKILL.md"
README = ROOT / "README.md"
CONFIG = ROOT / "openspec" / "config.yaml"


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_lead_authors_trace_references_but_does_not_own_semantic_pass_gate() -> None:
    lead = _normalized(LEAD)
    change = _normalized(CHANGE_SKILL)
    shared = _normalized(AGENTS)

    for text in (lead, change, shared):
        assert "required trace declarations/references" in text
        assert "semantic bidirectional PASS gate" in text

    assert "Reviewer / review-openspec" in change
    assert "Reviewer / review-openspec" in shared
    assert "independent" in lead and "Reviewer" in lead

    assert "verify required artifacts, bidirectional traceability" not in lead
    assert "perform both: - forward traceability" not in change
    assert "Lead also verifies required artifacts and bidirectional traceability" not in shared


def test_reviewer_retains_reverse_first_semantic_bidirectional_gate() -> None:
    reviewer = _normalized(REVIEWER)
    skill = _normalized(REVIEW_SKILL)

    assert "Reviewer owns" in reviewer
    assert "bidirectional traceability" in reviewer
    assert "reverse-first" in skill
    assert "tasks → design → specs → proposal" in skill
    assert "proposal → specs → design → tasks" in skill
    assert "both directions must be complete before PASS" in skill
    assert "PASS" in skill and "FINDINGS" in skill


def test_readme_orients_to_traceability_owners_without_copying_review_protocol() -> None:
    readme = _normalized(README)
    assert "Authoritative Scheduled-Agent shared runtime governance" in readme
    assert "authoritative runtime workflow topology" in readme
    assert "agents/AGENTS.md" in readme
    assert "agents/workflow.md" in readme
    assert "OpenSpec authoring conventions" in readme
    assert "openspec/config.yaml" in readme
    assert "review-openspec" in readme
    assert "下列名稱僅作 Human 搜尋與流程導覽" in readme
    assert "README 只提供 Human/contributor 導覽" in readme
    assert "reverse-first `tasks → design → specs → proposal`" not in readme


def test_executor_completion_does_not_claim_semantic_traceability_review() -> None:
    implementation = _normalized(IMPLEMENTATION)
    assert "Executor does not perform semantic bidirectional OpenSpec review" in implementation
    assert "material semantic OpenSpec change" in implementation
    assert "Lead / resolve-question" in implementation


def test_existing_openspec_authoring_and_mechanical_rules_remain_intact() -> None:
    config = _normalized(CONFIG)
    for required in (
        "Trace major design decisions to requirements",
        "Trace Behavior/Product tasks through proposal, capability specs, and design",
        "Before declaring a change complete, run strict OpenSpec validation",
    ):
        assert required in config
