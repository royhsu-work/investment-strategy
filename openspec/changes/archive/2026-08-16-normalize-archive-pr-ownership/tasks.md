# Tasks: Normalize Archive PR creation ownership

## Slice 1 — Archive automation branch-ready success

- [x] **RED** Add focused workflow tests proving successful validated archive-branch push is normal success and no normal `gh pr create` mutation is required.
- [x] **GREEN** Remove the normal Archive PR creation step from `.github/workflows/openspec-archive.yml` while preserving deterministic archive classification, mutation, validation, commit, and push.
- [x] **REFACTOR** Keep only branch-readiness evidence needed for later lifecycle reconstruction; remove now-unneeded PR-write permission/path without weakening recovery entry points.
- [x] **VERIFY** Run focused tests, full regression suite, Ruff, mypy, and strict OpenSpec validation.

Trace: proposal `What Changes` items 1–2; modified requirement `Normal OpenSpec archive mechanics remain owned by repository automation`; design Decision 1.

## Slice 2 — Lead normal Archive PR creation

- [x] **RED** Add lifecycle tests proving `finalize-change` distinguishes archive-branch-ready success from genuine failure, creates the final Archive PR with `Closes #N`, and reuses an equivalent existing PR idempotently.
- [x] **GREEN** Update shared governance and `lifecycle-finalize` so Lead consumes validated branch readiness and creates/reuses the final Archive PR as ordinary continuation before routing to `Reviewer / review-archive`.
- [x] **REFACTOR** Keep deterministic archive mutation in automation and PR merge authority with Executor; introduce no new action/status/lock/hidden state.
- [x] **VERIFY** Run focused tests and full quality/OpenSpec gates.

Trace: proposal `What Changes` item 3; modified requirement scenarios for Lead PR creation/reuse; design Decision 2.

## Slice 3 — Preserve failure and final lifecycle gates

- [x] **RED** Add regression tests proving mutation/validation/commit/push failures remain fail-closed and closing linkage never substitutes for review/authorization/merge/native-close gates.
- [x] **GREEN** Align governance/orientation wording with the normalized ownership boundary while preserving `review-archive`, Lead exact-head authorization, Executor merge, native close, and `finalize-archive`.
- [x] **REFACTOR** Remove stale recovery-only wording that would misclassify normal branch readiness, without broadening recovery semantics.
- [x] **VERIFY** Run the full repository quality suite and strict OpenSpec validation.

Trace: proposal `What Changes` items 4–5; modified requirement failure/linkage scenarios; design Decisions 3–4.

## Final verification

- [x] Verify proposal → spec → design → tasks forward traceability and reverse traceability.
- [x] Verify no broader GitHub Actions permission expansion, archive-semantic redesign, or second workflow state machine entered scope.
- [x] Record exact-revision strict OpenSpec validation evidence before Reviewer handoff.