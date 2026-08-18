# scheduled-agent-workflow Delta Specification

## MODIFIED Requirements

### Requirement: Scheduled execution is at-least-once and state reconstructable

Every scheduled action SHALL reconstruct relevant durable repository, Issue, PR, OpenSpec, GitHub Actions, and any specifically awaited external resource state before deciding what remains to be done.

The workflow MUST NOT require previous conversation memory or a previous scheduled run to have exited cleanly.

Partial execution, interruption, tool failure, or missing final response MUST NOT transfer ownership merely because some work was attempted.

When a prior operation failed after only some durable mutations completed, recovery SHALL distinguish observed durable mutations from intended-but-uncompleted work. If the current invocation can still write repository evidence, it SHALL preserve the existing canonical action/result/`EXECUTION_EXCEPTION`/cross-role `HANDOFF` evidence required by the owning action. If no repository evidence surface is writable, the run MUST NOT manufacture a durable workflow transition from external Scheduled Task output; a later wake SHALL reconstruct correctness from the repository state that actually exists.

When recovery evaluates an already-completed durable mutation or handoff, it SHALL also reconstruct whether valid causal-descendant evidence within the same coordination workflow proves that exact transition was already consumed by later lifecycle work. If such descendant evidence exists, recovery MUST NOT overwrite canonical routing to replay the earlier transition. It MAY repair only still-required non-routing journal evidence when that repair is non-contradictory. Ambiguous or contradictory consumption evidence MUST fail closed rather than authorize backward routing repair.

This consumed-transition guard is recovery-specific and MUST NOT be interpreted as a generic forward-only lifecycle rule; normal governed correction loops remain legal.

#### Scenario: Run stops after durable work but before handoff

- GIVEN a scheduled role completes durable action work
- AND the run terminates before routing changes
- WHEN a later run observes the same routing tuple
- THEN it reconstructs whether the durable action work already exists
- AND it performs only remaining legal work or the missing transition/handoff
- AND it does not require memory of the previous run

#### Scenario: Normal evidence write itself is unavailable

- GIVEN a catchable execution failure occurs
- AND the current invocation cannot write the normal coordination-Issue evidence surface
- WHEN no other repository-governed durable evidence surface is legally available
- THEN the invocation does not claim that a result, handoff, or ownership transfer became durable merely because external Scheduled Task output exists
- AND a later wake reconstructs from actual repository mutations and current routing

#### Scenario: Earlier merge transition already has causal descendants

- GIVEN merge mutation M and its accepted revision are already durable
- AND valid later lifecycle evidence in the same coordination workflow proves M's handoff was consumed
- AND a stale recovery attempt reconstructs M as already completed
- WHEN recovery evaluates whether to repair M's routing transition
- THEN recovery does not rewrite canonical routing back to M's immediate downstream owner/action
- AND it may repair only still-required non-routing journal evidence when safe
- AND legitimate separately governed correction loops remain unaffected

#### Scenario: Consumption evidence is contradictory

- GIVEN recovery reconstructs an already-completed durable mutation
- AND available same-workflow evidence is contradictory about whether its transition was consumed
- WHEN recovery evaluates routing repair
- THEN it fails closed
- AND it does not choose a lifecycle position by model inference
