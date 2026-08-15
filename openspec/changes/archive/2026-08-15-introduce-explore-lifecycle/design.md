# Design: Optional Scheduled Explore before Propose

## Context

The current Scheduled workflow has exactly nine normal actions and no pre-Propose research contract. Human-admitted work enters `Lead / propose-change`; once selected, Lead persists a non-`unset` Change identity and authors formal OpenSpec artifacts. That is correct for concrete/buildable direction but too committal for fuzzy problems, feasibility research, or investigations that may legitimately conclude no repository change is needed.

Current upstream OpenSpec Explore is deliberately lighter: optional, conversation/investigation-oriented, able to read/search the codebase and compare approaches, but it creates no change folder, no planning artifacts, and no implementation. It transitions to Propose when the direction is clear. The repository adaptation therefore needs only enough additional durability and routing to make that behavior reconstructable across Scheduled wakes.

## Requirements trace

- R1 — Explore is optional and preserves problem-before-solution semantics: proposal What Changes 1/4; delta requirements `Optional pre-Propose Explore preserves upstream investigation semantics`.
- R2 — Explore must not activate a formal Change or create artifacts/code: proposal What Changes 1; delta requirements `Explore keeps formal Change activation in Propose`.
- R3 — queued Explore and direct Propose coexist deterministically under single-workflow safety: proposal What Changes 3; delta modified admission/discovery requirements.
- R4 — decision-complete outcomes include proposal-ready, terminal no-change/no-go, and Human decision: proposal What Changes 2/5; delta requirement `Explore exits on decision-complete dispositions`.
- R5 — cross-wake reconstruction uses bounded durable evidence, not a research state machine: proposal What Changes 4; delta requirement `Explore persists bounded reconstructable evidence`.
- R6 — existing roles/review separation/archive ownership remain unchanged: proposal Scope Boundaries; modified action-surface requirement.

## Decision 1: Add one Lead action, not a new role or workflow engine

Add `Lead / explore-change` as the tenth normal action. Lead already owns specification decisions, scope clarification, bounded blast-radius analysis, and Human escalation; exploration is the pre-specification form of that authority. A new Research/Architect role would duplicate authority and create a new cross-role boundary without a demonstrated safety requirement.

Mapped procedure: `agents/skills/openspec-explore/SKILL.md`.

The skill adopts only the upstream semantic core needed here. It is repository-owned runtime procedure after merge; Scheduled execution does not fetch mutable upstream instructions as authority.

## Decision 2: Explore stays `Change: unset`; formal activation remains in Propose

An Explore Issue remains a Human-admitted coordination/research Issue with:

```text
Change: unset
agent:lead
action:explore-change
```

Explore does not create `openspec/changes/<id>/`. When Human later authorizes a proposal-ready direction, the same persistent Issue is routed to `Lead / propose-change` while `Change:` is still unset. Existing Propose activation then chooses/persists the immutable Change id and creates formal artifacts.

This preserves a clean boundary:

```text
Explore = reversible/no-stakes investigation
Propose activation = commitment to a formal OpenSpec Change identity
```

No research id, hidden sequence, temporary Change id, or fake archived Change is introduced.

## Decision 3: Deterministic queueing replaces an Explore `in_progress` marker

A new `status:exploring`, claim, lease, or heartbeat is unnecessary. When no persisted formal Change or terminal-pending workflow exists, all valid Human-admitted pre-activation entries participate in one queue:

```text
Lead / explore-change, Change: unset
Lead / propose-change, Change: unset
```

Selection is earliest GitHub `created_at`, then lower Issue number. Because an open Explore remains the same earliest entry across wakes, it naturally remains selected until it reaches a terminal result or Human authorizes the transition to Propose. Later queued work cannot bypass it, and a later direct proposal cannot race formal activation because Propose must re-check the same deterministic pre-activation winner before persisting a Change id.

This reuses existing durable Issue identity and ordering rather than introducing a second active-research state machine.

