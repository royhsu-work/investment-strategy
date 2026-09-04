## Delivery invariant

#138 is one parent outcome delivered through mandatory N-1 stages. Every stage MUST be independently executable/testable/mergeable/deployable on then-current N-1; otherwise split it further. A stage never completes #138 while later stages remain. Stage 1 is explicitly ordered: **1A exact-revision application resource first**, then **1B transport de-mailbox**. Stage 1A must be merged and deployed to then-current N-1 before a materially authoring or revising `Lead / propose-change` or `Lead / resolve-question` action may hand #138 to independent OpenSpec review; an unmerged implementation or green checks alone are insufficient. Stage 1B remains mandatory before Stage 2 consumes the run-scoped transport contract, but is not a prerequisite for semantic OpenSpec review readiness. Both Stage 1A and Stage 1B must be deployed before Stage 2.

## 1A. Exact-revision application resource

Parent advances: gate-derived exact-revision OpenSpec validation usable by the already selected Action for both newly produced and already-current target revisions. Remaining: transport de-mailbox, kernel, typed application, wake/state cutover, deletion. N-1: current comment-trigger/application bridge and qualified pinned OpenSpec. Boundary: validation resource only; no transport/topology/state/wake cutover. Next: Stage 1B.

- [ ] 1A.1 RED — reproduce repository-owned OpenSpec write producing exact revision `R` while event validation is `action_required`, has no validator job, or lacks checkout proof; ownership transfer stays fail-closed.
- [ ] 1A.2 RED — prove an already-current exact Change/PR head `R` that still needs readiness validation cannot require an artifact rewrite, dummy-touch, or unrelated content mutation merely to manufacture a validator trigger.
- [ ] 1A.3 RED — prove a materially revising `Lead / resolve-question` cannot be excluded from a required exact-R readiness resource by a Propose-only source Role/Action whitelist.
- [ ] 1A.4 GREEN — derive exact-revision resource eligibility from the governed readiness/effect/artifact gate rather than a hard-coded source Action whitelist.
- [ ] 1A.5 GREEN — support both forms of target `R`: the exact revision just produced by the current authorized OpenSpec mutation and an already-current exact Change/PR head requiring validation with no artifact rewrite.
- [ ] 1A.6 GREEN — run pinned strict validation directly against `R` or explicitly trigger a dedicated deterministic validator bound to `R`; structured evidence proves target `R`, validator checkout `HEAD == R`, qualified pinned compatibility, and strict PASS.
- [ ] 1A.7 GREEN — make that exact-R structured result consumable by the already selected semantic Action; reject missing/failed/cancelled/ambiguous/revision-mismatched/checkout-mismatched/malformed/expired evidence.
- [ ] 1A.8 REFACTOR — keep validation a bounded deterministic application resource, not another semantic Action/model wake, manual approval, stale-CI shortcut, direct-connector bypass, artifact dummy-touch, source-Action whitelist, or generic polling scheduler.
- [ ] 1A.9 VERIFY — live N-1 closed loop for both target forms: newly produced `R` and already-current `R` each obtain checkout proof, qualified pinned strict PASS, and structured evidence consumed by the same selected Action; retain `action_required`/no-validator-job and Resolve-whitelist exclusion as RED regressions.

## 1B. Transport de-mailbox + daily check-in lifecycle

Parent advances: #168 exact run-scoped dispatch/application/validation transport plus fresh daily-bounded runtime check-in discovery/rollover, with request/trigger/audit-only runtime comments, no normal machine-response mailbox, and no permanent check-in pointer. Remaining: kernel, typed application, wake/state cutover, deletion. N-1: Stage 1A is deployed. Boundary: transport adapter and repository-owned check-in administration only; workflow semantics and canonical state remain unchanged. Next: Stage 2.

