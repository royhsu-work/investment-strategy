# Design: Enforce dispatch cardinality preflight

## Context

The repository already owns the WIP=1 and complete-cardinality semantics in `agents/AGENTS.md` and canonical `scheduled-agent-workflow`. The incident behind #105 shows an enforcement gap rather than a need for a new lifecycle: a formal workflow existed for a substantial period before a different pre-activation Explore began, and later wakes continued the second workflow after the repository could already expose multiple formal active workflows.

Current execution is prompt/governance driven. There is no repository runtime dispatcher process invoked by Scheduled Tasks; the external Scheduled Task prompt is intentionally only a bootstrap that loads default-branch governance. Therefore adding an unused Python dispatcher or an external locking service would create a second mechanism without fixing the actual execution surface.

## Decision 1 — One shared dispatch-preflight procedure in `agents/AGENTS.md`

`agents/AGENTS.md` remains the authoritative owner of global dispatch semantics. Strengthen its current workflow-dynamic reconstruction wording into one concrete procedure that every wake performs before selecting a role/action:

```text
load default-branch governance
        ↓
obtain complete repository-wide durable Issue snapshot
        ↓
prove enumeration completeness
        ↓
classify:
  formal active
  terminal-pending
  bounded premature-close recovery candidates
        ↓
apply decision table
  0 → recovery/combined pre-activation queue
  1 → sole formal/terminal workflow
 >1 → FAIL CLOSED
  ? → FAIL CLOSED
        ↓
only then load selected role + mapped Skill
```

Completeness must be explicit. A result limit, first page, role-local query, a query that returns one plausible Issue, or a candidate-local read is not sufficient unless the tool/read contract proves the relevant repository-wide enumeration is complete. When a read surface reports completeness metadata, consume it. When pagination is required, exhaust the required pages. When the available surface cannot prove completeness, classify the result as indeterminate and fail closed.

This procedure is an operationalization of the existing canonical invariant, not a new workflow DAG.

## Decision 2 — Keep a small canonical decision table as the executable mental model

Add one compact decision table in shared governance rather than distributing priority prose across role/Skill files:

| formal/terminal cardinality | result |
| --- | --- |
| 0 | bounded recovery check, then combined pre-activation queue |
| 1 | only that formal/terminal workflow |
| >1 | fail closed |
| indeterminate | fail closed |

The table is deliberately cardinality-based. It must not contain model urgency, role priority between active workflows, or a "preferred winner" rule.

## Decision 3 — Pre-activation Skills reference, rather than duplicate, shared preflight

The first illegal incident action was pre-activation `explore-change`; formal activation then occurred in `propose-change`. Add narrow action-entry references to those two mapped Skills:

- `openspec-explore`: before substantive research, consume the shared pre-dispatch evidence and require formal/terminal cardinality zero plus selected-Issue equality with the deterministic combined-queue winner. If the evidence is stale, incomplete, or contradictory, stop/reconstruct before research.
- `openspec-change` (`propose-change` path): keep its existing immediate pre-write and post-write activation checks, but explicitly require those checks to use the same complete-cardinality contract rather than a candidate-local/partial enumeration.

Do not copy the whole decision table or repository-wide algorithm into either Skill. They reference the shared owner and add only action-specific preconditions.

### Skill provenance / modification rationale

No Skill is added or deleted.

- `agents/skills/openspec-explore/SKILL.md` — **modify** because the demonstrated first illegal action was an Explore that began despite existing formal WIP. The change is repository scheduling adaptation; it does not alter upstream OpenSpec Explore thinking semantics.
- `agents/skills/openspec-change/SKILL.md` — **modify** because Propose owns the formal activation write and already performs pre/post activation checks. The change narrows those checks to the shared complete-cardinality evidence source; it does not alter upstream OpenSpec proposal artifact semantics.

