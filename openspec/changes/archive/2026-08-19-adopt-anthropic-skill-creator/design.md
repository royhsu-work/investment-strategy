# Design: Adopt pinned Anthropic skill-creator

## Context

#84 requires the repository to correct the earlier #35 outcome by adopting Anthropic's original `skill-creator` package rather than treating the repository-authored `skill-maintenance.md` as an equivalent substitute.

Lead inspected `anthropics/skills` at immutable commit `0a64e398ec6bb34a494f0c347e8ccae53a862f8e`; the complete `skills/skill-creator/` subtree is `3cf9a8db32597ba3e24b584a3d696f4e11c7d7b6`. That package contains `SKILL.md`, `LICENSE.txt`, specialized agent instructions, eval/review assets, schema reference, and executable scripts. The pinned `SKILL.md` directly references those resources, and scripts have internal dependencies, so selective extraction would change the upstream capability surface without evidence that the omitted behavior is irrelevant to the requested baseline.

The repository also has real local authority constraints that Anthropic's general-purpose Skill does not own. The design must therefore preserve the upstream package as provenance-identifiable baseline while composing local governance through existing authority layers.

## Requirement traceability

| Requirement | Design decisions |
| --- | --- |
| `Repository Skill maintenance uses a pinned standard skill-creator baseline` | D1, D2, D4 |
| `Repository-specific Skill governance remains explicit and separate from the vendored baseline` | D2, D4 |
| `Governed Skill work composes skill-creator without changing action authority` | D3, D4 |

## D1 — Vendor the complete immutable upstream package, not a reconstructed subset

Copy the complete pinned upstream `skills/skill-creator/` tree into:

```text
agents/skills/skill-creator/
```

All files originating from upstream at the pinned tree are copied without repository-style rewriting during initial adoption. This includes `LICENSE.txt` and every agent/asset/eval-viewer/reference/script file in the pinned tree.

The baseline identity is:

```text
repository: anthropics/skills
path:       skills/skill-creator/
commit:     0a64e398ec6bb34a494f0c347e8ccae53a862f8e
subtree:    3cf9a8db32597ba3e24b584a3d696f4e11c7d7b6
```

Why full-tree vendoring is the smallest sufficient design: the requested capability is the *original Skill*, whose documented workflow includes bundled evaluation, comparison, review, schema, validation, packaging, and trigger-optimization components. Removing individual resources would establish a locally narrowed fork before the repository has even adopted the requested baseline.

Mutable upstream `main` is never a runtime dependency. A future update repeats the governed comparison/adoption lifecycle against another immutable revision.

## D2 — Keep local additions explicit; move repository-only maintenance guidance under the adopted Skill

Add a repository-owned provenance file, `agents/skills/skill-creator/UPSTREAM.md`, containing:

- upstream repository/path;
- pinned commit and subtree SHA;
- the exact upstream file inventory or a deterministic manifest sufficient for verification;
- upstream patch set (initially `none`);
- repository-authored additions and their purpose.

Do not edit upstream `SKILL.md` merely to record repository integration metadata.

The current `agents/skills/skill-maintenance.md` contains useful repository-specific constraints rather than the original Skill itself: authority ownership boundaries, progressive-disclosure integration guidance, and the rule that mutable external references cannot directly become Scheduled runtime authority. Preserve only that material as a clearly local resource such as:

```text
agents/skills/skill-creator/references/repository-governance.md
```

Record it as a local addition in `UPSTREAM.md`, then remove root `agents/skills/skill-maintenance.md`. This prevents the root file from remaining a competing pseudo-skill while keeping repository-specific rules separate from unchanged upstream content.

The local resource is specialization only. Normative shared runtime and role authority remain in their existing owners; the resource references those owners rather than creating parallel definitions.

## D3 — Compose skill-creator conditionally from existing action Skills

`skill-creator` is reusable capability guidance, not a workflow action. Do not add `action:skill-creator`, a new role, or dispatcher mapping.

Add a short conditional-loading contract to the existing mapped action Skills whose work can materially operate on repository Skills:

- `openspec-explore`: load when the admitted investigation materially concerns Skill structure/creation/maintenance/review;
- `openspec-change`: load when proposal/resolve work materially specifies a Skill change;
- `openspec-review`: load when the reviewed OpenSpec target materially concerns repository Skills;
- `implementation`: load when approved tasks create/modify Skill artifacts;
- `implementation-review`: load when the reviewed implementation materially creates/modifies Skill artifacts.

