# Design: decouple candidate withdrawal from readiness

## Context and intended observable result

This is the second independently delivered A2 supporting increment under #478's bound Human decision, after qualify-accepted-carrier-source. Its authoring N-1 is f327e5f7f054affa40120c8ca93a2804032a3f25. This design specifies future reviewed behavior; it does not govern its own unmerged delivery.

The stage's observable result is: the existing unique qualified unmerged PR is closed at its exact expected head by one accepted Application obligation; the truthful result describes remaining candidate work; the same coordination Issue stays open with its immutable Change and model-derived candidate Action; no replacement PR is required. A later fresh process can reconstruct this frontier and continue without replaying semantic work or close.

The parent restart decision preserves requirements and history. It does not license continued authoring on #479, copying its unmerged implementation/tests/completion markers, transferring its review/CI, or resetting Change to unset.

## Current source findings

The effect contract already maps Explore research/proposal coordination and Resolve research-required to DEFAULT_BRANCH evidence. The finite Action model already permits nonterminal research of an existing Change. Current formal qualification accepts a coherent immutable Change and qualified result/lifecycle suffix without requiring an implementation PR for a DEFAULT_BRANCH result.

The missing behavior is coupled across existing consumers:

1. semantic_intent_payload retains a close only for Lead / resolve-question / ready.
2. apply_effect_batch checks close-only semantic cardinality only for that tuple.
3. GitHubEffectAdapter._lead_retirement_target rejects a different Action or result before shared carrier qualification.
4. qualify_change_carrier(... implementation_retirement=True) permits that source purpose only for resolve-question.
5. _accepted_lead_retirement accepts only READY and a fixed implement-change successor; _accepted_formal_result_is_proven inspects the exact close only for that same tuple.

Broadening only item 5's event filter would be unsafe: another newly eligible tuple could otherwise reach a successful proof without the old READY-specific exact-close inspection. All new tuples must consume the same complete projection.

Existing code to reuse includes the exact stale-head rejection in application_bridge._fresh_github_mutation; the exact carrier preimage and CarrierRequired boundary; closed-unmerged observation; accepted-successor reconstruction; the existing formal-result builder; and the shared raw/legacy accepted-original reader deployed by the preceding helper. Do not replace these mechanisms with a new engine.

Canonical persistent-Issue and Explore requirements still contain pre-Change-only wording and obsolete same-wake/same-role continuation or Human-decision routing. The delta copies their complete blocks, preserves initial intake and surviving scenarios, and aligns current result vocabulary and model-owned projection. It does not change the finite model.

## Decisions

### D1. One bounded capability belongs to the effect contract

The existing scheduled_agent_effect_contract owner defines candidate withdrawal eligibility from the existing model and consequence specification:

- source Action belongs to the candidate-semantic set explore-change, propose-change, resolve-question;
- its Role is derived Lead;
- the Action/Result pair is legal;
- its consequence evidence target is DEFAULT_BRANCH; and
- next_action returns a nonterminal successor in the same candidate-semantic set.

Retain the existing resolve-question / ready retirement lane as a compatibility case with its actual READY semantics. Do not manufacture READY merely to use that lane.

At the current topology this produces the following descriptive matrix. Implementation derives successor through next_action; this table is not another executable transition registry.

| Source Action | Eligible non-ready/candidate-progress results |
| --- | --- |
| explore-change | proposal-ready, research-required, human-decision-required, blocked |
| propose-change | research-required, human-decision-required, blocked |
| resolve-question | research-required, human-decision-required, blocked |
| Existing compatibility | resolve-question / ready remains supported |

The rule excludes ready-for-openspec-review, lifecycle-ready, terminal results, other Lead Actions, Reviewer and Executor sources. Future topology changes must not silently broaden the intended candidate responsibility: the central policy and its finite contract tests make that architectural boundary explicit.

A result reports the remaining work. A separate candidate question may legitimately be blocked or require Human decision after withdrawal was already resolved. Restricting close to research-required alone would replace readiness coupling with another accidental result coupling.

### D2. Human semantic authority remains explicit

Lead must independently dereference the exact already-resolved withdrawal decision and disposition newer substantive Human input before the close request and consequential boundary. If withdrawal itself is unresolved, the legal semantic behavior is a Human question with no close effect. If only a different question about the future candidate remains unresolved, a truthful eligible human-decision-required result may accompany an already authorized withdrawal.

