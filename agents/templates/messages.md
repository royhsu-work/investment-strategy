# Canonical Workflow Messages

Messages are durable evidence surfaces. They never select an Issue, grant authority, choose a target,
authorize a retry, or replace current repository state. Every result includes the exact envelope:

Workflow: #<issue-number>
Change: <change-id>
Action: <action>
Role: <derived role>
Result: <result-kind>
Revision: <exact revision or none>
Evidence: <structured reference/content>

## ACTION_RESULT

Use for one semantic Action result. Include the exact typed result, evidence, requested effect
descriptions as untrusted data, and the postcondition/validation reference when application has
completed it.

## REVIEW_RESULT

Use for an independent review gate. Include the reviewed exact revision, PASS/FINDINGS or another
finite result, and precise findings/evidence.

## SLICE_CHECKPOINT

Use only after one implementation slice has passed its required VERIFY gates. Include completed
task IDs, exact revision, gate evidence, and the remaining approved boundary.

## MERGE_RESULT

Use after an explicit merge Action. Include exact PR/head, merge acceptance evidence, mutation
result, and observed postcondition.

## HUMAN_DECISION_REQUIRED

Use only for a decision that requires Human authority or intent. State the unresolved question,
at most three actionable options, material trade-offs, Lead recommendation, and the exact requested
Human response.

## EXECUTION_EXCEPTION

Use for a catchable failure when durable evidence can still be persisted. Preserve the raw observable
error after platform safety redaction, exact Action, attempted operation/tool, relevant revision/base,
whether any mutation completed, and the unfinished work boundary. Include separate classification and
disposition when evidence supports them.

Result templates carry Action identity: Action: <action>; Role is derived, and next Action/successor
is application output, not worker authority.
