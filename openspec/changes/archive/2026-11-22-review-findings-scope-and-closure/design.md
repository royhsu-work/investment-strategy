# Design: Scope-bound implementation review findings and independent correction

## Decision boundary

Issue #458 approved two procedural corrections and four acceptance examples. The accepted Explore comment 7076432623 established a bounded feasible route: reuse the existing Reviewer and Executor action-local Skills, rather than introduce more workflow or recovery logic. The repo-governance capability owns cross-Skill maintenance traceability; each mapped Skill remains the procedure owner for its existing Action. The current independent Reviewer gate, Lead semantic authority, executable Action model, Application-owned mutation controls, exact-head proof, and #435's no-replay contract are preserved.

## Design decisions

### 1. Use the existing implementation-review Skill for Finding qualification

`agents/skills/implementation-review/SKILL.md` receives a short instruction that blocking findings record the approved requirement/invariant, exact revision evidence, currently relevant gate/stage and observable closure condition. Implementation suggestions remain separate advisory material. Reviewer evaluates alternatives and counterevidence against this original predicate and independently issues the Review outcome.

Trace: #458 Reviewer approved intent → capability requirement `Implementation review findings stay within approved scope and stage-specific closure` → implementation slice 1.

### 2. Use the existing implementation Skill for independent correction

`agents/skills/implementation/SKILL.md` receives a short instruction to independently verify the Finding and source authority before editing, then limit changes to proven approved scope and test the actual counterexample/equivalent evidence. Disputed findings and viable alternatives return to the same Reviewer gate. Material semantics/scope changes route via the existing `SPEC_BLOCKER → Lead / resolve-question`, not via Executor self-approval.

Trace: #458 Executor approved intent → the same capability requirement → implementation slice 2.

### 3. Respect stage-appropriate gates and keep UNKNOWN safety local to its actual effect

The counterexample proof for RED is judged before GREEN; full test/validation/independent review still apply when that later gate arrives. A preimage contradiction must yield `CONTRADICTORY` and no unauthorized write. Historical `UNKNOWN` preserves non-idempotent no-replay while a different approved correction is blocked only by a concrete competing current effect or target. This is a review decision boundary, not a new Runtime recovery rule.

Trace: all four #458 acceptance cases → capability scenarios → both slices' scenario checks.

## Material Skill maintenance traceability

| Skill | Classification | Source | Before → after responsibility | Rationale | Replacement |
| --- | --- | --- | --- | --- | --- |
| `agents/skills/implementation-review/SKILL.md` | **Modified** | Human scope in #458; accepted Explore comment 7076432623 | Independent exact-head implementation review **preserved**; blocking Finding qualification and original-condition re-review made explicit | Stop review-driven unapproved scope expansion | None |
| `agents/skills/implementation/SKILL.md` | **Modified** | Human scope in #458; accepted Explore comment 7076432623 | Bounded approved Executor work **preserved**; independent Finding verification, minimal counterexample-tested correction and Reviewer re-adjudication made explicit | Stop unverified suggested fixes from being implemented as requirements | None |

These are repository-original mapped Skills; no upstream provenance is invented. One capability delta applies to two separately declared Skill files. During implementation Reviewer checks both exact-head files against this declaration. Only scoped changes to these two Skills are authorized; the current Draft #459 may be reused solely after independent qualification.

## Alternatives rejected and trade-offs

- A new Finding schema/parser, state label, approval gate, decision table service or review authority would duplicate existing owners and increase WIP and liveness risk without satisfying a missing capability.
- Automatically adopting Reviewer suggested implementation would violate Human-approved scope and independent engineering judgment.
- Executor unilaterally rejecting Findings would violate Reviewer independence. A counterexample stays evidence for the Reviewer to adjudicate.
- Reopening #435 or attempting to prove all historic UNKNOWN attempts finished would change an unrelated durable outcome and expand this Change.

The trade-off is that structured Finding explanations require a small amount of additional review text. They use existing review records and have no persisted runtime state, extra API, or new workflow transition.

## Traceability and completion

Proposal approved intent → the one `repository-governance` delta requirement (four GIVEN/WHEN/THEN cases) → Decisions 1–3 → tasks 1 and 2 → the two exact Skill files. Reverse trace from each task and each Skill modification leads to the same approved #458 requirement and its own stage-specific acceptance evidence.

Implementation readiness still requires strict validation of this exact OpenSpec revision and independent `review-openspec`. The eventual exact-head implementation requires focused behavioral checks, full repository quality gates, independent `review-implementation`, authorized merge, and fresh-read of both Skill blobs on `main`. No part of the design grants an early PASS or changes #435.
