## Delivery invariant

#138 is one parent outcome and PR #178 remains its implementation vehicle. Every boundary below MUST be independently executable, testable, reviewable, and deployable on then-current N-1 or be split only at the minimum safe verified boundary. No boundary completion alone closes #138.

The target state is Issue lifecycle + immutable Change + action:<action> with Role = role_for(Action). Results, reviews, Human decisions, exact revisions, and transport records remain evidence. WIP=1, finish-first, stale/replay/no-rewind/fail-closed behavior, Human authority, independent gates, exact-head merge safety, content-addressed ingress, and carrier separation remain required.

## A. Shadow the smallest executable model

- [ ] A.1 Reconstruct current production selection and the material failure evidence from main, #138, PR #178, and issuecomment-5528834334.
- [x] A.2 Define one finite Action vocabulary, ACTION_ROLE, TRANSITIONS, role_for(action), next_action(current_action, result), and select_work(authoritative_observations) on the default-branch-owned executable surface.
- [x] A.3 Define bounded typed result classes and exact deterministic effect/postcondition guards without adding a generic orchestration, retry, lock/lease, or second-DAG framework.
- [x] A.4 Generate or mechanically verify the Human-readable workflow presentation against the executable model; fail validation on drift instead of parsing Markdown at runtime.
- [x] A.5 Run a no-mutation shadow comparison across active, pre-activation, closed-debt, stale, replay, and competing-wake observations. Preserve exact evidence for any divergence.
- [x] A.6 Verify WIP=1, finish-first, Human authority, complete/provenance-qualified observation, and stale/concurrency fail-closed behavior in the shadow boundary.

## B. Cut over bounded transport and Action-only execution

### B1. Transport shard

- [ ] B1.1 Establish the current-day Asia/Taipei control shard with at most one usable shard for the day.
- [ ] B1.2 Correlate each request to exactly one Actions run and consume only that run's structured result.
- [ ] B1.3 Prove malformed, duplicate, missing, multiple, failed, cancelled, expired, uncorrelated, and stale transport evidence fails closed.
- [ ] B1.4 Establish today's shard before retiring an older shard and preserve an in-flight request -> exact run -> result chain.
- [ ] B1.5 Remove response-mailbox result authorization, latest/title/timing inference, and permanent control-Issue lifecycle semantics.

### B2. Fresh typed application

- [ ] B2.1 Fresh-reauthorize the exact source Issue/Change/Action and derive next_action from the current Action plus bounded typed result.
- [ ] B2.2 Apply only the exact necessary issue, routing, tree/commit/ref, validation, PR, or carrier effects and freshly observe every postcondition.
- [ ] B2.3 Preserve stale/concurrency fail-closed behavior, idempotent still-required reconciliation, no replay of durable work, and no rewind of consumed descendants.
- [ ] B2.4 Emit machine-readable deterministic rejection classification with relevant expected/observed evidence; rejection never authorizes retry or a weaker plan.

### B3. One Action per wake

- [ ] B3.1 Load one fresh machine-selected Action and its derived Role/Skill per Scheduled Task wake.
- [ ] B3.2 Execute one bounded verified semantic slice and record its typed result/evidence.
- [ ] B3.3 Persist the unique derived successor or terminal state, then exit before executing the successor.
- [ ] B3.4 Verify same-Role and cross-Role successors both require a later fresh dispatch and no continuation/barrier protocol.
- [ ] B3.5 Keep semantic judgment in the mapped Role/Skill; workers cannot self-select Issues, Roles, Actions, successors, targets, retries, or success.

### B4. Exact revision and work-product ingress

- [ ] B4.1 Preserve exact-R validation for both newly produced and already-current revisions with checkout HEAD == R, qualified pinned compatibility, and strict PASS.
- [ ] B4.2 Keep validation eligibility gate-derived rather than tied to a source-role/action whitelist.
- [ ] B4.3 Accept only unreferenced worker-created blobs plus exact branch/base/path/blob/current-SHA manifest identity.
- [ ] B4.4 Let application construct the one exact tree/commit/ref and observe PR/head/file postconditions; reject stale, duplicate, escaping, unavailable, mismatched, force, or incomplete operations.
- [ ] B4.5 Verify production live E2E from content ingress through exact tree, exact revision, and exact-R validation.

### B5. Explicit merge and carrier boundaries

- [ ] B5.1 Replace generic merge-pr phase inference with explicit merge-implementation-pr and merge-archive-pr Actions.
- [ ] B5.2 Preserve independent review gates, exact PR-head/linkage/revision checks, Human freshness, native archive close, and deterministic terminal cleanup.
- [ ] B5.3 Separate repository effect authority from mutation-carrier identity; the carrier executes only the bound plan and cannot select workflow meaning.
- [ ] B5.4 Preserve the observed Actions PR-create limitation without enabling Actions PR-create/approve permission; use a legal event-capable carrier where required.
- [ ] B5.5 Verify reuse-first recovery and exact-head postconditions for implementation and Archive PRs.

## C. Delete superseded production paths and context

- [ ] C.1 Retire normal agent:* routing after Action-only routing is deployed; preserve historical labels only as bounded migration/retirement evidence.
- [ ] C.2 Remove normal cross-role journal/completion protocols, same-role continuation, cross-role barriers, continuation flags/cursors, and public recovery states.
- [ ] C.3 Remove response-mailbox/history coupling and permanent control-Issue lifecycle semantics.
- [ ] C.4 Remove Markdown/prose topology and effect parsing from runtime and keep one generated/mechanically verified presentation.
- [ ] C.5 Remove generic merge-phase inference and redundant lifecycle-phase compatibility.
- [ ] C.6 Remove obsolete legacy model-host/Responses paths, unused transport shims, and redundant machine-control tests/prose after coverage is moved to the executable model.
- [ ] C.7 Re-run complete current-state, concurrency, stale/replay/no-rewind, review, merge, archive, and transport validation on the reduced production surface.
- [ ] C.8 Record a final size/authority comparison proving fewer canonical state dimensions and fewer independent executable decision paths than current main.

## Required semantic review

- [ ] R.1 Lead verifies all required artifacts, trace references, canonicalization readiness, and exact-R strict validation for the corrected revision.
- [ ] R.2 Independent Reviewer / review-openspec performs fresh source-chain, reverse/forward semantic, safety, and exact-revision review.
- [ ] R.3 Implementation does not begin under the corrected meaning until the new independent review gate passes.
- [ ] R.4 Existing PR #178, Change identity, Issue history, and unrelated content remain preserved throughout.

Refs #138
