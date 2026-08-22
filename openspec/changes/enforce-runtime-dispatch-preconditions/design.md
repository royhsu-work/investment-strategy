# Design: Enforce runtime dispatch preconditions

## Context

#105 corrected the workflow semantics but intentionally stopped at prose-governed runtime behavior plus a test-only classifier. #133 then extracted that classifier into `src/investment_strategy/workflow_dispatch.py`, added explicit same-invocation GitHub observation provenance, made regressions consume the production implementation, and updated governance/Skills to require executable consumption.

Reviewer implementation finding `issuecomment-5379837891` showed that the latter design still assumed a runtime capability that has not been demonstrated. The Scheduled-Agent environment can use the GitHub connector, but there is no repository checkout mounted and no proven pre-action hook that executes repository Python. A Skill instruction to call the helper therefore remains an Agent interpretation bridge rather than a live machine enforcement boundary.

The corrected design keeps the pure classifier and moves the first live executable integration point to GitHub Actions. The MVP intentionally proves one bounded formal-routing path before broadening Gate ownership.

## Decision 1 — Preserve the pure production classifier

Keep `src/investment_strategy/workflow_dispatch.py` as the repository-owned deterministic classifier/precondition implementation.

It remains pure and accepts explicit normalized `DispatchPreflight` input containing repository Issue snapshots plus enumeration/provenance evidence. It does not own GitHub I/O, lifecycle topology, routing mutation, Human authority, or workflow state.

The existing implementation and regressions are retained as groundwork. Tests and any machine authorization adapter MUST call this production implementation rather than defining another behavioral classifier.

## Decision 1A — Current-state input authority remains explicit

Authorization-bearing current fields remain qualified only when obtained from authoritative GitHub observations in the execution that consumes the decision. Historical comments, prior invocation output, conversation context, model memory/cache, and copied summaries do not satisfy current Issue state, Change identity, routing, or enumeration-completeness predicates.

The GitHub Actions Gate acquisition adapter is responsible for building this provenance-qualified input from GitHub. Missing or incomplete current evidence produces an indeterminate decision rather than a last-known-state fallback.

## Decision 2 — GitHub Actions owns the MVP live executable transition boundary

Add a thin default-branch GitHub Actions workflow, `.github/workflows/workflow-transition-gate.yml`, triggered by newly created Issue comments. The workflow checks out the authoritative default branch and invokes one repository-owned effectful adapter, for example `src/investment_strategy/workflow_transition_gate.py`.

The adapter owns only the live transition procedure:

1. parse a bounded transition intent from the triggering comment;
2. derive the coordination Issue number from the GitHub event, not from comment claims;
3. reconstruct current repository workflow state from GitHub with observable completeness;
4. normalize a provenance-qualified `DispatchPreflight`;
5. execute `workflow_dispatch.py`;
6. validate the bounded MVP source/target transition;
7. fresh-read the target Issue immediately before mutation;
8. mutate routing only after acceptance;
9. fresh-read the resulting routing and emit durable Gate result evidence.

The Gate does not become a second workflow DAG or state store.

## Decision 3 — Request comments carry intent, not authorization facts

The MVP request syntax is intentionally small:

```text
/transition reviewer review-openspec
```

or

```text
/transition executor implement-change
```

The comment location supplies the Issue number. Current source routing, persisted Change identity, formal-active cardinality, selected Issue, completeness, and observation provenance are always acquired by the Gate.

Any additional prose is audit context only. A request cannot make itself valid by asserting a current routing tuple or cardinality.

## Decision 4 — MVP transition surface is intentionally narrow

The Gate MVP supports only an already-formal coordination Issue whose current selected routing is `Lead / resolve-question` and whose requested target is one of the two legal successors already owned by `agents/workflow.md`:

- `Reviewer / review-openspec` for a material semantic correction ready for independent review;
- `Executor / implement-change` when clarification is resolved without material semantic change and implementation remains the legal consumer.

The Gate verifies that the production classifier selects the same Issue at the current `Lead / resolve-question` routing. The Gate does not determine the semantic judgment that caused Lead to choose one of the two legal targets; that judgment remains Lead-owned and is represented by the source action result.

No generic topology registry is added. Expanding Gate ownership to other actions is deferred until this live boundary is proven.

## Decision 5 — Gate outcomes are ACCEPTED, REJECTED, or INDETERMINATE

- `ACCEPTED`: current complete reconstruction selects the request Issue at `Lead / resolve-question`, the requested target is one of the bounded legal successors, immediate source preconditions still match, routing mutation succeeds, and post-write routing is freshly verified.
- `REJECTED`: the request is syntactically valid but current authoritative state does not authorize it, for example a different selected Issue, changed source routing, non-formal Issue, or unsupported target.
- `INDETERMINATE`: complete/provenance-qualified current authorization cannot be established, including incomplete enumeration, contradictory routing/Change identity, or multiple formal workflows.

Only `ACCEPTED` may mutate routing. `REJECTED` and `INDETERMINATE` leave routing unchanged.

## Decision 6 — Serialize authorization, then re-read current state

Configure one repository-wide GitHub Actions concurrency group for the transition Gate and do not cancel an in-progress Gate run merely because a newer request appears.

