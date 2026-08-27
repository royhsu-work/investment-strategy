# Design: Native closing merge preflight

## Context

The settled lifecycle requires one persistent coordination Issue to stay open until `Lead / finalize-archive` completes terminal verification. Existing `merge-pr` governance checks PR-level closing linkage, but #140 and #155 show that included commit messages using GitHub closing grammar can still close the Issue when merged to the default branch. Repository settings currently permit merge commit, squash merge, and rebase merge, so the effective presentation is strategy-dependent.

The design must prevent this mechanically without duplicating parsing logic across Reviewer and Executor or globally banning legitimate Issue resolution.

## Goals

- Make native-closing safety an executable exact-head merge-acceptance predicate.
- Scope detection to the exact workflow coordination Issue.
- Cover every effective repository-relevant closing producer for the selected merge strategy.
- Fail closed when acquisition or generated presentation is incomplete/ambiguous.
- Preserve separation of duties: one deterministic classifier, independent Reviewer consumption, fresh Executor application-time evaluation.
- Preserve the existing terminal topology and exceptional premature-close recovery.

## Non-goals

- General repository-wide policing of closing references to unrelated Issues.
- A new lifecycle action or state machine.
- Automatic commit-history rewriting or force-push correction.
- Reworking #138's broader executable-governance inventory.

## Decision 1: One repository-owned preflight owns native-close classification

Add the native-close predicate to the repository-owned merge/effect boundary rather than implementing keyword checks in role prompts. The preflight accepts structured, provenance-bound inputs and returns a deterministic allow/reject result plus diagnostic evidence. Reviewer and Executor both consume this result; neither role owns a second parser.

The parser models GitHub closing grammar for the exact repository/Issue identity. It distinguishes closing grammar from non-closing references and does not reject a closing reference to a different Issue merely because the text contains a closing keyword.

## Decision 2: Evidence is exact-head and merge-strategy aware

The preflight input is bound to:

- repository identity;
- coordination Issue number;
- PR number and current exact head SHA;
- lifecycle merge context;
- selected merge strategy;
- PR description/linkage text;
- complete included commit identities/messages for that exact head;
- effective generated merge/squash message inputs for the selected strategy;
- explicit acquisition-completeness/provenance state.

Because merge commit, squash, and rebase are all enabled, no strategy-independent assumption about generated messages is safe. The application path must either construct/observe the exact effective message under the chosen method or reject when that presentation cannot be determined safely.

A head change, strategy change, message-input change, or incomplete acquisition invalidates the prior result.

## Decision 3: Enforcement occurs twice without duplicating semantics

Reviewer may require/consume the deterministic preflight result for the reviewed exact head as part of independent implementation/archive acceptance. This proves the reviewed presentation is acceptable at that revision.

Executor still runs/acquires a fresh preflight immediately before the merge effect. This is a freshness/application guard, not a second semantic implementation. The merge mutation is permitted only if the fresh result matches the exact current head, selected strategy, coordination Issue, and complete presentation.

## Decision 4: Correction creates a new exact acceptance target

When a reviewed head contains an offending historical commit message, the workflow rejects that head. The correction mechanism is deliberately not prescribed as force-push/rebase/history rewrite. A legal repository/tool-specific correction may change commit structure, merge strategy, or presentation only if it yields a new exact acceptance target whose effective default-branch presentation is proven safe. Any changed head/presentation re-enters ordinary review and exact-head gates.

This keeps the safety invariant independent from the available mutation tooling.

## Decision 5: Terminal closure remains unchanged

The final Archive PR is subject to the same non-closing preflight. Merge success does not close the coordination Issue by design. `Lead / finalize-archive` remains the only normal terminal owner after valid `LIFECYCLE_COMPLETE`. Existing premature-close recovery remains bounded defense-in-depth for manual/platform/unexpected failures.

## Failure handling

Fail closed when:

- the current PR/head cannot be proven;
- commit enumeration is incomplete;
- a relevant message/presentation cannot be obtained;
- the selected merge strategy's effective generated message is ambiguous or unsupported;
- any effective presentation contains native closing grammar for the exact coordination Issue;
- evidence was produced for another head, strategy, repository, Issue, or lifecycle context.

Diagnostics may identify the offending surface/commit but do not authorize correction or routing.

## Traceability

- Proposal: executable exact-head native-close prevention scoped to the persistent coordination Issue.
- Modified capability requirement: `Merge acceptance preserves persistent coordination-Issue terminal authority`.
- Historical regression evidence: #140 commit `4075cac3d1a8759a3299f67c8520a2b328b053ca`; #155 commit `163b60f1a98bb83180e337da858b298f214639a6`.
- Upstream semantic baseline: #159 Explore `PROPOSAL_READY`, issue comment `5429709143`.
- Existing terminal ordering: #115 remains unchanged.

## Trade-offs

The design requires more complete merge-presentation acquisition than the current PR-linkage check, but the extra evidence is limited to the consequential merge boundary where GitHub can produce the irreversible native close side effect. Centralizing the classifier avoids repeated role-level complexity and makes incomplete evidence explicit instead of optimistic.