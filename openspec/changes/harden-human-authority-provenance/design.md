# Design: Provenance-bound Human authority

## Context

#35 demonstrated that connector-mediated mutations can be attributed to the same GitHub actor as the Human maintainer. The current actor-only authority check therefore cannot defend Human-reserved workflow boundaries against an Agent induced by untrusted repository content to manufacture its own apparent approval.

The validated evidence also shows that GitHub creation/event provenance and comment revision timestamps are sufficient for a smaller solution: a Human-created decision comment, followed by a Human-only approval-label event, remains valid only while the approved comment revision is unchanged.

## Requirements trace

- R1 — strengthened Human authority evidence: canonical `scheduled-agent-workflow` requirement `Human-required authority is bound to the repository Human actor`.
- R2 — admission/answer/authorization/resume consumers use the same authority predicate rather than separate ad-hoc checks.
- R3 — raw GitHub provenance is required when normalized connector data is insufficient.
- R4 — historical completed workflows are migration history, not retroactive authorization failures.
- R5 — deterministic tests prove connector-mediated evidence cannot self-authorize.

## D1 — Keep one Human-decision predicate

Use one repository-owned evaluation procedure for all Human-reserved consumers. The procedure receives an intended decision comment plus current Issue/comment/event evidence and returns valid/invalid; it does not persist a new authorization database, token, cursor, or hidden approval state.

The predicate requires:

1. comment author `royhsu-work`;
2. comment creation `performed_via_github_app == null`;
3. reserved approval label currently present;
4. qualifying later `labeled` event by `royhsu-work` with `performed_via_github_app == null`;
5. deterministic ordering/binding to the intended comment;
6. no edit after approval (`comment.updated_at <= approval_event.created_at`).

This is the smallest model directly supported by the #35 experiments.

## D2 — One reserved approval capability label

Use one reserved label for Human approval rather than separate labels for admission, answers, authorization, and resume. The label is only an approval-event capability surface; the label snapshot by itself is never authority. The actual authority is the matching Human-only `labeled` event plus the approved comment revision.

The implementation should choose a clear repository label name and document that Scheduled roles MUST NOT add, restore, or manufacture it. Existing `intake:approved` remains a separate admission marker unless implementation evidence proves consolidation is safe; this change must not silently redefine unrelated intake semantics.

## D3 — Bind approval to the intended comment without hidden state

The consuming action identifies the decision comment required by its current durable workflow evidence, then selects the latest qualifying Human-only approval event after that comment revision while the reserved label remains present. It does not infer a different comment merely because a newer comment exists.

If more than one candidate decision could satisfy the same boundary and current workflow evidence does not identify the intended one unambiguously, fail closed and require a new explicit Human decision/approval rather than model selection.

## D4 — Raw GitHub provenance is an evidence adapter, not a second workflow engine

Normalized connector reads may be used for ordinary metadata, but Human-authority evaluation must call a raw GitHub evidence path whenever `performed_via_github_app` is absent from the normalized representation. This helper is narrowly scoped to reading object/event provenance. It does not own routing, workflow transitions, retries, or lifecycle state.

## D5 — Prospective activation and migration

The default-branch merge is the activation boundary. Decisions newly created or newly consumed after activation use the strengthened predicate. Historical workflows already terminal before activation remain terminal. Earlier evidence that has already been consumed by a completed lifecycle is not re-litigated.

For an active workflow that crosses the activation boundary before consuming a still-pending Human decision, the stronger predicate applies at consumption time. If the prior evidence cannot satisfy it, fail closed and request a fresh Human decision/approval rather than accepting actor-only evidence.

## D6 — Threat and scope boundary

Covered threat: untrusted repository/work input influences an Agent that can mutate GitHub through the connected App while GitHub attributes those mutations to `royhsu-work`.

Not covered: compromise of the Human GitHub account, malicious GitHub platform behavior, cryptographic non-repudiation, external identity providers, or generic prompt-injection classification.

## Blast radius

Expected governed surfaces:
- `agents/AGENTS.md` Human authority shared invariant;
- `agents/roles/lead.md` Human-escalation/authority consumption wording only if needed;
- mapped skills that consume Human admission/answers/authorization/resume conditions;
- label documentation for the reserved Human approval capability;
- a narrow GitHub provenance helper/evidence adapter if deterministic code is required;
- governance/security regression tests;
- canonical `scheduled-agent-workflow` specification.

No change is required to strategy/data/backtest behavior, Reviewer independence, Executor implementation authority, archive ownership, scheduler topology, or the OpenSpec DAG.

## Trade-offs

A reserved approval label introduces one additional Human UI action, but it provides a GitHub event whose creation provenance was experimentally distinguishable from connector-mediated label creation. Avoiding the label would require a different immutable/revision-safe Human signature primitive that current evidence does not demonstrate.

The model may allow an Agent to invalidate/remove evidence and cause re-approval (availability impact), but it prevents the demonstrated connector paths from manufacturing valid Human authority. Closing denial-of-service would require materially broader authorization machinery and is out of scope.
