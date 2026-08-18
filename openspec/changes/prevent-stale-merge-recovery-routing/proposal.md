# Change: Prevent stale merge recovery from regressing routing

## Why

Issue #88 demonstrated a crash-recovery defect: an already-consumed implementation `merge-pr` transition was replayed after downstream Archive lifecycle evidence existed, regressing canonical routing back to `Lead / finalize-change` and causing unnecessary lifecycle replay.

The repository already has revision-bound merge acceptance and at-least-once recovery, but recovery does not yet require proof that the specific earlier transition remains causally unconsumed before repairing canonical routing.

## What Changes

- Add a causal-descendant consumption guard to recovery of already-completed durable mutations/handoffs.
- Keep one `Executor / merge-pr` action; derive implementation versus Archive merge context from existing PR/gate/linkage evidence rather than adding routing phase/context state.
- Permit recovery to repair missing journal evidence for an already-completed merge when safe, but prohibit backward routing repair when durable same-workflow descendant evidence proves that merge transition was already consumed.
- Specialize implementation and final Archive merge recovery with concrete descendant evidence.
- Add regression coverage reproducing the #88 routing regression and the symmetric final-Archive terminal case.

## Scope

In scope:
- Scheduled-Agent at-least-once/routing recovery semantics.
- `Executor / merge-pr` crash recovery.
- Regression tests for stale consumed-transition recovery.

Out of scope:
- Splitting `merge-pr` into separate implementation/archive actions.
- Adding global phase/status, sequence numbers, locks, leases, or a second workflow DAG.
- Prohibiting legitimate governed correction loops.

## Capabilities

### Modified capabilities
- `scheduled-agent-workflow`: prevent crash recovery of an earlier completed mutation from overwriting canonical routing once durable causal-descendant evidence proves that transition was consumed.

## Evidence

- #88 implementation PR #89 merge result and handoff were followed by `Lead / finalize-change`, Archive PR #90, and Archive review evidence.
- A later implementation-merge recovery replay nevertheless repaired routing backward to `Lead / finalize-change`; a subsequent Lead recovery had to restore `Reviewer / review-archive`.
- #91 Explore `ACTION_RESULT` records the decision-complete root cause and bounded remediation.