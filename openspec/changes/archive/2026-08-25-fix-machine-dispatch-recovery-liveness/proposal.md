# Change: Fix machine dispatch recovery liveness

## Why

#155 reproduced a self-hosting failure in the deployed workflow-dynamic dispatcher after #140 completed. The failure was triggered by historical Issue #91, but #91 is already terminal history: its compatible duplicate completion journal should not participate in authorization for unrelated current work.

Reviewer finding `issuecomment-5406357205` identified the first remaining defect: replacing full closed-history forensics with a structural projection still made every normal dispatch depend on a repository-history-sized closed set. Reviewer finding `issuecomment-5406912928` accepted that responsibility-boundary correction but identified two mutation-contract gaps in the revised target:

1. terminal close + routing retirement was specified as one full-label replacement even though `fresh-read routing → update labels` is not CAS and could erase an unrelated concurrent label; and
2. the one-time legacy normalization mutated multiple historical Issues without a governed owner/activation boundary.

The safety boundary is therefore narrower and explicit: normal dispatch authorizes from **current unresolved obligations**, while terminal routing retirement is an idempotent narrow effect that never treats a stale full-label snapshot as CAS. Pre-existing routed terminal history is resolved through the existing closed-routing `Lead / resolve-question` owner one exact candidate at a time rather than through an unowned bulk migration action.

## What Changes

- Define normal workflow-dynamic selection from a complete provenance-qualified snapshot of current open Issues plus a bounded current closed-routing-debt set; completed closed workflow history is not normal authorization input.
- Limit this read-reduction strictly to dispatch/recovery selection before an exact Issue/Role/Action is authorized. After `AUTHORIZE`, the mapped Action keeps its existing complete evidence-reconstruction and evidence-consumption contract; this Change does not filter, truncate, replace, or otherwise narrow action-required Issue comments, PR/review evidence, CI evidence, OpenSpec artifacts, Human evidence, or other durable inputs.
- Reuse existing routing state instead of adding a recovery registry: any closed coordination Issue retaining any workflow `agent:*` or `action:*` routing-label residue is current closed-routing debt until bounded resolution removes that residue or legally reopens the Issue.
- Make repository-owned terminal close + routing retirement one **logical idempotent effect**, not one full-label replacement. The effect closes state without replacing labels, fresh-reads, removes only exact workflow routing labels through narrow label removals with fresh preconditions/postconditions, and never writes a stale complete label set. Unrelated labels therefore survive concurrent additions/changes because the effect never replaces them.
- Keep partial/interrupted routing retirement observable: unresolved-close acquisition covers the complete fixed repository-governed set of both `agent:*` and `action:*` labels, deduplicates Issue identities, and treats any residual workflow routing label as debt until a fresh postcondition proves the Issue is closed and fully unrouted.
- Remove the standalone multi-Issue legacy migration/reconciliation effect. Pre-existing closed routed history is drained through the existing `Lead / resolve-question` recovery owner. Executable current-debt classification may select exactly one closed candidate for bounded resolution; terminal/retired candidates may request retirement of only their own routing residue, unfinished candidates retain the existing bounded reopen semantics, and ambiguous/incomplete evidence fails closed.
- When multiple current closed-routing candidates exist, executable classification may identify terminal/retired candidates from the complete current debt set and select at most one such candidate at a time for deterministic retirement. It MUST NOT reopen an unfinished candidate while another unresolved candidate or an open formal workflow exists. Genuine multiple unfinished/ambiguous debt remains fail closed.
- Keep semantic duplicate-terminal classification on the exceptional debt path: compatible repeated `LIFECYCLE_COMPLETE` journals are idempotent replay; conflicting immutable terminal facts remain indeterminate. This classifier no longer justifies keeping completed terminal history on the normal hot path.
- Include a bounded machine-owned diagnostic reason for `NO_WORK` and `FAIL_CLOSED` decisions without adding an Issue/Role/Action tuple or model override authority.
- Add production regressions proving both sides of the boundary: an already completed #91-like workflow no longer participates in ordinary dispatch after its routing debt is retired, while a selected mapped Action still receives every durable evidence input required by its existing governance and Skill even when that evidence is older Issue-comment history.

## Scope

Affected capability:
- `scheduled-agent-workflow`

In scope:
- `src/investment_strategy/scheduled_agent_runtime.py` current-state acquisition/orchestration needed to replace repository-history projection with bounded current routing-debt acquisition across all governed `agent:*` and `action:*` labels;
- `src/investment_strategy/workflow_dispatch.py` current routing-debt classification, candidate selection, exceptional terminal-evidence semantics, and the bounded `Lead / resolve-question` closed-candidate path;
- `src/investment_strategy/issue_comment_bridge.py` bounded non-authorization diagnostic presentation for `NO_WORK` / `FAIL_CLOSED`;
- repository-owned terminal Issue close/routing-retirement effect semantics needed to use narrow idempotent mutations and preserve unrelated labels under concurrency;
- `agents/AGENTS.md` minimum shared-governance alignment for current routing debt, partial retirement observability, and candidate-bound resolution;
- `agents/roles/lead.md` clarification that the existing `Lead / resolve-question` recovery owner also owns candidate-bound terminal routing retirement for an executable-classified closed candidate;
- `agents/skills/openspec-change/SKILL.md` minimum action-local procedure for that candidate-bound closed-routing resolution path;
- regression protection that confines dispatch read-reduction to pre-action selection and preserves existing mapped-Action evidence reconstruction/consumption semantics after `AUTHORIZE`;
- the canonical `Actionable workflow routing is one logical role/action tuple` and `Active-workflow cardinality and Issue-state coherence precede queue selection` requirements, plus directly related no-API decision behavior.

