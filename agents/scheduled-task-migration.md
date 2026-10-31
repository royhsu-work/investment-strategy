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

Before the normal dispatch, obtain the current Asia/Taipei date and the complete paginated all-state
Issue snapshot. Reuse `scheduled_agent_checkin.py` canonical Runtime Issue/date parsing and the
`plan_rollover_handoff` contract. A unique valid open current-day shard proceeds to normal dispatch;
closed/duplicate/malformed/future current-day identities or incomplete evidence fail closed. If today
is missing, inspect all older qualified Runtime shards, actual commentability (including a closed
shard only if comment creation and event delivery have been independently proven), locked status,
duplicate dates and complete paginated comment history. Only the latest *unique eligible* existing
older shard can carry the request; never assume yesterday exists or use it as a dispatch transport.
Missing permissions, incomplete pages, ambiguity or no eligible target mean no mutation.

Before writing, independently fresh-recheck the missing today-shard, the exact older target, current
comment permission and same-day request history. If an exact valid request for the local day is
already present, exit with no new comment. Otherwise the authorized external connector creates only
this exact three-line Issue comment (including final newline):

```text
ROLLOVER_REQUEST
Requested-Day: YYYY-MM-DD
Source-Shard: N
```

Fresh-read and verify the created comment id/body/actor and the source shard, then **end that wake**.
Do not create or close a shard, await or poll Actions, issue `DISPATCH_REQUEST` on the older shard,
or execute any Role/Action. The native `.github/workflows/scheduled-agent-checkin.yml` remains
scheduled independently, and its genuine `issue_comment: created` gate calls the same canonical
Check-in owner under the existing non-cancelling concurrency group. A `GITHUB_TOKEN`-authored comment
is not proof of event delivery. After actual Check-in success, only a separate fresh wake may
reconstruct default-branch governance and perform executable normal dispatch.

GitHub Project/Kanban fields are presentation only. They do not participate in dispatch, routing,
authority, or gate decisions; repository Issue/Change/Action state remains authoritative.

Scheduled prompts remain bootstrap-only. They do not duplicate application, exception, result, or
finalization semantics and do not emit status noise for ordinary silent wakes.

The default-branch merge is the activation boundary; an unmerged governance PR is review target/input
and must not govern its own current invocation. Pre-activation free-form/legacy messages remain
historical evidence under then-authoritative default-branch governance and are not a retroactive
template finding.
