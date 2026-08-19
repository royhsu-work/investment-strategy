# Tasks

## Slice 1 — Complete repository-wide dispatch preflight

Trace: proposal `What Changes` items 1–3; design Decisions 1, 2, and 5; `scheduled-agent-workflow` modified requirement `Active-workflow cardinality and Issue-state coherence precede queue selection`.

- [x] **RED:** Add fixture-driven workflow regressions for complete repository-wide dispatch classification covering formal/terminal cardinality `0`, `1`, `>1`, and indeterminate; include a partial/limited enumeration that omits an active workflow and prove formal WIP still wins over queued Explore/Propose work.
- [x] Run the focused RED tests and verify failures expose missing executable complete-cardinality/preflight enforcement rather than fixture or search-setup errors.
- [x] **GREEN:** Update shared `agents/AGENTS.md` dispatch procedure so a wake obtains repository-wide durable Issue state, establishes observable enumeration completeness, classifies formal active/terminal-pending/bounded recovery candidates, and applies the canonical `0 / 1 / >1 / indeterminate` decision table before selecting/loading a mapped normal action.
- [x] **REFACTOR:** Keep the complete-cardinality algorithm and decision table in the shared governance owner; remove or consolidate duplicated global dispatch wording rather than introducing a runtime dispatcher engine, second DAG, lock, lease, or hidden state.
- [x] **VERIFY:** Run focused dispatch/workflow tests, the full regression suite, Ruff, Mypy, and strict OpenSpec validation; persist satisfied Slice 1 task markers only after VERIFY succeeds.

## Slice 2 — Defend pre-activation Explore and Propose action entry

Trace: proposal `What Changes` items 2–4; design Decision 3 and Skill modification rationale; modified requirement scenarios `Pre-activation Explore revalidates zero formal WIP before substantive research` and existing activation safety semantics.

- [x] **RED:** Add regressions proving a previously selected Explore cannot begin substantive research if formal/terminal work appears or completeness becomes indeterminate before action entry; Propose cannot persist a Change when its immediate pre-write complete-cardinality check sees another active workflow; and a post-write competing/contradictory activation causes stale stop rather than continued lifecycle execution.
- [x] Run the focused RED tests and verify failures distinguish stale/partial preflight evidence from valid deterministic queue selection.
- [x] **GREEN:** Modify `agents/skills/openspec-explore/SKILL.md` to consume the shared pre-dispatch evidence and require zero formal/terminal WIP plus deterministic combined-queue winner before substantive Explore; modify `agents/skills/openspec-change/SKILL.md` so Propose's existing immediate pre/post activation checks explicitly consume the same complete-cardinality contract.
- [x] **REFACTOR:** Keep only action-local consumption/precondition wording in the two Skills and reference shared governance for the global procedure; preserve upstream OpenSpec Explore/Propose semantics and do not copy the dispatcher algorithm into Skills.
- [x] **VERIFY:** Run focused Explore/Propose workflow tests, the full regression suite, Ruff, Mypy, and strict OpenSpec validation; persist satisfied Slice 2 task markers only after VERIFY succeeds.

## Slice 3 — Preserve fail-closed multiple-active recovery boundary

Trace: proposal `What Changes` items 5–7; design Decisions 4–6; modified requirement scenarios `Two active workflows fail closed before a mapped action executes`, `Indeterminate enumeration cannot authorize work`, and `Human or maintainer repairs a multiple-active repository state`.

- [x] **RED:** Add regressions proving two formal active workflows prevent every normal mapped action; age, role/action priority, Issue number, or model choice cannot select a winner; Scheduled roles do not clear Change identities or rewrite routing to manufacture cardinality one; and after external Human/maintainer administrative repair a later wake derives state only from a fresh repository-wide reconstruction.
- [x] Add regression coverage proving parked/reset work resumed after a controlling dependency completes must compare then-current `main` and cannot inherit former PASS/readiness evidence as current authority.
- [x] Run the focused RED tests and verify failures correspond to unauthorized automatic winner/recovery assumptions rather than valid premature-close recovery behavior.
- [x] **GREEN:** Update shared governance/canonical implementation-facing wording and tests so multiple or indeterminate active state remains fail closed, administrative repair stays outside normal Scheduled-Agent lifecycle actions, and the next wake starts from repaired current durable state without a hidden recovery registry or new action/state.
- [x] **REFACTOR:** Remove any speculative winner-selection, automatic identity-reset, or duplicated external Scheduled Task routing logic introduced by the implementation; keep Scheduled Task prompts bootstrap-only and slot topology external.
- [x] **VERIFY:** Run focused recovery/dispatch tests, the full regression suite, Ruff, Mypy, and strict OpenSpec validation; persist satisfied Slice 3 task markers only after VERIFY succeeds.

## Completion

- [x] Confirm proposal → specs → design → tasks trace declarations are mechanically consistent and reverse traceability `tasks → design → specs → proposal` is reconstructable with no intentional orphan scope.
- [x] Confirm the proposal PR uses only non-closing `Refs #105` linkage; final Issue-closing linkage remains reserved for the final Archive PR.
- [x] Obtain strict OpenSpec validation for the exact proposal handoff revision and record checkout-identity evidence proving validator `HEAD` equals that revision.
- [x] Hand the exact semantic revision to `Reviewer / review-openspec`; Lead does not claim the independent semantic bidirectional PASS.
