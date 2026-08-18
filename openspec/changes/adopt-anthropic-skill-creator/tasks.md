# Tasks: Adopt pinned Anthropic skill-creator

## Slice 1 — Establish the complete immutable upstream Skill baseline

Trace: proposal complete immutable upstream adoption → `repository-governance` requirement `Repository Skill maintenance uses a pinned standard skill-creator baseline` → Design D1/D2.

- [ ] 1.1 RED — Add focused regression coverage/fixture expectations for the pinned `anthropics/skills@0a64e398ec6bb34a494f0c347e8ccae53a862f8e` `skills/skill-creator/` inventory, immutable provenance, upstream `LICENSE.txt`, and upstream-file integrity; run the focused tests and confirm they fail because the adopted package/provenance is absent, not because of test setup.
- [ ] 1.2 GREEN — Vendor the complete pinned upstream subtree to `agents/skills/skill-creator/` without modifying upstream-origin file content, including all agents/assets/eval-viewer/references/scripts and `LICENSE.txt`.
- [ ] 1.3 GREEN — Add `agents/skills/skill-creator/UPSTREAM.md` (or equivalently bounded provenance metadata) recording upstream repository/path, commit, subtree SHA, upstream inventory/integrity basis, initial upstream patch set `none`, and every repository-authored local addition.
- [ ] 1.4 REFACTOR — Remove any duplicated manifest/test data that is not needed to deterministically distinguish pinned upstream files from local additions while preserving immutable provenance and reviewability.
- [ ] 1.5 VERIFY — Run the focused provenance/package tests and the vendored upstream `quick_validate.py` against `agents/skills/skill-creator/`; verify success in the repository Python environment.

## Slice 2 — Preserve repository-only governance without a competing root pseudo-skill

Trace: proposal local governance separation → `repository-governance` requirement `Repository-specific Skill governance remains explicit and separate from the vendored baseline` → Design D2.

- [ ] 2.1 RED — Add focused regression assertions that repository-specific Skill governance is represented as an explicitly local adopted-Skill resource, is declared in provenance, and root `agents/skills/skill-maintenance.md` is no longer a parallel baseline; run them and confirm the current root pseudo-skill causes the intended RED failure.
- [ ] 2.2 GREEN — Move only the material repository-specific content from `agents/skills/skill-maintenance.md` into `agents/skills/skill-creator/references/repository-governance.md` (or an equivalently local progressive-disclosure resource) without editing Anthropic-origin files.
- [ ] 2.3 GREEN — Remove `agents/skills/skill-maintenance.md` after the material local guidance is preserved and provenance identifies the replacement as repository-authored.
- [ ] 2.4 REFACTOR — Keep the local resource narrowly specialized to repository integration/authority and replace duplicated normative runtime/role/action definitions with references to their existing owners.
- [ ] 2.5 VERIFY — Run the focused local-governance/provenance tests and confirm there is one adopted Skill baseline rather than two parallel Skill-maintenance authorities.

## Slice 3 — Compose the reusable Skill through existing governed actions

Trace: proposal conditional reuse without routing expansion → `repository-governance` requirement `Governed Skill work composes skill-creator without changing action authority` → Design D3.

- [ ] 3.1 RED — Add focused regression assertions for conditional `skill-creator` composition from the existing mapped action procedures that investigate/specify/review/implement repository Skill work, and assert no new `action:skill-creator` dispatcher mapping is introduced; run them and confirm the current Skills lack the required composition contract.
- [ ] 3.2 GREEN — Add bounded conditional loading to `openspec-explore`, `openspec-change`, `openspec-review`, `implementation`, and `implementation-review` for the default-branch `agents/skills/skill-creator/SKILL.md` when their current target materially concerns repository Skills.
- [ ] 3.3 GREEN — Where repository-specific integration/authority guidance is needed, make those mapped action procedures load the explicitly local adopted-Skill governance resource without restating its body.
- [ ] 3.4 REFACTOR — Ensure each mapped Skill retains only its action-specific loading condition/authority specialization; do not duplicate the Anthropic Skill body, global runtime invariants, role authority, or another dependency graph.
- [ ] 3.5 VERIFY — Run the focused composition tests and inspect default-branch-style routing mappings to prove reusable composition did not create a new role/action transition.

## Slice 4 — Close the adoption contract and protect #85 sequencing

Trace: all proposal intent → all three repository-governance requirements → Design D4.

- [ ] 4.1 RED — Add or extend regression coverage proving the pinned upstream package, license, explicit local additions/patch declarations, root pseudo-skill removal, and conditional composition must remain coherent together; include a regression that mutable upstream state is not needed to execute current default-branch Skill governance.
- [ ] 4.2 GREEN — Add the minimum durable repository documentation/linkage needed so later maintenance can identify #84's immutable upstream baseline and #85 can require the corrected default-branch `skill-creator` without using feature-branch artifacts or conversation memory.
- [ ] 4.3 REFACTOR — Review the #84 diff for accidental review/refactor of unrelated repository Skills; remove any #85 work or speculative framework/generalization from this change.
- [ ] 4.4 VERIFY — Run slice tests, full pytest regression suite, Ruff lint/format checks, mypy, and strict OpenSpec validation for `adopt-anthropic-skill-creator`; resolve all failures without weakening the approved contract.
- [ ] 4.5 VERIFY — Confirm #85 remains non-actionable until #84 reaches authoritative default-branch lifecycle completion, and that no #85 substantive Skill classification/refactor was performed in this change.
