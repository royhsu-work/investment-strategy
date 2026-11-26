## MODIFIED Requirements

### Requirement: Coordination Issue closure is the durable final lifecycle transition

A completion comment, Reviewer PASS, Archive merge, Lead terminal-verification decision, or statement that an Issue may be closed MUST NOT constitute completed coordination lifecycle by itself.

Implementation, implementation-correction, and final Archive PRs MUST NOT establish Issue-closing linkage to the persistent coordination Issue. The final Archive PR SHALL establish the repository-approved deterministic non-closing reference so Archive merge preserves traceability while leaving the coordination Issue open for required Lead terminal verification.

After Archive merge, Lead `finalize-archive` SHALL reconstruct the exact reviewed and merged Archive revision, canonical default-branch/archive state, required tracker state, cleanup/retention evidence, and applicable Human-input freshness. When those terminal conditions are satisfied, Lead SHALL persist `LIFECYCLE_COMPLETE`, then close the coordination Issue, re-observe `closed`, and only then treat the workflow as terminal.

If `LIFECYCLE_COMPLETE` is durable but the Issue close mutation or re-observation is missing, a later Lead run SHALL reconstruct the same terminal evidence and idempotently complete/re-observe the close. If the Issue is observed closed before valid `LIFECYCLE_COMPLETE` and terminal conditions, the lifecycle SHALL fail closed as premature completion and MAY use only the bounded shared premature-close recovery contract when its predicates prove one unambiguous unfinished candidate.

A closed Issue with valid `LIFECYCLE_COMPLETE` and observed close is terminal history and SHALL NOT consume normal formal-workflow cardinality.

A consumer qualifying an existing terminal retirement MUST use the exact bound terminal result, authoritative fresh `closed + no workflow routing` observation, and complete required lifecycle evidence. The result MUST be recorded before the closure and any Action-routing removal attributed to that retirement. Given one closure, either relative order of closure and the removal of the exact terminal Action is valid. A present Action-routing removal MUST match that exact Action and occur at most once in the bound retirement interval. A conflicting Action removal, multiple removals or closes, reopening, Action relabeling, or residual workflow routing MUST NOT qualify.

An otherwise qualified, compatible close-only history MAY qualify when the required evidence was acquired completely and no Action-removal event is recorded. Incomplete or failed evidence acquisition MUST NOT be reinterpreted as close-only history. A consumer MUST NOT replay an accepted retirement to produce a preferred event order.
#### Scenario: Authorized Archive PR merge completes the Issue natively

- GIVEN an authorized final Archive PR uses the repository-approved non-closing coordination-Issue reference
- WHEN GitHub merges that Archive PR
- THEN the coordination Issue remains open
- AND native Issue completion at Archive merge is no longer the normal lifecycle behavior
- AND routing continues to `Lead / finalize-archive`

#### Scenario: Archive state is correct but native completion is missing

- GIVEN the authorized Archive PR is merged
- AND canonical archived default-branch state satisfies final lifecycle conditions
- AND the coordination Issue remains open
- WHEN Lead runs `finalize-archive`
- THEN the open Issue is normal terminal-verification input rather than a missing native-close error
- AND Lead persists `LIFECYCLE_COMPLETE`, closes the coordination Issue, and re-observes `closed`

#### Scenario: Coordination Issue closes during implementation merge

- GIVEN the final Archive lifecycle has not reached valid `LIFECYCLE_COMPLETE`
- AND the coordination Issue becomes closed because an implementation PR established closing linkage
- WHEN a scheduled role reconstructs lifecycle state
- THEN the closed Issue is treated as premature illegal lifecycle state rather than successful completion
- AND normal archive completion is not inferred from the premature closure

#### Scenario: Archive merge leaves the Issue open for finalization

- GIVEN canonical archive state is produced by an authorized Archive PR merge
- AND the Archive PR carries the repository-approved non-closing reference
- WHEN GitHub applies the merge
- THEN the coordination Issue remains open
- AND routing continues to `Lead / finalize-archive`

#### Scenario: Lead completion closes the Issue

- GIVEN the authorized Archive PR is merged
- AND canonical archived default-branch state satisfies final lifecycle conditions
- AND the coordination Issue remains open
- WHEN Lead runs `finalize-archive`
- THEN Lead persists `LIFECYCLE_COMPLETE`
- AND then closes the coordination Issue
- AND re-observes `closed` before declaring terminal completion

#### Scenario: Completion is durable but close was interrupted

- GIVEN valid `LIFECYCLE_COMPLETE` is already durable for the final Archive merge
- AND the coordination Issue remains open because the close mutation or its re-observation was interrupted
- WHEN Lead reconstructs `finalize-archive`
- THEN Lead does not duplicate terminal verification meaning
- AND idempotently closes or re-observes the Issue as needed
- AND terminal completion requires the observed closed state

#### Scenario: Coordination Issue closes prematurely

- GIVEN valid `LIFECYCLE_COMPLETE` has not been established for the final Archive merge
- AND the coordination Issue becomes closed
- WHEN a scheduled role reconstructs lifecycle state
- THEN the closed Issue is treated as premature contradictory/recovery input rather than successful completion
- AND normal archive completion is not inferred from the premature closure

#### Scenario: Both terminal retirement event orders qualify

- GIVEN a valid exact terminal result is recorded before both retirement events
- AND one close and one removal of the exact terminal Action are observed in the same bound interval
- AND a fresh read observes closed with no workflow routing
- WHEN a consumer receives close before removal, removal before close, or either observable same-second ordering
- THEN it qualifies the same retirement without replaying any effect
- AND a dependency on that Issue can release only its own edge

#### Scenario: A later result cannot qualify an earlier retirement effect

- GIVEN the claimed result was recorded after the close or the attributed removal
- WHEN a fresh consumer observes the Issue is now closed with no workflow routing
- THEN the retirement does not qualify and the dependency remains suspended

#### Scenario: Contradictory terminal evidence does not release a dependency

- GIVEN claimed retirement evidence contains a different Action removal, multiple Action removals or closes, reopening, Action relabeling, or residual workflow routing
- WHEN a consumer reconstructs it
- THEN the evidence does not qualify and the dependency remains suspended

#### Scenario: Compatible legacy close-only retirement remains qualified

- GIVEN complete required evidence establishes a valid exact terminal result followed by one close
- AND no Action-removal event is recorded and fresh state is closed without workflow routing
- WHEN existing close-only compatibility rules apply
- THEN the lack of an Action-removal event alone does not prevent qualification

#### Scenario: Incomplete acquisition cannot stand in for a legacy close-only history

- GIVEN the required lifecycle evidence could not be acquired completely
- WHEN a consumer has a partial observation without an Action-removal event
- THEN it does not qualify the retirement as close-only
- AND the dependency remains suspended