Trade-off: a long-running Explore can block later queued work. That is consistent with the repository's one-workflow-at-a-time safety model. If future evidence shows that independent research should run concurrently, that is a separate concurrency-policy change.

## Decision 4: Explore admission is intentionally no-stakes; Propose requires Human intent

The routing action is the durable admission boundary:

- Human routes/adopts work as `Lead / explore-change` when asking for investigation without committing to implementation.
- Human routes/adopts concrete work as `Lead / propose-change` when authorizing formal change authoring.

Therefore `PROPOSAL_READY` does **not** automatically change the routing to Propose. Lead records a bounded proposal-ready conclusion and requests the Human decision to proceed using the existing `HUMAN_DECISION_REQUIRED` presentation/notification contract. A valid Human answer on the same Issue may then authorize Lead to route it to `Lead / propose-change` with `Change: unset`.

This mirrors upstream's no-stakes Explore → explicit user decision to Propose while reusing existing Human escalation machinery. It avoids adding an `explore:auto-propose` label or parsing informal text as hidden authorization state.

A Human can skip this entire boundary by admitting concrete work directly to `Lead / propose-change`.

## Decision 5: Decision completeness, not exhaustive research

Explore exits only when further investigation is no longer required to choose the next legal disposition. Lead does not need to enumerate every possible option or collect exhaustive evidence.

Material questions that could change the disposition must be one of:

- resolved by evidence;
- shown to be non-blocking;
- identified as a genuine Human intent/authority decision; or
- sufficient to establish current no-change/no-go.

Legal dispositions:

### `PROPOSAL_READY`

Evidence supports a concrete/buildable direction and Lead would not need to invent a material requirement or solution choice to author a bounded proposal. The next boundary is Human intent to proceed. The Issue stays open and routed to Explore until valid Human approval is reconstructed; after approval it transitions to Propose.

### `NO_CHANGE_REQUIRED`

The problem is already satisfied, is informational only, or otherwise does not require a repository change. Lead records the conclusion and may close the research Issue as completed. No OpenSpec Change is created.

### `NO_GO`

Current evidence shows the proposed direction is infeasible or unjustified. Lead records the blocking reason and, when identifiable, the material condition whose change would justify reconsideration. The research Issue may close as completed without creating a fake Change.

### `HUMAN_DECISION_REQUIRED`

Used only when repository/technical evidence cannot resolve a genuine Human intent/authority trade-off. The existing bounded, recommendation-bearing, no-repeat semantics apply. The Issue remains routed to Explore and resumes after authoritative Human input.

`SPECIFICATION_BLOCKED` remains a Propose/Resolve concept and is not used as a terminal Explore substitute.

## Decision 6: Minimal durable Explore evidence lives on the coordination Issue

Explore is conversation-first upstream; Scheduled execution needs only enough durable evidence to reconstruct across wakes. Use the existing Issue comment surface and canonical message presentation. A bounded Explore result includes, as applicable:

- problem/question investigated;
- relevant repository/external evidence inspected;
- material constraints and meaningful alternatives actually needed for the decision;
- conclusion and rationale;
- selected disposition;
- next Human/action boundary;
- material reconsideration condition for `NO_GO` when one is known.

Do not log every search/query/thought, create a research database, maintain completeness scores, or build a parallel proposal/spec/design/tasks DAG.

## Decision 7: No independent Explore review gate

Explore is not an approved behavior contract; it is investigation before committing to one. Requiring `Reviewer / review-explore` would turn the optional thinking action into a formal phase and add a new gate with no demonstrated safety benefit.

Independent semantic review begins after Propose has produced formal OpenSpec artifacts, through existing `Reviewer / review-openspec`.

## Decision 8: Bootstrap and activation compatibility

