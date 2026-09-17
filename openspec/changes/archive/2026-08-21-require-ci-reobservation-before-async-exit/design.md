# Design: Require CI re-observation before async Exit

## Context

Explore #124 `issuecomment-5366724594` found that #112 already owns the right shared rule: first absent/queued/in-progress exact-resource observation is non-exit evidence and return requires positive Exit Proof. The observed #110 recurrence happened because the decisive async-wait fact remains insufficiently executable: `tests/test_invocation_exit_proof.py` accepts `exact_resource_unconsumable` as a caller-provided boolean and the mapped exact-run procedures do not define a minimum observation sequence that derives it.

The correction must preserve the existing Exit taxonomy, no-timer/no-counter/no-waiter constraints, exact-head validation, fixed invocation role, and action authority.

## Decision 1: Keep the existing work-conserving requirement as the sole normative owner

Modify only `Selected Scheduled Agent actions are work-conserving within an invocation`. Do not add a parallel CI-wait requirement or a new Exit class.

The shared runtime rule becomes explicit that a just-triggered exact required resource needs a sequence of observations before ordinary async-wait Exit can be proven:

```text
trigger/push exact target R
        ↓
first fresh observation
        ├─ terminal → consume result
        └─ absent / queued / in_progress
                   ↓
           mandatory subsequent fresh observation
                   ├─ terminal → consume result
                   ├─ stale routing/head/precondition → existing stale Exit
                   └─ still absent/nonterminal
                              ↓
                    no other same-authority work actionable
                              ↓
                    existing ASYNC_WAIT Exit may be proven
```

This makes the positive evidence reconstructable without adding runtime state.

## Decision 2: Use a fixed minimum re-observation floor, not time-based waiting

The requirement is **at least one subsequent fresh observation after the first nonterminal observation**. It is a procedural floor, not a promise that CI will finish within an invocation.

Why this boundary:

- it directly closes the #110 defect, which returned after the first absent discovery read;
- it is objectively testable;
- it does not invent a wall-clock timeout, sleep interval, polling counter, background waiter, heartbeat, lease, or durable wait state;
- it keeps the existing legal async-wait class for genuinely still-pending resources;
- it avoids an unbounded busy-wait.

A later nonterminal observation is not globally sufficient on its own: the action also requires current routing/revision/preconditions and no other immediately actionable same-authority work before async-wait Exit.

## Decision 3: Regression derives wait eligibility from an observation sequence

Replace the current test-seam shortcut where `exact_resource_unconsumable=True` directly selects `ASYNC_WAIT` with a small deterministic observation-sequence model. The model should represent the facts needed for the approved behavior, for example:

- first observation status;
- whether a subsequent fresh observation occurred;
- subsequent status;
- whether terminal failure is actionably correctable;
- whether routing/head/preconditions became stale;
- whether other same-authority work remains actionable;
- attempted return.

The classifier derives `CONTINUE`, terminal-result consumption, existing `ASYNC_WAIT`, or existing stale Exit from those facts. It remains a test seam only, not production scheduler/dispatcher code.

## Decision 4: Only concrete trigger-and-consume Skills change

Current concrete action-local consumers are:

- `agents/skills/implementation/SKILL.md`: implementation push/checkpoint work can trigger Python Quality/OpenSpec Validate and immediately consume those exact-head gates.
- `agents/skills/openspec-change/SKILL.md`: Propose/Resolve authoring can trigger exact OpenSpec validation and immediately consume it for readiness.

Both retain their existing action authority. Their exact-run sections should state the mandatory subsequent fresh observation floor and terminal-result behavior, while referencing the shared Exit invariant rather than copying the generic taxonomy.

Do not modify Reviewer or lifecycle Skills merely because they can inspect CI. This Change is bounded to demonstrated same-action trigger-and-consume behavior.

## Decision 5: Preserve adjacent ownership

- `agents/AGENTS.md` remains shared runtime owner of continuation, async observation, and Exit Proof.
- `agents/workflow.md` remains workflow topology owner and is unchanged.
- #111 remains mechanical mutation-recovery ownership and is unchanged.
- Exact-head validator identity rules remain unchanged.
- Skill-maintenance traceability from #110 records the two mapped Skills as `Modified`; no Skill is added/removed.

## Traceability

- Explore #124 `issuecomment-5366724594` → proposal Why/What → MODIFIED `scheduled-agent-workflow` work-conserving requirement.
- MODIFIED requirement → Decision 1/2 observation sequence → action-local consumers in Decision 4.
- Regression scenarios → Decision 3 sequence-derived test seam.
- Skill-maintenance declaration → Decision 4 and implementation/review comparison.

## Trade-offs

One mandatory re-observation is intentionally a minimum, not a comprehensive CI waiting strategy. A larger fixed retry count or elapsed-time policy would be more arbitrary and would recreate the timer/counter machinery #112 deliberately excluded. The chosen floor prevents the demonstrated first-read exit while retaining a bounded legal async-wait path when the resource genuinely remains pending.