# Change: Secure Human authority with provenance-bound GitHub decisions

## Why

The current Scheduled-Agent contract still accepts durable GitHub activity attributed to `royhsu-work` as sufficient Human authority. #35 demonstrated that connector-mediated Agent mutations are also attributed to `royhsu-work`, so actor identity alone cannot distinguish a real Human decision from Agent-produced evidence. This is a demonstrated authorization gap at workflow boundaries that are explicitly reserved to Human authority.

The smallest validated correction is provenance-bound approval of a Human decision comment: Human-created comment provenance, a later Human-only approval-label event, current approval-label presence, unchanged comment revision, and a deterministic one-event→one-comment binding. The change must integrate that model with the current #52-era distinction between Human-admitted work and repository-authorized Explore without creating a second authorization state machine.

## What Changes

1. Replace actor-only Human authority checks with one provenance-bound Human-decision predicate for boundaries that governance reserves to Human.
2. Use the explicit reserved capability label `human:approved` as the approval event surface. Each qualifying label event binds to exactly one latest qualifying Human decision comment across all decision references before any boundary-specific comparison, so one generic event cannot silently authorize multiple outstanding decisions.
3. Define the complete current `decision_ref` mapping rather than leaving anchors illustrative: Human-admitted Explore, Human-admitted direct Propose, Human-only advisory admission, and any answer/authorization/resume produced from canonical `HUMAN_DECISION_REQUIRED` have exact serialized anchors. Unknown future Human-reserved consumers fail closed until their canonical contract defines an anchor.
4. Keep `intake:approved` distinct as the existing advisory-admission capability; where its consumption is Human-reserved, the exact advisory-admission decision reference plus provenance-bound Human evidence is required.
5. Require raw GitHub provenance when normalized connector reads omit `performed_via_github_app`; fail closed on missing, ambiguous, contradictory, unorderable, reference-mismatched, or post-approval-edited evidence.
6. Preserve repository-authorized Explore as a separate non-Human authority path. Human-only initial admission and genuine later Human decisions use the stronger predicate; ordinary repository-authorized admission does not impersonate Human authority.
7. Activate prospectively on default-branch merge and add deterministic regression coverage for exact anchors, one-event→one-comment semantics, competing/replacement comments, and multiple approval-event ordering.

## Affected Capabilities

- **MODIFIED** `scheduled-agent-workflow`: Human-reserved authority evidence, exact current decision-reference mapping, deterministic one-event→one-comment approval binding, Human-only admission/answer/resume consumption, and migration semantics.

## Scope Boundaries

In scope:
- provenance-bound Human decision evidence for Scheduled-Agent workflow boundaries;
- exact reserved approval capability `human:approved`;
- exact current `decision_ref` mappings derived from stable Issue/comment identity;
- deterministic one-event→one-comment binding before boundary reference comparison;
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
- Historical PR #55 and Reviewer findings are evidence only; PR #55 was explicitly revoked and closed unmerged.
- PR #64 Reviewer findings require both exact non-escalation anchor definitions and prevention of one generic approval event fanning out across unrelated decision refs; this revision resolves both as specification meaning rather than implementation inference.
