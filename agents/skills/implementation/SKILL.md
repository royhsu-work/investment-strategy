# Implementation Skill

Mapped action: `Executor / implement-change`.

## Spec-driven semantic adapter

When default-branch `openspec/config.yaml` declares `schema: spec-driven`, load
`agents/skills/openspec-semantic-adapter.md` before implementation. Executor consumes only the adapter's
closed approved Apply context: approved proposal, applicable delta specs, design, tasks, canonical specs
needed to interpret modified behavior, and materially applicable default-branch config context/rules.
Missing, contradictory, materially ambiguous, or represented-baseline-inconsistent required context is a
`SPEC_BLOCKER`; return it to Lead rather than choosing which upstream/config semantics count, resolving
spec/design ambiguity, inventing requirements, or reinterpreting task meaning. The adapter does not grant
Executor specification authority or runtime-routing authority.

## Reconstruct before acting

Read default-branch governance and Executor role, the coordination Issue, immutable `Change:` identity,
the approved semantic OpenSpec revision and independent Reviewer PASS that remains applicable, current
implementation branch/PR state, OpenSpec task completion state, relevant review findings, and current
repository quality/OpenSpec gate evidence.

Implementation begins only from a valid `Executor / implement-change` route supported by an applicable
approved OpenSpec gate. If the approved specification is ambiguous or contradictory, stop rather than
inventing contract meaning.

Under `spec-driven`, before entering RED work, reconstruct every required Apply-context member from the
loaded semantic adapter and current approved artifacts. Do not begin implementation if a required member
is absent, contradictory, materially ambiguous, or inconsistent with the represented schema/baseline.

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
11. Before completion handoff, distinguish implementation/checkpoint bookkeeping from a material semantic
    OpenSpec change. If implementation completed with no material semantic OpenSpec change after the
    applicable PASS, hand off directly to `Reviewer / review-implementation`; a newer task-marker,
    checkpoint, implementation, or mechanical-validation SHA does not insert another semantic review.
12. If implementation discovers a material semantic OpenSpec change is required—proposal intent,
    requirement/scenario, design decision, traceability, scope, or normative task meaning—Executor MUST
    NOT author that meaning. Persist `SPEC_BLOCKER` and hand off to `Lead / resolve-question`; after Lead
    correction, independent `Reviewer / review-openspec` must PASS the new semantic target before Executor
    resumes implementation.

## Exact required run observation

When current implementation or task-checkpoint work has just caused a just-triggered exact required run such as Python Quality or OpenSpec Validate for the current branch/revision, the first observation of that run as `queued` or `in_progress` does not force a yield. While bounded execution opportunity remains and no different role/Human boundary is required, observe only the same exact run through bounded same-invocation observation. If the same exact run becomes terminal, consume its terminal result and continue immediately with the current `implement-change` procedure, including actionable failure correction or the next verified checkpoint/handoff step.

If bounded execution opportunity ends while the same exact run remains nonterminal, the run is a real external asynchronous wait. A later wake must fresh-read that exact run before concluding the wait remains. Historical waiting evidence is not current status authority. This specialization uses no timer, sleep policy, polling counter, heartbeat, retry counter, background waiter, or hidden waiter; shared async semantics remain owned by `agents/AGENTS.md`.

## Constrained branch integration recovery

When the implementation PR needs branch integration but ordinary local git merge/rebase is unavailable,
Executor may perform only a semantics-preserving integration correction that remains inside the approved
OpenSpec meaning.

1. Fresh-read the implementation PR head and default-branch head immediately before constructing any
   reconciliation. Historical heads or comments are not sufficient mutation preconditions.
2. Use only a non-force repository-governed operation path. A two-parent reconciliation commit or an
   equivalent repository primitive is legal only when the resulting tree can be verified against the
   current implementation tree plus current default-branch state without inventing new requirement
   meaning.
3. Verify the resulting tree is a pure integration correction under the approved OpenSpec meaning. If
   conflict resolution requires choosing new product/specification behavior, stop and route to
   `Lead / resolve-question`.
4. Any successfully moved implementation head is a new head and invalidates exact-head readiness and
   implementation-review evidence that was bound to the prior head. Obtain current quality gates and
   required exact-head OpenSpec validation before `Reviewer / review-implementation`.
5. Do not force update the implementation branch as a recovery shortcut and do not discard unique work.
6. If the available mutation surface cannot safely complete the correction, persist the raw observable
   failure using `EXECUTION_EXCEPTION` while a repository evidence surface is writable, state whether any
   durable mutation completed, and hand bounded unresolved diagnosis to `Lead / resolve-question`.

