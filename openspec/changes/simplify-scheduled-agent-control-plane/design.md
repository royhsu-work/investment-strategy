## Context

#138 preserves formal Explore `issuecomment-5482546619`, Human architecture decisions `issuecomment-5475109024` / `issuecomment-5477274582`, #168 transport source `issuecomment-5442745071`, Human environment constraint `issuecomment-5303723685`, Executor blocker `issuecomment-5504609193`, Human execution clarification `issuecomment-5507379401`, and Human-approved M0/N-1 correction `issuecomment-5521336171`. Verified proposal-recovery checkpoint `issuecomment-5507709525` proves the current proposal revision already preserves the carrier, bounded-slice, and rejection-observability intent. M0 PR #189 established the bounded content-addressed ingress/Resolve-validation/HANDOFF substrate; production run `33730731896` exposed its cross-credential blob-GET defect, and follow-up PR #190 is merged/deployed at `main@e8c3dc7b256bc167217e25a397e98181bdf6f123` with application-owned tree resolution. That M0 pair is prerequisite/buildability evidence, not #138 completion; production connector-blob → Actions-tree → exact-R live E2E remains the acceptance obligation.

The correction keeps Human outcome fixed while separating four execution boundaries that prior formalization conflated or ordered incorrectly: exact revision `R` validation, content-addressed work-product ingress/application completion, run-scoped result transport, and identity-sensitive PR mutation carrier execution. Repository effect/revision authorization and repository-owned postcondition observation remain distinct from all three transport/carrier surfaces. The repeated fragmented recovery also demonstrates an execution-granularity defect: one mapped Action per wake is necessary, but the Action still needs a bounded independently verifiable work slice rather than file/API/run-sized stopping points.

## Decisions

### 1. One executable authority

After cutover, current workflow position is `Issue lifecycle + immutable Change + one Action + exact causal input`; Role derives from Action. A default-branch kernel solely owns Action vocabulary, Action→Role, finite result/transition/effect rules, WIP/FIFO/debt classification, effect capabilities, carrier eligibility, fresh authorization, stale/replay handling, deterministic rejection classification/evidence, and structural postconditions. `agents/workflow.md` is generated or mechanically verified presentation, not a parsed competing DAG. Semantic judgment remains with Lead/Reviewer/Executor. Generic `merge-pr` becomes `merge-implementation-pr` and `merge-archive-pr`.

### 2. Effect authority and mutation carrier are separate

Repository application derives and fresh-authorizes an exact target/precondition/revision-bound effect. A legal carrier then executes only that plan, after which repository application fresh-reads the resulting object/head/state before accepting success. The carrier MUST NOT choose Issue, Action, successor, effect, retry, weaker preconditions, or success semantics. Carrier replacement does not change workflow semantics.

Identity-sensitive PR create/presentation/head/ready/merge effects that Actions cannot legally execute, or whose bot identity breaks required event propagation, use an event-capable Scheduled-Agent connector/GitHub-App carrier. The target MUST NOT enable `Allow GitHub Actions to create and approve pull requests`.

Preserve #58: archive automation succeeds at validated archive-branch push; `Lead / finalize-change` presents or reuses the final Archive PR through the legal carrier; independent archive review, exact-head gates, Executor merge, native close, and terminal reconstruction remain. Recovery is reuse-first; create replacement only when fresh exact authority requires it. No carrier wait state, retry counter, lock/lease, or second DAG is added.

### 3. Work-product ingress is content-addressed and application-owned

OpenSpec work-product ingress is neither control/request transport nor run-scoped result transport, and it is not the identity-sensitive mutation carrier. A semantic worker may create only unreferenced Git blobs as untrusted content-addressed ingress. Its request carries no complete source/spec/test content; it carries the exact current PR/branch/base identity plus each Change-owned path, referenced blob SHA, and current expected blob SHA.

Repository application fresh-reauthorizes the exact source Action, verifies current Issue/Change/PR/branch/base/path/current-blob identities, uses application-owned `create tree` as the first cross-credential resolution of the manifest blob SHAs, then fresh-observes the exact created tree and requires every requested Change-owned path to resolve to the exact requested blob SHA before commit creation. It constructs one commit revision `R`, advances only the exact current branch without force, and accepts success only after fresh observation of ref, PR head, commit/tree/parent, and file-SHA postconditions. A stale base or expected SHA, unavailable/mismatched blob during tree construction, escaping/duplicate path, incomplete/truncated tree observation, force update, worker-created tree/commit/ref, or API success without observed postcondition fails closed before acceptance.

Direct `GET git/blobs/{sha}` by the application identity is not a required precondition for connector-created unreferenced ingress: production run `33730731896` demonstrated that such a pre-read may return 404 across credentials even when the connector-side object was freshly observable. Blob availability becomes authoritative only when application-owned tree construction resolves the SHA and the created tree is freshly verified. This does not make an unreferenced blob durable workflow state; transient ingress must be created and consumed within the bounded work-product operation.

The resulting exact `R` is handed to the same application-owned exact-revision validation boundary. After a cross-role source result/routing application, canonical `HANDOFF` is likewise application-owned: it is persisted only after the exact source `ACTION_RESULT`, routing mutation, and target routing are observed. The M0 bootstrap proves the mechanism can self-host this correction only when the live E2E succeeds; formal Stage 1B still owns production live-E2E acceptance and does not let bootstrap/unit-test evidence complete #138.

