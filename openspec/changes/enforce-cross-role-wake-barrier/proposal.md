# Change: Enforce cross-role wake barrier

## Why

Current default-branch capability truth already requires `workflow-dynamic` dispatch to keep the selected invocation role fixed and to end rather than redispatch into a different role, but shared runtime/presentation text and the current continuation helper/tests still permit or describe cross-role continuation inside one scheduled execution opportunity. Issue #161 demonstrated the resulting semantic/enforcement split through the completed #155 lifecycle.

The exact upstream Explore result is Issue #161 comment `5440915970` (`PROPOSAL_READY`, revision `387105aee9788f1abfd4fb997f3007b7edbd248a`). This Change formalizes that result without changing workflow topology or role authority.

## What Changes

- Make one Scheduled-Agent wake retain the role from its first repository-owned `AUTHORIZE` decision as an invocation-local `initial_role` boundary.
- Preserve fresh repository reconstruction and a fresh mapped worker for every successor action.
- Allow same-role successor actions on the same coordination Issue to continue during the same wake after fresh dispatch.
- Make a fresh dispatch that selects a different role wake-terminal: preserve the newly selected durable routing, but do not invoke that role until a later wake performs ordinary fresh reconstruction.
- Align shared governance and canonical message presentation with the existing capability requirement so `invocation`, mapped worker, and scheduled wake are not used to imply cross-role same-wake execution.
- Add executable regression coverage at the repository-owned continuation boundary for Lead→Reviewer, Reviewer→Executor, Executor→Lead, same-role continuation, and no-work/fail-closed behavior.

The dispatcher selection algorithm, formal workflow topology, WIP=1/finish-first behavior, Human authority, routing tuples, action ownership, and external scheduler role slots are unchanged.

## Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: clarify and mechanically enforce that the first selected role is immutable for one scheduled wake while same-role fresh-worker continuation remains work-conserving.

## Impact

Expected implementation surfaces are limited to shared Scheduled-Agent governance/presentation, the repository-owned continuation helper near effect application, and focused runtime/continuation tests. No new queue, lease, heartbeat, sequence counter, persistent wake-role state, fixed-role scheduler, or second workflow DAG is introduced.

Refs #161
Refs #155
