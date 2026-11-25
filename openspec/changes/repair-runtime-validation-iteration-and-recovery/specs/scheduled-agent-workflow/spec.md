## ADDED Requirements

### Requirement: Known mechanical validation failure permits same-Action correction

A qualified mechanical validator verdict SHALL identify the affected candidate revision, validation check, and authoritative run and attempt. This contract covers OpenSpec Strict Validation, Pytest, Ruff, Mypy, and other governed mechanical checks. A qualified FAIL SHALL retain the same Action and mapped author. A known ordinary mechanical failure with settled writes SHALL NOT itself require mutation Recovery; review findings and specification blockers SHALL use their existing correction routes. Unknown or partially completed durable obligations SHALL use the existing recovery owner. The Application SHALL preserve the old acceptance and exact write identity, observe prior effects, and freshly authorize any corrected revision. A predecessor with unresolved writes SHALL be reconciled before any conflicting write. An exact PASS SHALL satisfy only its applicable validation obligation. Formal Result and successor effects SHALL follow the established completion gates, including independent review where required.

#### Scenario: Repeated qualified failures followed by exact success

- GIVEN a candidate under the selected Action has a qualified mechanical FAIL
- WHEN the mapped author submits freshly authorized corrected revisions and the latest passes exact validation
- THEN the Application retains the failed attempts and completed effects, applies only necessary current effects, and completes the Formal Result and derived routing when all applicable gates are satisfied

#### Scenario: Validation is pending or interrupted

- GIVEN the exact validator run is still pending or its verdict cannot be qualified after interruption
- WHEN the Runtime checks completion
- THEN it bounds the wait, preserves the validation identity and outstanding obligations, and allows later fresh observation without inferring a verdict

#### Scenario: A terminated validation attempt supplies no qualified verdict

- GIVEN settled effects and a required check canceled, timed out, or terminated by its execution environment
- WHEN no current qualified exact-target verdict exists and verification is freshly authorized
- THEN the existing repository-owned verification path SHALL obtain an eligible validation attempt for that same target without repeating any settled mutation
- AND the validation obligation owner derives the required validator and exact target; an ordinary native wake may actuate only that qualified invocation when no usable verdict or eligible active invocation exists, including a completely observed absence of a run
- AND completion SHALL require complete evidence for the applicable workflow definition and validator baseline, checkout, attempt and required steps; a skipped mandatory check or an unrelated success cannot qualify
- AND an unavailable observation or unknown invocation outcome permits fresh observation without assuming absence, retrying a settled physical effect, or completing the obligation

### Requirement: Legacy accepted completion preserves evidence and current obligations

The Application SHALL reconcile a legacy acceptance or migrate its completion using immutable source evidence, qualified fresh postconditions, and current authority for remaining effects. It SHALL preserve prior accepted manifests and completed effects, distinguish validation of the current revision from qualification of an older manifest, and prevent unsafe replay or rewind. Recovery across shard rollover SHALL preserve the original causal identity.

#### Scenario: Formal Result exists and successor routing is incomplete

- GIVEN a qualified prior Formal Result exists for a legacy acceptance and successor routing remains incomplete
- WHEN fresh observations establish the current frontier
- THEN the Application reconciles only the remaining routing obligation when authorized and does not re-emit the Formal Result or rewind a completed descendant

### Requirement: Development materialization and verified slice completion are distinct consequences

For an approved implementation slice, repository Application SHALL authorize each necessary exact-preimage development materialization on the existing carrier independently of slice completion. An incomplete slice MAY span multiple commits, native CI runs and wakes. Development commits MAY precede mechanical validation and contain a failing candidate; they MUST NOT mark tasks complete, create a verified checkpoint or formal completion result, advance routing or authorize merge. Application SHALL preserve exact accepted intent, observed physical write postconditions and current ownership protection; worker, transport and CI cannot authorize writes. A settled development attempt with an authoritative terminal exact CI verdict SHALL allow fresh same-Action development or completion qualification without committing a formal result; a pending or unknown verdict SHALL allow bounded fresh observation, not a guessed success or competing write. Unknown, conflicting or unsettled effects SHALL retain their existing safety obligations.

Formal implementation tests SHALL execute in the existing native CI environment; the worker MUST NOT rely on local installation, a full local test environment, direct API tokens or direct Actions execution. The existing Python Quality checks SHALL execute Ruff lint, Ruff format check, Mypy, then pytest, stopping at the first failure. Valid RED SHALL require all preceding static checks PASS and an intended target-behavior pytest failure before production correction; syntax, indentation, format, type, import, fixture/setup, dependency and unrelated failure SHALL NOT qualify as RED. GREEN SHALL establish minimum approved behavior and all required gates PASS at the exact revision. Refactor, if needed, SHALL be revalidated. No special RED runner, TEST/VERIFY mode, commit trailer, semantic Action or persisted TDD phase SHALL be required.

Slice completion SHALL require the approved task criteria, fresh exact authorization, exact current required validation PASS (including applicable strict OpenSpec validation), durable task markers, and exactly one effective verified checkpoint and formal completion result before successor or next slice. If task markers produce a new HEAD, applicable gates SHALL validate that HEAD; previous-head PASS SHALL NOT be reused. A GREEN revision MAY satisfy VERIFY when all completion criteria and exact gates hold; no artificial extra commit/run is required. Existing independent review, merge and archive gates remain mandatory.

#### Scenario: CI-only RED and GREEN within one slice

- GIVEN an independently approved slice on the exact existing carrier and fresh authorized development manifest
- WHEN Application materializes tests before production correction and native CI observes static PASS followed by the intended behavioral failure
- THEN the revision is valid RED evidence without completing a task, checkpoint, formal result or routing transition
- AND a fresh authorized correction on the same slice obtains exact GREEN and applicable completion gates before the one verified completion result

#### Scenario: Static or environmental failure is not RED

- GIVEN a candidate CI run
- WHEN Ruff lint, format or Mypy fails
- THEN later steps do not execute
- AND neither static failure nor a pytest import, setup, dependency or unrelated failure qualifies as RED
- AND the mapped author corrects the candidate under existing fresh authority rather than manufacturing completion or a recovery obligation

#### Scenario: Completion marker changes revision

- GIVEN verified implementation behavior at R1 and a task marker update producing R2
- WHEN the completion consequence is evaluated
- THEN R2 receives its own applicable required gates through existing native CI
- AND no R1 PASS substitutes for R2 PASS
- AND exactly one effective checkpoint and formal completion result are persisted only after completion postconditions

