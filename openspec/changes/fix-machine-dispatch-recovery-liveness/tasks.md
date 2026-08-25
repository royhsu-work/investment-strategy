# Tasks: Fix machine dispatch recovery liveness

## Slice 1 — Current-only normal dispatch

- [ ] 1.1 RED — Add a production-path regression with many completed closed workflows, including the #91-compatible duplicate-terminal shape, plus one current formal workflow; prove the current implementation still enumerates historical closed workflow state before authorization.
- [ ] 1.2 RED — Add the formal-zero counterpart with one eligible queued `Lead / explore-change` candidate and with no queued work; instrument GitHub acquisition so the regression proves terminal-history Issue/comment reads are not permitted on the target normal path.
- [ ] 1.3 RED — Add a mapped-Action boundary regression where an older Issue comment is irrelevant to dispatch selection but required by the selected Action's existing evidence-reconstruction contract; prove the target behavior must preserve that comment/evidence after `AUTHORIZE` rather than filtering or truncating Action execution inputs.
- [ ] 1.4 GREEN — Change production acquisition/classification so steady-state normal selection consumes complete current open-Issue state plus complete current closed Issues that still retain workflow routing, without a repository-wide closed-history structural projection.
- [ ] 1.5 GREEN — Preserve complete current enumeration/provenance, WIP=1, current routing/Change coherence, deterministic combined pre-activation ordering, fresh action-entry identity, and effect-time reauthorization.
- [ ] 1.6 GREEN — Keep the read-reduction strictly before the mapped-Action boundary; do not add latest-comment shortcuts, bounded-comment readers, filtering, truncation, summaries, or other changes to action-specific Issue-comment/durable-evidence reconstruction after `AUTHORIZE`.
- [ ] 1.7 REFACTOR — Remove obsolete structural-projection plumbing from the normal authorization path without creating a second classifier, cache, cursor, hidden workflow state, or shared action-evidence filter.
- [ ] 1.8 VERIFY — Run focused dispatch/runtime tests, the history-proportion and mapped-Action evidence-preservation regressions, full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 2 — Closed-routing recovery signal and terminal routing retirement

- [ ] 2.1 RED — Add a regression for a nonterminal coordination Issue closed while its valid `agent:* + action:*` routing tuple remains attached; require current unresolved-close acquisition to find that exact candidate without scanning unrelated closed history.
- [ ] 2.2 RED — Add a terminal-close regression proving repository-owned formal terminal closure must produce a closed Issue with workflow routing removed while preserving unrelated labels; add the same behavior for legal `NO_CHANGE_REQUIRED` / `NO_GO` research closure.
- [ ] 2.3 RED — Add incomplete/malformed unresolved-close enumeration cases and multiple closed-routing candidates; require fail-closed behavior rather than model inference.
- [ ] 2.4 GREEN — Implement complete paginated closed-routing acquisition using the existing workflow `agent:*` labels, deduplicate by Issue identity, and validate the current routing/Change shape.
- [ ] 2.5 GREEN — Update repository-owned terminal Issue-close effects so close plus routing retirement is one logical fresh-read mutation that preserves unrelated labels and is fresh-observed afterward.
- [ ] 2.6 GREEN — Keep exactly one qualifying closed-routing candidate at formal-zero on the existing bounded `Lead / resolve-question` recovery path; coexistence with open formal work, multiple candidates, or indeterminate evidence remains `FAIL_CLOSED`.
- [ ] 2.7 REFACTOR — Reuse existing routing state as the recovery signal; do not add a recovery label/registry, lifecycle status, lease, lock, heartbeat, retry counter, or second DAG.
- [ ] 2.8 VERIFY — Run focused close/recovery tests, full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 3 — Legacy routing normalization and terminal-evidence correctness

- [ ] 3.1 RED — Reproduce the pre-existing legacy state where completed closed workflow Issues still retain routing labels and prove that steady-state closed-routing acquisition would otherwise misclassify them as current unresolved work.
- [ ] 3.2 RED — Add the exact #91 terminal-evidence shape with multiple compatible canonical `LIFECYCLE_COMPLETE` journals; require migration/recovery classification to treat them as one terminal fact rather than `indeterminate` from raw comment count.
- [ ] 3.3 RED — Add contrast coverage where otherwise valid terminal journals disagree on immutable terminal revision/Archive identity and must remain `indeterminate` / fail closed.
- [ ] 3.4 GREEN — Implement the one-time repository-owned legacy normalization path: completely enumerate the pre-existing closed routed set, remove only workflow routing labels from entries proven terminal/retired while preserving unrelated labels/body/comments/state, and leave/restore real unfinished obligations as explicit recovery work.
- [ ] 3.5 GREEN — Make normalization fail closed on incomplete/ambiguous evidence; rollout must not claim the history-independent steady state is ready while unresolved legacy routing debt remains.
- [ ] 3.6 GREEN — Implement the minimum semantic terminal-evidence comparison needed by normalization and exceptional recovery; compatible replay is terminal, conflicting immutable identity remains indeterminate.
- [ ] 3.7 REFACTOR — Leave no recurring migration cursor, cutover watermark, terminal-history cache, or generic event-sourcing/history framework after normalization.
- [ ] 3.8 VERIFY — Run focused migration/terminal tests, the exact #91 regression, full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 4 — Bounded machine diagnostic for non-authorizing decisions

