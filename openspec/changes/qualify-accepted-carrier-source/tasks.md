# Tasks: qualify accepted carrier source

## 1. Reconstruct the same accepted retirement from supported originals

- [ ] 1.1 Complete the accepted-original carrier equivalence Slice through the existing public qualification seam, preserving legacy and shared-reader safety.

Implement and VERIFY this single observable vertical Slice according to `design.md`; behavior cycles are smaller than the Slice and may require multiple commits/wakes. Do not batch all tests before all implementation.

1. Start with the minimal real raw `WORKER_RESULT` case that omits machine identity and optional evidence, retains the exact close effect, and is bound to a correct immutable ACCEPTED record. Publish a test-only revision. Obtain native static PASS and a pytest failure caused by the missing public qualification behavior; record exact revision/run/job and the actual assertion. Do not claim RED for static, import, fixture, setup or unrelated failures.
2. Apply the minimum implementation: consolidate source reading into the existing accepted-original owner with the narrow legacy-correlation policy; typed-validate before binding immutable identity/defaults; retain complete semantic-intent/nested-effect comparison and all downstream carrier predicates. Obtain native GREEN before selecting the next behavior difference.
3. Verify the remaining raw identity/provenance/effect cases and shared-reader legacy/strict-policy behavior through the same public outcomes and existing boundary substitutes. Add another test-first cycle only for behavior requiring a further implementation change. Preserve existing passing regressions as regression evidence rather than fabricating RED. Include cross-Issue/Change substitution rejection and older physical-original consumer compatibility.
4. Run the existing native full regression suite, Ruff lint/format, Mypy and exact-revision OpenSpec strict validation. Retain unique regression, supported historical compatibility and safety coverage; record the reason and equivalent protection for any affected test consolidation. Do not weaken a test merely to obtain GREEN.
5. Once the whole Slice is verified, mark only this implementation task complete and preserve its exact native RED/GREEN/VERIFY lineage in existing PR delivery evidence. Observe exact final-head validation after the marker commit. A failing candidate is not a completion checkpoint or formal READY result.

### Traceability

- Proposal: existing accepted-source implementation gap, shared impact, bounded A2 authority and full parent continuation.
- Canonical `scheduled-agent-workflow`: **Application consequence completion is reconstructable across interruption**; **Active formal transitions require repository-owned provenance**.
- Canonical `repository-governance`: **Governance rule categories have one authoritative surface**; **Repository design applies project-wide proportionality and simplicity**; **Test-first delivery and independent engineering review preserve observable behavior**.
- `openspec/config.yaml`: implementation-only task markers, vertical behavior delivery, native Test First evidence, full verification and test-lifecycle responsibilities.
- Design: chosen reader policy, immutable source binding, complete semantic equivalence, cross-Issue compatibility, N-1 delivery and recovery.

## Lifecycle Gates and Required Continuation

These are not Executor implementation task markers. Obtain native exact-R strict validation and independent OpenSpec semantic PASS before implementation. After verified implementation, obtain independent exact-head Implementation Review, including refactoring assessment and test-lifecycle review, then exact-head merge/deployed-source verification. Complete native OpenSpec archive and independent Archive Review/merge, using only the approved exact-branch linkage recovery if needed.

This helper's closure does not complete #478. Preserve and hand off all mandatory parent work from `proposal.md` and the Human-approved decision; use later fresh normal Dispatch for parent work after supporting deployment. Do not close #479, create the parent replacement, rebind its bootstrap, change the dependency DAG, transfer historical gates or manufacture a parent result as part of this Slice.
