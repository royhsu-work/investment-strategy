# Design: Governance SSOT and lifecycle execution boundaries

## Context

#29 combines one structural governance problem with two demonstrated execution failures whose correct fix depends on ownership placement.

Concrete duplication today includes:
- `README.md` carrying a detailed lifecycle flow and high-level role responsibilities that are also defined in `agents/AGENTS.md` and role files;
- shared Human escalation semantics appearing in `agents/AGENTS.md`, `agents/roles/lead.md`, and `agents/skills/openspec-change/SKILL.md`;
- shared exception/continuation semantics being summarized again in role/skill-local text;
- `agents/scheduled-task-migration.md` saying three slots are retained even though both README and AGENTS state slot count/topology/cadence are external product configuration.

The runtime authority boundary is already clear in one important respect: Scheduled Agents load governance from the default branch. This design keeps that invariant and narrows each document to the kind of rule it owns.

## Decision 1: Use a rule-category ownership matrix instead of a new registry

No generated governance registry or metadata index is added. The new `repository-governance` capability defines the ownership matrix normatively. Runtime documents then reference the correct owner.

Target model:

```text
README                     Human/contributor entry + links
  ↓ references
agents/AGENTS.md            shared runtime protocol
  ├─ agents/roles/*.md      role authority/ownership
  └─ agents/skills/*        action procedure

openspec/config.yaml        OpenSpec authoring rules
openspec/specs/*            approved capability requirements
openspec/changes/*          proposed change, then archived history

external Scheduled Tasks   topology/cadence/product config
```

OpenSpec capability specs remain normative product/governance requirements, but they are not a second runtime prompt source. `AGENTS.md`/role/skill files are the executable default-branch protocol Scheduled Agents actually load. A capability requirement may require those runtime artifacts to behave a certain way without copying the full procedural text into the spec.

### Trade-off

There will still be semantic trace across spec → runtime implementation, because requirements and implementation cannot be literally one file. SSOT here means one authoritative owner **per rule category/abstraction level**, not eliminating requirement-to-implementation traceability.

## Decision 2: Keep brief orientation, remove competing normative copies

README and higher-level files may retain concise orientation for Humans, but detailed MUST/SHALL lifecycle behavior belongs only at the owning layer. In affected scope:
- README lifecycle diagram becomes a compact overview pointing to `agents/AGENTS.md`;
- AGENTS may map roles/actions but role-specific mission detail lives in role files;
- role files keep authority/ownership and refer to shared governance for generic exception/Human/wait rules;
- skills keep action-local sequences and refer to shared contracts instead of repeating generic semantics.

Reviewer checks duplicate authority only within the blast radius of the change being reviewed; this is not a repository-wide prose-lint requirement.

## Decision 3: Treat same-invocation CI settle as execution continuation, not scheduler state

The initial problem is latency amplification: a 10–30 second CI can become a full wake interval when the first `queued` or `in_progress` observation is immediately declared a cross-invocation wait.

The fix belongs in shared execution governance because Lead, Reviewer, Executor, and archive recovery can all wait on exact resources. The contract is behavioral:
- a first nonterminal read of a resource just caused by the current selected action is not enough to prove a real cross-invocation wait;
- while the invocation still has bounded execution opportunity, it may continue observing only that exact resource;
- success during that opportunity continues the same action;
- when the invocation can no longer continue boundedly, it yields and the existing #28 resume contract takes over.

We intentionally do **not** specify a fixed sleep, exact seconds, retry count, or durable observation budget. Those values depend on the external execution product and tool-call latency, and encoding them in repository state would couple runtime governance to scheduler implementation.

### Verification model

Tests should model state sequences rather than wall-clock sleeps:
- first observation nonterminal → bounded continuation is still legal;
- later same-invocation observation terminal → continue, not yield;
- execution opportunity unavailable → legal external wait;
- next wake → fresh-read exact resource per #28.

## Decision 4: Scheduler topology remains external product configuration

`agents/scheduled-task-migration.md` is migration/bootstrap documentation, not durable runtime state. The sentence that the migration retains three slots should be reframed as a current/historical deployment note, not a requirement.

No minimum slot count or reaction-time SLO is invented. If Human later wants a repository-observable responsiveness SLO, that is a separate approved requirement; the implementation may then choose scheduler topology to meet it.

## Decision 5: Prevent terminal dead-end before native close using existing actions

#28 exposed this sequence:

```text
Archive PR merge
→ Issue native-close
→ Lead discovers safely deletable temporary branch
→ deletion is Executor-owned
→ closed Issue only allows Lead/finalize-archive
→ dead-end
```

The smallest sufficient correction is to make the known cleanup obligation a **pre-close merge prerequisite**, not to create post-close routing.

Reordered path:

```text
Reviewer archive PASS
→ Lead / finalize-archive
   reconstruct known temporary branch obligations
→ MERGE_AUTHORIZED exact Archive head
→ Executor / merge-pr
   fresh-read known temporary branches
   clean safe Executor-owned temporary residue
   if blocked: do not merge; Issue stays open; hand back to Lead as needed
→ merge final Archive PR
→ native close
→ Lead terminal reconstruction
```

This reuses existing `finalize-archive` and `merge-pr` ownership. It does not add a tenth action, reopen semantics, or a branch-cleanup state machine.

### Why cleanup belongs immediately before merge

Lead has lifecycle judgment authority and must identify whether terminal obligations exist. Executor owns the deletion mutation. `merge-pr` is already the operational action that sits immediately before native close and already rechecks unsafe preconditions. Therefore it is the narrowest existing action that can guarantee known cleanup is completed before close.

## Decision 6: #28 remains authoritative for post-yield recovery semantics

This change does not rewrite #28's fresh-read-on-resume, minimum durable evidence, constrained branch integration, or no-identical-retry contracts. It only defines the earlier classification boundary for when a cross-invocation wait begins and reorders terminal cleanup to avoid the newly demonstrated dead-end.

## Traceability

| Requirement source | Spec | Design |
| --- | --- | --- |
| #29 body: SSOT / document ownership | `repository-governance` Requirements 1–3 | Decisions 1–2 |
| #29 `issuecomment-5292380147`: short-lived CI / wake topology | `scheduled-agent-workflow` async-wait + topology requirements | Decisions 3–4 |
| #29 `issuecomment-5293197049`: post-close cleanup dead-end | `scheduled-agent-workflow` pre-native-close cleanup requirement | Decision 5 |
| #28 archived recovery contract | modified scheduled-agent spec preserves existing resume/recovery semantics | Decision 6 |

## Deferred / Non-goals

- Explore lifecycle (#38).
- Skill authoring/maintenance and broader project-wide simplicity work (#35).
- Human provenance/security changes.
- External Scheduled Task configuration changes.
- Automated branch garbage collection.
- New post-close Executor routing unless future evidence proves pre-close ordering insufficient.
