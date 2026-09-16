# Design: Operationalize review-openspec semantic proof

## Context

#233 establishes that the `review-openspec` regression is not an authority gap. The current Reviewer contract already owns independent semantic reconstruction, Human-intent preservation, same-Issue Explore consumption, proportionality/canonical-owner reasoning, exact-revision review, and fail-closed handling. The defect is procedural consumption: those predicates can remain descriptive prose instead of becoming evidence that changes `PASS` to `FINDINGS` when the reviewed artifacts do not establish the claimed semantic boundary.

The Human direction also constrains the solution against an unrealistic ideal verifier. The correction must operate on evidence and capabilities available to the current review/default-branch execution substrate and must not add a second Reviewer, hidden state, exhaustive replay requirement, or another normative owner.

## Goals

- Make already-owned semantic obligations decision-affecting before `PASS`.
- Keep one action-specific procedure owner: `agents/skills/openspec-review/SKILL.md`.
- Preserve Reviewer independence and the existing result/routing topology.
- Distinguish semantic judgment from deterministic structural regression.
- Keep the Change zero-delta at the canonical capability-spec layer.

## Non-goals

- New canonical requirements that restate existing Reviewer authority.
- New Action/Role/Result, reviewer service, verifier, score, token, registry, checklist state, workflow graph, or generic semantic linter.
- Requiring complete repository history when the reviewed claim does not depend on historical ordering.
- Treating candidate-only or future implementation capability as proof available to the current review.
- Moving implementation-review responsibility for exact code/consumer removal into OpenSpec review.

## Decision 1: Keep one action-specific procedural owner

The correction belongs in the existing `openspec-review` Skill. `agents/AGENTS.md`, the Reviewer Role, canonical `repository-governance`, and the current Skill already establish the authority boundary; none needs a duplicate rule.

The Skill is small enough that a new shared reference or new Skill package would add indirection without a demonstrated second consumer. Keep the semantic-proof loop in `agents/skills/openspec-review/SKILL.md` and preserve its current mapped Action declaration, frontmatter, exact-revision semantics, and conditional compositions.

## Decision 2: Operationalize one semantic-proof loop

The review procedure uses one compact loop:

```text
DERIVE -> CHALLENGE -> REALIZE -> CLOSE
```

### DERIVE

Before accepting candidate artifacts or tests as proof, derive the review decision boundary independently from:

- durable Human decisions that were available for the reviewed revision;
- the exact applicable same-Issue Explore result and its supporting evidence;
- canonical owners/specs and current default-branch governance/config;
- exact baseline `B` and reviewed target `R`.

Candidate proposal/design/tasks are evidence to test, not the source that defines the approved outcome. This is a reconstruction step, not a second Explore and not permission for Reviewer to invent missing architecture or scope.

### CHALLENGE

For each material claimed acceptance boundary, use the smallest discriminating challenge needed to distinguish actual correctness from artifact self-consistency. Depending on the claim, that may be one negative case, twin, partition, bypass, replay, ABA/mutate-away-and-back case, exception, or competing ownership partition.

This is not an exhaustive checklist and does not require every Change to enumerate every theoretical failure mode. A challenge is required only where a material branch or alternate interpretation can change `PASS` versus `FINDINGS`.

### REALIZE

Classify claimed proof by where it is actually observable:

- current default/review execution substrate;
- exact reviewed candidate revision;
- staged or future implementation state;
- unavailable or unverified capability/evidence.

Only evidence that is valid for the claim being reviewed can close it. A test or mechanism that exists only on the candidate branch, depends on a later deployment, assumes unavailable connector/runtime capability, or relies on inaccessible history cannot prove a present/default-branch claim unless the claim itself is explicitly about that candidate/future state.

Historical reconstruction is required only when the semantic claim depends on event ordering, provenance, replay, supersession, or review-time knowledge. The procedure does not require unlimited event replay for unrelated claims.

### CLOSE

When artifacts claim reuse, consolidation, one-owner semantics, removal, or no-delta, verify semantic consequence closure:

- the consequence being decided is identified;
- the intended semantic owner is identified;
- competing semantic authority is removed, localized, or explicitly shown non-authoritative;
- affected consumers/boundaries are dispositioned sufficiently for the semantic claim;
- retained complexity has a current requirement, safety property, or demonstrated failure mode.