The current _authorized_issue_observation mechanically checks Issue/route/Change coherence; the generic human_authorized value consumed by the Action application model is not a withdrawal-specific decision_ref proof. This design does not claim that either is such a proof. Semantic source interpretation and freshness disposition remain Lead responsibility under current Human authority rules. Application independently checks its existing machine source, accepted identity, exact effect and postcondition contracts. Neither layer substitutes for the other.

No new approval label, field, registry, or persisted decision state is introduced. Review must assess the actual procedural and mechanical boundaries, not infer native Human-semantic enforcement from a fixture boolean, label snapshot, actor identity, or successful API response.

### D3. The capability is exact close-only

New candidate-action capability is confined to one decoded existing github-mutation effect containing:

- the authorized Issue number;
- pull-request-update;
- the exact qualified PR number;
- its exact expected_head_sha; and
- fields exactly equal to state closed.

The same owner must recognize this shape for retention and cardinality. Fresh request qualification must reject a close mixed with title/body/base fields, reopening, another PR, additional semantic effects, or additional close obligations. Application's own single formal result and derived routing are projections, not additional worker-requested semantic effects. Preserve supported legacy application-owned control projection treatment without using it to hide extra untrusted writes in a new raw request.

Do not simply add general pull-request-update permission to Explore and Propose. Propose already qualifies an ordinary OpenSpec carrier, so such an operation-table expansion could unintentionally authorize ordinary PR edits. Keep generic operation permissions unchanged or provide an equally narrow existing-owner shape qualification; every newly admitted update path must reject non-close fields. Explore must not become a general OpenSpec materializer or a generic _OPENSPEC_CARRIER_SOURCES member.

### D4. One proof owner, two consumption phases

The existing scheduled_agent_application_carrier module owns withdrawal evidence and target meaning. Use a read-only typed projection of existing source objects if needed; it is not a new state or serialized withdrawal identity.

Before close, the projection binds the current repository, exact open coordination Issue and immutable Change, source Action/Result capability, unique recognized unmerged candidate PR/ref/head, existing exact source qualification, and the immutable accepted one-close intent. A fresh initial request must observe the uniquely qualified candidate still open before ACCEPT. An already closed target cannot be adopted as a newly accepted withdrawal, because a new ACCEPT would occur after its close. Only recovery of the exact already-durable accepted obligation may reconcile a closed-unmerged target; an invocation-local accepted_intent flag or generic idempotent equality is not itself durable proof of that phase. Reuse carrier identity, uniqueness, non-closing linkage, current default source, and other still-applicable target guards. The operation need not be mergeable: withdrawal is not merge. It does not require a replacement, artifact readiness, prior review PASS, or a future formal result.

After close, completed retirement proof adds the fresh closed-unmerged postcondition and exact attributed formal consequence. It verifies one native ACCEPT, original request/body digest/provenance/identity, the full retained semantic effect and nested JSON equality, and the real source-event chronology ACCEPT <= close <= formal. Read exact source timestamps; never infer ordering from numbers, prose or physical comment order. Missing or contradictory order is unqualified.

Every newly eligible tuple must receive the same exact-close inspection presently special-cased for READY. The legacy accepted implementation READY / Reviewer FINDINGS retirement lane remains separately supported by its existing proof; do not require it to contain a newly invented explicit close intent. Existing Lead READY proof consumes the consolidated exact-close owner.

An accepted-close projection can be consumed before formal result for actuation/reconciliation, while completed proof is consumed later for supersession. Requiring completed proof to authorize the original close would create a circular dependency and is prohibited.

### D5. Preserve accepted evidence rather than replay

Use the already-deployed _read_accepted_original_request and its policies. Preserve strict fresh raw typed preflight; legacy physical correlation requirements; raw omitted optional/default identity handling; validation of supplied identity before binding; complete semantic/nested-effect comparison; historical absent-content compatibility; and unchanged source bytes/digests.

The immutable accepted intent retains the exact close for every newly eligible tuple. An additional effect must not disappear during normalization and make an originally mixed request look close-only. Original and accepted source identity conflicts, cross-Issue/Change substitution, wrong PR/head or source hash, duplicate acceptance, changed semantics, and unavailable provenance remain rejected.

Existing unfinished Issues are not migrated or re-executed. Their accepted originals, completed effects and recovery obligations stay durable and retain their compatible historical proof. New coverage does not retroactively reclassify terminal history or transfer review/CI between candidates.

### D6. Reuse the existing consequence and interruption owners

The sequence remains fresh authorization, immutable ACCEPT, exact close carrier or read-only reconciliation, fresh closed-unmerged observation, truthful formal result, and model-derived routing.

