# Design: Fix machine dispatch recovery liveness

## Context

Reviewer finding `issuecomment-5406357205` rejects the first proposal revision because its structural closed-workflow projection still makes normal dispatch cost grow with repository history. #91 demonstrates the problem clearly: it is already terminal history, so its duplicate completion journal is an audit/recovery-classification concern and must not be re-adjudicated on every unrelated wake.

The revised design changes the responsibility boundary rather than making the old scan cheaper.

## Design goals

1. Keep normal selection proportional to current unresolved work, not accumulated terminal history.
2. Preserve complete provenance-qualified current open-Issue reconstruction, WIP=1, deterministic pre-activation ordering, and model non-override.
3. Preserve bounded premature-close recovery without a second workflow registry or moving cursor.
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
- a premature close naturally leaves that routing tuple behind;
- a legitimate terminal close retires routing at the close effect boundary.

Repository-owned terminal close effects therefore apply one logical Issue mutation that:

1. closes the Issue; and
2. removes the workflow `agent:*` and `action:*` routing labels while preserving unrelated labels.

The GitHub Issue update API can carry state and the complete preserved label set in one request after a fresh read, so this does not require an intermediate open-unrouted lifecycle state.

This applies to formal terminal close and pre-Change terminal research close (`NO_CHANGE_REQUIRED` / `NO_GO`). A successfully closed terminal Issue is closed and unrouted; it no longer appears in the unresolved-close query.

A manual or interrupted close that leaves routing attached remains visible as an explicit recovery candidate. Arbitrary administrative mutation that intentionally removes both routing and closes an unfinished Issue is outside normal Scheduled-Agent effect semantics and must be repaired administratively; normal dispatch does not reconstruct all history to defend against every possible out-of-band rewrite.

## Decision 3: Use a fixed cutover boundary, not perpetual migration state

Existing history predates the routing-retirement invariant, so old completed Issues may still be closed and routed. The new dispatcher must not mistake those historical artifacts for current recovery work.

Before steady-state activation, perform one bounded reconciliation of pre-cutover closed workflow history against exact authoritative evidence. The reconciliation must prove that every pre-cutover workflow obligation is either:

- terminal/retired history; or
- a real unresolved obligation that has been explicitly returned to current workflow/recovery state.

The implementation then pins one fixed recovery cutover boundary from that exact reconciliation evidence. The boundary is immutable for this behavior; it is not a moving cursor, TTL, cache watermark, lease, or hidden scheduler state.

Steady-state unresolved-close acquisition considers only closed routed Issues whose close/update is at or after that fixed cutover boundary. Historical pre-cutover terminal Issues are never rescanned by normal dispatch.

If reconciliation cannot prove pre-cutover completeness, the Change cannot activate the new fast path.

## Decision 4: Bounded unresolved-close acquisition

Production acquisition should use a fixed number of complete paginated GitHub reads keyed by the existing three `agent:*` routing labels and closed state, bounded by the fixed cutover boundary, then deduplicate by Issue number and validate the current routing tuple/Change identity.

The critical complexity property is:

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

## Decision 6: Terminal replay semantics remain exceptional correctness

Detailed recovery and one-time reconciliation still need deterministic terminal evidence semantics:

```text
no valid completion
  → not-terminal

one or more valid mutually compatible completions
  → terminal-history

valid completions with conflicting immutable terminal facts
  → indeterminate
```

Compatible duplicate journals are idempotent at-least-once replay. Conflicting immutable revision/Archive identity remains indeterminate. This classifier protects recovery correctness; it is not a reason to retain terminal history in normal dispatch input.

## Decision 7: Preserve strict current authorization boundaries

The new fast path still requires:

- complete current open-Issue enumeration;
- qualified provenance for current authorization-bearing fields;
- zero/one formal cardinality as applicable;
- current valid routing and immutable Change identity;
- complete current unresolved closed-routing enumeration after the fixed cutover;
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

Model a repository containing many pre-cutover completed workflows including #91-compatible duplicate terminal journals, plus one current open formal or queued pre-activation candidate.

Expected:
- normal dispatch does not enumerate or fetch those historical workflow Issues/comments;
- dispatch cost depends on current open state and current unresolved closed-routing candidates only;
- #91 cannot block current work because it is terminal history.

### Premature-close regression

Model a post-cutover coordination Issue closed while its valid nonterminal routing tuple remains attached.

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

### Cutover regression

Prove the new fast path cannot activate without exact pre-cutover reconciliation evidence and an immutable cutover boundary. After activation, old history is not consulted by normal dispatch.

### Diagnostic and safety regressions

Keep/add cases proving:
- incomplete current open or unresolved-close enumeration fails closed;
- multiple open formal workflows fail closed;
- duplicate compatible terminal journals classify terminal when exceptional code directly evaluates them;
- conflicting terminal identity remains indeterminate;
- direct-Propose admission and pre-activation ordering remain deterministic;
- non-authorizing bridge decisions expose bounded reason but no tuple.

## Governance impact

This is a behavioral contract change. Canonical `scheduled-agent-workflow` must stop requiring a complete closed-history structural projection for normal selection and must define routing retirement/current unresolved-close semantics.

`agents/AGENTS.md` needs the minimum matching shared-governance update. `agents/workflow.md` topology does not change: the same actions and correction loops remain authoritative. Terminal routing retirement is an effect/postcondition detail, not a new lifecycle node.

No role or mapped Skill ownership change is intended.

## Trade-offs

### Chosen: existing routing labels + fixed cutover

Pros:
- no new registry or lifecycle label;
- normal cost scales with unresolved work, not history;
- premature close produces a durable signal naturally because close does not erase routing;
- legitimate terminal close can retire routing in the same Issue mutation;
- one fixed cutover cleanly contains legacy history cost.

Cons:
- one-time pre-cutover reconciliation is required;
- out-of-band administrators can still deliberately erase the recovery signal, which is treated as administrative corruption rather than something every normal wake must defend against by full-history replay.

### Rejected: structural projection of every closed workflow

Still `O(repository-history)` and is the Reviewer finding being corrected.

### Rejected: new durable recovery registry/label

A separate registry or lifecycle label duplicates state already represented by the retained routing tuple and adds synchronization obligations.

### Rejected: cache terminal history

Caching requires invalidation/authority semantics and still leaves history in the authorization model.

### Deferred: lightweight Python runtime

The Python/`uv` execution-environment optimization remains independently reviewable follow-up work and is not coupled to this authorization-semantics correction.
