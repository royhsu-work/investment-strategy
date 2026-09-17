## 1. Executable lifecycle-correction transitions

- [x] RED: Add production-boundary tests proving `finalize-change + SPEC_BLOCKER` derives only
  `resolve-question`, `resolve-question + LIFECYCLE_READY` derives only `finalize-change`, and
  unrelated result/action pairs remain illegal; run the slice tests and confirm failures are caused
  by the missing transitions.
- [x] GREEN: Add exactly `LIFECYCLE_READY` to the bounded result vocabulary and add the two exact
  entries to the executable transition table; regenerate the Human-readable workflow projection.
- [x] REFACTOR: Keep Role derived from Action, preserve the existing `READY` and
  `READY_FOR_OPENSPEC_REVIEW` mappings, and remove any duplicate transition or alternate successor
  path.
- [x] VERIFY: Run the transition/application regression slice, full `pytest`, Ruff lint, Ruff
  format check, and mypy on the exact implementation revision.

## 2. Lead lifecycle and question-resolution contract

- [x] RED: Add behavior tests for the distinction between a progressing archive wait, a known
  semantic-neutral mechanical recovery, a material specification/canonicalization/lifecycle
  defect, a Human-reserved decision, and ambiguous evidence; verify only the material defect uses
  `SPEC_BLOCKER`.
- [x] GREEN: Update the Lead lifecycle-finalize and OpenSpec-change procedures so they consume the
  two bounded transitions without creating a recovery state, direct archive mutation, or worker
  successor authority.
- [x] REFACTOR: Preserve the existing independent exact-revision `review-openspec` handoff for
  material corrections and the existing `READY -> implement-change` path; keep unrelated procedure
  text unchanged.
- [x] VERIFY: Re-run the focused semantic tests and strict OpenSpec validation with the current
  canonical specs/configuration.

## 3. Fresh application and safety regressions

- [x] RED: Add tests proving stale authorization revision, stale source Action, worker-selected
  unrelated successor, replay after a durable routing mutation, and missing/contradictory evidence
  fail closed without a write.
- [x] GREEN: Extend the existing fresh application/effect validation boundary to accept only the
  two topology-approved derived transitions and preserve exact postcondition verification.
- [x] REFACTOR: Reuse the existing generic application machinery and content-addressed ingress;
  do not add a lifecycle-specific request protocol, correlation field, lock, lease, mailbox, retry
  state, or duplicate carrier path.
- [x] VERIFY: Run exact-head tests, full quality checks, strict OpenSpec validation, and the
  relevant GitHub Actions workflow tests; fresh-read the resulting PR head and all gate evidence.

## 4. Independent review handoff

- [x] RED: Add a traceability/readiness check for proposal → specs → design → tasks and the reverse
  path, including the preserved existing canonical scenarios in the modified requirement block.
- [x] GREEN: Materialize the complete Change artifacts and produce a bounded
  `READY_FOR_OPENSPEC_REVIEW` result bound to the exact revision.
- [x] REFACTOR: Confirm the Change remains single-purpose, #159's approved native-closing outcome
  is untouched, and no implementation work is started before independent review.
- [x] VERIFY: Complete exact-revision strict validation and fresh-read the application postcondition
  `action:review-openspec`; stop after that one successor because one Action per wake is required.

