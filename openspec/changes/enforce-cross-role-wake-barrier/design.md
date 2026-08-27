## Context

Issue #161 established that the repository currently has two distinct execution identities that must not be conflated: a fresh mapped worker for one machine-selected role/action, and the enclosing Scheduled-Agent wake that may perform fresh redispatch after durable effects. Current canonical `scheduled-agent-workflow` truth already says a role handoff ends the current run, while `agents/AGENTS.md`, `agents/templates/messages.md`, and continuation tests still describe cross-role fresh-worker continuation inside one runtime execution.

The exact Explore baseline is Issue #161 comment `5440915970`. The selected direction is Candidate B: same-role work-conserving continuation is allowed; a cross-role successor is durably selected but is wake-terminal.

## Goals / Non-Goals

**Goals:**
- Make `Role`, not `Action`, immutable for one scheduled wake.
- Preserve repository-owned dispatch as the only selector before every mapped worker.
- Preserve fresh mapped-worker isolation for same-role continuation.
- End the current wake when fresh dispatch selects a role different from the wake's initial role.
- Keep the successor routing/dispatch result intact for ordinary reconstruction by the next wake.
- Enforce the boundary mechanically with focused regression coverage.

**Non-Goals:**
- No formal topology changes in `agents/workflow.md`.
- No fixed Lead/Reviewer/Executor schedule semantics.
- No durable wake-role field, queue, lock, lease, heartbeat, sequence number, retry state, or second dispatcher.
- No change to WIP=1, Human authority, action ownership, routing labels, or dispatch candidate ordering.
- No reopening or rewriting of #155 historical lifecycle evidence.

## Decisions

### 1. `initial_role` is invocation-local wake state

The first repository-owned `AUTHORIZE` decision in a wake establishes `initial_role`. It is runtime-local context only and is never persisted to an Issue, comment, label, OpenSpec artifact, or hidden repository state.

Every subsequent action still begins from a fresh repository-owned dispatch result and a fresh mapped worker. The original role value is used only to decide whether the enclosing wake may consume that fresh continuation immediately.

### 2. Same-role continuation stays work-conserving

After a successful effect batch and fresh dispatch:

- no selected continuation ends the current action normally;
- a selected continuation whose role equals `initial_role` may run in the same wake, but only as a fresh mapped worker that reloads default-branch role/Skill governance and reconstructs current durable state;
- action identity may change while role identity remains fixed.

This preserves existing same-authority liveness such as `Lead / explore-change → Lead / propose-change` without treating action completion as a voluntary yield point.

### 3. Cross-role continuation ends the wake without rewriting routing

If fresh dispatch selects a role different from `initial_role`, the repository keeps that exact durable successor routing and machine selection as current state. The enclosing wake must not invoke the successor worker. A later scheduled wake performs ordinary fresh reconstruction and may select that role under then-current governance.

The wake barrier therefore does not add a queue or defer command and does not alter `AUTHORIZE | NO_WORK | FAIL_CLOSED` dispatch semantics.

### 4. Narrow executable enforcement lives beside effect continuation

`apply_effect_batch()` already fresh-reauthorizes the source, applies effects with postconditions, and returns the newly machine-selected `WorkerRequest` as `ApplyResult.continuation`. The existing `continuation_requires_fresh_wake(source, continuation)` helper is the narrowest repository-owned classification point and currently treats every non-null continuation alike.

Implementation should make this helper classify only a role change as requiring a new wake. Same-role selected work remains a fresh-worker continuation rather than a fresh-wake requirement. The enclosing runner consumes this decision; dispatch selection itself remains unchanged.

Focused tests must distinguish:
- same action / same role: fresh worker may continue in the wake;
- different action / same role: fresh worker may continue in the wake;
- Lead→Reviewer, Reviewer→Executor, Executor→Lead: require a new wake;
- no continuation: no successor worker;
- fresh dispatch remains authoritative regardless of the wake decision.

### 5. Shared prose aligns to capability truth

`agents/AGENTS.md` and `agents/templates/messages.md` must stop implying that cross-role work can run inside the same scheduled execution opportunity. They should reference the same distinction: fresh worker on every action; same-role may remain in the wake; cross-role handoff is a durable ownership transfer and wake-terminal boundary.

`agents/workflow.md` remains the sole topology owner and does not need a new edge or state.

## Risks / Trade-offs

- Cross-role lifecycle latency increases by up to one scheduler wake interval. This is intentional isolation cost and does not affect correctness/liveness because routing is already durable.
- If an enclosing external runner ignores the repository-owned wake classification, prose alone cannot enforce the barrier. Regression coverage therefore must exercise the repository classification boundary, and deployment integration must consume it where same-wake continuation is orchestrated.
- Terminology drift between `worker`, `invocation`, `run`, and `wake` could reintroduce ambiguity. The Change uses `scheduled wake` for the enclosing execution opportunity and `mapped worker` for each fresh role/action execution.

## Migration Plan

No durable-state migration is required. Existing routing tuples remain valid. Once merged to the default branch, later wakes apply the new continuation boundary; historical #155 execution remains historical evidence and is not retroactively invalidated.

## Open Questions

None requiring Human authority. The implementation mechanism is bounded by the exact Explore result and existing canonical capability requirement.
