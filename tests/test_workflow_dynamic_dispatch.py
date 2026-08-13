"""Contract coverage for dynamic dispatch, checkpoints, journaling, and terminal lifecycle."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
OPEN_SPEC_CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
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
    assert markers == ["fixed-role"]


def test_fixed_role_mode_preserves_legacy_role_local_discovery() -> None:
    text = _normalized(AGENTS)
    for required in (
        "fixed-role",
        "legacy externally assigned role",
        "role-local action priority",
        "earlier GitHub `created_at` wins",
        "lower numeric Issue number wins",
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


def test_invocation_role_is_immutable_after_dynamic_dispatch() -> None:
    text = _normalized(AGENTS)
    for required in (
        "invocation role MUST remain fixed",
        "current invocation MUST end",
        "does not redispatch",
    ):
        assert required in text


def test_change_identity_defines_single_active_workflow_and_queued_proposals() -> None:
    text = _normalized(AGENTS)
    for required in (
        "persisted non-`unset` `Change:` identity",
        "active workflow",
        "at most one",
        "`Change: unset`",
        "queued pre-activation",
        "MUST NOT count as an active workflow",
    ):
        assert required in text


def test_queued_activation_is_deterministic_and_refuses_second_active_change() -> None:
    text = _normalized(AGENTS)
    for required in (
        "MUST NOT activate a queued proposal while another active workflow exists",
        "earliest GitHub `created_at`",
        "lower Issue number",
        "persists its immutable Change identity",
    ):
        assert required in text


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


def test_orphan_evidence_blocks_new_activation_and_routes_to_bounded_lead_diagnosis() -> None:
    text = _normalized(AGENTS)
    for required in (
        "unexplained durable workflow evidence",
        "MUST NOT activate queued proposal work",
        "Lead diagnosis",
        "decision-ready escalation",
        "repository-wide fault classifier",
    ):
        assert required in text


def test_human_authority_is_actor_bound_and_notification_metadata_is_analytics_only() -> None:
    text = _normalized(AGENTS)
    for required in (
        "actor `royhsu-work`",
        "other actors",
        "MUST NOT satisfy Human-required admission, answers, authorization, or resume conditions",
        "`human:notified`",
        "analytics-only metadata",
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


def test_substantive_mutations_require_bounded_journal_and_interrupted_write_recovery() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "substantive durable workflow mutation",
        "one bounded comment on the persistent coordination Issue",
        "resulting durable state or evidence",
        "next action or terminal result",
        "journal comment itself",
        "does not recursively require another meta-comment",
        "mutation succeeds but its journal write is interrupted",
        "preserves the already durable mutation",
        "before performing further substantive workflow mutation or handoff",
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
        "authorized merged Archive PR",
        "no valid Lead `LIFECYCLE_COMPLETE`",
        "MUST NOT activate a queued proposal",
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
