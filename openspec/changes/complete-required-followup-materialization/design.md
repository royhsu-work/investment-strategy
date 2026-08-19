# Design: Complete required follow-up materialization

## Context

The current workflow already distinguishes required separate follow-up from ordinary out-of-scope work and already intends required follow-ups to route directly to `Lead / explore-change`. #98 shows the producer can still stop after Issue creation and leave an inert tracker. The design must close that gap without making dispatcher prose-aware or adding workflow state.

## D1. Treat materialization as one logical producer postcondition

The approved defer-decision owner remains responsible for a complete durable result:

```text
approved required defer decision
  -> deduplicate/reconstruct tracker candidates
  -> create or reuse exactly one tracker
  -> persist source linkage + Change: unset
  -> persist agent:lead + action:explore-change
  -> fresh-read complete postcondition
  -> only then declare obligation materialized
```

This is a logical transaction implemented with ordinary GitHub mutations and reconstruction, not a claim of API-level atomicity. The postcondition, not any individual mutation, defines success.

Minimum reconstructable source linkage identifies the source coordination Issue, source Change when present, and exact durable defer decision/reference that created the required obligation. The tracker body may carry this linkage because it is provenance/work evidence; routing labels remain the canonical execution identity.

## D2. Recover partial creation by convergence, not duplication

Before creating a tracker, and again after an interrupted run, Lead searches/reconstructs candidates from the exact source obligation. Outcomes are intentionally small:

- zero matching trackers -> create one and complete its postcondition;
- exactly one matching incomplete tracker -> repair that same tracker;
- exactly one complete tracker -> reuse/no-op;
- multiple/ambiguous/contradictory candidates -> fail closed to Lead diagnosis/resolution.

No lock, lease, retry counter, hidden registry, status label, or second queue is introduced. At-least-once safety comes from exact source linkage, deduplication, fresh reads, and idempotent convergence.

## D3. Make lifecycle verification consume the complete postcondition

Lead lifecycle preparation and terminal reconstruction must verify the same routing-complete materialization contract. `finalize-change` / Archive preparation may repair an unambiguous incomplete tracker when the source obligation and intended tracker are independently proven; otherwise readiness fails closed. `finalize-archive` cannot emit `LIFECYCLE_COMPLETE` while a still-applicable required obligation is represented only by inert/malformed/ambiguous tracker state.

Reviewer archive verification continues to inspect the Lead-prepared tracker state; it does not become the producer or repair owner.

## D4. Keep dispatcher and Human authority unchanged

No dispatcher change is needed. Existing canonical routing eligibility remains authoritative. The dispatcher never derives labels from natural-language claims.

Required-follow-up authority comes from the approved source decision, not the created Issue and not Human impersonation. Repairing #98-style historical malformed trackers therefore requires independent source evidence and unique linkage; it does not require a new generic Human approval when the source obligation is already approved.

## D5. Skill/governance placement

Use the narrowest current owners:

- `agents/AGENTS.md`: shared materialization/reconstruction invariant only if cross-action wording is needed;
- Lead role: producer ownership and lifecycle fail-safe responsibility;
- `openspec-change` / `lifecycle-finalize` Skills: executable create/reuse/repair/check procedures at their existing action boundaries;
- canonical `scheduled-agent-workflow` spec: externally verifiable normative behavior;
- tests: deterministic fixtures for partial creation, deduplication, malformed tracker blocking, and no prose inference.

Do not create a new reusable Skill merely for this one workflow-specific operation; existing mapped Skills already own the relevant action procedures. The adopted `skill-creator` guidance supports keeping this behavior in the narrowest existing action Skills rather than extracting hypothetical reuse.

## Trade-offs

A true multi-resource atomic GitHub transaction is unavailable and unnecessary. Defining a verified logical postcondition plus idempotent repair means a transient partial state can exist after interruption, but the source workflow may not call it complete and later reconstruction converges safely. This preserves the repository's existing at-least-once model with less complexity than hidden transaction state.

## Traceability

- Requirement `Required separate follow-up materialization is routing-complete` -> D1/D2/D3/D4 -> Tasks Slice 1/2/3.
- Repository simplicity/proportionality rules -> D5 and rejection of new queue/registry/lock/Skill abstractions.