Concurrency is execution serialization, not workflow state. Each Gate run reconstructs GitHub state when it actually executes. If request B waited behind request A and A changed routing, B observes the newer state and is rejected rather than replaying its earlier assumptions.

This provides a bounded stale-stop property without adding a lock, lease, heartbeat, claim, or hidden queue to repository workflow state.

## Decision 7 — Durable Gate evidence is audit evidence only

For every processed request, emit a durable Gate result carrying enough information to diagnose the decision:

- triggering Issue/comment identity;
- requested target;
- completeness/provenance disposition;
- formal-active Issue identities;
- selected Issue/current routing from the classifier;
- Gate outcome and reason;
- post-write routing when accepted.

The result comment is not an authorization token for a later run. Every later Gate execution reconstructs GitHub state again.

## Decision 8 — Correct prior Agent-owned executable-consumption claims

Shared governance and the two Skills previously modified by #133 must stop claiming that the Scheduled Agent itself is the demonstrated live executor of repository Python.

- `openspec-explore` keeps its existing procedural current-state/cardinality safety obligations, but the MVP does not place Explore admission behind the Gate.
- `openspec-change` keeps Lead specification/activation authority. For the already-formal `resolve-question` successor transition covered by the MVP, it submits transition intent and consumes the Gate outcome instead of directly changing routing. Propose activation remains outside this MVP.

The production classifier remains executable and test-owned; only the live ownership assumption changes.

## Decision 9 — Direct Issue-label bypass is an explicit MVP limitation

The current ChatGPT GitHub connector still has `Issues: write`, and Issue comments and routing-label writes share that permission class. The MVP therefore cannot truthfully claim that the Agent is physically incapable of bypassing the Gate and writing routing labels directly.

This revision treats that as a known limitation. A direct routing-label mutation outside the Gate is not evidence that the Gate accepted a transition, but this MVP does not yet add routing-event provenance enforcement that would make such a write unusable for later authorization.

Routing-event provenance hardening and connector/action-level capability restriction are deferred. The MVP's acceptance criterion is narrower: demonstrate a real repository-hosted executable authorization path that the Scheduled Agent can request and that performs accepted routing transitions from fresh authoritative state.

## Decision 10 — PR-stage tests and post-merge live canary are distinct

A newly added `issue_comment` workflow cannot be exercised as a live default-branch event trigger until that workflow exists on the default branch.

Before merge, regression/integration tests exercise the same transition adapter with representative GitHub event/state fixtures and verify classifier consumption, mutation gating, stale requests, incomplete state, and serialized re-evaluation behavior.

After the implementation is merged to the default branch, lifecycle completion requires live canary evidence showing:

1. one valid transition request reaches the real `issue_comment` workflow, executes the repository adapter/classifier, and produces `ACCEPTED` with the expected routing mutation; and
2. one invalid/stale request reaches the same live path, produces `REJECTED` or `INDETERMINATE`, and leaves routing unchanged.

PR-stage tests MUST NOT be described as proof that the default-branch event trigger already ran.

## Decision 11 — External Scheduled Task prompts remain unchanged

No Scheduled Task slot count, cadence, title, or prompt logic is moved into this Change. Scheduled Agents continue to load default-branch governance. The new behavior is repository-hosted: the governed action submits a transition request comment and GitHub Actions performs the executable authorization.

## Traceability

- Source Explore: #133 `issuecomment-5373937613`.
- Observation-provenance Reviewer correction: #133 `issuecomment-5377194503`.
- Prior implementation READY: #133 `issuecomment-5379787305` at PR #134 head `0727b030bb9c27d311a390e9d765d4421302abaa`.
- Runtime-consumption implementation finding: #133 `issuecomment-5379837891`.
- Runtime capability blocker: #133 `issuecomment-5379922085`.
- Existing production classifier: `src/investment_strategy/workflow_dispatch.py`.
- Existing topology owner: `agents/workflow.md`.
- Modified canonical requirement: `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- Added MVP requirement: `Issue-comment Transition Gate executes live formal-routing authorization`.
- Decisions 1–1A preserve the classifier/provenance groundwork.
- Decisions 2–7 define the live Gate path.
- Decision 8 defines governance/Skill correction.
- Decision 9 states the bypass limitation explicitly.
- Decision 10 defines honest live verification.

## Risks and mitigations

### Risk: Gate becomes a second workflow engine

Mitigation: constrain the MVP to one existing source action and its two existing legal successors. `agents/workflow.md` remains topology authority; the Gate performs authorization/mutation only.

### Risk: Request prose becomes stale authority

Mitigation: treat comments as intent only. Current source routing, Change identity, cardinality, selection, and completeness are always reacquired by the Gate.

### Risk: Concurrent requests race

Mitigation: serialize Gate runs and re-read current GitHub state when each run executes. A stale queued request is rejected.

### Risk: Direct label mutation bypass remains possible

Mitigation: state the limitation explicitly and do not claim permission-layer prevention. Routing-event provenance or action-level capability restriction is separate hardening after the MVP proves the live Gate path.

### Risk: Unit tests are mistaken for live integration

Mitigation: require a post-merge default-branch `issue_comment` canary before lifecycle completion and keep that evidence distinct from PR-stage tests.