This Change (#38) itself is intentionally bootstrapped through the old authoritative `Lead / propose-change` path. Its feature-branch `explore-change` rules are review input only and cannot govern #38 before merge.

After the implementation is merged to `main`:

- existing active non-`unset` Changes continue under their current lifecycle and are not pulled backward into Explore;
- existing Human-admitted `Lead / propose-change` + `Change: unset` Issues remain valid direct-to-Propose entries;
- deferred research Issues intentionally waiting for Explore may be Human-routed/admitted to the new `Lead / explore-change` action;
- historical workflow evidence remains interpreted under the governance that was authoritative when it was created.

## Decision 9: Fixed-role and workflow-dynamic discovery share one pre-activation intake winner

Workflow-dynamic remains primary: formal active/terminal-pending workflow first; otherwise the earliest valid pre-activation entry across Explore and direct Propose is selected.

Legacy fixed-role mode keeps Lead lifecycle/blocker work ahead of new intake:

```text
resolve-question > finalize-archive > finalize-change > pre-activation intake
```

If none of those higher-priority Lead actions is eligible, fixed-role pre-activation intake uses the **same combined queue** as workflow-dynamic: valid Human-admitted `Lead / explore-change + Change: unset` and `Lead / propose-change + Change: unset` entries are ordered together by earliest GitHub `created_at`, then lower Issue number. The selected Issue's routing determines whether Lead executes Explore or Propose. There is no `explore-change > propose-change` priority inside pre-activation intake.

Reviewer and Executor retain their existing fixed-role action priorities and stable tie breakers. This preserves deterministic legacy behavior while ensuring the activation/admission contract has one coherent winner rule in both dispatch modes. Explore remains optional: an older direct-Propose Issue wins over a newer Explore Issue, and an older Explore Issue wins over a newer direct-Propose Issue.

## Bounded blast-radius analysis

Authoritative surfaces expected to change during implementation:

- `agents/AGENTS.md`: ten-action map, routing validity, deterministic pre-activation queue, invocation discovery, Explore terminal eligibility.
- `agents/roles/lead.md`: Explore authority/action mapping and terminal research closure authority.
- `agents/skills/openspec-explore/SKILL.md`: new action-specific procedure.
- `agents/templates/messages.md`: only if the existing `ACTION_RESULT` / `HUMAN_DECISION_REQUIRED` shapes cannot express Explore outcomes without duplication; prefer reuse.
- `openspec/specs/scheduled-agent-workflow/spec.md`: canonical capability contract from this delta.
- README/migration orientation only where needed; no duplicate normative runtime rules.
- governance tests covering action map, admission/discovery, no-artifact behavior, terminal closure, Human proposal boundary, and bootstrap compatibility.

Directly related sibling actions checked:

- `propose-change`: remains the only formal Change activation/artifact-authoring entry.
- `resolve-question`: remains for ambiguity after formal Change semantics exist; Explore does not replace it.
- `review-openspec`: remains first independent semantic gate after formal artifacts exist.
- idle advisory: remains non-routing; Human may convert/admit a recommendation into either Explore or direct Propose based on clarity.
- lifecycle/archive actions: unchanged except that terminal Explore closure is a separate pre-Change path and never uses Archive PR linkage.

## Alternatives rejected

### Force every issue through Explore

Rejected: conflicts with upstream optional semantics and adds latency to already concrete work.

### Let `PROPOSAL_READY` auto-activate a Change

Rejected: weakens the no-stakes meaning of Explore and turns exploratory admission into implicit implementation/change authorization.

### Give Explore a temporary Change id

Rejected: creates fake formal lifecycle state and requires cleanup/archive semantics for research that may end in no change.

### Add `status:exploring` or a lease

Rejected: deterministic earliest-open selection already preserves the single-workflow model across wakes.

### Add `review-explore`

Rejected: no approved artifact exists yet to independently gate, and current evidence does not justify a new role boundary.

## Deferred decisions

- Mid-change Explore/sub-problem investigation is not part of this MVP.
- Whether implementation/archive PRs can be consolidated remains separate deferred research after Explore is authoritative.
- Same-role multi-action continuation and deferred-follow-up ticket materialization are tracked separately and must not be pulled into this Change.