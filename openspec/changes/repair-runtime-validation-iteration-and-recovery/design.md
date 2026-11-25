## Context

Application acceptance authorizes exact effects and can precede validator completion. The current application workflow skips its success-dependent completion step after Strict FAIL. Separately, Dispatch rejects repeated historical failure digests before checking current postconditions.

## Goals / Non-Goals

Support same-Action validation iteration and eventual correct completion after interruption. Preserve existing result, routing, dependency, and independent gate ownership. #473 owns proposal checkpointing. #474 owns follow-up materialization and dependency preservation.

## Decisions

1. Keep acceptance bound to an exact effect and candidate. Reuse the existing validation evidence and qualification boundary to recognize a known failure, pending observation, or exact success. Reauthorize the corrected candidate with fresh preconditions. This preserves old accepted evidence without granting competing completion rights. Moving all acceptance after validation would still require an authorization path for candidate persistence and would widen the migration.
2. Reuse the existing postcondition proof owner for Dispatch and continuation. Evaluate fresh facts before applying mutation deduplication. The existing causal evidence identity still gates substantive mutation. No extra routing state or progress store is required.
3. Reconcile Original, Formal Result, and successor as separate obligations with existing application ownership. If an older accepted manifest differs from the current carrier, require independently qualified lineage or the existing legal correction path before completion. Never borrow an exact PASS from another revision.

## Risks / Trade-offs

A runner or checkout failure can resemble a candidate failure. Require validator and identity evidence before offering correction. During rollout, keep changes behind one release boundary until legacy recovery and ordinary validation fail/success paths pass together. Preserve prior outcomes through rollback and re-observation.
