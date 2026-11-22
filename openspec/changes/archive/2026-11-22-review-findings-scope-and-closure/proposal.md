# Change: Constrain review findings to approved scope and observable closure

## Why

Issue #458 records a Human-approved procedure correction for two related causes of review/implementation drift. A Reviewer can promote a suggested implementation into a blocking requirement without identifying which approved invariant and present-stage gate actually fail. An Executor can then implement the suggestion without independently verifying the finding or its authority. The result is repeated repair, new requirements introduced by review prose, and failure to converge on the originally approved outcome.

This Change preserves the approved scope from #458 and its accepted `Explore / PROPOSAL_READY` result (Issue comment 7076432623). The four cases in #458 are acceptance examples, not permission to rewrite #435 or waive safety gates.

## What Changes

- In the existing `Reviewer / review-implementation` Skill, require every **blocking** Finding to identify the approved requirement or invariant, evidence at the exact review revision, the currently blocked stage/gate, and an observable closure condition. Separate the verified defect from any recommended implementation. Test an alternative solution or counterevidence against that same closure condition; enhancements that are not approved obligations remain advisory.
- In the existing `Executor / implement-change` Skill, independently check and where appropriate reproduce each Finding before editing. Correct substantiated defects only within approved scope using the smallest sufficient fix; verify with the original counterexample or equivalent evidence. Record disagreement/counterevidence for independent Reviewer re-review. Escalate a material change to approved meaning or scope via the existing `SPEC_BLOCKER → Lead / resolve-question` path.
- Retain the current independent Reviewer's PASS/FINDINGS authority and every existing exact-head, validation, no-replay, Human-authority, and mutation gate. Neither a Reviewer suggestion nor Executor agreement changes the approved contract.

## Scope and non-goals

Only `agents/skills/implementation-review/SKILL.md` and `agents/skills/implementation/SKILL.md` are materially modified by the eventual implementation. No new Role, Action, Result, state label, classifier, handoff, gate, review workflow, recovery machinery, or shared normative owner is introduced. No change to #435's pending Recovery Exit, original UNKNOWN Effect, routing, or acceptance obligations is authorized.

The open Draft PR #459 is an unreviewed implementation candidate. It does not replace this Change, authorize early Skill edits, or inherit any semantic review result.

## Impact and evidence

- Capability: `repository-governance` (one capability delta for both action-local procedures).
- Human scope and four acceptance examples: Issue #458; bounded research comment 7064623141; accepted `PROPOSAL_READY` comment 7076432623.
- Related review evidence: PR #455 accepted-preimage contradiction, PR #453 RED-stage review, Issue #435 historical UNKNOWN/no-replay, and alternative-fix counterevidence.
- Delivery: strict exact-revision OpenSpec validation and independent `review-openspec` before implementation; then Executor verification, independent exact-head implementation review and authorized merge.

## Material repository Skill declarations

1. **Modified** — `agents/skills/implementation-review/SKILL.md`. Approved source: Issue #458 Human scope, carried through accepted Explore comment 7076432623. Responsibility before: independent exact-head implementation review. Responsibility after: **preserved**, with an explicit stage-specific, approved-invariant, exact-evidence, observable-closure Finding procedure. Rationale: prevent review suggestions from silently expanding scope. Replacement/supersession: none.
2. **Modified** — `agents/skills/implementation/SKILL.md`. Approved source: the same Issue #458 Human scope and accepted Explore. Responsibility before: approved bounded Executor implementation and VERIFY. Responsibility after: **preserved**, with independent Finding verification, smallest in-scope correction, counterexample-based proof and Reviewer re-adjudication. Rationale: prevent unverified Reviewer suggestions from becoming self-authorized implementation. Replacement/supersession: none.

These repository-authored mapped Skills have no claimed external upstream equivalent. The two declarations are distinct maintenance entries but correspond to one capability delta, not two artificial normative capabilities.

Refs #458
