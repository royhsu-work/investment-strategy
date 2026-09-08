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

### Requirement: Corrective carrier repair preserves the approved decision boundary

This requirement records the approved correction carried by #227 within the existing Human decision boundary. Its exact evidence is the #221 rejection/root-cause record [issuecomment-5575078000](https://github.com/royhsu-work/investment-strategy/issues/221#issuecomment-5575078000), the latest Human-approved minimal repair direction [issuecomment-5578787305](https://github.com/royhsu-work/investment-strategy/issues/221#issuecomment-5578787305), and the deterministic implementation decision record [issuecomment-5585904208](https://github.com/royhsu-work/investment-strategy/issues/221#issuecomment-5585904208).

The rejection/root-cause evidence establishes that formal durable workflow state had two write paths: GitHub Actions/application for the earlier slices and an LLM/direct connector carrier for later `SLICE_CHECKPOINT`, `ACTION_RESULT`, and lifecycle evidence. When Actions was unavailable, failed, or unverifiable, the second path still allowed formal progress. The root cause was therefore a fail-open execution boundary, not checkpoint format, checkbox syntax, or notification behavior. Formal correctness SHALL remain gated by an exact successful repository-owned Actions/application run, fresh application authorization, and an observed durable postcondition.

The correction SHALL preserve the parent recovery outcome as an existing contract:

```text
verified slice
→ durable checkpoint
→ interruption
→ reconstruct current truth
→ previously verified slices are not replayed
→ resume first incomplete slice
```

A verified slice SHALL reach its durable checkpoint before continuation. After interruption, a later fresh repository-owned wake SHALL reconstruct current repository truth, skip previously verified slices, and select only the first incomplete slice. This is a bounded recovery/audit boundary and SHALL NOT become a hidden cursor, progress database, or second workflow state machine.

The existing `CarrierRequired is a hard invocation-exit boundary` requirement owns the carrier mechanics. Under this correction, `CarrierRequired` SHALL remain a hard invocation-exit: the application may expose only the exact immutable `CarrierPlan`; after that boundary the same invocation MUST NOT write a checkpoint, `ACTION_RESULT`, formal `action:*` routing, terminal/close state, or successor. Formal continuation SHALL occur only on a later fresh repository-owned wake. A merge carrier SHALL be handled by historical exact-head read-only reconciliation followed by fresh current-main authorization; stale authorization MUST NOT be replayed.

Application/carrier separation SHALL remain explicit. The application owns formal authorization, workflow meaning, and observed postconditions; the carrier executes only the exact authorized plan and does not choose routing, retry, terminal, successor, or success. Connector or out-of-band mutation is not a second formal write path.

This repository-governance requirement owns the shared carrier boundary. Active formal routing and terminal/close provenance remains owned by the `scheduled-agent-workflow` delta, without a competing normative copy in AGENTS, the workflow projection, a Role, or a Skill.

This correction SHALL reuse the existing Action, Result, `EFFECT_REQUEST`, application authorization, `CarrierPlan`, and postcondition surfaces. It SHALL NOT introduce a new carrier type or carrier-result protocol, registry, cursor, lease, heartbeat, retry state, mailbox, second DAG, generic recovery/provenance framework, dedicated GitHub App/token architecture, or GITHUB_TOKEN-only carrier replacement.

#### Scenario: CarrierRequired cannot open a second formal write path

- GIVEN the application has freshly authorized an exact `CarrierPlan` for a required carrier effect
- WHEN the application reaches `CarrierRequired`
- THEN the current invocation exposes only that exact plan and a carrier-required boundary outcome
- AND the current invocation writes no checkpoint, `ACTION_RESULT`, formal routing, terminal/close state, or successor
- AND a later fresh repository-owned wake must reconstruct current truth before applying any still-missing formal effect
- AND a connector-authored continuation is not accepted as workflow authority

#### Scenario: The approved recovery boundary survives interruption

- GIVEN one verified slice has a durable checkpoint and a later slice has not been verified
- WHEN interruption occurs before the later slice completes
- THEN a later fresh repository-owned wake reconstructs the current implementation truth
- AND it does not replay the verified slice
- AND it resumes at the first incomplete slice without adding a cursor, lease, mailbox, or second graph
