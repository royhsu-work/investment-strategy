# Tasks: Fix machine dispatch recovery liveness

## Slice 1 — Current-only normal dispatch

- [x] 1.1 RED — Add a production-path regression with many completed closed workflows, including the #91-compatible duplicate-terminal shape, plus one current formal workflow; prove the current implementation still enumerates historical closed workflow state before authorization.
- [x] 1.2 RED — Add the formal-zero counterpart with one eligible queued `Lead / explore-change` candidate and with no queued work; instrument GitHub acquisition so the regression proves retired terminal-history Issue/comment reads are not permitted on the target normal path.
- [x] 1.3 RED — Add a mapped-Action boundary regression where an older Issue comment is irrelevant to dispatch selection but required by the selected Action's existing evidence-reconstruction contract; prove the target behavior must preserve that comment/evidence after `AUTHORIZE` rather than filtering or truncating Action execution inputs.
- [x] 1.4 GREEN — Change production acquisition/classification so steady-state normal selection consumes complete current open-Issue state plus complete current closed-routing debt, without a repository-wide closed-history structural projection.
- [x] 1.5 GREEN — Preserve complete current enumeration/provenance, WIP=1, current routing/Change coherence, deterministic combined pre-activation ordering, fresh action-entry identity, and effect-time reauthorization.
- [x] 1.6 GREEN — Keep the read-reduction strictly before the mapped-Action boundary; do not add latest-comment shortcuts, bounded-comment readers, filtering, truncation, summaries, or other changes to action-specific Issue-comment/durable-evidence reconstruction after `AUTHORIZE`.
- [x] 1.7 REFACTOR — Remove obsolete structural-projection plumbing from the normal authorization path without creating a second classifier, cache, cursor, hidden workflow state, or shared action-evidence filter.
- [x] 1.8 VERIFY — Run focused dispatch/runtime tests, the history-proportion and mapped-Action evidence-preservation regressions, full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 2 — Closed-routing debt acquisition and concurrency-safe terminal retirement

- [x] 2.1 RED — Add a regression for a nonterminal coordination Issue closed while its valid `agent:* + action:*` routing tuple remains attached; require current closed-routing acquisition to find that exact candidate without scanning unrelated retired history.
- [x] 2.2 RED — Add partial-retirement regressions for `closed + agent:* only` and `closed + action:* only`; prove either residue remains discoverable and cannot be mistaken for retired terminal history.
- [x] 2.3 RED — Add a terminal-close concurrency regression where an unrelated label is added after the effect's fresh read but before workflow routing is retired; prove full-label replacement would lose it and the target behavior must preserve it.
- [x] 2.4 RED — Add incomplete/malformed closed-routing enumeration cases across the complete governed routing-label vocabulary and require fail-closed behavior rather than model inference.
- [x] 2.5 GREEN — Implement complete paginated closed-routing acquisition over every governed `agent:<role>` and `action:<action>` label with `state=closed`, union/deduplicate Issue identities, fresh-observe candidate state, and treat any workflow routing residue as debt.
- [x] 2.6 GREEN — Update repository-owned formal and pre-Change terminal close effects so the logical postcondition is `closed + no workflow routing`, but implement it as replay-safe narrow effects: close state without label replacement, fresh-read, remove only exact currently observed workflow routing labels one at a time with fresh pre/postconditions, and fresh-observe final postcondition.
- [x] 2.7 GREEN — Make interrupted retirement reconstructable: do not replay already-complete state transitions, leave partial routing residue visible as debt, and allow later candidate-bound cleanup to remove only missing workflow residue after fresh terminal proof.
- [x] 2.8 REFACTOR — Remove any full-label replacement assumption from terminal retirement; never treat fresh-read routing as mutex/CAS and do not add a lock, lease, heartbeat, retry counter, recovery registry, or second DAG.
- [x] 2.9 VERIFY — Run focused close/debt/concurrency tests, including unrelated-label preservation and action-only/agent-only residue, plus full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 3 — Candidate-bound debt resolution and terminal-evidence correctness

- [x] 3.1 RED — Reproduce pre-existing closed routed terminal history and prove the target must not rely on an unowned bulk migration mutation to reach steady state.
- [x] 3.2 RED — Add the exact #91 terminal-evidence shape with multiple compatible canonical `LIFECYCLE_COMPLETE` journals; require exceptional debt classification to treat them as one terminal fact rather than `indeterminate` from raw comment count.
- [x] 3.3 RED — Add contrast coverage where otherwise valid terminal journals disagree on immutable terminal revision/Archive identity and must remain `indeterminate` / fail closed.
- [x] 3.4 RED — Add multiple-debt coverage proving: one or more proven terminal/retired candidates may yield at most one deterministic cleanup candidate; an unfinished candidate is never reopened while another debt candidate or open formal workflow exists; multiple unfinished or any indeterminate candidate fails closed.
- [x] 3.5 GREEN — Extend production executable classification so it may authorize `Lead / resolve-question` for one exact closed-routing candidate with a constrained machine-derived disposition: terminal/retired cleanup or qualifying unfinished recovery. Candidate ordering for proven terminal cleanup is lower Issue number only after terminal classification.
- [x] 3.6 GREEN — Extend repository-owned application so a terminal/retired `Lead / resolve-question` result can retire only that exact closed candidate's currently observed workflow routing residue, while an unfinished candidate retains the existing bounded reopen semantics; fresh-reauthorize candidate identity/disposition/state before every durable effect.
- [x] 3.7 GREEN — Implement the minimum semantic terminal-evidence comparison needed by candidate classification; compatible replay is terminal, conflicting immutable identity remains indeterminate.
- [x] 3.8 GREEN — Update `agents/roles/lead.md` and `agents/skills/openspec-change/SKILL.md` only as required to make the existing `Lead / resolve-question` owner/procedure explicit for candidate-bound terminal routing-debt cleanup; preserve all existing specification-resolution and unfinished recovery responsibilities.
- [x] 3.9 REFACTOR — Remove the standalone bulk legacy-normalization concept; leave no migration action, startup mutation hook, activation flag, recurring migration cursor, cutover watermark, terminal-history cache, or generic event-sourcing/history framework.
- [x] 3.10 VERIFY — Run focused debt-resolution/terminal tests, the exact #91 regression, role/Skill governance tests, full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 4 — Bounded machine diagnostic for non-authorizing decisions

