# Design

## Current decision boundary

The original Explore reconstruction used default-branch revision `2e00e236f24ba41302c9ba18c685acdf4cebe4ed`; the earlier continuation was reconciled onto historical N-1 substrate `main@5fa6fdf7d9b33e3f2718c9525bb685f74393d3f3`. Fresh current delivery authority is `main@1ca1d8e37e42bf1b689826ec34a0e335ba1f68b4`; these owners remain unchanged:

- `workflow_dispatch.py` and the runtime preflight reconstruct current repository work and return `AUTHORIZE`, `NO_WORK`, or `FAIL_CLOSED`.
- `issue_comment_bridge.py` checks the authoritative default branch and publishes one run-scoped dispatch-result artifact.
- `scheduled_agent_application_bridge.py` and its materialization/effect modules own fresh reauthorization, exact repository effects, postconditions, carrier boundaries, and formal successor qualification.
- `.github/workflows/scheduled-agent-bridge.yml` and `.github/workflows/scheduled-agent-application.yml` are repository-owned execution carriers.
- the external Scheduled Task/bootstrap is the product boundary that must interpret the exact dispatch artifact and invoke a semantic Lead run; it is not represented in normal Issue routing.

The original gap was production reachability of bounded idle semantics. Normal selection remains authoritative; no empty queue permits inferred work. The typed substrate is now merged, while bounded advisory/wait delivery and post-terminal production acceptance remain required.

The historical pre-consolidation delivery baseline was `main@5fa6fdf7d9b33e3f2718c9525bb685f74393d3f3`. The shared application substrate and same-Change recovery established through #331 → #333 and #347/#349 required two bounded bootstrap continuations before this semantic review could be reached: PR #354 aligned the positive materialization postcondition observer with the deterministic replacement carrier already created by apply-side ownership, and PR #355 reused the existing safe two-parent reconciliation/carrier path when that accepted replacement became stale after a disjoint default-branch advance. Both are historical merged prerequisites and introduce no #322-specific recovery state. PR #357 subsequently consolidated every positive materialization consumer under the single proof at current N-1 `1ca1d8e37e42bf1b689826ec34a0e335ba1f68b4`. Continue ordinary verification, remaining idle implementation, and later lifecycle/production stages from this merged prerequisite; retain the full parent completion outcome.

## Decision 1: Keep normal dispatch Action-only

Do not add an Action, label, Role, transition, queue, or selector branch for idle. The normal dispatcher continues to select only existing canonical routed work. Its exact `NO_WORK` artifact is the only handoff signal that can start the bounded idle semantic mode.

The bootstrap consumes only a completed successful bridge run whose artifact, request comment, run identity, and checked-out default-branch revision agree. `AUTHORIZE` and `FAIL_CLOSED` terminate the idle path without invoking Lead idle semantics.

## Decision 2: Use a typed non-Action idle envelope

The bootstrap-to-Lead boundary receives an immutable envelope containing:

- repository and default branch;
- exact dispatch request-comment id;
- exact bridge run id and `dispatch-result.json` artifact identity/digest;
- the observed default-branch revision;
- the machine disposition, which must be `NO_WORK`;
- a fresh invocation/correlation id and source evidence reference.

The envelope is transport evidence for one wake, not workflow state. It is not written to the daily control shard as an accepted intent and is not used to reconstruct an Action. The idle result is typed as no-finding, advisory-only, or one candidate recommendation. It includes the exact source revision/evidence, but it does not itself authorize a GitHub mutation.

Lead's semantic execution remains bounded by the existing canonical idle requirement: no formal/pre-activation/orphan work should be advanced first, at most one advisory or one Formal Explore candidate may be proposed, and no exhaustive scan state is retained.

## Decision 3: Make admission a fresh application-owned boundary

For a candidate result, the bootstrap submits one explicit idle application request through the existing repository application carrier, using a distinct non-Action request marker rather than pretending that idle is `propose-change` or another normal Action. The request carries:

- the exact `NO_WORK` envelope;
- the Lead result and source evidence;
- either one existing candidate Issue id, one new Formal Explore descriptor, or one bounded advisory descriptor;
- a deterministic admission correlation derived from the exact wake and candidate evidence.

