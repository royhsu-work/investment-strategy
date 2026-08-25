# Design: Fix machine dispatch recovery liveness

## Context

The production dispatcher already separates current open-Issue selection from a structural closed-workflow conflict screen for the sole-formal case. The remaining liveness defect appears when open formal cardinality is zero: orchestration always enters detailed exceptional recovery before pre-activation selection or `NO_WORK`.

Detailed recovery currently traverses closed workflow history and, for modern non-`unset` workflows, reads comment history to classify terminal completion. `_terminal_evidence_from_comments()` also uses valid-comment cardinality as the terminal uniqueness rule: one valid completion is terminal history, while more than one is indeterminate. #91 demonstrates why that rule is incompatible with at-least-once durable journaling: two compatible completion records for one completed workflow block unrelated future work.

This Change keeps current authorization strict while narrowing what must be proven synchronously.

## Design goals

1. Preserve complete provenance-qualified current open-Issue reconstruction, WIP=1, deterministic pre-activation ordering, and model non-override.
2. Make exceptional recovery pay exceptional cost: detailed closed-history forensics runs only when a complete structural projection cannot rule out a conflict/recovery candidate.
3. Treat equivalent terminal journal replay idempotently while keeping genuine terminal contradiction fail closed.
4. Make non-authorizing machine decisions diagnostically useful without turning diagnostic text into authority.
5. Add no persistent cache, registry, lease, lock, cursor, or second workflow state.

## Decision 1: Apply one structural conflict gate to both formal-one and formal-zero

### Current shape

```text
open state
  ├─ formal = 1
  │    → closed structural projection
  │         ├─ CLEAR → authorize formal
  │         └─ non-CLEAR → detailed recovery
  └─ formal = 0
       → closed structural projection
       → detailed recovery unconditionally
       → pre-activation / NO_WORK
```

### Target shape

```text
complete authoritative open state
  → formal cardinality
  → complete bounded closed structural projection
       ├─ CLEAR
       │    ├─ formal = 1 → authorize sole formal
       │    └─ formal = 0 → deterministic pre-activation / NO_WORK
       └─ POSSIBLE_CONFLICT | INDETERMINATE
            → detailed exceptional recovery for relevant candidates
                 ├─ cleared → resume formal/pre-activation selection
                 ├─ one qualifying premature-close recovery → Lead/resolve-question
                 └─ contradiction/incomplete → FAIL_CLOSED
```

The structural projection is not terminal proof for every historical workflow. It is only a complete current conflict predicate: can any closed workflow-looking Issue still be capable of changing the dispatch result? If not, detailed terminal history is unnecessary for this authorization.

This preserves the existing safety property while moving broad forensic work behind an actual conflict signal.

## Decision 2: Candidate-bound detailed acquisition

`_acquire_structural_closed_preflight()` already distinguishes definitely non-conflicting closed history from possible conflicts using bounded current facts and the last visible terminal marker where needed. Formal-zero orchestration should consume that same structural result instead of entering detailed history solely because formal cardinality is zero.

When detailed recovery is required, production acquisition should fetch detailed comment/event/archive evidence only for the structural candidates that remain capable of affecting recovery or conflict classification. Definitely excluded historical terminal/retired entries must not be reintroduced merely because they exist in the repository.

The exact internal representation may reuse the existing structural preflight/candidate list or introduce a small ephemeral value object. It must not create durable state.

## Decision 3: Terminal replay identity is semantic, not raw-comment cardinality

A canonical terminal journal already carries stable semantic fields:

- coordination `Workflow` Issue;
- immutable `Change`;
- `Action: Lead / finalize-archive`;
- `Result: LIFECYCLE_COMPLETE`;
- terminal revision/Archive identity when present.

Classification rules:

```text
no valid completion
  → not-terminal

one or more valid completions, mutually compatible
  → terminal-history

one or more valid completions with conflicting immutable terminal facts
  → indeterminate
```

Compatibility is monotonic: a later replay may include additional compatible metadata that an earlier valid journal omitted. Raw body equality is not required. However, if two journals assert incompatible immutable Archive/revision identity or another required terminal fact, the result remains indeterminate.

Implementation should parse the minimum semantic terminal identity required to compare valid journals rather than treating `len(valid) > 1` as contradiction.

This aligns terminal reconstruction with the repository's at-least-once execution model and does not weaken contradictory-evidence handling.

