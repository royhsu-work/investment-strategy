# Change: Align coordination Issue closure with workflow terminal

## Explore result

This Change formalizes the decision-complete Explore result from coordination Issue #115, exact durable result `issuecomment-5355262548`.

The formalization preserves that result: the normal final Archive PR stops closing the coordination Issue; Archive merge hands off to open `Lead / finalize-archive`; Lead persists `LIFECYCLE_COMPLETE`, closes the Issue, and re-observes `closed` before the workflow becomes terminal. Closed Issues with valid completion are terminal history. Premature close remains bounded recovery/fail-closed input rather than a normal happy-path state.

## Why

Current governance requires `Lead / finalize-archive` after Archive merge, but the final Archive PR currently carries `Closes #<issue>`. GitHub therefore closes the coordination Issue one lifecycle step before Lead terminal verification and `LIFECYCLE_COMPLETE`. This forces the normal dispatcher to support a closed terminal-pending exception and makes Issue closure ambiguous between unfinished and terminal history.

The established lifecycle principle is simpler: a PR merge must not close the coordination Issue before required post-merge continuation is complete. Applying that principle consistently to Archive merge removes the mismatch without weakening review, merge, reconstruction, or single-WIP safety.

## What changes

- The normal invariant becomes: open coordination Issue means formal workflow not yet terminal; closed coordination Issue means terminal history.
- Final Archive PRs use deterministic non-closing linkage such as `Refs #N` instead of `Closes #N`.
- Archive Reviewer PASS and Executor exact-head merge safety remain unchanged.
- After Archive merge, Executor hands off to `Lead / finalize-archive` while the Issue remains open.
- Lead reconstructs terminal evidence, persists `LIFECYCLE_COMPLETE`, closes the Issue, re-observes `closed`, and only then declares terminal completion.
- Interrupted final close is idempotently reconstructable; premature closure before valid terminal completion remains bounded recovery/fail-closed input.
- Normal closed terminal-pending dispatch is removed from the happy path and closed+valid-completion Issues are terminal history.

## Scope

Affected capability: `scheduled-agent-workflow`.

In scope: Archive PR linkage, formal terminal definition, finalize-archive close ownership/order, dispatcher/cardinality consequences, interruption/premature-close recovery, mapped lifecycle/merge procedures, and focused regressions.

Out of scope: changing Reviewer/Executor authority, removing finalize actions, invocation-exit semantics (#112), workflow-topology SSOT extraction (#80), scheduler cadence/topology, or product/investment behavior.

## Compatibility and safety

The Change preserves exact-revision Reviewer PASS, unchanged-head/current-check merge preconditions, Human-input freshness, required follow-up/cleanup preparation, at-least-once reconstruction, one persistent coordination Issue, and WIP=1. It introduces no new lifecycle action, hidden state, lock, lease, heartbeat, counter, second DAG, or Human-reserved decision.
