## Delivery invariant

#138 is one parent outcome. Every stage MUST be independently executable/testable/mergeable/deployable on then-current N-1 or be split. Order: **1A exact-R validation → 1B content-addressed work-product ingress/self-hosting → 1C run-scoped transport/daily check-in → 1D identity-sensitive PR carrier → 2 kernel shadow → 3 typed application → 4 one-Action wake → 5 canonical cutover/source retirement → 6 deletion/context reduction**.

Stage 1A is the materially revised Resolve action's exact-handoff semantic-review prerequisite. Stage 1B preserves the distinct work-product ingress/application-completion boundary and production live-E2E obligation established by the M0 bootstrap. Stages 1C/1D remain mandatory before Stage 2 but add no separate semantic OpenSpec review gate after valid Stage-1A evidence.

Within each machine-authorized Action, plan the primary execution objective as one bounded verified vertical slice: `Reconstruct → RED exact gap/blocker → GREEN legal correction → VERIFY exact postcondition/revision/gate → durable checkpoint`. A file write, API call, Actions run, or first nonterminal resource is not a completed slice. If the slice cannot reasonably reach VERIFY in one normal invocation, split it before execution at a meaningful outcome boundary rather than fragmenting it opportunistically.

## 1A. Exact-revision application resource

Advances exact-R readiness for newly produced and already-current heads. Boundary: validation resource only. Next: 1B.

- [x] 1A.1 RED — reproduce `action_required`/no-validator-job or missing-checkout-proof failure for repository-produced `R`.
- [x] 1A.2 RED — prove already-current `R` cannot require rewrite/dummy-touch merely to trigger validation.
- [x] 1A.3 RED — prove `Lead / resolve-question` cannot be excluded by a Propose-only resource whitelist.
- [x] 1A.4 GREEN — derive eligibility from the governed readiness/effect/artifact gate.
- [x] 1A.5 GREEN — support newly produced and already-current exact `R`.
- [x] 1A.6 GREEN — evidence proves target `R`, checkout `HEAD == R`, qualified pinned compatibility, strict PASS.
- [x] 1A.7 GREEN — selected Action consumes structured result; invalid/missing/stale/mismatched evidence fails closed.
- [x] 1A.8 REFACTOR — no model wake, manual approval, stale CI, connector bypass, dummy-touch, source whitelist, or polling scheduler.
- [ ] 1A.9 VERIFY — live N-1 closed loop covers both target forms and retains both RED regressions.

## 1B. Content-addressed work-product ingress / self-hosting

Advances repository-owned OpenSpec work-product ingress/application completion without turning Issue comments, semantic workers, or mutation carriers into workflow authority. N-1: 1A deployed plus the bounded M0 bootstrap on current default branch. Boundary: work-product ingress, exact revision construction, and application-owned completion only; control/request transport, run-scoped result transport, and identity-sensitive PR carrier remain separate. Next: 1C.

- [ ] 1B.1 RED — reject full source/spec/test content as Issue-comment persistence transport; require a bounded manifest carrying only exact branch/base identity plus path, referenced blob SHA, and current expected blob SHA for each changed file.
- [ ] 1B.2 RED — reject stale PR head/base, stale current-file SHA, missing/mismatched referenced blob, duplicate/escaping path, force update, or any worker-created tree/commit/ref as authoritative application.
- [ ] 1B.3 GREEN — semantic worker may create only unreferenced Git blobs as untrusted work-product ingress; repository application fresh-reauthorizes the exact source Action, verifies current Issue/Change/PR/branch/base/path/current-blob identities, uses application-owned tree construction as the first cross-credential resolution boundary for referenced blob SHAs, fresh-observes exact path/blob mappings before commit, builds one single commit revision `R`, advances only the exact current branch without force, and fresh-observes ref/PR/commit/file postconditions.
- [ ] 1B.4 GREEN — application exposes the resulting exact `R` to the same exact-revision validation boundary and owns canonical cross-role `HANDOFF` persistence only after source `ACTION_RESULT`, routing mutation, and target routing are durably observed.
- [ ] 1B.5 REFACTOR — keep control/request transport, work-product ingress, effect/revision authorization, mutation-carrier execution, run-scoped result transport, and postcondition observation as distinct replaceable boundaries; direct application-side blob GET is not required for cross-credential existence, transient ingress is not durable workflow state, and the ingress/carrier gains no Issue/Action/successor/retry/success authority.
- [ ] 1B.6 VERIFY — live N-1 E2E proves connector-created content-addressed ingress → application-owned tree resolution → single revision `R` → exact-R strict validation and, for a cross-role transfer, application-owned canonical HANDOFF; stale/unavailable/mismatched inputs fail closed. M0 PRs #189/#190 are prerequisite/buildability evidence and do not by themselves complete this formal stage or #138.

