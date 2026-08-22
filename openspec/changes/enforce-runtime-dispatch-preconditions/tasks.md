# Tasks

## Slice 1 — Replace the parallel test model with the executable dispatch precondition

Trace: proposal prior executable-classifier groundwork; design Decision 1; modified `scheduled-agent-workflow` requirement `Active-workflow cardinality and Issue-state coherence precede queue selection`.

- [x] **RED:** Refactor/add dispatch-cardinality tests so they import a production classifier/precondition that does not yet exist; cover complete `0/1/>1` cardinality, indeterminate enumeration, deterministic pre-activation ordering, candidate-local/role-local incompleteness, and the exact #100 formal-active + #130 queued-Explore recurrence shape.
- [x] **RED:** Add executable regressions for input authority: historical body/comment routing must not restore an Issue whose current routing labels are absent; prior invocation output/cache/model context cannot satisfy current routing/state/Change predicates; inability to obtain same-invocation authoritative current routing/state must produce indeterminate/fail-closed.
- [x] Run the focused RED tests and verify failures are caused by the missing production executable/provenance surface rather than fixture/import/setup errors.
- [x] **GREEN:** Add the minimum repository-owned pure executable dispatch-precondition module with structured snapshot/completeness/provenance inputs and deterministic decision output. It must implement only the current approved shared cardinality/recovery/pre-activation selection semantics and must fail closed on incomplete, provenance-invalid, or contradictory input.
- [x] **GREEN:** Define the narrow acquisition/input adapter contract that marks authorization-bearing current fields qualified only when they came from authoritative GitHub observations obtained during the current invocation; keep GitHub I/O outside the pure classifier and prohibit historical/prior-run fallback for missing current fields.
- [x] **GREEN:** Replace the local classifier/authorization logic in `tests/test_dispatch_cardinality_preflight.py` with imports/calls to that production implementation; retain fixture clarity while removing the second behavioral implementation.
- [x] **REFACTOR:** Keep GitHub acquisition implementation, lifecycle topology, routing mutation, Human authority, and workflow state outside the classifier. Preserve shared governance/topology ownership and avoid a generic workflow engine or hidden freshness store.
- [x] **VERIFY:** Run focused dispatch tests, the full regression suite, Ruff, Mypy, and strict OpenSpec validation; persist Slice 1 markers only after all required verification succeeds.

## Slice 2 — Prior Agent-consumption implementation groundwork

Trace: prior #133 semantic target and completed implementation through the durable Slice 2 checkpoint. This slice remains historical completed work; Slice 4 replaces the unsupported live-owner assumption while retaining the reusable classifier/provenance helpers.

- [x] **RED:** Add regressions proving stale/incomplete/provenance-invalid executable decisions do not authorize Explore/Propose behavior.
- [x] **GREEN:** Add executable action-entry/pre/post activation helpers and same-invocation provenance-bearing contracts.
- [x] **GREEN:** Update shared governance and `openspec-explore` / `openspec-change` to consume the executable decision under the then-approved Agent-owned runtime assumption.
- [x] **REFACTOR:** Keep classifier/global provenance algorithms centralized rather than duplicated in Skills.
- [x] **VERIFY:** Run focused/full Python, Ruff, Mypy, and strict OpenSpec validation and persist the completed Slice 2 checkpoint.

## Slice 3 — Prior durable executable-decision evidence groundwork

Trace: prior #133 semantic target and completed implementation through the durable Slice 3 checkpoint. The evidence structures remain reusable; Slice 4 changes where live authorization is produced and consumed.

- [x] **RED:** Add presentation/behavior regressions for executable decision/completeness/provenance evidence.
- [x] **GREEN:** Extend canonical action-result presentation and action procedures to retain structured decision evidence.
- [x] **REFACTOR:** Keep evidence audit-only and avoid hidden invocation state, heartbeat, or freshness cache.
- [x] **VERIFY:** Run focused/full Python, Ruff, Mypy, and strict OpenSpec validation and persist the completed Slice 3 checkpoint.

## Slice 4 — Machine-gated Scheduled Agent runtime

Trace: proposal corrected `What Changes`; design Decisions 2–13; added requirement `Machine-gated runtime authorizes mapped work before model invocation and reauthorizes durable effects`; Reviewer findings `issuecomment-5379837891` and `issuecomment-5380345857`.

### 4A — Runtime acquisition and pre-model authorization

