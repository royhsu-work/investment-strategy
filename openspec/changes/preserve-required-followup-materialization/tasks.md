# Tasks: Preserve required follow-up materialization across Explore and Propose

Traceability baseline: #158 `issuecomment-5422771356` → proposal → `scheduled-agent-workflow` producer/preservation requirement → design decisions → slices below.

## Slice 1 — Make Explore produce a routing-complete required follow-up

- [ ] RED: extend `tests/test_required_followup_materialization.py` with focused regressions proving `openspec-explore` distinguishes ordinary deferred/optional/non-goal work from a semantically required separate follow-up, records the required decision in the durable Explore result, and does not complete Propose successor routing until the exact source-linked tracker is freshly observed as `Change: unset + agent:lead + action:explore-change`.
- [ ] RED: cover interrupted/replayed Explore materialization: a uniquely matching incomplete tracker is repaired idempotently, an already-complete tracker is reused, and multiple/ambiguous matches fail closed rather than creating a duplicate.
- [ ] GREEN: modify `agents/skills/openspec-explore/SKILL.md` only as needed to operationalize the existing global required-follow-up contract at decision-complete Explore, sequencing durable `ACTION_RESULT` source identity before tracker materialization and successor routing.
- [ ] REFACTOR: keep the global classification/materialization algorithm owned by canonical/shared workflow semantics; keep `openspec-explore` action-local and avoid a new status, tracker registry, workflow DAG, or generic issue-generation rule.
- [ ] VERIFY: run the focused materialization tests and repository Skill quick validation for `openspec-explore`; do not mark the slice complete until the exact implementation revision passes its required checks.

Trace: proposal `What Changes`; requirement scenarios `Explore materializes a newly required separate follow-up before successor routing`, `Interrupted Explore materialization resumes from the same durable decision`, `Ordinary deferred wording creates no tracker obligation`; design `Explore producer behavior`, `Materialization mechanics`.

## Slice 2 — Preserve Explore classification through Propose

- [ ] RED: extend `tests/test_explore_proposal_handoff.py` with a faithful case where exact Explore result E carries a required separate follow-up and Propose preserves E plus its tracker while keeping the later work outside current implementation scope.
- [ ] RED: add negative cases proving Propose rejects/delays readiness when a required tracker is missing or ambiguously duplicated, may repair only one uniquely matching incomplete tracker under current source authority, and does not upgrade ordinary deferred wording into a required obligation.
- [ ] GREEN: modify the `propose-change` procedure in `agents/skills/openspec-change/SKILL.md` to preserve required-follow-up classification from the exact durable Explore result and fresh-verify/repair the routing-complete tracker before OpenSpec readiness; leave its existing `resolve-question` materialization algorithm semantically unchanged.
- [ ] REFACTOR: reuse the existing Explore-result handoff and required-follow-up contracts rather than duplicating Reviewer/lifecycle rules or creating a second classification vocabulary.
- [ ] VERIFY: run the focused Explore→Propose tests and repository Skill quick validation for `openspec-change`; do not mark the slice complete until the exact implementation revision passes its required checks.

Trace: proposal `What Changes`; requirement scenarios `Propose preserves a required follow-up while keeping it outside current implementation scope`, `Propose repairs only a unique incomplete required tracker`; design `Propose preservation behavior`, `Ownership`.

## Slice 3 — Verify bounded contract and maintenance traceability

- [ ] RED/GREEN: add or adjust only the minimum canonical/governance regression assertions needed to prove the new producer/preservation requirement is externally represented without copying the existing global required-follow-up algorithm into multiple owners.
- [ ] GREEN: preserve the declared Skill-maintenance scope exactly: `openspec-explore` = Modified, `openspec-change` = Modified; no Skill Added/Removed and no responsibility transfer to Reviewer or lifecycle Skills.
- [ ] REFACTOR: keep #140 and #155 as historical classification evidence only; do not create retrospective trackers or rewrite their durable history.
- [ ] VERIFY: run focused tests, full Python quality gates, and exact-head strict OpenSpec validation; verify no workflow topology, WIP/cardinality, Human-authority, direct-Propose admission, runtime deployment, Reviewer ownership, or lifecycle ownership change was introduced.

## Completion

- [ ] Confirm exact Explore baseline #158 `issuecomment-5422771356` is identified in proposal/readiness evidence and all material decided scope/constraints/exclusions/direction are preserved.
- [ ] Confirm Proposal / Specs / Design / Tasks are bidirectionally traceable and the two prospective Skill modifications are explicitly declared with rationale/responsibility treatment.
- [ ] Confirm the requirement preserves the existing semantic distinction among ordinary deferred/optional/non-goal, required separate follow-up, and already-tracked separate work without using presentation words as classification tokens.
- [ ] Confirm no retrospective tracker is created for #140 or #155.
- [ ] Run final exact-head Python quality gates and strict OpenSpec validation before Executor reports `READY` and hands off to `Reviewer / review-implementation`.

No implementation task is complete at Propose time; Executor owns RED/GREEN/REFACTOR/VERIFY completion evidence after independent OpenSpec PASS.
