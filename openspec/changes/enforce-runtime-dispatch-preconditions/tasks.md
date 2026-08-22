# Tasks

## Slice 1 — Replace the parallel test model with the executable dispatch precondition

Trace: proposal prior executable-classifier groundwork; design Decisions 1 and 1A; modified `scheduled-agent-workflow` requirement `Active-workflow cardinality and Issue-state coherence precede queue selection`.

- [x] **RED:** Refactor/add dispatch-cardinality tests so they import a production classifier/precondition that does not yet exist; cover complete `0/1/>1` cardinality, indeterminate enumeration, deterministic pre-activation ordering, candidate-local/role-local incompleteness, and the exact #100 formal-active + #130 queued-Explore recurrence shape.
- [x] **RED:** Add executable regressions for input authority: historical body/comment routing must not restore an Issue whose current routing labels are absent; prior invocation output/cache/model context cannot satisfy current routing/state/Change predicates; inability to obtain same-invocation authoritative current routing/state must produce indeterminate/fail-closed.
- [x] Run the focused RED tests and verify failures are caused by the missing production executable/provenance surface rather than fixture/import/setup errors.
- [x] **GREEN:** Add the minimum repository-owned pure executable dispatch-precondition module with structured snapshot/completeness/provenance inputs and deterministic decision output. It must implement only the current approved shared cardinality/recovery/pre-activation selection semantics and must fail closed on incomplete, provenance-invalid, or contradictory input.
- [x] **GREEN:** Define the narrow acquisition/input adapter contract that marks authorization-bearing current fields qualified only when they came from authoritative GitHub observations obtained during the current invocation; keep GitHub I/O outside the pure classifier and prohibit historical/prior-run fallback for missing current fields.
- [x] **GREEN:** Replace the local classifier/authorization logic in `tests/test_dispatch_cardinality_preflight.py` with imports/calls to that production implementation; retain fixture clarity while removing the second behavioral implementation.
- [x] **REFACTOR:** Keep GitHub acquisition implementation, lifecycle topology, routing mutation, Human authority, and workflow state outside the classifier. Preserve `agents/AGENTS.md` as semantic SSOT and avoid a generic workflow engine or hidden freshness store.
- [x] **VERIFY:** Run focused dispatch tests, the full regression suite, Ruff, Mypy, and strict OpenSpec validation; persist Slice 1 markers only after all required verification succeeds.

## Slice 2 — Prior Agent-consumption implementation groundwork

Trace: prior #133 semantic target and completed implementation through the durable Slice 2 checkpoint. This slice remains historical completed work; Slice 4 corrects the live-owner assumption without discarding the reusable classifier/provenance behavior.

- [x] **RED:** Add regressions proving stale/incomplete/provenance-invalid executable decisions do not authorize Explore/Propose behavior.
- [x] **GREEN:** Add executable action-entry/pre/post activation helpers and same-invocation provenance-bearing contracts.
- [x] **GREEN:** Update shared governance and `openspec-explore` / `openspec-change` to consume the executable decision under the then-approved Agent-owned runtime assumption.
- [x] **REFACTOR:** Keep classifier/global provenance algorithms centralized rather than duplicated in Skills.
- [x] **VERIFY:** Run focused/full Python, Ruff, Mypy, and strict OpenSpec validation and persist the completed Slice 2 checkpoint.

## Slice 3 — Prior durable executable-decision evidence groundwork

Trace: prior #133 semantic target and completed implementation through the durable Slice 3 checkpoint. The evidence structures remain reusable; Slice 4 changes the live producer/consumer boundary for the MVP transition path.

- [x] **RED:** Add presentation/behavior regressions for executable decision/completeness/provenance evidence.
- [x] **GREEN:** Extend canonical action-result presentation and action procedures to retain structured decision evidence.
- [x] **REFACTOR:** Keep evidence audit-only and avoid hidden invocation state, heartbeat, or freshness cache.
- [x] **VERIFY:** Run focused/full Python, Ruff, Mypy, and strict OpenSpec validation and persist the completed Slice 3 checkpoint.

## Slice 4 — GitHub Actions Transition Gate MVP for formal resolve-question routing

Trace: proposal corrected `What Changes`; design Decisions 2–10; added requirement `Issue-comment Transition Gate executes live formal-routing authorization`; Reviewer implementation finding `issuecomment-5379837891`.

