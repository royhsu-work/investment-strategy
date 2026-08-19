# Design: Normalize repository Skill anatomy and provenance

## Context

#85 inspected the complete post-#84 `agents/skills/` namespace using the newly authoritative Anthropic `skill-creator`. The mapped repository Skills are already separated by repository action ownership, but their package anatomy predates the corrected Skill model: all eight mapped repository-authored `SKILL.md` files lack YAML frontmatter. Several also carry intentional adaptations of upstream OpenSpec responsibilities without a reproducible Skill-local delta ledger.

This change is intentionally structural and maintenance-oriented. It must not alter the workflow semantics those Skills currently operationalize.

## D1 — Normalize mapped Skill anatomy without changing procedure meaning

Add YAML frontmatter to each mapped repository-authored Skill:

- `archive-review`
- `implementation-review`
- `implementation`
- `lifecycle-finalize`
- `merge-pr`
- `openspec-change`
- `openspec-explore`
- `openspec-review`

Each frontmatter contains at least:

```yaml
---
name: <stable-skill-name>
description: <bounded trigger-oriented description>
---
```

Descriptions identify the Skill's actual repository responsibility and when it is loaded. They do not add routing authority or generic triggering semantics beyond the existing action map in `agents/AGENTS.md`.

The existing Markdown body remains the procedure authority owned by that mapped Skill. Implementation should minimize body edits unrelated to metadata/provenance.

## D2 — Keep upstream provenance Skill-local and responsibility-based

For Skills with a real upstream OpenSpec responsibility baseline, add a Skill-local provenance resource such as `UPSTREAM.md`. The baseline for this change is:

`Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020`

At minimum classify these relationships:

- `openspec-explore` → `skills/openspec-explore/`
- `openspec-change` Propose responsibility → `skills/openspec-propose/`; repository `resolve-question` remains a local addition.
- `implementation` → `skills/openspec-apply-change/`.
- `implementation-review` → upstream verification responsibility (currently `skills/openspec-verify-change/`) adapted into an independent Reviewer gate.
- archive lifecycle decomposition (`lifecycle-finalize`, `archive-review`, `merge-pr`) → upstream `skills/openspec-archive-change/` responsibility deliberately split across repository automation and three role/action owners.

`openspec-review` is repository-original independent semantic review; do not invent a one-to-one upstream source.

Each applicable provenance resource records:

- upstream repository/path/revision;
- relationship: adaptation/composition/decomposition;
- Added responsibilities;
- Deleted/omitted upstream responsibilities and their local owner when applicable;
- Modified responsibilities;
- concrete reason and maintenance implication.

A category with no material difference may explicitly say `none`. The ledger is maintenance provenance, not runtime routing authority.

## D3 — Verify structure/provenance, not rewritten behavior

Add focused repository regression tests that mechanically enumerate the mapped Skill paths from the authoritative current set and verify:

1. each mapped repository-authored `SKILL.md` has valid YAML frontmatter with non-empty `name` and `description`;
2. names are unique and stable for the Skill package;
3. the provenance resources required by D2 identify the pinned upstream revision/path and explicit delta categories;
4. repository-original Skills are not forced to carry fabricated upstream provenance;
5. existing root `openspec-semantic-adapter.md` remains untouched by this change except for any references strictly necessary to keep tests green.

Where practical, reuse the adopted `skill-creator/scripts/quick_validate.py` as an additional structure check rather than implementing a competing Skill validator. Repository tests should focus on repository-specific invariants and provenance completeness.

## D4 — Preserve follow-up boundaries

The #85 Explore identified larger reusable-capability work, but it is intentionally excluded here:

- converting `openspec-semantic-adapter.md` into an independent reusable Skill;
- #83 Human-authority provenance procedure extraction;
- #80 workflow topology ownership;
- #86 Explore→Propose semantic handoff review.

Completing anatomy/provenance normalization first gives those later changes a consistent Skill package baseline without coupling their semantic decisions into this change.

## Trade-offs

### One shared provenance document vs Skill-local ledgers

A single root mapping would be shorter, but it would recreate a miscellaneous shared-document surface under `agents/skills/` and weaken progressive disclosure. Skill-local provenance keeps maintenance context with the capability being compared while allowing repository-original Skills to remain free of fake upstream metadata.

### Full upstream vendoring vs provenance-only comparison

Unlike `skill-creator`, these repository Skills are intentional semantic adaptations under different role/tool constraints. Vendoring the upstream Skills would create competing procedures and authority. This change therefore records immutable provenance and explicit deltas without replacing local mapped procedures.

## Traceability

- Requirement `Repository Skills use standard anatomy and explicit provenance` → D1/D2/D3.
- Scenario `Mapped repository Skill lacks standard frontmatter` → D1 + Slice 1 RED/GREEN.
- Scenario `Standard metadata preserves existing action authority` → D1/D3 + regression assertions.
- Upstream provenance/decomposition scenarios → D2 + Slice 2.
- Future refresh reproducibility → D2/D3 + Slice 3.
