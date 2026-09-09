# Tasks: Qualify active formal consequences

## Parent outcome and staged delivery contract

Parent outcome: correctness-critical repository consequences become eligible only after observable current evidence is qualified by the existing executable owner through explicit machine-decidable predicates. The scheduled-agent active-formal provenance gap is the concrete proof and current delivery target; it does not replace the parent outcome.

Stage 1 boundary: produce application-correlation-bearing evidence inside the existing formal Action/Result evidence while preserving current acceptance behavior.

Stage 2 boundary: consume that correlation plus lifecycle-event ordering at the existing current-state, dispatch, and application boundaries; remove equality-only authority and enforce `QUALIFIED` / `INDETERMINATE`.

N-1 prerequisites:

- current default-branch governance and the finite Action/Role/Result model;
- complete current Issue snapshot reconstruction and current `ObservationProvenance` plumbing;
- existing formal Action/Result parsing, application reauthorization, derived successor/terminal effects, CarrierRequired handling, and exact postcondition observation;
- GitHub Issue lifecycle-event evidence is available as an authoritative read surface for ordering/supersession, but current dispatch preflight does not yet consume complete lifecycle-event reconstruction;
- existing quality, strict OpenSpec validation, exact-revision, and independent review gates.

Stage 1 exit criteria: every new repository application transition emits the minimum application-owned correlation in existing formal evidence; the correlation binds accepted Action/Result, application authorization, model-derived consequence, and exact durable postcondition; current acceptance behavior remains; no new workflow state/protocol/registry exists; and all Stage-1 tests and quality gates are green.

Stage 2 exit criteria: the existing owners consume correlation and lifecycle ordering; one current binding is `QUALIFIED`; missing/out-of-band/equality-only/ABA-superseded state is `INDETERMINATE` and fails closed; carrier and `Change: unset` compatibility remain; the equality shortcut is removed; and all parent exit criteria and quality gates are green.

Remaining mandatory outcome after Stage 1: Stage 2 qualification consumption and equality-shortcut removal remain required. Stage 1 completion is not parent completion. Use the existing `MORE_IMPLEMENTATION_REQUIRED` continuation to preserve this boundary; after Stage 2, use the existing implementation-ready path and later review/merge/lifecycle gates.

## Slice 1 — Produce correlation-bearing formal evidence (Stage 1)

Trace: parent outcome -> `repository-governance` invariant -> existing application authorization/evidence owner.

- [ ] 1.1 RED: add focused tests showing the existing formal result/postcondition chain lacks a machine-verifiable application-correlation binding, while preserving a fixture for the current acceptance path.
- [ ] 1.2 GREEN: add the minimum application-owned correlation field(s) to the existing formal Action/Result evidence and bind them to the exact accepted source, application authorization, model-derived consequence, and durable postcondition.
- [ ] 1.3 REFACTOR: reuse the existing formal evidence parser, application bridge, and postcondition observation; remove any duplicate receipt, transport, or correlation path.
- [ ] 1.4 VERIFY: run the focused Stage-1 evidence tests, full Python tests, Ruff check, Ruff format check, mypy, and strict OpenSpec validation at the exact revision; verify Stage 1 preserves current acceptance and leaves the Stage-2 continuation explicit.

## Slice 2 — Consume latest qualified transition at existing boundaries (Stage 2)

Trace: correlation-bearing formal evidence + lifecycle ordering -> current-state reconstruction/dispatch -> application/effect qualification.

- [ ] 2.1 RED: add focused fixtures for a qualified repository-owned transition, a direct/out-of-band route or close, current equality without a current binding, the A→B→C→B ABA sequence, exact carrier completion observed on a later wake, and `Change: unset` intake.
- [ ] 2.2 GREEN: reconstruct the relevant Issue lifecycle events, select the latest applicable transition for the same Issue/Change, consume the correlation-bearing application evidence and exact postcondition, and classify the current formal observation as `QUALIFIED` only when one coherent binding exists; otherwise use existing `INDETERMINATE` / fail-closed handling.
- [ ] 2.3 GREEN: make dispatch and application/effect consequences consume the one qualified observation path and remove the existing equality-only formal authority shortcut, while preserving finite Action/Role/Result, WIP/priority/finish-first/no-rewind/no-fallback, and CarrierRequired semantics.
- [ ] 2.4 REFACTOR: keep lifecycle events limited to ordering/supersession/ABA, keep actor/connector/carrier/timestamp/value identity non-authoritative, and delete any redundant late authority check or permanent legacy fallback made unnecessary by ingress qualification.
- [ ] 2.5 VERIFY: run the focused qualification, lifecycle-ordering, ABA, carrier, terminal, equality, and pre-activation tests; then run full Python tests, Ruff check, Ruff format check, mypy, strict OpenSpec validation, and exact repository checks at the final revision.
