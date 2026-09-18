# Tasks

## 1. Human-requested bounded Explore materialization

- [ ] 1.1 RED: add focused behavioral coverage showing that an explicit Human request to open one bounded Formal Explore requires the complete `open + Change: unset + action:explore-change` consequence, and that an unrouted created Issue fails the materialization postcondition.
- [ ] 1.2 GREEN: implement the minimum existing-owner materialization behavior needed to produce and fresh-observe that complete tuple without adding workflow state, tokens, origin registries, or routing dimensions.
- [ ] 1.3 REFACTOR: keep physical connector/writer identity out of positive and negative queue eligibility and reuse existing mutation/application ownership.

## 2. Origin-neutral downstream dispatch and reserved Human authority

- [ ] 2.1 RED: add regression coverage proving a coherently routed connector-materialized Explore is later selected by ordinary current-state pre-activation ordering, while an autonomous Agent recommendation without a qualified producer does not authorize materialization.
- [ ] 2.2 GREEN: replace the misleading actor-centric shared-governance projection with source-decision-centric wording while preserving current formal-first/WIP/finish-first behavior.
- [ ] 2.3 RED/GREEN: verify connector-created materialization evidence remains insufficient for later provenance-bound Human-reserved decisions and that no generic Human Explore approval is introduced.

## 3. Verification

- [ ] 3.1 Run focused materialization/dispatch/Human-authority tests and confirm the failures in RED are caused by the target behavior.
- [ ] 3.2 Run the full regression suite, type checks, lint/format checks, and strict OpenSpec validation on the exact implementation revision.
- [ ] 3.3 Confirm Role files, mapped Skills, executable Action topology, OpenSpec config, and unrelated capabilities remain unchanged unless concrete implementation evidence demonstrates an unavoidable existing-owner gap.
