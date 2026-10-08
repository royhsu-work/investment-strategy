# Change: Restore NO_WORK idle discovery reachability

## Why

Issue #322 originated from a real production integration gap: the Action-only repository dispatcher can produce an exact run-scoped `NO_WORK` result, while the Scheduled Task/bootstrap boundary has no executable continuation into the already-governed bounded Lead idle-discovery capability. The result is that a retained semantic capability exists in canonical governance but is unreachable in production.

The original Explore reconstruction used default-branch revision `2e00e236f24ba41302c9ba18c685acdf4cebe4ed`; the earlier continuation baseline was `main@5fa6fdf7d9b33e3f2718c9525bb685f74393d3f3`. Fresh current delivery authority is `main@1ca1d8e37e42bf1b689826ec34a0e335ba1f68b4`. Normal dispatch and its bridge remain intentionally Action-only, the bridge emits an exact machine `NO_WORK` artifact, and repository application owns mutations and postcondition qualification. The prior shared recovery and typed idle substrate through PR #355 remain characterization and reusable primitives. Human refinement exposed their competing positive materialization semantics; the reviewed PR #357 canonical consolidation now supplies the merged prerequisite, with the clarified target/witness and actual-parent contract below retained for ordinary implementation verification. Bounded advisory admission, unchanged-Human-decision suppression, and post-terminal production acceptance also remain delivery work until governed implementation and production evidence prove them.

## Recovery decision log — 2026-10-07

The accepted #322 application continuation reached run `37563005754`, attempt 2, job `112607809410`, against `main@cd8d45f64e901cdb8e5e8b42358d6081a293d08f`. Its persisted log proves only `effect precondition rejected`, three effects observed, and no CarrierPlan; the rejected effect and historical guard-specific reason were not persisted and cannot be reconstructed as facts. Current source independently proves that a still-missing materialization whose accepted paths overlap the default-branch advance is rejected as `materialization missing work overlaps default advance`. That current deterministic guard is evidence for the present blocker, not proof of the exact historical guard.

Decision: preserve the stale-preimage, same-path overlap, identity, cardinality, and authorization checks. Repair liveness at the existing application/evidence owner: preserve exact rejection and completed-effect evidence, explicitly retire an accepted materialization or physical-effect plan that no longer qualifies, and permit a fresh continuation only after current-state reconciliation and authorization. Re-plan only when canonical proof and exact path/preimage checks show it is safe; otherwise return the named conflict as a blocker and require the existing governed correction path. Never rerun the same run/job or unchanged rejected operation. There is no fixed numerical ceiling for substantive recovery attempts: each later transition requires a new qualified failure-evidence digest, one exact predecessor in the linear chain, fresh authorization, and current canonical proof. A run, plan, date, or nonce change alone never permits another attempt.

The existing continuation correlation currently binds only the original request and accepted-decision digest. That identity is too broad for bounded recovery: repeating it cannot distinguish a new qualified failure from the same transport, and multiple continuation comments can make run selection ambiguous. Extend the existing continuation/evidence owner so each continuation is content-addressed to one exact predecessor run/job/attempt/artifact and structured failure-evidence digest, plus a stable causal-episode fingerprint. The exact-evidence correlation deduplicates identical evidence. The stable episode key, which excludes nonce, date, run id, and plan id, preserves causal identity across distinct fresh continuations without imposing an attempt budget. Only one uniquely linked next run may proceed; duplicate or branching history is a blocker.

This correction does not claim the existing #322 payload can be auto-applied through the currently observed same-path conflict. If exact intent cannot be carried forward without overwriting current work, the legal outcome is a precise blocker and an explicit correction, not a forced write or a false completion.

## What Changes

