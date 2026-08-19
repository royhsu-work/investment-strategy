## ADDED Requirements

### Requirement: Repository Skill maintenance uses a pinned standard skill-creator baseline

The repository SHALL provide `agents/skills/skill-creator/SKILL.md` as a reusable default-branch Skill-authoring and Skill-maintenance baseline derived from an immutable upstream Anthropic `skills/skill-creator/` revision. The adopted baseline SHALL preserve the complete upstream package resources required by the pinned Skill's advertised behavior rather than substituting a repository-authored prose approximation.

The repository MUST record immutable source provenance sufficient to reconstruct the adopted upstream repository, path, commit, and package tree. Upstream files copied into the baseline MUST remain distinguishable from repository-authored changes. The provenance record MUST contain an explicit Added / Deleted / Modified ledger relative to the pinned upstream subtree; every non-empty entry MUST state the concrete repository reason, and an empty category MUST be recorded as `none` rather than omitted. A later mutable upstream change MUST NOT alter repository runtime behavior until a governed repository change deliberately adopts a new immutable baseline.

The upstream license/attribution file included with the pinned package MUST be preserved with the adopted Skill.

#### Scenario: Scheduled Agent loads the adopted Skill after merge

- GIVEN the pinned `skill-creator` package has been reviewed and merged to the default branch
- WHEN a governed action needs the reusable Skill-authoring or Skill-maintenance procedure
- THEN it loads the repository-owned default-branch `agents/skills/skill-creator/SKILL.md`
- AND it does not fetch mutable upstream `main` as runtime authority

#### Scenario: Upstream package contains bundled behavior resources

- GIVEN the pinned upstream `skill-creator` uses bundled agents, references, assets, viewer code, or scripts for advertised behavior
- WHEN the repository establishes the adopted baseline
- THEN the required pinned resources are preserved under `agents/skills/skill-creator/`
- AND the repository does not silently narrow the baseline to only `SKILL.md`

#### Scenario: Upstream changes after adoption

- GIVEN Anthropic changes `skills/skill-creator/` after the repository's recorded pinned revision
- WHEN a Scheduled Agent executes repository work before a governed baseline-update change is merged
- THEN the repository continues using the currently pinned default-branch Skill package
- AND the mutable upstream change has no authority over current execution

#### Scenario: Vendored package differs from the pinned upstream subtree

- GIVEN the repository-owned Skill directory contains any file addition, upstream-file deletion, or upstream-file modification relative to the pinned subtree
- WHEN provenance for that adopted baseline is inspected
- THEN each Added / Deleted / Modified category is explicitly present
- AND every difference states why the repository requires it
- AND a category with no differences is recorded as `none`

#### Scenario: Adopted package is redistributed in the repository

- GIVEN the pinned upstream package includes its license or attribution artifact
- WHEN the package is vendored into `agents/skills/skill-creator/`
- THEN that artifact remains present with the vendored package
- AND repository provenance identifies the immutable upstream source

### Requirement: Repository-specific Skill governance remains explicit and separate from the vendored baseline

Repository-specific authority and integration guidance needed when using the adopted `skill-creator` SHALL remain clearly identified as repository-authored local content and SHALL NOT be represented as unchanged Anthropic upstream content. The repository SHALL preserve the existing authority ownership boundaries: shared Scheduled-Agent runtime invariants remain owned by `agents/AGENTS.md`, role mission/authority remains owned by `agents/roles/*`, and mapped actions retain ownership of their action-specific procedure and result semantics.

Repository-specific guidance MAY be a progressive-disclosure resource beneath `agents/skills/skill-creator/` when it is needed specifically while composing that reusable Skill. The repository MUST record such local additions in the Added ledger with their concrete repository reason. A root-level pseudo-skill document MUST NOT be retained solely as a duplicate general Skill-authoring baseline once its material repository-only guidance has a clear local owner under the adopted Skill.

#### Scenario: Local governance must accompany the upstream baseline

- GIVEN the repository has authority boundaries that are not part of Anthropic's upstream package
- WHEN a governed action composes `skill-creator` for repository work
- THEN the applicable repository-authored governance resource is loaded as a local specialization
- AND the upstream `SKILL.md` is not rewritten merely to embed those repository-specific rules

#### Scenario: Provenance is inspected later

- GIVEN a later maintainer needs to compare the vendored Skill with its upstream baseline
- WHEN they read the repository-owned provenance metadata
- THEN they can distinguish the pinned upstream files from every repository-authored Added / Deleted / Modified difference
- AND every difference has a durable reason instead of relying on conversation memory

#### Scenario: Existing root skill-maintenance guidance is superseded as a baseline

- GIVEN the original Anthropic `skill-creator` is adopted as the standard reusable baseline
- AND material repository-only guidance from `agents/skills/skill-maintenance.md` is preserved under a clear local owner
- WHEN the adoption is implemented
- THEN the root pseudo-skill document is removed rather than retained as a parallel Skill-authoring baseline

### Requirement: Governed Skill work composes skill-creator without changing action authority

Existing governed actions SHALL conditionally load the default-branch `skill-creator` when their current work materially investigates, specifies, authors, modifies, or reviews repository Skill artifacts. The reusable Skill SHALL provide Skill-creation/maintenance procedure and evaluation guidance only; it MUST NOT create a new dispatcher action, select workflow routing, override the mapped action Skill, or acquire role authority.

Unsupported optional upstream mechanics such as a required external CLI, browser, or subagent facility MUST NOT become an unconditional prerequisite for ordinary repository workflow. A governed action SHALL use applicable supported portions of the adopted Skill and SHALL follow its available-environment fallback when the pinned upstream procedure provides one; higher-authority repository/system constraints continue to apply.

#### Scenario: Lead explores a repository Skill problem

- GIVEN `Lead / explore-change` is legally selected for a problem about repository Skills
- WHEN the Lead investigates Skill anatomy, composition, or maintenance behavior
- THEN it conditionally loads the default-branch `skill-creator`
- AND `Lead / explore-change` remains the owner of Explore authority and disposition

#### Scenario: Lead specifies a repository Skill change

- GIVEN `Lead / propose-change` is authoring a formal change whose target materially includes repository Skills
- WHEN it develops the proposal/spec/design/tasks
- THEN it conditionally consumes the default-branch `skill-creator` as Skill-domain procedure/evidence
- AND OpenSpec authoring authority remains with the mapped Propose action and applicable repository governance

#### Scenario: Executor modifies a repository Skill

- GIVEN `Executor / implement-change` has an approved task that creates or modifies repository Skills
- WHEN it performs that task
- THEN it conditionally loads the default-branch `skill-creator` and applicable local Skill-governance specialization
- AND it changes only the approved scope under the mapped implementation action

#### Scenario: Reviewer evaluates Skill-related work

- GIVEN an OpenSpec or implementation review materially concerns repository Skill artifacts
- WHEN Reviewer performs the applicable governed review
- THEN Reviewer may conditionally load the default-branch `skill-creator` to evaluate the Skill-domain contract
- AND Reviewer still produces only the result authorized by the mapped review action

#### Scenario: Optional upstream evaluation facility is unavailable

- GIVEN the adopted upstream Skill describes an optional evaluation mechanism that requires an unavailable CLI, browser, or subagent capability
- WHEN a governed repository action does not require that optional mechanism to satisfy its approved acceptance criteria
- THEN the action does not invent a new runtime dependency or fail solely because that optional facility is unavailable
- AND it uses the pinned Skill's applicable fallback or omits the explicitly conditional facility
