# Design: Extract authoritative workflow topology

Explore source: `issuecomment-5363202052`.

## Decision 1: Separate topology ownership from shared execution governance

`agents/workflow.md` becomes the single runtime owner of end-to-end workflow topology: the normal action graph, correction loops, same-role/cross-role successor relationships, pre-Change Explore terminal outcomes, and formal terminal completion.

`agents/AGENTS.md` keeps shared execution semantics that apply regardless of where an action sits in the graph: dynamic dispatch/cardinality, durable reconstruction, Human authority, evidence consumption, work-conserving execution, Invocation Exit, exception handling, concurrency safety, validation evidence, and queue/admission rules.

Rationale: the demonstrated SSOT problem is duplicated topology ownership. Moving unrelated execution invariants would broaden the Change and replace one mixed owner with another.

## Decision 2: Preserve narrow local references in roles and Skills

Role files continue to define mission, authority, and ownership. Mapped Skills continue to define action-local preconditions, procedure, results, validation, recovery, and handoff behavior. They may identify the local legal target action needed to execute their own procedure, but global lifecycle meaning is referenced to `agents/workflow.md` rather than redefined as a second DAG.

Rationale: deleting every action name from local procedures would make execution less usable; the SSOT requirement forbids competing normative topology, not bounded operational references.

## Decision 3: Keep OpenSpec and runtime topology as distinct authority categories

Canonical `openspec/specs/scheduled-agent-workflow/spec.md` remains the approved requirement/acceptance source. It may specify externally observable lifecycle behavior and ownership constraints. `agents/workflow.md` is the runtime instruction source for topology after the reviewed Change is merged.

Rationale: capability requirements and runtime instruction loading are different responsibilities. Removing acceptance scenarios to avoid textual overlap would weaken specification traceability rather than solve runtime SSOT.

## Decision 4: Keep README orientational

README should describe the repository at a high level and link to `agents/workflow.md` for authoritative Scheduled-Agent topology. Any existing canonical-looking DAG or detailed transition restatement should be reduced to orientation/reference where needed.

## Decision 5: Preserve the current lifecycle exactly

This is a behavior-preserving governance refactor. The implementation must reconstruct current `main` and transfer the topology that is authoritative at implementation time, including:

- optional pre-Propose Explore and its decision-complete terminal outcomes;
- Propose → independent OpenSpec review → implementation → independent implementation review;
- exact-head Reviewer PASS → Executor merge → Lead post-merge continuation;
- archive preparation → independent archive review → Executor merge;
- post-#115 terminal path: Archive merge leaves the coordination Issue open, routes to `Lead / finalize-archive`, Lead persists `LIFECYCLE_COMPLETE`, then closes and re-observes the Issue;
- legal specification/implementation/archive correction loops;
- same-role continuation versus cross-role handoff relationships.

No action, role, transition, merge/review gate, dispatch rule, queue priority, Human authority boundary, or terminal ordering is intentionally changed.

## Validation strategy

Use focused executable/structural regressions that fail if:

1. `agents/workflow.md` is missing the authoritative topology or omits a current legal transition/terminal path;
2. `agents/AGENTS.md`, README, roles, or mapped Skills retain a second normative global topology definition where a reference is sufficient;
3. action-local mappings no longer agree with the authoritative topology;
4. the post-#115 terminal ordering or another existing lifecycle path changes during extraction.

Run the full Python quality suite and strict exact-head OpenSpec validation before implementation handoff.

## Trade-offs

A new governance document adds one file, but removes distributed topology ownership and synchronization pressure. A generated registry or machine workflow engine would offer stronger mechanical centralization but is unnecessary for the demonstrated problem and is explicitly out of scope.