from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "agents" / "workflow.md"


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
    positions = [text.index(item) for item in ordered]
    assert positions == sorted(positions)


def test_workflow_keeps_runtime_and_requirement_owners_distinct() -> None:
    text = WORKFLOW.read_text()
    assert "single authoritative repository owner" in text
    assert "Canonical OpenSpec owns approved capability requirements" in text
    assert "do not redefine this global topology" in text
