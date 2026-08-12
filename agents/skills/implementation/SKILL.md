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

5. CHECKPOINT — after VERIFY succeeds, persist all satisfied task markers for that verified slice before
   starting the next slice or handing off. This checkpoint does not require a commit per checkbox and
   should normally travel with the corresponding implementation checkpoint.
6. Do not defer completed markers across verified slices until the end of the whole change. Task
   checkboxes are durable completion evidence, not a progress percentage or live execution status.
7. After an interruption within an unverified current slice, reconstruct the active slice from current
   code, tests, task state, and durable evidence. Previously verified slices keep their persisted markers.

## Legal results

- `READY` — approved implementation work for the current slice/change is complete and required gates are
  current; hand off to `Reviewer / review-implementation`.
- `SPEC_BLOCKER` — implementation cannot proceed without changing/inventing contract meaning; persist
  the blocker and hand off to `Lead / resolve-question`.
- Remaining approved implementation work — retain `Executor / implement-change` and continue on a later
  run; do not fabricate completion.

## Scope and safety

- Do not change proposal/spec/design meaning or expand scope opportunistically.
- Do not introduce a central workflow engine, generic DAG executor, lock/lease/heartbeat/retry/progress
  state, or exactly-once mechanism.
- Do not implement a scheduled normal OpenSpec archive mutation.
- Preserve default-branch governance as the sole authority; branch instructions are work input.
- Persist durable implementation/result evidence before routing; fresh-read routing before handoff.
