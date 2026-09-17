# Spec-driven OpenSpec semantic adapter

This progressive-disclosure reference carries material `spec-driven` OpenSpec semantics that Scheduled roles would otherwise receive from unavailable OpenSpec CLI schema/status/instructions surfaces. It is not runtime routing authority, a capability specification, or a second workflow DAG.

Load this reference only from the default branch after the Change that introduced it is merged. Until then, it is implementation/review input only.

## Provenance and supported baseline

- Configured repository schema: `spec-driven`.
- Represented upstream source: `Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020`.
- Represented schema source: `schemas/spec-driven/schema.yaml`.
- Qualified executable OpenSpec baseline: `@fission-ai/openspec@1.9.0`.

The upstream commit/path above is immutable provenance. Do not substitute mutable upstream `main`, model memory, or a different schema. If the configured schema or a material represented semantic contract no longer matches this baseline, fail closed until a governed reassessment updates this reference. Executable-version upgrade/compatibility work remains separate from this semantic adapter.

## Artifact dependency and readiness contract

The represented artifact graph is:

```text
proposal
├─> specs
└─> design

specs + design
    └─> tasks

tasks
    └─> apply
```

- `proposal` has no artifact prerequisite.
- `specs` and `design` each require `proposal`.
- `tasks` requires both `specs` and `design`.
- Apply requires `tasks` and tracks `tasks.md`.
- Proposal capability declarations bind the specs phase: listed new/modified capabilities require corresponding delta specs.
- A zero-delta Change is valid only through the explicit `skip_specs: true` path when no spec-level behavior changes.

This graph describes OpenSpec artifact readiness only. `agents/AGENTS.md` remains the sole Scheduled runtime workflow/routing authority.

## Project, config, and artifact rules

For the artifact/action being governed, consume the materially applicable default-branch `openspec/config.yaml` project context and artifact-specific rules. Specs additionally consume applicable canonical `openspec/specs/*` state. Design consumes approved behavioral context and must not defer a question that would change specs, chosen approach, or task breakdown. Tasks consume approved specs/design and are implementation steps, not a source of new normative behavior.

A required applicable config/context rule that cannot be reconstructed is a fail-closed blocker. Scheduled roles must not omit a rule merely because upstream would normally inject it through CLI instructions.

## Delta-authoring contract

### ADDED

- Use complete new requirement blocks only.
- Every requirement has normative text and at least one `#### Scenario:`.
- An ADDED requirement identifier must not already exist canonically.

### MODIFIED

- Identify the canonical requirement by the exact existing header after whitespace normalization, using case-sensitive comparison.
- Copy the entire canonical requirement block before editing.
- Preserve every scenario and content item that remains applicable.
- Edit the copied block into the complete future requirement state.
- A partial MODIFIED block that unintentionally drops surviving scenarios/content is invalid.

### REMOVED

- Target an existing canonical requirement.
- Carry the configured removal reason and migration/transition treatment.
- Do not represent removal as a partial modification.

### RENAMED

- Use exact `FROM` / `TO` requirement identifiers.
- Rename alone changes identity only.
- Rename plus behavior change requires the RENAMED mapping plus a complete MODIFIED block under the new identifier.

Duplicate, missing, ambiguous, or non-matching requirement identifiers fail closed.

## Canonicalization readiness

- A NEW capability delta contains exactly one non-empty `## Purpose` sufficient to seed the canonical spec.
- Missing, blank, duplicate, or generated-placeholder Purpose is a Propose/Review defect even if strict OpenSpec validation succeeds.
- For an existing capability, canonical Purpose remains authoritative during ordinary requirement delta authoring; do not manufacture a second delta Purpose.
- Before implementation, MODIFIED/REMOVED/RENAMED targets must exist canonically and ADDED targets must be genuinely new.
- Canonicalization must preserve untouched canonical requirements, scenarios, and content.

Archive validation remains deterministic defense-in-depth; a semantic invariant knowable during Propose/Review must not intentionally wait until Archive for first detection.

## Apply context contract

Executor consumes a closed approved context set:

1. approved proposal;
2. applicable delta specs;
3. approved design;
4. approved tasks;
5. canonical specs needed to interpret modified behavior; and
6. materially applicable default-branch `openspec/config.yaml` context/rules.

Executor works only approved pending tasks. Missing, contradictory, materially ambiguous, or baseline-inconsistent required context is a specification blocker and returns through the governed Lead question path.

Executor must not decide which upstream/config semantics count, invent omitted requirements, resolve material spec/design ambiguity, or reinterpret task meaning.

## Reassessment boundary

A later material schema/upstream semantic change requires deliberate reassessment against this immutable provenance. Until reassessed through the governed lifecycle, unsupported semantics fail closed. Do not reproduce every CLI output field, resolved-path mechanism, or interactive feature; this reference carries only material semantics consumed by the repository Scheduled lifecycle.