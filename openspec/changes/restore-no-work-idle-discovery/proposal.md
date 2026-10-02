# Change: Restore NO_WORK idle discovery reachability

## Why

Issue #322 identifies a real integration gap on the current default branch: the Action-only repository dispatcher can produce an exact run-scoped `NO_WORK` result, while the Scheduled Task/bootstrap boundary has no executable continuation into the already-governed bounded Lead idle-discovery capability. The result is that a retained semantic capability exists in canonical governance but is unreachable in production.

The original Explore reconstruction used default-branch revision `2e00e236f24ba41302c9ba18c685acdf4cebe4ed`; the current continuation baseline is freshly observed as `main@5fa6fdf7d9b33e3f2718c9525bb685f74393d3f3`. Fresh reconstruction confirms that normal dispatch and its bridge remain intentionally Action-only, that the bridge emits an exact machine `NO_WORK` artifact, and that repository application owns mutations and postcondition qualification. The current default branch contains the prior shared recovery and typed idle substrate, including the #322 repairs through PR #355. Those repairs are retained as production characterization and reusable proof primitives; latest Human evidence proves they do not yet close the systemic application/materialization root cause because one materialized durable consequence still has multiple effective positive completion semantics. Bounded advisory admission, unchanged-Human-decision suppression, and post-terminal production acceptance also remain delivery work until governed implementation and production evidence prove them.

## What Changes

- Define one exact, run-scoped `NO_WORK` handoff from normal Action-only dispatch to bounded Lead idle semantic execution.
- Keep `AUTHORIZE`, `FAIL_CLOSED`, and all existing formal/pre-activation ordering authoritative; only true `NO_WORK` may reach idle semantics.
- Add a typed, evidence-bound idle request/result contract that is not an Action, normal routing state, queue, cursor, lease, heartbeat, registry, or recovery workflow.
- Reuse the existing bridge transport, fresh repository preflight, application-owned effect/reconciliation, canonical Issue tuple, and later normal dispatch; consolidate the new boundary into those owners.
- Add the smallest repository-owned admission actuator for one bounded advisory or one existing/new routing-complete Explore candidate, with fresh reauthorization, minimal overlap serialization, read-only ambiguous-write reconciliation, and fail-closed guards. Advisory admission is non-routing, uses exactly `advisory:idle`, is limited to three recommendations, and never carries `Change:` state.
- Suppress repeated semantic ingress only when the current qualified frontier is the same unanswered `HUMAN_DECISION_REQUIRED → Lead / resolve-question` consequence and no newer qualifying Human decision or materially changed evidence exists. This is a derived no-op view, not persisted routing/retry/wait state.
- Consolidate shared application/materialization completion around one canonical read-only durable-consequence proof. For accepted intent `I` and fresh repository state `S`, that owner returns only `COMPLETE(target, witness)`, `INCOMPLETE`, or `CONTRADICTORY(reason)` after proving Identity, Content, Lineage, and Non-conflict. Apply-side already-complete checks, materialization postcondition, interruption recovery, and consequence completion classification MUST consume that same proof; historical/replacement/merged/reconciled/direct Git shapes remain proof primitives or witnesses, not separate positive completion semantics. Preserve bounded accepted-application continuation and all existing fail-closed guards without semantic replay.
- Define and verify the external Scheduled Task/bootstrap activation boundary so a merged repository implementation is not mistaken for production reachability.

## Decisions and proportionality

### REUSE

Reuse the current Action-only dispatcher and disposition contract, the existing bounded Lead idle semantics from the canonical workflow, the current application-owned exact-effect/postcondition machinery, the existing canonical `Change: unset + action:explore-change` tuple, and the current fresh-revision/run-scoped evidence model.

### CONSOLIDATE

Place idle handoff validation, admission preconditions, and reconciliation in the existing repository-owned bridge/application boundary. Consolidate materialized-consequence completion into one canonical read-only proof owner in the existing application/materialization layer; every positive completion consumer delegates to it, while topology-specific helpers remain subordinate witness/identity/safety primitives. Use one minimal ephemeral serialization boundary only for the final GitHub admission mutation. Keep semantic discovery with Lead and physical mutation with the application owner.

### NO-DELTA

Do not change normal Action-only dispatch, Role derivation, formal WIP/finish-first ordering, Human authority, normal routing labels, daily transport semantics, or the existing Action successor lifecycle. Do not create an idle Action, an idle transition, an `agent:*` normal routing dimension, a second queue/state machine, a cursor, lease, heartbeat, hidden backlog, or registry.

### ADD

Add only the typed non-Action `NO_WORK` handoff and the repository-owned candidate admission/reconciliation primitive required to make the retained capability executable and safe under overlap, interruption, stale evidence, and ambiguous GitHub writes.

## Scope

In scope:

- the canonical scheduled-agent workflow contract and focused runtime/bridge/application implementation;
- an exact non-Action idle request/result envelope tied to a successful dispatch run and artifact;
- advisory/existing/new candidate admission, deduplication, postcondition verification, and safe reconciliation;
- tests for the required negative, concurrency, interruption, stale-state, and handoff properties;
- one canonical read-only durable-consequence proof for materialized application consequences, shared by apply-side precheck, materialization postcondition, interruption recovery, and consequence completion classification;
- historical topology characterization retained as witness/proof shapes rather than separate completion semantics;
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

0. **Historical materialization recovery characterization — delivered, not systemic completion** — Current `main@5fa6fdf7d9b33e3f2718c9525bb685f74393d3f3` includes the prior #322 recovery chain through PRs #331–#333, #347, #349, #354, and #355. Those repairs provide valuable characterization, lineage helpers, merged/replacement/reconciliation witness logic, and interruption-recovery primitives. They do **not** prove a single authoritative positive completion definition. PR #357 is additional production RED evidence for the same structural defect and MUST be absorbed by the canonical proof rather than retained as a permanent topology-specific top-level branch.

