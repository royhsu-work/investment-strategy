## Why

#138 remains the parent Change simplify-scheduled-agent-control-plane, and PR #178 remains the single implementation/review vehicle. Fresh authoring state at main@e8c3dc7b256bc167217e25a397e98181bdf6f123 and pre-correction PR #178 head 5592ee855406c065c54c137832a85f532f617898 showed that the existing PR artifacts still described the superseded routing-label, continuation, and cross-role journal design. Human architecture direction issuecomment-5528834334 is newer material meaning and explicitly resets the design from first principles while preserving the Change, Issue, PR, evidence, and safety invariants.

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

## Skill maintenance traceability

This Change materially affects existing repository Skills because the cutover removes or replaces normal HANDOFF, same-role/cross-role continuation, cross-role barriers, generic merge-phase inference, and related procedure paths. The following inventory is part of the Apply context; it does not move shared workflow authority into Skills.

| Skill | Classification | Source/reference | Responsibility treatment | Rationale | Replacement/supersession |
| --- | --- | --- | --- | --- | --- |
| `agents/skills/openspec-change/SKILL.md` | Modified | Human reset `issuecomment-5528834334`; corrected scheduled-agent-workflow delta | Retain Lead semantic OpenSpec authoring, content-addressed ingress, and exact-R readiness; remove worker-authored HANDOFF, same-wake continuation, and worker successor choice | Preserve semantic authoring while removing duplicated control state | The executable Action model and application derive the successor; the next wake redispatches it |
| `agents/skills/openspec-explore/SKILL.md` | Modified | Human reset `issuecomment-5528834334`; one-Action wake requirement | Retain semantic Explore/proposal judgment and Human-boundary handling; remove same-role continuation and normal HANDOFF dependence | Explore remains semantic, but ownership is the persisted Action | Typed result plus application postconditions replace continuation/journal semantics |
| `agents/skills/openspec-review/SKILL.md` | Modified | Human reset `issuecomment-5528834334`; independent-gate and cutover requirements | Retain independent B/R, traceability, Human-freshness, and exact-R review; replace HANDOFF routing with Action-derived successor handling | Review independence and safety remain required | `review-openspec` result routes through the executable model; later wake loads the mapped Skill |
| `agents/skills/implementation/SKILL.md` | Modified | Human reset `issuecomment-5528834334`; one-Action wake and exact-ingress requirements | Retain semantic implementation slices, exact validation, and content ingress; remove same-wake continuation, barriers, and HANDOFF completion | Keep implementation safety while deleting wake orchestration | Typed result/application effects persist one successor and exit |
| `agents/skills/implementation-review/SKILL.md` | Modified | Human reset `issuecomment-5528834334`; independent implementation-gate requirement | Retain exact-head implementation review and finding classification; remove normal HANDOFF ownership-transfer dependence | The review gate is independent; transfer journaling is not canonical state | Result-derived Action transition plus a later fresh dispatch |
| `agents/skills/archive-review/SKILL.md` | Modified | Human reset `issuecomment-5528834334`; explicit archive-merge requirement | Retain archive correctness and exact-head review; remove normal HANDOFF dependence | Archive safety remains an independent gate | The explicit archive merge Action is derived by the executable model |
| `agents/skills/lifecycle-finalize/SKILL.md` | Modified | Human reset `issuecomment-5528834334`; Action-only lifecycle and deletion requirements | Retain Lead lifecycle/archive authority; remove same-wake continuation, transfer journals, and generic phase inference | Lifecycle authority is semantic and must not be recreated as a second machine state | Persist the derived Action/terminal state and let a later wake redispatch |
| `agents/skills/merge-pr/SKILL.md` | Modified | Human reset `issuecomment-5528834334`; explicit `merge-implementation-pr` / `merge-archive-pr` requirements | Retain only reusable exact-head merge mechanics; remove generic `merge-pr` phase inference and HANDOFF machinery | Merge safety is retained, while hidden lifecycle phase is removed | Explicit merge Actions own eligibility and successor meaning; the generic mapped phase is superseded or split during cutover |

The repository `skill-creator` composition and `openspec-semantic-adapter.md` remain reusable inputs without a material responsibility change. Role documents, templates, and runtime modules are separate governance/application surfaces and will be updated by the implementation tasks where the cutover requires it.

## Traceability and current evidence

This correction is based on:

- Human architecture reset issuecomment-5528834334;
- prior architecture-reset blocker issuecomment-5529009343 and prior Lead dispatch decision issuecomment-5529083195, both retained as historical pre-correction evidence;
- prior-cycle Lead correction dispatch decision issuecomment-5529654634, retained as historical pre-correction evidence;
- current default-branch governance at main@e8c3dc7b256bc167217e25a397e98181bdf6f123;
- prior semantic targets 9a9f131a03e5b22df3a43258fa6cc14cb3bd22cd and 872c7e988beb4bd684eeee6916bcc950509e7bb4, both historical pre-correction targets; the resulting exact target for this correction is the revision R emitted by the current Lead ACTION_RESULT and fresh PR/ref observation;
- openspec/config.yaml with schema: spec-driven;
- the independent safety evidence retained by the existing Change history;
- prior Lead readiness result issuecomment-5529602299 and prior exact validation run 33785030285, job 100747605621, correlation validation-resource-request-5529577659, all retained as historical pre-correction evidence;
- prior Reviewer finding issuecomment-5529497150 and prior-cycle Reviewer finding issuecomment-5529644414, retained as historical correction-chain evidence; and
- current F3 finding issuecomment-5529815334 and current Lead dispatch decision issuecomment-5529842334 bind this correction. The exact-R validation resource for resulting revision R is bound by the current Lead ACTION_RESULT and is not replaced by any prior-cycle validation record.

This is a material semantic correction. 

The causal same-Issue Explore result remains `issuecomment-5482546619` (`PROPOSAL_READY`) with supporting architecture evidence `issuecomment-5474475020` and transport evidence `issuecomment-5442745071`. Earlier Human clarifications `issuecomment-5475109024`, `issuecomment-5477274582`, and `issuecomment-5507379401` remain provenance for the bounded history; the newer Human reset `issuecomment-5528834334` is the controlling current semantic direction and supersedes conflicting mechanism choices. Lead is authoring the existing Change artifacts; independent Reviewer / review-openspec must review the resulting exact revision before implementation resumes. No duplicate Change or PR is created.

## Impact

The affected review artifacts are this Change's Proposal, delta Specs, Design, and Tasks. The implementation plan is intentionally reset around Shadow/Cutover/Delete. The resulting implementation must reduce canonical state dimensions and independent executable decision paths on the default branch.

Refs #138
