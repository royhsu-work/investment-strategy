## Context

Fresh current governance remains Scheduled-Dispatch-Mode: workflow-dynamic and currently selects #138 from agent:lead + action:resolve-question. Current main@e8c3dc7b256bc167217e25a397e98181bdf6f123 still carries the older role-label and continuation model, while PR #178 pre-reset head 5592ee855406c065c54c137832a85f532f617898 contained the prior incremental plan. PR #178 input head e522480b00178378876967ab5156c6fdc2671c3a is the pre-correction revision observed for this Lead invocation. It is historical input once this correction is applied; the resulting exact target R is the revision emitted by the current Lead ACTION_RESULT and fresh PR/ref observation, with its exact-R validation resource bound to that same R. Human intent issuecomment-5528834334 explicitly supersedes the prior plan and requires a first-principles reset.

The design therefore separates semantic responsibility, workflow action, and mutation capability. Lead/Reviewer/Executor retain semantic judgment in their mapped Skills. A small repository-owned executable model makes mechanical decisions. Repository application authorizes and observes mutations. External transport and identity-sensitive carriers remain adapters. No layer infers authority from prose, historical ordering, a worker's arbitrary successor, or a successful API call alone.

## Decisions

### 1. Action is the canonical workflow position

Normal current state is:

Issue lifecycle + immutable Change + one Action.

Role = role_for(Action) is a pure derived property. Evidence is durable and reconstructable, but result, review, Human, exact revision, transport, and carrier records do not become additional current routing dimensions. agent:* labels are accepted only as migration/source-retirement input during the transition and are absent from the target normal state.

The executable model contains the finite Action vocabulary, ACTION_ROLE, legal TRANSITIONS, typed result classes, role_for, next_action, and deterministic work selection. It is one machine-decidable source of truth. Human-readable workflow text is generated or mechanically checked from it and is never parsed as a second production topology.

### 2. A wake has one Action boundary

At every Scheduled Task wake:

1. repository-owned transport yields an exact run-scoped dispatch decision from fresh current state;
2. the mapped Role and default-branch Skill are loaded;
3. exactly one Action reconstructs its own evidence and performs its bounded semantic work;
4. the worker returns a typed result/evidence envelope;
5. repository application fresh-reauthorizes the exact source and effects;
6. application performs only necessary narrow mutations, exact validation, and postcondition observations;
7. next_action(current_action, result) derives one successor or terminal state;
8. the successor is persisted; the current invocation exits.

The successor never executes in the same wake, including a same-Role successor. This removes the need for invocation-role comparison, same-role continuation, cross-role barriers, and a separate normal ownership-transfer journal. A transition from implement-change with SPEC_BLOCKER can therefore persist resolve-question and exit; the next wake derives Lead from that Action.

Within one Action, work is bounded by a meaningful verified outcome. The execution shape is Reconstruct -> RED exact gap/blocker -> GREEN legal correction -> VERIFY exact postcondition/revision/gate -> checkpoint. An intermediate file/API/commit/run is not completion. If a slice cannot reach VERIFY in one normal invocation, it is split before execution at a safe outcome boundary.

### 3. Results and application effects are distinct

A semantic worker can state a typed result and evidence, but it cannot choose a successor or directly persist durable workflow state. The result is correlated to the exact dispatch decision and is consumed by repository application.

Application fresh-reads the Issue, Change, PR/head, branch, expected current identities, and relevant Human/review/gate evidence. It derives the legal effect plan and successor from the executable model, applies only the exact necessary effects, and fresh-observes every required postcondition. A stale, replayed, ambiguous, contradictory, or provenance-incomplete request fails closed. Already durable effects are not replayed merely to recreate evidence, and later consumed descendants are never rewound.

Recovery is ordinary idempotent reconciliation of still-required non-contradictory state. It is not another Action, public lifecycle state, transaction framework, retry counter, lock/lease, mailbox protocol, or second DAG.

