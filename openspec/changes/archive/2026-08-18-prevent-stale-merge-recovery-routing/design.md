# Design

## Problem shape

The same `Executor / merge-pr` action serves implementation and final Archive PRs. Current merge recovery correctly avoids replaying an already-completed merge mutation, but its routing repair can still be stale: it may reconstruct an earlier merge invocation and rewrite routing even after later lifecycle actions have durably consumed that transition.

The defect is therefore not missing action identity. It is missing consumption detection for the exact recovered transition.

## Decision 1: Keep one merge action and derive context

Do not add lifecycle context to routing and do not split the action surface.

For recovery, derive the merge invocation from existing durable evidence:

- target PR identity;
- implementation/correction versus final Archive PR classification;
- exact accepted head revision;
- applicable Reviewer PASS;
- merge result/merge commit; and
- required linkage/preparation evidence.

This is sufficient to distinguish the two merge uses without new phase state.

## Decision 2: Causal descendants prove consumption

Before recovery mutates routing for an already-completed durable mutation, reconstruct whether valid later same-workflow evidence proves the transition was consumed.

If causal-descendant evidence exists, recovery MUST NOT rewrite canonical routing backward. It may repair only missing non-routing journal evidence that remains required and non-contradictory.

This guard is transition-specific, not a generic forward-only lifecycle rule; ordinary governed correction loops remain legal.

### Implementation merge descendants

For an implementation merge invocation, descendants include a valid post-merge `Lead / finalize-change` result for that merge and any valid descendants of that result, including Archive branch/PR readiness, `ARCHIVE_PR_READY`, archive review, Archive merge, and terminal archive evidence.

### Final Archive merge descendants

For a final Archive merge invocation, descendants include valid `Lead / finalize-archive` evidence for that exact Archive merge, especially `LIFECYCLE_COMPLETE`.

## Decision 3: Ownership

- Shared `agents/AGENTS.md` / canonical `scheduled-agent-workflow` owns the general invariant: recovery of a completed mutation cannot regress routing after its transition is proven consumed by durable causal descendants.
- `agents/skills/merge-pr/SKILL.md` owns concrete implementation/archive recovery reconstruction.
- Tests own #88 regression fixtures and terminal Archive symmetry.

## Safety properties

- No new hidden state or routing field.
- No model-derived lifecycle phase.
- No mutation is replayed merely to rebuild journal evidence.
- Causal descendants must belong to the same persistent coordination Issue/Change and materially correspond to the recovered transition.
- Ambiguous or contradictory descendant evidence fails closed rather than authorizing a routing rewrite.

## Trade-off

Derived reconstruction is more evidence-intensive than a persisted sequence/phase token, but preserves the repository's existing at-least-once/reconstructable model and avoids introducing a second state machine.