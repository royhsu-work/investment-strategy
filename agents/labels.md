# Scheduled Agent Labels

Labels are repository vocabulary; current routing authority is the action:<action> label plus the
Issue lifecycle and immutable Change. Role is derived by role_for(Action).

## Action labels

Use only the finite Action labels:

- action:explore-change
- action:propose-change
- action:resolve-question
- action:finalize-change
- action:finalize-archive
- action:review-openspec
- action:review-implementation
- action:review-archive
- action:implement-change
- action:merge-implementation-pr
- action:merge-archive-pr

An open formal Issue has one action label. An open pre-activation Issue may use only the bounded
explore/propose Actions. Application owns routing mutations and validates the exact current label.

Legacy role labels are migration/source evidence only. Do not add or refresh them as normal routing.
Colors and descriptions do not carry authority.

## Advisory and Human capabilities

advisory:idle is presentation for an idle Lead advisory, never a routed Action.
human:approved remains a reserved provenance-bound Human capability; the label alone is insufficient.
intake:approved remains administrative capability where an approved Human admission contract requires
it; scheduled Roles never add, remove, restore, or manufacture either reserved capability.

Human-operated label creation is administrative setup. Scheduled execution does not infer authority
from actor identity, a connector, a label snapshot, Issue title, timing, or comment ordering.
