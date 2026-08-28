## MODIFIED Requirements

### Requirement: Workflow-dynamic dispatch derives one fixed invocation role from durable workflow state

In `workflow-dynamic` mode, a scheduled wake SHALL reconstruct current durable workflow state before selecting a role. If exactly one active workflow exists, its valid routing tuple SHALL determine the first invocation role/action and mapped skill.

Authoritative default-branch Scheduled-Agent governance MUST instruct the active model to treat the role from the first repository-owned `AUTHORIZE` decision as fixed for the remainder of that Scheduled-Agent wake. Every later mapped action in the same wake MUST still come from fresh repository-owned dispatch and MUST use a fresh mapped worker that reloads current default-branch governance and reconstructs its own durable preconditions.

A fresh dispatch MAY select another action owned by the same role; when that successor is immediately actionable, it MAY continue within the same Scheduled-Agent wake as a fresh mapped worker. Action identity is therefore not wake-immutable.

A routing handoff MAY persist a different next role/action and fresh dispatch MAY select that durable successor. When the selected role differs from the role being executed by the current wake, authoritative governance MUST instruct the current model invocation to end without executing the different-role successor. A later Scheduled-Agent wake SHALL reconstruct current durable state and perform ordinary repository-owned dispatch before that role executes. The wake barrier MUST NOT rewrite the successor routing, invent a defer command, or persist wake-role state in repository workflow state.

This cross-role wake boundary is a prompt/model-level behavioral contract. This capability MUST NOT require repository runtime code to retain or compare an invocation-local `initial_role`, provide a script-owned hard stop for the external ChatGPT execution context, use an OpenAI API key or GitHub Actions-hosted model worker, require a Work wake attestation, or claim repository-verifiable proof that the external host terminated. Repository tests MAY prove that authoritative governance presents the required instruction; they MUST NOT represent that evidence as mechanical proof of external-host compliance.

External Scheduled Task prompts MUST remain bootstrap/delegation surfaces that load and follow current default-branch governance rather than duplicating the workflow DAG or role-specific successor policy. The dispatcher MUST NOT introduce model-derived global urgency, cross-role priority scoring, fixed-role scheduler semantics, or a second workflow DAG.

#### Scenario: Active workflow routes to Reviewer

- GIVEN dispatch mode is `workflow-dynamic`
- AND the single active workflow has valid routing `agent:reviewer + action:review-openspec`
- WHEN a Scheduled Task dispatches the wake
- THEN Reviewer is selected as the role for that wake
- AND authoritative governance instructs the active model to keep that role for the current wake
- AND the `review-openspec` skill is loaded for a fresh mapped worker
- AND any legacy external Lead/Reviewer/Executor assignment is ignored for role selection

#### Scenario: Handoff changes the next owner

- GIVEN the current Scheduled-Agent wake is executing Lead
- AND Lead durably completes its action and legally hands off to Reviewer
- WHEN fresh repository-owned dispatch selects the Reviewer successor
- THEN the durable Reviewer routing and machine selection are preserved
- AND authoritative governance instructs the current Lead wake to end
- AND the current model does not execute Reviewer work in that same wake
- AND a later Scheduled-Agent wake must fresh-reconstruct before Reviewer may execute

#### Scenario: Same-role successor remains work-conserving

- GIVEN the current Scheduled-Agent wake is executing Lead
- AND Lead durably completes one action on the selected coordination Issue
- AND fresh repository-owned dispatch selects another immediately actionable Lead action on that same Issue
- WHEN the wake evaluates continuation under current governance
- THEN the wake may continue
- AND the successor executes as a fresh Lead mapped worker
- AND the prior worker context does not authorize or supply current-state evidence for that successor

#### Scenario: Cross-role barrier does not create durable wake state

- GIVEN a fresh dispatch selects a successor owned by a role different from the current wake role
- WHEN authoritative governance instructs the current wake to terminate at the cross-role boundary
- THEN no Issue field, routing label, comment protocol, lease, heartbeat, queue entry, attestation field, or hidden repository state is created to remember the wake role
- AND the already durable workflow routing remains the only successor workflow state consumed by the next wake

#### Scenario: Prompt-level boundary does not claim a mechanical host guarantee

- GIVEN the external ChatGPT Scheduled-Agent host does not expose a repository-owned hard-stop or repository-verifiable per-run wake attestation
- AND Human has approved prompt/model-level enforcement for this capability
- WHEN the repository verifies the cross-role wake policy
- THEN tests verify the authoritative governance instruction and durable routing behavior
- AND no test claims that repository code can mechanically prove termination of the external ChatGPT task
- AND no OpenAI API key or GitHub Actions-hosted model execution is required
