# Change: Improve workflow continuation integrity

## Why

The Scheduled-Agent workflow has three demonstrated integrity gaps: required deferred follow-up can be lost before lifecycle completion, same-role work can stop at an action boundary even when the next action is immediately actionable, and short exact CI/Actions runs can cause premature cross-wake yielding. #35 demonstrated the deferred-follow-up loss. #50 exploration established a bounded correction that preserves one selected workflow, fixed invocation role, role separation, durable routing, and fail-closed reconstruction.

A later recovery incident also demonstrated that interrupted/competing activation evidence must be reconstructed rather than silently rewritten. This change does not introduce hidden suspension state or a second dispatcher; it keeps recovery within explicit durable evidence and current routing.

## What Changes

- Define when an approved deferred item becomes a required durable follow-up obligation and require Lead to create/reuse a traceable tracker without auto-admitting it.
- Require `review-openspec` and terminal lifecycle finalization to detect missing required follow-up trackers while ignoring ordinary out-of-scope/non-goal statements.
- Allow one invocation to continue from one action to another only when the selected coordination Issue is unchanged, the invocation role is unchanged, and the target action is immediately actionable after fresh reconstruction.
- Keep `HANDOFF` as cross-role ownership-transfer evidence; same-role transitions rely on durable action result plus routing mutation and target reconstruction.
- Strengthen exact-resource asynchronous guidance so a just-triggered required CI/Actions run that becomes terminal during the same invocation is consumed immediately rather than voluntarily yielding.
- Preserve later-wake fresh-read behavior for real asynchronous waits and preserve cross-role stop boundaries.
- Add focused regression coverage for deferred-follow-up integrity, same-role continuation boundaries, and exact short-run handling.

## Scope

Affected capability:
- `scheduled-agent-workflow`

In scope:
- shared Scheduled-Agent reconstruction/continuation semantics;
- required deferred-follow-up tracking and lifecycle checks;
- `HANDOFF` presentation boundary;
- action-local exact CI/Actions observation guidance;
- focused workflow regression tests.

Out of scope:
- central dispatcher/workflow engine;
- lock, lease, heartbeat, retry/progress counters, hidden waiter, or hidden sequence state;
- same-invocation role switching;
- processing a second coordination Issue in one invocation;
- automatic tracking for ordinary out-of-scope ideas;
- changing Human admission authority;
- redesigning GitHub provenance security tracked separately by #47.

## Durable source decisions

- Coordination Issue: #50
- Explore result: issuecomment-5302486512
- Human proceed decision: issuecomment-5302641991
- Human recovery/priority authorization is supporting incident evidence; it does not create a second runtime authority surface.

## Deferred work

- Human-authority provenance hardening remains #47.
- Python Ruff security policy remains #48.
- Prompt/Agent security regression coverage remains #49.
