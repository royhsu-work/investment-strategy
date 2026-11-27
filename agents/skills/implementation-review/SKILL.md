---
name: implementation-review
description: Reviewer procedure for exact-head independent review of completed implementation.
---

# Implementation Review

Mapped Action: Reviewer / review-implementation.

Fresh-read the carrier, base, files, tasks, quality runs, applicable OpenSpec gate, Human freshness
and prior findings. For an open non-Draft carrier, require the exact implementation head to equal
the current PR head R. For a closed+merged carrier, review the immutable historical PR head with
current default-branch revision, merge metadata, ancestry and all in-scope post-merge repair changes.
Bind PASS to both `Revision: <historical PR head>` and `Default-Branch-Revision: <current main SHA>`.
Cover all material unreviewed changes since applicable independent baseline B and the complete state
at R; checkpoints do not advance B. The exact-current-head gate is mandatory; the semantic OpenSpec
bookkeeping exception does not weaken it.

For material repository Skill maintenance/review, load agents/skills/skill-creator/SKILL.md and
agents/skills/skill-creator/references/repository-governance.md as procedural input, not runtime authority.
Do not add, remove, restore or manufacture `human:approved` or `intake:approved`.

## Conditional staged-delivery composition

For a stage of an approved parent outcome, load agents/skills/openspec-delivery/SKILL.md. Evaluate the
approved stage against its own exit criteria and dependencies; reconcile completed and still-mandatory
work and carry required downstream acceptance forward to its applicable gate.

## Review method

1. **DERIVE** — Independently reconstruct expected behavior and observable closure from approved
   proposal, applicable specs, design, tasks, canonical/config context and prior findings. Derive
   the oracle before using Executor tests; distinguish source facts, inference and unresolved claims.
2. **INSPECT** — Trace real affected callers/interfaces through actual production owners to
   effects/outputs. Read changed and competing owners and tests; examine scope, stale/replay/no-rewind,
   effect authorization, carrier separation and unrelated-file changes.
3. **CHALLENGE** — Construct the smallest contrasting input, boundary/failure case or alternative
   that discriminates each material acceptance predicate. Seek caller-visible defects even with
   GREEN CI. Use safe actual public-seam probes and contract-preserving I/O substitutes when supported,
   or inspectable source/CI evidence. Bind observations to actual source, chronology, revision and
   provenance; distinguish demonstrated failure from unavailable proof, never fabricate a run.
4. **VERIFY** — For executable behavior, load agents/skills/tdd/SKILL.md; verify independent oracle,
   public test seam and actual source-bound intended pre-implementation RED then minimum GREEN for
   each behavior before the next cycle. Static, syntax, import, setup, fixture or unrelated failure
   is not RED; retrospective tests do not establish Test First. Verify focused/full exact-revision
   quality, exact validation, task markers/checkpoints and stage coverage. For material procedural
   changes, inspect actual fixed-input before/after decisions, consulted revisions and any applicable
   independent-discovery evidence; known-case rehearsal is not independent discovery. Check
   Skill maintenance traceability: every material Skill must be declared; a differently classified or
   undeclared change is a finding.
5. **REFACTOR** — Own proactive refactoring assessment. Load agents/skills/codebase-design/SKILL.md
   for affected responsibilities, interfaces, seams or tests. Investigate cohesion, coupling,
   locality, duplication/SSOT and unnecessary abstractions through observable consequences:
   remove -> reuse -> consolidate -> existing owner. Verify test replacement or retirement preserves
   still-applicable unique regression, safety and compatibility through verified equivalent or
   stronger coverage or authoritative contract retirement. Do not require a preferred pattern.
6. **DECIDE** — Fresh-disposition substantive Human input. For each blocking finding, identify the
   violated approved requirement or invariant, evidence at the reviewed revision, delivery stage or gate
   it blocks and observable condition that would close it. Distinguish the defect from any suggested
   implementation; assess alternative fixes and counterevidence against the same closure condition in
   independent re-review. Keep harmless improvements advisory, without new acceptance conditions.
   For review-implementation, legal results are PASS, FINDINGS, SPEC_BLOCKER, HUMAN_DECISION_REQUIRED, BLOCKED.
   Return one structured result: FINDINGS for proven implementation defects, SPEC_BLOCKER for
   specification defects requiring Lead, HUMAN_DECISION_REQUIRED for reserved decisions, BLOCKED for
   unqualified evidence. Fail closed rather than accepting missing proof. Exact qualified PASS
   derives merge-implementation-pr in the executable Action model. A merged-carrier PASS never
   authorizes reopening or rewriting the carrier. Reviewer does not modify its own target, merge,
   mutate routing, select a PR, or execute the successor.