#### Scenario: Pending or interrupted development is reconstructed

- GIVEN an accepted development manifest with incomplete CI or uncertain materialization
- WHEN a later wake observes fresh repository evidence
- THEN settled physical effects are never replayed
- AND pending CI is observed, while unresolved or competing writes prevent conflicting authorization
- AND a qualified terminal verdict with settled development writes allows the same Action to continue the first incomplete slice without an intermediate formal completion result


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

### Requirement: Application consequence completion is reconstructable across interruption

The application bridge SHALL treat an `EFFECT_REQUEST` as an ingress candidate,
not as an accepted application. Each current-frontier candidate SHALL be
classified independently as exactly one of `ACCEPTED`, `LIVE_PREACCEPT`,
`TERMINAL_NO_ACCEPT`, `REJECTED`, or `INVALID/UNKNOWN` before reduction. A
missing or not-yet-visible Actions run is asynchronous observation evidence,
not terminal or rejected evidence; `TERMINAL_NO_ACCEPT` requires authoritative
terminal/non-mutation evidence from the exact application execution. The
reducer SHALL apply these rules: more than one current `ACCEPTED` is ambiguous; one current
`ACCEPTED` exclusively owns continuation and terminal/rejected noise does not
compete; zero accepted plus more than one live candidate is ambiguous; zero
accepted plus exactly one live candidate waits without semantic redispatch;
zero accepted plus only proven terminal-no-accept/rejected candidates returns
ownership to the semantic Action; and unknown or contradictory evidence fails
closed. N terminal or rejected candidates SHALL never become ambiguous merely
from raw count.

Before cardinality reduction, the existing formal lifecycle and ingress qualifier SHALL exclude an accepted validation candidate from current ownership only when authoritative evidence binds a terminal mechanical FAIL to its exact acceptance, candidate revision, check and run attempt, every authorized write and carrier is proven settled with no pending writer, and no qualified Formal Result has committed the consequence. This exclusion SHALL be reconstructable after interruption from existing durable evidence and SHALL preserve the immutable historical acceptance, its writes, and audit lineage. A pending, unknown, canceled, or conflicting verdict, or an unsettled write, SHALL retain the existing ownership or blocking disposition. A committed Formal Result SHALL remain governed by existing completion reconciliation. The failed candidate SHALL have no further write, completion, or routing authority after exclusion.

With zero current accepted owners and no competing live or ambiguous ingress, the existing dispatcher SHALL return ownership to the mapped author of the same Action and lifecycle occurrence. The existing Application Phase A SHALL re-evaluate the same ownership predicate, bind a corrected candidate to the fresh exact target and preimage, reject reuse of the settled failed candidate, and enforce at most one current acceptance before authorizing effects. A stale or competing candidate SHALL receive no effect or completion authority. An exact qualifying PASS on a fresh candidate SHALL allow only the one formal consequence and derived route under existing gates.

For a qualified development-only materialization under the development/completion contract, the physical effect has its own immutable acceptance and postcondition, but does not commit a formal slice consequence. The same current-frontier qualifier SHALL release a settled development attempt after qualified terminal exact CI PASS or FAIL with no completion effects, before cardinality reduction, without emitting a formal result or deriving a routing mutation. Unknown or competing writes retain existing protections. Historical completion intents SHALL NOT be reclassified as development. A completion intent SHALL retain the existing formal-result commit boundary and require all exact completion gates.

Before any consequential effect, fresh application
authorization SHALL durably persist one exact `APPLICATION_DECISION: ACCEPTED`
bound to the request comment, source Issue, Role/Action, Change, authorization
revision, result, and immutable worker intent.

Whenever an application step emits recovery-evidence output, the scheduled-application workflow SHALL upload the JSON as one direct, unarchived file with canonical artifact name `application-recovery-evidence`; the uploaded file basename and configured artifact name MUST match exactly. The bridge consumer SHALL keep validating the exact run, attempt, job, artifact id, digest, and parsed content from those direct JSON bytes. Every step that uploads this artifact, including the initial and post-validation boundaries, SHALL set `overwrite: true` so a new workflow attempt can replace its predecessor's artifact and post-validation evidence can replace initial evidence without creating ambiguous duplicates. A basename/name mismatch, missing upload, or unsuccessful upload SHALL remain fail-closed; changing to an archive format requires a coordinated consumer change.

After durable acceptance, interruption recovery SHALL use only that exact
accepted intent and idempotently reconcile missing effects.  It SHALL never
re-execute the semantic Action because mutable ingress was edited, deleted, or
re-observed after acceptance.  The one canonical `ACTION_RESULT`,
`REVIEW_RESULT`, or `MERGE_RESULT`, exact-bound by `Application-Correlation`
and qualified against repository postconditions, SHALL be the normal logical
application-consequence commit boundary.  Routing or terminal state is a
projection of that committed consequence; `APPLICATION_OUTCOME: COMPLETED`
MUST NOT be an independent normal completion authority.

Current application ownership SHALL be derived from the existing formal
lifecycle qualifier: current routing is owned by the latest qualified formal
predecessor whose repository-derived successor equals that routing.  The
derivation SHALL preserve legal same-Action recurrence and alternating
recurrence (including `A -> A` and `A -> B -> A`) without persisting an epoch,
generation, retry counter, lease, mailbox, or second lifecycle/state system.

Phase A SHALL resolve the exact machine dispatch, derive authoritative source
and Change, normalize the semantic worker payload, validate it, fresh-
reauthorize the current repository, derive the exact effect plan, perform any
required executable verification, and persist `APPLICATION_DECISION:
ACCEPTED` or `REJECTED`. No consequential repository mutation may precede
`ACCEPTED`. The semantic worker MAY omit `requested_effects` and `evidence_ref`,
which normalize to `[]` and `null`; it SHALL not be required to recreate
Issue/Role/Action/Change/Authorization-Revision/routing/successor/formal
headers. The application-owned envelope SHALL carry those machine facts from
fresh dispatch evidence, preferably through one opaque exact dispatch
correlation. Phase B SHALL accept only the immutable accepted intent, fresh-
observe the repository, reconcile exact missing idempotent effects, use a
carrier only when required, validate postconditions, persist the canonical
formal result, and derive routing/terminal projection. Failure before ACCEPT
has zero authoritative repository consequence; failure after ACCEPT resumes
the same intent and semantic replay count remains zero. For development-only materialization, Phase A SHALL authorize the exact physical effect without requiring a future CI PASS, and Phase B SHALL prove the materialization and observe native CI without persisting a formal completion result or routing mutation. All completion intents remain subject to applicable verification and exact completion postconditions.

