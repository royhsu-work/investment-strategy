# Design: Align coordination Issue closure with workflow terminal

## Context

Current workflow closes the coordination Issue as a side effect of final Archive PR merge, then requires `Lead / finalize-archive` to reconstruct terminal state and persist `LIFECYCLE_COMPLETE`. The decision-complete Explore on #115 (`issuecomment-5355262548`) determined that this ordering makes GitHub close state precede the actual terminal verification boundary and forces a normal closed terminal-pending exception into dispatch.

## Decision 1: Use non-closing Archive PR linkage

Final Archive PRs use deterministic non-closing traceability (`Refs #N` or repository-equivalent) and must not contain Issue-closing linkage. This keeps the Issue open across Archive review and merge.

Trade-off: native close is no longer free at merge time, but closing becomes aligned with the role that already owns terminal verification.

## Decision 2: Lead owns terminal completion then close

After exact-head archive Reviewer PASS and Executor merge, routing moves to open `Lead / finalize-archive`. Lead reconstructs the exact reviewed/merged head, canonical archived state, required separate-follow-up trackers, temporary correction/recovery cleanup/retention evidence, and newer material Human input.

When terminal conditions hold, Lead writes `LIFECYCLE_COMPLETE` first, performs the Issue close mutation second, and re-observes `closed` third. The workflow is terminal only after all three facts are reconstructable.

This preserves separation of duties: Reviewer accepts, Executor merges, Lead verifies lifecycle/terminal state. Lead does not merge; Executor does not self-verify workflow terminality.

## Decision 3: Remove normal closed terminal-pending dispatch

Normal workflow work remains open until terminal. Closed + valid completion becomes history and is excluded from normal formal cardinality. Closed without valid completion is not a normal workflow shape; it is contradictory/premature-close recovery input.

This simplifies the happy path without deleting bounded recovery. Existing recovery remains reconstruction-based and fail-closed; no new state label, registry, lock, lease, or hidden cursor is introduced.

## Decision 4: Make final-write interruption idempotent

The durable order is:

```text
terminal reconstruction succeeds
→ persist LIFECYCLE_COMPLETE
→ close Issue
→ re-observe closed
```

If execution stops after the completion result but before close, the next Lead wake reuses the existing result and completes the missing close. If close succeeds but the run stops before re-observation, the next wake observes the existing close and completes terminal reconstruction without a second lifecycle meaning.

Premature manual/accidental close before valid completion remains fail-closed and may be recovered only under the shared bounded premature-close predicate.

## Responsibility / blast radius

- `agents/AGENTS.md`: normal open-until-terminal invariant; cardinality/routing/recovery changes.
- `agents/roles/lead.md`: terminal close ownership follows verified `LIFECYCLE_COMPLETE`.
- `agents/skills/lifecycle-finalize/SKILL.md`: finalize-change creates non-closing Archive PR; finalize-archive writes completion then closes/re-observes.
- `agents/skills/merge-pr/SKILL.md`: Archive merge requires non-closing linkage and hands off while Issue remains open.
- `agents/templates/messages.md` only if presentation wording currently assumes native-close-at-merge; it remains presentation-only.
- canonical `scheduled-agent-workflow`: terminal/linkage/cardinality requirements.
- focused tests cover normal and interrupted paths.

## Traceability

Proposal intent → delta requirements for routing, review/finalize, merge, archive mechanics, and Issue closure → this design → vertical slices in `tasks.md`.

The design intentionally does not absorb #112 invocation-exit semantics or #80 topology-SSOT extraction.
