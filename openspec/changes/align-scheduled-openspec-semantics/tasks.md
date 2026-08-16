# Tasks: Align Scheduled OpenSpec semantics

## 1. Semantic-adapter contract and RED coverage

- [ ] 1.1 Add RED governance tests proving Scheduled OpenSpec actions have one shared `spec-driven` semantic-adapter reference rather than independent duplicated semantic copies. Trace: proposal `What Changes` → spec `Scheduled roles preserve material OpenSpec semantics when CLI instructions are unavailable` → design Decisions 1/2.
- [ ] 1.2 Add RED coverage that fails when the configured schema/material semantic contract is unsupported or unavailable instead of allowing a Scheduled role to infer missing CLI-delivered semantics. Trace: same requirement → design Decision 2.6.
- [ ] 1.3 Add RED coverage for the exact represented artifact dependency graph: proposal → specs, proposal → design, specs + design → tasks, tasks → Apply; prove adapter loading does not replace Scheduled runtime routing. Trace: same requirement → design Decision 2.1.

## 2. Progressive-disclosure adapter and role consumption

- [ ] 2.1 Add the shared progressive-disclosure adapter with the already-decided contract from spec/design: immutable upstream source commit/path; artifact dependency/readiness; `openspec/config.yaml` context/rule consumption; exact ADDED/MODIFIED/REMOVED/RENAMED semantics; NEW-capability Purpose/canonicalization readiness; Apply context; and fail-closed reassessment behavior. Executor MUST transcribe/implement this decided contract and MUST NOT select which OpenSpec semantics belong in it. Trace: proposal `What Changes` → spec `Scheduled roles preserve material OpenSpec semantics when CLI instructions are unavailable` → design Decision 2.
- [ ] 2.2 Update `openspec-change`, `openspec-review`, and `implementation` skills to load that shared reference only when executing the applicable OpenSpec action, preserving existing role authority and shared governance ownership. Trace: same requirement plus spec `Executor consumes complete approved OpenSpec apply context` → design Decisions 1/3/4/5.
- [ ] 2.3 Add only the minimum role/shared-governance reference needed to make adapter ownership/consumption reconstructable; do not duplicate the adapter contract into `AGENTS.md` or role files. Trace: design Decision 1 and blast radius.

## 3. Delta-authoring and canonicalization-readiness regressions

- [ ] 3.1 Add RED regression coverage for the #29 failure class: a NEW capability lacking exactly one non-empty Purpose must not reach a successful `review-openspec` PASS boundary even if strict OpenSpec validation accepts the artifact set. Trace: proposal `Why` → spec `OpenSpec authoring and independent review prevent knowable canonicalization omissions` → design Decisions 2.4/3/4.
- [ ] 3.2 Add RED regression coverage for MODIFIED requirements proving the complete future block must preserve every still-applicable canonical scenario/content and use the exact existing canonical header; partial MODIFIED content must be rejected before implementation. Trace: spec adapter delta-authoring contract → design Decision 2.3.
- [ ] 3.3 Add RED regression coverage for ADDED/REMOVED/RENAMED semantics: ADDED cannot collide with canonical identifiers; REMOVED targets an existing requirement and carries required rationale/migration treatment; RENAMED uses exact FROM/TO, and rename+behavior change additionally requires a complete MODIFIED block under the new header. Trace: same requirement → design Decision 2.3.
- [ ] 3.4 Implement Lead authoring guidance and independent Reviewer verification against the shared semantic adapter so all represented delta/canonicalization requirements are checked before implementation handoff. Trace: spec `OpenSpec authoring and independent review prevent knowable canonicalization omissions` → design Decisions 3/4.
- [ ] 3.5 Preserve reverse-first plus forward traceability and exact-head validation as independent existing gates; prove semantic-adapter checks complement rather than replace them. Trace: same requirement → current canonical review/readiness contracts.

## 4. Apply-context preservation

- [ ] 4.1 Add RED coverage showing Executor fails closed/returns to Lead when any required approved Apply artifact, needed canonical spec, or applicable config context/rule is missing, contradictory, or materially ambiguous. Trace: proposal Apply correction → spec `Executor consumes complete approved OpenSpec apply context` → design Decisions 2.5/5.
- [ ] 4.2 Implement Executor consumption of the approved proposal/applicable delta specs/design/tasks, canonical specs needed to interpret modified behavior, and applicable config context/rules through the shared adapter without granting Executor specification authority. Trace: same requirement → design Decision 5.
- [ ] 4.3 Add regression coverage proving Executor does not choose which upstream/config semantics count, resolve material spec/design ambiguity, or reinterpret task meaning when the adapter/context is incomplete. Trace: same requirement → design Decisions 2.5/5.

## 5. Semantic provenance and reassessment

- [ ] 5.1 Record immutable adapter provenance for `Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020` `schemas/spec-driven/schema.yaml` plus observed executable baseline `@fission-ai/openspec@1.3.1`; do not bind behavior to mutable upstream `main`. Trace: proposal durable sources → spec provenance contract → design Decisions 2.6/6.
- [ ] 5.2 Add regression coverage that a material configured-schema/baseline mismatch fails closed until deliberate adapter reconciliation rather than silently using model memory or current upstream behavior. Trace: same requirement → design Decision 2.6.

## 6. Verify and handoff readiness

- [ ] 6.1 Run targeted governance tests, full regression tests, lint/format/type checks, and strict OpenSpec validation; resolve all failures within approved scope.
- [ ] 6.2 Confirm executable OpenSpec package pins/Archive compatibility guards are unchanged and #63 remains the only executable-version upgrade track.
- [ ] 6.3 Confirm required trace declarations remain mechanically and semantically bidirectional across proposal → specs → design → tasks and tasks → design → specs → proposal before independent OpenSpec review.
