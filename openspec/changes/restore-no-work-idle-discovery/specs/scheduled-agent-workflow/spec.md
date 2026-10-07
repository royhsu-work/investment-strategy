## MODIFIED Requirements

### Requirement: Lead idle advisory and discovery mode is bounded and non-disruptive

Lead SHALL keep idle discovery/advisory behavior bounded and subordinate to existing workflow work.

Lead may enter idle discovery only when no formal active or terminal-pending workflow requires advancement, no already eligible pre-activation work should be selected first, and no unresolved orphan/governance evidence requires diagnosis. Reviewer and Executor remain silent when they have no eligible workflow work.

An exact completed run-scoped dispatch result with disposition `NO_WORK` is the only normal-runtime handoff that may invoke this idle mode. The handoff MUST identify one request comment, one successful bridge run, one immutable dispatch-result artifact, and the default-branch revision observed by that run. A disposition of `AUTHORIZE` or `FAIL_CLOSED` MUST NOT invoke idle mode. Idle mode is semantic execution, not a mapped Action; it MUST NOT alter normal Action-only dispatch.

When the idle boundary is reached, Lead MAY create an idle advisory Issue containing at most three current recommendations only if no other open `advisory:idle` Issue exists. An advisory Issue MUST NOT contain `agent:*` or `action:*` routing labels and is not itself a coordination workflow instance. If an open advisory remains without valid Human admission, later Lead runs SHALL no-op rather than create duplicate advisory noise.

When forming bounded advisory recommendations, Lead SHALL consider relevant Issues created or materially active during the preceding seven days and recent durable workflow evidence for Skill-maintenance opportunities such as repeated Agent mistakes or recoverable failures, missing or obsolete action guidance, unnecessary Skill complexity, and materially duplicated Skill guidance. A Skill-maintenance recommendation remains diagnostic/advisory only: it MUST NOT directly mutate governed Skill behavior, bypass Human admission, or create a second maintenance workflow.

One idle invocation MAY instead autonomously materialize at most one valid repository-authorized Formal Explore candidate under the admission requirement above.
The bounded idle result MAY be no-finding, advisory-only, or one admission candidate. Only the repository-owned application admission boundary may materialize a candidate. Before any consequential candidate mutation, that boundary MUST fresh-reconstruct the exact `NO_WORK` handoff and current normal dispatch; it MUST perform no mutation when current dispatch is `AUTHORIZE` or `FAIL_CLOSED`. A successful candidate admission MUST leave the existing canonical `Change: unset + action:explore-change` tuple observable so a later normal wake, rather than idle mode, owns the workflow. Before creating that candidate, Lead MUST deduplicate against existing open or reconstructably unresolved Issues and required-deferred trackers.

An advisory-only result SHALL use a typed advisory candidate distinct from a Formal Explore candidate. Its repository-owned admission boundary MUST fresh-reconstruct the same exact `NO_WORK` evidence and current normal dispatch, create at most one open Issue with exactly `advisory:idle`, preserve the bounded recommendation body and source markers, and carry no `Change:` line, `action:*` label, or `agent:*` label. The candidate SHALL contain one through three recommendations. All-state correlation reconciliation MUST treat one complete open advisory as already admitted, and a closed, malformed, contradictory, or multiply correlated advisory as ambiguous and non-replaceable. An unrelated existing open `advisory:idle` Issue suppresses another advisory. Advisory admission is diagnostic only and does not enter normal Action workflow; only a later Formal Explore admission can hand back the canonical `Change: unset + action:explore-change` tuple.

Idle discovery SHALL use materiality rather than style preference. Repeated materially similar responsibility/knowledge/workaround evidence MAY use Rule-of-Three as sufficient investigation evidence; a clear single-instance structural hazard such as dual authority, circular ownership, dead abstraction, or a known-always-failing normal workflow step MAY also satisfy the threshold when concrete cost/risk/friction and bounded ownership are demonstrated.

Idle discovery MUST NOT introduce a scan cursor, TTL coverage registry, lease, heartbeat, progress counter, global priority score, hidden backlog state, or requirement for exhaustive repository coverage merely to remember what was inspected previously.

#### Scenario: Existing idle advisory has no Human decision

- GIVEN one open `advisory:idle` Issue exists
- AND no valid Human admission has occurred
- WHEN Lead runs while workflow is otherwise idle
- THEN Lead does not create another advisory Issue
- AND does not repeat the same recommendations as new workflow noise

#### Scenario: Recent workflow evidence suggests a Skill improvement

- GIVEN workflow execution is otherwise idle
- AND recent durable evidence shows a repeated action mistake or missing/obsolete Skill guidance
- WHEN Lead forms an eligible bounded idle advisory
- THEN Lead may recommend the narrowest Skill-maintenance change supported by that evidence
- AND the recommendation does not itself modify the Skill or create a parallel maintenance workflow
- AND any governed behavior change still requires normal Human-admitted/OpenSpec lifecycle