Application admission and Dispatch retirement SHALL use the same complete request judgment for native WORKER_RESULT and legacy EFFECT_REQUEST. Bind immutable input to an independently qualified source, Change, request, revision and run/attempt chain; validate the semantic envelope and every operation-specific payload. If all attempts have terminated, no ACCEPT or possible consequential write remains and the input is deterministically invalid, the ingress owner SHALL retire that request on unchanged main. A later fresh dispatch may authorize corrected input. Incomplete evidence SHALL be reobserved. Once a transient dependency recovers, fresh qualification MAY proceed on unchanged code when termination, absence of ACCEPT, zero writes and absence of competing live work are independently proven. An unresolved source, in-flight write, internal contradiction or reproducible implementation defect SHALL retain its applicable safety boundary. Exception text, stage names, historical digests and a code advance alone SHALL NOT determine retirement, repair or replay.

The repository-defined dispatch and application request formatters SHALL
round-trip through the actual production request parsers whenever they
construct a canonical envelope. The repository-owned application entrypoint
SHALL invoke its formatter/parser and SHALL preflight the embedded typed
worker result with the actual production validator before the internally
constructed envelope is admitted to Phase A. The separately external
`DISPATCH_REQUEST` publisher SHALL conform to the production dispatch parser's
wire contract; its real connector-side publication and native run correlation
SHALL be established at the post-deployment native production-evidence gate,
not inferred from repository-only fixture tests or required for Executor
implementation task completion. One canonical terminal newline is permitted;
extra blank lines, duplicate/unknown fields and invalid evidence references
SHALL be rejected. An external producer cannot create acceptance or
completion authority by claiming formatter conformance.

For new pre-ACCEPT semantic work, the external worker SHALL provide only the
raw typed-result JSON in a minimally framed `WORKER_RESULT` comment on the
existing runtime shard (exact first line `WORKER_RESULT`, then a newline and
one JSON object in the remainder, tolerating ordinary JSON whitespace and
one terminal newline); it SHALL NOT author the canonical `EFFECT_REQUEST`
envelope itself. The existing GitHub Actions application ingress SHALL
fresh-qualify the original external comment and authoritative machine source,
then use the repository's production application formatter and parser to
construct and validate the canonical envelope **in-process** before the same
Phase-A authorization/acceptance boundary. The original comment id, bytes,
actor, Issue, revision and correlation SHALL remain the provenance of the
application; the internally formatted envelope SHALL NOT be mistaken for an
independently published GitHub comment or an authorization source. Neither
the formatter nor the external transport may choose routing, source, Change,
successor or acceptance. Malformed/unqualified worker input SHALL cause zero
application ACCEPT/effects, with existing bounded rejection/exception evidence.
This mechanism SHALL NOT depend on an Actions-bot comment triggering a second
workflow. Historical or already accepted `EFFECT_REQUEST` ingress SHALL retain
its immutable original identities, legacy qualification and no-replay recovery;
the new raw input path SHALL activate only prospectively at the default-branch
merge boundary. The separate external dispatch emitter still requires proof
of actual producer-side contract use; unit-test-only renderers do not qualify.

For first-carrier materialization, the apply-side already-complete check, immediate postcondition, and later fresh observer SHALL use one canonical durable-consequence proof for exact Issue, Change, branch, head, PR, manifest/content identity, lineage, and non-conflict. A pending continuation MAY remain valid after default-branch advancement only when the same proof classifies the consequence `INCOMPLETE` rather than complete or contradictory and the immutable original base is its ancestor with all carrier paths disjoint from intervening changes. Existing stale, overlap, identity, cardinality, and ambiguity guards remain mandatory. When an exact accepted intent has the verified branch ref and content but no matching PR, recovery SHALL emit only the missing application-owned PR consequence against fresh current main after the canonical proof plus ancestry, disjointness, exact branch/head/content, and complete all-head PR cardinality checks. It SHALL NOT rerun semantic work, recreate the branch, move the ref, or blindly create a duplicate PR.

A fresh process SHALL reconstruct materialized-consequence completion from the existing `ConsequenceSpec.evidence_target` through the same canonical durable-consequence proof owner. It MUST NOT require invocation-local `_materialization_targets` to recognize an already durable consequence. Implementation-carrier qualification remains in its existing owner except where that owner supplies materialization proof primitives; it MUST NOT become a competing positive definition for the same materialized consequence. If an uncorrelated legacy result invalidates formal-frontier qualification while the exact source route remains current, recovery MAY resume only one accepted intent and its unique request-bound run/job after exact Issue/Change/Role/Action checks. For a completed request-bound run, `run_attempt` is GitHub-owned invocation evidence and is not the recovery budget. `run_attempt > 1` alone SHALL NOT permanently block recovery or authorize a rerun of that same run/job. A safe continuation MAY use the existing `APPLICATION_CONTINUATION` transport to start one fresh, separately identified run only after exact failure evidence, unique accepted intent/run/job, current authorization, and the bounded-recovery requirement below qualify it. Changed identity/routing, duplicate intent/run/job, or incomplete evidence SHALL fail closed. Existing correlation, formal qualification, source/frontier, carrier, validation, review, successor, and terminal gates remain in force.

The materialized durable consequence itself SHALL have exactly one authoritative positive proof definition. Given one accepted intent and fresh repository state, the proof owner SHALL return exactly one of `COMPLETE(target, witness)`, `INCOMPLETE`, `CONTRADICTORY(reason)`, or `UNKNOWN(reason)`. `UNKNOWN` means an authoritative source observation was unavailable rather than an observed conflicting Git state; it neither proves a missing mutation nor permits completion. All consumers SHALL fail closed without mutation and SHALL preserve the evidence boundary until a new complete authoritative observation exists. Historical missing artifacts likewise SHALL NOT be treated as evidence of a write or no write. `COMPLETE` SHALL require coherent Identity, Content, Lineage, and Non-conflict evidence together. Git topology labels such as historical, replacement, merged, reconciled, or direct SHALL be treated only as evidence/witness shapes and MUST NOT create separate top-level positive completion semantics.

