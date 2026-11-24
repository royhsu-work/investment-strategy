# Why

An approved necessary separate follow-up is already a repository obligation, but the current consequence path can accept readiness or review evidence without a tracker or a preserved dependency. #470's recorded required-work decision, accepted application intent with no tracker/dependency effect, and later Reviewer finding and #473 creation are the observed counterexample; the earlier PASS preceded the recorded Human intent and is not retroactively a failure. See [#474](https://github.com/royhsu-work/investment-strategy/issues/474), [accepted Explore](https://github.com/royhsu-work/investment-strategy/issues/474#issuecomment-7138031235), and its [accepted application decision](https://github.com/royhsu-work/investment-strategy/issues/474#issuecomment-7138030268). The complete-set dependency replacement lost-update and unknown-create two-world cases were reproduced in a fault model, not observed production races.

# What Changes

- Make every approved, exact-source required follow-up a machine-observable tracking and dependency obligation, independent of a worker's omission of requested effects. Preserve the distinction between required, optional, and unregistered natural-language intent.
- Establish one source-linked tracker with the canonical action-only pre-activation tuple, and preserve every still-applicable necessary prerequisite across split delivery and interruption. Existing qualified explicit dependencies and unrelated work remain intact.
- Enforce the same logical completion boundary at applicable readiness, review, lifecycle, and successor decisions. A semantic READY/PASS cannot substitute for tracker and dependency completeness; the source decision is preserved before effects that depend on it.
- Reconcile missing effects from fresh authoritative evidence, without duplicate trackers, semantic replay, guessed writes, or rewind. Preserve eventual delivery and eventual correctness; do not promise a transport guarantee that has not been established.
- Retain formal-first selection, WIP=1 execution eligibility, existing independent gates and native dispatch/application ownership.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scheduled-agent-workflow`: required-follow-up admission, source-linked materialization and dependency preservation, shared completion and eligibility.

## Scope and non-goals

One independently deliverable Change on current N-1, including the complete source-to-consequence-to-eligibility contract and actual integration/regression tests. All mandatory work remains in this Change; no new required separate follow-up is declared. No new workflow Action, routing label, lifecycle state, registry, scheduler, workflow graph, lock, recovery cursor, retry counter, or second dispatcher. No incident-number hardcoding, generic prose inference, direct external GitHub API, new credentials, or native dependency mutation requirement. No global strong consistency or total sequential processing. No change to the already-approved #470, #473, #468 or #435 scope, dependencies, or accepted evidence. #474 must be formally complete before those existing dependents become eligible.

## Parent outcome and exit

Preserve all Human-approved outcomes: one durable source-linked tracker at the required-defer boundary; necessary dependency preservation; lawful authority, source fidelity, idempotency and recovery; eventual consistency and eventual correctness; no scope expansion or guessed writes. Deliver these together under existing review/merge/archive gates. The acceptance matrix must demonstrate real RED/GREEN and strict validation, including omitted effect, invalid READY/PASS, optional work, interrupted create/reuse and route, unknown response and positive recovery, multiple/concurrent independent prerequisite contributions, no pre-existing blocker, cycle rejection, qualified terminal release, and producer-self continuation. The permanently unobservable external-write counterexample is an evidence boundary, not an approved reduction of delivery requirements: if an approved requirement cannot be met with the lawful actuator and evidence, return through existing Lead/Human authority rather than claiming completion or silently relaxing it.
