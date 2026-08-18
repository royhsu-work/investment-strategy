from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_implementation_pass_routes_directly_to_executor_merge() -> None:
    implementation_review = _read("agents/skills/implementation-review/SKILL.md")
    merge_pr = _read("agents/skills/merge-pr/SKILL.md")

    assert "`PASS` → `Executor / merge-pr`" in implementation_review
    assert "Reviewer PASS" in merge_pr
    assert "Lead authorization" not in merge_pr


def test_normal_implementation_merge_has_no_lead_authorization_hop() -> None:
    finalize = _read("agents/skills/lifecycle-finalize/SKILL.md")
    executor = _read("agents/roles/executor.md")

    assert "MERGE_AUTHORIZED" not in executor
    assert "Before merge authorization" not in finalize


def test_archive_preparation_is_complete_before_reviewer_handoff() -> None:
    finalize = _read("agents/skills/lifecycle-finalize/SKILL.md")
    archive_review = _read("agents/skills/archive-review/SKILL.md")

    assert "before `Reviewer / review-archive`" in finalize
    assert "required deferred follow-up" in finalize
    assert "temporary correction/recovery" in finalize
    assert "Lead preparation evidence" in archive_review


def test_archive_pass_routes_directly_to_executor_merge() -> None:
    archive_review = _read("agents/skills/archive-review/SKILL.md")

    assert "`PASS` → `Executor / merge-pr`" in archive_review


def test_shared_merge_contract_consumes_reviewer_pass_without_lead_token() -> None:
    shared = _read("agents/AGENTS.md")

    assert "Reviewer PASS for revision R" in shared
    assert "Lead MERGE_AUTHORIZED for revision R" not in shared
    assert "current PR head == R" in shared
    assert "required gate remains valid and non-contradictory" in shared


def test_shared_linkage_contract_has_no_second_lead_merge_token() -> None:
    shared = _read("agents/AGENTS.md")
    linkage = shared.split("## PR linkage lifecycle boundary", 1)[1].split(
        "## Routing validity", 1
    )[0]

    assert "Lead authorization" not in linkage
    assert "MERGE_AUTHORIZED" not in linkage


def test_merge_skill_keeps_path_specific_fresh_read_preconditions() -> None:
    merge_pr = _read("agents/skills/merge-pr/SKILL.md")

    assert "The target PR current head still equals R" in merge_pr
    assert "Required gates/checks remain valid" in merge_pr
    assert "does not establish GitHub Issue-closing" in merge_pr
    assert "Lead preparation evidence reviewed with PASS remains materially current" in merge_pr
    assert "No separate Lead merge-authorization token" in merge_pr


def test_normal_archive_branch_is_not_temporary_cleanup_input() -> None:
    finalize = _flat(_read("agents/skills/lifecycle-finalize/SKILL.md"))
    merge_pr = _flat(_read("agents/skills/merge-pr/SKILL.md"))
    shared = _flat(_read("agents/AGENTS.md"))

    assert "`agent/archive-<change>` branch is a lifecycle artifact" in finalize
    assert "never inferred to be temporary merely from" in finalize
    assert "The normal `agent/archive-<change>` branch" in merge_pr
    assert "never a temporary cleanup target merely because of its name" in merge_pr
    assert "never inferred to be temporary cleanup input from its name" in shared


def test_temporary_cleanup_requires_separate_durable_recovery_provenance() -> None:
    finalize = _flat(_read("agents/skills/lifecycle-finalize/SKILL.md"))
    merge_pr = _flat(_read("agents/skills/merge-pr/SKILL.md"))

    assert "explicit durable lifecycle, correction, integration, or recovery provenance" in finalize
    assert "explicitly provenance-owned temporary correction/recovery branches" in merge_pr
    assert "dispositions reviewed with the Archive target" in merge_pr
    assert "broad branch garbage collection" in merge_pr


def test_current_runtime_surfaces_do_not_reintroduce_merge_authorization_token() -> None:
    runtime_surfaces = (
        "agents/AGENTS.md",
        "agents/roles/lead.md",
        "agents/roles/executor.md",
        "agents/skills/implementation-review/SKILL.md",
        "agents/skills/archive-review/SKILL.md",
        "agents/skills/lifecycle-finalize/SKILL.md",
        "agents/skills/merge-pr/SKILL.md",
        "agents/templates/messages.md",
    )

    for path in runtime_surfaces:
        text = _read(path)
        assert "MERGE_AUTHORIZED" not in text, path
        assert "## `MERGE_AUTHORIZATION`" not in text, path


def test_readme_orientation_does_not_name_retired_merge_authorization() -> None:
    readme = _read("README.md")

    assert "merge authorization" not in readme
    assert "merge acceptance" in readme
