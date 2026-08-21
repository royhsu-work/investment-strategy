from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "agents" / "workflow.md"
AGENTS = ROOT / "agents" / "AGENTS.md"
README = ROOT / "README.md"


def _normal_transitions(text: str) -> set[tuple[str, str]]:
    rows: set[tuple[str, str]] = set()
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Current action |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break
        if line.startswith("| ---"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) != 3:
            continue
        rows.add((cells[0], cells[2]))
    return rows


def test_workflow_topology_owns_current_legal_progression() -> None:
    text = WORKFLOW.read_text()
    transitions = _normal_transitions(text)

    required = {
        ("Lead / propose-change", "Reviewer / review-openspec"),
        ("Reviewer / review-openspec", "Executor / implement-change"),
        ("Reviewer / review-openspec", "Lead / resolve-question"),
        ("Lead / resolve-question", "Reviewer / review-openspec"),
        ("Lead / resolve-question", "Executor / implement-change"),
        ("Executor / implement-change", "Reviewer / review-implementation"),
        ("Executor / implement-change", "Lead / resolve-question"),
        ("Reviewer / review-implementation", "Executor / implement-change"),
        ("Reviewer / review-implementation", "Executor / merge-pr"),
        ("Executor / merge-pr", "Lead / finalize-change"),
        ("Lead / finalize-change", "Executor / implement-change"),
        ("Lead / finalize-change", "Reviewer / review-archive"),
        ("Reviewer / review-archive", "Lead / finalize-change"),
        ("Reviewer / review-archive", "Executor / merge-pr"),
        ("Executor / merge-pr", "Lead / finalize-archive"),
    }
    assert required <= transitions


def test_workflow_preserves_explore_terminal_outcomes() -> None:
    text = WORKFLOW.read_text()
    for disposition in (
        "PROPOSAL_READY",
        "HUMAN_DECISION_REQUIRED",
        "NO_CHANGE_REQUIRED",
        "NO_GO",
    ):
        assert f"`{disposition}`" in text


def test_workflow_preserves_post_115_terminal_order() -> None:
    text = WORKFLOW.read_text()
    terminal = text.split("## Formal terminal completion", maxsplit=1)[1]
    ordered = [
        "final Archive PR exact-head review PASS",
        "Executor merges exact accepted Archive revision",
        "coordination Issue remains open",
        "route Lead / finalize-archive",
        "persist valid LIFECYCLE_COMPLETE",
        "close coordination Issue",
        "re-observe the same Issue as closed",
        "terminal history",
    ]
    positions = [terminal.index(item) for item in ordered]
    assert positions == sorted(positions)


def test_workflow_keeps_runtime_and_requirement_owners_distinct() -> None:
    text = WORKFLOW.read_text()
    assert "single authoritative repository owner" in text
    assert "Canonical OpenSpec owns approved capability requirements" in text
    assert "do not redefine this global topology" in text


def test_shared_governance_names_workflow_as_topology_owner() -> None:
    text = AGENTS.read_text()
    assert (
        "`agents/workflow.md` owns end-to-end Scheduled-Agent runtime workflow "
        "topology and lifecycle relationships"
    ) in text
    assert (
        "`agents/AGENTS.md` owns shared Scheduled-Agent runtime execution protocol "
        "and cross-role invariants"
    ) in text


def test_readme_points_to_authoritative_workflow_instead_of_copying_final_path() -> None:
    text = README.read_text()
    expected = "authoritative runtime workflow topology 位於 default-branch `agents/workflow.md`"
    assert expected in text
    assert "Final lifecycle 的高階導覽是：" not in text


def test_shared_governance_uses_topology_reference_for_semantic_correction_paths() -> None:
    text = AGENTS.read_text()
    assert "correction path defined in `agents/workflow.md`" in text
    assert (
        "Executor / implement-change → Lead /\n"
        "resolve-question → Reviewer / review-openspec → Executor / implement-change"
    ) not in text
    assert (
        "Reviewer / review-openspec PASS → Executor / implement-change →\n"
        "Reviewer / review-implementation"
    ) not in text


def test_roles_and_mapped_skills_do_not_define_a_second_global_transition_table() -> None:
    surfaces = list((ROOT / "agents" / "roles").glob("*.md"))
    surfaces.extend((ROOT / "agents" / "skills").glob("*/SKILL.md"))
    assert surfaces
    for surface in surfaces:
        assert "| Current action |" not in surface.read_text(), surface