### 4. Exact-revision validation remains application-owned

When readiness requires exact OpenSpec validation for `R`, application obtains deterministic evidence independent of a source-Action whitelist. `R` may be newly produced or already current; no dummy-touch is allowed. Accepted evidence proves target `R`, validator checkout `HEAD == R`, qualified pinned compatibility, and strict PASS. Stale CI, `run.head_sha` without checkout proof, manual approval, ungoverned connector mutation, or another model wake cannot satisfy the gate. `Lead / resolve-question` receives the same gate-derived resource availability as Propose.

### 5. Run-scoped transport and one Action per wake

Runtime check-in comments are request/trigger/audit only. Dispatch/application/validation results belong to the exact Actions run; exact request→run→result correlation is mandatory with no response-comment fallback. Each wake fresh-discovers exactly one open `Asia/Taipei` current-day check-in; rollover establishes today before closing yesterday and preserves in-flight prior-day correlations.

A normal wake is `fresh dispatch → one mapped Action → bounded verified slice → application → legal carrier if required → fresh postcondition/exact-resource consumption → durable checkpoint → exit`. No successor Action executes in that wake; the selected Action remains work-conserving internally.

### 6. Correction, replay, and migration

Before first independent `review-openspec` acceptance, a material formalization defect may return the same Issue to Explore without a new Human-reserved commitment while preserving Change, artifact/PR history, evidence, and WIP. After acceptance, material correction uses Resolve and renewed independent review.

Satisfied postconditions are idempotent. Carrier failure preserves exact plan/error/observed mutation and recovery continues only while source/effect remain current. Stage 5 uses a finite reviewed typed retirement plan plus complete current observations; prose/history/model inference never selects migration candidates. The first plan retires #168 to provenance-only after absorption into #138.

### 7. Bounded verified slices and deterministic rejection evidence

Inside one machine-authorized Action, the primary execution unit is one bounded vertical slice with an independently verifiable outcome:

`Reconstruct → RED exact gap/blocker → GREEN legal correction → VERIFY exact postcondition/revision/gate → durable checkpoint`.

The slice is not one file mutation, one API call, one GitHub Actions run, or another intermediate mechanical event. If the intended slice cannot reasonably reach VERIFY in one normal invocation, it is split before execution at a meaningful outcome boundary rather than being allowed to fragment opportunistically. Valid stop boundaries include verified slice completion, a cross-role handoff, a genuine Human decision boundary, an N-1 prerequisite deployment boundary, or an external resource wait only after no other legal same-authority continuation remains.

When repository application rejects a deterministic effect guard, it emits machine-readable rejection classification identifying the exact failed predicate/guard class and relevant expected/observed evidence. An aggregate message such as `effect precondition rejected` may remain diagnostic text but cannot be the only durable result. This evidence is observability of repository-owned authorization; it does not create semantic authority, choose a successor, authorize retry, weaken the rejected precondition, or create a second retry/state machine.

## Mandatory N-1 delivery

Order is **1A exact-revision application resource → 1B content-addressed work-product ingress/self-hosting → 1C run-scoped result transport/daily check-in → 1D identity-sensitive PR carrier → 2 kernel shadow → 3 typed application → 4 one-Action wake → 5 canonical cutover/source retirement → 6 deletion/context reduction**.

Every stage must be independently executable/testable/mergeable/deployable on N-1 or be split. Stage 1A is this materially revised Resolve action's semantic-review prerequisite. Stage 1B formalizes the distinct content-addressed ingress/application-completion boundary bootstrapped by M0 and retains production live-E2E acceptance. Stage 1C is the mandatory #168 run-scoped transport deployment. Stage 1D is the mandatory identity-sensitive PR carrier boundary proven necessary by Actions PR-create failure. Stages 1B–1D must be deployed before Stage 2; after valid Stage-1A evidence they do not add another semantic OpenSpec review prerequisite. Stage 3 owns machine-readable deterministic rejection evidence at the typed application boundary; Stage 4 consumes that boundary while enforcing one bounded verified slice inside the one authorized Action.

## Validation and deletion

Stage 1B verifies no full-content Issue-comment work-product persistence, exact manifest/base/path/current identity checks, application-owned tree resolution of referenced blob SHAs, exact recursive tree path/blob observation before commit, application-owned single commit `R`, non-force exact ref/PR/file postconditions, exact-R validation handoff, canonical application-owned cross-role HANDOFF, stale/unavailable/mismatched ingress behavior, and production live E2E. PRs #189/#190 are prerequisite/buildability evidence rather than formal completion evidence.

Stage 1D verifies carrier eligibility, no carrier-side selection/retry inference, exact target/head/base/linkage/precondition binding, reuse-first PR recovery, no Actions PR-create permission dependency, ordinary event propagation, fresh repository postconditions, stale/failure behavior, and preservation of the validated-archive-branch boundary.

Stage 3 validation verifies that every deterministic rejection exposes an exact machine-readable guard classification/evidence rather than forcing the semantic worker to reconstruct guard logic from routing/SHA/source code. Stage 4 validation verifies that one Action does not claim slice completion from an intermediate write/API/run and that a durable checkpoint follows VERIFY.

Final production removes normal `agent:*` routing, generic merge-phase inference, response-mailbox/history coupling, Markdown topology/effect parsing, same-wake continuation/barriers, obsolete compatibility, legacy model-host code, Actions-owned identity-sensitive PR lifecycle paths, and redundant tests/prose.