- [x] 4.1 RED — Add bridge parser/render tests proving `NO_WORK` and `FAIL_CLOSED` carry exactly one bounded machine-owned `Reason` while containing no Issue/Role/Action tuple.
- [x] 4.2 RED — Prove the diagnostic cannot be parsed or consumed as workflow routing/effect authority and that exact request-comment correlation remains mandatory.
- [x] 4.3 GREEN — Extend the durable `DISPATCH_DECISION` render/parse contract to publish the existing production `DispatchDecision.reason` for `NO_WORK` / `FAIL_CLOSED` only.
- [x] 4.4 GREEN — Keep `AUTHORIZE` tuple semantics unchanged and reject malformed decisions that mix a non-authorizing disposition with an Issue/Role/Action tuple.
- [x] 4.5 REFACTOR — Bound diagnostic values to stable repository-owned classifier output; do not emit exception traces, arbitrary GitHub payloads, or model prose.
- [x] 4.6 VERIFY — Run focused bridge tests, full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 5 — Governance alignment and end-to-end regression

- [x] 5.1 RED — Update/add governance regression coverage showing shared governance must no longer require a complete closed-history structural projection for normal selection and must instead require complete current open plus closed-routing-debt observations over all governed role/action labels while preserving the downstream mapped-Action evidence boundary.
- [x] 5.2 GREEN — Make the minimum `agents/AGENTS.md` wording change required to align current routing-debt, candidate cleanup, WIP/recovery, and narrow terminal-retirement behavior; do not duplicate executable classifier mechanics into prose or add a new workflow node.
- [x] 5.3 GREEN — Apply the proposal's Skill maintenance traceability: modify only `agents/skills/openspec-change/SKILL.md` for the new candidate-bound `resolve-question` branch, modify `agents/roles/lead.md` only for matching ownership clarity, and add/remove no Skills.
- [x] 5.4 GREEN — Add end-to-end production coverage proving a #91-like terminal routed candidate is selected for one candidate-local cleanup, becomes closed+unrouted without losing unrelated labels, and a later wake can authorize current work without reading #91/history as normal authorization input.
- [x] 5.5 GREEN — Add the companion current-recovery cases: one closed routed unfinished candidate at formal-zero routes `Lead / resolve-question`; the same unfinished candidate coexisting with an open formal workflow fails closed; proven terminal debt may be cleaned without reopening; multiple unfinished/indeterminate candidates fail closed.
- [x] 5.6 GREEN — Add end-to-end terminal-close coverage proving a partial retirement remains observable and later cleanup completes the `closed + unrouted` durable postcondition before the Issue leaves current debt.
- [x] 5.7 GREEN — Add end-to-end coverage proving that once dispatch returns `AUTHORIZE` for an ordinary mapped Action, the selected Action still reconstructs all evidence required by its existing contract, including an older required Issue comment that dispatch itself did not need for selection.
- [x] 5.8 REFACTOR — Remove obsolete tests/wording that equate safety with repeated historical reconstruction or bulk migration while preserving tests for multiple formal workflows, incomplete observations, stale current state, genuine debt/recovery ambiguity, exact action identity, and complete action-specific evidence reconstruction.
- [x] 5.9 VERIFY — Run all focused workflow/governance tests, complete pytest suite, mypy, ruff, and `openspec validate --all --strict --json --no-interactive` against the exact final implementation revision.

## Completion evidence

- [x] 6.1 Record the exact implementation PR head used for final verification and preserve test/quality/OpenSpec evidence for that revision.
- [x] 6.2 Record exact candidate-bound routing-debt evidence showing pre-existing terminal routed history is drained only one executable-selected Issue at a time, or that unresolved/ambiguous debt correctly blocks unsafe cleanup/recovery rather than being silently ignored.
- [x] 6.3 Demonstrate an interrupted terminal retirement with only partial workflow-routing residue remains discoverable and completes without replacing or losing unrelated labels.
- [x] 6.4 Demonstrate from production-path evidence that retired terminal history no longer participates in normal authorization while current premature-close routing debt remains recoverable/fail-closed as specified.
- [x] 6.5 Demonstrate that dispatch read-reduction did not alter the selected mapped Action's existing durable evidence reconstruction/consumption semantics, including required Issue-comment completeness where applicable.
- [x] 6.6 Confirm no lightweight-runtime/`uv`/packaging change, bulk migration action, recovery registry/label, cursor/watermark/cache, lock/lease/heartbeat, second DAG, or unrelated #138 scope entered this Change.