- Close the Human-approved refinement in source comment 5986774520 and independent FINDINGS 5987083136: later wakes must discover and consume the unique qualified pending CarrierPlan, distinguish a missing plan from a missing physical effect, and return qualified durable execution evidence through existing application ownership. The synchronous F3 carrier write to `ccfb3560571ca8d32d5d6217aaf0e9d45b4eb087`, application run `37254331790` attempt 2, exact-head strict validation, and review handoff are delivered evidence for that bounded effect only; native Scheduled Task consumption and the parent outcome remain unproven.
- Define one exact, run-scoped `NO_WORK` handoff from normal Action-only dispatch to bounded Lead idle semantic execution.
- Keep `AUTHORIZE`, `FAIL_CLOSED`, and all existing formal/pre-activation ordering authoritative; only true `NO_WORK` may reach idle semantics.
- Add a typed, evidence-bound idle request/result contract that is not an Action, normal routing state, queue, cursor, lease, heartbeat, registry, or recovery workflow.
- Reuse the existing bridge transport, fresh repository preflight, application-owned effect/reconciliation, canonical Issue tuple, and later normal dispatch; extend the existing continuation correlation with exact predecessor/evidence binding and reconstruct a single bounded attempt chain, without a new state store.
- Add the smallest repository-owned admission actuator for one bounded advisory or one existing/new routing-complete Explore candidate, with fresh reauthorization, minimal overlap serialization, read-only ambiguous-write reconciliation, and fail-closed guards. Advisory admission is non-routing, uses exactly `advisory:idle`, is limited to three recommendations, and never carries `Change:` state.
- Suppress repeated semantic ingress only when the current qualified frontier is the same unanswered `HUMAN_DECISION_REQUIRED → Lead / resolve-question` consequence and no newer qualifying Human decision or materially changed evidence exists. This is a derived no-op view, not persisted routing/retry/wait state.
- Consolidate shared application/materialization completion around one canonical read-only durable-consequence proof. For accepted intent `I` and fresh repository state `S`, that owner returns only `COMPLETE(target, witness)`, `INCOMPLETE`, or `CONTRADICTORY(reason)` after proving Identity, Content, Lineage, and Non-conflict. Apply-side already-complete checks, materialization postcondition, interruption recovery, and consequence completion classification MUST consume that same proof; historical/replacement/merged/reconciled/direct Git shapes remain proof primitives or witnesses, not separate positive completion semantics. Preserve immutable accepted intent, exact per-effect rejection evidence, legal plan supersession, fresh authorization, and bounded recovery without semantic replay; same-path conflicts remain fail-closed.
- Define and verify the external Scheduled Task/bootstrap activation boundary so a merged repository implementation is not mistaken for production reachability.

## Decisions and proportionality

### REUSE

For carrier closure, reuse immutable accepted intent, content-addressed CarrierPlan, exact Actions request/run/attempt/artifact identities, canonical `COMPLETE(T, W)` proof, application-completion qualification, the configured connector actuator, existing exception evidence, and `APPLICATION_CONTINUATION`. The saved plan is a handoff, not completed mutation or permission to replay its producer.
Reuse the current Action-only dispatcher and disposition contract, the existing bounded Lead idle semantics from the canonical workflow, the current application-owned exact-effect/postcondition machinery, the existing canonical `Change: unset + action:explore-change` tuple, and the current fresh-revision/run-scoped evidence model.

### CONSOLIDATE

The existing application-completion owner selects missing plan versus missing external effect versus missing validation/consequence. The same owner qualifies and deduplicates external execution evidence; external bootstrap performs only the exact freshly qualified connector operation. Remove recovery behavior that needlessly reruns a plan producer when a valid pending plan already exists.
Place idle handoff validation, admission preconditions, and reconciliation in the existing repository-owned bridge/application boundary. Consolidate materialized-consequence completion into one canonical read-only proof owner in the existing application/materialization layer; every positive completion consumer delegates to it, while topology-specific helpers remain subordinate witness/identity/safety primitives. Use one minimal ephemeral serialization boundary only for the final GitHub admission mutation. Keep semantic discovery with Lead and physical mutation with the application owner.

### NO-DELTA

Do not change normal Action-only dispatch, Role derivation, formal WIP/finish-first ordering, Human authority, normal routing labels, daily transport semantics, or the existing Action successor lifecycle. Do not create an idle Action, an idle transition, an `agent:*` normal routing dimension, a second queue/state machine, a cursor, lease, heartbeat, hidden backlog, or registry.

### ADD

At these existing owners, minimally extend the run-bound dispatch/artifact handoff and continuation evidence transport only as necessary to expose the unique eligible plan and preserve catchable actuator/reporting outcomes. This addition is required by the demonstrated saved-plan/unperformed-write boundary and missing qualified evidence; it introduces no Action, ResultKind, control state, registry, or external orchestrator. Canonical `EXECUTION_EXCEPTION` remains evidence with zero routing or terminal authority.
Add only the typed non-Action `NO_WORK` handoff and the repository-owned candidate admission/reconciliation primitive required to make the retained capability executable and safe under overlap, interruption, stale evidence, and ambiguous GitHub writes.