## 1C. Run-scoped transport + daily check-in

Advances #168 exact run-scoped transport and daily check-in lifecycle. N-1: 1A+1B deployed. Boundary: transport/discovery only. Next: 1D.

- [ ] 1C.1 RED — require exact request→run→structured-result correlation; reject `latest`, timing/title inference, response fallback, and incomplete/failed evidence.
- [ ] 1C.2 RED — require exactly one open `Asia/Taipei` current-day check-in from current GitHub state; reject zero/duplicate/ambiguous identity and permanent-pointer dependence.
- [ ] 1C.3 GREEN/REFACTOR — establish+observe today before closing prior check-ins; preserve in-flight prior-day correlation; runtime comments become request/trigger/audit only; remove response-mailbox and permanent pointer coupling.
- [ ] 1C.4 VERIFY — live Scheduled Task E2E proves current-day discovery, exact run-scoped dispatch/application/validation result, rollover, no response mailbox, and no model API in Actions.

## 1D. Identity-sensitive PR carrier boundary

Separates repository effect authority from GitHub mutation identity for identity-sensitive PR lifecycle effects. N-1: 1A+1B+1C deployed. Boundary: carrier execution only; no work-product ingress ownership, routing/topology/wake cutover, or durable wait/retry state. Next: 2.

- [ ] 1D.1 RED — reproduce a repository-authorized PR effect that `GITHUB_TOKEN` cannot legally execute or whose bot identity breaks required event propagation; permission widening is not the fix.
- [ ] 1D.2 RED — carrier cannot select Issue/Action/successor/effect, weaken exact target/head/base/linkage/preconditions, infer retry, or make API success authoritative; failures cannot authorize duplicate PR creation.
- [ ] 1D.3 GREEN — kernel/application derives carrier eligibility and exact target/precondition/revision-bound plan; event-capable Scheduled-Agent connector/GitHub App executes only that plan.
- [ ] 1D.4 GREEN/REFACTOR — reuse an existing legal PR when exact head/base/linkage can be preserved; replacement requires fresh exact authority. Repository fresh-observes postconditions. Preserve #58 validated-archive-branch success boundary; no carrier wait state, generic retry, lock/lease, or second DAG.
- [ ] 1D.5 VERIFY — E2E covers event propagation, exact binding, reuse-first recovery, stale/failure reconstruction, no Actions PR-create permission dependency, and unchanged independent review/merge/archive gates.

## 2. Executable kernel shadow

Advances one executable machine topology in shadow. N-1: 1A–1D deployed. Boundary: no mutation cutover. Next: 3.

- [ ] 2.1 RED — exhaust Action vocabulary, Action→Role, explicit merge Actions, finite transitions/effects, WIP/FIFO/debt, carrier eligibility, illegal states, stale/replay, postconditions.
- [ ] 2.2 GREEN — smallest kernel consumes the same authoritative observations as production without owning mutation.
- [ ] 2.3 REFACTOR — generate/mechanically verify `agents/workflow.md`; no competing executable registry.
- [ ] 2.4 VERIFY — shadow production decisions and explain every divergence from source evidence.

## 3. Typed result/application

Advances typed semantic result→exact kernel effect/carrier plan→fresh application/postcondition, including deterministic rejection observability. N-1: Stage 2 equivalence. Routing/wake unchanged. Next: 4.

