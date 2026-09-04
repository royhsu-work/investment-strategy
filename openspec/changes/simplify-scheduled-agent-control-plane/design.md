## Context

Current `main` already contains useful deterministic pieces: complete authoritative acquisition and dispatch, bounded structured Explore/Propose-correction results, repository-owned effect contracts, current-state FIFO, stale/precondition checks, and a no-API Issue-comment bridge that can invoke deterministic GitHub Actions. The problem is not absence of control-plane code. The problem is that the finite workflow is still independently represented and reconstructed across multiple owners: persistent Role+Action labels, `agents/workflow.md`, `agents/AGENTS.md`, procedural Skills, dispatcher/runtime predicates, effect-side Markdown topology parsing, worker/result schemas, transport comments, and wake-continuation instructions.

#138's Explore result `5470121673` established that the common failure pattern across #133/#140/#155/#158/#161/#164/#168/#175 is duplicated state-machine ownership. It also verified the deployment constraint: the model can be woken normally only by ChatGPT Scheduled Tasks; deterministic repository execution can run in GitHub Actions; no OpenAI/Responses/other model API is permitted.

The target therefore consolidates existing deterministic responsibilities instead of wrapping them in another orchestrator.

## Goals / Non-Goals

**Goals:**

- Make one executable finite topology the only machine-decidable workflow-semantic authority used by production dispatch, typed result validation, transition derivation, effect authorization, migration, and tests.
- Reduce live routing to Action-only state and derive Role from Action.
- Make the two merge lifecycle positions explicit in Action identity.
- Execute exactly one mapped semantic action per Scheduled Task wake while keeping the selected action internally work-conserving.
- Keep the model responsible for semantic judgment and evidence; keep repository code responsible for finite state/result/effect mechanics.
- Keep current connector/Issue-comment/Actions transport replaceable and non-authoritative.
- Preserve WIP=1, finish-first, exact-revision gates, Human authority, role separation, semantic evidence/review, archive ownership, stale/concurrency fail-closed behavior, and at-least-once reconstruction.
- Migrate/cut over once, then remove legacy parsers/Role labels/continuation machinery from the production hot path.

**Non-goals:**

- No OpenAI API, Responses API, other model API, GitHub-hosted model worker, or repository-owned AI wake loop.
- No generic workflow/orchestration framework, daemon, second scheduler, broker, lock, lease, heartbeat, retry counter, hidden cursor, or additional workflow-state database.
- No semantic keyword classifier for Human intent, materiality, feasibility, requirements, review adequacy, or implementation conformance.
- No permanent dual old/new dispatcher/application paths after migration acceptance.
- No claim that the current connector's broad physical write surface makes bypass cryptographically impossible.
- No weakening of #175's source-backed Explore/Propose/Reviewer semantic gates.

## Decisions

### Decision 1: Canonical live state is Issue lifecycle + Action + immutable Change

For an ordinary open coordination Issue, current workflow state is:

```text
Issue identity/open state
Change: unset | <immutable-change-id>
action:<action>   # exactly one while routed
```

Role is derived from Action by the executable topology. `agent:*` is not canonical state after cutover and must not be required for dispatch, transition, terminal-debt discovery, or application.

Durable `ACTION_RESULT`, `REVIEW_RESULT`, `MERGE_RESULT`, Human decisions, exception records, HANDOFF/presentation records, PR/CI state, commits, and transport requests/results remain evidence/audit input where their owning semantic/lifecycle gate needs them. They are not a second current routing dimension.

Closed Issues with a retained `action:*` label remain bounded routing debt until repository-owned terminal retirement or recovery proves the legal disposition. Terminal postcondition is `closed + no action:*` while preserving unrelated labels.

**Why:** removing persistent Role eliminates one entire mismatch/residue axis. Role is a pure deterministic function of Action and therefore should not be stored independently.

### Decision 2: Merge phase is explicit in Action identity

Replace generic `merge-pr` with:

```text
merge-implementation-pr -> Executor
merge-archive-pr        -> Executor
```

The lifecycle topology directly routes `review-implementation PASS` to `merge-implementation-pr` and `review-archive PASS` to `merge-archive-pr`. Their semantic merge checks remain those already required for implementation versus Archive PRs.

**Why:** one Action label must identify a complete machine state. Keeping one generic merge action would force application/dispatch to infer phase from PR/history evidence and would reintroduce hidden state.

### Decision 3: One executable topology owns finite workflow semantics

The final production code SHALL expose one small typed topology/kernel boundary containing:

- Action enum/vocabulary;
- Action → Role derivation;
- action-owned typed result vocabulary where finite results exist;
- legal `(source action, typed result/effect) -> successor/terminal effect` mappings;
- deterministic pre-activation/formal selection and WIP/cardinality predicates;
- action effect capabilities and structural preconditions;
- source-action fresh reauthorization, stale/replay rejection, and postcondition expectations.

