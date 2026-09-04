## ADDED Requirements

### Requirement: Executable kernel owns Action-only current workflow control

After cutover, one default-branch executable kernel SHALL solely own Action vocabulary, Action→Role, finite typed result→transition/effect rules, WIP/FIFO/debt dispatch, effect capabilities, fresh authorization, stale/replay classification, and structural postconditions. An open routed Issue SHALL have exactly one valid `action:*`; Role is derived, `Change:` remains immutable formal identity after activation, and Issue open/closed remains lifecycle state. Results/reviews/Human decisions are evidence; HANDOFF/transport/history and legacy `agent:*` are not current routing authority. Zero/multiple/unknown Actions fail closed; `closed + action:*` is debt until retirement to `closed + no action:*`, preserving unrelated labels. WIP remains one.

Normal selection SHALL be neutral `workflow-dynamic`: active non-`unset` workflow first, then closed-routing debt, else one combined unset Explore/Propose FIFO by `created_at`, then Issue number, using complete authoritative current GitHub state. Task names, conversation/prior roles, feature-branch governance, Role labels, response comments, prose, and model inference MUST NOT select work. Fixed-role MAY survive only as bounded N-1 compatibility. Production dispatch/application/migration/tests consume the kernel directly; `agents/workflow.md` is generated/mechanically verified presentation, not a parsed competing DAG; AGENTS/roles/Skills retain semantic procedure/judgment. An unmerged kernel is review input only.

#### Scenario: Current Action is the one selector

- GIVEN one active Issue has `action:review-openspec` while queued work, stale Role labels, and historical routing prose exist
- WHEN neutral dispatch reconstructs complete current state
- THEN that Issue is selected and Reviewer is derived from Action without using alternate selectors

### Requirement: Persistent Issue permits bounded pre-acceptance Explore correction

The same coordination Issue SHALL persist through Explore and formal lifecycle. Ordinary pre-Propose Explore keeps `Change: unset`, and Propose still verifies exact same-Issue durable `PROPOSAL_READY`. Before first independent semantic `review-openspec` acceptance, if formalization materially invalidates that Explore source/evidence/feasibility premise and the same bounded problem remains researchable without new Human-reserved requirement/scope/risk/architecture commitment, the same Issue MAY return to `explore-change` after provisional non-`unset` Change activation. It SHALL preserve Change identity, Proposal/PR/results/history, Issue identity, and active WIP; it MUST NOT unset/replace Change, erase history, create a replacement Issue, or release work to queued intake. New Human-reserved commitment still requires Human authority. After independent semantic acceptance, material correction uses `Lead / resolve-question` plus renewed independent review. Terminal `NO_CHANGE_REQUIRED`/`NO_GO` Explore is pre-activation only.

#### Scenario: Provisional Change returns without reset

- GIVEN Change `C` is provisional, OpenSpec acceptance has not occurred, and formalization invalidates a bounded research premise without new Human authority
- WHEN Lead dispositions it
- THEN the same Issue may return to Explore while `Change: C`, existing Proposal/PR/history, and WIP stay intact

### Requirement: Runtime transport uses exact run-scoped results without response mailbox

ChatGPT Scheduled Task SHALL be the only normal model wake. GitHub Actions MAY run deterministic control-plane code but MUST NOT host/invoke OpenAI API, Responses API, another model API, or repository-owned model worker. Runtime check-in comments MAY be request/trigger/audit only; normal dispatch/application/validation results SHALL belong to the exact Actions run caused by the request and be consumed from its run-scoped surface. GitHub Actions MUST NOT return normal `DISPATCH_RESULT`, `DISPATCH_DECISION`, or application-result data as machine response comments. Exact request→run→structured-result correlation is mandatory; latest/time/title/model/history inference is forbidden. Dispatch exposes `AUTHORIZE | NO_WORK | FAIL_CLOSED`; application exposes exact applied/already-satisfied/failed outcome plus postcondition evidence. Missing/multiple/failed/cancelled/malformed/expired evidence fails closed with NO Issue-response fallback. Runtime check-in is daily-bounded; coordination-Issue semantic comments remain governed evidence. Future transport replacement MUST NOT change workflow semantics.

#### Scenario: Exact run is the normal result carrier

- GIVEN request R causes exact run A
- WHEN Scheduled Task consumes dispatch/application
- THEN only A's valid run-scoped result is accepted, and missing/ambiguous/failed A cannot fall back to a plausible response comment

