# Upstream responsibility provenance

- Upstream repository: `Fission-AI/OpenSpec`
- Upstream Skill path: `skills/openspec-archive-change/`
- Upstream revision: `2826b8889e5223a9a8095d4428b60b56597e1020`
- Local Skill: `agents/skills/archive-review/SKILL.md`
- Relationship: decomposition of upstream Archive verification into an independent Reviewer gate.

## Relationship

The local Skill carries independent verification of the final Archive PR and the Lead-prepared lifecycle evidence. Archive creation, lifecycle preparation, merge, and terminal finalization remain with other repository owners.

## Added responsibilities

- Exact-current-head Archive PR review with revision-bound PASS/findings.
- Independent validation of Lead preparation evidence, canonical spec preservation, active-change removal, and unrelated-change absence.
- Explicit handoff to Executor merge or Lead correction owners.

Reason: repository separation of duties requires Archive acceptance to be independent from both lifecycle preparation and merge mutation.

Maintenance implication: preserve the Reviewer gate when adopting future upstream Archive checks; upstream checks may enrich this gate but do not transfer artifact mutation authority.

## Deleted or omitted responsibilities

- OpenSpec archive mutation is omitted and owned by repository automation.
- Archive PR creation and lifecycle-preparation judgment are omitted and owned by `Lead / finalize-change`.
- Merge/pre-close cleanup mutation is omitted and owned by `Executor / merge-pr`.
- Terminal completion reconstruction is omitted and owned by `Lead / finalize-archive`.

Reason: the upstream Archive responsibility is intentionally decomposed across automation and role-separated actions.

Maintenance implication: future upstream archive-and-verify behavior must be mapped across these owners instead of silently concentrating responsibility in Reviewer.

## Modified responsibilities

- Archive verification is an exact-head independent gate over an already prepared final Archive PR rather than part of the archive mutation itself.
- PASS is bound both to revision and materially reviewed preparation meaning.

Reason: at-least-once execution and lifecycle side effects require stale-review and changed-preparation protection.

Maintenance implication: evaluate upstream verification changes against the repository's revision/preparation binding when refreshing this ledger.