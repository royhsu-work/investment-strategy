# Change: Restore NO_WORK idle discovery reachability

## Why

Issue #322 identifies a real integration gap on the current default branch: the Action-only repository dispatcher can produce an exact run-scoped `NO_WORK` result, while the Scheduled Task/bootstrap boundary has no executable continuation into the already-governed bounded Lead idle-discovery capability. The result is that a retained semantic capability exists in canonical governance but is unreachable in production.

The current default branch at this Explore boundary is `2e00e236f24ba41302c9ba18c685acdf4cebe4ed`. Fresh reconstruction confirms that `select_work()` and its bridge remain intentionally Action-only, that the bridge emits an exact machine `NO_WORK` artifact, and that the application bridge owns repository mutations and postcondition qualification. No current executable consumer connects that artifact to bounded Lead idle semantics.

## What Changes

- Define one exact, run-scoped `NO_WORK` handoff from normal Action-only dispatch to bounded Lead idle semantic execution.
- Keep `AUTHORIZE`, `FAIL_CLOSED`, and all existing formal/pre-activation ordering authoritative; only true `NO_WORK` may reach idle semantics.
- Add a typed, evidence-bound idle request/result contract that is not an Action, normal routing state, queue, cursor, lease, heartbeat, registry, or recovery workflow.
- Reuse the existing bridge transport, fresh repository preflight, application-owned effect/reconciliation, canonical Issue tuple, and later normal dispatch; consolidate the new boundary into those owners.
- Add the smallest repository-owned admission actuator for one existing-candidate update or one new routing-complete Explore Issue, with fresh reauthorization, minimal overlap serialization, read-only ambiguous-write reconciliation, and fail-closed guards.
- Define and verify the external Scheduled Task/bootstrap activation boundary so a merged repository implementation is not mistaken for production reachability.

## Decisions and proportionality

### REUSE

Reuse the current Action-only dispatcher and disposition contract, the existing bounded Lead idle semantics from the canonical workflow, the current application-owned exact-effect/postcondition machinery, the existing canonical `Change: unset + action:explore-change` tuple, and the current fresh-revision/run-scoped evidence model.

### CONSOLIDATE

Place idle handoff validation, admission preconditions, and reconciliation in the existing repository-owned bridge/application boundary. Use one minimal ephemeral serialization boundary only for the final GitHub admission mutation. Keep semantic discovery with Lead and physical mutation with the application owner.

### NO-DELTA

Do not change the Action enum/topology, `select_work()`, normal Role derivation, formal WIP/finish-first ordering, Human authority, normal routing labels, daily control-shard semantics, or the existing Action successor lifecycle. Do not create an idle Action, an idle transition, an `agent:*` normal routing dimension, a second queue/state machine, a cursor, lease, heartbeat, hidden backlog, or registry.

### ADD

Add only the typed non-Action `NO_WORK` handoff and the repository-owned candidate admission/reconciliation primitive required to make the retained capability executable and safe under overlap, interruption, stale evidence, and ambiguous GitHub writes.

## Scope

In scope:

- the canonical scheduled-agent workflow contract and focused runtime/bridge/application implementation;
- an exact non-Action idle request/result envelope tied to a successful dispatch run and artifact;
- existing/new candidate admission, deduplication, postcondition verification, and safe reconciliation;
- tests for the required negative, concurrency, interruption, stale-state, and handoff properties;
- production-shaped bootstrap/cutover evidence and documentation of the external execution boundary.

Out of scope:

- adding any Action or idle lifecycle;
- moving semantic discovery into `select_work()`;
- changing Human approval/provenance rules;
- creating a second workflow graph, queue, lease, cursor, progress registry, or recovery workflow;
- changing financial strategy behavior;
- inventing a replacement for unavailable external Scheduled Task configuration.

## Staged delivery

1. Contract and dark executable substrate: typed `NO_WORK` envelope/result, pure qualification, and negative/positive contract tests without enabling writes.
2. Safe admission boundary: repository-owned fresh reauthorization, existing/new candidate atomic mutation, overlap serialization, postcondition/reconciliation tests, and application-shaped carrier.
3. Bootstrap activation and proof: connect the real Scheduled Task/bootstrap to the exact `NO_WORK` artifact, exercise bounded Lead idle semantics, verify no-finding/no-noise and one safe admission, and prove that the next normal wake authorizes ordinary `Lead / explore-change`.

Each stage remains independently testable, reviewable, mergeable, and deployable on the current N-1 substrate while preserving this parent outcome. A merged repository stage is not completion until the production wake path and the normal Action handoff are observed.

## Completion evidence

The parent Change is complete only when fresh evidence proves:

- exact `AUTHORIZE` and `FAIL_CLOSED` never invoke idle;
- exact normal `NO_WORK` invokes bounded Lead idle semantics;
- no-finding creates no repository noise;
- existing and new candidate admission each form exactly one legal canonical tuple;
- overlapping wakes admit at most one candidate;
- stale source/default branch, interruption, and ambiguous writes fail safe;
- successful admission is consumed by a later ordinary normal Action dispatch;
- repository implementation is merged and the active OpenSpec Change is archived;
- the actual production bootstrap boundary is activated and has production-shaped evidence.

## Human invariants preserved

This change does not reopen #322's approved architecture. Normal dispatch stays Action-only; `NO_WORK` remains an idle semantic boundary; normal work always wins; Lead retains semantic materiality judgment; the application owns consequential mutation; successful admission returns immediately to the existing canonical Action workflow; and no second workflow/control state is introduced.

## Skill maintenance

No Role or Skill semantic responsibility change is intended. `Lead / explore-change` and `Lead / propose-change` continue to use their existing procedures. Implementation must load the repository skill-maintenance procedure only if fresh evidence shows that a Skill itself changes.
