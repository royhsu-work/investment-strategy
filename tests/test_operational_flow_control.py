"""Contract coverage for Scheduled-Agent operational flow control."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents" / "AGENTS.md"
LEAD = ROOT / "agents" / "roles" / "lead.md"
OPEN_SPEC_CHANGE = ROOT / "agents" / "skills" / "openspec-change" / "SKILL.md"


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_closed_nonterminal_work_is_not_executable_while_closed() -> None:
    text = _normalized(AGENTS)
    for required in (
        "closed nonterminal",
        "contradictory durable state",
        "MUST NOT execute its stale routed action while closed",
        "terminal-pending `Lead / finalize-archive`",
    ):
        assert required in text


def test_unique_premature_close_candidate_uses_bounded_lead_recovery() -> None:
    shared = _normalized(AGENTS)
    lead = _normalized(LEAD)
    for required in (
        "premature-close recovery candidate",
        "`Lead / resolve-question`",
        "reopen that same coordination Issue",
        "immutable Change identity",
        "pre-close nonterminal routing tuple",
        "repository-wide active cardinality",
        "recovery invocation MUST NOT execute the preserved normal lifecycle action",
        "later wake",
    ):
        assert required in shared
    for required in (
        "premature-close recovery",
        "reopen",
        "preserve",
        "fresh-read",
        "single coherent formal active workflow",
    ):
        assert required in lead


def test_ambiguous_or_human_terminated_premature_close_stays_fail_closed() -> None:
    text = _normalized(AGENTS)
    for required in (
        "qualifying provenance-bound Human decision",
        "second premature-close recovery candidate",
        "MUST remain fail closed",
        "MUST NOT reopen by inference",
        "generic fault state machine",
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
        "create or reuse",
        "`agent:lead + action:explore-change`",
        "without Human admission",
    ):
        assert required in change


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