The implementation MAY evolve/rename/consolidate current `workflow_dispatch.py`, `scheduled_agent_effect_contract.py`, `scheduled_agent_effects.py`, and runtime helpers, but final production must not leave a second independently maintained topology registry/parser beside the kernel.

`agents/workflow.md` becomes generated from, or mechanically verified against, the executable topology. A repository test must fail when its machine-readable action/role/transition presentation diverges. Human-readable explanations may remain prose, but they cannot redefine executable state transitions.

**Why:** the architecture problem is duplicated state-machine ownership. A new kernel only succeeds if old full decision paths are retired.

### Decision 4: Semantic worker output is typed control outcome plus narrative evidence

A mapped semantic action receives an exact repository-owned authorization envelope bound to current Issue + Action + required revision/evidence references. It returns:

```text
source issue
authorized source action
bounded typed result/effect request
narrative result_content / source evidence
revision/evidence references required by that action
```

The worker does not return arbitrary successor routing. Repository application validates the action-owned result, derives the only legal transition/effects from the executable topology, fresh-observes/re-authorizes the source action, verifies effect-specific preconditions, applies, then fresh-observes postconditions.

Free-form Markdown remains Human-readable evidence; production control outcomes must not be parsed back from Markdown when a typed value exists.

Semantic ownership remains with the model for Explore conclusions, Human-materiality/reserved-boundary judgment, formal OpenSpec meaning, semantic review, implementation conformance, regression adequacy, and other meaning-dependent decisions.

### Decision 5: One Scheduled Task wake executes exactly one mapped action

Normal model execution becomes:

```text
wake
  -> load current default-branch governance
  -> neutral executable dispatch
  -> AUTHORIZE exact Issue + Action
  -> derive Role and load mapped Skill
  -> execute that one semantic action to its action-defined result/boundary
  -> deterministic application/transition/postcondition
  -> end invocation

next Scheduled Task wake
  -> fresh neutral dispatch
```

There is no same-wake successor model action, even if the successor derives to the same Role. The repository may persist the successor Action, but it does not wake or chain another model worker.

The selected action remains internally work-conserving: RED→GREEN→REFACTOR/VERIFY work, correction of actionable validation failure, and bounded consumption of an exact just-triggered CI/resource remain inside that one action while source Action/revision/authority/preconditions stay current. Action completion itself is an invocation terminal boundary after application.

This removes same-role continuation, fixed invocation-role comparison for successors, cross-role wake barriers, fresh-worker same-wake chaining, `continuation_required`/equivalent flags, and prompt logic whose only purpose is deciding whether another mapped action may execute in the same wake.

### Decision 6: Transport is an exact-correlated adapter, never state authority

Under current connector capabilities the transport can remain Issue-comment-triggered GitHub Actions, but it must behave like RPC:

```text
exact dispatch request comment
  -> exact bridge Actions run/job
  -> structured dispatch result

exact application request/result payload
  -> exact deterministic Actions run/job
  -> applied/failed structured result + postcondition evidence
```

The Scheduled Task consumes the exact correlated run/result it caused; it must not search for "latest" matching prose, infer workflow state from comment history, or use the response comment as authorization for later wakes. After cutover, normal machine responses need not be written back as a comment mailbox when exact run/job output is available.

A future direct Actions invocation transport may replace the adapter without changing the kernel, Action vocabulary, typed result contract, or lifecycle semantics.

### Decision 7: Application is stale/replay safe and at-least-once

Before every consequential workflow effect, application must fresh-observe the exact source Issue/Action/Change and any effect-specific revision/gate evidence. A result applies only when the exact source Action is still authorized and the topology admits the typed result/effect.

If another wake already applied the result, application recognizes the postcondition and returns an idempotent already-applied outcome without rewinding state. If state moved incompatibly or evidence is stale/contradictory, application fails closed and performs no speculative successor mutation.

Fresh-read is not treated as a mutex/CAS. Existing revision/SHA protections are used where available; narrow idempotent effects and postcondition observation protect other mutations.

### Decision 8: Migration is bounded, observable, and deletes compatibility

Migration has five phases:

