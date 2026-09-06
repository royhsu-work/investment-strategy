from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "openspec/config.yaml"
DELIVERY = ROOT / "agents/skills/openspec-delivery/SKILL.md"

STAGE_CONSUMERS = (
    "agents/skills/openspec-explore/SKILL.md",
    "agents/skills/openspec-change/SKILL.md",
    "agents/skills/openspec-review/SKILL.md",
    "agents/skills/implementation-review/SKILL.md",
    "agents/skills/lifecycle-finalize/SKILL.md",
)

NON_CONSUMERS = (
    "agents/skills/implementation/SKILL.md",
    "agents/skills/archive-review/SKILL.md",
    "agents/AGENTS.md",
    "agents/workflow.md",
)


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_config_owns_the_staged_delivery_authoring_predicate() -> None:
    config = _normalized(CONFIG)

    for required in (
        "recursively decompose delivery until each stage is independently "
        "executable, testable, reviewable, mergeable, and deployable on then-current N-1",
        "preserving the full approved parent outcome, requirements, constraints, and exit criteria",
        "parent-outcome coverage",
        "N-1 prerequisites",
        "stage exit criteria",
        "remaining mandatory outcome",
        "required continuation",
        "only an explicit approved reduction or defer may remove parent scope",
    ):
        assert required in config


def test_delivery_skill_defines_reconciliation_and_continuation() -> None:
    delivery = _normalized(DELIVERY)

    for required in (
        "approved parent outcome",
        "current stage boundary",
        "parent-outcome coverage",
        "N-1 prerequisites",
        "stage exit criteria",
        "remaining mandatory outcome",
        "required continuation",
        "prior-stage completion + current-stage completion + still-mandatory outcome",
        "MORE_IMPLEMENTATION_REQUIRED",
        "explicit approved reduction or defer",
        "implementation convenience",
        "stage size",
    ):
        assert required in delivery

    assert "Mapped Action:" not in delivery
    for prohibited_authority in (
        "new Action",
        "new Result kind",
        "lifecycle state",
        "stage-status label",
    ):
        assert prohibited_authority in delivery


def test_only_the_approved_mapped_procedures_load_delivery_skill() -> None:
    for relative in STAGE_CONSUMERS:
        body = _normalized(ROOT / relative)
        assert "## Conditional staged-delivery composition" in body
        assert body.count("agents/skills/openspec-delivery/SKILL.md") == 1

    for relative in NON_CONSUMERS:
        body = _normalized(ROOT / relative)
        assert "agents/skills/openspec-delivery/SKILL.md" not in body


def test_consumer_references_do_not_copy_the_shared_evidence_contract() -> None:
    shared_terms = (
        "parent-outcome coverage",
        "N-1 prerequisites",
        "stage exit criteria",
        "remaining mandatory outcome",
    )

    for relative in STAGE_CONSUMERS:
        body = _normalized(ROOT / relative)
        assert not all(term in body for term in shared_terms)


def test_existing_topology_and_continuation_remain_the_owners() -> None:
    workflow = _normalized(ROOT / "agents/workflow.md")
    action_model = _normalized(ROOT / "src/investment_strategy/scheduled_agent_action_model.py")
    shared = _normalized(ROOT / "agents/AGENTS.md")

    assert "MORE_IMPLEMENTATION_REQUIRED" in action_model
    assert "Role = role_for(Action)" in shared
    assert "agents/skills/openspec-delivery/SKILL.md" not in workflow
    assert "agents/skills/openspec-delivery/SKILL.md" not in shared