The application rejects malformed, stale, contradictory, or replayed requests before mutation. Immediately before any write it fresh-reads the default branch and reconstructs normal dispatch. Only exact current `NO_WORK` permits the write. An advisory descriptor is limited to one through three recommendations, carries exactly `advisory:idle`, carries no `Change:` line or `action:*`/`agent:*` label, and is never a normal workflow candidate.

Existing-candidate admission uses one GitHub Issue update whose body and full label set are derived from the fresh observed object, preserving all unrelated fields while leaving exactly `Change: unset` and one `action:explore-change`. New-candidate admission uses one Issue creation with the canonical body, reconstructable source evidence, and exactly one `action:explore-change` label. The application then fresh-reads the target and reports success only after the complete tuple is visible.

Advisory admission uses one Issue creation with the bounded recommendation body, exact source markers, and only `advisory:idle`. It reports success only after the open Issue, exact body, and exact label set are visible. An existing open `advisory:idle` Issue suppresses another advisory, even when its recommendation is unrelated; a correlated Issue in any state must first be proven uniquely complete or the request fails closed.

The final write boundary may be protected by a workflow concurrency group with cancellation disabled. This serializes only concurrent idle admission attempts; it is not a durable lock, lease, heartbeat, cursor, or workflow state. Every serialized attempt redoes the normal `NO_WORK` precondition.

## Decision 4: Reconcile interruptions and ambiguous writes from GitHub truth

Before the write, interruption leaves no admission state. After a successful write, the canonical Issue routing is the durable owner and a later normal wake can select it. If the response is lost, the application performs read-only reconciliation:

- existing target: verify the exact Issue id and complete tuple;
- new Formal Explore or advisory target: enumerate **all Issue states** (not only current open Issues) for exactly one immutable admission correlation/source-evidence marker and the complete tuple;
- one match: continue from the observed consequence;
- zero matches: treat the consequence as unproven and fail closed rather than blind-create (for advisory creation, a different open `advisory:idle` Issue also suppresses a new advisory);
- multiple matches or contradictory state: fail closed.

For a correlated advisory, a single complete open Issue is `ALREADY_ADMITTED`; a closed, malformed, or otherwise incomplete correlated Issue is not replaceable and returns `AMBIGUOUS`. This all-state rule protects both Formal Explore and advisory admissions from replay after an interrupted or unknown write.

A later retry must never replay Lead semantic discovery merely to recreate an application record. If current normal dispatch already returns `AUTHORIZE`, the idle request is stale and performs no mutation.

## Decision 5: Preserve the normal handoff

Once a complete candidate tuple is observed, idle ownership ends. The next normal Scheduled Task wake fresh-dispatches and authorizes ordinary `Lead / explore-change`. The idle path never executes that Action in the same wake and never stores a successor/cursor.

## Decision 6: Derive unanswered-Human waiting without adding workflow state

When the current qualified frontier is an unanswered `HUMAN_DECISION_REQUIRED` whose repository-derived successor is the same `Lead / resolve-question`, a later Scheduled Task wake must not repeat the same semantic Action merely because it is a new transport request. Before semantic ingress, the bootstrap/runtime derives the current frontier from existing formal result, routing, Human provenance, and relevant repository evidence. If there is no newer qualifying Human decision and no material evidence change, the wake is a repository-silent derived wait/no-op: it emits no new `EFFECT_REQUEST`, formal result, routing write, retry counter, lease, cursor, mailbox, or persisted waiting state.

A newer qualifying Human decision or materially changed authoritative evidence invalidates that derived wait and restores ordinary fresh dispatch plus semantic execution. This rule is deliberately narrower than a generic “same BLOCKED fingerprint” cache: unrelated BLOCKED results remain normal Action outcomes and evidence freshness is never hidden by suppression.

## Repository implementation of the boundary

### Qualified carrier consumption and execution evidence

