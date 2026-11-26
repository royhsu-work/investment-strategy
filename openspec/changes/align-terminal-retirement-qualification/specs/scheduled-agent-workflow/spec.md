## MODIFIED Requirements

### Requirement: Coordination Issue closure is the durable final lifecycle transition

A completion comment, Reviewer PASS, Archive merge, Lead terminal-verification decision, or statement that an Issue may be closed MUST NOT constitute completed coordination lifecycle by itself.

Implementation, implementation-correction, and final Archive PRs MUST NOT establish Issue-closing linkage to the persistent coordination Issue. The final Archive PR SHALL establish the repository-approved deterministic non-closing reference so Archive merge preserves traceability while leaving the coordination Issue open for required Lead terminal verification.

After Archive merge, Lead `finalize-archive` SHALL reconstruct the exact reviewed and merged Archive revision, canonical default-branch/archive state, required tracker state, cleanup/retention evidence, and applicable Human-input freshness. When those terminal conditions are satisfied, Lead SHALL persist `LIFECYCLE_COMPLETE`, then close the coordination Issue, re-observe `closed`, and only then treat the workflow as terminal.

If `LIFECYCLE_COMPLETE` is durable but the Issue close mutation or re-observation is missing, a later Lead run SHALL reconstruct the same terminal evidence and idempotently complete/re-observe the close. If the Issue is observed closed before valid `LIFECYCLE_COMPLETE` and terminal conditions, the lifecycle SHALL fail closed as premature completion and MAY use only the bounded shared premature-close recovery contract when its predicates prove one unambiguous unfinished candidate.

A closed Issue with valid `LIFECYCLE_COMPLETE` and observed close is terminal history and SHALL NOT consume normal formal-workflow cardinality.

The terminal formal result MUST causally precede the retirement effects attributed to it. A current consumer MUST prove the exact terminal Action and the observed `closed + no workflow routing` postcondition without requiring the close event and the removal of that Action's routing label to appear in either specific relative order. If a routing-removal event is attributed to this terminal retirement, it MUST correspond to the exact terminal Action and occur at most once. A conflicting Action removal, duplicate removal or close, reopening, relabeling, incomplete evidence, or residue of workflow routing MUST NOT qualify. A fresh consumer MUST NOT replay the already observed accepted retirement to manufacture a preferred event order.

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

#### Scenario: One qualified retirement can produce two valid event orders

- GIVEN the exact native terminal result was written and the Issue's retirement is observed closed with no workflow routing
- AND its complete lifecycle evidence has one close and, if present, one removal of the terminal Action route after the result
- WHEN a fresh consumer observes close before route removal, the opposite order, or a same-second event-ID ordering
- THEN it qualifies the same result and the dependency can release
- AND it does not replay the retirement or modify the dependency

#### Scenario: A contradictory retirement does not release the dependency

- GIVEN a claimed terminal retirement has a different Action removed, more than one route removal or close, a reopen/relabel, routing residue, or missing or mismatched required source evidence
- WHEN a fresh consumer reconstructs it
- THEN the terminal evidence does not qualify and the dependency remains suspended
