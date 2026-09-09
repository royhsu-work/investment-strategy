# Tasks: Qualify active formal consequences

## Parent outcome and staged delivery contract

Parent outcome: correctness-critical repository consequences become eligible only after observable current evidence is qualified by the existing executable owner through explicit machine-decidable predicates. The scheduled-agent active-formal provenance gap is the concrete proof and current delivery target; it does not replace the parent outcome.

Stage 1 boundary: produce mandatory application-correlation-bearing evidence inside the existing formal Action/Result evidence while preserving current acceptance, and provide the minimum existing-owner capability required to materialize a fresh Stage 2 implementation carrier after the Stage 1 merge.

Stage 2 boundary: on a fresh carrier based on the then-current default branch, consume that correlation plus complete lifecycle-event ordering at the existing current-state, dispatch, and application boundaries; remove equality-only authority and enforce `QUALIFIED` / `INDETERMINATE`.

Lifecycle meaning:

```text
Stage 1 implement-change
→ READY
→ review-implementation
→ PASS
→ merge-implementation-pr
→ MERGED
→ finalize-change
→ MORE_IMPLEMENTATION_REQUIRED
→ later fresh wake / Stage 2 implement-change
```

These are delivery boundaries within one Issue and immutable Change. The merge creates the default-branch activation boundary; a same-Action continuation does not.

N-1 prerequisites:

- current default-branch governance and the finite Action/Role/Result model;
- complete current Issue snapshot reconstruction and current `ObservationProvenance` plumbing;
- existing formal Action/Result parsing, application reauthorization, derived successor/terminal effects, CarrierRequired handling, and exact postcondition observation;
- the existing content-addressed materialization owner and exact implementation-carrier identity checks;
- complete lifecycle-event evidence as an authoritative read surface for ordering and supersession; and
- existing quality, strict OpenSpec validation, exact-revision, and independent review gates.

Stage 1 exit criteria: every new repository application transition emits the minimum application-owned correlation; the correlation binds accepted Action/Result, application authorization, model-derived consequence, and exact durable postcondition; current acceptance remains; the minimum continuation-carrier capability is present; and no new workflow state/protocol/registry exists.

After Stage 1 implementation is reviewed, merged, and observed on the default branch, `finalize-change` must preserve the remaining mandatory Stage 2 outcome through the existing `MORE_IMPLEMENTATION_REQUIRED` result. The successor is executed only by a later fresh dispatch.

Stage 2 exit criteria: the existing owners consume correlation and complete lifecycle ordering; one current binding is `QUALIFIED`; missing/out-of-band/equality-only/incomplete/contradictory/ABA-superseded state is `INDETERMINATE` and fails closed; carrier and `Change: unset` compatibility remain; the equality shortcut is removed; and all parent exit criteria and quality gates are green.

## Slice 1 — Produce correlation-bearing formal evidence and continuation capability (Stage 1)

Trace: parent outcome -> `repository-governance` invariant -> existing application authorization/evidence and materialization owners.

- [ ] 1.1 RED: add focused tests showing the existing formal result/postcondition chain lacks a machine-verifiable application-correlation binding, while preserving a fixture for the current acceptance path.
- [ ] 1.2 GREEN: add the minimum application-owned correlation field or identity to the existing formal Action/Result evidence and bind it to the exact accepted source, application authorization, model-derived consequence, and durable postcondition.
- [ ] 1.3 GREEN: extend the existing materialization owner only as needed to establish a fresh implementation carrier from the then-current default branch after the prior carrier has merged, reusing the same Issue, immutable Change, content-addressed ingress, exact postconditions, and CarrierRequired boundary.
- [ ] 1.4 REFACTOR: reuse the existing formal evidence parser, application bridge, postcondition observation, and carrier plan; remove any duplicate receipt, transport, stage registry, or multi-stage protocol.
- [ ] 1.5 VERIFY: run the focused Stage-1 evidence and continuation-carrier tests, full Python tests, Ruff check, Ruff format check, mypy, and strict OpenSpec validation at the exact revision; verify current acceptance and the mandatory Stage-2 continuation remain explicit.

## Slice 2 — Consume latest qualified transition at existing boundaries (Stage 2)

Trace: correlation-bearing formal evidence + complete lifecycle ordering -> current-state reconstruction/dispatch -> application/effect qualification.

- [ ] 2.1 RED: add focused fixtures for a qualified repository-owned transition, a direct/out-of-band route or close, current equality without a current binding, incomplete lifecycle observation, the A→B→C→B ABA sequence, exact carrier completion observed on a later wake, and `Change: unset` intake.
- [ ] 2.2 GREEN: reconstruct a complete relevant lifecycle observation, select the latest applicable transition for the same Issue/Change, consume the correlation-bearing application evidence and exact postcondition, and classify the current formal observation as `QUALIFIED` only when one coherent binding exists; otherwise use existing `INDETERMINATE` / fail-closed handling.
- [ ] 2.3 GREEN: make dispatch and application/effect consequences consume the one qualified observation path and remove the existing equality-only formal authority shortcut, while preserving finite Action/Role/Result, WIP/priority/finish-first/no-rewind/no-fallback, and CarrierRequired semantics.
- [ ] 2.4 REFACTOR: keep lifecycle events limited to ordering/supersession/ABA, keep actor/connector/carrier/timestamp/value identity non-authoritative, and delete any redundant late authority check or permanent legacy fallback made unnecessary by ingress qualification.
- [ ] 2.5 VERIFY: run the focused qualification, lifecycle-ordering, ABA, carrier, terminal, equality, completeness, and pre-activation tests; then run full Python tests, Ruff check, Ruff format check, mypy, strict OpenSpec validation, and exact repository checks at the final revision.