Source: Human refinement 5986774520 and independent findings 5987083136; trace to the modified `Application consequence completion is reconstructable across interruption` requirement. Fresh synchronous F3 request 5986891888, continuation 5986915159, application run 37254331790, artifact 11321399885/plan `carrier-plan-300473adfaa9ca73445581e53d026f9c81642fed9293e69d831afcf0effa3636`, exact non-force connector write, and attempt 2 validation establish one manual carrier/postcondition/handoff. They demonstrate the missing consumer boundary; they do not prove native scheduled execution or authorize reuse of that historical plan.

Remove unconditional producer rerun when a valid saved plan exists. Reuse application-completion discovery to resolve one current accepted owner, its exact request-bound application run/attempt, and the unique relevant carrier artifact. Qualify artifact expiry/digest/content and deterministic CarrierPlan identity against accepted intent, plan operation and full current repository preconditions. Reuse the canonical proof to separate COMPLETE, genuinely missing physical effect, necessary plan absence, and contradictory/unknown evidence. Do not infer plan absence from a failed API read. Reuse current disjoint-advance and target/witness/preimage semantics; reject conflicting evolution. Historical artifacts with the same identical content-addressed plan can be deduplicated only after complete source/lineage qualification; differing current plans or ambiguous cardinality fail closed. Dispatch's existing run-scoped result may carry the minimal qualified carrier descriptor alongside the existing continuation transport; it remains FAIL_CLOSED/non-semantic handoff, never AUTHORIZE for a successor or NO_WORK.

The thin bootstrap obtains that exact repository output, fresh-reads current governance and the qualified plan, and invokes only the specified configured connector operation after a final current-state guard. It records actual tool/operation and target/preimage identity. API acknowledgement is discarded as completion authority: the application-completion/materialization owner fresh-proves the resulting repository state. Already-complete effects skip mutation. CarrierRequired still exits its producing invocation; physical execution and application completion occur in subsequent fresh boundaries. Reuse exact APPLICATION_CONTINUATION for missing validation/consequence, with no semantic resubmission. A producer is resumed only when its existing owner proves reconstruction is necessary.

Extend the existing continuation/evidence staging boundary minimally to carry bounded external outcome evidence, using strict parsing, source/request/run/attempt/artifact/plan correlation and deduplication. This is the unavoidable minimal ADD within existing owners: current durable exception policy lacks a qualified actuator-to-application producer/parser/consumer. It is not another event bus or workflow. The repository consumer fresh-qualifies and preserves immutable accepted intent and writes existing canonical exception evidence when applicable. Normal CarrierRequired remains distinguishable from actual refusal/error and unknown response. Capture raw observable platform-redacted errors separately from classification; record COMPLETE/NOT_COMPLETE/UNKNOWN mutation evidence and precise unfinished boundary as observations, not new lifecycle statuses. An external report has no routing/terminal authority; canonical proof and formal consequence retain those responsibilities.

On lost response, perform read-only target reconciliation before any new write. On reporting failure, preserve actual platform/run output and explicitly state repository persistence is unproven wherever a legal evidence path remains. Later recovery must use durable GitHub truth, never invented comments or conversation-held completion. Evidence refusal does not permit bypassing safety, changing transport to repeat a denied operation, or creating replacement carriers. Existing exception disposition and unchanged-failure rules apply. Three is the maximum substantive attempts for one unresolved causal recovery episode, derived across the accepted intent and qualified exception/effect evidence rather than a new counter; a new nonce, date, run, or replacement plan does not reset it. An unchanged refusal is not retried. A hard kill before evidence capture is reconstructed without fabricating a raw error.

No additional Role, Action, ResultKind, state machine, queue, cursor, lease, retry registry, or progress store is retained. Bootstrap instructions move to current repository-owned guidance rather than duplicated Scheduled Task prompt semantics. Existing Skill responsibilities are reused; shared handoff guidance is consolidated, with conditional skill-maintenance composition if a material Skill file must change.

`scheduled_agent_idle_admission.py` is the repository-owned implementation of the typed boundary.
Its envelope binds the request comment, successful bridge run, unexpired `dispatch-result.json`
artifact id/digest, parsed artifact content, checked-out default-branch revision, and the exact
`NO_WORK / no-routed-work` disposition. The admission request binds one bounded Lead candidate to
that envelope with a content-addressed correlation; no request registry or retry record is persisted.

