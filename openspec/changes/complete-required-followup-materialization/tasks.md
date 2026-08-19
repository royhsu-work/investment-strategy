# Tasks

## Slice 1 — Required follow-up creation becomes routing-complete

- [ ] 1.1 RED: add focused regression coverage proving a required separate follow-up is not fully materialized when the tracker exists but canonical `agent:lead + action:explore-change` routing or exact source linkage is missing.
- [ ] 1.2 GREEN: update the narrow authoritative governance/Lead producer contract so the owning defer-decision action creates or reuses exactly one tracker with `Change: unset`, exact source Issue/Change/defer-decision linkage, and canonical Explore routing before declaring the obligation materialized.
- [ ] 1.3 REFACTOR: keep shared invariant text in the narrowest owner and action procedure in existing mapped Skills; do not add a new queue, status, registry, or reusable Skill without demonstrated cross-Skill need.
- [ ] 1.4 VERIFY: run focused tests, full Python regression/quality gates, and strict OpenSpec validation.

## Slice 2 — Interrupted materialization converges idempotently

- [ ] 2.1 RED: add regression cases for Issue-created-before-routing interruption, exactly-one incomplete tracker repair, already-complete tracker reuse, and multiple/ambiguous candidate failure.
- [ ] 2.2 GREEN: implement create/reuse/repair reconstruction so zero candidates creates one, one incomplete candidate is repaired, one complete candidate is reused, and ambiguous/contradictory candidates fail closed without duplicates.
- [ ] 2.3 GREEN: require fresh source-evidence and candidate-state reads around repair/mutation boundaries; preserve the existing at-least-once model without lock/lease/retry-counter state.
- [ ] 2.4 VERIFY: run focused tests, full Python regression/quality gates, and strict OpenSpec validation.

## Slice 3 — Lifecycle fail-safe and #98 regression

- [ ] 3.1 RED: reproduce the #98 sequence and prove an inert/malformed required tracker cannot satisfy Archive preparation or terminal required-follow-up reconstruction.
- [ ] 3.2 GREEN: update lifecycle-finalize procedure/tests so still-applicable required obligations are satisfied only by routing-complete uniquely reconstructed trackers; allow bounded repair only when independent source evidence uniquely identifies the intended tracker.
- [ ] 3.3 GREEN: add a regression proving dispatcher eligibility is never inferred from Issue prose and ordinary out-of-scope/non-required text does not create routed follow-up work.
- [ ] 3.4 GREEN: cover legacy #98-style repair semantics from independent approved source evidence without introducing generic Human admission or treating tracker prose as authority.
- [ ] 3.5 VERIFY: run focused tests, full Python regression/quality gates, and strict OpenSpec validation; confirm no unrelated #98 substantive Skill-conversion work entered this Change.

## Final verification

- [ ] 4.1 Verify proposal → specs → design → tasks trace declarations are mechanically complete and reverse traceability tasks → design → specs → proposal has no orphan scope.
- [ ] 4.2 Run exact-revision strict OpenSpec validation for the review target and capture checkout-identity evidence.
- [ ] 4.3 Confirm the implementation/Proposal PR uses non-closing `Refs #100` linkage and remains within the single-purpose workflow-integrity scope.
