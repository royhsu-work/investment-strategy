# Design: Improve workflow continuation integrity

## Context

The existing workflow already has durable routing, fixed-role execution, at-least-once reconstruction, exact-resource asynchronous semantics, and cross-role handoff evidence. The required correction is to make those existing ownership layers sufficient for three demonstrated failure modes without adding another workflow engine.

Primary source evidence:
- #50 Explore result `issuecomment-5302486512`;
- #35 deferred-follow-up loss case;
- current default-branch `agents/AGENTS.md`, Lead/Reviewer/Executor role contracts, mapped skills, message templates, and canonical `scheduled-agent-workflow` spec.

## Decision 1: Required deferred follow-up is an explicit semantic class, not keyword scanning

A durable tracker obligation exists only when Lead-owned approved scope/specification meaning explicitly says work remains required and is deferred to a separate later change. Ordinary non-goals, optional ideas, or out-of-scope statements do not create trackers.

Lead owns tracker creation because Lead owns scope/specification meaning. The tracker stores durable work evidence only and receives no Human admission or routing automatically. Idempotency uses a reconstructable source linkage tuple: source coordination Issue/Change plus defer-decision reference.

Reviewer checks the invariant during `review-openspec`; `finalize-archive` is the terminal fail-safe. This catches loss early and again before lifecycle completion without creating a general backlog generator.

## Decision 2: Invocation identity is one workflow + one fixed role; action is not invocation identity

The invocation selects exactly one coordination Issue and fixes one role. After an action result and routing mutation, a target action owned by that same role can continue only after a fresh read and full target-action reconstruction. The prior action grants no inherited precondition or authority.

The legal continuation predicate is deliberately small:

```text
same Issue
AND target role == invocation role
AND current routing matches target
AND target immediately actionable
AND no Human / real async / ambiguity / stale / unsafe boundary
```

Multiple same-role transitions may continue while those conditions remain true. No counter or durable continuation state is added; runtime opportunity is an execution-environment boundary, not repository state.

## Decision 3: `HANDOFF` remains cross-role only

`HANDOFF` communicates ownership transfer. A same-role action transition does not transfer ownership, so adding synthetic `HANDOFF` records would create noise and confuse recovery.

Same-role crash recovery is reconstructable from:
- source `ACTION_RESULT` or equivalent durable decision evidence;
- current routing tuple;
- current repository/PR/OpenSpec/Actions state.

Cross-role routing still requires `HANDOFF` and ends the invocation.

## Decision 4: Strengthen exact-resource work conservation, do not add polling machinery

Shared governance already distinguishes the first nonterminal observation of an exact resource just triggered by the selected action from a real asynchronous wait. Action guidance will make this executable: while bounded same-invocation opportunity remains, observe only that exact resource and continue immediately if it becomes terminal.

A later wake always fresh-reads the exact awaited resource. No sleeps, poll counters, timers, background waiters, leases, or heartbeat state are added.

Actions directly affected include Lead OpenSpec validation producers and Executor quality/OpenSpec-validation producers. Merge-triggered Archive remains cross-role and therefore does not permit Executor to wait and execute Lead work.

## Decision 5: Preserve single-active workflow and immutable Change identity

This change does not add a general suspend/preemption state. The duplicate-active recovery incident is retained as evidence that activation and recovery must remain revision-aware and explicit, but normal execution continues to enforce one active workflow and immutable Change identity.

Any future Human-authorized preemption/suspension model requires a separately approved contract if still needed after this change. This change does not legitimize hidden suspension metadata or silent identity rewrites.

## Blast radius

Authoritative surfaces expected to change during implementation:
- `openspec/specs/scheduled-agent-workflow/spec.md`;
- `agents/AGENTS.md` for shared continuation/deferred-follow-up invariants;
- `agents/templates/messages.md` to clarify `HANDOFF` as cross-role transfer;
- `agents/roles/lead.md` for tracker ownership/final fail-safe specialization;
- `agents/skills/openspec-change/SKILL.md` for same-role continuation and exact validation observation;
- `agents/skills/openspec-review/SKILL.md` for required-defer tracker gate;
- `agents/skills/lifecycle-finalize/SKILL.md` for terminal tracker fail-safe and same-role lifecycle continuation;
- `agents/skills/implementation/SKILL.md` for exact required CI/Actions observation;
- focused tests covering governance/message/skill contracts.

`merge-pr` retains its cross-role stop invariant. Reviewer and Executor role authority does not expand.

## Compatibility

- New semantics activate only after merge to default branch.
- Historical `HANDOFF` records remain valid under the governance active when written.
- Completed historical changes are not retroactively invalidated for missing required-defer trackers.
- Existing trackers satisfy new obligations when their durable source linkage is reconstructable.
- Existing active workflows evaluate only still-applicable obligations under the activated contract.

## Rejected alternatives

### Add an `ACTION_TRANSITION` message
Rejected because routing plus durable result already reconstruct same-role transitions.

### Add a continuation counter or runtime timer
Rejected because it creates unnecessary state and does not improve authority safety.

### Auto-create trackers for every out-of-scope statement
Rejected because it creates backlog noise and changes scope semantics.

### Let one invocation switch roles
Rejected because it weakens independent review and role separation.

### General suspend/preemption state in this change
Rejected as broader than the demonstrated #50 decision-complete scope; it would add lifecycle state not required for the three target failure modes.
