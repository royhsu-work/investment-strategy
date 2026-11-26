---
name: codebase-design
description: Evaluate interface responsibility, coupling, delivery slices, and test seams during OpenSpec or implementation review.
---

# Codebase Design

Use these concepts to evaluate a concrete design or test decision. The mapped Reviewer procedure supplies the evidence, authority, and finding criteria.

- A **module** owns related behavior behind an **interface** used by callers and tests. A deep module exposes a small interface that hides substantial implementation knowledge. Judge the interface by what callers must know, not by internal size.
- A **seam** is where behavior can vary. An **adapter** implements the interface at that seam. Keep internal seams private. Introduce a new interface where a real variation or dependency requires one.
- **Locality** is how well a decision, fix, or verification stays with its owner. Ask where the complexity would move if an existing abstraction were removed. Prefer a design that keeps the change and its evidence together.

## OpenSpec Review

Compare the proposed plan with the smallest vertical increment that produces an observable result through a real caller interface. Trace responsibility from the caller through the owner and trace how that increment can be verified independently. Challenge a plan that requires unrelated interface changes or later work to prove its own completion. Identify the approved behavior, verifiability, or delivery obligation actually at risk. An independently verifiable alternative can be acceptable without sharing the Reviewer's preferred design.

## Implementation Review

Trace an affected caller-visible result through the actual interface. A test substitute must honor the same contract. Prefer real in-process collaborators when feasible and substitute at actual I/O or service seams. If a dependency has a representative local stand-in, check the same public outcomes through it. A setup failure or a test that only inspects internal calls cannot prove the intended result.

For each affected test, trace the protection it supplies to a current observable contract. Preserve unique regression, safety and supported compatibility coverage. Accept replacement or consolidation when the revised evidence protects that behavior at least as well. Retire tests for implementation assumptions that no longer apply when verified coverage preserves the contract, or when the contract itself was authoritatively retired. Record the affected protection, reason, and replacement or retirement evidence under the existing review procedure.

Treat design patterns and code smells as prompts for investigation. An approved requirement or invariant and revision-bound evidence determine whether a finding blocks delivery. Keep a harmless preference advisory.