#### Scenario: Existing pre-activation work prevents autonomous materialization

- GIVEN no formal active workflow exists
- AND an eligible queued pre-activation Issue already exists
- WHEN Lead wakes
- THEN Lead advances the deterministic pre-activation winner before idle discovery
- AND does not create a new autonomous Explore candidate first

#### Scenario: One idle invocation creates at most one candidate

- GIVEN Lead reaches the idle-discovery boundary
- AND multiple material candidate problems are observed
- WHEN Lead chooses to materialize repository-authorized Formal Explore work
- THEN at most one new candidate Issue is created in that invocation
- AND no global priority/scoring framework is introduced to rank the remaining observations

#### Scenario: No material finding is a valid idle result

- GIVEN Lead performs bounded idle discovery
- AND no candidate meets repository-authority/materiality requirements
- WHEN the invocation completes
- THEN no workflow mutation is required
- AND the run does not create repository noise merely to report that nothing material was found

#### Scenario: Bounded advisory admission is non-routing and all-state deduplicated

- GIVEN exact `NO_WORK` remains current
- AND Lead returns one advisory candidate containing no more than three recommendations
- AND no open `advisory:idle` Issue exists
- WHEN the repository-owned admission boundary evaluates the candidate
- THEN it creates at most one Issue with exactly `advisory:idle`
- AND the Issue has no `Change:` line, `action:*` label, or `agent:*` label
- AND the body contains the exact admission correlation and source markers
- AND a later retry reconstructs all Issue states before deciding whether the advisory is already admitted

#### Scenario: Closed or contradictory advisory evidence blocks replacement

- GIVEN a candidate's exact correlation is found on a closed, malformed, or contradictory Issue
- WHEN the advisory admission boundary reconciles the repository
- THEN it returns an ambiguous/fail-closed result
- AND it does not create a replacement advisory Issue

#### Scenario: Existing open advisory suppresses advisory noise

- GIVEN one unrelated open `advisory:idle` Issue exists without a valid Human admission
- WHEN Lead returns another bounded advisory candidate
- THEN the admission boundary performs no create
- AND it returns the existing advisory as the durable suppression evidence

#### Scenario: Exact AUTHORIZE does not enter idle mode

- GIVEN the fresh normal dispatcher returns `AUTHORIZE`
- WHEN the Scheduled Task bootstrap evaluates the machine dispatch result
- THEN it invokes no idle semantic mode
- AND it executes only the authorized normal Action

#### Scenario: Exact FAIL_CLOSED does not enter idle mode

- GIVEN the fresh normal dispatcher returns `FAIL_CLOSED`
- WHEN the Scheduled Task bootstrap evaluates the machine dispatch result
- THEN it invokes no idle semantic mode
- AND it performs no idle workflow mutation

#### Scenario: Exact NO_WORK reaches bounded Lead idle semantics

- GIVEN the bridge completed one successful run-scoped dispatch for the current default-branch revision
- AND its exact artifact has disposition `NO_WORK`
- AND no later normal dispatch evidence supersedes that handoff
- WHEN the bootstrap invokes idle mode
- THEN Lead performs one bounded semantic discovery invocation
- AND the invocation is not represented as an Action, routing label, transition, queue item, or lifecycle state

#### Scenario: Normal work wins idle reauthorization

- GIVEN an idle result proposes one consequential admission
- AND a fresh normal dispatch immediately before mutation returns `AUTHORIZE` or `FAIL_CLOSED`
- WHEN the application evaluates the admission
- THEN it performs no idle workflow mutation
- AND the normal or fail-closed dispatch result remains authoritative

#### Scenario: Existing candidate admission is routing-complete

- GIVEN idle semantics identify one existing equivalent open candidate
- AND fresh normal dispatch still returns exact `NO_WORK`
- WHEN the application admits that candidate
- THEN it preserves unrelated Issue body and labels
- AND the fresh postcondition contains `Change: unset` and exactly one `action:explore-change`
- AND no duplicate Issue is created

#### Scenario: New candidate admission is routing-complete

- GIVEN idle semantics identify one material problem with reconstructable independent source evidence
- AND fresh normal dispatch still returns exact `NO_WORK`
- WHEN the application creates the candidate
- THEN the one logical creation includes `Change: unset` and exactly one `action:explore-change`
- AND fresh observation verifies the complete tuple before admission is reported

#### Scenario: Ambiguous idle write fails closed

- GIVEN an idle create or update response is lost or otherwise ambiguous
- WHEN a later invocation reconciles authoritative GitHub state
- THEN it reuses one uniquely identifiable complete candidate if and only if that consequence is provable
- AND it performs no blind replacement create
- AND it fails closed when uniqueness or the complete tuple cannot be proved