- [ ] **RED:** Add Gate-adapter tests for a newly created Issue-comment intent on an already-formal `Lead / resolve-question` Issue. The valid case must require the production classifier to select that same Issue/current source routing before the requested `Reviewer / review-openspec` or `Executor / implement-change` target can be accepted.
- [ ] **RED:** Add a non-selected/wrong-Issue case proving a request on another Issue is rejected without routing mutation even when its comment requests an otherwise supported target.
- [ ] **RED:** Add incomplete/multiple-active cases proving the Gate returns `INDETERMINATE` and performs no routing mutation when complete current authorization cannot be established.
- [ ] **RED:** Add a stale-request case: the request is created while source routing is `Lead / resolve-question`, current routing changes before Gate execution, and the Gate fresh reconstruction rejects the stale request rather than trusting comment-time state.
- [ ] **RED:** Add serialized-request coverage proving request B re-reads state after request A is accepted; B must reject when A's accepted transition changed the source routing. Do not model a durable lock/lease/claim as workflow state.
- [ ] Run the focused RED suite and verify failures are caused by the missing live Gate adapter/transition behavior, not fixture/import/setup failure.
- [ ] **GREEN:** Add the minimum repository-owned effectful transition adapter. It must derive Issue identity from the event, perform authoritative GitHub acquisition/completeness normalization, call `workflow_dispatch.py`, validate only the bounded `Lead / resolve-question` MVP successor set, and keep topology ownership in `agents/workflow.md`.
- [ ] **GREEN:** Add `.github/workflows/workflow-transition-gate.yml` on the implementation branch with `issue_comment` `created` trigger, repository-wide non-cancelling concurrency, checkout of the authoritative default-branch implementation, and minimum required token permissions. The workflow must remain a thin adapter launcher, not a second policy implementation.
- [ ] **GREEN:** Implement minimal intent parsing such as `/transition reviewer review-openspec` and `/transition executor implement-change`. Request prose must not supply current source routing, Change identity, selected Issue, cardinality, or completeness evidence.
- [ ] **GREEN:** Implement `ACCEPTED` / `REJECTED` / `INDETERMINATE` outcomes. Only `ACCEPTED` may change routing; accepted routing changes require an immediate fresh source precondition check and fresh post-write routing observation.
- [ ] **GREEN:** Correct shared governance plus `agents/skills/openspec-explore/SKILL.md` and `agents/skills/openspec-change/SKILL.md` so they no longer claim that the Scheduled-Agent container itself is the demonstrated live executor of repository Python. For the MVP `resolve-question` formal successor path, `openspec-change` submits transition intent and consumes the Gate result instead of directly changing routing.
- [ ] **GREEN:** Reuse the existing structured decision/evidence presentation where applicable and add durable Gate result evidence without turning comments into workflow state or later-run authorization tokens.
- [ ] **REFACTOR:** Keep `workflow_dispatch.py` pure, keep GitHub I/O in the Gate adapter, keep legal topology in `agents/workflow.md`, and do not introduce a generic workflow engine, hidden queue, lease, heartbeat, or request registry.
- [ ] **REFACTOR:** Preserve the explicit MVP limitation that direct ChatGPT-connector routing-label writes remain technically possible. Do not add routing-event provenance hardening or claim permission-layer prevention in this slice.
- [ ] **VERIFY:** Run focused Gate/dispatch tests, full regression, Ruff, Mypy, and strict OpenSpec validation on the exact implementation head.
- [ ] **VERIFY:** Verify the implementation PR's changed workflow file and adapter are reviewable before merge, while explicitly recording that PR-stage tests are not a live `issue_comment` default-branch event proof.

## Post-merge live Gate canary

Trace: design Decision 10; added requirement scenarios for accepted and rejected live requests.

- [ ] After the Gate workflow exists on the default branch, produce one controlled live valid request that reaches the real `issue_comment` workflow, executes the repository adapter/classifier, returns `ACCEPTED`, and produces exactly the expected routing mutation plus post-write observation.
- [ ] Produce one controlled live invalid/stale request through the same default-branch event path; require `REJECTED` or `INDETERMINATE` and prove routing remained unchanged.
- [ ] Persist the exact workflow-run/request/result evidence needed to distinguish live default-branch execution from fixture-only integration tests.

## Completion

- [ ] Confirm proposal → specs → design → tasks trace declarations are mechanically consistent and reverse traceability `tasks → design → specs → proposal` has no intentional orphan scope after the runtime-owner correction.
- [ ] Confirm the revised semantic target preserves the prior classifier/provenance work as reusable groundwork while removing the unsupported claim that the Scheduled-Agent container itself is the live executable owner.
- [ ] Confirm Skill maintenance traceability covers every Skill materially corrected by this MVP and introduces no fictional upstream metadata.
- [ ] Confirm the proposal/implementation PR continues using non-closing `Refs #133` linkage; final closing linkage remains reserved for the final Archive PR lifecycle boundary.
- [ ] Obtain strict OpenSpec validation for the exact revised proposal handoff revision with checkout-identity evidence proving validator `HEAD` equals that revision.
- [ ] Hand the exact revised semantic revision to `Reviewer / review-openspec`; Lead does not claim the independent semantic bidirectional PASS.
- [ ] Before lifecycle completion, require the post-merge live Gate canary evidence above; do not treat PR-stage fixtures as equivalent live-trigger evidence.