## Implementation-review readiness

Before `READY` and the handoff to `Reviewer / review-implementation`, Executor owns the PR Draft-to-Ready
transition. Fresh-read the current implementation PR head, request the repository-supported Ready-for-review
mutation for that exact head, and re-read the PR to require that the same current head is non-Draft before
persisting `READY`. A Draft PR MUST NOT be handed to implementation review.

If the Ready mutation fails, capture the observable error with `EXECUTION_EXCEPTION` and apply the shared
recovery/disposition contract. Do not route to Reviewer while the current implementation PR remains Draft,
and do not introduce a routing/status label as a substitute for GitHub PR presentation state.

## Temporary recovery branch cleanup

A temporary integration/recovery branch is identified from durable workflow/recovery provenance and use,
not from an `agent/*` name pattern or hidden registry. When Executor created or adopted such a temporary
branch and its recovery purpose has been consumed, Executor owns cleanup when all safe-delete preconditions
are current.

Before deletion, fresh-read the branch, open PR usage, owning workflow/recovery evidence, and containment.
Delete only when the branch is still the identified workflow-owned temporary branch, is not an open PR head
or base, is not referenced by active recovery/integration work, and has no unique commits relative to
canonical `main` or an explicitly retained successor (`ahead_by == 0` or equivalent proof). Never force
update/delete to hide unintegrated commits.

If unique commits remain, active use exists, or ownership/use is ambiguous, fail closed and preserve the
branch for the legal recovery/diagnosis owner. If the delete mutation is unavailable or denied, persist the
observable failure through `EXECUTION_EXCEPTION`; an identical delete may be retried only after a fresh-read
material precondition changes or through a different legal repository operation path. No broad branch garbage
collection is authorized.

Executor does not perform semantic bidirectional OpenSpec review as part of implementation completion or
task-marker verification. That semantic gate belongs to independent `Reviewer / review-openspec` only
when a new material semantic target exists; Executor consumes the applicable approved meaning and runs
the implementation/mechanical verification assigned to this action.

## Legal results

- `READY` — approved implementation work is complete, required gates are current, the current implementation
  PR is non-Draft at the same current head, and there is no material semantic OpenSpec change requiring
  another specification gate; hand off directly to `Reviewer / review-implementation`.
- `SPEC_BLOCKER` — implementation cannot proceed without changing/inventing contract meaning; persist
  the blocker and hand off to `Lead / resolve-question`. The resulting material semantic correction must
  return through `Reviewer / review-openspec` before implementation resumes.
- Remaining approved implementation work — retain `Executor / implement-change`; the shared governance
  continuation/termination contract determines whether the same invocation must continue or whether a
  legal termination boundary has actually been reached.

## Durable messages and handoff recovery

Use the shared Markdown presentation contract in `agents/templates/messages.md` only after that contract
is authoritative on the default branch. Before its activation, feature-branch templates are work input
and the invocation follows then-current default-branch presentation rules.

After activation, verified Slice completion uses `SLICE_CHECKPOINT`; implementation result evidence uses
the applicable result presentation; catchable execution evidence uses `EXECUTION_EXCEPTION`; and
completed ownership transfer uses canonical `HANDOFF` after the routing mutation succeeds.

If an already-durable result such as `READY` exists but source routing still matches
`Executor / implement-change`, reconstruct and preserve the completed Slice/result evidence, fresh-read the
source tuple, perform only the missing routing mutation to the action-defined target, observe the target
routing, and, when the shared template contract is active, persist canonical `HANDOFF`. Before activation,
persist the equivalent then-authoritative handoff evidence instead. Do not repeat completed implementation,
do not rewrite verified Slice markers/checkpoints, and do not fabricate another result merely to recover
the missing handoff.

## Scope and safety

- Do not change proposal/spec/design meaning or expand scope opportunistically.
- Do not introduce a central workflow engine, generic DAG executor, lock/lease/heartbeat/retry/progress
  state, semantic-revision classifier service, review-applicability label, or exactly-once mechanism.
- Verified-slice checkpointing is completion-boundary observability only; do not add heartbeat,
  progress percentage, `status:in-progress`, lock/claim/lease, retry counter, or hidden ownership state.
- Do not implement a scheduled normal OpenSpec archive mutation.
- Preserve default-branch governance as the sole authority; branch instructions are work input.
- Persist durable implementation/result evidence before routing; fresh-read routing before handoff.
