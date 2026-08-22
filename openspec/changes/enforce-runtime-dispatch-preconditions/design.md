# Design: Enforce runtime dispatch preconditions

## Context

#105 corrected dispatch/cardinality semantics but intentionally stopped at Agent-interpreted runtime behavior plus a test-only classifier. #133 then extracted those semantics into the production pure module `src/investment_strategy/workflow_dispatch.py`, added explicit same-execution GitHub observation provenance, made regressions consume that implementation, and initially required the Scheduled Agent to execute it.

Reviewer implementation finding `issuecomment-5379837891` proved that the real Scheduled-Agent environment had no demonstrated pre-action repository execution hook. A later correction proposed an Issue-comment-triggered GitHub Actions Transition Gate, but Reviewer OpenSpec finding `issuecomment-5380345857` correctly rejected that boundary because #133's first demonstrated violation was substantive #130 Explore itself, before any later routing transition. A gate that runs only after the model action cannot prevent that recurrence.

The required enforcement boundary is therefore before model invocation. GitHub Actions owns scheduling, current-state acquisition, production-classifier execution, and durable-effect application. The model remains the action worker, but it is invoked only after executable authorization and does not receive durable GitHub write authority.

## Decision 1 — Preserve the pure production classifier

Keep `src/investment_strategy/workflow_dispatch.py` as the repository-owned deterministic dispatch/cardinality/action-authorization implementation.

It remains pure and accepts explicit normalized `DispatchPreflight` input containing repository Issue snapshots plus enumeration/provenance evidence. It does not own GitHub I/O, lifecycle topology, model invocation, durable mutation, Human authority, or workflow state.

Tests and every live runtime authorization boundary MUST call this production implementation rather than defining another behavioral classifier.

## Decision 2 — GitHub Actions owns the pre-model Scheduled Agent runtime boundary

Add one default-branch GitHub Actions Scheduled Agent runtime. It is the normal scheduler/runtime after cutover.

Each wake executes this order before any mapped model work:

1. check out authoritative default-branch runtime/governance code;
2. acquire complete current repository workflow state from GitHub with observable enumeration completeness;
3. normalize provenance-qualified `DispatchPreflight` input;
4. execute `workflow_dispatch.py`;
5. compare the classifier-selected current role with the fixed role assigned to that schedule/manual invocation;
6. exit without a model request unless the decision is `AUTHORIZE` for one exact coordination Issue and the selected role matches the fixed slot;
7. only then construct the mapped role/action worker request.

`FAIL_CLOSED`, `NO_WORK`, role mismatch, incomplete enumeration, multiple-active state, contradictory current fields, or unqualified observation provenance MUST terminate before model invocation.

## Decision 3 — Preserve fixed role slots; scheduling does not choose workflow state

Preserve three fixed runtime slots corresponding to Lead, Reviewer, and Executor. The schedule carries only that fixed role identity. It does not carry an Issue number, Change, action, winner, or workflow priority.

The production classifier independently selects current work from GitHub. A Lead slot cannot execute Reviewer/Executor work, and vice versa. A role mismatch is a normal pre-model no-op.

An optional GitHub Actions `workflow_dispatch` manual wake MAY accept a fixed role input for controlled/manual execution. It is subject to exactly the same acquisition/classifier/role-match boundary and cannot override selection.

## Decision 4 — The action worker uses the Responses API, not Codex

After authorization, repository runtime code invokes an OpenAI Responses API model worker for the exact selected Issue/role/action. Codex is not the worker runtime for this Change.

The worker receives:

- authoritative default-branch role and mapped Skill instructions;
- the exact machine-authorized Issue/role/action identity;
- GitHub/repository read capability required for current evidence reconstruction and action-local work;
- a local checkout/workspace and bounded shell/patch tooling when implementation work requires it;
- an output contract for the action result and requested durable effects.

Provider/model authentication is deployment configuration. It MUST NOT be encoded as workflow state, routing state, or authorization evidence.

## Decision 5 — The model worker has no durable GitHub write authority

The worker execution boundary MUST NOT expose a write-capable GitHub credential to model-controlled tools or shell execution.

