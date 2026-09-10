# Change: Qualify active formal consequences

## Why

Issue #229 applies the decision-atomicity precedent established by #133/#134 and refined by #138/#178 to one current correctness gap. The repository-wide outcome is:

```text
observable current evidence
+ explicit machine-decidable predicates
→ qualification by the existing executable owner of the consequence
→ consequence becomes eligible
```

The current active-formal scheduled-agent path can treat structural/value equality or invocation-local observation as sufficient current-state provenance. That permits independently reconstructed, superseded, or freshly continued evidence to participate in dispatch or lifecycle consequences without one application-owned binding that can be reconstructed from durable repository evidence. The repair must reuse the existing owner and decision surface rather than add another provenance or workflow system.

The controlling Human decisions are issuecomment-5607080928, issuecomment-5611740462, issuecomment-5612882299, and the later correction issuecomment-5614126835. The latest correction supersedes only the earlier Stage-1 mechanism premise that “current acceptance remains unchanged”: Stage 1 must preserve the intended accepted cases while removing the same-invocation `_formal_evidence_observed` dependency. It preserves the original outcome, exactly two deployment stages, bounded untrusted `EFFECT_REQUEST` ingress, and #218 exclusion.

## Architecture decision

One consequence has one decision surface:

```text
authoritative observation set
→ one executable decision surface
→ one structured decision
→ downstream consumers consume the decision
```

For the concrete active-formal consequence, the final Stage-2 contract remains:

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
4. Stage 1 adds the minimum durable application binding and repairs fresh continuation: after invocation N has produced the exact durable repository-owned evidence required by the current Action and execution crosses validation/carrier/application boundaries, invocation N+1 with a fresh `GitHubEffectAdapter` reconstructs the intended current qualification from durable repository evidence. Same-invocation `_formal_evidence_observed` memory is not authority, and an old formal result is not replayed or recreated solely to make the successor eligible. The full strict Stage-2 qualifier is not activated in Stage 1.
5. Reuse the existing repository-governance machine-readable rejection contract (`NO-DELTA` to its owner): when the existing application decision knows which predicate failed, the same evaluation exposes its failed classification plus relevant effect/identity/parser expected/observed evidence. Aggregate `effect precondition rejected` text may accompany that evidence but is not the only diagnostic. No second predicate reconstruction or decision owner is added.
6. Keep `Change: unset` pre-activation behavior, typed successor derivation, Human gates, merge gates, carrier authority, WIP/finish-first behavior, bounded untrusted `EFFECT_REQUEST` ingress, and `openspec/config.yaml` unchanged.
7. Deliver the approved behavior through exactly two implementation slices separated by the existing review, merge, and finalize lifecycle.

## Affected capabilities and surfaces

- Modified capability: `repository-governance`, by modifying its existing one-authoritative-surface requirement. Its existing generic machine-readable application-rejection requirement is reused without another normative owner.
- Modified capability: `scheduled-agent-workflow`, by modifying its existing active-formal qualification requirement and making fresh-continuation reconstructability a lasting invariant.
- Implementation surfaces: `agents/AGENTS.md` and the existing scheduled-agent evidence, application/materialization, lifecycle-observation, dispatch, and effect owners.
- No capability or configuration delta: Action/Role/Result topology, Human authority, carrier authority, pre-activation `Change: unset`, WIP/finish-first, bounded `EFFECT_REQUEST` ingress, and `openspec/config.yaml`.

## Delivery boundary

Stage 1 produces the minimum durable application-owned correlation and binding, repairs fresh-continuation reconstruction while preserving intended accepted cases, exposes existing application rejection evidence from the same decision evaluation, adds the architecture-precedent hook, and provides the minimum continuation-carrier capability:

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
2. binds accepted Action/Result, exact application authorization, model-derived consequence, and exact durable postcondition while preserving intended accepted cases;
3. proves the N→N+1 fresh-continuation regression: invocation N produces the exact durable repository-owned evidence, crosses the validation/carrier/application boundary, invocation N+1 creates a fresh `GitHubEffectAdapter`, and qualification plus the repository-derived successor remain reconstructable without invocation-local memory or replay/recreation of an old formal result;
4. exposes a known application predicate rejection through the existing decision owner with machine-readable failed classification and relevant effect/identity/parser evidence from that same evaluation;
5. adds the short default-branch architecture-precedent discovery hook; and
6. enables exactly one fresh replacement implementation carrier for mandatory same-Issue/same-Change continuation after the prior carrier is exact merged history.

Stage 2 is complete when one later reviewed revision:

1. builds one `QualificationInput` from current formal identity, the Stage-1 binding, exact postcondition, and complete lifecycle ordering;
2. produces one `QUALIFIED | INDETERMINATE` decision consumed by dispatch and application/lifecycle consumers;
3. rejects missing, incomplete, stale, ambiguous, contradictory, equality-only, out-of-band, or ABA-superseded evidence through the existing fail-closed path;
4. preserves pre-activation and carrier compatibility; and
5. removes the equality-only authority shortcut without introducing a competing decision path.

## Scope boundaries

In scope are the two named canonical capabilities, the `agents/AGENTS.md` discovery hook, existing scheduled-agent executable owners, minimum durable application binding, fresh-continuation reconstruction, same-evaluation machine-readable rejection evidence, complete relevant lifecycle ordering, continuation-carrier materialization, and focused regressions.

Out of scope are #218; new Action/Role/Result or persistent workflow/stage state; registries, ledgers, cursors, leases, receipt lifecycles, policy engines, second DAGs, generic provenance services, fallback/migration behavior, historical Issue rewriting, and unrelated product behavior. Historical Issues, PRs, archived Changes, and active Changes remain evidence or review input and do not become competing authority.