Other mapped Skills continue to load `agents/AGENTS.md` before acting. The strengthened shared pre-dispatch gate prevents role/action selection when multiple or indeterminate active state exists; copying the same global rule into every Skill would violate SSOT.

## Decision 4 — Multiple-active recovery remains outside normal Scheduled-Agent actions

If complete reconstruction yields multiple formal/terminal workflows, normal dispatch stops before a mapped action is selected. Scheduled roles do not:

- choose the older/newer workflow;
- apply action/role priority to select a winner;
- clear or rewrite Change identities;
- change routing to force cardinality one;
- create a recovery Issue or hidden fault state.

Human/maintainer may perform an administrative durable-state repair. The next wake then starts from current repository state and must independently pass normal preflight. The repository does not encode this incident's exact #86/#100 mutations as a generic automated rollback recipe.

This preserves the existing distinction between normal automated premature-close recovery (which already has explicit safe predicates) and an ambiguous multi-active governance fault.

## Decision 5 — Regression tests exercise state fixtures against the canonical decision table

Current tests predominantly assert that governance text contains required phrases. Add fixture-driven tests that model repository-state inputs and verify the canonical decision table and action-entry contracts.

To avoid a second production dispatcher, the test helper remains test-only and intentionally small. It represents only the four-way cardinality table and deterministic pre-activation ordering necessary to assert the documented contract. Tests also structurally verify that the authoritative table/procedure remains present in `agents/AGENTS.md` and that `openspec-explore` / `openspec-change` reference the shared preflight rather than re-defining it.

Required fixtures:

1. zero formal work + queued Explore/Propose → deterministic oldest combined winner;
2. one formal active + queued Explore → formal active only;
3. partial/incomplete enumeration → indeterminate/fail closed;
4. two formal active workflows → fail closed;
5. stale preflight where formal work appears before Explore action entry → Explore cannot begin;
6. Propose pre-write sees new active workflow → no activation write;
7. Propose post-write sees contradictory competing activation → stale stop;
8. external task name differs from repository-selected role → task name has no effect;
9. multiple-active state after administrative repair → next result is derived only from fresh repaired state;
10. parked/resumed work may not inherit old PASS/readiness in place of comparing then-current `main`.

The test helper is evidence for the documented decision function, not a new runtime authority surface.

## Decision 6 — External Scheduled Task configuration stays thin

No Scheduled Task prompt, task name, wake-slot count, or cadence change belongs in this Change. Existing external wakes continue to bootstrap:

```text
read current main governance
→ reconstruct durable state
→ derive role/action
```

The repository must remain correct with overlapping at-least-once wakes through reconstruction and stale checks. The incident does not justify a lock/lease because it persisted across widely separated wake windows and is explained by missing reliable enforcement of complete reconstruction.

## Traceability

- Proposal → modified canonical requirement `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- Requirement → Decisions 1–6.
- Decisions 1–4 → governance + narrow pre-activation Skill implementation slices.
- Decision 5 → fixture-driven RED/GREEN regression slice.
- Decision 6 → negative-scope tests/document checks ensuring external prompts do not become a second authority source.

## Risks and mitigations

### Risk: More pre-dispatch reads increase execution work

Mitigation: require only the minimum repository-wide enumeration necessary for cardinality, routing, and recovery classification. Do not add general repository scanning.

### Risk: "Defense in depth" duplicates global semantics

Mitigation: Skills only reference the shared preflight and state their local consumption precondition; the algorithm and decision table remain owned by `agents/AGENTS.md`.

### Risk: Fixture helper drifts into a second dispatcher implementation

Mitigation: keep it test-only, table-sized, and explicitly non-authoritative. Tests validate the default-branch governance text and examples together; no Scheduled Task calls the helper.

### Risk: Ambiguous multi-active repair becomes automated winner selection

Mitigation: specification explicitly keeps >1 cardinality fail-closed and requires Human/maintainer administrative repair outside normal Scheduled-Agent lifecycle execution.
