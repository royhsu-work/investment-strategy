# Design: Qualify active formal consequences

## Decision boundary

The approved parent outcome is machine-decidable consequence eligibility qualified by the existing executable owner from observable current evidence. The concrete scheduled-agent repair applies the #133/#134 decision-atomicity precedent:

```text
authoritative observation set
→ one executable decision surface
→ one structured decision
→ all consequence consumers reuse that decision
```

The controlling Human decisions are issuecomment-5607080928, issuecomment-5611740462, issuecomment-5612882299, issuecomment-5614126835, and issuecomment-5619420395. The latest correction preserves one Issue, one immutable Change, exactly two deployment stages, bounded untrusted `EFFECT_REQUEST` ingress, and #218 as a downstream boundary, while replacing the flawed Stage-1 same-invocation qualification mechanism.

## Architecture-precedent disposition

| Candidate delta | Consequence and current owner | Disposition |
| --- | --- | --- |
| Generic machine-decidable consequence rule | `repository-governance` one-authoritative-surface requirement | `CONSOLIDATE`: extend that requirement instead of adding a second generic requirement. |
| Active-formal qualification | Existing scheduled-agent current-state/application owner | `REUSE`: add one domain qualification decision to the existing owner. |
| `ObservationProvenance` result space | Existing Action model/runtime | `NO-DELTA`: reuse `QUALIFIED | INDETERMINATE`. |
| Application correlation | Existing formal result/application evidence chain | `ADD`: bind the existing chain to one exact, fresh-verified application/request execution identity that is unique to that execution; tuple-only correlation and Evidence-Ref aliasing are insufficient. |
| Fresh-continuation reconstruction | Existing formal-evidence/current application owner | `CONSOLIDATE`: reconstruct intended current qualification from durable repository evidence; remove same-invocation `_formal_evidence_observed` authority without creating another store or owner. |
| Known application rejection diagnostics | Existing application decision/repository-governance rejection contract | `REUSE`: emit failed classification and relevant effect/identity/parser evidence from the same evaluation; no second predicate reconstruction or decision owner. |
| Lifecycle ordering | GitHub Issue lifecycle read surface plus existing reconstruction | `REUSE`: use it only for ordering, supersession, and ABA. |
| Continuation carrier | Existing materialization and CarrierRequired owners | `CONSOLIDATE`: extend only the missing post-merge same-Change case. |
| Architecture-precedent discovery | `agents/AGENTS.md` shared governance | `ADD`: add a short hook that points changes back to their consequence and owner before another control concept is retained. |

No new decision owner, workflow graph, registry, ledger, cursor, stage state, or other persistent workflow state is required.

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

## Stage 1 — durable evidence producer, fresh continuation, and continuation capability

Current N-1 already parses typed results, authorizes their exact source, derives the successor/terminal effect, applies it, and observes the postcondition. It also has an invocation-local `_formal_evidence_observed` set. A fresh `GitHubEffectAdapter` begins with that set empty; therefore a repository-derived successor can be rejected after an exact validation/carrier/application boundary even when invocation N already produced the durable evidence. Preserving that mechanism is not acceptable.

Stage 1 augments the existing chain with the minimum durable application correlation/binding and changes current qualification reconstruction so intended accepted cases remain accepted across a fresh adapter/application boundary from durable repository evidence. Invocation-local `_formal_evidence_observed` is not required for eligibility, and the old formal result is not replayed or recreated solely to repopulate local memory. Stage 1 deliberately does not activate the full strict Stage-2 `QualificationInput` lifecycle/ABA consumer yet.

The regression boundary is exact:

```text
invocation N
→ accepted typed Action/Result
→ exact application authorization/correlation
→ exact durable repository postcondition
→ validation/carrier/application boundary
→ invocation N+1 creates a fresh GitHubEffectAdapter
→ current qualification reconstructed from durable repository evidence
→ repository-derived successor remains eligible
```

