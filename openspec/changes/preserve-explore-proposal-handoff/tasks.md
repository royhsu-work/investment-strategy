# Tasks: Preserve Explore-to-Propose semantic handoff

## Slice 1 — Encode the handoff invariant

- [ ] RED: add focused governance/spec regressions proving an Explore-originated Change must carry an exact durable `PROPOSAL_READY` Explore-result reference and that direct Propose does not require one.
- [ ] GREEN: update the shared Scheduled-Agent governance and canonical workflow contract with the minimum Explore → Propose preservation invariant.
- [ ] REFACTOR: remove any duplicate local wording introduced by the change; keep one authoritative owner per rule category.
- [ ] VERIFY: run focused tests, full regression/quality gates, and strict OpenSpec validation before marking this slice complete.

Trace: proposal `What Changes`; capability requirement `Explore-originated Propose preserves the exact decision-complete Explore result`; design `Decision`, `Ownership`, `Human boundary`.

## Slice 2 — Make Propose preserve and Reviewer verify the Explore decision

- [ ] RED: add focused mapped-Skill regressions with an internally consistent OpenSpec target that contradicts its referenced Explore decision and must fail `review-openspec`, plus a faithful formalization case that remains reviewable without re-running Explore.
- [ ] GREEN: update `openspec-change` so Explore-originated Propose records/dereferences the exact durable Explore result and preserves its material boundary; update `openspec-review` so Reviewer verifies that preservation before ordinary bidirectional OpenSpec traceability.
- [ ] GREEN: keep direct-to-Propose behavior unchanged and keep `openspec-semantic-adapter.md` outside workflow-handoff ownership.
- [ ] REFACTOR: keep the mapped Skills focused on their local action responsibilities and use references rather than duplicating the complete Explore result or global workflow semantics.
- [ ] VERIFY: run focused tests, full regression/quality gates, and strict OpenSpec validation before marking this slice complete.

Trace: proposal `What Changes`; capability scenarios `Faithful Explore formalization proceeds to ordinary OpenSpec review`, `Internally consistent OpenSpec artifacts contradict the Explore decision`, `Direct Propose does not fabricate an Explore reference`; design `Preservation semantics`, `Alternatives rejected`.

## Completion

- [ ] Confirm Proposal / Specs / Design / Tasks remain bidirectionally traceable and the exact source Explore is declared as #86 issuecomment-5342834590.
- [ ] Run strict OpenSpec validation for the exact handoff revision and resolve all findings.
- [ ] Do not mark implementation tasks complete during Propose; Executor owns RED/GREEN/REFACTOR/VERIFY completion evidence after independent OpenSpec PASS.
