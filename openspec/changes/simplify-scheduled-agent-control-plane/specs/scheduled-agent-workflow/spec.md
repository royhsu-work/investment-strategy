## ADDED Requirements

### Requirement: Executable kernel owns Action-only workflow control
After cutover one default-branch kernel SHALL own Action→Role, typed transitions/effects, WIP/FIFO/debt dispatch, capability, fresh authorization, deterministic rejection classification/evidence, stale/replay and postconditions. Open routed Issues SHALL have exactly one valid `action:*`; Role is derived, `Change:` immutable after activation, WIP one. Evidence/history/legacy `agent:*` MUST NOT route. Normal dynamic order SHALL be active non-`unset` → closed-routing debt → unset Explore/Propose FIFO (`created_at`, Issue number) from complete current GitHub state. Fixed-role is N-1 compatibility only; production SHALL consume the kernel and workflow prose SHALL be generated/mechanically verified.
#### Scenario: Action selects work
- GIVEN one active Issue has one valid Action plus stale alternate routing
- WHEN neutral dispatch observes complete state
- THEN it selects that Issue and derives Role only from Action

### Requirement: Cutover retires explicitly absorbed pre-activation sources
Stage 5 SHALL use a finite reviewed machine-readable plan binding exact source Issue/state/`Change:`/workflow labels, absorber Issue/Change, and durable source/assignment refs. Entry plus current authoritative observations, never prose/history/model inference, selects the source; invalid/stale/ambiguous/contradictory/incomplete or newer-undispositioned-Human evidence fails closed. Application SHALL fresh-reauthorize, close if needed, remove only workflow routing, preserve evidence/unrelated labels, and accept only fresh `closed + no workflow routing`; interruption is debt and replay idempotent. The plan MUST NOT become a runtime selector/exception registry.
#### Scenario: Absorbed #168 retires
- GIVEN the reviewed entry binds #168 to #138 / `simplify-scheduled-agent-control-plane` and fresh state matches
- WHEN Stage 5 applies it
- THEN #168 is `closed + no workflow routing` with evidence/unrelated labels preserved

### Requirement: Persistent Issue permits bounded pre-acceptance Explore correction
Before first independent `review-openspec` acceptance, a material defect in the causal Explore source/evidence/feasibility MAY return the same Issue to `explore-change` when the same bounded problem is researchable without new Human-reserved commitment. Non-`unset` Change, Issue, PR/artifacts/history/evidence and WIP SHALL remain; Change MUST NOT be unset/replaced or work requeued. After acceptance use `resolve-question` plus independent review; `NO_CHANGE_REQUIRED`/`NO_GO` remain pre-activation only.
#### Scenario: Provisional Change returns
- GIVEN unaccepted Change C has a researchable causal-Explore defect
- WHEN Lead returns it to Explore
- THEN C, Issue, history and WIP remain intact

### Requirement: Runtime transport uses exact run-scoped results
Scheduled Task SHALL be the only normal model wake; Actions MUST NOT host/invoke model APIs/workers. Check-in comments MAY be request/trigger/audit only. Dispatch/application/validation results SHALL be consumed only from the exact caused Actions run; response-mailbox fallback and latest/time/title/model/history inference are forbidden. Exact correlation is mandatory; missing/multiple/failed/cancelled/malformed/expired evidence fails closed. Each wake SHALL fresh-discover exactly one current-day Asia/Taipei check-in by non-workflow identity+date; permanent pointers are forbidden. Rollover SHALL establish/observe today before closing prior days without invalidating an in-flight request→run chain.
#### Scenario: Exact run carries result
- GIVEN request C caused exact run R
- WHEN its result is consumed
- THEN only R qualifies and no response comment may substitute

### Requirement: Repository readiness self-hosts exact-revision validation
When readiness requires OpenSpec validation for R, repository deterministic application SHALL provide the resource from the gate/artifact requirement, not a Role/Action whitelist. R MAY be new or already current and correct artifacts MUST NOT be dummy-rewritten. Evidence SHALL prove target R, validator `HEAD == R`, qualified pinned compatibility and strict PASS; stale CI, `run.head_sha` alone, manual approval workaround, ungoverned connector mutation or another semantic wake MUST NOT qualify. Material `resolve-question` SHALL have the same required resource as Propose.
#### Scenario: Resolve validates current R
- GIVEN materially revised Resolve requires readiness for already-current R
- WHEN validation runs
- THEN no dummy mutation occurs and evidence proves R, checkout R, compatibility and strict PASS

