# Design: Provenance-bound Human authority

## Context

#35 proves actor identity is not a sufficient Human-authority primitive because ChatGPT connector mutations are also attributed to `royhsu-work`. Raw GitHub REST provenance distinguishes the tested Human UI creation/label events (`performed_via_github_app == null`) from tested connector mutations, while comment `updated_at` detects edits after a Human approval event.

Current governance now also permits repository-authorized Explore. The implementation therefore must strengthen only Human-reserved authority boundaries and must not misclassify repository-authorized Explore as Human evidence.

## Requirements trace

- R1 — provenance-bound Human decision evidence: proposal items 1, 2, 4.
- R2 — exact approval capability and `intake:approved` relationship: proposal items 2–3.
- R3 — deterministic approval-event → decision-comment binding: proposal items 2, 4.
- R4 — all Human-reserved consumers use the same predicate while repository-authorized Explore remains separate: proposal item 5.
- R5 — prospective migration and historical compatibility: proposal item 6.
- R6 — deterministic security regression coverage: proposal item 7.

## D1 — One repository-owned Human-decision predicate

Use one evaluator for every workflow boundary that the canonical contract reserves to Human. It receives the expected durable `decision_ref` for that boundary plus current Issue/comment/event evidence and returns valid/invalid. It does not persist an approval token, authorization database, hidden state, cursor, or second workflow engine.

A decision is valid only when:

1. the current Human-reserved consumer can reconstruct exactly one expected `decision_ref` from already-durable workflow evidence;
2. the selected decision comment explicitly declares that exact `decision_ref` in the canonical line `Human-Decision-For: <decision_ref>`;
3. the selected decision comment author is `royhsu-work`;
4. raw creation provenance proves `performed_via_github_app == null`;
5. `human:approved` is currently present;
6. a qualifying later `labeled` event for `human:approved` has `actor.login == royhsu-work` and `performed_via_github_app == null`;
7. for that approval event, the selected comment is the latest qualifying Human-created comment on the same coordination Issue whose declared `Human-Decision-For` exactly equals the expected `decision_ref` and whose creation/update exists no later than the approval event; and
8. `comment.updated_at <= approval_event.created_at`.

The `decision_ref` is not a secret or an authorization token. It is a stable reference to the Human-reserved decision already present in durable workflow evidence. Existing surfaces provide the anchor rather than a new state store: for a Lead escalation it is the exact canonical `HUMAN_DECISION_REQUIRED` issue-comment reference; for another Human-reserved admission/authorization/resume consumer it is the exact durable boundary reference that governance already requires that consumer to reconstruct (for example the coordination Issue admission boundary or exact PR/revision authorization target).

When evaluating a current approval, use the latest qualifying Human-only `human:approved` labeled event that occurs after at least one matching candidate comment. Within that event, select the latest matching qualifying Human-created comment by GitHub `created_at`, then numeric comment id as a stable tie-breaker. A later matching comment is therefore a replacement decision for the same boundary, not an ambiguous second payload. A comment with a different or missing `decision_ref` is not a candidate for that boundary.

If the expected boundary cannot produce exactly one `decision_ref`, if required timestamps/ids/provenance are missing, or if candidate/event ordering cannot be reconstructed, fail closed. Model judgment must not choose a different comment or infer that unrelated Human prose was intended for the boundary.

A later edit invalidates the prior approval. Re-approval requires a later qualifying Human-only `human:approved` labeled event after the edited revision; because GitHub cannot produce another `labeled` event while the label remains present, Human may need to remove and re-add the reserved label. `unlabeled` provenance may invalidate current-label state but never establishes authority.

## D2 — `human:approved` is the approval capability; `intake:approved` stays distinct

Use exactly `human:approved` as the generic provenance-bound Human-decision approval capability. Scheduled roles may consume its evidence but MUST NOT add, restore, or manufacture it.

Keep `intake:approved` because current governance already uses it for the Human-only advisory-admission capability. It is not renamed or consolidated by this change. Its label snapshot remains insufficient Human proof; when advisory admission consumes a Human decision, the intended decision evidence must satisfy D1. This avoids silently changing existing intake semantics while still closing the actor-only authority gap.

## D3 — Raw provenance is an evidence adapter, not workflow state

Normalized connector objects may omit `performed_via_github_app`. The implementation adds the narrowest raw GitHub evidence read needed for comment creation and label-event provenance. That adapter does not own routing, retries, lifecycle transitions, or decision persistence.

Missing or inaccessible required provenance is a fail-closed authority result, not a fallback to actor-only semantics.

## D4 — Consumer boundary follows authority meaning, not action names

Apply D1 where governance requires Human authority: Human-only initial admission, decision answers, explicit Human authorizations, and resume conditions after Human escalation. Each consumer must supply the exact reconstructable `decision_ref` for the authority decision it is consuming; the shared evaluator must not discover a boundary by scanning prose.

Repository-authorized Explore remains valid through its existing independent repository-authority evidence and does not pretend to be Human activity.

If future governance adds another Human-reserved consumer, it should reuse the predicate and define its durable `decision_ref` anchor instead of copying an actor check or inventing a private approval state.

## D5 — Prospective activation and migration

Default-branch merge is the activation boundary. Workflows already terminal before activation stay terminal. Human evidence already legally consumed before activation is not re-litigated.

A still-pending Human-reserved decision consumed after activation uses D1 even if the Issue predates activation. If prior evidence cannot satisfy the predicate, fail closed and require a fresh Human decision comment carrying the expected `decision_ref` plus a later Human approval event.

Historical PR #55 remains review evidence only. Its missing complete MODIFIED requirement/scenarios and unspecified label identity are explicitly corrected in this new change.

## D6 — Threat and scope boundary

Covered threat: untrusted repository/work content influences an Agent that can mutate GitHub through the connected App while GitHub attributes those mutations to `royhsu-work`.

Not covered: compromise of the Human GitHub account, malicious GitHub platform behavior, cryptographic non-repudiation, external identity providers, generic prompt-injection classification, or denial-of-service caused by an Agent removing/invalidating evidence.

## Blast radius

Expected implementation surfaces:
- canonical `scheduled-agent-workflow` specification;
- shared `agents/AGENTS.md` Human-authority invariant and any current Human-reserved consumption rules;
- Lead/skills only where they currently produce/consume Human decision boundaries and therefore must expose the expected `decision_ref`;
- a narrow raw-provenance helper/evidence adapter if code is needed;
- labels/documentation for `human:approved` while retaining `intake:approved`;
- deterministic workflow/governance regression tests.

No strategy/data/backtest behavior, Reviewer independence, Executor implementation authority, archive ownership, or scheduler topology changes.