Identity SHALL include the exact repository, Issue, immutable Change, source Role/Action, intended PR/ref/branch, and unique carrier/cardinality. Content SHALL prove every accepted desired blob/content identity in the immutable qualified witness `W`. The current target `T` SHALL be the exact freshly qualified carrier/consumer revision for the requested evidence target; exact review and validation SHALL bind `T`. The proof MAY return `COMPLETE(T, W)` with `T != W` after legal same-Change evolution changes the target or accepted paths, provided Identity, complete Lineage from `W` to the qualified target, and Non-conflict remain proven. It MUST NOT require original desired bytes at a legal later `T`, `T == W`, or equality with an invocation-local apply target as durable completion predicates.

The accepted authorization revision `A`, declared carrier base `B`, actual prospective mutation parent/preimage `P`, and fresh default-branch revision `D` SHALL be qualified as separate identities and MAY differ. `A` records immutable accepted authorization; `B` is the declared carrier graph anchor; `P` is the actual tree a missing write would extend, including parent zero for an existing-carrier correction/reconciliation; `D` supplies fresh governance and authorization. Before each missing mutation, `expected_sha` SHALL match the requested path in actual prospective parent `P`, not merely in `A`, `B`, or `D`. A reconciliation with parents `[P, D]` and a declared base `B != P` SHALL retain that preimage guard, complete graph/compare/overlap checks, and unrelated-content preservation. A mutation preimage SHALL remain a stale-write authorization guard and MUST NOT be required to remain current as durable completion evidence after the accepted desired consequence is proven at `W`. Lineage SHALL qualify these separate revisions, witness/current target, PR base/head/merge ancestry, and application-built reconciliation lineage from complete actual Git evidence. Non-conflict SHALL reject duplicate or ambiguous carriers, wrong PR/ref/blob, requested-path overlap, broken or incomplete ancestry/compare evidence, unrelated overwritten content, and contradictory repository observations.

Application/apply-side already-complete checks, materialization observation/postcondition, fresh interruption recovery, and consequence completion classification SHALL all consume that same proof owner. Existing exact-manifest, historical-ancestry, merged-witness, reconciliation, and replacement-carrier helpers MAY remain as proof primitives or witness finders, but MUST NOT independently define top-level completion. After any consequential mutation the application SHALL discard local success as authority, fresh-read repository state, and use the same proof; only fresh `COMPLETE` permits completion to proceed.

The existing application-completion owner SHALL reconstruct pending carrier work before selecting a producer continuation. It SHALL qualify one immutable accepted intent and the unique current necessary CarrierPlan from complete source request, application run/attempt, artifact identity/digest/content, plan correlation, and fresh repository evidence. It SHALL preserve current Human disposition, governance, Issue/Change/Role/Action, exact branch/ref/PR/head/base, commit parents/tree/manifest/content, actual preimage, lineage, overlap, and cardinality guards. A saved plan SHALL NOT grant semantic, successor, routing, or terminal authority to the external actuator.

When the canonical proof returns `COMPLETE(T, W)`, recovery SHALL execute zero duplicate materialization mutation and satisfy only missing qualified evidence, exact-target validation, or derived consequence. When a valid current plan exists and the exact physical effect remains missing under fresh authorization, a later fresh external boundary SHALL perform only that plan's allowed non-force operation. The owner SHALL reconstruct a producer only when necessary plan absence or invalidation requiring a legal current reconstruction is proven; an unconsumed valid plan alone MUST NOT trigger another producer run. Stale, conflicting, duplicate, expired, superseded, incomplete, ambiguous, or contradictory evidence SHALL fail closed with its precise reason, never guessed selection, rewind, force-update, substitute carrier, or semantic replay. Safe disjoint evolution MAY qualify through the existing proof; unconditional revision equality SHALL NOT erase that existing capability.

Normal `CarrierRequired` SHALL remain an application invocation exit and normal external handoff, distinct from actual actuator rejection/error and unknown write response. Catchable external outcomes SHALL preserve exact source request/run/attempt/artifact/plan, operation/tool, target versions/preimage, platform-redacted raw observable error, separately justified classification, whether mutation is proven complete, proven not complete, or unknown, and the unfinished boundary. The legal repository-owned evidence/application path SHALL fresh-qualify and deduplicate this bounded evidence against immutable accepted intent and actual GitHub truth. It SHALL reuse canonical `EXECUTION_EXCEPTION` for exceptions without adding a lifecycle Action, ResultKind, state, queue, lease, cursor, retry registry, or progress database. External reports MUST NOT overwrite accepted intent, authorize routing/termination, or manufacture Human approval. A report's claimed success SHALL NOT substitute for the canonical postcondition.

After a lost or ambiguous write response, recovery SHALL observe/reconcile the exact target before any further write and SHALL fail closed when unique identity or completion cannot be proven. When reporting itself fails, the invocation SHALL retain the observable platform/run error and its evidence limits wherever a legal path remains, without claiming an absent GitHub record. A later wake SHALL recover solely from actual durable truth; uncatchable termination SHALL not produce fabricated prior observations. Exceptions SHALL obey existing disposition and unchanged-denial retry rules. No fixed numerical ceiling applies to new substantive recovery transitions; each later attempt SHALL require a new exact evidence digest, one uniquely linked predecessor, fresh authorization, and current canonical proof. An unchanged refusal or repeated evidence digest SHALL NOT be retried.

#### Scenario: Invalid typed worker input terminates a zero-write pre-ACCEPT failure

- GIVEN an exact source-bound native application run terminated before ACCEPT
- AND bot-authored evidence uniquely proves the same request and all terminated attempts, exact qualified source identity, absence of ACCEPT and zero consequential writes
- AND the immutable input deterministically fails the shared complete request contract, including the nested operation payload
- WHEN a later wake reads the same current `main` and the complete original evidence
- THEN the existing ingress reducer classifies the failed request as `TERMINAL_NO_ACCEPT`
- AND the next authorized semantic Action is eligible only in a separate fresh wake
- AND neither the failed request nor its effects are replayed

#### Scenario: Ambiguous failure cannot become terminal through parser inference

- GIVEN a failed application request whose native run, source, revision, attempt, correlation, HEAD, zero-write, ACCEPT absence, or complete evidence cannot be positively established
- OR the original worker input remains valid under the complete request contract
- WHEN the completion owner evaluates the current frontier
- THEN it does not infer deterministic malformed-input termination
- AND it reobserves missing evidence without mutation and escalates a reproducible internal defect only on qualified evidence

