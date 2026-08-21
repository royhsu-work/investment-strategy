## ADDED Requirements

### Requirement: Required separate follow-up work is materialized as one routing-complete postcondition

When an approved specification, scope, or lifecycle decision explicitly classifies work as a required separate/deferred follow-up, the owning Lead action MUST materialize that obligation as one logical postcondition consisting of exactly one deduplicated durable tracker with `Change: unset`, exact source coordination/change and defer-decision/reference linkage, and canonical `agent:lead + action:explore-change` routing.

Creating or reusing the tracker without completing the required routing MUST NOT satisfy the obligation. Before creating a new tracker or repairing an incomplete one, the owning Lead action MUST fresh-read the relevant durable trackers and source obligation. If exactly one matching tracker exists and is incomplete only in materialization fields the Lead is already authorized to establish, Lead MUST repair that tracker idempotently rather than create a duplicate. If multiple or ambiguous matching candidates exist, or the source obligation cannot be reconstructed exactly, the action MUST fail closed rather than guess, duplicate, or infer authority from tracker prose.

Lifecycle preparation that is already responsible for reconstructing required separate-follow-up obligations MUST verify this same routing-complete postcondition. When a unique matching tracker is incomplete and the approved source obligation still supplies the required authority, the Lead lifecycle owner MAY repair that incomplete materialization before review handoff. Lifecycle preparation MUST NOT introduce a contradictory local rule that preserves an unrouted required tracker as complete.

Dispatcher admission remains unchanged: scheduled dispatch MUST consume canonical routing and MUST NOT infer missing `agent:*` or `action:*` routing from Issue body text, source linkage, or the existence of a required-follow-up obligation.

#### Scenario: Required follow-up is created and routed as one logical result

- GIVEN an approved decision explicitly requires a separate follow-up
- AND no matching tracker exists
- WHEN the owning Lead action materializes the obligation
- THEN exactly one tracker exists with `Change: unset`
- AND it records the exact source coordination/change and defer-decision/reference linkage
- AND it is routed to `agent:lead + action:explore-change`
- AND the producer does not report the obligation complete before those properties are durably observable

#### Scenario: Interrupted create-before-route is repaired idempotently

- GIVEN an approved required separate-follow-up obligation remains applicable
- AND exactly one matching tracker already exists with exact source linkage and `Change: unset`
- AND the tracker is missing its required canonical Explore routing because an earlier materialization was interrupted
- WHEN the owning Lead action reconstructs the obligation
- THEN it repairs that same tracker to `agent:lead + action:explore-change`
- AND it does not create a second tracker
- AND completion is recognized only after the repaired durable state is re-observed

#### Scenario: Ambiguous matching trackers fail closed

- GIVEN an approved required separate-follow-up obligation remains applicable
- AND more than one tracker plausibly matches the same required obligation
- WHEN Lead attempts materialization or repair
- THEN Lead does not choose a tracker by model judgment
- AND Lead does not create another tracker
- AND the obligation remains incomplete pending legal resolution of the ambiguity

#### Scenario: Tracker prose does not create routing authority

- GIVEN an Issue body describes itself as a required follow-up
- AND canonical `agent:*` / `action:*` routing is absent
- WHEN scheduled dispatch reconstructs eligibility
- THEN the dispatcher does not infer `Lead / explore-change` from the prose
- AND the Issue is not admitted solely because its text resembles a required follow-up

#### Scenario: Optional or ordinary deferred work creates no required tracker

- GIVEN approved artifacts describe work only as optional, non-goal, ordinary out-of-scope, or uncommitted future work
- WHEN Lead evaluates separate-follow-up materialization
- THEN no required tracker/routing obligation is created from that text alone

#### Scenario: Lifecycle preparation repairs one uniquely incomplete required tracker

- GIVEN lifecycle preparation reconstructs an applicable approved required separate-follow-up obligation
- AND exactly one matching tracker exists with exact source linkage and `Change: unset`
- AND the tracker lacks canonical `Lead / explore-change` routing
- WHEN Lead prepares the lifecycle boundary for independent review
- THEN Lead treats the obligation as incomplete
- AND repairs the same tracker to the required routing when current authoritative source evidence still permits that repair
- AND does not hand off lifecycle review while the required postcondition remains incomplete
