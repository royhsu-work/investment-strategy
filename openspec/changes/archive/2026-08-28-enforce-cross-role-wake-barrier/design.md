## Context

Issue #161 established that the repository has two distinct execution identities that must not be conflated: a fresh mapped worker for one machine-selected role/action, and the enclosing external Scheduled-Agent wake that may perform fresh redispatch after durable effects. Current canonical `scheduled-agent-workflow` truth and `agents/workflow.md` already say a cross-role handoff ends the current invocation, while shared runtime/presentation text has described cross-role fresh-worker continuation inside one execution opportunity.

The exact Explore baseline is Issue #161 comment `5440915970`. The original selected direction was Candidate B: same-role work-conserving continuation is allowed and a cross-role successor is wake-terminal. Implementation review then established that the repository-owned continuation classifier is not itself an enclosing control boundary for the external ChatGPT Scheduled-Agent wake. A subsequent Candidate D attestation PoC remained `INDETERMINATE` because the available execution environment did not expose a testable Work webhook task surface.

Human decision comment `5452121226`, approved by the later Human-only `human:approved` event `30162729509`, supersedes the earlier enforcement mechanism: choose Option 3 and downgrade the cross-role wake barrier to prompt/model-level enforcement. Machine/script enforcement is no longer required for this Change.

## Goals / Non-Goals

**Goals:**
- Keep `Role`, not `Action`, conceptually immutable for one Scheduled-Agent wake as an authoritative model/governance instruction.
- Preserve repository-owned dispatch as the only selector before every mapped worker.
- Preserve fresh mapped-worker isolation and fresh authoritative reconstruction for every successor action.
- Preserve same-role work-conserving continuation.
- Instruct the current mapped model invocation to end when fresh dispatch selects a different role, leaving the durable successor routing intact for a later wake.
- Align shared default-branch governance/presentation with the existing `agents/workflow.md` cross-role invocation-terminal topology.
- Make the downgraded assurance boundary explicit: this Change does not claim that repository code can mechanically terminate the external ChatGPT execution context.

**Non-Goals:**
- No repository-owned mechanical hard-stop guarantee for the external Scheduled-Agent wake.
- No OpenAI API key and no GitHub Actions-hosted model/Responses API worker.
- No Work wake attestation requirement.
- No formal topology changes in `agents/workflow.md` unless implementation discovers a real contradiction rather than presentation drift.
- No fixed Lead/Reviewer/Executor schedule semantics.
- No durable wake-role field, queue, lock, lease, heartbeat, sequence number, retry state, or second dispatcher.
- No change to WIP=1, Human authority, action ownership, routing labels, or dispatch candidate ordering.
- No reopening or rewriting of #155 historical lifecycle evidence.

## Decisions

### 1. The wake-role boundary is an authoritative model instruction, not repository runtime state

The first repository-owned `AUTHORIZE` decision selected in a Scheduled-Agent wake establishes the role that the active model is instructed to treat as fixed for that wake. The repository does not persist a wake-local `initial_role` and this Change no longer requires repository runtime code to retain or compare one in order to prove external-host isolation.

Every successor action still begins from a fresh repository-owned dispatch result and a fresh mapped worker that reloads current default-branch governance and reconstructs durable state. The wake-role rule constrains what the external model is instructed to execute during the current wake; it does not replace dispatch authorization.

### 2. Same-role continuation stays work-conserving

After durable effects and fresh dispatch:

- no selected continuation ends the current action normally;
- a selected continuation owned by the same role may execute during the same wake as a fresh mapped worker, subject to current governance and ordinary fresh reconstruction;
- action identity may change while the wake-level role instruction remains fixed.

This preserves same-authority liveness such as `Lead / explore-change → Lead / propose-change` without turning every action boundary into a scheduled-wake yield.

### 3. Cross-role continuation is prompt/model-level wake-terminal behavior

When fresh dispatch selects a successor role different from the role being executed by the current wake, current default-branch governance instructs the model to stop the wake after the durable cross-role handoff is complete. The already-persisted successor routing remains current workflow state. A later Scheduled-Agent wake performs ordinary fresh reconstruction and dispatch before that role may execute.

This is intentionally a prompt/model-level behavioral contract. The repository does not claim an unforgeable per-run wake identity, scheduler attestation, or script-owned ability to terminate the external ChatGPT task. Human has explicitly accepted that reduced assurance in Option 3.

### 4. Remove the superseded mechanical wake classifier requirement

The previous design required `continuation_requires_fresh_wake(source, continuation)` and an enclosing runner to mechanically classify same-role versus cross-role continuation. That implementation mechanism is no longer required by the approved contract because the actual external Scheduled-Agent wake is outside the repository-owned process boundary.

Executor should reconcile implementation added solely for that superseded guarantee: remove or simplify wake-specific helper behavior/tests where they no longer serve another approved runtime invariant. This correction must preserve repository-owned dispatch freshness, effect reauthorization/postconditions, durable routing, fresh-worker isolation, same-role liveness, and all unrelated runtime safety behavior.

### 5. Default-branch governance is the prompt contract; scheduler prompts stay bootstrap-only

`agents/workflow.md` remains the topology owner for same-role/cross-role successor relationships. `agents/AGENTS.md` and `agents/templates/messages.md` should align their execution/presentation wording with that topology: same-role continuation may remain in the wake as a fresh worker; cross-role handoff instructs the current invocation to end.

External Scheduled Task prompts should remain neutral bootstrap instructions that load current default-branch governance and obey the resulting wake-terminal decision. They must not copy the workflow DAG, role-specific successor rules, or a durable `initial_role` protocol into external product configuration. This avoids a second drifting policy surface while still implementing the Human-approved prompt/model enforcement boundary.

## Risks / Trade-offs

- Cross-role lifecycle latency may increase by up to one scheduler wake interval when the model follows the wake-terminal instruction. This remains the intended isolation behavior.
- Option 3 deliberately accepts weaker assurance: a prompt/model instruction cannot mechanically prove that the external ChatGPT host terminated or prevent platform/model noncompliance. Repository tests can verify that authoritative governance presents the correct instruction, not that the external host obeyed it.
- Removing the superseded mechanical classifier must not accidentally remove unrelated fresh-dispatch/effect-application protections.
- Terminology drift between `worker`, `invocation`, `run`, and `wake` could reintroduce ambiguity. Use `Scheduled-Agent wake` for the external execution opportunity and `mapped worker` for each fresh role/action execution.

## Migration Plan

No durable-state migration is required. Existing routing tuples remain valid. The earlier mechanical implementation on PR #173 is treated as superseded work to be reconciled after independent OpenSpec review. Once the revised Change is merged to the default branch, later wakes consume the prompt/model-level cross-role termination instruction from authoritative governance. Historical #155 execution remains historical evidence and is not retroactively invalidated.

## Open Questions

None requiring further Human authority. Human comment `5452121226` explicitly accepts Option 3 and removes machine/script enforcement as a requirement for this Change.
