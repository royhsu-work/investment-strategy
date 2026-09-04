## ADDED Requirements

### Requirement: Action is the sole normal workflow routing dimension

After cutover, normal current workflow state SHALL contain only Issue open/closed lifecycle, immutable Change: identity once formal work is activated, and exactly one valid action:<action> on an open routed coordination Issue. Role SHALL be derived as role_for(action) and MUST NOT be required as a separately persisted normal routing dimension. Semantic results, review findings/PASS, Human decisions, exact-revision evidence, transport/run records, and carrier records remain durable evidence and MUST NOT become current routing state. Normal agent:* labels are migration/source-retirement residue and MUST NOT select target-state work.

An open routed Issue with zero, multiple, or illegal action:* labels MUST fail closed. Unrelated labels MUST be preserved. Closed workflow labels are bounded migration/debt input only and MUST NOT become normal active state after cutover.

#### Scenario: Action derives the owner

- GIVEN an open coordination Issue has exactly one action:review-openspec
- WHEN executable dispatch selects it
- THEN it derives Role reviewer
- AND no normal agent:reviewer label is required for ownership
- AND the Issue's semantic evidence does not alter the derived Role

#### Scenario: Stale role label cannot override Action

- GIVEN an Issue has action:resolve-question and a stale agent:executor
- WHEN current dispatch reconstructs the Issue
- THEN it derives Lead from the Action
- AND it does not execute Executor work or repair the stale label as a semantic prerequisite

### Requirement: The executable model derives transitions and successors

The default-branch executable workflow model SHALL own ACTION_ROLE, the finite Action vocabulary, legal TRANSITIONS, role_for(action), next_action(current_action, typed_result), and select_work(authoritative_observations). A worker MAY return only a bounded typed result/evidence envelope. The worker MUST NOT choose an arbitrary Issue, Role, Action, successor, target, retry, or success meaning.

next_action SHALL derive at most one legal successor or terminal state from the current Action and typed result. The application SHALL fresh-reauthorize the source Action, derive the successor from the current state, apply exact necessary effects, and fresh-observe postconditions before treating the successor as current. There is no second production DAG, generic orchestration framework, or recovery state machine.

#### Scenario: Result derives a unique successor

- GIVEN implement-change returns a valid SPEC_BLOCKER
- WHEN application evaluates the typed result against the current Action
- THEN it derives resolve-question
- AND the worker cannot substitute another Lead Action or Issue

#### Scenario: Stale result is rejected

- GIVEN an Action result was produced from a stale Issue, Change, PR head, or default-branch revision
- WHEN application fresh-reauthorizes the effect
- THEN it fails closed
- AND it does not apply a guessed successor or replay completed work

### Requirement: One Scheduled Task wake executes exactly one Action

Each normal Scheduled Task wake SHALL fresh-dispatch exactly one repository-authorized Action, load the Role and Skill derived from that Action, execute that Action, return structured result/evidence, apply the necessary repository effects, observe postconditions, persist the unique derived successor or terminal state, and exit. A successor Action SHALL execute only on a later wake after fresh dispatch, even when it maps to the same Role.

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

### Requirement: Application performs exact effects and ordinary idempotent reconciliation

Repository application SHALL fresh-reauthorize the exact source Action, Change, Issue, PR/head, revision, Human/review/gate evidence, and effect-specific preconditions before every consequential mutation. It SHALL apply only necessary exact effects, preserve unrelated content, and fresh-observe each postcondition. Stale, replayed, ambiguous, contradictory, incomplete, or provenance-incomplete evidence MUST fail closed.

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

### Requirement: Daily control shards are bounded transport only

The retained control surface SHALL provide at most one usable current-day Asia/Taipei shard. Each request SHALL be correlated exactly to one Actions run and that run's structured result. latest, title inference, timing proximity, comment ordering, permanent response history, or an Issue-response mailbox MUST NOT authorize a result. Today SHALL be established and freshly observed before an older shard is retired, and retirement MUST NOT invalidate an in-flight request -> exact run -> result chain.

A control shard MUST NOT carry canonical Change/Action/Role/WIP state, semantic workflow evidence, successor authority, or recovery state. Dispatch/application/validation results MUST NOT be restored as response comments merely to make the shard useful. Transport changes MUST NOT change workflow semantics.

#### Scenario: In-flight rollover remains valid

- GIVEN a request on yesterday's shard already identifies exact run R
- WHEN today's shard is established and yesterday's shard is retired
- THEN R remains consumable from its exact run-scoped result
- AND no new mailbox or recovery state is created

### Requirement: Exact-R validation is gate-derived and preserves checkout proof

Whenever an approved gate requires strict OpenSpec validation for revision R, accepted evidence SHALL prove target revision R, validator checkout HEAD == R before validation, qualified pinned OpenSpec compatibility, and strict validation PASS. Eligibility SHALL be derived from the governed gate/artifact requirement and MUST NOT be restricted by a Propose-only or source-role/action whitelist. An already-current correct target MUST be validated without a dummy rewrite. Stale CI, run.head_sha without checkout proof, manual approval, connector bypass, or another model wake MUST NOT satisfy the gate.

#### Scenario: Resolve validates its current head

- GIVEN Lead / resolve-question materially revises OpenSpec artifacts on the current PR head R
- WHEN the exact validation resource is requested
- THEN it validates R without a dummy mutation
- AND the evidence proves checkout HEAD == R and strict PASS

