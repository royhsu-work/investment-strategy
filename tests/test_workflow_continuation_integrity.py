from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split())


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


def test_action_transition_redispatches_same_issue_with_fresh_worker() -> None:
    shared = _read("agents/AGENTS.md")
    topology = _read("agents/workflow.md")
    assert "same coordination Issue" in shared
    assert (
        "only the returned exact Issue/role/action may determine the mapped model worker" in shared
    )
    assert "fresh executable redispatch" in shared
    assert "fresh mapped model invocation" in shared
    assert "Same-role transition does not mean same-model continuation" in shared
    assert "cross-role transition does not wait for a dedicated role schedule slot" in shared
    assert "cross-role" in shared and "Human authority" in shared
    assert "real external asynchronous wait" in shared
    assert "stale" in shared and "unsafe" in shared
    assert "Same-role and cross-role boundaries" in topology


def test_scheduled_wake_uses_prompt_role_boundary_and_cross_role_is_wake_terminal() -> None:
    shared = _read("agents/AGENTS.md")
    messages = _read("agents/templates/messages.md")
    topology = _read("agents/workflow.md")

    for required in (
        "first repository-owned `AUTHORIZE` decision",
        "authoritative model/governance instruction",
        "same scheduled wake",
        "cross-role",
        "later scheduled wake",
    ):
        assert required in shared

    for forbidden in (
        "invocation-local `initial_role`",
        "role == initial_role",
        "role != initial_role",
    ):
        assert forbidden not in shared

    for required in (
        "same scheduled wake",
        "wake-terminal",
        "later scheduled wake",
        "fresh mapped model invocation",
        "prompt/model-level",
    ):
        assert required in messages

    old_cross_role_continuation = (
        "cross-role continuation likewise receives a fresh invocation for the newly "
        "machine-selected role"
    )
    assert old_cross_role_continuation not in messages
    assert "target role differs from the fixed invocation role" in topology
    assert "invocation ends" in topology


def test_wake_barrier_preserves_routing_without_mechanical_wake_state() -> None:
    shared = _read("agents/AGENTS.md")

    for required in (
        "durable successor routing",
        "prompt/model-level",
        "does not wait for a dedicated fixed-role schedule slot",
        "second workflow DAG",
        "fixed role schedule slots are not part of the normal authorization contract",
    ):
        assert required in shared

    for forbidden in (
        "persist wake-role state",
        "repository-owned mechanical hard-stop",
    ):
        assert forbidden not in shared


def test_external_scheduled_task_guidance_remains_generic_bootstrap() -> None:
    migration = _read("agents/scheduled-task-migration.md")

    assert "common bootstrap prompt" in migration
    assert "Scheduled Task prompts remain bootstrap-only" in migration
    assert "load default-branch governance" in migration
    assert "must not duplicate" in migration
    assert "workflow DAG" not in migration
    assert "initial_role" not in migration


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
        "absent, `queued`, or `in_progress`",
        "subsequent fresh observation",
        "same exact target/resource",
        "becomes terminal",
        "continue",
        "later fresh mapped invocation",
        "fresh-read that exact run",
        "no other immediately actionable same-authority work remains",
    ):
        assert required in change


def test_implementation_observes_only_just_triggered_exact_required_runs() -> None:
    implementation = _read("agents/skills/implementation/SKILL.md")
    for required in (
        "just-triggered exact required run",
        "Python Quality",
        "OpenSpec Validate",
        "absent, `queued`, or `in_progress`",
        "subsequent fresh observation",
        "same exact target/resource",
        "becomes terminal",
        "continue",
        "later wake",
        "fresh-read that exact run",
        "no timer",
        "polling counter",
        "heartbeat",
        "hidden waiter",
    ):
        assert required in implementation