### Requirement: Dynamic dispatch tolerates overlapping wakes without hidden ownership state

Workflow-dynamic dispatch SHALL remain at-least-once and MUST NOT rely on Scheduled Tasks to provide mutual exclusion.

Overlapping wakes SHALL remain safe through durable reconstruction, idempotency where practical, revision/precondition-aware unsafe mutations, first-valid-write-wins where applicable, and stale-run termination. The workflow MUST NOT add lock, claim, lease, heartbeat, retry counter, hidden sequence, or `status:in-progress` state solely to serialize dispatcher runs.

Overlapping `NO_WORK` idle wakes MAY both perform bounded semantic discovery, but any consequential idle admission MUST use only a minimal non-durable serialization boundary and MUST fresh-recompute normal dispatch inside that boundary. The first complete canonical admission makes later overlapping requests stale through ordinary current routing; no idle-specific ownership record is permitted.

#### Scenario: Two wakes observe the same active tuple

- GIVEN two wakes reconstruct the same active workflow and routing tuple concurrently
- WHEN both dispatch the same role/action
- THEN neither assumes single-flight execution
- AND each action re-evaluates durable preconditions before unsafe mutation
- AND a run that becomes stale stops rather than overwriting newer durable state

#### Scenario: Two overlapping idle wakes admit at most one candidate

- GIVEN two completed `NO_WORK` wakes invoke bounded Lead idle semantics concurrently
- AND both identify the same material problem
- WHEN their admission boundaries execute
- THEN at most one complete `Change: unset + action:explore-change` candidate is admitted
- AND the other request observes current normal work or an existing equivalent candidate and performs no duplicate mutation
- AND no durable lock, lease, cursor, heartbeat, or idle registry is created

### Requirement: One Scheduled Task wake executes exactly one Action

Each normal Scheduled Task wake SHALL fresh-dispatch exactly one repository-authorized Action, load the Role and Skill derived from that Action, execute that Action, return structured result/evidence, apply the necessary repository effects, observe postconditions, persist the unique derived successor or terminal state, and exit. A successor Action SHALL execute only on a later wake after fresh dispatch, even when it maps to the same Role.

A normal wake remains exactly-one-Action. When its exact dispatch artifact is `NO_WORK`, the external bootstrap MAY invoke one bounded Lead idle semantic mode as a separate non-Action boundary after the normal dispatch exits. That handoff MUST NOT create an Action or same-wake successor. Any admitted candidate is consumed only by a later fresh normal dispatch.

The Action's primary execution unit SHALL be one bounded verified slice: Reconstruct -> RED exact gap/blocker -> GREEN legal correction -> VERIFY exact postcondition/revision/gate -> durable checkpoint. An intermediate file write, API call, commit, Actions run, or first nonterminal observation MUST NOT by itself complete the slice or authorize Exit. A slice that cannot reasonably reach VERIFY in one normal invocation SHALL be split before execution at a meaningful safe boundary.

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

### Requirement: Application performs exact effects and ordinary idempotent reconciliation

Repository application SHALL fresh-reauthorize the exact source Action, Change, Issue, PR/head, revision, Human/review/gate evidence, and effect-specific preconditions before every consequential mutation. It SHALL apply only necessary exact effects, preserve unrelated content, and fresh-observe each postcondition. Stale, replayed, ambiguous, contradictory, incomplete, or provenance-incomplete evidence MUST fail closed.

For an idle-derived admission, application SHALL accept only a typed request bound to the exact completed `NO_WORK` dispatch artifact, source request/run identity, observed default-branch revision, and reconstructable Lead evidence. It MUST fresh-read the current default branch, current normal dispatch, and the exact existing or candidate Issue immediately before the one necessary create/update mutation. Existing-candidate update MUST preserve unrelated content and labels; new Formal Explore creation MUST form the complete pre-activation tuple in that one logical boundary; advisory creation MUST form only the exact non-routing advisory body and label set. The application MUST fresh-observe the tuple after mutation and MUST reconcile an ambiguous result read-only before any retry. Idle requests do not create an Action, normal routing dimension, accepted-intent registry, queue, cursor, lease, heartbeat, or recovery workflow.

If an earlier invocation already made a required mutation durable, recovery MAY complete only still-required non-contradictory effects. It MUST NOT replay semantic work merely to recreate a missing record, and MUST NOT rewind current routing or lifecycle state when valid descendant evidence proves the earlier transition was consumed. Recovery is ordinary idempotent application/reconciliation; it is not another Action, lifecycle state, transaction framework, retry/lock/lease system, or public protocol. Deterministic rejections identify the exact failed guard class and relevant expected/observed evidence machine-readably.

