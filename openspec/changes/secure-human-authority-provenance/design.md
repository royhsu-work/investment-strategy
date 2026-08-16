# Design: Provenance-bound Human authority

## Context

#35 proves actor identity is not a sufficient Human-authority primitive because ChatGPT connector mutations are also attributed to `royhsu-work`. Raw GitHub REST provenance distinguishes the tested Human UI creation/label events (`performed_via_github_app == null`) from tested connector mutations, while comment `updated_at` detects edits after a Human approval event.

Current governance now also permits repository-authorized Explore. The implementation therefore must strengthen only Human-reserved authority boundaries and must not misclassify repository-authorized Explore as Human evidence.

## Requirements trace

- R1 — provenance-bound Human decision evidence: proposal items 1, 2, 4.
- R2 — exact approval capability and `intake:approved` relationship: proposal items 2–3.
- R3 — all Human-reserved consumers use the same predicate while repository-authorized Explore remains separate: proposal item 5.
- R4 — prospective migration and historical compatibility: proposal item 6.
- R5 — deterministic security regression coverage: proposal item 7.

## D1 — One repository-owned Human-decision predicate

Use one evaluator for every workflow boundary that the canonical contract reserves to Human. It receives the intended Human decision comment plus current Issue/comment/event evidence and returns valid/invalid. It does not persist an approval token, authorization database, hidden state, cursor, or second workflow engine.

A decision is valid only when:

1. the intended decision comment author is `royhsu-work`;
2. raw creation provenance proves `performed_via_github_app == null`;
3. `human:approved` is currently present;
4. a qualifying later `labeled` event for `human:approved` has `actor.login == royhsu-work` and `performed_via_github_app == null`;
5. the event is deterministically associated with the intended comment using current durable workflow evidence; and
6. `comment.updated_at <= approval_event.created_at`.

A later edit invalidates the prior approval. Ambiguous candidate comments/events fail closed instead of allowing model selection.

## D2 — `human:approved` is the approval capability; `intake:approved` stays distinct

Use exactly `human:approved` as the generic provenance-bound Human-decision approval capability. Scheduled roles may consume its evidence but MUST NOT add, restore, or manufacture it.

Keep `intake:approved` because current governance already uses it for the Human-only advisory-admission capability. It is not renamed or consolidated by this change. Its label snapshot remains insufficient Human proof; when advisory admission consumes a Human decision, the intended decision evidence must satisfy D1. This avoids silently changing existing intake semantics while still closing the actor-only authority gap.

## D3 — Raw provenance is an evidence adapter, not workflow state

Normalized connector objects may omit `performed_via_github_app`. The implementation adds the narrowest raw GitHub evidence read needed for comment creation and label-event provenance. That adapter does not own routing, retries, lifecycle transitions, or decision persistence.

Missing or inaccessible required provenance is a fail-closed authority result, not a fallback to actor-only semantics.

## D4 — Consumer boundary follows authority meaning, not action names

Apply D1 where governance requires Human authority: Human-only initial admission, decision answers, explicit Human authorizations, and resume conditions after Human escalation. Repository-authorized Explore remains valid through its existing independent repository-authority evidence and does not pretend to be Human activity.

If future governance adds another Human-reserved consumer, it should reuse the predicate instead of copying an actor check.

## D5 — Prospective activation and migration

Default-branch merge is the activation boundary. Workflows already terminal before activation stay terminal. Human evidence already legally consumed before activation is not re-litigated.

A still-pending Human-reserved decision consumed after activation uses D1 even if the Issue predates activation. If prior evidence cannot satisfy the predicate, fail closed and require a fresh Human decision plus Human approval event.

Historical PR #55 remains review evidence only. Its missing complete MODIFIED requirement/scenarios and unspecified label identity are explicitly corrected in this new change.

## D6 — Threat and scope boundary

Covered threat: untrusted repository/work content influences an Agent that can mutate GitHub through the connected App while GitHub attributes those mutations to `royhsu-work`.

Not covered: compromise of the Human GitHub account, malicious GitHub platform behavior, cryptographic non-repudiation, external identity providers, generic prompt-injection classification, or denial-of-service caused by an Agent removing/invalidating evidence.

## Blast radius

Expected implementation surfaces:
- canonical `scheduled-agent-workflow` specification;
- shared `agents/AGENTS.md` Human-authority invariant and any current Human-reserved consumption rules;
- Lead/skills only where they currently consume Human decisions or admission evidence;
- a narrow raw-provenance helper/evidence adapter if code is needed;
- labels/documentation for `human:approved` while retaining `intake:approved`;
- deterministic workflow/governance regression tests.

No strategy/data/backtest behavior, Reviewer independence, Executor implementation authority, archive ownership, or scheduler topology changes.
