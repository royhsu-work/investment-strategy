# Change: Prevent native closing bypass at merge

## Why

The persistent coordination Issue is required to remain open until `Lead / finalize-archive` records valid `LIFECYCLE_COMPLETE` and performs terminal closure. Current merge acceptance rejects PR-level closing linkage, but historical #140 and #155 demonstrate that an included commit message such as `Resolve #N` can still activate GitHub native closing semantics when the accepted head reaches the default branch. A PR may therefore use legal non-closing `Refs #N` presentation and still close its coordination Issue prematurely.

Explore result: issue comment `5429709143` on #159 (`Lead / explore-change`, `PROPOSAL_READY`). This proposal formalizes that decision-complete boundary without reopening the terminal topology settled by #115 or absorbing the broader executable-governance inventory in #138.

## What Changes

- Add one repository-owned executable native-closing preflight for merge acceptance, scoped to the exact persistent coordination Issue and exact PR head.
- Require complete acquisition of every repository-relevant presentation that can establish GitHub native closing semantics for the selected merge strategy: PR description/linkage, included commit messages, and effective generated merge/squash message inputs where applicable.
- Reject a non-terminal implementation, implementation-correction, or final Archive merge when any effective presentation contains a GitHub-native closing reference to that workflow's exact coordination Issue; legal non-closing references remain allowed and unrelated Issues remain outside this lifecycle guard.
- Bind the deterministic result to repository, coordination Issue, PR, exact head, lifecycle context, merge strategy/presentation, and acquisition completeness. Changed or incomplete evidence fails closed.
- Make Reviewer consume the same deterministic result as review evidence when relevant, while Executor freshly re-evaluates it immediately before merge. No second parser is introduced in role prose.
- Preserve terminal closure exclusively as a post-`LIFECYCLE_COMPLETE` `Lead / finalize-archive` effect; premature-close recovery remains exceptional defense-in-depth.
- Treat an already-reviewed offending head as stale merge acceptance. Correction must produce a new acceptable exact head/presentation and re-enter ordinary exact-head gates; this Change does not authorize force-push, history rewriting, or waiver of native-close safety.

## Capabilities

### Modified capabilities

- `scheduled-agent-workflow`: extend merge acceptance so GitHub-native closing semantics cannot bypass persistent coordination-Issue terminal authority through commit or merge presentation surfaces.

## Scope

In scope:

- exact coordination-Issue native-closing detection for repository-governed implementation, correction, and final Archive merges;
- merge-strategy-aware presentation acquisition and fail-closed completeness;
- deterministic shared preflight consumption by Reviewer and Executor;
- exact-head invalidation and focused regressions reproducing #140/#155.

Out of scope:

- changing the #115 terminal ordering;
- globally forbidding closing references to unrelated Issues;
- redesigning closed-routing-debt recovery;
- absorbing #138's repository-wide executable-governance inventory;
- adding a new lifecycle action, lock, lease, heartbeat, retry registry, or second workflow DAG;
- authorizing history rewrite or force-push as a correction mechanism.

## Impact

Expected implementation blast radius is limited to the repository-owned merge/effect preflight boundary and focused tests, plus the `merge-pr` Skill/Executor consumption and only the shared governance/workflow references materially required to state ownership. The canonical `scheduled-agent-workflow` capability is modified. No product strategy or market-data behavior changes.

## Skill maintenance traceability

- Modified: `agents/skills/merge-pr/SKILL.md`
  - Source: #159 / Change `prevent-native-closing-bypass`.
  - Preserved responsibility: Executor remains the sole owner of authorized PR merge mutation and exact-head merge acceptance.
  - Changed responsibility detail: merge acceptance consumes the repository-owned deterministic native-close preflight and requires a fresh exact-head result immediately before merge rather than validating only PR-level closing linkage.
  - Rationale: the #140/#155 failure family proves PR-level linkage inspection alone does not cover included commit-message closing semantics.

No other Skill responsibility is intentionally changed by this proposal.