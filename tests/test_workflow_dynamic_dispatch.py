"""Contract coverage for dynamic dispatch, Slice checkpoints, and work-conserving lifecycle flow."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
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


def test_dynamic_mode_selects_role_from_single_active_workflow() -> None:
    text = _normalized(AGENTS)
    for required in (
        "workflow-dynamic",
        "Exactly one active workflow",
        "valid routing tuple",
        "determines the invocation role/action and mapped skill",
        "global urgency",
        "second workflow DAG",
    ):
        assert required in text


def test_dynamic_dispatch_fails_closed_for_invalid_or_multiple_active_workflows() -> None:
    text = _normalized(AGENTS)
    for required in (
        "multiple active workflows",
        "fail closed",
        "invalid routing",
        "MUST NOT guess",
    ):
        assert required in text


def test_invocation_role_is_fixed_but_same_role_actions_may_continue() -> None:
    text = _normalized(AGENTS)
    for required in (
        "fixed invocation role",
        "selected coordination Issue remains fixed",
        "cross-role handoff",
        "current invocation MUST then end",
        "does not redispatch to the new role",
        "same-role action transition",
        "may continue on the same coordination Issue",
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


def test_combined_intake_is_deterministic_and_refuses_later_propose_activation() -> None:
    text = _normalized(AGENTS)
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "combined pre-activation queue",
        "earliest GitHub `created_at`",
        "lower Issue number",
        "there is no `explore-change > propose-change` priority",
        "MUST NOT activate a queued proposal",
        "older eligible Explore/direct-Propose entry",
        "formal active or terminal-pending workflow must win over pre-activation intake",
    ):
        assert required in text
    for required in (
        "complete shared pre-activation candidate-set contract",
        "every coherent open `Lead / explore-change + Change: unset` entry",
        "every legally admitted `Lead / propose-change + Change: unset` entry",
        "Do not maintain or infer an action-local Explore-origin admission enumeration",
        (
            "A later proposal-ready direct-Propose Issue MUST NOT activate while an older "
            "eligible Explore candidate"
        ),
        "same-Issue direct-Propose fallback preserving its original authority envelope",
        "re-read durable state and require this Issue to remain the combined pre-activation winner",
    ):
        assert required in change
    assert "approved Explore-origin set" not in change


def test_activation_overlap_uses_first_valid_write_and_stale_run_termination() -> None:
    shared = _normalized(AGENTS)
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "first-valid-write-wins",
        "re-read",
        "stale",
        "lock",
        "claim",
        "lease",
        "heartbeat",
    ):
        assert required in shared
    for required in (
        "reconstruct active workflow state before persisting an unset Change identity",
        "first valid activation",
        "re-read durable state",
        "stop as stale",
    ):
        assert required in change


def test_oldest_explore_stays_winner_without_claim_or_status_state() -> None:
    shared = _normalized(AGENTS)
    explore = _normalized(EXPLORE)

    for required in (
        "oldest eligible open Explore naturally remains the deterministic winner across wakes",
        "no claim, lease, heartbeat, or hidden ownership state",
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


def test_archive_native_close_hands_off_to_terminal_lead_without_role_switch() -> None:
    shared = _normalized(AGENTS)
    merge = _normalized(MERGE_PR)
    for required in (
        "final Archive PR",
        "natively closed",
        "`agent:lead + action:finalize-archive`",
        "closed Issue",
        "bounded merge/native-close/handoff journal",
        "MUST NOT execute Lead finalization in the same invocation",
    ):
        assert required in shared
    for required in (
        "Archive PR is durably merged",
        "coordination Issue is observed natively `closed`",
        "replace the consumed routing tuple with exactly `agent:lead + action:finalize-archive`",
        "bounded merge/native-close/handoff journal",
        "do not re-merge",
        "repair only the missing terminal routing and journal evidence",
    ):
        assert required in merge


def test_closed_terminal_pending_work_blocks_activation_until_lifecycle_complete() -> None:
    shared = _normalized(AGENTS)
    finalize = _normalized(LIFECYCLE_FINALIZE)
    for required in (
        "terminal-pending active workflow",
        "closed coordination Issue",
        "`agent:lead + action:finalize-archive`",
        "accepted merged Archive PR",
        "no valid Lead `LIFECYCLE_COMPLETE`",
        "MUST NOT activate or execute queued pre-activation intake",
        "terminal history",
        "MUST NOT block later workflow admission",
    ):
        assert required in shared
    for required in (
        "LIFECYCLE_COMPLETE",
        "Archive PR exact head",
        "merge commit",
        "does not reopen or redundantly close the Issue",
        "canonical archived default-branch state",
        "observed native Issue closure",
    ):
        assert required in finalize


def test_selected_workflow_is_work_conserving_until_a_legal_termination_boundary() -> None:
    shared = _normalized(AGENTS)
    implementation = _normalized(IMPLEMENTATION)

    for required in (
        "work-conserving",
        "all immediately actionable work",
        "current action",
        "failed-but-actionable validation",
        "verified Slice checkpoint",
        "not a legal voluntary yield point",
        "target role equals the fixed invocation role",
        "reconstruct the target action",
        "real external asynchronous wait",
        "stale/concurrency loss",
        "cross-role",
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
        "active/terminal-pending workflow first",
        "pre-activation intake",
        "universal `blocked` result",
    ):
        assert required in text


def test_dispatch_requires_complete_active_cardinality_before_queue_selection() -> None:
    text = _normalized(AGENTS)
    for required in (
        "complete cardinality",
        "terminal-pending and formal active workflows",
        "Before evaluating pre-activation queue",
        "partial enumeration",
        "MUST NOT",
        "queued work",
    ):
        assert required in text
