## MODIFIED Requirements

### Requirement: Review and finalize actions have Lead-owned minimum gate contracts

The repository specification SHALL define the minimum checks and legal result categories for the three Reviewer gates and the two Lead finalize actions. Procedural skills MAY operationalize these checks but MUST NOT invent or weaken them.

`review-openspec` SHALL, at minimum:

- inspect the current OpenSpec change revision;
- verify forward traceability `proposal → specs → design → tasks` and reverse traceability `tasks → design → specs → proposal`;
- verify contract/scope coherence and compatibility with repository `README.md` and `openspec/config.yaml` governance that applies to the change;
- consume the shared substantive direct-Human input freshness/disposition contract before finalizing the review result when newer coordination-Issue input could affect scope, traceability, or gate validity;
- produce actionable findings when a material problem exists;
- produce only `PASS` or `FINDINGS` as the gate result; and
- bind the result to the reviewed repository/branch revision.

`review-implementation` SHALL, at minimum:

- inspect the current implementation PR head revision;
- compare implementation and task-completion state with the approved OpenSpec contract;
- inspect the relevant diff, tests, quality checks, and OpenSpec validation evidence;
- verify scope discipline and absence of unauthorized contract redefinition;
- consume the shared substantive direct-Human input freshness/disposition contract before finalizing the gate when newer coordination-Issue input could affect correctness, approved scope, traceability, or gate validity;
- classify material findings as implementation findings or specification findings;
- bind `PASS`/findings to the reviewed PR head revision; and
- on an unambiguous exact-head PASS, route directly to `Executor / merge-pr` without requiring an intervening Lead merge-authorization action.

`review-archive` SHALL, at minimum:

- inspect the current archive PR revision and the intended source change;
- verify the intended change is being archived from the correct merged default-branch state;
- verify resulting canonical specs represent the approved contract, active change state is removed as intended, archived history is preserved, and unrelated changes are absent;
- inspect strict OpenSpec and applicable repository validation evidence;
- verify that Lead-owned pre-review Archive lifecycle preparation is durably reconstructable for the same coordination workflow, including required separate-follow-up tracker state and any explicitly provenance-owned temporary correction/recovery cleanup obligation that must be satisfied before native close;
- consume the shared substantive direct-Human input freshness/disposition contract before finalizing the gate when newer coordination-Issue input could affect archive correctness, lifecycle preparation, or gate validity;
- bind `PASS`/findings to the reviewed archive PR revision; and
- on an unambiguous exact-head PASS, route directly to `Executor / merge-pr` without requiring an intervening Lead merge-authorization action.

`finalize-change` SHALL, at minimum:

- after an implementation merge, reconstruct actual default-branch/OpenSpec/archive state and choose only a legal outcome such as `MORE_IMPLEMENTATION_REQUIRED`, `WAITING_FOR_ARCHIVE_AUTOMATION`, `ARCHIVE_PR_READY`, or a repository-defined recovery decision;
- when a validated archive branch is ready, create or reuse the final Archive PR with the repository-approved closing linkage;
- before routing that Archive PR to `Reviewer / review-archive`, reconstruct every still-applicable approved required separate-follow-up obligation and ensure each has its required durable tracker;
- before routing that Archive PR to `Reviewer / review-archive`, reconstruct any separately workflow-owned temporary correction/recovery branch from explicit durable provenance and classify the pre-native-close cleanup/retention obligation without treating the normal `agent/archive-<change>` branch as temporary cleanup input;
- consume the shared substantive direct-Human input freshness/disposition contract before a lifecycle result or handoff when newer coordination-Issue input could materially affect the lifecycle judgment; and
- fail closed instead of handing the Archive PR to Reviewer when those Lead-owned preparation obligations are ambiguous, missing, or contradictory.

`finalize-archive` SHALL, at minimum:

