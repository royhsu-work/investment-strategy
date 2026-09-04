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

ChatGPT Scheduled Task SHALL be the only normal model wake. GitHub Actions MAY run deterministic control-plane code but MUST NOT host/invoke OpenAI API, Responses API, another model API, or repository-owned model worker. Runtime check-in comments MAY be request/trigger/audit only; normal dispatch/application results SHALL belong to the exact Actions run caused by the request and be consumed from its run-scoped surface. GitHub Actions MUST NOT return normal `DISPATCH_RESULT`, `DISPATCH_DECISION`, or application-result data as machine response comments. Exact request→run→structured-result correlation is mandatory; latest/time/title/model/history inference is forbidden. Dispatch exposes `AUTHORIZE | NO_WORK | FAIL_CLOSED`; application exposes exact applied/already-satisfied/failed outcome plus postcondition evidence. Missing/multiple/failed/cancelled/malformed/expired evidence fails closed with NO Issue-response fallback. Runtime check-in is daily-bounded; coordination-Issue semantic comments remain governed evidence. Future transport replacement MUST NOT change workflow semantics.

#### Scenario: Exact run is the normal result carrier

- GIVEN request R causes exact run A
- WHEN Scheduled Task consumes dispatch/application
- THEN only A's valid run-scoped result is accepted, and missing/ambiguous/failed A cannot fall back to a plausible response comment

### Requirement: One wake executes one typed semantic Action with fresh application

A normal wake SHALL fresh neutral-dispatch, execute exactly one authorized mapped semantic Action, submit its bounded typed result plus narrative/source evidence, let repository application fresh-reauthorize exact Issue/Action/immutable Change/revision/effect predicates, derive only kernel-legal narrow effects, observe postconditions, and end. Workers MUST NOT choose arbitrary successors or make Markdown authoritative control. Historical dispatch proves entry only, not current mutation authority. Stale/contradictory state fails closed; already-satisfied legal postcondition is idempotent and MUST NOT rewind or execute successor work. A successor, same Role or not, always waits for later fresh neutral dispatch.

The selected Action remains work-conserving internally through immediately actionable RED→GREEN→REFACTOR→VERIFY, local correction, and bounded exact-resource consumption until its result or genuine Human/external/stale/contradictory/hard boundary. Correctness MUST NOT depend on same-role successor continuation, cross-role wake barriers, same-wake worker/model chaining, fixed wake Role, continuation tokens/cursors, locks/leases/heartbeats/retry-state, or hidden wake ownership.

#### Scenario: Completion or replay cannot chain/rewind

- GIVEN Action A completes to successor B, or a duplicate result for A arrives after B is current
- WHEN application observes current state
- THEN the wake ends at A's applied postcondition, replay is idempotent, and B executes only after later fresh dispatch

### Requirement: Independent semantic gates use explicit merge Actions

`review-openspec` remains independent, reverse-first then forward, source/Human-intent preserving and semantic-target bound. `review-implementation` independently assesses exact implementation head and PASS derives `merge-implementation-pr`; `review-archive` independently assesses exact Archive head/canonicalization/lifecycle preparation/cleanup-retention and PASS derives `merge-archive-pr`. Executor retains exact phase-appropriate PASS/current head/checks/non-closing linkage/Human freshness and applicable phase predicates; Archive additionally retains lifecycle preparation and cleanup/retention. No second Lead merge token is required. Recovery uses explicit merge Action + exact PR/head/merge state, is idempotent, and MUST NOT infer phase or reuse implementation PASS for Archive. `finalize-change`/`finalize-archive` retain existing Lead lifecycle, multi-PR, archive-automation, Human freshness, immutable Change, terminal evidence, and close obligations.

#### Scenario: PASS selects one explicit unchanged merge phase

- GIVEN Reviewer passes exact implementation or Archive revision R
- WHEN application/Executor evaluates the gate
- THEN the matching explicit merge Action is derived and changed-head or wrong-phase PASS does not authorize merge

### Requirement: Architecture reset is mandatory N-1 delivery with deletion

#138 SHALL remain one parent outcome. Every stage MUST be independently executable/testable/mergeable/deployable on then-current N-1 or be split without weakening the parent, and SHALL record outcomes advanced/still incomplete, N-1 prerequisites, rollback/cutover boundary, and required continuation. No intermediate stage completes #138. Order is mandatory: (1) transport de-mailbox + daily run-scoped dispatch/application results; (2) executable-kernel shadow without mutation cutover; (3) typed result→kernel effect + fresh application; (4) one-action-per-wake; (5) Action-only/Role-derived/explicit-merge cutover; (6) deletion/context reduction. Dual paths MAY coexist only for bounded N-1 proof/cutover. After cutover, production MUST delete/disable superseded Role routing, response-mailbox/history coupling, Markdown topology/effect parsing, same-wake continuation/wake barriers, obsolete compatibility hot paths, legacy Responses/model-worker host code, and redundant machine-control tests/prose. Historical evidence remains audit only.

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
**Reason**: It couples reconstruction to same-wake successors. **Migration**: Fresh application remains; one Action is wake boundary.
### Requirement: Routing handoff persists evidence before ownership transfer
**Reason**: It uses Role/same-wake transition mechanics. **Migration**: Action is ownership; evidence remains audit; successor waits.
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
**Reason**: It extends same-Action progress to same-Role successor. **Migration**: Same-Action stays work-conserving; application ends wake.
### Requirement: Persisted Change identity defines the single active workflow boundary
**Reason**: It binds WIP to Role tuples/pre-activation-only correction. **Migration**: WIP is Issue+Change+Action and bounded correction preserves it.
### Requirement: Dynamic dispatch tolerates overlapping wakes without hidden ownership state
**Reason**: Wording is tied to old routing. **Migration**: Fresh typed application preserves overlap safety without hidden owner.
