# Change: Preserve parent outcomes across staged OpenSpec delivery

## Why

Issue #180's current-main Explore found a procedural gap in the existing OpenSpec authoring owner. The current openspec/config.yaml already requires single-purpose scope, traceability, vertical slices, RED/GREEN/REFACTOR, strict validation, and bounded complexity. It does not explicitly require delivery decomposition to preserve the complete Human-approved parent outcome when one Change must be delivered in stages.

The Human-confirmed invariant is: outcome is not decomposed; delivery is. Each stage must remain independently executable, testable, reviewable, mergeable, and deployable on the then-current N-1 substrate, while the full parent outcome remains accounted for.

This Change makes that current decision effective at the point where proposals and implementation plans are formed. It does not create another workflow authority or change the Scheduled-Agent Action model.

## What Changes

- Extend openspec/config.yaml with the two staged-delivery authoring rules:
  - recursively decompose delivery until each stage is independently executable, testable, reviewable, mergeable, and deployable on the then-current N-1 substrate;
  - preserve the complete approved parent outcome, requirements, constraints, and exit criteria across all stages.
- Add one reusable OpenSpec-domain procedure at agents/skills/openspec-delivery/SKILL.md for stage coverage, N-1 prerequisites, exit criteria, remaining mandatory outcome, and required continuation.
- Make only the mapped OpenSpec procedures that need this concern compose the reusable procedure: Explore, Change, Review, implementation review, and lifecycle finalization. Existing archive review remains the downstream gate and does not become a second decomposition owner.
- Require Proposal, Design, Tasks, Review, and finalization evidence to reconcile prior-stage completion, current-stage completion, and still-mandatory continuation. An implementation convenience or stage-size decision cannot silently reduce scope.
- Use the existing MORE_IMPLEMENTATION_REQUIRED continuation result when an approved parent outcome remains incomplete. Do not add a stage state, Action, Result kind, label, registry, artifact DAG, or history store.
- Add focused regression coverage for the authoring order, parent-outcome reconciliation, N-1/stage evidence, and preservation of existing Action/Role/Result topology.

## Ownership and canonical contract disposition

openspec/config.yaml is the single normative owner for these OpenSpec authoring conventions. The reusable Skill is an action-specific procedural adapter and cannot weaken the config or approved Change meaning. agents/AGENTS.md and agents/workflow.md remain shared runtime and topology owners and are not modified to duplicate this rule.

No canonical capability spec is changed by this Change. The existing repository-governance ownership matrix already assigns OpenSpec authoring and validation conventions to openspec/config.yaml. The no-changes spec marker records that this is a procedure correction at that existing owner, not a new capability contract or a second proportionality requirement.

## Scope boundaries

In scope:

- the two staged-delivery and parent-outcome-preservation rules in openspec/config.yaml;
- one reusable, progressively loaded OpenSpec delivery procedure;
- conditional composition by the mapped procedures whose action boundaries consume stage reconciliation;
- focused tests and removal of any directly duplicated staged-delivery wording found in those touched procedures.

Out of scope:

- new Scheduled-Agent workflow Actions, Result kinds, lifecycle states, labels, registries, or control-plane mechanisms;
- changes to WIP, finish-first, Human authority, exact-head, carrier, archive, or merge semantics;
- making agents/AGENTS.md or agents/workflow.md an owner of OpenSpec delivery policy;
- reopening #138, #169, #200, or #201;
- mandatory history archaeology for ordinary work;
- a new validator, conformance engine, history database, capability registry, or parallel artifact graph;
- changing current canonical proportionality ownership or rewriting it in another surface.

## Evidence and traceability

- Issue #180 current body and Human-confirmed invariants.
- Explore result comment issuecomment-5559877011, produced from main@77537cf9b8f22a6655ff2e356a9a0059d3f4e94a.
- Current openspec/config.yaml: existing authoring owner and existing complexity/traceability/vertical-slice rules.
- Current repository-governance specification: existing ownership matrix and project-wide proportionality requirement.
- Current executable Action model and workflow projection: no new Action/Result/state is required.
- Current implementation/lifecycle continuation: MORE_IMPLEMENTATION_REQUIRED already represents incomplete approved work.

## Acceptance boundary

The Change is complete only when current default-branch evidence shows:

1. the decision boundary is consumed before solution formation;
2. the subtractive/coverage check precedes retaining any stage-specific addition;
3. each retained delivery mechanism has an exact approved requirement, safety property, or demonstrated failure basis;
4. parent outcome, stage coverage, N-1 prerequisites, exit criteria, and continuation are reconstructable without hidden state;
5. incomplete approved outcome follows the existing continuation path;
6. the existing Action/Role/Result topology and deterministic regression surfaces are unchanged;
7. strict OpenSpec validation, tests, lint, and type checks pass at the exact reviewed revision.
