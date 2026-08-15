# Skill maintenance guidance

This shared resource applies only when a governed action is authoring, implementing, or reviewing repository Skills. It does not replace `agents/AGENTS.md`, role authority, or a mapped action Skill.

Keep each mapped `SKILL.md` focused on the common executable procedure for its action. Use progressive disclosure when detail is conditionally needed and keeping it inline would obscure the common path. A conditional resource must have an explicit loading condition from the owning Skill or role/action procedure.

Extract shared guidance only for genuine cross-Skill reuse where maintaining duplicate copies would create synchronization-by-convention. Do not create a shared resource for hypothetical future reuse.

Authority boundaries remain unchanged:

- shared Scheduled-Agent runtime invariants stay in `agents/AGENTS.md`;
- role mission, authority, and ownership stay in `agents/roles/*`;
- action-specific executable procedure stays in the mapped `agents/skills/*/SKILL.md`;
- this resource may contain reusable Skill-maintenance guidance only and must not become a competing owner for those contracts.

External mutable Skill-authoring references may be used as design or review evidence during a governed change, but MUST NOT become runtime authority. Adopted behavior must be represented in current default-branch repository artifacts before Scheduled Agents rely on it.

When evaluating a Skill change, prefer the smallest sufficient edit. Repeated mistakes, missing or obsolete guidance, unnecessary Skill complexity, or duplicated guidance are evidence for maintenance; they do not by themselves authorize mutation outside the normal Human-admitted OpenSpec lifecycle.
