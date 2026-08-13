# Scheduled Task migration

External scheduler configuration and repository workflow governance have separate ownership.

Each external Scheduled Task uses a common bootstrap prompt: read `README.md` and default-branch `agents/AGENTS.md`, derive dispatch mode only from default-branch governance, use the legacy assigned role only in `fixed-role`, and under `workflow-dynamic` reconstruct the repository-selected role/action before loading the mapped role and skill.

Migration retains the existing three wake slots externally. Exact slot count/topology/cadence is outside repository capability/runtime state and is not modeled as durable workflow state.

Associated-conversation and result surfacing are external product behavior, not repository workflow state.
