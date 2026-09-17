## ADDED Requirements

### Requirement: Merge acceptance preserves persistent coordination-Issue terminal authority

Repository-governed merge acceptance SHALL prevent GitHub-native textual closing semantics from closing the selected workflow's persistent coordination Issue before the repository terminal contract authorizes closure.

For every implementation, implementation-correction, and final Archive PR merge, a repository-owned executable native-closing preflight MUST evaluate the exact repository, exact persistent coordination Issue, exact PR and current head, lifecycle context, selected merge strategy, and the complete current presentation that can become effective on the default branch. Relevant presentation MUST include PR description/linkage, every included commit message that reaches the default branch under the selected strategy, and any generated merge/squash commit-message input whose effective message can establish native closing semantics.

The preflight MUST apply GitHub-native closing-reference semantics to the exact coordination Issue rather than using a broad keyword ban. A non-closing reference such as `Refs #N` MUST remain legal. A closing reference to an unrelated Issue MUST NOT be rejected merely by this coordination-lifecycle guard.

Acquisition completeness and provenance are part of the acceptance predicate. Missing commits, indeterminate presentation, unsupported/ambiguous merge-strategy message construction, changed exact head, or otherwise incomplete evidence MUST fail closed. A result bound to an earlier head or different effective presentation MUST NOT authorize the merge.

Reviewer MAY consume the deterministic repository-owned preflight result as independent review evidence but MUST NOT implement a separate native-closing parser. Executor MUST obtain a fresh result for the exact accepted head and effective merge presentation immediately before the merge mutation. A prior review/preflight result does not waive this fresh application-time check.

If an already-reviewed head contains an offending native closing reference to the coordination Issue, merge acceptance MUST fail. Correction SHALL produce a new acceptable exact head/presentation and SHALL re-enter the ordinary exact-head review and gate contracts; the workflow MUST NOT infer authority to force-push, rewrite history, or waive the invariant.

The final Archive PR is also non-closing. Persistent coordination-Issue closure remains exclusively a `Lead / finalize-archive` terminal effect after valid `LIFECYCLE_COMPLETE`; native textual merge side effects MUST NOT substitute for that effect. Existing premature-close/closed-routing-debt recovery remains exceptional safety handling rather than a normal merge path.

#### Scenario: Included commit closes the exact coordination Issue

- GIVEN PR P is an otherwise acceptable non-terminal merge for coordination Issue N
- AND P's body uses legal non-closing `Refs #N`
- AND one commit included in exact head R contains a GitHub-native closing reference `Resolve #N`
- WHEN Executor evaluates merge acceptance for R
- THEN the executable native-closing preflight rejects the merge
- AND the coordination Issue is not intentionally exposed to the textual closing side effect

#### Scenario: Ordinary non-closing reference remains legal

- GIVEN the complete exact-head presentation refers to coordination Issue N only with non-closing references such as `Refs #N`
- AND all other merge acceptance predicates pass
- WHEN the native-closing preflight evaluates the presentation
- THEN those non-closing references do not cause rejection

#### Scenario: Closing reference to an unrelated Issue is outside the lifecycle guard

- GIVEN the selected workflow coordination Issue is N
- AND the complete exact-head presentation contains a GitHub-native closing reference to another Issue M
- AND it contains no native closing reference to N
- WHEN the native-closing preflight evaluates the presentation
- THEN this coordination-lifecycle guard does not reject solely because M is referenced with closing grammar

#### Scenario: Exact head changes after validation

- GIVEN a native-closing preflight passed for PR head R1
- AND the PR current head becomes R2 before merge
- WHEN Executor evaluates the merge mutation
- THEN the R1 result is stale
- AND a fresh complete preflight for R2 is required

#### Scenario: Commit or presentation acquisition is incomplete

- GIVEN the runtime cannot prove the complete commit set or effective merge presentation for exact head R
- WHEN merge acceptance evaluates native-closing safety
- THEN the preflight fails closed
- AND the merge is not authorized by assuming the missing content is safe

#### Scenario: Merge strategy changes effective generated presentation

- GIVEN repository settings permit multiple merge strategies
- AND the selected strategy can generate an effective commit message from PR or merge inputs
- WHEN the preflight evaluates merge acceptance
- THEN it evaluates the effective presentation for that selected strategy
- AND it does not reuse a result produced for a different strategy or message construction

#### Scenario: Reviewer and Executor share one deterministic classifier

- GIVEN Reviewer needs native-closing evidence for exact head R
- WHEN Reviewer evaluates the implementation or archive gate
- THEN Reviewer consumes the repository-owned deterministic preflight result
- AND does not maintain a second parser
- AND Executor later re-evaluates the same repository-owned preflight against fresh exact-head/effective-presentation evidence immediately before merge

#### Scenario: Offending reviewed head requires ordinary correction and re-gating

- GIVEN exact head R passed an earlier review gate
- AND complete merge presentation for R is later proven to contain a native closing reference to coordination Issue N
- WHEN merge acceptance is evaluated
- THEN R is rejected for merge
- AND any corrected successor head must satisfy ordinary exact-head review and required gates again
- AND the workflow does not infer permission to rewrite history or waive the invariant

#### Scenario: Terminal closure remains Lead-owned after lifecycle completion

- GIVEN the final Archive PR for coordination Issue N is ready to merge
- WHEN Executor evaluates and merges that PR
- THEN its effective presentation remains non-closing for N
- AND the merge itself does not serve as workflow terminal closure
- AND only a later valid `Lead / finalize-archive` action after `LIFECYCLE_COMPLETE` may close N under the terminal effect contract
