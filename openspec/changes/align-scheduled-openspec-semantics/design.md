# Design: Align Scheduled OpenSpec semantics

## Context

The repository intentionally decomposes broader OpenSpec responsibilities across Lead authoring, independent Reviewer gates, Executor implementation, lifecycle authorization, and deterministic repository automation. #40 found that this decomposition is policy to preserve, not drift.

The material gap is environmental: Scheduled roles cannot execute the OpenSpec CLI, while upstream OpenSpec workflows obtain semantic inputs dynamically from schema/status/instructions surfaces. The repository is configured specifically as `schema: spec-driven`, so the smallest correction is not general schema execution; it is an accessible, reviewable semantic adapter for the configured schema and the lifecycle responsibilities actually consumed by Scheduled roles.

The #29 NEW-capability Purpose failure proves that relying on strict validation plus role familiarity is insufficient. Archive's Purpose guard detected the omission safely, but only after Propose, independent OpenSpec review, implementation, implementation review, authorization, and implementation merge had already occurred.

Reviewer finding `issuecomment-5308031658` identified the remaining design defect in the first proposal revision: the adapter categories were named, but the normative content inside those categories was still left to Executor. This revision therefore fixes the contract itself before implementation.

## Decision 1: Use one progressive-disclosure semantic adapter, not duplicated skill prose

Create one shared reference under the existing Agent/Skill ownership hierarchy for material `spec-driven` OpenSpec semantics that Scheduled roles would otherwise receive from unavailable CLI instructions.

The adapter is procedural semantic input, not runtime routing authority and not a new canonical capability specification. Ownership remains:

- `openspec/config.yaml`: repository OpenSpec schema selection plus project context and artifact rules;
- `openspec/specs/*`: approved capability requirements;
- `agents/AGENTS.md`: Scheduled runtime governance and role separation;
- role/skills: who consumes OpenSpec semantics and when;
- shared semantic adapter: exact represented `spec-driven` artifact/dependency/context/delta/apply semantics needed by multiple Scheduled actions because the CLI surface is unavailable.

Skills load the adapter progressively only for OpenSpec actions that need it. This avoids copying the same semantic contract into Propose, Review, and Implementation while also avoiding a generated registry or second DAG.

## Decision 2: Bind the adapter to one immutable upstream semantic baseline and enumerate the contract

The represented upstream semantic source for this Change is immutable:

- OpenSpec commit: `2826b8889e5223a9a8095d4428b60b56597e1020`
- schema source: `schemas/spec-driven/schema.yaml`
- repository executable baseline observed when adopted: `@fission-ai/openspec@1.3.1`

The adapter does not say “follow OpenSpec generally” or “use current upstream main.” It records the material contract actually consumed by this repository:

### 2.1 Artifact dependency/readiness

The represented graph is:

```text
proposal
├─> specs
└─> design

specs + design
    └─> tasks

tasks
    └─> apply
```

`proposal` has no artifact prerequisite. `specs` and `design` each require `proposal`. `tasks` requires both `specs` and `design`. Apply requires `tasks` and tracks `tasks.md`.

Proposal capability declarations bind the specs phase: listed new/modified capabilities require corresponding delta specs. A zero-delta Change is valid only through the explicit `skip_specs: true` path when no spec-level behavior changes. This is artifact readiness, not Scheduled routing; `AGENTS.md` remains the runtime workflow owner.

### 2.2 Project/config/artifact rules

Lead and Reviewer consume applicable default-branch `openspec/config.yaml` project context and artifact-specific rules at the artifact they govern. Specs additionally consume applicable canonical specs. Design consumes the approved behavioral context and must not defer a question that would change specs, chosen approach, or task breakdown. Tasks consume approved specs/design and remain implementation steps, not a source of new normative behavior.

A required applicable config/context rule that cannot be reconstructed is a fail-closed blocker; Scheduled roles do not silently omit it because upstream would normally have injected it through CLI instructions.

### 2.3 Delta-authoring semantics

The adapter makes these rules explicit so Executor never chooses them:

- **ADDED**: complete new requirement blocks only; every requirement has normative text and at least one `#### Scenario:`. An ADDED identifier must not already exist canonically.
- **MODIFIED**: identify the canonical requirement by the exact existing header after whitespace normalization with case-sensitive comparison; copy the entire requirement block, preserve every scenario/content that remains applicable, then edit to the complete future state. A partial MODIFIED block that unintentionally drops surviving scenarios/content is invalid.
- **REMOVED**: identify an existing canonical requirement and carry the configured removal reason plus migration/transition treatment. Removal is not represented as a partial modification.
- **RENAMED**: use exact `FROM`/`TO` requirement identifiers. Rename alone changes identity only. Rename plus behavior change requires the RENAMED mapping plus a complete MODIFIED block under the new identifier.
- duplicate, missing, ambiguous, or non-matching target identifiers fail closed.

### 2.4 Canonicalization readiness

For a NEW capability, the delta has exactly one non-empty `## Purpose` sufficient to seed the canonical spec. Missing, blank, or generated-placeholder Purpose is a Propose/Review defect even if strict validation happens to pass.

For an existing capability, current canonical Purpose remains authoritative during ordinary requirement delta authoring; the adapter does not manufacture a second delta Purpose.

Before implementation, Lead and Reviewer verify that MODIFIED/REMOVED/RENAMED targets exist canonically and ADDED targets are genuinely new. Canonicalization must preserve untouched canonical requirements/scenarios/content. Archive checks may remain deterministic defense-in-depth, but no knowable Propose-time invariant intentionally waits until Archive for first detection.

### 2.5 Apply context

Executor receives a closed set of required context: approved proposal, applicable delta specs, design, tasks, canonical specs needed to interpret modified behavior, and materially applicable default-branch `openspec/config.yaml` context/rules.

