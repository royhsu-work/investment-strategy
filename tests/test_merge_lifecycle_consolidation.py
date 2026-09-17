from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_implementation_pass_derives_explicit_implementation_merge_action() -> None:
    implementation_review = _read("agents/skills/implementation-review/SKILL.md")
    merge_pr = _read("agents/skills/merge-pr/SKILL.md")
    assert "derives merge-implementation-pr" in implementation_review
    assert "Reviewer PASS" in merge_pr
    assert "merge-implementation-pr" in merge_pr
    assert "merge-archive-pr" in merge_pr
    assert "generic merge label" in merge_pr


def test_archive_pass_derives_explicit_archive_merge_action() -> None:
    archive_review = _read("agents/skills/archive-review/SKILL.md")
    assert "derives merge-archive-pr" in archive_review


def test_merge_keeps_exact_head_and_non_closing_safety() -> None:
    merge_pr = _flat(_read("agents/skills/merge-pr/SKILL.md"))
    for required in (
        "exact PR identity",
        "current head",
        "non-closing linkage",
        "independent Reviewer PASS",
        "exact head unchanged",
        "fails closed",
        "Human freshness",
    ):
        assert required in merge_pr


def test_lifecycle_and_executor_keep_semantic_boundaries() -> None:
    finalize = _read("agents/skills/lifecycle-finalize/SKILL.md")
    executor = _read("agents/roles/executor.md")
    assert "archive preparation" in finalize
    assert "does not perform normal PR merge mutation" in finalize
    assert "exact repository mutation" in executor
    assert "A material semantic change is a Lead correction" in executor


def test_runtime_surfaces_do_not_introduce_a_second_merge_authorization_token() -> None:
    runtime_surfaces = (
        "agents/AGENTS.md",
        "agents/roles/lead.md",
        "agents/roles/executor.md",
        "agents/skills/implementation/SKILL.md",
        "agents/skills/implementation-review/SKILL.md",
        "agents/skills/archive-review/SKILL.md",
        "agents/skills/lifecycle-finalize/SKILL.md",
        "agents/skills/merge-pr/SKILL.md",
        "agents/templates/messages.md",
    )
    for path in runtime_surfaces:
        text = _read(path)
        assert "MERGE_AUTHORIZED" not in text
        assert "MERGE_AUTHORIZATION" not in text


def test_readme_names_merge_actions_without_a_generic_merge_action() -> None:
    readme = _read("README.md")
    assert "merge-implementation-pr" in readme
    assert "merge-archive-pr" in readme
    assert "merge authorization" not in readme
