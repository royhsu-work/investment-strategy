## Context

The repository has one executable finite Action model. `Role` is derived from `Action`, and
`next_action` derives one successor from the current Action and a bounded typed result. Current
finalization can describe a material OpenSpec/canonicalization/lifecycle defect, but the transition
table only retains `finalize-change` for its generic blocked result. Current question resolution can
return to implementation or semantic review, but cannot explicitly return to the post-merge
lifecycle owner when no semantic revision remains.

The default-branch application is now the single authorization and mutation boundary. It fresh
reconstructs the Issue/Change/Action and current revision, derives Role from Action, applies only
the exact requested content capability, derives routing from the typed result, and verifies the
postcondition. Transport/run records and worker claims remain evidence or stale-binding input, not
authority.

## Goals / Non-Goals

**Goals:**

- Make the two Human-approved transitions executable and mechanically reject unrelated successors.
- Keep `SPEC_BLOCKER` bounded to a material specification/canonicalization/lifecycle-contract
  defect outside the current Lead action's authority.
- Make `LIFECYCLE_READY` express only the no-material-revision, valid-merged-lifecycle return case.
- Preserve independent semantic review for material OpenSpec corrections and the existing
  implementation path for `READY`.
- Cover the behavior with exact transition and fresh-application regressions.

**Non-goals:**

- No new Action, state machine, result family beyond the one bounded result, or recovery subsystem.
- No change to transport, scheduler cadence, archive automation, or #159's approved outcome.
- No worker authority over Issue, Role, Action, target, successor, routing, or mutation.
- No relaxation of stale/replay/no-rewind/fail-closed or exact-revision/exact-head gates.

## Decisions

### Decision 1: Reuse `SPEC_BLOCKER` for the missing finalize edge

`SPEC_BLOCKER` already represents a material specification boundary in the finite result vocabulary.
The transition table adds it only to `finalize-change`, and maps it to `resolve-question`. Lead
must use it only after fresh evidence distinguishes a material semantic/canonicalization/lifecycle
defect from a progressing external wait, a known action-local mechanical recovery, a genuine Human
decision, or ambiguous evidence. Those other cases retain their existing action-local result or
fail-closed path.

### Decision 2: Add exactly `LIFECYCLE_READY` for the return edge

`LIFECYCLE_READY` is a bounded result of `resolve-question`, not a persistent state. It is legal only
when the question is resolved without a material semantic OpenSpec revision, the already-merged
implementation remains valid, and the post-merge lifecycle is again the legal consumer. The
application derives `finalize-change`; it does not accept a worker-selected successor.

### Decision 3: Preserve the existing material-correction and implementation branches

Material OpenSpec correction continues to return `READY_FOR_OPENSPEC_REVIEW` and therefore obtains a
fresh independent `review-openspec` gate. An implementation-ready resolution continues to return
`READY` and derive `implement-change`. The new edge does not skip either gate or merge boundary.

### Decision 4: Keep authority in current repository state

The worker may return only the bounded result, evidence, and content-addressed work-product
references. Application re-reads the current default branch and source Issue/Action before applying
effects, rejects stale authorization revisions, and verifies the routing postcondition. A dispatch
Artifact or transport correlation is not replayed as application authority.

## Safety and Invariants

- Canonical durable state remains Issue lifecycle + immutable Change + `action:<action>`.
- One Action is executed per wake; the successor waits for a later fresh dispatch.
- WIP=1, finish-first, Human authority, independent exact-revision review, exact-head merge safety,
  no duplicate Change/branch/PR, and normal archive ownership remain unchanged.
- Stale, replayed, contradictory, incomplete, ambiguous, provenance-incomplete, or no-rewind
  violations fail closed.
- No worker gains tree/commit/ref/PR/routing authority.
- `RECOVERY_DECISION_REQUIRED`, where retained as diagnosis in lifecycle evidence, does not create
  a new durable state and does not replace the bounded ownership transition.

## Traceability

| Design decision | Governed behavior |
| --- | --- |
| Reuse `SPEC_BLOCKER` for material finalize defects | `finalize-change + SPEC_BLOCKER -> resolve-question` |
| Add bounded `LIFECYCLE_READY` | `resolve-question + LIFECYCLE_READY -> finalize-change` |
| Preserve existing result branches | `READY_FOR_OPENSPEC_REVIEW -> review-openspec`; `READY -> implement-change` |
| Fresh application authority | current default-branch reconstruction, exact preconditions, postconditions, and one-wake successor persistence |