- [ ] **RED:** Add acquisition-adapter tests that reconstruct complete current Issue/routing/Change state into the production `DispatchPreflight` contract, including pagination/completeness and provenance failure cases.
- [ ] **RED:** Add runtime tests proving the model-invocation adapter is not called for `FAIL_CLOSED`, `NO_WORK`, multiple-active, incomplete/unqualified reconstruction, or fixed-role mismatch.
- [ ] **RED:** Add the exact #100 formal-active + #130 queued-Explore runtime regression: a Lead wake MUST select #100's current formal action and MUST NOT invoke a model for #130 Explore.
- [ ] **RED:** Add a Propose regression proving a second `Lead / propose-change` worker is not invoked while another formal workflow occupies WIP.
- [ ] Run focused RED tests and prove failures are caused by the missing runtime/acquisition integration rather than fixture/import/setup errors.
- [ ] **GREEN:** Add the minimum repository-owned GitHub acquisition/normalization adapter that can establish observable complete current workflow state and call the existing production classifier.
- [ ] **GREEN:** Add a Scheduled Agent runtime entrypoint that accepts only a fixed slot role plus trigger metadata, executes acquisition/classifier first, and constructs a worker request only for one exact authorized Issue/role/action whose role matches the slot.
- [ ] **GREEN:** Add `.github/workflows/scheduled-agent-runtime.yml` with the three fixed Lead/Reviewer/Executor schedule slots, an optional manual `workflow_dispatch` fixed-role input, authoritative default-branch checkout, and one repository-wide non-cancelling concurrency group. Cron/inputs carry no Issue/Change/action selection authority.
- [ ] **REFACTOR:** Keep selection semantics in `workflow_dispatch.py`; do not duplicate cardinality/queue logic in YAML, prompt text, or runtime orchestration.

### 4B — Responses API worker and credential isolation

- [ ] **RED:** Add worker-adapter tests proving an authorized exact Issue/role/action is passed to the mapped default-branch role/Skill context and that no model request occurs without the runtime authorization object produced in the same execution.
- [ ] **RED:** Add credential-boundary tests/configuration assertions proving model-controlled shell/tools cannot obtain a durable write-capable GitHub credential or persisted checkout credential.
- [ ] **GREEN:** Add the minimum OpenAI Responses API worker adapter. Do not use Codex as the worker runtime. Keep model/provider authentication outside workflow state and expose only the read/local-workspace capabilities required by the selected action.
- [ ] **GREEN:** Define a structured action-result/effect output contract sufficient to carry the source Issue/role/action, canonical result content, local patch/workspace result when applicable, and requested durable effects without treating that output as authorization.
- [ ] **GREEN:** Configure checkout/tooling so implementation workers may edit/test the local workspace while remote GitHub durable writes remain unavailable from model-controlled execution.
- [ ] **REFACTOR:** Keep action reasoning in the mapped role/Skill and runtime authorization outside the model prompt. The worker must not be asked to decide whether it was allowed to start.

### 4C — Fresh effect application and stale-stop

- [ ] **RED:** Add application-gate tests proving every staged effect batch fresh-reconstructs repository state, calls the production classifier again, and rejects the whole normal batch when the exact source Issue/role/action is no longer authorized.
- [ ] **RED:** Add stale-during-work coverage: worker starts from an authorized source, durable state changes before apply, and application performs no stale normal effect.
- [ ] **RED:** Add routing-successor coverage proving routing effects are accepted only when the requested successor is legal under the canonical `agents/workflow.md` topology and the source tuple is still current.
- [ ] **RED:** Add effect-specific guards for the currently supported durable effect classes used by mapped Skills, including exact Issue/labels/Change, exact PR/head/review/merge identity where applicable, and branch/ref expectations for implementation/archive work.
- [ ] **GREEN:** Add repository-owned effect application that holds the write authority unavailable to the worker, fresh-revalidates source dispatch plus effect-specific preconditions, applies only bounded authorized effects, and fresh-observes durable postconditions.
- [ ] **GREEN:** Keep staged result/effect transport invocation-local. If separate Actions jobs require an artifact/patch transport, prove it cannot authorize another run and is never read as current workflow state.
- [ ] **GREEN:** After successful apply, re-run complete dispatch before any same-role continuation. Continue only when the newly selected role still matches the fixed role slot; end on cross-role routing.
- [ ] **REFACTOR:** Do not add rollback transactions, lease/heartbeat/claim state, a request registry, or a second workflow DAG. Existing recovery semantics own partial-write recovery.