- execute only after the final Archive PR merge/native-close boundary or when reconstructing that already-completed boundary;
- reject stale or contradictory terminal evidence;
- reconstruct canonical default-branch/archive state, the exact reviewed Archive PR head and merge commit, observed native Issue completion, required separate-follow-up tracker state, and pre-merge temporary correction/recovery cleanup/retention evidence;
- consume the shared substantive direct-Human input freshness/disposition contract before persisting terminal completion when newer coordination-Issue input could materially affect the terminal judgment; and
- persist `LIFECYCLE_COMPLETE` only when final lifecycle conditions are actually satisfied, using explicit Issue-close recovery only when canonical archive merge is complete but the expected native close is missing.

#### Scenario: Reviewer performs OpenSpec review

- GIVEN a coordination Issue is routed to `Reviewer / review-openspec`
- AND an OpenSpec change revision is identified
- WHEN Reviewer executes the gate
- THEN Reviewer checks bidirectional traceability, contract/scope coherence, and applicable repository governance
- AND records revision-bound `PASS` or actionable `FINDINGS`
- AND the procedural skill does not invent additional contract meaning to make the gate pass

#### Scenario: Lead evaluates implementation merge authorization

- GIVEN Reviewer recorded an unambiguous implementation PASS for exact revision R
- AND the implementation PR is still at R
- WHEN `review-implementation` completes its legal PASS result
- THEN routing moves directly to `Executor / merge-pr`
- AND no normal Lead `MERGE_AUTHORIZED` action or replacement authorization token is required between review and merge
- AND Executor still fresh-reads all merge preconditions before mutation

#### Scenario: Archive preparation completes before independent review

- GIVEN merged implementation/default-branch state has produced a validated archive branch and final Archive PR
- WHEN Lead prepares the Archive PR for `review-archive`
- THEN Lead reconstructs required separate-follow-up tracker obligations before the handoff
- AND Lead reconstructs any separately provenance-owned temporary correction/recovery cleanup obligation before the handoff
- AND the normal `agent/archive-<change>` branch is not classified as temporary recovery input
- AND unresolved Lead-owned preparation blocks review handoff rather than being deferred until after Reviewer PASS

#### Scenario: Archive review PASS routes directly to merge

- GIVEN Reviewer recorded an unambiguous archive PASS for exact revision R
- AND the reviewed lifecycle-preparation evidence remains applicable
- WHEN `review-archive` completes its legal PASS result
- THEN routing moves directly to `Executor / merge-pr`
- AND no normal Lead `MERGE_AUTHORIZED` action or replacement authorization token is required between archive review and merge
- AND Executor still fresh-reads all Archive merge and cleanup preconditions before mutation

#### Scenario: Human asks material question before implementation review PASS

- GIVEN Executor has handed an implementation PR to `Reviewer / review-implementation`
- AND a newer direct-Human coordination-Issue comment asks a question that may affect approved scope or traceability correctness
- AND that exact comment has no durable disposition
- WHEN Reviewer evaluates PASS for the current implementation head
- THEN Reviewer MUST NOT record PASS while silently ignoring the comment
- AND Reviewer dispositions it through the legal review finding, bounded answer, or owner-routing path before the gate can complete

### Requirement: Scheduled execution is at-least-once and state reconstructable

Every scheduled action SHALL reconstruct relevant durable repository, Issue, PR, OpenSpec, GitHub Actions, and any specifically awaited external resource state before deciding what remains to be done.

The workflow MUST NOT require previous conversation memory or a previous scheduled run to have exited cleanly.

Partial execution, interruption, tool failure, or missing final response MUST NOT transfer ownership merely because some work was attempted.

Before a Scheduled role persists a consequential workflow result or completes a routing ownership transition, it SHALL fresh-read the persistent coordination Issue for direct-Human comments newer than the durable workflow evidence boundary on which the pending decision relies. The same freshness/disposition contract applies at an unsafe merge mutation through the merge requirement below.

