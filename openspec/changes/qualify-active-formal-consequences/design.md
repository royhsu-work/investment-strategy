# Design: Qualify active formal consequences

## Decision boundary

The approved parent outcome is machine-decidable consequence eligibility qualified by the existing executable owner from observable current evidence. The concrete scheduled-agent repair applies the #133/#134 decision-atomicity precedent:

```text
authoritative observation set
→ one executable decision surface
→ one structured decision
→ all consequence consumers reuse that decision
```

The final Human decisions are issuecomment-5607080928 and issuecomment-5611740462. The design preserves one Issue, one immutable Change, the two deployment stages, and #218 as a downstream boundary.

## Architecture-precedent disposition

| Candidate delta | Consequence and current owner | Disposition |
| --- | --- | --- |
| Generic machine-decidable consequence rule | `repository-governance` one-authoritative-surface requirement | `CONSOLIDATE`: extend that requirement instead of adding a second generic requirement. |
| Active-formal qualification | Existing scheduled-agent current-state/application owner | `REUSE`: add one domain qualification decision to the existing owner. |
| `ObservationProvenance` result space | Existing Action model/runtime | `NO-DELTA`: reuse `QUALIFIED | INDETERMINATE`. |
| Application correlation | Existing formal result/application evidence chain | `ADD`: add only the minimum identity missing from the current causal binding. |
| Lifecycle ordering | GitHub Issue lifecycle read surface plus existing reconstruction | `REUSE`: use it only for ordering, supersession, and ABA. |
| Continuation carrier | Existing materialization and CarrierRequired owners | `CONSOLIDATE`: extend only the missing post-merge same-Change case. |
| Architecture-precedent discovery | `agents/AGENTS.md` shared governance | `ADD`: add a short hook that points changes back to their consequence and owner before another control concept is retained. |

No new decision owner, workflow graph, or persistent state is required.

## One qualification decision

The existing active-formal owner receives one immutable `QualificationInput` containing:

- exact current Issue, immutable Change, current Action or terminal/close candidate;
- the accepted typed Action/Result and model-derived consequence;
- the minimum exact application request/run correlation produced by Stage 1;
- the exact durable postcondition for that consequence;
- a complete relevant lifecycle observation ordered by durable event identity; and
- the absence of a later relevant mutation that supersedes the binding, including an A→B→C→B sequence.

`qualify_current_formal_consequence(input)` returns only the existing `ObservationProvenance.QUALIFIED` or `ObservationProvenance.INDETERMINATE`. Consumers receive this structured decision. Dispatch and application/lifecycle code do not separately rebuild or reinterpret the same predicates.

Structural validity and value equality may participate in postcondition reconciliation only after qualification. Actor, connector, carrier, timestamp, or physical writer identity does not supply consequence authority. Lifecycle events establish ordering and supersession, not application authorization.

## Decision atomicity and mutation atomicity

The qualification call decides whether a current consequence is eligible. A `QUALIFIED` result does not perform a mutation and does not weaken the existing mutation boundary:

```text
qualification decision
→ fresh application reauthorization
→ exact necessary effect
→ fresh postcondition observation
```

This keeps a single semantic/control decision while preserving effect-specific stale checks, carrier separation, and exact postconditions.

## Stage 1 — evidence producer and continuation capability

Current N-1 already parses typed results, authorizes their exact source, derives the successor/terminal effect, applies it, and observes the postcondition. Stage 1 augments that existing chain with the minimum durable correlation needed to bind those facts uniquely. Current acceptance remains active; the strict qualification consumer is not deployed yet.

Stage 1 also adds the short `agents/AGENTS.md` discovery hook and extends the existing materialization owner for one missing case:

```text
same open Issue
+ same immutable Change
+ prior implementation carrier is exact merged history
+ current repository-derived implement-change remains
+ no eligible current implementation carrier
→ materialize one fresh replacement carrier from current default branch
```

The carrier remains an actuator. The content-addressed manifest, fresh authorization, exact branch/PR identities, CarrierRequired boundary, and postcondition checks remain unchanged.

## Stage 2 — qualification consumer

After Stage 1 is reviewed, merged, active on the default branch, and `finalize-change` returns `MORE_IMPLEMENTATION_REQUIRED`, a later wake uses a fresh carrier. Stage 2:

1. reconstructs complete relevant lifecycle ordering;
2. builds the one `QualificationInput` from current identity, correlation-bearing evidence, model consequence, and exact postcondition;
3. calls the single qualifier;
4. passes its structured result to every active-routing and terminal/close consumer; and
5. deletes the equality-only authority shortcut and any duplicate local reconstruction made redundant by the qualifier.

If relevant lifecycle evidence or any binding dimension is unavailable or incoherent, the qualifier returns `INDETERMINATE` and the existing fail-closed path applies.

## Activation and compatibility

The default-branch merge remains the prospective activation boundary. Stage 2 does not retroactively invalidate or reopen workflows already terminal before activation. An active workflow rerouted or closed after activation without a qualifying current binding is `INDETERMINATE`; there is no migration registry, grandfather flag, or fallback.

`Change: unset` pre-activation behavior bypasses the active-formal qualifier and remains under existing admission semantics. Exact carrier completion becomes eligible only after a later fresh observation binds the application plan to its postcondition. Human gates, merge gates, typed successor derivation, WIP/finish-first, and carrier authority remain with their existing owners.

## Staged-delivery evidence tuple

| Evidence | Stage 1 | Stage 2 |
| --- | --- | --- |
| Parent outcome | Preserved in full | Completed in full |
| N-1 prerequisite | Existing Action/Result application chain and materialization owner | Stage-1 correlation producer and continuation carrier active on default branch |
| Stage boundary | Produce binding; preserve acceptance; enable later carrier | Consume one qualifier; remove equality authority |
| Exit criteria | Correlation, discovery hook, continuation capability, all gates green | Qualified and adverse cases, single-consumer path, all gates green |
| Remaining mandatory outcome | Strict qualification consumption | None after all parent criteria pass |
| Required continuation | Review → merge → finalize → `MORE_IMPLEMENTATION_REQUIRED` | Normal review/merge/finalize/archive lifecycle |

## Verification

Stage 1 tests prove correlation uniqueness, preservation of current acceptance, the shared discovery hook, and the exact post-merge continuation-carrier predicates. Stage 2 tests prove qualified routing/terminal cases, missing or incomplete binding, out-of-band equality, ABA supersession, carrier and pre-activation compatibility, and single-decision consumption.

Each stage runs focused tests, full `pytest`, Ruff check and format check, mypy, strict OpenSpec validation, current required repository checks, and independent exact-revision review.
