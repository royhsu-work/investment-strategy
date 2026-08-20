# Change: Enforce invocation exit proof

## Explore result

This Change formalizes the decision-complete Explore result from coordination Issue #112, exact durable result `issuecomment-5360318078`.

The formalization preserves that result: continuation is the default after a Scheduled invocation selects a legal workflow/action, and return is legal only when current evidence positively proves one bounded Invocation Exit class. The Change does not redefine workflow terminal semantics settled by #115, mechanical repository-mutation recovery owned by #111, or future workflow-topology ownership explored by #80.

## Why

Current default-branch governance already requires selected actions to be work-conserving and explicitly rejects several voluntary yield points. Durable #107 evidence nevertheless demonstrated that an intended RED could be correctly established, the exact next GREEN step could already be known, and the invocation could still return. Similar premature returns occurred after first observations of exact CI as absent or nonterminal. A later tool/capability failure was different because continued execution was genuinely unavailable after legal local recovery was not available.

The remaining gap is therefore the return decision itself: negative non-yield guidance still leaves the final invocation exit dependent on model judgment. A positive Exit Proof contract makes continuation the default and requires a reconstructable reason before returning.

## What changes

- Add one shared continuation-by-default, termination-by-proof invariant for Scheduled invocations.
- Require a positive Exit Proof before a selected invocation may return.
- Limit legal Exit classes to completed cross-role handoff, true terminal result, genuine Human-reserved authority boundary, genuine unconsumable external asynchronous wait, stale/precondition loss, materially contradictory state requiring fail-closed disposition, or a hard execution boundary after applicable same-authority recovery is unavailable.
- Explicitly state that RED/GREEN/REFACTOR milestones, failed-but-actionable validation, commit/push completion, first absent/queued/in-progress CI observation, verified Slice checkpoints with remaining work, and immediately actionable same-role successors are not Exit Proof by themselves.
- Keep Exit Proof internal to execution; reuse existing durable action results, handoffs, exceptions, awaited-resource evidence, and lifecycle journals instead of creating new workflow state.
- Add executable regressions for representative Executor, Lead same-role, Reviewer cross-role, async-wait, stale-state, hard-boundary, and no-proof cases.

## Scope

Affected capability: `scheduled-agent-workflow`.

In scope: shared invocation continuation/exit governance, narrow action-local procedure consumption where current wording can still treat intermediate states as exits, canonical acceptance scenarios, and focused executable regressions.

Out of scope: workflow topology or terminal semantics (#115/#80), the mechanical mutation-recovery algorithm (#111), scheduler cadence/topology, new lifecycle actions/statuses, timers/counters/heartbeats/leases, or product/investment behavior.

## Compatibility and safety

The Change preserves fixed invocation role, one selected workflow, role authority separation, exact-revision gates, Human authority boundaries, at-least-once reconstruction, stale/concurrency fail-closed behavior, WIP=1, and the #115 terminal invariant. It introduces no new Human-reserved decision, durable waiter state, progress state, central dispatcher engine, or second workflow DAG.