#### Scenario: Request emitter and consumer share the typed wire contract

- GIVEN a dispatch or application request is constructed for an authorized source
- WHEN its canonical renderer packages the exact request bytes
- THEN the corresponding production parser accepts the emitted bytes and typed fields
- AND the application emitter validates the embedded worker result before any canonical application envelope is admitted into Phase A
- AND malformed evidence, duplicate terminal blank lines and unknown or repeated fields fail preflight

#### Scenario: Actions owns production envelope construction for an external raw result

- GIVEN a newly created, uniquely source-qualified external `WORKER_RESULT` comment on the current runtime shard
- AND a current repository dispatch authorizes its Issue, Role, Action and Change
- WHEN the existing application Actions job processes that immutable comment
- THEN its production Python entrypoint validates the raw typed result and invokes the canonical renderer/parser before the existing Phase A
- AND the original comment remains the unique provenance and correlation without a second comment or workflow event
- AND only the existing Application may persist ACCEPT and subsequent effects

#### Scenario: Invalid raw input cannot publish a canonical application intent

- GIVEN an external raw-result comment has an invalid evidence reference, malformed JSON, wrong claimed source, changed provenance or incomplete current dispatch evidence
- WHEN the same production Actions job attempts to form the application request
- THEN the canonical typed preflight rejects it before ACCEPT or any consequential effect
- AND it never posts a synthetic `EFFECT_REQUEST`, retries an accepted intent or manufactures a successor
- AND a later fresh wake is governed solely by the existing terminal/unknown evidence reducer

#### Scenario: Recovery evidence remains named and replaceable

- GIVEN the application publishes recovery evidence as a direct JSON artifact

- WHEN the first upload, post-validation upload, or a later workflow attempt publishes that evidence

- THEN the uploaded file basename and configured artifact name both equal `application-recovery-evidence`

- AND every upload permits replacement while preserving one exact current run/attempt/job artifact

- AND the consumer parses and digest-checks the same direct JSON bytes

- AND missing, duplicate, stale, or mismatched artifact evidence fails closed

#### Scenario: Valid pending plan selects the consumer rather than the producer

- GIVEN one accepted current intent has one fully qualified saved CarrierPlan and the canonical proof is `INCOMPLETE` solely because its external operation has not occurred
- WHEN a later fresh wake reconstructs pending application work
- THEN the repository exposes that exact plan for fresh qualification and external actuation
- AND it does not rerun semantic work or rerun the producer merely to regenerate that saved plan
- AND only a still later fresh application boundary proves the consequence and performs missing validation or handoff

#### Scenario: Completed effect and missing plan select different missing work

- GIVEN complete current evidence either proves the desired consequence or proves a necessary plan is absent
- WHEN application-completion selects recovery
- THEN proven completion permits only missing evidence, validation, or derived consequence with zero duplicate mutation
- AND proven plan absence permits only the existing owner's legally required reconstruction
- AND absent or incomplete observations alone do not prove either case

#### Scenario: Carrier qualification rejects ambiguous or conflicting plans

- GIVEN a plan has stale/expired/superseded identity, overlap, wrong content/lineage, duplicate current ownership, wrong request/run/attempt/artifact digest, or incomplete observations
- WHEN the current repository-owned boundary qualifies it
- THEN it records the precise fail-closed reason and performs zero connector mutation
- AND it does not force-update, rewind, choose a substitute carrier, or replay semantic intent

#### Scenario: External outcome evidence cannot grant completion authority

- GIVEN a qualified carrier operation returns explicit refusal, a catchable error, or an ambiguous response
- WHEN the invocation captures and reports its observable outcome
- THEN raw platform-redacted evidence and exact source/operation/version identity remain separate from classification and mutation status
- AND the repository-owned consumer qualifies and deduplicates that evidence without changing accepted intent
- AND only fresh canonical proof establishes completed mutation; the report cannot route or terminate work

#### Scenario: Write and evidence interruptions reconstruct only missing effects

- GIVEN execution interrupts before write, after successful write before response, before evidence persistence, or before/after continuation or validation
- WHEN a later fresh wake reconstructs actual durable GitHub truth
- THEN it identifies proven complete, proven missing, or unknown boundaries through the same owners
- AND completed writes, semantic results, and qualified evidence are not duplicated
- AND unknown writes receive read-only reconciliation before any new write

#### Scenario: Reporting denial preserves an explicit evidence limit

- GIVEN an observable external operation outcome exists and the legal result-reporting path returns a catchable rejection or error
- WHEN the invocation retains the remaining legal platform/run evidence
- THEN it records the observable reporting error and that repository persistence is unproven
- AND it does not fabricate a successful comment, approval, completion, or prior error
- AND later recovery uses actual GitHub truth rather than conversation memory

#### Scenario: Accepted application resumes without semantic replay

- GIVEN an `APPLICATION_DECISION: ACCEPTED` is durable for one exact request
- AND an interruption occurs after any requested effect, carrier, validation, formal-result, routing, terminal, or final-postcondition prefix
- WHEN a later process reconstructs the application
- THEN it uses the immutable accepted intent
- AND applies only missing idempotent effects
- AND persists no second semantic Action execution or independent completion truth

#### Scenario: Historical same-Action evidence does not poison the current frontier

- GIVEN the current formal qualifier reconstructs a later `A -> A` or `A -> B -> A` frontier
- AND an earlier accepted/rejected/aborted application has the same Role/Action
- WHEN application completion is qualified
- THEN the earlier occurrence remains historical
- AND it does not block the current frontier

#### Scenario: Terminal pre-accept noise does not compete by count

- GIVEN the current frontier has N independently observed terminal-no-accept or rejected ingress candidates
- AND no candidate has durable `APPLICATION_DECISION: ACCEPTED`
- WHEN application completion is qualified
- THEN the candidates are inert evidence rather than competing application owners
- AND N does not by itself produce ambiguity

#### Scenario: One live candidate wins over terminal noise

- GIVEN the current frontier has one live pre-accept candidate and any number of terminal-no-accept or rejected candidates
- WHEN application completion is qualified
- THEN application waits for that one live ingress
- AND it does not redispatch the semantic Action

#### Scenario: Accepted intent wins over terminal or rejected noise