A candidate comment counts as direct-Human input for this freshness contract only when durable raw creation provenance identifies the designated Human actor and shows creation was not performed via a GitHub App. This classification is an input-freshness safeguard only and MUST NOT itself satisfy a Human-reserved admission, answer, authorization, resume, or risk/scope decision; those boundaries continue to require their separately governed provenance-bound predicate and exact decision reference.

If newer direct-Human input could materially affect correctness, approved scope, traceability, gate validity, lifecycle preparation, or mutation assumptions, the current role MUST NOT silently proceed from its older snapshot. Before the consequential boundary completes, the exact comment id SHALL have one reconstructable durable disposition that is legal for the current authority boundary: addressed within current authority with bounded rationale; classified non-blocking with a bounded reason when clearly informational, administrative, or immaterial; converted into an existing action-defined finding/blocker/correction result; or routed/escalated to the legal role or Human-reserved boundary. A role MUST NOT answer outside its existing authority merely to clear the disposition requirement.

A prior valid disposition SHALL identify the exact Human comment id so later wakes can reconstruct that it is already handled without a comment queue, unread counter, acknowledgement label, hidden registry, or new lifecycle state. A direct-Human comment that appears after action start but before the consequential boundary is newer evidence at the final fresh-read. Missing raw provenance, ambiguous materiality, or an unresolved legal disposition MUST fail closed at that boundary rather than assume the older snapshot remains complete.

When a prior operation failed after only some durable mutations completed, recovery SHALL distinguish observed durable mutations from intended-but-uncompleted work. If the current invocation can still write repository evidence, it SHALL preserve the existing canonical action/result/`EXECUTION_EXCEPTION`/cross-role `HANDOFF` evidence required by the owning action. If no repository evidence surface is writable, the run MUST NOT manufacture a durable workflow transition from external Scheduled Task output; a later wake SHALL reconstruct correctness from the repository state that actually exists.

When recovery evaluates an already-completed durable mutation or handoff, it SHALL also reconstruct whether valid causal-descendant evidence within the same coordination workflow proves that exact transition was already consumed by later lifecycle work. If such descendant evidence exists, recovery MUST NOT overwrite canonical routing to replay the earlier transition. It MAY repair only still-required non-routing journal evidence when that repair is non-contradictory. Ambiguous or contradictory consumption evidence MUST fail closed rather than authorize backward routing repair.

This consumed-transition guard is recovery-specific and MUST NOT be interpreted as a generic forward-only lifecycle rule; normal governed correction loops remain legal.

After a selected action persists its durable result and legally changes routing, the invocation MAY continue to the next action only when all of the following are true:

- the selected coordination Issue is unchanged;
- the target role equals the fixed invocation role;
- the target routing is current after a fresh read;
- the target action is immediately actionable without Human authority, a real external asynchronous wait, ambiguity, or unsafe/stale state; and
- the target action reloads its mapped default-branch skill and reconstructs its own required durable state and preconditions before mutation.

The invocation MUST stop at the first cross-role transfer, unresolved Human boundary, real external asynchronous wait, ambiguity/unsafe state, stale/concurrency loss, or actual execution interruption. Same-role continuation MUST NOT process a second coordination Issue or introduce a timer, continuation counter, lease, heartbeat, hidden dispatcher, or second workflow state machine.

A first `absent`, `queued`, or `in_progress` observation of the exact required external resource just created or triggered by the selected action MUST NOT by itself be treated as a real cross-invocation asynchronous wait while bounded same-invocation execution opportunity remains. The action SHALL confine bounded observation to that same exact resource and, if it becomes terminal during the invocation, SHALL consume that terminal result immediately when the current action remains authorized. A later wake resuming a real wait SHALL fresh-read the exact awaited resource before yielding again.

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

#### Scenario: Same-role action becomes immediately actionable