- [ ] 1B.1 RED — prove exact request->run->structured dispatch/application result correlation; reject `latest`, timing/title inference, response fallback, and missing/multiple/failed/cancelled/malformed/expired evidence.
- [ ] 1B.2 RED — prove each wake must fresh-discover exactly one open `Asia/Taipei` current-day check-in by dedicated non-workflow + canonical local-date identity; zero/duplicate/ambiguous current-day identity and reliance on a permanent `AGENT_RUNTIME_CHECKIN_ISSUE`-style pointer fail closed.
- [ ] 1B.3 RED — prove daily rollover cannot close the prior-day check-in before today's usable check-in is established and fresh-observed, and prove closing the prior-day Issue does not break an already-triggered immutable request `C -> exact run R -> structured result` chain.
- [ ] 1B.4 GREEN — implement idempotent repository-owned daily rollover: establish and fresh-observe today's unique usable check-in before closing prior check-ins; new wakes discover today's Issue from current GitHub state without conversation memory or a permanent pointer.
- [ ] 1B.5 GREEN — make runtime Issue comments request/trigger/audit only and consume dispatch/application/validation results from exact run-scoped surfaces while preserving an in-flight prior-day `C -> R -> result` chain and coordination-Issue semantic evidence.
- [ ] 1B.6 REFACTOR — remove normal response-mailbox correlation/dedup and permanent check-in-pointer coupling without moving workflow semantics into transport or adding recursive workflow-trigger dependence.
- [ ] 1B.7 VERIFY — live Scheduled Task dispatch+application E2E discovers exactly one current-day check-in, proves request C -> exact run R -> terminal -> exact structured result with no machine response comment, exercises idempotent close/create rollover with an in-flight prior-day request, and confirms no model API in Actions.

## 2. Executable kernel shadow

Parent advances: one executable machine topology computes shadow decisions. Remaining: N-1 production still owns effects/state/wakes. N-1: complete Stages 1A+1B provide run-scoped transport plus exact-revision validation resources. Boundary: no mutation cutover. Next: Stage 3.

- [ ] 2.1 RED — exhaustively cover Action vocabulary, Action→Role, explicit merge Actions, finite transitions/effects, WIP/FIFO/debt, illegal states, stale/replay and postconditions.
- [ ] 2.2 GREEN — consolidate smallest kernel and feed it the same authoritative observations as production without owning mutations.
- [ ] 2.3 REFACTOR — generate/mechanically verify `agents/workflow.md`; remove any second executable registry.
- [ ] 2.4 VERIFY — shadow production decisions and explain every divergence from source evidence.

## 3. Typed result/application

Parent advances: typed semantic result→kernel effect→fresh application/postcondition. Remaining: old routing/wake representation. N-1: Stage 2 equivalence on the Stage-1A+1B closed loop. Boundary: routing/wake unchanged; rollback to N-1 effect path. Next: Stage 4.

- [ ] 3.1 RED — bind result to exact Issue/source Action; reject arbitrary successors, Markdown control extraction, stale/contradictory state and replay rewind.
- [ ] 3.2 GREEN — generalize action-owned typed results plus narrative/source evidence; derive effects, fresh-reauthorize, mutate narrowly and observe postconditions.
- [ ] 3.3 REFACTOR — retain action-specific result vocabularies, not a generic outcome state machine.
- [ ] 3.4 VERIFY — cover Explore, pre-acceptance Propose correction, review/implementation/merge/lifecycle finite boundaries plus direct-Human freshness/disposition, partial-mutation/causal-descendant replay, bounded exact-resource observation, and `EXECUTION_EXCEPTION` evidence.

## 4. Wake simplification

Parent advances: exactly one mapped Action/wake with work-conserving action internals. Remaining: N-1 routing representation. N-1: Stage 3 safely persists successor for later fresh wake. Boundary: no state migration. Next: Stage 5.