- GIVEN one current-frontier candidate has durable `APPLICATION_DECISION: ACCEPTED`
- AND other candidates are terminal-no-accept or rejected
- WHEN application completion is qualified
- THEN only the immutable accepted intent owns continuation
- AND the noise does not create ambiguity or replay
#### Scenario: Apply postcondition accepts a valid disjoint first-carrier continuation

- GIVEN an accepted first-carrier intent was based on a default-branch revision that remains an ancestor of current main
- AND the intervening main paths are disjoint from the exact requested manifest
- AND the exact branch head, one-commit file set, content, Issue, Change, and PR on its original base are freshly observed
- WHEN application observes its materialization postcondition on current main
- THEN the canonical durable-consequence proof returns `COMPLETE` for the same accepted consequence
- AND apply-side and postcondition consumers reuse that result
- AND it does not reject solely because main advanced

#### Scenario: Branch-ref recovery emits only the missing PR carrier

- GIVEN accepted immutable first-carrier intent has an exact branch ref and content commit
- AND current main has advanced from the accepted base along a disjoint path
- AND no PR exists for that exact head on any base branch
- WHEN a later application invocation resumes the accepted intent
- THEN it emits one exact PR-create plan against current main using the existing head
- AND it creates no replacement commit, branch, or semantic result

#### Scenario: Unsafe first-carrier continuation fails closed

- GIVEN the original base is not an ancestor, paths overlap, source/Change identity changed, the head/content differs, PR discovery is incomplete, or any wrong/duplicate PR uses the branch head
- WHEN application observes or resumes the carrier
- THEN it rejects the continuation without creating or changing a branch or PR

#### Scenario: Restart recognizes an already completed consequence

- GIVEN accepted consequence evidence and its exact effect payload are durable
- AND a later process starts without access to state held only in the earlier process
- WHEN consequence completion observes the current carrier
- THEN it recognizes the exact already completed consequence from current repository evidence
- AND it preserves the existing source, correlation, qualification, validation, review, and successor gates
- AND it does not replay an already-completed effect

#### Scenario: Merged materialization is not converted into a replacement

- GIVEN an accepted materialization names one exact PR carrier
- AND that PR is closed and merged, its merge commit and recorded head are in current main
- AND the accepted base is an ancestor of the PR base
- AND one complete compare-history commit reachable from the recorded head contains every requested blob
- WHEN a later application process resumes or observes the materialization
- THEN the canonical proof returns the freshly qualified consumer target `T` together with the exact historical content witness `W`, which may differ from `T`
- AND it creates no same-Change replacement branch, commit, or PR
- AND later same-Change updates to those files do not erase the historical consequence
- AND missing, truncated, stale, or contradictory ancestry/content evidence fails closed

#### Scenario: Merged same-Change successor satisfies an older carrier intent

- GIVEN an accepted materialization names a historical PR carrier whose merge commit is in current main
- AND the accepted base is newer than that carrier's recorded PR base
- AND one complete compare-history commit from the accepted base to current main contains every requested blob
- AND the historical carrier merge commit is an ancestor of that exact materialization commit
- WHEN a later application process resumes or observes the materialization
- THEN it returns `COMPLETE(T, W)` with that exact historical materialization revision as immutable witness `W` and the freshly qualified consumer revision as target `T`
- AND it creates no replacement branch, commit, or PR
- AND missing, truncated, stale, or contradictory ancestry/content evidence fails closed

#### Scenario: Accepted application resumes across an uncorrelated legacy result

- GIVEN one immutable accepted application intent exactly matches the current open Issue, Change, Role, and Action
- AND an earlier invocation made an application-owned effect durable but left only an uncorrelated legacy result before the formal frontier became unqualifiable
- AND the current-state observer finds the one exact application run and its one `apply` job
- WHEN a fresh bridge invocation checks application completion
- THEN it resumes only that accepted application job through the existing accepted-intent owner
- AND the uncorrelated result does not qualify a formal consequence or authorize a successor
- AND the application still performs fresh authorization and exact postcondition checks before any remaining mutation
- AND semantic work is not repeated

#### Scenario: A later run attempt does not permanently block bounded recovery

- GIVEN one immutable accepted application intent still matches the current open Issue, Change, Role, and Action
- AND its completed request-bound application run reports `run_attempt > 1`
- AND qualified durable evidence proves a specific incomplete effect, no unresolved write ambiguity, and remaining recovery capacity
- WHEN a fresh bridge invocation checks application completion
- THEN it does not rerun that same completed run/job
- AND it MAY emit only the existing `APPLICATION_CONTINUATION` for a new fresh run bound to the same intent and exact evidence
- AND semantic work is not replayed and fresh authorization/preconditions remain mandatory

#### Scenario: Ambiguous accepted-application recovery remains fail closed

- GIVEN the current source/Change differs, more than one accepted intent or application run/job matches, authorization is stale, or required evidence is incomplete
- WHEN a fresh bridge invocation checks application completion
- THEN it does not resume or select any guessed application job
- AND it does not qualify the uncorrelated result or derive a successor
- AND the existing fail-closed or ambiguous classification is preserved

#### Scenario: Apply and fresh observation have one completion meaning

- GIVEN repository application legally produces fresh state `S'` for accepted materialization intent `I`
- WHEN a new process evaluates the canonical durable-consequence proof using only fresh GitHub truth
- THEN it returns `COMPLETE` for that same consequence
- AND no apply-side, postcondition, recovery, or classifier-specific positive rule can disagree

#### Scenario: Completion survives safe repository evolution

- GIVEN the canonical proof has returned `COMPLETE` for an accepted materialized consequence
- AND current repository state later undergoes a disjoint default-branch advance, legal application reconciliation, legal merge, or legal same-Change descendant
- WHEN the consequence is freshly proven again
- THEN it remains `COMPLETE` when Identity, Content, Lineage, and Non-conflict still hold
- AND it does not become `INCOMPLETE` merely because the Git topology shape changed

#### Scenario: Mutation preimage is not durable completion evidence

- GIVEN an accepted materialization was authorized against one exact preimage `expected_sha`
- AND the desired accepted blob/content identities are now durably present in a qualified witness
- AND legal later evolution means the original preimage is no longer current
- WHEN the canonical proof evaluates the consequence
- THEN the absent old preimage does not by itself make the consequence `INCOMPLETE`
- AND content and lineage are proven from the accepted desired identities and fresh GitHub graph evidence

