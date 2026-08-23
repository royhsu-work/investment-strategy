# Design: Validate no-API Issue-comment bridge

## Context

The repository's current machine-gated runtime code and regression coverage demonstrate how repository-owned dispatch and effect authorization can work inside GitHub Actions, but the deployed worker path still calls the OpenAI Responses API. #140 narrows the first no-API step to transport feasibility only: prove that ChatGPT Scheduled Task can synchronously exchange a request/result pair with bounded repository-owned GitHub Actions execution through Issue comments.

Primary source evidence:
- #140 Human Phase 1 refinement `issuecomment-5386416122`;
- #140 decision-complete Explore result `issuecomment-5386482159`;
- current default-branch `.github/workflows/scheduled-agent-runtime.yml` and `src/investment_strategy/scheduled_agent_worker.py` showing the existing Responses API worker path;
- GitHub Actions documentation for the `issue_comment` `created` event and GitHub's `GITHUB_TOKEN` recursion suppression semantics.

The canary is deliberately not workflow authorization. Its only question is whether the actual product/runtime boundary can complete this round trip inside one Scheduled Task invocation:

```text
Scheduled Task
  → GitHub Issue comment request
  → issue_comment Actions event
  → repository-owned handler
  → GitHub Issue comment result
  → same Scheduled Task reads exact correlated result
```

## Decision 1: Add a separate transport canary instead of modifying production dispatch

Phase 1 uses a dedicated `issue_comment: types: [created]` workflow. It does not modify `workflow_dispatch.py`, the current production classifier, mapped Role/Skill loading, or the existing Responses API runtime path.

This isolates the only unproven property that matters for Phase 1: transport between ChatGPT Scheduled Task and repository-owned executable code. A canary failure therefore does not change normal workflow authorization semantics, and the canary can be removed or extended after evidence is collected.

The workflow checks out the repository default branch for handler execution. The result records the exact checkout revision used by the handler.

## Decision 2: The GitHub request comment ID is the sole correlation identity

The request body is exactly the bounded protocol:

```text
DISPATCH_REQUEST
Requested-At: <timestamp>
```

After the comment write, the GitHub comment ID returned or freshly observed for that exact request is the correlation identity. No custom UUID is generated.

The result body is:

```text
DISPATCH_RESULT
Request-Comment-ID: <exact GitHub request comment ID>
Default-Branch-Revision: <exact handler checkout revision>
Result: BRIDGE_OK
```

The Scheduled Task accepts only a result whose `Request-Comment-ID` equals its own exact request comment ID. It must not select the latest result, infer correlation from time proximity, or guess from comment order.

Using GitHub's immutable comment identity removes an unnecessary identifier layer while keeping correlation deterministic and directly tied to the triggering event.

## Decision 3: Check-in Issue selection is explicit deployment configuration, not workflow authority

A Human creates the Phase 1 check-in Issue outside this Change. The repository canary accepts a request only when the triggering comment belongs to the exact configured check-in Issue number.

The check-in Issue number is deployment/configuration input, preferably an explicit repository variable consumed by the workflow. It is not a workflow-routing or authorization field and must not be interpreted as Role/Action selection.

If the configured Issue identity is absent, malformed, or does not match the triggering Issue, the workflow performs no valid request handling. Phase 1 does not create, rotate, or close check-in Issues automatically.

## Decision 4: Strict parsing plus required request-scoped serialization bounds duplicate delivery

The repository-owned handler validates all of these before producing a result:

- event activity is a newly created Issue comment;
- the event belongs to the configured check-in Issue;
- the comment body matches the exact two-line request contract with one parseable `Requested-At` value;
- the event exposes a positive numeric request comment ID;
- no already persisted valid `DISPATCH_RESULT` exists for that exact request comment ID.

Malformed/unrelated input is an ignored/non-request outcome rather than authority to do additional work. A rerun or duplicate delivery for a request that already has a valid correlated result is an idempotent no-op.

The workflow MUST serialize handling for the same immutable request comment ID with a request-scoped GitHub Actions concurrency group and `cancel-in-progress: false`. Different request comment IDs remain independent. After entering that serialized execution boundary, the handler MUST freshly re-check whether a valid correlated `DISPATCH_RESULT` already exists immediately before posting a new result. If one already exists, the run is an idempotent no-op.

The correctness boundary is therefore:

```text
exact request comment ID
→ same-request Actions serialization
→ fresh correlated-result re-check
→ at most one effective DISPATCH_RESULT
```

The concurrency group is transient GitHub Actions execution serialization, not a durable workflow lock, lease, claim, retry registry, or hidden lifecycle state. The durable GitHub comment remains the completion evidence, while required serialization prevents two overlapping check-then-write runs for the same request from both passing the absence check and posting duplicate valid results.

## Decision 5: RESULT cannot authorize workflow execution

Phase 1 `DISPATCH_RESULT` contains no Issue/Role/Action selection, no mapped Skill identity, no requested effect, and no instruction to mutate canonical workflow state. `BRIDGE_OK` means only that repository-owned code handled the transport request.

The result body is intentionally syntactically distinct from `DISPATCH_REQUEST`, so an Actions-created result cannot satisfy the canary request parser. GitHub's documented suppression of ordinary workflow recursion from `GITHUB_TOKEN` mutations provides an additional platform-level guard, but parser separation remains defense in depth.

