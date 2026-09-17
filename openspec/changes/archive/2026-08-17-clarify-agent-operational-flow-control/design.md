# Design: Scheduled-Agent operational flow control

## Decision 1 — Keep lifecycle, eligibility, and scheduling orthogonal

The existing role/action state machine remains the only lifecycle/routing authority. Execution eligibility is derived at the selected action boundary from durable preconditions already owned by that action. Human waits, CI waits, environment limitations, conflicts, and dependencies therefore remain evidence/reasons for why the next action cannot currently complete rather than new lifecycle states.

Trace: requirement `Operational execution eligibility remains orthogonal to lifecycle state`.

This intentionally reuses the existing Human escalation, asynchronous-resource, execution-exception, and action-specific disposition contracts. A universal blocker enum or `status:blocked` label would duplicate those owners and create a second state machine.

## Decision 2 — Formal WIP remains exactly one, including blocked work

The current single-active invariant is the executable WIP limit. A blocked formal workflow continues to occupy that slot. Releasing WIP on a wait would permit another Change to activate and recreate ambiguous multiple-active state, as observed with #48/#49.

The scheduling policy is therefore finish-first for formal work: active/terminal-pending workflow first; only when none exists does the existing combined pre-activation FIFO queue apply. No expedite lane or global priority scoring is introduced.

Trace: requirements `Operational execution eligibility remains orthogonal to lifecycle state` and `Active-workflow cardinality and Issue-state coherence precede queue selection`.

## Decision 3 — Reconstruct authoritative cardinality before derived flow decisions, with one bounded premature-close recovery

Dispatch must first establish `0 / 1 / >1` formal/terminal-pending workflow cardinality from repository durable state. Queue selection, blocker projection, aging/priority presentation, and Project fields are evaluated only after that result. A failed/partial enumeration is not equivalent to zero.

Normal nonterminal workflow routing requires an open Issue. Closed nonterminal state is fail-closed contradiction; the existing closed `Lead / finalize-archive` terminal-pending exception remains unchanged.

The demonstrated #40 premature-close class gets one narrow recovery rule rather than a general fault state machine. A closed Issue is a **premature-close recovery candidate** only when all of the following are reconstructable from durable repository evidence:

1. it has a persisted non-`unset` Change identity and exactly one otherwise legal nonterminal routing tuple;
2. the formal lifecycle is demonstrably unfinished (for example an active OpenSpec Change or other matching nonterminal lifecycle evidence still exists);
3. there is no authorized final Archive merge/native-close completion and no durable `LIFECYCLE_COMPLETE` for that Change;
4. the closure is not backed by a qualifying provenance-bound Human decision explicitly requiring termination/non-resumption; a bare Issue close event or actor identity alone is not such authority;
5. repository-wide reconstruction finds no other normal formal/terminal-pending workflow and no second contradictory recovery candidate, so reopening cannot create multiple-active ambiguity.

When exactly one candidate satisfies those predicates, normal lifecycle execution remains stopped and pre-activation intake remains blocked. Governance deterministically assigns the bounded recovery to `Lead / resolve-question`; the stale nonterminal routing on the closed Issue is evidence to preserve, not an action to execute while closed. Lead may reopen that same coordination Issue without changing its immutable Change identity or its pre-close nonterminal routing tuple. Lead then immediately fresh-reads Issue state, routing, OpenSpec/PR evidence, and repository-wide active cardinality. Recovery succeeds only if the reopened Issue now reconstructs as the single coherent formal active workflow and its preserved routing is still legal. No normal lifecycle mutation is executed in that recovery invocation; a later wake dispatches from the freshly reconstructed preserved tuple.

If any predicate is missing, contradictory, Human-reserved, or would produce more than one formal/recovery candidate, Lead does not reopen by inference. The state remains fail closed under existing diagnosis/Human-escalation semantics. This rule is intentionally limited to premature external closure of an otherwise coherent formal workflow; it does not create a generic recovery registry, new routing state, cancellation lifecycle, or authority to undo a qualifying Human decision.

Trace: requirement `Active-workflow cardinality and Issue-state coherence precede queue selection`; #40 premature-close and #63/#65 partial-reconstruction incidents; Reviewer finding `issuecomment-5317087714`.

## Decision 4 — Required deferred follow-up materializes directly as queued Explore

A decision that explicitly says bounded work is *required to be handled separately* already provides independent repository authority. At that same Lead-owned decision boundary, create/reuse the tracker with exact source/defer linkage and route it immediately as `Change: unset + Lead / explore-change`.

Explore later revalidates current evidence before formal activation. This keeps admission conservative without creating the non-runnable tracker state observed for #49/#63. Optional/non-goal/speculative work still creates no admitted workflow.

Trace: requirement `Required separate follow-up is directly queueable for fresh Explore revalidation`.

## Decision 5 — Direct Propose may fall back to Explore only before activation

When Human admitted a concrete problem directly to Propose but Lead discovers current evidence is not proposal-ready, the safer action is an explicit same-Issue `propose-change → explore-change` transition while `Change: unset`. This preserves durable history and does not ask Human to know the technical entry action.

Explore can return only through `PROPOSAL_READY`; once the Change id is set, ambiguity belongs to `resolve-question`. No ordinary Propose/Explore loop is introduced.

Trace: requirement `Pre-activation Propose may conservatively fall back to Explore`.

## Decision 6 — Project/Kanban stays projection-only

Project status, blocker view, work-item age, and similar metrics may help Human flow visibility, but no Project field participates in dispatch or authority. This avoids another synchronization surface and keeps reconstruction possible from Issue/PR/OpenSpec/Actions state alone.

Trace: requirement `Flow visualization is derived and non-authoritative`.

## Rejected / deferred alternatives

- New states such as Waiting Human/CI/Environment: rejected as combinatorial lifecycle expansion.
- `blocked` label or universal blocker result: rejected because action-specific durable evidence already owns the reason and recovery path.
- Releasing WIP for blocked work: rejected because it defeats the single-active safety invariant.
- Global priority/expedite scoring: rejected without a demonstrated need that survives finish-first + FIFO.
- Human-only reopening for every premature close: rejected because a bare close event is not provenance-bound Human lifecycle authority; requiring Human for a mechanically provable nonterminal contradiction would add avoidable blockage. A qualifying Human decision still prevents automatic reopen.
- Generic automatic reopen of any closed routed Issue: rejected because it could override terminal or Human-authorized state and become a fault-recovery engine.
- Removing Lead `MERGE_AUTHORIZED`: deferred; archive finalization still owns material deferred-obligation and cleanup judgment, and changing merge authority is not required to solve the operational eligibility/WIP problem.
- External scheduler enable/disable remediation: outside repository execution authority; workflow-dynamic remains independent of legacy task names but cannot create a wake source when all external tasks are disabled.

## Blast radius

Expected implementation is governance/tests only:
- `agents/AGENTS.md` for shared eligibility/WIP/cardinality/coherence and bounded premature-close recovery semantics;
- `agents/roles/lead.md` and `agents/skills/openspec-change/SKILL.md` / `openspec-explore/SKILL.md` for recovery, required-defer materialization, and pre-activation fallback ownership;
- focused regression tests for cardinality-before-queue, closed/nonterminal fail-closed + deterministic reopen recovery, required-follow-up queueing, and Propose→Explore fallback;
- optional README/Project orientation only where non-normative navigation needs clarification.

No strategy/runtime investment behavior changes.