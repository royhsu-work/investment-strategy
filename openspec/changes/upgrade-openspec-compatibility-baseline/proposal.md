# Change: Upgrade executable OpenSpec compatibility baseline

## Why

The repository's executable OpenSpec automation still installs `@fission-ai/openspec@1.3.1` in both validation and archive workflows. That baseline predates upstream fixes for a failure class already observed in this repository: incomplete `MODIFIED` requirement scenario preservation could survive authoring/validation and fail only during archive/canonicalization.

OpenSpec `v1.9.0` is the current upstream release as of 2026-08-17 (`Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020`). Its release explicitly adds authoring-time scenario safety for `MODIFIED` requirements, stricter spec-driven task-number validation, safer root-resolution behavior, faithful spec rebuilds, and archived-task validation. The executable baseline should be upgraded deliberately rather than leaving repository compatibility guards permanently anchored to an obsolete CLI version.

## What Changes

- Move the executable OpenSpec baseline from `1.3.1` to verified `1.9.0` for repository validation and archive automation.
- Give the executable version one repository-owned source of truth consumed by both workflows so validation and archive cannot silently drift to different OpenSpec versions.
- Add deterministic compatibility regression coverage for the repository-specific behaviors that matter across the upgrade: complete `MODIFIED` scenario preservation, archive/canonicalization behavior, Purpose preservation, and strict spec-driven validation behavior.
- Keep repository semantic safety contracts that remain independently valuable. In particular, complete-MODIFIED authoring semantics and exact canonical Purpose preservation remain required defense-in-depth even where OpenSpec `1.9.0` now catches part of the same failure class earlier.
- Update version-bound compatibility provenance in the Scheduled-Agent semantic adapter without changing the adapter's represented schema semantics or runtime routing authority.

## Scope

In scope:
- executable OpenSpec version ownership and workflow installation;
- deterministic repository compatibility fixtures/tests needed to qualify `1.9.0`;
- existing Purpose snapshot/preserve compatibility guard classification and retained behavior;
- version/provenance references directly tied to the executable baseline.

Out of scope:
- changing Scheduled-Agent workflow/routing semantics;
- replacing the spec-driven semantic adapter with runtime CLI calls;
- adopting new OpenSpec product features unrelated to demonstrated repository compatibility needs;
- changing Human authority, review independence, exact-head gates, or archive-branch ownership;
- broad dependency/toolchain upgrades unrelated to OpenSpec.

## Affected capabilities

- `repository-governance`: add the executable OpenSpec compatibility-baseline contract.

## Deferred work

No required deferred follow-up is introduced by this change. Future OpenSpec releases require a new evidence-based compatibility reassessment rather than automatic floating-version adoption.

## Traceability

- Source coordination Issue: #63
- Required deferred source: #40 executable OpenSpec compatibility track
- Current repository baseline: `@fission-ai/openspec@1.3.1`
- Target upstream release: `v1.9.0`
- Immutable upstream provenance: `Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020`
- Canonical capability target: `openspec/specs/repository-governance/spec.md`