### 4D — Governance/Skill integration and full mapped-action coverage

- [ ] **RED:** Add governance/presentation regressions proving normal mapped work is not authorized merely because a ChatGPT Scheduled Task/model invocation exists; machine pre-model dispatch is required after cutover.
- [ ] **RED:** Add coverage proving Issue-comment transition commands are not part of the normal runtime authorization contract.
- [ ] **GREEN:** Correct `agents/AGENTS.md`, `agents/templates/messages.md`, `agents/skills/openspec-explore/SKILL.md`, and `agents/skills/openspec-change/SKILL.md` to the machine-gated worker/apply contract and remove obsolete Agent-owned-helper / Transition-Gate wording.
- [ ] **GREEN:** Audit every other mapped Skill (`openspec-review`, `implementation`, `implementation-review`, `merge-pr`, `lifecycle-finalize`, `archive-review`, and any other current mapped Skill) for direct model-owned GitHub mutation assumptions. Modify every genuinely affected Skill and record concrete traceability; do not change unaffected Skills mechanically.
- [ ] **GREEN:** Demonstrate all ten mapped actions can be invoked through the runtime with their required read/local-work capabilities and can express their current durable effects through the shared application boundary before cutover is declared ready.
- [ ] **REFACTOR:** Keep `agents/workflow.md` as the only global topology owner and keep fixed role ownership unchanged.

### 4E — Verification and cutover readiness

- [ ] **VERIFY:** Run focused runtime/acquisition/worker/apply tests, full Python regression, Ruff, Mypy, and strict OpenSpec validation on the exact implementation head.
- [ ] **VERIFY:** Verify the Actions workflow uses default-branch runtime/governance code, fixed role slots, non-cancelling repository-wide concurrency, and no model-controlled write credential path.
- [ ] **VERIFY:** Verify all mapped actions have runtime coverage and no independent legacy normal scheduler is required for an unsupported action.
- [ ] **VERIFY:** Persist implementation readiness evidence without claiming live default-branch scheduled execution before the workflow is merged to `main`.

## Post-merge live runtime canary and cutover

Trace: design Decisions 11–12; added requirement live-cutover scenarios.

- [ ] Before enabling the new runtime as the sole normal scheduler, verify legacy ChatGPT Lead/Reviewer/Executor Scheduled Tasks are disabled so there is no dual normal execution path.
- [ ] After the runtime workflow exists on `main`, use the ordinary current #133 lifecycle state. Observe at least one scheduled fixed role that does **not** match the current production-classifier-selected role and prove the run stops before any model invocation.
- [ ] Observe the matching fixed role slot and prove the live default-branch runtime executes complete acquisition, the production classifier authorizes the exact current #133 Issue/role/action, and only then invokes the model worker.
- [ ] If the live worker requests durable effects, prove the application phase fresh-reconstructs/re-authorizes the same source before write and fresh-observes the resulting durable state.
- [ ] Persist exact Actions run/revision/decision/model-invocation/apply evidence sufficient to distinguish the live runtime from PR-stage test doubles.
- [ ] Do not create a synthetic second formal workflow, synthetic routing state, or special `Lead / resolve-question` state solely for the canary.

## Completion

- [ ] Confirm proposal → specs → design → tasks trace declarations are mechanically consistent and reverse traceability `tasks → design → specs → proposal` has no intentional orphan scope after the runtime-owner correction.
- [ ] Confirm the revised target preserves completed classifier/provenance/evidence groundwork while removing both unsupported runtime models: Agent-self-executed authorization and post-action Issue-comment Transition Gate.
- [ ] Confirm Skill maintenance traceability names every Skill materially changed by the worker/apply split and gives the concrete reason for each change.
- [ ] Confirm PR #134 continues using non-closing `Refs #133` linkage; final closing linkage remains reserved for the final Archive PR lifecycle boundary.
- [ ] Obtain strict OpenSpec validation for the exact revised proposal handoff revision with checkout-identity evidence proving validator `HEAD` equals that revision.
- [ ] Hand the exact revised semantic revision to `Reviewer / review-openspec`; Lead does not claim the independent semantic bidirectional PASS.
- [ ] Before lifecycle completion, require the post-merge live runtime/cutover evidence above; PR-stage fixtures are not equivalent live proof.