#### Scenario: Contradictory or incomplete proof remains fail closed

- GIVEN the candidate evidence has a wrong blob, wrong PR/ref, duplicate or ambiguous carrier, requested-path overlap, broken ancestry, incomplete compare evidence, unrelated overwritten content, or another contradiction
- WHEN any completion consumer evaluates the materialized consequence
- THEN the canonical proof returns `CONTRADICTORY` or otherwise fails closed
- AND no topology-specific fallback manufactures `COMPLETE` or authorizes a mutation

#### Scenario: Interruption reconstruction uses the same proof

- GIVEN execution interrupts after any durable boundary including accepted decision, blob/tree/content commit, branch/ref, PR carrier, CarrierRequired exit, validation, formal result, merge, successor routing, terminal transition, or final postcondition
- WHEN a later process resumes from fresh repository truth
- THEN it reconstructs materialized-consequence completion through the same canonical proof
- AND it does not depend on invocation-local memory or replay completed semantic work

#### Scenario: Legal same-Change correction separates current target from immutable witness

- GIVEN accepted desired content is proven at immutable witness `W`
- AND a qualified legal same-Change descendant `T` changes one accepted path while preserving complete lineage and non-conflict
- WHEN a fresh consumer proves the older accepted materialized consequence
- THEN the canonical proof returns `COMPLETE(T, W)` with `T != W` and no materialization replay
- AND exact-head review and validation consume `T`, not the historical witness or invocation-local target
- AND wrong Issue/Change/carrier identity, broken descendant lineage, incomplete compare evidence, or conflicting evolution fails closed

#### Scenario: Existing-carrier mutation guards its actual parent rather than declared base

- GIVEN accepted authorization revision `A`, declared carrier base `B`, fresh main `D`, and actual current PR-head prospective parent `P` are separately qualified
- AND `A` or `B` differs from `P`, as in the existing #353 correction or a reconciliation with parents `[P, D]`
- WHEN the application plans a genuinely missing materialization write under fresh current authorization
- THEN each `expected_sha` must match the requested path in `P`, with complete lineage, overlap, cardinality, and unrelated-content guards
- AND a preimage that matches only `A`, `B`, or `D` but differs in `P` rejects the write
- AND after accepted desired content is proven at a qualified witness, the obsolete preimage need not remain current

#### Scenario: Settled validation failure releases the current candidate without replay

- GIVEN R1 has an immutable ACCEPTED record, a qualified exact mechanical FAIL, settled writes, and no committed Formal Result
- WHEN Dispatch reconstructs ownership after interruption and Phase A receives a corrected R2 for the same Action
- THEN R1 remains historical and owns no further writes or completion
- AND only a uniquely qualified fresh candidate can acquire new effect authority
- AND repeated settled FAIL followed by exact PASS yields one Formal Result and derived successor

#### Scenario: Unsettled or competing candidates retain ownership protection

- GIVEN a candidate has pending or unqualified validation, unsettled writes, or competing current ingress
- WHEN Dispatch and Phase A reconstruct the current occurrence
- THEN no competing correction gains effect or completion authority
- AND a committed Formal Result is reconciled through its existing postconditions

### Requirement: One Scheduled Task wake executes exactly one Action

Each normal Scheduled Task wake SHALL fresh-dispatch exactly one repository-authorized Action, load the Role and Skill derived from that Action, execute that Action, return structured result/evidence, apply the necessary repository effects, observe postconditions, persist the unique derived successor or terminal state when the formal consequence completes, and exit at the governed boundary. Development-only materialization may end at a real bounded asynchronous wait without formal result or routing change. A successor Action SHALL execute only on a later wake after fresh dispatch, even when it maps to the same Role.

A normal wake remains exactly-one-Action. When its exact dispatch artifact is `NO_WORK`, the external bootstrap MAY invoke one bounded Lead idle semantic mode as a separate non-Action boundary after the normal dispatch exits. That handoff MUST NOT create an Action or same-wake successor. Any admitted candidate is consumed only by a later fresh normal dispatch.

The Action's primary execution unit SHALL remain a bounded verified slice: Reconstruct -> RED exact gap/blocker -> GREEN legal correction -> VERIFY exact postcondition/revision/gate -> durable checkpoint. An implementation slice MAY span one or more development commits, native CI runs and wakes under the development/completion contract without changing Action or creating a new formal completion result. An intermediate file write, API call, commit, Actions run, or first nonterminal observation MUST NOT by itself complete the slice or justify voluntary Exit. Continue immediately actionable work within current authority and bounded opportunity; an actual external asynchronous wait or exhausted execution opportunity permits later fresh reconstruction without pretending the slice completed. Decompose genuinely oversized delivery at meaningful safe boundaries, not merely because CI spans wakes. Other Actions retain their applicable work-conserving exit contract.

The wake MUST NOT require same-role continuation, cross-role barriers, invocation-role comparison, a continuation cursor, a fresh-worker chain, a public recovery mode, or a separate normal transfer journal. Bounded async observation and at-least-once reconstruction remain safety capabilities, not new routing state.

#### Scenario: Same-role successor waits

- GIVEN Lead completes one Action and application persists a legal next Lead Action
- WHEN the current wake reaches its postcondition
- THEN it exits
- AND the next Lead Action runs only after a later fresh dispatch

#### Scenario: Cross-role successor waits

- GIVEN Executor returns a valid result whose derived successor is Lead-owned
- WHEN application observes the new Action
- THEN the current wake exits
- AND no cross-role journal or wake barrier is required
- AND a later wake derives Lead from the successor Action

#### Scenario: Intermediate success is not completion

- GIVEN the selected Action has only completed an intermediate write or first external run observation
- WHEN the slice is evaluated
- THEN it is not complete
- AND the Action continues only while its source authority and safe execution opportunity remain current

#### Scenario: NO_WORK is a non-Action idle handoff

- GIVEN the exact normal dispatch result is `NO_WORK`
- WHEN the bootstrap invokes bounded idle semantics
- THEN no `Action.IDLE_*`, `action:idle-*`, idle transition, or normal successor is created
- AND the normal Action-only selector remains unchanged
- AND a later wake performs any canonical Action execution

#### Scenario: Idle admission hands back to normal dispatch

- GIVEN bounded idle semantics have durably admitted `Change: unset + action:explore-change`
- WHEN a later fresh normal wake reconstructs repository state
- THEN normal dispatch authorizes ordinary `Lead / explore-change`
- AND the idle invocation does not execute or select that Action