## Scope

In scope:

- the canonical scheduled-agent workflow contract and focused runtime/bridge/application implementation;
- an exact non-Action idle request/result envelope tied to a successful dispatch run and artifact;
- advisory/existing/new candidate admission, deduplication, postcondition verification, and safe reconciliation;
- tests for the required negative, concurrency, interruption, stale-state, and handoff properties;
- one canonical read-only durable-consequence proof for materialized application consequences, shared by apply-side precheck, materialization postcondition, interruption recovery, and consequence completion classification;
- historical topology characterization retained as witness/proof shapes rather than separate completion semantics;
- accepted-application recovery after an uncorrelated legacy result or a rejected effect, including exact source/Change/run binding, durable guard-specific evidence, safe plan supersession, and fail-closed handling of duplicate intents, duplicate runs, changed routing, and unresolved same-path conflicts;
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

0. **Historical materialization recovery characterization — delivered, not systemic completion** — Historical `main@5fa6fdf7d9b33e3f2718c9525bb685f74393d3f3` included the prior #322 recovery chain through PRs #331–#333, #347, #349, #354, and #355. Those repairs provide valuable characterization, lineage helpers, merged/replacement/reconciliation witness logic, and interruption-recovery primitives. They do **not** prove a single authoritative positive completion definition. PR #357 originally supplied additional production RED evidence; its final merged repair absorbed that case into the canonical proof without retaining a permanent topology-specific top-level branch.

1. **Canonical durable-consequence proof consolidation — merged prerequisite; ordinary verification retained** — The bounded Human-authorized bootstrap merged PR #357 at `1ca1d8e37e42bf1b689826ec34a0e335ba1f68b4` after independent exact-head review `5405763214`, 891 passing tests, required quality checks, and strict OpenSpec validation on candidate `63df1af3928e2c41f0ef69dcd3cc3623f4221544`. Production continuation run `37199451772` then validated existing PR #353 revision `ae9eba694cf56e510051b7a85f0eae531d528829` without materialization replay. Ordinary Executor delivery must verify this merged N-1 against the clarified target/witness and revision/preimage contract; this bootstrap does not close the parent outcome. The delivered sequence was to first retain the historical production shapes and negative cases as characterization without changing behavior; then introduce one read-only proof owner in shadow, cut materialization observation/postcondition/fresh recovery/consequence classification over to it, cut apply-side already-complete logic over to the same owner, verify the four systemic properties (apply/observe consistency, interruption invariance, safe-evolution monotonicity, conflict preservation), and only then remove superseded topology-specific top-level completion branches. After every consequential mutation, local API success is discarded as authority and fresh GitHub truth is evaluated by the same proof. This stage is complete only when all positive consumers share that owner and the negative fail-closed cases remain protected.

2. **Contract and dark executable substrate — already delivered; re-verify after Stage 1** — The typed run-bound `NO_WORK` envelope and exact idle qualification already exist without changing `select_work()`, the Action enum, or normal routing. Their prior delivery does not bypass the canonical-proof prerequisite; final implementation review must verify they remain correct after Stage 1 cutover. The external idle wake remains an explicit activation boundary.
3. **Safe admission boundary — partially delivered on current main** — Existing/new Explore admission, fresh `NO_WORK` reauthorization, interruption reconciliation, and the typed idle substrate are already present. Bounded advisory admission and the derived unchanged-Human-decision wait remain implementation work and MUST be independently reviewed and merged before this stage is complete.
4. **Governed lifecycle, then production acceptance** — N-1 is the remaining repository implementation merged on the default branch. Complete independent implementation review, exact-head merge, finalize/archive review and merge, and legal terminal lifecycle first; while #322 remains routed formal work, normal dispatch cannot truthfully produce `NO_WORK`. After formal routing is gone, use a later real Scheduled Task wake to prove exact `NO_WORK` idle execution, no-finding silence or safe advisory/Explore admission, and—when a Formal Explore is admitted—a still later ordinary wake authorizing `Lead / explore-change`. No special dispatcher exception or validation-hold state is introduced. Human-defined completion requires both the legal lifecycle terminal state and this post-terminal production acceptance evidence.

