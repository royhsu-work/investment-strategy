# Tasks

## 1. Slice: one qualified executable OpenSpec baseline

- [x] 1.1 RED: add regression coverage proving validation and archive automation must resolve the same repository-owned executable OpenSpec version and demonstrate failure against the current duplicated hard-coded pins.
- [x] 1.2 GREEN: introduce the minimal executable-version SSOT pinned to `1.9.0` and make both OpenSpec workflows consume it without changing their ownership or trigger semantics.
- [x] 1.3 REFACTOR: remove obsolete duplicated version literals while keeping installation/readability simple.
- [x] 1.4 VERIFY: run focused tests, full Python Quality, and strict OpenSpec validation; confirm both workflows deterministically resolve `1.9.0`.

Trace: proposal `What Changes` 1–2; R1 scenarios `Validation and archive use the qualified baseline`, `Future OpenSpec release becomes available`; design D1.

## 2. Slice: qualify MODIFIED and archive semantics under 1.9.0

- [x] 2.1 RED: add executable compatibility fixtures that demonstrate the target safety expectations for incomplete versus complete `MODIFIED` requirements and archive/canonical-spec shape; prove the new compatibility assertions fail before their harness/behavior is present rather than from fixture/setup errors.
- [x] 2.2 GREEN: implement the smallest deterministic compatibility harness using the repository-pinned OpenSpec CLI and make the 1.9.0 cases pass, including rejection of a surviving-scenario omission before successful archive.
- [x] 2.3 REFACTOR: keep fixtures minimal and behavior-oriented; do not reproduce OpenSpec parsing/schema logic in repository code.
- [x] 2.4 VERIFY: run compatibility cases plus full Python Quality and strict OpenSpec validation; record immutable upstream release/commit provenance used by the qualification.

Trace: proposal `Why`, `What Changes` 3; R1 scenario `Modified requirement would lose a surviving scenario`; design D2/D4.

## 3. Slice: preserve exact Purpose safety across the upgrade

- [x] 3.1 RED: add/extend compatibility regression cases proving unexpected generated/blank/drifted Purpose results fail the repository archive postcondition and that valid new/existing capability Purpose outcomes remain accepted.
- [x] 3.2 GREEN: retain `purpose-snapshot` / `purpose-preserve` as the exact repository postcondition under 1.9.0 and adjust only version-specific implementation details that the compatibility cases prove obsolete.
- [x] 3.3 REFACTOR: remove duplicated workaround branches only where the exact Purpose invariant remains fully covered; keep unknown transformations fail-closed.
- [x] 3.4 VERIFY: run focused archive/Purpose tests, full Python Quality, exact OpenSpec validation, and the executable compatibility harness.

Trace: proposal `What Changes` 3–4; R1 scenarios `Archive canonicalization changes Purpose unexpectedly`, `Upstream adds overlapping safety validation`; design D3.

## 4. Slice: align executable compatibility provenance

- [ ] 4.1 RED: add regression coverage proving the Scheduled-Agent semantic adapter records the qualified executable baseline distinctly from its immutable represented-schema provenance and fails if repository version references drift.
- [ ] 4.2 GREEN: update the adapter's executable-baseline provenance to `1.9.0` while retaining represented upstream/schema provenance `2826b8889e5223a9a8095d4428b60b56597e1020` and existing semantic/runtime-authority boundaries.
- [ ] 4.3 REFACTOR: remove stale `1.3.1` compatibility references in the bounded upgrade scope without rewriting historical archived provenance.
- [ ] 4.4 VERIFY: run focused governance tests, full Python Quality, compatibility fixtures, and `openspec validate --all --strict --json --no-interactive` using the qualified baseline.

Trace: proposal `What Changes` 5; R1 executable-provenance paragraph and future-release scenario; design D4/D5.

## 5. Completion

- [ ] 5.1 Confirm no implementation/archive workflow uses an independently hard-coded OpenSpec version outside the repository-owned qualified baseline.
- [ ] 5.2 Confirm Human authority, role separation, exact-head validation, fail-closed archive behavior, and validated archive-branch ownership are unchanged.
- [ ] 5.3 Run the full required verification set and resolve all OpenSpec strict-validation issues before declaring the Change ready for implementation review.
