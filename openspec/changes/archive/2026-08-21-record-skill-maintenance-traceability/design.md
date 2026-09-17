# Design: Record Skill maintenance traceability

Explore source: `issuecomment-5364628074`; material Human correction: `issuecomment-5364679558`.

## Decision 1: Reuse archived Change artifacts as the maintenance-history container

Material Skill Added / Modified / Removed traceability will live in the governed OpenSpec Change that authorizes the Skill change, rather than in a new global Skill changelog, tombstone directory, or per-Skill history database.

Rationale: archived OpenSpec already provides durable, immutable-by-governance historical provenance and naturally survives Skill removal. A separate registry would duplicate lifecycle/history ownership and create synchronization-by-convention risk.

The proposal carries a `Skill maintenance traceability` declaration because it is visible before implementation and review. Design/tasks may reference and operationalize it, but do not create competing copies with different meaning.

## Decision 2: Keep capability deltas and Skill maintenance declarations orthogonal

Capability specs answer what repository behavior is required. Skill maintenance traceability answers why a repository Skill artifact/responsibility changed. One capability requirement may map to multiple material Skill changes; no one-file-one-capability-delta convention is introduced.

Rationale: #105 showed that the capability-level `MODIFIED` workflow requirement was correct while the concrete Skill modifications still needed explicit maintenance explanation.

## Decision 3: Preserve `UPSTREAM.md` as a different provenance axis

For adopted/adapted Skills, `UPSTREAM.md` continues to represent immutable upstream provenance and current repository divergence from that baseline. It is reassessed only when the represented upstream/local divergence changes.

The Change maintenance declaration is chronological governed-change provenance. Repository-authored Skills therefore need no synthetic upstream file.

Rationale: collapsing these axes would either turn `UPSTREAM.md` into a chronological changelog or force nonexistent upstream provenance onto repository-authored Skills.

## Decision 4: Materiality is semantic/responsibility based, not file-touch based

A Skill maintenance declaration is required when a change materially affects responsibility, executable semantics, composition/loading behavior, trigger behavior, authority, or maintenance meaning. Formatting, wording, and reference-only changes are excluded when those meanings remain stable.

Rationale: file-touch rules produce noise and weaken reviewer attention; the demonstrated gap concerns maintainable responsibility provenance.

## Decision 5: Enforcement follows existing role separation

Lead owns the declaration as approved Change meaning through `openspec-change`. `Reviewer / review-openspec` verifies that declared Skill changes are justified and traceable from the approved scope. `Reviewer / review-implementation` compares the exact implementation head against the approved declaration and reports undeclared/differently classified material Skill changes.

Executor does not gain authority to revise the declaration or specification meaning. If implementation reveals that a materially different Skill set/responsibility change is required, the existing specification-blocker path returns to Lead.

Rationale: this keeps traceability enforceable without allowing implementation to self-authorize scope drift.

## Decision 6: Retrospective repair is bounded by an explicit historical window

Human correction `issuecomment-5364679558` supersedes the earlier #105-only repair. This Change retrospectively evaluates merged implementation Changes from #105 through the pre-#110 baseline and records material Skill modifications for #105/#106, #107/#109, #86/#114, #115/#117, and #112/#119. #80/#121 is explicitly excluded because it did not modify `agents/skills/*`.

The retrospective classification is based on source implementation diffs plus the source Change semantics. Historical archives remain immutable. `UPSTREAM.md` updates observed in the window remain their own upstream/current-local-divergence provenance and do not substitute for this chronological maintenance explanation.

Rationale: the bounded window repairs recent governed Skill maintenance consistently without turning #110 into an unbounded repository-history audit or falsely grandfathering material post-#105 changes.

## Validation strategy

Add focused regressions that exercise the trace contract as data/behavior rather than only searching for prose. At minimum cover:

1. two Skills mapped to one capability change are both accepted without duplicate capability deltas;
2. undeclared material Skill changes are rejected by review classification;
3. formatting/reference-only changes are non-material;
4. Added/Removed/decomposition declarations require responsibility/replacement information as applicable;
5. upstream-adapted and repository-authored Skills use distinct provenance paths;
6. the bounded retrospective window is reconstructable from #110 without modifying historical archives;
7. #80/#121 is represented as an evaluated exclusion rather than silently omitted.

Repository-level structure checks may verify that the mapped author/review Skills reference the canonical maintenance-trace contract, but semantic acceptance must not rely only on Markdown phrase presence.

## Trade-offs

Using each Change as the history container means maintainers reconstruct a Skill's full history across archived Changes rather than reading one per-Skill chronological ledger. That cost is acceptable because Git/OpenSpec history already indexes governed changes, while a per-Skill ledger would duplicate history, require special handling for removals, and add synchronization obligations unsupported by the demonstrated failure mode.