- GIVEN one invocation selected coordination Issue I with fixed role Lead
- AND Lead action A persisted its result and legally routed I to another Lead action B
- AND no Human, asynchronous, ambiguous, stale, or unsafe boundary exists
- WHEN the invocation fresh-reads I and reconstructs B
- THEN it loads B's mapped default-branch skill
- AND continues B in the same invocation
- AND it does not select another Issue or redispatch to another role

#### Scenario: Cross-role routing ends the invocation

- GIVEN an invocation selected Issue I with fixed role Lead
- AND the current action legally routes I to Reviewer
- WHEN the routing mutation succeeds
- THEN the Lead invocation records the required cross-role handoff evidence
- AND ends without executing Reviewer work

#### Scenario: Just-triggered exact validation completes quickly

- GIVEN the selected action created or triggered exact required validation resource R
- AND the first observation of R is queued or in progress
- AND bounded same-invocation execution opportunity remains
- WHEN R becomes terminal during that invocation
- THEN the action consumes R's terminal result immediately when still authorized
- AND it does not voluntarily yield merely because the first observation was nonterminal

#### Scenario: Later wake resumes a real asynchronous wait

- GIVEN an earlier invocation yielded because exact awaited resource R remained nonterminal after bounded execution opportunity ended
- WHEN a later wake reconstructs the selected action
- THEN it fresh-reads R itself before concluding the wait still exists
- AND historical waiting evidence alone cannot justify another yield

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

#### Scenario: Human input arrives while Executor is preparing READY

- GIVEN Executor reconstructed an implementation snapshot and is correcting approved findings
- AND before Executor persists `READY`, a newer direct-Human comment appears that could materially affect correctness or scope
- WHEN Executor performs the consequential-boundary fresh-read
- THEN the older implementation snapshot is insufficient for READY
- AND Executor MUST disposition the exact comment within Executor authority or route the unresolved meaning to its legal owner before READY can be persisted

#### Scenario: Clearly non-substantive Human comment does not create lifecycle waiting state

- GIVEN a newer direct-Human comment is administrative or clearly immaterial to the pending workflow decision
- WHEN the current role evaluates the consequential boundary
- THEN it MAY record a bounded non-blocking disposition referencing that exact comment id
- AND the workflow MAY continue without creating a new waiting status, lifecycle action, blocker label, or Human-approval ceremony

#### Scenario: Human-reserved decision remains provenance-bound

- GIVEN a newer direct-Human comment contains a statement about a decision that governance reserves to Human authority
- WHEN a Scheduled role evaluates that statement
- THEN this freshness/disposition contract does not itself authorize the decision
- AND the existing exact `Human-Decision-For` plus qualifying provenance-bound approval predicate remains required at the mapped Human-reserved boundary

#### Scenario: Question belongs to another role authority

- GIVEN a newer direct-Human comment raises a material specification/scope question while Executor or Reviewer owns the current action
- WHEN the current role cannot legally resolve that meaning within its authority
- THEN it MUST NOT answer outside its role merely to mark the comment handled
- AND it dispositions the comment by using the existing finding/blocker and routing path to the legal owner

#### Scenario: Repeated wake recognizes prior exact-comment disposition

- GIVEN a direct-Human comment C was previously durably dispositioned by exact comment id under a legal action result, finding, answer, or routing boundary
- WHEN a later wake reconstructs the same coordination Issue
- THEN C does not require a duplicate acknowledgement or disposition
- AND only newer or materially unresolved direct-Human input remains relevant to the current consequential-boundary fresh-read

#### Scenario: Connector-authored workflow message is not reclassified as direct-Human input

- GIVEN a coordination-Issue comment is attributed to the designated account but raw creation provenance shows it was performed via a GitHub App
- WHEN a Scheduled role evaluates the Human-input freshness contract
- THEN that comment is not classified as direct-Human input
- AND its actor identity alone neither creates this disposition obligation nor grants Human authority

