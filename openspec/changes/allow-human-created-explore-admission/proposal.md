# Change: Allow Human-created Explore admission

## Why

The repository's provenance-bound Human-authority contract correctly prevents connector-mediated activity from impersonating Human authority. However, Formal Explore intake currently requires a second `Human-Decision-For` comment plus later Human-only `human:approved` event even when the Human has already directly created an Issue for the sole purpose of authorizing that Explore.

#84 exposed the operational cost of that duplication. #88 then established the narrower property to preserve: a directly Human-created Formal Explore Issue may itself be the admission decision when its raw creation provenance and creation-time admission declaration are reconstructable, while connector/Agent-created Issues and every later Human-reserved boundary remain protected by the existing predicate.

## What Changes

- Add one alternative admission path for initial `Lead / explore-change` intake only: a directly Human-created Issue can establish Human Explore admission when raw Issue creation provenance proves `user.login == royhsu-work` and `performed_via_github_app == null`, the creation-time Issue body contains the exact repository-defined Explore-admission declaration with `Change: unset`, and current routing is legally `Lead / explore-change`.
- Treat routing labels as routing state, not creation authority. Later connector-applied `agent:lead + action:explore-change` labels may route an already-valid Human-created intake but cannot manufacture admission for an app-created Issue.
- Fail closed when creation provenance is unavailable, app-mediated, ambiguous, or the required creation-time declaration cannot be reconstructed safely; the existing provenance-bound `Human-Decision-For + human:approved` path remains available.
- Preserve the existing #47 provenance-bound decision predicate unchanged for direct-Propose admission, advisory admission, escalation answers/resume, and later product/scope/risk/security/privacy/cost decisions.
- Add focused regression coverage for Human UI-created Explore intake, connector-created Human-looking Issues, later connector routing, mutation/ambiguity, missing raw provenance, and fallback to the existing approval path.

## Capabilities

### Modified

- `scheduled-agent-workflow`
  - allow one creation-bound Human Explore admission alternative;
  - preserve existing Human-authority semantics for every other reserved boundary.

## Scope Boundaries

In scope:
- shared Scheduled-Agent admission/Human-authority governance directly needed for initial Formal Explore intake;
- Lead Explore/Propose reconstruction procedures only where needed to consume the new admission alternative;
- `src/investment_strategy/human_authority.py` and focused tests for raw Issue-creation parsing/evaluation;
- the Human intake presentation contract that defines the exact creation-time admission declaration.

Out of scope:
- weakening or replacing `human:approved` generally;
- changing direct-Propose admission;
- changing Human escalation answer/resume authority;
- treating connector mutations as Human actions;
- granting Agent-created Issues Human authority;
- redesigning the broader Skill architecture tracked separately by #84/#85.

## Evidence and Intent

- #47 established the current provenance-bound Human-authority hardening.
- #79/#83 demonstrated why raw GitHub provenance must be reconstructed rather than inferred from normalized snapshots.
- #88 decision-complete Explore established the narrow creation-bound alternative and explicitly retained the existing predicate as the fallback/default for every other boundary.

## Traceability

- Creation-bound Explore admission -> modified `scheduled-agent-workflow` Human authority/admission requirements.
- App-mediated creation rejection and routing/authority separation -> design D1/D2 and regression tasks.
- Mutation/ambiguity fallback -> design D3 and regression tasks.
- Preservation of #47 for all other boundaries -> design D4 and regression tasks.

Refs #88
