# Change: Harden Human authority with provenance-bound GitHub decisions

## Why

The current Scheduled-Agent contract treats durable GitHub activity attributable to `royhsu-work` as sufficient Human authority. #35 demonstrated that connector-mediated Agent mutations are also attributed to `royhsu-work`, so actor identity alone cannot distinguish a Human decision from an Agent mutation. This is a demonstrated authorization failure mode at Human-reserved admission, answer, authorization, and resume boundaries.

The smallest validated boundary is provenance-based authorization of a Human decision comment followed by a Human-only approval-label event. The repository should encode that boundary without adding prompt-injection detection, cryptography, an external approval service, or a generic authorization engine.

## What Changes

1. Replace actor-only Human authority with a provenance-bound decision contract for new Human-reserved workflow decisions after activation.
2. Represent the decision payload with a Human-created GitHub comment and bind it to a later reserved Human approval-label event.
3. Require raw GitHub provenance when normalized connector reads do not expose `performed_via_github_app`.
4. Fail closed when author/provenance/current-label/revision/event evidence is missing or contradictory, and require re-approval after post-approval comment edits.
5. Apply the strengthened boundary to new admission, Human answers, authorization, and resume conditions while preserving already-completed historical workflow evidence and avoiding retroactive self-invalidation.
6. Add deterministic tests proving connector-mediated Agent activity cannot manufacture valid Human authority under the demonstrated threat model.

## Affected Capabilities

- **MODIFIED** `scheduled-agent-workflow`: Human-required authority evidence and migration semantics.

## Scope Boundaries

In scope:
- Human authority provenance for Scheduled-Agent workflow decisions;
- revision-safe binding of a Human decision comment to approval evidence;
- admission, answer, authorization, and resume consumers;
- minimum governance/helper/tests needed to evaluate raw GitHub provenance.

Out of scope:
- prompt-injection detection/classification;
- secret phrases or cryptographic signatures;
- external approval services or generic IAM/authorization engines;
- GitHub account-compromise threat model;
- Ruff/Bandit/Semgrep policy;
- prompt/Agent security regression policy tracked separately.

## Evidence / Trace

- Human-admitted coordination Issue: #47.
- Primary demonstrated failure and candidate authority model: #35 `issuecomment-5291555571`.
- Deferred-security disposition proving this concern was intentionally not consumed by #35: `openspec/changes/archive/2026-08-15-adopt-skill-creator-and-project-simplicity/proposal.md`.
- Current affected requirement: canonical `scheduled-agent-workflow` requirement `Human-required authority is bound to the repository Human actor`.