The existing application workflow accepts the request through one typed `IDLE_ADMISSION_REQUEST`
Issue-comment RPC on the current daily runtime shard. The comment is only a connector trigger and
staging carrier; it is not an accepted intent, mailbox, or repository-owned state record. A
no-finding result remains silent and creates no comment. Its idle job has a repository concurrency
group with cancellation disabled. The job rechecks the exact request body, current runtime shard,
default branch ref, and normal dispatch immediately before each possible write. Existing targets
use one full Issue update derived from the fresh object; new targets use one Issue create with the
correlation/source evidence in the body. Both paths fresh-observe the complete tuple, including the
full candidate body and preserved existing body and labels. Correlation reconciliation enumerates
all Issue states (not just open Issues), so a closed or contradictory prior result remains fail-closed. Advisory requests use the same boundary but create only a non-routing Issue with exactly `advisory:idle`, at most three recommendations, and no `Change:` line; any open advisory suppresses duplicate advisory noise.
A lost or ambiguous response is reconciled read-only by exact Issue identity/correlation and never
blindly replayed. The same daily-shard comment boundary carries an
`APPLICATION_CONTINUATION` transport after an accepted application reaches GitHub's exhausted
run-attempt boundary; that body is content-addressed to the immutable accepted decision and the
application re-reads the decision before applying any effect.

The external bootstrap must obtain the envelope from the successful bridge run, execute bounded Lead
idle semantics, and post exactly one typed `IDLE_ADMISSION_REQUEST` body through the configured
GitHub connector only when a candidate exists. It must also relay an exact
`APPLICATION_CONTINUATION` body emitted by the dispatch artifact when an accepted application needs
a fresh transport boundary; it must not create a new semantic request. Repository access alone does not prove external Task activation. Available native automation inspection/update/run-now capabilities can manage its bootstrap setting; activation remains an explicit production handoff requiring observable native execution and durable GitHub effects, not configuration or request acknowledgement alone.

## Production activation boundary

The repository implementation can make the contract executable and expose the exact carrier, but true production `NO_WORK` acceptance is only observable after #322 has completed its governed merge/archive lifecycle and no routed formal work remains to outrank idle. The external Scheduled Task configuration must then consume exact `NO_WORK`, invoke bounded Lead idle semantics, and post the typed idle request to the current runtime shard only when a candidate exists. It must relay an emitted application continuation body exactly once per fresh boundary without inventing a new semantic request. Production proof must include the real post-terminal wake/run/artifact identity, a no-finding run with zero repository mutation or one safe advisory/Explore admission, and for Formal Explore admission a later ordinary dispatch that consumes the canonical Issue.

If that external configuration is not exposed to the available capability, repository implementation and tests remain valid delivery work but production activation is not proven. The final lifecycle must report that exact blocker rather than calling a merged repository implementation complete.

## Shared materialization and consequence recovery

The idle path depends on the same shared application substrate used by normal Actions. It MUST NOT acquire a #322-specific recovery path, and Git topology MUST NOT define separate positive completion states.

### Single durable-consequence proof owner

For one accepted materialization intent `I` and fresh repository state `S`, one canonical read-only proof owner answers only:

```text
COMPLETE(target, witness)
INCOMPLETE
CONTRADICTORY(reason)
```

`target` (`T`) is the exact currently qualified carrier/consumer revision for the requested evidence target, including any review or validation that consumes it. `witness` (`W`) is immutable Git evidence that the exact accepted desired content was legally produced. The same proof may therefore return `COMPLETE(T, W)` with `T != W`: a legal same-Change descendant can become the current target and change accepted paths while the ancestor witness still proves the older accepted consequence. Content is proved at `W`; exact-head review/validation remains bound to `T`. Identity, complete lineage from `W` to the qualified current target, and Non-conflict must still hold. Neither `T == W` nor equality with an invocation-local apply target defines durable completion; local target memory supplies no independent authority.