### Requirement: OpenSpec work product uses content-addressed application ingress

For a materially revised Lead OpenSpec Change, the semantic worker MAY create unreferenced Git blobs only. Its bounded manifest SHALL contain exact branch/base identity and, for each Change-owned path, the new blob SHA and current expected blob SHA. Full source/spec/test content MUST NOT be transported through Issue comments merely to persist files.

Repository application SHALL fresh-reauthorize the exact source Action and verify current PR/head/base, Change-owned paths, current file identities, and every referenced blob during application-owned tree construction. It SHALL construct one tree and one commit revision R, advance only the exact branch without force, and fresh-observe the exact ref, PR head, commit/tree/parent, and file postconditions before exposing R to exact validation. Duplicate/escaping paths, stale identity, unavailable/mismatched blobs, worker-created tree/commit/ref, force updates, incomplete tree observations, and API success without postcondition proof MUST fail closed.

#### Scenario: Lead ingress becomes one exact revision

- GIVEN Lead has authored a corrected existing Change on PR #178
- AND the worker has created only unreferenced blobs for the five Change-owned artifact files
- WHEN application consumes the exact manifest
- THEN it constructs one exact revision R
- AND it does not carry complete file content through the check-in Issue
- AND exact-R validation receives R only after application postconditions are observed

### Requirement: Independent gates derive explicit merge Actions

review-implementation and review-archive SHALL remain independent exact-revision/exact-head gates. A passing implementation review SHALL derive merge-implementation-pr; a passing Archive review SHALL derive merge-archive-pr. Executor SHALL not infer merge phase from a generic Action or reuse an implementation PASS for Archive. Merge recovery SHALL be idempotent and exact-head bound, and Lead lifecycle/archive authority SHALL remain separate.

#### Scenario: Review PASS selects its explicit phase

- GIVEN Reviewer passes the exact implementation or Archive revision
- WHEN application derives the successor
- THEN it selects only the matching explicit merge Action
- AND the other merge Action is not authorized

### Requirement: Cutover deletes superseded normal control paths

The Change SHALL be delivered through Shadow, Cutover, and Delete boundaries. After Cutover is accepted, normal production correctness MUST NOT depend on separately persisted role labels, canonical cross-role journal/completion records, same-role continuation, cross-role barriers, response-mailbox history, Markdown topology/effect parsing, generic merge-phase inference, or legacy model-host compatibility paths. Historical records remain auditable evidence and migration/source-retirement input only.

#### Scenario: Historical evidence is not live routing

- GIVEN old role labels or transfer records remain in repository history during migration
- WHEN current dispatch runs after Action-only cutover
- THEN it selects only the current Action model and authoritative observations
- AND it does not parse historical prose or labels to invent current work

## REMOVED Requirements

### Requirement: Actionable workflow routing is one logical role/action tuple

**Reason/Migration**: Action is the sole normal routing dimension and Role is derived; preserve the Issue/Change lifecycle and migrate old role labels as bounded source-retirement input.

### Requirement: Routing handoff persists evidence before ownership transfer

**Reason/Migration**: A successor Action plus application postconditions is the current control fact; separate normal cross-role journal/completion semantics are removed while durable results and audit evidence remain.

### Requirement: Each scheduled run processes at most one actionable work item using a fixed stable order

**Reason/Migration**: The new neutral dispatcher selects one Action per wake; fixed-role continuation and old role-local action ordering are superseded by the executable model.

### Requirement: Workflow-dynamic dispatch derives one fixed invocation role from durable workflow state

**Reason/Migration**: Role derives from each selected Action and successors always wait for a later fresh wake; fixed invocation-role and same-wake continuation semantics are removed.

### Requirement: Selected Scheduled Agent actions are work-conserving within an invocation

**Reason/Migration**: Work conservation is bounded inside one selected Action; it does not authorize same-wake successor execution.

### Requirement: Scheduled execution is at-least-once and state reconstructable

**Reason/Migration**: At-least-once reconstruction and stale/replay/no-rewind safety are retained by the new application/reconciliation requirement without the old continuation and transfer-journal semantics.

### Requirement: Material workflow lifecycle transitions are journaled on the coordination Issue

**Reason/Migration**: Typed results and repository postconditions remain durable evidence; a separate required lifecycle-journal/HANDOFF control fact is removed.

### Requirement: Runtime workflow topology has one authoritative repository owner

**Reason/Migration**: The executable Action model becomes the machine authority; Human-readable workflow text becomes a generated/mechanically verified presentation.

### Requirement: The MVP exposes exactly ten normal scheduled actions

**Reason/Migration**: The target uses the smallest approved Action set, including explicit implementation/archive merge Actions rather than a generic merge phase.

### Requirement: A no-API Issue-comment canary proves the Scheduled Task transport boundary without granting workflow authority

**Reason/Migration**: The permanent comment canary/response result is replaced by bounded daily shard transport with exact run-scoped structured results.

### Requirement: The deployed no-API bridge carries the production dispatch decision without model-side selection

**Reason/Migration**: Dispatch remains machine-owned, but normal results are consumed from the exact run-scoped surface rather than response-mailbox comments.

### Requirement: External wake topology is deployment configuration, not repository workflow state

**Reason/Migration**: Preserve the non-state principle while replacing the unbounded control surface with a bounded daily shard requirement.
