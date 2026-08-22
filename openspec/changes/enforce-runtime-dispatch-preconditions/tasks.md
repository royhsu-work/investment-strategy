# Tasks

## Slice 1 — Replace the parallel test model with the executable dispatch precondition

Trace: proposal `What Changes` items 1–3 and regression requirement; design Decisions 1, 1A, 2, and 5; modified `scheduled-agent-workflow` requirement `Active-workflow cardinality and Issue-state coherence precede queue selection`.

- [x] **RED:** Refactor/add dispatch-cardinality tests so they import a production classifier/precondition that does not yet exist; cover complete `0/1/>1` cardinality, indeterminate enumeration, deterministic pre-activation ordering, candidate-local/role-local incompleteness, and the exact #100 formal-active + #130 queued-Explore recurrence shape.
- [x] **RED:** Add executable regressions for input authority: historical body/comment routing must not restore an Issue whose current routing labels are absent; prior invocation output/cache/model context cannot satisfy current routing/state/Change predicates; inability to obtain same-invocation authoritative current routing/state must produce indeterminate/fail-closed.
- [x] Run the focused RED tests and verify failures are caused by the missing production executable/provenance surface rather than fixture/import/setup errors.
- [x] **GREEN:** Add the minimum repository-owned pure executable dispatch-precondition module with structured snapshot/completeness/provenance inputs and deterministic decision output. It must implement only the current approved shared cardinality/recovery/pre-activation selection semantics and must fail closed on incomplete, provenance-invalid, or contradictory input.
- [x] **GREEN:** Define the narrow acquisition/input adapter contract that marks authorization-bearing current fields qualified only when they came from authoritative GitHub observations obtained during the current invocation; keep GitHub I/O outside the pure classifier and prohibit historical/prior-run fallback for missing current fields.
- [x] **GREEN:** Replace the local classifier/authorization logic in `tests/test_dispatch_cardinality_preflight.py` with imports/calls to that production implementation; retain fixture clarity while removing the second behavioral implementation.
- [x] **REFACTOR:** Keep GitHub acquisition implementation, lifecycle topology, routing mutation, Human authority, and workflow state outside the classifier. Preserve `agents/AGENTS.md` as semantic SSOT and avoid a generic workflow engine or hidden freshness store.
- [x] **VERIFY:** Run focused dispatch tests, the full regression suite, Ruff, Mypy, and strict OpenSpec validation; persist Slice 1 markers only after all required verification succeeds.

## Slice 2 — Consume executable authorization at pre-activation action entry

Trace: proposal `What Changes` items 2–6; design Decisions 1A, 2–4, and 7; modified requirement scenarios for executable Explore/Propose authorization and current-state provenance.

- [x] **RED:** Add regressions proving `Lead / explore-change` cannot begin substantive research when the executable decision contains any formal active workflow, indeterminate completeness/provenance, a different deterministic winner, stale routing, or current routing that cannot be authoritatively observed; include #100/#130 as a named recurrence fixture.
- [x] **RED:** Add a regression proving a previously routed Issue with current routing labels removed is not counted active merely because historical Issue body/comments or prior invocation output still describe its former tuple.
- [x] **RED:** Add regressions proving `Lead / propose-change` cannot perform the activation write unless the immediate executable pre-write decision authorizes the same Issue from same-invocation authoritative current-state evidence, and that post-write multiple/contradictory/provenance-incomplete state yields no accepted activation or legal successor.
- [x] Run the focused RED tests and verify failures demonstrate missing runtime consumption/input-authority enforcement rather than merely missing documentation strings.
- [x] **GREEN:** Update shared `agents/AGENTS.md` runtime procedure to require execution/consumption of the default-branch classifier result at workflow-dynamic selection/action entry; require authorization-bearing current Issue state / Change / routing fields to come from authoritative GitHub observations obtained in the same invocation; fail closed when the runtime cannot execute the helper or cannot provide complete provenance-qualified normalized evidence.
- [x] **GREEN:** Modify `agents/skills/openspec-explore/SKILL.md` minimally so substantive Explore consumes the fresh executable action-entry decision built from same-invocation authoritative current-state evidence and retains that exact decision for its result evidence.
- [x] **GREEN:** Modify `agents/skills/openspec-change/SKILL.md` minimally so Propose consumes the same executable decision immediately before activation and on the immediate post-write reconstruction; activation is accepted only after the post-write decision proves exactly this Issue is the sole formal active workflow from complete provenance-qualified current evidence.
- [x] **REFACTOR:** Keep the classifier algorithm and global provenance semantics out of both Skills; reference the shared owner/helper and preserve existing Explore/Propose responsibility boundaries. Do not add a new dispatch Skill.
- [x] **VERIFY:** Run focused workflow/Skill tests, full regression, Ruff, Mypy, and strict OpenSpec validation; persist Slice 2 markers only after verification succeeds.