#### Scenario: Durable effect is not replayed

- GIVEN a result comment or routing change is already durable
- AND a later invocation observes the remaining required effect
- WHEN application reconciles the state
- THEN it performs only the missing non-contradictory effect
- AND it does not replay the semantic Action or rewind a consumed descendant

#### Scenario: Contradictory evidence fails closed

- GIVEN current Issue, PR, revision, or provenance evidence is contradictory
- WHEN application evaluates a consequential effect
- THEN it returns the exact failed guard evidence
- AND it applies no guessed mutation

#### Scenario: Stale idle source cannot mutate

- GIVEN an idle request cites a dispatch artifact or source revision that is no longer the current default-branch authority
- WHEN application reauthorizes the request
- THEN it performs no consequential mutation
- AND it returns a stale-source guard that identifies the observed and expected evidence

#### Scenario: Interruption before idle mutation leaves no partial state

- GIVEN idle semantic evaluation completes
- AND execution is interrupted before the application mutation
- WHEN a later invocation reconstructs current repository state
- THEN no partial workflow tuple is treated as an admission
- AND the later invocation may continue only from a fresh valid `NO_WORK` boundary

#### Scenario: Interruption after idle mutation does not duplicate

- GIVEN the application mutation succeeded
- AND execution stopped before its postcondition was locally recorded
- WHEN a later invocation observes the Issue and normal dispatch
- THEN it recognizes the complete canonical tuple if uniquely provable
- AND it creates no duplicate Issue and does not replay semantic discovery

### Requirement: Application consequence completion is reconstructable across interruption

The application bridge SHALL treat an `EFFECT_REQUEST` as an ingress candidate,
not as an accepted application. Each current-frontier candidate SHALL be
classified independently as exactly one of `ACCEPTED`, `LIVE_PREACCEPT`,
`TERMINAL_NO_ACCEPT`, `REJECTED`, or `INVALID/UNKNOWN` before reduction. A
missing or not-yet-visible Actions run is asynchronous observation evidence,
not terminal or rejected evidence; `TERMINAL_NO_ACCEPT` requires authoritative
terminal/non-mutation evidence from the exact application execution. The
reducer SHALL apply these rules: more than one `ACCEPTED` is ambiguous; one
`ACCEPTED` exclusively owns continuation and terminal/rejected noise does not
compete; zero accepted plus more than one live candidate is ambiguous; zero
accepted plus exactly one live candidate waits without semantic redispatch;
zero accepted plus only proven terminal-no-accept/rejected candidates returns
ownership to the semantic Action; and unknown or contradictory evidence fails
closed. N terminal or rejected candidates SHALL never become ambiguous merely
from raw count. Before any consequential effect, fresh application
authorization SHALL durably persist one exact `APPLICATION_DECISION: ACCEPTED`
bound to the request comment, source Issue, Role/Action, Change, authorization
revision, result, and immutable worker intent.

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
the same intent and semantic replay count remains zero.

For first-carrier materialization, the apply-side already-complete check, immediate postcondition, and later fresh observer SHALL use one canonical durable-consequence proof for exact Issue, Change, branch, head, PR, manifest/content identity, lineage, and non-conflict. A pending continuation MAY remain valid after default-branch advancement only when the same proof classifies the consequence `INCOMPLETE` rather than complete or contradictory and the immutable original base is its ancestor with all carrier paths disjoint from intervening changes. Existing stale, overlap, identity, cardinality, and ambiguity guards remain mandatory. When an exact accepted intent has the verified branch ref and content but no matching PR, recovery SHALL emit only the missing application-owned PR consequence against fresh current main after the canonical proof plus ancestry, disjointness, exact branch/head/content, and complete all-head PR cardinality checks. It SHALL NOT rerun semantic work, recreate the branch, move the ref, or blindly create a duplicate PR.

A fresh process SHALL reconstruct materialized-consequence completion from the existing `ConsequenceSpec.evidence_target` through the same canonical durable-consequence proof owner. It MUST NOT require invocation-local `_materialization_targets` to recognize an already durable consequence. Implementation-carrier qualification remains in its existing owner except where that owner supplies materialization proof primitives; it MUST NOT become a competing positive definition for the same materialized consequence. If an uncorrelated legacy result invalidates formal-frontier qualification while the exact source route remains current, recovery MAY resume only one accepted intent and its unique request-bound run/job after exact Issue/Change/Role/Action checks. For a completed request-bound run, `run_attempt` is GitHub-owned invocation evidence and is not the recovery budget. `run_attempt > 1` alone SHALL NOT permanently block recovery or authorize a rerun of that same run/job. A safe continuation MAY use the existing `APPLICATION_CONTINUATION` transport to start one fresh, separately identified run only after exact failure evidence, unique accepted intent/run/job, current authorization, and the bounded-recovery requirement below qualify it. Changed identity/routing, duplicate intent/run/job, or incomplete evidence SHALL fail closed. Existing correlation, formal qualification, source/frontier, carrier, validation, review, successor, and terminal gates remain in force.

