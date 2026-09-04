# Repository integration guidance

Load this local resource together with the vendored `skill-creator` only when the current governed action materially creates, modifies, maintains, or reviews repository Skills.

The imported Anthropic Skill is reusable procedural guidance; it does not change repository authority. Current default-branch `agents/AGENTS.md` remains the owner of shared Scheduled-Agent runtime invariants, `agents/roles/*` remains the owner of role mission/authority/ownership, and the current mapped action Skill remains the owner of action-specific executable procedure, mutation authority, routing, escalation, results, and handoff semantics.

Apply progressive disclosure to repository Skills when conditionally needed detail would obscure the common action path. Keep reusable content shared only when there is demonstrated cross-Skill reuse; do not extract a shared resource for hypothetical future reuse or duplicate global governance/role authority into Skills.

External or mutable Skill-authoring material may be evidence during a governed change, but it is never Scheduled-Agent runtime authority by itself. Repository execution may rely on adopted behavior only after the reviewed repository artifact is authoritative on the default branch. For the vendored `skill-creator`, use the immutable upstream provenance and local-delta ledger in `../UPSTREAM.md` when evaluating refreshes or local changes.

When changing repository Skills, prefer the smallest sufficient edit supported by approved scope and demonstrated evidence. Repeated mistakes, missing or obsolete guidance, unnecessary complexity, and duplicated guidance are maintenance evidence; they do not grant mutation authority outside the current governed workflow.
