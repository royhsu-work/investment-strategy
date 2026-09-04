## Context

`main@2eb17faa57248ed8218d6ccd47441837268e51e9` already has deterministic dispatch/effect pieces. #138 `issuecomment-5474475020` identifies the defect as duplicated control ownership across Role+Action labels, prose topology, runtime parsers, transport comments and wake orchestration. Human clarification `issuecomment-5475109024` adds #168 de-mailbox, bounded pre-acceptance Explore correction and mandatory N-1 order.

## Decisions

### 1. Minimum state and explicit merge phase

After cutover, normal routed state is `Issue + open/closed + immutable Change + exactly one Action`; Role is derived. Results/reviews/Human decisions are semantic evidence; transport/HANDOFF/history are not routing. Replace generic `merge-pr` with `merge-implementation-pr` and `merge-archive-pr`, both using the existing merge procedure Skill while preserving their distinct review/head/check/linkage/cleanup gates.

### 2. One executable machine authority

A small kernel owns Action vocabulary, Action→Role, finite result→transition/effect mappings, WIP/FIFO/debt classification, effect capabilities, source reauthorization, stale/replay handling and structural postconditions. Dispatch, application and tests consume it directly. `agents/workflow.md` becomes generated or mechanically verified presentation. AGENTS/roles/Skills retain shared protocol, role authority and semantic procedure without a competing executable transition table.

### 3. Typed semantic/application boundary

One authorized worker returns its source Issue/Action, bounded action-owned typed result, narrative/source evidence and bounded effect inputs. The worker cannot select arbitrary successors. Application validates the result, derives legal effects, fresh-reauthorizes source/effect predicates, mutates narrowly and fresh-observes postconditions. Meaning-dependent Explore/Human/OpenSpec/review/implementation judgments remain model-owned.

### 4. #168 run-scoped transport

Runtime check-in comments are request/trigger/audit only. Dispatch/application results belong to the exact Actions run caused by the request and are consumed from that run-scoped surface. Exact request→run→structured-result correlation is mandatory. Missing, ambiguous, failed, cancelled, malformed or expired evidence fails closed; no response-comment fallback exists. Coordination-Issue semantic comments remain separate governed evidence.

### 5. One mapped Action per wake

Normal wake: fresh bootstrap → exact dispatch → one mapped Action → application/postcondition → exit. No successor Action executes in that wake even when Role is unchanged. The selected Action remains internally work-conserving through immediately actionable RED→GREEN→REFACTOR→VERIFY, local correction and bounded exact-resource consumption. Same-role chaining, cross-role wake barriers, fresh-worker same-wake identity and continuation flags are deleted.

### 6. Bounded formalization correction

Before first independent semantic `review-openspec` acceptance, if Propose proves its Explore source/evidence/feasibility premise materially invalid, the executable contract may return the same Issue to `explore-change` even after provisional non-`unset` Change activation. Preserve Change identity, Proposal/PR history and audit evidence; this is not a scope reset or generic backward transition. After independent semantic acceptance, material correction uses `resolve-question` → independent review.

### 7. Stale/replay safety

Every consequence fresh-reads exact source state and effect-specific evidence. Already-satisfied legal postconditions are idempotent and never rewound. Incompatible state, incomplete provenance or ambiguous transport fails closed. Fresh read is not a mutex/CAS.

## Mandatory N-1 delivery

Each stage must be indepently executable/testable/mergeable/deployable on N-1; otherwise split it. #138 completes only after stage 6 and full parent verification.

| Stage | Advances | Still incomplete | N-1 / boundary | Next |
| --- | --- | --- | --- | --- |
| 1 Transport de-mailbox + daily check-in | Run-scoped dispatch/application results; no normal response comments | Kernel/state/wake unchanged | Current comment-trigger bridge remains; rollback restores old transport | 2 |
| 2 Kernel shadow | One executable topology computes shadow decisions | Old production control still owns effects | Stage 1 carries shadow evidence; no mutation cutover | 3 |
| 3 Typed result/application | Typed result→kernel effect→fresh application | Wake and Role+Action state unchanged | Stage 2 equivalence proven; rollback before cutover | 4 |
| 4 Wake simplification | Exactly one mapped Action/wake | Canonical state still old | Stage 3 safely persists successor for later wake | 5 |
| 5 Canonical-state cutover | Action-only routing + explicit merge Actions | Legacy code/prose remains cleanup | Complete live-state plan; irreversible semantic cutover | 6 |
| 6 Deletion/context reduction | Removes superseded selectors/parsers/mailbox/continuation/model-host/prose | Parent outcome complete after full gates | Rollback translates from new state; never restores permanent second authority | Verify |

## Validation and deletion

Tests cover live run-scoped transport E2E, exhaustive kernel topology, fresh application/stale/replay, one-action wake with internal work conservation, governance projection, complete live-state migration, full Python quality and exact-revision strict OpenSpec.

Final production removes normal `agent:*` routing, generic merge-phase inference, Issue-response result mailbox/history correlation, Markdown topology/effect parsing, same-wake successor/wake-barrier logic, obsolete historical compatibility, legacy Responses/model-worker host code and corresponding redundant tests/prose. Historical evidence remains readable but non-authoritative.
