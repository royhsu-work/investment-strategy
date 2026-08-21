# Tasks

Traceability baseline: Explore `issuecomment-5364628074` → proposal → `repository-governance` requirement → design decisions → slices below.

## Slice 1 — Establish the Skill-maintenance trace contract

- [ ] RED: add focused behavioral tests for material Added / Modified / Removed Skill trace declarations, one-capability-to-many-Skills mapping, non-material wording-only edits, and retrospective-vs-original-history distinction.
- [ ] GREEN: implement the minimum repository-governance support for a bounded `Skill maintenance traceability` declaration in governed Changes without adding a global Skill changelog/database.
- [ ] REFACTOR: keep capability delta semantics, Skill maintenance traceability, and `UPSTREAM.md` provenance as distinct ownership layers with no synchronization-by-convention copies.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint/format checks, and strict OpenSpec validation; persist the verified Slice checkpoint.

## Slice 2 — Enforce authoring and independent review

- [ ] RED: add executable review fixtures where an undeclared material Skill change fails, a declared two-Skill/one-capability change passes, and a formatting-only Skill edit does not create false maintenance noise.
- [ ] GREEN: update `agents/skills/openspec-change/SKILL.md` so Lead authors/maintains the declaration from approved scope; update `agents/skills/openspec-review/SKILL.md` so OpenSpec review verifies declaration completeness/traceability; update `agents/skills/implementation-review/SKILL.md` so exact-head review compares material Skill changes with the approved declaration.
- [ ] REFACTOR: preserve existing Lead/Reviewer/Executor authority boundaries; implementation must return to the governed specification path rather than letting Executor self-authorize a materially different Skill set or responsibility change.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint/format checks, and strict OpenSpec validation; persist the verified Slice checkpoint.

## Slice 3 — Make #105 repair durable without rewriting history

- [ ] RED: add regression evidence that the #105 maintenance gap is reconstructable from the new Change and that the archived #105 Change is not rewritten.
- [ ] GREEN: preserve the proposal's retrospective `Modified` entries for `openspec-explore` and `openspec-change`, linked to #105 / PR #106 / archive PR #108 / `issuecomment-5346223908`, with preserved action ownership and cardinality-preflight rationale.
- [ ] REFACTOR: keep retrospective scope limited to #105 plus prospective enforcement; do not trigger a repository-wide historical Skill audit.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint/format checks, and strict OpenSpec validation; persist the verified Slice checkpoint.

## Completion

- [ ] Confirm the exact Explore baseline `issuecomment-5364628074` is preserved, including rejection of a global changelog and one-capability-delta-per-Skill conventions.
- [ ] Confirm proposal/spec/design/tasks are bidirectionally traceable and the three prospective Skill modifications are explicitly declared in the proposal.
- [ ] Confirm `UPSTREAM.md` remains the current upstream/local-divergence owner and repository-authored Skills require no fictional upstream metadata.
- [ ] Confirm no product, workflow-topology, Human-authority, or runtime-role responsibility change was introduced.
- [ ] Run final Python quality gates and exact-head strict OpenSpec validation before `READY_FOR_OPENSPEC_REVIEW`.