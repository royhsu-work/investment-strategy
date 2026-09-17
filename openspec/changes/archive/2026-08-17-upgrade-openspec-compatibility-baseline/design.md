# Design: Upgrade executable OpenSpec compatibility baseline

## Context

Repository OpenSpec validation and archive workflows independently hard-code `@fission-ai/openspec@1.3.1`. The repository has since accumulated compatibility defenses because pinned CLI behavior did not fully preserve or validate all semantics required by this project, especially complete `MODIFIED` requirement scenario preservation and exact Purpose canonicalization.

Upstream OpenSpec `v1.9.0` (`2826b8889e5223a9a8095d4428b60b56597e1020`) directly improves several relevant behaviors, including authoring-time scenario safety, strict spec-driven task numbering, honest root resolution, faithful spec rebuilds, and archived-task validation. The upgrade must therefore be treated as a compatibility migration rather than a simple version-string edit.

## Requirements trace

- R1 `Executable OpenSpec baseline is pinned and compatibility-qualified`
  - D1 single executable-version SSOT
  - D2 compatibility regression matrix
  - D3 retain independently required semantic guards
  - D4 update executable/provenance references without changing runtime governance

## Decision 1: one executable-version SSOT

Introduce one small repository-owned version source consumed by both `.github/workflows/openspec-validate.yml` and `.github/workflows/openspec-archive.yml`. The workflows may install the CLI differently only if they still resolve the exact same pinned value from that source.

This removes the current synchronization-by-convention between two hard-coded `1.3.1` strings without adding a package-management subsystem solely for one global CLI.

## Decision 2: qualify 1.9.0 with repository compatibility fixtures

Add deterministic compatibility coverage that executes the pinned CLI against temporary representative OpenSpec fixtures. The suite should cover only repository-relevant semantics:

1. incomplete `MODIFIED` requirement scenario preservation is rejected before archive;
2. a complete `MODIFIED` requirement preserves surviving scenarios through canonicalization;
3. new/existing capability Purpose behavior remains compatible with the repository's exact Purpose contract;
4. strict spec-driven task numbering/shape used by this repository remains accepted/rejected as expected;
5. archive produces the expected active-change removal/archive-history/canonical-spec shape.

The suite is compatibility evidence, not a replacement OpenSpec implementation and not a second schema engine.

## Decision 3: retain Purpose preservation as defense-in-depth

Keep `purpose-snapshot` / `purpose-preserve` after the upgrade. Even if 1.9.0 produces the correct Purpose for covered fixtures, the repository guard owns an explicit stronger invariant: approved exact Purpose must survive archive, generated placeholders are unacceptable, existing canonical Purpose must not drift, and unknown transformations fail loudly before archive-branch publication.

This guard is small, deterministic, and protects a repository-specific canonicalization boundary. The upgrade may simplify only obsolete version-specific branches proven unnecessary by compatibility tests; it must not remove the exact-Purpose postcondition itself.

## Decision 4: keep complete-MODIFIED authoring semantics

OpenSpec 1.9.0's native scenario counting is welcome earlier defense, but it does not replace the repository semantic-adapter rule requiring Lead/Reviewer to copy the complete canonical requirement block and preserve all still-applicable content. The adapter remains the Scheduled-Agent semantic contract; executable CLI validation is an additional machine check.

Update the adapter's recorded executable baseline from `1.3.1` to the qualified `1.9.0`, while retaining immutable represented-schema provenance at `2826b8889e5223a9a8095d4428b60b56597e1020` unless material semantic review proves otherwise.

## Decision 5: do not automatically adopt unrelated 1.9.0 features

`validate --archived`, new tool adapters, and other upstream features are not enabled merely because they exist. A feature may be used within this change only when it directly strengthens the compatibility qualification without changing repository lifecycle semantics. This prevents a version upgrade from becoming an opportunistic OpenSpec workflow redesign.

## Failure behavior

- Version source missing/malformed: workflow fails before invoking OpenSpec.
- Validation and archive resolve different versions: repository regression fails.
- Compatibility fixture fails under target version: upgrade is not ready; retain current baseline until corrected.
- Purpose transformation is unexpected: archive fails before pushing a validated archive branch.
- Upstream behavior is ambiguous relative to an approved repository invariant: retain the stricter repository guard and fail closed rather than guessing simplification.

## Deferred decisions

No required deferred decisions. Future OpenSpec versions are evaluated by a later bounded compatibility change using the same evidence model.
