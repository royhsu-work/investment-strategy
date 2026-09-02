## Context

#138 preserves formal Explore `issuecomment-5482546619`, Human architecture decisions `issuecomment-5475109024` / `issuecomment-5477274582`, and #168 transport source `issuecomment-5442745071`.

Two observed execution-boundary defects require this correction. First, exact revision `R` can exist while event validation is `action_required` with no validator job, so exact-`R` readiness must self-host deterministically. Second, repository effect authority is conflated with the Actions `GITHUB_TOKEN` mutation identity. Human environment constraint `issuecomment-5303723685` rejects enabling `Allow GitHub Actions to create and approve pull requests` as the target solution; Executor `SPEC_BLOCKER` `issuecomment-5504609193` records the resulting `pull-request-create` HTTP 403.

This changes mechanism, not Human outcome.

## Decisions

### 1. Executable authority and current state

After cutover, current workflow position is `Issue lifecycle + immutable Change + one Action + exact causal input`; Role derives from Action. A default-branch kernel solely owns Action vocabulary, Action→Role, finite result/transition/effect rules, WIP/FIFO/debt classification, effect capabilities, carrier eligibility, fresh authorization, stale/replay handling, and structural postconditions. `agents/workflow.md` is generated/mechanically verified presentation, not a parsed competing DAG. Semantic judgment remains with Lead/Reviewer/Executor.

Generic `merge-pr` becomes `merge-implementation-pr` and `merge-archive-pr`.

### 2. Effect authority is separate from mutation carrier

An authorized worker returns exact source Issue/Action, typed result, evidence, and bounded effect inputs. Repository application:

```text
typed result
 -> derive kernel-legal effect
 -> bind exact target/preconditions/revision
 -> select legal carrier class
 -> fresh authorize
 -> carrier executes only that plan
 -> repository fresh-reads resulting object/head/state
 -> accept postcondition or reject
```

The carrier is an actuator only. It MUST NOT choose Issue/Action/effect, weaken preconditions, infer retry, or make API success authoritative. Replacing a carrier does not change workflow semantics.

### 3. Exact-revision validation remains application-owned

When readiness requires exact OpenSpec validation for `R`, application obtains deterministic evidence independent of a source-Action whitelist. `R` may be newly produced or already current; no dummy-touch is allowed.

Accepted evidence proves target `R`, validator checkout `HEAD == R`, qualified pinned compatibility, and strict PASS. Stale CI, `run.head_sha` without checkout proof, manual approval workaround, ungoverned connector mutation, or another model wake cannot satisfy the gate. `Lead / resolve-question` gets the same gate-derived resource availability as Propose.

### 4. Identity-sensitive PR effects use a legal event-capable carrier

Actions may execute only mutations whose identity and event semantics satisfy the lifecycle. PR create/presentation/head/ready/merge effects requiring ordinary GitHub event propagation, or forbidden to Actions, use an event-capable Scheduled-Agent connector/GitHub-App carrier after application authorizes an exact plan.

The target MUST NOT enable `Allow GitHub Actions to create and approve pull requests`.

Preserve #58 Archive ownership: automation ends successfully at validated archive-branch push; `Lead / finalize-change` presents/reuses final Archive PR through the legal carrier; independent archive review, exact-head gates, Executor merge, native close, and terminal reconstruction remain.

Recovery is reuse-first. Reuse an existing legal PR when it can represent the exact authorized head/linkage. Create replacement only when fresh authoritative state plus exact effect requires one. Actions inability is never authority to create a duplicate. No durable `waiting-for-carrier`, retry counter, lock/lease, or second DAG is added.

### 5. Run-scoped transport and one Action per wake

Runtime check-in comments are request/trigger/audit only. Dispatch/application/validation results belong to the exact Actions run. Exact request→run→result correlation is mandatory; no response-comment fallback. Each wake fresh-discovers exactly one open `Asia/Taipei` current-day check-in; rollover establishes today before closing yesterday and preserves in-flight prior-day correlations.

A normal wake executes `fresh dispatch -> one mapped Action -> application -> legal carrier if required -> fresh postcondition/exact-resource consumption -> exit`. No successor Action executes in the same wake. The selected Action remains work-conserving internally.

### 6. Correction, replay, and migration

Before first independent `review-openspec` acceptance, a material formalization defect may return the same Issue to Explore without a new Human-reserved commitment while preserving Change, artifacts/PR history, evidence, and WIP. After acceptance, material correction uses Resolve then independent review.

Satisfied postconditions are idempotent. Carrier failure preserves exact plan/error/observed mutation; same-authority recovery continues only while source/effect remain current. Changed preconditions make the plan stale. No generic retry/fault state machine is introduced.

Stage 5 uses a finite reviewed typed retirement plan plus complete current observations; prose/history/model inference never selects migration candidates. The first plan includes #168 as provenance-only after absorption into #138.

## Mandatory N-1 delivery

1. **1A Exact-revision application resource** — exact-`R` validation for newly produced/already-current targets.
2. **1B Transport de-mailbox** — run-scoped results and daily check-in lifecycle.
3. **1C PR mutation carrier boundary** — authority/identity split, legal event-capable carrier, reuse-first recovery, no Actions PR-create permission.
4. **2 Kernel shadow** — executable topology including carrier eligibility; no mutation cutover.
5. **3 Typed application** — typed result → exact effect/carrier plan → fresh postcondition.
6. **4 Wake simplification** — one mapped Action/wake.
7. **5 Canonical cutover** — Action-only routing, explicit merge Actions, typed source retirement.
8. **6 Deletion/context reduction** — remove superseded control paths.

Each stage must be executable/testable/mergeable/deployable on N-1 or be split. Stage 1A remains this materially revised Resolve action's semantic-review prerequisite. Stage 1B/1C block Stage 2 but do not add a separate semantic review gate after valid Stage-1A evidence.

## Validation and deletion

Stage 1C tests carrier eligibility, no carrier-side selection/retry inference, exact target/head/precondition binding, reuse-first PR recovery, no Actions PR-create permission dependency, ordinary event propagation, fresh repository postconditions, carrier failure/stale-plan behavior, and preservation of the validated-archive-branch boundary.

Final production removes normal `agent:*` routing, generic merge-phase inference, response mailbox/history correlation, Markdown topology/effect parsing, same-wake continuation/barriers, obsolete compatibility, legacy model-host code, Actions-owned identity-sensitive PR lifecycle paths, and redundant tests/prose.
