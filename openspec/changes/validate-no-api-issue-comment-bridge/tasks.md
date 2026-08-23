# Tasks: Validate no-API Issue-comment bridge

## Slice 1 — Correlated Issue-comment transport canary

- [ ] **RED** Add focused tests that fail until the canary strictly accepts only the configured check-in Issue plus exact two-line `DISPATCH_REQUEST` contract, uses the triggering GitHub comment ID as the sole correlation identity, rejects malformed/unrelated/RESULT comments, requires same-request GitHub Actions serialization with `cancel-in-progress: false`, and re-checks for an already-correlated result inside that serialized boundary before any result post.
- [ ] **GREEN** Add the standalone default-branch `issue_comment: created` workflow and bounded repository-owned handler that checks out current default branch, validates the configured check-in Issue/request event, serializes runs by the exact immutable request comment ID, freshly re-checks for an existing correlated result before posting, treats an already-completed request as an idempotent no-op, and writes only the exact `DISPATCH_RESULT` transport fields with `Result: BRIDGE_OK`.
- [ ] **REFACTOR** Keep the canary isolated from `workflow_dispatch.py`, production classifier/runtime, Role/Skill loading, canonical routing/Change/review state, and consequential effect authorization; consolidate request/result parsing and rendering without adding custom request IDs, hidden durable state, retry counters, polling services, locks, leases, or heartbeat machinery. Treat the required Actions concurrency group only as transient same-request execution serialization.
- [ ] **VERIFY** Run the focused canary tests, full pytest suite, mypy, Ruff, and strict OpenSpec validation for the exact implementation revision; verify the workflow trigger/permissions/configuration, exact-comment-ID concurrency key, `cancel-in-progress: false`, fresh pre-post correlated-result re-check, and that no production dispatch/Role/Skill/effect surface changed.

Trace: proposal `What Changes` items 1–5; added requirement `A no-API Issue-comment canary proves the Scheduled Task transport boundary without granting workflow authority`; design Decisions 1–5.

### Required deployment boundary before Slice 2

Slice 2 MUST NOT begin as a pre-merge check of the implementation revision that first introduces the canary workflow. GitHub only triggers `issue_comment` workflows whose workflow file already exists on the default branch.

The intended existing multi-PR lifecycle is:

1. complete Slice 1 while leaving every Slice 2 task unchecked;
2. pass normal implementation review and merge the Slice 1 implementation so `.github/workflows/scheduled-agent-bridge-canary.yml` exists on `main`;
3. let `Lead / finalize-change` reconstruct the still-incomplete Change and return `MORE_IMPLEMENTATION_REQUIRED → Executor / implement-change`;
4. only then execute Slice 2 against the deployed default-branch canary;
5. record the real E2E evidence and justified Slice 2 task completion in the subsequent implementation revision/PR, then pass the normal implementation review/merge lifecycle before archive eligibility is considered.

This is sequencing inside the existing one-Change/multi-PR lifecycle. It does not authorize an implementation merge outside normal review/merge gates and does not introduce a second workflow state machine.

## Slice 2 — Real same-Scheduled-Task round-trip proof

- [ ] **RED** Before declaring bridge success, establish both that repository-only tests provide no qualifying real Scheduled Task round-trip evidence and that the canary workflow must already be present on `main`; therefore Slice 2 remains incomplete through the first implementation merge even when Slice 1 tests are fully green.
- [ ] **GREEN** After the Slice 1 implementation is merged and `finalize-change` has returned the incomplete Change through `MORE_IMPLEMENTATION_REQUIRED`, use a Human-created configured check-in Issue and execute one real ChatGPT Scheduled Task invocation that writes the exact request, captures its exact GitHub request comment ID, performs bounded fresh reads for only that identity, and observes the matching Actions-produced `DISPATCH_RESULT` before the invocation ends.
- [ ] **REFACTOR** Record only the minimum transport evidence required for the experiment—request/result GitHub timestamps, exact request comment ID, exact handler default-branch revision, Scheduled Task matching-result observation, and derived round-trip latency—without promoting canary messages into workflow authority or adding callback/waiter state. Do not mark Slice 2 complete before this real evidence exists.
- [ ] **VERIFY** In the subsequent implementation revision/PR, confirm the observed result correlates only by the exact request comment ID, `Default-Branch-Revision` matches the handler checkout used for the run, `BRIDGE_OK` contains no mapped Issue/Role/Action/Skill/effect authorization, the result was observed within the same Scheduled Task invocation execution opportunity, and the evidence came from the already-deployed default-branch canary rather than a feature-branch-only workflow.

Trace: proposal `What Changes` item 6; added requirement final acceptance paragraph and scenario `Same-invocation round trip is required for Phase 1 acceptance`; design Decision 6.

## Final verification

- [ ] Verify proposal → specs → design → tasks forward traceability and tasks → design → specs → proposal reverse traceability.
- [ ] Verify the Change remains limited to the Phase 1 Issue-comment bridge and does not implement production dispatch, Role/Skill loading, consequential effects, no-bypass capability separation, automatic check-in Issue lifecycle, #137, or #138.
- [ ] Verify the implementation lifecycle preserves the required two-stage deployment/E2E sequence: first implementation merge deploys Slice 1 with Slice 2 pending; `finalize-change` returns `MORE_IMPLEMENTATION_REQUIRED`; only a later implementation revision records real E2E completion.
- [ ] Record exact-revision strict OpenSpec validation evidence before Reviewer handoff.
