## ADDED Requirements

### Requirement: Required separate follow-up materialization is routing-complete

When an approved Lead-owned specification or scope decision creates a required separate follow-up obligation, the workflow SHALL consider that obligation materialized only when exactly one reconstructable tracker exists with all of the following durable state:

- `Change: unset`;
- exact linkage to the source coordination Issue and source Change when one exists;
- exact linkage to the approved defer decision/reference that created the obligation; and
- canonical routing `agent:lead + action:explore-change`.

The Lead action that owns the approved defer decision SHALL create or reuse the tracker and complete this logical postcondition before treating the required follow-up as satisfied. Tracker existence without the required source linkage or canonical routing MUST be treated as incomplete materialization.

If creation is interrupted after a unique matching tracker exists but before all required materialization state is durable, recovery SHALL fresh-read source evidence and existing candidate trackers and SHALL repair that same unique matching tracker when the source obligation remains valid. Recovery MUST NOT create a duplicate merely because routing or source metadata is incomplete. Multiple or ambiguous candidate trackers, contradictory source evidence, or inability to prove the exact source obligation MUST fail closed.

Lifecycle preparation and terminal finalization SHALL reconstruct required separate follow-ups as routing-complete materialized trackers rather than checking tracker existence alone. A still-applicable required obligation backed only by an inert, malformed, ambiguously duplicated, or unrouted tracker MUST block the affected lifecycle readiness/completion boundary until the legal Lead owner repairs or resolves the contradiction.

Dispatcher semantics remain canonical-routing based. Scheduled dispatch MUST NOT infer missing `agent:*` or `action:*` routing from Issue title/body prose, and an Agent-created tracker MUST NOT self-authorize by copying required-follow-up wording.

An existing malformed tracker MAY be repaired without new Human admission only when independent durable source evidence proves the same approved required-separate-follow-up obligation and uniquely identifies that tracker as the intended materialization target.

#### Scenario: Required follow-up is created with complete workflow identity

- GIVEN an approved Lead-owned decision explicitly requires work in a separate follow-up
- AND the source decision/reference is reconstructable
- WHEN the owning Lead action materializes the follow-up
- THEN exactly one tracker is created or reused
- AND it records `Change: unset`
- AND it records the exact source Issue/Change and defer decision/reference
- AND it is routed `agent:lead + action:explore-change`
- AND only then may the source workflow treat the follow-up obligation as durably materialized

#### Scenario: Issue creation succeeds before routing and recovery resumes

- GIVEN a required follow-up Issue was durably created
- BUT the run ended before canonical routing became durable
- AND later reconstruction proves exactly one matching tracker and the same still-valid source obligation
- WHEN the legal Lead owner resumes materialization
- THEN it repairs the existing tracker to the complete postcondition
- AND it does not create a duplicate tracker

#### Scenario: Duplicate or ambiguous candidate trackers fail closed

- GIVEN a source required-follow-up obligation is valid
- AND reconstruction finds multiple plausible trackers or contradictory source linkage
- WHEN Lead evaluates materialization or repair
- THEN it does not guess which tracker is canonical
- AND it does not create another tracker
- AND the obligation remains incomplete until the ambiguity is resolved through the legal workflow

#### Scenario: Inert required tracker blocks lifecycle readiness

- GIVEN a still-applicable required separate follow-up obligation exists
- AND a linked tracker exists but lacks required canonical routing or exact source linkage
- WHEN Lead reconstructs Archive review readiness or terminal lifecycle completion
- THEN tracker existence alone is insufficient
- AND the lifecycle boundary fails closed until the required tracker is routing-complete or the source obligation is validly resolved

#### Scenario: Dispatcher does not infer routing from prose

- GIVEN an open Issue body claims to be a required separate follow-up
- AND the Issue lacks a coherent canonical routing tuple
- WHEN scheduled dispatch reconstructs eligible work
- THEN it does not infer `Lead / explore-change` from the prose
- AND producer/repair semantics remain responsible for persisting canonical routing

#### Scenario: Existing malformed tracker is repaired from independent source evidence

- GIVEN an existing tracker lacks required routing
- AND independent approved source evidence proves one exact required separate follow-up obligation
- AND that evidence uniquely identifies the tracker as the intended follow-up
- WHEN the legal Lead owner repairs the materialization
- THEN no new Human admission is required
- AND the tracker text itself is not treated as its own authority source
- AND the repaired tracker becomes eligible only after canonical routing is durably present

#### Scenario: Ordinary out-of-scope work does not create routed follow-up

- GIVEN a proposal or review identifies ordinary out-of-scope, optional, non-goal, or merely deferred work
- AND no approved decision classifies it as required separate follow-up
- WHEN Lead evaluates follow-up materialization
- THEN no required tracker/routing obligation is created
- AND the text cannot impersonate required-follow-up authority
