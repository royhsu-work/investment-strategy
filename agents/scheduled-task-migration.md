# Scheduled Task migration

External scheduler configuration and repository workflow governance have separate ownership.

Each external Scheduled Task uses a common bootstrap prompt: read `README.md` and default-branch `agents/AGENTS.md`, derive dispatch mode only from default-branch governance, use the legacy assigned role only in `fixed-role`, and under `workflow-dynamic` reconstruct the repository-selected role/action before loading the mapped role and skill.

Migration retains the existing three wake slots externally. Exact slot count/topology/cadence is outside repository capability/runtime state and is not modeled as durable workflow state.

Ordinary wakes are Human-silent. Reviewer/Executor workflow results, checkpoints, handoffs, merge results, and `EXECUTION_EXCEPTION` evidence remain repository-durable only; ordinary Lead results and exception evidence do likewise. Only a Lead-owned unresolved `HUMAN_DECISION_REQUIRED` condition is eligible for Human-facing scheduled delivery.

Actual notification, associated-conversation, and result surfacing remain external product configuration and are not repository routing, waiting, authorization, or completion state. Scheduled Task prompts must not emit `No Human action is required` or equivalent status noise as a substitute for silence.

Scheduled Task prompts remain bootstrap-only and must not duplicate the shared exception-capture or invocation-finalization protocol; they only load default-branch governance and do not become a second execution contract.
