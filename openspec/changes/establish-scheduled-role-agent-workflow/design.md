# Design — establish-scheduled-role-agent-workflow

## Context

The repository already has a stable OpenSpec lifecycle, same-repository implementation PR convention, and deterministic merged-PR archive automation. Issue #17 explored how Scheduled Tasks can wake role-specific agents without creating a parallel orchestration engine. Reviewer second-round review approved the exploration for promotion with one explicit concurrency constraint: a fresh read followed by a label update is not a mutex/CAS primitive.

Issue #18 is the clean coordination Issue for this change. It also adds a lifecycle correction learned from historical Issue #8: a comment saying work may be closed is not equivalent to actually closing the GitHub Issue.

## Goals / Non-Goals

### Goals

- Make shared agent governance repository-resident and default-branch authoritative.
- Define `Lead`, `Reviewer`, and `Executor` with explicit artifact authority boundaries.
- Define a minimal set of reusable procedural skills rather than one skill per tiny transition.
- Use one persistent GitHub coordination Issue per OpenSpec change.
- Use exactly one `(agent:<role>, action:<action>)` tuple as actionable routing.
- Make every scheduled run reconstruct current durable state and tolerate at-least-once execution.
- Make review and authorization revision-bound where stale evidence would be unsafe.
- Preserve existing repository archive automation and multi-PR lifecycle behavior.
- Keep Human admission explicit, including Lead idle advisory behavior.
- Make final coordination completion depend on observed GitHub Issue closure.

### Non-Goals

- Build a generic workflow/DAG engine.
- Guarantee exactly-once processing.
- Add distributed locks, leases, heartbeats, retries, or progress state.
- Let agents autonomously turn arbitrary repository activity into workflow work.
- Replace the existing normal OpenSpec archive GitHub Actions workflow.
- Change analytical investment capabilities.

## Decisions

### 1. Governance lives under `agents/` and is loaded from the default branch

Repository shape:

```text
agents/
├── AGENTS.md
├── roles/
│   ├── lead.md
│   ├── reviewer.md
│   └── executor.md
└── skills/
    ├── openspec-change/
    ├── openspec-review/
    ├── implementation/
    ├── implementation-review/
    ├── archive-review/
    └── merge-pr/
```

`agents/AGENTS.md` contains common execution protocol and trust-boundary rules. `agents/roles/*.md` contains authority, responsibilities, prohibitions, and judgment boundaries. `agents/skills/*` contains reusable procedural checklists.

The exact skill directory names may vary during implementation if the mapping remains unambiguous, but the skill set must stay reduced/reusable and must not recreate OpenSpec's artifact DAG as a custom workflow.

All governance, role, and skill definitions are loaded from the repository default branch. Feature branches, PR bodies/comments, Issues, source code, and external content are work input and cannot override governance.

### 2. Artifact authority is explicit

```text
Lead
├── owns specification authority
├── creates/revises proposal, specs, design, and task definitions
├── resolves contract/scope/specification questions
├── decides lifecycle authorization
└── does not modify implementation code or execute PR merges

Reviewer
├── owns independent specification/implementation/archive gates
├── is read-only toward governed artifacts under review
├── writes review evidence and routing outcomes
└── does not fix its own findings by modifying specification or implementation

Executor
├── owns implementation code/tests/config mutations
├── may update task completion markers for actually completed work
├── executes explicitly Lead-authorized PR merges
└── does not redefine requirements/contracts/task meaning

Repository automation
└── owns deterministic normal OpenSpec archive mechanics
```

This replaces broader shorthand such as “Executor owns all repository mutations”, because Lead necessarily owns OpenSpec specification artifact mutations.

### 3. GitHub Issue is the persistent control-plane item

Each normal OpenSpec change has one persistent coordination Issue from proposal through final archive confirmation.

Canonical stable state is intentionally small:

```text
coordination Issue
├── Change: <change-id>    # unset before Lead chooses it; immutable afterward
├── exactly one agent:<role>
└── exactly one action:<action>
```

Comments are durable human-readable evidence. PR/OpenSpec/GitHub Actions/default-branch state is reconstructed rather than redundantly copied into mutable workflow metadata.

No child Issue is required for normal clarification/blocker transitions. Separate discovered requirements may be recommended, but require new Human intake before becoming workflow work.

