# Tasks

Traceability baseline: Explore `issuecomment-5364628074` + Human correction `issuecomment-5364679558` → proposal → `repository-governance` requirement → design decisions → slices below.

## Slice 1 — Establish the Skill-maintenance trace contract

- [x] RED: add focused behavioral tests for material Added / Modified / Removed Skill trace declarations, one-capability-to-many-Skills mapping, non-material wording/reference-only edits, and retrospective-vs-original-history distinction.
- [x] GREEN: implement the minimum repository-governance support for a bounded `Skill maintenance traceability` declaration in governed Changes without adding a global Skill changelog/database.
- [x] REFACTOR: keep capability delta semantics, Skill maintenance traceability, and `UPSTREAM.md` provenance as distinct ownership layers with no synchronization-by-convention copies.
- [x] VERIFY: run focused tests, full regression suite, type checks, lint/format checks, and strict OpenSpec validation; persist the verified Slice checkpoint.

## Slice 2 — Enforce authoring and independent review

- [x] RED: add executable review fixtures where an undeclared material Skill change fails, a declared two-Skill/one-capability change passes, and a formatting/reference-only Skill edit does not create false maintenance noise.
- [x] GREEN: update `agents/skills/openspec-change/SKILL.md` so Lead authors/maintains the declaration from approved scope; update `agents/skills/openspec-review/SKILL.md` so OpenSpec review verifies declaration completeness/traceability; update `agents/skills/implementation-review/SKILL.md` so exact-head review compares material Skill changes with the approved declaration.
- [x] REFACTOR: preserve existing Lead/Reviewer/Executor authority boundaries; implementation must return to the governed specification path rather than letting Executor self-authorize a materially different Skill set or responsibility change.
- [x] VERIFY: run focused tests, full regression suite, type checks, lint/format checks, and strict OpenSpec validation; persist the verified Slice checkpoint.

## Slice 3 — Repair the bounded #105-through-pre-#110 window without rewriting history

- [ ] RED: add regression evidence that the bounded retrospective window is reconstructable from this Change, that every source implementation Change in the window is classified, and that historical archived Changes are not rewritten.
- [ ] GREEN: preserve retrospective `Modified` entries for #105/PR #106 (`openspec-explore`, `openspec-change`), #107/PR #109 (`archive-review`, `implementation-review`, `implementation`, `lifecycle-finalize`, `merge-pr`, `openspec-change`, `openspec-review`), #86/PR #114 (`openspec-change`, `openspec-review`), #115/PR #117 (`lifecycle-finalize`, `merge-pr`), and #112/PR #119 (`implementation-review`, `implementation`, `openspec-change`), with source-linked responsibility/rationale evidence.
- [ ] GREEN: record #80/PR #121 as an evaluated exclusion because it did not modify `agents/skills/*`; do not silently omit it from the bounded window.
- [ ] REFACTOR: keep retrospective scope bounded to #105 and subsequent merged implementation Changes through the pre-#110 baseline; do not trigger an audit of history before #105, and do not repurpose `UPSTREAM.md` as chronological maintenance history.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint/format checks, and strict OpenSpec validation; persist the verified Slice checkpoint.

## Completion

- [ ] Confirm the exact Explore baseline `issuecomment-5364628074` remains preserved except where materially superseded by Human correction `issuecomment-5364679558`, including continued rejection of a global changelog and one-capability-delta-per-Skill conventions.
- [ ] Confirm proposal/spec/design/tasks are bidirectionally traceable, the three prospective Skill modifications are explicitly declared, and the bounded retrospective window is complete through the pre-#110 baseline.
- [ ] Confirm `UPSTREAM.md` remains the current upstream/local-divergence owner and repository-authored Skills require no fictional upstream metadata.
- [ ] Confirm no product, workflow-topology, Human-authority, or runtime-role responsibility change was introduced.
- [ ] Run final Python quality gates and exact-head strict OpenSpec validation before `READY_FOR_OPENSPEC_REVIEW`.
