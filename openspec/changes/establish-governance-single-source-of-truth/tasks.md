# Tasks

## Slice 1 — Governance ownership matrix and references

- [ ] RED: add focused tests/assertions that identify current duplicated normative ownership in the affected governance surfaces and fail before the SSOT cleanup.
- [ ] GREEN: add the repository-governance ownership contract and update runtime documentation so README/shared governance/roles/skills each retain only their owned rule categories plus references/orientation.
- [ ] REFACTOR: remove stale competing normative copies in the touched scope without broad unrelated documentation rewriting.
- [ ] VERIFY: run focused governance tests, full regression suite, lint/type checks, and strict OpenSpec validation.

Trace: #29 body → `repository-governance` Requirements 1–3 → Design Decisions 1–2.

## Slice 2 — Same-invocation async-wait classification

- [ ] RED: add behavioral tests for exact-resource state sequences showing that a first `absent`/`queued`/`in_progress` observation does not automatically force cross-invocation yield when bounded same-action continuation remains possible.
- [ ] GREEN: update shared Scheduled-Agent governance and only the necessary action references so a resource that settles during the current invocation continues under work-conserving execution, while true cross-invocation waits still use #28 fresh-read-on-resume.
- [ ] REFACTOR: keep timing/counter/polling implementation details out of durable governance state and avoid per-role copies of the shared rule.
- [ ] VERIFY: run focused wait/reconstruction tests, full regression suite, lint/type checks, and strict OpenSpec validation.

Trace: #29 `issuecomment-5292380147` → `scheduled-agent-workflow` async-wait requirement → Design Decision 3.

## Slice 3 — External wake topology ownership

- [ ] RED: add/update governance tests proving slot count/cadence are not interpreted as repository routing/waiting/completion state or a permanent three-slot requirement.
- [ ] GREEN: narrow `agents/scheduled-task-migration.md` and related overview text so exact slot count/topology/cadence are external product/deployment configuration while bootstrap behavior remains repository-governed.
- [ ] REFACTOR: do not add a repository SLO or scheduler abstraction without a Human-approved requirement.
- [ ] VERIFY: run focused dynamic-dispatch/migration tests, full regression suite, lint/type checks, and strict OpenSpec validation.

Trace: #29 body + `issuecomment-5292380147` → `scheduled-agent-workflow` wake-topology requirement → Design Decision 4.

## Slice 4 — Pre-native-close terminal cleanup ordering

- [ ] RED: add lifecycle tests reproducing #28's dead-end: a known safely deletable Executor-owned temporary branch remains immediately before final Archive merge.
- [ ] GREEN: make Lead `finalize-archive` reconstruct known terminal cleanup obligations before final Archive authorization and make Executor `merge-pr` retire safe known temporary recovery branches before the Archive merge/native-close mutation.
- [ ] GREEN: when cleanup is blocked/unsafe/unavailable, keep the coordination Issue open by refusing the Archive merge and use existing exception/disposition/Lead-diagnosis semantics.
- [ ] REFACTOR: do not add a new post-close Executor action, generic reopen state, branch registry, or cleanup state machine.
- [ ] VERIFY: run focused archive/merge/temporary-branch tests, full regression suite, lint/type checks, and strict OpenSpec validation.

Trace: #29 `issuecomment-5293197049` + #28 source incident → `scheduled-agent-workflow` pre-native-close cleanup requirement → Design Decision 5.

## Slice 5 — Final coherence and traceability

- [ ] Verify proposal → specs → design → tasks references for both affected capabilities.
- [ ] Verify reverse trace tasks → design → specs → proposal without claiming the independent Reviewer semantic PASS.
- [ ] Confirm #28 recovery semantics remain intact and #35/#38 remain out of scope.
- [ ] Confirm implementation PR uses non-closing `Refs #29` linkage.
- [ ] Run full project quality gates and strict OpenSpec validation on the exact final revision before `READY_FOR_OPENSPEC_REVIEW`.