The existing `agent:*`, `action:*`, `Change:`, review gates, and production classifier remain completely outside the Phase 1 result contract.

## Decision 6: Real end-to-end evidence is part of acceptance, not replaced by repository tests

Unit/structural tests prove parser, filter, correlation, same-request serialization, idempotency, result shape, workflow trigger/permissions, and authority-isolation behavior. They cannot prove ChatGPT Scheduled Task execution opportunity and Actions round-trip latency.

GitHub's `issue_comment` event only runs a workflow when the workflow file exists on the repository default branch. Therefore the real canary cannot be a pre-merge acceptance step for the first implementation revision that introduces `.github/workflows/scheduled-agent-bridge-canary.yml`.

The Change uses the repository's existing multi-PR lifecycle instead of inventing a deployment exception:

1. The first implementation revision completes Slice 1, including the workflow, handler, deterministic tests, required same-request serialization, and repository validation. Slice 2 remains explicitly incomplete.
2. After normal implementation review and merge, the canary workflow exists on `main`. Because approved work remains, `Lead / finalize-change` reconstructs the incomplete Change and uses the existing `MORE_IMPLEMENTATION_REQUIRED → Executor / implement-change` continuation rather than attempting archive.
3. A later real ChatGPT Scheduled Task invocation uses the Human-created configured check-in Issue, writes the exact request, captures its exact GitHub request comment ID, performs bounded fresh reads for only that correlation, and observes the matching Actions-produced result before the invocation ends.
4. The resulting transport evidence and justified Slice 2 task completion are recorded in the subsequent implementation revision/PR under the normal multi-PR workflow. No task is marked complete before the real evidence exists.
5. That subsequent implementation revision passes the normal implementation review/merge lifecycle. Only after no approved implementation work remains may `finalize-change` proceed toward archive.

For the real invocation itself, acceptance requires that it:

1. writes the exact request;
2. captures its exact request comment ID;
3. performs bounded fresh reads for only that correlation;
4. observes the matching Actions-produced result before the invocation ends; and
5. records request/result timestamps, the handler revision, and the observation needed to determine round-trip latency.

If the result is not observed within that same invocation, the bridge is not declared successful and Slice 2 remains incomplete. That failure is evidence for the next design decision; it does not justify adding polling state, webhook callbacks, or an OpenAI API worker inside this Change.

This sequencing is deployment ordering inside the existing one-Change/multi-PR lifecycle. It does not introduce a second workflow DAG, a special merge authorization, or a new persistent state machine.

## Blast radius

Expected implementation surfaces are intentionally narrow:

- `.github/workflows/scheduled-agent-bridge-canary.yml` — standalone `issue_comment` trigger, explicit permissions/configuration, required request-scoped serialization, default-branch checkout, bounded handler invocation;
- `src/investment_strategy/scheduled_agent_bridge_canary.py` — request validation, exact correlation/idempotency, result rendering/posting boundary;
- `tests/test_scheduled_agent_bridge_canary.py` — focused deterministic regressions;
- this OpenSpec Change and its delta requirement.

No default-branch `agents/AGENTS.md`, `agents/workflow.md`, role, mapped Skill, canonical message template, production dispatch classifier, or effect-gate change is required for Phase 1.

## Compatibility and rollout

- The existing scheduled Responses API runtime remains unchanged during this canary Change; its continued presence does not prove or disprove the no-API bridge.
- The new canary workflow has no scheduled trigger and no `workflow_dispatch` dependency. Only matching `issue_comment: created` events on the configured check-in Issue are handled.
- The Human-created check-in Issue is external deployment setup and may be removed after the experiment without changing canonical workflow state.
- The first implementation merge deploys the canary but does not declare Phase 1 complete; the real Scheduled Task E2E remains required follow-on work inside the same Change.
- Phase 1 success authorizes only the conclusion that the transport works. Any later connection to the production dispatcher requires a new bounded Change and current-state review.

## Rejected alternatives

### Reuse the existing Responses API worker

Rejected because the entire Phase 1 question is whether repository-owned execution can be reached from ChatGPT Scheduled Task without an OpenAI API worker.

### Put the canary into the production dispatch workflow

Rejected because it would couple a transport experiment to workflow authorization and make failures harder to classify or roll back.

### Generate a custom request UUID

Rejected because GitHub already supplies an exact immutable comment ID for the triggering request; another correlation identifier adds state without capability.

### Correlate using the latest comment or timestamps

Rejected because concurrent or delayed comments make ordering/proximity non-authoritative. Exact request-comment identity is deterministic.

### Rely on check-then-post without same-request serialization

Rejected because two overlapping runs can both observe no existing correlated result before either posts. Required request-scoped Actions serialization plus a fresh result re-check closes that demonstrated race without adding durable coordination state.

### Run the real canary before the workflow is merged to the default branch

Rejected because GitHub only triggers `issue_comment` workflows whose workflow file already exists on the default branch. The existing multi-PR `MORE_IMPLEMENTATION_REQUIRED` lifecycle provides the needed deployment sequence without a special bypass.

### Automate daily check-in Issue lifecycle now

Rejected because Issue creation/rotation is unrelated to proving transport and would expand the mutation surface before the bridge itself is known to work.

### Add callback, polling service, lock, lease, heartbeat, or durable retry state

Rejected for Phase 1. The first canary should measure the actual bounded same-invocation round trip before introducing any additional runtime machinery.