The materialized durable consequence itself SHALL have exactly one authoritative positive proof definition. Given one accepted intent and fresh repository state, the proof owner SHALL return exactly one of `COMPLETE(target, witness)`, `INCOMPLETE`, or `CONTRADICTORY(reason)`. `COMPLETE` SHALL require coherent Identity, Content, Lineage, and Non-conflict evidence together. Git topology labels such as historical, replacement, merged, reconciled, or direct SHALL be treated only as evidence/witness shapes and MUST NOT create separate top-level positive completion semantics.

Identity SHALL include the exact repository, Issue, immutable Change, source Role/Action, intended PR/ref/branch, and unique carrier/cardinality. Content SHALL prove every accepted desired blob/content identity in the immutable qualified witness `W`. The current target `T` SHALL be the exact freshly qualified carrier/consumer revision for the requested evidence target; exact review and validation SHALL bind `T`. The proof MAY return `COMPLETE(T, W)` with `T != W` after legal same-Change evolution changes the target or accepted paths, provided Identity, complete Lineage from `W` to the qualified target, and Non-conflict remain proven. It MUST NOT require original desired bytes at a legal later `T`, `T == W`, or equality with an invocation-local apply target as durable completion predicates.

The accepted authorization revision `A`, declared carrier base `B`, actual prospective mutation parent/preimage `P`, and fresh default-branch revision `D` SHALL be qualified as separate identities and MAY differ. `A` records immutable accepted authorization; `B` is the declared carrier graph anchor; `P` is the actual tree a missing write would extend, including parent zero for an existing-carrier correction/reconciliation; `D` supplies fresh governance and authorization. Before each missing mutation, `expected_sha` SHALL match the requested path in actual prospective parent `P`, not merely in `A`, `B`, or `D`. A reconciliation with parents `[P, D]` and a declared base `B != P` SHALL retain that preimage guard, complete graph/compare/overlap checks, and unrelated-content preservation. A mutation preimage SHALL remain a stale-write authorization guard and MUST NOT be required to remain current as durable completion evidence after the accepted desired consequence is proven at `W`. Lineage SHALL qualify these separate revisions, witness/current target, PR base/head/merge ancestry, and application-built reconciliation lineage from complete actual Git evidence. Non-conflict SHALL reject duplicate or ambiguous carriers, wrong PR/ref/blob, requested-path overlap, broken or incomplete ancestry/compare evidence, unrelated overwritten content, and contradictory repository observations.

Application/apply-side already-complete checks, materialization observation/postcondition, fresh interruption recovery, and consequence completion classification SHALL all consume that same proof owner. Existing exact-manifest, historical-ancestry, merged-witness, reconciliation, and replacement-carrier helpers MAY remain as proof primitives or witness finders, but MUST NOT independently define top-level completion. After any consequential mutation the application SHALL discard local success as authority, fresh-read repository state, and use the same proof; only fresh `COMPLETE` permits completion to proceed.

The existing application-completion owner SHALL reconstruct pending carrier work before selecting a producer continuation. It SHALL qualify one immutable accepted intent and the unique current necessary CarrierPlan from complete source request, application run/attempt, artifact identity/digest/content, plan correlation, and fresh repository evidence. It SHALL preserve current Human disposition, governance, Issue/Change/Role/Action, exact branch/ref/PR/head/base, commit parents/tree/manifest/content, actual preimage, lineage, overlap, and cardinality guards. A saved plan SHALL NOT grant semantic, successor, routing, or terminal authority to the external actuator.

When the canonical proof returns `COMPLETE(T, W)`, recovery SHALL execute zero duplicate materialization mutation and satisfy only missing qualified evidence, exact-target validation, or derived consequence. When a valid current plan exists and the exact physical effect remains missing under fresh authorization, a later fresh external boundary SHALL perform only that plan's allowed non-force operation. The owner SHALL reconstruct a producer only when necessary plan absence or invalidation requiring a legal current reconstruction is proven; an unconsumed valid plan alone MUST NOT trigger another producer run. Stale, conflicting, duplicate, expired, superseded, incomplete, ambiguous, or contradictory evidence SHALL fail closed with its precise reason, never guessed selection, rewind, force-update, substitute carrier, or semantic replay. Safe disjoint evolution MAY qualify through the existing proof; unconditional revision equality SHALL NOT erase that existing capability.