**Carrier refinement delivery before production cutover.** Preserve the approved parent outcome and all Stage 0–4 coverage. Insert two atomic stages after the verified canonical-proof prerequisite: (a) unique pending-carrier discovery/consumer selection and exact connector execution, then (b) qualified execution-evidence/reporting/interruption closure. Both reuse then-current N-1 accepted-intent/CarrierPlan/canonical-proof/application-completion owners, are independently executable/testable/reviewable/mergeable, and require exact-head review and merge before the next stage consumes them. Their exits close the demonstrated carrier gaps only; bounded advisory, derived Human-wait, native activation, full lifecycle and post-terminal NO_WORK remain mandatory. Add a third atomic correction stage after qualified evidence: recover exact effect refusals through plan disposition and current authorization, with no same-path write, unchanged-denial retry, or continuation-counter reset; strict OpenSpec review must pass before this semantic correction is implemented. Continue through the existing MORE_IMPLEMENTATION_REQUIRED/later fresh dispatch path when any mandatory repository work remains.

The repository-visible cutover uses the existing `scheduled-agent-application.yml` carrier with one
typed `IDLE_ADMISSION_REQUEST` Issue-comment RPC on the current daily runtime shard. The comment is
only a trigger/staging transport, not a mailbox or accepted-intent record; no-finding remains silent.
The same boundary carries an exact `APPLICATION_CONTINUATION` body for an accepted application that
needs a fresh GitHub workflow run after a completed invocation. A real external Scheduled Task must
still be configured to read the exact successful bridge artifact, invoke bounded Lead idle semantics,
and post the exact typed body only when a candidate or continuation is present; that external setting
is an external product boundary. The available automation capability can inspect/update the saved prompt and request an immediate run, but its acknowledgement and last-run metadata do not expose a complete execution trace or prove GitHub effects. Use actual native output and durable repository correlation where available; explicitly retain unknown links and capability limits.

Every stage must have a fresh exact-head review, required validation, and an exact-head merge before the next stage uses it as N-1. Stages are independently testable and deployable while preserving the full parent outcome; their exit criteria do not replace the parent completion evidence below. A merged stage, including the bootstrap prerequisite, is not completion until Stage 4 proves the production wake path and normal Action handoff.

## Completion evidence

The parent Change is complete only when fresh evidence proves:

- a later ordinary fresh wake discovers the unique eligible carrier, qualifies immutable intent and the exact plan from current GitHub truth, executes only a genuinely missing operation, and reaches canonical postcondition proof, application continuation, exact-target validation, and derived handoff;
- completed effects cause zero duplicate mutation; missing plans alone permit owner-selected producer reconstruction; stale, conflicting, duplicated, superseded, incomplete, ambiguous, or contradictory plans fail closed;
- normal CarrierRequired, actual rejection/error, unknown write response, and blocked result reporting remain distinguishable with exact request/run/attempt/artifact/plan and target/preimage identity, platform-redacted raw evidence, known mutation status, and unfinished boundary; legal application qualification deduplicates evidence without rewriting accepted intent or creating routing authority;
- real native Scheduled Task evidence establishes request -> run/attempt -> artifact/log -> fresh repository postcondition independently of this conversation. Run-now acceptance and fixtures that manually mutate simulated GitHub state do not satisfy external handoff acceptance;
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
- current target `T` and immutable desired-content witness `W` remain separate: legal same-Change evolution may return `COMPLETE(T, W)` with changed target content and `T != W`, while exact review/validation binds `T` and no invocation-local target equality supplies completion authority;
- accepted authorization `A`, declared carrier base `B`, actual prospective mutation parent/preimage `P`, and fresh default branch `D` remain distinct; each missing write checks `expected_sha` against `P` under fresh authorization and full graph/non-conflict guards, while an obsolete preimage need not remain current after the accepted desired witness is proven;
- fresh-process consequence completion uses durable GitHub evidence and canonical proof primitives without replaying semantic work or requiring local target memory;
- successful admission is consumed by a later ordinary normal Action dispatch;
- every accepted-application precondition rejection has reconstructable effect-level evidence; stale plans are superseded only after exact current-state proof, while overlap or unknown writes remain blockers;
- the same qualified rejection evidence produces at most one continuation/run; a genuinely new evidence transition links to exactly one predecessor, while duplicate, branching, missing, or ambiguous history fails closed; the stable causal-episode cap cannot be reset by changing its transport correlation;
- one unresolved causal recovery episode may continue only through unique, newly qualified evidence-linked transitions; identical evidence and unchanged refusal are not retried, while fresh authorization and canonical proof remain required for every new attempt;
- repeated wakes do not emit a new semantic request/result while the same qualified `HUMAN_DECISION_REQUIRED → resolve-question` frontier remains unanswered and materially unchanged, while newer qualifying Human/material evidence resumes execution;
- repository implementation is merged and the active OpenSpec Change reaches its legal terminal lifecycle before true `NO_WORK` production acceptance is attempted;
- the actual production bootstrap boundary is activated and has post-terminal production-shaped evidence.

