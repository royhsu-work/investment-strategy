## Why

#138 remains the parent Change simplify-scheduled-agent-control-plane, and PR #178 remains the single implementation/review vehicle. Fresh current state at main@e8c3dc7b256bc167217e25a397e98181bdf6f123 shows that the existing PR artifacts still describe the superseded routing-label, continuation, and cross-role journal design. Human architecture direction issuecomment-5528834334 is newer material meaning and explicitly resets the design from first principles while preserving the Change, Issue, PR, evidence, and safety invariants.

The current structure is not an isolated execution edge case. It makes the repository depend on several overlapping control facts: role labels, action labels, prose topology, worker-selected continuation, cross-role handoff records, permanent response history, and phase inference. That duplication is the structural problem #138 must remove. A correction that only adds another bridge or recovery phase would preserve the same failure shape.

## What Changes

### Canonical current state

After cutover, normal workflow state is only:

- Issue open/closed lifecycle;
- immutable Change: <id> once formal work is activated; and
- exactly one action:<action> for an open routed Issue.

Role is derived as role_for(action). Semantic results, review findings and PASS evidence, Human decisions, exact-revision evidence, and transport/run records remain durable evidence; they are not additional routing dimensions. Normal agent:* labels are migration/source-retirement residue and are not selected as target-state ownership.

### One small executable workflow model

A single default-branch executable surface owns the machine-decidable model:

- ACTION_ROLE;
- TRANSITIONS;
- role_for(action);
- next_action(current_action, typed_result); and
- select_work(authoritative_observations).

It also owns the exact deterministic guards for WIP=1, finish-first ordering, stale/concurrency rejection, effect authorization, carrier eligibility, and postcondition acceptance. agents/workflow.md remains Human-readable governance and may be generated from or mechanically verified against that surface; runtime does not parse Markdown prose as a competing topology. No generic workflow kernel, orchestration framework, retry/lock/lease engine, second DAG, or compatibility hot path is required.

### One Action per Scheduled Task wake

Each wake performs one fresh machine dispatch, derives the mapped Role and Skill, executes exactly one Action, returns a bounded typed result plus semantic evidence, and lets repository application fresh-reauthorize and apply only the necessary exact effects. Application then observes postconditions, derives the unique successor from the current Action and typed result, persists that successor or terminal state, and exits. A successor is executed only by a later fresh wake, even when it maps to the same Role. A worker never chooses an arbitrary successor and no separate normal HANDOFF, completion phase, same-role continuation, cross-role barrier, or recovery Action is required.

### Bounded transport and application boundaries

The retained daily Asia/Taipei control surface is a bounded trigger-and-audit shard, not workflow state or a response mailbox. Every request is correlated to exactly one Actions run and its structured result; latest-comment, title, timing, ordering, or permanent Issue history cannot authorize work. Today is established before an older shard is retired, and an in-flight request/run/result chain remains valid during rollover.

Content-addressed OpenSpec ingress, exact-revision validation, repository-owned mutation planning, and mutation-carrier separation remain independent capabilities. A semantic worker may provide only unreferenced Git blobs plus an exact path/blob/current-SHA manifest. Repository application owns tree/commit/ref construction and fresh postconditions. Exact-R validation proves target revision, validator checkout HEAD == R, qualified pinned compatibility, and strict PASS. A carrier executes only an already-authorized plan and cannot select work, targets, successors, retries, or success.

### Review, merge, safety, and deletion

Independent Reviewer gates remain required. Implementation and Archive merge positions become explicit Actions (merge-implementation-pr and merge-archive-pr) so phase is not inferred from a generic merge Action. WIP=1, finish-first, Human authority, semantic role separation, completeness/provenance, stale/replay/no-rewind/fail-closed behavior, exact-head review and merge gates, and deterministic archive safety remain required.

The delivery resets to the smallest safe N-1 shape: Shadow the executable model, Cut over the bounded transport/application and Action-only routing, then Delete superseded agent:* routing, normal cross-role journal/continuation/recovery machinery, response-mailbox coupling, Markdown runtime parsing, generic merge-phase inference, and obsolete compatibility/model-host paths. Historical evidence remains evidence and is not a live control path.

## Capabilities

### Modified Capabilities

- scheduled-agent-workflow: replace role/action tuple routing and continuation protocols with Action-only state, derived Role, one Action per wake, a small executable transition model, bounded run-scoped transport, fresh application, explicit merge Actions, and safe deletion.
- repository-governance: make the executable Action model the sole machine-decidable workflow authority while keeping Human-readable governance, semantic Skills, effect/carrier separation, and OpenSpec authority distinct.

## Traceability and current evidence

This correction is based on:

- Human architecture reset issuecomment-5528834334;
- current #138 ACTION_RESULT/routing transition issuecomment-5529009343;
- the fresh Lead / resolve-question dispatch decision issuecomment-5529083195;
- current default-branch governance at main@e8c3dc7b256bc167217e25a397e98181bdf6f123;
- current PR #178 head 5592ee855406c065c54c137832a85f532f617898;
- openspec/config.yaml with schema: spec-driven; and
- the independent safety evidence retained by the existing Change history.

This is a material semantic correction. Lead is authoring the existing Change artifacts; independent Reviewer / review-openspec must review the resulting exact revision before implementation resumes. No duplicate Change or PR is created.

## Impact

The affected review artifacts are this Change's Proposal, delta Specs, Design, and Tasks. The implementation plan is intentionally reset around Shadow/Cutover/Delete. The resulting implementation must reduce canonical state dimensions and independent executable decision paths on the default branch.

Refs #138
