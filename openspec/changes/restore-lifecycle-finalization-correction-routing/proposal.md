## Why

Issue #169 exposes a bounded lifecycle-topology gap. `Lead / finalize-change` can prove that
continuation requires a material specification, canonicalization, or lifecycle-contract correction,
but the current executable Action model has no legal successor to `Lead / resolve-question`. The
action can therefore remain associated with a diagnostic recovery classification even though Lead's
existing specification-authority path is the correct owner.

The same gap exists in the return direction. After `Lead / resolve-question` establishes that no
material semantic revision remains, the already-merged implementation and post-merge lifecycle may
again be the legal consumer. The current model has no bounded result for returning to
`Lead / finalize-change`, so it cannot express that existing ownership boundary without inventing
another recovery state.

The latest Human-approved direction is recorded in #169 comment `issuecomment-5551181808`. It
confirms the smallest correction:

```text
finalize-change + SPEC_BLOCKER
    -> resolve-question

resolve-question + LIFECYCLE_READY
    -> finalize-change
```

The enabling repository-application repair is already active on default-branch revision
`961384a79ef169658f031c03f8f1ba551b650a59` through PR #200. That repair removes transport
correlation and historical dispatch-result replay from application authorization and provides one
fresh, application-owned materialization boundary. It is enabling infrastructure, not a change to
this lifecycle meaning.

## What Changes

- Reuse the existing `SPEC_BLOCKER` result for `finalize-change` only when a material
  specification/canonicalization/lifecycle-contract defect is outside finalize-change's authority.
- Add exactly one bounded result, `LIFECYCLE_READY`, for `resolve-question` when no material
  semantic revision remains, the already-merged implementation remains valid, and the post-merge
  lifecycle is again the legal consumer.
- Keep material OpenSpec correction on `READY_FOR_OPENSPEC_REVIEW -> review-openspec` and preserve
  independent exact-revision semantic review before later consumption.
- Keep the existing `resolve-question + READY -> implement-change` transition unchanged.
- Keep action-local semantic-neutral mechanical recovery action-local; a diagnostic classification
  does not become a new workflow state or a substitute for ownership/routing.
- Express the correction in the executable Action model and its canonical workflow requirement,
  with regression coverage at the transition/application boundary.

## Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: add the two bounded lifecycle-correction transitions and their
  conditions while retaining existing review, implementation, archive, Human, and fail-closed
  contracts.

## Scope Boundaries

- No new Action, Role, recovery state machine, hidden lifecycle state, retry/lock/lease/heartbeat,
  mailbox, second DAG, or generic fault engine.
- No change to the approved native-closing outcome owned by #159.
- No bypass of independent `review-openspec`, exact-revision validation, exact-head review or
  merge gates.
- No direct archive mutation from `resolve-question`; normal archive mechanics remain repository
  automation-owned.
- No transport or external scheduler state becomes workflow state. The application continues to
  derive authority from current default-branch state and fresh classification.

## Evidence and Traceability

- Human architecture direction: #169 comment `issuecomment-5551181808`.
- Semantic source Issue: #169, current default-branch routing `action:propose-change` with
  `Change: unset`.
- Current executable source: `src/investment_strategy/scheduled_agent_action_model.py`.
- Current canonical capability: `openspec/specs/scheduled-agent-workflow/spec.md`, especially the
  executable-transition and Lead review/finalize requirements.
- Concrete regression evidence: #159's historical archive canonicalization defect, used only to
  justify the bounded correction ownership and not to reopen or redefine #159.