| Observed boundary | Legal next work |
| --- | --- |
| Before ACCEPT | No consequential close; preserve truthful source and failed qualification evidence. |
| ACCEPT durable, close missing | Reconstruct the same accepted obligation and produce only its currently necessary existing carrier plan. |
| Carrier emitted | Honor the existing hard invocation-exit boundary; a later fresh boundary consumes the exact plan/outcome. |
| Close durable, response/formal missing | Fresh-observe exact closed-unmerged; issue no second close; produce only missing formal consequence. |
| Formal durable, routing missing | Qualify the same formal consequence and apply only its missing model-derived projection. |
| Valid descendant consumed the result | No semantic replay, duplicate close, old formal recreation, or routing rewind. |

No separate recovery Action, state machine, counter, lock, queue, or generic planner is added. Changed or ambiguous target/source evidence remains fail closed.

ConsequenceSpec's DEFAULT_BRANCH target can be reused for the truthful coordination result. The current production completion path is issue_comment_bridge._formal_consequence(mode=current) -> _fresh_completion_postconditions -> effects.consequence_postconditions_complete; its generic DEFAULT_BRANCH branch returns only _valid_sha(current_revision) before observing any retained close. This helper must narrowly recognize the accepted withdrawal obligation and consume the same carrier-owned exact closed-unmerged proof BEFORE that generic return. Otherwise a fresh post-formal completion could incorrectly pass after the old PR was reopened, changed head, merged, or contradicted by a competing carrier. The phase distinction must be preserved: a formal-present completion consumer uses the completed proof, while pre-formal effect execution uses its accepted pre-close/post-close view without requiring a future formal result. No second consequence engine, duplicated close qualification, blanket PR requirement for unrelated DEFAULT_BRANCH results, or change to the existing formal-routing owner is permitted.

### D7. Establish the no-replacement frontier; defer replacement materialization

After a resolve-question / research-required close result, the existing next_action model yields Explore. The Issue stays open, Change stays identical, and exactly one current routing label is observed. A fresh process must qualify that source/frontier without an open replacement PR.

After a later Explore proposal-ready result, Propose remains model-derived for the same Change. This stage does not implement a new existing-Change Propose carrier. Current parse_materialization_payload rejects a no-PR supersession for Lead / propose-change; that is the next separately reviewed A2 increment.

That subsequent increment must keep expected_change == change == the original immutable Change, use the deterministic supersession branch, fresh main parent, exact content manifest/preimages and non-force Git, unique PR and missing-PR-only recovery. New artifacts obtain new strict and independent OpenSpec acceptance. No candidate identity is reset to unset to pass a first-activation parser.

## Ownership and proportionality

| Consequence | Existing owner | Treatment and boundary |
| --- | --- | --- |
| Finite Action/Result and successor | scheduled_agent_action_model | REUSE. No transition, role, Action or Result addition. |
| Candidate withdrawal capability | scheduled_agent_effect_contract | ADD one bounded capability at the existing authority layer, derived from legal topology and candidate responsibility; no broad mutation permission. |
| Exact semantic close projection and carrier identity | scheduled_agent_application_carrier with existing decoded effect contract | CONSOLIDATE current repeated retirement guards; no new durable state. |
| Immutable accepted effect retention and cardinality | scheduled_agent_effects | CONSOLIDATE using the same capability/projection; do not normalize away unauthorized writes. |
| Raw/legacy original qualification | existing _read_accepted_original_request | REUSE deployed policy, complete equality and strict legacy/raw distinctions. |
| Physical close, postcondition and recovery | existing effects/carrier application | REUSE exact expected-head plan, CarrierRequired exit, observed closed-unmerged and missing-effect continuation. |
| Formal frontier and routing | existing formal qualifier and application consequence owner | REUSE. Prove no replacement needed for the existing DEFAULT_BRANCH coordination result. |
| Same-Change Propose materialization | existing materialization owner | NO-DELTA in this helper; mandatory next increment. |
| Human meaning/freshness | Lead plus existing Human source contract | REUSE semantic responsibility; do not claim an invented native exact decision_ref gate. |

## Material Role and Skill maintenance

Update agents/roles/lead.md to remove READY as a prerequisite for a Human-resolved candidate withdrawal, distinguish ordinary same-PR semantic correction from lawful withdrawal followed by separate replacement, and preserve exact authority, fresh Human disposition, close-only request and new independent acceptance. This is a Role authority projection, not a new Role or an implementation task granting Lead direct mutation.

