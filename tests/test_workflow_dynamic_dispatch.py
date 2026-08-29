"""Contract coverage for dynamic dispatch, Slice checkpoints, and work-conserving lifecycle flow."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
WORKFLOW = ROOT / "agents" / "workflow.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
OPEN_SPEC_CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"
IMPLEMENTATION = ROOT / "agents" / "skills" / "implementation" / "SKILL.md"
MERGE_PR = ROOT / "agents" / "skills" / "merge-pr" / "SKILL.md"
LIFECYCLE_FINALIZE = ROOT / "agents" / "skills" / "lifecycle-finalize" / "SKILL.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _governance() -> str:
    return _read(AGENTS)


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_dispatch_mode_has_one_authoritative_marker() -> None:
    text = _governance()
    markers = re.findall(
        r"^Scheduled-Dispatch-Mode: (fixed-role|workflow-dynamic)$",
        text,
        re.MULTILINE,
    )
    assert markers == ["workflow-dynamic"]


def test_fixed_role_mode_preserves_lifecycle_priority_then_combined_intake() -> None:
    text = _normalized(AGENTS)
    for required in (
        "fixed-role",
        "legacy externally assigned role",
        "resolve-question > finalize-archive > finalize-change > pre-activation intake",
        "combined pre-activation queue",
        "earliest GitHub `created_at`",
        "lower Issue number",
        "MUST NOT choose different pre-activation winners",
    ):
        assert required in text


def test_dynamic_mode_uses_executable_normal_selection_authority() -> None:
    text = _normalized(AGENTS)
    for required in (
        "workflow-dynamic",
        "repository-owned executable dispatch is the only normal-selection authority",
        "authoritative current GitHub observations",
        "`AUTHORIZE`, `NO_WORK`, or `FAIL_CLOSED`",
        "only the returned exact Issue/role/action may determine the mapped model worker",
        "second natural-language classifier",
    ):
        assert required in text


def test_dynamic_dispatch_fails_closed_for_invalid_or_multiple_active_workflows() -> None:
    text = _normalized(AGENTS)
    for required in (
        "multiple open formal workflows produces `FAIL_CLOSED`",
        "invalid open routing",
        "Incomplete/provenance-invalid reconstruction",
        "A dispatch decision never substitutes for those downstream gates",
    ):
        assert required in text


def test_machine_selected_identity_is_worker_local_and_redispatched() -> None:
    text = _normalized(AGENTS)
    for required in (
        "before any mapped model invocation",
        "only the returned exact Issue/role/action may determine the mapped model worker",
        "repository-owned application fresh-reauthorizes",
        "fresh global dispatch",
        "single scheduled wake path",
        "fixed role schedule slots are not part of the normal authorization contract",
    ):
        assert required in text


def test_change_identity_defines_active_workflow_and_combined_pre_activation_intake() -> None:
    text = _normalized(AGENTS)
    for required in (
        "persisted non-`unset` `Change:` identity",
        "active workflow",
        "at most one active workflow",
        "`Lead / explore-change`",
        "`Lead / propose-change`",
        "`Change: unset`",
        "queued pre-activation work",
        "None of these entries count as an active formal workflow",
        "Formal activation remains owned by Propose",
    ):
        assert required in text


def test_combined_intake_is_executable_and_propose_keeps_activation_guards() -> None:
    text = _normalized(AGENTS)
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "combined pre-activation candidate contract",
        "coherent routed Explore",
        "coherent routed Propose",
        "earliest GitHub `created_at` then lower Issue number ordering",
        "Current routing debt is handled before intake",
        "A formal workflow otherwise wins over intake",
        "immediate pre-write and fresh post-write activation checks",
    ):
        assert required in text
    for required in (
        "shared dispatcher owns one combined pre-activation queue",
        (
            "every coherent open `Lead / explore-change + Change: unset` and "
            "`Lead / propose-change + Change: unset` entry"
        ),
        "MUST NOT reconstruct origin/admission history",
        "Require the consumed pre-write machine decision to authorize this exact Issue",
        "Repository application MUST fresh-reconstruct before applying the write",
        "dereference exactly one same-Issue durable Explore `ACTION_RESULT(PROPOSAL_READY)`",
        "action-local semantic preconditions still pass",
    ):
        assert required in change
    assert "approved Explore-origin set" not in change
    assert "executable-approved direct-Propose" not in text
    assert "same-Issue direct-Propose fallback" not in change


def test_activation_overlap_keeps_first_valid_write_and_fresh_decisions() -> None:
    shared = _normalized(AGENTS)
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "first-valid-write-wins",
        "Immediately before a non-`unset` `Change:` write",
        "must fresh-reauthorize this exact `Lead / propose-change` candidate",
        "newly fresh executable decision",
        "Stale, contradictory, incomplete, competing, or provenance-invalid evidence stops",
        "lock",
        "claim",
        "lease",
        "heartbeat",
    ):
        assert required in shared
    for required in (
        "application-time effect boundary",
        "first-valid-write-wins",
        "fresh-reconstruct before applying the write",
        "post-write decision",
        "rejects continuation",
    ):
        assert required in change


def test_explore_ordering_remains_executable_without_claim_or_status_state() -> None:
    shared = _normalized(AGENTS)
    explore = _normalized(EXPLORE)
    for required in (
        "earliest GitHub `created_at` then lower Issue number ordering",
        "No lock, claim, lease, heartbeat",
        "`status:exploring`",
    ):
        assert required in shared
    assert "Change: unset" in explore
    assert "does not require `status:exploring`" in explore


def test_orphan_evidence_blocks_new_activation_and_routes_to_bounded_lead_diagnosis() -> None:
    text = _normalized(AGENTS)
    for required in (
        "unexplained durable workflow evidence",
        "MUST NOT activate or execute queued pre-activation work",
        "Lead diagnosis",
        "decision-ready escalation",
        "repository-wide fault classifier",
    ):
        assert required in text


def test_human_authority_is_provenance_bound_and_notification_metadata_is_analytics_only() -> None:
    text = _normalized(AGENTS)
    for required in (
        "durable GitHub actor identity alone MUST NOT satisfy Human authority",
        "actors other than `royhsu-work`",
        "MUST NOT satisfy Human-required admission, answers, authorization, or resume conditions",
        "`performed_via_github_app == null`",
        "`Human-Decision-For: <decision_ref>`",
        "`human:approved`",
        "event-first",
        "`human:notified`",
        "analytics-only",
        "historical metadata",
        "MUST NOT grant authority",
    ):
        assert required in text


def test_lead_escalation_is_decision_ready_bounded_and_not_repeated() -> None:
    shared = _normalized(AGENTS)
    lead = _normalized(LEAD)
    for required in (
        "at most three actionable proposals",
        "material impact",
        "risk/trade-off",
        "Lead recommendation",
        "MUST NOT repeat materially equivalent unanswered notifications",
    ):
        assert required in shared
    for required in (
        "authoritative Human answer",
        "material evidence change",
        "no-op",
    ):
        assert required in lead


def test_verified_slice_requires_markers_and_bounded_issue_checkpoint() -> None:
    shared = _normalized(AGENTS)
    implementation = _normalized(IMPLEMENTATION)
    for required in (
        "one bounded checkpoint comment",
        "persistent coordination Issue",
        "completed slice/task IDs",
        "durable checkpoint or verified revision",
        "VERIFY/gate result",
        "remaining approved work or handoff",
        "before beginning the next slice or handing off",
    ):
        assert required in shared
    for required in (
        "one bounded checkpoint comment",
        "persistent coordination Issue",
        "PR/commit",
        "task markers",
        "CI evidence",
        "completion-boundary",
    ):
        assert required in implementation


def test_missing_verified_slice_checkpoint_is_recovered_without_replaying_completion() -> None:
    shared = _normalized(AGENTS)
    implementation = _normalized(IMPLEMENTATION)
    for required in (
        "task markers are durable but the checkpoint comment is missing",
        "does not rerun or clear the already verified slice",
        "persists the missing bounded checkpoint",
    ):
        assert required in shared
    for required in (
        "markers are already durable but the checkpoint comment is missing",
        "do not repeat the implementation or marker writes",
        "persist only the missing checkpoint",
        "before further slice work or handoff",
    ):
        assert required in implementation


def test_lifecycle_transitions_use_bounded_journal_without_per_mutation_logging() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "material workflow lifecycle transition",
        "one bounded comment on the persistent coordination Issue",
        "resulting durable state or evidence",
        "next action or terminal result",
        "journal comment itself",
        "does not recursively require another meta-comment",
        "Ordinary RED/GREEN/refactor/test-trigger/compatibility-correction commits",
        "do not independently require coordination-Issue comments",
        "lifecycle transition succeeds but its journal write is interrupted",
        "preserves the already durable transition",
        "before performing a further lifecycle transition or handoff",
    ):
        assert required in shared


def test_archive_merge_keeps_issue_open_and_hands_to_terminal_lead() -> None:
    topology = _normalized(WORKFLOW)
    merge = _normalized(MERGE_PR)
    for required in (
        "final Archive PR",
        "non-closing",
        "Lead / finalize-archive",
        "coordination Issue remains open",
    ):
        assert required in topology
    for required in (
        "Archive PR to be durably merged",
        "coordination Issue to remain open",
        ("replace the consumed routing tuple with exactly `agent:lead + action:finalize-archive`"),
        "merge/handoff journal",
        "do not re-merge",
        "repair only the missing terminal routing and journal evidence",
    ):
        assert required in merge


def test_lifecycle_complete_precedes_issue_close_and_closed_is_terminal_history() -> None:
    shared = _normalized(AGENTS)
    topology = _read(WORKFLOW).split("## Formal terminal completion", maxsplit=1)[1]
    finalize = _normalized(LIFECYCLE_FINALIZE)
    for required in (
        "LIFECYCLE_COMPLETE",
        "Issue close/routing retirement is incomplete",
        "closed + no workflow routing",
        "current closed-routing debt",
        "terminal history",
        "excluded from formal WIP",
    ):
        assert required in shared
    ordered = (
        "persist valid LIFECYCLE_COMPLETE",
        "close coordination Issue",
        "re-observe the same Issue as closed",
        "terminal history",
    )
    positions = [topology.index(item) for item in ordered]
    assert positions == sorted(positions)
    for required in (
        "LIFECYCLE_COMPLETE",
        "Archive PR exact head",
        "merge commit",
        "Issue is open",
        "Only after `LIFECYCLE_COMPLETE` is durable",
        "requires observed `closed`",
    ):
        assert required in finalize


def test_selected_workflow_is_work_conserving_until_a_legal_termination_boundary() -> None:
    shared = _normalized(AGENTS)
    implementation = _normalized(IMPLEMENTATION)
    for required in (
        "work-conserving execution is the default",
        "all immediately actionable work",
        "model worker ends early",
        "If no legal Exit class is proven",
        "failed-but-actionable validation",
        "verified Slice checkpoint",
        "Invocation Exit",
        "fresh executable redispatch",
        "fresh mapped model invocation",
        "genuine external asynchronous wait",
        "stale routing, revision, concurrency, or precondition loss",
        "cross-role transition does not wait for a dedicated role schedule slot",
    ):
        assert required in shared
    assert "continue on a later run" not in implementation
    assert "remaining approved implementation work" in implementation
    assert "same invocation" in implementation


def test_active_workflow_remains_wip_while_next_action_is_blocked() -> None:
    text = _normalized(AGENTS)
    for required in (
        "Execution eligibility",
        "same formal active workflow",
        "single formal WIP slot",
        "active workflow first",
        "pre-activation intake",
        "universal `blocked` result",
    ):
        assert required in text


def test_dispatch_requires_complete_executable_evidence_before_queue_selection() -> None:
    text = _normalized(AGENTS)
    for required in (
        "observable enumeration/provenance completeness",
        (
            "A partial enumeration is never proof of zero formal WIP or zero current "
            "closed-routing debt"
        ),
        "multiple open formal workflows produces `FAIL_CLOSED`",
        (
            "Any current closed-routing debt enters bounded candidate-specific exceptional "
            "classification before ordinary work"
        ),
        "Current routing debt is handled before intake",
    ):
        assert required in text