Normal `CarrierRequired` SHALL remain an application invocation exit and normal external handoff, distinct from actual actuator rejection/error and unknown write response. Catchable external outcomes SHALL preserve exact source request/run/attempt/artifact/plan, operation/tool, target versions/preimage, platform-redacted raw observable error, separately justified classification, whether mutation is proven complete, proven not complete, or unknown, and the unfinished boundary. The legal repository-owned evidence/application path SHALL fresh-qualify and deduplicate this bounded evidence against immutable accepted intent and actual GitHub truth. It SHALL reuse canonical `EXECUTION_EXCEPTION` for exceptions without adding a lifecycle Action, ResultKind, state, queue, lease, cursor, retry registry, or progress database. External reports MUST NOT overwrite accepted intent, authorize routing/termination, or manufacture Human approval. A report's claimed success SHALL NOT substitute for the canonical postcondition.

After a lost or ambiguous write response, recovery SHALL observe/reconcile the exact target before any further write and SHALL fail closed when unique identity or completion cannot be proven. When reporting itself fails, the invocation SHALL retain the observable platform/run error and its evidence limits wherever a legal path remains, without claiming an absent GitHub record. A later wake SHALL recover solely from actual durable truth; uncatchable termination SHALL not produce fabricated prior observations. Exceptions SHALL obey existing disposition and unchanged-denial retry rules. No fixed numerical ceiling applies to new substantive recovery transitions; each later attempt SHALL require a new exact evidence digest, one uniquely linked predecessor, fresh authorization, and current canonical proof. An unchanged refusal or repeated evidence digest SHALL NOT be retried.

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

## ADDED Requirements

### Requirement: NO_WORK idle admission is typed, fresh, and bounded

The repository-owned idle boundary SHALL accept only a typed request bound to one completed,
successful `scheduled-agent-bridge.yml` run, its unexpired `dispatch-result.json` artifact id and
digest, the parsed artifact content, the exact request comment, and the checked-out default-branch
revision. In the current Scheduled Task environment, one candidate SHALL enter through a strictly
parsed `IDLE_ADMISSION_REQUEST` comment on the current daily runtime shard. That comment is only
trigger/staging evidence and MUST NOT become accepted intent, routing, workflow state, or mailbox
authority; repository application MUST fresh-reauthorize it before mutation. A no-finding result
MUST submit no request. The envelope MUST carry the exact `NO_WORK / no-routed-work` disposition. `AUTHORIZE`,
`FAIL_CLOSED`, incomplete observations, stale revisions, contradictory run/artifact identity, and
ambiguous artifacts MUST not invoke idle admission or mutate a repository Issue.

An idle candidate request SHALL contain no more than one no-finding, existing-target, or new-target
candidate. Immediately before every consequential write, the application MUST fresh-read the default
branch ref and reconstruct exact normal dispatch; only qualified `NO_WORK` permits the write. An
existing target SHALL preserve its complete body and all unrelated labels while producing exactly
one `action:explore-change` routing label and `Change: unset`. A new target SHALL be created in one
logical write with the complete candidate body, `Change: unset`, reconstructable source evidence, and
exactly one `action:explore-change` routing label. The application MUST fresh-observe the complete
tuple and reconcile an unknown write outcome by exact Issue identity or immutable admission
correlation across all Issue states before any later wake; it MUST never blindly replay a create or
update, including when a prior correlated Issue is closed.

The application carrier MAY use one non-durable concurrency group for idle admission. It MUST NOT
create an idle Action, transition, queue, cursor, lease, heartbeat, retry registry, or accepted-intent
record. After a complete tuple is observed, the next normal wake MUST own the ordinary
`Lead / explore-change` Action.

#### Scenario: Exact NO_WORK envelope reaches one bounded idle request

- GIVEN one successful bridge run has one unexpired `dispatch-result.json` artifact whose digest,
  request comment, run identity, and checked-out main revision agree
- AND the parsed artifact disposition is exactly `NO_WORK / no-routed-work`
- WHEN the external bootstrap submits one typed idle request
- THEN the repository application can evaluate one bounded candidate
- AND no Action, successor, or idle control state is created

#### Scenario: Normal work suppresses idle mutation

- GIVEN an idle request was derived from an earlier exact `NO_WORK` envelope
- AND fresh dispatch now returns `AUTHORIZE` or `FAIL_CLOSED`
- WHEN the application reaches the admission boundary
- THEN it performs no Issue create or update
- AND it fails closed without replaying Lead semantic work

#### Scenario: No finding is repository-silent

- GIVEN bounded Lead idle semantics return no candidate
- WHEN the bootstrap completes the wake
- THEN it submits no idle admission mutation
- AND no Issue comment, label, body, or routing state is created

#### Scenario: Existing candidate preserves unrelated Issue state

