# repository-governance Delta Specification

## ADDED Requirements

### Requirement: Material repository Skill changes carry durable maintenance traceability

Each governed OpenSpec Change that materially adds, modifies, or removes repository Skills SHALL durably declare every materially affected Skill as `Added`, `Modified`, or `Removed` within that Change's own archived traceability. For each declared Skill, the Change SHALL identify the approved source/reference, the responsibility boundary before and after the change or explicitly state that responsibility is preserved, the rationale for the change, and any replacement or supersession target when applicable.

The declaration SHALL be independent from capability delta cardinality. A single capability requirement MAY drive multiple Skill changes, and the repository MUST NOT fabricate one OpenSpec capability delta per Skill file merely to satisfy Skill maintenance traceability.

Wording, formatting, or other non-material edits that do not alter Skill responsibility, semantics, composition, trigger behavior, authority, or maintenance meaning MUST NOT require maintenance-trace entries solely because a Skill file changed.

For Skills derived from an external upstream baseline, immutable upstream provenance and current local divergence remain separately owned by the applicable `UPSTREAM.md` contract. Skill-maintenance traceability MUST NOT replace or falsify that upstream provenance layer. Repository-authored Skills with no external upstream MUST NOT receive fictional upstream metadata merely to satisfy this requirement.

Lead SHALL make the material Skill-maintenance declaration part of the approved Change meaning before implementation. Reviewer SHALL verify during OpenSpec review that the declared Skill changes are justified by approved scope and during implementation review that the exact-head material Skill changes match the approved declaration. An undeclared material Skill change, a changed classification/responsibility boundary, or an unexplained removal/addition is a review finding unless the approved Change meaning is revised through the existing governed specification path.

Historical repair introduced after a prior Change SHALL be explicitly retrospective, SHALL link the original durable source evidence, and SHALL NOT rewrite archived artifacts to make the earlier Change appear to have followed a later rule.

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

- GIVEN a Skill edit changes only wording or formatting
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

#### Scenario: Later Change repairs historical traceability

- GIVEN an older completed Change materially modified repository Skills before this requirement existed
- AND a later governed Change is explicitly approved to repair that traceability gap
- WHEN the later Change records the historical maintenance explanation
- THEN it references the original Issue/PR/archive evidence and identifies the repair as retrospective
- AND it does not edit the older archived Change to imply the newer rule existed at that time
