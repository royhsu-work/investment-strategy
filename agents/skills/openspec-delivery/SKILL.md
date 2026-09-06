---
name: openspec-delivery
description: Reusable OpenSpec-domain procedure for staged delivery, parent-outcome reconciliation, and then-current N-1 buildability.
---

# OpenSpec staged delivery

Load this procedure only when an approved OpenSpec outcome is being delivered in stages or when a
then-current N-1 substrate affects the delivery boundary. It is a procedural adapter for the mapped
action; openspec/config.yaml remains the single normative owner of OpenSpec authoring rules, and
the approved Change and canonical specs remain authoritative for meaning.

## Establish the stage boundary

Before planning or reviewing a staged delivery, record the approved parent outcome and its
requirements, constraints, architecture outcome, and exit criteria. State the current stage
boundary and why that boundary is independently executable, testable, reviewable, mergeable, and
deployable on the then-current N-1 substrate. The stage boundary is a delivery choice; it does not
rewrite the parent outcome.

For the current stage, keep one reconstructable evidence tuple:

- approved parent outcome and constraints;
- current stage boundary;
- parent-outcome coverage;
- N-1 prerequisites;
- stage exit criteria;
- remaining mandatory outcome;
- required continuation.

## Reconcile without scope evaporation

At every stage handoff, account for:

prior-stage completion + current-stage completion + still-mandatory outcome


Use the tuple to show what is complete, what this stage delivers, and what remains mandatory. A
stage can be independently mergeable while the parent outcome remains incomplete. Preserve all
requirements and exit criteria until they are completed or an explicit approved reduction or defer
decision is recorded.

An explicit approved reduction or defer must be distinguishable from omission caused by stage size or
implementation convenience. If mandatory work remains, keep the remaining mandatory outcome and
required continuation explicit and use the existing MORE_IMPLEMENTATION_REQUIRED result through the
current lifecycle. Do not declare the parent complete merely because the current stage is complete.

## Authority and completion boundary

This procedure does not own canonical requirements, Human authority, Action selection, Result
vocabulary, routing, merge gates, or implementation details. It must not create a new Action, a new
Result kind, a lifecycle state, a stage-status label, hidden progress state, parallel artifact graph,
or secondary registry. It only helps a mapped action reconstruct evidence at the action boundary.

When no mandatory outcome remains and all parent exit criteria are met, the mapped lifecycle owner may
use the existing completion path. Otherwise, preserve the required continuation for a later stage.
