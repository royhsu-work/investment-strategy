# Implementation Review Skill

Mapped action: `Reviewer / review-implementation`.

## Reconstruct before acting

Read default-branch governance and Reviewer role, the coordination Issue and immutable `Change:`, the
approved semantic OpenSpec gate that remains applicable, the current implementation PR and exact head
revision, current task completion markers, relevant diff/tests, project quality checks, and strict
OpenSpec validation evidence.

Reconstruct the action-specific accepted baseline B from the last valid independent `review-implementation` gate that remains applicable to this implementation stream, and the current target R as the exact current implementation PR head. Inspect all material unreviewed changes in `(B, R]` and evaluate the complete current state at R; an older accepted result is only the coverage baseline and never substitutes for a current exact-head gate.

This action is an exact-current-head gate. The semantic OpenSpec bookkeeping exception does not weaken this gate: task-marker-only OpenSpec revisions may leave the approved semantic contract applicable, but Reviewer still evaluates the exact current implementation PR head R.

## Minimum gate

For the exact current implementation PR head R:

1. Compare implemented behavior and completed-task claims with the approved OpenSpec contract.
2. Inspect the relevant diff and tests for required behavior and meaningful regression coverage.
3. Verify required project gates and OpenSpec validation evidence are current. When strict OpenSpec
   validation is claimed for R, durable validator evidence must prove checkout `HEAD == R` before the
   strict command; `run.head_sha == R` alone or a different synthetic merge checkout is insufficient.
4. Verify implementation remains inside approved scope and did not redefine requirements/contracts.
5. Classify each material problem as either:
   - `IMPLEMENTATION_FINDINGS`: implementation defect, missing approved work, insufficient tests, or
     quality-gate failure;
   - `SPEC_FINDINGS`: material ambiguity/defect requiring Lead specification authority.
6. If all required checks pass, record `PASS` bound to the exact PR head revision.

## Legal results and handoff

- `PASS` → `Lead / finalize-change`.
- `IMPLEMENTATION_FINDINGS` → `Executor / implement-change`.
- `SPEC_FINDINGS` → `Lead / resolve-question`.

A later PR head does not inherit the prior result. Contradictory current evidence fails closed.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation only when that presentation contract
is authoritative on the default branch. Once active, the revision-bound gate result uses `REVIEW_RESULT`;
a completed ownership transfer uses canonical `HANDOFF` only after the routing mutation succeeds. Do not
duplicate shared template bodies in this skill.

## Independence and handoff safety

Reviewer does not modify implementation or specification artifacts to make the gate pass. Persist the
revision-bound review result before routing, fresh-read current routing, and do not overwrite a newer
routing tuple. A label update is not a mutex/CAS guarantee.
