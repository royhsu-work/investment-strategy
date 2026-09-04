# Design: Enforce invocation exit proof

## Context

Issue #112 `issuecomment-5360318078` established that the current work-conserving contract expresses the desired continuation behavior but does not positively govern the final return decision. #107 demonstrated premature returns at intermediate actionable points, while #115 has since settled the workflow-terminal boundary that Invocation Exit must consume rather than redefine.

The canonical `scheduled-agent-workflow` specification already has one requirement that owns the selected-action termination/yield boundary: `Selected Scheduled Agent actions are work-conserving within an invocation`. This Change must strengthen that existing owner rather than introduce a parallel requirement for the same behavior.

The affected capability is repository-governed Scheduled-Agent execution only. The Change must preserve role authority, one selected workflow/fixed invocation role, exact-revision safety, current asynchronous-resource semantics, #111 mechanical recovery ownership, and #80 workflow-topology ownership.

## Decision 1: Strengthen the existing canonical work-conserving owner

`agents/AGENTS.md` remains the authoritative runtime owner of invocation-wide execution semantics, and the existing canonical work-conserving requirement remains the sole capability owner of the termination/yield contract. Modify that complete requirement to add one positive contract:

```text
before return
    ↓
classify current evidence against bounded legal Exit classes
    ↓
proven Exit → return allowed
no proven Exit → continue current selected workflow
```

The complete MODIFIED future-state requirement preserves every still-applicable canonical scenario/content while strengthening the return boundary with continuation-by-default and positive Exit Proof. Role files do not duplicate the taxonomy. Mapped Skills consume the shared rule only where their local procedure currently creates a concrete return/yield boundary.

This is deliberately stronger than adding more `MUST NOT yield after X` sentences and deliberately narrower than adding a second capability requirement: the default branch already accumulated correct negative rules and existing termination categories, yet #107 showed that an intermediate state could still be treated as an implicit stopping point.

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

## Decision 3: Preserve adjacent canonical ownership instead of duplicating algorithms

The strengthened work-conserving requirement must not absorb adjacent responsibilities:

- #111 remains the owner of how Executor mechanically recovers repository-mutation failures. The modified requirement only consumes the resulting fact: a recoverable failure is not a hard Exit; a hard Exit requires evidence that applicable same-authority recovery/disposition cannot legally continue.
- Existing at-least-once/asynchronous-resource rules remain authoritative for how a just-triggered exact resource is observed. The modified requirement adds only the return proof: first absent/queued/in-progress observation is not Exit Proof; a genuinely unconsumable exact-resource wait can be.
- Existing catchable-exception requirements remain authoritative for exception capture, retry legality, recovery, and disposition. The modified requirement does not restate that algorithm.
- #115 remains authoritative for workflow terminal. Invocation Exit may consume a true terminal fact, but does not redefine terminal topology.
- #80 remains separate future workflow-topology ownership work.

Action-local Skill edits should therefore be minimal consumers/clarifications, not private copies of the Exit taxonomy.

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

- Proposal / Explore result → strengthened canonical owner: Requirement `Selected Scheduled Agent actions are work-conserving within an invocation`.
- Complete MODIFIED requirement → shared runtime owner: `agents/AGENTS.md`.
- Complete MODIFIED requirement → action-local consumers: only mapped Skills with concrete local continuation/yield wording; do not duplicate taxonomy.
- Complete MODIFIED requirement → executable verification: focused deterministic Exit Proof fixture plus existing workflow/governance regressions.
- Config tasks rule → vertical slices use RED → GREEN → REFACTOR → VERIFY and complete only with full quality/OpenSpec gates.

## Trade-offs

A positive proof taxonomy adds a small explicit classification step before return, but removes open-ended model discretion at the highest-risk boundary. Keeping that step inside the existing canonical owner avoids dual authority; keeping it internal avoids lifecycle/state complexity while allowing future mapped actions to consume the same invariant without copying it.

No alternative lock, runtime engine, scheduler-side continuation state, persistent exit token, or parallel termination requirement is justified because current repository reconstruction and durable action evidence already provide the facts needed to make the decision.
