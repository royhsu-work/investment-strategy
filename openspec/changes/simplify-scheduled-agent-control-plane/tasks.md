## 1. Slice: establish one typed executable topology without changing production mutations

- [ ] 1.1 RED — add exhaustive tests for the approved Action vocabulary, Action→Role derivation, legal typed results/transitions, terminal effects, effect capabilities, and illegal/unknown transitions; include distinct `merge-implementation-pr` and `merge-archive-pr` states.
- [ ] 1.2 RED — add governance regression coverage proving the machine-readable topology cannot diverge from the Human-readable `agents/workflow.md` projection and proving production code does not parse that Markdown to reconstruct transitions.
- [ ] 1.3 GREEN — introduce the smallest executable topology/kernel owner by consolidating or replacing the current duplicated dispatcher/effect-contract/topology logic; keep existing production mutation authority unchanged during this slice.
- [ ] 1.4 GREEN — make Role a pure derivation from Action in the kernel and expose typed result/transition APIs consumed by tests without introducing a generic workflow framework.
- [ ] 1.5 REFACTOR — remove any newly redundant second Action/Role/transition registry created during implementation; the slice is not complete while two executable DAGs require synchronization by convention.
- [ ] 1.6 VERIFY — run the exhaustive topology/governance tests plus existing dispatcher/effect regressions and prove no production mutation behavior has changed yet.

## 2. Slice: make Action-only routing work at production dispatch/application boundaries

- [ ] 2.1 RED — add production-boundary tests where open workflow state contains exactly one `action:*` label and no `agent:*`; prove role derivation, WIP=1/finish-first, pre-activation FIFO, formal active selection, closed-routing debt, terminal retirement, invalid/multiple Action failure, and preservation of unrelated labels.
- [ ] 2.2 RED — add regressions proving legacy `agent:*` presence after cutover cannot become an alternate current routing authority or recreate a Role/Action mismatch selector.
- [ ] 2.3 GREEN — change authoritative GitHub acquisition/normalization and dispatch to consume Action-only current routing and derive Role from the executable topology.
- [ ] 2.4 GREEN — change repository application to derive successor Action and effect capabilities from the same topology, fresh-reauthorize the exact source Action/Change/revision, apply narrow effects, and prove fresh postconditions.
- [ ] 2.5 GREEN — route implementation-review PASS to `merge-implementation-pr` and archive-review PASS to `merge-archive-pr`; preserve all existing phase-specific exact-head/review/linkage/cleanup merge gates.
- [ ] 2.6 REFACTOR — remove normal production dependence on persistent `agent:*` labels, Role/Action tuple validators, and phase inference made obsolete by explicit merge actions.
- [ ] 2.7 VERIFY — run dispatcher/application/merge/lifecycle regressions including #155 and #175 cases against the production-consumed boundary.

## 3. Slice: generalize typed semantic results and exact deterministic application

- [ ] 3.1 RED — add action-bound result tests proving a worker result is correlated to exact Issue + authorized source Action and cannot choose arbitrary successor routing.
- [ ] 3.2 RED — prove free-form narrative containing `Action:`, `Role:`, `Result:`, or routing-looking Markdown cannot redefine a typed control result or transition.
- [ ] 3.3 RED — add stale/replay regressions: stale source Action/Change/revision rejects mutation; already-applied legal postcondition returns idempotently without rewind; contradictory state fails closed.
- [ ] 3.4 GREEN — provide one typed semantic-result envelope for action-owned finite results while preserving action-specific narrative/source evidence and semantic Role authority.
- [ ] 3.5 GREEN — make application validate typed results and derive only topology-owned effects; eliminate Markdown transition/effect parsing from the normal path.
- [ ] 3.6 REFACTOR — retain action-specific semantic result vocabularies rather than inventing one generic success/failure workflow taxonomy.
- [ ] 3.7 VERIFY — run result/application regressions for Explore, Propose correction, reviews, implementation readiness, both merge actions, lifecycle results, Human boundaries, and terminal effects where those actions have bounded control outcomes.

## 4. Slice: enforce one mapped action per Scheduled Task wake and simplify governance/Skills