The existing application decision is also the diagnostic owner. When a known predicate fails, the same evaluation that rejects the effect exposes its machine-readable classification and relevant expected/observed effect, identity, or parser evidence. Aggregate diagnostic text may remain, but it does not replace the structured evidence and no second evaluator reconstructs the predicate.

Stage 1 also adds the short `agents/AGENTS.md` discovery hook and extends the existing materialization owner for one missing case:

```text
same open Issue
+ same immutable Change
+ prior implementation carrier is exact merged history
+ current repository-derived implement-change remains
+ no eligible current implementation carrier
→ materialize one fresh replacement carrier from current default branch
```

The carrier remains an actuator. The content-addressed manifest, fresh authorization, exact branch/PR identities, bounded untrusted `EFFECT_REQUEST` ingress, CarrierRequired boundary, and postcondition checks remain unchanged.

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

`Change: unset` pre-activation behavior bypasses the active-formal qualifier and remains under existing admission semantics. Exact carrier completion becomes eligible only after a later fresh observation binds the application plan to its postcondition. Human gates, merge gates, typed successor derivation, WIP/finish-first, bounded untrusted `EFFECT_REQUEST` ingress, and carrier authority remain with their existing owners.

## Staged-delivery evidence tuple

| Evidence | Stage 1 | Stage 2 |
| --- | --- | --- |
| Parent outcome | Preserved in full | Completed in full |
| N-1 prerequisite | Existing Action/Result application chain, durable GitHub evidence surfaces, and materialization owner | Stage-1 durable binding/fresh-continuation repair and continuation carrier active on default branch |
| Stage boundary | Produce durable binding; repair fresh reconstruction; preserve intended accepted cases; expose same-evaluation rejection evidence; enable later carrier | Consume one strict qualifier; remove equality authority |
| Exit criteria | N→N+1 fresh-adapter regression, correlation, rejection evidence, discovery hook, continuation capability, all gates green | Qualified and adverse cases, single-consumer path, all gates green |
| Remaining mandatory outcome | Strict full qualification consumption with complete lifecycle ordering/ABA | None after all parent criteria pass |
| Required continuation | Review → merge → finalize → `MORE_IMPLEMENTATION_REQUIRED` | Normal review/merge/finalize/archive lifecycle |

## Verification

Stage 1 tests prove correlation uniqueness, the exact N→N+1 fresh-adapter regression, preservation of intended accepted cases without invocation-local memory or replay/recreation of an old formal result, same-evaluation machine-readable rejection detail, the shared discovery hook, and the exact post-merge continuation-carrier predicates. The N→N+1 regression must fail on current N-1 and pass after Stage 1.

Stage 2 tests prove qualified routing/terminal cases, missing or incomplete binding, out-of-band equality, ABA supersession, carrier and pre-activation compatibility, and single-decision consumption.

Each stage runs focused tests, full `pytest`, Ruff check and format check, mypy, strict OpenSpec validation, current required repository checks, and independent exact-revision review.


## Latest implementation correction — exact application/request identity

The Human-approved correction in issuecomment-5619420395 refines Stage 1's minimum binding. The existing application bridge's exact, fresh-verified request/event identity is the binding anchor for one application chain. The application-derived consequence, authorization revision, and exact durable postcondition remain part of the same existing chain. A deterministic tuple of Issue, Change, Role, Action, Result kind, and default-branch revision may describe the chain but cannot uniquely identify it; Evidence-Ref remains evidence and is not a fallback correlation.

The correction adds two bounded regressions within Slice 1: a collision test proving that different exact request identities do not share a binding even when every tuple field is equal, and an actual bridge test that crosses the validation/application boundary and executes a fresh `--validation-passed` continuation without replaying the old result or depending on local adapter memory. It also rechecks the existing implementation-resource bookkeeping relaxation; because N-1 already demonstrates legal fresh-wake continuation, arbitrary non-OpenSpec files alongside `tasks.md` are removed from that bookkeeping exception unless a concrete #229 safety or failure case proves they are needed.

This is a Stage 1 correction, not a third stage or new workflow state. Existing application, evidence, materialization, CarrierRequired, Action/Result, and fresh postcondition owners remain authoritative.
