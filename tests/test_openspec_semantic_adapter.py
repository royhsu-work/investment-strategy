from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
ADAPTER = AGENTS / "skills/openspec-semantic-adapter.md"
CHANGE = AGENTS / "skills/openspec-change/SKILL.md"
REVIEW = AGENTS / "skills/openspec-review/SKILL.md"
IMPLEMENTATION = AGENTS / "skills/implementation/SKILL.md"
CONFIG = ROOT / "openspec/config.yaml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_spec_driven_actions_share_one_adapter_without_new_runtime_authority() -> None:
    config = _read(CONFIG)
    adapter = _normalized(ADAPTER)
    assert "schema: spec-driven" in config
    assert "not runtime routing authority" in adapter
    runtime_authority = (
        "agents/AGENTS.md` remains the sole Scheduled runtime workflow/routing authority"
    )
    assert runtime_authority in adapter

    for skill in (CHANGE, REVIEW, IMPLEMENTATION):
        text = _normalized(skill)
        assert "openspec-semantic-adapter.md" in text
        assert "schema: spec-driven" in text
        assert "fail closed" in text


def test_adapter_records_immutable_semantic_and_executable_provenance() -> None:
    adapter = _normalized(ADAPTER)
    assert "Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020" in adapter
    assert "schemas/spec-driven/schema.yaml" in adapter
    assert "@fission-ai/openspec@1.3.1" in adapter
    assert "mutable upstream `main`" in adapter
    assert "material represented semantic contract no longer matches this baseline" in adapter


def test_adapter_declares_spec_driven_dependency_readiness() -> None:
    adapter = _normalized(ADAPTER)
    for required in (
        "`proposal` has no artifact prerequisite",
        "`specs` and `design` each require `proposal`",
        "`tasks` requires both `specs` and `design`",
        "Apply requires `tasks`",
        "skip_specs: true",
    ):
        assert required in adapter


def test_adapter_rejects_incomplete_canonicalization_semantics_before_implementation() -> None:
    adapter = _normalized(ADAPTER)
    review = _normalized(REVIEW)
    change = _normalized(CHANGE)

    for required in (
        "exactly one non-empty `## Purpose`",
        "ADDED requirement identifier must not already exist canonically",
        "partial MODIFIED block that unintentionally drops surviving scenarios/content is invalid",
        "REMOVED",
        "RENAMED",
        "Rename plus behavior change",
    ):
        assert required in adapter

    assert "strict validation alone" in change
    assert "even when strict validation passes" in review
    assert "preserve every still-applicable scenario/content" in review


def test_executor_apply_context_is_closed_and_specification_authority_stays_with_lead() -> None:
    adapter = _normalized(ADAPTER)
    implementation = _normalized(IMPLEMENTATION)

    for required in (
        "approved proposal",
        "applicable delta specs",
        "approved design",
        "approved tasks",
        "canonical specs needed to interpret modified behavior",
        "materially applicable default-branch `openspec/config.yaml` context/rules",
    ):
        assert required in adapter

    assert "SPEC_BLOCKER" in implementation
    assert "choosing which upstream/config semantics count" in implementation
    assert "does not grant Executor specification authority" in implementation


def test_adapter_keeps_archive_guards_and_executable_upgrade_out_of_scope() -> None:
    adapter = _normalized(ADAPTER)
    assert "Executable-version upgrade/compatibility work remains separate" in adapter
    assert "Archive validation remains deterministic defense-in-depth" in adapter