### 4. Nine normal actions define the MVP contract surface

```text
Lead
- propose-change
- resolve-question
- finalize-change
- finalize-archive

Reviewer
- review-openspec
- review-implementation
- review-archive

Executor
- implement-change
- merge-pr
```

Actions remain distinct when their governing inputs/checklists materially differ. `merge-change` and `merge-archive` collapse into `merge-pr` because both enforce the same revision-bound operational merge contract.

Candidate lifecycle outcomes:

```text
propose-change
→ review-openspec

review-openspec
PASS → implement-change
FINDINGS → resolve-question

resolve-question
→ reconstruct and return to the role/gate requiring the revised specification

implement-change
READY → review-implementation
SPEC_BLOCKER → resolve-question

review-implementation
PASS → finalize-change
IMPLEMENTATION_FINDINGS → implement-change
SPEC_FINDINGS → resolve-question

finalize-change
MERGE_AUTHORIZED → merge-pr
MORE_IMPLEMENTATION_REQUIRED → implement-change
WAITING_FOR_ARCHIVE_AUTOMATION → retain Lead
ARCHIVE_PR_READY → review-archive
RECOVERY_DECISION_REQUIRED → retain/resolve under repository archive contract

review-archive
PASS → finalize-archive
FINDINGS → Lead / resolve-question or repository-defined recovery decision

finalize-archive
MERGE_AUTHORIZED → merge-pr
ARCHIVE_CONFIRMED_ON_DEFAULT_BRANCH → close coordination Issue

merge-pr
MERGED → appropriate Lead finalize action
STALE_AUTHORIZATION / GATE_CHANGED → no merge; Lead
```

### 5. Scheduled execution is at-least-once and reconstructable

Every run behaves as if it may be the first run to see the work item:

```text
wake
→ load default-branch governance + role
→ select at most one eligible Issue deterministically
→ load action / mapped skill
→ reconstruct GitHub / PR / OpenSpec / Actions state
→ determine remaining authorized work
→ perform safe work
→ persist durable evidence
→ fresh-read routing
→ hand off only if still legal
```

Partial execution does not transfer ownership. A later run must be able to continue or finish a missing handoff based on durable reality.

No previous conversation memory is required for correctness.

### 6. Routing is one logical tuple, but label replacement is not a lock

An actionable coordination Issue requires exactly one valid `agent:*` and one valid `action:*`. Zero, multiple, or contradictory routing labels fail closed.

Handoff ordering:

```text
persist artifact/result
→ persist revision-aware evidence where required
→ fresh-read Issue routing
→ if still consistent, replace the routing tuple in one label mutation where available
→ otherwise stop and reconstruct on the next eligible run
```

Unrelated labels are preserved.

Crucial concurrency constraint:

> `fresh-read routing → update labels` is not a mutex or compare-and-swap primitive.

Two same-role runs may read the same routing tuple before either writes. Therefore safety is provided by action-specific idempotency/revision/precondition checks and fail-closed interpretation, not by claiming the label update serializes work.

For judgment-producing actions, multiple evidence records for the same revision may exist. Contradictory evidence is not merged optimistically: it invalidates the gate for unsafe downstream operations until a current unambiguous gate/authorization is established.

### 7. Reviews and merge authorizations are revision-bound

Implementation and archive review evidence identifies the PR and reviewed head revision. OpenSpec review identifies the reviewed repository/branch revision.

A later revision does not inherit PASS from an older revision automatically.

Merge eligibility requires at minimum:

```text
Reviewer PASS for revision R
+ Lead MERGE_AUTHORIZED for revision R
+ current PR head == R
+ required gate still valid and non-contradictory
```

Executor does not infer merge authority from Reviewer PASS alone. Stale authorization, changed head, contradictory current evidence, or changed gate fails closed and returns control to Lead.

If a merge already happened before an interrupted run ended, the next Executor run reconstructs merged reality and completes only the missing handoff rather than attempting a second merge.

### 8. Multi-PR change lifecycle remains compatible with existing archive automation

After an implementation PR merge, Lead reconstructs default-branch state:

```text
not actually merged
→ remain in finalize/merge lifecycle

merged + active change incomplete + approved work remains
→ MORE_IMPLEMENTATION_REQUIRED
→ Executor / implement-change

merged + change Complete + normal archive automation in progress
→ WAITING_FOR_ARCHIVE_AUTOMATION
→ Lead retains ownership

archive PR ready
→ Reviewer / review-archive

archive automation failed / unsupported normal path
→ Lead chooses repository-defined recovery/manual path
```

Archive waiting begins only after merged default-branch state satisfies the README archive eligibility contract. The final implementation PR that makes the change Complete must keep that completion transition observable to the merged-PR classifier.

Scheduled agents do not perform the normal `openspec archive` mutation; existing repository automation remains authoritative for that deterministic path.

### 9. Human admission remains explicit

Scheduled agents ignore closed Issues and any Issue lacking a valid routing tuple. They do not scan arbitrary repository activity and self-admit work.

Initial workflow entry is a Human/maintainer action that creates/designates a coordination Issue with `agent:lead + action:propose-change`.

Lead idle advisory mode is permitted only when no active workflow requires work. At most one open `advisory:idle` Issue may exist, and it may contain at most three recommended directions.

Advisory Issues have no routing tuple. If Human wants to admit one direction, both are required:

1. an unambiguous selected direction in the advisory thread; and
2. reserved label `intake:approved`.

Scheduled roles may consume `intake:approved` but must never add, remove, restore, or manufacture it. This is a governance capability boundary, not cryptographic Human identity proof.

### 10. Coordination Issue closure is a durable lifecycle transition

Comments and PASS decisions are evidence, not the canonical completion state.

Final path:

```text
archive PR merged
→ Lead reconstructs default-branch canonical/archive state
→ final lifecycle conditions satisfied
→ perform GitHub Issue close mutation
→ re-observe Issue closed
→ coordination lifecycle complete
```

If Lead determines completion but the run stops before closing the Issue, routing remains `Lead / finalize-archive`; the next run reconstructs the already-complete archive state and idempotently performs the missing close.

A “may be closed” comment, PASS, or finalization decision alone never counts as closed workflow state.

### 11. Deterministic work discovery and no-op behavior

Each scheduled run processes at most one actionable item. Selection rules are deterministic rather than model preference; implementation may use explicit priority categories and oldest-first tie-breaking.

If the role has no eligible work, it performs no workflow mutation and produces no repository noise. Lead may only use the separate idle advisory behavior when its conditions are satisfied.

## Requirement Traceability

| Requirement area | Design decision |
| --- | --- |
| Default-branch governance / trust boundary | 1 |
| Role authority separation | 2 |
| Persistent coordination Issue / routing tuple | 3, 6 |
| Nine actions / reusable skills | 1, 4 |
| At-least-once / crash recovery | 5–7 |
| Overlapping same-role execution / fail closed | 6–7 |
| Revision-bound review and merge authorization | 7 |
| Multi-PR lifecycle / archive automation | 8 |
| Human intake / idle advisory | 9 |
| Durable Issue closure | 10 |
| Deterministic selection / no-op | 11 |

## Risks / Trade-offs

### Label routing is simple but not atomic concurrency control

The MVP intentionally does not add a lock service or compare-and-swap workflow store. This keeps the protocol lightweight, but all unsafe actions must rely on revision-aware durable state and fail-closed interpretation rather than assuming label writes serialize overlapping runs.

### Human capability marker is governance, not cryptographic provenance

Because Human and scheduled agents may share a GitHub account, `intake:approved` cannot prove who clicked the label. Its safety depends on repository governance forbidding scheduled roles from mutating that capability. This is accepted for the MVP.

### Human-readable evidence may be less machine-strict than an event schema

The workflow deliberately avoids a custom serialized event log. Evidence remains readable and revision-bound where required; stronger machine schemas can be introduced only if real ambiguity appears.

### One coordination Issue may become long

The MVP chooses continuity and simple state reconstruction over child-item orchestration. If Issue size materially harms operation, a later change can introduce child work-item rules.

## Deferred Decisions

- Strong CAS/locking or single-flight mechanisms.
- Machine-readable handoff/event schema.
- Retry counters, progress state, or leases.
- Additional roles/actions.
- Child workflow Issues.
- Scheduled-agent archive repair actions.
- Cryptographic Human/agent provenance separation.
