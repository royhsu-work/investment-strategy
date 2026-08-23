# Tasks: Validate no-API Issue-comment bridge

## Slice 1 — Correlated Issue-comment transport canary

- [ ] **RED** Add focused tests that fail until the canary strictly accepts only the configured check-in Issue plus exact two-line `DISPATCH_REQUEST` contract, uses the triggering GitHub comment ID as the sole correlation identity, rejects malformed/unrelated/RESULT comments, and treats an already-correlated request as idempotently complete.
- [ ] **GREEN** Add the standalone default-branch `issue_comment: created` workflow and bounded repository-owned handler that checks out current default branch, validates the configured check-in Issue/request event, prevents duplicate effective results, and writes only the exact `DISPATCH_RESULT` transport fields with `Result: BRIDGE_OK`.
- [ ] **REFACTOR** Keep the canary isolated from `workflow_dispatch.py`, production classifier/runtime, Role/Skill loading, canonical routing/Change/review state, and consequential effect authorization; consolidate request/result parsing and rendering without adding custom request IDs, hidden state, retry counters, polling services, locks, leases, or heartbeat machinery.
- [ ] **VERIFY** Run the focused canary tests, full pytest suite, mypy, Ruff, and strict OpenSpec validation for the exact implementation revision; verify workflow trigger/permissions/configuration and that no production dispatch/Role/Skill/effect surface changed.

Trace: proposal `What Changes` items 1–5; added requirement `A no-API Issue-comment canary proves the Scheduled Task transport boundary without granting workflow authority`; design Decisions 1–5.

## Slice 2 — Real same-Scheduled-Task round-trip proof

- [ ] **RED** Before declaring bridge success, establish that repository-only tests provide no qualifying real Scheduled Task round-trip evidence and therefore cannot satisfy the Phase 1 end-to-end acceptance scenario by themselves.
- [ ] **GREEN** Using a Human-created configured check-in Issue, execute one real ChatGPT Scheduled Task invocation that writes the exact request, captures its exact GitHub request comment ID, performs bounded fresh reads for only that identity, and observes the matching Actions-produced `DISPATCH_RESULT` before the invocation ends.
- [ ] **REFACTOR** Record only the minimum transport evidence required for the experiment—request/result GitHub timestamps, exact request comment ID, exact handler default-branch revision, Scheduled Task matching-result observation, and derived round-trip latency—without promoting canary messages into workflow authority or adding callback/waiter state.
- [ ] **VERIFY** Confirm the observed result correlates only by the exact request comment ID, `Default-Branch-Revision` matches the handler checkout used for the run, `BRIDGE_OK` contains no mapped Issue/Role/Action/Skill/effect authorization, and the result was observed within the same Scheduled Task invocation execution opportunity.

Trace: proposal `What Changes` item 6; added requirement final acceptance paragraph and scenario `Same-invocation round trip is required for Phase 1 acceptance`; design Decision 6.

## Final verification

- [ ] Verify proposal → specs → design → tasks forward traceability and tasks → design → specs → proposal reverse traceability.
- [ ] Verify the Change remains limited to the Phase 1 Issue-comment bridge and does not implement production dispatch, Role/Skill loading, consequential effects, no-bypass capability separation, automatic check-in Issue lifecycle, #137, or #138.
- [ ] Record exact-revision strict OpenSpec validation evidence before Reviewer handoff.