## Human invariants preserved

This change does not reopen #322's approved architecture. Normal dispatch stays Action-only; `NO_WORK` remains an idle semantic boundary; normal work always wins; Lead retains semantic materiality judgment; the application owns consequential mutation; successful admission returns immediately to the existing canonical Action workflow; and no second workflow/control state is introduced.

## Skill maintenance

The carrier extension affects shared bootstrap/application procedural guidance at its existing owner. Preserve existing Role and Skill responsibilities; declare REUSE for openspec-change/review/delivery and current application procedures, CONSOLIDATE for duplicated bootstrap handoff instructions, and NO-DELTA for all unrelated Skills. No Skill creation, removal, or rename is planned. If implementation needs a material Skill change, it must follow the current skill-maintenance procedure and obtain independent review of that declared scope.
No Role or Skill semantic responsibility change is intended. `Lead / explore-change` and `Lead / propose-change` continue to use their existing procedures. Implementation must load the repository skill-maintenance procedure only if fresh evidence shows that a Skill itself changes.

## 2026-10-08 integrated carrier handoff decision

The production chain is one contract: dispatch artifact (`application_continuation` plus `qualified_carrier`) → enabled Lead Workflow Chat → exact plan read and connector operation → fresh postcondition → one durable `APPLICATION_CARRIER_OUTCOME` report → repository parser → exact continuation → fresh application authorization/postcondition. The Task report is evidence only. Missing, malformed, refused, ambiguous, stale, or unknown outcomes emit no continuation.

The report binds the original request and accepted-decision digest, continuation correlation, predecessor run/attempt/job, recovery artifact id/digest, failure-evidence and episode digests, carrier artifact id/digest, Plan-ID, operation, outcome, mutation status, precondition status and observed expected-field JSON, postcondition, unfinished boundary, and redacted failure summary. The parser requires the exact ordered schema. Only one complete report with a matching observed precondition and exact lineage releases continuation.

A later fail-closed dispatch must not hide an older unresolved carrier handoff. The bridge inspects every earlier trusted DISPATCH_REQUEST result on the current runtime shard; missing runs/artifacts or any same-plan handoff without its exact outcome remains a named blocker. The two legacy #322 continuation runs are not merged by shared correlation: both logs lack effect-level failure evidence and mutation frontier. The stale six-file accepted manifest is not replayed; its tests/effects preimage is mismatched and other paths have since changed. Reconciliation can resume only from current canonical proof and a fresh exact plan.

No fixed numeric recovery ceiling is added. Identical evidence/refusal, same completed run/job, stale precondition, unknown write, branching identity, or incomplete report remain blockers. The existing native task schedule/enablement and connector permissions stay unchanged.

## 2026-10-08 exact-head integration correction

The first exact-head Python run of `6635bc1` exposed five failures and one test-setup error (912 passed): the legacy accepted-manifest merge-acceptance line passed `durable_checkpoint_revision` to the current `apply_effect_batch` API, which does not accept that parameter; a report-parser test incorrectly expected a context-free syntax parser to reject a syntactically valid repository value; and the carrier lineage parameterization had been separated from its test during insertion. Revert the out-of-scope legacy merge-acceptance transplant to the exact PR pre-change file rather than expanding the shared effects API without canonical proof. Keep report shape validation in the parser and accepted-request/repository/plan binding in the bridge consumer; test both layers. The old manifest remains unreconciled and is not considered applied.