In particular, model-controlled execution cannot directly create/update/delete Issue or PR state, mutate routing labels or Change identity, push repository refs, create/merge PRs, close/reopen Issues, or perform equivalent durable GitHub effects.

The worker may modify its local checkout/workspace. Any desired durable effect is returned through repository-owned invocation-local result/effect transport for later application.

This removes the direct-write bypass that made a post-action Transition Gate insufficient: the worker cannot make its own action selection or durable effect authoritative merely by writing GitHub state.

## Decision 6 — Staged effects are ephemeral transport, not workflow state

Worker-requested effects and local patches are invocation-local transport between the authorized worker phase and repository-owned application phase.

They MUST NOT be treated as:

- durable workflow state;
- an authorization token for another run;
- a second queue or request registry;
- a source of current GitHub state;
- a substitute for a fresh application-time classifier decision.

The implementation may use an Actions artifact or equivalent bounded runner transport when separate jobs are required for credential isolation. Such transport expires with the invocation/cutover mechanics and has no lifecycle meaning.

## Decision 7 — Durable effects require fresh application-time reauthorization

Before applying a staged effect batch, repository-owned application code MUST:

1. fresh-acquire complete current GitHub workflow state;
2. rebuild provenance-qualified classifier input;
3. execute `workflow_dispatch.py` again;
4. prove the same source coordination Issue/role/action is still authorized;
5. verify effect-specific current preconditions such as exact PR/head, current labels/routing, expected Change identity, current branch/ref, or merge/review gates where applicable;
6. validate any requested routing successor against the authoritative topology in `agents/workflow.md`;
7. apply only the bounded authorized effects;
8. fresh-read the resulting durable state and fail closed on contradiction.

If the source became stale while the model was working, none of that stale batch is authorized for normal application. Partial external writes that already occurred are handled by existing action/recovery semantics rather than by inventing transaction/rollback state.

## Decision 8 — `agents/workflow.md` remains the only lifecycle-topology owner

The runtime does not define a second global action DAG.

`agents/workflow.md` remains authoritative for legal successor relationships. Runtime code may parse/validate the canonical topology representation or implement only the minimum adapter necessary to validate a requested successor against that owner, but MUST NOT maintain a separate normative lifecycle graph that can drift.

Role authority remains in role definitions, action-local procedure remains in Skills, and canonical OpenSpec remains capability semantics.

## Decision 9 — Same-role continuation is re-dispatched after durable application

A source action authorization ends when its durable effect batch has been applied/verified or rejected.

After a successful effect batch, runtime performs another complete executable dispatch from the new GitHub state. If the resulting selected role is the same fixed role and work-conserving continuation is otherwise legal, the runtime may invoke the next mapped action. It MUST NOT reuse the previous classifier output as authorization for that continuation.

If the target role differs, the current fixed-role run ends and the next matching role slot owns execution.

## Decision 10 — Serialize runtime executions without creating workflow state

Use one repository-wide non-cancelling GitHub Actions concurrency boundary for Scheduled Agent runtime executions.

A queued run reconstructs current GitHub state only when it actually executes. It does not inherit the earlier run's preflight. Concurrency is execution serialization only and does not create a lock, lease, heartbeat, claim, durable owner, hidden queue semantics, or winner priority in repository workflow state.

## Decision 11 — Cutover requires full mapped-action coverage and no parallel legacy scheduler

The new runtime must support all mapped normal actions before it becomes the authoritative scheduled path. This specifically includes the two demonstrated pre-activation surfaces `Lead / explore-change` and `Lead / propose-change`; protecting only formal successor routing is insufficient.

Legacy ChatGPT Scheduled Tasks MUST be disabled before/when the GitHub Actions runtime becomes authoritative. They are not a fallback normal runtime because an independently waking model would recreate the pre-model bypass.

Manual Human/maintenance operations remain governed by their existing authority semantics, but a normal mapped Agent action executed outside the machine-gated runtime is not an authorized scheduled execution after cutover.

## Decision 12 — Live verification uses ordinary #133 state, not synthetic workflow state

