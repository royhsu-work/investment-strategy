# Change: Require CI re-observation before async Exit

Explore source: #124 `issuecomment-5366724594`.

## Why

#112 established continuation-by-default and positive Invocation Exit Proof, and current canonical/runtime governance already says that the first observation of a just-triggered exact external resource as absent, queued, or in progress is not legal Exit Proof. #110 nevertheless returned immediately after pushing implementation revision `c6944826c6b79baaddfb0283521b0765218c4020` when the first exact-head Python Quality / OpenSpec Validate discovery read found no runs. A later wake consumed successful exact-head runs and continued.

The remaining gap is not a missing Exit taxonomy. The current executable seam accepts `exact_resource_unconsumable=True` as an already-decided fact, so it does not verify the observation sequence that must establish that fact. Action-local exact-run procedures similarly require bounded observation but do not define a mechanically testable minimum re-observation floor before the existing async-wait Exit can be claimed.

## What changes

- Strengthen the existing canonical requirement `Selected Scheduled Agent actions are work-conserving within an invocation` so a just-triggered exact required resource cannot qualify for ordinary asynchronous-wait Exit after only its first absent/queued/in-progress observation.
- Require at least one subsequent fresh same-invocation observation of that same exact target/resource after the first nonterminal observation before the existing async-wait Exit may be proven.
- If the subsequent observation becomes terminal, require immediate consumption of terminal success or actionable failure under the current action rather than Exit.
- Permit the existing async-wait Exit after that bounded re-observation remains absent/nonterminal only when no other immediately actionable same-authority work remains and current routing/revision/preconditions remain valid.
- Replace regression dependence on a caller-supplied `exact_resource_unconsumable` boolean with sequence-derived observation evidence covering first observation, re-observation, terminal consumption, stale state, and legal async wait.
- Apply the minimum corresponding procedure clarification to the mapped Skills that concretely trigger and consume exact required validation in the same invocation: `implementation` and `openspec-change`.

## Affected capabilities

- `scheduled-agent-workflow` — MODIFIED existing work-conserving / Invocation Exit requirement only.

## Scope boundaries

In scope: exact-resource observation evidence needed to distinguish first-discovery latency from a real async-wait Exit; sequence-derived regression coverage; minimal action-local consumers for implementation and OpenSpec authoring/validation.

Out of scope: new Exit classes; scheduler cadence; wall-clock timeout/sleep policy; polling counters; durable waiter state; heartbeat/lease/retry state; workflow topology; #111 mechanical mutation recovery; Reviewer/lifecycle action changes without demonstrated trigger-and-consume ownership; product/investment behavior.

## Skill maintenance traceability

| Skill | Class | Approved source | Responsibility treatment | Rationale |
| --- | --- | --- | --- | --- |
| `agents/skills/implementation/SKILL.md` | Modified | #124 / this Change | Preserve Executor `implement-change` ownership; make its just-triggered exact-run observation procedure require the shared sequence-derived re-observation floor before async-wait Exit | Prevent implementation from treating first exact-head CI discovery latency as unconsumable wait evidence |
| `agents/skills/openspec-change/SKILL.md` | Modified | #124 / this Change | Preserve Lead Propose/Resolve authoring and exact-validation ownership; make its just-triggered validation observation consume the same sequence-derived re-observation floor | Prevent OpenSpec authoring from reproducing the same first-observation premature Exit pattern |

No Skill is Added or Removed. `agents/AGENTS.md` remains the shared runtime owner; the Skills consume rather than duplicate the generic Exit taxonomy.

## Deferred work

None required by this Change. Other actions remain unchanged unless later durable evidence demonstrates the same trigger-and-consume defect.