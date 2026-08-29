## Why

Production Scheduled-Agent dispatch can currently remove an already-routed `Lead / propose-change + Change: unset` Issue from the pre-activation queue before FIFO ordering by re-reading and re-parsing prior LLM-authored `ACTION_RESULT` prose. #168 → #169 and the earlier #161 → #168 recurrence show that an older Issue can already have current Propose routing yet a later Explore is authorized. This makes historical prose reconstruction act like workflow state even though current GitHub routing is intended to be the operational state.

The fix must reduce control-plane interpretation rather than add another parser/provenance layer. The Human-established direction for #175 is to make current coherent routing canonical for dispatch, remove Human direct-Propose as a normal intake path, keep semantic evidence checks action-local, and make deterministic repository application derive Explore successor effects from a bounded result code without introducing another model call or workflow engine.

Authoritative Explore baseline: #175 `ACTION_RESULT(PROPOSAL_READY)` comment `5461100685`, produced from current `main` revision `a0a30a9d87d420d23e04a04b656d39f6e1e037c7`.

## What Changes

- Remove `preactivation_eligible` and the global Propose admission/readiness reconstruction that reads Issue comments/events before FIFO selection.
- Define pre-activation operational selection from current coherent `Lead / explore-change + Change: unset` and `Lead / propose-change + Change: unset` routing, using the existing GitHub `created_at` then Issue-number ordering after formal-work and routing-debt handling.
- Remove Human direct-Propose as a normal workflow/admission path. Normal formal intake becomes routed Explore → bounded `PROPOSAL_READY` → Propose, while genuine `HUMAN_DECISION_REQUIRED`, advisory admission, Human-input freshness, and other Human-reserved boundaries remain unchanged.
- Keep the exact durable Explore result as action-local semantic authority for Explore-originated Propose and the corresponding Reviewer traceability check. Missing, stale, ambiguous, or contradictory semantic evidence retains/fails the selected Propose action instead of causing dispatch to skip to another Issue.
- Carry the four governed Explore dispositions — `PROPOSAL_READY`, `HUMAN_DECISION_REQUIRED`, `NO_CHANGE_REQUIRED`, and `NO_GO` — as bounded structured worker results rather than reconstructing the machine result from free-form Markdown.
- Make repository application derive Explore routing/terminal effects from the freshly authorized source action plus the bounded result. The worker no longer chooses an arbitrary successor routing tuple for Explore.
- Preserve WIP=1/finish-first, complete authoritative GitHub reconstruction, routing-debt handling, structural routing validation, Change immutability, exact-revision gates, role separation, and existing fail-closed behavior.
- Keep the result-derived mechanism bounded to the demonstrated Explore dispositions. #138 remains the owner of any broader executable-governance inventory.

## Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: make current routing the pre-activation operational selection state; remove direct-Propose admission; preserve Propose/Reviewer semantic traceability downstream of selection; and add bounded structured Explore result → repository-owned effect derivation.

## Skill maintenance traceability

Source/change reference for all entries below: #175 exact durable `ACTION_RESULT(PROPOSAL_READY)` comment `5461100685` and Change `canonicalize-routing-and-explore-results`.

- **Modified — `agents/skills/openspec-explore/SKILL.md`**
  - Responsibility before: Lead owns bounded Explore judgment and returns one governed disposition plus worker-requested routing/terminal effects; the Skill also carries the direct-Propose fallback/preserved-authority path.
  - Responsibility after: Lead still owns the semantic Explore judgment and durable narrative evidence, but returns one bounded structured Explore disposition; repository application derives the governed successor/terminal effect from the authorized source action plus that disposition. Normal direct-Propose fallback language is removed.
  - Rationale: remove arbitrary worker-selected successor control state and eliminate the direct-Propose special path while preserving Explore semantic authority.
  - Replacement/supersession: no replacement Skill; the same Skill retains Explore procedure ownership with narrower effect-selection authority.

- **Modified — `agents/skills/openspec-change/SKILL.md`**
  - Responsibility before: Propose supports both provenance-bound Human direct-to-Propose and Explore-originated entry, including direct-Propose fallback to Explore and special combined-queue admission handling.
  - Responsibility after: normal Propose formalization consumes the exact same-Issue durable `PROPOSAL_READY` Explore baseline as an action-local semantic precondition; a current coherent Propose tuple may be operationally selected, but missing/ambiguous semantic evidence fails/retains that selected action. Direct-Propose admission/fallback branches are removed.
  - Rationale: keep semantic readiness at the mapped Propose boundary instead of using historical prose/Human-admission reconstruction as global dispatcher eligibility.
  - Replacement/supersession: no replacement Skill; direct-Propose-only procedure is removed rather than moved elsewhere.

- **Modified — `agents/skills/openspec-review/SKILL.md`**
  - Responsibility before: Reviewer verifies Explore-result preservation for Explore-originated Changes but also carries an explicit valid direct-to-Propose exception that requires no synthetic Explore result.
  - Responsibility after: Reviewer continues independent Explore-baseline preservation plus reverse-first/forward semantic review for the normal Explore → Propose lifecycle; the direct-to-Propose exception is removed with the normal direct-Propose path.
  - Rationale: keep Reviewer traceability aligned with the single normal intake model without weakening independent semantic review.
  - Replacement/supersession: no replacement Skill; independent review ownership remains unchanged.

No repository Skill is added or removed by this Change. `skill-creator` is composition guidance consumed while specifying these modifications and is not itself a modification target.

## Impact

Expected implementation surfaces include shared workflow governance and Lead procedures, canonical `scheduled-agent-workflow` requirements, `workflow_dispatch.py`, `scheduled_agent_runtime.py`, `scheduled_agent_worker.py`, `scheduled_agent_effects.py`, direct-Propose-only Human-authority helpers that become dead, and production-boundary regression tests.

The independent OpenSpec review target before implementation is intentionally limited to this Change's proposal, delta spec, design, and tasks. Governance, Skill, runtime, and test files listed above are implementation surfaces and must not be edited as part of the Propose review target before `Reviewer / review-openspec` PASS.

No OpenAI API/model-call fallback, label-writer provenance gate, hidden admission token, lock/lease/heartbeat, retry counter, second workflow DAG, or generic workflow engine is introduced.

The one-time Human administrative sequencing override that temporarily parked #168 and #169 is deployment context only. Those Issues remain open and preserved; they are not part of the normal priority contract introduced by this Change.