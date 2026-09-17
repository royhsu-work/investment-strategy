# Design: Restore verified-slice checkpoints for interruption recovery

## Current decision boundary

The current default branch already decides the outcome. The canonical workflow
specification requires task completion at verified vertical-slice boundaries and
requires one bounded `SLICE_CHECKPOINT` before another slice or handoff. Current
governance requires one Action per wake, fresh reconstruction, application-owned
effects, and successor derivation only after durable postconditions. No new
workflow state or checkpoint requirement is needed.

The existing ownership layers are sufficient:

- `openspec/specs/scheduled-agent-workflow/spec.md`: normative checkpoint and
  recovery contract;
- `agents/templates/messages.md`: bounded message presentation;
- `agents/skills/implementation/SKILL.md` and `agents/roles/executor.md`:
  action-local slice procedure;
- `scheduled_agent_action_model.py`: finite Action/Result topology;
- `scheduled_agent_effects.py`: fresh effect reauthorization, effect ordering,
  postconditions, and typed successor persistence;
- `scheduled_agent_application_materialization.py` and
  `scheduled_agent_validation_resource.py`: content-addressed work-product and
  current task-only materialization;
- existing tests and CI: executable regression surfaces.

## D1 — Completion-boundary predicate

The current typed result remains the source of control outcome. The application
adds one narrow predicate before the requested effects are applied:

```text
source = Executor / implement-change
result = MORE_IMPLEMENTATION_REQUIRED or READY
        |
        +-- exactly one current-Change tasks.md materialization
        |   whose content is a monotonic checkbox-only update
        |
        +-- exactly one bounded SLICE_CHECKPOINT effect
            whose envelope/action/change/revision/evidence fields match source
        |
        v
requested effects pass existing guards and postconditions
        |
        v
application derives the existing successor
```

The predicate is an application acceptance rule, not a new Result or state. A
blocked, incomplete, unverified, or specification-blocked slice keeps its
existing result disposition and does not claim a completed slice. The normal
implementation procedure must use the completion results only after VERIFY and
the checkpoint obligation are ready.

The predicate runs before any requested effect is applied when its required
effect set is structurally incomplete. Existing effect ordering then supplies
the durable boundary: task materialization and checkpoint postconditions must be
observed before the derived routing effect. If an external carrier or later
comment write is interrupted, routing remains at the source Action and a fresh
wake replays only still-missing effects.

## D2 — Candidate A exact-head sequence

The implementation slice is first materialized on the existing implementation PR
using current content-addressed ingress and the existing carrier. The worker then
verifies the exact PR head and required checks. A subsequent bounded checkpoint
effect uses the current task-only exception to materialize only
`openspec/changes/<change>/tasks.md` on the same PR and emits one
`SLICE_CHECKPOINT` comment. The task-only materialization is based on the exact
implementation head and is itself observed with current PR/ref/head identity.

The checkpoint comment records the verified implementation revision, not a new
workflow cursor. Current code/tests/PR/head and task markers remain the recovery
truth. The comment supplies a bounded human/audit view of the same completion
boundary. A replay may observe an already-applied task commit or already-existing
bot comment and continue with the remaining effect without creating duplicates.

Candidate B was rejected because it would widen the existing application
capability to classify a mixed implementation/task manifest, increasing the
semantic and stale/replay surface without evidence that Candidate A cannot reach
the exact required boundary.

## D3 — Monotonic task bookkeeping

For the normal Executor task-only checkpoint, application reads the exact
`expected_sha` content and the candidate blob before creating or accepting the
work-product commit. The candidate is valid only when:

- the path is exactly the current Change's `tasks.md`;
- the source is exactly Executor / `implement-change`;
- every non-marker line and every task description is unchanged;
- the ordered task-marker list is unchanged;
- each changed marker is exactly `[ ] -> [x]`;
- at least one marker changes;
- no `[x] -> [ ]`, addition, deletion, wording change, reorder, stale expected
  SHA, or ambiguous source is accepted.

The action-specific procedure identifies which already-verified current-slice task
IDs are satisfied. The application proves the semantic-neutral file delta and
the exact content-addressed postcondition; it does not infer task meaning from
free-form comments or create a second task registry.

## D4 — Bounded checkpoint evidence

The required effect is an existing `issue-comment` effect with the current
canonical `SLICE_CHECKPOINT` presentation. The application checks only the
bounded completion fields needed for the acceptance predicate: exact workflow
Issue, immutable Change, Executor implement Action, completed task IDs, exact
verified revision tied to the task checkpoint base, VERIFY/gate evidence, and a
nonempty remaining approved boundary. It does not parse comments as routing
state, maintain a cursor, or use comment recency as recovery authority.

Exactly one checkpoint effect is accepted for one completed slice. Existing
idempotent bot-comment reuse handles replay after the comment already exists.

## D5 — Task-authoring boundary

The current OpenSpec authoring owner receives one concise rule: implementation
task markers must describe work Executor can implement and VERIFY during
`implement-change`. Reviewer PASS, merge completion, archive completion, and
post-review lifecycle transitions remain lifecycle evidence and gate conditions;
they are not implementation task markers. The rule is procedural/authoring
guidance, not a second lifecycle representation. The existing #207 downstream
checkbox is removed or rewritten only through the normal semantic correction path
for this Change; the lifecycle gate itself remains intact.

## D6 — Post-merge reconciliation retirement

The current post-merge task-only branch remains present while the normal path is
being repaired. It is not used as the normal completion architecture. After the
new predicate, monotonic normal task path, checkpoint evidence, focused
regressions, and a fresh active/legacy-consumer inventory are all green, the final
implementation slice removes the compensating path and only its obsolete tests
and special-case imports. If a live legacy consumer remains, the path stays with
that exact reason recorded in the implementation evidence.

## Verification and failure behavior

The focused regressions exercise the real application boundary:

- missing task/checkpoint effects reject before successor persistence;
- task-only marker updates accept only monotonic checkbox changes;
- checkpoint body identity and required fields are bounded to the selected source;
- postcondition failure leaves the source routing unchanged;
- interruption/replay accepts already durable effects without duplicate commits or
  comments;
- one slice cannot advance to a later Action without its checkpoint;
- downstream lifecycle gates are not represented as task markers.

All existing exact revision, current PR/head, carrier, stale, replay, and
fail-closed checks remain in force. The design adds no new carrier protocol,
transport state, validator subsystem, Action, Result kind, or orchestration.