The helper's archived design declares both material Skill changes before implementation:

| Skill | Class | Responsibility treatment | Approved source and rationale | Replacement |
| --- | --- | --- | --- | --- |
| agents/skills/openspec-explore/SKILL.md | Modified | Preserve bounded research and no formal artifact authoring; specify formal immutable-Change research and optional exact already-authorized withdrawal request under the common capability. No replacement creation, direct close, or same-wake successor. | Bound Human decision 7199792110/7199709164 and this workflow delta; avoid fake readiness and activation reset. | Same Skill; no new package. |
| agents/skills/openspec-change/SKILL.md | Modified | Preserve semantic authoring and resolution; distinguish truthful research/remaining Human questions from already-resolved withdrawal, with application-owned effects and later independent review. No Propose materialization implementation added here. | Same bound decision and workflow delta; keep the closed candidate separate from future acceptance. | Same Skill; no new package. |

Reassess each existing UPSTREAM.md's local responsibility ledger against the exact changed meaning while retaining immutable upstream Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020. Explore's description as intentionally only pre-Change and its old same-role-continuation wording cannot continue to contradict the approved formal research and one-wake boundary. Record only relevant local Add/Modify responsibility differences and maintenance implications; do not rewrite upstream history, imply an upstream feature, or use a ledger as workflow authority. The Change maintenance declaration and upstream provenance remain separate.

Load the current repository skill-creator and repository-governance reference when authoring, implementing or reviewing these material procedure changes. Supported evaluation procedure remains subject to native CI-only and repository authority. Existing metadata and trigger responsibility stay stable; no new Skill or generic helper resource is justified.

### Fixed semantic procedure cases

Use identical source/governance inputs before and after the actual Skill edits and record the actual decisions in existing PR delivery evidence. These cases are planned, not claimed executed by this artifact.

| Case | Input | Discriminating expected behavior |
| --- | --- | --- |
| C1 | Exact qualified Human withdrawal; source resolve-question; new candidate research incomplete; no replacement. | Old default procedures expose the READY-only restriction. New procedures choose truthful research-required and, only with deployed capability and exact source checks, the one close-only request; no fake READY or replacement. |
| C2 | Source Explore; whether to withdraw is itself unresolved; no qualifying approval. | Both correct baseline and candidate refuse close and ask the bounded Human decision. Candidate capability must not create semantic permission. |
| C3 | Exact immutable accepted non-ready withdrawal; same-head closed-unmerged; formal/route unfinished. | Baseline flags the future non-ready accepted fixture as outside then-deployed capability, not retroactively supported. Candidate reconstructs only missing formal/route through the original accepted chain, with zero semantic replay and duplicate close. |

Keep baseline and candidate judgments independent of artifact self-consistency. These procedure cases do not claim Python RED, actual GitHub event delivery, or a native live close.

## Test First and verification plan

### First genuine N-1 behavior

Use the existing public GitHubEffectAdapter.guard and carrier_plan_if_required seams with a real exact close effect, source Lead / resolve-question, expected_result_kind research-required, and a qualified exact unique open/unmerged carrier. Use the canonical agent/<change> first-carrier branch with no historical or future supersession prerequisite. Extend the existing transport fixture in tests/test_scheduled_agent_application_carrier.py, especially _fake_github and test_lead_retirement_guard_uses_real_code_only_implementation_qualification, to supply complete actual I/O shapes: issues/229 must include the correct Action label, creation timestamp, open state and immutable Change, plus all requested repository/ref/PR observations. The present fixture lacks fields needed by the public guard, so an early fixture rejection must not be mistaken for the intended behavior failure. Substitute GitHub reads, not adapter decisions, the carrier qualifier, capability decision, or result of guard.

The expected behavior is guard acceptance and an exact existing close carrier plan without replacement evidence. First require a READY control through the identical complete I/O fixture and actual public guard/carrier path to pass on N-1. Only then does the research-required case isolate the current _lead_retirement_target READY-only refusal. Commit the test-only revision first; native Ruff lint/format and Mypy must pass, then pytest must fail on that behavioral assertion. Missing imports/APIs, broken fixture shape, setup/static failure, and unrelated regression are not intended RED. Do not introduce a new production API merely to write this first test.

### Sequential behavior cycles inside one Slice

After that RED, implement only enough for its genuine GREEN. Then select the next demonstrated missing behavior rather than publishing every test up front and batching the implementation:

