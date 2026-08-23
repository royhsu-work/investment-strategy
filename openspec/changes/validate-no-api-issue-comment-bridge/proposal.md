# Change: Validate no-API Issue-comment bridge

## Why

The repository already contains machine-dispatch and effect-gating code, but the current Scheduled Agent GitHub Actions worker invokes the OpenAI Responses API. That does not establish the runtime path required by the actual ChatGPT Scheduled Task environment, where the model invocation originates in ChatGPT and repository-owned executable code must be reached without requiring an OpenAI API worker.

#140 Explore established a smaller feasibility boundary: first prove that one ChatGPT Scheduled Task invocation can write an exact GitHub Issue comment, cause a default-branch `issue_comment` GitHub Actions workflow to execute bounded repository-owned code, and read back the exact correlated result. This transport proof is intentionally separated from real workflow dispatch, mapped Role/Skill loading, consequential effect application, and mechanical no-bypass enforcement.

## What Changes

- Add a standalone GitHub `issue_comment` transport canary that accepts only a bounded `DISPATCH_REQUEST` comment on one explicitly configured Human-created check-in Issue.
- Use the GitHub request comment ID as the sole correlation identity; do not introduce a custom request UUID and do not correlate by latest comment.
- Execute a bounded repository-owned handler from the current default-branch checkout and write a correlated `DISPATCH_RESULT` containing the exact request-comment ID, handler default-branch revision, and bridge result.
- Make malformed, unrelated, repeated, or already-completed requests fail closed or become idempotent no-ops, and ensure a RESULT cannot itself satisfy the REQUEST contract.
- Keep REQUEST/RESULT messages transport/audit only: Phase 1 returns no Role, Action, Skill, workflow authorization, or consequential-effect authority.
- Add focused automated regression coverage plus one real same-Scheduled-Task end-to-end canary acceptance proving request write → Actions execution → exact correlated result readback, with timestamps/revision sufficient to measure the round trip.

## Scope

Affected capability:
- `scheduled-agent-workflow`

In scope:
- one standalone default-branch `issue_comment: created` canary workflow;
- a bounded repository-owned request parser/handler;
- explicit check-in Issue configuration;
- exact request-comment-ID correlation and idempotency;
- focused tests for request filtering, correlation, duplicate handling, result shape, and authority isolation;
- actual Phase 1 end-to-end bridge evidence from the ChatGPT Scheduled Task environment.

Out of scope:
- changing or replacing `workflow_dispatch.py` or the production cardinality classifier;
- real workflow dispatch or returning exact mapped Issue/Role/Action;
- loading Lead, Reviewer, Executor, or mapped Skills from the bridge result;
- consequential effect application or stale-state mutation authorization;
- mechanical no-bypass/capability separation;
- removing the existing Responses API runtime path in this Change;
- automatic daily check-in Issue creation or closure;
- multi-repository control-plane work;
- #137 proposal-entry feasibility policy or #138 executable/semantic context reduction.

## Durable source decisions

- Coordination Issue: #140
- Human Phase 1 refinement: `issuecomment-5386416122`
- Decision-complete Explore result: `issuecomment-5386482159`
- Explore baseline revision: `cb8f9ec12d826e0d71897a4c73ece961d00df59e`

The Human refinement is authoritative work input for the Phase 1 correlation contract: the exact GitHub request comment ID replaces the earlier custom `request_id` wording.

## Deferred work

After the bridge succeeds, a later bounded Change may connect the transport to the existing production dispatch classifier. Consequential effect gating and mechanical no-bypass/capability separation remain separate later gates and must be driven by actual canary evidence rather than assumed in this transport Change.
