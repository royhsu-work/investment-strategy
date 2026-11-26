## Context

Base: main `4d09480e833e6552c3e2aa247f6f7ff7030b174e`. #481 wrote a native terminal result, then GitHub recorded close and removal one second apart. #458 used the same order within one second. The verifier currently conflates event transport order with the workflow's causal contract. Prototype #486 also showed that accepting either order without checking identity or cardinality would allow wrong or duplicate removals.

## Goals / Non-Goals

**Goals:** One shared terminal-proof rule; producer/fresh consumer agreement; post-deployment evidence that the existing #478 dependency releases.  
**Non-goals:** Changing the terminal writer, inventing another dispatcher or Action, reversing a completed lifecycle, relying on old PR review or CI gates, removing Blocked by, or addressing #479 restart sequencing.

## Decisions

1. Keep result-before-effect causality and require the final closed/no-workflow-route observation. Permit either order of close and the optional recorded route retirement in the same qualified interval. Check route name against the exact terminal Action and reject multiple removals, duplicate closes, reopening, relabeling, wrong request where the accepted-request boundary applies, or partial state. Preserve compatible close-only evidence when existing canonical rules already qualify it.
2. Reuse the current formal qualification owner and the existing I/O adapters. No per-Issue exception and no trust in raw timeline order beyond the required causal boundaries. No replay or retrospective state alteration.
3. Use exact-revision independent OpenSpec review before implementation. Keep the distinction between OpenSpec artifacts and native Action admission. The normal queue is currently blocked; follow the Human-directed manual OpenSpec path through the existing independent maintenance and release boundaries. Author and review the proposal on an exact revision before implementation. No lifecycle route or formal result is fabricated; native Dispatch is not used to advance this Change.
4. Use the existing Python Quality job, not a second CI path. The pinned baseline runs pytest before Ruff and Mypy. After OpenSpec approval, first make a setup-only revision that moves the existing Ruff lint, Ruff format and Mypy steps before pytest, retaining job identity, triggers, and fail-fast behavior, and verify that revision without changing application behavior or tests. Then record a separate test-only revision with CI proof of exact checkout, passing static checks, and the predicted behavioral failure. A failure on the discarded prototype, a tooling failure, or a failing negative control alone is not the fresh RED.

## Risks / Trade-offs

- Mere closure does not establish retirement. Use a positive matrix for both real cases, an opposite-order control, and negative cases on the same public seams.
- A native Bridge may reject a later gate even after dependency selection is repaired. Report the exact live result rather than retry or weaken dependencies.

## Migration Plan

Prepare and independently review this exact proposal and delta; implement only in an authorized path. Obtain native CI proof, independent implementation review, and exact deployment evidence. Then observe the first qualifying, already-scheduled native run and its exact deployed revision and decision artifact. Do not issue a native Dispatch request to advance #485 or to force verification. If no qualifying run has been observed, deployment is not yet release proof. Existing terminal Issues remain as observed.
