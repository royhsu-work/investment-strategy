# Design: Fix machine dispatch recovery liveness

## Context

Reviewer finding `issuecomment-5406357205` rejects the first proposal revision because its structural closed-workflow projection still makes normal dispatch cost grow with repository history. #91 demonstrates the problem clearly: it is already terminal history, so its duplicate completion journal is an audit/recovery-classification concern and must not be re-adjudicated on every unrelated wake.

The revised design changes the responsibility boundary rather than making the old scan cheaper.

## Design goals

1. Keep normal selection proportional to current unresolved work, not accumulated terminal history.
2. Preserve complete provenance-qualified current open-Issue reconstruction, WIP=1, deterministic pre-activation ordering, and model non-override.
3. Preserve bounded premature-close recovery without a second workflow registry, activation flag, cutover cursor, or hidden lifecycle status.
4. Keep detailed terminal/recovery forensics exceptional and candidate-bound.
5. Preserve bounded machine diagnostics for `NO_WORK` / `FAIL_CLOSED`.

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
+ complete current unresolved closed-routing set
  → classify current formal WIP / recovery
      ├─ unresolved closed-routing set empty
      │    → sole formal / pre-activation / NO_WORK from current open state
      ├─ exactly one unresolved closed-routing candidate
      │    → detailed recovery for that candidate only
      └─ multiple / incomplete / contradictory
           → FAIL_CLOSED
```

Completed closed workflow history is not an authorization input. Historical Issue #91 therefore cannot block unrelated current work merely because its terminal journal contains duplicate compatible evidence.

## Decision 2: Reuse the existing routing tuple as the unresolved-close signal

Do not add a durable recovery registry or a second lifecycle status.

A coordination Issue that is closed while it still retains an `agent:<role> + action:<action>` routing tuple is a current unresolved closed-routing candidate. This reuses durable state the workflow already owns:

- legitimate open work is routed;
- a premature/manual/interrupted close naturally leaves that routing tuple behind;
- a legitimate terminal close retires routing at the close effect boundary.

Repository-owned terminal close effects therefore apply one logical Issue mutation that:

1. closes the Issue; and
2. removes the workflow `agent:*` and `action:*` routing labels while preserving unrelated labels.

The GitHub Issue update API can carry state and the complete preserved label set in one request after a fresh read, so this does not require an intermediate open-unrouted lifecycle state.

This applies to formal terminal close and pre-Change terminal research close (`NO_CHANGE_REQUIRED` / `NO_GO`). A successfully closed terminal Issue is closed and unrouted; it no longer appears in the unresolved-close query.

An out-of-band actor that both closes unfinished work and deliberately removes its routing tuple has erased the repository's current recovery signal. That is administrative corruption/repair territory; normal dispatch does not reconstruct all history on every wake to defend against arbitrary destructive rewrites.

## Decision 3: Normalize legacy routed history once; transition fails closed until clean

Existing terminal history predates the routing-retirement invariant, so some completed closed Issues may still retain workflow routing labels. Those old routed labels will initially appear in the same unresolved closed-routing set as a genuine premature close.

The rollout therefore includes one repository-owned bounded migration/reconciliation over the pre-existing closed routed set:

- detailed evidence proves terminal/retired → remove only `agent:*` / `action:*` routing labels, preserve unrelated labels and all historical comments/body/state;
- evidence proves a real unfinished obligation → leave/restore it as explicit current recovery work under the existing recovery contract;
- ambiguous/incomplete evidence → migration fails closed and the routing debt remains visible.

There is no separate activation flag or migration-complete marker. If the history-independent selector is present while legacy routed debt remains, that debt is visible as unresolved current state and normal dispatch may return `FAIL_CLOSED` until normalization succeeds. The repository MUST NOT hide or bypass those candidates merely to make rollout proceed.

After normalization succeeds, no cutover timestamp, cursor, watermark, migration registry, or recurring reconciliation state remains. The normalized durable invariant itself is sufficient:

```text
closed + workflow routing present = current unresolved recovery candidate
closed + workflow routing absent  = terminal/retired history for normal dispatch
```

## Decision 4: Bounded unresolved-close acquisition

Production acquisition uses a fixed number of complete paginated GitHub reads keyed by the existing three `agent:*` routing labels and `state=closed`, then deduplicates by Issue number and validates the current routing tuple/Change identity.

Because successful terminal close and the one-time legacy migration remove routing labels, these queries return unresolved routed closed work rather than accumulated terminal history. The steady-state complexity property is:

```text
normal dispatch cost = O(current open work + current unresolved close candidates)
```

not:

```text
O(all historical workflow Issues)
```

Incomplete pagination/provenance, malformed current routing, or inability to establish the current unresolved set is `FAIL_CLOSED`.

## Decision 5: Detailed recovery remains candidate-bound

When no unresolved closed-routing candidate exists, no terminal comments, legacy archive state, Human-retirement evidence, or old closed-Issue history is fetched merely for selection.

When exactly one candidate exists, detailed exceptional recovery evaluates only that candidate using the existing safety predicates:

- persisted non-`unset` Change when formal recovery applies;
- one otherwise legal nonterminal routing tuple;
- unfinished lifecycle evidence;
- no valid terminal completion or qualifying Human termination/non-resumption decision;
- no competing open formal workflow;
- no second unresolved recovery candidate.

One qualifying candidate at formal-zero routes `Lead / resolve-question`; coexistence with an open formal workflow, ambiguity, incomplete evidence, or multiple candidates remains `FAIL_CLOSED`.

The one-time legacy migration is the only rollout path allowed to classify and retire a pre-existing multi-Issue routed history set. Steady-state dispatch does not generalize that migration into repeated all-history repair.

## Decision 6: Terminal replay semantics remain exceptional correctness

Detailed recovery and the one-time migration still need deterministic terminal evidence semantics:

```text
no valid completion
  → not-terminal

