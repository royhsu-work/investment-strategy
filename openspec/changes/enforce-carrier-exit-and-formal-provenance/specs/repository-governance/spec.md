## ADDED Requirements

### Requirement: CarrierRequired is a hard invocation-exit boundary

The repository-owned application SHALL treat `CarrierRequired` as a hard
invocation-exit boundary. Before emitting a carrier plan, the application
MUST freshly authorize the exact source Issue, immutable Change, Action,
authorization revision, operation, target, expected values, and
postcondition. The application MAY output only that exact immutable
`CarrierPlan`.

When `CarrierRequired` is reached, the current invocation MUST end its
application/effect sequence at that boundary. The current invocation MUST NOT
write or cause a later write of `SLICE_CHECKPOINT`, `ACTION_RESULT`,
formal `action:*` routing, terminal/close state, or a successor. The carrier
MUST execute only the exact operation, target, and expected values in the
authorized plan. The carrier MUST NOT choose workflow meaning, routing,
retry, or success.

Formal continuation after the carrier SHALL occur only through a later fresh
repository-owned Actions/application wake that reconstructs current truth and
freshly authorizes any still-missing effects. This boundary SHALL reuse the
existing Action, Result, carrier, postcondition, stale, replay, and no-rewind
primitives and SHALL NOT introduce a carrier-result protocol, mailbox,
registry, continuation token, retry state, or second workflow graph.

#### Scenario: CarrierRequired ends the current invocation before formal effects

- GIVEN a repository-owned application has freshly authorized an exact
  `CarrierPlan` and an effect requires that carrier
- WHEN `CarrierRequired` is raised while applying the effect batch
- THEN the application exposes only the exact plan and a carrier-required
  boundary outcome
- AND the current invocation exits before any later checkpoint, action result,
  formal routing, terminal/close, or successor effect is applied
- AND the carrier can execute only the operation, target, expected values, and
  postcondition bound in that plan

#### Scenario: A later fresh wake reconciles an already-current non-merge effect

- GIVEN a carrier has executed an authorized non-merge plan and its exact
  postcondition is now present
- WHEN a later repository-owned Actions/application wake freshly reconstructs
  the same workflow boundary
- THEN the application may observe that postcondition as current
- AND it applies only still-missing effects authorized by the fresh observation
- AND it does not replay a verified slice or accept a carrier-authored formal
  result as workflow authority

#### Scenario: A merge carrier is reconciled from its historical exact head

- GIVEN an authorized merge plan was emitted and the carrier changed the
  default branch from the plan's authorization revision
- WHEN the old request is presented to a later application wake
- THEN the old authorization is treated as stale for new mutation
- AND the later wake read-only reconciles the historical exact-head merge
  postcondition
- AND it obtains fresh current-main authorization before any continuation or
  successor effect
- AND it does not replay the stale merge authorization
