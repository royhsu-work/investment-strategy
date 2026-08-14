# Change: Establish repository governance single source of truth

## Why

Repository governance is currently expressed across `README.md`, `agents/AGENTS.md`, `agents/roles/*`, `agents/skills/*`, `agents/scheduled-task-migration.md`, and OpenSpec artifacts. Several rules are summarized or restated at multiple layers, which makes authority and change ownership harder to reconstruct and increases drift risk.

#29 also carries two demonstrated execution-contract gaps that depend on getting ownership placement right:

- short-lived exact-head CI can be classified as a cross-invocation external asynchronous wait too early, amplifying seconds of CI latency into a full wake interval (`#29 issuecomment-5292380147`);
- #28 proved that discovering an Executor-owned temporary-branch cleanup only after final Archive PR native-close can create a closed-Issue routing dead-end (`#29 issuecomment-5293197049`; source lifecycle #28).

The change should make each rule category have one authoritative surface, remove normative duplication where practical, and fix those two execution boundaries at the narrowest existing ownership layer.

## What Changes

1. Define a repository governance ownership model:
   - `README.md`: Human/contributor entry point and repository overview; reference governance instead of restating runtime lifecycle rules.
   - `agents/AGENTS.md`: shared Scheduled-Agent runtime protocol and cross-role invariants.
   - `agents/roles/*.md`: role mission, authority, ownership, and role-specific invariants only.
   - `agents/skills/*`: action-specific executable procedures and local result/handoff rules only.
   - `openspec/config.yaml`: OpenSpec authoring/validation conventions.
   - `openspec/specs/*`: approved capability-level requirements and acceptance scenarios; not an alternative runtime instruction source.
   - active `openspec/changes/*`: proposed change intent/design/tasks until merged; not runtime governance.
   - archived changes: immutable change history and traceability, not current runtime authority.
   - `agents/scheduled-task-migration.md`: external scheduler/bootstrap migration documentation; slot count/cadence remain external product configuration, not repository workflow state.

2. Add a rule-category → authoritative-surface matrix and require references rather than duplicated normative definitions across layers.

3. Remove or narrow concrete duplicated runtime descriptions, especially README lifecycle/role restatement and shared Human/exception/continuation rules repeated in role/skill surfaces. Brief non-normative orientation remains allowed when clearly referential.

4. Clarify first-observation async-wait semantics:
   - `absent` / `queued` / `in_progress` on a just-created or just-triggered exact resource does not automatically prove a real cross-invocation wait;
   - while the same invocation still has bounded execution opportunity and no different authority boundary is required, the selected action may continue bounded observation of that exact resource;
   - if the resource resolves within that bounded opportunity, work-conserving execution continues in the same invocation;
   - once the invocation can no longer continue bounded observation, yielding becomes a legal external asynchronous wait and the existing #28 fresh-read-on-resume contract applies;
   - no durable timer, polling state, heartbeat, retry counter, or hidden waiter is introduced.

5. Keep wake-slot topology external:
   - repository governance defines bootstrap/dispatch behavior, not an exact number of Scheduled Task slots or cadence;
   - `scheduled-task-migration.md` may describe current migration configuration as informational history, but it must not create a permanent normative three-slot requirement;
   - no repository SLO is invented without a Human-approved requirement.

6. Prevent the #28 terminal cleanup dead-end by ordering existing responsibilities instead of adding a new post-close state:
   - before final Archive merge is allowed to native-close the coordination Issue, Lead `finalize-archive` must reconstruct known workflow-owned temporary recovery/integration branches and identify unresolved terminal cleanup obligations;
   - `Executor / merge-pr` for the final Archive PR must perform any already-safe Executor-owned temporary-branch cleanup before the merge mutation and fresh-read the relevant preconditions;
   - if cleanup is blocked, the Issue is still open and can legally return to Lead diagnosis;
   - only after pre-close cleanup obligations are cleared may the final Archive PR merge/native-close proceed;
   - no new post-close Executor action, broad reopen path, generic branch registry, or cleanup state machine is added.

## Affected Capabilities

- **NEW** `repository-governance`: authority/ownership model, SSOT/reference rules, and current-vs-history boundaries.
- **MODIFIED** `scheduled-agent-workflow`: first-observation external async-wait boundary, scheduler-topology ownership, and pre-native-close terminal cleanup ordering.

## Scope Boundaries

In scope:
- governance document ownership and normative-reference rules;
- bounded removal/narrowing of demonstrated duplicate normative text;
- async-wait classification/continuation semantics;
- external wake-slot ownership semantics;
- terminal cleanup ordering needed to avoid the demonstrated closed-Issue dead-end;
- focused tests for the above.

Out of scope:
- redesigning all repository documentation;
- adding Explore lifecycle (#38);
- Skill maintenance/skill-creator work (#35);
- adding a new scheduler service, lock/lease/heartbeat/retry state;
- changing Human provenance/security policy;
- replacing the existing nine-action lifecycle;
- repository-wide branch garbage collection;
- changing external Scheduled Task configuration in this change.

## Evidence / Trace

- Coordination Issue: #29.
- Short-lived CI / async-wait requirement: #29 `issuecomment-5292380147`.
- Native-close terminal cleanup routing gap: #29 `issuecomment-5293197049`, demonstrated by #28.
- Existing recovery semantics that must remain intact: archived change `harden-scheduled-agent-recovery` and canonical `scheduled-agent-workflow` spec.
- Proportionality constraint: current default-branch `agents/proportionality.md`; prefer reordering/reuse of existing ownership over a new post-close lifecycle state.
