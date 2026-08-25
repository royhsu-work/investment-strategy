# Design: Fix machine dispatch recovery liveness

## Context

Reviewer finding `issuecomment-5406357205` rejected the first proposal revision because its structural closed-workflow projection still made normal dispatch cost grow with repository history. #91 demonstrates the problem clearly: it is already terminal history, so its compatible duplicate completion journal is an audit/recovery-classification concern and must not be re-adjudicated on every unrelated wake.

Revision `4db9789ae96795ce6b7333af063dd1cbebd9006f` corrected that responsibility boundary, but Reviewer finding `issuecomment-5406912928` identified two remaining mutation-contract defects: terminal routing retirement relied on a full-label replacement as if fresh-read implied CAS, and the legacy normalization path introduced consequential multi-Issue mutation without a governed owner/activation boundary.

This design keeps the current-unresolved-obligation architecture and removes those two defects. Dispatch read-reduction ends when an exact Issue/Role/Action or exact closed-routing candidate is selected. The mapped Action's existing durable-evidence reconstruction remains independently governed and is not an optimization target of this Change.

## Design goals

1. Keep normal selection proportional to current unresolved work, not accumulated terminal history.
2. Preserve complete provenance-qualified current open-Issue reconstruction, WIP=1, deterministic pre-activation ordering, and model non-override.
3. Preserve bounded premature-close recovery without a second workflow registry, activation flag, cutover cursor, or hidden lifecycle status.
4. Make terminal routing retirement concurrency-safe and idempotent without treating fresh-read label replacement as CAS.
5. Give legacy/current closed-routing cleanup one existing governed owner and one-candidate mutation boundary rather than a bulk migration action.
6. Keep detailed terminal/recovery forensics exceptional and candidate-bound.
7. Preserve bounded machine diagnostics for `NO_WORK` / `FAIL_CLOSED`.
8. Preserve every existing action-specific evidence reconstruction/consumption obligation after `AUTHORIZE`.

## Decision 1: Normal dispatch consumes current unresolved obligations only

### Current shape

```text
current open Issues
  → formal cardinality
  → enumerate historical closed workflow-looking Issues
  → structural projection
  → maybe detailed recovery
  → authorize / pre-activation / NO_WORK
```

Even with structural screening, this remains `O(repository-history)` in steady state.

### Target shape

```text
complete current open-Issue snapshot
+ complete current closed-routing-debt set
  → classify current formal WIP / debt
      ├─ debt empty
      │    → sole formal / pre-activation / NO_WORK from current open state
      └─ debt present
           → bounded detailed classification for current debt candidates
                ├─ one terminal/retired candidate selected for cleanup
                ├─ one qualifying unfinished candidate selected for recovery
                └─ competing / ambiguous / incomplete debt → FAIL_CLOSED
```

Completed closed workflow history whose routing debt has been retired is not an authorization input. Historical Issue #91 therefore cannot block unrelated current work merely because its terminal journal contains compatible duplicate evidence.

## Decision 2: Any workflow-routing residue is current closed-routing debt

Do not add a durable recovery registry or a second lifecycle status.

A closed coordination Issue retaining any repository-governed workflow routing label is current debt. The observable signal is intentionally broader than a perfect `agent:<role> + action:<action>` tuple because interruption may occur between narrow routing-label removals:

```text
closed + agent:* + action:*  = routing debt
closed + agent:* only        = routing debt
closed + action:* only       = routing debt
closed + no workflow routing = terminal/retired history for normal selection
```

This reuses durable state the workflow already owns:

- legitimate open work is routed;
- a premature/manual close naturally leaves routing behind;
- an interrupted terminal retirement leaves at least one routing-label residue until cleanup completes;
- a completed terminal retirement leaves no workflow routing residue.

An out-of-band actor that both closes unfinished work and deliberately removes all workflow routing has erased the repository's current recovery signal. That is administrative corruption/repair territory; normal dispatch does not reconstruct all historical workflows on every wake to defend against arbitrary destructive rewrites.

## Decision 3: Terminal close + routing retirement is one logical idempotent effect, not one full-label replacement

Repository-owned formal terminal closure and legal pre-Change research closure (`NO_CHANGE_REQUIRED` / `NO_GO`) require the same logical postcondition:

```text
Issue state = closed
AND no workflow agent:* label
AND no workflow action:* label
AND every unrelated label is preserved
```

The implementation MUST NOT achieve this by computing a complete label set from a fresh read and replacing all labels. A fresh read does not serialize a later label write, and another actor may add an unrelated label between read and replacement.

