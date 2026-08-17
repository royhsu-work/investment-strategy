## ADDED Requirements

### Requirement: Executable OpenSpec baseline is pinned and compatibility-qualified

The repository MUST use one repository-owned executable OpenSpec version baseline for all governed OpenSpec validation and archive automation. Validation and archive workflows MUST consume the same pinned baseline and MUST NOT independently float or silently diverge to different OpenSpec versions.

A baseline upgrade MUST be qualified against deterministic repository compatibility evidence for the OpenSpec behaviors on which current governance depends, including complete `MODIFIED` requirement scenario preservation, strict spec-driven validation behavior, archive/canonicalization behavior, and exact canonical Purpose preservation. A newer upstream release MUST NOT weaken repository Human authority, role separation, exact-revision validation, fail-closed archive semantics, or validated archive-branch ownership.

Repository-side semantic safeguards that enforce an independently required repository contract MUST remain in force even when a newer OpenSpec release adds overlapping validation. A compatibility guard MAY be removed only when the repository contract it protects is either no longer required or is deterministically enforced at an equal-or-stronger authoritative boundary without leaving a coverage gap.

Executable baseline provenance MUST identify the selected OpenSpec release/version and immutable upstream source revision sufficiently for a later compatibility reassessment. The executable version MAY differ from immutable semantic-adapter provenance only when the adapter explicitly records that distinction and its represented material semantics remain compatible.

#### Scenario: Validation and archive use the qualified baseline

- GIVEN the repository has selected a qualified executable OpenSpec baseline
- WHEN OpenSpec validation and archive automation install or invoke OpenSpec
- THEN both consume the same repository-owned pinned version
- AND neither workflow silently floats to an unqualified newer version

#### Scenario: Modified requirement would lose a surviving scenario

- GIVEN a canonical requirement has multiple still-applicable scenarios
- AND a proposed `MODIFIED` delta omits one surviving scenario
- WHEN the qualified compatibility/validation boundary evaluates the change
- THEN the incomplete modified requirement is rejected before successful archive canonicalization
- AND the repository does not rely on archive-time data loss to discover the defect

#### Scenario: Archive canonicalization changes Purpose unexpectedly

- GIVEN an approved change has an exact canonical Purpose contract
- WHEN the selected OpenSpec baseline archives or canonicalizes the change
- THEN deterministic repository compatibility protection verifies the resulting Purpose contract
- AND an unknown, blank, generated-placeholder, duplicated, or otherwise unexpected Purpose transformation fails closed before a validated archive branch is published

#### Scenario: Upstream adds overlapping safety validation

- GIVEN a newer OpenSpec release natively detects a failure class also covered by repository semantic safeguards
- WHEN the repository evaluates whether to simplify its compatibility layer
- THEN overlapping validation alone does not automatically delete the repository safeguard
- AND removal is allowed only when deterministic evidence proves the required repository safety property remains fully enforced without that guard

#### Scenario: Future OpenSpec release becomes available

- GIVEN upstream publishes a release newer than the repository's qualified baseline
- WHEN repository automation runs without an approved compatibility change
- THEN it continues using the currently qualified pinned baseline
- AND adopting the newer release requires a deliberate compatibility reassessment with refreshed immutable provenance