1. **Canonical durable-consequence proof consolidation — mandatory next prerequisite** — On the then-current N-1, first retain the historical production shapes and negative cases as characterization without changing behavior; then introduce one read-only proof owner in shadow, cut materialization observation/postcondition/fresh recovery/consequence classification over to it, cut apply-side already-complete logic over to the same owner, verify the four systemic properties (apply/observe consistency, interruption invariance, safe-evolution monotonicity, conflict preservation), and only then remove superseded topology-specific top-level completion branches. After every consequential mutation, local API success is discarded as authority and fresh GitHub truth is evaluated by the same proof. This stage is complete only when all positive consumers share that owner and the negative fail-closed cases remain protected.

2. **Contract and dark executable substrate — already delivered; re-verify after Stage 1** — The typed run-bound `NO_WORK` envelope and exact idle qualification already exist without changing `select_work()`, the Action enum, or normal routing. Their prior delivery does not bypass the canonical-proof prerequisite; final implementation review must verify they remain correct after Stage 1 cutover. The external idle wake remains an explicit activation boundary.
3. **Safe admission boundary — partially delivered on current main** — Existing/new Explore admission, fresh `NO_WORK` reauthorization, interruption reconciliation, and the typed idle substrate are already present. Bounded advisory admission and the derived unchanged-Human-decision wait remain implementation work and MUST be independently reviewed and merged before this stage is complete.
4. **Governed lifecycle, then production acceptance** — N-1 is the remaining repository implementation merged on the default branch. Complete independent implementation review, exact-head merge, finalize/archive review and merge, and legal terminal lifecycle first; while #322 remains routed formal work, normal dispatch cannot truthfully produce `NO_WORK`. After formal routing is gone, use a later real Scheduled Task wake to prove exact `NO_WORK` idle execution, no-finding silence or safe advisory/Explore admission, and—when a Formal Explore is admitted—a still later ordinary wake authorizing `Lead / explore-change`. No special dispatcher exception or validation-hold state is introduced. Human-defined completion requires both the legal lifecycle terminal state and this post-terminal production acceptance evidence.

The repository-visible cutover uses the existing `scheduled-agent-application.yml` carrier with one
typed `IDLE_ADMISSION_REQUEST` Issue-comment RPC on the current daily runtime shard. The comment is
only a trigger/staging transport, not a mailbox or accepted-intent record; no-finding remains silent.
The same boundary carries an exact `APPLICATION_CONTINUATION` body for an accepted application that
needs a fresh GitHub workflow run after an exhausted attempt. A real external Scheduled Task must
still be configured to read the exact successful bridge artifact, invoke bounded Lead idle semantics,
and post the exact typed body only when a candidate or continuation is present; that external setting
is not available through repository access.

Every stage must have a fresh exact-head review, required validation, and an exact-head merge before the next stage uses it as N-1. Stages are independently testable and deployable while preserving the full parent outcome; their exit criteria do not replace the parent completion evidence below. A merged stage, including Stage 0, is not completion until Stage 3 proves the production wake path and normal Action handoff.

## Completion evidence

The parent Change is complete only when fresh evidence proves:

- exact `AUTHORIZE` and `FAIL_CLOSED` never invoke idle;
- exact normal `NO_WORK` invokes bounded Lead idle semantics;
- no-finding creates no repository noise;
- one bounded advisory is non-routing, carries at most three recommendations, and is deduplicated across all Issue states without replacement after interruption;
- existing and new candidate admission each form exactly one legal canonical tuple;
- overlapping wakes admit at most one candidate;
- stale source/default branch, interruption, and ambiguous writes fail safe;
- first-carrier recovery after a branch-ref/PR-carrier interruption creates only the missing exact PR consequence against current main when the old base is an ancestor and changes are disjoint;
- one canonical read-only durable-consequence proof is the only positive completion authority for a materialized consequence; it proves Identity AND Content AND Lineage AND Non-conflict and returns only `COMPLETE`, `INCOMPLETE`, or fail-closed `CONTRADICTORY`;
- apply-side already-complete logic, materialization postcondition, fresh interruption recovery, and consequence completion classification all consume that same proof, so a consequence legally produced by apply is `COMPLETE` under a fresh observer and remains complete across safe disjoint evolution/merge/reconciliation unless fresh evidence proves contradiction;
- mutation preimages such as `expected_sha` remain stale-write authorization guards and are not required to remain present after the accepted desired blobs/manifest are durably proven;
- fresh-process consequence completion uses durable GitHub evidence and canonical proof primitives without replaying semantic work or requiring local target memory;
- successful admission is consumed by a later ordinary normal Action dispatch;
- repeated wakes do not emit a new semantic request/result while the same qualified `HUMAN_DECISION_REQUIRED → resolve-question` frontier remains unanswered and materially unchanged, while newer qualifying Human/material evidence resumes execution;
- repository implementation is merged and the active OpenSpec Change reaches its legal terminal lifecycle before true `NO_WORK` production acceptance is attempted;
- the actual production bootstrap boundary is activated and has post-terminal production-shaped evidence.

## Human invariants preserved

This change does not reopen #322's approved architecture. Normal dispatch stays Action-only; `NO_WORK` remains an idle semantic boundary; normal work always wins; Lead retains semantic materiality judgment; the application owns consequential mutation; successful admission returns immediately to the existing canonical Action workflow; and no second workflow/control state is introduced.

## Skill maintenance

No Role or Skill semantic responsibility change is intended. `Lead / explore-change` and `Lead / propose-change` continue to use their existing procedures. Implementation must load the repository skill-maintenance procedure only if fresh evidence shows that a Skill itself changes.
