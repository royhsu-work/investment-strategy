# Tasks

## 1. RED — consumed implementation-merge recovery

- [x] 1.1 Add a regression fixture reproducing #88: implementation merge is already durable, later `finalize-change`/Archive lifecycle evidence exists, and stale implementation merge recovery attempts routing repair.
- [x] 1.2 Verify the regression fails because current recovery permits backward routing repair after the transition was consumed.

## 2. GREEN — causal-descendant recovery guard

- [x] 2.1 Add the minimum shared recovery invariant preventing an earlier completed mutation/handoff from overwriting canonical routing when same-workflow causal-descendant evidence proves the transition was consumed.
- [x] 2.2 Update `merge-pr` recovery to derive implementation versus Archive context from existing PR/gate/linkage evidence and apply the consumption guard before routing repair.
- [x] 2.3 Preserve journal-only repair when required evidence is missing but routing is already causally beyond the recovered transition.

## 3. RED/GREEN — final Archive symmetry

- [x] 3.1 Add a regression where final Archive merge is durable and valid `LIFECYCLE_COMPLETE` already exists.
- [x] 3.2 Verify stale Archive merge recovery does not recreate or rewrite terminal routing.

## 4. REFACTOR / contract consistency

- [x] 4.1 Ensure the solution adds no new action identity, routing phase/context field, sequence state, lock/lease, or generic forward-only rule.
- [x] 4.2 Check directly related routing/handoff recovery wording for contradictory duplicate semantics and keep one authoritative owner per rule category.

## 5. VERIFY

- [x] 5.1 Run targeted recovery/workflow tests.
- [x] 5.2 Run the full Python test suite, Ruff lint/format checks, and mypy.
- [x] 5.3 Run strict OpenSpec validation for the exact implementation revision.
