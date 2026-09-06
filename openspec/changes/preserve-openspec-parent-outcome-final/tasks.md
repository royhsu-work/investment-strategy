# Tasks: Preserve parent outcomes across staged OpenSpec delivery

## Delivery stage 1 - One independently mergeable procedural correction

Parent-outcome coverage: all Issue #180 invariants and decision-complete exit criteria.

N-1 prerequisites: current openspec/config.yaml, mapped OpenSpec Skills, existing tests, executable Action model, and existing MORE_IMPLEMENTATION_REQUIRED result.

Stage exit criteria: every slice below is complete; exact-head semantic and implementation review pass; full tests, lint, type checks, and strict OpenSpec validation pass.

Remaining mandatory outcome after this stage: none. If implementation is intentionally partial, leave the uncompleted parent outcome explicit and use the existing MORE_IMPLEMENTATION_REQUIRED continuation. Do not mark the Change complete by silently reducing scope.

## Slice 1 - Establish the current owner and authoring predicate

Trace: Issue #180 current Human invariant -> openspec/config.yaml existing authoring owner -> Design D1.

- [ ] 1.1 RED - Add focused regression coverage proving the current config has its existing OpenSpec authoring rules but does not yet state recursive stage decomposition and parent-outcome reconciliation. Verify the failure is the missing predicate.
- [ ] 1.2 GREEN - Add the smallest config rules for N-1-independent stages, parent-outcome preservation, minimum stage evidence, and explicit approved reduction/defer.
- [ ] 1.3 REFACTOR - Keep the rules at the existing config owner and remove directly duplicated staged-delivery wording from touched procedural surfaces. Do not copy the project-wide proportionality requirement.
- [ ] 1.4 VERIFY - Run the focused config regression, strict OpenSpec validation, and relevant repository quality checks.

## Slice 2 - Add one reusable OpenSpec delivery procedure

Trace: Issue #180 reusable-procedure decision -> Design D2.

- [ ] 2.1 RED - Add focused structural tests for the required evidence tuple, parent/current/remaining reconciliation, explicit reduction/defer distinction, and absence of routing/state/registry authority.
- [ ] 2.2 GREEN - Add agents/skills/openspec-delivery/SKILL.md with conditional-use instructions and the minimum stage evidence contract.
- [ ] 2.3 REFACTOR - Keep the Skill action-specific and progressively disclosed; reuse current config/spec/test owners and delete any direct duplicate introduced in touched procedures.
- [ ] 2.4 VERIFY - Run focused Skill tests plus full repository quality checks.

## Slice 3 - Compose only where stage reconciliation is needed

Trace: Issue #180 mapped-consumer decision -> Design D3.

- [ ] 3.1 RED - Add regressions proving only openspec-explore, openspec-change, openspec-review, implementation-review, and lifecycle-finalize need conditional stage-reconciliation references; workflow topology, shared runtime governance, and archive ownership remain unchanged.
- [ ] 3.2 GREEN - Add concise conditional references to the reusable procedure in those mapped Skills.
- [ ] 3.3 GREEN - Require each consumer to preserve the existing Action/Role/Result boundary and route incomplete approved outcome through existing MORE_IMPLEMENTATION_REQUIRED semantics.
- [ ] 3.4 REFACTOR - Remove directly adjacent duplicate staged-delivery guidance while preserving current action-specific meaning. Do not refactor unrelated repository prose.
- [ ] 3.5 VERIFY - Run focused composition tests, Action model regression tests, full pytest, Ruff lint/format, and mypy.

## Slice 4 - Reconciliation and final quality gate

Trace: Issue #180 parent-outcome exit criteria -> Design D4/D6.

- [ ] 4.1 RED/GREEN - Add deterministic tests for complete stage coverage, missing mandatory continuation, explicit approved reduction/defer, and implementation-convenience omission.
- [ ] 4.2 Verify no new Action, Result kind, route, label, state, or parallel artifact graph is added; existing continuation semantics are reused.
- [ ] 4.3 Verify current ownership matrix and canonical proportionality remain single-owned and unchanged; no duplicate normative copy is introduced.
- [ ] 4.4 Run full pytest, Ruff lint, Ruff format check, mypy, focused governance/Skill tests, and strict exact-revision OpenSpec validation.
- [ ] 4.5 Confirm proposal -> no-canonical-spec delta -> design -> tasks traceability and exact current Issue/Change/PR linkage.
- [ ] 4.6 Mark the Change implementation-ready only after exact-head required gates are green and independent Review has passed.

## Continuation boundary

If any stage exits with approved parent outcome still incomplete, record the remaining mandatory outcome and required continuation and return the existing MORE_IMPLEMENTATION_REQUIRED result. Only an explicit approved reduction or defer decision may remove that remainder.