The effect instead uses narrow replay-safe operations:

1. fresh-reauthorize the exact terminal close source action and exact Issue;
2. close Issue state without supplying a replacement label set;
3. fresh-read the same Issue;
4. for each currently observed workflow routing label on that Issue, fresh-check that the Issue remains the exact authorized terminal target and remove only that exact label through the narrow label-removal operation;
5. after each consequential removal, fresh-observe the Issue before continuing;
6. finish only after a fresh observation proves `closed + no workflow routing`; unrelated labels are never written/replaced by this effect.

If execution stops after close or after removing only part of the routing tuple, the remaining residue is current closed-routing debt and is recoverable by the same candidate-bound resolution semantics. Replaying an already-completed close or an already-removed routing label is unnecessary; reconstruction consumes durable postconditions and applies only missing narrow effects.

This is one **logical lifecycle effect** with an observable postcondition, not one atomic GitHub API request.

## Decision 4: Bounded closed-routing acquisition covers the full governed routing-label surface

Production acquisition uses a fixed number of complete paginated GitHub reads for `state=closed`, keyed by every repository-governed workflow routing label in the finite routing vocabulary:

- all `agent:<role>` labels for the three governed roles; and
- all `action:<action>` labels for the ten governed actions.

The results are deduplicated by Issue number, then each current Issue is validated from authoritative current state. Any closed Issue containing at least one workflow routing label remains in the debt set even when the other half of its tuple is absent.

Because successful terminal retirement removes all routing labels, the steady-state complexity property is:

```text
normal dispatch cost = O(current open work + current closed-routing debt)
```

not:

```text
O(all historical workflow Issues)
```

Incomplete pagination/provenance, inability to establish the complete fixed-label query set, or malformed current debt state fails closed.

## Decision 5: Existing `Lead / resolve-question` owns candidate-bound closed-routing resolution

Do not introduce a repository-owned bulk migration action, hidden startup hook, or one-time multi-Issue mutation pass.

The existing closed-workflow recovery boundary already belongs to `Lead / resolve-question`. This Change extends that same action narrowly so executable dispatch may authorize it for one exact closed-routing candidate with an explicit debt disposition.

For an exact selected candidate:

- **terminal/retired evidence** → Lead requests only the narrow routing-retirement effect for that same closed Issue; the Issue remains closed;
- **qualifying unfinished premature-close evidence** → existing bounded reopen semantics apply; immutable Change and preserved legal routing identity are retained, then a later fresh dispatch selects ordinary work;
- **ambiguous/incomplete/contradictory evidence** → no retirement or reopen request; fail closed;
- **candidate identity/current state changed before effect** → stale request is rejected; fresh classification is required.

The worker does not enumerate historical Issues and choose mutation targets by model judgment. Repository-owned executable acquisition/classification supplies the exact candidate and disposition envelope; repository-owned application fresh-reauthorizes the exact source action and exact candidate before each durable effect.

### Multiple debt candidates

A backlog of pre-existing terminal routed Issues may produce more than one current debt candidate during rollout. That does not authorize bulk mutation.

Executable classification may inspect the complete current debt set and, when authoritative evidence deterministically proves one or more candidates terminal/retired without inventing meaning, choose **at most one** deterministic terminal/retired candidate for `Lead / resolve-question` cleanup. Stable candidate ordering is by lower Issue number after terminal/retired classification; ordering is cleanup determinism only, not a workflow priority system.

An unfinished candidate MUST NOT be reopened while another unresolved debt candidate exists or while an open formal workflow exists. Multiple unfinished candidates, any ambiguous candidate that could be unfinished, incomplete enumeration/provenance, or contradictory debt evidence remains `FAIL_CLOSED`.

Therefore old routed terminal history drains one candidate at a time through a governed existing owner. No durable migration-complete marker is needed; once the debt set is empty, normal dispatch naturally enters steady state.

## Decision 6: Detailed recovery/retirement remains candidate-bound

When no closed-routing debt exists, no terminal comments, legacy archive state, Human-retirement evidence, or old closed-Issue history is fetched merely for selection.

When debt exists, detailed evidence is reconstructed only for the exact candidate(s) needed to classify current debt. A selected candidate is the only Issue the resulting `Lead / resolve-question` invocation may mutate.

The unfinished recovery predicates remain strict:

- persisted non-`unset` Change when formal recovery applies;
- one otherwise legal nonterminal routing identity reconstructable from durable evidence;
- unfinished lifecycle evidence;
- no valid terminal completion or qualifying Human termination/non-resumption decision;
- no competing open formal workflow;
- no other unresolved debt candidate before reopen.

