"""Contract coverage for Scheduled-Agent operational flow control."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
OPEN_SPEC_CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"
EXPLORE = ROOT / "agents" / "skills" / "openspec-explore" / "SKILL.md"
MIGRATION = ROOT / "agents" / "scheduled-task-migration.md"


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_closed_nonterminal_work_is_not_normal_routing_eligibility() -> None:
    text = _normalized(AGENTS)
    for required in (
        "Any closed Issue retaining a repository-governed `agent:*` or `action:*` label",
        "current routing debt rather than ordinary routing eligibility",
        "partial residue containing only one side of the tuple still counts as debt",
        "bounded candidate-specific executable boundary",
    ):
        assert required in text


def test_unique_premature_close_candidate_keeps_bounded_lead_recovery() -> None:
    shared = _normalized(AGENTS)
    lead = _normalized(LEAD)
    for required in (
        (
            "Exactly one qualifying unfinished candidate may use premature-close recovery "
            "only at formal-zero"
        ),
        "`Lead / resolve-question`",
        "An open formal workflow coexisting with unfinished or indeterminate debt fails closed",
        "no second unresolved debt candidate exists",
    ):
        assert required in shared
    for required in (
        "unfinished-recovery",
        "reopen",
        "preserving",
        "fresh dispatch",
        "no competing debt/open formal workflow",
    ):
        assert required in lead


def test_ambiguous_or_human_terminated_premature_close_stays_fail_closed() -> None:
    text = _normalized(AGENTS)
    for required in (
        "multiple unfinished candidates, any indeterminate candidate",
        "Human-retirement evidence",
        "candidate-bound",
        "no central workflow engine",
    ):
        assert required in text


def test_required_separate_follow_up_is_directly_routed_to_explore() -> None:
    shared = _normalized(AGENTS)
    lead = _normalized(LEAD)
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "required separate follow-up",
        "`Change: unset + agent:lead + action:explore-change`",
        "source coordination Issue/Change",
        "exact defer decision/reference",
        "combined pre-activation queue",
        "MUST NOT require Human admission or a second idle-discovery admission step",
    ):
        assert required in shared
    for required in (
        "required deferred follow-up",
        "route it directly to `Lead / explore-change`",
        "Change: unset",
        "source coordination Issue/Change",
        "exact defer decision/reference",
    ):
        assert required in lead
    for required in (
        "required deferred follow-up",
        "reconstruct the approved source obligation and all matching trackers",
        "`agent:lead + action:explore-change`",
        "without Human admission",
    ):
        assert required in change


def test_current_routed_intake_is_origin_neutral_but_creation_remains_bounded() -> None:
    shared = _normalized(AGENTS)
    for required in (
        (
            "Open `Lead / explore-change + Change: unset` and "
            "`Lead / propose-change + Change: unset` entries are legal queued pre-activation work "
            "when routing is coherent"
        ),
        (
            "Origin, admission history, and semantic readiness do not control dispatcher "
            "eligibility for either current tuple"
        ),
        "Scheduled Agents MUST NOT create arbitrary routed Explore work",
        "deduplication and one-candidate limits",
        (
            "required separate follow-up routing remains derived from its exact "
            "approved source defer decision/linkage"
        ),
    ):
        assert required in shared
    for obsolete in (
        "approved origin classes",
        "creation-bound Human Explore admission alternative",
        "complete approved origin set",
        "direct-Propose fallback preserves the original Propose authority envelope",
    ):
        assert obsolete not in shared


def test_propose_activation_consumes_current_routing_shared_queue() -> None:
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "shared dispatcher owns one combined pre-activation queue",
        (
            "every coherent open `Lead / explore-change + Change: unset` and "
            "`Lead / propose-change + Change: unset` entry"
        ),
        "MUST NOT reconstruct origin/admission history",
        "Require the consumed pre-write machine decision to authorize this exact Issue",
        "independently choose among queued candidates",
        "action-local semantic preconditions still pass",
    ):
        assert required in change
    assert "approved Explore-origin set" not in change
    assert "same-Issue direct-Propose fallback" not in change


def test_optional_or_plain_deferred_work_does_not_create_queue_admission() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "ordinary out-of-scope item",
        "non-goal",
        "optional future idea",
        "creates no tracking obligation",
        "MUST NOT receive workflow routing",
    ):
        assert required in shared


def test_selected_propose_research_gap_returns_same_issue_without_dispatcher_fallback() -> None:
    change = _normalized(OPEN_SPEC_CHANGE)
    explore = _normalized(EXPLORE)
    for required in (
        "Missing, ambiguous, stale, contradictory, unsupported, or materially invalidated baseline/source evidence does not cause dispatcher fallback to another queued Issue",
        "`RESEARCH_REQUIRED`",
        "same Issue `Lead / propose-change → Lead / explore-change` correction",
        "preserving `Change: unset` and the Issue's original queue identity",
    ):
        assert required in change
    for required in (
        "`RESEARCH_REQUIRED`",
        "repository application derives the same-Issue correction back to `Lead / explore-change`",
        "This retains the selected Issue rather than falling through to later work",
    ):
        assert required in explore


def test_propose_research_correction_is_bounded_by_human_and_formal_boundaries() -> None:
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "the worker MUST NOT request the correction routing itself",
        "still researchable within the same bounded problem",
        "new Human-reserved requirement, scope/risk acceptance, or architecture decision",
        "Once a non-`unset` Change identity exists",
        "formal semantic correction uses `Lead / resolve-question`",
    ):
        assert required in change


def test_project_kanban_projection_cannot_substitute_for_repository_authority() -> None:
    orientation = _normalized(MIGRATION)
    for required in (
        "GitHub Project/Kanban",
        "presentation only",
        (
            "they do not participate in Scheduled-Agent dispatch, routing, "
            "authority, or gate decisions"
        ),
        "Repository durable workflow state remains authoritative",
    ):
        assert required in orientation
