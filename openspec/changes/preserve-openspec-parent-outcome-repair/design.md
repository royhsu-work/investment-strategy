# Design: Preserve parent outcomes across staged OpenSpec delivery

## Current decision boundary

The current default-branch evidence establishes:

- openspec/config.yaml owns OpenSpec authoring and validation conventions;
- repository-governance owns the project-wide proportionality requirement and ownership boundaries;
- agents/AGENTS.md owns shared Scheduled-Agent invariants;
- agents/workflow.md presents topology;
- the executable Action model owns Action, Role derivation, transitions, Result vocabulary, selection, and deterministic effects;
- existing MORE_IMPLEMENTATION_REQUIRED is the legal continuation when approved work remains incomplete.

The implementation must consume that boundary before forming a solution. The staged-delivery rule must not be copied into shared runtime governance or workflow topology.

## D1 — Put the authoring rule at the existing owner

Extend the existing config rules with the smallest wording that makes the Human-confirmed invariant operational:

1. if one approved outcome is too large for one independently executable delivery boundary, recursively split delivery;
2. every stage records its parent-outcome coverage, N-1 prerequisites, stage exit criteria, remaining mandatory outcome, and required continuation;
3. completion is the reconciliation of prior-stage completion, current-stage completion, and still-mandatory continuation;
4. only an explicit approved reduction or defer decision can remove parent scope.

This is an authoring predicate, not a new runtime state. It is evaluated in the current Change artifacts and evidence.

## D2 — One conditionally loaded procedural adapter

Add agents/skills/openspec-delivery/SKILL.md as one reusable procedure. It owns only the mechanics needed when an action is handling staged OpenSpec delivery:

- establish the approved parent outcome and current stage boundary;
- run remove, reuse, consolidate, and existing-owner checks before proposing stage-specific additions;
- record the minimum stage evidence;
- reconcile completed, current, and remaining mandatory outcome;
- distinguish explicit approved reduction/defer from implementation-driven omission;
- hand incomplete approved work to the existing MORE_IMPLEMENTATION_REQUIRED path.

It does not own routing, Action selection, Result vocabulary, Human authority, canonical requirements, validation infrastructure, history, or implementation details. When the concern is absent, the procedure is not loaded.

## D3 — Minimal mapped composition

The mapped procedure references are conditional and action-local:

| Mapped procedure | Load condition | Responsibility |
| --- | --- | --- |
| openspec-explore | feasibility or delivery scope may require staging | establish parent outcome, N-1 feasibility, and stage boundary |
| openspec-change | Proposal, Design, or Tasks are staged | record coverage and continuation without scope evaporation |
| openspec-review | reviewing a staged OpenSpec plan | independently check current authority, subtraction, and reconciliation |
| implementation-review | verifying a staged implementation | check prior/current/remaining outcome evidence against the exact revision |
| lifecycle-finalize | deciding implementation or archive readiness | prevent completion while mandatory parent outcome remains unaccounted for |

Implementation itself continues to follow the existing Tasks and current Action boundary; it does not gain a new shared framework. Archive review remains the existing independent final gate and consumes finalization evidence when needed.

## D4 — Subtractive-first and evidence rule

The procedure applies this order to any retained stage-specific concept:

1. remove it;
2. reuse an existing artifact, test, procedure, or owner;
3. consolidate with an existing concept;
4. use the existing ownership layer;
5. only if those are insufficient, retain an addition and record its exact approved requirement, concrete safety property, or demonstrated failure mode.

Stage size, implementation convenience, hypothetical reuse, and historical precedent are not sufficient justifications. History may be consulted only when current evidence is insufficient for rationale, ambiguity, conflict, provenance, or forensic investigation.

The staged-delivery procedure itself is justified by the exact Human-approved Issue #180 invariant and by the demonstrated #138 delivery/scope-loss failure context already recorded in the current Issue. It adds no state or enforcement engine.

## D5 — Regression surface

Reuse existing repository tests and CI surfaces. Add focused structural/procedure regressions that assert:

- config contains the staged-delivery authoring predicate at its existing owner;
- the reusable Skill contains the exact order and no routing/registry/state authority;
- mapped procedures reference the Skill conditionally without copied normative definitions;
- a staged evidence example cannot claim completion while mandatory parent outcome remains unaccounted for;
- explicit approved reduction/defer is distinguishable from accidental omission;
- Action, Role, Result, transition, selection, and current deterministic validation surfaces remain unchanged.

Do not introduce a new validator framework. Machine-decidable workflow invariants remain covered by the existing executable model and regression tests.

## D6 — Delivery-stage assessment

This Change is one independently mergeable stage on the current N-1 substrate. Its parent outcome is the procedure correction; its stage covers config owner, one reusable adapter, required mapped composition, focused tests, and full quality gates.

- Parent-outcome coverage: all Issue #180 exit criteria.
- N-1 prerequisites: current config/Skills/test harness, existing Action model, existing continuation result.
- Stage exit criteria: exact-head PR passes semantic review, implementation review, tests, lint, type checks, and strict OpenSpec validation.
- Remaining mandatory outcome after this stage: none.
- Required continuation: none when all exit criteria pass; if a stage is intentionally partial, finalization must retain the existing MORE_IMPLEMENTATION_REQUIRED continuation and cannot declare the parent complete.