## Slice 3 — Make preflight and activation evidence reconstructable without creating state

Trace: proposal `What Changes` items 7–11; design Decisions 4, 6, and 8; modified requirement scenarios for durable executable-preflight evidence.

- [x] **RED:** Add presentation/behavior regressions proving applicable `Lead / explore-change` `ACTION_RESULT` evidence carries the exact executable action-entry completeness, authoritative observation provenance, formal-active Issue IDs, pre-activation candidate IDs, selected Issue, and disposition actually consumed by the action.
- [x] **RED:** Add regressions proving applicable `Lead / propose-change` `ACTION_RESULT` evidence additionally carries the executable pre-write decision, expected Change identity, post-write formal-active Issue IDs/completeness/provenance/disposition, and accepted/not-accepted activation outcome.
- [x] **RED:** Add regressions proving durable comments, prior invocation output, and historical routing evidence are audit-only and can never satisfy a later invocation's current-state predicate or authorization input.
- [x] **RED:** Add a regression proving optional wake/invocation-source correlation is preserved only when the runtime actually exposes it and is never fabricated or used as routing/authorization state; observation provenance must remain expressible without inventing scheduler identity.
- [x] Run the focused RED tests and verify failures expose missing durable evidence/input-authority fields rather than parser/template assumptions.
- [x] **GREEN:** Extend `agents/templates/messages.md` `ACTION_RESULT` evidence requirements for these pre-activation boundaries and the corresponding action procedures to render the structured executable decision and authoritative observation provenance rather than re-summarizing a second Agent-derived Issue list.
- [x] **GREEN:** Add/adjust canonical implementation-facing wording/tests so the evidence is explicitly audit-only; later invocations must fresh-reconstruct from authoritative GitHub observations and re-execute the classifier rather than consume an old comment as an authorization token.
- [x] **REFACTOR:** Keep external Scheduled Task prompts unchanged/bootstrap-only. Do not add a debug message bus, hidden invocation registry, heartbeat, freshness cache, or per-wake noise beyond the action-result boundary.
- [x] **VERIFY:** Run focused message/workflow tests, full regression, Ruff, Mypy, and strict OpenSpec validation; persist Slice 3 markers only after verification succeeds.

## Completion

- [ ] Confirm proposal → specs → design → tasks trace declarations are mechanically consistent and reverse traceability `tasks → design → specs → proposal` has no intentional orphan scope.
- [ ] Confirm the corrected semantic target preserves temporal evidence boundaries: original Explore conclusions remain distinct from the later Reviewer-driven observation-provenance correction, and causal/timeline claims that matter are grounded in authoritative source objects rather than cross-Issue summary prose.
- [ ] Confirm Skill maintenance traceability lists every materially modified repository Skill and no fictional upstream metadata is introduced.
- [ ] Confirm the proposal/implementation PR uses non-closing `Refs #133` linkage; final closing linkage remains reserved for the final Archive PR lifecycle boundary.
- [ ] Obtain strict OpenSpec validation for the exact proposal handoff revision with checkout-identity evidence proving validator `HEAD` equals that revision.
- [ ] Hand the exact semantic revision to `Reviewer / review-openspec`; Lead does not claim the independent semantic bidirectional PASS.