1. Retain the same non-ready close in immutable accepted intent through the existing semantic_intent_payload/public application boundary, including exact semantic effect cardinality and new raw input.
2. Prove completed non-ready retirement through the existing qualify_supersession_branch/public qualification seam using a real original, unique ACCEPT, actual close state, formal result and model-derived successor. Qualify a possible later branch identity without creating that branch or requiring replacement readiness.
3. Reconstruct exact accepted close at the interruption boundaries and the same-Change no-replacement frontier through the existing application/formal/dispatch consumers in a fresh process/adapter view.
4. Extend finite source/result coverage and negatives under the same central contract; preserve READY/FINDINGS, Lead READY and shared raw/legacy historical protection.

Each behavior requiring a production correction needs its own source-bound test-only native intended RED before minimum GREEN. Cases already passing are regression evidence, not retrospective Test First. Independent review may refine sequence when actual N-1 observations show a smaller dependency; it must not lower the stage outcome or fabricate RED.

### Required behavioral coverage

- Every legal candidate capability pair and exclusion of all other legal Action/Result pairs, plus malformed inputs; successors are model-derived.
- The exact one-close effect survives new raw ingress and accepted reconstruction, while title/body/base/reopen/mixed-fields, additional semantic effects, duplicate close and replacement mutations remain unauthorized.
- Fresh exact PR/head/repo/Issue/Change/linkage/cardinality, merged/draft/competing or changed target and incomplete source reads preserve current guards and fail closed where unqualified. Initial pre-ACCEPT already-closed target is rejected; only exact durable accepted recovery can reconcile closed-unmerged.
- Unique native ACCEPT, raw/legacy original digest and provenance, typed supplied identity, full nested effect semantics, supported absent-content legacy policy, and accepted-before-close-before-formal source timing.
- Existing Lead READY and implementation READY/Reviewer FINDINGS paths, multiple legitimate supersession generations, no cross-Issue/Change substitution, no transfer of review/CI.
- Before ACCEPT zero close; ACCEPT with missing close; carrier exit; durable close with lost response; missing formal; missing routing; valid descendant already consumed. No duplicate close, semantic replay, or rewind. After a qualified formal result, fresh _formal_consequence completion must reject reopened, wrong-head, merged or competing-target contradictions through the same shared proof before the generic DEFAULT_BRANCH success.
- New fresh-process no-replacement frontier with original Issue/Change, actual model-derived route and no fabricated replacement. Fixtures do not claim live #479 withdrawal or native cross-day delivery.
- Unrelated unfinished workflow originals, accepted effects, existing reader defaults and terminal history remain compatible without batch mutation.

Whole-Slice VERIFY uses existing native full pytest regression, Ruff lint/format, Mypy and exact checkout OpenSpec strict validation. Retain unique safety and compatibility protection when consolidating obsolete implementation-specific tests; document the covered requirement and verified equivalent replacement before removing anything. Static/import/setup failures and test-after-implementation additions are never reported as RED.

Do not run repository tests, lint, type checks, OpenSpec, imports or production code locally. Local text/diff/hash inspection is not execution evidence.

## Delivery, evidence and remaining parent outcome

Semantic artifacts receive exact-R native strict validation and new independent semantic OpenSpec review before implementation. Mechanical strict PASS alone is not semantic acceptance. After whole-Slice verification, mark only tasks 1.1 complete, produce the single valid completed-Slice checkpoint, and verify the exact final marker head. Implementation Review remains independent and owns proactive refactoring/test-lifecycle findings; Executor authors and verifies corrections and does not self-clear PASS.

Merge uses exact current head/gates and postconditions. Observe deployed source, complete native archive, obtain independent archive review and merge, and verify canonical preservation and removal of this active helper. The approved narrow missing-linkage archive-PR recovery is available only on fresh exact branch/source and deduplication proof; no repeated archive or false workflow success.

Parent reconciliation is fully preserved in proposal.md and the bound decision/handoff. After helper deployment and lifecycle, a later fresh normal parent Dispatch may carry out actual #479 withdrawal through the legal Application. The helper does not execute that parent successor or silently rebind the bootstrap. The next A2 Propose entry, new candidate acceptance, conditional bounded bootstrap, Development Transaction, itemwise authority/Manifest/Task Contract, exact completion CI, canonical Consequence/Recovery, failure disposition, cross-day liveness, preservation of old Issues, complete parent lifecycle and dependency release remain mandatory.

At authoring time there is no new RED/GREEN/VERIFY, semantic PASS, implementation PASS, deployed helper, or live #479 close to claim. Evidence must be recorded from actual native source revisions and runs as those boundaries complete.