## Decision 4: Preserve strict current authorization boundaries

The fast path does not authorize from history, cache, or prior output. It still requires:

- complete current open-Issue enumeration;
- qualified provenance for authorization-bearing fields;
- zero/one formal cardinality as applicable;
- current valid routing and immutable Change identity;
- complete current structural closed-conflict projection;
- deterministic combined pre-activation ordering for formal-zero;
- fresh action-entry dispatch and existing effect-time reauthorization.

Any incomplete structural projection, possible conflict, or genuine contradiction enters detailed recovery or fails closed. The model cannot elect to skip this boundary.

## Decision 5: Publish bounded non-authorizing diagnostics

`DispatchDecision.reason` already exists in the executable classifier, but the issue-comment bridge drops it for `NO_WORK` and `FAIL_CLOSED`. The bridge should publish one exact bounded `Reason` field for non-authorizing decisions.

The parser/result contract must continue to enforce:

- `AUTHORIZE` → exact Issue/Role/Action tuple, no model-selected substitute;
- `NO_WORK` / `FAIL_CLOSED` → no Issue/Role/Action tuple;
- `Reason` → diagnostic only and never a routing/effect authorization token.

Use stable bounded classifier messages or a bounded reason code/string; do not serialize arbitrary exception traces or model prose into the decision protocol.

## Regression strategy

### Exact production reproduction

Model the #91 failure shape using production acquisition/classifier surfaces:

```text
closed #91
  completion A: valid LIFECYCLE_COMPLETE
  completion B: valid compatible LIFECYCLE_COMPLETE

open state
  formal cardinality = 0
  one eligible Lead/explore-change candidate
```

Expected result after this Change:
- structural-clear path does not enter unrelated detailed #91 forensics merely because formal cardinality is zero; and
- if #91 is directly fed to detailed terminal classification, the compatible replay still classifies as `terminal-history`.

These are complementary protections: responsibility boundary and replay semantics.

### Safety regressions

Keep or add cases proving:
- incomplete current open enumeration fails closed;
- multiple open formal workflows fail closed;
- structural possible conflict still enters detailed recovery;
- a real qualifying premature-close recovery candidate blocks pre-activation;
- multiple/indeterminate recovery candidates fail closed;
- incompatible terminal revisions remain indeterminate;
- direct-Propose admission and pre-activation ordering remain deterministic;
- non-authorizing bridge decisions expose a bounded reason but never a tuple.

## Governance impact

The canonical `scheduled-agent-workflow` requirement currently mandates detailed exceptional recovery whenever formal cardinality is zero. Therefore this is a behavioral contract change, not an implementation-only optimization. `openspec/specs/scheduled-agent-workflow/spec.md` must be updated through archive if this Change is approved.

`agents/AGENTS.md` may require a minimal matching update so default-branch governance no longer says formal-zero always enters detailed recovery. Do not duplicate classifier mechanics there; retain authority, provenance, result meaning, and fail-closed boundaries only.

No role file, mapped Skill, or `agents/workflow.md` topology change is intended. If implementation proves one is materially necessary, return to Lead specification authority rather than expanding silently.

## Trade-offs

### Chosen: structural completeness before detailed semantics

Pros:
- removes O(history-comment-forensics) work from ordinary formal-zero dispatch when no conflict exists;
- preserves current authoritative evidence and recovery safety;
- reuses an existing executable ownership layer;
- no new durable runtime state.

Cons:
- structural projection correctness becomes important for both formal-one and formal-zero; regressions must prove that possible conflicts cannot be incorrectly cleared.

### Rejected: cache terminal history

A cache could reduce API calls but would require freshness/invalidation semantics for authorization. It would introduce hidden authority state and does not solve the semantic duplicate-journal defect.

### Rejected: delete/edit duplicate historical comments

That destroys or rewrites durable evidence and repairs one symptom rather than the classifier. The system must tolerate at-least-once durable history.

### Rejected: blanket ignore closed history at formal-zero

This would strand legitimate premature-close recovery and weaken a real safety property. The design keeps a complete structural conflict predicate and detailed recovery whenever the predicate is not clear.

### Deferred: lightweight Python runtime

Removing full project environment setup is independently valuable but changes an execution/runtime boundary rather than the authorization semantics repaired here. Keeping it separate improves reviewability and avoids hiding safety changes inside a performance refactor.
