# Tasks

## 1. Atomic Human-requested Explore materialization contract

- [x] 1.1 RED: add focused contract/regression coverage showing that Human-requested bounded Formal Explore materialization is not complete unless the externally observed GitHub state is one open Issue with `Change: unset` and exactly one `action:explore-change` routing label.
- [x] 1.2 GREEN: encode the minimum canonical/shared contract that assigns the Human-request interpretation and atomic create/update + fresh-read postcondition to the interaction-layer producer that already owns that requested GitHub mutation; do not add Issue creation to Scheduled-Agent worker/application capability.
- [x] 1.3 REFACTOR: keep repository application, mutation carriers, dispatcher, and worker effect capability unchanged unless a concrete repository consumer regression requires a correction; remove duplicated actor-centric decision wording if encountered.

## 2. Source-decision authority and origin-neutral dispatch

- [x] 2.1 RED: add regressions proving connector writer identity does not change later current-state dispatch eligibility, while connector/Issue provenance alone does not manufacture Human-reserved authority or autonomous queue authority.
- [x] 2.2 GREEN: update the canonical scheduled-agent workflow requirement and shared governance projection so source-decision authority, queue eligibility, reserved Human authority, physical mutation carrier, and external interaction-layer materialization responsibility remain distinct.
- [x] 2.3 REFACTOR: keep `agents/AGENTS.md` concise and defer normative behavior to the canonical capability instead of creating a second rule surface.

## 3. Preserve Human-reserved provenance and existing scheduling invariants

- [x] 3.1 RED: add/extend regressions showing connector-created materialization evidence cannot satisfy a later Human-reserved decision and that a coherently materialized Explore remains queued behind existing formal WIP/finish-first ordering.
- [x] 3.2 GREEN: make only the minimum repository changes needed for those existing invariants to remain true under the clarified ingress contract.
- [x] 3.3 REFACTOR: confirm no new Action, result kind, label class, approval/delegation token, origin registry, connector whitelist, queue state, workflow graph, repository Issue-creation surface, or worker effect capability was introduced.

## 4. Verification

- [x] 4.1 Run focused dispatch/Human-authority and materialization-contract tests.
- [x] 4.2 Run the full regression suite, type checks, and lint checks required by repository quality governance.
- [x] 4.3 Run strict OpenSpec validation and resolve all reported issues.
