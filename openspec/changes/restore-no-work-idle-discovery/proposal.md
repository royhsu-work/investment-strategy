# Change: Restore NO_WORK idle discovery reachability

## Why

Issue #322 identifies a real integration gap on the current default branch: the Action-only repository dispatcher can produce an exact run-scoped `NO_WORK` result, while the Scheduled Task/bootstrap boundary has no executable continuation into the already-governed bounded Lead idle-discovery capability. The result is that a retained semantic capability exists in canonical governance but is unreachable in production.

The original Explore reconstruction used default-branch revision `2e00e236f24ba41302c9ba18c685acdf4cebe4ed`; the current continuation baseline is freshly observed as `main@e617a05ada51af9ff8f20697bbf07c4bfc8ec19e`. Fresh reconstruction confirms that normal dispatch and its bridge remain intentionally Action-only, that the bridge emits an exact machine `NO_WORK` artifact, and that repository application owns mutations and postcondition qualification. No current executable consumer connects that artifact to bounded Lead idle semantics.

## What Changes

- Define one exact, run-scoped `NO_WORK` handoff from normal Action-only dispatch to bounded Lead idle semantic execution.
- Keep `AUTHORIZE`, `FAIL_CLOSED`, and all existing formal/pre-activation ordering authoritative; only true `NO_WORK` may reach idle semantics.
- Add a typed, evidence-bound idle request/result contract that is not an Action, normal routing state, queue, cursor, lease, heartbeat, registry, or recovery workflow.
- Reuse the existing bridge transport, fresh repository preflight, application-owned effect/reconciliation, canonical Issue tuple, and later normal dispatch; consolidate the new boundary into those owners.
- Add the smallest repository-owned admission actuator for one existing-candidate update or one new routing-complete Explore Issue, with fresh reauthorization, minimal overlap serialization, read-only ambiguous-write reconciliation, and fail-closed guards.
- Repair shared application materialization and consequence recovery so safe ancestor/disjoint continuation, interruption between branch and PR creation, and fresh-process completion reconcile from exact accepted intent and durable repository evidence without replaying completed semantic work or weakening safety guards. Also preserve recovery of one exact accepted application when an uncorrelated legacy result invalidates formal-frontier qualification while the accepted source route remains unchanged.
- Define and verify the external Scheduled Task/bootstrap activation boundary so a merged repository implementation is not mistaken for production reachability.

## Decisions and proportionality

### REUSE

Reuse the current Action-only dispatcher and disposition contract, the existing bounded Lead idle semantics from the canonical workflow, the current application-owned exact-effect/postcondition machinery, the existing canonical `Change: unset + action:explore-change` tuple, and the current fresh-revision/run-scoped evidence model.

### CONSOLIDATE

Place idle handoff validation, admission preconditions, and reconciliation in the existing repository-owned bridge/application boundary. Use one minimal ephemeral serialization boundary only for the final GitHub admission mutation. Keep semantic discovery with Lead and physical mutation with the application owner.

### NO-DELTA

Do not change normal Action-only dispatch, Role derivation, formal WIP/finish-first ordering, Human authority, normal routing labels, daily transport semantics, or the existing Action successor lifecycle. Do not create an idle Action, an idle transition, an `agent:*` normal routing dimension, a second queue/state machine, a cursor, lease, heartbeat, hidden backlog, or registry.

### ADD

Add only the typed non-Action `NO_WORK` handoff and the repository-owned candidate admission/reconciliation primitive required to make the retained capability executable and safe under overlap, interruption, stale evidence, and ambiguous GitHub writes.

## Scope

In scope:

- the canonical scheduled-agent workflow contract and focused runtime/bridge/application implementation;
- an exact non-Action idle request/result envelope tied to a successful dispatch run and artifact;
- existing/new candidate admission, deduplication, postcondition verification, and safe reconciliation;
- tests for the required negative, concurrency, interruption, stale-state, and handoff properties;
- accepted-application recovery after an uncorrelated legacy result, including exact source/Change/run binding and fail-closed handling of duplicate intents, duplicate runs, or changed routing;
- production-shaped bootstrap/cutover evidence and documentation of the external execution boundary.

Out of scope:

- adding any Action or idle lifecycle;
- moving semantic discovery into normal dispatch;
- changing Human approval/provenance rules;
- creating a second workflow graph, queue, lease, cursor, progress registry, or recovery workflow;
- changing financial strategy behavior;
- inventing a replacement for unavailable external Scheduled Task configuration.

## Staged delivery

