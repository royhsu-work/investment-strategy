# Change: Enforce runtime dispatch preconditions

## Why

#105 / Change `enforce-dispatch-cardinality-preflight` correctly established WIP=1, complete repository-wide cardinality reconstruction, fail-closed dispatch, and pre-activation Explore/Propose guards. #133 then added one production executable classifier plus same-invocation observation-provenance inputs, and the implementation through PR #134 head `0727b030bb9c27d311a390e9d765d4421302abaa` made regression tests consume that production implementation.

Reviewer implementation finding `issuecomment-5379837891` identified the remaining architecture gap: the real Scheduled-Agent path still has no demonstrated callable boundary that executes repository Python before normal work or routing mutation. The current Skills can instruct the Agent to execute `workflow_dispatch.py`, but that instruction is still an Agent interpretation bridge. Green tests therefore prove classifier behavior, not live runtime consumption.

The corrected target moves live executable ownership to a repository-hosted GitHub Actions Transition Gate. A Scheduled Agent submits a minimal transition intent as an Issue comment; the Gate independently reconstructs current GitHub state, executes the production classifier, accepts or rejects the requested transition, and performs the routing mutation only after acceptance. The pure classifier remains reusable and stateless; the Gate becomes the effectful runtime adapter.

This revision is deliberately an MVP. It proves the end-to-end live boundary first for normal formal `Lead / resolve-question` routing transitions. It does not claim that the current ChatGPT GitHub connector has lost direct Issue-label write capability, and it does not yet move Explore admission or Propose activation behind the Gate. Those are explicit limits, not hidden claims of hard enforcement.

## What Changes

- Preserve `src/investment_strategy/workflow_dispatch.py` as the one repository-owned pure classifier/precondition implementation used by executable regressions and by machine authorization surfaces.
- Add one effectful repository-owned transition adapter executed by GitHub Actions. It performs authoritative GitHub acquisition, builds provenance-qualified classifier input, executes the production classifier, validates the MVP transition request, performs the routing mutation only on acceptance, and freshly verifies the resulting routing.
- Trigger the MVP Gate from a newly created Issue comment on an already-formal coordination Issue. The request carries only target intent (for example `/transition reviewer review-openspec`); the Issue number, current Change identity, current routing, cardinality, and completeness are acquired by the Gate and MUST NOT be trusted from comment prose.
- Limit the MVP Gate to normal formal transitions whose current source is `Lead / resolve-question` and whose requested target is one of its two existing legal formal successors: `Reviewer / review-openspec` or `Executor / implement-change`. The Gate does not create or redefine lifecycle topology.
- Serialize Gate authorization runs through one repository-wide GitHub Actions concurrency group. Every queued request reconstructs current GitHub state when its run executes; a request that became stale while waiting is rejected rather than replaying old state.
- Define three Gate outcomes: `ACCEPTED`, `REJECTED`, and `INDETERMINATE`. Only `ACCEPTED` may mutate routing. `INDETERMINATE` is fail-closed for incomplete enumeration, provenance failure, multiple active workflows, or otherwise unprovable current authorization.
- Require a fresh post-write read after an accepted mutation and durable Gate result evidence sufficient to reconstruct the request, classifier decision, and resulting routing without making the result comment workflow state.
- Correct the earlier Agent-owned executable-consumption wording in shared governance and the two previously modified OpenSpec Skills. Scheduled Agents remain responsible for their governed action judgment and authoritative current-state reconstruction, but the MVP's live executable routing authorization is owned by the GitHub Actions Gate rather than by an assumed ability to execute repository Python inside the Scheduled-Agent container.
- Keep the existing classifier, provenance, and audit-evidence implementation work as reusable groundwork; add new RED/GREEN/REFACTOR/VERIFY work only for the Gate MVP and the semantic corrections required to stop claiming an unavailable Agent-side runtime hook.
- Require post-merge live canary evidence because a newly added `issue_comment` workflow is not a live trigger until that workflow exists on the default branch. PR-stage tests may verify the same adapter with event/GitHub fixtures, but they MUST NOT be represented as proof that the default-branch event path already ran.
- Keep external Scheduled Task prompts bootstrap-only.

## Affected Capabilities

### Modified

