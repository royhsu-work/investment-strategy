# Design: Enforce invocation exit proof

## Context

Issue #112 `issuecomment-5360318078` established that the current work-conserving contract expresses the desired continuation behavior but does not positively govern the final return decision. #107 demonstrated premature returns at intermediate actionable points, while #115 has since settled the workflow-terminal boundary that Invocation Exit must consume rather than redefine.

The affected capability is repository-governed Scheduled-Agent execution only. The Change must preserve role authority, one selected workflow/fixed invocation role, exact-revision safety, current asynchronous-resource semantics, #111 mechanical recovery ownership, and #80 workflow-topology ownership.

## Decision 1: Shared governance owns positive Exit Proof

`agents/AGENTS.md` remains the authoritative owner of invocation-wide execution semantics. Add one positive contract:

```text
before return
    ↓
classify current evidence against bounded legal Exit classes
    ↓
proven Exit → return allowed
no proven Exit → continue current selected workflow
```

The bounded Exit classes are defined by the capability requirement. Role files do not duplicate the taxonomy. Mapped Skills consume the shared rule only where their local procedure currently creates a concrete return/yield boundary.

This is deliberately stronger than adding more `MUST NOT yield after X` sentences: the default branch has already accumulated correct negative rules, yet #107 showed that an intermediate state could still be treated as an implicit stopping point.

## Decision 2: Exit Proof is not durable workflow state

Exit Proof is an internal precondition for returning from an invocation. It is reconstructed from already-governed durable/current evidence such as:

- canonical cross-role HANDOFF plus observed target routing;
- action/lifecycle terminal results;
- exact Human-reserved authority evidence;
- exact awaited asynchronous-resource evidence;
- stale/concurrency/precondition observations;
- fail-closed contradiction/disposition evidence; and
- EXECUTION_EXCEPTION plus the applicable action-defined recovery/disposition boundary.

Do not add an `exit:*` label, workflow action, status, progress comment, timer/counter, heartbeat, lease, waiter registry, or hidden cursor. The absence of a new durable state keeps at-least-once reconstruction unchanged.

## Decision 3: Preserve local ownership instead of duplicating algorithms

The shared Exit taxonomy must not absorb adjacent responsibilities:

- #111 remains the owner of how Executor mechanically recovers repository-mutation failures. This Change only consumes the resulting fact: a recoverable failure is not a hard Exit; an unrecoverable legal boundary may be.
- Current asynchronous-resource rules remain authoritative for how a just-triggered exact resource is observed. This Change adds only the return test: first absent/queued/in-progress observation is not Exit Proof; a genuinely unconsumable exact-resource wait can be.
- #115 remains authoritative for workflow terminal. Invocation Exit may use a true terminal fact, but does not redefine terminal topology.
- #80 remains separate future workflow-topology ownership work.

Action-local Skill edits should therefore be minimal consumers/clarifications, not private copies of the seven Exit classes.

## Decision 4: Executable regression uses a bounded classification seam

Regression safety should not depend only on Markdown phrase presence. Add a small deterministic test fixture/model that classifies representative current-evidence states as `CONTINUE` or one legal Exit category. It is a test seam for the approved behavior, not a production dispatcher or second workflow engine.

Coverage must exercise at least:

- RED → GREEN continues;
- failed-but-actionable validation continues;
- first absent/queued/in-progress exact CI observation continues;
- verified Slice with remaining work continues;
- same-role Lead successor continues;
- completed Reviewer cross-role handoff exits;
- genuine exact-resource async wait exits;
- stale/precondition loss exits fail-closed;
- hard unrecoverable execution boundary exits;
- no proven Exit class rejects return.

## Traceability

- Proposal / Explore result → shared positive Exit Proof: Requirement `Invocation exit requires positive proof`.
- Requirement → shared runtime owner: `agents/AGENTS.md`.
- Requirement → action-local consumers: only mapped Skills with concrete local continuation/yield wording; do not duplicate taxonomy.
- Requirement → executable verification: focused deterministic Exit Proof fixture plus existing workflow/governance regressions.
- Config tasks rule → vertical slices use RED → GREEN → REFACTOR → VERIFY and complete only with full quality/OpenSpec gates.

## Trade-offs

A positive proof taxonomy adds a small explicit classification step before return, but removes open-ended model discretion at the highest-risk boundary. Keeping that step internal avoids lifecycle/state complexity while allowing future mapped actions to consume the same invariant without copying it.

No alternative lock, runtime engine, scheduler-side continuation state, or persistent exit token is justified because current repository reconstruction and durable action evidence already provide the facts needed to make the decision.