#### Scenario: Implementation CI spans wakes

- GIVEN the first incomplete implementation slice has a durably materialized development revision and native CI is pending
- WHEN bounded same-invocation observation opportunity is exhausted
- THEN the wake may yield without claiming slice completion or changing routing
- AND a later fresh dispatch or qualified continuation reconstructs the same slice from exact evidence
- AND immediately actionable work is not voluntarily abandoned.

### Requirement: Executor persists task completion at verified vertical-slice checkpoints

Executor SHALL treat OpenSpec task checkboxes as durable completion evidence rather than fine-grained live progress state.

For each approved vertical feature slice, after that slice's required `VERIFY` succeeds, Executor SHALL persist completion markers for every task in that slice whose completion criteria are satisfied before starting the next slice or handing off from `implement-change`.

Executor MUST NOT defer completed slice markers until the end of the entire OpenSpec change. Development commits MUST preserve incomplete task markers. When marker persistence changes HEAD, the resulting exact HEAD MUST satisfy applicable required gates before the slice checkpoint and formal result; a previous revision's PASS does not transfer.

The workflow MUST NOT require a dedicated commit for each individual checkbox. Task-marker updates SHOULD be committed together with the corresponding implementation checkpoint when practical.

If execution is interrupted during the current incomplete or unverified slice, that slice's markers MAY remain unpersisted; recovery SHALL reconstruct actual code, test, and task state, while markers from previously verified slices remain durable.

#### Scenario: Verified slice reaches its implementation checkpoint

- GIVEN Executor has completed a vertical slice through its required `VERIFY`
- AND the slice's task completion criteria are satisfied
- WHEN Executor prepares to begin the next slice or hand off
- THEN Executor persists the completed task markers for that slice
- AND the marker update is normally included with the corresponding implementation checkpoint rather than deferred to the end of the whole change

#### Scenario: Individual task finishes before the slice is verified

- GIVEN work for one task inside the current vertical slice is complete
- AND the slice has not yet completed its required `VERIFY`
- WHEN Executor continues implementation
- THEN the workflow does not require a dedicated task-marker commit for that checkbox
- AND the slice remains the task-persistence checkpoint

#### Scenario: Run is interrupted during an active slice

- GIVEN previously verified slices have persisted task markers
- AND Executor is interrupted while the current slice is incomplete or unverified
- WHEN a later Executor run reconstructs implementation state
- THEN previously verified slice markers remain durable
- AND the current slice is reconstructed from repository, test, and task reality without treating missing current-slice markers as proof that no work exists

### Requirement: Exact-R validation is gate-derived and preserves checkout proof

Whenever an approved gate requires strict OpenSpec validation for revision R, accepted evidence SHALL prove target revision R, validator checkout HEAD == R before validation, qualified pinned OpenSpec compatibility, and strict validation PASS. Eligibility SHALL be derived from the governed gate/artifact requirement and MUST NOT be restricted by a Propose-only or source-role/action whitelist. An already-current correct target MUST be validated without a dummy rewrite. Stale CI, run.head_sha without checkout proof, manual approval, connector bypass, or another model wake MUST NOT satisfy the gate.

For a governed active Task artifact, the exact mechanical gate SHALL include repository-specific Task Contract validation alongside native strict OpenSpec validation. Each actual task checkbox SHALL be consumable by the existing runtime slice/checkpoint contract, with a unique stable supported Task ID, membership in a recognized nonempty vertical slice, and no silently skipped malformed, duplicate or unassigned task. CI and runtime SHALL consume one shared executable parser/validation owner; a competing grammar, separate runner or LLM-only check MUST NOT substitute. The repository authoring contract SHALL declare the applicable Task/Slice convention. A legitimate partial authoring stage without tasks.md MAY proceed under its applicable gate, but any present governed tasks artifact SHALL be checked in full and a missing required artifact MUST NOT satisfy final readiness. Archived historical artifacts and terminal results SHALL NOT be retroactively revalidated as active tasks solely by activation of this requirement.

Existing applicable CI and Application-owned exact validation entry points SHALL consume the same mechanical contract against R; applicable archive checks SHALL preserve this contract for active tasks without changing historical archives. A missing or failed applicable component SHALL prevent mechanical completion, READY and successor effects; a native strict PASS alone MUST NOT certify the complete gate. Evidence SHALL identify the exact checkout, qualified validation components, run/attempt and verdict, with actionable failure diagnostics. Qualified ordinary mechanical FAIL SHALL follow the existing same-Action correction contract, not constitute a mutation Recovery obligation by itself. Mechanical PASS SHALL remain distinct from semantic acceptance. Current default-branch authority and independent review SHALL remain intact during rollout.

#### Scenario: Resolve validates its current head

- GIVEN Lead / resolve-question materially revises OpenSpec artifacts on the current PR head R
- WHEN the exact validation resource is requested
- THEN it validates R without a dummy mutation
- AND the evidence proves checkout HEAD == R and strict PASS

#### Scenario: Native Strict PASS does not certify an invalid Task artifact

- GIVEN native strict OpenSpec validation passes at exact R
- AND an applicable tasks.md contains an unnumbered, duplicate, unassigned or otherwise unconsumable actual task checkbox, including one mixed with valid tasks
- WHEN the existing mechanical validation gate evaluates R
- THEN the shared parser rejects the artifact with a diagnostic and the gate fails
- AND Application does not emit READY or advance routing on that verdict
- AND the owning Action may correct the candidate under the existing normal failure contract

#### Scenario: Valid task contract is shared across CI and checkpoint

- GIVEN a complete governed tasks.md has uniquely identified tasks in valid nonempty slices at exact R
- WHEN applicable CI and runtime checkpoint consumers evaluate its task structure
- THEN they consume the same executable validation owner and agree on the task identities and slices
- AND a marker-only revision receives its own applicable exact gate without changing the separate semantic review applicability or weakening the exact marker-delta contract

#### Scenario: Partial authoring and historical archive remain distinct

- GIVEN a legal partial authoring boundary before tasks.md is required, or a historical archived Change
- WHEN the applicable mechanical gate runs
- THEN it does not invent a required active Task artifact at that boundary or retrospectively validate historical archived tasks as active work
- AND any present governed active tasks artifact is validated in full
- AND final readiness cannot pass with a missing required tasks artifact
