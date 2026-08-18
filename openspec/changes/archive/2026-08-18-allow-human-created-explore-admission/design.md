# Design: Human-created Formal Explore admission

## Context

The current Human-authority contract protects reserved boundaries by binding an exact Human decision comment to a later Human-only `human:approved` event. That remains the correct default because actor identity and normalized connector views are insufficient provenance.

The narrow duplication occurs only when the Human directly creates an Issue whose sole creation-time purpose is to admit Formal Explore. In that case the Issue creation event can already carry stronger raw provenance than a later connector-applied routing mutation. The design therefore adds one creation-bound admission alternative without changing the existing decision evaluator used by every other Human-reserved boundary.

## Requirement traceability

| Requirement | Design decisions |
| --- | --- |
| `Human-required authority is bound to the repository Human actor` | D1, D2, D3, D4 |
| `Workflow admission is explicitly authority-controlled` | D2, D4 |

## D1 — Add a separate raw Issue-creation admission predicate

Add a small creation-bound evaluator beside, not inside, the existing general Human decision/approval evaluator.

Its inputs are raw Issue creation evidence plus current routing. It returns qualifying Explore admission only when:

- `user.login == royhsu-work`;
- raw `performed_via_github_app` exists and is `null`;
- the creation-time body contains exactly one `Admission: Lead / explore-change` declaration;
- the same creation-time body declares `Change: unset`;
- current routing is exactly `agent:lead + action:explore-change`; and
- mutation/history evidence does not make the creation declaration ambiguous or invalid.

The existing `is_human_decision_approved` semantics remain unchanged.

## D2 — Separate routing from admission authority

`agent:lead + action:explore-change` labels are operational routing only. They may be applied after Human creation by repository tooling, but they do not establish creation authority.

This preserves a first-principles split:

```text
Human raw creation evidence
        ↓ admission authority
current routing tuple
        ↓ actionability
Lead / explore-change
```

An app-created Issue with identical visible actor/body/routing still fails the Human-created path because raw creation provenance identifies the app.

## D3 — Fail closed on mutation ambiguity and keep the existing fallback

Issue bodies/titles are mutable. The creation-bound shortcut must therefore be used only when the repository can reconstruct the required creation declaration safely.

The implementation should prefer immutable/raw creation-history evidence where available. If the tool/API surface cannot prove the relevant creation declaration or subsequent mutation state unambiguously, the shortcut fails closed rather than inferring unchanged intent from the current body.

Failure of this shortcut is not workflow denial. The existing full `Human-Decision-For + human:approved` path remains available and authoritative when its predicate passes.

## D4 — Keep the shortcut narrowly scoped to initial Explore intake

No generic Human-authority abstraction is weakened. The creation-bound path is consumed only where default-branch governance maps the boundary to initial `Lead / explore-change` admission.

The following keep their existing behavior:

- direct `Lead / propose-change` admission;
- advisory admission;
- answers/resume for canonical `HUMAN_DECISION_REQUIRED`;
- later product/scope/risk/security/privacy/cost decisions;
- repository-authorized Explore origins.

This avoids turning Issue creation into a reusable approval token.

## Human intake declaration

Use one exact, machine-reconstructable declaration:

```text
Admission: Lead / explore-change
Change: unset
```

The declaration is intentionally explicit and action-specific. Free-form phrases such as "please explore" are not parsed as authority.

The declaration may be documented/presented through the existing Human intake guidance surface during implementation. It does not require a new dispatcher action or hidden state.

## Alternatives considered

### Keep the current second approval ceremony for all Explore intake

Rejected for directly Human-created Formal Explore Issues because it repeats the same admission decision without adding a distinct authority boundary.

### Trust current Issue author plus routing labels

Rejected. Connector-created Issues may display `royhsu-work`, and routing can be applied later by automation. Raw creation provenance is required.

### Treat any Human-created Issue as Explore admission

Rejected. Human creation must carry an explicit creation-time Formal Explore declaration; ordinary Issues are not workflow admission by default.

### Generalize Issue creation as Human authority for all boundaries

Rejected. Later reserved decisions need correlation to a specific current boundary and retain the existing exact decision-reference/approval predicate.

## Risks and mitigations

- **Risk: connector-created Issue impersonates Human intake.** Mitigation: raw `performed_via_github_app == null` is mandatory.
- **Risk: later routing is mistaken for admission.** Mitigation: routing and authority are evaluated separately.
- **Risk: edited Issue body changes original intent.** Mitigation: ambiguous mutation/history fails the shortcut and falls back to the existing predicate.
- **Risk: shortcut spreads to later decisions.** Mitigation: canonical scope explicitly limits it to initial Explore admission and regression tests cover direct Propose/escalation negative cases.

## Deferred / related work

- #84/#85 may later revise the Skill package architecture. This Change does not depend on or redesign that work.
- #83's reusable provenance-acquisition procedure remains separate Skill-maintenance input; this Change only needs the smallest runtime evidence path required by the approved behavior.
