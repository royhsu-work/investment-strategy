# Design: Preserve parent outcomes across staged OpenSpec delivery

## Current ownership boundary

The current default-branch evidence establishes:

- openspec/config.yaml owns OpenSpec authoring and validation conventions;
- repository-governance owns the project-wide ownership matrix and shared proportionality boundary;
- agents/AGENTS.md owns shared Scheduled-Agent invariants;
- agents/workflow.md presents lifecycle topology;
- the executable Action model owns Action, Role derivation, transitions, Result vocabulary, selection, and effects;
- existing MORE_IMPLEMENTATION_REQUIRED is the continuation when approved work remains incomplete.

This Change stays within that boundary. It makes the staged-delivery contract explicit at the existing OpenSpec owner and uses one action-specific procedure where stage reconciliation is needed. It does not copy this rule into shared runtime or topology documents.

## D1 - Put the authoring rule at the existing owner

Extend the existing config rules with the smallest wording needed for the Human-confirmed invariant:

1. if one approved outcome is too large for one independently executable delivery boundary, recursively split delivery;
2. every stage records its parent-outcome coverage, N-1 prerequisites, stage exit criteria, remaining mandatory outcome, and required continuation;
3. completion reconciles prior-stage completion, current-stage completion, and still-mandatory continuation;
4. only an explicit approved reduction or defer decision can remove parent scope.

This is an OpenSpec authoring rule, not a new runtime state. It is represented in the current Change artifacts and review evidence.

## D2 - One conditionally loaded procedural adapter

Add agents/skills/openspec-delivery/SKILL.md as one reusable procedure. It owns only the mechanics needed when an action handles staged OpenSpec delivery:

- establish the approved parent outcome and current stage boundary;
- record the minimum stage evidence;
- reconcile completed, current, and remaining mandatory outcome;
- distinguish explicit approved reduction or defer from implementation-driven omission;
- hand incomplete approved work to the existing MORE_IMPLEMENTATION_REQUIRED path.

It does not own routing, Action selection, Result vocabulary, Human authority, canonical requirements, or implementation details. When staged delivery is not present, the procedure is not loaded.

## D3 - Minimal mapped composition

The mapped references are conditional and action-local:

| Mapped procedure | Load condition | Responsibility |
| --- | --- | --- |
| openspec-explore | feasibility or delivery scope may require staging | establish parent outcome, N-1 feasibility, and stage boundary |
| openspec-change | Proposal, Design, or Tasks are staged | record coverage and continuation without scope evaporation |
| openspec-review | reviewing a staged OpenSpec plan | independently check coverage and reconciliation |
| implementation-review | verifying a staged implementation | check prior/current/remaining outcome evidence at the exact revision |
| lifecycle-finalize | deciding implementation or archive readiness | prevent completion while mandatory parent outcome remains unaccounted for |

Implementation continues to follow the existing Tasks and current Action boundary. Archive review remains the existing independent final gate and does not become a second decomposition owner.

## D4 - Reconcile parent scope without hidden state

Each staged artifact records the same small evidence tuple in its local text:

- approved parent outcome and constraints;
- current stage coverage;
- N-1 prerequisites;
- stage exit criteria;
- remaining mandatory outcome;
- required continuation, or the explicit approved reduction/defer decision that removed it.

Proposal, Design, Tasks, Review, implementation review, and finalization use that evidence to account for prior-stage completion plus current-stage completion plus still-mandatory continuation. A stage can be independently mergeable while the parent remains incomplete; finalization must then select the existing MORE_IMPLEMENTATION_REQUIRED continuation.

No separate stage database, artifact graph, counter, label, or workflow state is introduced.

## D5 - Regression surface

Reuse existing repository tests and CI surfaces. Add focused structural and procedure regressions that assert:

- config contains the staged-delivery authoring predicate at its existing owner;
- the reusable Skill contains the minimum evidence tuple and existing continuation path;
- mapped procedures reference the Skill conditionally without copied normative definitions;
- a staged evidence example cannot claim completion while mandatory parent outcome remains unaccounted for;
- an explicit approved reduction or defer is distinguishable from accidental omission;
- Action, Role, Result, transition, selection, and existing validation surfaces remain unchanged.

Existing executable model and CI tests remain the enforcement surface for machine-decidable workflow invariants.

## D6 - Delivery-stage assessment

This Change is one independently mergeable stage on the current N-1 substrate. Its parent outcome is the staged-delivery contract; its stage covers the config owner, one reusable adapter, required mapped composition, focused tests, and full quality gates.

- Parent-outcome coverage: all Issue #180 invariants and decision-complete exit criteria.
- N-1 prerequisites: current config/Skills/test harness, existing Action model, and existing continuation result.
- Stage exit criteria: exact-head semantic and implementation review pass; full tests, lint, type checks, and strict OpenSpec validation pass.
- Remaining mandatory outcome after this stage: none.
- Required continuation: none when all exit criteria pass; if implementation is partial, finalization must retain the existing MORE_IMPLEMENTATION_REQUIRED continuation and cannot declare the parent complete.
