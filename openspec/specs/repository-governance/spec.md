# repository-governance Specification

## Purpose

Define repository governance authority and ownership boundaries, single-source-of-truth reference rules, and current-versus-history boundaries so approved governance remains traceable without competing normative copies.

## Requirements

### Requirement: Governance rule categories have one authoritative surface

The repository SHALL assign each governance rule category to one authoritative surface and SHALL NOT require duplicated normative definitions across multiple surfaces to remain synchronized by convention.

The minimum ownership model SHALL be:

| Rule category | Authoritative surface | Other surfaces |
| --- | --- | --- |
| Repository overview / Human entry point | README.md | MAY link to authoritative governance; MUST NOT redefine runtime protocol |
| Shared Scheduled-Agent runtime protocol and safety invariants | agents/AGENTS.md | roles/skills MAY reference; MUST NOT duplicate the shared contract |
| Machine-decidable Action vocabulary, Action→Role mapping, finite transition/result rules, deterministic selection, effect authorization, carrier eligibility, explicit merged-carrier reconciliation, stale/replay/no-rewind guards, and postconditions | one default-branch executable workflow model | agents/workflow.md MAY be generated or mechanically verified Human-readable presentation; AGENTS/roles/skills/runtime/transport/carriers MUST NOT maintain a competing production DAG or parse prose as topology |
| Semantic role authority | agents/roles/*.md | AGENTS/Skills MAY orient/reference; MUST NOT redefine machine Action→Role or successor selection |
| Action-specific semantic procedure and evidence meaning | agents/skills/* | roles/AGENTS MAY map/reference; MUST NOT duplicate machine topology/effect bodies |
| OpenSpec authoring and validation conventions | openspec/config.yaml | Change artifacts follow them; MUST NOT restate them as runtime rules |
| Approved capability requirements and acceptance scenarios | openspec/specs/* | runtime code implements/references them; they are not an alternative runtime instruction surface |
| Proposed intent/design/tasks before merge | active openspec/changes/* | review input only; MUST NOT govern its own current invocation |
| Historical change provenance | archived OpenSpec changes | evidence only; MUST NOT override current default-branch governance or become routing state |
| Scheduled Task cadence and transport wiring | external product configuration and a replaceable transport adapter | repository docs MAY describe deployment context; transport MUST NOT define Action/Role/WIP/successor state |
| Project-wide proportionality and simplicity | openspec/specs/repository-governance/spec.md | runtime/documentation surfaces MAY implement or reference it; MUST NOT maintain a competing workflow-only definition |

The executable workflow model becomes authoritative for machine-decidable workflow semantics only after the approved implementation and delegating governance are merged to the current default branch. An active Change or feature branch containing a future model remains review input and MUST NOT govern its own invocation.

The Human-readable workflow surface MAY include rationale and semantic guidance that cannot be represented in the finite model. Any machine-decidable Action/Role/transition/effect/carrier rule represented there MUST be produced from or mechanically checked against the executable owner so divergence fails validation rather than being resolved by runtime prose parsing.

Repository application/kernel authorization and mutation-carrier identity SHALL remain separate. Application binds each effect to its exact target, preconditions, revision, and legal carrier class. A carrier is an actuator only and MUST NOT choose workflow meaning, target, effect, successor, retry, weaker preconditions, or success. Repository-owned fresh observation is required before a mutation can support a routing, gate, lifecycle, merge, or successor consequence.

For a carrier that is already closed and merged, application MAY authorize only the explicit read-only reconciliation contract: exact historical head, repositories/base/ref, merge metadata, current default-branch revision and ancestry, and the matching revision-bound independent PASS must all be fresh and coherent. The carrier performs no merge write; it only exposes the existing postcondition for application observation. Reopen, rewrite, force movement, substitution, duplicate merge writes, and duplicate PR creation are prohibited.

Deterministic application rejection SHALL include a machine-readable guard classification and relevant expected/observed identity or predicate evidence whenever that boundary knows the failed predicate. Aggregate diagnostic text MAY accompany it but MUST NOT be the only rejection evidence. Rejection evidence never authorizes retry, weaker preconditions, alternate targets, or a worker-selected successor.

#### Scenario: Project-wide design principle is needed by workflow and production design

- GIVEN proportionality applies to both Scheduled-Agent governance and ordinary project design
- WHEN the repository assigns normative ownership
- THEN the capability-level requirement is owned by repository-governance
- AND runtime/documentation surfaces may implement or reference it without maintaining a competing workflow-only normative definition

#### Scenario: Shared rule appears in a role or skill

- GIVEN a rule is owned by shared governance or the executable workflow model
- WHEN a role or skill needs that rule
- THEN it references the owner or states only its semantic specialization
- AND it does not define a second machine-control copy

#### Scenario: Active change contains future governance

- GIVEN an unmerged Change or feature branch defines a future executable model
- WHEN a Scheduled Agent wakes before that change is merged
- THEN the feature content is review input only
- AND current execution loads authority from the default branch

#### Scenario: Action derives role without a second owner

- GIVEN the current routed state contains one valid action:review-openspec
- WHEN machine dispatch selects work
- THEN it derives reviewer through role_for(action)
- AND no separately persisted normal role label is required for ownership

#### Scenario: Human-readable presentation drifts

- GIVEN agents/workflow.md differs from the default-branch executable Action model
- WHEN governance validation runs
- THEN validation fails
- AND runtime does not resolve the conflict by parsing or preferring Markdown

#### Scenario: Transport changes without changing workflow semantics

- GIVEN a supported transport invokes the same default-branch dispatch/application entry points
- WHEN the transport adapter changes
- THEN Action vocabulary, Role derivation, transitions, WIP/cardinality, effects, and success criteria remain unchanged
- AND transport is not a second workflow authority

#### Scenario: Mutation carrier cannot gain authority

- GIVEN application has authorized one exact mutation plan
- AND the Actions identity cannot legally execute it
- WHEN a legal connector/App carrier executes the plan
- THEN the carrier changes no Issue/Action/Role/effect/successor/retry meaning
- AND application accepts only the exact freshly observed postcondition

### Requirement: Non-authoritative orientation is distinguishable from normative authority

A non-authoritative surface MAY contain a brief orientation or link to help Human readers navigate the repository, but it MUST make the authoritative destination clear and MUST NOT restate detailed MUST/SHALL lifecycle semantics in a way that can conflict with the owning surface.

#### Scenario: README explains the development lifecycle

- GIVEN README needs to explain that the repository uses Scheduled Agents and OpenSpec
- WHEN it presents the development workflow
- THEN it may provide a concise overview and link to the authoritative governance
- AND detailed routing, role priority, Human escalation, retry, or terminal-state rules remain authoritative only in their owning governance surfaces

### Requirement: Reviewer and Executor use ownership boundaries during changes

Reviewer SHALL treat duplicate normative authority, stale copies, and ownership drift within the current change scope as reviewable governance defects. Executor SHALL modify the authoritative surface for a rule category and SHALL update dependent references only when needed, rather than maintaining parallel normative copies.

#### Scenario: Change modifies a shared runtime invariant

- GIVEN an approved change modifies a cross-role runtime invariant
- WHEN Executor implements it
- THEN the authoritative shared governance surface is modified
- AND role/skill files are changed only for references or true role/action-specific specialization
- AND Reviewer checks that no stale competing normative copy remains in the affected scope

### Requirement: Repository design applies project-wide proportionality and simplicity

Repository design SHALL prefer the smallest sufficient design that preserves required capabilities and safety properties across production code, architecture, persisted state, APIs, configuration, dependencies, tests/tooling, GitHub Actions, OpenSpec design, and Agent/workflow governance.

Before adding a concept or mechanism, the change SHALL identify a current approved requirement, concrete safety property, or demonstrated failure mode that requires the added complexity. When an existing concept is within the current change scope, the design SHALL prefer removal, consolidation, or an existing ownership layer when required capabilities and safety properties still hold without that concept.

This evaluation MUST remain bounded to the current change's relevant scope and MUST NOT turn ordinary change work into an unrelated repository-wide simplification audit.

#### Scenario: New abstraction has no demonstrated need

- GIVEN a proposed change introduces a new abstraction or persistent mechanism
- AND no current requirement, safety property, or demonstrated failure mode requires that mechanism
- WHEN Lead and Reviewer evaluate the design
- THEN the proposal does not retain the mechanism for hypothetical future generality alone
- AND the design prefers removal, consolidation, or an existing ownership layer

#### Scenario: Existing complexity is necessary

- GIVEN a concept within the current change scope appears removable
- WHEN removing it would violate a required capability or safety property
- THEN the design may retain the concept
- AND the requirement or safety property that justifies it is identifiable from current evidence

### Requirement: Skill maintenance uses bounded progressive disclosure and existing authority layers

Repository Skill authoring and maintenance SHALL keep each `SKILL.md` focused on the executable procedure for its mapped action. Conditionally needed detail MAY be moved to clearly referenced bundled/shared resources when that improves progressive disclosure, and guidance reused by multiple Skills SHOULD be extracted to one reusable source when genuine cross-Skill reuse exists.

Skill resources MUST NOT become a competing owner for shared Scheduled-Agent runtime invariants or role authority. Shared runtime invariants remain owned by `agents/AGENTS.md`; role mission/authority remains owned by `agents/roles/*`; action-specific procedure remains owned by the mapped Skill.

External mutable Skill-authoring references MAY inform a governed change, but scheduled runtime MUST NOT depend on fetching or obeying those external sources as authority. Adopted behavior SHALL be represented in current default-branch repository governance/artifacts before it can govern execution.

#### Scenario: Skill grows with conditionally needed detail

- GIVEN a mapped Skill contains detail needed only for a specific execution condition
- WHEN keeping that detail inline would make the main procedure unnecessarily large or obscure the common path
- THEN the Skill may reference a bundled or shared resource loaded only for that condition
- AND the main `SKILL.md` retains the action's compact executable flow

#### Scenario: Guidance is shared by multiple Skills

- GIVEN materially identical procedural guidance is needed by multiple Skills
- WHEN maintaining copies would create synchronization-by-convention
- THEN the repository prefers one explicit reusable guidance source with clear loading conditions
- AND does not move shared runtime invariants or role authority into that Skill resource

#### Scenario: External skill guidance changes upstream

- GIVEN an external Skill-authoring reference changes after repository approval
- WHEN a Scheduled Agent executes repository work
- THEN the external change does not alter runtime behavior
- AND any adopted update must enter the repository's governed change lifecycle before becoming authoritative

### Requirement: Python static security extends the existing Ruff quality gate

The repository SHALL enforce Ruff's non-preview `S` security rule family through the existing Python Quality Ruff lint gate rather than requiring a parallel static-analysis lifecycle. The selected security family SHALL apply to repository Python code under the normal Ruff scope. Test files under `tests/**` MAY ignore `S101` so ordinary test assertions remain valid, but production/source code and repository Python scripts MUST NOT receive a blanket `S101` exemption. Any additional security-rule ignore MUST be narrowly scoped and justified by concrete repository context; the `S` family MUST NOT be globally disabled to avoid remediation. Bandit, Semgrep, or another static-security scanner MUST NOT be required by this contract unless a separately demonstrated capability gap shows the existing Ruff gate cannot satisfy a required security property.

#### Scenario: Stable security rule is applicable

- GIVEN repository Python code violates a non-preview rule selected by Ruff's `S` family
- WHEN the existing Python Quality Ruff lint step runs
- THEN the same Ruff gate reports the violation
- AND no second static-analysis lifecycle is required for that coverage

#### Scenario: Test assertion is linted

- GIVEN a Python file is under `tests/**`
- AND it uses an ordinary `assert` statement for test verification
- WHEN Ruff evaluates `S101`
- THEN the configured test-only exception permits that assertion
- AND the exception does not grant a blanket `S101` exemption to production/source code or repository Python scripts

#### Scenario: Preview security rule exists

- GIVEN Ruff exposes a security rule that is still preview-only
- WHEN the repository selects the `S` family under this contract
- THEN this change does not enable Ruff preview mode merely to activate that rule
- AND preview-rule adoption requires separate evidence before becoming part of the quality contract

#### Scenario: Additional security finding appears

- GIVEN enabling the `S` family exposes a stable security finding
- WHEN Executor implements the approved change
- THEN the finding is remediated where feasible
- AND any exception is narrowly scoped and justified by the concrete repository pattern
- AND the `S` family is not globally disabled to make the gate pass

#### Scenario: Security lint configuration regresses

- GIVEN the repository has adopted the Ruff security-family policy
- WHEN a later change removes `S` from the configured lint families or broadens the test-only `S101` exception into production scope
- THEN focused repository regression coverage fails
- AND the existing Python Quality workflow surfaces the regression without a second scanner job

#### Scenario: Another scanner is proposed

- GIVEN Bandit, Semgrep, or another static-security scanner is proposed in addition to Ruff
- WHEN no concrete required capability gap in Ruff has been demonstrated
- THEN the repository does not add the duplicate scanner lifecycle under this requirement
- AND a separately evidenced need is required before such an expansion is governed

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

### Requirement: Repository Skills use standard anatomy and explicit provenance

Every repository-authored Skill package under `agents/skills/` that is consumed as a Skill SHALL provide a `SKILL.md` with YAML frontmatter containing at least a stable `name` and a trigger-oriented `description` consistent with the Skill's actual bounded responsibility. Adding standard Skill metadata MUST NOT itself expand dispatcher routing, role authority, Human authority, or action semantics.

When a repository Skill materially derives from, adapts, decomposes, or composes behavior from an actual upstream Skill, the repository SHALL keep reproducible Skill-local provenance identifying the upstream repository, exact Skill path, and immutable upstream revision inspected. That provenance SHALL classify the local relationship and SHALL record every material local Add, Delete-or-omit, and Modify responsibility difference with a concrete repository policy, role split, environment/tool, or ownership reason and a maintenance implication.

A repository-original Skill with no actual upstream Skill equivalent MUST NOT invent an upstream mapping merely to satisfy provenance uniformity. Reusable upstream responsibility moved to another local owner SHALL identify that owner rather than appearing as an unexplained omission.

#### Scenario: Mapped repository Skill lacks standard frontmatter

- GIVEN a repository-authored mapped Skill has executable action procedure content
- AND its `SKILL.md` does not contain required YAML frontmatter with `name` and `description`
- WHEN repository Skill-conformance regression evaluates the Skill
- THEN the Skill fails structural conformance
- AND the repository does not treat action routing metadata elsewhere as a substitute for standard Skill anatomy

#### Scenario: Standard metadata preserves existing action authority

- GIVEN a mapped action Skill receives standard `name` and `description` frontmatter
- WHEN the normalized Skill is consumed by Scheduled-Agent execution
- THEN its existing mapped action, role authority, routing, and result semantics remain owned by current default-branch governance and role/action contracts
- AND the metadata does not create a new dispatcher action or broaden the Skill's legal mutation scope

#### Scenario: OpenSpec-derived Skill records immutable responsibility provenance

- GIVEN a repository Skill materially adapts an upstream OpenSpec Skill
- WHEN its provenance is inspected
- THEN the record identifies the upstream repository, exact Skill path, and immutable revision
- AND it classifies the local relationship such as semantic adaptation or repository-specific composition
- AND every material local addition, omission, or modification states the concrete reason and maintenance implication

#### Scenario: Upstream responsibility is intentionally decomposed across repository owners

- GIVEN an upstream Skill responsibility is split across repository Lead, Reviewer, Executor, automation, or multiple mapped Skills
- WHEN the local delta ledger records that difference
- THEN it identifies the exact local owner of each moved responsibility
- AND explains the repository role/stage or environment reason for the decomposition
- AND the decomposition is not represented as unexplained upstream drift

#### Scenario: Repository-original Skill has no upstream equivalent

- GIVEN a repository Skill implements a repository-specific responsibility with no actual upstream Skill equivalent
- WHEN provenance requirements are evaluated
- THEN the repository records or classifies it as repository-original where needed for maintenance
- AND it does not fabricate an upstream path, commit, or semantic mapping

#### Scenario: Future upstream refresh can distinguish intentional local deltas

- GIVEN a later maintainer compares a repository Skill with a newer upstream Skill revision
- WHEN they inspect the Skill-local provenance and delta ledger
- THEN they can distinguish unchanged upstream responsibility from intentional local additions, omissions, and modifications
- AND unexplained differences remain review findings rather than being accepted as historical customization

### Requirement: Material repository Skill changes carry durable maintenance traceability

Each governed OpenSpec Change that materially adds, modifies, or removes repository Skills SHALL durably declare every materially affected Skill as `Added`, `Modified`, or `Removed` within that Change's own archived traceability. For each declared Skill, the Change SHALL identify the approved source/reference, the responsibility boundary before and after the change or explicitly state that responsibility is preserved, the rationale for the change, and any replacement or supersession target when applicable.

The declaration SHALL be independent from capability delta cardinality. A single capability requirement MAY drive multiple Skill changes, and the repository MUST NOT fabricate one OpenSpec capability delta per Skill file merely to satisfy Skill maintenance traceability.

Wording, formatting, reference-only, or other non-material edits that do not alter Skill responsibility, semantics, composition, trigger behavior, authority, or maintenance meaning MUST NOT require maintenance-trace entries solely because a Skill file changed.

For Skills derived from an external upstream baseline, immutable upstream provenance and current local divergence remain separately owned by the applicable `UPSTREAM.md` contract. Skill-maintenance traceability MUST NOT replace or falsify that upstream provenance layer. Repository-authored Skills with no external upstream MUST NOT receive fictional upstream metadata merely to satisfy this requirement.

Lead SHALL make the material Skill-maintenance declaration part of the approved Change meaning before implementation. Reviewer SHALL verify during OpenSpec review that the declared Skill changes are justified by approved scope and during implementation review that the exact-head material Skill changes match the approved declaration. An undeclared material Skill change, a changed classification/responsibility boundary, or an unexplained removal/addition is a review finding unless the approved Change meaning is revised through the existing governed specification path.

Historical repair introduced after a prior Change SHALL be explicitly retrospective, SHALL link the original durable source evidence, and SHALL NOT rewrite archived artifacts to make the earlier Change appear to have followed a later rule. When an approved repair defines a bounded historical window, every merged implementation Change in that window SHALL be evaluated for material repository Skill Added/Modified/Removed effects; material effects SHALL be declared and non-material or no-Skill effects SHALL be explicitly excludable with rationale rather than silently grandfathered.

#### Scenario: One capability change modifies two Skills

- GIVEN one approved capability requirement requires action-local changes in two existing repository Skills
- WHEN Lead authors and Reviewer evaluates the governed Change
- THEN both Skills are declared as material Skill-maintenance entries with their individual responsibility treatment and rationale
- AND the repository does not require two artificial capability deltas solely because two Skill files change

#### Scenario: Repository-authored Skill is materially modified

- GIVEN a repository-authored Skill has no external upstream baseline
- AND its responsibility, semantics, composition, trigger behavior, authority, or maintenance meaning materially changes
- WHEN the Change is prepared for implementation
- THEN the Skill is declared `Modified` with approved source, before/after or preserved responsibility boundary, and rationale
- AND no fictional `UPSTREAM.md` provenance is required

#### Scenario: Skill is removed because another Skill supersedes it

- GIVEN an approved Change removes a repository Skill
- AND another Skill or responsibility owner supersedes its material responsibility
- WHEN the Change is reviewed
- THEN the removed Skill is declared `Removed`
- AND the declaration identifies the replacement/supersession target and why required capability is preserved or intentionally removed
- AND the maintenance record remains available after archive even though the Skill directory no longer exists

#### Scenario: Skill responsibility is decomposed

- GIVEN an approved Change splits one Skill responsibility across multiple governed Skills
- WHEN the Change is reviewed
- THEN the maintenance declaration identifies the old responsibility boundary and the new owners
- AND each material Added/Modified/Removed Skill is classified without inventing duplicate capability requirements

#### Scenario: Pure wording cleanup is non-material

- GIVEN a Skill edit changes only wording, formatting, or a reference with no semantic effect
- AND responsibility, semantics, composition, trigger behavior, authority, and maintenance meaning remain unchanged
- WHEN maintenance traceability is evaluated
- THEN no Added/Modified/Removed declaration is required solely for that edit

#### Scenario: Upstream-adapted Skill is refreshed

- GIVEN a Skill has immutable external upstream provenance
- AND a governed Change materially updates the repository Skill
- WHEN maintenance traceability is evaluated
- THEN the Change records the material Skill maintenance class/rationale
- AND the applicable upstream provenance/current-local-divergence record is reassessed separately when its represented divergence changes
- AND neither layer substitutes for the other

#### Scenario: Implementation head contains an undeclared material Skill change

- GIVEN Reviewer inspects an exact implementation head
- AND that head materially changes a repository Skill not covered by the approved Skill-maintenance declaration
- WHEN `Reviewer / review-implementation` applies the gate
- THEN the review returns a finding
- AND internal capability Proposal↔Specs↔Design↔Tasks consistency does not excuse the unexplained Skill drift

#### Scenario: Later Change repairs a bounded historical window

- GIVEN older completed Changes materially modified repository Skills before this requirement existed
- AND a later governed Change is explicitly approved to repair traceability across a bounded historical window
- WHEN the later Change records the historical maintenance explanation
- THEN every merged implementation Change in that window is evaluated
- AND material Skill effects reference their original Issue/implementation/archive evidence and are identified as retrospective
- AND a source Change with no material Skill effect may be explicitly excluded with rationale
- AND the repair does not edit older archived Changes to imply the newer rule existed at that time
