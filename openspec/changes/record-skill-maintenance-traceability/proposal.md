# Change: Record Skill maintenance traceability

Explore source: `issuecomment-5364628074` on coordination Issue #110, materially corrected by direct Human input `issuecomment-5364679558`.

## Why

Repository Skill maintenance currently has two useful traceability layers, but neither completely answers why a material repository Skill change occurred. OpenSpec capability deltas explain normative capability behavior, while `UPSTREAM.md` explains current local divergence from an immutable external Skill baseline. #105 demonstrated the remaining gap: two existing Skills were materially modified and the capability delta was correct, yet the Human still had to ask separately whether those Skill changes had corresponding Added / Modified / Removed treatment.

The repository needs a small durable Skill-maintenance trace contract that survives archive and removal without introducing a parallel Skill changelog database or forcing one capability delta per changed file. Human correction `issuecomment-5364679558` additionally requires the retrospective repair window to cover #105 and every subsequent merged implementation Change through the pre-#110 baseline, rather than silently grandfathering recent material Skill changes.

## What changes

- Require each governed OpenSpec Change that materially adds, modifies, or removes repository Skills to include a bounded Skill-maintenance trace declaration in its own durable Change artifacts.
- Classify each materially affected Skill as `Added`, `Modified`, or `Removed` and record the approved source/reference, responsibility boundary before/after or preserved responsibility, rationale, and replacement/supersession target when applicable.
- Exempt wording/format/reference-only edits that do not alter Skill responsibility, semantics, composition, trigger behavior, authority, or maintenance meaning.
- Keep capability deltas independent: one capability requirement may legitimately drive multiple Skill modifications without fabricating one capability delta per Skill file.
- Keep immutable-upstream provenance independent: `UPSTREAM.md` continues to describe upstream baseline/current-local divergence for adopted Skills and is not repurposed as a chronological maintenance log.
- Make Lead authoring and Reviewer semantic/implementation gates enforce the declaration for material Skill changes.
- Add an explicit retrospective backfill for #105 and subsequent merged implementation Changes through the pre-#110 baseline, without rewriting their archived history.

## Affected capabilities

- `repository-governance` — add repository-wide Skill-maintenance traceability requirements and review behavior.

## Scope boundaries

In scope: Skill Added / Modified / Removed maintenance traceability, materiality threshold, ownership across Lead/Reviewer action procedures, interaction with upstream provenance, bounded retrospective repair from #105 through the pre-#110 baseline, and focused regressions.

Out of scope: one OpenSpec capability delta per Skill file, a global Skill changelog/database, rewriting any historical archived Change, auditing history before #105, changing Skill runtime authority, changing workflow topology, or changing product/strategy behavior.

## Skill maintenance traceability

### Prospective changes in this Change

| Skill | Class | Approved source | Responsibility treatment | Rationale |
| --- | --- | --- | --- | --- |
| `agents/skills/openspec-change/SKILL.md` | Modified | #110 / this Change | Preserve Lead proposal/specification authority; add authoring/readiness procedure for the Skill-maintenance trace declaration | Lead must make material Skill scope explicit before implementation/review rather than leaving it to file-diff archaeology |
| `agents/skills/openspec-review/SKILL.md` | Modified | #110 / this Change | Preserve independent OpenSpec semantic-review authority; add reverse-first/forward verification of declared material Skill changes | Internally consistent capability traceability must not hide unexplained Skill responsibility drift |
| `agents/skills/implementation-review/SKILL.md` | Modified | #110 / this Change | Preserve exact-head implementation-review authority; compare material Skill file changes with the approved maintenance declaration | Reviewer must catch undeclared or differently classified Skill changes at the exact implementation head |

No Skill is Added or Removed by this Change. `skill-creator` remains reusable guidance and is not made a second normative owner.

### Retrospective repair window: #105 through pre-#110 baseline

This later Change records missing Skill-maintenance explanations without editing any earlier archived Change. Every listed entry is `Modified`; no Skill was Added or Removed by these source Changes.

| Historical source | Historical Skill(s) | Responsibility treatment | Rationale |
| --- | --- | --- | --- |
| #105 / PR #106 / archive PR #108; Human question `issuecomment-5346223908` | `openspec-explore`, `openspec-change` | Preserve their existing Lead action ownership while adding action-local consumption/defense-in-depth of the shared cardinality preflight | Operationalized the approved repository-wide WIP/cardinality contract at Explore entry and Propose activation |
| #107 / PR #109 | `archive-review`, `implementation-review`, `implementation`, `lifecycle-finalize`, `merge-pr`, `openspec-change`, `openspec-review` | Preserve each mapped action's authority while adding shared substantive-Human-input freshness/disposition consumption at the action boundary appropriate to that Skill | Prevent newer material direct-Human input from being silently ignored before consequential results, reviews, mutations, or handoffs; associated `UPSTREAM.md` edits remain upstream/local-divergence provenance rather than chronological maintenance history |
| #86 / PR #114 | `openspec-change`, `openspec-review` | Preserve Lead authoring and Reviewer review authority while making the exact Explore `PROPOSAL_READY` result a required semantic baseline for Explore-originated formalization/review | Prevent Explore→Propose semantic drift without creating a second admission or workflow path |
| #115 / PR #117 | `lifecycle-finalize`, `merge-pr` | Preserve lifecycle authorization and merge ownership while changing final Archive completion/merge procedure to keep the coordination Issue open through Archive merge and let Lead persist `LIFECYCLE_COMPLETE`, close, and re-observe | Align coordination-Issue closure with the formal terminal contract and remove Archive-PR closing-linkage ownership |
| #112 / PR #119 | `implementation-review`, `implementation`, `openspec-change` | Preserve existing action ownership while adding continuation-by-default / Invocation Exit Proof consumption to action-local wait/continuation boundaries | Prevent actions from yielding merely because an intermediate step completed or an exact run was initially absent/queued/in-progress |

#80 / PR #121 is explicitly evaluated and excluded from retrospective Skill entries because it did not modify `agents/skills/*`.

The retrospective record is explicitly later provenance. It does not assert that the source Changes originally contained this new maintenance contract, and it does not replace any applicable `UPSTREAM.md` provenance.

## Deferred work

None required by this Change. Historical Skill changes before #105 are not retroactively audited merely because this prospective invariant is introduced.