### 4. Exact revision and work-product boundaries stay independent

When a Lead correction changes OpenSpec artifacts, the semantic worker may create unreferenced Git blobs only. It submits a manifest containing exact branch/base identity, Change-owned paths, each new blob SHA, and each current expected SHA. Application creates the one tree and commit, advances the exact branch without force, and fresh-observes ref, PR head, commit/tree/parent, and file postconditions. Complete file content is not carried through Issue comments.

The resulting revision R is validated by an application-owned exact-R resource. Accepted evidence proves target R, validator checkout HEAD == R, the qualified pinned OpenSpec baseline, and strict validation PASS. Validation eligibility comes from the governed artifact/gate requirement, not a Propose-only or role whitelist; an already-current correct target is validated without a dummy rewrite.

### 5. Bounded daily transport

The daily control surface derived from #168 is a transport shard for the governed Asia/Taipei day. There is at most one usable current-day shard. A request identifies exactly one Actions run, and only that exact run's structured result can be consumed. The shard does not carry Change/Action/Role/WIP, semantic result authority, successor authority, or recovery state.

Rollover establishes and freshly observes today's shard before retiring an older one. Retirement does not invalidate an in-flight request -> exact run -> result chain. Permanent response history, latest, timing proximity, title inference, and mailbox-style result comments are not authorization mechanisms.

### 6. Explicit merge Actions and retained safety

Independent review-implementation and review-archive gates remain separate and exact-revision/exact-head bound. Their PASS results derive merge-implementation-pr and merge-archive-pr respectively. Executor retains exact target, head, linkage, Human-freshness, and unchanged-revision checks; Archive retains lifecycle preparation and cleanup obligations. Merge recovery reuses an exact current PR/head when legal and never infers a phase from a generic merge Action.

Human authority, WIP=1/finish-first, complete and provenance-qualified observations, stale/concurrency fail-closed behavior, exact-head merge safety, content-addressed ingress, and deterministic archive completion remain. Carrier identity is replaceable and executes only a repository-authorized plan; it cannot select work, effects, successors, retries, or success.

### 7. Safe delivery and deletion

The delivery has three semantic boundaries:

- Shadow: introduce the smallest executable Action model and compare its decisions with current production without mutation cutover;
- Cutover: deploy bounded run-scoped transport, structured results, Action-only routing, derived Role, fresh application, exact validation/ingress, carrier separation, one Action per wake, and explicit merge Actions;
- Delete: remove superseded normal role routing, cross-role journal/continuation/recovery machinery, response-mailbox/history coupling, Markdown topology/effect parsing, generic merge inference, and obsolete model-runtime/compatibility paths.

Each boundary must be independently testable, reviewable, and deployable on the then-current N-1. A boundary is split only when required for a verified safe transition. No intermediate boundary is mistaken for #138 completion.

## Acceptance criteria

- Current state can be reconstructed as Issue lifecycle, immutable Change, and one Action, with Role derived.
- One executable model is the only production selector/transition authority.
- A single wake executes one Action, persists only its derived successor/terminal state, and exits before successor execution.
- Worker result/evidence is bounded and cannot choose arbitrary targets or successors.
- Application fresh reauthorization, exact effects, stale/replay/no-rewind guards, and postcondition observation are preserved.
- Exact-R validation and content-addressed ingress pass their independent production tests.
- Daily transport is bounded and exact-run correlated; it is not a lifecycle mailbox.
- Independent review, exact-head merge, Human authority, WIP=1, and archive safety remain intact.
- The cutover measurably reduces canonical state dimensions and executable paths, and deletion removes rather than hides superseded mechanisms.

## Non-goals

This Change does not create a duplicate Change or PR, move semantic authority from Lead/Reviewer/Executor, weaken Human-required decisions, use a model API inside Actions, add a generic workflow framework, or turn transport/audit history into current workflow state.

Refs #138