### Requirement: Executor merges only an explicitly authorized unchanged revision

Executor SHALL execute `merge-pr` only when durable evidence establishes:

- an unambiguous independent Reviewer PASS for exact revision R under the required implementation or archive gate;
- the current target PR head still equals R;
- the required checks remain valid and non-contradictory;
- the shared substantive direct-Human input freshness/disposition contract has been consumed at mutation time for newer coordination-Issue input that could affect accepted meaning or merge assumptions; and
- all path-specific lifecycle and linkage preconditions required by the current merge target remain satisfied.

The exact-head Reviewer PASS is the normal durable acceptance authority for the merge action. The workflow MUST NOT require a second Lead `MERGE_AUTHORIZED(R)` token, or an equivalent replacement token under another name, solely to repeat the accepted revision/gate state.

If the target revision, Reviewer gate, required checks, lifecycle preparation, Human-input disposition state, or linkage state becomes stale or contradictory, Executor MUST NOT merge and SHALL route to the legal correction/diagnosis owner according to the action contract.

For implementation and implementation-correction PRs associated with a persistent coordination Issue, Executor SHALL verify before merge that the PR does not establish GitHub Issue-closing linkage to that coordination Issue. A closing linkage on an implementation PR is a lifecycle-contract violation and MUST fail closed rather than being merged.

For the final Archive PR, Executor SHALL verify before merge that the PR establishes the repository-approved closing linkage to the same persistent coordination Issue. That linkage is a final-lifecycle side effect only and MUST NOT substitute for Reviewer PASS, unchanged-head verification, current checks, pre-review lifecycle preparation, or any other merge precondition.

#### Scenario: Authorized implementation revision remains current without closing linkage

- GIVEN Reviewer PASS exists for implementation revision R
- AND the target PR head is still R
- AND no contradictory current gate or check evidence exists
- AND the implementation PR does not establish closing linkage to its coordination Issue
- WHEN Executor performs `merge-pr`
- THEN Executor may execute the merge mutation without a separate Lead authorization token
- AND the coordination Issue remains open for post-merge and archive lifecycle work

#### Scenario: Implementation PR would close the coordination Issue

- GIVEN an implementation PR is otherwise eligible for merge
- AND the PR establishes GitHub Issue-closing linkage to its persistent coordination Issue
- WHEN Executor evaluates `merge-pr`
- THEN Executor does not merge
- AND the closing linkage is treated as a lifecycle-contract violation requiring correction

#### Scenario: Archive PR has the approved closing linkage

- GIVEN Reviewer archive PASS exists for archive revision R
- AND the archive PR head is still R
- AND required checks and pre-review lifecycle preparation remain valid and non-contradictory
- AND any explicitly identified pre-close temporary correction/recovery cleanup obligation is cleared or has an approved durable retention disposition
- AND the Archive PR establishes the repository-approved closing linkage to its coordination Issue
- WHEN Executor performs `merge-pr`
- THEN Executor may execute the archive merge without a separate Lead authorization token
- AND GitHub native Issue completion caused by that merge is treated only as the expected final lifecycle side effect

#### Scenario: PR head changes after authorization

- GIVEN Reviewer accepted revision R1
- AND the PR head is now R2
- WHEN Executor evaluates `merge-pr`
- THEN Executor does not merge
- AND the PASS for R1 is not reused for R2
- AND the changed revision returns through the legal review/correction path

#### Scenario: Human input arrives after Reviewer PASS but before merge

- GIVEN Reviewer recorded exact-head PASS for revision R
- AND before `Executor / merge-pr` mutates the PR, a newer direct-Human comment appears that could invalidate a relied-upon merge assumption or the accepted meaning
- WHEN Executor performs mutation-time fresh-read
- THEN the older PASS alone is insufficient to authorize merge
- AND Executor MUST NOT merge until the exact comment is durably dispositioned through the legal owner/path and all resulting merge preconditions are current