- `scheduled-agent-workflow`
  - authoritative same-invocation GitHub reconstruction remains required for current-state predicates;
  - production classifier remains shared by executable regression and machine authorization;
  - live executable ownership moves from an assumed Scheduled-Agent helper invocation to a GitHub Actions Transition Gate for the bounded MVP transition surface;
  - serialized request handling provides stale-stop behavior at the Gate;
  - direct connector label-write bypass remains an explicit MVP limitation rather than being misrepresented as permission-layer prevention.

## Scope

In scope:

- The existing pure production dispatch classifier and provenance-bearing input contract.
- One GitHub Actions `issue_comment` Transition Gate and one repository-owned effectful adapter that consumes the production classifier.
- Minimal transition intent syntax carried by a newly created Issue comment.
- Fresh complete repository reconstruction by the Gate; current Issue/routing/Change/cardinality values are never accepted from request prose.
- Repository-wide Gate concurrency and fresh execution-time stale detection.
- MVP support only for already-formal `Lead / resolve-question -> Reviewer / review-openspec` and `Lead / resolve-question -> Executor / implement-change` routing transitions.
- `ACCEPTED` / `REJECTED` / `INDETERMINATE` result behavior, accepted-only routing mutation, post-write verification, and durable audit evidence.
- PR-stage adapter/regression tests plus post-merge live canary requirements for one accepted and one rejected request.
- Correcting prior governance/Skill wording that incorrectly made Scheduled-Agent execution of repository Python the live enforcement boundary.

Out of scope for this MVP:

- Removing the ChatGPT connector's direct `Issues: write` / routing-label capability or claiming that direct bypass is physically impossible.
- Routing-event provenance hardening that would make non-Gate routing writes unqualified for later authorization.
- Moving Explore admission or substantive Explore action-entry authorization behind the Gate.
- Moving Propose activation (`Change: unset -> non-unset`) or its pre/post activation acceptance behind the Gate.
- Migrating every formal lifecycle action to the Gate in this revision.
- Automatically selecting a winner from an already multiple-active repository state.
- Automatically rolling back or repairing a direct unauthorized label mutation.
- A lock, lease, heartbeat, hidden queue, durable claim, central workflow engine, global priority score, or second workflow DAG.
- Moving workflow semantics into Scheduled Task prompts.
- Treating historical comments, Issue prose, previous invocation output, model memory, or cache as a current-state source.
- Changing Human authority, Reviewer independence, role ownership, or the legal lifecycle topology in `agents/workflow.md`.

## Skill maintenance traceability

- `agents/skills/openspec-explore/SKILL.md` — **Modified**. Sources: the earlier #133 semantic target plus Reviewer implementation finding `issuecomment-5379837891`. Preserve Explore's research/admission responsibility and current-state freshness rules, but remove the claim that the Scheduled Agent itself is the demonstrated live executor of repository Python. The Gate MVP does not yet own Explore admission.
- `agents/skills/openspec-change/SKILL.md` — **Modified**. Sources: the earlier #133 semantic target plus Reviewer implementation finding `issuecomment-5379837891`. Preserve Lead specification/activation authority. For the MVP's already-formal `resolve-question` successor transition, submit target intent to the shared Transition Gate rather than directly mutating routing; do not broaden the MVP to Propose activation.

No Skill is added or removed. The GitHub Actions Gate is shared runtime infrastructure, not a user-triggered Skill.

## Traceability

- Source decision-complete Explore: #133 `issuecomment-5373937613`.
- Observation-provenance semantic correction: Reviewer finding #133 `issuecomment-5377194503`.
- Completed prior implementation target and final verification: #133 `issuecomment-5379787305`, PR #134 head `0727b030bb9c27d311a390e9d765d4421302abaa`.
- Runtime-integration implementation finding that requires this correction: #133 `issuecomment-5379837891`.
- Capability blocker that demonstrated the Scheduled-Agent container has no proven repository execution boundary: #133 `issuecomment-5379922085`.
- Prior semantic remediation: #105 / Change `enforce-dispatch-cardinality-preflight`.
- Existing canonical requirement: `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- New MVP requirement in this delta: `Issue-comment Transition Gate executes live formal-routing authorization`.
- Capability delta: `specs/scheduled-agent-workflow/spec.md`.
- Design: `design.md`.
- Implementation slices: `tasks.md`.
