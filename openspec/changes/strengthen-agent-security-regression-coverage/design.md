# Design: Deterministic Agent and suppression-safety regressions

## Decision

Use deterministic repository tests/fixtures to protect two already-demonstrated security boundaries without creating a second runtime policy engine or scanner:

1. the existing Scheduled-Agent authority/trust boundary; and
2. material safety assumptions behind narrowly scoped security lint suppressions when static linting cannot preserve those assumptions over time.

## Requirements trace

- `scheduled-agent-workflow` / `Agent security boundaries have deterministic regression coverage` → proposal `Why` and `What Changes`.
- Source authority: #49 fresh Explore `issuecomment-5311100572`; required deferred source #35 `issuecomment-5291586680`; #48 current Ruff/S603 evidence.

## Test model

### Slice A — Authority-source boundary

Deterministic fixtures represent conflicting feature-branch, Issue/PR/comment/source/external/prior-conversation/Scheduled-Task instructions. Assertions remain anchored to default-branch governance/role/skill ownership and prove the fixtures stay work input only.

This protects against structural contract drift. It does not claim to prove that every future model ignores every adversarial string.

### Slice B — Role and Human authority boundary

Representative work input attempts to grant Executor specification authority, asks Reviewer to mutate governed artifacts to make its own gate pass, and claims Human approval through natural language. Tests assert the existing canonical role and provenance contracts; they do not duplicate the Human-decision binding algorithm.

### Slice C — Security-suppression semantic invariants

The current baseline contains three equivalent `S603` exceptions in test helpers. Each currently calls a repository-owned fixed script through `sys.executable`, with `shell` not enabled. The exception rationale is safe only while those properties and the trusted argument boundary remain true.

Add focused deterministic assertions over the concrete helper source/structure or an equally narrow reusable test representation so a later edit fails if a suppressed site stops satisfying the justified boundary. For the current sites the guarded properties are:

- executable is `sys.executable`;
- target script is the repository-owned helper constant, not a caller-selected executable/path;
- shell execution is absent/not enabled;
- ordinary argument values do not expand to arbitrary unvalidated external-derived values behind the suppression;
- if a specific external-derived argument is required, its validation boundary is explicit and deterministic rather than inferred from the suppression.

The regression must therefore fail when a call retains the same fixed interpreter/script and `shell=False` but starts forwarding an arbitrary unvalidated external-derived value as an ordinary argument. This remains a concrete structural/semantic contract for the three demonstrated suppressed sites, not general taint inference.

The tests should detect semantic drift in the current justified sites, not infer general taint safety. If a future suppression has materially different safety assumptions, it needs its own demonstrated requirement before being brought under this contract.

## Ownership boundary

- `agents/AGENTS.md`, roles, mapped skills, and canonical specs remain normative authority; fixtures/tests are evidence only.
- #48/current Python Quality configuration owns Ruff `S` rule selection and whether a concrete lint finding receives a scoped exception.
- This change owns only deterministic regression proof for already-justified security assumptions where static linting alone leaves a demonstrated drift gap.
- Human-authority provenance mechanics remain owned by their existing canonical requirement/tests.

## Trade-offs

A generic prompt-injection benchmark, suppression registry, taint engine, or second SAST lifecycle would add nondeterminism or duplicated policy without a demonstrated need. Narrow structural tests are less general but directly fail when the repository-owned contracts or the three current suppression assumptions drift.

## Compatibility

- No runtime routing/action/state additions.
- No change to the Human provenance algorithm.
- No change to Ruff rule selection.
- No new label, token, scanner, registry, or external service.
- Existing tests remain authoritative only as regression evidence; normative meaning stays in default-branch governance and canonical specs.