The accepted authorization revision `A` is the immutable revision under which the intent was accepted. The declared carrier base `B` is the accepted carrier's declared graph anchor. The actual prospective mutation parent/preimage `P` is the tree that a missing write would extend (parent zero for an existing-carrier correction or reconciliation). The fresh default-branch revision `D` supplies current governance and authorization. These are separate identities and need not be equal. Fresh authorization against `D` and graph/non-conflict qualification of `A`, `B`, and `P` are mandatory; equality is not a substitute for those checks. Before a missing mutation, every `expected_sha` MUST match its requested path in the actual prospective parent `P`, not merely in `A`, `B`, or `D`. A reconciliation may use parents `[P, D]` with a declared base `B` different from `P`; the accepted path preimages still guard `P`, while complete compare/overlap evidence protects both lineages and unrelated content. After a qualified durable witness exists, an obsolete preimage need not remain current.

`COMPLETE` requires all four proof dimensions:

1. **Identity** — exact repository, Issue, immutable Change, source Role/Action, intended PR/ref/branch, and unique carrier/cardinality.
2. **Content** — every accepted desired blob/content identity is present in the qualified witness. A mutation preimage such as `expected_sha` is a stale-write guard, not durable completion evidence after the accepted desired consequence exists.
3. **Lineage** — Complete Git graph evidence qualifies the separate accepted authorization revision `A`, declared carrier base `B`, actual mutation parent `P`, fresh default branch `D`, immutable witness `W`, and current target `T`, including PR base/head/merge and application-built reconciliation ancestry. It does not collapse those identities or require accepted bytes to remain at a legal later target.
4. **Non-conflict** — no duplicate/ambiguous carrier, wrong PR/ref/blob, requested-path overlap, broken or incomplete ancestry/compare evidence, unrelated overwritten content, or contradictory observation.

Existing exact-manifest checks, historical ancestry validation, merged-witness lookup, reconciliation recognition, replacement qualification, and similar helpers remain reusable proof primitives or witness finders. They MUST NOT independently return a competing top-level positive completion meaning.

### Consumers and mutation protocol

The apply-side already-complete pre-check, materialization observer/postcondition, fresh interruption recovery, and higher consequence-completion classifier MUST consume the same canonical proof. The postcondition is a thin consumer; it does not define a second success predicate. A fresh process reconstructs proof from GitHub truth and does not require invocation-local `_materialization_targets`.

The mutation protocol is:

```text
fresh observe
→ canonical proof
   COMPLETE       → zero materialization mutation; return current target T and durable witness W
   CONTRADICTORY  → fail closed
   INCOMPLETE     → plan only the narrow missing mutation
→ consequential mutation
→ discard local success as authority
→ fresh observe
→ the same canonical proof
```

API success, commit/ref/PR creation, carrier return, validation, or merge response never independently establishes workflow completion.

### Historical topology is characterization, not semantics

The existing ancestor-carrier, disjoint-main-advance, historical PR-base, reconciled carrier, merged carrier, merged carrier plus same-Change successor, deterministic replacement, replacement plus main advance, reconciliation, and reconciliation plus later one-parent correction cases are retained as characterization/witness shapes. PR #357 originally supplied a valid RED for the last class. Its final reviewed repair replaced the temporary `direct_carrier_postcondition`-style positive branch with the canonical proof and merged at `1ca1d8e37e42bf1b689826ec34a0e335ba1f68b4`; historical topology remains characterization rather than a permanent completion authority.

Accepted first-carrier branch→PR recovery and accepted-application continuation remain bounded missing-effect mechanisms. They may plan only a genuinely `INCOMPLETE` consequence after the canonical proof and existing fresh authorization/cardinality/overlap checks. They MUST NOT replay semantic work, recreate an already-proven carrier, force-move a ref, or create a competing recovery lifecycle.

### Accepted-application rejection recovery

The 2026-10-07 #322 continuation record contains only a generic `effect precondition rejected` result and no CarrierPlan. The historical effect-level guard cannot be recovered from that log. Current source independently reproduces a precise same-path default-advance rejection. The correction therefore addresses both evidence loss and recovery liveness without weakening that guard.