### Requirement: Repository-owned artifact mutation self-hosts exact-revision strict validation

When an authorized selected Action changes OpenSpec artifacts and exact-revision validation is a readiness gate, the repository-owned deterministic application boundary SHALL obtain validation evidence for the exact resulting revision `R` before ownership transfer. It MAY run pinned strict validation directly after mutation/postcondition or explicitly invoke a dedicated deterministic validator bound to `R`; the mechanism is implementation-owned and MUST NOT create another semantic Action or model wake.

Accepted evidence SHALL prove target revision `R`, validator checkout `HEAD == R`, qualified pinned OpenSpec compatibility, and strict OpenSpec validation PASS. That structured validation result SHALL belong to the exact deterministic application/validation execution and be consumable by the already selected semantic Action as exact-resource evidence. Missing, failed, cancelled, ambiguous, revision-mismatched, checkout-mismatched, malformed, or expired evidence SHALL fail closed. Stale validation, `run.head_sha == R` without checkout proof, manual approval/operator workarounds, direct connector bypass, or another semantic Action/model wake SHALL NOT satisfy the gate.

#### Scenario: Event validation cannot execute

- GIVEN repository application produced revision `R`
- AND an event-triggered validation reports `action_required` with no validator job
- WHEN Lead evaluates exact-revision readiness
- THEN `R` is not validated
- AND ownership does not transfer
- AND repository application must self-host or explicitly trigger exact-`R` deterministic validation, otherwise fail closed

#### Scenario: Exact-R validation completes inside the selected Action

- GIVEN repository application produced revision `R`
- WHEN the exact deterministic validation execution proves target `R`, checkout `R`, qualified pinned compatibility, and strict PASS
- THEN the same selected semantic Action may consume that structured result for readiness
- AND no second semantic Action or model wake is created

### Requirement: One wake executes one typed semantic Action with fresh application

A normal wake SHALL fresh neutral-dispatch, execute exactly one authorized mapped semantic Action, submit its bounded typed result plus narrative/source evidence, let repository application fresh-reauthorize exact Issue/Action/immutable Change/revision/effect predicates, derive only kernel-legal narrow effects, observe postconditions, and end. Workers MUST NOT choose arbitrary successors or make Markdown authoritative control. Historical dispatch proves entry only, not current mutation authority. The source Action's required durable result/evidence and legal effects SHALL be persisted and observed before any successor becomes current. Stale/contradictory state fails closed; already-satisfied legal postconditions are idempotent and MUST NOT rewind or execute successor work. A successor, same Role or not, always waits for later fresh neutral dispatch.

Each selected Action SHALL reconstruct the durable repository, Issue, PR, OpenSpec, Actions, and specifically awaited external-resource state required by that Action before deciding what remains. Correctness MUST NOT depend on prior conversation memory or a previous wake exiting cleanly. Partial execution, interruption, tool failure, or a missing final response MUST NOT transfer ownership. Recovery SHALL distinguish observed durable mutations from intended-but-uncompleted work and SHALL NOT rewind an already-consumed transition when valid causal-descendant evidence proves later lifecycle work has consumed it; contradictory consumption evidence fails closed.

Immediately before a consequential action result, effect request, or ownership transition, the acting role SHALL fresh-read workflow-relevant coordination-Issue activity newer than the durable evidence boundary on which that consequence relies. A candidate direct-Human comment counts for this freshness contract only when raw creation provenance identifies the designated Human and `performed_via_github_app == null`; missing or ambiguous provenance fails closed. Material newer direct-Human input SHALL have a durable exact-comment disposition before the consequence proceeds: address it within current authority, classify it non-blocking with concrete rationale, convert it to an existing finding/blocker/correction result, or route/escalate it to the legal owner/Human boundary. This freshness classification MUST NOT itself satisfy a separately Human-reserved decision predicate. Later wakes SHALL reconstruct prior exact-comment dispositions without adding a comment queue, unread counter, acknowledgement label/state, cursor, hidden registry, lock, lease, heartbeat, or second workflow DAG.

The selected Action remains work-conserving internally through immediately actionable RED→GREEN→REFACTOR→VERIFY, local correction, and bounded exact-resource consumption until its result or genuine Human/external/stale/contradictory/hard boundary. The first observation of the exact resource just triggered by that Action as absent, queued, or in progress MUST NOT by itself end the Action while bounded same-action observation remains possible. The Action MAY re-observe only that exact resource and consume its terminal result if the source remains authorized; a later wake resuming a real wait SHALL fresh-read that exact resource again. This bounded observation MUST NOT become a generic polling/retry scheduler or permit successor Action execution in the same wake.

