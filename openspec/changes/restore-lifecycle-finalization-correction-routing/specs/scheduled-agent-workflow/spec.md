## MODIFIED Requirements

### Requirement: The executable model derives transitions and successors

The default-branch executable workflow model SHALL own ACTION_ROLE, the finite Action vocabulary, legal TRANSITIONS, role_for(action), next_action(current_action, typed_result), and select_work(authoritative_observations). A worker MAY return only a bounded typed result/evidence envelope. The worker MUST NOT choose an arbitrary Issue, Role, Action, successor, target, retry, or success meaning.

next_action SHALL derive at most one legal successor or terminal state from the current Action and typed result. The application SHALL fresh-reauthorize the source Action, derive the successor from the current state, apply exact necessary effects, and fresh-observe postconditions before treating the successor as current. There is no second production DAG, generic orchestration framework, or recovery state machine.

For the bounded lifecycle-correction path, `finalize-change` MAY return `SPEC_BLOCKER` only when fresh evidence proves a material specification, canonicalization, or lifecycle-contract defect outside finalize-change's action-local authority; that result SHALL derive `Lead / resolve-question`. Progressing external work, a known semantic-neutral mechanical recovery, a genuine Human-reserved decision, or ambiguous evidence SHALL continue through their existing action-local or fail-closed handling and MUST NOT be relabeled as this correction edge. `RECOVERY_DECISION_REQUIRED`, when used as a diagnostic classification, SHALL NOT become a durable workflow state or replace ownership routing.

`resolve-question` MAY return exactly one additional bounded result, `LIFECYCLE_READY`, only when no material semantic OpenSpec revision remains, the already-merged implementation remains valid, and the post-merge lifecycle is again the legal consumer; that result SHALL derive `Lead / finalize-change`. A material OpenSpec correction SHALL continue to return `READY_FOR_OPENSPEC_REVIEW` and derive `Reviewer / review-openspec`, while an implementation-ready resolution SHALL continue to return `READY` and derive `Executor / implement-change`.

#### Scenario: Result derives a unique successor

- GIVEN implement-change returns a valid SPEC_BLOCKER
- WHEN application evaluates the typed result against the current Action
- THEN it derives resolve-question
- AND the worker cannot substitute another Lead Action or Issue

#### Scenario: Stale result is rejected

- GIVEN an Action result was produced from a stale Issue, Change, PR head, or default-branch revision
- WHEN application fresh-reauthorizes the effect
- THEN it fails closed
- AND it does not apply a guessed successor or replay completed work

#### Scenario: Material finalize defect routes to the existing question owner

- GIVEN Lead owns `finalize-change`
- AND fresh lifecycle evidence proves a material specification, canonicalization, or lifecycle-contract defect outside finalize-change's authority
- AND the evidence does not describe merely progressing external work or a known semantic-neutral mechanical recovery
- WHEN Lead returns `SPEC_BLOCKER`
- THEN application derives `resolve-question`
- AND it does not retain finalize-change merely as `RECOVERY_DECISION_REQUIRED`
- AND it does not blindly replay the same failing mutation

#### Scenario: Mechanical recovery remains action-local

- GIVEN Lead owns `finalize-change`
- AND fresh evidence proves a known semantic-neutral repository-defined mechanical recovery with satisfied preconditions
- WHEN Lead evaluates the recovery
- THEN the recovery remains within the existing finalize-change procedure
- AND Lead does not use `SPEC_BLOCKER` to manufacture a specification-question handoff

#### Scenario: Lifecycle-ready resolution returns to finalization

- GIVEN Lead owns `resolve-question` for an active immutable Change
- AND no material semantic OpenSpec revision remains
- AND the already-merged implementation remains valid
- AND the post-merge lifecycle is again the legal consumer
- WHEN Lead returns `LIFECYCLE_READY`
- THEN application derives `finalize-change`
- AND the successor waits for a later fresh wake

#### Scenario: Material correction still requires independent review

- GIVEN Lead owns `resolve-question`
- AND resolving the question materially changes OpenSpec meaning or representation
- WHEN Lead returns `READY_FOR_OPENSPEC_REVIEW`
- THEN application derives `review-openspec`
- AND a fresh independent exact-revision Reviewer gate remains required before later consumption

#### Scenario: Implementation-ready resolution remains unchanged

- GIVEN Lead owns `resolve-question`
- AND the approved implementation may resume without a material OpenSpec revision
- WHEN Lead returns `READY`
- THEN application derives `implement-change`
- AND the new lifecycle-return result is not substituted

