## ADDED Requirements

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
