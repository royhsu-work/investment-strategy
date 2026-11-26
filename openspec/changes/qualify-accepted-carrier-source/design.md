# Design: accepted carrier original-source equivalence

## Decision Boundary

Apply the Human-approved A2 scope and all still-applicable parent intent recorded in #478. The approved outcome is a bounded prerequisite repair, preserving full parent continuation. The current default branch governs execution; this candidate does not govern its own authoring or authorize implementation. No product strategy or public Decision/Backtest artifact changes are involved.

This is a zero-delta implementation repair. Canonical `Application consequence completion is reconstructable across interruption` already requires raw external `WORKER_RESULT`, immutable original provenance, an in-process envelope, legacy compatibility and accepted-intent continuation. `Active formal transitions require repository-owned provenance` already requires fresh-process reconstruction. `repository-governance` owns consequence SSOT, proportionality and genuine Test First. The configured `spec-driven` adapter supplies the explicit `skip_specs: true` path.

## Current Evidence and Failure

At base `661b58c0148bdcf42a7c29c89a2d774ebae392d3`:

- Carrier `_accepted_formal_result_is_proven` independently reads and hashes the original, then invokes legacy-only `parse_application_request`. A raw original returns no envelope.
- Application `_read_accepted_original_request` already qualifies the original ID, bytes, actor, accepted identity and authorization revision, and supports raw or legacy normalization. It never needs a current Dispatch to recreate historical authority.
- Raw canonicalization preserves the semantic payload; Application later adds machine identity. Therefore the normal minimal raw payload can omit Issue/Role/Action/Change and optional `evidence_ref`. Merely swapping the carrier reader still leaves a semantic-projection mismatch.
- Carrier `_canonical_intent_effect_json` preserves retained intent while normalizing nested `payload_json` serialization. The existing typed/content-only `_worker_semantic_projection` is insufficient to replace the complete retained-effect comparison.
- `test_versionless_ingress_proves_accepted_lead_retirement` uses a legacy envelope with an omitted projection-version field. It remains useful legacy coverage, but is not raw coverage.

These are source observations. The first native intended RED is still required and must fail on the public qualification result after static checks pass.

## Ownership and Proportionality

| Consequence or concern | Existing owner | Treatment |
| --- | --- | --- |
| Exact accepted original provenance and format normalization | Application accepted-original reader | CONSOLIDATE carrier duplicate reading/parsing into this owner |
| Worker typed meaning and optional defaults | Existing typed worker parser and semantic-intent projection | REUSE; validate before binding immutable machine identity |
| Complete accepted/source semantic equivalence | Existing carrier equivalence consumer and nested JSON normalization | REUSE; preserve retained effects rather than comparing content alone |
| Exact closed-unmerged carrier/head, accepted close target, formal correlation, lifecycle, uniqueness and ancestry | Existing carrier qualifier | NO-DELTA |
| Dispatch, Action/Role/Result selection, Human/review/merge gates and other Issue dependencies | Existing executable owners | NO-DELTA |

No additional source metadata, public protocol, dataclass, registry, persisted state or second positive carrier proof is needed. The narrow reader policy below exists because legacy carrier proof requires a persisted correlation while raw source authority is the exact ACCEPTED original. Removing all correlation checks or inventing a current-dispatch witness would weaken required safety.

## Chosen Interface and Flow

Extend the existing accepted-original reader with `require_legacy_dispatch_correlation: bool = False`. Retain the current meaning and default of `require_dispatch_correlation`:

| Original format and caller policy | Required behavior |
| --- | --- |
| Raw, existing `require_dispatch_correlation=True` | Still reject: an internally generated correlation is not a persisted witness |
| Raw, carrier's new legacy-only policy | Normalize only after the exact immutable ACCEPT/source/provenance checks |
| Legacy, either strict policy enabled | Require the existing exact persisted dispatch correlation |
| Existing consumers with both default policies | Preserve their current compatibility contract |

The carrier passes the new legacy-only policy; wire-format detection stays inside the existing reader. The carrier builds the source only from its already-coherent formal event and ACCEPTED decision, and the reader verifies that source against the record. Do not call a fresh planner, current Dispatch, current route or new authorization path to reconstruct history. Do not change physical-original consumers' defaults or their effect semantics.

After qualification, use the existing typed parser to reject any supplied contradictory identity before deriving omitted machine fields. In memory, bind Issue/Role/Action/Change to the immutable accepted source and apply only the parser's supported defaults (`evidence_ref=null`, absent effects as `[]`). Use the existing Application-owned semantic-intent projection/version handling on that bound representation. Never edit the original comment, digest, accepted record or saved content, and never accept an external projection-version claim prohibited by the raw parser.

Compare the complete retained semantic intent, including result kind, evidence/content and retained effects. Preserve the existing nested-JSON normalization so serialization whitespace is not a semantic difference, while changed targets, heads, payload fields, evidence or content remain differences. Invocation-owned formal projections may be removed only by the existing semantic projection; do not discard arbitrary worker effects or compare only the selected close effect. Do not use typed-result/content equality alone as complete equivalence.

