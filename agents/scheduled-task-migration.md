# Scheduled Task migration

External scheduler configuration and repository workflow governance have separate ownership.

Each external Scheduled Task uses a bootstrap prompt that reads README.md and current default-branch
agents/AGENTS.md, then obtains the repository-owned executable dispatch. Under
Scheduled-Dispatch-Mode: workflow-dynamic, the machine-selected Action is authoritative and its Role
is derived from role_for(Action). The prompt does not select a Role or Action.

The Asia/Taipei daily shard is bounded transport only. It records one request, one exact Actions run,
and one structured result, and carries no lifecycle, routing, successor, retry, or mailbox authority.
Rollover establishes and observes today's shard before retiring an older one; an in-flight request/run/
result chain remains valid. Slot count, cadence, notification, and associated-conversation behavior
are external product configuration.

GitHub Project/Kanban fields are presentation only. They do not participate in dispatch, routing,
authority, or gate decisions; repository Issue/Change/Action state remains authoritative.

Scheduled prompts remain bootstrap-only. They do not duplicate application, exception, result, or
finalization semantics and do not emit status noise for ordinary silent wakes.

The default-branch merge is the activation boundary; an unmerged governance PR is review target/input
and must not govern its own current invocation. Pre-activation free-form/legacy messages remain
historical evidence under then-authoritative default-branch governance and are not a retroactive
template finding.
