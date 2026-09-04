# Scheduled-Agent Workflow

Scheduled-Dispatch-Mode: workflow-dynamic

This file is the Human-readable projection of the repository-owned executable Action model. Runtime
code does not parse this Markdown as topology or effect authority. The current default branch is
read at every wake.

## Canonical state

Current workflow state is Issue lifecycle, immutable Change, and one action:<action> for an open
formal Issue. Role = role_for(Action). Evidence such as results, review decisions, Human input,
revisions, transport runs, and carrier output is durable evidence, not a competing state machine.

## One Action per Scheduled Task wake

Each wake performs one fresh dispatch, one semantic Action, one structured result, fresh repository
reauthorization, exact necessary effects, required validation, postcondition observation,
next_action(current_action, result), and persistence of one successor or terminal state before exit.
The successor is executed only by a later fresh wake.

The worker cannot choose a target, Role, Action, successor, retry, or success. Repository application
derives routing from the executable model and rejects stale, replayed, ambiguous, contradictory, or
incomplete input. Exact revision, content-addressed ingress, WIP=1, finish-first, Human authority,
independent review, exact-head merge, and carrier separation remain mandatory.

## Transport

The Asia/Taipei daily shard is bounded transport only: one request, one Actions run, one structured
result. It does not authorize lifecycle, routing, or successor state. Rollover preserves an
in-flight request/run/result chain.

## Explicit merge Actions

Implementation review PASS selects merge-implementation-pr. Archive review PASS selects
merge-archive-pr. Executor rechecks exact current PR head, required gates, linkage, Human freshness,
and archive cleanup immediately before mutation. A changed or contradictory observation fails closed.

## Human notes

Role documents define semantic responsibility and Skills define action procedure. OpenSpec artifacts
define approved meaning. README is orientation. External scheduler slot/cadence/notification
configuration remains outside repository workflow authority.

<!-- BEGIN GENERATED ACTION MODEL -->
## Executable Action model (generated)

### Action to Role
| Action | Role |
| --- | --- |
| `explore-change` | `lead` |
| `propose-change` | `lead` |
| `resolve-question` | `lead` |
| `finalize-change` | `lead` |
| `finalize-archive` | `lead` |
| `review-openspec` | `reviewer` |
| `review-implementation` | `reviewer` |
| `review-archive` | `reviewer` |
| `implement-change` | `executor` |
| `merge-implementation-pr` | `executor` |
| `merge-archive-pr` | `executor` |

### Typed-result transitions
| Current Action | Result | Successor |
| --- | --- | --- |
| `explore-change` | `proposal-ready` | `propose-change` |
| `explore-change` | `research-required` | `explore-change` |
| `explore-change` | `human-decision-required` | `resolve-question` |
| `explore-change` | `no-change-required` | `terminal` |
| `explore-change` | `no-go` | `terminal` |
| `explore-change` | `blocked` | `explore-change` |
| `propose-change` | `ready-for-openspec-review` | `review-openspec` |
| `propose-change` | `research-required` | `explore-change` |
| `propose-change` | `human-decision-required` | `resolve-question` |
| `propose-change` | `no-go` | `terminal` |
| `propose-change` | `blocked` | `propose-change` |
| `resolve-question` | `ready-for-openspec-review` | `review-openspec` |
| `resolve-question` | `ready` | `implement-change` |
| `resolve-question` | `research-required` | `explore-change` |
| `resolve-question` | `human-decision-required` | `resolve-question` |
| `resolve-question` | `no-go` | `terminal` |
| `resolve-question` | `blocked` | `resolve-question` |
| `finalize-change` | `more-implementation-required` | `implement-change` |
| `finalize-change` | `archive-ready` | `review-archive` |
| `finalize-change` | `human-decision-required` | `finalize-change` |
| `finalize-change` | `no-go` | `terminal` |
| `finalize-change` | `blocked` | `finalize-change` |
| `finalize-archive` | `lifecycle-complete` | `terminal` |
| `finalize-archive` | `human-decision-required` | `finalize-archive` |
| `finalize-archive` | `blocked` | `finalize-archive` |
| `review-openspec` | `pass` | `implement-change` |
| `review-openspec` | `findings` | `resolve-question` |
| `review-openspec` | `human-decision-required` | `resolve-question` |
| `review-openspec` | `no-go` | `terminal` |
| `review-openspec` | `blocked` | `review-openspec` |
| `review-implementation` | `pass` | `merge-implementation-pr` |
| `review-implementation` | `findings` | `implement-change` |
| `review-implementation` | `spec-blocker` | `resolve-question` |
| `review-implementation` | `human-decision-required` | `resolve-question` |
| `review-implementation` | `blocked` | `review-implementation` |
| `review-archive` | `pass` | `merge-archive-pr` |
| `review-archive` | `findings` | `finalize-change` |
| `review-archive` | `human-decision-required` | `finalize-change` |
| `review-archive` | `no-go` | `terminal` |
| `review-archive` | `blocked` | `review-archive` |
| `implement-change` | `ready` | `review-implementation` |
| `implement-change` | `spec-blocker` | `resolve-question` |
| `implement-change` | `more-implementation-required` | `implement-change` |
| `implement-change` | `human-decision-required` | `resolve-question` |
| `implement-change` | `blocked` | `implement-change` |
| `merge-implementation-pr` | `merged` | `finalize-change` |
| `merge-implementation-pr` | `lifecycle-violation` | `resolve-question` |
| `merge-implementation-pr` | `blocked` | `merge-implementation-pr` |
| `merge-archive-pr` | `merged` | `finalize-archive` |
| `merge-archive-pr` | `lifecycle-violation` | `finalize-change` |
| `merge-archive-pr` | `blocked` | `merge-archive-pr` |
<!-- END GENERATED ACTION MODEL -->
