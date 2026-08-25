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


def test_routed_explore_is_origin_neutral_but_creation_remains_bounded() -> None:
    shared = _normalized(AGENTS)
    for required in (
        "ordinary routed Explore eligibility does not require Human approval",
        "origin does not control dispatcher eligibility",
        "Scheduled Agents MUST NOT create arbitrary routed Explore work",
        "deduplication and one-candidate limits",
        (
            "required separate follow-up routing remains derived from its exact "
            "approved source defer decision/linkage"
        ),
        "direct-Propose fallback preserves the original Propose authority envelope",
    ):
        assert required in shared
    for obsolete in (
        "approved origin classes",
        "creation-bound Human Explore admission alternative",
        "complete approved origin set",
    ):
        assert obsolete not in shared


def test_propose_activation_consumes_origin_neutral_shared_queue() -> None:
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "complete shared pre-activation candidate-set contract",
        "every coherent open `Lead / explore-change + Change: unset` entry",
        "Do not maintain or infer an action-local Explore-origin admission enumeration",
        "same-Issue direct-Propose fallback preserving its original authority envelope",
        "MUST NOT activate while an older eligible Explore candidate",
        "deterministic combined pre-activation winner",
    ):
        assert required in change
    assert "approved Explore-origin set" not in change
    assert "combine valid Human-admitted open `Lead / explore-change + Change: unset`" not in change


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


def test_unset_direct_propose_may_fall_back_to_explore_without_second_admission() -> None:
    change = _normalized(OPEN_SPEC_CHANGE)
    explore = _normalized(EXPLORE)
    for required in (
        "Change: unset",
        "not yet proposal-ready",
        "requested same-Issue routing effect to `Lead / explore-change`",
        "do not request `HANDOFF` or a second Human admission",
        "fresh post-apply dispatch",
    ):
        assert required in change
    for required in (
        "pre-activation Propose fallback",
        "same admitted authority envelope",
        "returns to `Lead / propose-change`",
        "no second Human admission",
    ):
        assert required in explore


def test_activated_change_cannot_fall_back_from_propose_to_explore() -> None:
    change = _normalized(OPEN_SPEC_CHANGE)
    for required in (
        "non-`unset` Change",
        "MUST NOT route backward to Explore",
        "`Lead / resolve-question`",
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