### Requirement: Repository effect authority is independent from mutation carrier
Kernel/application SHALL own legal-effect derivation, exact target/preconditions/revision, carrier eligibility, fresh authorization and accepted postconditions. A carrier SHALL execute only the exact authorized plan and MUST NOT select Issue/Action/effect, weaken preconditions, infer retry/successor, change meaning or declare authoritative success; repository code SHALL fresh-observe the result before routing/gate/lifecycle consequence. Actions MAY carry effects only where its identity/event semantics satisfy lifecycle; identity-sensitive PR create/presentation/head/ready/merge effects requiring normal event propagation or forbidden to Actions SHALL use an event-capable Scheduled-Agent connector/GitHub-App carrier. The target MUST NOT enable `Allow GitHub Actions to create and approve pull requests`. Preserve Archive automation ending at validated branch; final Archive PR is a normal Lead carrier effect, then independent review and Executor merge. Bootstrap/recovery SHALL reuse a legal exact-head PR where possible and MUST NOT replace it merely because Actions PR-create returns 403.

When deterministic authorization/application rejects a plan before or during guarded application, the result SHALL identify the exact failed guard class and relevant expected/observed identity or predicate evidence machine-readably whenever that boundary has the information. Aggregate-only `effect precondition rejected` is insufficient. Rejection evidence MUST NOT authorize retry, weaker preconditions, a different target, successor execution, or carrier-side workflow inference.
#### Scenario: Actions identity cannot create PR
- GIVEN application authorizes exact PR presentation but Actions identity cannot legally create it
- WHEN that effect executes
- THEN repository authority remains and a legal carrier executes it without widening Actions permission

#### Scenario: Deterministic guard rejection is explicit
- GIVEN repository application rejects an effect because one deterministic guard fails
- WHEN the semantic worker consumes the result
- THEN the exact failed guard class and relevant expected/observed evidence are machine-readable
- AND the worker does not need to infer the deterministic failure from routing, SHA, branch payload, or application source
- AND the rejection itself does not authorize retry or a weaker effect

### Requirement: One wake executes one typed semantic Action with fresh application
A wake SHALL fresh-dispatch, execute exactly one mapped Action, return typed result/evidence, then let application fresh-reauthorize exact Issue/Action/Change/revision/effects, apply legal narrow effects, observe postconditions and end; every successor waits for later dispatch. Each Action SHALL reconstruct required durable state.

Within that one authorized Action, the primary execution unit SHALL be one bounded vertical slice with an independently verifiable outcome: `Reconstruct → RED exact gap/blocker → GREEN legal correction → VERIFY exact postcondition/revision/gate → durable checkpoint`. A slice that cannot reasonably reach VERIFY within one normal invocation SHALL be split before execution at a meaningful outcome boundary. One file mutation, API call, GitHub Actions run, first nonterminal resource observation, or other intermediate mechanical success MUST NOT by itself satisfy slice completion or Invocation Exit.

Interruption MUST NOT transfer ownership/rewind consumed descendants. Before consequential result/effect/transfer, newer workflow-relevant direct-Human input with qualifying provenance SHALL be durably dispositioned or fail closed. Bounded same-Action observation of one exact resource is allowed but MUST NOT become generic polling/successor execution. Catchable exception evidence MUST NOT itself authorize retry/transition. Correctness MUST NOT depend on cursors/locks/leases/heartbeats/retry state/same-wake chaining/fixed wake Role.
#### Scenario: Successor waits
- GIVEN Action A reaches an observed postcondition and successor B becomes current
- WHEN this wake completes
- THEN B executes only after later fresh dispatch

#### Scenario: Intermediate mechanical success does not complete a slice
- GIVEN the current authorized Action's bounded slice requires a durable artifact correction plus exact postcondition verification
- AND the artifact write or first Actions observation succeeds
- BUT VERIFY proof of the slice outcome is not yet complete
- WHEN Invocation Exit is evaluated
- THEN the intermediate success is not completion evidence
- AND the same authorized Action continues through the remaining legal same-slice work unless a governed stop boundary is reached

