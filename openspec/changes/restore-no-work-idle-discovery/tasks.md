# Tasks

## Slice 1 — 0A. Historical materialization recovery characterization

- [x] 0.1 RED: reproduce the first-carrier postcondition contradiction after a safe disjoint main advance, with real current materialization source and exact Issue/Change/branch/head/PR/content observations.
- [x] 0.2 GREEN: make `materialization_postcondition()` compare the canonical fresh observer's exact target while retaining pending-continuation ancestry, path, identity, and ambiguity guards.
- [x] 0.3 RED: reproduce interruption after branch-ref creation but before PR creation, followed by a disjoint main advance; prove a missing-carrier plan is required and unsafe/wrong/duplicate/incomplete PR evidence is rejected.
- [x] 0.4 GREEN: resume only the missing PR carrier from the verified immutable intent and existing branch/head, using fresh current main and a shared exact plan builder.
- [x] 0.5 RED: prove a fresh consequence observer with an empty adapter-local materialization-target map rejects no valid durable materialization/implementation carrier.
- [x] 0.6 GREEN: reconstruct the `ConsequenceSpec.evidence_target` through the existing canonical current-state materialization or implementation-carrier owner.
- [x] 0.7 VERIFY: cover all applicable durable prefixes from acceptance through final postcondition and prove no duplicate, rewind, semantic replay, target broadening, or new recovery state.
- [x] 0.8 RED: reproduce an accepted intent with an exact current Issue/Change/Role/Action, a durable partial effect, an uncorrelated legacy `ACTION_RESULT`, and an invalid current frontier; prove the current bridge fails before resolving the accepted application run/job.
- [x] 0.9 GREEN: resume only the unique exact accepted intent and its unique request-bound application run/job through the existing recovery owner; prove stale source, changed route/Change, duplicate acceptance/run/job, and incomplete evidence still fail closed without semantic replay.
- [x] 0.10 VERIFY: execute the current-source reproduction and the full application/bridge interruption regression against fresh default-branch code; verify no semantic replay or duplicate mutation.
- [x] 0.11 HISTORICAL characterization: the prior implementation failed closed at `run_attempt > 1` (including the live #322 attempt-7+ fixture) and prevented same-run reruns. This records the old behavior only; the permanent run-attempt ban is superseded by the reviewed bounded-recovery correction in Slice 5 (0E).
- [x] 0.12 RED/GREEN: reproduce an accepted materialization whose exact PR carrier merged before the application process resumed; reconcile the merged head from complete GitHub compare history and exact historical blob evidence without creating a same-Change replacement, while retaining the existing replacement path when content or ancestry proof is incomplete.
- [x] 0.13 RED/GREEN: reproduce an accepted materialization whose historical carrier is superseded by a same-Change merge after acceptance; recover the exact immutable manifest from current-main compare history only when the historical merge commit remains an ancestor, and fail closed for incomplete evidence.

These historical repairs were merged by baseline `main@5fa6fdf7d9b33e3f2718c9525bb685f74393d3f3` and remain prerequisites: the application recovery chain #331 → #333 plus #347/#349/#354/#355 provides production characterization and reusable recovery/lineage/witness primitives. They did **not** themselves close the systemic root gate: Human refinement exposed competing positive completion semantics before the canonical consolidation. PR #357 originally supplied additional RED characterization; its final canonical consolidation is now merged at `1ca1d8e37e42bf1b689826ec34a0e335ba1f68b4`, without retaining that topology-specific positive branch. The 0A items describe historical delivery; their local target comparison is superseded by the single proof and separate target/witness contract below.

## Slice 2 — 0B. Canonical durable-consequence proof consolidation

The bounded Human-authorized bootstrap delivered the canonical owner and consumer cutover in PR #357 on candidate `63df1af3928e2c41f0ef69dcd3cc3623f4221544`, merged as current prerequisite N-1 `1ca1d8e37e42bf1b689826ec34a0e335ba1f68b4`. Independent exact-head review `5405763214`, remote Python Quality (891 tests plus Ruff/format/mypy), strict OpenSpec validation, and actual continuation run `37199451772` provide delivery evidence. The unchecked items below require ordinary Executor verification and task-ledger reconciliation against the merged implementation and this clarified approved meaning; they do not authorize rebuilding a competing owner. Advisory/wait implementation, final lifecycle, and actual post-terminal Scheduled Task acceptance remain mandatory.

- [x] 0.14 VERIFY: confirm the merged executable positive characterization for ancestor carrier, disjoint main advance, historical PR base, reconciled carrier, merged carrier, merged carrier plus same-Change successor, deterministic replacement, replacement plus main advance, reconciliation, and reconciliation plus later one-parent correction (#357), plus negative wrong-blob/PR/ref, duplicate/ambiguous carrier, overlap, broken ancestry, incomplete compare, and contradictory-state cases; reconcile the task ledger with exact merged characterization evidence without rebuilding the completed stage.
- [x] 0.15 VERIFY: confirm the merged single canonical read-only materialized durable-consequence proof owner returning `COMPLETE(target, witness)`, `INCOMPLETE`, or `CONTRADICTORY(reason)` from Identity + Content + Lineage + Non-conflict; verify its characterization/shadow comparison evidence and current result consistency after the delivered cutover.
- [x] 0.16 VERIFY: confirm the delivered materialization observation/postcondition, fresh interruption recovery, and consequence-completion classification cutover to the canonical proof; keep existing topology helpers only as proof primitives/witness finders and prove the consumers cannot independently manufacture positive completion.
- [x] 0.17 VERIFY: confirm apply-side already-complete qualification delegates to the same canonical proof; prove `apply(I) -> fresh prove(I) == COMPLETE` and that an obsolete mutation preimage such as `expected_sha` does not invalidate an otherwise proven durable desired consequence.
- [x] 0.18 VERIFY: exercise interruption after accepted decision, blob/tree/commit, branch/ref, PR carrier, CarrierRequired exit, validation, formal result, merge, successor routing, terminal transition, and final postcondition; each fresh continuation reconstructs solely from GitHub truth with zero semantic replay.
- [x] 0.19 VERIFY: prove safe-evolution monotonicity across disjoint main advance, legal reconciliation, legal merge, and legal same-Change descendants; prove conflict preservation for all stale/overlap/identity/cardinality/blob/ancestry/incomplete/contradictory negatives.
- [x] 0.20 VERIFY: confirm every positive completion consumer delegates to the canonical owner and the merged cleanup removed superseded topology-specific top-level completion branches (including the permanent need for a `direct_carrier_postcondition`-style #357 special case) while retaining reusable proof primitives; run focused/full pytest, Ruff, format, mypy, static workflow invariants, and exact-revision OpenSpec validation.

- [x] 0.21 VERIFY F1: trace the legal same-Change correction scenario through the merged canonical owner and every consumer; prove `COMPLETE(T, W)` with `T != W` and changed target path content, immutable accepted content at `W`, exact validation/review bound to `T`, zero materialization replay, and fail-closed identity/lineage/incomplete/conflict negatives. Local apply-target equality must supply no completion authority.
- [x] 0.22 VERIFY F2: trace the actual existing #353 correction and reconciliation graph with separate accepted authorization `A`, declared base `B`, actual prospective parent zero `P`, and fresh main `D`; prove missing-write `expected_sha` guards `P` even when `A/B != P`, rejects a preimage matching only another revision, preserves full compare/overlap/cardinality/unrelated-content guards, and does not require an obsolete preimage after durable desired-content proof.

## Slice 3 — 0C. Pending carrier consumption at existing owners

Trace: Human refinement 5986774520 / findings 5987083136 -> proposal carrier closure -> modified application-consequence requirement -> design qualified carrier consumption. N-1 is the current merged canonical proof and existing accepted-intent/CarrierPlan/application-continuation substrate, verified by 0.14–0.22. Prior F3 manual completion is characterization, not native acceptance. This slice is independently implementable/testable/reviewable/mergeable on N-1; its exit delivers unique pending-plan selection and a real connector-consumer seam, while evidence closure, advisory/Human-wait, native activation, full lifecycle and post-terminal idle remain mandatory next work.

- [x] 0.23 RED: run current-source tests showing saved qualified plan plus missing physical effect incorrectly selects another producer rather than the external consumer; separately prove COMPLETE skips mutation, genuine plan absence alone permits owner reconstruction, and missing/incomplete API evidence does not imply absence. Failures must be target behavior, not setup/import errors.
- [x] 0.24 GREEN: reuse application-completion, immutable accepted intent, exact run/attempt/artifact/digest/content-addressed CarrierPlan, canonical proof and fresh preconditions to expose only the unique eligible pending operation through the existing run-bound dispatch handoff; preserve FAIL_CLOSED/non-semantic authority, disjoint evolution, T/W and A/B/P/D semantics, and invocation-exit CarrierRequired.
- [ ] 0.26 RED/GREEN/VERIFY: first reproduce an exact carrier-outcome parser/consumer contract failure; then make the repository parser consume the strict carrier-outcome schema, bind every report to accepted intent/request/run/attempt/job/recovery-artifact/failure-evidence/carrier-artifact/plan/operation, and release the exact continuation only for one complete report. Scan all prior dispatch handoffs so an intervening fail-closed request cannot hide an earlier unreported plan; incomplete/orphaned history blocks. Verify focused/full tests and keep native acceptance a separate production gate.

The former 0.25 native Chat connector action is an external production acceptance witness, **not** an Executor-implementable checkbox. The still-open 0.26 covers only the repository parser and its tests. Its prompt/parser schema must agree, but CI/fake-connector proof does not substitute for the production witness.

The first exact implementation head `6635bc1` then reported five failures plus one setup error (912 passed). Whole-system diagnosis: one exact-preimage legacy merge-acceptance transplant called an unsupported current effects parameter; one test assigned accepted-repository binding to the context-free parser instead of the bridge consumer; and the intended lineage test parameterization was detached during insertion. Revert the legacy transplant, keep syntax and contextual binding at their respective layers, and rerun the full exact-head gate. These historical findings do not discharge current repository parser task 0.26 or the separate native production acceptance.

## Historical diagnostics (not unfinished Executor tasks)

Former unchecked 0.27–0.35 captured successive rejected-plan/evidence-transport hypotheses. They are **removed**, not marked as performed, and do not impose an old-plan-replay, per-ordinal completion, or retry-count prerequisite. Retain only the relevant externally testable safety behavior in current delta/design and the 0G RED/GREEN slice: fresh exact preimages, no duplicate irreversible effect, complete source reads, canonical materialization proof, unknown-versus-conflict distinction, and refusal to replay an unchanged denial. Distinct new approved work can be added as a scoped Executor slice after review if a test actually demonstrates a missing necessary behavior.

## Slice 5 follow-up — 0F. Exact-head carrier review corrections

- [x] 0.36 RED/GREEN: reproduce a same-lineage report with a missing/different `Plan-ID` beside a valid complete report, and prove the contradiction blocks regardless of comment order while unrelated lineage is ignored.
- [x] 0.37 RED/GREEN: reject noncanonical unpadded URL-safe base64 for observed preconditions; prove alternate spellings that decode to the same bytes are invalid.
- [x] 0.38 VERIFY: read full paginated runtime-shard history without a 30-day/last-N cutoff for continuation, outcome, and prior-handoff evidence; prove an unresolved request older than 30 days still blocks and history/read absence fails closed. Retain the bounded repository-wide ingress scan.
Former unchecked 0.39–0.41 are also **removed as standalone task markers**, not declared complete: validation is in 4.1–4.3, the artifact-upload shape is an existing contract/test rather than a second Recovery Exit, and UNKNOWN-versus-CONFLICT safety is covered by 0G. The independent review is a lifecycle gate, never an Executor checkbox.

## 0G. Forward Recovery — directly implementable slice (2026-10-22 Human refinement)

The old diagnostic identified a contract conflict, not proof that the historical plan completed. Historical effect ordinals, missing uploads, checkpoint audit comments, and attempts remain evidence, **not a mandatory sequence of completion gates**. Current Executor tasks implement only the reviewed I/R/M/V/S/F contract; material semantic changes require independent exact-revision OpenSpec review before implementation. Native and lifecycle witnesses are defined below, without checklist markers.

- [x] 0.42 **RED:** reproduce the original accepted result (request `6019133874`, decision `6019173711`, historical/continuation runs) entering `_formal_consequence` with no `ACTION_RESULT`. Parameterize I/R/M/V/S/F across `COMPLETE / INCOMPLETE / UNKNOWN / CONFLICT`, false READY with unfinished necessary tasks, missing old upload/checkpoint, duplicate irreversible effect, stale/FINDINGS review, ambiguous read, conflicting route/result, and complete source with no formal record; require deterministic disposition independent of model output. For review independence, cover distinct authenticated logins, equal `royhsu-work` logins with an exact subsequent direct-Human review-ID/R attestation and qualified Human-only approval event, and negative missing/edited/connector-authored/unbound/competing attestation cases.
- [x] 0.43 **GREEN:** implement pre-formal I/R/M/V/S/F predicates at the existing application/consequence owners and bounded exact-R Human-authorized recovery-review evidence adoption. Reuse current canonical Human comment/event provenance for same-login Reviewer separation; never infer independence from a shared connector login or from the author/review receipt prose. No new Action, routing, registry or result type. Persist the immutable accepted `READY` formal result at most once only after pre-write COMPLETE; fresh-read and project only `review-implementation` with `next_action`. Reconcile lost responses read-only; preserve old UNKNOWN, no old effect replay, and fresh P/D, W/T, CAS and per-effect isolation for distinct corrections.
- [x] 0.44 **REFACTOR/VERIFY:** run focused/full boundary tests, type/lint/static checks and exact-head validation; prove precise operation-specific blockers, duplicate formal-result and checkpoint NO_WRITE negatives, legal disjoint descendant SHA advance and preservation of prior witness, and one unambiguous consumer for result/route. Record evidence without claiming post-merge production acceptance.


## 1. Contract and typed NO_WORK handoff

- [x] 1.1 RED/GREEN: add contract tests proving `AUTHORIZE` and `FAIL_CLOSED` never enter idle, while one exact completed `NO_WORK` artifact can invoke one bounded Lead idle semantic request.
- [x] 1.2 GREEN: add the typed non-Action dispatch envelope/result parser and producer/consumer boundary, bound to exact request comment, bridge run, artifact id/digest, default-branch revision, and source evidence.
- [x] 1.3 REFACTOR: keep normal `select_work()`, the Action enum, Role derivation, normal labels, and successor lifecycle unchanged; the implementation introduces no idle routing state.

## 2. Safe idle admission application

- [x] 2.1 RED/GREEN: add tests for no-finding zero mutation, existing-candidate tuple completion with unrelated content/labels preserved, and new-candidate creation with exactly `Change: unset + action:explore-change`.
- [x] 2.2 GREEN: implement the smallest repository-owned idle admission actuator using fresh default-branch reauthorization and one logical create/update boundary.
- [x] 2.3 RED/GREEN: cover stale source/default branch, real Actions run/artifact identity and content, interruption-before/after mutation, overlap recovery through all-state correlation, closed/contradictory matches, body/label preservation, and ambiguous-write reconciliation.
- [x] 2.4 GREEN: add minimal non-durable workflow concurrency and read-only ambiguous-write reconciliation; fail closed when uniqueness or the complete postcondition cannot be proved.
- [x] 2.5 REFACTOR: reuse current dispatch/application carrier and fresh-read primitives; no duplicate queue, lock state, lease, cursor, heartbeat, registry, recovery workflow, or hidden backlog is introduced.
- [ ] 2.6 RED/GREEN: add the bounded typed advisory candidate path with one-to-three recommendation validation, exact `advisory:idle` non-routing admission, all-state correlation reconciliation, open-advisory suppression, closed/contradictory fail-closed recovery, ambiguous-write coverage, and production-shaped issue-comment ingress.
- [ ] 2.7 RED/GREEN: derive an unanswered `HUMAN_DECISION_REQUIRED → Lead / resolve-question` wait from the qualified current frontier before semantic ingress; prove an unchanged frontier emits no new `EFFECT_REQUEST`/formal result/mutation, and prove newer qualifying Human or materially changed evidence resumes ordinary execution without persisted wait/retry state.

## 3. Scheduled Task/bootstrap cutover

- [x] 3.1 RED/GREEN: add a production-shaped bridge/bootstrap test showing the exact `NO_WORK` artifact reaches one typed bounded Lead idle ingress and `AUTHORIZE`/`FAIL_CLOSED` do not.
- [x] 3.2 GREEN: connect the repository-visible application carrier to the typed idle boundary through one `IDLE_ADMISSION_REQUEST` Issue-comment RPC on the current daily runtime shard, without representing idle as an Action or relying on the comment as accepted-intent state; reuse the same boundary for content-addressed `APPLICATION_CONTINUATION` recovery.
External Scheduled Task configuration and production acceptance are deployment/lifecycle evidence, not Executor implementation task markers; see final acceptance below.

## 4. Verification and delivery

- [x] 4.1 Run focused idle contract, application, bridge, dispatch, advisory, and unchanged-Human-frontier tests on the final implementation head.
- [x] 4.2 Run full regression, type checks, lint, and repository workflow/static invariant checks on the final implementation head; require remote Python Quality on that exact head.
- [x] 4.3 Run strict OpenSpec validation on this corrected exact OpenSpec revision and again on the final implementation head as required.
## Native production evidence (not implementation task markers)

- Execute the former 0.25 physical Chat connector operation from an actual native Lead Workflow wake, with exact plan, fresh precondition/postcondition reads and durable `APPLICATION_CARRIER_OUTCOME` evidence; no fake connector run counts.
- Observe **two distinct legitimate repository-dispatched Action/Commit/Witness chains** on separate normal wakes with a lawful intervening advance: `P1/D1 -> C1 -> W1`, then fresh `P2/D2 -> C2 -> W2`. Verify successor continuity and preserved W1, not merely two maintenance commits or CI runs.
- Correlate **real native execution** (not manual/fixture/run-now acknowledgement alone) to its exact request, run/artifact or actual execution log and freshly read GitHub postcondition. A required connector operation uses a fresh qualified plan, writes only the missing effect and reaches lawful application continuation; genuine incomplete or conflicting evidence stays UNKNOWN/NO_WRITE.
- After the governed review/merge/finalize/archive lifecycle, observe a real unattended `NO_WORK` wake entering bounded Lead idle discovery with zero noise or one lawful admission. If admission occurs, observe a subsequent normal Action-only wake that takes over its canonical tuple.
- Do not alter the scheduler without separate Human authorization or count a manual imitation as production acceptance.

## Lifecycle gates

These are workflow lifecycle gates, not implementation tasks: independent OpenSpec review must PASS before implementation is authorized; independent implementation review and all current repository gates must PASS before exact-head merge; post-merge canonical state must be freshly verified before governed archive review, merge, and terminal-state verification.

## Parent-outcome continuation

The parent outcome requires a lawful application exit, two real continuous normal Action/Commit witnesses, and later native unattended NO_WORK following lifecycle completion. The 0G checkboxes cover only Executor-implementable Recovery Exit work. Historical diagnostics are not an added gate. A merge does not prove unattended activation; outstanding work remains in the governed lifecycle.
