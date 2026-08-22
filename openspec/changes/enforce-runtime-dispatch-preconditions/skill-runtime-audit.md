# Mapped Skill runtime audit

This implementation audit records how every current mapped action composes with the #133 machine-gated worker/application boundary. It is implementation trace evidence, not a second lifecycle topology or a replacement for the approved OpenSpec contract.

Shared rule: `agents/AGENTS.md` owns the physical runtime split. A machine dispatch authorizes the exact Issue/role/action before a fresh model worker starts; the worker retains the mapped Skill's semantic action ownership but has no durable GitHub write authority; requested durable effects are staged and repository-owned application code fresh-reauthorizes and applies them. Routing successors continue to be validated against `agents/workflow.md`, the sole lifecycle-topology owner.

| Mapped Skill / actions | Audit disposition | Concrete reason |
| --- | --- | --- |
| `openspec-explore` / `Lead / explore-change` | Modified | Earlier wording coupled Explore to Agent-owned executable authorization. It now consumes the machine-selected identity and expresses durable results/routing only through the shared worker/application boundary. |
| `openspec-change` / `Lead / propose-change`, `Lead / resolve-question` | Modified | Earlier correction paths contained Issue-comment Transition-Gate/direct-worker durable-transition assumptions. It now preserves Lead semantic authority while the shared application boundary owns durable effects and fresh post-effect redispatch. |
| `openspec-review` / `Reviewer / review-openspec` | No additional action-local change required | The Skill defines independent semantic review, durable result meaning, and legal successor routing; it does not require a fixed role schedule or model-selected authorization. Common `issue-comment` and `routing-transition` effects cover its durable outputs. |
| `implementation` / `Executor / implement-change` | No additional action-local change required | The Skill defines local RED/GREEN/REFACTOR/VERIFY work and the durable changes Executor is authorized to request. The worker receives local workspace write capability while repository publication is expressed through shared contents/ref/PR operations. No model-visible durable GitHub credential is required. |
| `implementation-review` / `Reviewer / review-implementation` | No additional action-local change required | The Skill is an independent exact-head gate. Its durable outputs are review evidence plus legal routing, covered by common comment/routing effects; it contains no fixed-slot runtime requirement. |
| `merge-pr` / `Executor / merge-pr` | No additional action-local change required | Exact-head merge/cleanup semantics remain action-owned. Physical PR merge and reviewed temporary-ref deletion are represented by the shared `pull-request-merge` and `ref-delete` application operations with fresh target guards. |
| `lifecycle-finalize` / `Lead / finalize-change`, `Lead / finalize-archive` | No additional action-local change required | Lead lifecycle judgment remains unchanged. Issue/tracker/Archive-PR/terminal Issue effects are expressed by the shared issue and PR application operations; dynamic scheduling does not change lifecycle authority. |
| `archive-review` / `Reviewer / review-archive` | No additional action-local change required | The Skill is an independent Archive gate whose durable outputs are review evidence and legal routing, covered by common effects. It does not own scheduling or executable dispatch. |

## Runtime durable-effect coverage

`src/investment_strategy/scheduled_agent_effect_contract.py` contains an explicit profile for all ten mapped role/action identities. Every worker can request the common `issue-comment` and legal `routing-transition` effects. Action-specific repository mutations are additionally bounded as follows:

- `Lead / explore-change`: Issue update/label effects.
- `Lead / propose-change`: Issue, contents, ref, and PR create/update effects required to formalize a Change.
- `Lead / resolve-question`: the Propose-class effects plus source-linked Issue creation for required follow-ups.
- `Lead / finalize-change`: Issue/tracker and final Archive-PR create/update effects.
- `Lead / finalize-archive`: terminal Issue update/label effects.
- Reviewer actions: common review-result comment and legal routing effects only.
- `Executor / implement-change`: contents/ref/PR create/update plus PR ready-for-review effects.
- `Executor / merge-pr`: exact-head PR merge plus reviewed temporary-ref deletion effects.

The application adapter verifies the exact source workflow remains current and applies operation-specific current-target guards (including blob/ref/head expectations) before durable mutation. Accepted batches are followed by a complete fresh dispatch; any selected action, including the same action with remaining work, requires another fresh mapped model invocation.

No mapped Skill gains a direct write credential, no fixed role slot is required, no Issue comment becomes authorization state, and no operation mapping duplicates legal routing topology from `agents/workflow.md`.
