## Why

#470 addresses the repeated premature invocation return reported by Human during #468 Explore and Propose: submitting a Worker Result and triggering its Application was mistaken for completion or sufficient progress to exit. The same incident class was previously addressed by #112, #124 and #130. The current control-plane reset deliberately removed fixed-role and same-wake successor continuation; it did not intend to permit intermediate-step termination. Current canonical asynchronous observation permits "MAY continue" despite requiring one complete selected Action. The shared execution owner lacks a consolidated positive Invocation Exit obligation.

Human confirmed a narrowly scoped SSOT correction and the dependency order #470 → #468 → #435. Only #470 is delivered here. The dependency order is not authority to change or consume either dependent's work.

## What Changes

- Restore continuation-by-default and termination-by-proof for the one current repository-dispatched Action.
- Make bounded observation of necessary exact external resources mandatory when the current authority, revision, preconditions and real execution opportunity remain valid; distinguish intermediate semantic output, Application and Action completion.
- Preserve existing legal exits, exception disposition, hard carrier handoff, Human authority, stale/precondition safety, fresh reconstruction and one Action per wake.
- Verify observable behavior with source-qualified execution traces or applicable Agent behavioral evaluations; do not equate static checks or run success with behavioral acceptance.
- Do not introduce another runtime state or execution engine. Do not implement or recover #468 or #435.

## Capabilities

### Modified Capabilities

- scheduled-agent-workflow: strengthen the existing external asynchronous waits requirement and shared one-Action continuation/exit behavior.

## Impact

- Consolidate shared runtime instructions in the existing owner `agents/AGENTS.md`.
- Modify the one existing canonical requirement through the normal OpenSpec delta and archive lifecycle; no separate canonical runtime owner.
- Role/Skill treatment: REUSE. No Skill Added, Modified, Removed or Replaced is presently justified. Existing Role/Skill procedures consume shared governance; any demonstrated material conflict must be returned through the governed scope/semantic correction path before changing them.
- NO-DELTA: Dispatcher, Application, Recovery, Action/Role model, dependency DAG, routing, schedules, carriers, review/merge gates and workflow topology; no durable waiter, registry, timer, heartbeat, fixed observation count, lease, retry engine or second dispatcher.
- Complete independent semantic, implementation and archive review, applicable exact-revision gates, formal lifecycle completion/closed/no-routing, and verify #468 dependency satisfaction without executing it. No historical reopening or blanket replay.

## Traceability

Human source: [#470](https://github.com/royhsu-work/investment-strategy/issues/470), including the approved scope and boundaries. Native Explore [PROPOSAL_READY](https://github.com/royhsu-work/investment-strategy/issues/470#issuecomment-7125391526) and [ACCEPTED decision](https://github.com/royhsu-work/investment-strategy/issues/470#issuecomment-7125390633), exact baseline 7ad60ca6417d6ca42656cf0fca00d33d6e16b8ed. [#112](https://github.com/royhsu-work/investment-strategy/issues/112), [#124](https://github.com/royhsu-work/investment-strategy/issues/124), [#130](https://github.com/royhsu-work/investment-strategy/issues/130) and the archived reset `2026-09-04-simplify-scheduled-agent-control-plane` are historical evidence, not current authority.

Refs #470
