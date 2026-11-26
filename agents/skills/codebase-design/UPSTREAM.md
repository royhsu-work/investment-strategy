# Upstream responsibility provenance

- Upstream repository: `mattpocock/skills`
- Upstream revision: `6f7f7831a625f040a8e06a0e7954826b87ce775a`
- Upstream source paths: `skills/engineering/codebase-design/SKILL.md`, `skills/engineering/codebase-design/DEEPENING.md`, `skills/engineering/codebase-design/DESIGN-IT-TWICE.md`, `skills/engineering/code-review/SKILL.md`, `LICENSE`.
- Local Skill: `agents/skills/codebase-design/SKILL.md`
- Relationship: compact adaptation of design vocabulary and comparative reasoning for existing independent review procedures.

## Added responsibilities

- Compare a proposed slice against an independently verifiable vertical increment through a caller-visible interface.
- Assess test retirement against observable behavior, unique protections and verified replacement or authoritative retirement.

Reason: both review stages need repository-specific evidence without another gate or test registry.
Maintenance implication: retain scope, applicable test protection and existing acceptance authority when updating this guidance.

## Deleted or omitted responsibilities

- Omit separate setup, tracker, delegated reviews, fixed smell catalog and required comparison reports.
- Omit per-seam user confirmation and shell-based upstream procedures.

Reason: repository roles and the approved OpenSpec context already own review, scope and escalation.
Maintenance implication: adopt useful upstream knowledge without adding execution roles or duplicating review procedures.

## Modified responsibilities

- Adapt upstream dependency categories to choose representative test seams case by case.
- Treat code-review standards and smells as advisory heuristics unless evidence ties a defect to an approved requirement or invariant.

Reason: the exact-revision Reviewer owns evidence and disposition.
Maintenance implication: keep this Skill a knowledge source invoked by existing reviews.

## License

MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
