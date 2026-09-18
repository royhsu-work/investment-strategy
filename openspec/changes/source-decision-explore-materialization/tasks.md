# Tasks

## 1. Atomic Human-requested Explore materialization

- [ ] 1.1 RED: add focused regression tests showing an explicit Human-requested bounded Formal Explore is not complete when the created Issue lacks `Change: unset` or exactly one `action:explore-change` routing label; verify the RED failure is the missing atomic materialization/postcondition behavior.
- [ ] 1.2 GREEN: implement the minimum existing application/interaction-boundary behavior that materializes and freshly verifies the complete open-Issue + `Change: unset` + `action:explore-change` tuple without adding workflow state or origin classification.
- [ ] 1.3 REFACTOR: reuse existing Issue/routing mutation and postcondition owners; remove duplicated actor-centric decision logic if encountered.

## 2. Source-decision authority and origin-neutral dispatch

- [ ] 2.1 RED: add regressions proving connector writer identity neither removes explicit Human materialization authority nor changes later current-state dispatch eligibility, while an autonomous Agent recommendation alone remains insufficient to authorize materialization.
- [ ] 2.2 GREEN: update the canonical scheduled-agent workflow requirement and shared governance projection so source-decision authority, queue eligibility, reserved Human authority, and physical mutation carrier remain distinct.
- [ ] 2.3 REFACTOR: keep `agents/AGENTS.md` concise and defer normative behavior to the canonical capability instead of creating a second rule surface.

## 3. Preserve Human-reserved provenance and existing scheduling invariants

- [ ] 3.1 RED: add/extend regressions showing connector-created materialization evidence cannot satisfy a later Human-reserved decision and that a coherently materialized Explore remains queued behind existing formal WIP/finish-first ordering.
- [ ] 3.2 GREEN: make only the minimum changes needed for those existing invariants to remain true under the clarified ingress rule.
- [ ] 3.3 REFACTOR: confirm no new Action, result kind, label class, approval/delegation token, origin registry, connector whitelist, queue state, or workflow graph was introduced.

## 4. Verification

- [ ] 4.1 Run focused materialization/dispatch/Human-authority tests.
- [ ] 4.2 Run the full regression suite, type checks, and lint checks required by repository quality governance.
- [ ] 4.3 Run strict OpenSpec validation and resolve all reported issues.
