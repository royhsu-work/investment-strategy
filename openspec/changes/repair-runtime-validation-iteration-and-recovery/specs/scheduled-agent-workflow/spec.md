## ADDED Requirements

### Requirement: Known mechanical validation failure permits same-Action correction

A qualified mechanical validator verdict SHALL identify the affected candidate revision, validation check, and authoritative run and attempt. This contract covers OpenSpec Strict Validation, Pytest, Ruff, Mypy, and other governed mechanical checks. A qualified FAIL SHALL retain the same Action and mapped author. The Application SHALL preserve the old acceptance and exact write identity, observe prior effects, and freshly authorize any corrected revision. A predecessor with unresolved writes SHALL be reconciled before any conflicting write. An exact PASS SHALL satisfy only its applicable validation obligation. Formal Result and successor effects SHALL follow the established completion gates, including independent review where required.

#### Scenario: Repeated qualified failures followed by exact success

- GIVEN a candidate under the selected Action has a qualified mechanical FAIL
- WHEN the mapped author submits freshly authorized corrected revisions and the latest passes exact validation
- THEN the Application retains the failed attempts and completed effects, applies only necessary current effects, and completes the Formal Result and derived routing when all applicable gates are satisfied

#### Scenario: Validation is pending or interrupted

- GIVEN the exact validator run is still pending or its verdict cannot be qualified after interruption
- WHEN the Runtime checks completion
- THEN it bounds the wait, preserves the validation identity and outstanding obligations, and allows later fresh observation without inferring a verdict

### Requirement: Legacy accepted completion preserves evidence and current obligations

The Application SHALL reconcile a legacy acceptance or migrate its completion using immutable source evidence, qualified fresh postconditions, and current authority for remaining effects. It SHALL preserve prior accepted manifests and completed effects, distinguish validation of the current revision from qualification of an older manifest, and prevent unsafe replay or rewind. Recovery across shard rollover SHALL preserve the original causal identity.

#### Scenario: Formal Result exists and successor routing is incomplete

- GIVEN a qualified prior Formal Result exists for a legacy acceptance and successor routing remains incomplete
- WHEN fresh observations establish the current frontier
- THEN the Application reconciles only the remaining routing obligation when authorized and does not re-emit the Formal Result or rewind a completed descendant

## MODIFIED Requirements

### Requirement: Accepted-application rejection recovery is exact and evidence-deduplicated

Accepted intent `I`, materialization/effect plan `P`, optional externally executable CarrierPlan `C` (which may be absent), and execution attempt `R` SHALL remain distinct. A failed effect SHALL NOT rewrite or replace `I`. Before an effect-precondition rejection is reduced to a generic batch outcome, the existing application/evidence owner SHALL preserve the exact failed effect and ordinal, operation/target, expected and observed preimage, guard reason, canonical completion proof, effects already proven complete, mutation status (`complete`, `not-complete`, or `unknown`), and unfinished boundary. Evidence SHALL bind the immutable accepted-decision digest and exact request/run/attempt/artifact and any plan ids that exist, and SHALL explicitly represent an absent CarrierPlan rather than guessing one. It SHALL not contain credentials or fabricate unobserved platform errors.

Before any later write, recovery SHALL use current repository truth and fresh authorization. Unknown or lost write outcomes SHALL be reconciled read-only first. A complete canonical proof SHALL skip duplicate mutation. A stale/expired `P` or existing `C` MAY receive a `PLAN_SUPERSEDED` disposition only after its invalidation and already-completed effects are proven; this ends that plan's execution authority without changing `I`. A replacement `P` or `C` MAY be created only when the same accepted intent remains current and the canonical proof plus exact current preimages, lineage, authorization, and non-conflict checks prove the operation remains safe. Same-path overlap or an unresolvable expected/observed preimage conflict SHALL remain fail-closed with its exact blocker and the existing governed correction path; no automatic overwrite, force update, semantic replay, or guessed payload is allowed.

A `run_attempt > 1` value alone SHALL neither permanently block a safe continuation nor authorize rerunning its completed run/job. A continuation SHALL use the existing `APPLICATION_CONTINUATION` path and create a fresh run only after unique intent/current predecessor, current Issue/Change/Role/Action, exact evidence chain, fresh authorization, and a new qualified failure-evidence transition is proven. No new Action, ResultKind, retry registry, counter, queue, cursor, lease, or progress database is introduced.

The existing `APPLICATION_CONTINUATION` correlation SHALL be extended to bind the accepted-decision digest, one exact predecessor run/job/attempt and artifact id/digest, the structured rejection-evidence digest, and a stable causal-episode fingerprint. The per-transition correlation SHALL be deterministic from qualified evidence, not an arbitrary nonce; identical evidence SHALL map to the same correlation and at most one next continuation/run. Each new run SHALL have exactly one evidence-linked predecessor in one linear chain. Duplicate, branching, missing, or ambiguous continuation/run/artifact links SHALL fail closed **for continuation or replay of that physical operation**. The stable episode fingerprint, which excludes run id, plan id, nonce, and date, SHALL preserve causal identity across distinct transition correlations without imposing a numeric attempt cap. Historical intent-only continuation comments do not qualify as new failure evidence. When a legacy attempt has only generic or incomplete failure evidence and a fresh canonical/safety proof cannot uniquely recover the remaining work and evidence chain, the owner SHALL return a specific evidence-incomplete blocker without emitting an **old-plan continuation**. This historical blocker SHALL NOT alone prohibit an independently authorized prospective correction with sufficient current final-state and material safety evidence.

