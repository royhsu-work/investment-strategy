## Decision-boundary traceability (non-normative)

This section records the Human decision boundary and source evidence carried by #227. It is context and traceability only; it is not an additional OpenSpec requirement and does not create a second normative owner.

Source evidence:
- #221 rejection and root-cause record: https://github.com/royhsu-work/investment-strategy/issues/221#issuecomment-5575078000
- #221 latest Human-approved minimal repair direction: https://github.com/royhsu-work/investment-strategy/issues/221#issuecomment-5578787305
- #221 deterministic implementation decision record: https://github.com/royhsu-work/investment-strategy/issues/221#issuecomment-5585904208
- #227 current Explore evidence: https://github.com/royhsu-work/investment-strategy/issues/227#issuecomment-5581185977
- The prior #227 review evidence at issuecomment-5582134734 is historical and was invalidated by later material changes.

Those records describe a fail-open execution boundary: formal durable state had a repository-owned Actions/application path and an LLM or direct-connector path, and the latter could still be treated as formal progress when the repository-owned path was unavailable or unverifiable. The defect is therefore the execution and provenance boundary, not checkpoint syntax, checkbox formatting, or notification behavior.

The approved boundary carried by this Change keeps formal correctness with repository-owned Actions/application authorization and observed durable postconditions. The connector remains bounded untrusted EFFECT_REQUEST transport, and the existing CarrierPlan, CarrierRequired, and application/carrier separation are retained. #221 remains historical and is not reopened, rewritten, or treated as Human accepted by this Change; #218 remains blocked. The verified-slice/checkpoint/recovery outcome remains owned by the canonical scheduled-agent-workflow surface; this context points to that owner without restating its normative semantics here.

Excluded from this correction are new Action or Result types, a checkpoint/progress registry, cursor, lease, heartbeat, retry state, mailbox, second DAG, new carrier type or result protocol, generic provenance/recovery framework, dedicated GitHub App or token infrastructure, a GITHUB_TOKEN-only carrier replacement, ruleset redesign, and #218/#207/#180 scope.

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
