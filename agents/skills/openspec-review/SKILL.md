---
name: openspec-review
description: Reviewer procedure for independent exact-revision OpenSpec semantic review and gate results.
---

# OpenSpec Review

Mapped Action: Reviewer / review-openspec.

Fresh-read current default-branch governance, Issue/Change/PR, exact review target R, applicable
semantic baseline B, Human input, canonical specs, all Change artifacts, config and exact-R
validation. Review all material semantic changes in (B, R] that remain unreviewed and the complete state at R;
bookkeeping does not advance B. Successful mechanical OpenSpec validation is not semantic PASS evidence,
even when strict validation passes.

When openspec/config.yaml declares schema: spec-driven, load
agents/skills/openspec-semantic-adapter.md. For material repository Skill maintenance or review,
load agents/skills/skill-creator/SKILL.md and
agents/skills/skill-creator/references/repository-governance.md. These resources are procedural input,
not runtime authority.

## Conditional staged-delivery composition

For staged delivery load agents/skills/openspec-delivery/SKILL.md and reconcile completed, current
and still-mandatory parent outcome on then-current N-1; the reference is procedural input.

## Review method

1. **DERIVE** — Before using candidate claims, independently reconstruct the current decision boundary:
   Human-approved outcomes, invariants, exclusions, constraints, acceptance consequences, applicable
   same-Issue Explore result and its supporting sources, canonical owners, and exact B/R. Dereference
   evidence, not a summary; distinguish source facts, inference and unresolved claims.
2. **CONFORMANCE** — Inspect each artifact against its responsibility: proposal why/what/scope,
   delta externally verifiable normative behavior, design structure/ownership/trade-offs, tasks
   observable implement/verify slices. Apply existing config and semantic adapter, including
   complete delta blocks, canonical Purpose, valid explicit zero-delta and scope; preserve every
   still-applicable scenario/content in MODIFIED requirements. Strict GREEN cannot excuse responsibility defects.
3. **CHALLENGE** — For every material semantic boundary, test each material acceptance predicate
   with the smallest contrasting case that could change PASS to FINDINGS. Try failure, bypass,
   replay or competing ownership; reuse a case only if it discriminates each covered predicate.
   For material interfaces, architecture, feasibility, testability or slice design, load
   agents/skills/codebase-design/SKILL.md and compare with simpler owners, interfaces and vertical
   slices through real caller or observable consequences. Establish executability, testability,
   reviewability, mergeability and deployability on current N-1, not merely a coherent document.
   Consume openspec/specs/repository-governance/spec.md via agents/proportionality.md (not a competing authority);
   apply remove -> reuse -> consolidate -> existing ownership layer. Retaining or adding a mechanism
   without a current requirement, concrete safety property, or demonstrated failure mode, or despite
   a sufficient simpler alternative, is existing FINDINGS. Harmless alternatives are advisory.
   - REALIZE: Bind each proof to current default/review execution, exact candidate revision,
     staged/future state, or unavailable evidence. Verify actual source, time/revision and provenance
     for ordering, replay, supersession and review-time knowledge; do not use future evidence as current proof.
   - CLOSE: For reuse, consolidation, one-owner, removal or no-delta, identify the decided consequence
     and owner and disposition competing responsibilities and affected boundaries. OpenSpec review closes design/spec/task-level meaning;
     review-implementation closes exact code-level removal, consumer coverage and runtime postconditions.
4. **TRACE** — Review reverse-first tasks -> design -> specs -> proposal, then forward
   proposal -> specs -> design -> tasks at R; use canonical context for valid zero-delta work.
   Both directions must be complete before PASS. Verify scope, scenarios, invariants, upstream evidence, trade-offs and
   Skill maintenance traceability; an undeclared material Skill, misclassification or Formatting drift
   is a finding. Traceability does not substitute for independent correctness.
5. **DECIDE** — Fresh-disposition substantive Human input at the consequential boundary.
   Return exact-revision PASS only when every material predicate and both traces meet the existing
   gate. Use FINDINGS for a material defect with evidence, affected requirement and observable
   closure; use HUMAN_DECISION_REQUIRED, NO_GO or BLOCKED when applicable under the existing Action
   contract; fail closed on missing, contradictory, stale or unqualified semantic evidence.
   Preserve staged coverage and the original approved outcome. Return one structured result;
   the executable model derives the successor. Do not edit the review target or execute a successor.