- [ ] 4.1 RED — add governance/runtime tests proving one wake may execute exactly one repository-authorized mapped Action and must end after its result/application boundary even when the successor derives to the same Role.
- [ ] 4.2 RED — prove action-internal work remains work-conserving: actionable RED→GREEN→REFACTOR/VERIFY, correction of action-local validation failure, and bounded consumption of an exact just-triggered external resource stay inside the selected action while preconditions remain current.
- [ ] 4.3 GREEN — remove same-role successor continuation, cross-role wake-barrier orchestration, fresh-worker same-wake chaining, fixed-invocation-role successor comparison, `continuation_required`/equivalent state, and Scheduled Task prompt logic used only to decide a second mapped action in the same wake.
- [ ] 4.4 GREEN — align `agents/AGENTS.md`, roles, mapped Skills, and canonical message guidance so they retain semantic procedure/evidence/exception obligations but delegate finite routing/transition semantics to the executable topology/kernel.
- [ ] 4.5 GREEN — mechanically generate or verify `agents/workflow.md` Action/Role/transition presentation from the executable topology; preserve explanatory prose only where it does not redefine machine semantics.
- [ ] 4.6 REFACTOR — shorten/remove duplicated deterministic predicates from mapped Skills instead of moving them to another prose helper; keep `skill-creator` responsibility boundaries and progressive disclosure intact.
- [ ] 4.7 VERIFY — run governance/Skill/template tests and prove no OpenAI/Responses/other model API or GitHub-hosted model worker is required for wake correctness.

## 5. Slice: prove replaceable no-API transport and live application before cutover

- [ ] 5.1 RED — add adapter tests for exact request → exact GitHub Actions run/job/result correlation for dispatch and application; reject latest-result/time-window/history-prose inference as a fallback.
- [ ] 5.2 GREEN — reduce Issue-comment bridge behavior to transport/RPC only and expose structured run-scoped dispatch/application results consumable by Scheduled Tasks without making response comments workflow state.
- [ ] 5.3 GREEN — implement the deterministic application transport needed for a Scheduled Task to submit one typed worker result to GitHub Actions and receive exact applied/failed postcondition evidence, with no model execution inside Actions.
- [ ] 5.4 VERIFY — exercise one live no-API dispatch E2E and one live typed application E2E against an authorized test/real workflow boundary, including stale/replay failure behavior and postcondition observation.
- [ ] 5.5 REFACTOR — delete response-mailbox/history-dedup code that is unnecessary once exact run/job correlation owns transport; keep a thin replaceable adapter so a future direct Actions invocation surface can replace comments without semantic changes.

## 6. Slice: shadow, canonicalize live state, cut over, and delete the old control plane

- [ ] 6.1 RED — build migration fixtures from complete authoritative GitHub observations covering every live/routed coordination Issue shape: terminal, valid pre-activation/formal Action state, closed debt, legacy Role+Action state, and genuinely ambiguous state.
- [ ] 6.2 GREEN — run the new kernel in shadow against current production observations and compare dispatch/effect decisions; classify every divergence from source evidence rather than normalizing it away.
- [ ] 6.3 GREEN — produce a one-time canonicalization plan mapping each current live/routed Issue to Action-only state or terminal retirement; require Human input only for genuinely ambiguous cases and never use a write to discover the answer.
- [ ] 6.4 VERIFY — prove migration dry-run completeness/provenance and exact before→after expectations, including preservation of unrelated labels and immutable `Change:` identities.
- [ ] 6.5 GREEN — perform the approved cutover: migrate current live routing to Action-only labels, switch production dispatch/application/bootstrap to the executable kernel, and verify each mutated Issue/postcondition before continuing.
- [ ] 6.6 GREEN — after cutover acceptance, delete obsolete production hot paths: persistent `agent:*` routing support, Role/Action tuple mismatch/recovery branches, historical eligibility/cutoff parsers no longer required by live canonical state, Markdown topology/effect parsers, obsolete model-worker host code, same-wake continuation/wake-barrier machinery, and compatibility-only transport logic.
- [ ] 6.7 REFACTOR — remove compatibility tests/helpers that only preserve deleted representations while retaining migration/audit fixtures needed to prove historical evidence remains readable but non-authoritative.
- [ ] 6.8 VERIFY — run the full Python test suite, Ruff lint/format, mypy, governance/Skill consistency checks, migration regressions, production-boundary E2E tests, and strict OpenSpec validation on the exact final implementation revision.
- [ ] 6.9 VERIFY — record before/after architectural subtraction evidence: canonical live routing dimensions, executable topology owners, history/parser hot paths, wake continuation paths, and transport-state dependencies are strictly fewer after cutover.

### Cutover constraint

Dual old/new control paths are permitted only through Slices 1–5 for shadow/proof while current production mutation authority remains unchanged. Slice 6 must not declare completion until production uses the new kernel and superseded normal selectors/parsers/continuation paths are removed. A bounded emergency compatibility adapter after cutover may translate from new canonical state only; it must not restore old Role labels or historical prose as a second current-state authority.