# Tasks: Operationalize review-openspec semantic proof

## 1. Make existing review semantics decision-affecting

- [ ] 1.1 **RED — lock the mapped procedure boundary.** Add one narrow regression on the existing repository-Skill test surface proving that `agents/skills/openspec-review/SKILL.md` does not yet expose the approved `DERIVE -> CHALLENGE -> REALIZE -> CLOSE` semantic-proof loop. Run the focused test first and confirm the failure is caused by the missing procedure rather than fixture, syntax, import, or setup failure.

- [ ] 1.2 **GREEN — add the minimum semantic-proof loop.** Update only the existing `openspec-review` Skill as needed so Reviewer explicitly DERIVEs the independent approved semantic decision boundary, CHALLENGEs material acceptance predicates with the smallest discriminating case, REALIZEs whether claimed proof is available on the current review substrate, and CLOSEs semantic consequence/ownership claims before `PASS`. Preserve current exact-revision review, Human/canonical source reconstruction, same-Issue Explore consumption, proportionality, mapped Action, existing result vocabulary, and non-mutation boundary.

- [ ] 1.3 **GREEN — make execution-substrate realism explicit.** Ensure the procedure distinguishes current/default-branch evidence from exact candidate evidence, staged/future state, and unavailable/unverified capability. Candidate-only or future capability must not silently prove a current claim; historical reconstruction is required only when the semantic claim materially depends on ordering, provenance, replay, supersession, or review-time knowledge.

- [ ] 1.4 **GREEN — make semantic closure explicit without stealing implementation review.** Ensure claimed reuse/consolidation/one-owner/removal/no-delta semantics identify the consequence and intended owner and disposition competing semantic authority/affected boundaries sufficiently for OpenSpec review, while exact code-level removal and consumer/runtime closure remain `review-implementation` responsibility.

- [ ] 1.5 **REFACTOR — keep one compact owner.** Collapse or remove nearby duplicative procedural prose made redundant by the loop. Do not add another Skill/reference, canonical requirement, checklist state, score, verifier, routing state, or semantic oracle.

- [ ] 1.6 **VERIFY — focused Skill regressions.** Run the focused #233 structural regression plus the adopted Skill quick validator and existing repository-Skill/action-ownership/frontmatter tests. Verify deterministic coverage checks only procedure presence/ownership/wiring and does not attempt to score arbitrary semantic prose.

- [ ] 1.7 **VERIFY — repository quality gates.** Run the full regression suite, type checks, and lint checks required by the repository. Resolve only failures caused by this bounded change; unrelated failures remain evidence/blockers rather than scope expansion.

- [ ] 1.8 **VERIFY — OpenSpec zero-delta validity.** Run strict OpenSpec validation for `operationalize-review-openspec-semantic-proof` and verify `.openspec.yaml` declares `skip_specs: true`, no capability delta spec is introduced, and proposal/design/tasks remain consistent with the no-canonical-spec-change decision.
