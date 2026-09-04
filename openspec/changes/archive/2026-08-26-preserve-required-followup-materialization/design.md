# Design: Preserve required follow-up materialization across Explore and Propose

## Context

The repository already owns the global invariant that an approved required separate follow-up needs one durable source-linked tracker and that ordinary deferred/optional/non-goal work does not. `Lead / resolve-question` and lifecycle verification already operationalize create/reuse/repair and fail-safe behavior. The missing integration is at the earlier producer boundary demonstrated by #158: Explore can decide a required split, then Propose can faithfully preserve broad scope while still losing the required-follow-up classification/materialization obligation.

The exact semantic baseline is #158 `issuecomment-5422771356`. It also establishes that #140 and #155 do not justify retrospective tracker creation.

## Decision

Keep classification semantic and bounded to the decision-producing Lead action, then make materialization mechanical once the exact durable defer decision exists.

```text
Lead / explore-change
  → classify bounded later work
      ├─ ordinary deferred / optional / non-goal
      │    → no tracker
      ├─ already-tracked separate work
      │    → reuse exact source-linked tracker
      └─ required separate follow-up
           → persist ACTION_RESULT E with exact required-follow-up decision
           → create / reuse / repair exactly one tracker linked to E
           → verify Change: unset
           → verify agent:lead + action:explore-change
           → only then complete routing to Lead / propose-change
                  ↓ exact ACTION_RESULT E
Lead / propose-change
  → dereference E
  → preserve required-follow-up classification
  → fresh verify / repair required tracker postcondition
  → formalize Proposal / Specs / Design / Tasks
```

This sequencing matters: E must be durable before it can serve as the exact defer-decision reference. `PROPOSAL_READY` may therefore be persisted before its successor routing is completed, but Explore MUST NOT treat the disposition's transition/postcondition as complete or route to Propose until every required tracker is routing-complete. This is ordinary reconstructable at-least-once effect sequencing, not a new lifecycle state or topology edge.

Reviewer and lifecycle contracts remain unchanged: Reviewer verifies the approved required tracker during semantic review, and lifecycle finalization remains a fail-safe if a previously approved obligation is missing or incomplete.

## Classification boundary

The semantic classes are existing meaning, not new workflow state:

- **ordinary deferred / optional / non-goal** — no durable tracker obligation;
- **required separate follow-up** — the approved source decision says the later work is required and must be handled as a separate change;
- **already-tracked separate work** — the required/independent work already has the exact reusable durable tracker.

Words such as `Deferred work`, `out of scope`, `follow-up`, or `separately reviewable` are presentation text only. They cannot independently create, remove, upgrade, or downgrade the semantic class.

## Durable source identity

For an Explore-originated obligation, the durable semantic anchor is the exact same-Issue Explore `ACTION_RESULT` that records `PROPOSAL_READY` and the required-separate-follow-up decision, together with:

- the exact source coordination Issue/Change where applicable;
- a bounded follow-up problem/scope sufficient to identify the intended tracker;
- the tracker source linkage required by the existing global follow-up contract.

The result is persisted first so its exact durable reference can be used by tracker materialization. Propose must later dereference that exact Explore result rather than reconstruct classification from conversation memory or editorial proposal wording.

## Materialization mechanics

After Lead has semantically classified a required separate follow-up and the exact durable decision reference exists, materialization uses the existing idempotent contract:

1. **No matching tracker** — create exactly one source-linked coordination Issue.
2. **Exactly one matching but incomplete tracker** — repair only the missing durable identity/routing fields still authorized by current source evidence.
3. **Exactly one complete matching tracker** — reuse it; do not create a duplicate.
4. **Multiple or ambiguous matches** — fail closed; do not guess or create another tracker.

Completion requires a fresh postcondition proving the intended tracker is source-linked and has:

```text
Change: unset
agent:lead
action:explore-change
```

An Issue that merely exists, or exists with only part of the routing tuple, is not complete materialization.

## Explore producer behavior

When Explore reaches a decision-complete direction:

- classify any explicitly separated later work before writing the final `ACTION_RESULT`;
- record every **required separate follow-up** and its bounded identity in that durable result so it becomes the exact defer-decision source;
- after the result is durable, materialize required trackers and reuse already-tracked separate work;
- leave ordinary deferred/optional/non-goal material untracked;
- do not complete the `PROPOSAL_READY` successor routing while a required tracker postcondition is missing, ambiguous, or contradictory.

If an invocation stops after the result is durable but before tracker/routing completion, the next `Lead / explore-change` reconstruction consumes that same durable result and completes only the missing idempotent materialization/routing effects. It must not create a second decision or reinterpret the classification.

This adds an action-local producer step; it does not make Explore a generic issue generator and does not let Agent-authored prose recursively authorize new work.

## Propose preservation behavior

For Explore-originated Propose:

- dereference exact Explore result E under the existing Explore → Propose semantic handoff contract;
- preserve every still-applicable required-follow-up classification from E in proposal/readiness evidence;
- fresh-read matching tracker state and repair only a uniquely identified incomplete tracker when current source authority still permits it;
- fail closed on missing authority, duplicate/ambiguous matches, or a contradiction between E and current durable tracker evidence;
- never downgrade a required obligation merely by placing it in `Deferred work` or `Out of scope`;
- never upgrade ordinary deferred text into a required obligation merely from wording.

The Proposal / Specs / Design / Tasks set may keep the separate work outside the current implementation scope; what must survive is the semantic classification and durable tracker obligation, not inclusion of that later work in the current Change.

## Ownership

- `openspec-explore` — semantic classification at Explore decision completion, durable source-result production, and normal tracker materialization before successor routing when Explore creates a required separate follow-up.
- `openspec-change` — exact Explore-result dereference, classification preservation, and fresh verify/repair before Propose readiness; its existing `resolve-question` materialization behavior remains intact.
- `openspec-review` — unchanged independent verification that required obligations have their durable tracker; no producer responsibility is moved here.
- `lifecycle-finalize` — unchanged terminal fail-safe; it does not become the normal producer.
- canonical `scheduled-agent-workflow` — externally verifiable producer/preservation invariant.

## Historical treatment

#140 and #155 are classification evidence only. The exact #158 Explore reconstruction concluded that neither source proves a missing approved required separate-follow-up obligation. This Change therefore creates no retrospective tracker for either Issue and does not rewrite their historical evidence.

## Alternatives rejected

- **Track every `Deferred work` or `follow-up` sentence** — overproduces work and turns presentation vocabulary into authority.
- **Create the tracker before the Explore result is durable** — cannot provide the exact durable Explore defer-decision reference required for reconstructable source linkage.
- **Wait until finalize-archive to create trackers** — preserves a late safety net but leaves the known producer gap intact and risks semantic loss before review.
- **Move creation to Reviewer** — violates separation of duties; Reviewer should verify Lead decisions, not create the decision it reviews.
- **Add a new durable classification label/state** — unnecessary; exact approved source evidence plus existing tracker state is sufficient and avoids a second workflow state machine.
- **Duplicate the entire global follow-up algorithm in every Skill** — increases governance drift. Skills should integrate narrowly with the existing shared contract.

## Traceability

- Proposal `Why` ↔ root cause: action-local producer/preservation omission rather than missing global semantics.
- Proposal `What Changes` ↔ `Decision`, `Explore producer behavior`, `Propose preservation behavior`.
- Capability requirement ↔ externally verifiable Explore materialization and Propose preservation scenarios.
- Implementation tasks ↔ focused Explore producer and Explore → Propose preservation regressions plus the two declared Skill modifications.