Keep separate identities for immutable accepted intent `I`, the accepted materialization/effect plan `P`, an optional externally executable CarrierPlan `C` (which may not yet exist), and each actual execution attempt `R`. Before a rejected effect is collapsed into a batch result, preserve the exact effect identity/ordinal, operation and target, expected and observed preimage, guard reason, canonical completion proof, effects already proven complete, mutation status (complete/not-complete/unknown), and unfinished boundary. Bind this evidence to the accepted-decision digest and exact request/run/attempt/artifact and any plan ids that actually exist; explicitly record absent evidence instead of guessing. Exclude credentials and do not infer a raw error that the platform did not expose. A generic refusal without this evidence is not enough to authorize another write.

Recovery stays with the existing accepted-intent, application-completion, exception-evidence, and `APPLICATION_CONTINUATION` owners. Reconcile unknown writes read-only before any further operation. A currently proven-complete consequence performs no duplicate mutation. A valid fresh plan may complete only its exact non-force operation after the existing authorization and preimage checks. An expired or stale `P` or existing `C` may be recorded as `PLAN_SUPERSEDED` only after its invalidation and already-completed effects are proven; that disposition ends the old plan's execution authority but does not change `I`. A replacement `P` or `C` is legal only when fresh current authorization and the canonical proof show the immutable requested content can be applied with exact current preimages, complete lineage, and no conflicting path evolution. If an accepted path overlaps a changed default-branch path and the exact accepted intent cannot be proven already complete or safely projected, return the precise conflict to the normal governed correction path. Never overwrite, force-update, rerun semantic discovery, or silently reinterpret the accepted intent.

A `run_attempt > 1` value is GitHub-owned evidence, not a permanent recovery ban or an independent recovery attempt. Never rerun the same completed run/job. A new attempt requires the existing typed continuation to create a fresh run bound to the same accepted intent, exact failure evidence, current routing, and fresh authorization. One stable unresolved causal failure episode is keyed by immutable accepted-intent identity and normalized failing operation/guard/path, not by run id, plan id, nonce, or date. Count only substantive fresh recovery attempts, across every wake, run, continuation, and replacement plan; stop at three. Do not retry an unchanged denial. Missing/ambiguous evidence, a reporting failure, or attempt exhaustion yields an explicit fail-closed blocker with its exact reopening condition. Only qualified causal repair or the existing authorized correction may reopen evaluation; a new transport correlation alone may not.

### Staged cutover and systemic properties

The bounded Human-authorized bootstrap consolidated this prerequisite in PR #357 at `1ca1d8e37e42bf1b689826ec34a0e335ba1f68b4`. Exact-head independent review `5405763214`, Python Quality (891 tests, Ruff/format, mypy), and strict OpenSpec validation bound candidate `63df1af3928e2c41f0ef69dcd3cc3623f4221544`. Production continuation run `37199451772` then reused the existing PR #353 head with zero materialization replay and validated exact revision `ae9eba694cf56e510051b7a85f0eae531d528829`. This establishes the current prerequisite N-1, not completion of the parent Change. Ordinary Executor delivery must verify the merged proof against this clarified contract and retain advisory admission, derived Human wait, final review/lifecycle, and post-terminal production acceptance.

The consolidation's atomic and recoverable sequence is:

1. **Characterization:** freeze historical positive shapes and conflict negatives without changing production behavior.
2. **Read-only proof:** introduce the canonical proof owner in shadow and compare its result with current consumers.
3. **Observer/postcondition cutover:** materialization observation, postcondition, fresh recovery, and consequence classification consume the proof.
4. **Apply-side cutover:** already-complete logic consumes the same proof, eliminating apply/observe semantic divergence.
5. **Property verification:** prove apply→fresh-observe consistency, interruption invariance across every durable mutation boundary, safe-evolution monotonicity across legal disjoint advance/reconciliation/merge/same-Change descendant, and conflict preservation.
6. **Cleanup:** only after all consumers are cut over, delete superseded topology-specific top-level positive decision branches while retaining necessary proof primitives.

The accepted-application continuation remains subject to exact Issue/Change/Role/Action identity, unique accepted decision and run/job, current authorization, and complete qualified evidence. `run_attempt > 1` alone neither blocks a safe fresh continuation nor authorizes rerunning the same run/job. Recovery uses the existing continuation owner and derives its three-attempt ceiling from durable exception/effect evidence; it adds no retry state.

