# Design: substantive Human input freshness and disposition

## Context

The persistent coordination Issue is already the durable workflow journal. #105 showed that an ordinary direct-Human question can be posted between Scheduled-Agent snapshots without becoming part of the next role's explicit gate evidence. Existing exact-head and contradictory-evidence rules protect PR/OpenSpec revisions, but current action procedures do not share an equivalent last-moment check for newer direct-Human coordination-Issue input.

This change must preserve the existing distinction between ordinary Human input and decisions that are actually reserved to Human authority.

## Requirements trace

- `Scheduled execution is at-least-once and state reconstructable` → D1-D6 → Tasks 1-3; owns the shared freshness/disposition and reconstructability invariant.
- `Review and finalize actions have Lead-owned minimum gate contracts` → D2/D4/D5 → Tasks 1.3, 2.3, 3.1; integrates the shared invariant into Reviewer and Lead consequential gates.
- `Executor merges only an explicitly authorized unchanged revision` → D2/D5 → Tasks 1.3, 2.3; integrates mutation-time disposition into merge preconditions.
- #105 regression timing cases → D2/D5 → Tasks 1.1-1.4, 3.1.
- Human-authority non-forgeability → D3 → Tasks 2.1, 3.1.
- Role separation → D4 → Tasks 2.1-2.3, 3.1.
- No hidden/comment-queue state → D1/D6 → Tasks 1.1, 2.1, 3.1.

## D1 — Reuse the coordination Issue; add no comment-processing state machine

The shared contract uses current Issue comments plus durable dispositions that reference exact comment ids. There is no unread pointer, cursor, acknowledgement label, comment queue, hidden registry, or new routing/lifecycle action.

Why: the requirement is reconstructability, not message-delivery bookkeeping. Durable comment ids and existing workflow result/finding/routing evidence are sufficient to prove that a specific Human input was handled.

## D2 — Put one freshness invariant in shared governance

`agents/AGENTS.md` owns the invariant that immediately before a consequential result, routing ownership transfer, or unsafe merge mutation, the acting role fresh-reads newer direct-Human coordination-Issue activity relevant to the evidence it is relying on.

The canonical capability remains split by existing responsibility instead of adding a parallel requirement identifier: `Scheduled execution is at-least-once and state reconstructable` owns the shared invariant; the existing review/finalize and merge requirements consume it at their specialized boundaries.

Mapped Skills do not redefine classification semantics. They only state where their existing action boundary consumes the shared invariant, for example:

- Executor before `READY`;
- Reviewer before a review result is finalized;
- Executor immediately before merge mutation;
- Lead before lifecycle results/handoffs where newer Human input could materially affect the judgment.

This follows SSOT and avoids synchronization-by-convention across ten independent copies.

## D3 — Direct-Human provenance is a freshness classifier, not authority

Because connector/App workflow comments may also be attributed to `royhsu-work`, actor identity alone cannot distinguish Human comments from Agent-authored durable messages. The candidate-input classifier therefore uses durable raw comment creation provenance: designated Human actor plus `performed_via_github_app == null`.

This does not grant authorization. If the content expresses a Human-reserved decision, the existing mapped decision reference, Human decision comment shape, later qualifying Human-only `human:approved` event, current-label, and tamper checks remain independently required.

If required raw provenance for a candidate Human-attributed comment cannot be reconstructed at a consequential boundary, the role fails closed rather than guessing that the activity is either direct Human or ignorable.

## D4 — Disposition follows existing role ownership

The current role has four bounded choices for material direct-Human input:

1. answer/disposition it within authority;
2. classify it non-blocking with concrete rationale;
3. convert it into an existing action-defined finding/blocker/correction result; or
4. route/escalate to the legal owner/Human boundary.

No role gains new specification, implementation, review, merge, or Human authority merely to clear a comment.

Examples:

- Reviewer may turn a traceability concern into a review finding.
- Executor may answer an implementation-state question that needs no specification judgment, but a scope/requirement question goes to Lead.
- A genuine Human-reserved choice continues through `HUMAN_DECISION_REQUIRED` / provenance-bound resume semantics.

## D5 — Treat late Human input like other mutation-time contradictory evidence

A consequential boundary operates on a relied-upon durable evidence snapshot. A new material direct-Human comment arriving after action start is newer evidence. The action must fresh-read immediately before the boundary; if the input can invalidate the assumption, the older result cannot be emitted until disposition makes the state coherent again.

This is especially important at three regression boundaries:

```text
Executor correction → READY
Reviewer review → PASS/findings completion
Reviewer PASS → Executor merge mutation
```

The design does not require continuous polling during the action.

## D6 — Durable disposition is explicit but presentation-light

A disposition references the exact Human comment id and includes enough bounded rationale/owner outcome for later reconstruction. Existing `ACTION_RESULT`, `REVIEW_RESULT`, `MERGE_RESULT`, finding/blocker comments, or a direct bounded answer may carry the disposition when appropriate. `agents/templates/messages.md` may describe this evidence field/presentation expectation but does not own behavioral semantics.

Repeated wakes reconstruct the exact prior disposition and do not emit duplicate acknowledgements.

## Affected surfaces

Expected implementation blast radius:

- `agents/AGENTS.md` — shared invariant/definitions;
- Lead/Reviewer/Executor role text only where role ownership needs clarification, avoiding shared-rule duplication;
- `agents/skills/implementation/SKILL.md` — consume before READY;
- `agents/skills/openspec-review/SKILL.md`, `implementation-review/SKILL.md`, `archive-review/SKILL.md` — consume before gate result;
- `agents/skills/merge-pr/SKILL.md` — consume at mutation-time fresh-read;
- `agents/skills/lifecycle-finalize/SKILL.md`, and `openspec-change/SKILL.md` where consequential Lead result/handoff can be materially affected;
- `agents/templates/messages.md` — minimal presentation orientation for exact-comment disposition evidence if needed;
- workflow regression tests — executable event/comment snapshots.

Do not modify `skill-creator` itself. The affected mapped Skills remain action-local consumers of the shared invariant.

## Trade-offs

Using raw creation provenance adds a fail-closed dependency at consequential boundaries, but avoids misclassifying connector-authored Scheduled-Agent journal messages as direct Human input. Reusing existing Issue/result evidence requires roles to make a materiality judgment, but avoids a combinatorial comment-state taxonomy and preserves the existing role authority model.

## Deferred / non-goals

- reusable extraction of Human-authority provenance as an independent Skill remains separate work (#83);
- no generic notification inbox, unread state, or comment processor;
- no changes to Human-reserved decision semantics beyond explicitly preserving them.