A retry of a rejected physical operation SHALL be eligible without a fixed numerical attempt ceiling only when its failure-evidence digest is new within the same stable causal episode and its exact predecessor is unique. Completion of a different outstanding obligation SHALL be evaluated against its own fresh proof and authorization. The recovery ordinal SHALL be derived from the complete artifact chain for audit and structural validation; it SHALL NOT be used as a retry budget. New run ids, plan ids, nonces, dates, or unrelated default-branch changes SHALL NOT qualify as new evidence. An unchanged explicit refusal or repeated evidence digest SHALL NOT be retried. Missing/ambiguous evidence or a failed evidence write SHALL produce a precise fail-closed blocker and reopening condition. Only a newly qualified evidence transition or a newly governed correction may reopen substantive recovery mutation. Historical digest equality SHALL NOT prevent fresh read-only evaluation of the current postconditions. A newly verified remaining obligation SHALL require its own current authorization and deduplication before mutation.

#### Scenario: Effect rejection preserves the exact failed guard

- GIVEN an accepted application has three proposed effects and the second effect's expected preimage does not match the fresh observed target
- WHEN the application rejects the effect batch
- THEN durable qualified evidence names that exact effect, expected and observed preimage, guard reason, completed-effect set, mutation status, and unfinished boundary
- AND the batch result is not reduced to `effect precondition rejected` alone

#### Scenario: Same-path default advance remains a precise blocker

- GIVEN an accepted plan is missing a desired materialization
- AND fresh default-branch history changed the same requested path after the plan base
- AND the canonical proof cannot prove the accepted desired consequence complete or safely project it
- WHEN recovery reconciles the rejected plan
- THEN it reports the exact path conflict and expected/observed preimage and performs no old-plan carrier or repository mutation
- AND `PLAN_SUPERSEDED` is recorded only if **both** the plan invalidation and sufficient completed-effect frontier have been proven, otherwise historical UNKNOWN remains unchanged
- AND a new prospective operation requires separately qualified governed Forward Correction with fresh authorization and preimage, not silent rebasing of the rejected plan

#### Scenario: Safe disjoint evolution permits a fresh plan

- GIVEN the accepted materialization is incomplete
- AND all intervening default-branch changes are proven disjoint from every requested path
- AND exact identity, content, lineage, current authorization, and prospective-parent preimages remain valid
- WHEN a fresh continuation reconstructs the necessary plan
- THEN it may create one new plan bound to the same immutable accepted intent and current proof
- AND it performs only the missing exact non-force operation
- AND it creates no duplicate, rewind, or semantic request

#### Scenario: Unknown write is reconciled before continuation

- GIVEN a connector may have applied an operation but its response or evidence write was lost
- WHEN a fresh recovery begins
- THEN it performs read-only reconciliation against the exact target and accepted intent first
- AND it does not issue another write until the outcome is proven incomplete and safe to continue
- AND ambiguous evidence returns a precise blocker

#### Scenario: Legacy generic rejection is not guessed into a recovery attempt

- GIVEN a historical accepted application has only a generic precondition-rejected result
- AND no exact failed effect, evidence chain, or remaining attempt history can be reconstructed
- WHEN the recovery owner evaluates the accepted intent
- THEN it performs only the fresh read-only proof required to determine whether the consequence is already complete
- AND if remaining work, a unique predecessor, and safe effect state are not provable, it returns an evidence-incomplete blocker
- AND it emits no new old-plan continuation and fabricates no guard reason
- AND that old-plan evidence gap does not independently prohibit a separately authorized safe prospective correction whose defined current postconditions and side-effect safety can be machine-verified

#### Scenario: New evidence continues after the former numeric threshold

- GIVEN one accepted intent has three substantive fresh recovery transitions for one unresolved causal episode
- AND a later run produces a new exact failure-evidence digest linked to the unique predecessor
- AND the current authorization and canonical proof still qualify the accepted intent and exact operation
- WHEN the recovery owner evaluates the new evidence
- THEN it may emit exactly one continuation for the new transition
- AND an unchanged refusal or repeated evidence digest still emits no continuation or mutation

#### Scenario: Transport identity alone never creates another attempt

- GIVEN one accepted intent has any number of substantive recovery transitions for one unresolved causal guard/path
- AND later wakes change only a transition correlation, request correlation, run id, plan id, or date without new qualified failure evidence or causal repair
- WHEN the recovery owner evaluates the intent
- THEN it emits no further continuation or mutation
- AND it preserves the exact blocker and reopening condition

#### Scenario: An unchanged refusal is not retried

- GIVEN the last qualified attempt was explicitly refused by the same unchanged guard
- AND no qualified causal repair or governed correction exists
- WHEN a later scheduled wake evaluates the accepted intent
- THEN it performs no application rerun or semantic replay
- AND it returns the existing evidence-bound fail-closed disposition

#### Scenario: Repeated historical evidence permits fresh postcondition observation

- GIVEN a historical failure-evidence digest is repeated
- WHEN the dispatcher evaluates the current accepted obligation
- THEN it evaluates fresh qualified postconditions and emits no duplicate mutation or unchanged continuation
- AND improved evidence may qualify only the still-outstanding operation through the existing authorization boundary
