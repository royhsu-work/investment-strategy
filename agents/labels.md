# Scheduled Agent Labels

These labels are repository workflow vocabulary. Creating/configuring labels is administrative setup;
changing Issue routing remains governed by `agents/AGENTS.md` and the mapped action skill.

## Routing labels

Create these role labels:

- `agent:lead`
- `agent:reviewer`
- `agent:executor`

Create these action labels:

- `action:explore-change`
- `action:propose-change`
- `action:resolve-question`
- `action:finalize-change`
- `action:finalize-archive`
- `action:review-openspec`
- `action:review-implementation`
- `action:review-archive`
- `action:implement-change`
- `action:merge-pr`

An actionable coordination Issue has exactly one legal role/action tuple. Label colors/descriptions are
presentation metadata and do not change routing semantics.

## Advisory label

- `advisory:idle` marks the single optional open Lead idle-advisory Issue.

An advisory Issue has no `agent:*` or `action:*` routing tuple and contains at most three recommendations.

## Reserved Human capabilities

- `human:approved` is the reserved generic Human-decision approval capability. Its current presence is
  necessary but never sufficient by itself: Human-reserved consumers must also validate the exact
  provenance-bound decision comment and qualifying Human-only `labeled` event defined by repository
  governance.
- `intake:approved` remains the distinct Human/maintainer capability marker used only when admitting an
  unambiguously selected idle-advisory direction. Its snapshot alone is not Human-decision proof.

Scheduled Lead, Reviewer, and Executor MUST NEVER add, remove, restore, or manufacture either
`human:approved` or `intake:approved`. They may only observe/consume the capabilities under the
repository-authoritative Human-decision contract. Repository administrators should therefore bootstrap
these labels manually or through Human-operated repository setup, not through scheduled-role procedures.

## Example Human-operated bootstrap

With a suitably authenticated GitHub CLI, a Human/maintainer may create missing labels, for example:

```bash
gh label create 'agent:lead' --description 'Scheduled Lead routing'
gh label create 'agent:reviewer' --description 'Scheduled Reviewer routing'
gh label create 'agent:executor' --description 'Scheduled Executor routing'
gh label create 'action:explore-change' --description 'Lead explores a problem before formal Propose'
gh label create 'action:propose-change' --description 'Lead proposes an OpenSpec change'
gh label create 'action:resolve-question' --description 'Lead resolves specification/lifecycle questions'
gh label create 'action:finalize-change' --description 'Lead finalizes implementation lifecycle state'
gh label create 'action:finalize-archive' --description 'Lead finalizes archive lifecycle state'
gh label create 'action:review-openspec' --description 'Reviewer OpenSpec gate'
gh label create 'action:review-implementation' --description 'Reviewer implementation gate'
gh label create 'action:review-archive' --description 'Reviewer archive gate'
gh label create 'action:implement-change' --description 'Executor implementation work'
gh label create 'action:merge-pr' --description 'Executor revision-authorized PR merge'
gh label create 'advisory:idle' --description 'Lead idle advisory; never a routing tuple'
gh label create 'human:approved' --description 'Reserved provenance-bound Human decision approval'
gh label create 'intake:approved' --description 'Reserved Human workflow-admission capability'
```

The commands above are documentation only; scheduled roles do not obtain authority to mutate the
reserved capabilities from their presence here.