- [ ] 4.1 RED — Add bridge parser/render tests proving `NO_WORK` and `FAIL_CLOSED` carry exactly one bounded machine-owned `Reason` while containing no Issue/Role/Action tuple.
- [ ] 4.2 RED — Prove the diagnostic cannot be parsed or consumed as workflow routing/effect authority and that exact request-comment correlation remains mandatory.
- [ ] 4.3 GREEN — Extend the durable `DISPATCH_DECISION` render/parse contract to publish the existing production `DispatchDecision.reason` for `NO_WORK` / `FAIL_CLOSED` only.
- [ ] 4.4 GREEN — Keep `AUTHORIZE` tuple semantics unchanged and reject malformed decisions that mix a non-authorizing disposition with an Issue/Role/Action tuple.
- [ ] 4.5 REFACTOR — Bound diagnostic values to stable repository-owned classifier output; do not emit exception traces, arbitrary GitHub payloads, or model prose.
- [ ] 4.6 VERIFY — Run focused bridge tests, full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 5 — Governance alignment and end-to-end regression

- [ ] 5.1 RED — Update/add governance regression coverage showing shared governance must no longer require a complete closed-history structural projection for normal selection and must instead require complete current open plus unresolved closed-routing observations while preserving the downstream mapped-Action evidence boundary.
- [ ] 5.2 GREEN — Make the minimum `agents/AGENTS.md` wording change required to align with the approved canonical behavior; do not duplicate executable classifier mechanics into prose, change workflow topology, or alter existing role/Skill evidence-consumption semantics.
- [ ] 5.3 GREEN — Add end-to-end production coverage proving normalized #91-like terminal history + one current legal queued Explore yields `AUTHORIZE` without reading #91/history as authorization input.
- [ ] 5.4 GREEN — Add the companion current-recovery cases: one closed routed unfinished candidate at formal-zero routes `Lead / resolve-question`; the same candidate coexisting with an open formal workflow fails closed; multiple/indeterminate candidates fail closed.
- [ ] 5.5 GREEN — Add end-to-end terminal-close coverage proving closed+unrouted is the durable terminal postcondition and a later wake excludes it from current unresolved recovery.
- [ ] 5.6 GREEN — Add end-to-end coverage proving that once dispatch returns `AUTHORIZE`, the selected mapped Action still reconstructs all evidence required by its existing contract, including an older required Issue comment that dispatch itself did not need for selection.
- [ ] 5.7 REFACTOR — Remove obsolete tests/wording that equate safety with repeated historical reconstruction while preserving tests for multiple formal workflows, incomplete observations, stale current state, genuine recovery ambiguity, exact action identity, and complete action-specific evidence reconstruction.
- [ ] 5.8 VERIFY — Run all focused workflow/governance tests, complete pytest suite, mypy, ruff, and `openspec validate --all --strict --json --no-interactive` against the exact final implementation revision.

## Completion evidence

- [ ] 6.1 Record the exact implementation PR head used for final verification and preserve test/quality/OpenSpec evidence for that revision.
- [ ] 6.2 Record exact legacy-normalization evidence showing pre-existing terminal routed history was normalized or that any unresolved/ambiguous entry correctly blocked rollout rather than being silently ignored.
- [ ] 6.3 Demonstrate from production-path evidence that completed terminal history no longer participates in normal authorization while current premature-close routing debt remains recoverable/fail-closed as specified.
- [ ] 6.4 Demonstrate that dispatch read-reduction did not alter the selected mapped Action's existing durable evidence reconstruction/consumption semantics, including required Issue-comment completeness where applicable.
- [ ] 6.5 Confirm no lightweight-runtime/`uv`/packaging change, recovery registry/label, cursor/watermark/cache, lock/lease/heartbeat, second DAG, or unrelated #138 scope entered this Change.
