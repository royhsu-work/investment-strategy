# Design

## Context

Current shared governance and Lead authority already require a required separate/deferred follow-up to be represented by one source-linked `Change: unset` tracker routed to `Lead / explore-change`. The observed defect is procedural atomicity/reconstruction: tracker creation and routing are separate GitHub mutations, so interruption can leave an inert tracker. In addition, `lifecycle-finalize` contains local guidance that contradicts the shared/Lead owner by prohibiting the required routing.

The design must preserve SSOT: dispatcher admission remains in shared governance; Lead authority remains in the Lead role; mapped Skills operationalize the postcondition without redefining either.

## Decisions

### 1. Model completion as a logical postcondition, not a transactional API primitive

GitHub Issue creation and label mutation need not become physically atomic. The producer succeeds only after fresh observation proves the complete durable postcondition:

`unique tracker + Change: unset + exact source/defer linkage + agent:lead + action:explore-change`.

This preserves at-least-once reconstruction and avoids locks, claims, leases, or hidden transaction state.

Trace: added requirement scenarios for normal materialization and interrupted create-before-route repair.

### 2. Repair only one uniquely matching incomplete tracker

Before create or repair, the producer reconstructs the approved source obligation and matching trackers. Zero matches permits creation; exactly one incomplete match permits repair; multiple/ambiguous matches fail closed. Tracker prose cannot supply missing authority.

Trace: idempotent repair, ambiguity, and no-prose-inference scenarios.

### 3. Lifecycle preparation consumes the same postcondition

`lifecycle-finalize` remains a fail-safe reconstruction boundary. It does not own a second tracker/routing model. When it encounters one uniquely matching incomplete required tracker and the authoritative approved source obligation remains reconstructable, it repairs that same postcondition; otherwise it blocks review handoff.

Trace: lifecycle-preparation scenario.

### 4. Do not change dispatcher admission

No dispatcher fallback is added for prose-described trackers. A tracker without canonical routing remains non-actionable until the legal Lead producer/lifecycle boundary repairs it.

Trace: no-prose-inference scenario.

### 5. Skill ownership follows existing responsibility

`openspec-change` operationalizes required-follow-up materialization at specification/scope decision boundaries. `lifecycle-finalize` operationalizes fail-safe reconstruction/repair before lifecycle handoff. Neither Skill restates shared queue/admission semantics or expands Lead authority.

## Failure handling

- Missing/contradictory source obligation: fail closed; do not create/repair.
- Multiple matching trackers: fail closed; do not choose or duplicate.
- Mutation error with uncertain durable result: fresh-read before retry and follow current shared execution-exception/recovery governance.
- Optional/non-goal/ordinary deferred text: no materialization obligation.

## Non-goals

No workflow topology change, dispatcher inference, Human-authority change, new status, lock/lease, generic retry engine, or #98 semantic-adapter conversion.