OpenSpec review checks this design/spec/task-level closure. Exact implementation/code-level consumer removal and runtime closure remain `review-implementation` responsibility.

## Decision 3: Preserve Reviewer/upstream boundaries

Reviewer still independently verifies the exact reviewed revision and returns only the existing bounded result vocabulary. It does not mutate governed artifacts, rewrite the Change, select routing, or redo Explore as an authoring action.

If DERIVE/CHALLENGE/REALIZE/CLOSE exposes missing material meaning that Lead must resolve, the existing `FINDINGS` / Human-decision paths and executable successor model remain authoritative. No new topology is necessary.

## Decision 4: Deterministic regressions test wiring, not semantic judgment

A deterministic test may prove that the mapped `openspec-review` Skill retains the compact procedure, remains the sole action-specific procedure owner, passes the adopted Skill validator, and keeps existing action ownership/frontmatter contracts.

The test must not attempt to decide whether arbitrary prose semantically passes review. #229 remains the focused semantic regression scenario consumed by Reviewer judgment: if the approved source preserves a repository-wide outcome plus a P0 proof case while the candidate narrows around P0 or leaves a required boundary undispositioned, the corrected procedure must surface a finding.

## #229 regression mapping

The original reviewed evidence provides four review-time examples of how the loop changes the decision:

1. **DERIVE — scope/boundary preservation**: Human evidence preserved repository-wide qualification and made active-formal P0 a proof case; the candidate had to disposition the broader representative boundaries instead of letting P0 become the implicit scope.
2. **CHALLENGE — fresh-current proof**: current equality was not sufficient proof when mutate-away-and-back history could reproduce the same current value; the smallest discriminating ABA/twin case exposes the ambiguity without requiring knowledge of the later concrete implementation.
3. **REALIZE — proof substrate**: a claimed proof or executable path must exist on the substrate being used for review; candidate/staged/future capability cannot silently stand in for current evidence.
4. **CLOSE — ownership/proportionality**: active-formal-specific meaning placed in both generic and domain layers requires an explicit semantic-owner/consequence closure showing why both surfaces are necessary or which one owns the meaning.

Later regressions may corroborate that the pattern recurs, but they do not establish what the original Reviewer knew at the earlier review time.

## Rejected alternatives

### Add more canonical Reviewer requirements

Rejected because the required authority already exists. Repeating it would create more normative surface without addressing consumption.

### Add a second semantic verifier or review Action

Rejected because it duplicates ownership and creates another acceptance boundary rather than fixing the existing one.

### Add persistent checklist/score/token/registry state

Rejected because the defect is semantic consumption, not missing durable workflow state. Such mechanisms would create new authority and synchronization problems.

### Add a generic prose/LLM linter

Rejected because the material predicates are contextual semantic judgments; a mechanical prose score would be a false oracle.

### Require exhaustive history replay for every review

Rejected because it exceeds the current execution need and environment. Historical evidence is consumed only where the reviewed claim materially depends on history/order/provenance.

### Add a new shared Skill/reference

Rejected because `openspec-review/SKILL.md` is already compact and there is no demonstrated second consumer for this action-specific loop.

## Validation strategy

1. **RED**: add one narrow structural regression on the existing repository-Skill test surface that fails because the explicit `DERIVE -> CHALLENGE -> REALIZE -> CLOSE` review procedure is absent.
2. **GREEN**: add the minimum Skill procedure while preserving current exact-revision semantics, source/evidence reconstruction, proportionality, mapped Action, existing results, and non-mutation boundary.
3. **REFACTOR**: remove or collapse nearby duplicative procedural prose if the new loop would otherwise restate the same obligation twice.
4. **VERIFY**: run the focused regression, adopted Skill quick validation, repository Skill/action-ownership tests, full test suite, type checks, lint checks, and strict OpenSpec validation for this zero-delta Change.

## Deferred decisions

None at proposal time. Exact sentence placement inside the existing Skill and exact test function placement are ordinary implementation details as long as the approved procedure, ownership, and verification boundary remain unchanged.
