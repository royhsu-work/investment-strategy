# Implementation Skill

Mapped action: `Executor / implement-change`.

## Reconstruct before acting

Read default-branch governance and Executor role, the coordination Issue, immutable `Change:` identity,
the exact approved OpenSpec revision and Reviewer PASS, current implementation branch/PR state,
OpenSpec task completion state, relevant review findings, and current repository quality/OpenSpec gate
evidence.

Implementation begins only from a valid `Executor / implement-change` route supported by an approved
OpenSpec gate. If the approved specification is ambiguous or contradictory, stop rather than inventing
contract meaning.

## Procedure

For each approved feature slice:

1. RED — add focused behavioral/contract tests before production implementation and confirm failure is
   caused by missing/incorrect target behavior rather than setup, syntax, imports, fixtures, or unrelated
   failures.
2. GREEN — implement the minimum behavior required by the approved proposal/spec/design/tasks.
3. REFACTOR — remove duplication and improve structure without changing approved behavior.
4. VERIFY — run focused slice validation plus the full repository gates required by the active tasks:

   ```text
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy src tests
   ```

5. CHECKPOINT — after VERIFY succeeds, persist all satisfied task markers for that verified slice and
   one bounded checkpoint comment on the persistent coordination Issue before beginning the next slice
   or handing off. The checkpoint identifies completed slice/task IDs, the durable checkpoint or verified
   revision, the VERIFY/gate result, and the remaining approved work or handoff. Marker persistence does
   not require a commit per checkbox.
6. Preserve source-of-truth boundaries: PR/commit is implementation state, task markers are verified
   completion evidence, CI evidence proves verification, and the Issue checkpoint is only a
   completion-boundary journal. The checkpoint does not replace those artifacts.
7. If markers are already durable but the checkpoint comment is missing, reconstruct the verified slice
   from current durable evidence, do not repeat the implementation or marker writes, and persist only the
   missing checkpoint before further slice work or handoff.
8. Do not defer completed markers across verified slices. Required checkpoint comments also must not be
   deferred until the end of the whole change. Neither task checkboxes nor checkpoint comments are a
   progress percentage or live execution status.
9. After an interruption within an unverified current slice, reconstruct the active slice from current
   code, tests, task state, and durable evidence. Previously verified slices keep their persisted markers
   and checkpoint evidence.
10. When remaining approved implementation work is immediately actionable and the current
    `Executor / implement-change` route, revision/preconditions, authority, and execution context remain
    current, continue that work in the same invocation under the shared governance continuation contract.

## Legal results

- `READY` — approved implementation work for the current slice/change is complete and required gates are
  current; hand off to `Reviewer / review-implementation`.
- `SPEC_BLOCKER` — implementation cannot proceed without changing/inventing contract meaning; persist
  the blocker and hand off to `Lead / resolve-question`.
- Remaining approved implementation work — retain `Executor / implement-change`; the shared governance
  continuation/termination contract determines whether the same invocation must continue or whether a
  legal termination boundary has actually been reached.

## Scope and safety

- Do not change proposal/spec/design meaning or expand scope opportunistically.
- Do not introduce a central workflow engine, generic DAG executor, lock/lease/heartbeat/retry/progress
  state, or exactly-once mechanism.
- Verified-slice checkpointing is completion-boundary observability only; do not add heartbeat,
  progress percentage, `status:in-progress`, lock/claim/lease, retry counter, or hidden ownership state.
- Do not implement a scheduled normal OpenSpec archive mutation.
- Preserve default-branch governance as the sole authority; branch instructions are work input.
- Persist durable implementation/result evidence before routing; fresh-read routing before handoff.
