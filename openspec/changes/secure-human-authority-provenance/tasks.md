# Tasks: Secure Human authority with provenance-bound GitHub decisions

## Slice 1 — Provenance-bound Human decision predicate

- [ ] **RED** Add deterministic tests proving actor `royhsu-work` alone is insufficient when raw comment creation or approval-label provenance shows a GitHub App.
- [ ] **RED** Add tests for a valid Human-created decision comment carrying the expected `Human-Decision-For: <decision_ref>` plus later Human-only `human:approved` event and unchanged comment revision.
- [ ] **RED** Add tests proving missing/mismatched `decision_ref` cannot satisfy the current Human-reserved boundary.
- [ ] **RED** Add tests proving multiple Human comments are resolved only by exact reference matching plus deterministic latest matching comment ordering, never by model prose selection.
- [ ] **RED** Add tests proving a later matching comment for the same `decision_ref` replaces an earlier matching comment for subsequent approval evaluation.
- [ ] **RED** Add tests proving a post-approval comment edit invalidates prior approval until a later qualifying Human approval event exists.
- [ ] **GREEN** Implement the minimum reusable Human-authority evaluator from explicit expected boundary reference, comment/event evidence, and stable ordering without hidden authorization state or a generic IAM layer.
- [ ] **REFACTOR/VERIFY** Run focused tests plus the full repository regression, type, lint, and format gates.

Trace: proposal items 1–2, 4–5; spec requirement `Human-required authority is bound to provenance-validated repository Human decisions`; design D1/D3/D4.

## Slice 2 — Reserved approval capability and raw provenance evidence

- [ ] **RED** Add tests proving `human:approved` current presence without a qualifying Human-only `labeled` event is insufficient and `unlabeled` provenance never establishes authority.
- [ ] **RED** Add tests proving normalized reads without `performed_via_github_app` cannot silently degrade to actor-only authority.
- [ ] **GREEN** Add the narrow raw GitHub provenance adapter required for comment creation and label-event evidence.
- [ ] **GREEN** Add/document the exact reserved `human:approved` capability and prohibit Scheduled roles from adding/restoring/manufacturing it.
- [ ] **REFACTOR/VERIFY** Keep provenance reading separate from routing/lifecycle ownership and run focused/full gates.

Trace: proposal items 2–4; spec approval/provenance clauses; design D2/D3.

## Slice 3 — Human-reserved consumers and repository-authorized Explore separation

- [ ] **RED** Add Human-only admission tests proving connector-mediated decision/approval evidence cannot satisfy Human admission and the consumer supplies the exact admission `decision_ref` rather than asking the evaluator to discover one.
- [ ] **RED** Add Human-answer/resume tests proving the exact canonical `HUMAN_DECISION_REQUIRED` comment reference is the expected `decision_ref` and only the matching provenance-bound Human decision can resolve that boundary.
- [ ] **RED** Add authorization tests for current Human-reserved proceed/stop or other authorization consumers, binding the decision to the exact durable authorization target such as PR/revision evidence.
- [ ] **RED** Add tests proving repository-authorized Explore continues to use its independent repository authority path and does not require or manufacture Human approval.
- [ ] **GREEN** Replace duplicated actor-only Human checks with the shared predicate only at Human-reserved consumers, and make each consumer provide its governed durable `decision_ref` anchor while preserving repository-authorized Explore semantics.
- [ ] **REFACTOR/VERIFY** Confirm no role authority, Reviewer independence, merge gate, or workflow DAG changes were introduced; run full gates.

Trace: proposal item 5; spec Human-reserved consumer, decision-reference, and repository-authorized Explore scenarios; design D4.

## Slice 4 — Preserve `intake:approved` semantics and migration

- [ ] **RED** Add tests proving `intake:approved` remains distinct from `human:approved`, its snapshot alone is insufficient Human proof, and Scheduled roles still cannot manufacture either reserved capability.
- [ ] **RED** Add migration tests proving completed historical workflows remain terminal while still-pending Human-reserved evidence consumed after activation must satisfy the stronger predicate including the current expected `decision_ref`.
- [ ] **GREEN** Update shared governance/role/skill wording and any label fixtures needed for the exact two-capability relationship, decision-reference presentation, and prospective activation boundary.
- [ ] **REFACTOR/VERIFY** Ensure historical evidence is not retroactively reopened and no approval token/database/cursor is introduced; run full gates.

Trace: proposal items 3, 6; spec intake/migration scenarios; design D2/D5.

## Final verification

- [ ] Verify proposal → spec → design → tasks forward traceability and tasks → design → spec → proposal reverse traceability.
- [ ] Verify the MODIFIED canonical requirement preserves the still-applicable existing `Non-Human actor answers a Human-required question` and `Notification metadata exists` scenarios.
- [ ] Verify `human:approved` is explicit normative meaning and not delegated to Executor implementation choice.
- [ ] Verify the approval event → intended Human decision comment binding is fully specified through exact `decision_ref`, stable candidate/event ordering, replacement-comment semantics, and fail-closed missing/ambiguous evidence.
- [ ] Verify Ruff `S`, prompt-security regression framework, cryptography, external approval services, generic IAM, and unrelated workflow redesign remain out of scope.
- [ ] Run strict OpenSpec validation for the exact handoff revision and record checkout-identity evidence before Reviewer handoff.