- [ ] 3.1 RED — bind result to exact Issue/source Action; reject arbitrary successor, Markdown control extraction, stale/contradictory state, replay rewind, and aggregate-only deterministic guard failure reporting that hides which predicate failed.
- [ ] 3.2 GREEN — action-owned typed results + narrative/source evidence; derive exact effect/carrier plan, fresh-reauthorize, execute narrowly, accept only repository-observed postcondition, and emit machine-readable exact failed guard class plus relevant expected/observed evidence on deterministic rejection.
- [ ] 3.3 REFACTOR — retain action-specific result vocabularies and structured rejection evidence at the executable owner; do not create a generic outcome/retry state machine or move workflow authority into the carrier.
- [ ] 3.4 VERIFY — cover Explore/correction/review/implementation/merge/lifecycle, Human freshness, partial mutation/causal descendants, exact-resource observation, carrier failure, `EXECUTION_EXCEPTION`, and representative rejection classes such as stale source, expected-SHA mismatch, unsupported operation, and failed effect-specific structural guard without semantic reverse engineering.

## 4. One-Action wake

Advances exactly one mapped Action per wake with one bounded verified vertical slice as the primary execution objective and work-conserving internals. N-1: Stage 3 persists successor for later dispatch. Next: 5.

- [ ] 4.1 RED — completed Action ends wake even for same Role; the authorized Action's bounded `Reconstruct→RED→GREEN→VERIFY→checkpoint` slice stays inside the Action; file/API/Actions intermediate success or first nonterminal exact resource is not alone Exit Proof; no successor Action executes.
- [ ] 4.2 GREEN — execute the bounded same-Action slice through exact VERIFY and durable checkpoint when legal; split before execution when the objective cannot reasonably reach VERIFY in one normal invocation; remove same-role chaining, cross-role barriers, fresh-worker same-wake identity, fixed-role successor comparison, continuation flags.
- [ ] 4.3 REFACTOR — shorten governance/Skills/messages without weakening semantic/evidence/carrier/exception obligations or the verified-slice stop boundaries.
- [ ] 4.4 VERIFY — prove intermediate mechanical success cannot be reported as slice completion, verify governed stop boundaries, and prove no OpenAI/Responses/other model API or Actions-hosted model worker.

## 5. Canonical cutover + typed source retirement

Advances Action-only routing, Role derivation, explicit merge Actions, typed retirement of explicitly absorbed sources. N-1: 1A–4. Requires authoritative dry-run + finite reviewed retirement plan. Rollback translates from new state only. Next: 6.

- [ ] 5.1 RED — cover terminal/current/debt/legacy/ambiguous Issue shapes; preserve immutable Change and unrelated labels.
- [ ] 5.2 RED — reject missing/duplicate/malformed retirement entries, prose/history/model-discovered candidates, state/provenance contradiction, newer unresolved Human input.
- [ ] 5.3 GREEN — finite reviewed plan binds exact source Issue, expected lifecycle/Change/routing, absorbing Issue/Change, exact durable source/assignment refs; never becomes normal selector/exception registry.
- [ ] 5.4 GREEN — fresh-verify; close source if open; remove only observed workflow `agent:*`/`action:*`; preserve body/comments/results/unrelated labels; interruption remains visible closed-routing debt.
- [ ] 5.5 GREEN — migrate remaining live state to one Action; production uses kernel; generic merge becomes explicit implementation/archive merge Actions.
- [ ] 5.6 VERIFY — retire #168 to fresh-observed `closed + no workflow routing` while preserving `ACTION_RESULT(PROPOSAL_READY)` provenance; replay idempotent; no FIFO selection/suppression through plan/prose/history.
- [ ] 5.7 VERIFY — fresh-observe every mutation and run WIP/FIFO/debt/review/merge/lifecycle regressions including interruption and plan drift.

## 6. Deletion/context reduction

Completes #138 only after full gates. N-1: Stage 5 canonical state. Rollback never restores permanent dual authority.

- [ ] 6.1 RED — deleted representations cannot re-enter control; history remains readable but non-authoritative.
- [ ] 6.2 GREEN — delete normal `agent:*` routing, generic merge-phase inference, response mailbox/history coupling, Markdown topology/effect parsing, same-wake continuation/barriers, obsolete compatibility, legacy model-host code, Actions-owned identity-sensitive PR lifecycle paths, redundant machine-control prose/tests.
- [ ] 6.3 REFACTOR — remove helpers only preserving deleted paths; retain bounded migration/audit fixtures.
- [ ] 6.4 VERIFY — full Python/Ruff/mypy/governance/Skill/live-E2E/migration/production tests plus exact-revision strict OpenSpec.
- [ ] 6.5 VERIFY — record architectural subtraction versus current `main`.