When a catchable tool/runtime/execution failure is observable and repository evidence remains writable, the current role SHALL persist canonical `EXECUTION_EXCEPTION` evidence containing the raw observable error after platform redaction, selected role/action, attempted operation/tool, relevant revision/base when applicable, known completed durable mutations, and unfinished work boundary. Classification and interpretation remain separate and `UNCLASSIFIED_EXECUTION_EXCEPTION` is legal. Exception evidence MUST NOT itself authorize retry, result, transition, or ownership transfer. Legal same-authority recovery MAY continue only while routing, revision, preconditions, and execution context remain current; otherwise use the governed disposition path. A truly uncatchable termination is reconstructed from actual durable state and MUST NOT be retroactively fabricated. This contract MUST NOT introduce a universal blocked result, generic retry engine, fault state machine, retry counter, or hidden execution status.

Correctness MUST NOT depend on same-role successor continuation, cross-role wake barriers, same-wake worker/model chaining, fixed wake Role, continuation tokens/cursors, locks/leases/heartbeats/retry-state, or hidden wake ownership.

#### Scenario: Completion or replay cannot chain/rewind

- GIVEN Action A completes to successor B, or a duplicate result for A arrives after B is current
- WHEN application observes current state
- THEN the wake ends at A's applied postcondition, replay is idempotent, and B executes only after later fresh dispatch

#### Scenario: Newer direct-Human input blocks a stale consequence

- GIVEN Action A relies on durable evidence E
- AND a newer workflow-relevant direct-Human comment has qualifying raw provenance but no legal durable disposition
- WHEN A reaches a consequential result, effect, or ownership boundary
- THEN A fails closed at that boundary
- AND neither actor identity nor the freshness classifier grants any Human-reserved authority

#### Scenario: Exact resource may finish inside the selected Action

- GIVEN Action A has just triggered exact external resource R
- AND the first observation of R is absent, queued, or in progress
- WHEN bounded same-action observation remains possible and A is still authorized
- THEN A may re-observe only R and consume its terminal result
- AND no successor Action executes in that wake

#### Scenario: Catchable failure is evidence, not a transition

- GIVEN Action A encounters an observable catchable failure and repository evidence remains writable
- WHEN A cannot complete the attempted operation
- THEN canonical `EXECUTION_EXCEPTION` preserves the raw observable failure and unfinished boundary
- AND the exception alone does not authorize retry, routing, result, or ownership transfer

### Requirement: Independent semantic gates use explicit merge Actions

`review-openspec` remains independent, reverse-first then forward, source/Human-intent preserving and semantic-target bound. `review-implementation` independently assesses exact implementation head and PASS derives `merge-implementation-pr`; `review-archive` independently assesses exact Archive head/canonicalization/lifecycle preparation/cleanup-retention and PASS derives `merge-archive-pr`. Executor retains exact phase-appropriate PASS/current head/checks/non-closing linkage/Human freshness and applicable phase predicates; Archive additionally retains lifecycle preparation and cleanup/retention. No second Lead merge token is required. Recovery uses explicit merge Action + exact PR/head/merge state, is idempotent, and MUST NOT infer phase or reuse implementation PASS for Archive. `finalize-change`/`finalize-archive` retain existing Lead lifecycle, multi-PR, archive-automation, Human freshness, immutable Change, terminal evidence, and close obligations.

#### Scenario: PASS selects one explicit unchanged merge phase

- GIVEN Reviewer passes exact implementation or Archive revision R
- WHEN application/Executor evaluates the gate
- THEN the matching explicit merge Action is derived and changed-head or wrong-phase PASS does not authorize merge

### Requirement: Architecture reset is mandatory N-1 delivery with deletion

