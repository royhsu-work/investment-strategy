# Tasks — align-issue-completion-with-archive

## 1. PR linkage governance

- [x] 1.1 Add RED contract coverage proving implementation/implementation-correction PRs must not establish closing linkage to the persistent coordination Issue and that `merge-pr` fails closed when they do.
- [x] 1.2 Update shared governance and applicable Lead/Executor skills so implementation PR references are non-closing and closing linkage is reserved for the final Archive PR.
- [x] 1.3 VERIFY the linkage-governance slice with focused tests and repository quality checks; persist satisfied markers before the next slice.

## 2. Archive PR completion boundary

- [x] 2.1 Add RED contract coverage proving the final Archive PR identifies the correct coordination Issue and carries the repository-approved closing linkage without treating that linkage as merge authorization.
- [x] 2.2 Update the existing archive PR creation/documentation path, without adding a second archive engine, so final Archive PR closing linkage is deterministic and testable.
- [x] 2.3 Update Executor archive `merge-pr` preconditions to require correct closing linkage in addition to Reviewer PASS, Lead exact-revision authorization, unchanged head, and current gate validity.
- [x] 2.4 VERIFY the archive-boundary slice and persist satisfied markers before the next slice.

## 3. Finalization and recovery

- [x] 3.1 Add RED coverage for normal native Issue completion after authorized Archive PR merge, missing-native-close recovery, and premature implementation-time closure fail-closed behavior.
- [x] 3.2 Update `Lead / finalize-archive` governance/skill so normal completion reconstructs canonical archive state and observes the Issue closed; explicit Lead close is used only when the authorized Archive PR is merged and canonical archive state is correct but native completion is missing.
- [x] 3.3 Define durable handling for premature Issue closure so it cannot be mistaken for successful archive completion.
- [x] 3.4 VERIFY the finalization/recovery slice and persist satisfied markers before final handoff.

## 4. Documentation and final verification

- [x] 4.1 Align README lifecycle documentation with archive-only closing linkage, native final completion, and explicit-close recovery.
- [x] 4.2 Confirm the implementation retains one persistent coordination Issue, exactly nine normal actions, existing Human admission, and repository-owned archive automation with no new progress/locking engine.
- [x] 4.3 Run full Python quality and exact-revision strict OpenSpec validation; verify validator checkout identity evidence satisfies repository governance.
- [x] 4.4 Re-check bidirectional traceability across proposal → modified spec → design → tasks and tasks → design → modified spec → proposal, then prepare revision-bound handoff evidence for Reviewer.