The shared application recovery is a prerequisite for the idle path. No idle admission or production handoff stage may begin on an N-1 revision that still rejects a valid materialization continuation or cannot reconstruct its durable consequence after process restart.

0. **Shared application materialization and consequence recovery** — N-1 is the freshly read default branch with the existing application behavior. Reproduce the apply/observer contradiction, the branch-ref-without-PR interruption after a disjoint main advance, and fresh-process loss of consequence recognition from current source. Exit only after the shared owners accept the same exact safe materialization, emit only a missing PR consequence when ancestry/path/cardinality/content checks pass, reconstruct already durable consequences after restart, and resume only one exact accepted application across the uncorrelated-result frontier case. Run applicable durable-prefix, stale/overlap/identity/cardinality/ambiguity negatives, focused and full regression, type/lint/format checks, strict OpenSpec validation, and independent implementation review; merge the exact reviewed revision. This repairs shared behavior without enabling idle admission. The parent idle outcome remains mandatory.
1. **Contract and dark executable substrate** — N-1 is Stage 0 on the default branch. Add the typed run-bound `NO_WORK` handoff and positive/negative qualification while writes and the external idle wake remain disabled. Exit when exact completed `NO_WORK` reaches one bounded Lead semantic request, `AUTHORIZE` and `FAIL_CLOSED` do not, and the Action-only selector and all normal routing remain unchanged under focused and full validation. Candidate admission and production reachability remain mandatory.
2. **Safe admission boundary** — N-1 is Stage 1 on the default branch. Add one existing-candidate update or new routing-complete Issue create, immediate fresh reauthorization, minimal overlap serialization, exact postcondition, and read-only ambiguous-write reconciliation. Exit when no-finding is mutation-free; unrelated state is preserved; existing/new candidates form one canonical tuple; overlap, stale evidence, interruption, and ambiguous outcomes remain safe; and full applicable gates pass. Scheduled Task/bootstrap production proof remains mandatory.
3. **Scheduled Task/bootstrap activation and parent proof** — N-1 is Stages 0–2 merged on the default branch. Connect the real Scheduled Task/bootstrap to the exact dispatch artifact and typed boundary; exercise bounded Lead semantics and safe admission; then prove a later ordinary wake authorizes `Lead / explore-change`. Exit only with production-shaped wake, run, and artifact evidence for `AUTHORIZE`/`FAIL_CLOSED` suppression, true `NO_WORK` idle execution, no-finding silence, safe existing/new admission, overlap and interruption recovery, and the later normal Action handoff. Verify the active OpenSpec Change is complete and archive it only through its governed lifecycle. If external scheduler configuration cannot be changed through available authorized capability, the production activation criterion remains unmet and the exact external boundary stays a blocker.

Every stage must have a fresh exact-head review, required validation, and an exact-head merge before the next stage uses it as N-1. Stages are independently testable and deployable while preserving the full parent outcome; their exit criteria do not replace the parent completion evidence below. A merged stage, including Stage 0, is not completion until Stage 3 proves the production wake path and normal Action handoff.

## Completion evidence

The parent Change is complete only when fresh evidence proves:

- exact `AUTHORIZE` and `FAIL_CLOSED` never invoke idle;
- exact normal `NO_WORK` invokes bounded Lead idle semantics;
- no-finding creates no repository noise;
- existing and new candidate admission each form exactly one legal canonical tuple;
- overlapping wakes admit at most one candidate;
- stale source/default branch, interruption, and ambiguous writes fail safe;
- first-carrier recovery after a branch-ref/PR-carrier interruption creates only the missing exact PR consequence against current main when the old base is an ancestor and changes are disjoint;
- fresh-process consequence completion uses durable GitHub evidence and the canonical positive observer without replaying semantic work or requiring local target memory;
- successful admission is consumed by a later ordinary normal Action dispatch;
- repository implementation is merged and the active OpenSpec Change is archived;
- the actual production bootstrap boundary is activated and has production-shaped evidence.

## Human invariants preserved

This change does not reopen #322's approved architecture. Normal dispatch stays Action-only; `NO_WORK` remains an idle semantic boundary; normal work always wins; Lead retains semantic materiality judgment; the application owns consequential mutation; successful admission returns immediately to the existing canonical Action workflow; and no second workflow/control state is introduced.

## Skill maintenance

No Role or Skill semantic responsibility change is intended. `Lead / explore-change` and `Lead / propose-change` continue to use their existing procedures. Implementation must load the repository skill-maintenance procedure only if fresh evidence shows that a Skill itself changes.
