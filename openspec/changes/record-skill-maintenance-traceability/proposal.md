# Change: Record Skill maintenance traceability

Explore source: `issuecomment-5364628074` on coordination Issue #110.

## Why

Repository Skill maintenance currently has two useful traceability layers, but neither completely answers why a material repository Skill change occurred. OpenSpec capability deltas explain normative capability behavior, while `UPSTREAM.md` explains current local divergence from an immutable external Skill baseline. #105 demonstrated the remaining gap: two existing Skills were materially modified and the capability delta was correct, yet the Human still had to ask separately whether those Skill changes had corresponding Added / Modified / Removed treatment.

The repository needs a small durable Skill-maintenance trace contract that survives archive and removal without introducing a parallel Skill changelog database or forcing one capability delta per changed file.

## What changes

- Require each governed OpenSpec Change that materially adds, modifies, or removes repository Skills to include a bounded Skill-maintenance trace declaration in its own durable Change artifacts.
- Classify each materially affected Skill as `Added`, `Modified`, or `Removed` and record the approved source/reference, responsibility boundary before/after or preserved responsibility, rationale, and replacement/supersession target when applicable.
- Exempt wording/format-only edits that do not alter Skill responsibility, semantics, composition, trigger behavior, authority, or maintenance meaning.
- Keep capability deltas independent: one capability requirement may legitimately drive multiple Skill modifications without fabricating one capability delta per Skill file.
- Keep immutable-upstream provenance independent: `UPSTREAM.md` continues to describe upstream baseline/current-local divergence for adopted Skills and is not repurposed as a chronological maintenance log.
- Make Lead authoring and Reviewer semantic/implementation gates enforce the declaration for material Skill changes.
- Add an explicit retrospective #105 backfill in this Change instead of rewriting #105's archived history.

## Affected capabilities

- `repository-governance` — add repository-wide Skill-maintenance traceability requirements and review behavior.

## Scope boundaries

In scope: Skill Added / Modified / Removed maintenance traceability, materiality threshold, ownership across Lead/Reviewer action procedures, interaction with upstream provenance, #105 retrospective repair, and focused regressions.

Out of scope: one OpenSpec capability delta per Skill file, a global Skill changelog/database, rewriting archived #105 artifacts, retroactively auditing every historical Skill change, changing Skill runtime authority, changing workflow topology, or changing product/strategy behavior.

## Skill maintenance traceability

### Prospective changes in this Change

| Skill | Class | Approved source | Responsibility treatment | Rationale |
| --- | --- | --- | --- | --- |
| `agents/skills/openspec-change/SKILL.md` | Modified | #110 / this Change | Preserve Lead proposal/specification authority; add authoring/readiness procedure for the Skill-maintenance trace declaration | Lead must make material Skill scope explicit before implementation/review rather than leaving it to file-diff archaeology |
| `agents/skills/openspec-review/SKILL.md` | Modified | #110 / this Change | Preserve independent OpenSpec semantic-review authority; add reverse-first/forward verification of declared material Skill changes | Internally consistent capability traceability must not hide unexplained Skill responsibility drift |
| `agents/skills/implementation-review/SKILL.md` | Modified | #110 / this Change | Preserve exact-head implementation-review authority; compare material Skill file changes with the approved maintenance declaration | Reviewer must catch undeclared or differently classified Skill changes at the exact implementation head |

No Skill is Added or Removed by this Change. `skill-creator` remains reusable guidance and is not made a second normative owner.

### Retrospective #105 repair

This later Change records the missing Skill-maintenance explanation without editing the archived `enforce-dispatch-cardinality-preflight` Change:

| Historical Skill | Class | Historical source | Responsibility treatment | Rationale |
| --- | --- | --- | --- | --- |
| `agents/skills/openspec-explore/SKILL.md` | Modified | #105 / PR #106 / archive PR #108; Human question `issuecomment-5346223908` | Preserved `Lead / explore-change` ownership while adding action-entry consumption/defense-in-depth of the shared cardinality preflight | Operationalized the already-approved repository-wide WIP/cardinality contract at Explore entry; no new Skill/capability was added |
| `agents/skills/openspec-change/SKILL.md` | Modified | #105 / PR #106 / archive PR #108; Human question `issuecomment-5346223908` | Preserved Propose/Resolve ownership while strengthening pre/post activation consumption of the shared cardinality preflight | Operationalized the same approved shared contract at Propose activation; no Skill was added or removed |

This retrospective record is explicitly later provenance. It does not assert that #105 originally contained this new maintenance contract.

## Deferred work

None required by this Change. Historical Skill changes other than the explicit #105 repair are not retroactively audited merely because this prospective invariant is introduced.