# Implementation Review Skill

Mapped action: `Reviewer / review-implementation`.

## Reconstruct before acting

Read default-branch governance and Reviewer role, the coordination Issue and immutable `Change:`, the
approved OpenSpec revision/gate, the current implementation PR and exact head revision, current task
completion markers, relevant diff/tests, project quality checks, and strict OpenSpec validation evidence.

## Minimum gate

For the exact current implementation PR head:

1. Compare implemented behavior and completed-task claims with the approved OpenSpec contract.
2. Inspect the relevant diff and tests for required behavior and meaningful regression coverage.
3. Verify required project gates and OpenSpec validation evidence are current.
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

## Independence and handoff safety

Reviewer does not modify implementation or specification artifacts to make the gate pass. Persist the
revision-bound review result before routing, fresh-read current routing, and do not overwrite a newer
routing tuple. A label update is not a mutex/CAS guarantee.
