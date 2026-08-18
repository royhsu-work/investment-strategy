## MODIFIED Requirements

### Requirement: Human-required authority is bound to the repository Human actor

For workflow decisions that governance reserves to Human, durable GitHub actor identity alone MUST NOT satisfy Human authority. Activity from actors other than `royhsu-work` MAY be supporting evidence but MUST NOT satisfy Human-required admission, answers, authorization, or resume conditions.

The default Human-reserved decision predicate SHALL remain provenance-bound to an exact durable `decision_ref`, a qualifying Human-created decision comment, current `human:approved` presence, and a later qualifying Human-only `human:approved` labeled event, as defined by the canonical workflow contract.

Initial Formal Explore admission SHALL additionally permit exactly one creation-bound alternative when all of the following are reconstructable from raw GitHub evidence:

- the coordination Issue was created by `royhsu-work`;
- raw Issue creation provenance has `performed_via_github_app == null`;
- the Issue creation-time body contains exactly one repository-defined declaration `Admission: Lead / explore-change` and declares `Change: unset`;
- current routing is exactly `agent:lead + action:explore-change`; and
- no durable evidence makes the creation-time declaration ambiguous, replaced, or inapplicable.

For this creation-bound alternative, the Human Issue creation event itself SHALL be the admission decision. A second `Human-Decision-For: issue:<N>:admission:lead:explore-change` comment and later `human:approved` event SHALL NOT be required solely to repeat the same initial Explore admission.

Routing labels SHALL remain routing state rather than Human authority. Connector- or Agent-applied routing MAY make an already qualifying Human-created Explore Issue actionable, but MUST NOT make an app-created or provenance-ambiguous Issue Human-admitted.

If required raw creation provenance or the creation-time declaration cannot be reconstructed unambiguously, the creation-bound alternative MUST fail closed. Failure of this alternative MUST NOT weaken or replace the existing provenance-bound Human-decision path, which remains the legal Human admission mechanism when its full predicate is satisfied.

The creation-bound alternative SHALL apply only to initial `Lead / explore-change` admission. Human direct-Propose admission, Human-only advisory admission, canonical `HUMAN_DECISION_REQUIRED` answers/authorization/resume, and all other Human-reserved boundaries MUST continue to use their existing exact `decision_ref` mappings and provenance-bound decision/approval predicate unless a later canonical requirement explicitly changes them.

#### Scenario: Human-created Formal Explore Issue is sufficient admission

- GIVEN Issue N was created directly by `royhsu-work`
- AND raw Issue creation provenance shows `performed_via_github_app == null`
- AND the creation-time body contains exactly `Admission: Lead / explore-change` and `Change: unset`
- AND current routing is exactly `agent:lead + action:explore-change`
- WHEN dispatch evaluates initial Formal Explore admission
- THEN Issue creation itself satisfies the Human Explore admission boundary
- AND no second Human decision comment or `human:approved` event is required solely for that same admission

#### Scenario: Connector-created Human-looking Issue is not Human admission

- GIVEN an Issue displays `user.login == royhsu-work`
- AND raw Issue creation provenance identifies a GitHub App
- WHEN dispatch evaluates creation-bound Explore admission
- THEN the creation-bound alternative fails
- AND later connector-applied routing labels do not manufacture Human authority

#### Scenario: Later connector routing can route but not authorize

- GIVEN a Human-created Issue already satisfies the creation-bound Explore admission predicate
- AND repository tooling later applies `agent:lead + action:explore-change`
- WHEN dispatch evaluates the routed Issue
- THEN those labels may make the already-admitted Issue actionable
- AND the label mutation itself is not treated as the Human admission event

#### Scenario: Ambiguous or mutated creation declaration falls back to existing predicate

- GIVEN creation-time Explore admission meaning cannot be reconstructed unambiguously because required raw provenance or declaration history is unavailable or contradictory
- WHEN dispatch evaluates the creation-bound alternative
- THEN that alternative fails closed
- AND the Issue may proceed only if another independently legal admission path, including the existing full provenance-bound Human decision predicate, is satisfied

#### Scenario: Direct Propose keeps existing Human approval contract

- GIVEN a Human wants to admit a coordination Issue directly to `Lead / propose-change`
- WHEN dispatch evaluates Human authority
- THEN the creation-bound Explore alternative does not apply
- AND the existing exact `issue:<N>:admission:lead:propose-change` provenance-bound decision/approval predicate remains required

### Requirement: Workflow admission is explicitly authority-controlled

Scheduled agents MUST NOT autonomously admit arbitrary Issues, PRs, repository activity, discussions, discovered requirements, or Agent-authored recommendations into workflow work.

Human admission remains valid through the repository Human-authority contract. Initial Formal Explore admission MAY use either the canonical provenance-bound Human decision/approval predicate or the narrowly defined Human-created Issue alternative in the `Human-required authority is bound to the repository Human actor` requirement. No other Human-reserved boundary inherits that shortcut by implication.

Repository-authorized Explore admission remains separately legal only under the canonical bounded repository-authorized origin classes and MUST NOT impersonate Human admission.

#### Scenario: Repository-authorized Explore does not impersonate Human admission

- GIVEN an Explore candidate has valid independent repository-authorized admission evidence under the canonical bounded admission contract
- WHEN dispatch evaluates that candidate
- THEN the candidate may be admitted without manufacturing Human evidence
- AND neither the creation-bound Human shortcut nor `human:approved` is required merely to relabel repository authority as Human authority

#### Scenario: App-created Issue with routing remains unauthorized

- GIVEN an Issue was created through a GitHub App
- AND it currently has `Change: unset + agent:lead + action:explore-change`
- AND no repository-authorized admission source or full provenance-bound Human decision exists
- WHEN dispatch evaluates admission
- THEN the Issue is not eligible Formal Explore work
- AND routing state alone does not authorize it