### Requirement: Independent semantic gates use explicit merge Actions
`review-openspec` remains independent. `review-implementation` PASS SHALL derive `merge-implementation-pr`; `review-archive` PASS SHALL derive `merge-archive-pr`. Executor SHALL retain exact phase PASS/current-head/check/linkage/Human-freshness predicates; Archive also retains lifecycle preparation/cleanup-retention. Recovery SHALL use explicit merge Action+exact PR/head state, be idempotent, and MUST NOT infer phase or reuse implementation PASS for Archive. Lead finalize authority remains.
#### Scenario: PASS selects merge phase
- GIVEN Reviewer passes exact implementation or Archive R
- WHEN merge authorization is derived
- THEN only the matching explicit merge Action for unchanged R is legal

### Requirement: Architecture reset is mandatory N-1 delivery with deletion
#138 SHALL remain one parent outcome and every stage MUST be N-1 executable/testable/mergeable/deployable or split without weakening it; intermediate completion MUST NOT complete #138. Order is **1A exact-R resource → 1B run-scoped transport/daily check-in → 1 C PR authority/carrier split → 2 kernel shadow → 3 typed application → 4 one-action-per-wake → 5 Action-only/Role-derived/explicit merges + absorbed-source retirement → 6 deletion/context reduction**. 1A SHALL precede materially revised Propose/Resolve handoff and validate final R. 1B+1C SHALL precede Stage 2 but MUST NOT add semantic review prerequisites once valid 1A exists. 1C SHALL include existing-PR reuse. Stage 3 SHALL deliver machine-readable deterministic rejection classification/evidence. Stage 4 SHALL enforce bounded verified vertical-slice completion inside the one authorized Action before durable completion checkpoint. After cutover production MUST delete superseded Role routing, response/history mailbox, Markdown topology/effect parsing, continuation/wake barriers, compatibility/model-worker paths, Actions-owned identity-sensitive PR mutation, and redundant machine-control prose/tests.
#### Scenario: Stage cannot finish early
- GIVEN a stage cannot self-host on N-1 or later stages remain
- WHEN completion is evaluated
- THEN it is split or continuation remains mandatory through Stage 6

## REMOVED Requirements
### Requirement: Actionable workflow routing is one logical role/action tuple
#*Reason/Migration**: Action becomes canonical; Role routing retires.
### Requirement: One persistent coordination Issue represents the normal OpenSpec workflow lifecycle
**Reason/Migration**: Replacement permits bounded pre-acceptance formal Explore while preserving Issue/Change/history/WIP.
### Requirement: Review and finalize actions have Lead-owned minimum gate contracts
**Reason/Migration**: Preserve gates with explicit merge Actions.
### Requirement: Scheduled execution is at-least-once and state reconstructable
**Reason/Migration**: Durable Action reconstruction remains; successors use later dispatch.
### Requirement: Routing handoff persists evidence before ownership transfer
**Reason/Migration**: HANDOFF becomes audit; source result/effects precede successor.
### Requirement: Fresh-read plus label update is not treated as mutual exclusion
**Reason/Migration**: Fresh typed application retains stale/idempotent safety.
### Requirement: Executor merges only an explicitly authorized unchanged revision
**Reason/Migration**: Explicit phase merge Actions preserve exact-head authorization.
### Requirement: Merge recovery is idempotent and reconstructable
**Reason/Migration**: Explicit merge Action+PR state replaces phase inference.
### Requirement: Each scheduled run processes at most one actionable work item using a fixed stable order
**Reason/Migration**: Neutral dynamic Action dispatch replaces fixed-role selection.
### Requirement: Repository agent artifacts expose the governance contract
#*Reason/Migration**: Kernel owns machine semantics; prose becomes generated/verified.
### Requirement: Default-branch governance declares the scheduled dispatch mode
#*Reason/Migration**: Dynamic is normal; fixed-role is bounded N-1 only.
### Requirement: Workflow-dynamic dispatch derives one fixed invocation role from durable workflow state
**Reason/Migration**: Role derives per Action; successor waits.
### Requirement: Selected Scheduled Agent actions are work-conserving within an invocation
**Reason/Migration**: Work conservation stays inside one Action only.
### Requirement: Persisted Change identity defines the single active workflow boundary
**Reason/Migration**: Current position includes Issue+Change+Action+causal binding.
### Requirement: Dynamic dispatch tolerates overlapping wakes without hidden ownership state
**Reason/Migration**: Fresh typed application preserves overlap safety without hidden owner.