The terminal-cleanup path requires terminal/retired evidence strong enough to prove that removing only routing residue cannot erase a live workflow obligation. Missing or conflicting required evidence fails closed and leaves the debt visible.

## Decision 7: Terminal replay semantics remain exceptional correctness

Detailed debt classification needs deterministic terminal evidence semantics:

```text
no valid completion
  → not-terminal

one or more valid mutually compatible completions
  → terminal-history

valid completions with conflicting immutable terminal facts
  → indeterminate
```

Compatible duplicate journals are idempotent at-least-once replay. Conflicting immutable revision/Archive identity remains indeterminate. This classifier protects recovery/cleanup correctness; it is not a reason to retain retired terminal history in normal dispatch input.

## Decision 8: Preserve strict current authorization boundaries

The new path still requires:

- complete current open-Issue enumeration;
- qualified provenance for current authorization-bearing fields;
- zero/one formal cardinality as applicable;
- current valid routing and immutable Change identity for open work;
- complete current closed-routing-debt enumeration across the finite governed routing-label set;
- deterministic combined pre-activation ordering for formal-zero;
- fresh action-entry dispatch and existing effect-time reauthorization.

Incomplete current evidence, multiple formal workflows, stale routing/Change contradictions, unresolved debt ambiguity, or execution failure remains `FAIL_CLOSED`.

## Decision 9: Dispatch optimization stops at the mapped-Action boundary

The selection fast path owns only the evidence needed to choose the exact current Issue/Role/Action or current closed-routing candidate. Once `AUTHORIZE` selects a mapped Action, that Action's default-branch governance and Skill continue to own reconstruction of all durable evidence they require.

Therefore this Change does **not** introduce a generic bounded-comment reader, comment-age cutoff, latest-comment shortcut, evidence index, summary substitute, or action-local evidence filter. If a mapped Action currently requires complete Issue-comment reconstruction, historical review findings, prior `ACTION_RESULT`/`HANDOFF`, Human-decision evidence, exact PR/review state, CI evidence, OpenSpec artifacts, or another durable input, the implementation must continue to provide that evidence under the existing action contract.

```text
dispatch selection
  → current metadata + current closed-routing debt
  → AUTHORIZE exact Issue/Role/Action

mapped Action execution
  → existing action-specific evidence reconstruction
  → no #155-induced filtering/truncation
```

## Decision 10: Publish bounded non-authorizing diagnostics

`DispatchDecision.reason` already exists in the executable classifier, but the issue-comment bridge drops it for `NO_WORK` and `FAIL_CLOSED`. Publish one bounded repository-owned `Reason` field for those non-authorizing decisions.

- `AUTHORIZE` keeps the exact Issue/Role/Action tuple and no model-selected substitute.
- `NO_WORK` / `FAIL_CLOSED` contain no tuple.
- `Reason` is diagnostic only and never routing/effect authority.

## Regression strategy

### Normal-path proportion regression

Model many completed closed workflows whose routing has been retired, including #91-compatible duplicate terminal journals, plus one current open formal or queued pre-activation candidate.

Expected:
- normal dispatch does not enumerate or fetch retired historical workflow Issues/comments;
- closed-routing queries return no retired terminal history;
- dispatch cost depends on current open state and current routing debt only;
- #91 cannot block current work after its routing debt has been retired.

### Action-evidence preservation regression

Model a selected mapped Action whose governing evidence includes an older Issue comment irrelevant to dispatch selection but required by that Action's current reconstruction contract.

Expected:
- dispatch authorizes without reading that comment for selection;
- after `AUTHORIZE`, mapped Action reconstruction still receives/evaluates it exactly as before;
- no dispatch optimization layer filters, truncates, summarizes, or substitutes for action-required evidence.

### Concurrent unrelated-label regression

Model terminal close authorization for an Issue with workflow routing and label `foo`. After the effect's fresh read but before routing removal, another actor adds unrelated label `security-review`.

Expected:
- the terminal effect never performs full label replacement;
- only exact workflow routing labels are removed;
- both `foo` and `security-review` remain after retirement;
- fresh postcondition proves closed + unrouted.

### Interrupted retirement regression

Model terminal close followed by removal of only the `agent:*` label before interruption, leaving `action:finalize-archive` on the closed Issue.

