---
name: lifecycle-finalize
description: Lead procedure for finalize-change and finalize-archive lifecycle preparation and terminal evidence.
---

# Lifecycle Finalize

Mapped Actions: Lead / finalize-change and Lead / finalize-archive.

Fresh-read the current Issue/Change, PR/ref state, OpenSpec status, implementation/archive evidence,
Human input, and exact gates. For finalize-change, determine whether more approved implementation is
required or whether the Change is ready for independent archive review. For finalize-archive, verify
the Change is complete and archive terminal evidence is ready.

Archive preparation owns semantic completeness, exact Change/Issue linkage, non-closing linkage,
archive preparation is a Lead-only semantic step with no duplicate Change, PR, lifecycle state, recovery state, or control mailbox.
deterministic cleanup obligations, and the evidence needed by Reviewer / review-archive. It does not
perform normal PR merge mutation. A premature close or ambiguous cleanup condition is blocked.

Return one structured `archive-ready`, `more-implementation-required`, `lifecycle-complete`,
`human-decision-required`, `no-go`, or `blocked` result. The executable model derives
`review-archive`, `implement-change`, `finalize-archive`, or terminal state; the successor executes
only on a later wake.

The lifecycle result is evidence, not runtime state. Do not create a duplicate Change, PR, lifecycle
state, recovery state, or control mailbox. There is no duplicate Change, PR, lifecycle state, recovery
state, or control mailbox. Optional or deferred prose is not a lifecycle obligation.

## Archive activation carrier

For `finalize-change` returning `archive-ready`, fresh-read exact archive evidence before selecting
effects:

- If no exact successful archive workflow run and archive branch head are present for the current
  default-branch revision, request the invocation-local five-line `ARCHIVE_REQUEST` evidence comment
  and one `workflow-dispatch` effect. The dispatch must use `openspec-archive.yml`, the current
  default branch, exact current revision, and request key
  `archive-<coordination-issue>-<revision>`.
- If the exact archive run already produced the archive branch at the expected head, do not request
  another archive comment or workflow dispatch. Return `archive-ready` with only the missing
  `pull-request-create` mutation.

The archive PR creation effect must bind all carrier identity:
`head=agent/archive-<change>`, `expected_head_sha=<fresh archive branch head>`,
`base=<current default branch>`, and the current default-branch revision observed by the
application. Use a non-draft title and the exact non-closing archive body:

```text
Archive OpenSpec change `<change>`.

This pull request is the repository-owned final archive snapshot. Its non-closing linkage preserves traceability while the coordination Issue remains open; independent Reviewer PASS, unchanged-head verification, current gates, and Lead terminal finalization remain required.

Refs #<coordination-issue>
```

The application must verify the exact archive branch SHA, default-branch ref and SHA, repository
identity, title, body, draft state, open/non-merged state, and absence of an existing PR before
creating the carrier; it must then re-read and verify the same postcondition.

For `finalize-archive`, verify the archive PR is the exact non-closing carrier, the independent
Reviewer PASS and current gates are fresh, the expected head is unchanged, and cleanup is
deterministic before returning `lifecycle-complete`.
