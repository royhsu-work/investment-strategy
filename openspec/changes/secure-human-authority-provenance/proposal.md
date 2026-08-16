# Change: Secure Human authority with provenance-bound GitHub decisions

## Why

The current Scheduled-Agent contract still accepts durable GitHub activity attributed to `royhsu-work` as sufficient Human authority. #35 demonstrated that connector-mediated Agent mutations are also attributed to `royhsu-work`, so actor identity alone cannot distinguish a real Human decision from Agent-produced evidence. This is a demonstrated authorization gap at workflow boundaries that are explicitly reserved to Human authority.

The smallest validated correction is provenance-bound approval of a Human decision comment: Human-created comment provenance, a later Human-only approval-label event, current approval-label presence, unchanged comment revision, and a deterministic binding between that approval event and the exact durable Human decision boundary being consumed. The change must integrate that model with the current #52-era distinction between Human-admitted work and repository-authorized Explore without creating a second authorization state machine.

## What Changes

1. Replace actor-only Human authority checks with one provenance-bound Human-decision predicate for boundaries that governance reserves to Human.
2. Use the explicit reserved capability label `human:approved` as the approval event surface. The label snapshot alone is never authority; each Human-reserved consumer supplies an exact durable `decision_ref`, and the approved Human decision comment must explicitly declare `Human-Decision-For: <decision_ref>` so the later qualifying approval event binds to the latest matching qualifying comment rather than arbitrary Human prose.
3. Keep `intake:approved` distinct as the existing advisory-admission capability. Where its consumption is Human-reserved, actor identity or label presence alone is insufficient; the Human decision evidence consumed by that boundary must satisfy the strengthened provenance contract.
4. Require raw GitHub provenance when normalized connector reads omit `performed_via_github_app`; fail closed on missing, ambiguous, contradictory, unorderable, reference-mismatched, or post-approval-edited evidence.
5. Apply the predicate to Human-only admission paths, Human answers, Human authorizations, and Human-resume decisions, while preserving repository-authorized Explore as a separate non-Human authority path defined by existing governance. Each Human-reserved consumer owns the exact durable boundary anchor from which its `decision_ref` is reconstructed; the shared evaluator does not infer intent by scanning prose.
6. Activate prospectively on default-branch merge: completed historical workflows remain terminal, while still-pending Human-reserved decisions newly consumed after activation must satisfy the stronger predicate.
7. Add deterministic regression coverage proving connector-mediated activity cannot manufacture valid Human authority under the demonstrated threat model, including competing/replacement comments and multiple approval-event ordering.

## Affected Capabilities

- **MODIFIED** `scheduled-agent-workflow`: Human-reserved authority evidence, deterministic decision-reference binding, Human-only admission/answer/authorization/resume consumption, and migration semantics.

## Scope Boundaries

In scope:
- provenance-bound Human decision evidence for Scheduled-Agent workflow boundaries;
- exact reserved approval capability `human:approved`;
- deterministic `decision_ref` binding from existing durable Human-reserved boundary evidence to a Human decision comment and later approval event;
- relationship to existing `intake:approved` and repository-authorized Explore;
- raw GitHub provenance reads required to evaluate the predicate;
- focused governance/helper/tests needed for the boundary.

Out of scope:
- prompt-injection detection/classification;
- secret phrases, cryptographic signatures, or external approval services;
- generic IAM/authorization engines or hidden approval databases;
- GitHub account-compromise threat model;
- Ruff/Bandit/Semgrep policy;
- general prompt/Agent security regression policy;
- changes to Reviewer/Executor separation, merge gates, archive ownership, or scheduler topology.

## Evidence / Trace

- Coordination Issue: #47.
- Primary demonstrated failure and tested candidate model: #35 `issuecomment-5291555571`.
- Required deferred disposition: `openspec/changes/archive/2026-08-15-adopt-skill-creator-and-project-simplicity/proposal.md` → `Security evidence disposition`.
- Current canonical requirement: `scheduled-agent-workflow` → `Human-required authority is bound to the repository Human actor`.
- Historical PR #55 and Reviewer findings are evidence only; PR #55 was explicitly revoked and closed unmerged. This proposal is freshly authored from current `main` and incorporates the prior findings rather than reusing that branch.
- Current PR #64 independent Reviewer finding requires the approval event → intended decision comment association rule to be explicit specification meaning rather than implementation/model inference.