The existing carrier owner then applies its unchanged exact close-effect, PR/head, closed-unmerged, branch, formal correlation, authorization-revision ancestry, uniqueness and lifecycle predicates. Source-format equivalence neither grants withdrawal authority nor creates a replacement, transfers old review/CI gates, or declares parent readiness. A read failure or malformed/ambiguous source remains non-qualification, never a write or guessed fallback.

## Observable Verification

Use `qualify_supersession_branch`, the real caller-facing qualification seam, with real in-process parsers/projectors and the existing representative GitHub read substitute. Do not assert private call counts or recompute the expected result with the target implementation.

The first behavior cycle uses a qualified exact closed-unmerged old PR/head, accepted Lead READY close intent and formal result. Its original is a real minimally framed `WORKER_RESULT`, omitting Issue/Role/Action/Change, `evidence_ref` and external `_semantic_intent_version`, with one exact close effect and the correct original-body digest. The accepted intent contains Application-bound identity. Expected public outcome: qualification succeeds. On N-1 the source predicts failure; only an actual executed native test failure after static PASS can qualify as RED.

After its minimum GREEN, cover remaining behavior differences one at a time as needed:

- Minimal and explicitly matching raw identity have equivalent outcomes; conflicting supplied Issue/Change/Role/Action, bad body digest, actor/app, accepted identity, changed evidence/content or close target/head do not qualify.
- A correct legacy persisted correlation remains accepted; missing or wrong correlation remains rejected. The existing all-format strict policy still rejects raw. No shared-reader default changes for older unfinished work.
- Nested JSON formatting differences remain accepted; retained effect changes and additional retained mutations remain rejected. Preserve the existing legitimate invocation-effect projection coverage.
- Preserve unique legacy, physical-original, authorization ancestry, exact-head, closed/merged state, formal-result provenance, duplicate acceptance/carrier and historical compatibility protections in the existing carrier/bridge suites.

Use generic Issue/Change fixtures, not a #478 exception. Explicitly verify cross-Issue/Change substitution rejection so the shared reader cannot attach another unfinished Issue's original to this accepted record. Tests that already pass and protect unchanged behavior are regression evidence, not a manufactured RED. Retain the versionless legacy test and clarify its name/docstring if needed; do not remove or weaken it to make raw coverage green.

Every new executable behavior follows native CI-only, static-first Test First: exact test-only revision, Ruff lint, format and Mypy success, intended pytest failure; then the minimum sufficient implementation and native GREEN. A setup/import/static/unrelated failure is not RED. Complete the Slice only after full native regression, lint, format, type and exact-R strict validation pass. Record exact commit ordering, run/attempt/job, checkout and failing/passing test evidence. No local test run or replayed retrospective failure may substitute.

## N-1 Delivery and Recovery

| Boundary | Existing capability and proof |
| --- | --- |
| Input/authorization | Fresh main, direct A2 decision/comment/event, exact helper paths and branch/PR deduplication; independent semantic review before implementation |
| Materialization | Approved maintenance Connector; fresh complete file content/blob SHA, exact parent/tree/ref, non-force CAS and post-read verification |
| Validation | Existing event-driven Quality and OpenSpec Validate jobs on actual exact revisions; no direct workflow dispatch or new CI mode |
| Completion | One verified helper Slice; implementation task marker only after full verification; independent review and lifecycle gates remain separate |
| Recovery | Observe exact Git objects and CI after interruption; reuse the unique existing helper/PR and missing obligations; unknown writes are never replayed blindly |

The Human-approved maintenance mode supplies development commits without requiring the future Development Transaction to authorize its own first RED. The helper contains no such transaction implementation and does not rebind the parent bootstrap. Parent #478's normal selected Action and result remain separate from this manual helper's independent reviews and lifecycle.

After implementation review and exact-head merge, native archive automation must run the existing pinned CLI. If it has already validated/pushed the exact archive branch but stops at missing helper coordination linkage, the approved maintenance scope permits fresh branch/source/changed-file/cardinality verification and creation or reuse of the one archive PR with non-closing `Refs #478`. Do not rerun an already-completed archive, move canonical files manually or call a failed run successful. Independently review and merge the archive; verify the active helper path is gone and canonical specs are unchanged for this zero-delta Change.

## Parent Outcome Reconciliation

The base already includes the current Test First/independent engineering-review contract and the deployed terminal-qualification repair; those remain regression obligations. This stage supplies only accepted-original carrier equivalence. All remaining parent requirements listed in `proposal.md` remain mandatory, especially lawful non-ready withdrawal, fresh-main reproposal, the conditional future bootstrap binding, development/manifest/Task/CI/recovery contracts and cross-day completion. No dependency is released, no #479 history is erased, and no new canonical stage state is created by completing this helper. The next supporting increment must be independently scoped and reviewed against its then-current N-1.
