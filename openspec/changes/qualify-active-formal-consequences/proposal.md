# Change: Qualify active formal consequences

## Why

Issue #229 applies the decision-atomicity precedent established by #133/#134 and refined by #138/#178 to one current correctness gap. The repository-wide outcome is:

```text
observable current evidence
+ explicit machine-decidable predicates
→ qualification by the existing executable owner of the consequence
→ consequence becomes eligible
```

The current active-formal scheduled-agent path can treat structural/value equality as sufficient current-state provenance. That permits independently reconstructed or superseded evidence to participate in dispatch or lifecycle consequences without one application-owned binding. The repair must reuse the existing owner and decision surface rather than add another provenance or workflow system.

The final Human decisions are issuecomment-5607080928 and issuecomment-5611740462. They supersede conflicting earlier #229 wording while preserving the original outcome, two-stage deployment boundary, and #218 exclusion.

## Architecture decision

One consequence has one decision surface:

```text
authoritative observation set
→ one executable decision surface
→ one structured decision
→ downstream consumers consume the decision
```

For the concrete active-formal consequence:

```text
QualificationInput
→ qualify_current_formal_consequence()
→ QUALIFIED | INDETERMINATE
```

`QualificationInput` combines the exact current Issue/Change/Action identity, accepted Action/Result and model-derived consequence, exact application-owned correlation, exact durable postcondition, complete relevant lifecycle ordering, and proof that no later relevant mutation superseded the binding, including ABA protection. Every dimension must be coherent and fresh for `QUALIFIED`; otherwise the existing fail-closed path consumes `INDETERMINATE`.

Decision atomicity is separate from mutation atomicity. The qualification decision does not replace fresh application reauthorization, exact effects, or postcondition observation.

## What changes

1. Extend the existing `repository-governance` one-authoritative-surface requirement with the generic decision-atomicity/reuse invariant. Before adding a check, guard, qualification, lifecycle rule, gate, carrier rule, or state, the affected consequence and existing owner are identified and the delta is classified as `REUSE`, `CONSOLIDATE`, `NO-DELTA`, or `ADD`.
2. Add the short architecture-precedent discovery hook to `agents/AGENTS.md` during implementation. It applies the canonical invariant without creating another decision owner.
3. Keep the concrete active-formal rule in the existing `scheduled-agent-workflow` owner. Active routing and terminal/close boundaries consume one `QUALIFIED | INDETERMINATE` decision; no consumer independently reconstructs the consequence.
4. Keep `Change: unset` pre-activation behavior, typed successor derivation, Human gates, merge gates, carrier authority, WIP/finish-first behavior, and `openspec/config.yaml` unchanged.
5. Deliver the approved behavior through exactly two implementation slices separated by the existing review, merge, and finalize lifecycle.

## Affected capabilities and surfaces

- Modified capability: `repository-governance`, by modifying its existing one-authoritative-surface requirement.
- Modified capability: `scheduled-agent-workflow`, by modifying its existing active-formal qualification requirement.
- Implementation surfaces: `agents/AGENTS.md` and the existing scheduled-agent evidence, application/materialization, lifecycle-observation, dispatch, and effect owners.
- No capability or configuration delta: Action/Role/Result topology, Human authority, carrier authority, pre-activation `Change: unset`, WIP/finish-first, and `openspec/config.yaml`.

## Delivery boundary

Stage 1 produces the minimum application-owned correlation while preserving current acceptance, adds the architecture-precedent hook, and provides the minimum continuation-carrier capability:

```text
Stage 1 implement-change
→ READY
→ review-implementation
→ PASS
→ merge-implementation-pr
→ default-branch activation
→ finalize-change
→ MORE_IMPLEMENTATION_REQUIRED
```

Stage 2 starts only in a later fresh wake on a fresh implementation carrier based on the then-current default branch. It consumes the Stage-1 evidence plus complete lifecycle ordering through the single qualification decision and removes equality-only authority.

Stages are deployment boundaries, not workflow state. A merged carrier remains read-only. The same open coordination Issue and immutable Change may use one fresh replacement implementation carrier when mandatory post-merge work remains and no eligible current carrier exists.

## Acceptance boundary

Stage 1 is complete when one reviewed revision:

1. emits the minimum durable application-owned correlation for new formal consequences;
2. binds accepted Action/Result, exact application authorization, model-derived consequence, and exact durable postcondition while preserving current acceptance;
3. adds the short default-branch architecture-precedent discovery hook; and
4. enables exactly one fresh replacement implementation carrier for mandatory same-Issue/same-Change continuation after the prior carrier is exact merged history.

Stage 2 is complete when one later reviewed revision:

1. builds one `QualificationInput` from current formal identity, the Stage-1 binding, exact postcondition, and complete lifecycle ordering;
2. produces one `QUALIFIED | INDETERMINATE` decision consumed by dispatch and application/lifecycle consumers;
3. rejects missing, incomplete, stale, ambiguous, contradictory, equality-only, out-of-band, or ABA-superseded evidence through the existing fail-closed path;
4. preserves pre-activation and carrier compatibility; and
5. removes the equality-only authority shortcut without introducing a competing decision path.

## Scope boundaries

In scope are the two named canonical capabilities, the `agents/AGENTS.md` discovery hook, existing scheduled-agent executable owners, minimum correlation evidence, complete relevant lifecycle ordering, continuation-carrier materialization, and focused regressions.

Out of scope are #218; new Action/Role/Result or persistent workflow/stage state; registries, ledgers, cursors, leases, receipt lifecycles, policy engines, second DAGs, generic provenance services, fallback/migration behavior, historical Issue rewriting, and unrelated product behavior. Historical Issues, PRs, archived Changes, and active Changes remain evidence or review input and do not become competing authority.