- GIVEN one fresh existing Issue target has no immutable Change and arbitrary unrelated body/labels
- AND fresh normal dispatch remains exact `NO_WORK`
- WHEN the idle application admits it
- THEN one Issue update establishes `Change: unset` and one `action:explore-change`
- AND every unrelated body byte and label remains present
- AND the next normal dispatch authorizes ordinary `Lead / explore-change`

#### Scenario: New candidate and ambiguous result are reconciled from GitHub truth

- GIVEN one bounded new candidate has exact source evidence and one immutable admission correlation
- AND fresh normal dispatch remains exact `NO_WORK`
- WHEN the application creates the candidate or loses the create response
- THEN it observes exactly one complete open Issue with `Change: unset` and one
  `action:explore-change`, or fails closed when zero/multiple contradictory matches remain
- AND it never blindly creates a replacement Issue

### Requirement: Unanswered Human escalation is a derived wait without repeated semantic ingress

When the current qualified formal frontier is an unanswered `HUMAN_DECISION_REQUIRED` whose repository-derived successor is the same `Lead / resolve-question`, a later Scheduled Task wake SHALL derive waiting from current repository evidence before invoking the semantic worker. If there is no newer qualifying Human decision and no material change to the authoritative evidence consumed by that question, the wake SHALL emit no new semantic `EFFECT_REQUEST`, formal result, routing mutation, retry record, cursor, lease, mailbox, or persisted waiting state.

The derived wait SHALL be invalidated by a newer qualifying Human decision or materially changed authoritative evidence. After invalidation, ordinary fresh dispatch and the mapped semantic Action SHALL resume. The repository MUST NOT generalize this rule into a cache of arbitrary `BLOCKED` outcomes or suppress evidence changes merely because Issue/Action identity is unchanged.

#### Scenario: Unchanged unanswered Human question is repository-silent

- GIVEN the qualified current frontier is `HUMAN_DECISION_REQUIRED → Lead / resolve-question`
- AND no newer qualifying Human decision exists
- AND the authoritative evidence relevant to the question is materially unchanged
- WHEN a later Scheduled Task wake reconstructs the same current frontier
- THEN it does not invoke the semantic `resolve-question` worker again
- AND it emits no new `EFFECT_REQUEST`, formal result, routing mutation, or persisted wait/retry state

#### Scenario: New Human or material evidence resumes execution

- GIVEN a prior wake was suppressed as an unchanged unanswered Human question
- AND a newer qualifying Human decision or materially changed authoritative evidence is now present
- WHEN the next Scheduled Task wake reconstructs current state
- THEN the derived wait no longer applies
- AND ordinary fresh dispatch may invoke the mapped `Lead / resolve-question` Action

### Requirement: Accepted-application rejection recovery is exact and evidence-deduplicated

Accepted intent `I`, materialization/effect plan `P`, optional externally executable CarrierPlan `C` (which may be absent), and execution attempt `R` SHALL remain distinct. A failed effect SHALL NOT rewrite or replace `I`. Before an effect-precondition rejection is reduced to a generic batch outcome, the existing application/evidence owner SHALL preserve the exact failed effect and ordinal, operation/target, expected and observed preimage, guard reason, canonical completion proof, effects already proven complete, mutation status (`complete`, `not-complete`, or `unknown`), and unfinished boundary. Evidence SHALL bind the immutable accepted-decision digest and exact request/run/attempt/artifact and any plan ids that exist, and SHALL explicitly represent an absent CarrierPlan rather than guessing one. It SHALL not contain credentials or fabricate unobserved platform errors.

Before any later write, recovery SHALL use current repository truth and fresh authorization. Unknown or lost write outcomes SHALL be reconciled read-only first. A complete canonical proof SHALL skip duplicate mutation. A stale/expired `P` or existing `C` MAY receive a `PLAN_SUPERSEDED` disposition only after its invalidation and already-completed effects are proven; this ends that plan's execution authority without changing `I`. A replacement `P` or `C` MAY be created only when the same accepted intent remains current and the canonical proof plus exact current preimages, lineage, authorization, and non-conflict checks prove the operation remains safe. Same-path overlap or an unresolvable expected/observed preimage conflict SHALL remain fail-closed with its exact blocker and the existing governed correction path; no automatic overwrite, force update, semantic replay, or guessed payload is allowed.

A `run_attempt > 1` value alone SHALL neither permanently block a safe continuation nor authorize rerunning its completed run/job. A continuation SHALL use the existing `APPLICATION_CONTINUATION` path and create a fresh run only after unique intent/current predecessor, current Issue/Change/Role/Action, exact evidence chain, fresh authorization, and a new qualified failure-evidence transition is proven. No new Action, ResultKind, retry registry, counter, queue, cursor, lease, or progress database is introduced.

