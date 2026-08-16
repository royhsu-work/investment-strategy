# Design: Align Scheduled OpenSpec semantics

## Context

The repository intentionally decomposes broader OpenSpec responsibilities across Lead authoring, independent Reviewer gates, Executor implementation, lifecycle authorization, and deterministic repository automation. #40 found that this decomposition is policy to preserve, not drift.

The material gap is environmental: Scheduled roles cannot execute the OpenSpec CLI, while current upstream OpenSpec workflows obtain semantic inputs dynamically from `status` and `instructions` outputs. The repository is configured specifically as `schema: spec-driven`, so the smallest correction is not general schema execution; it is an accessible, reviewable semantic adapter for the configured schema and the lifecycle responsibilities actually consumed by Scheduled roles.

The #29 NEW-capability Purpose failure proves that relying on strict validation plus role familiarity is insufficient. Archive's Purpose guard detected the omission safely, but only after Propose, independent OpenSpec review, implementation, implementation review, authorization, and implementation merge had already occurred.

## Decision 1: Use one progressive-disclosure semantic adapter, not duplicated skill prose

Create one shared reference under the existing Agent/Skill ownership hierarchy for material `spec-driven` OpenSpec semantics that Scheduled roles would otherwise receive from unavailable CLI instructions.

The adapter is procedural semantic input, not runtime routing authority and not a new canonical capability specification. Ownership remains:

- `openspec/config.yaml`: repository OpenSpec schema selection plus project context and artifact rules;
- `openspec/specs/*`: approved capability requirements;
- `agents/AGENTS.md`: Scheduled runtime governance and role separation;
- role/skills: who consumes OpenSpec semantics and when;
- shared semantic adapter: the minimum spec-driven artifact/dependency/context/instruction semantics needed by multiple Scheduled actions because the CLI surface is unavailable.

Skills load the adapter progressively only for OpenSpec actions that need it. This avoids copying the same semantic contract into Propose, Review, and Implementation while also avoiding a generated registry or second DAG.

## Decision 2: The adapter is constrained to the configured `spec-driven` schema

The adapter describes only material semantics for the repository's current `schema: spec-driven` configuration, including:

- proposal → delta specs → design → tasks dependency/readiness relationships;
- applicable `openspec/config.yaml` project context and artifact-specific rules;
- complete delta-authoring expectations for ADDED/MODIFIED requirements and scenarios;
- NEW capability canonical information that is already knowable before archive, including one non-empty Purpose;
- apply context consisting of approved proposal/specs/design/tasks plus applicable project context/rules;
- fail-closed behavior when the configured schema or required semantic input cannot be represented by the current adapter.

It does not pretend to reproduce every OpenSpec schema, CLI output field, resolved path mechanism, or interactive feature. If repository configuration later changes away from the represented schema, Scheduled actions fail closed until the adapter is deliberately re-evaluated.

## Decision 3: Propose owns semantic authoring completeness before independent review

`Lead / propose-change` and materially revised `resolve-question` must load the semantic adapter and consume:

1. current default-branch `openspec/config.yaml`;
2. applicable canonical capability specs;
3. current durable Human/repository authority and declared source decisions;
4. the adapter's artifact dependency/context/instruction semantics.

Before handoff, Lead must ensure required artifact information is semantically sufficient for the later lifecycle, not merely structurally present. For a NEW capability this includes a non-empty Purpose because canonicalization requires it and that information is knowable during Propose.

Lead still does not perform the independent Reviewer PASS. Exact-head strict validation remains an additional mechanical gate, not proof of semantic completeness.

## Decision 4: Reviewer independently verifies lifecycle-survivable OpenSpec semantics

`Reviewer / review-openspec` consumes the same applicable adapter independently. Reverse-first plus forward traceability remains mandatory, but PASS additionally requires the reviewed artifact set to satisfy material spec-driven authoring/context semantics needed by later Apply/Sync/Archive.

The review must catch a NEW-capability missing-Purpose defect before implementation even when strict OpenSpec validation itself accepts the change. Reviewer does not copy Archive-script implementation details into a checklist; it verifies the semantic invariant represented by the shared adapter.

## Decision 5: Executor consumes approved apply context without acquiring specification authority

`Executor / implement-change` loads the adapter's apply-context section and consumes the approved Change artifacts plus applicable config context/rules. If required context is missing, contradictory, or materially ambiguous, Executor uses the existing specification-question path back to Lead.

The adapter does not authorize Executor to infer missing requirements, select new product scope, or rewrite task meaning. RED → GREEN → REFACTOR → VERIFY and verified-slice checkpoint semantics remain unchanged.

## Decision 6: Version provenance makes semantic reassessment explicit

The adapter records the upstream semantic baseline from which its represented responsibilities were derived and the repository executable baseline observed when adopted. This is compatibility provenance, not a claim that the executable pin already implements all upstream behavior.

#63 remains responsible for changing the executable pin and reassessing version-bound compatibility guards. A later pin/schema/upstream semantic change must compare against this adapter and update it only when material represented semantics changed.

## Traceability

- Proposal `Why` / `What Changes` → delta `Scheduled roles preserve material OpenSpec semantics when CLI instructions are unavailable` → Decisions 1, 2, and 6 → Tasks 1 and 2.
- Proposal Propose/Review correction → delta `OpenSpec authoring and independent review prevent knowable canonicalization omissions` → Decisions 3 and 4 → Tasks 2 and 3.
- Proposal Apply correction → delta `Executor consumes complete approved OpenSpec apply context` → Decision 5 → Tasks 2 and 4.

## Blast radius

Expected implementation surfaces:

- one shared progressive-disclosure OpenSpec semantic reference under `agents/skills/`;
- `agents/skills/openspec-change/SKILL.md`;
- `agents/skills/openspec-review/SKILL.md`;
- `agents/skills/implementation/SKILL.md`;
- minimal shared-governance/role references only if needed to identify the adapter consumption boundary without duplicating its content;
- focused tests proving NEW-capability Purpose is rejected before implementation and required adapter/context loading is preserved;
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

### Wait for #63 and solve both tracks together
Rejected because executable compatibility/version evaluation and no-CLI Scheduled semantic consumption are distinct responsibilities. The two-track split keeps both Changes bounded and independently reviewable.
