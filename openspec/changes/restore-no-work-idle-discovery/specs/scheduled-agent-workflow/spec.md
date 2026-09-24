## MODIFIED Requirements

### Requirement: Lead idle advisory and discovery mode is bounded and non-disruptive

Lead SHALL keep idle discovery/advisory behavior bounded and subordinate to existing workflow work.

Lead may enter idle discovery only when no formal active or terminal-pending workflow requires advancement, no already eligible pre-activation work should be selected first, and no unresolved orphan/governance evidence requires diagnosis. Reviewer and Executor remain silent when they have no eligible workflow work.

An exact completed run-scoped dispatch result with disposition `NO_WORK` is the only normal-runtime handoff that may invoke this idle mode. The handoff MUST identify one request comment, one successful bridge run, one immutable dispatch-result artifact, and the default-branch revision observed by that run. A disposition of `AUTHORIZE` or `FAIL_CLOSED` MUST NOT invoke idle mode. Idle mode is semantic execution, not a mapped Action; it MUST NOT alter normal Action-only dispatch.

When the idle boundary is reached, Lead MAY create an idle advisory Issue containing at most three current recommendations only if no other open `advisory:idle` Issue exists. An advisory Issue MUST NOT contain `agent:*` or `action:*` routing labels and is not itself a coordination workflow instance. If an open advisory remains without valid Human admission, later Lead runs SHALL no-op rather than create duplicate advisory noise.

When forming bounded advisory recommendations, Lead SHALL consider relevant Issues created or materially active during the preceding seven days and recent durable workflow evidence for Skill-maintenance opportunities such as repeated Agent mistakes or recoverable failures, missing or obsolete action guidance, unnecessary Skill complexity, and materially duplicated Skill guidance. A Skill-maintenance recommendation remains diagnostic/advisory only: it MUST NOT directly mutate governed Skill behavior, bypass Human admission, or create a second maintenance workflow.

One idle invocation MAY instead autonomously materialize at most one valid repository-authorized Formal Explore candidate under the admission requirement above.
The bounded idle result MAY be no-finding, advisory-only, or one admission candidate. Only the repository-owned application admission boundary may materialize a candidate. Before any consequential candidate mutation, that boundary MUST fresh-reconstruct the exact `NO_WORK` handoff and current normal dispatch; it MUST perform no mutation when current dispatch is `AUTHORIZE` or `FAIL_CLOSED`. A successful candidate admission MUST leave the existing canonical `Change: unset + action:explore-change` tuple observable so a later normal wake, rather than idle mode, owns the workflow. Before creating that candidate, Lead MUST deduplicate against existing open or reconstructably unresolved Issues and required-deferred trackers.

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

For an idle-derived admission, application SHALL accept only a typed request bound to the exact completed `NO_WORK` dispatch artifact, source request/run identity, observed default-branch revision, and reconstructable Lead evidence. It MUST fresh-read the current default branch, current normal dispatch, and the exact existing or candidate Issue immediately before the one necessary create/update mutation. Existing-candidate update MUST preserve unrelated content and labels; new-candidate creation MUST form the complete pre-activation tuple in that one logical boundary. The application MUST fresh-observe the tuple after mutation and MUST reconcile an ambiguous result read-only before any retry. Idle requests do not create an Action, normal routing dimension, accepted-intent registry, queue, cursor, lease, heartbeat, or recovery workflow.

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

For first-carrier materialization, the apply result, immediate postcondition, and later fresh observer SHALL use one canonical positive materialization observation for exact Issue, Change, branch, head, PR, manifest, and content identity. A pending continuation MAY remain valid after default-branch advancement only when the immutable original base is its ancestor and all carrier paths are disjoint from the intervening changes; the existing stale, overlap, identity, cardinality, and ambiguity guards remain mandatory. When an exact accepted intent already has the verified branch ref and content but no matching PR, recovery SHALL emit only the missing application-owned PR consequence against fresh current main after rechecking ancestry, disjointness, exact branch/head/content, and complete all-head PR cardinality. It SHALL NOT rerun semantic work, recreate the branch, move the ref, or blindly create a duplicate PR.

A fresh process SHALL reconstruct consequence completion from the existing `ConsequenceSpec.evidence_target` and its canonical current-state positive observer. It MUST NOT require invocation-local `_materialization_targets` to recognize an already durable consequence. Implementation-carrier consequences SHALL use their existing implementation-carrier qualification owner. If an uncorrelated legacy result invalidates formal-frontier qualification while the exact source route remains current, recovery MAY resume only one accepted intent and its unique request-bound run/job after exact Issue/Change/Role/Action checks; changed identity/routing, duplicate intent/run/job, or incomplete evidence SHALL fail closed. Existing correlation, formal qualification, source/frontier, carrier, validation, review, successor, and terminal gates remain in force.

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
- THEN it compares the fresh canonical target with the apply target and recognizes the same valid consequence
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

#### Scenario: Accepted application resumes across an uncorrelated legacy result

- GIVEN one immutable accepted application intent exactly matches the current open Issue, Change, Role, and Action
- AND an earlier invocation made an application-owned effect durable but left only an uncorrelated legacy result before the formal frontier became unqualifiable
- AND the current-state observer finds the one exact application run and its one `apply` job
- WHEN a fresh bridge invocation checks application completion
- THEN it resumes only that accepted application job through the existing accepted-intent owner
- AND the uncorrelated result does not qualify a formal consequence or authorize a successor
- AND the application still performs fresh authorization and exact postcondition checks before any remaining mutation
- AND semantic work is not repeated

#### Scenario: Ambiguous accepted-application recovery remains fail closed

- GIVEN the current source/Change differs, more than one accepted intent or application run/job matches, authorization is stale, or required evidence is incomplete
- WHEN a fresh bridge invocation checks application completion
- THEN it does not resume or select any guessed application job
- AND it does not qualify the uncorrelated result or derive a successor
- AND the existing fail-closed or ambiguous classification is preserved
