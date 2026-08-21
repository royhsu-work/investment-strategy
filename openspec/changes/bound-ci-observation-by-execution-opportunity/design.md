# Design

## Context

The shared Invocation Exit taxonomy already has the correct high-level class: an external asynchronous wait is legal only when the exact resource cannot be further consumed within the current legal execution opportunity. #124 added a necessary subsequent-observation floor, but current shared/action-local text then collapses that stronger predicate into a proxy: later nonterminal observation + no other same-authority work.

PR #129 disproves that proxy. Runs can satisfy repeated `in_progress` observations and still become terminal within seconds. The correction should therefore remove the proxy rather than add another observation count.

## Decisions

### 1. Keep one shared Exit class; change its proof rule

Do not add a CI-specific Exit state or another lifecycle action. `agents/AGENTS.md` remains the shared runtime owner. The canonical `scheduled-agent-workflow` requirement states the externally verifiable invariant. A nonterminal observation sequence is resource-state evidence only. It never independently establishes unconsumability.

### 2. Preserve #124's re-observation floor, but not its sufficiency shortcut

A first absent/queued/in-progress observation remains explicit non-exit evidence and requires subsequent observation while legal execution opportunity exists. The later observation is not a magic threshold. If another legal observation can still be executed, bounded observation continues.

### 3. Execution opportunity is invocation-local capability, not durable time state

The positive ordinary async-wait boundary is current evidence that the invocation can no longer legally execute another same-resource observation/consumption while workflow preconditions remain current. This is not represented by a persisted deadline, elapsed CI duration, N observations, sleep/backoff state, polling/retry counters, heartbeat/lease/waiter/scheduler state. Uncatchable termination is handled by later at-least-once reconstruction.

### 4. Keep other Exit classes distinct

- terminal success → consume and continue;
- terminal actionable failure → correct/continue within current authority;
- stale routing/head/precondition → stale/precondition Exit;
- hard tool/permission/runtime boundary after legal recovery is exhausted → hard execution-boundary Exit;
- nonterminal external resource + explicit inability to perform another legal observation now → ordinary async-wait Exit.

### 5. Align only demonstrated trigger-and-consume Skills

`implementation/SKILL.md` and `openspec-change/SKILL.md` both currently repeat the #124 sufficiency shortcut and materially require modification. They should state the action-local observation procedure and defer the decisive Exit classification to shared governance. Do not broaden Reviewer/lifecycle Skills without evidence.

### 6. Make regression evidence sequence + opportunity based

Regression coverage must model observation sequences and whether another legal observation remains executable; it must not accept a bare caller assertion as decisive proof. The exact helper shape is implementation-owned.

## Trade-offs

This rule can keep a scheduled invocation occupied longer than #124's one-reobservation shortcut when CI is genuinely long-running. That is intentional while another legal observation remains executable. The design deliberately does not invent a repository timer or fixed maximum wait.

## Compatibility

- #112 continuation-by-default remains authoritative.
- #124 remains historical provenance; its archived artifacts are unchanged.
- Exact-head validation and later-wake fresh-read rules remain unchanged.
- No workflow topology, role authority, Human boundary, or #111 mutation-recovery behavior changes.