PR-stage tests MUST prove the acquisition adapter, pre-model no-invocation behavior, worker isolation contract, effect reauthorization, stale-stop, and fixed-role matching against fixtures and test doubles. They do not prove that the default-branch scheduled runtime has executed live.

After the runtime implementation is merged to `main`, verify it using whatever ordinary #133 lifecycle state exists then:

1. observe at least one fixed role slot whose role does not match the production classifier's current selected role; the run must stop before a model request and persist enough Actions evidence to prove that no mapped model invocation occurred;
2. observe the matching fixed role slot; it must execute the same default-branch classifier, authorize the exact current #133 Issue/role/action, and only then invoke the model worker;
3. if that worker requests durable effects, the application phase must fresh-revalidate the same source before applying them and persist post-write evidence.

This canary does not require manufacturing a second formal workflow or restoring `Lead / resolve-question` merely to exercise a trigger.

## Decision 13 — Correct prior Agent-owned/Transition-Gate governance wording

Shared governance and affected Skills must stop asserting either of these obsolete models:

- the current ChatGPT Scheduled Agent itself executes repository Python as its own authorization boundary;
- an Issue-comment Transition Gate after action completion is sufficient runtime enforcement.

The new common contract is:

- repository runtime authorizes before worker invocation;
- mapped Skill/role semantics still govern what the authorized worker is trying to accomplish;
- durable effects are applied only through the repository runtime after fresh reauthorization;
- every same-role continuation re-enters executable dispatch.

Implementation MUST audit all mapped Skills for procedure text that assumes direct model-owned durable mutation and update every genuinely affected Skill with explicit traceability rather than silently changing its execution meaning.

## Traceability

- Source Explore: #133 `issuecomment-5373937613`.
- Observation-provenance Reviewer correction: #133 `issuecomment-5377194503`.
- Prior implementation READY: #133 `issuecomment-5379787305` at PR #134 head `0727b030bb9c27d311a390e9d765d4421302abaa`.
- Runtime-consumption implementation finding: #133 `issuecomment-5379837891`.
- Scheduled-Agent capability blocker: #133 `issuecomment-5379922085`.
- Transition-Gate OpenSpec rejection: #133 `issuecomment-5380345857`.
- Existing production classifier: `src/investment_strategy/workflow_dispatch.py`.
- Existing topology owner: `agents/workflow.md`.
- Modified canonical requirement: `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- Added requirement: `Machine-gated runtime authorizes mapped work before model invocation and reauthorizes durable effects`.
- Decisions 1–3 define the pre-model dispatch boundary.
- Decisions 4–7 define worker isolation and durable-effect application.
- Decisions 8–10 preserve topology ownership, continuation semantics, and stateless serialization.
- Decisions 11–12 define cutover/live verification.
- Decision 13 defines governance/Skill correction.

## Risks and mitigations

### Risk: Runtime becomes a second workflow engine

Mitigation: `workflow_dispatch.py` remains the dispatch implementation, `agents/workflow.md` remains topology owner, and runtime code only acquires state, invokes the selected worker, validates/apply effects, and re-dispatches.

### Risk: Worker finds a write credential through shell/repository state

Mitigation: the model-controlled worker phase/job is provisioned without durable GitHub write credentials and without persisted checkout credentials. Write-capable application runs in a separate repository-controlled boundary when credential isolation requires it.

### Risk: Staged effect manifest becomes hidden workflow state

Mitigation: effect transport is invocation-local, expires with the run, cannot authorize a later invocation, and is always rechecked against fresh GitHub state before application.

### Risk: Long model execution races with newer durable state

Mitigation: fresh application-time dispatch and effect-specific guards reject stale output. No stale preflight is carried through to write authorization.

### Risk: Dual scheduler reintroduces the original bypass

Mitigation: full mapped-action coverage is required before cutover and legacy ChatGPT Scheduled Tasks are disabled rather than retained as fallback.

### Risk: Live canary requires illegal/synthetic state

Mitigation: fixed role slots naturally provide both a non-matching pre-model STOP case and the matching authorized invocation on the ordinary post-merge #133 state.
