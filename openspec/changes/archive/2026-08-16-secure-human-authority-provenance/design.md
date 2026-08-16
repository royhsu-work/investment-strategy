# Design: Provenance-bound Human authority

## Context

#35 proves actor identity is not a sufficient Human-authority primitive because ChatGPT connector mutations are also attributed to `royhsu-work`. Raw GitHub REST provenance distinguishes the tested Human UI creation/label events (`performed_via_github_app == null`) from tested connector mutations, while comment `updated_at` detects edits after a Human approval event.

Current governance now also permits repository-authorized Explore. The implementation therefore must strengthen only Human-reserved authority boundaries and must not misclassify repository-authorized Explore as Human evidence.

## Requirements trace

- R1 — provenance-bound Human decision evidence: proposal items 1, 2, 4.
- R2 — exact approval capability and `intake:approved` relationship: proposal items 2–3.
- R3 — deterministic approval-event → one decision-comment binding: proposal items 2, 4.
- R4 — exact current consumer `decision_ref` mapping while repository-authorized Explore remains separate: proposal item 5.
- R5 — prospective migration and historical compatibility: proposal item 6.
- R6 — deterministic security regression coverage: proposal item 7.

## D1 — One repository-owned Human-decision predicate

Use one evaluator for every workflow boundary that the canonical contract reserves to Human. It receives the exact expected durable `decision_ref` for that boundary plus current Issue/comment/event evidence and returns valid/invalid. It does not persist an approval token, authorization database, hidden state, cursor, or second workflow engine.

Current `decision_ref` mappings are exhaustive rather than illustrative:

- Human-admitted Explore: `issue:<issue-number>:admission:lead:explore-change`.
- Human-admitted direct Propose: `issue:<issue-number>:admission:lead:propose-change`.
- Human-only advisory admission guarded by `intake:approved`: `issue:<issue-number>:advisory-admission`.
- Human answer/authorization/resume following a canonical `HUMAN_DECISION_REQUIRED`: `issuecomment:<escalation-comment-id>` using the exact escalation comment id.

A future Human-reserved consumer must add its exact mapping to the canonical contract before the evaluator can consume it. Unknown/unmapped boundaries fail closed.

A decision is valid only when:

1. the current Human-reserved consumer reconstructs exactly one expected mapped `decision_ref`;
2. a qualifying Human-created decision comment on the same coordination Issue contains exactly one canonical `Human-Decision-For: <decision_ref>` line;
3. the decision comment author is `royhsu-work`;
4. raw creation provenance proves `performed_via_github_app == null`;
5. `human:approved` is currently present;
6. a qualifying `labeled` event for `human:approved` has `actor.login == royhsu-work` and `performed_via_github_app == null`;
7. independently of the boundary being checked, that event binds to exactly one comment: the latest qualifying Human-created decision comment across all decision references that precedes the event, ordered by GitHub `created_at` then numeric comment id;
8. that event-bound comment declares the expected `decision_ref`; and
9. `comment.updated_at <= approval_event.created_at`.

The crucial ordering is event-first, not boundary-filter-first. The evaluator first determines the one comment approved by each event without filtering candidates to the requested `decision_ref`; only then does it compare the bound comment reference to the current expected boundary reference. This prevents one generic label event from fanning out into approvals for R1, R2, and other outstanding boundaries.

When several qualifying Human-only approval events exist, inspect newest to oldest and accept only the newest event whose single bound comment is current and declares the expected reference. An event bound to another reference is irrelevant to the current boundary. A later replacement comment for the same reference is not approved by an older event; it requires a later qualifying approval event. Missing/unorderable provenance, malformed or multiple reference lines, unknown anchor mappings, or reference mismatch fail closed.

A later edit invalidates the prior approval. Re-approval requires a later qualifying Human-only `human:approved` labeled event after the edited revision; because GitHub cannot produce another `labeled` event while the label remains present, Human may need to remove and re-add the reserved label. `unlabeled` provenance may invalidate current-label state but never establishes authority.

## D2 — `human:approved` is the approval capability; `intake:approved` stays distinct

Use exactly `human:approved` as the generic provenance-bound Human-decision approval capability. Scheduled roles may consume its evidence but MUST NOT add, restore, or manufacture it.

Keep `intake:approved` because current governance already uses it for the Human-only advisory-admission capability. It is not renamed or consolidated by this change. Its label snapshot remains insufficient Human proof; advisory admission uses the exact `issue:<N>:advisory-admission` reference and otherwise satisfies D1. This avoids silently changing existing intake semantics while still closing the actor-only authority gap.

## D3 — Raw provenance is an evidence adapter, not workflow state

Normalized connector objects may omit `performed_via_github_app`. The implementation adds the narrowest raw GitHub evidence read needed for comment creation and label-event provenance. That adapter does not own routing, retries, lifecycle transitions, or decision persistence.

Missing or inaccessible required provenance is a fail-closed authority result, not a fallback to actor-only semantics.

## D4 — Consumer boundary follows authority meaning, not action names

Apply D1 only where current governance requires Human authority. Current Human-only initial admission, advisory admission, and decisions/resume after `HUMAN_DECISION_REQUIRED` use the exact mappings in D1. A generic category such as “other authorization” is not independently executable authority: if the authorization arises from `HUMAN_DECISION_REQUIRED`, it uses that escalation comment id; if a future contract introduces a new Human-reserved authorization without that escalation, the future contract must first define a new exact anchor mapping.

Repository-authorized Explore remains valid through its existing independent repository-authority evidence and does not pretend to be Human activity.

## D5 — Prospective activation and migration

Default-branch merge is the activation boundary. Workflows already terminal before activation stay terminal. Human evidence already legally consumed before activation is not re-litigated.

A still-pending Human-reserved decision consumed after activation uses D1 even if the Issue predates activation. If prior evidence cannot satisfy the predicate, fail closed and require a fresh Human decision comment carrying the mapped `decision_ref` plus a later Human approval event.

Historical PR #55 remains review evidence only. Its missing complete MODIFIED requirement/scenarios and unspecified label identity are explicitly corrected in this new change.

## D6 — Threat and scope boundary

Covered threat: untrusted repository/work content influences an Agent that can mutate GitHub through the connected App while GitHub attributes those mutations to `royhsu-work`.

Not covered: compromise of the Human GitHub account, malicious GitHub platform behavior, cryptographic non-repudiation, external identity providers, generic prompt-injection classification, or denial-of-service caused by an Agent removing/invalidating evidence.

## Blast radius

Expected implementation surfaces:
- canonical `scheduled-agent-workflow` specification;
- shared `agents/AGENTS.md` Human-authority invariant and current Human-reserved consumption rules;
- Lead/skills where they produce canonical `HUMAN_DECISION_REQUIRED` or Human admission boundaries;
- a narrow raw-provenance helper/evidence adapter if code is needed;
- labels/documentation for `human:approved` while retaining `intake:approved`;
- deterministic workflow/governance regression tests.

No strategy/data/backtest behavior, Reviewer independence, Executor implementation authority, archive ownership, or scheduler topology changes.
