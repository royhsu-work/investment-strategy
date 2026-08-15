# Tasks

## Slice 1 — Project-wide proportionality ownership

- [ ] RED: add focused governance tests showing the current proportionality contract is workflow-only/duplicated and does not establish one project-wide owner.
- [ ] GREEN: make project-wide proportionality/simplicity authoritative at the repository-governance layer and update only the runtime/reference surfaces needed to apply it.
- [ ] REFACTOR: remove or consolidate the standalone workflow-only proportionality copy so no synchronization-by-convention remains.
- [ ] VERIFY: run focused tests, full regression suite, lint/type checks, and strict OpenSpec validation.

Trace: #35 project-wide design direction → `repository-governance` proportionality requirement → Design Decisions 1 and 5.

## Slice 2 — Skill authoring and progressive disclosure guidance

- [ ] RED: add focused governance tests for compact mapped Skills, bounded progressive disclosure, external-reference non-authority, and preservation of AGENTS/role/skill ownership boundaries.
- [ ] GREEN: implement the minimum default-branch Skill-maintenance guidance needed to adopt the approved `skill-creator` principles without importing its runtime/tooling workflow.
- [ ] REFACTOR: extract shared Skill guidance only where demonstrated cross-Skill duplication exists; do not create speculative resource layers.
- [ ] VERIFY: run focused tests, full regression suite, lint/type checks, and strict OpenSpec validation.

Trace: #35 skill-creator direction → `repository-governance` Skill-maintenance requirement → Design Decisions 2 and 3.

## Slice 3 — Lead idle Skill-maintenance advisory

- [ ] RED: add focused tests proving eligible Lead idle analysis may consider repeated action mistakes, missing/obsolete Skill guidance, unnecessary complexity, and duplicated guidance without creating routing or mutation authority.
- [ ] GREEN: extend the existing bounded idle advisory procedure/role references only as needed to produce evidence-based Skill-maintenance recommendations.
- [ ] REFACTOR: reuse the existing advisory path; do not add a maintenance workflow, memory store, new action, or autonomous Skill mutation path.
- [ ] VERIFY: run focused tests, full regression suite, lint/type checks, and strict OpenSpec validation.

Trace: #35 idle-maintenance direction → `scheduled-agent-workflow` idle-advisory requirement → Design Decision 4.

## Slice 4 — Final coherence and traceability

- [ ] Verify proposal → specs → design → tasks references and reverse traceability.
- [ ] Confirm the project-wide rule is bounded to current change scope and does not trigger unrelated repository audits.
- [ ] Confirm Agent memory/knowledge/RAG, mandatory Skill benchmark infrastructure, and #38 Explore lifecycle remain out of scope.
- [ ] Confirm #35 security evidence `issuecomment-5291555571` and `issuecomment-5291586680` is explicitly preserved as deferred separate Human-admitted follow-up scope, not silently consumed or implemented by this change.
- [ ] Confirm the implementation PR uses non-closing `Refs #35` linkage.
- [ ] Run final project quality gates and exact-revision strict OpenSpec validation before `READY_FOR_OPENSPEC_REVIEW`.

Trace: deferred security disposition → Design Decision 6; this trace records scope disposition only and does not add security implementation tasks to this change.
