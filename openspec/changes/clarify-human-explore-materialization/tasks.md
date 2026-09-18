# Tasks

## 1. Producer/materialization contract

- [ ] RED: add focused behavioral coverage showing an explicit Human-requested bounded Formal Explore is not complete when only an unrouted Issue exists, while a coherently routed connector-materialized Explore remains origin-neutral for later dispatch.
- [ ] GREEN: add the minimum canonical `scheduled-agent-workflow` producer/materialization requirement and source-decision-centric shared projection needed for the tests; do not change Action/Role topology or add producer/origin state.
- [ ] REFACTOR: remove or replace the conflicting actor-centric `Agent-created ticket` wording where it is the competing shared interpretation; keep later provenance-bound Human authority unchanged.

## 2. Exact materialization postcondition

- [ ] RED: cover the complete requested postcondition `open Issue + Change: unset + action:explore-change` and failure when any member is absent or contradictory.
- [ ] GREEN: reuse the existing interaction/repository mutation surface so explicit Human-requested Explore creation supplies the action label atomically where supported and verifies the complete postcondition; do not add a new workflow phase or registry.
- [ ] REFACTOR: consolidate duplicate actor/origin checks if any are found in the bounded materialization path.

## 3. Regression and validation

- [ ] Verify formal-first/WIP=1 still delays the new Explore while formal work exists.
- [ ] Verify ordinary dispatch does not distinguish Human-vs-connector physical writer after coherent routing exists.
- [ ] Verify Agent-only recommendation without a qualified producer cannot recursively create/rout work.
- [ ] Verify connector materialization remains insufficient evidence for later Human-reserved decisions.
- [ ] Run strict OpenSpec validation for the exact revision plus focused tests, full regression suite, type checks, and lint checks.