Executor works only approved pending tasks. Missing, contradictory, or materially ambiguous required context returns through the existing specification-question path. Executor never decides which upstream/config rules “count,” invents omitted requirements, resolves material spec/design ambiguity, or rewrites task meaning.

### 2.6 Provenance and reassessment

The adapter records the immutable upstream commit/path for each represented semantic family and the executable baseline observed at adoption. A later material schema/upstream semantic change requires deliberate reassessment. Until that happens, unsupported semantics fail closed rather than falling back to model memory or current upstream `main`.

This design deliberately does not reproduce every CLI output field, resolved path mechanism, or interactive feature. Only material semantics consumed by the repository Scheduled lifecycle are represented.

## Decision 3: Propose owns semantic authoring completeness before independent review

`Lead / propose-change` and materially revised `resolve-question` load the semantic adapter and consume:

1. current default-branch `openspec/config.yaml`;
2. applicable canonical capability specs;
3. current durable Human/repository authority and declared source decisions;
4. the exact adapter dependency/config/delta/canonicalization semantics above.

Before handoff, Lead ensures required artifact information is semantically sufficient for the later lifecycle, not merely structurally present. Lead still does not perform the independent Reviewer PASS. Exact-head strict validation remains an additional mechanical gate, not proof of semantic completeness.

## Decision 4: Reviewer independently verifies lifecycle-survivable OpenSpec semantics

`Reviewer / review-openspec` consumes the same applicable adapter independently. Reverse-first plus forward traceability remains mandatory, but PASS additionally requires the reviewed artifact set to satisfy the exact represented dependency, config-rule, delta-authoring, and canonicalization-readiness semantics needed by later Apply/Sync/Archive.

The review catches NEW-capability missing Purpose, partial MODIFIED content, invalid rename/change combinations, missing canonical targets, and other adapter-defined semantic defects before implementation even when strict OpenSpec validation itself accepts the change. Reviewer verifies the shared semantic invariant, not Archive-script implementation details.

## Decision 5: Executor consumes approved apply context without acquiring specification authority

`Executor / implement-change` loads the adapter's Apply section and consumes only the already-decided context listed in Decision 2.5. If required context is missing, contradictory, or materially ambiguous, Executor uses the existing specification-question path back to Lead.

The adapter does not authorize Executor to infer missing requirements, choose which OpenSpec semantics matter, select new product scope, or rewrite task meaning. RED → GREEN → REFACTOR → VERIFY and verified-slice checkpoint semantics remain unchanged.

## Decision 6: Version provenance makes semantic reassessment explicit

The adapter records the upstream semantic baseline from which its represented responsibilities were derived and the repository executable baseline observed when adopted. This is compatibility provenance, not a claim that executable `1.3.1` implements every upstream `v1.9.0` semantic.

#63 remains responsible for changing the executable pin and reassessing version-bound compatibility guards. A later pin/schema/upstream semantic change compares against this adapter and updates it only when material represented semantics change.

## Traceability

- Proposal `Why` / `What Changes` → delta `Scheduled roles preserve material OpenSpec semantics when CLI instructions are unavailable` → Decisions 1/2/6 → Tasks 1/2.
- Proposal Propose/Review correction → delta `OpenSpec authoring and independent review prevent knowable canonicalization omissions` → Decisions 2/3/4 → Tasks 2/3.
- Proposal Apply correction → delta `Executor consumes complete approved OpenSpec apply context` → Decisions 2/5 → Tasks 2/4.

## Blast radius

Expected implementation surfaces:

- one shared progressive-disclosure OpenSpec semantic reference under `agents/skills/` containing the already-decided contract above;
- `agents/skills/openspec-change/SKILL.md`;
- `agents/skills/openspec-review/SKILL.md`;
- `agents/skills/implementation/SKILL.md`;
- minimal shared-governance/role references only if needed to identify adapter consumption without duplicating content;
- focused tests for dependency/readiness, delta semantics, NEW-capability Purpose, partial MODIFIED preservation, rename+modify behavior, fail-closed unsupported semantics, and Apply context;
- canonical `scheduled-agent-workflow` after archive.

No implementation change is required to Strategy Engine or market-data behavior.

## Compatibility

- Existing approved/terminal workflows are not retroactively invalidated solely because they predate this adapter.
- Current active work first consumed after activation follows current default-branch semantics.
- The executable OpenSpec pin remains unchanged by this Change.
- Existing Archive validation and Purpose defenses remain unchanged until #63 evaluates them against an upgraded executable baseline; this Change makes them defense-in-depth rather than the first intended detector for knowable authoring omissions.

## Rejected alternatives

### Teach each role a separate copy of OpenSpec semantics
Rejected because repeated normative-looking copies would recreate the responsibility drift #40 is meant to remove.

### Require Scheduled roles to execute OpenSpec CLI directly
Rejected because the execution environment does not provide that capability; environment limitation must be adapted rather than wished away.

### Implement a generic OpenSpec schema engine in Agent governance
Rejected because repository config is currently `spec-driven` and no requirement justifies duplicating OpenSpec's engine or generated state.

### Treat successful strict validation as semantic completeness
Rejected by the #29 Purpose regression: strict validation passed while a later required canonicalization invariant was already unsatisfied.

### Bind to mutable upstream main
Rejected because Reviewer/Executor completeness would change nondeterministically as upstream moves. The adapter is bound to an immutable source baseline and changes only through repository review.

### Wait for #63 and solve both tracks together
Rejected because executable compatibility/version evaluation and no-CLI Scheduled semantic consumption are distinct responsibilities. The two-track split keeps both Changes bounded and independently reviewable.
