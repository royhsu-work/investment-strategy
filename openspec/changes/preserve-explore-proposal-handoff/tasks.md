# Tasks: Preserve Explore-to-Propose semantic handoff

## Slice 1 — Encode the handoff invariant

- [ ] RED: add focused regressions proving an Explore-originated Change must carry an exact durable `PROPOSAL_READY` Explore-result reference and direct Propose does not require one.
- [ ] GREEN: update shared Scheduled-Agent governance and canonical workflow contract with the minimum Explore → Propose preservation invariant.
- [ ] REFACTOR: remove duplicate local wording and keep one authoritative owner per rule category.
- [ ] VERIFY: run focused tests, full quality gates, and strict OpenSpec validation before marking the slice complete.

Trace: proposal `What Changes`; requirement `Explore-originated Propose preserves the exact decision-complete Explore result`; design `Decision`, `Ownership`, `Human boundary`.

## Slice 2 — Make Propose preserve and Reviewer verify

- [ ] RED: add focused mapped-Skill regressions where an internally consistent target contradicts its referenced Explore result and must fail review, plus a faithful formalization case.
- [ ] GREEN: update `openspec-change` to record/dereference the exact durable Explore result and preserve its material boundary.
- [ ] GREEN: update `openspec-review` to verify preservation before ordinary bidirectional traceability.
- [ ] GREEN: keep direct-to-Propose unchanged and keep the spec-driven semantic adapter outside workflow-handoff ownership.
- [ ] REFACTOR: keep mapped Skills action-local and reference shared governance rather than duplicating the full invariant.
- [ ] VERIFY: run focused tests, full quality gates, and strict OpenSpec validation before marking the slice complete.

Trace: proposal `What Changes`; capability scenarios `Faithful Explore formalization proceeds to ordinary OpenSpec review`, `Internally consistent OpenSpec artifacts contradict the Explore decision`, `Direct Propose does not fabricate an Explore reference`; design `Preservation semantics`, `Alternatives rejected`.

## Completion

- [ ] Confirm Proposal / Specs / Design / Tasks are bidirectionally traceable and declare current source Explore #86 issuecomment-5352138330.
- [ ] Run strict OpenSpec validation for the exact handoff revision and resolve all findings.
- [ ] Do not mark implementation tasks complete during Propose; Executor owns implementation completion evidence after independent OpenSpec PASS.