Out of scope:
- weakening complete current open-Issue enumeration, provenance qualification, WIP=1, deterministic pre-activation ordering, exact selected action identity, stale-state rejection, or effect-time reauthorization;
- optimizing, bounding, filtering, truncating, indexing away, or otherwise changing the existing action-specific durable evidence reconstruction/consumption contract after a mapped Action is selected;
- automatically resolving ambiguous or genuinely contradictory recovery state;
- a bulk multi-Issue migration action, generic recovery registry, new workflow lifecycle status, activation flag, lock, lease, heartbeat, retry counter, cursor/watermark, or cache-based authorization;
- treating `fresh-read + full label replacement` as a mutex/CAS primitive;
- lightweight Python/control-plane packaging or removal of `uv run` from bridge/runtime workflows;
- the separate `scheduled-agent-runtime.yml` `PYTHONPATH` execution defect unless implementation proves it is inseparable from this Change's authorization semantics;
- the broader executable-governance inventory tracked by #138.

## Skill maintenance traceability

### Modified — `agents/skills/openspec-change/SKILL.md`

- Approved source/change: #155 / `fix-machine-dispatch-recovery-liveness`, resolving Reviewer finding `issuecomment-5406912928` F3.
- Responsibility before: `Lead / resolve-question` owns specification-question resolution and participates in the existing bounded premature-close recovery path, but the Skill has no explicit candidate-bound terminal routing-retirement procedure.
- Responsibility after: preserve all existing specification-resolution behavior and add only the bounded closed-routing branch needed by the existing recovery owner: consume exact executable candidate classification; for terminal/retired debt request narrow retirement of that same closed Issue's routing residue; for qualifying unfinished debt use the existing bounded reopen semantics; for ambiguous/incomplete/competing debt request no cleanup/reopen mutation.
- Rationale: gives legacy/current closed-routing cleanup an existing governed owner and exact action-local boundary instead of inventing an unowned bulk migration action.
- Replacement/supersession: none; this is a narrow extension of the existing `resolve-question` recovery responsibility.

No repository Skill is added or removed by this Change.

## Durable source decisions and evidence

- Coordination Issue: #155
- First-principles investigation: `issuecomment-5405282007`
- Historical decision-complete interactive Explore evidence: `issuecomment-5405497269`; this remains contextual evidence and explicitly is not a canonical `ACTION_RESULT`.
- Exceptional self-hosting bootstrap record: `issuecomment-5405643748`.
- Reviewer finding requiring current-unresolved-obligation semantics: `issuecomment-5406357205`.
- Reviewer findings requiring concurrency-safe retirement and governed normalization ownership: `issuecomment-5406912928`.
- Reviewer provenance finding F5: `issuecomment-5407975502`.
- Canonical Human escalation for F5: `issuecomment-5408263684`.
- Direct-Human Option 1 decision: `issuecomment-5408291799`, declaring `Human-Decision-For: issuecomment-5408263684` and prospectively re-admitting the already-formalized Change scope.
- Bound Human-only approval event: Issue event `29967025795`, a later `human:approved` label event by `royhsu-work` with no GitHub App provenance.
- Production reproduction source: closed workflow #91 with canonical completion comments `5333895069` and `5335505763`; #91 is terminal history and is evidence of the responsibility-boundary defect, not a current recovery obligation.
- Baseline default-branch revision for this correction: `00a0e5a2c8068077faf5d18980e4a6f84f72f74e`.

### Current semantic-authority basis after F5

The historical Explore evidence remains factual context and is not retyped, rewritten, or promoted into an `ACTION_RESULT`. No synthetic Explore lifecycle event is created.

The provenance-qualified Human Option 1 decision prospectively establishes current Human authority for the already-formalized `fix-machine-dispatch-recovery-liveness` scope so this existing proposal can proceed without rewriting historical workflow evidence. This authority repair does not claim that the historical Explore produced the missing canonical result, does not turn the exceptional bootstrap into normal machine authorization, and does not alter the Change's behavioral scope. Independent `Reviewer / review-openspec` remains responsible for deciding whether this repaired provenance satisfies the current semantic review contract.

## Deferred work

The lightweight control-plane runtime optimization identified by #155 remains independently reviewable follow-up work: proving and adopting the minimum Python execution environment for the bridge/dispatch path should not be coupled to this authorization/recovery semantic correction.
