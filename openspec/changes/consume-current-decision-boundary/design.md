# Design: Consume current decision boundary before solution formation

## Current ownership boundary

Fresh current-main evidence establishes the following ownership:

- `openspec/specs/repository-governance/spec.md` owns the project-wide proportionality and simplicity contract.
- `agents/proportionality.md` is a reference projection and cannot become a competing normative owner.
- `openspec/config.yaml` owns OpenSpec authoring conventions.
- `agents/AGENTS.md` owns shared Scheduled-Agent invariants.
- `agents/workflow.md` presents the executable workflow projection.
- `src/investment_strategy/scheduled_agent_action_model.py` owns Action, Role derivation, transitions, Result vocabulary, and selection.
- The existing `review-openspec + FINDINGS -> resolve-question` path owns unsupported OpenSpec proposals.
- `tests/test_skill_maintenance_guidance.py` is the existing focused regression surface for this Skill-maintenance concern.

This zero-delta Change composes those owners. It does not create another normative owner or alter the runtime topology.

## D1 - Establish the current decision boundary first

Before forming material solution candidates, each relevant Lead phase reconstructs one current boundary from:

1. Human-approved Issue intent and non-negotiable outcomes, invariants, constraints, and scope;
2. applicable current canonical specifications;
3. current default-branch governance and OpenSpec configuration;
4. current repository evidence, including existing ownership and deterministic tests.

The procedure records the outcome of that reconstruction in the action result or work product as needed. It must preserve already-decided meaning and must not substitute implementation convenience for an approved boundary.

## D2 - Apply the existing proportionality owner subtractively

After the boundary is established, Explore and Change authoring consume the existing proportionality reference and its canonical owner in this order:

1. remove an unnecessary mechanism;
2. reuse an existing capability or artifact;
3. consolidate with an existing mechanism;
4. use the existing ownership layer;
5. only if those are insufficient, retain an addition with the exact current requirement, concrete safety property, or demonstrated failure mode that requires it.

The Skill wording is an action-specific adapter. It points to the current owner and does not restate a second project-wide normative contract. Hypothetical future generality is not sufficient evidence.

## D3 - Keep Explore bounded and current-first

`openspec-explore` consumes D1 and D2 before solution candidates. It verifies whether current truth already resolves the question and avoids history archaeology unless a rationale, ambiguity, conflict, provenance, or forensic question cannot be resolved from current evidence. It keeps Change identity and routing under the existing application boundary.

## D4 - Keep Change authoring bounded and subtractive

`openspec-change` consumes D1 and D2 immediately before material Proposal, Design, Tasks, or semantic correction. It preserves the approved outcome and scope, reuses the existing Change vehicle, and deletes directly adjacent stale or duplicated procedure wording only where that file is already touched. It does not broaden into repository-wide Role/Workflow cleanup or alter canonical specifications.

## D5 - Make Review symmetric with existing results

`openspec-review` independently reconstructs D1 rather than trusting the Proposal or artifact wording as authority. It checks both directions:

- retained or additional complexity without an exact current requirement, safety property, or demonstrated failure mode is a finding;
- removal, reuse, consolidation, or an existing owner is sufficient but a new mechanism remains is a finding.

The reviewer emits the existing `FINDINGS` result and the existing transition routes it to `resolve-question`. No Action, Result, routing state, or review-result type is added.

## D6 - Remove only directly adjacent duplicate wording

The implementation may remove directly adjacent duplicates that are inside the three touched Skills, such as repeated semantic-adapter text, worker-mutation prohibitions, validation/fail-closed phrasing, or duplicate review checks. Unrelated duplicate debt in Roles, Workflow, or shared governance remains outside this Change.

## D7 - Reuse existing executable regression surfaces

Extend the existing Skill-maintenance tests with structural assertions that:

- the canonical proportionality owner is singular;
- `agents/proportionality.md` remains reference-only;
- Explore, Change, and Review each consume the existing owner at the correct phase;
- subtraction-first ordering and evidence-justified addition are present;
- the existing `FINDINGS` route is referenced;
- no competing authority or new framework is introduced.

Existing Action-model, workflow, OpenSpec, lint, type, and CI checks remain the machine-decidable enforcement surfaces.

## Trade-offs and deferred decisions

This design intentionally leaves canonical specs and `openspec/config.yaml` unchanged because fresh evidence shows those owners already express the required capability. It also leaves the repository-wide Role/Workflow cleanup to #218. The trade-off is that action-local procedural wording must be maintained with the existing Skill tests; this is the smallest sufficient surface and avoids a new policy compiler or semantic linter.

## Delivery boundary

This is one independently mergeable procedural correction. Its parent outcome is the complete Issue #207 decision procedure, including current-boundary reconstruction, subtraction-first ordering, evidence-justified addition, history restraint, Reviewer symmetry, singular ownership, and existing regression protection. The stage exit criteria are exact-head independent review, full tests/lint/type checks, strict OpenSpec validation, implementation merge, and the required archive lifecycle. If any approved outcome remains incomplete, the existing lifecycle continuation must be used; completion cannot silently reduce scope.
