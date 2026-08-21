# Design: Complete required follow-up materialization

## Context

Shared governance and the Lead role already own the authority rule: an approved required separate follow-up is represented by a source-linked `Change: unset` tracker routed to `Lead / explore-change`. The remaining defect is procedural inconsistency: lifecycle preparation can currently preserve an unrouted tracker even though the dispatcher cannot execute it.

## Decision 1: One logical producer postcondition

Trace: `Approved required separate follow-ups are materialized as routing-complete Explore trackers`.

Treat tracker identity/linkage and routing as one logical materialization postcondition. This does not require transactional GitHub mutation or a lock. At-least-once execution remains safe because each reconstruction fresh-reads current durable state and completes only the missing portion of the same approved obligation.

## Decision 2: Repair the unique incomplete tracker

Trace: interrupted-create and ambiguity scenarios.

When source evidence proves the obligation and exactly one tracker matches its source/defer identity, Lead repairs missing routing on that tracker. If zero trackers exist, create one; if multiple candidates match ambiguously, fail closed. Never infer authority from tracker prose and never create a duplicate to avoid deciding ambiguity.

## Decision 3: Lifecycle preparation consumes the shared postcondition

Trace: lifecycle-preparation scenario and Skill maintenance traceability.

`lifecycle-finalize` remains a fail-safe reconstruction point. It must verify the same source-linked + routed postcondition and may complete an unambiguous missing-routing repair within existing Lead authority. Remove its contradictory local instruction that required trackers must remain unrouted. Do not add a second dispatcher/admission definition to the Skill.

## Decision 4: Keep dispatcher and Human authority unchanged

Trace: no-prose-inference and optional-work scenarios.

The dispatcher continues to select only canonical routing. Required-follow-up authority still comes from the approved source defer decision. Optional/non-goal/out-of-scope prose does not become routable. No new Human approval, waiting state, lock, lease, queue, or hidden workflow state is introduced.

## Regression strategy

Add executable tests that model materialization state as source obligation + matching trackers + routing. Cover fresh create, interrupted create-before-route, unique repair, duplicate ambiguity, optional work, no prose inference, and lifecycle readiness rejecting or repairing the #98-shaped malformed tracker.

## Trade-offs

GitHub Issue creation and label writes are not atomic at the API level. The design intentionally uses reconstructable logical atomicity rather than introducing distributed transaction machinery. A crash between create and route leaves an incomplete but repairable tracker; the next legal Lead reconstruction finishes the same postcondition.