one or more valid mutually compatible completions
  → terminal-history

valid completions with conflicting immutable terminal facts
  → indeterminate
```

Compatible duplicate journals are idempotent at-least-once replay. Conflicting immutable revision/Archive identity remains indeterminate. This classifier protects migration/recovery correctness; it is not a reason to retain terminal history in normal dispatch input.

## Decision 7: Preserve strict current authorization boundaries

The new fast path still requires:

- complete current open-Issue enumeration;
- qualified provenance for current authorization-bearing fields;
- zero/one formal cardinality as applicable;
- current valid routing and immutable Change identity;
- complete current unresolved closed-routing enumeration;
- deterministic combined pre-activation ordering for formal-zero;
- fresh action-entry dispatch and existing effect-time reauthorization.

Incomplete current evidence, multiple formal workflows, stale routing/Change contradictions, unresolved closed-routing ambiguity, or execution failure remains `FAIL_CLOSED`.

## Decision 8: Publish bounded non-authorizing diagnostics

`DispatchDecision.reason` already exists in the executable classifier, but the issue-comment bridge drops it for `NO_WORK` and `FAIL_CLOSED`. Publish one bounded repository-owned `Reason` field for those non-authorizing decisions.

- `AUTHORIZE` keeps the exact Issue/Role/Action tuple and no model-selected substitute.
- `NO_WORK` / `FAIL_CLOSED` contain no tuple.
- `Reason` is diagnostic only and never routing/effect authority.

## Regression strategy

### Normal-path proportion regression

Model a repository whose legacy migration has normalized many completed workflows including #91-compatible duplicate terminal journals, plus one current open formal or queued pre-activation candidate.

Expected:
- normal dispatch does not enumerate or fetch historical completed workflow Issues/comments;
- closed-routing queries return no normalized terminal history;
- dispatch cost depends on current open state and current unresolved closed-routing candidates only;
- #91 cannot block current work because it is terminal history.

### Premature-close regression

Model a coordination Issue closed while its valid nonterminal routing tuple remains attached.

Expected:
- bounded unresolved-close acquisition finds that exact Issue;
- detailed recovery evaluates only that candidate;
- one qualifying candidate at formal-zero routes `Lead / resolve-question`;
- coexistence with an open formal workflow or ambiguous/multiple candidates fails closed.

### Terminal-close regression

Model repository-owned terminal completion followed by the terminal close effect.

Expected:
- the close mutation preserves unrelated labels while removing `agent:*` / `action:*` routing;
- fresh observation sees the Issue closed and unrouted;
- later normal dispatch never includes it in the unresolved-close set.

### Legacy-migration regression

Model rollout with pre-existing closed routed terminal history. The history-independent selector sees that routing debt as unresolved and remains fail closed where necessary. One-time normalization classifies the bounded legacy routed set; proven terminal/retired entries become closed+unrouted, genuine unfinished work remains explicit, and ambiguous evidence keeps rollout fail closed. After normalization succeeds, no activation flag, cursor/state, or recurring history scan remains.

### Diagnostic and safety regressions

Keep/add cases proving:
- incomplete current open or unresolved-close enumeration fails closed;
- multiple open formal workflows fail closed;
- duplicate compatible terminal journals classify terminal when migration/recovery code directly evaluates them;
- conflicting terminal identity remains indeterminate;
- direct-Propose admission and pre-activation ordering remain deterministic;
- non-authorizing bridge decisions expose bounded reason but no tuple.

## Governance impact

This is a behavioral contract change. Canonical `scheduled-agent-workflow` must stop requiring a complete closed-history structural projection for normal selection and must define routing retirement/current unresolved-close semantics.

`agents/AGENTS.md` needs the minimum matching shared-governance update. `agents/workflow.md` topology does not change: the same actions and correction loops remain authoritative. Terminal routing retirement is an effect/postcondition detail, not a new lifecycle node.

No role or mapped Skill ownership change is intended.

## Trade-offs

### Chosen: existing routing labels + one-time normalization

Pros:
- no new registry, recovery label, lifecycle status, activation flag, cursor, or watermark;
- normal cost scales with unresolved work, not history;
- premature close produces a durable signal naturally because close does not erase routing;
- legitimate terminal close can retire routing in the same Issue mutation;
- legacy cost is paid once, then migration state disappears.

Cons:
- one-time migration must inspect the bounded pre-existing closed routed set during rollout;
- rollout may temporarily fail closed while legacy routing debt remains;
- out-of-band administrators can deliberately erase the recovery signal, which is treated as administrative corruption rather than something every normal wake must defend against by full-history replay.

### Rejected: structural projection of every closed workflow

Still `O(repository-history)` and is the Reviewer finding being corrected.

### Rejected: fixed cutover cursor/watermark

A fixed boundary avoids old history but still introduces another durable semantic marker. One-time normalization achieves the same steady-state property with less persistent state.

### Rejected: activation flag

A migration-ready flag would create another authoritative state bit that must stay synchronized with GitHub Issue reality. Transitional fail-closed behavior already provides the safe rollout boundary without that state.

### Rejected: new durable recovery registry/label

A separate registry or lifecycle label duplicates state already represented by the retained routing tuple and adds synchronization obligations.

### Rejected: cache terminal history

Caching requires invalidation/authority semantics and still leaves history in the authorization model.

### Deferred: lightweight Python runtime

The Python/`uv` execution-environment optimization remains independently reviewable follow-up work and is not coupled to this authorization-semantics correction.
