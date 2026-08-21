from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_required_deferred_follow_up_has_one_shared_semantic_boundary() -> None:
    shared = _read("agents/AGENTS.md")
    assert "required deferred follow-up" in shared
    assert "ordinary out-of-scope" in shared
    assert "source coordination Issue/Change" in shared
    assert "exact defer decision" in shared
    assert "MUST NOT Human-admit" in shared


def test_required_deferred_follow_up_is_enforced_at_review_and_finalization() -> None:
    lead = _read("agents/roles/lead.md")
    review = _read("agents/skills/openspec-review/SKILL.md")
    finalize = _read("agents/skills/lifecycle-finalize/SKILL.md")

    assert "create or reuse" in lead and "required deferred follow-up" in lead
    assert "required deferred follow-up" in review
    assert "missing" in review and "tracker" in review
    assert "ordinary out-of-scope" in review.lower()
    assert "required deferred follow-up" in finalize
    assert "LIFECYCLE_COMPLETE" in finalize
    assert "tracker" in finalize


def test_same_role_transition_continues_only_same_issue_and_fixed_role() -> None:
    shared = _read("agents/AGENTS.md")
    topology = _read("agents/workflow.md")
    assert "same coordination Issue" in shared
    assert "fixed invocation role" in shared
    assert "legal successor from `agents/workflow.md` has the same role" in shared
    assert "load the target action's mapped default-branch skill" in shared
    assert "reconstruct the target action" in shared
    assert "cross-role" in shared and "Human authority" in shared
    assert "real external asynchronous wait" in shared
    assert "stale" in shared and "unsafe" in shared
    assert "Same-role and cross-role boundaries" in topology


def test_handoff_is_cross_role_only_and_same_role_needs_no_synthetic_message() -> None:
    shared = _read("agents/AGENTS.md")
    messages = _read("agents/templates/messages.md")
    change = _read("agents/skills/openspec-change/SKILL.md")

    assert "HANDOFF is cross-role" in shared
    assert "Same-role action transitions MUST NOT emit" in messages
    assert "source `ACTION_RESULT`" in messages
    assert "same-role" in change.lower()
    assert "without `HANDOFF`" in change


def test_openspec_change_observes_only_just_triggered_exact_validation_run() -> None:
    change = _read("agents/skills/openspec-change/SKILL.md")
    for required in (
        "just-triggered exact required run",
        "`queued` or `in_progress`",
        "bounded same-invocation observation",
        "same exact run",
        "becomes terminal",
        "continue immediately",
        "later wake",
        "fresh-read that exact run",
    ):
        assert required in change


def test_implementation_observes_only_just_triggered_exact_required_runs() -> None:
    implementation = _read("agents/skills/implementation/SKILL.md")
    for required in (
        "just-triggered exact required run",
        "Python Quality",
        "OpenSpec Validate",
        "`queued` or `in_progress`",
        "bounded same-invocation observation",
        "same exact run",
        "becomes terminal",
        "continue immediately",
        "later wake",
        "fresh-read that exact run",
        "no timer",
        "polling counter",
        "heartbeat",
        "hidden waiter",
    ):
        assert required in implementation
