## Delivery invariant

#138 is one parent outcome delivered through mandatory N-1 stages. Every stage MUST be independently executable/testable/mergeable/deployable on then-current N-1; otherwise split it further. A stage never completes #138 while later stages remain.

## 1. Transport de-mailbox + daily check-in

Parent advances: #168 exact run-scoped dispatch/application results. Remaining: kernel, typed application, wake/state cutover, deletion. N-1: current comment-trigger bridge. Boundary: transport only; rollback may restore old transport. Next: Stage 2.

- [ ] 1.1 RED — prove exact request→exact Actions run→structured result; reject latest/time-proximity/response fallback and missing/multiple/failed/cancelled/malformed/expired evidence.
- [ ] 1.2 GREEN — make runtime Issue request/trigger/audit only; consume dispatch/application results from exact run-scoped surfaces; retain bounded daily check-in and coordination-Issue semantic evidence.
- [ ] 1.3 REFACTOR — remove normal response-mailbox correlation/dedup without moving workflow semantics into transport.
- [ ] 1.4 VERIFY — live Scheduled Task dispatch+application E2E; no model API in Actions.

## 2. Executable kernel shadow

Parent advances: one executable machine topology computes shadow decisions. Remaining: N-1 production still owns effects/state/wakes. N-1: Stage 1 transports shadow evidence. Boundary: no mutation cutover. Next: Stage 3.

- [ ] 2.1 RED — exhaustively cover Action vocabulary, Action→Role, explicit merge Actions, finite transitions/effects, WIP/FIFO/debt, illegal states, stale/replay and postconditions.
- [ ] 2.2 GREEN — consolidate smallest kernel and feed it the same authoritative observations as production without owning mutations.
- [ ] 2.3 REFACTOR — generate/mechanically verify `agents/workflow.md`; remove any second executable registry.
- [ ] 2.4 VERIFY — shadow production decisions and explain every divergence from source evidence.

## 3. Typed result/application

Parent advances: typed semantic result→kernel effect→fresh application/postcondition. Remaining: old routing/wake representation. N-1: Stage 2 equivalence. Boundary: routing/wake unchanged; rollback to N-1 effect path. Next: Stage 4.

- [ ] 3.1 RED — bind result to exact Issue/source Action; reject arbitrary successors, Markdown control extraction, stale/contradictory state and replay rewind.
- [ ] 3.2 GREEN — generalize action-owned typed results plus narrative/source evidence; derive effects, fresh-reauthorize, mutate narrowly and observe postconditions.
- [ ] 3.3 REFACTOR — retain action-specific result vocabularies, not a generic outcome state machine.
- [ ] 3.4 VERIFY — cover Explore, pre-acceptance Propose correction, review/implementation/merge/lifecycle/Human finite boundaries.

## 4. Wake simplification

Parent advances: exactly one mapped Action/wake with work-conserving action internals. Remaining: N-1 routing representation. N-1: Stage 3 safely persists successor for later fresh wake. Boundary: no state migration. Next: Stage 5.

- [ ] 4.1 RED — completed Action ends wake even for same Role; RED→GREEN→REFACTOR→VERIFY/local correction/bounded exact-resource consumption stays inside selected Action.
- [ ] 4.2 GREEN — remove same-role chaining, cross-role wake barriers, fresh-worker same-wake identity, fixed-role successor comparison and continuation flags.
- [ ] 4.3 REFACTOR — shorten governance/Skills/messages without weakening semantic/evidence/exception obligations.
- [ ] 4.4 VERIFY — wake correctness requires no OpenAI/Responses/other model API or Actions-hosted model worker.

## 5. Canonical-state cutover

Parent advances: Action-only routing, Role derivation, explicit merge Actions, live-state migration. Remaining: legacy cleanup. N-1: Stages 1–4. Boundary: complete authoritative dry-run required; this is semantic cutover. Post-cutover rollback translates from new state only. Next: Stage 6.

- [ ] 5.1 RED — cover terminal/current/debt/legacy/ambiguous live Issue shapes; preserve unrelated labels and immutable Change.
- [ ] 5.2 GREEN — dry-run canonicalization; Human only for genuine ambiguity; never write to discover.
- [ ] 5.3 GREEN — migrate to one Action, switch production dispatch/application/bootstrap to kernel, replace generic merge Action with explicit implementation/archive merge Actions.
- [ ] 5.4 VERIFY — fresh-observe every mutation and run WIP/FIFO/debt/review/merge/lifecycle production regressions.

## 6. Deletion/context reduction

Parent advances: removes superseded production paths and completes #138 after full gates. Remaining: none after verification. N-1: Stage 5 canonical state. Boundary: rollback never restores permanent dual authority. Next: ordinary lifecycle.

- [ ] 6.1 RED — deleted representations cannot re-enter normal control; history remains readable but non-authoritative.
- [ ] 6.2 GREEN — delete normal `agent:*` routing, generic merge-phase inference, response-mailbox/history coupling, Markdown topology/effect parsing, same-wake continuation/barriers, obsolete history compatibility, legacy Responses/model-worker host code and redundant machine-control prose/tests.
- [ ] 6.3 REFACTOR — remove compatibility helpers that only preserve deleted paths; retain bounded migration/audit fixtures.
- [ ] 6.4 VERIFY — full Python/Ruff/mypy/governance/Skill/live-E2E/migration/production tests plus exact-revision strict OpenSpec.
- [ ] 6.5 VERIFY — record architectural subtraction versus current `main`.
