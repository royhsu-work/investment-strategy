# Change: Preserve parent outcomes across staged OpenSpec delivery

## Why

Issue #180's current-main Explore found an authoring gap in the existing OpenSpec owner. The current openspec/config.yaml already defines single-purpose Changes, traceability, vertical slices, RED/GREEN/REFACTOR, strict validation, and bounded scope. It does not explicitly require delivery decomposition to preserve the complete Human-approved parent outcome when one Change must be delivered in stages.

The Human-confirmed invariant is: outcome is not decomposed; delivery is. Each stage must remain independently executable, testable, reviewable, mergeable, and deployable on the then-current N-1 substrate, while the full parent outcome remains accounted for.

This Change formalizes that staged-delivery contract at the existing OpenSpec ownership surface. It does not redesign the Scheduled-Agent control plane or create another lifecycle authority.

## What Changes

- Extend openspec/config.yaml with the two staged-delivery authoring rules:
  - recursively decompose delivery until each stage is independently executable, testable, reviewable, mergeable, and deployable on the then-current N-1 substrate;
  - preserve the complete approved parent outcome, requirements, constraints, and exit criteria across all stages.
- Add one reusable OpenSpec-domain procedure at agents/skills/openspec-delivery/SKILL.md for parent-outcome coverage, N-1 prerequisites, stage exit criteria, remaining mandatory outcome, and required continuation.
- Make only the mapped OpenSpec procedures that need this concern compose the reusable procedure: Explore, Change, Review, implementation review, and lifecycle finalization. Existing archive review remains the downstream gate.
- Require Proposal, Design, Tasks, Review, and finalization evidence to reconcile prior-stage completion, current-stage completion, and still-mandatory continuation. A stage-size or implementation decision cannot silently reduce scope.
- Use the existing MORE_IMPLEMENTATION_REQUIRED continuation result when an approved parent outcome remains incomplete. Do not add a stage state, Action, Result kind, label, registry, artifact graph, or workflow mechanism.
- Add focused regression coverage for stage evidence, parent-outcome reconciliation, N-1 prerequisites, and preservation of the existing Action/Role/Result topology.

## Ownership and canonical contract disposition

openspec/config.yaml is the single normative owner for these OpenSpec authoring conventions. The reusable Skill is an action-specific procedural adapter and cannot weaken the config or approved Change meaning. agents/AGENTS.md and agents/workflow.md remain shared runtime and topology owners and are not modified to own this delivery rule.

No canonical capability spec is changed by this Change. The existing repository-governance ownership matrix already assigns OpenSpec authoring and validation conventions to openspec/config.yaml. The no-changes spec marker records that this is an authoring/procedure correction at that existing owner, not a new capability contract.

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
- a parallel artifact graph, hidden progress state, or duplicated governance owner;
- changing current canonical proportionality ownership or rewriting it in another surface.

## Evidence and traceability

- Issue #180 current body and Human-confirmed staged-delivery invariants.
- Explore result comment issuecomment-5559877011, produced from main@77537cf9b8f22a6655ff2e356a9a0059d3f4e94a.
- Current openspec/config.yaml and its existing OpenSpec authoring rules.
- Current repository-governance specification and ownership matrix.
- Current executable Action model and workflow projection.
- Current implementation/lifecycle continuation: MORE_IMPLEMENTATION_REQUIRED already represents incomplete approved work.

## Acceptance boundary

The Change is complete only when current default-branch evidence shows:

1. delivery stages are independently executable, testable, reviewable, mergeable, and deployable on the then-current N-1 substrate when decomposition is needed;
2. the full parent outcome, requirements, constraints, and exit criteria are reconciled across prior, current, and remaining work;
3. minimum stage evidence is reconstructable without hidden state;
4. incomplete approved outcome follows the existing continuation path, while only an explicit approved reduction or defer decision removes scope;
5. the existing Action/Role/Result topology and existing regression surfaces are unchanged;
6. strict OpenSpec validation, tests, lint, and type checks pass at the exact reviewed revision.