#138 SHALL remain one parent outcome. Every stage MUST be independently executable/testable/mergeable/deployable on then-current N-1 or be split without weakening the parent, and SHALL record outcomes advanced/still incomplete, N-1 prerequisites, rollback/cutover boundary, and required continuation. No intermediate stage completes #138. Order is mandatory: (1) transport de-mailbox + daily run-scoped dispatch/application/validation results + exact-revision validation bootstrap; (2) executable-kernel shadow without mutation cutover; (3) typed result→kernel effect + fresh application; (4) one-action-per-wake; (5) Action-only/Role-derived/explicit-merge cutover; (6) deletion/context reduction. Stage 1 MAY split into independently executable transport and validation-bootstrap sub-slices, but both SHALL be deployed before later stages depend on repository-owned OpenSpec artifact mutation. Dual paths MAY coexist only for bounded N-1 proof/cutover. After cutover, production MUST delete/disable superseded Role routing, response-mailbox/history coupling, Markdown topology/effect parsing, same-wake continuation/wake barriers, obsolete compatibility hot paths, legacy Responses/model-worker host code, and redundant machine-control tests/prose. Historical evidence remains audit only.

#### Scenario: Stage cannot self-host or complete early

- GIVEN a stage cannot run on N-1 or later mandatory stages remain
- WHEN completion is evaluated
- THEN it is split or continuation remains mandatory and #138 stays incomplete through Stage 6 deletion/full verification

## REMOVED Requirements

### Requirement: Actionable workflow routing is one logical role/action tuple
**Reason**: Role+Action duplicates authority. **Migration**: Stage 5 Action-only; Stage 6 retires Role routing.
### Requirement: One persistent coordination Issue represents the normal OpenSpec workflow lifecycle
**Reason**: It forbids approved bounded post-activation pre-acceptance Explore. **Migration**: Replacement preserves Issue/Change/history and formal correction after acceptance.
### Requirement: Review and finalize actions have Lead-owned minimum gate contracts
**Reason**: It embeds generic `merge-pr`. **Migration**: Replacement preserves gates/finalize and uses explicit merge Actions.
### Requirement: Scheduled execution is at-least-once and state reconstructable
**Reason**: Its same-wake successor mechanics conflict with the one-Action wake boundary. **Migration**: The replacement preserves action-specific durable reconstruction, direct-Human freshness/disposition, partial-mutation and causal-descendant replay safety, bounded exact-resource observation, and execution-exception evidence while moving every successor Action to a later fresh wake.
### Requirement: Routing handoff persists evidence before ownership transfer
**Reason**: Synthetic Role-oriented HANDOFF is no longer a control primitive. **Migration**: The source Action's result/evidence and legal effects remain durable before its successor becomes current; HANDOFF may remain audit/provenance only, and every successor waits for later fresh dispatch.
### Requirement: Fresh-read plus label update is not treated as mutual exclusion
**Reason**: Tuple wording is obsolete. **Migration**: Fresh typed application preserves no-mutex/stale/idempotent safety.
### Requirement: Executor merges only an explicitly authorized unchanged revision
**Reason**: Generic merge hides phase. **Migration**: Explicit merge Actions preserve exact-head gates.
### Requirement: Merge recovery is idempotent and reconstructable
**Reason**: Generic recovery infers phase. **Migration**: Explicit merge Action + PR state drives recovery.
### Requirement: Each scheduled run processes at most one actionable work item using a fixed stable order
**Reason**: It keeps fixed-role normal selection. **Migration**: Neutral dynamic dispatch preserves WIP/debt/FIFO; fixed-role is bounded compatibility.
### Requirement: Repository agent artifacts expose the governance contract
**Reason**: Machine topology is distributed in prose. **Migration**: Kernel owns machine semantics; workflow.md is generated/verified.
### Requirement: Default-branch governance declares the scheduled dispatch mode
**Reason**: It permits peer normal fixed-role mode. **Migration**: Dynamic is normal; fixed-role is bounded N-1 compatibility.
### Requirement: Workflow-dynamic dispatch derives one fixed invocation role from durable workflow state
**Reason**: It freezes wake Role/same-wake successors. **Migration**: Role derives for one Action; successor waits.
### Requirement: Selected Scheduled Agent actions are work-conserving within an invocation
**Reason**: It extends same-Action progress into same-Role successor execution. **Migration**: Same-Action RED→GREEN→REFACTOR→VERIFY, local correction, and bounded exact-resource observation remain work-conserving; application ends the wake before any successor Action.
### Requirement: Persisted Change identity defines the single active workflow boundary
**Reason**: It binds WIP to Role tuples/pre-activation-only correction. **Migration**: WIP is Issue+Change+Action and bounded correction preserves it.
### Requirement: Dynamic dispatch tolerates overlapping wakes without hidden ownership state
**Reason**: Wording is tied to old routing. **Migration**: Fresh typed application preserves overlap safety without hidden owner.