Each loading site remains small: it points to the default-branch `agents/skills/skill-creator/SKILL.md` and, for repository-specific integration/authority, its local governance reference. It does not restate the imported Skill body.

The mapped action always wins on action authority, routing, allowed repository mutation, Human escalation, and result semantics. System/runtime constraints likewise remain higher authority. This means Claude-specific optional mechanics are not transformed into unconditional repository dependencies. The pinned upstream Skill itself already documents environment-dependent behavior such as no-subagent/browser/headless paths and conditional CLI-based description optimization.

## D4 — Verify provenance/composition deterministically; do not rebuild the upstream eval system in CI

Focused repository regression should verify the adoption boundary rather than execute every optional Anthropic workflow feature.

Required verification:

1. every pinned upstream file is present at the expected repository path;
2. copied upstream content matches the recorded immutable baseline (using deterministic hashes/content fixtures or an equivalent checked-in manifest);
3. `LICENSE.txt` is present and matches the pinned upstream copy;
4. `UPSTREAM.md` declares all repository-local additions and any upstream patches; initial patch set is empty;
5. root `agents/skills/skill-maintenance.md` no longer exists after its material local guidance is preserved;
6. upstream `quick_validate.py` succeeds on the adopted Skill in the repository Python environment; PyYAML is already a repository dependency;
7. affected mapped action Skills contain the intended conditional composition contract without adding dispatcher mappings;
8. default-branch governance/role ownership is not duplicated into the imported upstream files.

Do not make `claude -p`, a browser server, subagents, or trigger-optimization runs a normal CI requirement. Those are optional capabilities of the adopted Skill, not necessary evidence that the repository copied the pinned package correctly.

## Alternatives considered

### Copy only `SKILL.md`

Rejected. The Skill itself refers to bundled agents, schemas, assets/viewer, and scripts. Copying only the entry point creates dangling instructions and does not adopt the original capability surface.

### Copy only files currently executable in the Scheduled ChatGPT environment

Rejected. That would define the baseline by today's runner limitations instead of the Human-requested original Skill. The package already treats several facilities as optional/environment-dependent; preserving them does not make them mandatory workflow dependencies.

### Rewrite upstream `SKILL.md` to use repository terminology and governance

Rejected for initial adoption. It obscures provenance and repeats the #35 failure mode of substituting a repository-designed interpretation for the original Skill. Repository-specific constraints can be composed as an explicitly local reference while higher-level governance remains authoritative.

### Keep root `skill-maintenance.md` alongside the imported Skill unchanged

Rejected. Its broad name/location would preserve two apparent Skill-maintenance baselines. Its material repository-only content has a natural local specialization location under the adopted reusable Skill.

### Add a dedicated dispatcher action for skill-creator

Rejected. Reusable Skills can be composed by action Skills; no independent workflow transition or role authority is required.

### Use a git submodule or fetch upstream at runtime

Rejected. Runtime external mutability conflicts with current repository-governance requirements and weakens deterministic default-branch authority. A pinned vendored snapshot is simpler to reconstruct and review.

## Risks and mitigations

- **Risk: local edits drift from upstream while still appearing original.** Mitigation: explicit provenance manifest plus deterministic upstream-file integrity regression.
- **Risk: upstream package adds tools unavailable in the Scheduled environment.** Mitigation: optional mechanics remain conditional; mapped action and system constraints remain authoritative; no unsupported facility becomes CI/runtime prerequisite solely due to vendoring.
- **Risk: local governance gets mixed into upstream content.** Mitigation: upstream files remain unchanged; local resource and provenance declarations are separate.
- **Risk: imported Skill duplicates role/runtime governance.** Mitigation: local composition reference points back to existing owners, and affected action Skills only load the reusable procedure conditionally.
- **Risk: scope expands into repository-wide Skill refactoring.** Mitigation: #85 remains the explicit dependent follow-up and does not begin until #84 completes on default branch.

## Deferred / related work

- #85: after #84 lifecycle completion, load the adopted default-branch `skill-creator` and review the complete `agents/skills/` namespace.
- #83: Human-authority provenance capability classification remains input to #85; it is not implemented by this change.
- #80: workflow-document ownership remains unrelated unless later post-#85 evidence establishes an interaction.
