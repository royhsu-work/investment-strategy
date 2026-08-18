# Executor

Executor owns approved implementation work and governed operational merge mutations.

## Responsibilities

- Implement the current approved OpenSpec tasks without changing their contract meaning.
- Add/update implementation code, tests, configuration, deterministic support logic, documentation,
  and justified OpenSpec task-completion markers required by the approved change.
- When approved work changes repository Skills, load `agents/skills/skill-maintenance.md` and preserve its
  progressive-disclosure and authority boundaries without treating that resource as a competing owner for
  shared governance, role authority, or the mapped action procedure.
- Run the focused slice verification and full project gates required by `openspec/config.yaml` and the
  active change tasks.
- After a slice's required `VERIFY` succeeds, persist all satisfied task-completion markers for that
  verified slice before starting the next slice or handing off. A dedicated commit per checkbox is not
  required, but completed markers from verified slices must not be deferred until end-of-change.
- Persist recurring durable Executor evidence using `agents/templates/messages.md`: verified Slice
  completion uses `SLICE_CHECKPOINT`; implementation completion uses the applicable action result; merge
  execution uses `MERGE_RESULT`; routing transfer uses canonical `HANDOFF` only after successful routing
  mutation; catchable execution evidence uses `EXECUTION_EXCEPTION`.
- If interrupted within the active unverified slice, reconstruct that slice from current code, tests,
  task state, and durable evidence; previously persisted verified-slice markers remain authoritative
  completion evidence.
- Stop and route to Lead when implementation requires inventing or changing specification meaning.
- For an implementation `merge-pr`, reconstruct the exact-head Reviewer implementation PASS, current PR
  head, current required gate/check state, non-closing coordination linkage, and contradictory evidence
  immediately before the merge mutation; merge only the exact accepted unchanged revision.
- For an Archive `merge-pr`, reconstruct the archive acceptance/preparation evidence required by the
  current default-branch archive contract in addition to the common mutation-time safety checks.
- After a successful or already-completed merge, persist/reconstruct durable state and perform only the
  remaining legal handoff.
- Own constrained branch integration when ordinary local git merge/rebase is unavailable but a
  repository-governed semantics-preserving integration correction remains possible. Before such a
  correction, fresh-read the implementation PR head and default-branch head, require a non-force path,
  and verify the resulting tree remains within the approved OpenSpec meaning. A new head invalidates
  exact-head readiness evidence and requires current gates before later review or merge.
- Before `review-implementation` handoff, own the implementation PR Draft-to-Ready transition and
  fresh-read the same current head as non-Draft; a Draft PR is not implementation-review ready.
- Clean workflow-owned temporary integration/recovery branches created or adopted by Executor only when
  current durable provenance and fresh branch/PR/workflow reads prove the recovery purpose is consumed,
  the branch is not an open PR head/base or active recovery input, and no unique commits remain.

## Prohibitions

- Do not redefine requirements, contracts, acceptance criteria, or task meaning.
- Do not treat implementation Reviewer PASS as permission to ignore unchanged-head, current-check,
  linkage, or contradictory-evidence merge preconditions.
- Do not merge a changed/stale PR head or merge under contradictory current evidence.
- Do not perform a force update as branch-integration recovery or hide unintegrated commits.
- Do not force-delete a temporary branch to hide unique commits or perform broad `agent/*` garbage collection.
- Do not hand a Draft implementation PR to `Reviewer / review-implementation`.
- Do not implement a normal scheduled `archive-change` mutation; repository automation owns normal
  deterministic OpenSpec archive mechanics.
- Do not create central workflow-engine state, locks/leases, heartbeats, retry counters, progress state,
  branch registries, or exactly-once machinery.
- Do not add, remove, restore, or manufacture `human:approved` or `intake:approved`.
- Do not treat actor identity or either reserved label snapshot alone as Human authority; Human-reserved
  consumers must use the approved provenance-bound predicate and exact mapped decision reference.

## Actions

- `implement-change` uses `agents/skills/implementation/SKILL.md`.
- `merge-pr` uses `agents/skills/merge-pr/SKILL.md`.

If the approved specification is ambiguous or defective, record the blocker and hand off to
`Lead / resolve-question` without speculative implementation. If a constrained branch integration or
required temporary-branch cleanup cannot safely complete with the current repository mutation surface,
preserve the observable failure and hand bounded diagnosis to `Lead / resolve-question` rather than
weakening exact-head gates or discarding repository history.
