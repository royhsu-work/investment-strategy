# Qualify accepted carrier source

## Why

The current Application accepts external `WORKER_RESULT` comments and retains their original comment identity and bytes as provenance. A later carrier observer still calls the legacy-only `parse_application_request` directly when proving an accepted retirement. That observer rejects a legitimate raw original even when the immutable ACCEPTED intent, exact closed-unmerged PR/head, formal consequence, and remaining carrier evidence are coherent. The existing versionless-retirement fixture still renders `EFFECT_REQUEST`; it does not exercise the normal raw format.

This is a source-observed implementation gap at main `661b58c0148bdcf42a7c29c89a2d774ebae392d3`, not a claimed executed RED or a new retirement policy. The first observable repair is a fresh `qualify_supersession_branch` call recognizing the same already-accepted retirement from either supported original format.

## What Changes

- Consolidate accepted-original reading in the existing Application source owner, preserving the exact request ID/body digest, connector provenance, ACCEPTED identity and historical authorization revision.
- Let the carrier consume a qualified raw original while retaining its stricter persisted-correlation requirement for legacy originals. Existing consumers that require a persisted dispatch-correlation witness for every format remain unchanged.
- Preserve strict typed preflight for raw originals at the existing reader boundary. For immutable historical accepted intent, validate every supplied identity through the existing identity owner before binding omitted machine identity, without imposing fresh-result content requirements. Reuse the existing semantic-intent projection and complete retained-effect comparison, including nested JSON equivalence.
- Add genuine CI Test First coverage through the existing public carrier seam and preserve legacy, physical-original, provenance, identity, exact-head and cardinality regression protection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None at the specification level. This repairs implementation of existing `scheduled-agent-workflow` requirements **Application consequence completion is reconstructable across interruption** and **Active formal transitions require repository-owned provenance**. The existing `repository-governance` ownership, proportionality and Test First requirements also apply. This Change explicitly uses `skip_specs: true`; it has no delta-spec directory and does not redefine canonical requirements.

## Scope and Impact

The production scope is the accepted-original reader in `scheduled_agent_application_bridge.py` and its equivalence consumer in `scheduled_agent_application_carrier.py`, with their existing test modules. No workflow, Role, Action, ResultKind, routing, lifecycle, validation or merge gate changes are proposed. There is no new ingress family, state, registry, dispatcher, recovery engine, token or GitHub client.

The reader is shared by other unfinished Issues. Compatibility is part of this repair: preserve their original requests and immutable accepted intent, do not replay completed effects or rewrite historical results, retain existing legacy correlation checks, and reject cross-Issue/Change/source substitutions. Existing reader consumers keep their current defaults. This helper neither updates other Issues nor changes dependencies, review applicability or carrier ownership.

## Authority and Staged Delivery

This is the first supporting A2 maintenance increment authorized by Human [7199792110](https://github.com/royhsu-work/investment-strategy/issues/478#issuecomment-7199792110), bound to decision [7199709164](https://github.com/royhsu-work/investment-strategy/issues/478#issuecomment-7199709164) and direct approval event `37396880785`. Its separate Change and `maintenance/qualify-accepted-carrier-source` branch use non-closing `Refs #478`; they do not replace the parent Change `repair-runtime-validation-iteration-and-recovery`, create a new tracker, or add a formal dependency.

The then-current N-1 already supplies the source reader, typed parser, semantic projection, public carrier seam and native quality/OpenSpec jobs. The approved maintenance mode supplies only the bounded connector persistence needed to obtain independent semantic review, test-only static PASS/intended RED, minimum GREEN/full VERIFY, independent implementation review, exact-head merge and archive review/merge. It does not preapprove any gate.

This helper is independently executable, testable, reviewable, mergeable and deployable without the future withdrawal or development-transaction capability. Its exit is equivalent raw/legacy qualification under unchanged safety checks, verified in native CI, independently reviewed, deployed and archived. Its completion does not complete #478 or release downstream dependencies.

Mandatory continuation remains: non-ready withdrawal with a reconstructable no-replacement frontier; same-Change fresh-main proposal and new independent acceptance; the approved conditional bootstrap rebind only after its exact replacement prerequisites; non-completing development transactions and multiple commits/wakes per Slice; item-wise semantic authority and manifest/materialization separation; common Task Contract and exact completion CI; canonical consequence/recovery and normal-FAIL/pre-/post-ACCEPT disposition; cross-day submission/continuation; compatibility, independent review, merge, archive and full parent lifecycle. Preserve #479 history and the decision to retire it through the later lawful Application path, without inheriting its unmerged implementation, tests, markers or gates. Preserve the #474/#473/#470/#468/#435 and #483 dependency obligations and #470's broader bounded-await scope. Delivery stages do not reduce the parent outcome or fix its Slice count.

## Validation Boundary

At initial proposal creation, no helper implementation, test execution, RED, GREEN, semantic PASS or deployment had occurred. The initial semantic revision subsequently received independent review, and the test-only raw case obtained native static PASS and intended RED.

A later implementation attempt at `f5786a318625d1ce434918c9e313097bd2047731` passed static checks but failed eight existing legacy supersession/lineage regressions in native [run 45876814250](https://github.com/royhsu-work/investment-strategy/actions/runs/45876814250/job/140105865603). The full fresh-worker parser incorrectly required `result_content` from historical already-accepted intent whose existing wire contract permits its absence. This amendment corrects that mechanism while preserving the original compatibility outcome and existing fixtures; it does not invent missing content or reduce validation. The revised proposal/design/tasks require a new exact-revision strict PASS and independent semantic PASS before the implementation correction. Details and observable closure evidence are in `design.md` and `tasks.md`.