Expected:
- closed-routing acquisition still finds the Issue through the action-label query;
- the candidate is not treated as retired history;
- candidate-bound resolution removes only the remaining workflow residue after fresh terminal proof;
- no unrelated label is replaced.

### Premature-close regression

Model a coordination Issue closed while its valid nonterminal routing tuple remains attached.

Expected:
- bounded acquisition finds the exact candidate;
- one qualifying candidate at formal-zero routes `Lead / resolve-question`;
- the recovery invocation may only reopen that exact candidate under existing predicates;
- another unresolved candidate or an open formal workflow prevents reopen.

### Legacy routing-debt drain regression

Model rollout with several pre-existing closed routed terminal Issues including #91 and one genuinely unfinished or ambiguous candidate.

Expected:
- no bulk migration mutation is available;
- executable classification may select at most one proven terminal/retired candidate for cleanup per invocation;
- cleanup removes only that candidate's exact workflow routing residue;
- unfinished debt is never retired as terminal;
- multiple unfinished/ambiguous debt remains fail closed;
- after terminal debt is drained and only one qualifying unfinished candidate remains, existing recovery semantics may select it.

### Diagnostic and safety regressions

Keep/add cases proving:
- incomplete current open or closed-routing enumeration fails closed;
- multiple open formal workflows fail closed;
- duplicate compatible terminal journals classify terminal when exceptional code directly evaluates them;
- conflicting terminal identity remains indeterminate;
- direct-Propose admission and pre-activation ordering remain deterministic;
- non-authorizing bridge decisions expose bounded reason but no tuple;
- action-specific evidence completeness remains unchanged after an `AUTHORIZE` decision.

## Governance impact

This is a behavioral contract change. Canonical `scheduled-agent-workflow` must stop requiring a complete closed-history structural projection for normal selection and must define current routing-debt, partial-retirement observability, candidate-bound terminal cleanup, and concurrency-safe routing retirement while preserving the downstream action-evidence boundary.

`agents/AGENTS.md` needs the minimum matching shared-governance update. `agents/roles/lead.md` and `agents/skills/openspec-change/SKILL.md` need narrow updates because existing `Lead / resolve-question` becomes the explicit owner/procedure for executable-selected terminal routing-debt cleanup in addition to its existing unfinished premature-close recovery responsibility.

`agents/workflow.md` topology does not change: no new action or lifecycle node is introduced. Terminal routing retirement remains an effect/postcondition detail, and closed-routing cleanup is an exceptional branch of the existing `Lead / resolve-question` ownership boundary.

## Trade-offs

### Chosen: existing routing labels + candidate-bound cleanup through existing owner

Pros:
- no new registry, recovery label, lifecycle status, activation flag, cursor, migration action, or watermark;
- normal cost scales with unresolved work, not history;
- partial retirement remains naturally observable through any routing-label residue;
- narrow label removals preserve unrelated concurrent labels;
- legacy routed history drains through an existing governed action, one Issue at a time;
- interruption is reconstructable from durable state.

Cons:
- rollout may require multiple bounded cleanup invocations before all terminal debt is retired;
- a genuinely ambiguous legacy candidate intentionally blocks further unsafe recovery/normal work until resolved;
- out-of-band administrators can deliberately erase the entire recovery signal, treated as administrative corruption.

### Rejected: full-label replacement during terminal close

A fresh read is not CAS. Replacing the full label set can erase an unrelated label added concurrently and therefore violates the preserve-unrelated-label contract.

### Rejected: one-time bulk legacy migration

A multi-Issue mutation pass needs an independent governed owner, activation event, per-Issue authorization, stale-write handling, and interruption recovery. Candidate-bound cleanup through the existing `Lead / resolve-question` boundary provides the required transition without adding that machinery.

### Rejected: structural projection of every closed workflow

Still `O(repository-history)` and is the earlier Reviewer finding being corrected.

### Rejected: bounded or filtered mapped-Action comment reconstruction

This would weaken action evidence completeness and reintroduce missed-comment failures. It is outside this Change.

### Rejected: fixed cutover cursor/watermark or activation flag

Both introduce additional authoritative state that must stay synchronized with GitHub Issue reality. The routing-debt invariant already supplies the necessary durable signal.

### Rejected: new durable recovery registry/label

A separate registry duplicates state already represented by workflow routing residue and adds synchronization obligations.

### Rejected: cache terminal history

Caching requires invalidation/authority semantics and still leaves history in the authorization model.

### Deferred: lightweight Python runtime

The Python/`uv` execution-environment optimization remains independently reviewable follow-up work and is not coupled to this authorization-semantics correction.
