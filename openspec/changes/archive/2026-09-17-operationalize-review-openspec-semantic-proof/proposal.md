# Change: Operationalize review-openspec semantic proof

## Why

Issue #233 reconstructs the #229 exact-revision semantic-review regression and finds a consumption defect rather than a missing authority rule. At review time, the existing `Reviewer / review-openspec` contract already required independent Human-intent reconstruction, same-Issue Explore consumption, bidirectional traceability, proportionality/canonical-owner reasoning, and fail-closed handling of material semantic uncertainty. The review nevertheless returned `PASS` / `Findings: None` without making several review-time-knowable conflicts decision-affecting.

The Human-approved correction is explicitly not more Reviewer rules, a larger checklist, another review layer, or an idealized verifier that assumes complete history or capabilities unavailable in the actual review environment. The repair must make already-owned semantic obligations reliably affect `PASS` / `FINDINGS` on the execution substrate the Reviewer actually has.

This is a zero-delta OpenSpec Change. No canonical capability requirement changes: repository governance already assigns action-specific review procedure to the mapped Skill and already owns Reviewer independence, proportionality, canonical ownership, and fail-closed semantic review. The Change therefore uses `skip_specs: true` and changes only the existing review procedure plus focused deterministic wiring coverage.

## Residual formal-activation closure

The #233 progression also exposed a runtime transition defect at the boundary that this review correction must keep visible: pre-activation identity promotion, durable producer/application evidence, current qualification, and continuation must form one reconstructable chain. A valid historical recovery must remain usable after the default branch advances through a descendant repair; an inert closed historical Issue must not be allowed to contaminate a fresh active observation.

The current default branch now contains the generic owner-level repairs for the observed cases: closed inert history is excluded from active qualification, and a valid application-owned recovery contributes its recorded default-branch revision to the existing descendant ancestry check. These repairs preserve fail-closed qualification and the existing application/carrier separation. They are current execution evidence and regression input for this Change, not a new #233-specific state, exception, or authority layer.

The required continuation proof is therefore:

```text
pre-activation / formal promotion
→ durable result or application recovery at revision N
→ fresh descendant qualification at revision N+1
→ typed Lead continuation
→ existing application-owned postcondition
```

The Change must preserve and verify this boundary on the real current substrate. It must not make the qualifier permissive merely to unblock continuation, and it must not treat a label, actor, or current shape as a substitute for the durable causal/ancestry evidence.

## What Changes

1. Strengthen the existing `agents/skills/openspec-review/SKILL.md` in place with one compact semantic-proof loop:
   - **DERIVE** the approved semantic decision boundary independently from Human decisions, applicable same-Issue Explore evidence, canonical owners, and current governance before treating candidate artifacts or tests as proof.
   - **CHALLENGE** the actual material acceptance predicate with the smallest discriminating negative, twin, partition, bypass, replay, or exception case needed to distinguish correctness from artifact self-consistency.
   - **REALIZE** require claimed proof/evidence/capability to be observable on the current review/default-branch execution substrate; candidate-only, staged, future, or unavailable capability is not current proof.
   - **CLOSE** verify semantic consequence and ownership closure when consolidation, one-owner, removal, or reuse is claimed; exact code-level removal/consumer closure remains `review-implementation` responsibility.
2. Keep Reviewer within its existing boundary: independently verify semantic completeness and return the existing result vocabulary; do not edit governed artifacts, redo upstream Explore as an authoring action, or invent missing architecture/scope meaning.
3. Add focused deterministic regression coverage only for procedure presence/ownership and mapped-Skill wiring. Tests do not score semantic quality and do not replace Reviewer judgment.
4. Preserve the existing `PASS` / `FINDINGS` topology, Action/Role/Result model, Human-authority model, OpenSpec validation flow, and canonical specifications.
5. Carry the residual formal-activation/application transition as an explicit verification boundary, reusing the repaired current runtime owner and its exact descendant/recovery qualification evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change intentionally has no spec-level behavior delta; `.openspec.yaml` declares `skip_specs: true`.

## Impact

- Procedure: `agents/skills/openspec-review/SKILL.md`.
- Focused regression: existing repository-Skill test surface, primarily `tests/test_repository_skills.py` unless implementation-time evidence shows a narrower existing owner.
- Runtime boundary evidence: current-main qualification/application behavior and the existing production-shaped closed-history and advanced-recovery regressions.
- No canonical spec, `agents/AGENTS.md`, role contract, workflow topology, `openspec/config.yaml`, application/runtime model, or OpenSpec executable-version change is required.
- #229 remains the owner of affirmative-qualification semantics and implementation; #137 remains the Explore-to-Propose readiness boundary; #218 remains Role/Workflow SSOT duplicate-authority work; #207 remains broader decision-boundary context.

## Scope Boundaries

In scope:
- operational consumption of existing `review-openspec` semantic obligations;
- verification that formal activation, durable recovery evidence, fresh descendant qualification, and typed continuation remain closed on the current substrate;
- execution-realistic proof discrimination on the current review substrate;
- focused wiring/regression coverage that prevents the compact procedure from silently disappearing.

Out of scope:
- adding a second Reviewer or verification service;
- a new Action, Result, routing state, approval token, semantic score, registry, checklist state, second workflow graph, or generic prose/LLM linter;
- exhaustive history replay or assuming evidence surfaces unavailable to the current execution environment;
- reopening or modifying #229 semantics/implementation;
- changing canonical capability requirements solely to restate authority already owned elsewhere.

## Evidence / Trace

- #233 Human direction `issuecomment-5691628160`: find the root pattern, do not add more rules, and keep the correction realistic to the execution environment.
- #233 Explore result `issuecomment-5691778894`: `PROPOSAL_READY`, identifying the minimum `DERIVE -> CHALLENGE -> REALIZE -> CLOSE` procedure and no canonical-spec delta.
- #229 original review regression: PR #232 exact reviewed revision `2366bbfa853576b4d1f736c9833d7ed3b799822c` and review `issuecomment-5597482415`.
- Current authority: `agents/skills/openspec-review/SKILL.md`, `openspec/specs/repository-governance/spec.md`, `agents/AGENTS.md`, and `openspec/config.yaml`.
- Later regressions are corroborating recurrence evidence only; they do not retroactively establish what the original Reviewer knew.
- Current-main generic runtime repairs: PR #253 closed inert-history qualification boundary and PR #254 restored durable recovery ancestry across main advancement; both are verified prerequisite evidence for the residual transition boundary.
- Human durable scope decision `issuecomment-5693448791`: the residual formal-activation/application defect is part of #233 handling and must be closed before a READY/PASS boundary.
