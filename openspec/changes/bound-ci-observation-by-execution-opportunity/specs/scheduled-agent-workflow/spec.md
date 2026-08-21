## MODIFIED Requirements

### Requirement: Selected actions are work-conserving within the fixed invocation role

Once a Scheduled Agent invocation selects one legal workflow Issue and fixes its invocation role, the selected action MUST continue all immediately actionable work while routing, authority, required revision/preconditions, and execution capability remain current. Before returning, the invocation MUST positively prove a legal Invocation Exit from current evidence; absence of such proof requires continuation on the same selected workflow under the fixed invocation role.

A genuine external asynchronous-wait Exit requires an exact awaited resource and positive evidence that the resource cannot be further consumed within the current legal execution opportunity. For an exact external resource just created or triggered by the selected action, a first observation of `absent`, `queued`, or `in_progress` MUST NOT prove that Exit and the action MUST perform at least one subsequent fresh observation of the same exact resource while another legal observation remains executable. Any finite sequence of absent/queued/in-progress observations MUST remain nonterminal resource-state evidence only and MUST NOT independently prove unconsumability, even when no unrelated same-authority work remains.

While the invocation can still legally perform another same-resource observation and routing/revision/preconditions remain current, it MUST continue bounded same-invocation observation rather than voluntarily yield solely because the exact resource remains nonterminal. Ordinary asynchronous-wait Exit MAY be proven only when an independent current invocation-local execution boundary establishes that another legal same-resource observation or consumption cannot be performed in the current invocation. This boundary MUST NOT be manufactured from observation count, elapsed-resource duration, absence of unrelated work, a repository-persisted timer/counter, or hidden waiter state.

If the exact resource becomes terminal while it is still legally consumable, the selected action MUST consume that terminal result immediately and continue when the result is actionable within current authority. If routing, revision, concurrency, or another required precondition becomes stale, the existing stale/precondition Exit applies. If a hard tool/permission/runtime boundary prevents further legal execution after applicable same-authority recovery/disposition has been evaluated, the existing hard execution-boundary Exit applies. A genuinely uncatchable runtime termination may prevent current-run persistence and is handled by later at-least-once reconstruction; the invocation MUST NOT pre-classify such a possible future termination as ordinary asynchronous-wait Exit.

This execution-opportunity contract is invocation-local and MUST NOT introduce a durable timer, sleep schedule, polling/retry counter, heartbeat, lease, hidden waiter, scheduler state, or second workflow DAG. A later wake resuming from a real wait MUST fresh-read the exact awaited resource before concluding that waiting still applies.

#### Scenario: First nonterminal exact-resource observation cannot exit

- GIVEN the selected action has just triggered exact external resource E
- AND routing, revision, authority, and preconditions remain current
- WHEN the first fresh observation finds E absent, queued, or in progress
- THEN that observation is not Invocation Exit Proof
- AND the current invocation performs a subsequent fresh observation of E while another legal observation remains executable

#### Scenario: Repeated nonterminal observations do not prove unconsumability

- GIVEN exact resource E has been observed absent, queued, or in progress more than once in the current invocation
- AND another legal same-resource observation remains executable
- AND no unrelated same-authority work remains
- WHEN Invocation Exit is evaluated
- THEN the finite nonterminal observation sequence does not prove that E cannot be further consumed
- AND the invocation continues bounded observation of E

#### Scenario: Short run becomes terminal after repeated in-progress observations

- GIVEN exact resource E is observed in progress across consecutive fresh observations
- AND E becomes terminal while the current invocation can still legally consume it
- WHEN the next bounded observation obtains that terminal result
- THEN the invocation consumes the terminal result immediately
- AND a prior repeated in-progress observation sequence does not justify an asynchronous-wait Exit

#### Scenario: Explicit execution-opportunity boundary permits asynchronous-wait exit

- GIVEN exact resource E remains absent or nonterminal
- AND routing, revision, authority, and preconditions remain current
- AND current invocation-local runtime/tool evidence establishes that another legal same-resource observation cannot be performed in this invocation
- WHEN Invocation Exit is evaluated
- THEN the genuine external asynchronous-wait Exit may be proven for E
- AND the exact awaited resource identity is preserved for later fresh reconstruction

#### Scenario: Stale precondition uses stale exit rather than asynchronous wait

- GIVEN exact resource E is nonterminal
- AND the selected routing, head revision, concurrency state, or another required precondition becomes stale
- WHEN continued observation from the old context would be unsafe
- THEN the invocation uses the existing stale/precondition Exit
- AND it does not classify E as unconsumable asynchronous-wait evidence

#### Scenario: Hard runtime boundary remains a distinct exit

- GIVEN exact resource E remains nonterminal
- AND a hard tool, permission, or runtime boundary prevents further legal execution
- AND any applicable same-authority recovery/disposition has been evaluated and cannot continue
- WHEN Invocation Exit is evaluated
- THEN the existing hard execution-boundary Exit may be proven
- AND repeated nonterminal observations are not used as a substitute proof
