## ADDED Requirements

### Requirement: Approved required separate follow-ups are materialized as routing-complete Explore trackers

When an approved specification or lifecycle decision classifies work as a required separate follow-up, the owning Lead action SHALL materialize that obligation as one logical postcondition: exactly one deduplicated durable tracker with `Change: unset`, exact linkage to the source coordination Issue/Change and defer decision/reference, and canonical `agent:lead + action:explore-change` routing.

Creating or reusing the tracker without the required routing MUST be treated as incomplete materialization. When durable source evidence proves the approved obligation and exactly one matching incomplete tracker exists, the owning Lead action SHALL fresh-read and repair that tracker idempotently rather than create a duplicate. Multiple or ambiguous matching trackers MUST fail closed.

Lifecycle preparation that must prove required separate-follow-up obligations are durably tracked SHALL verify the same routing-complete postcondition and MUST NOT treat an unrouted required tracker as satisfied. The dispatcher MUST continue to consume canonical routing and MUST NOT infer missing routing from Issue prose.

Ordinary optional, non-goal, out-of-scope, or merely deferred work that lacks an approved required-separate-follow-up decision MUST NOT gain routing or tracker authority from this requirement.

#### Scenario: Required follow-up is created with canonical routing

- GIVEN an approved decision classifies work as a required separate follow-up
- AND no matching tracker exists
- WHEN the owning Lead action materializes the obligation
- THEN exactly one tracker records `Change: unset` and exact source/defer linkage
- AND the tracker has `agent:lead + action:explore-change` routing

#### Scenario: Interrupted create-before-route is repaired idempotently

- GIVEN an approved required separate-follow-up obligation exists
- AND exactly one matching tracker has the required identity/linkage but lacks canonical routing
- WHEN the owning Lead action reconstructs materialization
- THEN it repairs that same tracker to `agent:lead + action:explore-change`
- AND it does not create a duplicate tracker

#### Scenario: Ambiguous matching trackers fail closed

- GIVEN an approved required separate-follow-up obligation exists
- AND multiple trackers ambiguously match the same obligation
- WHEN materialization is reconstructed
- THEN the owning Lead action does not guess which tracker to repair
- AND it does not create another tracker

#### Scenario: Lifecycle preparation rejects an unrouted required tracker

- GIVEN lifecycle preparation must prove an approved required separate follow-up is durably materialized
- AND the matching tracker lacks required canonical routing
- WHEN Lead evaluates lifecycle readiness
- THEN the obligation is not considered satisfied
- AND Lead repairs the unique matching incomplete tracker when the approved source evidence and current authority make that repair unambiguous

#### Scenario: Dispatcher does not infer routing from tracker prose

- GIVEN an Issue body describes itself as a required separate follow-up
- AND canonical `agent:lead + action:explore-change` routing is absent
- WHEN workflow dispatch evaluates eligibility
- THEN the Issue prose does not substitute for routing
- AND the Issue is not selected merely from that prose

#### Scenario: Optional future work does not become routed follow-up

- GIVEN repository text identifies work only as optional, non-goal, out of scope, or merely deferred
- AND no approved decision classifies it as a required separate follow-up
- WHEN Lead evaluates follow-up materialization
- THEN no required tracker or routing authority is created from this requirement