- [ ] 4.1 RED — completed Action ends wake even for same Role; RED→GREEN→REFACTOR→VERIFY/local correction stays inside selected Action; first absent/queued/in-progress exact resource is not alone Exit Proof while bounded same-action consumption remains, and no successor Action executes in that wake.
- [ ] 4.2 GREEN — remove same-role chaining, cross-role wake barriers, fresh-worker same-wake identity, fixed-role successor comparison and continuation flags.
- [ ] 4.3 REFACTOR — shorten governance/Skills/messages without weakening semantic/evidence/exception obligations.
- [ ] 4.4 VERIFY — wake correctness requires no OpenAI/Responses/other model API or Actions-hosted model worker.

## 5. Canonical-state cutover

Parent advances: Action-only routing, Role derivation, explicit merge Actions, typed retirement of explicitly absorbed pre-activation sources, and live-state migration. Remaining: legacy cleanup. N-1: Stages 1A–4. Boundary: complete authoritative dry-run and reviewed machine-readable retirement plan required; this is semantic cutover. Post-cutover rollback translates from new state only. Next: Stage 6.

- [ ] 5.1 RED — cover terminal/current/debt/legacy/ambiguous live Issue shapes; preserve unrelated labels and immutable Change.
- [ ] 5.2 RED — for the generic absorbed-source retirement entry and live #168 fixture, reject missing/duplicate/malformed plan entries, prose/history/model-discovered candidates, source/absorber identity or state mismatch, incomplete provenance, contradictory observations, and unresolved newer direct-Human input before mutation.
- [ ] 5.3 GREEN — produce and consume one finite reviewed machine-readable cutover plan whose absorbed-source entries bind exact source Issue, expected open/closed + `Change:` + workflow routing state, exact absorbing Issue/Change, and exact durable source/assignment references; do not retain it as a normal dispatch selector or permanent exception registry.
- [ ] 5.4 GREEN — dry-run canonicalization; Human only for genuine ambiguity; never write to discover. For each authorized absorbed-source entry, fresh-verify source/absorber state, close the source if open, remove only currently observed workflow `agent:*`/`action:*` labels, preserve body/comments/results and unrelated labels, and treat interruption as visible closed-routing debt resumable only through missing narrow effects.
- [ ] 5.5 GREEN — migrate remaining live state to one Action, switch production dispatch/application/bootstrap to kernel, and replace generic merge Action with explicit implementation/archive merge Actions.
- [ ] 5.6 VERIFY — execute the reviewed live #168 entry from expected `open + Change: unset + agent:lead + action:explore-change` to fresh-observed `closed + no workflow routing`; prove its `ACTION_RESULT(PROPOSAL_READY)`, body/comments and unrelated labels remain provenance, replay is idempotent, and later normal FIFO cannot select or suppress it through plan/prose/history.
- [ ] 5.7 VERIFY — fresh-observe every mutation and run WIP/FIFO/debt/review/merge/lifecycle production regressions, including close-before-routing-cleanup interruption and fail-closed plan/state drift.

## 6. Deletion/context reduction

Parent advances: removes superseded production paths and completes #138 after full gates. Remaining: none after verification. N-1: Stage 5 canonical state. Boundary: rollback never restores permanent dual authority. Next: ordinary lifecycle.

- [ ] 6.1 RED — deleted representations cannot re-enter normal control; history remains readable but non-authoritative.
- [ ] 6.2 GREEN — delete normal `agent:*` routing, generic merge-phase inference, response-mailbox/history coupling, Markdown topology/effect parsing, same-wake continuation/barriers, obsolete history compatibility, legacy Responses/model-worker host code and redundant machine-control prose/tests.
- [ ] 6.3 REFACTOR — remove compatibility helpers that only preserve deleted paths; retain bounded migration/audit fixtures.
- [ ] 6.4 VERIFY — full Python/Ruff/mypy/governance/Skill/live-E2E/migration/production tests plus exact-revision strict OpenSpec.
- [ ] 6.5 VERIFY — record architectural subtraction versus current `main`.
