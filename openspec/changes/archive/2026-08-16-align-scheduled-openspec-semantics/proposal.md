# Change: Align Scheduled OpenSpec semantics

## Why

#40 found that the repository's deliberate Lead / Reviewer / Executor decomposition preserves most OpenSpec lifecycle intent, but the Scheduled-Agent environment cannot run the OpenSpec CLI surfaces that upstream workflows use to obtain schema status, artifact dependencies, artifact instructions, project context/rules, apply context files, and resolved paths.

That execution constraint currently leaves material semantics implicit. The demonstrated #29 regression is the concrete failure case: a NEW capability delta omitted `## Purpose`, strict OpenSpec validation passed, independent OpenSpec review passed, and the defect was discovered only when Archive automation attempted canonicalization. Archive correctly failed closed, but information already required at Propose time escaped both Lead authoring and independent review.

The repository should preserve its intentional role/stage separation while making the exact material `spec-driven` semantics that would normally arrive through unavailable CLI/schema instructions explicitly accessible to the responsible Scheduled roles. Executable OpenSpec version upgrade/compatibility work remains the separate required follow-up #63.

## What Changes

- Define one repository-accessible **spec-driven OpenSpec semantic adapter** bound to immutable upstream baseline `Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020` `schemas/spec-driven/schema.yaml`, rather than a vague “follow OpenSpec” contract or mutable upstream-main reference.
- Make the adapter contract decision-complete before implementation. It explicitly owns the represented artifact dependency/readiness graph (`proposal → specs`, `proposal → design`, `specs + design → tasks`, `tasks → Apply`), applicable `openspec/config.yaml` rule/context consumption, complete ADDED/MODIFIED/REMOVED/RENAMED delta semantics, NEW-capability Purpose/canonicalization readiness, Apply context, and fail-closed baseline/schema mismatch behavior.
- Require `Lead / propose-change` and materially revised `resolve-question` to consume that adapter together with `openspec/config.yaml`, applicable canonical specs, and declared authoritative source decisions before authoring/handoff. Required semantic information knowable before later canonicalization must not be deferred to Archive as the first detector.
- Require independent `Reviewer / review-openspec` to verify the same exact applicable semantic contract in addition to bidirectional traceability, including complete MODIFIED scenario/content preservation and rename+modify treatment, so an artifact set that cannot legally survive later Sync/Archive cannot PASS merely because trace shape and strict validation succeed.
- Require `Executor / implement-change` to consume the already-decided approved Apply context: proposal, applicable delta specs, design, tasks, canonical specs needed to interpret modified behavior, and materially applicable config context/rules. Missing/contradictory/ambiguous required context returns to Lead; Executor does not decide which upstream semantics count.
- Keep deterministic CLI mechanics and exact-head strict validation in repository automation. Preserve Lead / Reviewer / Executor separation, independent gates, fail-closed behavior, and the existing archive review/authorization lifecycle.
- Record immutable semantic source provenance plus observed executable baseline so later executable-version work (#63) can deterministically identify what must be re-reviewed when the pinned/schema/upstream baseline changes.

## Scope

Affected capability:
- `scheduled-agent-workflow`

In scope:
- Scheduled-Agent adaptation of material OpenSpec `spec-driven` artifact/instruction/context semantics unavailable through CLI in the Scheduled environment;
- exact represented dependency/readiness and delta-authoring semantics;
- Lead Propose/resolve authoring completeness;
- independent OpenSpec review completeness/coherence;
- Executor Apply-context consumption;
- shared progressive-disclosure reference and focused governance regression tests;
- durable semantic-baseline provenance for reassessment.

Out of scope:
- changing the executable OpenSpec package pin or proving a new executable compatibility baseline (tracked by #63);
- arbitrary/custom OpenSpec schema support while repository config remains `schema: spec-driven`;
- collapsing intentional Lead / Reviewer / Executor stages into upstream slash-command shapes;
- changing merge authorization, Archive PR ownership, native close, or final lifecycle gates;
- duplicating the OpenSpec CLI, maintaining generated schema state, or creating a second artifact/workflow engine.

## Durable source decisions

- Coordination Issue: #40.
- Human-approved semantic-adaptation principle: `issuecomment-5295389683`.
- Demonstrated #29 Purpose responsibility leak: `issuecomment-5296313818`.
- Decision-complete refreshed Explore result: `issuecomment-5303719185` plus post-#52/#58 reconstruction `issuecomment-5305800863`.
- Reviewer finding requiring decision-complete adapter semantics: `issuecomment-5308031658`.
- Current repository baseline at activation: `bcc4022dda94b097a4e610fba7b1428fb26df510`.
- Executable baseline remains `@fission-ai/openspec@1.3.1`.
- Immutable upstream semantic baseline for the represented `spec-driven` contract: commit `2826b8889e5223a9a8095d4428b60b56597e1020`, path `schemas/spec-driven/schema.yaml` (release context observed during Explore: `v1.9.0`).

## Deferred work

- #63 owns executable OpenSpec version evaluation/upgrade and re-evaluation of version-bound Archive compatibility guards.
- #52 owns Lead Explore/admission authority and is already complete; this change does not redefine that boundary.
