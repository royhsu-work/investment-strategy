# Change: Enforce cross-role wake barrier

## Why

Current default-branch capability truth and `agents/workflow.md` require `workflow-dynamic` execution to keep the selected invocation role fixed and to end rather than redispatch into a different role. Issue #161 demonstrated that this desired cross-role wake boundary is distinct from fresh-worker isolation, while later implementation review established that the repository does not own the enclosing external ChatGPT Scheduled-Agent execution context strongly enough to mechanically force that host to terminate a wake.

The exact upstream Explore result is Issue #161 comment `5440915970` (`PROPOSAL_READY`, revision `387105aee9788f1abfd4fb997f3007b7edbd248a`). The later Human decision in Issue #161 comment `5452121226`, bound to escalation `issuecomment:5448395244`, explicitly chooses Option 3: keep the cross-role wake barrier as prompt/model-level enforcement and no longer require machine/script enforcement for this Change. This revision preserves that latest Human decision without changing workflow topology or role authority.

## What Changes

- Keep one Scheduled-Agent wake conceptually bound to the role selected by its first repository-owned `AUTHORIZE` decision as an authoritative model/governance instruction.
- Preserve fresh repository reconstruction and a fresh mapped worker for every successor action.
- Allow same-role successor actions on the same coordination Issue to continue during the same wake after fresh dispatch.
- When fresh dispatch selects a different role, require the current mapped model invocation to treat the cross-role handoff as wake-terminal: preserve the durable successor routing and end rather than execute the different-role successor in the same wake.
- Remove the requirement that repository runtime code carry/compare an invocation-local `initial_role`, provide a script-owned hard stop, or mechanically prove termination of the external ChatGPT task.
- Align shared default-branch governance and canonical message presentation with `agents/workflow.md` so the model receives one coherent cross-role termination instruction. External Scheduled Task prompts remain bootstrap-only and defer to current default-branch governance instead of copying role-specific workflow logic.
- Reconcile the earlier mechanical helper/tests that were introduced solely for the superseded machine-enforcement requirement after independent OpenSpec review.

The dispatcher selection algorithm, formal workflow topology, WIP=1/finish-first behavior, Human authority, routing tuples, action ownership, and external scheduler topology/cadence are unchanged.

## Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: clarify that the first selected role is treated as fixed for one Scheduled-Agent wake at the authoritative prompt/model-governance layer, while same-role fresh-worker continuation remains work-conserving and no repository-owned mechanical hard-stop guarantee is required.

## Impact

Expected implementation surfaces are limited to shared Scheduled-Agent governance/presentation and reconciliation of the earlier continuation-helper/tests that encoded the superseded mechanical guarantee. This Change does not introduce an OpenAI API key, a GitHub Actions-hosted model worker, Work wake attestation, a queue, lease, heartbeat, sequence counter, persistent wake-role state, fixed-role scheduler, or second workflow DAG.

The accepted residual risk is explicit: repository governance can instruct the external Scheduled-Agent model to end at a cross-role boundary, but the repository cannot mechanically guarantee compliance by the external ChatGPT execution host under this downgraded Option 3 contract.

Refs #161
Refs #155
