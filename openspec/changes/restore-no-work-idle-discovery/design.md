# Design

## Current decision boundary

The current default branch is `2e00e236f24ba41302c9ba18c685acdf4cebe4ed`. Fresh source inspection establishes these owners:

- `workflow_dispatch.py` and the runtime preflight reconstruct current repository work and return `AUTHORIZE`, `NO_WORK`, or `FAIL_CLOSED`.
- `issue_comment_bridge.py` checks the authoritative default branch and publishes one run-scoped dispatch-result artifact.
- `scheduled_agent_application_bridge.py` and its materialization/effect modules own fresh reauthorization, exact repository effects, postconditions, carrier boundaries, and formal successor qualification.
- `.github/workflows/scheduled-agent-bridge.yml` and `.github/workflows/scheduled-agent-application.yml` are repository-owned execution carriers.
- the external Scheduled Task/bootstrap is the product boundary that must interpret the exact dispatch artifact and invoke a semantic Lead run; it is not represented in normal Issue routing.

The current gap is therefore a missing reachability boundary, not a defect in normal selection and not permission to infer work from an empty queue.

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
- either one existing candidate Issue id or one new-candidate descriptor;
- a deterministic admission correlation derived from the exact wake and candidate evidence.

The application rejects malformed, stale, contradictory, or replayed requests before mutation. Immediately before any write it fresh-reads the default branch and reconstructs normal dispatch. Only exact current `NO_WORK` permits the write.

Existing-candidate admission uses one GitHub Issue update whose body and full label set are derived from the fresh observed object, preserving all unrelated fields while leaving exactly `Change: unset` and one `action:explore-change`. New-candidate admission uses one Issue creation with the canonical body, reconstructable source evidence, and exactly one `action:explore-change` label. The application then fresh-reads the target and reports success only after the complete tuple is visible.

The final write boundary may be protected by a workflow concurrency group with cancellation disabled. This serializes only concurrent idle admission attempts; it is not a durable lock, lease, heartbeat, cursor, or workflow state. Every serialized attempt redoes the normal `NO_WORK` precondition.

## Decision 4: Reconcile interruptions and ambiguous writes from GitHub truth

Before the write, interruption leaves no admission state. After a successful write, the canonical Issue routing is the durable owner and a later normal wake can select it. If the response is lost, the application performs read-only reconciliation:

- existing target: verify the exact Issue id and complete tuple;
- new target: search current open Issues for exactly one immutable admission correlation/source-evidence marker and the complete tuple;
- one match: continue from the observed consequence;
- zero matches: treat the consequence as unproven and fail closed rather than blind-create;
- multiple matches or contradictory state: fail closed.

A later retry must never replay Lead semantic discovery merely to recreate an application record. If current normal dispatch already returns `AUTHORIZE`, the idle request is stale and performs no mutation.

## Decision 5: Preserve the normal handoff

Once a complete candidate tuple is observed, idle ownership ends. The next normal Scheduled Task wake fresh-dispatches and authorizes ordinary `Lead / explore-change`. The idle path never executes that Action in the same wake and never stores a successor/cursor.

## Production activation boundary

The repository implementation can make the contract executable and expose the exact carrier, but the external Scheduled Task configuration must be updated to consume `NO_WORK`, invoke Lead idle semantics, and submit the typed idle request when a candidate exists. Production proof must include the real wake/run/artifact identity, a no-finding run with zero repository mutation, and a material finding whose canonical Issue is consumed by the next normal dispatch.

If that external configuration is not exposed to the available capability, repository implementation and tests remain valid delivery work but production activation is not proven. The final lifecycle must report that exact blocker rather than calling a merged repository implementation complete.

## Blast radius and non-goals

No Action model, `agent:*` routing dimension, idle label, idle transition, queue, cursor, lease, heartbeat, hidden backlog, registry, or generic model-selected repository target is introduced. No semantic discovery is added to `select_work()`. Existing application formal result/correlation logic remains the owner for normal Actions; idle admission uses a separate typed boundary because an Action-specific completion record would incorrectly turn idle into workflow state.

## Validation strategy

The implementation must provide executable coverage for:

- `AUTHORIZE` and `FAIL_CLOSED` suppression;
- exact `NO_WORK` idle execution and no-finding no-op;
- existing/new candidate tuple formation and unrelated-field preservation;
- overlap first-valid-write-wins;
- stale revision/source refusal;
- interruption before/after mutation;
- ambiguous create/update reconciliation;
- later normal `AUTHORIZE` after successful admission;
- static negative invariants proving no idle Action, transition, queue, cursor, lease, heartbeat, registry, or selector discovery branch;
- repository workflow and production-shaped carrier evidence.

## Implementation note

The exact module/file decomposition remains subject to implementation review and current default-branch conventions. The non-negotiable ownership boundaries and evidence properties above are normative.
