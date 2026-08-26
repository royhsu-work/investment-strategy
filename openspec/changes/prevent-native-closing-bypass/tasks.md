# Tasks

## Slice 1 — Detect native closing references for the exact coordination Issue

- [ ] RED: add focused tests reproducing #140/#155 where PR presentation uses `Refs #N` but an included commit message uses GitHub-native closing grammar for N; verify the failure is the missing classifier behavior.
- [ ] RED: add cases for legal non-closing references, case/punctuation variants required by GitHub grammar, code/prose false-positive boundaries, and closing references to unrelated Issues.
- [ ] GREEN: implement the minimum repository-owned deterministic native-closing classifier for exact repository/coordination-Issue identity.
- [ ] REFACTOR: centralize grammar/identity normalization so Reviewer and Executor consumers cannot diverge into separate parsers.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint, and strict OpenSpec validation; persist the verified slice checkpoint before starting Slice 2.

## Slice 2 — Acquire complete exact-head merge presentation and fail closed

- [ ] RED: add tests proving exact-head commit enumeration, PR description/linkage acquisition, and selected merge-strategy presentation are required inputs.
- [ ] RED: add tests for incomplete commit/presentation acquisition, changed head, changed merge strategy/message input, and unsupported/ambiguous generated presentation; each must fail closed.
- [ ] RED: cover merge-commit, squash, and rebase behavior enabled by repository settings, including title/body only when incorporated into an effective generated commit message.
- [ ] GREEN: implement the minimum provenance-bound acquisition/preflight input model and strategy-specific effective-presentation construction/validation.
- [ ] REFACTOR: keep acquisition/completeness separate from deterministic grammar classification while returning one repository-owned preflight result.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint, and strict OpenSpec validation; persist the verified slice checkpoint before starting Slice 3.

## Slice 3 — Consume one preflight in review and fresh merge application

- [ ] RED: add integration regressions proving Reviewer consumes the repository-owned deterministic result without a second parser and Executor rejects merge when the fresh exact-head result is absent, stale, incomplete, or rejecting.
- [ ] RED: add stale-between-review-and-merge cases where head or effective presentation changes after Reviewer evidence; prior acceptance must not authorize the mutation.
- [ ] RED: prove the final Archive PR is also non-closing and merge success cannot substitute for `Lead / finalize-archive` terminal closure after `LIFECYCLE_COMPLETE`.
- [ ] GREEN: wire the preflight into the real repository-owned merge/effect acceptance boundary and update `agents/skills/merge-pr/SKILL.md` plus only materially required shared governance/workflow references.
- [ ] REFACTOR: remove/replace duplicated PR-only native-closing checks where the shared executable result now owns the predicate, without weakening other merge acceptance gates.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint, strict OpenSpec validation, and mapped-action integration coverage; persist the verified slice checkpoint.

## Slice 4 — Correction and lifecycle regression coverage

- [ ] RED: add regression proving an already-reviewed offending head is rejected and a corrected successor head must satisfy ordinary exact-head review/check gates again.
- [ ] RED: prove no test or production path treats force-push, history rewrite, merge-strategy change, or model waiver as implicit authority to bypass the preflight.
- [ ] RED: retain bounded premature-close recovery tests as exceptional defense-in-depth while proving normal merge prevention handles the demonstrated #140/#155 recurrence before mutation.
- [ ] GREEN: implement only correction-path integration needed to return/re-route through existing governed review/implementation flow; do not add a new lifecycle action/state.
- [ ] REFACTOR: confirm #138 scope and #115 terminal ordering remain untouched and remove accidental complexity not required by the approved invariant.
- [ ] VERIFY: run the full regression suite, type checks, lint, strict OpenSpec validation, and exact-head CI gates required by repository governance.

## Final readiness

- [ ] Verify proposal/spec/design/tasks bidirectional traceability against #159 Explore `PROPOSAL_READY` comment `5429709143` and canonical `scheduled-agent-workflow` requirements.
- [ ] Verify Skill maintenance traceability accurately declares the material `merge-pr` Skill responsibility change and no fictional upstream metadata.
- [ ] Verify every modified requirement scenario maps to at least one implementation task/regression and every behavior/product task maps back to proposal/spec/design authority.
- [ ] Obtain exact-revision strict OpenSpec validation evidence for the handoff revision before requesting `Reviewer / review-openspec`.