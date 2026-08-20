# Upstream responsibility provenance

- Upstream repository: `Fission-AI/OpenSpec`
- Upstream Skill path: `skills/openspec-verify-change/`
- Upstream revision: `2826b8889e5223a9a8095d4428b60b56597e1020`
- Local Skill: `agents/skills/implementation-review/SKILL.md`
- Relationship: semantic adaptation of upstream Verify into an independent Reviewer implementation gate.

## Relationship

The local Skill preserves the upstream responsibility of verifying implementation against approved OpenSpec meaning, but separates verification from implementation ownership and binds the gate to the exact current PR head.

## Added responsibilities

- Independent Reviewer ownership with exact-current-head PASS/findings evidence.
- Explicit classification into implementation findings versus specification findings.
- Revision-aware handoff to Executor merge or correction owners.
- Consumption of the repository-owned substantive Human-input freshness/disposition invariant before finalizing the exact-head gate.

Reason: repository separation of duties requires implementation acceptance to be independent from the Executor that produced the change, and gate completion must not silently skip newer material Human input affecting correctness, scope, traceability, or validity.

Maintenance implication: retain independent gate ownership and consequential-boundary consumption when comparing future upstream Verify behavior; new upstream checks may be adopted without collapsing Reviewer/Executor separation. The shared classifier remains owned by `agents/AGENTS.md`.

## Deleted or omitted responsibilities

- Implementation mutation or fixing findings is omitted and owned by Executor.
- Specification repair is omitted and owned by Lead.
- Merge execution is omitted and owned by `Executor / merge-pr` after PASS.

Reason: Reviewer must not modify governed artifacts to make its own gate pass.

Maintenance implication: any future upstream verify-and-fix behavior must remain decomposed across repository owners unless governance explicitly changes.

## Modified responsibilities

- Verification is exact-head and revision-bound rather than a session-local validation step.
- A PASS is durable merge-acceptance evidence but does not waive current merge preconditions.
- Gate completion additionally consumes shared current coordination-Issue Human-input freshness/disposition evidence without granting Human authority.

Reason: at-least-once scheduled execution, later PR changes, and newer material Human input require stale-review protection.

Maintenance implication: reassess upstream verification changes against exact-head coverage, contradiction handling, and the shared consequential-boundary invariant, not only checklist similarity.