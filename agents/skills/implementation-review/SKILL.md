---
name: implementation-review
description: Reviewer procedure for exact-head independent review of completed implementation.
---

# Implementation Review

Mapped Action: Reviewer / review-implementation.

Fresh-read the current implementation carrier, base, files, task markers, quality runs, OpenSpec gate,
Human freshness, and prior findings. Review implementation behavior, approved scope, tests,
stale/replay/no-rewind guards, effect authorization, carrier separation, and unrelated-file changes.
For an open non-Draft carrier, the exact implementation head and exact current implementation PR head are the review identity. For a
closed+merged carrier, review the immutable historical PR head together with the current default-branch
revision, merge metadata, ancestry, and all post-merge repair changes in scope. PASS must bind both
`Revision: <historical PR head>` and `Default-Branch-Revision: <current main SHA>`; a PASS for another
head or default-branch revision is invalid.

Check Skill maintenance traceability: every materially affected Skill has a declaration, and a
differently classified or undeclared Skill change is a finding.

Return one structured PASS, FINDINGS, HUMAN_DECISION_REQUIRED, NO_GO, or BLOCKED result. PASS on the
exact unchanged open head, or on the exact historical-head/current-default-revision tuple for a
closed+merged carrier, derives merge-implementation-pr in the executable Action model. A merged-carrier
PASS never authorizes reopening or rewriting the carrier. Reviewer does not merge, mutate routing,
select a PR, or execute the successor.

## Skill maintenance and reserved capabilities

When a mapped Action materially creates or modifies a repository Skill, load
agents/skills/skill-creator/SKILL.md and
agents/skills/skill-creator/references/repository-governance.md. This repository Skill guidance is
procedural input, not runtime authority. The reserved capabilities `human:approved` and
`intake:approved` are never added, removed, restored, or manufactured by a Scheduled Role.

The exact-current-head gate is mandatory. A semantic OpenSpec bookkeeping exception does not weaken
this gate.
