# Change: Adopt skill-authoring guidance and project-wide simplicity

## Why

#35 asks the repository to improve Scheduled-Agent behavior primarily through better-maintained Skills rather than a new memory/knowledge subsystem, while also promoting the existing workflow-only proportionality rule into a project-wide design principle.

Current evidence shows two ownership gaps:

- `agents/proportionality.md` and the canonical `scheduled-agent-workflow` specification express proportionality only as workflow-governance guidance, even though the Human requirement applies equally to production architecture, data/state, APIs, dependencies, configuration, tests/tooling, Actions, and Agent governance.
- The repository has action Skills but no shared rule for how Skill guidance should stay compact, use progressive disclosure, and extract genuinely reusable guidance without moving role authority or shared invariants into Skills.

Anthropic's current `skill-creator` is useful design input for progressive disclosure and skill organization, but it is an external mutable source and therefore must not become runtime authority. The repository should adopt only the bounded principles needed here into default-branch governance and keep all behavior changes inside the normal OpenSpec lifecycle.

## What Changes

1. Promote proportionality/simplicity to a project-wide repository design rule:
   - before adding a concept, require a current capability, safety property, or demonstrated failure mode that needs it;
   - when reviewing an existing concept, prefer removal/consolidation when required capabilities and safety still hold without it;
   - apply this only within the current change's relevant scope/blast radius, not as an unrelated repository-wide audit;
   - relocate the existing workflow-only canonical proportionality requirement into `repository-governance` so there is one capability-level owner rather than duplicate normative definitions.

2. Define shared Skill-maintenance guidance:
   - keep each `SKILL.md` focused on its mapped action procedure;
   - use progressive disclosure only when detail is conditionally needed or would otherwise make the main Skill unnecessarily large;
   - extract shared reusable guidance only when multiple Skills genuinely need the same procedure/reference;
   - keep shared runtime invariants in `agents/AGENTS.md` and role authority in `agents/roles/*` rather than moving them into Skill resources;
   - treat Anthropic `skill-creator` as design/reference evidence, not an instruction source loaded by scheduled runtime.

3. Extend bounded Lead idle advisory analysis so recent durable workflow evidence may produce Skill-maintenance recommendations for repeated mistakes, missing/obsolete guidance, unnecessary complexity, or duplicated Skill guidance. This remains advisory only and does not grant direct Skill mutation authority.

4. Keep the existing governance hierarchy and nine-action lifecycle unchanged. Any Skill modification that changes governed repository behavior still enters Human-admitted OpenSpec workflow.

## Affected Capabilities

- **MODIFIED** `repository-governance`: project-wide proportionality/simplicity ownership and shared Skill-maintenance/reference boundaries.
- **MODIFIED** `scheduled-agent-workflow`: Lead idle advisory evidence may include bounded Skill-maintenance opportunities; remove the old workflow-only proportionality requirement after its project-wide owner is established.

## Scope Boundaries

In scope:
- project-wide addition/removal proportionality rule;
- bounded Skill authoring/maintenance guidance based on `skill-creator` principles;
- Lead idle advisory Skill-maintenance analysis;
- consolidation/removal of duplicate workflow-only proportionality ownership;
- focused governance tests and references required by the change.

Out of scope:
- Agent memory, RAG, vector database, hidden cross-run context, or a new knowledge lifecycle;
- automatic self-modification of Skills;
- a new Agent role or maintenance workflow;
- mandatory eval/benchmark infrastructure for every Skill;
- importing Anthropic's entire skill-creator implementation, scripts, or test harness;
- unrelated repository-wide refactoring;
- Explore lifecycle work tracked by #38;
- Human-authority provenance redesign, including signed Human-decision/comment approval binding and raw GitHub App provenance requirements;
- enabling Ruff `S`, Bandit, Semgrep, or other Python source-security scanner policy;
- prompt-injection/prompt-security regression policy beyond the existing default-branch trust boundary.

## Security evidence disposition

Earlier durable #35 evidence remains valid and is explicitly preserved, but it is not part of this change's single-purpose Skill-maintenance/project-simplicity contract:

- `issuecomment-5291555571` demonstrates that actor identity alone is insufficient to prove Human authority under connector-mediated mutations and records a candidate provenance-bound authorization model plus unresolved admission/answer/authorization/resume design questions.
- `issuecomment-5291586680` records two distinct security tracks: enabling stable Ruff `S` rules through the existing Ruff gate, and prompt/Agent security regression coverage that is separate from Python source-code security.

These concerns are **deferred, not rejected or consumed**. Incorporating them here would combine three independent security contracts with the Skill-maintenance/proportionality change and violate the repository's single-purpose OpenSpec rule. They require a separate Human-admitted OpenSpec follow-up before any governed behavior changes. In that future follow-up, Lead owns specification resolution from the preserved durable evidence, Reviewer retains the independent semantic gate, and implementation remains subject to the normal role/authority boundaries. Until such a change is admitted and merged, current default-branch Human-authority, lint, and prompt-security behavior remains unchanged; the `injection` label remains test evidence only and grants no authority.

## Evidence / Trace

- Human-admitted direction and acceptance questions: #35.
- Existing narrow proportionality source: `agents/proportionality.md` and canonical `scheduled-agent-workflow` requirement `Workflow governance applies a simplicity and proportionality constraint`.
- Current SSOT ownership model: canonical `repository-governance` specification from #29.
- External design reference: Anthropic `skills/skill-creator/SKILL.md`, especially its skill anatomy/progressive-disclosure model; this reference is non-authoritative runtime input.
- Preserved deferred security evidence: #35 `issuecomment-5291555571` and `issuecomment-5291586680`; these remain future follow-up input and are not treated as resolved security requirements by this change.
