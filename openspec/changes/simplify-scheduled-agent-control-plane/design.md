## Context

#138 preserves formal Explore `issuecomment-5482546619`, Human architecture decisions `issuecomment-5475109024` / `issuecomment-5477274582`, #168 transport source `issuecomment-5442745071`, Human environment constraint `issuecomment-5303723685`, Executor blocker `issuecomment-5504609193`, and Human execution clarification `issuecomment-5507379401`. Verified proposal-recovery checkpoint `issuecomment-5507709525` proves the current proposal revision already preserves the latest carrier, bounded-slice, and rejection-observability intent.

The correction addresses two execution-boundary defects without changing Human outcome: exact revision `R` may exist while event validation is `action_required` with no validator job, and repository effect authority has been conflated with the Actions `GITHUB_TOKEN` mutation identity. The repeated fragmented recovery also demonstrates an execution-granularity defect: one mapped Action per wake is necessary, but the Action still needs a bounded independently verifiable work slice rather than file/API/run-sized stopping points.

## Decisions

### 1. One executable authority

After cutover, current workflow position is `Issue lifecycle + immutable Change + one Action + exact causal input`; Role derives from Action. A default-branch kernel solely owns Action vocabulary, Action→Role, finite result/transition/effect rules, WIP/FIFO/debt classification, effect capabilities, carrier eligibility, fresh authorization, stale/replay handling, deterministic rejection classification/evidence, and structural postconditions. `agents/workflow.md` is generated or mechanically verified presentation, not a parsed competing DAG. Semantic judgment remains with Lead/Reviewer/Executor. Generic `merge-pr` becomes `merge-implementation-pr` and `merge-archive-pr`.

### 2. Effect authority and mutation carrier are separate

Repository application derives and fresh-authorizes an exact target/precondition/revision-bound effect. A legal carrier then executes only that plan, after which repository application fresh-reads the resulting object/head/state before accepting success. The carrier MUST NOT choose Issue, Action, successor, effect, retry, weaker preconditions, or success semantics. Carrier replacement does not change workflow semantics.

Identity-sensitive PR create/presentation/head/ready/merge effects that Actions cannot legally execute, or whose bot identity breaks required event propagation, use an event-capable Scheduled-Agent connector/GitHub-App carrier. The target MUST NOT enable `Allow GitHub Actions to create and approve pull requests`.

Preserve #58: archive automation succeeds at validated archive-branch push; `Lead / finalize-change` presents or reuses the final Archive PR through the legal carrier; independent archive review, exact-head gates, Executor merge, native close, and terminal reconstruction remain. Recovery is reuse-first; create replacement only when fresh exact authority requires it. No carrier wait state, retry counter, lock/lease, or second DAG is added.

### 3. Exact-revision validation remains application-owned

When readiness requires exact OpenSpec validation for `R`, application obtains deterministic evidence independent of a source-Action whitelist. `R` may be newly produced or already current; no dummy-touch is allowed. Accepted evidence proves target `R`, validator checkout `HEAD == R`, qualified pinned compatibility, and strict PASS. Stale CI, `run.head_sha` without checkout proof, manual approval, ungoverned connector mutation, or another model wake cannot satisfy the gate. `Lead / resolve-question` receives the same gate-derived resource availability as Propose.

### 4. Run-scoped transport and one Action per wake

Runtime check-in comments are request/trigger/audit only. Dispatch/application/validation results belong to the exact Actions run; exact request→run→result correlation is mandatory with no response-comment fallback. Each wake fresh-discovers exactly one open `Asia/Taipei` current-day check-in; rollover establishes today before closing yesterday and preserves in-flight prior-day correlations.

A normal wake is `fresh dispatch → one mapped Action → bounded verified slice → application → legal carrier if required → fresh postcondition/exact-resource consumption → durable checkpoint → exit`. No successor Action executes in that wake; the selected Action remains work-conserving internally.

### 5. Correction, replay, and migration

Before first independent `review-openspec` acceptance, a material formalization defect may return the same Issue to Explore without a new Human-reserved commitment while preserving Change, artifact/PR history, evidence, and WIP. After acceptance, material correction uses Resolve and renewed independent review.

Satisfied postconditions are idempotent. Carrier failure preserves exact plan/error/observed mutation and recovery continues only while source/effect remain current. Stage 5 uses a finite reviewed typed retirement plan plus complete current observations; prose/history/model inference never selects migration candidates. The first plan retires #168 to provenance-only after absorption into #138.

### 6. Bounded verified slices and deterministic rejection evidence

Inside one machine-authorized Action, the primary execution unit is one bounded vertical slice with an independently verifiable outcome:

`Reconstruct → RED exact gap/blocker → GREEN legal correction → VERIFY exact postcondition/revision/gate → durable checkpoint`.

The slice is not one file mutation, one API call, one GitHub Actions run, or another intermediate mechanical event. If the intended slice cannot reasonably reach VERIFY in one normal invocation, it is split before execution at a meaningful outcome boundary rather than being allowed to fragment opportunistically. Valid stop boundaries include verified slice completion, a cross-role handoff, a genuine Human decision boundary, an N-1 prerequisite deployment boundary, or an external resource wait only after no other legal same-authority continuation remains.

When repository application rejects a deterministic effect guard, it emits machine-readable rejection classification identifying the exact failed predicate/guard class and relevant expected/observed evidence. An aggregate message such as `effect precondition rejected` may remain diagnostic text but cannot be the only durable result. This evidence is observability of repository-owned authorization; it does not create semantic authority, choose a successor, authorize retry, weaken the rejected precondition, or create a second retry/state machine.

## Mandatory N-1 delivery

Order is **1A exact-revision application resource → 1B transport de-mailbox → 1C PR mutation carrier boundary → 2 kernel shadow → 3 typed application → 4 one-Action wake → 5 Action-only/explicit-merge cutover plus typed source retirement → 6 deletion/context reduction**.

Every stage must be independently executable/testable/mergeable/deployable on N-1 or be split. Stage 1A is this materially revised Resolve action's semantic-review prerequisite. Stages 1B and 1C remain mandatory before Stage 2 but are not additional semantic review gates after valid Stage-1A evidence. Stage 3 owns machine-readable deterministic rejection evidence at the typed application boundary; Stage 4 consumes that boundary while enforcing one bounded verified slice inside the one authorized Action.

## Validation and deletion

Stage 1C verifies carrier eligibility, no carrier-side selection/retry inference, exact target/head/base/linkage/precondition binding, reuse-first PR recovery, no Actions PR-create permission dependency, ordinary event propagation, fresh repository postconditions, stale/failure behavior, and preservation of the validated-archive-branch boundary.

Stage 3 validation verifies that every deterministic rejection exposes an exact machine-readable guard classification/evidence rather than forcing the semantic worker to reconstruct guard logic from routing/SHA/source code. Stage 4 validation verifies that one Action does not claim slice completion from an intermediate write/API/run and that a durable checkpoint follows VERIFY.

Final production removes normal `agent:*` routing, generic merge-phase inference, response-mailbox/history coupling, Markdown topology/effect parsing, same-wake continuation/barriers, obsolete compatibility, legacy model-host code, Actions-owned identity-sensitive PR lifecycle paths, and redundant tests/prose.