## Blast radius and non-goals

No Action model, `agent:*` routing dimension, idle label, idle transition, queue, cursor, lease, heartbeat, hidden backlog, registry, or generic model-selected repository target is introduced. No semantic discovery is added to `select_work()`. Existing application formal result/correlation logic remains the owner for normal Actions; idle admission uses a separate typed boundary because an Action-specific completion record would incorrectly turn idle into workflow state.

## Validation strategy

Carrier closure uses real current-source RED tests before GREEN, with the actual external-consumer seam invoking a connector adapter and observing repository state through the canonical owner. The adapter must cause the write; tests that directly premark fake GitHub completion remain post-write recovery characterization only. Cover complete-vs-missing-plan-vs-pending-effect selection; every source/run/attempt/artifact/digest/plan mismatch; stale/expired/duplicate/superseded plans; overlap, identity/cardinality/content/lineage conflicts; exact per-effect rejection and expected/observed preimage; three-attempt exhaustion across changed run/plan/nonce; explicit rejection, actual error, lost response, and reporting denial. Inject interruptions before write, after server write before response, before evidence persistence, and before/after continuation/validation. Verify zero duplicate mutation, rewind, semantic replay, approval manufacture, and evidence authority leakage.

First execute synchronously to observe the concrete stopped boundary, then validate the saved native Task without this conversation acting as its carrier. Record native versus manual origin separately and link exact request -> run/attempt -> artifact/log -> fresh repository postcondition, including plan, dispatch/application revisions, operation, canonical target/witness, validation checkout head, and formal handoff. A run-now acknowledgement is only requested execution; Task last-run metadata, green workflows, and missing comments do not prove completion or non-execution. If raw native output or another link cannot be observed, mark it unknown and report the exact capability limit. Real native carrier acceptance is required before parent completion, and post-terminal exact NO_WORK acceptance retains its later lifecycle boundary. Do not create an OpenAI API/model worker/new orchestrator or manufacture NO_WORK while routed work exists.

The implementation must provide executable coverage for:

- `AUTHORIZE` and `FAIL_CLOSED` suppression;
- exact `NO_WORK` idle execution and no-finding no-op;
- advisory/non-routing and existing/new candidate formation with unrelated-field preservation;
- overlap first-valid-write-wins;
- stale revision/source refusal;
- interruption before/after mutation;
- canonical-proof characterization for ancestor carrier, disjoint default-branch advance, historical PR base, reconciled carrier, merged carrier, merged carrier plus same-Change successor, deterministic replacement, replacement plus main advance, reconciliation, and reconciliation plus later one-parent correction;
- apply→fresh-observe consistency for every legally produced materialized consequence;
- interruption invariance across accepted decision, blob/tree/commit, branch/ref, PR carrier, CarrierRequired exit, validation, formal result, merge, and successor routing boundaries;
- safe-evolution monotonicity across disjoint main advance, legal reconciliation, legal merge, and legal same-Change descendants;
- conflict preservation for wrong blob/PR/ref, duplicate or ambiguous carrier, requested-path overlap, broken ancestry, incomplete compare evidence, and contradictory repository evidence;
- each first-carrier durable prefix, including accepted intent, content commit, branch ref, PR carrier, returned carrier, validation, formal result, routing, and terminal state;
- a disjoint default-branch advance before PR-carrier recovery, plus overlap, non-ancestor, wrong/duplicate PR, changed identity, and incomplete-observation negatives;
- a new process with empty adapter-local target maps reconstructing the same current materialization/implementation consequence;
- ambiguous create/update reconciliation;
- later normal `AUTHORIZE` after successful admission;
- static negative invariants proving no idle Action, transition, queue, cursor, lease, heartbeat, registry, or selector discovery branch;
- repository workflow and production-shaped carrier evidence;
- unchanged unanswered-Human frontier suppression before semantic ingress, plus resumption when qualifying Human/material evidence changes;
- post-terminal true-`NO_WORK` production acceptance without a dispatcher exception or synthetic idle-validation state.

## Implementation note

The exact module/file decomposition remains subject to implementation review and current default-branch conventions. The non-negotiable ownership boundaries and evidence properties above are normative.
