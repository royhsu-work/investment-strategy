## MODIFIED Requirements

### Requirement: Workflow-dynamic dispatch derives one fixed invocation role from durable workflow state

In `workflow-dynamic` mode, a scheduled wake SHALL reconstruct current durable workflow state before selecting a role. If exactly one active workflow exists, its valid routing tuple SHALL determine the first invocation role/action and mapped skill.

The role from the first repository-owned `AUTHORIZE` decision MUST remain fixed as the wake's invocation-local `initial_role` for the remainder of that scheduled wake. Every later mapped action in the same wake MUST still come from fresh repository-owned dispatch and MUST use a fresh mapped worker that reloads current default-branch governance and reconstructs its own durable preconditions.

A fresh dispatch MAY select another action owned by `initial_role`; when that successor is immediately actionable, it MAY continue within the same scheduled wake as a fresh mapped worker. Action identity is therefore not wake-immutable.

A routing handoff MAY persist a different next role/action and fresh dispatch MAY select that durable successor, but if the selected role differs from `initial_role`, the current scheduled wake MUST end without invoking the successor role. A later scheduled wake SHALL reconstruct current durable state and perform ordinary repository-owned dispatch. The wake barrier MUST NOT rewrite the successor routing, invent a defer command, or persist `initial_role` as repository workflow state.

The dispatcher MUST NOT introduce model-derived global urgency, cross-role priority scoring, fixed-role scheduler semantics, or a second workflow DAG.

#### Scenario: Active workflow routes to Reviewer

- GIVEN dispatch mode is `workflow-dynamic`
- AND the single active workflow has valid routing `agent:reviewer + action:review-openspec`
- WHEN a Scheduled Task dispatches the wake
- THEN Reviewer is selected as `initial_role` for that wake
- AND the `review-openspec` skill is loaded for a fresh mapped worker
- AND any legacy external Lead/Reviewer/Executor assignment is ignored for role selection

#### Scenario: Handoff changes the next owner

- GIVEN the current scheduled wake has `initial_role` Lead
- AND Lead durably completes its action and legally hands off to Reviewer
- WHEN fresh repository-owned dispatch selects the Reviewer successor
- THEN the durable Reviewer routing and machine selection are preserved
- AND the current scheduled wake ends as Lead
- AND it does not execute Reviewer work in that same wake
- AND a later scheduled wake must fresh-reconstruct before Reviewer may execute

#### Scenario: Same-role successor remains work-conserving

- GIVEN the current scheduled wake has `initial_role` Lead
- AND Lead durably completes one action on the selected coordination Issue
- AND fresh repository-owned dispatch selects another immediately actionable Lead action on that same Issue
- WHEN the enclosing wake evaluates continuation
- THEN the wake may continue
- AND the successor executes as a fresh Lead mapped worker
- AND the prior worker context does not authorize or supply current-state evidence for that successor

#### Scenario: Cross-role barrier does not create durable wake state

- GIVEN a fresh dispatch selects a successor whose role differs from `initial_role`
- WHEN the current wake terminates at the cross-role boundary
- THEN no Issue field, routing label, comment protocol, lease, heartbeat, queue entry, or hidden repository state is created to remember the wake role
- AND the already durable workflow routing remains the only successor workflow state consumed by the next wake