1. **Kernel shadow:** implement typed topology/kernel and exhaustive tests without owning mutations; feed it the same complete authoritative observations as current production and compare dispatch/effect decisions.
2. **Live-state canonicalization plan:** enumerate every current Issue carrying workflow routing; classify terminal, legal current Action/Change, or genuinely ambiguous using authoritative GitHub state. Produce an explicit before→after plan; Human resolves only ambiguous cases.
3. **Transport/application proof:** prove one live no-model-API dispatch and one live typed application path, including stale/replay rejection and postcondition observation.
4. **Cutover:** atomically enough for repository semantics, convert live routed Issues to Action-only labels, switch production dispatch/application and governance bootstrap to the kernel, and mechanically verify `agents/workflow.md` projection.
5. **Deletion:** remove `agent:*` normal routing support, Role/Action tuple validators, history/cutoff eligibility branches made obsolete by canonical state, Markdown topology/effect parsing, obsolete model-worker host paths, same-wake continuation/wake-barrier logic, response-mailbox/history dedup used only by old transport, and compatibility-only tests.

Rollback is allowed before cutover by leaving current production mutation authority unchanged. After canonical live state is accepted, rollback must not reintroduce old Role labels/history parsing as a permanent second selector; any bounded emergency adapter must translate from the new canonical state.

### Decision 9: Governance ownership follows executable versus semantic responsibility

Machine-decidable finite topology/state/result/effect rules live once in executable code and are tested mechanically. `agents/AGENTS.md` declares the execution protocol and points to that authority; `agents/workflow.md` presents it; mapped Skills own action procedure and semantic judgment only; OpenSpec defines the approved external/governance contract.

This does not make implementation code higher authority than current default-branch governance during an unmerged Change. Before activation, current default-branch governance remains authoritative. After the approved implementation merges, the default branch's governance explicitly delegates its machine-decidable workflow topology to the executable topology/kernel.

## Responsibility split

```text
ChatGPT Scheduled Task
  -> bootstrap from current default branch
  -> request neutral dispatch
  -> execute exactly one authorized semantic action
  -> return typed outcome + evidence

GitHub acquisition adapter
  -> authoritative complete observations + provenance

Executable topology/kernel
  -> canonical Action model + Role derivation
  -> WIP/FIFO/debt dispatch
  -> typed result validation + legal transition/effect
  -> fresh source reauthorization + stale/replay checks
  -> postcondition expectations

Repository application adapter
  -> perform exact authorized GitHub mutations
  -> fresh-observe postconditions

Lead / Reviewer / Executor Skills
  -> semantic meaning, analysis, review, implementation judgment
  -> evidence required by action contract

Transport adapter
  -> exact request/run/result correlation only
```

## Failure behavior

- Incomplete authoritative enumeration/provenance fails closed before dispatch.
- Zero/multiple/unknown Action labels on an open routed Issue fail closed; an `agent:*` label after cutover is migration/debt evidence, not an alternate routing owner.
- Multiple formal active workflows continue to fail closed; queued work never bypasses WIP=1.
- Unknown/invalid typed worker result fails before mutation.
- Result bound to stale source Action/Change/revision is rejected.
- Replay after already-observed legal postcondition is idempotent and does not rewind.
- Transport ambiguity or inability to correlate the exact request/run/result fails closed; "latest" or history-prose inference is forbidden as fallback.
- Semantic ambiguity remains with the mapped Role/Human boundary; deterministic code does not guess meaning.
- One mapped action finishing never causes same-wake execution of its successor.
- Migration ambiguity is surfaced explicitly; read failure never creates replacement state.

## Validation strategy

1. Exhaustive topology tests cover every Action, derived Role, legal typed result/successor, terminal effect, illegal transition, and both explicit merge actions.
2. Property/regression tests prove exactly one Action label is canonical; no Action→Role ambiguity; terminal retirement removes only workflow Action labels and preserves unrelated labels.
3. Production-boundary dispatcher tests prove WIP=1, FIFO, routing debt, incomplete enumeration/provenance, stale state, and #155/#175 regressions from complete observations without `agent:*` or historical-prose eligibility.
4. Application tests prove source reauthorization, stale/replay rejection, idempotent already-applied handling, narrow mutations, and fresh postconditions.
5. Governance tests prove `agents/workflow.md` is generated/mechanically verified from executable topology and mapped Skills do not contain competing machine transition tables.
6. Wake-contract tests prove exactly one mapped action is allowed per invocation; action-internal continuation remains work-conserving; same-role/cross-role successor chaining is absent.
7. Shadow tests compare old/new production decisions on representative current-state snapshots before cutover and fail on unexplained divergence.
8. Migration tests cover terminal/current/ambiguous live state, Action-only canonicalization, legacy Role-label retirement, and post-cutover rejection/diagnosis of obsolete representations.
9. Live no-API E2E proves exact dispatch request → exact Actions decision and typed worker-result application → exact Actions result/postcondition, with no model API in GitHub Actions.
10. Full Python quality, repository governance checks, and strict OpenSpec validation run on the exact implementation/review revision.

The success metric is architectural subtraction: after cutover the production normal path has fewer durable current-state dimensions, one executable transition authority, one mapped action per wake, and no need to reconstruct normal state from historical prose.