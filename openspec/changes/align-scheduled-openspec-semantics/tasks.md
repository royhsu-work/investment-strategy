# Tasks: Align Scheduled OpenSpec semantics

## 1. Semantic-adapter contract and RED coverage

- [ ] 1.1 Add RED governance tests proving Scheduled OpenSpec actions have one shared `spec-driven` semantic-adapter reference rather than independent duplicated semantic copies. Trace: proposal `What Changes` → spec `Scheduled roles preserve material OpenSpec semantics when CLI instructions are unavailable` → design Decisions 1/2.
- [ ] 1.2 Add RED coverage that fails when the adapter/configured schema contract is unsupported or unavailable instead of allowing a Scheduled role to infer missing CLI-delivered semantics. Trace: same requirement → design Decision 2.

## 2. Progressive-disclosure adapter and role consumption

- [ ] 2.1 Add the minimum shared progressive-disclosure reference for the repository's configured `spec-driven` artifact dependency, project context/rules, delta-authoring, canonicalization-readiness, apply-context, and version-provenance semantics. Trace: proposal `What Changes` → spec `Scheduled roles preserve material OpenSpec semantics when CLI instructions are unavailable` → design Decisions 1/2/6.
- [ ] 2.2 Update `openspec-change`, `openspec-review`, and `implementation` skills to load that shared reference only when executing the applicable OpenSpec action, preserving existing role authority and shared governance ownership. Trace: same requirement plus spec `Executor consumes complete approved OpenSpec apply context` → design Decisions 1/3/4/5.
- [ ] 2.3 Add only the minimum role/shared-governance reference needed to make adapter ownership/consumption reconstructable; do not duplicate the adapter contract into `AGENTS.md` or role files. Trace: design Decision 1 and blast radius.

## 3. Propose/review canonicalization-readiness regression

- [ ] 3.1 Add RED regression coverage for the #29 failure class: a NEW capability lacking one non-empty Purpose must not reach a successful `review-openspec` PASS boundary even if strict OpenSpec validation accepts the artifact set. Trace: proposal `Why` → spec `OpenSpec authoring and independent review prevent knowable canonicalization omissions` → design Decisions 3/4.
- [ ] 3.2 Implement Lead authoring guidance and independent Reviewer verification against the shared semantic adapter so knowable later-canonicalization requirements are checked before implementation handoff. Trace: same requirement → design Decisions 3/4.
- [ ] 3.3 Preserve reverse-first plus forward traceability and exact-head validation as independent existing gates; prove semantic-adapter checks complement rather than replace them. Trace: same requirement → current canonical review/readiness contracts.

## 4. Apply-context preservation

- [ ] 4.1 Add RED coverage showing Executor fails closed/returns to Lead when required approved apply context or applicable config semantics are missing or materially ambiguous. Trace: proposal Apply correction → spec `Executor consumes complete approved OpenSpec apply context` → design Decision 5.
- [ ] 4.2 Implement Executor consumption of the approved proposal/specs/design/tasks plus applicable config context/rules through the shared adapter without granting Executor specification authority. Trace: same requirement → design Decision 5.

## 5. Verify and handoff readiness

- [ ] 5.1 Run targeted governance tests, full regression tests, lint/format/type checks, and strict OpenSpec validation; resolve all failures within approved scope.
- [ ] 5.2 Confirm executable OpenSpec package pins/Archive compatibility guards are unchanged and #63 remains the only executable-version upgrade track.
- [ ] 5.3 Confirm required trace declarations remain mechanically and semantically bidirectional across proposal → specs → design → tasks and tasks → design → specs → proposal before independent OpenSpec review.
