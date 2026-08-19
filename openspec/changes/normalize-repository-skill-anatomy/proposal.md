# Change: Normalize repository Skill anatomy and provenance

## Why

#85's decision-complete review used the corrected default-branch Anthropic `skill-creator` adopted by #84 and found one systemic first-step defect: every repository-authored mapped `agents/skills/*/SKILL.md` lacks the standard Skill YAML frontmatter (`name`, `description`). The same review also found that local Skills adapted from upstream OpenSpec behavior do not yet carry reproducible Skill-local provenance/delta accounting, making intentional repository role/stage decomposition hard to distinguish from accidental semantic drift during later OpenSpec upgrades.

This change fixes that structural and maintenance gap without changing Scheduled-Agent routing, role authority, action semantics, Human authority, or OpenSpec lifecycle behavior.

## What Changes

- Add standard YAML frontmatter with stable `name` and trigger-oriented `description` to the eight repository-authored mapped Skills while preserving their existing procedure bodies and authority boundaries.
- Add Skill-local immutable upstream provenance/delta ledgers to repository Skills that materially derive from or adapt actual OpenSpec Skills at `Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020`.
- Record intentional Add / Delete-or-omit / Modify responsibility differences with concrete repository reasons, including role/stage decomposition and Scheduled-Agent environment constraints.
- Treat repository-original Skills as repository-original; do not manufacture an upstream mapping merely to make the inventory uniform.
- Add focused regression coverage that validates mapped Skill anatomy and applicable provenance completeness without asserting or changing action behavior.
- Keep conversion of root `agents/skills/openspec-semantic-adapter.md` into a reusable Skill, #83 Human-authority provenance extraction, #80 workflow-topology ownership, and #86 Explore→Propose handoff analysis as separate follow-up work.

## Capabilities

### Modified

- `repository-governance`
  - require repository-authored Skills to use standard Skill anatomy;
  - require reproducible immutable provenance and explicit local delta rationale when a real upstream Skill is adapted;
  - forbid fabricated upstream provenance for repository-original Skills.

## Scope Boundaries

In scope:
- YAML frontmatter for the eight mapped repository-authored Skills;
- Skill-local upstream provenance/delta ledgers for actual OpenSpec-derived/adapted Skills;
- focused structural/provenance regression tests;
- repository-governance delta requirements.

Out of scope:
- changing any role/action routing or workflow transition;
- changing Human authority, merge acceptance, review gates, archive mechanics, or implementation semantics;
- converting `openspec-semantic-adapter.md` into a Skill;
- implementing #83 or #80;
- beginning #86 before #85 completes;
- broad repository Skill refactoring beyond anatomy/provenance normalization.

## Evidence and Intent

- #85 issuecomment-5337695282 records the complete post-#84 Skill inventory and `PROPOSAL_READY` conclusion.
- The authoritative default-branch `skill-creator` defines a Skill as a directory with `SKILL.md`, YAML frontmatter containing required `name` and `description`, and optional progressively disclosed bundled resources.
- Current mapped repository Skills are coherent action procedures but all eight start directly with Markdown headings and therefore fail that standard anatomy.
- OpenSpec upstream `skills/` at immutable revision `2826b8889e5223a9a8095d4428b60b56597e1020` supplies concrete baselines for Explore, Propose, Apply, Verify, and Archive responsibilities; repository role/stage decomposition intentionally redistributes some of those responsibilities.
- Existing root `openspec-semantic-adapter.md` is a separate reusable-capability finding and is deliberately not folded into this first structural correction.

## Traceability

- Standard mapped-Skill anatomy → repository-governance ADDED requirement `Repository Skills use standard anatomy and explicit provenance` → Design D1 → Task Slice 1.
- OpenSpec responsibility provenance/delta accounting → same requirement → Design D2 → Task Slice 2.
- Repository-original no-fabricated-mapping rule → same requirement → Design D2 → Task Slice 2.
- Behavior preservation and structural regression → same requirement → Design D3 → Task Slice 3.

Refs #85
