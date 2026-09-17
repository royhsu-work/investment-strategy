# Change: Consume current decision boundary before solution formation

## Why

Issue #207 identifies a procedural-consumption gap. Current-main evidence shows that the project already has one canonical project-wide proportionality and simplicity contract in `openspec/specs/repository-governance/spec.md`, a reference-only `agents/proportionality.md`, matching OpenSpec authoring rules in `openspec/config.yaml`, and an existing `review-openspec + FINDINGS -> resolve-question` workflow path. The gap is that the existing authority is not always consumed early enough to remove unnecessary solution mechanisms before solution formation.

The Human-approved outcome is to make the current decision boundary explicit before forming a solution, then apply the smallest-sufficient order:

```text
current Human-approved intent
+ applicable current canonical specs
+ current governance/config
+ current repository evidence
              |
      current decision boundary
              |
remove -> reuse -> consolidate -> existing ownership layer
              |
      only if still insufficient:
      addition justified by an exact current requirement,
      concrete safety property, or demonstrated failure mode
              |
       independent review
```

History remains a source for rationale, ambiguity, conflict, provenance, or forensic questions only when current truth is insufficient. It is not the normal decision database.

## What Changes

- Update `agents/skills/openspec-explore/SKILL.md` so Lead establishes and consumes the current decision boundary before forming solution candidates and does not perform unnecessary history archaeology when current truth is sufficient.
- Update `agents/skills/openspec-change/SKILL.md` so material Proposal, Design, Tasks, and semantic corrections use the same subtraction-first order and retain additions only with current evidence.
- Update `agents/skills/openspec-review/SKILL.md` so Reviewer independently reconstructs the same boundary and uses the existing `FINDINGS` result when retained complexity is unsupported or an existing owner/consolidation is sufficient.
- Remove only directly adjacent stale or duplicated wording in those touched Skills, including duplicate validation and worker-mutation prohibitions where present.
- Extend the existing `tests/test_skill_maintenance_guidance.py` regression surface to protect singular canonical ownership, reference-only projection, phase consumption, subtraction-first ordering, and absence of a competing authority.
- Keep the Change zero-delta at the capability-spec layer through `skip_specs: true`; no fresh current-main evidence presently shows a canonical requirement gap.

## Ownership and canonical disposition

`openspec/specs/repository-governance/spec.md` remains the single normative owner of project-wide proportionality and simplicity. `agents/proportionality.md` remains reference-only, and `openspec/config.yaml` remains the OpenSpec authoring-rule owner. The three Skills are action-specific procedural consumers; they do not copy or replace the canonical contract.

The executable Action model, existing result vocabulary, existing routing, and existing review disposition remain unchanged. The existing `review-openspec + FINDINGS -> resolve-question` path is reused.

## Scope boundaries

In scope:

- current decision-boundary reconstruction before solution formation in the three existing OpenSpec Skills;
- subtraction-first consumption of the existing proportionality authority;
- independent Reviewer symmetry using existing `FINDINGS`;
- directly adjacent duplicate or stale procedure wording in those touched Skills;
- focused regression coverage in the existing Skill-maintenance test surface.

Out of scope:

- any canonical capability-spec or `openspec/config.yaml` semantic expansion;
- new Action, Result, routing state, label, registry, history index, shared Skill, validator, policy compiler, or parallel test architecture;
- repository-wide Role/Workflow cleanup assigned to #218;
- changes to `agents/AGENTS.md`, `agents/workflow.md`, executable topology, implementation-review ownership, or #180 staged-delivery semantics;
- unrelated branch-protection, CI, control-plane, or portfolio behavior.

## Evidence and traceability

- Human-approved Issue #207 body and current Explore result comment.
- Current `main@b456fc8d42bae76338507783e340d00c994def04`.
- Current `openspec/specs/repository-governance/spec.md`, `agents/proportionality.md`, and `openspec/config.yaml`.
- Current executable Action model and workflow projection.
- Current Lead role, OpenSpec Skills, and `tests/test_skill_maintenance_guidance.py`.

## Acceptance boundary

The Change is complete only when current exact-head evidence shows:

1. Explore establishes the current decision boundary before solution candidates and uses current truth without normal history archaeology.
2. Change authoring applies remove, reuse, consolidate, and existing-owner checks before any addition, and every retained addition identifies the exact current requirement, safety property, or demonstrated failure mode.
3. Reviewer independently reconstructs the boundary and returns existing `FINDINGS` for unsupported retained complexity or sufficient existing ownership/consolidation.
4. The canonical proportionality owner remains singular and the reference layer remains reference-only.
5. No new Action, Result, routing state, registry, history authority, validator framework, or competing test architecture is introduced.
6. The focused and full existing quality gates, exact-revision OpenSpec validation, independent review, implementation merge, and required archive lifecycle all pass.
