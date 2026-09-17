# Design — align-issue-completion-with-archive

## Context

The persistent coordination Issue must remain actionable across proposal, implementation, implementation review/merge, archive creation, archive review, and archive merge. GitHub closing keywords can automatically close a linked Issue when a PR merges into the default branch. Issue #18 demonstrated that an implementation PR carrying an unintended closing linkage can violate this lifecycle by closing the coordination Issue before archive work is complete.

The existing workflow already has the correct authority separation and final-state reconstruction. This change relocates the normal close mutation to the platform side effect of the final Archive PR merge while retaining explicit Lead close as recovery only.

## Goals

- Prevent implementation merges from closing the persistent coordination Issue.
- Make final Archive PR merge the only normal PR-driven Issue completion boundary.
- Preserve all existing revision-bound archive review, authorization, and merge gates.
- Keep lifecycle completion dependent on reconstructed canonical archive state plus observed closed Issue state.
- Provide deterministic recovery when the native close side effect is absent.

## Non-Goals

- No new role or action.
- No new workflow engine, lifecycle status label, lock, lease, or progress state.
- No replacement for repository archive automation.
- No change to Human admission or investment-analysis behavior.

## Decisions

### Decision 1: Closing linkage is archive-only

Implementation and implementation-correction PRs use non-closing references such as `Refs #N`. They must not use GitHub closing keywords or equivalent closing linkage for the persistent coordination Issue.

The final Archive PR uses the repository-approved closing linkage, e.g. `Closes #N`, after the archive branch has been deterministically generated. This makes the platform completion side effect occur at the lifecycle boundary where closure is actually valid.

### Decision 2: Closing linkage is not authority

The presence of Archive PR closing linkage is a structural precondition for the final merge, not authorization. Reviewer archive PASS, Lead exact-revision `MERGE_AUTHORIZED`, unchanged PR head, and current non-contradictory gates remain mandatory.

### Decision 3: Executor verifies linkage before merge

`merge-pr` distinguishes implementation PR and Archive PR context from reconstructed durable state. Implementation merge fails closed if it would close the coordination Issue. Archive merge fails closed if the approved closing linkage is absent or points at the wrong coordination Issue.

This check belongs to the merge safety contract because merge is the mutation that would trigger the platform side effect.

### Decision 4: Archive PR creation makes linkage deterministic

The existing repository archive path should create or document the Archive PR such that its relationship to the persistent coordination Issue is deterministic and testable. The implementation may use repository automation, templates, or generated body metadata consistent with existing architecture; it must not introduce a second archive engine.

The coordination Issue remains the single workflow instance. Change identity is used to correlate archive output with that Issue through existing durable repository/Issue evidence rather than a new progress store.

### Decision 5: Lead observes normal completion; explicit close is recovery

After authorized Archive PR merge, Lead `finalize-archive` reconstructs the merged default branch, canonical spec/archive state, and coordination Issue state. If the Issue is already closed by GitHub, Lead records final completion without another close mutation.

If the Archive PR is correctly merged and canonical archive state is correct but the Issue remains open, Lead uses the existing explicit close capability as recovery and re-observes closed state. This preserves at-least-once reconstructability without depending absolutely on the platform side effect.

### Decision 6: Premature closure fails closed

An Issue closed before authorized Archive PR merge is not lifecycle completion. Scheduled work must not infer success from that state. Recovery may reopen/restore routing only through repository-authorized lifecycle behavior; implementation should make the normal premature-close path impossible by enforcing non-closing implementation PRs.

## Traceability

- Proposal archive-only linkage → modified Executor merge requirement → Decisions 1–3 → Tasks 1–3.
- Proposal native archive completion → modified coordination closure requirement → Decisions 1, 5, 6 → Tasks 2–4.
- Proposal deterministic Archive PR linkage → modified archive mechanics requirement → Decision 4 → Tasks 2–3.
- Proposal no new engine/state → all three modified requirements → Decisions 1–6 → regression/scope checks in Task 4.

## Risks and Mitigations

- GitHub closing semantics may not fire as expected: explicit Lead close remains a bounded recovery after archive state is proven correct.
- A closing keyword can be accidentally added to implementation PR text: merge-precondition tests and governance documentation fail closed before merge.
- Archive PR linkage could target the wrong Issue: Executor verifies the expected persistent coordination Issue before merge.
- Platform side effects could be mistaken for authorization: the spec explicitly preserves independent Reviewer PASS and Lead authorization gates.