The existing `APPLICATION_CONTINUATION` correlation SHALL be extended to bind the accepted-decision digest, one exact predecessor run/job/attempt and artifact id/digest, the structured rejection-evidence digest, and a stable causal-episode fingerprint. The per-transition correlation SHALL be deterministic from qualified evidence, not an arbitrary nonce; identical evidence SHALL map to the same correlation and at most one next continuation/run. Each new run SHALL have exactly one evidence-linked predecessor in one linear chain. Duplicate, branching, missing, or ambiguous continuation/run/artifact links SHALL fail closed. The stable episode fingerprint, which excludes run id, plan id, nonce, and date, SHALL preserve causal identity across distinct transition correlations without imposing a numeric attempt cap. Historical intent-only continuation comments do not qualify as new failure evidence. When a legacy attempt has only generic or incomplete failure evidence and a fresh canonical/safety proof cannot uniquely recover the remaining work and evidence chain, the owner SHALL return a specific evidence-incomplete blocker without emitting a continuation.



A substantive recovery transition SHALL be eligible without a fixed numerical attempt ceiling only when its failure-evidence digest is new within the same stable causal episode and its exact predecessor is unique. The recovery ordinal SHALL be derived from the complete artifact chain for audit and structural validation; it SHALL NOT be used as a retry budget. New run ids, plan ids, nonces, dates, or unrelated default-branch changes SHALL NOT qualify as new evidence. An unchanged explicit refusal or repeated evidence digest SHALL NOT be retried. Missing/ambiguous evidence or a failed evidence write SHALL produce a precise fail-closed blocker and reopening condition. Only a newly qualified evidence transition or a newly governed correction may reopen evaluation.

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
- THEN it records `PLAN_SUPERSEDED` for that exact plan and reports the path conflict and expected/observed preimage
- AND it performs no carrier or repository mutation
- AND a new plan requires the existing governed correction path

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
- AND if remaining work and attempt capacity are not uniquely provable, it returns an evidence-incomplete blocker
- AND it emits no new continuation and fabricates no guard reason

#### Scenario: New evidence continues after the former numeric threshold

- GIVEN one accepted intent has three substantive fresh recovery transitions for one unresolved causal episode
- AND a later run produces a new exact failure-evidence digest linked to the unique predecessor
- AND the current authorization and canonical proof still qualify the accepted intent and exact operation
- WHEN the recovery owner evaluates the new evidence
- THEN it may emit exactly one continuation for the new transition
- AND an unchanged refusal or repeated evidence digest still emits no continuation or mutation

- GIVEN one accepted intent has reached three substantive attempts for the same unresolved causal guard/path
- AND later wakes use a new transition correlation, request correlation, run id, plan id, or date but show no qualified causal repair
- WHEN the recovery owner evaluates the intent
- THEN it emits no further continuation or mutation
- AND it preserves the exact blocker and reopening condition

#### Scenario: An unchanged refusal is not retried

- GIVEN the last qualified attempt was explicitly refused by the same unchanged guard
- AND no qualified causal repair or governed correction exists
- WHEN a later scheduled wake evaluates the accepted intent
- THEN it performs no application rerun or semantic replay
- AND it returns the existing evidence-bound fail-closed disposition

### Requirement: Production idle acceptance follows legal formal termination

The #322 repository implementation SHALL complete its normal independent review, exact-head merge, governed finalize/archive, and legal terminal lifecycle before true production `NO_WORK` acceptance is required. While #322 remains open formal routed work, normal dispatch SHALL continue to prefer that work and MUST NOT fabricate `NO_WORK` for validation.

After #322 formal routing is legally gone, a later real Scheduled Task wake SHALL provide the production acceptance evidence for exact `NO_WORK` idle execution. Human-defined completion SHALL require this post-terminal evidence in addition to repository lifecycle completion. No special dispatcher exception, validation-only Action, temporary routing removal, or persisted validation-hold state may be introduced merely to manufacture the proof.

#### Scenario: Routed #322 prevents synthetic idle validation

- GIVEN #322 remains an open formal Issue with a current `action:*` route
- WHEN normal dispatch runs
- THEN that formal work remains eligible ahead of idle
- AND the system does not return synthetic `NO_WORK` merely to test idle behavior

#### Scenario: Post-terminal wake proves the parent outcome

- GIVEN the repository implementation has passed its governed merge/archive lifecycle
- AND #322 no longer contributes routed formal work
- WHEN a later real Scheduled Task wake receives exact `NO_WORK`
- THEN bounded Lead idle semantics execute through the typed production boundary
- AND no-finding is repository-silent or at most one safe advisory/Explore candidate is admitted
- AND if a Formal Explore is admitted, a still later ordinary Action-only wake owns `Lead / explore-change`
- AND only this lifecycle-plus-production evidence satisfies Human-defined completion

