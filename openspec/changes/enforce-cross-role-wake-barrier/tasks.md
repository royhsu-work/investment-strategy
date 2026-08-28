## 1. RED — lock the prompt/model wake boundary

- [ ] 1.1 Add or revise governance contract regressions proving authoritative default-branch governance instructs same-role continuations to remain work-conserving as fresh workers and cross-role successors to end the current Scheduled-Agent wake.
- [ ] 1.2 Add a regression proving external Scheduled Task bootstrap guidance remains generic and deferential to current default-branch governance rather than duplicating the workflow DAG, fixed-role semantics, or a second wake-state protocol.
- [ ] 1.3 Remove or replace prior acceptance tests whose required behavior is repository-owned mechanical `initial_role` / `continuation_requires_fresh_wake` enforcement; RED must fail because the branch still encodes the superseded Option 1-style mechanical guarantee, not because of unrelated setup or syntax failures.

## 2. GREEN — implement the downgraded enforcement contract

- [ ] 2.1 Align `agents/AGENTS.md` and `agents/templates/messages.md` with the `agents/workflow.md` topology: fresh worker for every selected successor, same-role same-wake continuation allowed, and cross-role handoff instructs the current model invocation to end while preserving durable successor routing.
- [ ] 2.2 Reconcile or remove `continuation_requires_fresh_wake` behavior and related repository runtime code added solely to provide the superseded mechanical hard-stop guarantee. Preserve fresh dispatch, effect reauthorization/postconditions, routing correctness, and unrelated runtime safety behavior.
- [ ] 2.3 Reconcile executable tests tied only to mechanical wake termination while retaining coverage for repository-owned dispatch freshness, routing preservation, mapped-worker freshness, and same-role liveness.
- [ ] 2.4 Keep `agents/workflow.md` unchanged unless implementation proves an actual topology inconsistency. Do not move role-specific successor logic into external Scheduled Task product configuration.

## 3. REFACTOR — make the assurance boundary explicit

- [ ] 3.1 Ensure governance, code, and tests distinguish `fresh mapped worker`, `Scheduled-Agent wake`, and the accepted prompt/model-level wake-terminal instruction without implying a mechanically guaranteed external-host boundary.
- [ ] 3.2 Verify the implementation introduces no OpenAI API key, GitHub Actions-hosted model worker, Work wake attestation, durable wake-role state, queue, lock, lease, heartbeat, sequence counter, fixed-role scheduler, or second dispatcher.

## 4. VERIFY — prove policy coherence without claiming host enforcement

- [ ] 4.1 Run focused Scheduled-Agent governance/runtime regressions covering same-role continuation, cross-role termination instruction, dispatch freshness, and routing preservation.
- [ ] 4.2 Run the repository-required Python quality/test gate and strict OpenSpec validation against the exact implementation head.
- [ ] 4.3 Verify same-role `Lead / explore-change → Lead / propose-change` remains immediately continuable after fresh repository-owned dispatch and a fresh mapped worker.
- [ ] 4.4 Verify Lead→Reviewer, Reviewer→Executor, and Executor→Lead are represented as wake-terminal model/governance instructions while tests do not claim the repository can mechanically prove external ChatGPT task termination.
- [ ] 4.5 Verify WIP=1, Human authority, at-least-once reconstruction, workflow topology, action ownership, and no durable wake-role state remain unchanged.

Refs #161
Explore baseline: #161 comment `5440915970`
Human decision: #161 comment `5452121226` (Option 3; machine/script enforcement no longer required)

<!-- Verification retry trigger only: completion markers remain unset until exact-head VERIFY succeeds. -->
