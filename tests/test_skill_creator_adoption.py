from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "agents" / "skills" / "skill-creator"

UPSTREAM_FILES = {
    "LICENSE.txt",
    "SKILL.md",
    "agents/analyzer.md",
    "agents/comparator.md",
    "agents/grader.md",
    "assets/eval_review.html",
    "eval-viewer/generate_review.py",
    "eval-viewer/viewer.html",
    "references/schemas.md",
    "scripts/__init__.py",
    "scripts/aggregate_benchmark.py",
    "scripts/generate_report.py",
    "scripts/improve_description.py",
    "scripts/package_skill.py",
    "scripts/quick_validate.py",
    "scripts/run_eval.py",
    "scripts/run_loop.py",
    "scripts/utils.py",
}


def test_pinned_skill_creator_package_and_provenance() -> None:
    assert SKILL_ROOT.is_dir()
    actual = {
        str(path.relative_to(SKILL_ROOT))
        for path in SKILL_ROOT.rglob("*")
        if path.is_file()
    }
    assert UPSTREAM_FILES <= actual

    upstream = (SKILL_ROOT / "UPSTREAM.md").read_text()
    assert "0a64e398ec6bb34a494f0c347e8ccae53a862f8e" in upstream
    assert "3cf9a8db32597ba3e24b584a3d696f4e11c7d7b6" in upstream
    assert "## Added" in upstream
    deleted = upstream.split("## Deleted", 1)[1].split("## Modified", 1)[0]
    modified = upstream.split("## Modified", 1)[1]
    assert "none" in deleted.lower()
    assert "none" in modified.lower()
    assert "references/repository-governance.md" in upstream
    assert (SKILL_ROOT / "LICENSE.txt").exists()


def test_repository_governance_is_local_to_adopted_skill() -> None:
    assert not (ROOT / "agents" / "skills" / "skill-maintenance.md").exists()
    local = SKILL_ROOT / "references" / "repository-governance.md"
    text = local.read_text()
    assert "agents/AGENTS.md" in text
    assert "agents/roles/" in text
    assert "mapped" in text.lower()


def test_mapped_actions_conditionally_compose_skill_creator() -> None:
    paths = [
        "agents/skills/openspec-explore/SKILL.md",
        "agents/skills/openspec-change/SKILL.md",
        "agents/skills/openspec-review/SKILL.md",
        "agents/skills/implementation/SKILL.md",
        "agents/skills/implementation-review/SKILL.md",
    ]
    for path in paths:
        text = (ROOT / path).read_text()
        assert "agents/skills/skill-creator/SKILL.md" in text
        assert "repository Skills" in text or "Skill artifacts" in text

    agents = (ROOT / "agents" / "AGENTS.md").read_text()
    assert "action:skill-creator" not in agents
