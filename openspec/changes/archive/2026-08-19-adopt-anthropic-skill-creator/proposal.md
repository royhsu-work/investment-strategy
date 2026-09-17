# Change: Adopt pinned Anthropic skill-creator

## Why

The repository currently uses `agents/skills/skill-maintenance.md` as general Skill-maintenance guidance, but Human direction for #84 is to adopt Anthropic's original `skill-creator` Skill itself as the repository baseline. The original upstream artifact is a complete Skill package with bundled agents, references, assets, evaluator/viewer code, and scripts; reducing it to a repository-authored prose substitute loses the upstream capability surface and makes future Skill review depend on locally reconstructed conventions.

This change adopts an immutable upstream package snapshot into default-branch repository authority while keeping repository-specific governance separate, minimal, and traceable.

## What Changes

- Vendor the complete `anthropics/skills` `skills/skill-creator/` subtree pinned at commit `0a64e398ec6bb34a494f0c347e8ccae53a862f8e` and subtree `3cf9a8db32597ba3e24b584a3d696f4e11c7d7b6` into `agents/skills/skill-creator/`.
- Preserve copied upstream files unchanged as the initial baseline, including the upstream Apache-2.0 `LICENSE.txt` and all bundled resources needed by the advertised Skill workflow.
- Add repository-owned provenance metadata that records the immutable source revision and explicitly distinguishes upstream files from local additions/patches; initial upstream patch set is empty.
- Move the material repository-specific authority/integration guidance currently held in root `agents/skills/skill-maintenance.md` into an explicitly local progressive-disclosure resource under the adopted Skill, then remove the root pseudo-skill document.
- Make existing governed actions conditionally compose the default-branch `skill-creator` when their work investigates, specifies, implements, or reviews repository Skill artifacts. Composition does not add a new `action:*` dispatcher route and does not transfer mapped-action or role authority to the reusable Skill.
- Add focused regression coverage for package completeness/provenance, license presence, local-vs-upstream separation, Skill validation, and conditional composition contracts.
- Keep #85 blocked from substantive repository-wide Skill review until #84 is authoritative on default branch and its lifecycle is complete.

## Capabilities

### Modified

- `repository-governance`
  - establish the pinned default-branch `skill-creator` package as the reusable Skill-authoring/maintenance baseline;
  - preserve immutable upstream provenance and explicit local deviations;
  - compose the reusable Skill through existing governed actions without changing dispatcher or role authority.

## Scope Boundaries

In scope:
- the complete pinned upstream `skills/skill-creator/` package;
- local provenance and repository-governance resource placement under `agents/skills/skill-creator/`;
- removal of root `agents/skills/skill-maintenance.md` after its material repository-only guidance is preserved locally;
- bounded conditional loading changes in existing action Skills that actually investigate/design/author/modify/review repository Skills;
- repository-governance delta requirements and focused tests/checks.

Out of scope:
- reviewing or refactoring the other repository Skills; #85 owns that work after this change completes;
- rewriting Anthropic `skill-creator` for repository style;
- automatically tracking mutable upstream `main`;
- requiring Claude CLI description optimization, browser UI, or subagents as ordinary repository CI/runtime prerequisites;
- adding a new dispatcher action, role, plugin registry, Skill dependency graph, or second workflow DAG;
- resolving #83 or #80 as part of this change.

## Evidence and Intent

- #84 Human direction explicitly requires adopting the original Anthropic Skill before #85 reviews other Skills.
- Decision-complete Explore evidence is persisted in #84 issuecomment-5334135830.
- Inspected immutable upstream source is `anthropics/skills@0a64e398ec6bb34a494f0c347e8ccae53a862f8e`; the `skills/skill-creator/` subtree is `3cf9a8db32597ba3e24b584a3d696f4e11c7d7b6`.
- Upstream `SKILL.md` references the bundled grader/comparator/analyzer, schema reference, eval-review/viewer assets, benchmark tooling, validation, packaging, and description-trigger evaluation tooling; package scripts also reference each other. The complete pinned subtree is therefore the smallest evidence-supported baseline that preserves the original advertised capability surface.
- The upstream package includes Apache License 2.0 in `LICENSE.txt`; the vendored copy preserves it.
- Repository `pyproject.toml` already includes PyYAML required by upstream `quick_validate.py`; Claude CLI-specific features remain conditional rather than becoming a repository prerequisite.

## Traceability

- Complete immutable upstream adoption → repository-governance ADDED requirement `Repository Skill maintenance uses a pinned standard skill-creator baseline` → Design D1/D2 → Task Slice 1.
- Local governance separation and root pseudo-skill removal → ADDED requirement `Repository-specific Skill governance remains explicit and separate from the vendored baseline` → Design D2 → Task Slice 2.
- Conditional composition without routing authority → ADDED requirement `Governed Skill work composes skill-creator without changing action authority` → Design D3 → Task Slice 3.
- Provenance/composition regression and #85 sequencing → all requirements → Design D4 → Task Slice 4.

Refs #84
